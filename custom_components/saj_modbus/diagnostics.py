"""Diagnostics support for SAJ Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusError

from .hub import SajConfigEntry

TO_REDACT = {
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SajConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    hub = entry.runtime_data

    try:
        raw_registers: dict[str, Any] = {
            space: {f"0x{address:04X}": value for address, value in values.items()}
            for space, values in (await hub.device.async_read_raw()).items()
        }
    except ModbusError as ex:
        raw_registers = {"error": str(ex)}

    diagnostics_data = {
        "config_entry_data": async_redact_data(entry.data, TO_REDACT),
        "config_entry_options": async_redact_data(entry.options, TO_REDACT),
        "inverter_data": async_redact_data(hub.inverter_data, TO_REDACT),
        "last_fetched_data": hub.data,
        "raw_registers": raw_registers,
    }

    return diagnostics_data
