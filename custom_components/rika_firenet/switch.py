import logging
from homeassistant.components.switch import SwitchEntity
from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up platform switches")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    for stove in coordinator.get_stoves():
        stove_switches = ["on off", "heating times"]

        if RikaFirenetStove.is_airFlapsPossible(stove):
            stove_switches.append("eco mode")
        if RikaFirenetStove.is_multiAir1(stove):
            stove_switches.append("convection fan1")
        if RikaFirenetStove.is_multiAir2(stove):
            stove_switches.append("convection fan2")

        stove_entities.extend(
            [
                RikaFirenetStoveBinarySwitch(entry, stove, coordinator, switch_type)
                for switch_type in stove_switches
            ]
        )

    if stove_entities:
        async_add_entities(stove_entities, True)


class RikaFirenetStoveBinarySwitch(RikaFirenetEntity, SwitchEntity):
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, switch_type):
        super().__init__(config_entry, stove, coordinator, switch_type)
        self._switch_type = switch_type

    @property
    def unique_id(self):
        return f"{self._stove._id}_{self._switch_type}".lower()
    
    @property
    def translation_key(self):
        return self._switch_type

    @property
    def icon(self):
        if self._switch_type == "eco mode":
            return "hass:leaf"
        elif self._switch_type.startswith("convection fan"):
            return "hass:fan"
        return "hass:power"

    @property
    def is_on(self):
        if self._switch_type == "on off":
            return self._stove.is_stove_on()
        elif self._switch_type == "convection fan1":
            return self._stove.is_stove_convection_fan1_on()
        elif self._switch_type == "convection fan2":
            return self._stove.is_stove_convection_fan2_on()
        elif self._switch_type == "heating times":
            return self._stove.is_stove_heating_times_on()
        elif self._switch_type == "eco mode":
            return self._stove.is_stove_eco_mode()

    def turn_on(self, **kwargs):
        _LOGGER.info("Turning on switch '%s' for stove '%s'", self._switch_type, self._stove._name)
        try:
            if self._switch_type == "on off":
                self._stove.turn_on()
            elif self._switch_type == "convection fan1":
                self._stove.turn_convection_fan1_on()
            elif self._switch_type == "convection fan2":
                self._stove.turn_convection_fan2_on()
            elif self._switch_type == "heating times":
                self._stove.turn_heating_times_on()
            elif self._switch_type == "eco mode":
                self._stove.turn_on_eco_mode()
            self.schedule_update_ha_state()
        except Exception as ex:
            _LOGGER.error("Failed to turn on '%s': %s", self._switch_type, ex)

    def turn_off(self, **kwargs):
        _LOGGER.info("Turning off switch '%s' for stove '%s'", self._switch_type, self._stove._name)
        try:
            if self._switch_type == "on off":
                self._stove.turn_off()
            elif self._switch_type == "convection fan1":
                self._stove.turn_convection_fan1_off()
            elif self._switch_type == "convection fan2":
                self._stove.turn_convection_fan2_off()
            elif self._switch_type == "heating times":
                self._stove.turn_heating_times_off()
            elif self._switch_type == "eco mode":
                self._stove.turn_off_eco_mode()
            self.schedule_update_ha_state()
        except Exception as ex:
            _LOGGER.error("Failed to turn off '%s': %s", self._switch_type, ex)
