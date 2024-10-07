import logging

from homeassistant.components.climate import (ClimateEntity,
                                                HVACMode,
                                                ClimateEntityFeature,
                                                PRESET_COMFORT,
                                                PRESET_NONE,
                                                HVACAction,
                                                )

from homeassistant.const import (ATTR_TEMPERATURE, UnitOfTemperature)

from .const import (DOMAIN, SUPPORT_PRESET)
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
        temp = self._stove.get_room_temperature()
        return temp

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
        if self._stove.get_stove_operation_mode() == 2:
            return PRESET_COMFORT
        else:
            return PRESET_NONE

    def set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        _LOGGER.debug('preset mode : ' + str(preset_mode))
        if preset_mode == PRESET_COMFORT:
            _LOGGER.debug("setting up PRESET COMFORT")
            self._stove.set_stove_operation_mode(2)
        else:
            _LOGGER.debug("setting up PRESET NONE")
            if self._stove.is_stove_heating_times_on() == True:
                self._stove.set_stove_operation_mode(1)
            else:
                self._stove.set_stove_operation_mode(0)
        self.schedule_update_ha_state()

    @property
    def target_temperature(self):
        temp = self._stove.get_room_thermostat()
        return temp

    @property
    def target_temperature_step(self):
        return 1

    @property
    def hvac_mode(self):
        return self._stove.get_hvac_mode()

    @property
    def hvac_modes(self) -> HVACMode:
        return HVAC_MODES

    @property
    def hvac_action(self) -> HVACAction:
        """Return current operation ie. heat, cool, idle."""
        if self._stove.get_status_text() == "stove_off":
            return HVACAction.OFF
        elif self._stove.get_status_text() == "offline":
            return HVACAction.OFF
        elif self._stove.get_status_text() == "standby":
            return HVACAction.IDLE
        else:
            return HVACAction.HEATING

    def set_hvac_mode(self, hvac_mode):
        _LOGGER.debug('set_hvac_mode()): ' + str(hvac_mode))
        self._stove.set_hvac_mode(str(hvac_mode))
        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        return SUPPORT_FLAGS

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    def set_temperature(self, **kwargs):
        temperature = int(kwargs.get(ATTR_TEMPERATURE))
        _LOGGER.debug('set_temperature(): ' + str(temperature))
        if kwargs.get(ATTR_TEMPERATURE) is None:
            return
        if not self._stove.is_stove_on():
            return
        # do nothing if HVAC is switched off
        self._stove.set_stove_temperature(temperature)
        self.schedule_update_ha_state()
