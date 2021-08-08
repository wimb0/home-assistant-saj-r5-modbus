from homeassistant.components.sensor import SensorEntity
import logging
from typing import Optional

from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.util.dt as dt_util

from .const import ATTR_MANUFACTURER, DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    hub_name = entry.data[CONF_NAME]
    hub = hass.data[DOMAIN][hub_name]["hub"]

    device_info = {
        "identifiers": {(DOMAIN, hub_name)},
        "name": hub_name,
        "manufacturer": ATTR_MANUFACTURER,
    }

    entities = []
    for sensor_info in SENSOR_TYPES.values():
        sensor = SajSensor(
            hub_name,
            hub,
            device_info,
            sensor_info[0],
            sensor_info[1],
            sensor_info[2],
            sensor_info[3],
            sensor_info[4],
            sensor_info[5] if len(sensor_info) > 5 else None,
            sensor_info[6] if len(sensor_info) > 6 else None,
        )
        entities.append(sensor)

    async_add_entities(entities)
    return True


class SajSensor(SensorEntity):
    """Representation of an SAJ Modbus sensor."""

    def __init__(
        self,
        platform_name,
        hub,
        device_info,
        name,
        key,
        unit,
        icon,
        device_class,
        state_class,
        last_reset,
    ):
        """Initialize the sensor."""
        self._platform_name = platform_name
        self._hub = hub
        self._key = key
        self._name = name
        self._attr_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_device_info = device_info
        self._attr_state_class = state_class

        if last_reset == "today":
            self._attr_last_reset = (
                dt_util.now().today().replace(hour=0, minute=0, second=0, microsecond=0)
            )
        elif last_reset:
            self._attr_last_reset = dt_util.utc_from_timestamp(0)

        self._attr_should_poll = False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self._hub.async_add_saj_sensor(self._modbus_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._hub.async_remove_saj_sensor(self._modbus_data_updated)

    @callback
    def _modbus_data_updated(self):
        self.async_write_ha_state()

    @callback
    def _update_state(self):
        if self._key in self._hub.data:
            self._state = self._hub.data[self._key]

    @property
    def name(self):
        """Return the name."""
        return f"{self._platform_name} {self._name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self._key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._key in self._hub.data:
            return self._hub.data[self._key]
