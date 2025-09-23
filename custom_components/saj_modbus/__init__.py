"""The SAJ Modbus Integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    ATTR_MANUFACTURER,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .hub import SAJModbusHub
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a SAJ modbus entry from a config entry."""
    host = entry.data.get(CONF_HOST)
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    port = entry.data.get(CONF_PORT)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hub = SAJModbusHub(hass, name, host, port, scan_interval)

    device_info = {
        "identifiers": {(DOMAIN, name)},
        "name": name,
        "manufacturer": ATTR_MANUFACTURER,
    }

    entry.runtime_data = {"hub": hub, "device_info": device_info}

    try:
        # Await the initial setup of the inverter data.
        await hub.async_setup()
        await hub.async_refresh()
    except (UpdateFailed, ConfigEntryNotReady) as err:
        raise ConfigEntryNotReady from err

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if hub := entry.runtime_data.get("hub"):
        hub.close()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
