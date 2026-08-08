"""Tests for the SAJ R5 device model against the modbus-connection mock."""

from datetime import datetime

import pytest
from modbus_connection.mock import MockModbusUnit, ReadEvent, WriteEvent

from custom_components.saj_modbus.inverter import (
    InverterInfo,
    PowerState,
    RealtimeData,
    SajR5Inverter,
    Settings,
)

# Modbus function code 0x10, write-multiple-registers.
WRITE_MULTIPLE_REGISTERS = 0x10


async def test_inverter_info(
    mock_modbus_unit: MockModbusUnit, info_registers: dict
) -> None:
    """The info component decodes the static device data."""
    mock_modbus_unit.holding.update(info_registers)
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


async def test_realtime_data(
    mock_modbus_unit: MockModbusUnit, realtime_registers: dict
) -> None:
    """The realtime component decodes a full poll."""
    mock_modbus_unit.holding.update(realtime_registers)
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


async def test_realtime_read_plan(
    mock_modbus_unit: MockModbusUnit, realtime_registers: dict
) -> None:
    """A realtime poll is a single block read of the 0x100 block."""
    mock_modbus_unit.holding.update(realtime_registers)
    realtime = RealtimeData(mock_modbus_unit)

    await realtime.async_update()

    blocks = [(event.address, event.count) for event in mock_modbus_unit.read_events]
    assert blocks == [(0x100, 59)]


async def test_power_state(
    mock_modbus_unit: MockModbusUnit, realtime_registers: dict
) -> None:
    """The power state component reads 0x1037."""
    mock_modbus_unit.holding.update(realtime_registers)
    power = PowerState(mock_modbus_unit)

    await power.async_update()

    assert power.poweronoff is True
    assert mock_modbus_unit.read_events == [ReadEvent("holding", 0x1037, 1)]


async def test_unset_clock_decodes_to_none(mock_modbus_unit: MockModbusUnit) -> None:
    """An unset inverter clock (all zeroes) is not a datetime."""
    realtime = RealtimeData(mock_modbus_unit)

    await realtime.async_update()

    assert realtime.datetime is None


async def test_write_power_on_off(mock_modbus_unit: MockModbusUnit) -> None:
    """Power on/off writes register 0x1037, and must use FC16.

    The R5 rejects FC06, so force_fc16 on the field is load-bearing: a single
    register would otherwise go out as a write-single-register.
    """
    events: list[WriteEvent] = []
    mock_modbus_unit.on_write(events.append)
    power = PowerState(mock_modbus_unit)

    await power.write("poweronoff", False)

    assert events == [WriteEvent("holding", 0x1037, [0], WRITE_MULTIPLE_REGISTERS)]


async def test_write_limit_power(mock_modbus_unit: MockModbusUnit) -> None:
    """The power limit is written in tenths of a percent, also with FC16."""
    events: list[WriteEvent] = []
    mock_modbus_unit.on_write(events.append)
    settings = Settings(mock_modbus_unit)

    await settings.write("limitpower", 55.5)

    assert mock_modbus_unit.holding[0x801F] == 555
    assert events == [WriteEvent("holding", 0x801F, [555], WRITE_MULTIPLE_REGISTERS)]


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


async def test_probe_returns_serial(
    mock_modbus_unit: MockModbusUnit, info_registers: dict, serial: str
) -> None:
    """The setup probe reads the serial number."""
    mock_modbus_unit.holding.update(info_registers)

    assert await SajR5Inverter.async_probe(mock_modbus_unit) == serial


async def test_read_raw_covers_all_components(device: SajR5Inverter) -> None:
    """The diagnostics raw dump spans every readable component."""
    raw = await device.async_read_raw()

    assert raw["holding"][0x8F00] == 3
    assert raw["holding"][0x100] == 2
    assert raw["holding"][0x1037] == 1
