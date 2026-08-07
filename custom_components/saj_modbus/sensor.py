"""Sensor Platform Device for SAJ R5 Inverter Modbus."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    COUNTER_SENSOR_TYPES,
    SENSOR_TYPES,
    SajModbusSensorEntityDescription,
)
from .entity import SajEntity
from .hub import SajConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SajConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    hub = entry.runtime_data

    entities: list[SajSensor] = [
        SajSensor(hub, description) for description in SENSOR_TYPES.values()
    ]
    entities.extend(
        SajCounterSensor(hub, description)
        for description in COUNTER_SENSOR_TYPES.values()
    )

    async_add_entities(entities)


class SajSensor(SajEntity, SensorEntity):
    """Representation of an SAJ Modbus sensor."""

    entity_description: SajModbusSensorEntityDescription

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._value


class SajCounterSensor(SajSensor):
    """Representation of a SAJ Modbus counter sensor."""

    @property
    def native_value(self):
        """Return the value of the sensor."""
        if self.coordinator.device.realtime.mpvmode in (1, 2):
            return self._value
        return None
