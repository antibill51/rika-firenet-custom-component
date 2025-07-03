import logging
from homeassistant.const import UnitOfTemperature, UnitOfTime, UnitOfMass, PERCENTAGE, REVOLUTIONS_PER_MINUTE
from homeassistant.helpers.entity import EntityCategory
from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

SENSOR_ATTRIBUTES = {
    "stove consumption": {"unit": UnitOfMass.KILOGRAMS, "icon": "mdi:weight-kilogram", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_consumption"},
    "stove runtime": {"unit": UnitOfTime.HOURS, "icon": "mdi:timer-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_runtime_pellets"},
    "stove runtime logs": {"unit": UnitOfTime.HOURS, "icon": "mdi:timer-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_runtime_logs"},
    "stove temperature": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer", "category": EntityCategory.DIAGNOSTIC,"command": "get_stove_temperature"},
    "room temperature": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer","command": "get_room_temperature"},
    "stove thermostat": {"unit": UnitOfTemperature.CELSIUS, "icon": "mdi:thermometer","command": "get_room_thermostat"},
    "stove burning": {"icon": "mdi:fire", "category": EntityCategory.DIAGNOSTIC,"command": "is_stove_burning"},
    "stove status": {"icon": "mdi:information-outline","command": "get_status_text"},
    "pellets before service": {"unit": UnitOfMass.KILOGRAMS, "icon": "mdi:weight-kilogram", "category": EntityCategory.DIAGNOSTIC,"command": "get_pellets_before_service"},
    "fan velocity": {"unit": "l/min","icon": "mdi:speedometer", "category": EntityCategory.DIAGNOSTIC,"command": "get_fan_velocity"},
    "diag motor": {"unit": "‰","icon": "mdi:speedometer", "category": EntityCategory.DIAGNOSTIC,"command": "get_diag_motor"},
    "airflaps": {"unit": PERCENTAGE,"icon": "mdi:rotate-right", "category": EntityCategory.DIAGNOSTIC,"command": "get_outputAirFlaps"},
    "number fail": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_number_fail"},
    "main state": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_main_state"},
    "sub state": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_sub_state"},
    "statusError": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_status_error"},
    "statusWarning": {"icon": "mdi:alert-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_status_warning"},
    "statusSubError": {"icon": "mdi:information-outline", "category": EntityCategory.DIAGNOSTIC,"command": "get_status_sub_error"},
}


async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up platform sensor")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    for stove in coordinator.get_stoves():
        DEVICE_SENSORS = [
            "stove consumption",
            "stove runtime",
            "stove temperature",
            "room temperature",
            "stove thermostat",
            "stove burning",
            "stove status",
            "pellets before service",
            "fan velocity",
            "diag motor",
            "number fail",
            "main state",
            "sub state",
            "statusError",
            "statusSubError",
            "statusWarning"
        ]

        if stove.is_logRuntimePossible():
            DEVICE_SENSORS.append("stove runtime logs")
        if stove.is_airFlapsPossible():
            DEVICE_SENSORS.append("airflaps")

        stove_entities.extend(
            [
                RikaFirenetStoveSensor(entry, stove, coordinator, sensor)
                for sensor in DEVICE_SENSORS
            ]
        )

    if stove_entities:
        async_add_entities(stove_entities, True)

class RikaFirenetStoveSensor(RikaFirenetEntity):
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, sensor):
        super().__init__(config_entry, stove, coordinator, sensor)
        self._sensor = sensor

    @property
    def state(self):
        # Special case for a coordinator-level sensor attached to a stove device
        if self._sensor == "number fail":
            return self.coordinator.get_number_fail()

        # For all other sensors, get the value from the stove object
        command = SENSOR_ATTRIBUTES.get(self._sensor, {}).get("command")
        if command:
            return getattr(self._stove, command)()
        return None

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
