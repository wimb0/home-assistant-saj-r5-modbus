"""Config flow for SAJ R5 Inverter Modbus."""

from __future__ import annotations

import ipaddress
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    FlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from modbus_connection import ModbusError

from .const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .inverter import UNIT_ID, SajR5Inverter, create_connection


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


async def async_probe(host: str, port: int) -> str:
    """Probe the inverter, returning its serial; raises ModbusError on failure."""
    connection = create_connection(host, port)
    try:
        return await SajR5Inverter.async_probe(connection.for_unit(UNIT_ID))
    finally:
        await connection.close()


class SAJModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """SAJ Modbus config flow."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
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
                try:
                    await async_probe(host, user_input[CONF_PORT])
                except ModbusError:
                    errors["base"] = "cannot_connect"
            if not errors:
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

        setup_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=setup_schema, errors=errors
        )


class SAJModbusOptionsFlowHandler(OptionsFlow):
    """SAJ Modbus config flow options handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                },
                options={
                    **self.config_entry.options,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )
            return self.async_abort(reason="reconfigure_successful")

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=self.config_entry.data.get(CONF_HOST)
                ): str,
                vol.Required(
                    CONF_PORT, default=self.config_entry.data.get(CONF_PORT)
                ): int,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
