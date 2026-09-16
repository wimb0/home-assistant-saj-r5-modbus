"""Config flow for SAJ R5 Inverter Modbus."""

from __future__ import annotations

import ipaddress
import re
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
from homeassistant.helpers.selector import SerialPortSelector
from modbus_connection import ModbusError

from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_PORT,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_NAME,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STOPBITS,
    DOMAIN,
    SERIAL_BAUDRATES,
)
from .inverter import (
    UNIT_ID,
    SajR5Inverter,
    create_connection,
    create_serial_connection,
)


# A DNS label: alphanumeric, inner hyphens allowed, 1-63 characters.
_HOSTNAME = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return True
    if len(host) > 253 or not _HOSTNAME.match(host):
        return False
    # RFC 1123: the top-level label may not be all-numeric, which is what
    # separates a hostname from a malformed IP address such as 192.168.1.999.
    return not host.rstrip(".").rsplit(".", 1)[-1].isdigit()


def serial_port_valid(device: str) -> bool:
    """Return True if the serial device looks usable.

    Accepts a local port (``/dev/ttyUSB0``), a Windows COM port (``COM3``),
    and the serial-over-network URLs modbus-connection supports
    (``socket://host:port``, ``rfc2217://host:port``).
    """
    device = (device or "").strip()
    if not device:
        return False
    lowered = device.lower()
    if lowered.startswith(("socket://", "rfc2217://")):
        return "://" in device and len(device) > len("socket://") + 1
    return True


async def async_probe(host: str, port: int) -> str:
    """Probe the inverter over TCP, returning its serial; raises on failure."""
    connection = create_connection(host, port)
    try:
        return await SajR5Inverter.async_probe(connection.for_unit(UNIT_ID))
    finally:
        await connection.close()


async def async_probe_serial(
    device: str,
    baudrate: int,
    bytesize: int,
    parity: str,
    stopbits: int,
) -> str:
    """Probe the inverter over a serial line, returning its serial number."""
    connection = create_serial_connection(
        device, baudrate, bytesize, parity, stopbits
    )
    try:
        return await SajR5Inverter.async_probe(connection.for_unit(UNIT_ID))
    finally:
        await connection.close()


class SAJModbusConfigFlow(ConfigFlow, domain=DOMAIN):
    """SAJ Modbus config flow."""

    VERSION = 3

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return SAJModbusOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick the transport, then delegate to its step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=[CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL],
        )

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the TCP setup step."""
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
                    serial = await async_probe(host, user_input[CONF_PORT])
                except ModbusError:
                    errors["base"] = "cannot_connect"
            if not errors:
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                }
                options = {
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }
                # Key the entry on the serial where the inverter reports one,
                # so the same device is recognised across addresses. Firmware
                # that does not serve the info block falls back to the host.
                await self.async_set_unique_id(serial or host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_NAME], data=data, options=options
                )

        tcp_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(
            step_id="tcp", data_schema=tcp_schema, errors=errors
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the serial (RS485) setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            device = user_input[CONF_SERIAL_PORT]

            if not serial_port_valid(device):
                errors[CONF_SERIAL_PORT] = "invalid_serial_port"
            elif any(
                entry.data.get(CONF_SERIAL_PORT) == device
                for entry in self._async_current_entries()
            ):
                errors[CONF_SERIAL_PORT] = "already_configured"
            else:
                try:
                    serial = await async_probe_serial(
                        device,
                        user_input[CONF_BAUDRATE],
                        DEFAULT_BYTESIZE,
                        DEFAULT_PARITY,
                        DEFAULT_STOPBITS,
                    )
                except ModbusError:
                    errors["base"] = "cannot_connect"
            if not errors:
                data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
                    CONF_SERIAL_PORT: device,
                    CONF_BAUDRATE: user_input[CONF_BAUDRATE],
                }
                options = {
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }
                # Same identity rule as TCP: the inverter's serial where it
                # reports one, else the port path it was found on.
                await self.async_set_unique_id(serial or device)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_NAME], data=data, options=options
                )

        serial_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_SERIAL_PORT): SerialPortSelector(),
                vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In(
                    list(SERIAL_BAUDRATES)
                ),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }
        )

        return self.async_show_form(
            step_id="serial", data_schema=serial_schema, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick which transport to reconfigure."""
        entry = self._get_reconfigure_entry()
        current = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_TCP)
        if user_input is not None:
            if user_input[CONF_CONNECTION_TYPE] == CONNECTION_TYPE_SERIAL:
                return await self.async_step_reconfigure_serial()
            return await self.async_step_reconfigure_tcp()
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONNECTION_TYPE, default=current
                    ): vol.In([CONNECTION_TYPE_TCP, CONNECTION_TYPE_SERIAL]),
                }
            ),
        )

    async def async_step_reconfigure_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Change where the inverter lives (TCP)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            if not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    serial = await async_probe(host, user_input[CONF_PORT])
                except ModbusError:
                    errors["base"] = "cannot_connect"
            if not errors:
                if serial:
                    # Refuse to repoint this entry at a different inverter,
                    # which would orphan its entities and duplicate its device.
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_mismatch(reason="wrong_inverter")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_CONNECTION_TYPE: CONNECTION_TYPE_TCP,
                        CONF_HOST: host,
                        CONF_PORT: user_input[CONF_PORT],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure_tcp",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST)): str,
                    vol.Required(CONF_PORT, default=entry.data.get(CONF_PORT)): int,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Change where the inverter lives (serial)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            device = user_input[CONF_SERIAL_PORT]
            if not serial_port_valid(device):
                errors[CONF_SERIAL_PORT] = "invalid_serial_port"
            else:
                try:
                    serial = await async_probe_serial(
                        device,
                        user_input[CONF_BAUDRATE],
                        DEFAULT_BYTESIZE,
                        DEFAULT_PARITY,
                        DEFAULT_STOPBITS,
                    )
                except ModbusError:
                    errors["base"] = "cannot_connect"
            if not errors:
                if serial:
                    await self.async_set_unique_id(serial)
                    self._abort_if_unique_id_mismatch(reason="wrong_inverter")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
                        CONF_SERIAL_PORT: device,
                        CONF_BAUDRATE: user_input[CONF_BAUDRATE],
                    },
                )

        return self.async_show_form(
            step_id="reconfigure_serial",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERIAL_PORT,
                        default=entry.data.get(CONF_SERIAL_PORT) or vol.UNDEFINED,
                    ): SerialPortSelector(),
                    vol.Required(
                        CONF_BAUDRATE,
                        default=entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
                    ): vol.In(list(SERIAL_BAUDRATES)),
                }
            ),
            errors=errors,
        )


class SAJModbusOptionsFlowHandler(OptionsFlow):
    """SAJ Modbus config flow options handler."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the polling interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
