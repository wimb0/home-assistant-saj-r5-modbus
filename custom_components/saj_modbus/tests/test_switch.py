"""Test the SAJ Modbus switch platform."""
from unittest.mock import AsyncMock, call

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_modbus.const import DOMAIN
from custom_components.saj_modbus.hub import SAJModbusHub
from .const import MOCK_CONFIG


@pytest.mark.parametrize(
    ("service", "expected_hub_call"),
    [
        (SERVICE_TURN_ON, call.async_set_power_on_off(True)),
        (SERVICE_TURN_OFF, call.async_set_power_on_off(False)),
    ],
)
async def test_switch_services(
    hass: HomeAssistant,
    mock_saj_modbus_hub: AsyncMock,
    service: str,
    expected_hub_call: call,
) -> None:
    """Test switch services."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="test-entry",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    switch_entity = entity_registry.async_get("switch.saj_power_on_off")
    assert switch_entity

    # Manually enable the entity
    entity_registry.async_update_entity(switch_entity.entity_id, disabled_by=None)
    await hass.async_block_till_done()

    state = hass.states.get(switch_entity.entity_id)
    assert state
    assert state.state == "on"

    # Call the service
    await hass.services.async_call(
        SWITCH_DOMAIN,
        service,
        {ATTR_ENTITY_ID: switch_entity.entity_id},
        blocking=True,
    )

    # Check that the correct hub method was called
    assert expected_hub_call in SAJModbusHub.instance.mock_calls
