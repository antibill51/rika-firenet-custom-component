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
        return RikaFirenetOptionsFlowHandler()

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit data."""
        if user_input is None:
            user_input = {}
            
        default_username = user_input.get(CONF_USERNAME, "")
        if default_username is None: default_username = ""
        
        default_password = user_input.get(CONF_PASSWORD, "")
        if default_password is None: default_password = ""

        schema_properties = {
            vol.Required(CONF_USERNAME, default=default_username): str,
            vol.Required(CONF_PASSWORD, default=default_password): str,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_properties),
            errors=self._errors,
        )

    async def _test_credentials(self, username, password):
        """Return true if credentials is valid."""
        try:
            return await self.hass.async_add_executor_job(
                RikaFirenetCoordinator.test_authentication, username, password
            )
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("test_credentials_exception")
            return False


class RikaFirenetOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for RikaFirenet."""
    
    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            options = dict(self.config_entry.options)
            options.update(user_input)
            return self.async_create_entry(title="", data=options)

        options = dict(self.config_entry.options)
        
        current_temp = options.get(CONF_DEFAULT_TEMPERATURE, 21)
        if not isinstance(current_temp, int): current_temp = 21
        
        current_scan = options.get(CONF_DEFAULT_SCAN_INTERVAL, 15)
        if not isinstance(current_scan, int): current_scan = 15

        schema_properties = {
            vol.Required(
                CONF_DEFAULT_TEMPERATURE,
                default=current_temp,
            ): int,
            vol.Required(
                CONF_DEFAULT_SCAN_INTERVAL,
                default=current_scan,
            ): int,
        }
        
        for platform in sorted(PLATFORMS):
            platform_id = str(platform)
            
            current_value = options.get(platform_id, True)
            if not isinstance(current_value, bool):
                current_value = True
                
            schema_properties[
                vol.Required(platform_id, default=current_value)
            ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_properties),
        )
