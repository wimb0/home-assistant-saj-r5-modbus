"""Tests for tolerating components the inverter does not serve."""

import pytest
from modbus_connection import (
    AcknowledgeError,
    IllegalDataAddressError,
    IllegalDataValueError,
    IllegalFunctionError,
    ModbusExceptionError,
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)

from custom_components.saj_modbus.hub import SAJModbusHub


def make_hub() -> SAJModbusHub:
    """Build a hub without running its Modbus-touching __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub._absent = set()
    return hub


@pytest.mark.parametrize(
    "error",
    [IllegalFunctionError(), IllegalDataAddressError()],
    ids=lambda e: type(e).__name__,
)
def test_structural_rejection_marks_component_absent(
    error: ModbusExceptionError,
) -> None:
    """Illegal function and illegal data address mean the registers are not there."""
    hub = make_hub()

    hub._note_absent("power", error)

    assert hub._absent == {"power"}


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
def test_transient_rejection_propagates(error: ModbusExceptionError) -> None:
    """Any other code is a failed read, not missing registers, and must not be hidden.

    Swallowing these would report a faulting or busy inverter as one that
    permanently lacks the registers.
    """
    hub = make_hub()

    with pytest.raises(ModbusExceptionError) as raised:
        hub._note_absent("power", error)

    assert raised.value is error
    assert hub._absent == set()
