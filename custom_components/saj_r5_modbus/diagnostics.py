"""Diagnostics support for SAJ Modbus."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import SAJModbusHub

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    hub: SAJModbusHub = hass.data[DOMAIN][entry.data[CONF_NAME]]["hub"]

    diagnostics_data = {
        "config_entry_data": entry.data,
        "config_entry_options": entry.options,
        "inverter_data": hub.inverter_data,
        "last_fetched_data": hub.data,
    }

    return diagnostics_data
