import logging
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory

from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_ATTRIBUTES = {
    "door": {
        "device_class": BinarySensorDeviceClass.DOOR,
        "category": EntityCategory.DIAGNOSTIC,
        "is_on_func": lambda stove: not stove.is_door_closed(),
    },
    "pellet lid": {
        "device_class": BinarySensorDeviceClass.OPENING,
        "category": EntityCategory.DIAGNOSTIC,
        "is_on_func": lambda stove: not stove.is_cover_closed(),
    },
    "grid contact": {
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "category": EntityCategory.DIAGNOSTIC,
        "is_on_func": lambda stove: not stove.is_grid_contact_ok(),
    },
    "external request": {
        "device_class": BinarySensorDeviceClass.RUNNING,
        "category": EntityCategory.DIAGNOSTIC,
        "is_on_func": lambda stove: stove.is_external_request(),
    },
}

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up platform binary_sensor")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for stove in coordinator.get_stoves():
        for sensor_name in BINARY_SENSOR_ATTRIBUTES:
            entities.append(
                RikaFirenetStoveBinarySensor(entry, stove, coordinator, sensor_name)
            )

    if entities:
        async_add_entities(entities, True)

class RikaFirenetStoveBinarySensor(RikaFirenetEntity, BinarySensorEntity):
    """Representation of a Rika Firenet binary sensor."""

    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, sensor_name: str):
        super().__init__(config_entry, stove, coordinator, sensor_name)
        self._sensor_name = sensor_name

        attrs = BINARY_SENSOR_ATTRIBUTES.get(sensor_name, {})
        self._attr_device_class = attrs.get("device_class")
        self._attr_entity_category = attrs.get("category")
        self._is_on_func = attrs.get("is_on_func")

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        if self._is_on_func:
            return self._is_on_func(self._stove)
        return False

    @property
    def translation_key(self):
        return self._sensor_name
