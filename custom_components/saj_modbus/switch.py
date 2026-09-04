"""Switch entity for SAJ Modbus integration."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    SWITCH_TYPES,
    SajModbusSwitchEntityDescription,
)
from .entity import SajEntity, served
from .hub import SajConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SajConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from a config entry."""
    hub = entry.runtime_data

    entities = [
        SajSwitch(hub, description)
        for description in served(hub, SWITCH_TYPES.values())
    ]
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
        await self._async_switch(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_switch(False)

    async def _async_switch(self, value: bool) -> None:
        """Write the new power state, then read back what the inverter did.

        A write that raises nothing is not proof the inverter took it: a
        discarded write sends no exception response. Only a read tells us the
        real state, so always refresh.
        """
        await self.coordinator.async_set_power_on_off(value)
        await self.coordinator.async_request_refresh()
