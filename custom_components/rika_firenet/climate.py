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
        return self._stove.get_hvac_action()

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
