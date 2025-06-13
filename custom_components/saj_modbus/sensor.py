"""Sensor Platform Device for SAJ R5 Inverter Modbus."""

from __future__ import annotations
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
import logging

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry

from .const import (
    ATTR_MANUFACTURER,
    COUNTER_SENSOR_TYPES,
    DOMAIN,
    SENSOR_TYPES,
    SajModbusSensorEntityDescription,
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
    for sensor_description in SENSOR_TYPES.values():
        sensor = SajSensor(
            hub_name,
            hub,
            device_info,
            sensor_description,
        )
        entities.append(sensor)
    for sensor_description in COUNTER_SENSOR_TYPES.values():
        sensor = SajCounterSensor(
            hub_name,
            hub,
            device_info,
            sensor_description,
        )
        entities.append(sensor)

    async_add_entities(entities)
    return True


class SajSensor(CoordinatorEntity, SensorEntity):
    """Representation of an SAJ Modbus sensor."""

    _attr_has_entity_name = True
    entity_description: SajModbusSensorEntityDescription

    def __init__(
        self,
        platform_name: str,
        hub: SAJModbusHub,
        device_info: DeviceInfo,
        description: SajModbusSensorEntityDescription,
    ):
        """Initialize the sensor."""
        self._attr_device_info = device_info
        self.entity_description = description
        self._attr_unique_id = f"{platform_name}_{self.entity_description.key}"
        super().__init__(coordinator=hub)

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key, None)


class SajCounterSensor(SajSensor):
    """Representation of a SAJ Modbus counter sensor."""

    @property
    def native_value(self):
        """Return the value of the sensor."""
        # When the inverter working mode is not "Waiting" or "Normal",
        # the values returned by the inverter are not reliable.
        if self.coordinator.data.get("mpvmode") in (1, 2):  # "Waiting" or "Normal"
            return self.coordinator.data.get(self.entity_description.key)
        return None
