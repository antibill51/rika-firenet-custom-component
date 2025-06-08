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
        if self._stove_data and 'sensors' in self._stove_data and 'inputRoomTemperature' in self._stove_data['sensors']:
            try:
                return float(self._stove_data['sensors']['inputRoomTemperature'])
            except (ValueError, TypeError): return None
        return None

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
        # Use _stove_data to read the current state
        op_mode = self._stove_data.get('controls', {}).get('operatingMode') if self._stove_data else None
        return PRESET_COMFORT if op_mode == 2 else PRESET_NONE

    @property
    def target_temperature(self):
        if self._stove_data and 'controls' in self._stove_data and 'targetTemperature' in self._stove_data['controls']:
            try:
                return float(self._stove_data['controls']['targetTemperature'])
            except (ValueError, TypeError): return None
        return None

    @property
    def target_temperature_step(self):
        return 1

    @property
    def hvac_modes(self) -> HVACMode:
        return HVAC_MODES

    @property
    def hvac_mode(self):
        if not self._stove_data or not self._stove_data.get('controls', {}).get('onOff'):
            return HVACMode.OFF
        
        op_mode = self._stove_data.get('controls', {}).get('operatingMode')
        heating_times_active = self._stove_data.get('controls', {}).get('heatingTimesActiveForComfort')

        if op_mode == 1 or (op_mode == 2 and heating_times_active): # AUTO mode (scheduled)
            return HVACMode.AUTO
        return HVACMode.HEAT # Manual mode (or if op_mode == 0)

    @property
    def hvac_action(self) -> HVACAction:
        """Return current operation ie. heat, cool, idle."""
        # This logic should use self._stove_data
        return self._get_heating_state_from_data()

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
        _LOGGER.debug(f'Setting preset_mode for {self.name} to: {preset_mode}')
        if preset_mode == PRESET_COMFORT:
            _LOGGER.debug("Setting PRESET_COMFORT (operatingMode 2)") # Comfort mode
            self._stove.set_stove_operation_mode(2)
        else: # PRESET_NONE
            _LOGGER.debug("Setting PRESET_NONE (operatingMode based on heating times)") # No preset
            # If heating times are active, switch to mode 1 (Auto), otherwise mode 0 (Manual)
            # This logic is already in RikaFirenetStove's turn_heating_times_on/off
            # For PRESET_NONE, we might want a simple manual mode (mode 0)
            # or let the user manage via the "heating times" switch.
            # For now, assume PRESET_NONE means "manual mode without active heating times".
            # If heating times are active, deactivate them.
            if self._stove.is_stove_heating_times_on(): # Checks the current state of the stove object
                 self._stove.turn_heating_times_off() # This will set operatingMode to 0 if not already in comfort
            else: # If not already in scheduled mode, ensure it's in manual mode (0)
                 self._stove.set_stove_operation_mode(0)
        await self.coordinator.async_request_refresh()

    def _get_heating_state_from_data(self) -> HVACAction:
        """Helper method to get stove heating action from coordinator data."""
        if not self._stove_data:
            return HVACAction.OFF # Return OFF if data is not available
        status = self._stove.get_status_text() # get_status_text uses the internal state of the stove object, which is updated by the coordinator
        if status == "stove_off" or status == "offline":
            return HVACAction.OFF
        elif status == "standby":
            return HVACAction.IDLE
        return HVACAction.HEATING
