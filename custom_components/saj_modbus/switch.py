"""Switch entity for SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    SWITCH_TYPES,
    SajModbusSwitchEntityDescription,
)
from .entity import SajEntity
from .hub import SajConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SajConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    hub = entry.runtime_data

    entities = [SajSwitch(hub, description) for description in SWITCH_TYPES.values()]
    async_add_entities(entities)


class SajSwitch(SajEntity, SwitchEntity):
    """Representation of an SAJ Modbus switch."""

    entity_description: SajModbusSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the state of the switch."""
        return self._value

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        if not await self.coordinator.async_set_power_on_off(True):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        if not await self.coordinator.async_set_power_on_off(False):
            await self.coordinator.async_request_refresh()
