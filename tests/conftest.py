"""Shared register fixtures for the SAJ Modbus tests."""

import pytest
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusUnit

from custom_components.saj_modbus.const import FAMILY_R6_HIGH, FAMILY_R6_HYBRID
from custom_components.saj_modbus.inverter import SajR5Inverter

# Family probe registers the R6 families answer and an R5 does not serve.
R6_HYBRID_PROBE = 0x4004
R6_HIGH_PROBE = 0x6013


def refuse_r6_probes(unit: MockModbusUnit) -> None:
    """Make the mock look like an R5: the R6 probe blocks refuse."""
    unit.fail_read(R6_HYBRID_PROBE, IllegalDataAddressError())
    unit.fail_read(R6_HIGH_PROBE, IllegalDataAddressError())


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


R6_HYBRID_REGISTERS = {
    0x4004: 4,  # mpvmode: grid + load (battery)
    0x4007: 0,
    0x4008: 0x00000001,  # mfaultmsg (uint32, big endian): Code 33 Bus Voltage High
    0x400F: 5,  # errorcount
    0x4010: 450,  # sinktempc 45.0 C
    0x4011: 301,  # ambtempc 30.1 C
    0x4069: 512,  # batvolt 51.2 V
    0x406A: -120,  # batcurr -1.20 A
    0x406D: -300,  # batpower -300 W
    0x406E: 280,  # battempc 28.0 C
    0x406F: 7550,  # batsoc 75.50 %
    0x4071: 3050,  # pv1volt 305.0 V
    0x4072: 512,  # pv1curr 5.12 A
    0x4073: 1500,  # pv1power 1500 W
    0x407D: 511,  # pv1strcurr1 5.11 A
    0x40A5: 1560,  # totalpvpower
    0x40BF: [0, 1234],  # todaypvenergy 12.34 kWh
    0x40C5: [120, 25680],  # totalpvenergy 78900.00 kWh
    0x340B: 1000,  # limitpower raw 100.0 %
    0x340C: 0,  # inverterstop: power on
}

R6_HIGH_REGISTERS = {
    0x6004: [1, 13374],  # totalenergy (uint32) 78910 raw = 789.10 kWh
    0x6013: 2,  # mpvmode: Normal
    0x6014: 0,
    0x6015: 0x00000001,  # faultmsg0 (uint32, big endian): Code 33 Bus Voltage High
    0x601D: [0, 2790],  # power 2790 W
    0x6022: 2301,  # l1volt 230.1 V
    0x6023: 402,  # l1curr 4.02 A
    0x6026: 921,  # l1power 921 W
    0x6045: 3050,  # pv1volt
    0x6057: 512,  # pv1strcurr1 5.12 A
    0x101C: 1000,  # limitpower raw 100.0 %
    0x1037: 1,  # poweronoff: on
}


@pytest.fixture
def r6_hybrid_registers() -> dict:
    """Return an R6 3-15K hybrid's registers."""
    return dict(R6_HYBRID_REGISTERS)


@pytest.fixture
def r6_high_registers() -> dict:
    """Return an R6 17-50K / C6's registers."""
    return dict(R6_HIGH_REGISTERS)


@pytest.fixture
def device(mock_modbus_unit: MockModbusUnit) -> SajR5Inverter:
    """Return an R5 inverter whose registers are all populated."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)
    mock_modbus_unit.holding.update(REALTIME_REGISTERS)
    refuse_r6_probes(mock_modbus_unit)
    return SajR5Inverter(mock_modbus_unit)


@pytest.fixture
def r6_hybrid_device(mock_modbus_unit: MockModbusUnit) -> SajR5Inverter:
    """Return an R6 3-15K hybrid with its registers populated."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)
    mock_modbus_unit.holding.update(R6_HYBRID_REGISTERS)
    return SajR5Inverter(mock_modbus_unit, family=FAMILY_R6_HYBRID)


@pytest.fixture
def r6_high_device(mock_modbus_unit: MockModbusUnit) -> SajR5Inverter:
    """Return an R6 17-50K / C6 with its registers populated."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)
    mock_modbus_unit.holding.update(R6_HIGH_REGISTERS)
    return SajR5Inverter(mock_modbus_unit, family=FAMILY_R6_HIGH)
