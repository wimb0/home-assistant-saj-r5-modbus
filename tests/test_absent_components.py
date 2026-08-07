"""Tests for tolerating components the inverter does not serve."""

import pytest
from modbus_connection import BlockReadError

from custom_components.saj_modbus.hub import SAJModbusHub


def make_hub() -> SAJModbusHub:
    """Build a hub without running its Modbus-touching __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub._absent = set()
    return hub


def rejection(code: int) -> BlockReadError:
    """Build a rejection carrying ``code``."""
    return BlockReadError("holding", 0x1037, 1, code)


@pytest.mark.parametrize("code", [1, 2])
def test_structural_rejection_marks_block_absent(code: int) -> None:
    """Illegal function and illegal data address mean the registers are not there."""
    hub = make_hub()

    hub._note_absent("power", rejection(code))

    assert hub._absent == {"power"}


@pytest.mark.parametrize("code", [3, 4, 5, 6])
def test_transient_rejection_propagates(code: int) -> None:
    """Any other code is a failed read, not missing registers, and must not be hidden.

    Swallowing these would report a faulting or busy inverter as one that
    permanently lacks the registers.
    """
    hub = make_hub()
    err = rejection(code)

    with pytest.raises(BlockReadError) as raised:
        hub._note_absent("power", err)

    assert raised.value is err
    assert hub._absent == set()
