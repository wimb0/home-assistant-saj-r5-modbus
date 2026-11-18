"""Tests for discovering which components an inverter serves."""

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
from modbus_connection.mock import MockModbusUnit

from custom_components.saj_modbus.const import SENSOR_TYPES, SWITCH_TYPES
from custom_components.saj_modbus.entity import served
from custom_components.saj_modbus.inverter import SajR5Inverter

POWER_REGISTER = 0x1037
INFO_REGISTER = 0x8F00
STRINGS_REGISTER = 0x13B

STRING_SENSORS = [
    description
    for description in SENSOR_TYPES.values()
    if description.component == "strings"
]


@pytest.mark.parametrize(
    "error",
    [IllegalFunctionError(), IllegalDataAddressError()],
    ids=lambda e: type(e).__name__,
)
async def test_setup_records_a_component_the_inverter_refuses(
    device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
    error: ModbusExceptionError,
    serial: str,
) -> None:
    """A refusal meaning "not in my map" costs that component, not setup."""
    mock_modbus_unit.fail_read(POWER_REGISTER, error)

    await device.async_setup()

    assert device.absent == {"power"}
    assert device.info.sn == serial


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
async def test_setup_propagates_any_other_refusal(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit, error: ModbusExceptionError
) -> None:
    """A transient refusal must not be recorded as missing registers.

    Hiding it would report a faulting or busy inverter as one that
    permanently lacks the registers.
    """
    mock_modbus_unit.fail_read(POWER_REGISTER, error)

    with pytest.raises(ModbusExceptionError):
        await device.async_setup()


async def test_an_absent_component_is_never_polled(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """What setup found missing is not in the polled group at all."""
    mock_modbus_unit.fail_read(POWER_REGISTER, IllegalDataAddressError())
    await device.async_setup()

    mock_modbus_unit.read_events.clear()
    await device.async_update()

    reads = [event.address for event in mock_modbus_unit.read_events]
    assert POWER_REGISTER not in reads


async def test_static_information_is_never_polled(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """Setup reads the information registers, and polling never asks again."""
    await device.async_setup()
    assert INFO_REGISTER in [event.address for event in mock_modbus_unit.read_events]

    mock_modbus_unit.read_events.clear()
    await device.async_update()

    reads = [event.address for event in mock_modbus_unit.read_events]
    assert INFO_REGISTER not in reads


async def test_a_served_inverter_polls_everything(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """With nothing refused, the poll still reads the power register."""
    await device.async_setup()

    mock_modbus_unit.read_events.clear()
    await device.async_update()

    reads = [event.address for event in mock_modbus_unit.read_events]
    assert POWER_REGISTER in reads
    assert STRINGS_REGISTER in reads
    assert device.absent == frozenset()


async def test_entities_are_not_created_for_an_absent_component(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """The power switch is left out when the inverter refuses its register."""
    mock_modbus_unit.fail_read(POWER_REGISTER, IllegalDataAddressError())
    await device.async_setup()

    class _Hub:
        absent_components = device.absent

    assert served(_Hub(), SWITCH_TYPES.values()) == []
    assert len(SWITCH_TYPES) == 1


async def test_an_absent_strings_component_is_never_polled(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """Older firmware without the string registers is not asked for them again."""
    mock_modbus_unit.fail_read(STRINGS_REGISTER, IllegalDataAddressError())
    await device.async_setup()

    assert device.absent == {"strings"}

    mock_modbus_unit.read_events.clear()
    await device.async_update()

    reads = [event.address for event in mock_modbus_unit.read_events]
    assert STRINGS_REGISTER not in reads


async def test_string_sensors_are_not_created_for_an_absent_component(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """The string current sensors are left out when the inverter refuses them."""
    mock_modbus_unit.fail_read(STRINGS_REGISTER, IllegalDataAddressError())
    await device.async_setup()

    class _Hub:
        absent_components = device.absent

    assert len(STRING_SENSORS) == 16
    assert served(_Hub(), STRING_SENSORS) == []
