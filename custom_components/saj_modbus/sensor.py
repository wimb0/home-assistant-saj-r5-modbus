"""Sensor Platform Device for SAJ R5 Inverter Modbus."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    COUNTER_SENSOR_TYPES,
    SENSOR_TYPES,
    SajModbusSensorEntityDescription,
)
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    # Retrieve the hub and device_info from the central runtime_data.
    hub: SAJModbusHub = entry.runtime_data["hub"]
    device_info = entry.runtime_data["device_info"]

    entities = []
    for sensor_description in SENSOR_TYPES.values():
        entities.append(SajSensor(hub, device_info, sensor_description))
    for sensor_description in COUNTER_SENSOR_TYPES.values():
        entities.append(SajCounterSensor(hub, device_info, sensor_description))

    async_add_entities(entities)


class SajSensor(CoordinatorEntity[SAJModbusHub], SensorEntity):
    """Representation of an SAJ Modbus sensor."""

    entity_description: SajModbusSensorEntityDescription

    def __init__(
        self,
        hub: SAJModbusHub,
        device_info,
        description: SajModbusSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=hub)
        self._attr_device_info = device_info
        self.entity_description = description
        self._attr_unique_id = f"{hub.name}_{self.entity_description.key}"

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self.coordinator.name} {self.entity_description.name}"

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key, None)


class SajCounterSensor(SajSensor):
    """Representation of a SAJ Modbus counter sensor."""

    @property
    def native_value(self):
        """Return the value of the sensor."""
        if self.coordinator.data and self.coordinator.data.get("mpvmode") in (1, 2):
            return self.coordinator.data.get(self.entity_description.key)
        return None
