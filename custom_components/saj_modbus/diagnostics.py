"""Diagnostics support for SAJ Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusError

from .const import COUNTER_SENSOR_TYPES, NUMBER_TYPES, SENSOR_TYPES, SWITCH_TYPES
from .hub import SAJModbusHub, SajConfigEntry
from .inverter import SajR5Inverter

TO_REDACT = {
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
}


def _decoded_values(hub: SAJModbusHub) -> dict[str, Any]:
    """Every value this integration exposes, keyed by entity key.

    Built from the entity descriptions rather than from the device model, so a
    diagnostics download reports exactly what the entities report.
    """
    return {
        description.key: description.value_fn(hub)
        for descriptions in (
            SENSOR_TYPES,
            COUNTER_SENSOR_TYPES,
            NUMBER_TYPES,
            SWITCH_TYPES,
        )
        for description in descriptions.values()
    }


def _register_layout(device: SajR5Inverter) -> dict[str, dict[str, str]]:
    """Where every declared field sits on the device, per component.

    Taken from the library's resolved layout rather than a second address
    table here, so a raw register dump can be read without the protocol
    document beside it.
    """
    return {
        name: {
            field: f"{resolved.space}:0x{resolved.address:04X}"
            + (
                f"-0x{resolved.address + resolved.count - 1:04X}"
                if resolved.count > 1
                else ""
            )
            for field, resolved in component.resolved_fields.items()
        }
        for name, component in device.components.items()
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

    return {
        "config_entry_data": async_redact_data(entry.data, TO_REDACT),
        "config_entry_options": async_redact_data(entry.options, TO_REDACT),
        "decoded_values": _decoded_values(hub),
        "unserved_components": sorted(hub.absent_components),
        "register_layout": _register_layout(hub.device),
        "raw_registers": raw_registers,
    }
