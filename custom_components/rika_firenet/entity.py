import logging
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, DEFAULT_NAME, VERSION
from .core import RikaFirenetStove, RikaFirenetCoordinator

_LOGGER = logging.getLogger(__name__)


class RikaFirenetEntity(CoordinatorEntity):
    """Base class for all Rika Firenet entities."""

    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator, suffix=None):
        """Initialize the entity."""
        super().__init__(coordinator)

        self._config_entry = config_entry
        self._stove = stove
        self._stove_id = stove.get_id()
        self._suffix = suffix
        self._name = f"{stove.get_name()} {suffix}" if suffix else stove.get_name()
        self._unique_id = self._generate_unique_id()

        _LOGGER.debug("Created RikaFirenetEntity: name=%s, unique_id=%s for stove_id=%s", self._name, self._unique_id, self._stove_id)

    def _generate_unique_id(self):
        """Generate a unique ID for the entity."""
        # Ensure stove_id is a string to avoid errors with .replace
        stove_id_str = str(self._stove_id)
        if self._suffix:
            # Combine stove ID and suffix for uniqueness
            return f"{stove_id_str}_{self._suffix}".lower()
        return stove_id_str.lower()

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def device_info(self):
        """Return the device information."""
        # Ensure stove_id is a string for identifiers
        stove_id_str = str(self._stove_id)
        return {
            "identifiers": {(DOMAIN, stove_id_str)},
            "name": self._stove.get_name(),
            "manufacturer": DEFAULT_NAME, # Manufacturer name
            "model": f"Firenet Stove ({stove_id_str})", # More specific model
            "sw_version": VERSION, # Integration version
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # The stove is available if the coordinator is available and the stove has a state.
        return super().available and self._stove.get_state() is not None
