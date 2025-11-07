import logging
import time
from datetime import datetime, timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    ClimateEntityFeature,
    PRESET_COMFORT,
    PRESET_NONE,
    HVACAction,
)

from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import callback

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
        self._last_mode_change = datetime.now()
        self._mode_change_min_interval = timedelta(seconds=5)  # Intervalle minimal entre les changements de mode

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
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        try:
            temperature = int(temperature)
            if not MIN_TEMP <= temperature <= MAX_TEMP:
                _LOGGER.warning(f"Temperature {temperature}°C is outside valid range ({MIN_TEMP}-{MAX_TEMP}°C)")
                return
        except ValueError:
            _LOGGER.error(f"Invalid temperature value: {temperature}")
            return

        _LOGGER.debug(f'Setting temperature to {temperature}°C for {self.name}')
        
        if not self._stove.is_stove_on():
            _LOGGER.info(f"Stove {self.name} is off, turning it on before setting temperature")
            self._stove.set_stove_on_off(True)
            await self.coordinator.async_request_refresh()
            # Petit délai pour laisser le poêle se mettre en route
            await self.hass.async_add_executor_job(time.sleep, 2)
            
        self._stove.set_stove_temperature(temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set HVAC mode with rate limiting and retry logic."""
        now = datetime.now()
        if (now - self._last_mode_change) < self._mode_change_min_interval:
            _LOGGER.warning(f"Mode change requested too soon for {self.name}. Please wait.")
            return

        _LOGGER.debug(f'Setting HVAC mode to {hvac_mode} for {self.name}')
        self._last_mode_change = now

        try:
            # Attendre un court instant pour assurer la stabilité de la transition
            await self.hass.async_add_executor_job(time.sleep, 1)
            
            current_mode = self._stove.get_hvac_mode()
            if current_mode == hvac_mode:
                _LOGGER.debug(f"Stove {self.name} already in {hvac_mode} mode")
                return

            self._stove.set_hvac_mode(str(hvac_mode))
            
            # Premier rafraîchissement pour envoyer la commande
            await self.coordinator.async_request_refresh()
            
            # Attendre et vérifier que le changement a été appliqué
            await self.hass.async_add_executor_job(time.sleep, 2)
            
            # Deuxième rafraîchissement pour confirmer le changement
            await self.coordinator.async_request_refresh()
            
            # Vérifier si le changement a été appliqué
            if self._stove.get_hvac_mode() != hvac_mode:
                _LOGGER.warning(f"Mode change to {hvac_mode} may not have been applied for {self.name}")
                # Un dernier essai
                await self.coordinator.async_request_refresh()
                
        except Exception as e:
            _LOGGER.error(f"Error setting HVAC mode for {self.name}: {e}")
            # Réinitialiser le timer en cas d'erreur pour permettre une nouvelle tentative
            self._last_mode_change = datetime.now() - self._mode_change_min_interval

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode with validation."""
        if preset_mode not in self.preset_modes:
            _LOGGER.warning(f"Invalid preset mode {preset_mode} for {self.name}")
            return

        _LOGGER.debug(f"Setting preset mode to {preset_mode} for {self.name}")
        
        try:
            # Vérifier si nous sommes déjà dans ce mode
            current_preset = self._stove.get_preset_mode()
            if current_preset == preset_mode:
                _LOGGER.debug(f"Stove {self.name} already in {preset_mode} preset mode")
                return

            # Appliquer le nouveau mode
            self._stove.set_preset_mode(preset_mode)
            await self.coordinator.async_request_refresh()

            # Vérifier que le changement a été appliqué
            await self.hass.async_add_executor_job(time.sleep, 1)
            await self.coordinator.async_request_refresh()

            if self._stove.get_preset_mode() != preset_mode:
                _LOGGER.warning(f"Preset mode change to {preset_mode} may not have been applied for {self.name}")
                await self.coordinator.async_request_refresh()
        
        except Exception as e:
            _LOGGER.error(f"Error setting preset mode for {self.name}: {e}")
