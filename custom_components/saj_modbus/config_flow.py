"""Config flow for SAJ R5 Inverter Modbus."""

import ipaddress
import re
from typing import Any
import voluptuous as vol
import logging

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    FlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


def host_valid(host):
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in (4, 6):
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-.]")
        return all(x and not disallowed.search(x) for x in host.split("."))


@callback
def saj_modbus_entries(hass: HomeAssistant):
    """Return the hosts already configured."""
    return {
        config_entry.data.get(CONF_HOST)
        for config_entry in hass.config_entries.async_entries(DOMAIN)
    }


class SAJModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """SAJ Modbus configflow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input[CONF_PORT],
            }
            options = {
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
            }

            if host in saj_modbus_entries(self.hass):
                errors[CONF_HOST] = "already_configured"
            elif not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_NAME], data=data, options=options
                )

        setup_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=setup_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Handle options flow."""
        return SAJModbusOptionsFlowHandler(config_entry)


class SAJModbusOptionsFlowHandler(OptionsFlow):
    """SAJ Modbus config flow options handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            else:
                new_data = self.config_entry.data.copy()
                new_data[CONF_HOST] = user_input[CONF_HOST]
                new_data[CONF_PORT] = user_input[CONF_PORT]

                new_options = self.config_entry.options.copy()
                new_options[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]

                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data, options=new_options
                )

                return self.async_abort(reason="reconfigure_successful")

        current_host = self.config_entry.data.get(CONF_HOST)
        current_port = self.config_entry.data.get(CONF_PORT, DEFAULT_PORT)
        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current_host): str,
                vol.Required(CONF_PORT, default=current_port): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_scan_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=600)
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
