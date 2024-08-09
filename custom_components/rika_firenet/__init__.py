import asyncio
import logging

import requests.exceptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .const import (CONF_DEFAULT_TEMPERATURE, CONF_DEFAULT_SCAN_INTERVAL, CONF_PASSWORD,
                    CONF_USERNAME, DOMAIN, PLATFORMS, STARTUP_MESSAGE)
from .core import RikaFirenetCoordinator

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)

async def async_setup(hass: HomeAssistant, config: dict):
    _LOGGER.info('setup_platform()')
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.info('async_setup_entry():' + str(entry.entry_id))

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    default_temperature = int(entry.options.get(CONF_DEFAULT_TEMPERATURE, 21))
    default_scan_interval = int(entry.options.get(CONF_DEFAULT_SCAN_INTERVAL, 15))

    coordinator = RikaFirenetCoordinator(hass, username, password, default_temperature, default_scan_interval)

    try:
        await hass.async_add_executor_job(coordinator.setup)
    except KeyError:
        _LOGGER.error("Failed to login to firenet")
        return False
    except RuntimeError as exc:
        _LOGGER.error("Failed to setup rika firenet: %s", exc)
        return ConfigEntryNotReady
    except requests.exceptions.Timeout as ex:
        raise ConfigEntryNotReady from ex
    except requests.exceptions.HTTPError as ex:
        if ex.response.status_code > 400 and ex.response.status_code < 500:
            _LOGGER.error("Failed to login to rika firenet: %s", ex)
            return False
        raise ConfigEntryNotReady from ex
    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await async_reload(hass, entry)
