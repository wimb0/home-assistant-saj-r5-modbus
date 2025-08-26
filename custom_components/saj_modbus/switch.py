"""Switch entity for SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    SWITCH_TYPES,
    SajModbusSwitchEntityDescription,
)
from .hub import SAJModbusHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    hub: SAJModbusHub = entry.runtime_data["hub"]
    device_info = entry.runtime_data["device_info"]

    entities = [
        SajSwitch(
            hub,
            device_info,
            description,
        )
        for description in SWITCH_TYPES.values()
    ]
    async_add_entities(entities)


class SajSwitch(CoordinatorEntity[SAJModbusHub], SwitchEntity):
    """Representation of an SAJ Modbus switch."""

    entity_description: SajModbusSwitchEntityDescription

    def __init__(
        self,
        hub: SAJModbusHub,
        device_info,
        description: SajModbusSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator=hub)
        self._attr_device_info = device_info
        self.entity_description = description
        self._attr_unique_id = f"{hub.name}_{description.key}"

    @property
    def name(self) -> str:
        """Return the name."""
        return f"{self.coordinator.name} {self.entity_description.name}"

    @property
    def is_on(self) -> bool | None:
        """Return the state of the switch."""
        if self.coordinator.data:
            return self.coordinator.data.get(self.entity_description.key)
        return None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        if not await self.coordinator.async_set_power_on_off(True):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        if not await self.coordinator.async_set_power_on_off(False):
            await self.coordinator.async_request_refresh()
