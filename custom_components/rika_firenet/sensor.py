import logging
from homeassistant.const import UnitOfTemperature, UnitOfTime, UnitOfMass, PERCENTAGE, REVOLUTIONS_PER_MINUTE
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass

from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

SENSOR_ATTRIBUTES = {
    "stove consumption": {
        "unit": UnitOfMass.KILOGRAMS,
        "icon": "mdi:weight-kilogram",
        "category": EntityCategory.DIAGNOSTIC,
        "command": "get_stove_consumption",
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.WEIGHT
    },
    "stove runtime": {
        "unit": UnitOfTime.HOURS,
        "icon": "mdi:timer-outline",
        "category": EntityCategory.DIAGNOSTIC,
        "command": "get_stove_runtime_pellets",
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.DURATION
    },
    "stove runtime logs": {
        "unit": UnitOfTime.HOURS,
        "icon": "mdi:timer-outline",
        "category": EntityCategory.DIAGNOSTIC,
        "command": "get_stove_runtime_logs",
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "device_class": SensorDeviceClass.DURATION
    },
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

BASE_DEVICE_SENSORS = [
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

def get_sensor_device_list(stove: RikaFirenetStove) -> list[str]:
    """Return the list of sensor entities for a given stove."""
    # Start with a copy of the base sensors for each stove
    sensors_for_stove = list(BASE_DEVICE_SENSORS)

    if stove.is_logRuntimePossible():
        sensors_for_stove.append("stove runtime logs")
    if stove.is_airFlapsPossible():
        sensors_for_stove.append("airflaps")
    
    return sensors_for_stove

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up platform sensor")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    for stove in coordinator.get_stoves():
        sensors_for_stove = get_sensor_device_list(stove)
        stove_entities.extend(
            [
                RikaFirenetStoveSensor(entry, stove, coordinator, sensor)
                for sensor in sensors_for_stove
            ]
        )

    if stove_entities:
        async_add_entities(stove_entities, True)

class RikaFirenetStoveSensor(RikaFirenetEntity, SensorEntity):
    """Représentation d'un capteur Rika Firenet."""
    
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, sensor):
        """Initialise le capteur."""
        super().__init__(config_entry, stove, coordinator, sensor)
        self._sensor = sensor
        self._attr_has_entity_name = True
        
        # Définir directement les attributs d'état
        sensor_attrs = SENSOR_ATTRIBUTES.get(sensor, {})
        self._attr_native_unit_of_measurement = sensor_attrs.get("unit")
        self._attr_icon = sensor_attrs.get("icon")
        self._attr_entity_category = sensor_attrs.get("category")
        self._attr_device_class = sensor_attrs.get("device_class")
        self._attr_state_class = sensor_attrs.get("state_class")

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        try:
            # Special case for a coordinator-level sensor
            if self._sensor == "number fail":
                return self.coordinator.get_number_fail()

            # Get the command method name from attributes
            command = SENSOR_ATTRIBUTES.get(self._sensor, {}).get("command")
            if not command:
                return None

            # Get the raw value from the stove
            value = getattr(self._stove, command)()
            if value is None:
                return None

            # Pour les capteurs cumulatifs (avec state_class TOTAL_INCREASING)
            if self._attr_state_class == SensorStateClass.TOTAL_INCREASING:
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    _LOGGER.error(f"Invalid value for total_increasing sensor {self._sensor}: {value}")
                    return None

            return value

        except Exception as e:
            _LOGGER.error(f"Error getting native value for sensor {self._sensor}: {e}")
            return None

    @property
    def translation_key(self):
        return self._sensor
