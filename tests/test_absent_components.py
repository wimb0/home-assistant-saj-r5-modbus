"""Tests for tolerating components the inverter does not serve."""

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import (
    AcknowledgeError,
    IllegalDataAddressError,
    IllegalDataValueError,
    IllegalFunctionError,
    ModbusExceptionError,
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.inverter import SajR5Inverter

POWER_REGISTER = 0x1037


def make_hub(unit: MockModbusUnit, connection: MockModbusConnection) -> SAJModbusHub:
    """Build a hub on ``unit`` without running its connecting __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub.device = SajR5Inverter(unit)
    hub._connection = connection
    hub._absent = set()
    hub._info_read = False
    hub._timeouts = 0
    return hub


@pytest.fixture
def hub(
    mock_modbus_connection: MockModbusConnection,
    mock_modbus_unit: MockModbusUnit,
    info_registers: dict,
    realtime_registers: dict,
) -> SAJModbusHub:
    """Return a hub whose inverter answers every register."""
    mock_modbus_unit.holding.update(info_registers)
    mock_modbus_unit.holding.update(realtime_registers)
    return make_hub(mock_modbus_unit, mock_modbus_connection)


@pytest.mark.parametrize(
    "error",
    [IllegalFunctionError(), IllegalDataAddressError()],
    ids=lambda e: type(e).__name__,
)
async def test_structural_refusal_is_tolerated(
    hub: SAJModbusHub, mock_modbus_unit: MockModbusUnit, error: ModbusExceptionError
) -> None:
    """A refusal that means "not in my map" costs the switch, not the poll."""
    mock_modbus_unit.fail_read(POWER_REGISTER, error)

    await hub._async_update_data()

    assert hub._absent == {"power"}
    assert hub.poweronoff is None
    # The rest of the poll still landed.
    assert hub.device.realtime.pv1volt == 305.0


@pytest.mark.parametrize(
    "error",
    [
        IllegalDataValueError(),
        ServerDeviceFailureError(),
        AcknowledgeError(),
        ServerDeviceBusyError(),
    ],
    ids=lambda e: type(e).__name__,
)
async def test_transient_refusal_fails_the_poll(
    hub: SAJModbusHub, mock_modbus_unit: MockModbusUnit, error: ModbusExceptionError
) -> None:
    """A transient refusal must not be recorded as missing registers.

    Hiding it would report a faulting or busy inverter as one that
    permanently lacks the registers.
    """
    mock_modbus_unit.fail_read(POWER_REGISTER, error)

    with pytest.raises(UpdateFailed):
        await hub._async_update_data()

    assert hub._absent == set()


async def test_an_absent_component_is_not_read_again(
    hub: SAJModbusHub, mock_modbus_unit: MockModbusUnit
) -> None:
    """Once the inverter has refused the registers, stop asking for them."""
    mock_modbus_unit.fail_read(POWER_REGISTER, IllegalDataAddressError())
    await hub._async_update_data()

    mock_modbus_unit.read_events.clear()
    await hub._async_update_data()

    reads = [event.address for event in mock_modbus_unit.read_events]
    assert POWER_REGISTER not in reads
