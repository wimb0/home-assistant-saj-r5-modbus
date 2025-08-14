"""Sensor Platform Device for SAJ R5 Inverter Modbus."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
import logging

from .const import DOMAIN, SENSOR_TYPES, SajModbusSensorEntityDescription
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up SAJ sensors from a config entry."""
    hub: SAJModbusHub = hass.data[DOMAIN][entry.entry_id]["hub"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    
    entities = []
    for description in SENSOR_TYPES.values():
        entity = SajSensor(hub, device_info, description)
        entities.append(entity)

    async_add_entities(entities)
    _LOGGER.info(f"Added {len(entities)} SAJ sensors")

class SajSensor(CoordinatorEntity, SensorEntity):
    """Representation of an SAJ Modbus sensor."""

    def __init__(self, hub: SAJModbusHub, device_info: dict, description: SajModbusSensorEntityDescription):
        """Initialize the sensor."""
        super().__init__(coordinator=hub)
        self.entity_description = description
        self._attr_device_info = device_info
        self._attr_unique_id = f"{hub.name}_{description.key}"
        self._attr_name = f"{hub.name} {description.name}"
        self._attr_entity_registry_enabled_default = description.entity_registry_enabled_default
        self._attr_force_update = description.force_update

    @property
    def native_last_reset_time(self):
        """Return the time when the sensor was last reset, if applicable."""
        if self.entity_description.state_class == SensorStateClass.TOTAL:
            now = dt_util.utcnow()
            if self.entity_description.reset_period == "daily":
                return now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif self.entity_description.reset_period == "monthly":
                return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif self.entity_description.reset_period == "yearly":
                return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            _LOGGER.debug(f"No data for sensor {self._attr_name}")
        return value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

        #_LOGGER.debug(f"Sensor {self._attr_name} added to Home Assistant")
