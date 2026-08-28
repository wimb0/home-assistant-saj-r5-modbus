"""Tests for the coordinator's pure helpers."""

from custom_components.saj_modbus.const import FAULT_MESSAGES
from custom_components.saj_modbus.hub import translate_fault_code_to_messages


def test_translate_fault_code_to_messages() -> None:
    """Set bits translate to their fault messages."""
    assert translate_fault_code_to_messages(0, FAULT_MESSAGES[0]) == []
    assert translate_fault_code_to_messages(0x00000001, FAULT_MESSAGES[1]) == [
        "Code 01: Master Relay Error"
    ]
    assert translate_fault_code_to_messages(
        0x80000000 | 0x00000001, FAULT_MESSAGES[0]
    ) == [
        "Code 81: Lost Communication D<->C",
        "Code 33: Master Bus Voltage High",
    ]
