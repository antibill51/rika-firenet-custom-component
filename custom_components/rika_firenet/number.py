import logging

from homeassistant.const import PERCENTAGE, UnitOfTemperature
from .entity import RikaFirenetEntity
from homeassistant.components.number import NumberEntity

from .const import DOMAIN
from .core import RikaFirenetCoordinator
from .core import RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

# Configuration for number entities to reduce if/elif chains
NUMBER_CONFIG = {
    "room power request":           {"min": 1,  "max": 4,   "step": 1, "unit": None,                     "icon": "mdi:speedometer",    "command_get": "get_room_power_request",           "command_set": "set_room_power_request", "int_value": True},
    "heating power":                {"min": 30, "max": 100, "step": 5, "unit": PERCENTAGE,               "icon": "mdi:speedometer",    "command_get": "get_heating_power",                "command_set": "set_heating_power", "int_value": True},
    "convection fan1 level":        {"min": 0,  "max": 5,   "step": 1, "unit": None,                     "icon": "mdi:fan",            "command_get": "get_convection_fan1_level",        "command_set": "set_convection_fan1_level", "int_value": True},
    "convection fan1 area":         {"min": -30,"max": 30,  "step": 1, "unit": PERCENTAGE,               "icon": "mdi:arrow-split-horizontal", "command_get": "get_convection_fan1_area",         "command_set": "set_convection_fan1_area", "int_value": True},
    "convection fan2 level":        {"min": 0,  "max": 5,   "step": 1, "unit": None,                     "icon": "mdi:fan",            "command_get": "get_convection_fan2_level",        "command_set": "set_convection_fan2_level", "int_value": True},
    "convection fan2 area":         {"min": -30,"max": 30,  "step": 1, "unit": PERCENTAGE,               "icon": "mdi:arrow-split-horizontal", "command_get": "get_convection_fan2_area",         "command_set": "set_convection_fan2_area", "int_value": True},
    "set back temperature":         {"min": 12, "max": 20,  "step": 1, "unit": UnitOfTemperature.CELSIUS,"icon": "mdi:thermometer-minus","command_get": "get_stove_set_back_temperature",   "command_set": "set_stove_set_back_temperature", "int_value": False}, # API might expect float
    "set frost protection temperature": {"min": 4, "max": 10, "step": 1, "unit": UnitOfTemperature.CELSIUS,"icon": "mdi:snowflake-thermometer", "command_get": "get_frost_protection_temperature", "command_set": "set_frost_protection_temperature", "int_value": True},
    "temperature offset":           {"min": -4, "max": 4,   "step": 0.1,"unit": UnitOfTemperature.CELSIUS,"icon": "mdi:thermometer-plus", "command_get": "get_temperatureOffset",            "command_set": "set_temperatureOffset", "int_value": False},
}

# Default values if a number type is not in NUMBER_CONFIG
DEFAULT_NUMBER_MIN = 0
DEFAULT_NUMBER_MAX = 100
DEFAULT_NUMBER_STEP = 1


def get_number_device_list(stove: RikaFirenetStove) -> list[str]:
    """Return the list of number entities for a given stove."""
    device_numbers = [
        "room power request",
        "heating power",
        "temperature offset",
        "set back temperature",
        "set frost protection temperature"
    ]
    if stove.is_multiAir1():
        device_numbers.extend(["convection fan1 level", "convection fan1 area"])
    if stove.is_multiAir2():
        device_numbers.extend(["convection fan2 level", "convection fan2 area"])
    return device_numbers

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("setting up platform number")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []
    # Create 'number' entities for each stove
    for stove in coordinator.get_stoves():
        device_numbers_for_stove = get_number_device_list(stove)
        stove_entities.extend(
            [
                RikaFirenetStoveNumber(entry, stove, coordinator, number)
                for number in device_numbers_for_stove
            ]
        )

    if stove_entities:
        async_add_entities(stove_entities, True)


class RikaFirenetStoveNumber(RikaFirenetEntity, NumberEntity):
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, number):
        super().__init__(config_entry, stove, coordinator, number)
        self._number = number
        self._config = NUMBER_CONFIG.get(self._number, {})

    @property
    def native_min_value(self) -> float:
        return self._config.get("min", DEFAULT_NUMBER_MIN)

    @property
    def native_max_value(self) -> float:
        return self._config.get("max", DEFAULT_NUMBER_MAX)

    @property
    def native_step(self) -> float:
        return self._config.get("step", DEFAULT_NUMBER_STEP)

    @property
    def native_value(self):
        command = self._config.get("command_get")
        if command:
            return getattr(self._stove, command)()
        _LOGGER.warning(f"No get command configured for number entity: {self._number}")
        return None

    @property
    def native_unit_of_measurement(self):
        return self._config.get("unit")

    @property
    def icon(self):
        return self._config.get("icon", "mdi:numeric") # Default icon if not specified

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        _LOGGER.info(f"Setting native value for {self.name} ({self._number}) to: {value}")
        command_set = self._config.get("command_set")
        if command_set:
            # Determine if the value should be an int or float based on config
            is_int_value = self._config.get("int_value", False) # Default to float if not specified
            processed_value = int(value) if is_int_value else float(value)
            getattr(self._stove, command_set)(processed_value)
        else:
            _LOGGER.warning(f"No set command configured for number entity: {self._number}")
            return
        
        # The methods above on self._stove mark _controls_changed = True
        # Ask the coordinator to send the command and refresh
        await self.coordinator.async_request_refresh()
