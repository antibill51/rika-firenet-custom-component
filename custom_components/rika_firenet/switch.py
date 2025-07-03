import logging
from homeassistant.components.switch import SwitchEntity
from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

SWITCH_CONFIG = {
    "on off": {
        "is_on": "is_stove_on",
        "turn_on": ("set_stove_on_off", True),
        "turn_off": ("set_stove_on_off", False),
        "icon": "hass:power",
    },
    "heating times": {
        "is_on": "is_stove_heating_times_on",
        "turn_on": ("turn_heating_times_on",),
        "turn_off": ("turn_heating_times_off",),
        "icon": "mdi:calendar-clock",
    },
    "frost protection": {
        "is_on": "is_frost_protection",
        "turn_on": ("turn_on_off_frost_protection", True),
        "turn_off": ("turn_on_off_frost_protection", False),
        "icon": "hass:snowflake-check",
    },
    "eco mode": {"is_on": "is_stove_eco_mode", "turn_on": ("turn_on_off_eco_mode", True), "turn_off": ("turn_on_off_eco_mode", False), "icon": "hass:leaf"},
    "convection fan1": {"is_on": "is_stove_convection_fan1_on", "turn_on": ("turn_convection_fan1_on_off", True), "turn_off": ("turn_convection_fan1_on_off", False), "icon": "hass:fan"},
    "convection fan2": {"is_on": "is_stove_convection_fan2_on", "turn_on": ("turn_convection_fan2_on_off", True), "turn_off": ("turn_convection_fan2_on_off", False), "icon": "hass:fan"},
}

async def async_setup_entry(hass, entry, async_add_entities):
    _LOGGER.info("Setting up platform switches")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    for stove in coordinator.get_stoves():
        stove_switches = ["on off", "heating times", "frost protection"]

        if stove.is_airFlapsPossible():
            stove_switches.append("eco mode")
        if stove.is_multiAir1():
            stove_switches.append("convection fan1")
        if stove.is_multiAir2():
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
        self._config = SWITCH_CONFIG.get(self._switch_type, {})

    @property
    def translation_key(self):
        return self._switch_type

    @property
    def icon(self):
        return self._config.get("icon")

    @property
    def is_on(self):
        command = self._config.get("is_on")
        if command:
            return getattr(self._stove, command)()
        return False

    async def _async_call_command(self, command_key: str):
        """Execute a command from the config."""
        command_info = self._config.get(command_key)
        if not command_info:
            _LOGGER.warning("No command '%s' for switch '%s'", command_key, self._switch_type)
            return

        method_name, *args = command_info
        method = getattr(self._stove, method_name)
        method(*args)

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        _LOGGER.info("Turning on switch '%s' for stove '%s'", self._switch_type, self._stove.get_name())
        await self._async_call_command("turn_on")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        _LOGGER.info("Turning off switch '%s' for stove '%s'", self._switch_type, self._stove.get_name())
        await self._async_call_command("turn_off")
