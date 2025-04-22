import logging

from homeassistant.const import PERCENTAGE, UnitOfTemperature
from .entity import RikaFirenetEntity
from homeassistant.components.number import NumberEntity

from .const import DOMAIN
from .core import RikaFirenetCoordinator
from .core import RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("setting up platform number")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    # Crée les entités 'number' pour chaque poêle
    for stove in coordinator.get_stoves():
        DEVICE_NUMBERS = [
            "room power request",
            "heating power",
            "temperature offset",
            "set back temperature",
            "set frost protection temperature",
            "pellet stock capacity"
        ]
        # Ajout de paramètres pour les poêles multi-air
        if RikaFirenetStove.is_multiAir1(stove):
            DEVICE_NUMBERS.append("convection fan1 level")
            DEVICE_NUMBERS.append("convection fan1 area")
        if RikaFirenetStove.is_multiAir2(stove):
            DEVICE_NUMBERS.append("convection fan2 level")
            DEVICE_NUMBERS.append("convection fan2 area")

        # Crée les entités 'number' pour chaque appareil
        stove_entities.extend(
            [
                RikaFirenetStoveNumber(entry, stove, coordinator, number)
                for number in DEVICE_NUMBERS
            ]
        )

    if stove_entities:
        async_add_entities(stove_entities, True)


class RikaFirenetStoveNumber(RikaFirenetEntity, NumberEntity):
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, number):
        super().__init__(config_entry, stove, coordinator, number)
        self._number = number

    @property
    def unique_id(self):
        return f"{self._stove._id}_{self._number}".lower()

    @property
    def native_min_value(self) -> float:
        if self._number == "room power request":
            return 1
        elif self._number == "heating power":
            return 30
        elif self._number == "convection fan1 level":
            return 0
        elif self._number == "convection fan1 area":
            return -30
        elif self._number == "convection fan2 level":
            return 0
        elif self._number == "convection fan2 area":
            return -30
        elif self._number == "set back temperature":
            return 12
        elif self._number == "set frost protection temperature":
            return 4
        elif self._number == "temperature offset":
            return -4
        elif self._number == "pellet stock capacity":
            return 1
        return 0

    @property
    def native_max_value(self) -> float:
        if self._number == "room power request":
            return 4
        elif self._number == "heating power":
            return 100
        elif self._number == "convection fan1 level":
            return 5
        elif self._number == "convection fan1 area":
            return 30
        elif self._number == "convection fan2 level":
            return 5
        elif self._number == "convection fan2 area":
            return 30
        elif self._number == "set back temperature":
            return 20
        elif self._number == "set frost protection temperature":
            return 10
        elif self._number == "temperature offset":
            return 4
        elif self._number == "pellet stock capacity":
            return 50
        return 100

    @property
    def native_step(self) -> float:
        if self._number == "room power request":
            return 1
        elif self._number == "heating power":
            return 5
        elif self._number == "convection fan1 level":
            return 1
        elif self._number == "convection fan1 area":
            return 1
        elif self._number == "convection fan2 level":
            return 1
        elif self._number == "convection fan2 area":
            return 1
        elif self._number == "set back temperature":
            return 1
        elif self._number == "set frost protection temperature":
            return 1
        elif self._number == "temperature offset":
            return 0.1
        elif self._number == "pellet stock capacity":
            return 0.5
        return 10

    @property
    def native_value(self):
        if self._number == "room power request":
            return self._stove.get_room_power_request()
        elif self._number == "heating power":
            return self._stove.get_heating_power()
        elif self._number == "convection fan1 level":
            return self._stove.get_convection_fan1_level()
        elif self._number == "convection fan1 area":
            return self._stove.get_convection_fan1_area()
        elif self._number == "convection fan2 level":
            return self._stove.get_convection_fan2_level()
        elif self._number == "convection fan2 area":
            return self._stove.get_convection_fan2_area()
        elif self._number == "set back temperature":
            return self._stove.get_stove_set_back_temperature()
        elif self._number == "set frost protection temperature":
            return self._stove.get_frost_protection_temperature()
        elif self._number == "temperature offset":
            return self._stove.get_temperatureOffset()
        elif self._number == "pellet stock capacity":
            return self._stove.get_pellet_stock_capacity()

    @property
    def native_unit_of_measurement(self):
        if self._number == "heating power":
            return PERCENTAGE
        elif self._number == "convection fan1 area":
            return PERCENTAGE
        elif self._number == "convection fan2 area":
            return PERCENTAGE
        elif self._number == "set back temperature":
            return UnitOfTemperature.CELSIUS
        elif self._number == "set frost protection temperature":
            return UnitOfTemperature.CELSIUS
        elif self._number == "temperature offset":
            return UnitOfTemperature.CELSIUS
        elif self._number == "pellet stock capacity":
            return "kg"

    @property
    def icon(self):
        if "temperature" in self._number:
            return "mdi:thermometer"
        elif self._number == "pellet stock capacity":
            return "mdi:weight-kilogram"
        return "mdi:speedometer"

    def set_native_value(self, value: float) -> None:
        _LOGGER.info(f"set_value {self._number} {value}")
        if self._number == "room power request":
            self._stove.set_room_power_request(int(value))
        elif self._number == "heating power":
            self._stove.set_heating_power(int(value))
        elif self._number == "convection fan1 level":
            return self._stove.set_convection_fan1_level(int(value))
        elif self._number == "convection fan1 area":
            return self._stove.set_convection_fan1_area(int(value))
        elif self._number == "convection fan2 level":
            return self._stove.set_convection_fan2_level(int(value))
        elif self._number == "convection fan2 area":
            return self._stove.set_convection_fan2_area(int(value))
        elif self._number == "set back temperature":
            return self._stove.set_stove_set_back_temperature(value)
        elif self._number == "set frost protection temperature":
            return self._stove.set_frost_protection_temperature(int(value))
        elif self._number == "temperature offset":
            return self._stove.set_temperatureOffset(value)
        elif self._number == "pellet stock capacity":
            return self._stove.set_pellet_stock_capacity(value)
        self.schedule_update_ha_state()
