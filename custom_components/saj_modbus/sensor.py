"""Sensor Platform Device for SAJ R5 Inverter Modbus."""

from __future__ import annotations
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging

from .const import (
    ATTR_MANUFACTURER,
    COUNTER_SENSOR_TYPES,
    DOMAIN,
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
    hub: SAJModbusHub = entry.runtime_data
    
    device_info = {
        "identifiers": {(DOMAIN, entry.data[CONF_NAME])},
        "name": entry.data[CONF_NAME],
        "manufacturer": ATTR_MANUFACTURER,
    }

    entities = []
    for sensor_description in SENSOR_TYPES.values():
        sensor = SajSensor(
            hub,
            device_info,
            sensor_description,
        )
        entities.append(sensor)
    for sensor_description in COUNTER_SENSOR_TYPES.values():
        sensor = SajCounterSensor(
            hub,
            device_info,
            sensor_description,
        )
        entities.append(sensor)

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
