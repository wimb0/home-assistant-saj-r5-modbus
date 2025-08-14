"""Number entity for SAJ Modbus integration."""

import logging
import asyncio
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up SAJ number entities."""
    hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]

    entities = [
        SajExportLimitInputEntity(hub, device_info)
    ]

    async_add_entities(entities)

class SajNumberEntity(NumberEntity):
    """Base class for SAJ writable number entities."""
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hub, name, unique_id, min_val, max_val, step, default, device_info, unit=None):
        self._hub = hub
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_value = default
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = device_info

    @property
    def native_value(self):
        return self._attr_native_value
