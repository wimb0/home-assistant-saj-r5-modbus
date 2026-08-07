"""Base entity for the SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    SajModbusNumberEntityDescription,
    SajModbusSensorEntityDescription,
    SajModbusSwitchEntityDescription,
)
from .hub import SAJModbusHub

type SajEntityDescription = (
    SajModbusSensorEntityDescription
    | SajModbusNumberEntityDescription
    | SajModbusSwitchEntityDescription
)


class SajEntity(CoordinatorEntity[SAJModbusHub]):
    """An entity reading one value off the inverter."""

    _attr_has_entity_name = True

    def __init__(self, hub: SAJModbusHub, description: SajEntityDescription) -> None:
        """Initialize the entity."""
        super().__init__(coordinator=hub)
        self.entity_description = description
        self._attr_device_info = hub.device_info
        self._attr_unique_id = f"{hub.identifier}_{description.key}"

    @property
    def _value(self):
        """This entity's value, read straight off the device model."""
        return self.entity_description.value_fn(self.coordinator)
