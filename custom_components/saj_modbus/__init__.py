"""The SAJ Modbus Integration."""

import logging

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType
from modbus_connection import ModbusError

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

    try:
        await hub.async_setup()
    except ModbusError as err:
        raise ConfigEntryNotReady(f"Could not reach the inverter: {err}") from err

    await hub.async_config_entry_first_refresh()
    _async_migrate_to_serial_identity(hass, entry, hub)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SajConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _async_migrate_to_serial_identity(
    hass: HomeAssistant, entry: SajConfigEntry, hub: SAJModbusHub
) -> None:
    """Rebuild this entry's identity around the inverter's serial number.

    Identity was originally derived from the host (config entry) and the
    user-chosen name (device and entities), so renaming the integration or
    moving the inverter to a new address orphaned everything. Runs before the
    platforms are set up so entities register under their new unique ids.

    The migration is best-effort: a registry collision leaves the affected
    entity or device on its old identity rather than failing setup.
    """
    serial = hub.serial_number
    if serial is None:
        # The info block was not readable, so identity stays name-based for
        # this session; a later reload that reads it migrates then.
        return

    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    if name != serial:
        registry = er.async_get(hass)
        old_prefix = f"{name}_"
        for registry_entry in er.async_entries_for_config_entry(
            registry, entry.entry_id
        ):
            if not registry_entry.unique_id.startswith(old_prefix):
                continue
            new_unique_id = (
                f"{serial}_{registry_entry.unique_id.removeprefix(old_prefix)}"
            )
            # A second entry pointing at the same inverter would collide here,
            # and async_update_entity raises on a duplicate — which inside
            # setup would put the entry into a permanent error state.
            if registry.async_get_entity_id(
                registry_entry.domain, DOMAIN, new_unique_id
            ):
                _LOGGER.warning(
                    "Not migrating %s to unique id %s: already in use",
                    registry_entry.entity_id,
                    new_unique_id,
                )
                continue
            registry.async_update_entity(
                registry_entry.entity_id, new_unique_id=new_unique_id
            )

        device_registry = dr.async_get(hass)
        for device in dr.async_entries_for_config_entry(
            device_registry, entry.entry_id
        ):
            if (DOMAIN, name) not in device.identifiers:
                continue
            try:
                device_registry.async_update_device(
                    device.id, new_identifiers={(DOMAIN, serial)}
                )
            except HomeAssistantError as err:
                _LOGGER.warning("Not migrating device %s: %s", device.id, err)
            break

    hub.freeze_identity()

    if entry.unique_id != serial:
        hass.config_entries.async_update_entry(entry, unique_id=serial)


async def options_update_listener(hass: HomeAssistant, entry: SajConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
