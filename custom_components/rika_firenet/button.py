import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import RikaFirenetEntity
from .const import DOMAIN
from .core import RikaFirenetCoordinator, RikaFirenetStove

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Rika Firenet button platform."""
    _LOGGER.info("Setting up platform button")
    coordinator: RikaFirenetCoordinator = hass.data[DOMAIN][entry.entry_id]

    stove_entities = []

    for stove in coordinator.get_stoves():
        # Ajouter uniquement le bouton de réinitialisation du stock
        stove_entities.append(
            ResetPelletStockButton(entry, stove, coordinator)
        )

    if stove_entities:
        async_add_entities(stove_entities, True)


class ResetPelletStockButton(RikaFirenetEntity, ButtonEntity):
    """Button to reset the pellet stock level."""
    
    def __init__(self, config_entry, stove: RikaFirenetStove, coordinator: RikaFirenetCoordinator):
        """Initialize the button entity."""
        super().__init__(config_entry, stove, coordinator, "reset_pellet_stock")
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:restart"
        
    @property
    def translation_key(self):
        """Return the translation key for the button."""
        return "reset_pellet_stock"
        
    async def async_press(self):
        """Handle the button press."""
        _LOGGER.info(f"Resetting pellet stock for stove {self._stove.get_id()}")
        
        # Réinitialiser la valeur du stock de pellets dans le stove state
        await self.hass.async_add_executor_job(
            self._stove.reset_pellet_stock
        )
        
        # Forcer la mise à jour des entités après la réinitialisation
        await self.coordinator.async_request_refresh() 