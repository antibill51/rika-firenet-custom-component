import logging

from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    ClimateEntityFeature,
    PRESET_COMFORT,
    PRESET_NONE,
    HVACAction,
)

from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .const import DOMAIN, SUPPORT_PRESET
from .core import RikaFirenetCoordinator
from .entity import RikaFirenetEntity

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON

MIN_TEMP = 14
MAX_TEMP = 28

HVAC_MODES = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up platform."""
    _LOGGER.info("setting up platform climate")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    # Create stove sensors
    for stove in coordinator.get_stoves():
        stove_entities.append(RikaFirenetStoveClimate(entry, stove, coordinator))

    if stove_entities:
        async_add_entities(stove_entities, True)


class RikaFirenetStoveClimate(RikaFirenetEntity, ClimateEntity):
    _enable_turn_on_off_backwards_compatibility = False
    def __init__(self, config_entry, stove, coordinator):
        super().__init__(config_entry, stove, coordinator)
        self._attr_translation_key = "stove_climate"  # Key used for translation

    @property
    def entity_picture(self):
        # Use self._stove_data if available, otherwise self._stove as a fallback
        # or better, directly self._stove which has its own get_status_picture logic
        return self._stove.get_status_picture() # self._stove is updated by the coordinator

    @property
    def current_temperature(self):
        return self._stove.get_room_temperature()

    @property
    def min_temp(self):
        return MIN_TEMP

    @property
    def max_temp(self):
        return MAX_TEMP

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return SUPPORT_PRESET

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return self._stove.get_preset_mode()

    @property
    def target_temperature(self):
        return self._stove.get_room_thermostat()

    @property
    def target_temperature_step(self):
        return 1

    @property
    def hvac_modes(self) -> HVACMode:
        return HVAC_MODES

    @property
    def hvac_mode(self):
        return self._stove.get_hvac_mode()

    @property
    def hvac_action(self) -> HVACAction:
        """Return current operation ie. heat, cool, idle."""
        # First, check if the stove is commanded to be off. This is the most reliable state.
        if not self._stove_data or not self._stove_data.get('controls', {}).get('onOff'):
            return HVACAction.OFF

        sensors = self._stove_data.get('sensors', {})
        main_state = sensors.get('statusMainState')
        sub_state = sensors.get('statusSubState')

        # States indicating active heating (ignition, running, split log mode)
        HEATING_STATES = [2, 3, 4, 11, 13, 14, 16, 17, 20, 21, 50]
        # States indicating the stove is on but not actively producing heat (standby, cleaning, burn-off)
        IDLE_STATES = [5, 6]

        if main_state in HEATING_STATES:
            return HVACAction.HEATING
        
        elif main_state in IDLE_STATES:
            return HVACAction.IDLE

        elif main_state == 1:  # Special handling for standby/off states
            if sub_state == 0:  # Explicitly off
                return HVACAction.OFF
            # For other sub-states (1=standby, 2=external_request, 3=standby),
            # the stove is on but waiting. IDLE is the most appropriate action.
            return HVACAction.IDLE

        # Default to OFF for any other unknown or unhandled state.
        return HVACAction.OFF # Default for unknown or off states

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    async def async_set_temperature(self, **kwargs):
        temperature = int(kwargs.get(ATTR_TEMPERATURE))
        _LOGGER.debug(f'set_temperature(): {temperature}')
        if kwargs.get(ATTR_TEMPERATURE) is None:
            return
        # Checking if the stove is on can be done here or in self._stove.set_stove_temperature
        # if not (self._stove_data and self._stove_data.get('controls', {}).get('onOff')):
        #     _LOGGER.debug(f"Stove {self._stove.get_name()} is off, not setting temperature.")
        #     return
            
        self._stove.set_stove_temperature(temperature) # Modifies the "desired" state on the stove object
        await self.coordinator.async_request_refresh() # Asks the coordinator to send the command and refresh

    async def async_set_hvac_mode(self, hvac_mode):
        _LOGGER.debug(f'set_hvac_mode() for {self.name}: {hvac_mode}')
        self._stove.set_hvac_mode(str(hvac_mode)) # Modifies the "desired" state
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        self._stove.set_preset_mode(preset_mode)
        await self.coordinator.async_request_refresh()
