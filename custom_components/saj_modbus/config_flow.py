"""Config flow for SAJ R5 Inverter Modbus."""
import ipaddress
import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
import logging

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
})

OPTIONS_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
})

ERROR_ALREADY_CONFIGURED = "already_configured"
ERROR_INVALID_HOST = "invalid_host"

def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        ip_version = ipaddress.ip_address(host).version
        return ip_version in [4, 6]
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))

@callback
def saj_modbus_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return {entry.data[CONF_HOST] for entry in hass.config_entries.async_entries(DOMAIN)}

class SAJModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """SAJ Modbus configflow."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def _host_in_configuration_exists(self, host) -> bool:
        """Return True if host exists in configuration."""
        return host in saj_modbus_entries(self.hass)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            if self._host_in_configuration_exists(host):
                errors[CONF_HOST] = ERROR_ALREADY_CONFIGURED
            elif not host_valid(host):
                errors[CONF_HOST] = ERROR_INVALID_HOST
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow to allow configuration changes after setup."""
        return SAJModbusOptionsFlowHandler(config_entry)


class SAJModbusOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle an options flow for SAJ Modbus."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            try:
                # Get the hub from the saved data with robust default handling
                hub = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {}).get("hub")

                if hub is None:
                    _LOGGER.error(f"Hub not found for entry_id: {self.config_entry.entry_id}")
                    return self.async_abort(reason="hub_not_found")

                # Update the hub configuration
                await hub.update_connection_settings(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_SCAN_INTERVAL]
                )

                # Save the new options in config_entry.options
                return self.async_create_entry(title="", data=user_input)
            except Exception as e:
                _LOGGER.error(f"Error updating SAJ Modbus configuration: {str(e)}")
                return self.async_abort(reason="update_failed")

        # Show the options form with defaults from config entry
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=self.config_entry.options.get(CONF_HOST, self.config_entry.data.get(CONF_HOST, ''))): str,
                vol.Required(CONF_PORT, default=self.config_entry.options.get(CONF_PORT, self.config_entry.data.get(CONF_PORT, 502))): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=self.config_entry.options.get(CONF_SCAN_INTERVAL, self.config_entry.data.get(CONF_SCAN_INTERVAL, 30))): int,
            }),
        )
