"""Base entity for the SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .hub import SAJModbusHub


class SajEntity(CoordinatorEntity[SAJModbusHub]):
    """An entity backed by one key of the coordinator's data."""

    _attr_has_entity_name = True

    def __init__(self, hub: SAJModbusHub, description: EntityDescription) -> None:
        """Initialize the entity."""
        super().__init__(coordinator=hub)
        self.entity_description = description
        self._attr_device_info = hub.device_info
        self._attr_unique_id = f"{hub.identifier}_{description.key}"

    @property
    def _value(self):
        """The coordinator's value for this entity's key."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.entity_description.key)
