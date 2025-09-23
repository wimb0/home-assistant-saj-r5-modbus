"""Config flow for SAJ R5 Inverter Modbus."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    OptionsFlow,
    ConfigEntry,
    FlowResult,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector

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
        return SAJModbusOptionsFlowHandler(config_entry)

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
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=600, step=1)
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class SAJModbusOptionsFlowHandler(OptionsFlow):
    """SAJ Modbus options flow handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not host_valid(user_input[CONF_HOST]):
                errors[CONF_HOST] = "invalid_host"
            else:
                return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=self.config_entry.data.get(CONF_HOST)
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
                ): int,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=600, step=1)
                ),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=options_schema, errors=errors
        )
