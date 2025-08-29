"""Test the SAJ Modbus sensor platform."""
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_modbus.const import DOMAIN
from .const import MOCK_CONFIG


async def test_sensors_created(
    hass: HomeAssistant, mock_saj_modbus_hub: AsyncMock
) -> None:
    """Test if all sensors are created with correct states."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="test-entry",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)

    # Test for a regular sensor
    sensor_power = entity_registry.async_get("sensor.saj_active_power_of_inverter_total_output")
    assert sensor_power
    state = hass.states.get(sensor_power.entity_id)
    assert state
    assert state.state == "2811"

    # Test for a counter sensor
    sensor_today_energy = entity_registry.async_get("sensor.saj_power_generation_on_current_day")
    assert sensor_today_energy
    state = hass.states.get(sensor_today_energy.entity_id)
    assert state
    assert state.state == "10.5"
