"""Base entity for the SAJ Modbus integration."""

from __future__ import annotations

from collections.abc import Iterable

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


def served(
    hub: SAJModbusHub, descriptions: Iterable[SajEntityDescription]
) -> list[SajEntityDescription]:
    """Drop the descriptions that read a component this inverter does not serve."""
    return [
        description
        for description in descriptions
        if description.component not in hub.absent_components
    ]


class SajEntity(CoordinatorEntity[SAJModbusHub]):
    """An entity reading one value off the inverter."""

    _attr_has_entity_name = True
    entity_description: SajEntityDescription

    def __init__(self, hub: SAJModbusHub, description: SajEntityDescription) -> None:
        """Initialize the entity."""
        super().__init__(coordinator=hub)
        self.entity_description = description
        self._attr_device_info = hub.device_info
        self._attr_unique_id = f"{hub.identifier}_{description.key}"

    @property
    def available(self) -> bool:
        """Whether the last poll refreshed the value behind this entity.

        A poll that failed, either wholly or only in this entity's component,
        leaves values that are not worth publishing as if they were current.
        """
        if self.entity_description.always_available:
            # So an accumulator never reads unavailable, and holds its last
            # value even if the device is gone for good. That is the trade:
            # statistics continuity beats liveness signalling for a counter,
            # and whether the inverter is reachable belongs on a connectivity
            # or diagnostic entity, not on its lifetime yield.
            return True
        return (
            super().available
            and self.entity_description.component
            not in self.coordinator.failed_components
        )

    @property
    def _value(self):
        """This entity's value, read straight off the device model."""
        return self.entity_description.value_fn(self.coordinator)
