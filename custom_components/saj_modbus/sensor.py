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
from .entity import SajEntity, served
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
        SajSensor(hub, description)
        for description in served(hub, SENSOR_TYPES.values())
    ]
    entities.extend(
        SajCounterSensor(hub, description)
        for description in served(hub, COUNTER_SENSOR_TYPES.values())
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

    _last_value = None

    @property
    def native_value(self):
        """Return the value of the sensor.

        These registers only read true while the inverter is generating, and
        every counter here is a running total: publishing nothing outside
        those modes would blank each one every night, which leaves the same
        hole in its long-term statistics that going unavailable would. So the
        last generated value stands until the inverter generates again.
        """
        if self.coordinator.device.realtime.mpvmode in (1, 2):
            self._last_value = self._value
        return self._last_value
