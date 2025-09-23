"""Diagnostics support for SAJ Modbus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

from .hub import SAJModbusHub

TO_REDACT = {
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    hub: SAJModbusHub = entry.runtime_data["hub"]

    diagnostics_data = {
        "config_entry_data": async_redact_data(entry.data, TO_REDACT),
        "config_entry_options": async_redact_data(entry.options, TO_REDACT),
        "inverter_data": async_redact_data(hub.inverter_data, TO_REDACT),
        "last_fetched_data": hub.data,
    }

    return diagnostics_data
