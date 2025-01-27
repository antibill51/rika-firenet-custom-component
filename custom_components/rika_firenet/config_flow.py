import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_DEFAULT_TEMPERATURE,
    CONF_DEFAULT_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
    PLATFORMS,
)
from .core import RikaFirenetCoordinator

_LOGGER = logging.getLogger(__name__)


class RikaFirenetFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        # Permettre une seule instance de l'intégration
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            valid = await self._test_credentials(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if valid:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
            else:
                self._errors["base"] = "auth"
            return await self._show_config_form(user_input)
        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return RikaFirenetOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit data."""
        if user_input is None:
            user_input = {}
        schema_properties = {
            vol.Required(CONF_USERNAME, default=user_input.get(CONF_USERNAME, None)): str,
            vol.Required(CONF_PASSWORD, default=user_input.get(CONF_PASSWORD, None)): str,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_properties),
            errors=self._errors,
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            coordinator = RikaFirenetCoordinator(self.hass, username, password, 21, 15, True)
            await self.hass.async_add_executor_job(coordinator.setup)
            return True
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("test_credentials_exception")
            pass
        return False


class RikaFirenetOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for RikaFirenet."""

    def __init__(self, config_entry):
        """Initialize RikaFirenet options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Initialize options flow."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        schema_properties = {
            vol.Required(
                CONF_DEFAULT_TEMPERATURE,
                default=self.options.get(CONF_DEFAULT_TEMPERATURE, 21),
            ): int,
            vol.Required(
                CONF_DEFAULT_SCAN_INTERVAL,
                default=self.options.get(CONF_DEFAULT_SCAN_INTERVAL, 15),
            ): int,
        }
        schema_properties.update(
            {
                vol.Required(x, default=self.options.get(x, True)): bool
                for x in sorted(PLATFORMS)
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_properties),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.title, data=self.options
        )

    @staticmethod
    @callback
    def async_options_flow(config_entry):
        """Return an options flow handler."""
        return RikaFirenetOptionsFlowHandler(config_entry)
