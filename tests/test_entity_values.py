"""Tests that every entity description resolves against the device model."""

import pytest
from modbus_connection.mock import MockModbusUnit

from custom_components.saj_modbus.const import (
    COUNTER_SENSOR_TYPES,
    NUMBER_TYPES,
    SENSOR_TYPES,
    SWITCH_TYPES,
)
from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.inverter import SajR5Inverter
from custom_components.saj_modbus.sensor import SajCounterSensor

MPVMODE_REGISTER = 0x100

ALL_DESCRIPTIONS = [
    description
    for descriptions in (SENSOR_TYPES, COUNTER_SENSOR_TYPES, NUMBER_TYPES, SWITCH_TYPES)
    for description in descriptions.values()
]


def make_hub(device: SajR5Inverter) -> SAJModbusHub:
    """Build a hub around ``device`` without running its connecting __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub.device = device
    hub.name = "SAJ"
    hub._identifier = "SAJ"
    hub._power_limit = 110.0
    return hub


@pytest.fixture
async def hub(device: SajR5Inverter) -> SAJModbusHub:
    """Return a hub whose components have all been read."""
    await device.info.async_update()
    await device.realtime.async_update()
    await device.power.async_update()
    return make_hub(device)


@pytest.mark.parametrize("description", ALL_DESCRIPTIONS, ids=lambda d: d.key)
def test_value_fn_resolves(description, hub: SAJModbusHub) -> None:
    """Every description reads a value without raising.

    The value functions name attributes on the device model, which no type
    checker verifies — a typo would otherwise only surface at runtime.
    """
    description.value_fn(hub)


def test_every_description_has_a_value_fn() -> None:
    """No description may be added without one."""
    assert all(callable(d.value_fn) for d in ALL_DESCRIPTIONS)


def test_values_match_the_device_model(hub: SAJModbusHub) -> None:
    """Spot-check that descriptions read the value they name."""
    values = {d.key: d.value_fn(hub) for d in ALL_DESCRIPTIONS}

    assert values["pv1volt"] == 305.0
    assert values["totalenergy"] == 78910.11
    assert values["invtempc"] == -1.0
    assert values["sn"] == "R5-3K-S2SN01"
    assert values["mpvmode"] == 2
    # Derived on the hub rather than read from a register.
    assert values["mpvstatus"] == "Normal"
    assert values["faultmsg"] == "Code 01: Master Relay Error"
    assert values["poweronoff"] is True
    assert values["limitpower"] == 110.0


async def test_a_counter_holds_its_value_when_generation_stops(
    hub: SAJModbusHub, mock_modbus_unit: MockModbusUnit
) -> None:
    """Dusk moves the inverter out of its generating modes every day.

    The counters read true only while it generates, so they are not read
    again until it does -- publishing nothing would gap their statistics.
    """
    sensor = SajCounterSensor(hub, COUNTER_SENSOR_TYPES["TotalEnergy"])
    sensor._process_data()
    assert sensor.native_value == 78910.11

    # Not Connected: the DC side is down for the night.
    mock_modbus_unit.holding[MPVMODE_REGISTER] = 0
    await hub.device.realtime.async_update()
    sensor._process_data()

    assert sensor.native_value == 78910.11
