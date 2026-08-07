"""Shared register fixtures for the SAJ Modbus tests."""

import pytest
from modbus_connection.mock import MockModbusUnit

from custom_components.saj_modbus.inverter import SajR5Inverter


def encode_string(value: str, length: int) -> list[int]:
    """Pack an ASCII string into null-padded registers, two characters per word."""
    raw = value.encode("ascii").ljust(length * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, len(raw), 2)]


SERIAL = "R5-3K-S2SN01"

INFO_REGISTERS = {
    0x8F00: [3, 1, 1013]
    + encode_string(SERIAL, 10)
    + encode_string("PC987654", 10)
    + [1001, 2002, 1234, 1005, 1006, 1007],
}

REALTIME_REGISTERS = {
    0x100: [
        2,  # mpvmode: Normal
        0x0000,
        0x0000,  # faultmsg0
        0x0000,
        0x0001,  # faultmsg1: Master Relay Error
        0x0000,
        0x0000,  # faultmsg2
        3050,
        512,
        1500,  # pv1: 305.0 V, 5.12 A, 1500 W
        2980,
        431,
        1290,  # pv2
        0,
        0,
        0,  # pv3
        3900,  # busvolt: 390.0 V
        0xFFF6,  # invtempc: -1.0 °C
        0xFFFF,  # gfci: -1
        2790,  # power
        0xFFCE,  # qpower: -50
        998,  # pf: 0.998
        2301,
        402,
        4999,
        3,
        921,
        999,  # l1
        2302,
        403,
        5001,
        0xFFFD,
        930,
        997,  # l2
        2303,
        404,
        5000,
        4,
        939,
        1000,  # l3
        8000,
        8001,
        8002,
        8003,  # iso1-4
        1234,  # todayenergy: 12.34
        0,
        45678,  # monthenergy: 456.78
        1,
        57920,  # yearenergy: 1234.56
        120,
        26691,  # totalenergy: 78910.11
        65,  # todayhour: 6.5
        1,
        57920,  # totalhour: 12345.6
        7,  # errorcount
        2026,
        (8 << 8) | 7,
        (3 << 8) | 21,
        42 << 8,  # datetime
    ],
    0x1037: 1,  # poweronoff
}


@pytest.fixture
def serial() -> str:
    """Return the serial number the mocked inverter reports."""
    return SERIAL


@pytest.fixture
def info_registers() -> dict:
    """Return the inverter's static information registers."""
    return dict(INFO_REGISTERS)


@pytest.fixture
def realtime_registers() -> dict:
    """Return the inverter's realtime and power-state registers."""
    return dict(REALTIME_REGISTERS)


@pytest.fixture
def device(mock_modbus_unit: MockModbusUnit) -> SajR5Inverter:
    """Return an inverter whose registers are all populated."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)
    mock_modbus_unit.holding.update(REALTIME_REGISTERS)
    return SajR5Inverter(mock_modbus_unit)
