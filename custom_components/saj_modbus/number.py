"""Number entity for SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    NUMBER_TYPES,
    SajModbusNumberEntityDescription,
)
from .entity import SajEntity
from .hub import SajConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SajConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    hub = entry.runtime_data

    entities = [SajNumber(hub, description) for description in NUMBER_TYPES.values()]
    async_add_entities(entities)


class SajNumber(SajEntity, NumberEntity):
    """Representation of an SAJ Modbus number."""

    entity_description: SajModbusNumberEntityDescription

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.key in self.coordinator.data
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the number entity."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value by calling the hub."""
        if self.entity_description.key == "limitpower":
            if not await self.coordinator.async_set_limit_power(value):
                await self.coordinator.async_request_refresh()
