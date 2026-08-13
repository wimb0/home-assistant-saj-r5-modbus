"""Sensor Platform Device for SAJ R5 Inverter Modbus."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import RestoreSensor
from homeassistant.core import HomeAssistant, callback
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


class SajSensor(SajEntity, RestoreSensor):
    """Representation of an SAJ Modbus sensor."""

    entity_description: SajModbusSensorEntityDescription

    @property
    def available(self) -> bool:
        """A total stays available even when nothing answered the poll."""
        return self.entity_description.is_total or super().available

    async def async_added_to_hass(self) -> None:
        """Seed a total from the state it had before the restart."""
        await super().async_added_to_hass()
        if (
            self.entity_description.is_total
            and (last_data := await self.async_get_last_sensor_data()) is not None
        ):
            self._attr_native_value = last_data.native_value
        self._process_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Take this poll's value before publishing the state."""
        self._process_data()
        super()._handle_coordinator_update()

    def _process_data(self) -> None:
        """Store what the device now reads, unless a total reads nothing."""
        value = self._value
        if value is not None or not self.entity_description.is_total:
            self._attr_native_value = value


class SajCounterSensor(SajSensor):
    """Representation of a SAJ Modbus counter sensor."""

    def _process_data(self) -> None:
        """Take a new value only while the inverter is generating.

        These registers only read true in those modes, and every counter here
        is a running total: following them outside would blank each one every
        night, leaving the same hole in its long-term statistics that going
        unavailable would.
        """
        if self.coordinator.device.realtime.mpvmode in (1, 2):
            super()._process_data()
