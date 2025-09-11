"""Config flow for SAJ R5 Inverter Modbus."""
from __future__ import annotations

import ipaddress
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry, FlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in (4, 6):
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-.]")
        return all(x and not disallowed.search(x) for x in host.split("."))


class SAJModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """SAJ Modbus config flow."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        # This is the corrected line.
        # The handler is now created without any arguments.
        return SAJModbusOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]

            if not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            elif any(
                entry.data.get(CONF_HOST) == host
                for entry in self._async_current_entries()
            ):
                errors[CONF_HOST] = "already_configured"
            else:
                # Separate data from options
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                }
                options = {
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }

                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_NAME], data=data, options=options
                )

        # Define the schema for the user setup form
        setup_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=600)),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=setup_schema, errors=errors
        )


class SAJModbusOptionsFlowHandler(OptionsFlow):
    """SAJ Modbus options flow handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            else:
                # A reconfigure flow updates both data and options
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        # Keep the original name
                        CONF_NAME: self.config_entry.data.get(CONF_NAME),
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                    },
                    options={
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )
                # Abort with success reason to show the user a success message
                return self.async_abort(reason="reconfigure_successful")

        # Define the schema for the options form
        options_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=600)
                ),
            }
        )

        # Populate the form with the current values
        suggested_values = {
            CONF_HOST: self.config_entry.data.get(CONF_HOST),
            CONF_PORT: self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
            CONF_SCAN_INTERVAL: self.config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema, suggested_values
            ),
            errors=errors,
        )
