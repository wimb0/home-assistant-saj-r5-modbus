"""Test the SAJ Modbus number platform."""
from unittest.mock import AsyncMock, call

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_modbus.const import DOMAIN
from custom_components.saj_modbus.hub import SAJModbusHub
from .const import MOCK_CONFIG


async def test_number_set_value(
    hass: HomeAssistant, mock_saj_modbus_hub: AsyncMock
) -> None:
    """Test the number entity's set_value service."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="test-entry",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    number_entity = entity_registry.async_get("number.saj_limit_power")
    assert number_entity

    state = hass.states.get(number_entity.entity_id)
    assert state
    assert state.state == "110.0"

    # Call the service to set a new value
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number_entity.entity_id, "value": 80.0},
        blocking=True,
    )

    # Check that the correct hub method was called
    assert call.async_set_limit_power(80.0) in SAJModbusHub.instance.mock_calls
