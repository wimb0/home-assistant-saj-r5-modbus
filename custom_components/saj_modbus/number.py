"""Number entity for SAJ Modbus integration."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import (
    ATTR_MANUFACTURER,
    DOMAIN,
    NUMBER_TYPES,
    SajModbusNumberEntityDescription,
)
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up entry for hub."""
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = DeviceInfo(
        identifiers={(DOMAIN, hub_name)},
        name=hub_name,
        manufacturer=ATTR_MANUFACTURER,
    )

    entities = []
    for number_description in NUMBER_TYPES.values():
        number = SajNumber(
            hub_name,
            hub,
            device_info,
            number_description,
        )
        entities.append(number)

    async_add_entities(entities)
    return True


class SajNumber(CoordinatorEntity, NumberEntity):
    """Representation of an SAJ Modbus number."""

    _attr_has_entity_name = True
    coordinator: SAJModbusHub
    entity_description: SajModbusNumberEntityDescription

    def __init__(
        self,
        platform_name: str,
        hub: SAJModbusHub,
        device_info: DeviceInfo,
        description: SajModbusNumberEntityDescription,
    ):
        """Initialize the sensor."""
        self._attr_device_info = device_info
        self._attr_unique_id = f"{platform_name}_{description.key}"
        self.entity_description = description
        super().__init__(coordinator=hub)

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self.native_value is not None

    @property
    def native_value(self) -> float | None:
        """Return the state of the number entity."""
        return self.coordinator.data.get(self.entity_description.key, None)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.hass.async_add_executor_job(
            self.coordinator.set_value, self.entity_description.key, value
        )
