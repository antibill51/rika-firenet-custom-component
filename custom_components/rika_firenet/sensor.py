import logging
from homeassistant.const import UnitOfTemperature, UnitOfTime, UnitOfMass, PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

DEVICE_SENSORS = [
    "stove_consumption",
    "stove_runtime",
    "stove_temperature",
    "room_temperature",
    "stove_thermostat",
    "stove_burning",
    "stove_status",
    "pellets_before_service",
    "fan_velocity",
    "diag_motor",
    "number_fail",
    "main_state",
    "sub_state",
    "statusError",
    "statusSubError"
]

SENSOR_ATTRIBUTES = {
    "stove_consumption": {"unit": UnitOfMass.KILOGRAMS, "icon": "mdi:weight-kilogram", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_consumption"},
    "stove_runtime": {"unit": UnitOfTime.HOURS, "icon": "mdi:timer-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_runtime"},
    "stove_temperature": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_temperature"},
    "room_temperature": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer","command": "get_room_temperature"},
    "stove_thermostat": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer","command": "get_room_thermostat"},
    "stove_burning": {"icon": "mdi:fire", "category": EntityCategory.DIAGNOSTIC,"command": "is_stove_burning"},
    "stove_status": {"icon": "mdi:information-outline","command": "get_status_text"},
    "pellets_before_service": {"unit": UnitOfMass.KILOGRAMS, "icon": "mdi:weight-kilogram", "category": EntityCategory.DIAGNOSTIC,"command": "get_pellets_before_service"},
    "fan_velocity": {"icon": "mdi:speedometer", "category": EntityCategory.DIAGNOSTIC,"command": "get_fan_velocity"},
    "diag_motor": {"icon": "mdi:speedometer", "category": EntityCategory.DIAGNOSTIC,"command": "get_diag_motor"},
    "number_fail": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_number_fail"},
    "main_state": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_main_state"},
    "sub_state": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_sub_state"},
    "statusError": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_status_error"},
    "statusSubError": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_status_sub_error"},
}


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up platform sensor")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = [
        RikaFirenetStoveSensor(entry, stove, coordinator, sensor)
        for stove in coordinator.get_stoves()
        for sensor in DEVICE_SENSORS
    ]

    if stove_entities:
        async_add_entities(stove_entities, True)


class RikaFirenetStoveSensor(RikaFirenetEntity):
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, sensor):
        super().__init__(config_entry, stove, coordinator, sensor)
        self._sensor = sensor

    @property
    def state(self):
        return getattr(self._stove, f"{SENSOR_ATTRIBUTES.get(self._sensor, {}).get("command")}")()

    @property
    def unit_of_measurement(self):
        return SENSOR_ATTRIBUTES.get(self._sensor, {}).get("unit")

    @property
    def icon(self):
        return SENSOR_ATTRIBUTES.get(self._sensor, {}).get("icon")

    @property
    def entity_category(self):
        return SENSOR_ATTRIBUTES.get(self._sensor, {}).get("category")

    @property
    def translation_key(self):
        return self._sensor
