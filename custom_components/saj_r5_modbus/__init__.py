"""The SAJ Modbus Integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
)
from .hub import SAJModbusHub
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a SAJ modbus entry from a config entry."""
    host = entry.data.get(CONF_HOST)
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    port = entry.data.get(CONF_PORT)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hub = SAJModbusHub(hass, name, host, port, scan_interval)
    
    try:
        await hub.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        raise

    entry.runtime_data = hub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if hub := entry.runtime_data:
        hub.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
