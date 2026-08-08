"""Tests that every entity description resolves against the device model."""

import pytest

from custom_components.saj_modbus.const import (
    COUNTER_SENSOR_TYPES,
    NUMBER_TYPES,
    SENSOR_TYPES,
    SWITCH_TYPES,
)
from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.inverter import SajR5Inverter

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
