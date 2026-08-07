"""The SAJ Modbus Integration."""

import logging

from typing import Any

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import (
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .hub import SAJModbusHub, SajConfigEntry
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number", "switch"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's services once."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SajConfigEntry) -> bool:
    """Set up a SAJ modbus entry from a config entry."""
    host = entry.data[CONF_HOST]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    port = entry.data[CONF_PORT]
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    hub = SAJModbusHub(hass, entry, name, host, port, scan_interval)
    entry.async_on_unload(hub.async_close)
    entry.runtime_data = hub

    await hub.async_config_entry_first_refresh()
    await _async_migrate_to_serial_identity(hass, entry, hub)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SajConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_migrate_to_serial_identity(
    hass: HomeAssistant, entry: SajConfigEntry, hub: SAJModbusHub
) -> None:
    """Rebuild this entry's identity around the inverter's serial number.

    Identity was originally derived from the host (config entry) and the
    user-chosen name (device and entities), so renaming the integration or
    moving the inverter to a new address orphaned everything. Runs before the
    platforms are set up so entities register under their new unique ids.
    """
    serial = hub.serial_number
    if serial is None:
        # The info block was not readable; identity stays name-based, and this
        # runs again on the next reload that manages to read it.
        return

    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    if name != serial:
        old_prefix = f"{name}_"

        @callback
        def _migrate_entity(registry_entry: er.RegistryEntry) -> dict[str, Any] | None:
            if not registry_entry.unique_id.startswith(old_prefix):
                return None
            suffix = registry_entry.unique_id.removeprefix(old_prefix)
            return {"new_unique_id": f"{serial}_{suffix}"}

        await er.async_migrate_entries(hass, entry.entry_id, _migrate_entity)

        device_registry = dr.async_get(hass)
        if device := device_registry.async_get_device(identifiers={(DOMAIN, name)}):
            device_registry.async_update_device(
                device.id, new_identifiers={(DOMAIN, serial)}
            )

    if entry.unique_id != serial:
        hass.config_entries.async_update_entry(entry, unique_id=serial)


async def options_update_listener(hass: HomeAssistant, entry: SajConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
