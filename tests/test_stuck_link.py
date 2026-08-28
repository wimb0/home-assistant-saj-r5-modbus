"""Tests for dropping a link that stops answering."""

from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection

from custom_components.saj_modbus.hub import _STUCK_AFTER_TIMEOUTS, SAJModbusHub


def make_hub(connection: MockModbusConnection) -> SAJModbusHub:
    """Build a hub on ``connection`` without running its connecting __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub._connection = connection
    hub._timeouts = 0
    return hub


async def test_one_timeout_keeps_the_link(
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """A single timeout is a slow reply, not a stuck link."""
    await mock_modbus_connection.connect()
    hub = make_hub(mock_modbus_connection)

    await hub._async_note_timeout()

    assert mock_modbus_connection.connected


async def test_repeated_timeouts_drop_the_link(
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """After enough timeouts the link is dropped so the next request reopens it."""
    await mock_modbus_connection.connect()
    hub = make_hub(mock_modbus_connection)

    for _ in range(_STUCK_AFTER_TIMEOUTS):
        await hub._async_note_timeout()

    assert not mock_modbus_connection.connected
    # Dropping is not closing: the connection still works.
    unit = mock_modbus_connection.for_unit(1)
    assert await unit.read_holding_registers(0x100, 1) == [0]
    assert mock_modbus_connection.connected


async def test_a_device_that_answers_nothing_times_out(
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """fail_requests models a device that is present but answers no request."""
    unit = mock_modbus_connection.for_unit(1)
    unit.fail_requests(ModbusTimeoutError("no reply"))

    try:
        await unit.read_holding_registers(0x100, 1)
    except ModbusTimeoutError:
        pass
    else:
        raise AssertionError("expected a timeout")
