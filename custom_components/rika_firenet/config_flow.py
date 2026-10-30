import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_DEFAULT_TEMPERATURE,
    CONF_DEFAULT_SCAN_INTERVAL,
    CONF_PENDING_TIMEOUT,
    DEFAULT_PENDING_TIMEOUT,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_HOST,
    CONF_CONNECTION_TYPE,
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_LOCAL,
    CONF_HOST_DEFAULT,
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
            conn_type = user_input.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_CLOUD)
            if conn_type == CONNECTION_TYPE_LOCAL:
                host = user_input.get(CONF_HOST, CONF_HOST_DEFAULT)
                valid = await self._test_local_connection(host)
                if valid:
                    return self.async_create_entry(
                        title=f"Open Firenet ({host})",
                        data=user_input
                    )
                self._errors["base"] = "cannot_connect"
            else:
                username = user_input.get(CONF_USERNAME, "")
                password = user_input.get(CONF_PASSWORD, "")
                valid = await self._test_credentials(username, password)
                if valid:
                    return self.async_create_entry(
                        title=username,
                        data=user_input
                    )
                self._errors["base"] = "auth"
            return await self._show_config_form(user_input)
        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return RikaFirenetOptionsFlowHandler()

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit data."""
        if user_input is None:
            user_input = {}

        conn_type = user_input.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_CLOUD)
        default_username = user_input.get(CONF_USERNAME, "") or ""
        default_password = user_input.get(CONF_PASSWORD, "") or ""
        default_host = user_input.get(CONF_HOST, CONF_HOST_DEFAULT) or CONF_HOST_DEFAULT

        schema_properties = {
            vol.Required(CONF_CONNECTION_TYPE, default=conn_type): vol.In(
                {
                    CONNECTION_TYPE_CLOUD: "Rika Firenet Cloud (rika-firenet.com)",
                    CONNECTION_TYPE_LOCAL: "Open Firenet Local HTTP (open-firenet)",
                }
            ),
            vol.Optional(CONF_HOST, default=default_host): str,
            vol.Optional(CONF_USERNAME, default=default_username): str,
            vol.Optional(CONF_PASSWORD, default=default_password): str,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_properties),
            errors=self._errors,
        )

    async def _test_local_connection(self, host):
        """Return true if local Open Firenet bridge is reachable."""
        try:
            return await self.hass.async_add_executor_job(
                RikaFirenetCoordinator.test_local_connection, host
            )
        except Exception:
            _LOGGER.exception("test_local_connection_exception")
            return False

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

        current_timeout = options.get(CONF_PENDING_TIMEOUT, DEFAULT_PENDING_TIMEOUT)
        if not isinstance(current_timeout, int): current_timeout = DEFAULT_PENDING_TIMEOUT

        schema_properties = {
            vol.Required(
                CONF_DEFAULT_TEMPERATURE,
                default=current_temp,
            ): int,
            vol.Required(
                CONF_DEFAULT_SCAN_INTERVAL,
                default=current_scan,
            ): int,
            vol.Required(
                CONF_PENDING_TIMEOUT,
                default=current_timeout,
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
