"""The SAJ Modbus Integration."""

import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .hub import SAJModbusHub
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

SAJ_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: SAJ_MODBUS_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = ["sensor", "number"]


async def async_setup(hass, config):
    """Set up the SAJ modbus component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a SAJ mobus."""
    hass.data.setdefault(DOMAIN, {})
    
    host = entry.data.get(CONF_HOST)
    name = entry.data.get(CONF_NAME)
    port = entry.data.get(CONF_PORT)
    scan_interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = timedelta(seconds=scan_interval_seconds)

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    _LOGGER.debug("host is %s, port is %s and scan_interval %s seconds", host, port, scan_interval)

    hub = SAJModbusHub(hass, name, host, port, scan_interval)
    await hub.async_config_entry_first_refresh()

    """Register the hub."""
    hass.data[DOMAIN][name] = {"hub": hub}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload SAJ modbus entry."""

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        hass.config_entries.async_update_entry(config_entry, version=2)

        entity_registry = er.async_get(hass)
        existing_entries = er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )

        for entry in list(existing_entries):
            _LOGGER.debug("Deleting version 1 entity: %s", entry.entity_id)
            entity_registry.async_remove(entry.entity_id)

    _LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
