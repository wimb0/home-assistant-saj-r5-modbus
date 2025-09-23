"""Number entity for SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    NUMBER_TYPES,
    SajModbusNumberEntityDescription,
)
from .hub import SAJModbusHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from a config entry."""
    # Retrieve the hub and device_info from the central runtime_data.
    hub: SAJModbusHub = entry.runtime_data["hub"]
    device_info = entry.runtime_data["device_info"]

    entities = [
        SajNumber(
            hub,
            device_info,
            description,
        )
        for description in NUMBER_TYPES.values()
    ]
    async_add_entities(entities)


class SajNumber(CoordinatorEntity[SAJModbusHub], NumberEntity):
    """Representation of an SAJ Modbus number."""

    entity_description: SajModbusNumberEntityDescription

    def __init__(
        self,
        hub: SAJModbusHub,
        device_info,
        description: SajModbusNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator=hub)
        self._attr_device_info = device_info
        self.entity_description = description
        self._attr_unique_id = f"{hub.name}_{description.key}"

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self.coordinator.name} {self.entity_description.name}"

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
        if self.coordinator.data:
            return self.coordinator.data.get(self.entity_description.key)
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value by calling the hub."""
        if self.entity_description.key == "limitpower":
            if not await self.coordinator.async_set_limit_power(value):
                await self.coordinator.async_request_refresh()
