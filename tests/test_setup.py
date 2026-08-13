"""End-to-end setup of the integration inside Home Assistant."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.saj_modbus.const import DOMAIN
from custom_components.saj_modbus.inverter import UNIT_ID

MPVMODE_REGISTER = 0x100


@pytest.fixture
def mock_connection(info_registers: dict, realtime_registers: dict):
    """Serve the inverter's registers wherever the hub opens a connection."""
    connection = MockModbusConnection()
    unit = connection.for_unit(UNIT_ID)
    unit.holding.update(info_registers)
    unit.holding.update(realtime_registers)
    with patch(
        "custom_components.saj_modbus.hub.create_connection", return_value=connection
    ):
        yield connection


async def test_setup_entry(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_connection: MockModbusConnection,
    serial: str,
) -> None:
    """Set the integration up against a mocked inverter and read a sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_HOST: "192.168.1.10", CONF_PORT: 502, CONF_NAME: "SAJ"},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert len(entities) > 50

    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_totalenergy")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "78910.11"


async def test_a_total_restores_its_value_across_a_restart(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    mock_connection: MockModbusConnection,
    serial: str,
) -> None:
    """Restarting at night must not leave the counters unknown until dawn.

    The energy registers only read true while the inverter generates, so a
    restart while it is idle has nothing to publish and the value has to come
    back from the state machine instead.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_HOST: "192.168.1.10", CONF_PORT: 502, CONF_NAME: "SAJ"},
    )
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{serial}_totalenergy",
        config_entry=entry,
        suggested_object_id="saj_total_energy",
    )
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("sensor.saj_total_energy", "12345.6"),
                {"native_value": 12345.6, "native_unit_of_measurement": "kWh"},
            ),
        ),
    )
    # Not Connected: the DC side is down for the night.
    mock_connection.for_unit(UNIT_ID).holding[MPVMODE_REGISTER] = 0

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.saj_total_energy")
    assert state is not None
    assert state.state == "12345.6"
