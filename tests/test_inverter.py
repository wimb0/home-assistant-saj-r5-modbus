"""Tests for the SAJ R5 device model against the modbus-connection mock."""

from datetime import datetime

import pytest
from modbus_connection.mock import MockModbusUnit, WriteEvent

from custom_components.saj_modbus.inverter import (
    InverterInfo,
    RealtimeData,
    SajR5Inverter,
    Settings,
)


def encode_string(value: str, length: int) -> list[int]:
    """Pack an ASCII string into null-padded registers, two chars per word."""
    raw = value.encode("ascii").ljust(length * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, len(raw), 2)]


INFO_REGISTERS = {
    0x8F00: [3, 1, 1013]
    + encode_string("R5-3K-S2SN01", 10)
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


async def test_inverter_info(mock_modbus_unit: MockModbusUnit) -> None:
    """The info component decodes the static device data."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)
    info = InverterInfo(mock_modbus_unit)

    await info.async_update()

    assert info.devtype == 3
    assert info.subtype == 1
    assert info.commver == 1.013
    assert info.sn == "R5-3K-S2SN01"
    assert info.pc == "PC987654"
    assert info.dv == 1.001
    assert info.mcv == 2.002
    assert info.scv == 1.234
    assert info.disphwversion == 1.005
    assert info.ctrlhwversion == 1.006
    assert info.powerhwversion == 1.007


async def test_realtime_data(mock_modbus_unit: MockModbusUnit) -> None:
    """The realtime component decodes a full poll."""
    mock_modbus_unit.holding.update(REALTIME_REGISTERS)
    realtime = RealtimeData(mock_modbus_unit)

    await realtime.async_update()

    assert realtime.mpvmode == 2
    assert realtime.faultmsg0 == 0
    assert realtime.faultmsg1 == 1
    assert realtime.faultmsg2 == 0
    assert realtime.pv1volt == 305.0
    assert realtime.pv1curr == 5.12
    assert realtime.pv1power == 1500
    assert realtime.pv3volt == 0.0
    assert realtime.busvolt == 390.0
    assert realtime.invtempc == -1.0
    assert realtime.gfci == -1
    assert realtime.power == 2790
    assert realtime.qpower == -50
    assert realtime.pf == 0.998
    assert realtime.l1volt == 230.1
    assert realtime.l1curr == 4.02
    assert realtime.l1freq == 49.99
    assert realtime.l1dci == 3
    assert realtime.l1power == 921
    assert realtime.l1pf == 0.999
    assert realtime.l2dci == -3
    assert realtime.l3pf == 1.0
    assert realtime.iso4 == 8003
    assert realtime.todayenergy == 12.34
    assert realtime.monthenergy == 456.78
    assert realtime.yearenergy == 1234.56
    assert realtime.totalenergy == 78910.11
    assert realtime.todayhour == 6.5
    assert realtime.totalhour == 12345.6
    assert realtime.errorcount == 7
    assert realtime.datetime == datetime(2026, 8, 7, 3, 21, 42).astimezone()
    assert realtime.poweronoff is True


async def test_realtime_read_plan(mock_modbus_unit: MockModbusUnit) -> None:
    """A poll issues exactly two block reads: the 0x100 block and 0x1037."""
    mock_modbus_unit.holding.update(REALTIME_REGISTERS)
    realtime = RealtimeData(mock_modbus_unit)

    await realtime.async_update()

    blocks = sorted(
        (event.address, event.count) for event in mock_modbus_unit.read_events
    )
    assert blocks == [(0x100, 59), (0x1037, 1)]


async def test_unset_clock_decodes_to_none(mock_modbus_unit: MockModbusUnit) -> None:
    """An unset inverter clock (all zeroes) is not a datetime."""
    realtime = RealtimeData(mock_modbus_unit)

    await realtime.async_update()

    assert realtime.datetime is None


async def test_write_power_on_off(mock_modbus_unit: MockModbusUnit) -> None:
    """Power on/off writes register 0x1037 with FC16."""
    events: list[WriteEvent] = []
    mock_modbus_unit.on_write(events.append)
    realtime = RealtimeData(mock_modbus_unit)

    await realtime.write("poweronoff", False)

    assert events == [WriteEvent("holding", 0x1037, [0])]


async def test_write_limit_power(mock_modbus_unit: MockModbusUnit) -> None:
    """The power limit is written in tenths of a percent."""
    settings = Settings(mock_modbus_unit)

    await settings.write("limitpower", 55.5)

    assert mock_modbus_unit.holding[0x801F] == 555


async def test_write_datetime(mock_modbus_unit: MockModbusUnit) -> None:
    """Setting the clock packs the datetime into four registers at 0x8020."""
    settings = Settings(mock_modbus_unit)

    await settings.write("datetime", datetime(2026, 8, 7, 12, 30, 15))

    assert [mock_modbus_unit.holding[0x8020 + i] for i in range(4)] == [
        2026,
        (8 << 8) | 7,
        (12 << 8) | 30,
        15 << 8,
    ]


async def test_read_only_fields_reject_writes(mock_modbus_unit: MockModbusUnit) -> None:
    """Realtime measurement fields are read-only."""
    realtime = RealtimeData(mock_modbus_unit)

    with pytest.raises(AttributeError):
        await realtime.write("power", 1)


async def test_probe_returns_serial(mock_modbus_unit: MockModbusUnit) -> None:
    """The setup probe reads the serial number."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)

    assert await SajR5Inverter.async_probe(mock_modbus_unit) == "R5-3K-S2SN01"


async def test_read_raw_covers_all_components(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """The diagnostics raw dump spans the info and realtime blocks."""
    mock_modbus_unit.holding.update(INFO_REGISTERS)
    mock_modbus_unit.holding.update(REALTIME_REGISTERS)
    device = SajR5Inverter(mock_modbus_unit)

    raw = await device.async_read_raw()

    assert raw["holding"][0x8F00] == 3
    assert raw["holding"][0x100] == 2
    assert raw["holding"][0x1037] == 1
