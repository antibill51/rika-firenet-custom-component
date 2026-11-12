import logging
import requests.exceptions

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er

from .const import (
    CONF_CONNECTION_TYPE,
    CONNECTION_TYPE_CLOUD,
    CONF_HOST,
    CONF_DEFAULT_TEMPERATURE,
    CONF_DEFAULT_SCAN_INTERVAL,
    CONF_PENDING_TIMEOUT,
    DEFAULT_PENDING_TIMEOUT,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .core import RikaFirenetCoordinator

_LOGGER = logging.getLogger(__name__)

# CONFIG_SCHEMA est déprécié pour les intégrations configurées via UI,
# mais on le laisse vide pour éviter des erreurs si HA le cherche.
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Rika Firenet component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Rika Firenet from a config entry."""
    _LOGGER.info("async_setup_entry(): %s", entry.entry_id)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_CLOUD)
    host = entry.data.get(CONF_HOST)
    default_temperature = int(entry.options.get(CONF_DEFAULT_TEMPERATURE, 21))
    default_scan_interval = int(entry.options.get(CONF_DEFAULT_SCAN_INTERVAL, 15))
    pending_timeout = int(entry.options.get(CONF_PENDING_TIMEOUT, DEFAULT_PENDING_TIMEOUT))

    coordinator = RikaFirenetCoordinator(
        hass,
        username,
        password,
        default_temperature,
        default_scan_interval,
        pending_timeout,
        connection_type=connection_type,
        host=host,
    )

    try:
        # 'setup' contient des appels réseaux bloquants (requests),
        # donc on l'exécute dans un thread séparé (executor).
        await hass.async_add_executor_job(coordinator.setup)        
        await coordinator.async_refresh()

        if not coordinator.last_update_success:
            raise ConfigEntryNotReady("Coordinator update failed")

    except requests.exceptions.Timeout as ex:
        _LOGGER.warning("Timeout during Rika Firenet setup: %s", ex)
        raise ConfigEntryNotReady from ex

    except Exception as ex:
        _LOGGER.exception("Unexpected error during Rika Firenet setup: %s", ex)
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Nettoyage automatique des appareils et entités orphelins (ex. poêle retiré du cloud)
    await _async_cleanup_orphan_devices(hass, entry, coordinator)

    # On active uniquement les plateformes nécessaires
    enabled_platforms = [
        platform for platform in PLATFORMS if entry.options.get(str(platform), entry.options.get(platform, True))
    ]
    await hass.config_entries.async_forward_entry_setups(entry, enabled_platforms)

    # On attache le listener pour les mises à jour d'options
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    _LOGGER.info("Unloading entry: %s", entry.entry_id)
    
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        
    return unloaded

async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.info("Options updated for entry: %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)

async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow manual removal of a device from the Home Assistant UI."""
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN].get(config_entry.entry_id)
    if not coordinator:
        return True

    # Récupérer les identifiants Rika du device
    rika_identifiers = {
        ident[1] for ident in device_entry.identifiers if ident[0] == DOMAIN
    }

    # Si le poêle est encore actif dans le coordinateur, on refuse la suppression
    active_stove_ids = {str(stove.get_id()) for stove in coordinator.get_stoves()}
    for ident in rika_identifiers:
        if ident in active_stove_ids:
            _LOGGER.warning(
                "Cannot remove device %s: stove %s is still configured and active",
                device_entry.name,
                ident,
            )
            return False

    # Nettoyage des entités associées au device
    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_device(entity_reg, device_entry.id)
    for entity in entities:
        _LOGGER.info("Removing orphan entity: %s", entity.entity_id)
        entity_reg.async_remove(entity.entity_id)

    _LOGGER.info("Device %s (%s) successfully removed", device_entry.name, device_entry.id)
    return True

async def _async_cleanup_orphan_devices(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: RikaFirenetCoordinator
) -> None:
    """Automatically purge devices and entities that are no longer reported by the coordinator."""
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    active_stove_ids = {str(stove.get_id()) for stove in coordinator.get_stoves()}
    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)

    for device in devices:
        rika_identifiers = {
            ident[1] for ident in device.identifiers if ident[0] == DOMAIN
        }
        # Si aucun identifiant du device ne correspond à un poêle actif, c'est un orphelin
        if rika_identifiers and rika_identifiers.isdisjoint(active_stove_ids):
            _LOGGER.info(
                "Cleaning up orphan device %s (identifiers=%s) no longer present in Rika",
                device.name,
                rika_identifiers,
            )
            # Supprimer d'abord les entités rattachées
            entities = er.async_entries_for_device(entity_reg, device.id)
            for entity in entities:
                _LOGGER.info("Removing orphan entity: %s", entity.entity_id)
                entity_reg.async_remove(entity.entity_id)

            # Supprimer l'appareil
            device_reg.async_remove_device(device.id)
