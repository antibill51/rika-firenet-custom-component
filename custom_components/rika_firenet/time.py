"""Time platform for Rika Firenet: schedule slot start and end times."""

from __future__ import annotations

from datetime import time
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove
from .entity import RikaFirenetEntity
from .schedule import DAYS, EDGES, SLOTS_PER_DAY, slot_index

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Rika Firenet schedule time entities."""
    _LOGGER.info("Setting up Rika Firenet time platform")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    time_entities = []
    for stove in coordinator.get_stoves():
        for day in range(len(DAYS)):
            for slot in range(SLOTS_PER_DAY):
                for edge in EDGES:
                    time_entities.append(
                        RikaFirenetScheduleTime(
                            entry, stove, coordinator, day, slot, edge
                        )
                    )

    if time_entities:
        async_add_entities(time_entities, True)


class RikaFirenetScheduleTime(RikaFirenetEntity, TimeEntity):
    """Entity representing one time boundary of the heating schedule."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        config_entry: ConfigEntry,
        stove: RikaFirenetStove,
        coordinator: RikaFirenetCoordinator,
        day: int,
        slot: int,
        edge: str,
    ) -> None:
        key = f"schedule_{DAYS[day]}_{slot + 1}_{edge}"
        super().__init__(config_entry, stove, coordinator, key)
        self._day = day
        self._slot = slot
        self._edge = edge
        self._index = slot_index(day, slot)
        self._attr_translation_key = key

    @property
    def native_value(self) -> time | None:
        """Return the current time for this slot boundary."""
        return self.coordinator.schedule_time(self._index, self._edge, self._stove_id)

    async def async_set_value(self, value: time) -> None:
        """Set a new time for this slot boundary (staged until sent)."""
        self.coordinator.schedule_set_pending(self._index, self._edge, value)
