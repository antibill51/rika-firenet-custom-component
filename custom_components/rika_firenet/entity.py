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

        _LOGGER.debug("Created RikaFirenetEntity: name=%s, unique_id=%s", self._name, self._unique_id)

    def _generate_unique_id(self):
        """Generate a unique ID for the entity."""
        if self._suffix:
            # Combine stove ID and suffix for uniqueness
            return f"{self._stove_id}_{self._suffix}".replace(" ", "_").lower()
        return self._stove_id.replace(" ", "_").lower()

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
        return {
            "identifiers": {(DOMAIN, self._stove_id)},
            "name": self._stove.get_name(),
            "model": VERSION,
            "manufacturer": DEFAULT_NAME,
        }
