"""Button platform for Rika Firenet: schedule copy, send, and discard."""

from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SCHEDULE_ENTITY, DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove
from .entity import RikaFirenetEntity

_LOGGER = logging.getLogger(__name__)

BUTTON_TYPES = {
    "schedule_copy": {
        "icon": "mdi:calendar-arrow-right",
        "default_enabled": True,
    },
    "schedule_send": {
        "icon": "mdi:calendar-check",
        "default_enabled": False,
    },
    "schedule_discard": {
        "icon": "mdi:calendar-remove",
        "default_enabled": False,
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Rika Firenet schedule buttons."""
    _LOGGER.info("Setting up Rika Firenet button platform")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    buttons = []
    for stove in coordinator.get_stoves():
        for key in BUTTON_TYPES:
            buttons.append(RikaFirenetScheduleButton(entry, stove, coordinator, key))

    if buttons:
        async_add_entities(buttons, True)


class RikaFirenetScheduleButton(RikaFirenetEntity, ButtonEntity):
    """Button entity to interact with the stove schedule."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        config_entry: ConfigEntry,
        stove: RikaFirenetStove,
        coordinator: RikaFirenetCoordinator,
        button_key: str,
    ) -> None:
        super().__init__(config_entry, stove, coordinator, button_key)
        self._button_key = button_key
        config = BUTTON_TYPES.get(button_key, {})
        self._attr_icon = config.get("icon")
        self._attr_entity_registry_enabled_default = config.get("default_enabled", False)
        self._attr_translation_key = button_key

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._button_key == "schedule_copy":
            schedule_entity = self._config_entry.options.get(CONF_SCHEDULE_ENTITY)
            await self.coordinator.schedule_copy_from(schedule_entity, self._stove_id)
        elif self._button_key == "schedule_send":
            await self.coordinator.schedule_send(self._stove_id)
        elif self._button_key == "schedule_discard":
            self.coordinator.schedule_discard()
            await self.coordinator.async_request_refresh()
