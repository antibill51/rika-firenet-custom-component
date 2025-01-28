import asyncio
import logging
import requests.exceptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_DEFAULT_TEMPERATURE,
    CONF_DEFAULT_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)
from .core import RikaFirenetCoordinator

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict):
    _LOGGER.info("setup_platform()")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info("async_setup_entry(): %s", entry.entry_id)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    default_temperature = int(entry.options.get(CONF_DEFAULT_TEMPERATURE, 21))
    default_scan_interval = int(entry.options.get(CONF_DEFAULT_SCAN_INTERVAL, 15))

    coordinator = RikaFirenetCoordinator(
        hass, username, password, default_temperature, default_scan_interval
    )

    try:
        await hass.async_add_executor_job(coordinator.setup)
        await coordinator.async_refresh()

        if not coordinator.last_update_success:
            raise ConfigEntryNotReady

    except requests.exceptions.Timeout as ex:
        _LOGGER.warning("Timeout during Rika Firenet setup: %s", ex)
        raise ConfigEntryNotReady from ex

    except Exception as ex:
        _LOGGER.exception("Unexpected error during Rika Firenet setup: %s", ex)
        return ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward entry setups for all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register platforms dynamically
    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            try:
                coordinator.platforms.append(platform)
                _LOGGER.info("Platform '%s' initialized.", platform)
            except Exception as ex:
                _LOGGER.error("Failed to initialize platform '%s': %s", platform, ex)

    entry.add_update_listener(_async_options_updated)
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
    await async_reload_entry(hass, entry)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)