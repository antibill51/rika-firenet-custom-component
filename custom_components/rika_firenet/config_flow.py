import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DEFAULT_TEMPERATURE,
    CONF_DEFAULT_SCAN_INTERVAL,
    CONF_PENDING_TIMEOUT,
    DEFAULT_PENDING_TIMEOUT,
    CONF_SCHEDULE_ENTITY,
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

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._reconfigure_entry = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user: menu to select connection mode."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["cloud", "local"],
        )

    async def async_step_cloud(self, user_input=None):
        """Handle Cloud connection flow."""
        self._errors = {}
        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "")
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            valid = await self._test_credentials(username, password)
            if valid:
                data = {
                    CONF_CONNECTION_TYPE: CONNECTION_TYPE_CLOUD,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                }
                return self.async_create_entry(title=username, data=data)
            self._errors["base"] = "auth"

        default_user = (user_input or {}).get(CONF_USERNAME, "")
        default_pass = (user_input or {}).get(CONF_PASSWORD, "")
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=default_user): str,
                vol.Required(CONF_PASSWORD, default=default_pass): str,
            }
        )
        return self.async_show_form(
            step_id="cloud",
            data_schema=schema,
            errors=self._errors,
        )

    async def async_step_local(self, user_input=None):
        """Handle Local Open Firenet connection flow."""
        self._errors = {}
        if user_input is not None:
            host = user_input.get(CONF_HOST, CONF_HOST_DEFAULT).strip()
            await self.async_set_unique_id(f"local_{host.lower()}")
            self._abort_if_unique_id_configured()

            valid = await self._test_local_connection(host)
            if valid:
                data = {
                    CONF_CONNECTION_TYPE: CONNECTION_TYPE_LOCAL,
                    CONF_HOST: host,
                }
                return self.async_create_entry(title=f"Open Firenet ({host})", data=data)
            self._errors["base"] = "cannot_connect"

        default_host = (user_input or {}).get(CONF_HOST, CONF_HOST_DEFAULT) or CONF_HOST_DEFAULT
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=default_host): str,
            }
        )
        return self.async_show_form(
            step_id="local",
            data_schema=schema,
            errors=self._errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration initialized by the user."""
        self._reconfigure_entry = self._get_reconfigure_entry()
        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["reconfigure_cloud", "reconfigure_local"],
        )

    async def async_step_reconfigure_cloud(self, user_input=None):
        """Reconfigure to Cloud mode."""
        self._errors = {}
        entry = self._reconfigure_entry or self._get_reconfigure_entry()

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "")
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            valid = await self._test_credentials(username, password)
            if valid:
                new_data = dict(entry.data)
                new_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_CLOUD
                new_data[CONF_USERNAME] = username
                new_data[CONF_PASSWORD] = password
                return self.async_update_reload_and_abort(
                    entry,
                    title=username,
                    unique_id=username.lower(),
                    data=new_data,
                )
            self._errors["base"] = "auth"

        current_user = (user_input or {}).get(CONF_USERNAME) or entry.data.get(CONF_USERNAME, "") or ""
        current_pass = (user_input or {}).get(CONF_PASSWORD) or entry.data.get(CONF_PASSWORD, "") or ""
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=current_user): str,
                vol.Required(CONF_PASSWORD, default=current_pass): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure_cloud",
            data_schema=schema,
            errors=self._errors,
        )

    async def async_step_reconfigure_local(self, user_input=None):
        """Reconfigure to Local Open Firenet mode."""
        self._errors = {}
        entry = self._reconfigure_entry or self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input.get(CONF_HOST, CONF_HOST_DEFAULT).strip()
            await self.async_set_unique_id(f"local_{host.lower()}")
            self._abort_if_unique_id_configured()

            valid = await self._test_local_connection(host)
            if valid:
                new_data = dict(entry.data)
                new_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_LOCAL
                new_data[CONF_HOST] = host
                return self.async_update_reload_and_abort(
                    entry,
                    title=f"Open Firenet ({host})",
                    unique_id=f"local_{host.lower()}",
                    data=new_data,
                )
            self._errors["base"] = "cannot_connect"

        current_host = (user_input or {}).get(CONF_HOST) or entry.data.get(CONF_HOST, CONF_HOST_DEFAULT) or CONF_HOST_DEFAULT
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure_local",
            data_schema=schema,
            errors=self._errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return RikaFirenetOptionsFlowHandler()

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
        """Return true if credentials are valid."""
        try:
            return await self.hass.async_add_executor_job(
                RikaFirenetCoordinator.test_authentication, username, password
            )
        except Exception:
            _LOGGER.exception("test_credentials_exception")
            return False


class RikaFirenetOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for RikaFirenet."""

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_init(self, user_input=None):
        """Display options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["general", "cloud", "local"],
        )

    async def async_step_general(self, user_input=None):
        """Manage general functional options."""
        self._errors = {}
        options = dict(self.config_entry.options)

        if user_input is not None:
            options.update(user_input)
            return self.async_create_entry(title="", data=options)

        current_temp = options.get(CONF_DEFAULT_TEMPERATURE, 21)
        if not isinstance(current_temp, int):
            current_temp = 21

        current_scan = options.get(CONF_DEFAULT_SCAN_INTERVAL, 15)
        if not isinstance(current_scan, int):
            current_scan = 15

        current_timeout = options.get(CONF_PENDING_TIMEOUT, DEFAULT_PENDING_TIMEOUT)
        if not isinstance(current_timeout, int):
            current_timeout = DEFAULT_PENDING_TIMEOUT

        schema_properties = {
            vol.Required(CONF_DEFAULT_TEMPERATURE, default=current_temp): int,
            vol.Required(CONF_DEFAULT_SCAN_INTERVAL, default=current_scan): int,
            vol.Required(CONF_PENDING_TIMEOUT, default=current_timeout): int,
            vol.Optional(
                CONF_SCHEDULE_ENTITY,
                description={"suggested_value": options.get(CONF_SCHEDULE_ENTITY)},
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="schedule")),
        }

        for platform in sorted(PLATFORMS):
            platform_id = str(platform)
            current_value = options.get(platform_id, True)
            if not isinstance(current_value, bool):
                current_value = True
            schema_properties[vol.Required(platform_id, default=current_value)] = bool

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(schema_properties),
            errors=self._errors,
        )

    async def async_step_cloud(self, user_input=None):
        """Switch connection to Cloud Rika Firenet."""
        self._errors = {}
        entry_data = dict(self.config_entry.data)

        if user_input is not None:
            username = user_input.get(CONF_USERNAME, "").strip()
            password = user_input.get(CONF_PASSWORD, "")
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id != self.config_entry.entry_id:
                    if entry.data.get(CONF_CONNECTION_TYPE) == CONNECTION_TYPE_CLOUD and (entry.data.get(CONF_USERNAME) or "").lower() == username.lower():
                        self._errors["base"] = "already_configured"
                        break
            if not self._errors:
                valid = await self._test_credentials(username, password)
                if valid:
                    entry_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_CLOUD
                    entry_data[CONF_USERNAME] = username
                    entry_data[CONF_PASSWORD] = password
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=username,
                        unique_id=username.lower(),
                        data=entry_data,
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(title="", data=self.config_entry.options)
                self._errors["base"] = "auth"

        default_user = (user_input or {}).get(CONF_USERNAME) or entry_data.get(CONF_USERNAME, "") or ""
        default_pass = (user_input or {}).get(CONF_PASSWORD) or entry_data.get(CONF_PASSWORD, "") or ""
        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default=default_user): str,
                vol.Required(CONF_PASSWORD, default=default_pass): str,
            }
        )
        return self.async_show_form(
            step_id="cloud",
            data_schema=schema,
            errors=self._errors,
        )

    async def async_step_local(self, user_input=None):
        """Switch connection to Local Open Firenet."""
        self._errors = {}
        entry_data = dict(self.config_entry.data)

        if user_input is not None:
            host = user_input.get(CONF_HOST, CONF_HOST_DEFAULT).strip()
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id != self.config_entry.entry_id:
                    if entry.data.get(CONF_CONNECTION_TYPE) == CONNECTION_TYPE_LOCAL and (entry.data.get(CONF_HOST) or "").lower() == host.lower():
                        self._errors["base"] = "already_configured"
                        break
            if not self._errors:
                valid = await self._test_local_connection(host)
                if valid:
                    entry_data[CONF_CONNECTION_TYPE] = CONNECTION_TYPE_LOCAL
                    entry_data[CONF_HOST] = host
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        title=f"Open Firenet ({host})",
                        unique_id=f"local_{host.lower()}",
                        data=entry_data,
                    )
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                    return self.async_create_entry(title="", data=self.config_entry.options)
                self._errors["base"] = "cannot_connect"

        default_host = (user_input or {}).get(CONF_HOST) or entry_data.get(CONF_HOST, CONF_HOST_DEFAULT) or CONF_HOST_DEFAULT
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=default_host): str,
            }
        )
        return self.async_show_form(
            step_id="local",
            data_schema=schema,
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
        """Return true if credentials are valid."""
        try:
            return await self.hass.async_add_executor_job(
                RikaFirenetCoordinator.test_authentication, username, password
            )
        except Exception:
            _LOGGER.exception("test_credentials_exception")
            return False
