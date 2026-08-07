"""The SAJ Modbus Integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import (
    ATTR_MANUFACTURER,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MODBUS_TIMEOUT,
)
from .hub import SAJModbusHub
from .inverter import UNIT_ID, SajR5Inverter
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a SAJ modbus entry from a config entry."""
    host = entry.data[CONF_HOST]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    port = entry.data[CONF_PORT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    connection = ModbusConnection(
        ModbusTcpParams(host=host, port=port), timeout=MODBUS_TIMEOUT
    )
    entry.async_on_unload(connection.close)

    device = SajR5Inverter(connection.for_unit(UNIT_ID))
    hub = SAJModbusHub(hass, entry, name, device, scan_interval)

    entry.runtime_data = {
        "hub": hub,
        "device_info": {
            "identifiers": {(DOMAIN, name)},
            "name": name,
            "manufacturer": ATTR_MANUFACTURER,
        },
    }

    await hub.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.add_update_listener(options_update_listener)

    async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unload_services(hass)
    return unload_ok


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
