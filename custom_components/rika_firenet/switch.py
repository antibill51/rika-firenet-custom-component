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
        stove_switches = ["on off", "heating times", "frost protection"]

        if stove.is_airFlapsPossible(): # Corrected: call on the stove instance
            stove_switches.append("eco mode")
        if stove.is_multiAir1(): # Corrected: call on the stove instance
            stove_switches.append("convection fan1")
        if stove.is_multiAir2(): # Corrected: call on the stove instance
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
        elif self._switch_type.startswith("frost protection"):
            return "hass:snowflake-check"
        return "hass:power"

    @property
    def is_on(self):
        if self._switch_type == "on off":
            return self._stove.is_stove_on()
        # The is_stove_* methods of self._stove read the current state
        elif self._switch_type == "convection fan1":
            return self._stove.is_stove_convection_fan1_on()
        elif self._switch_type == "convection fan2":
            return self._stove.is_stove_convection_fan2_on()
        elif self._switch_type == "heating times":
            return self._stove.is_stove_heating_times_on() # Utilise la logique interne de RikaFirenetStove
        elif self._switch_type == "eco mode":
            return self._stove.is_stove_eco_mode()
        elif self._switch_type == "frost protection":
            return self._stove.is_frost_protection()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.info("Turning on switch '%s' for stove '%s'", self._switch_type, self._stove.get_name())
        # Corrected logic here
        if self._switch_type == "on off":
            self._stove.set_stove_on_off(True)
        elif self._switch_type == "convection fan1":
            self._stove.turn_convection_fan1_on_off(True)
        elif self._switch_type == "convection fan2":
            self._stove.turn_convection_fan2_on_off(True)
        elif self._switch_type == "heating times":
            self._stove.turn_heating_times_on()
        elif self._switch_type == "eco mode":
            self._stove.turn_on_off_eco_mode(True)
        elif self._switch_type == "frost protection":
            self._stove.turn_on_off_frost_protection(True)
        else:
            _LOGGER.warning(f"Unknown switch type '{self._switch_type}' for turn_on action.")
            return

        # The methods above on self._stove mark _controls_changed = True
        # Ask the coordinator to send the command and refresh
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        _LOGGER.info("Turning off switch '%s' for stove '%s'", self._switch_type, self._stove.get_name())
        if self._switch_type == "on off":
            self._stove.set_stove_on_off(False)
        elif self._switch_type == "convection fan1":
            self._stove.turn_convection_fan1_on_off(False)
        elif self._switch_type == "convection fan2":
            self._stove.turn_convection_fan2_on_off(False)
        elif self._switch_type == "heating times":
            self._stove.turn_heating_times_off()
        elif self._switch_type == "eco mode":
            self._stove.turn_on_off_eco_mode(False)
        elif self._switch_type == "frost protection":
            self._stove.turn_on_off_frost_protection(False)
        else:
            _LOGGER.warning(f"Unknown switch type '{self._switch_type}' for turn_off action.")
            return
        # The methods above on self._stove mark _controls_changed = True
        # Ask the coordinator to send the command and refresh
        await self.coordinator.async_request_refresh()
