from __future__ import annotations
from datetime import datetime
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
import logging
from typing import Optional

from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.util.dt as dt_util

from .const import (
    ATTR_MANUFACTURER,
    DOMAIN,
    SENSOR_TYPES,
    SajModbusSensorEntityDescription,
)

from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
    }

    entities = []
    for sensor_description in SENSOR_TYPES.values():
        sensor = SajSensor(
            hub_name,
            hub,
            device_info,
            sensor_description,
        )
        entities.append(sensor)

    async_add_entities(entities)
    return True


class SajSensor(CoordinatorEntity, SensorEntity):
    """Representation of an SAJ Modbus sensor."""

    def __init__(
        self,
        platform_name: str,
        hub: SAJModbusHub,
        device_info,
        description: SajModbusSensorEntityDescription,
    ):
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._attr_device_info = device_info
        self.entity_description: SajModbusSensorEntityDescription = description

        super().__init__(coordinator=hub)

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.coordinator.async_add_listener(self._modbus_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self.coordinator.async_remove_listener(self._modbus_data_updated)

    @callback
    def _modbus_data_updated(self):
        self._attr_state = (
            self.coordinator.data[self.entity_description.key]
            if self.entity_description.key in self.coordinator.data
            else None
        )
        self.async_write_ha_state()

    @property
    def name(self):
        """Return the name."""
        return f"{self._platform_name} {self.entity_description.name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self.entity_description.key}"

    @property
    def last_reset(self) -> datetime | None:

        if self.entity_description.set_last_reset_today:
            return (
                dt_util.now().today().replace(hour=0, minute=0, second=0, microsecond=0)
            )
        elif self.entity_description.set_last_reset:
            return dt_util.utc_from_timestamp(0)
        return None
