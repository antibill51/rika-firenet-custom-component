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

    @property
    def entity_picture(self):
        return self._stove.get_status_picture()

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
        return PRESET_COMFORT if self._get_operation_mode() == 2 else PRESET_NONE

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
        return self._get_heating_state()

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS




    def set_temperature(self, **kwargs):
        temperature = int(kwargs.get(ATTR_TEMPERATURE))
        _LOGGER.debug(f'set_temperature(): {temperature}')
        if kwargs.get(ATTR_TEMPERATURE) is None:
            return
        if not self._stove.is_stove_on():
            return
        # do nothing if HVAC is switched off
        self._stove.set_stove_temperature(temperature)
        self.schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode):
        _LOGGER.debug(f'set_hvac_mode(): {hvac_mode}')
        self._stove.set_hvac_mode(str(hvac_mode))
        self.schedule_update_ha_state()

    def set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        _LOGGER.debug('preset mode : ' + str(preset_mode))
        if preset_mode == PRESET_COMFORT:
            _LOGGER.debug("setting up PRESET COMFORT")
            self._stove.set_stove_operation_mode(2)
        else:
            _LOGGER.debug("setting up PRESET NONE")
            if self._stove.is_stove_heating_times_on():
                self._stove.set_stove_operation_mode(1)
            else:
                self._stove.set_stove_operation_mode(0)
        self.schedule_update_ha_state()

    def _get_stove_status(self):
        """Helper method to get stove status text."""
        return self._stove.get_status_text()

    def _get_operation_mode(self):
        """Helper method to get stove operation mode."""
        return self._stove.get_stove_operation_mode()

    def _get_heating_state(self):
        """Helper method to check if stove is heating."""
        status = self._get_stove_status()
        if status == "stove_off" or status == "offline":
            return HVACAction.OFF
        elif status == "standby":
            return HVACAction.IDLE
        return HVACAction.HEATING
