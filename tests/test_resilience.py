"""One failing component must not take the rest of the poll with it.

The inverter's two polled components are read independently: a block that is
slow or refused costs its own component and nothing else.
"""

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import (
    ModbusConnectionError,
    ModbusTimeoutError,
    ServerDeviceBusyError,
)
from modbus_connection.mock import MockModbusConnection, MockModbusUnit

from custom_components.saj_modbus.const import (
    NUMBER_TYPES,
    SENSOR_TYPES,
    SWITCH_TYPES,
)
from custom_components.saj_modbus.entity import SajEntity, SajEntityDescription
from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.inverter import SajR5Inverter

INFO_REGISTER = 0x8F00
REALTIME_REGISTER = 0x100
POWER_REGISTER = 0x1037
# Active power, in the middle of the realtime block.
POWER_OUTPUT_REGISTER = 0x113


def make_hub(device: SajR5Inverter, connection: MockModbusConnection) -> SAJModbusHub:
    """Build a hub around ``device`` without running its connecting __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub._connection = connection
    hub.device = device
    hub._timeouts = 0
    hub._failed_components = frozenset()
    hub._identifier = "R5"
    hub.name = "SAJ"
    hub.last_update_success = True
    return hub


def is_available(hub: SAJModbusHub, description: SajEntityDescription) -> bool:
    """Whether the entity for ``description`` would report itself available."""
    return SajEntity(hub, description).available


async def test_a_failed_component_leaves_the_rest_fresh(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """A refused power register costs the switch, not the sixty sensors."""
    await device.async_setup()
    await device.async_update()
    assert device.power.poweronoff is True

    mock_modbus_unit.holding[POWER_OUTPUT_REGISTER] = 1234  # output changes
    mock_modbus_unit.holding[POWER_REGISTER] = 0  # so does the power state
    mock_modbus_unit.fail_read(POWER_REGISTER, ModbusTimeoutError("slow register"))
    report = await device.async_update()

    assert not report.complete
    assert set(report.failed) == {"power"}
    assert isinstance(report.failed["power"], ModbusTimeoutError)
    assert report.updated == {"realtime"}
    assert device.realtime.power == 1234
    assert device.power.poweronoff is True  # previous value kept


async def test_a_failed_realtime_block_leaves_the_power_state_fresh(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """And the other way round: the big block failing is contained too."""
    await device.async_setup()
    await device.async_update()
    before = device.realtime.power

    mock_modbus_unit.holding[POWER_OUTPUT_REGISTER] = 1234
    mock_modbus_unit.holding[POWER_REGISTER] = 0
    mock_modbus_unit.fail_read(REALTIME_REGISTER, ModbusTimeoutError("slow block"))
    report = await device.async_update()

    assert set(report.failed) == {"realtime"}
    assert report.updated == {"power"}
    assert device.realtime.power == before
    assert device.power.poweronoff is False


async def test_listeners_fire_at_the_end_and_only_for_fresh_components(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """Nothing is published until every component has been tried."""
    await device.async_setup()
    await device.async_update()
    seen: list[int] = []
    device.realtime.add_update_listener(
        lambda: seen.append(len(mock_modbus_unit.read_events))
    )
    device.power.add_update_listener(lambda: seen.append(-1))

    mock_modbus_unit.fail_read(POWER_REGISTER, ModbusTimeoutError("slow register"))
    mock_modbus_unit.read_events.clear()
    await device.async_update()

    # One notification, raised after both reads were attempted, and none for
    # the component that failed.
    assert seen == [len(mock_modbus_unit.read_events)]


async def test_a_dead_link_raises_instead_of_reporting(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """With the link itself down there is no partial poll to report."""
    await device.async_setup()
    mock_modbus_unit.fail_requests(ModbusConnectionError("link down"))

    with pytest.raises(ModbusConnectionError):
        await device.async_update()


async def test_every_component_refreshes_on_a_healthy_device(
    device: SajR5Inverter,
) -> None:
    """A healthy poll reports itself complete."""
    await device.async_setup()

    report = await device.async_update()

    assert report.complete
    assert report.failed == {}
    assert report.updated == {"realtime", "power"}


async def test_the_poll_reads_one_block_per_component(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """Reading per component did not change what goes on the wire.

    The realtime and power registers are 0xF00 apart, far beyond the planner's
    merge gap, so the pooled group these replaced already issued two reads.
    """
    await device.async_setup()

    mock_modbus_unit.read_events.clear()
    await device.async_update()

    blocks = [(event.address, event.count) for event in mock_modbus_unit.read_events]
    assert blocks == [(REALTIME_REGISTER, 59), (POWER_REGISTER, 1)]


async def test_a_failed_setup_raises_and_is_retried(
    device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """Setup settles what to poll, so until it lands there is nothing partial."""
    mock_modbus_unit.fail_read(INFO_REGISTER, ServerDeviceBusyError())

    with pytest.raises(ServerDeviceBusyError):
        await device.async_update()

    mock_modbus_unit.fail_read(INFO_REGISTER, None)
    report = await device.async_update()

    assert report.complete
    assert device.absent == frozenset()


async def test_a_partial_poll_does_not_fail_the_update(
    device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """The coordinator stays successful as long as something answered."""
    hub = make_hub(device, mock_modbus_connection)
    await device.async_setup()
    mock_modbus_unit.fail_read(POWER_REGISTER, ModbusTimeoutError("slow register"))

    await hub._async_update_data()

    assert hub.failed_components == {"power"}
    # The device answered, so this is not the stuck link the counter watches for.
    assert hub._timeouts == 0


async def test_a_poll_that_reads_nothing_fails_the_update(
    device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """An inverter answering none of its blocks is still a failed poll."""
    hub = make_hub(device, mock_modbus_connection)
    await device.async_setup()
    mock_modbus_unit.fail_requests(ModbusTimeoutError("no reply"))

    with pytest.raises(UpdateFailed):
        await hub._async_update_data()

    assert hub.failed_components == {"realtime", "power"}
    assert hub._timeouts == 1


async def test_only_the_failed_components_entities_go_unavailable(
    device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """The power switch drops out; the sensors reading realtime do not."""
    hub = make_hub(device, mock_modbus_connection)
    await device.async_setup()
    mock_modbus_unit.fail_read(POWER_REGISTER, ModbusTimeoutError("slow register"))

    await hub._async_update_data()

    assert not is_available(hub, SWITCH_TYPES["PowerOnOff"])
    assert is_available(hub, SENSOR_TYPES["MPVMode"])
    assert is_available(hub, SENSOR_TYPES["SN"])
    assert is_available(hub, NUMBER_TYPES["LimitPower"])


async def test_a_failed_realtime_block_drops_only_its_own_sensors(
    device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """The static information sensors never depend on a poll."""
    hub = make_hub(device, mock_modbus_connection)
    await device.async_setup()
    mock_modbus_unit.fail_read(REALTIME_REGISTER, ModbusTimeoutError("slow block"))

    await hub._async_update_data()

    assert not is_available(hub, SENSOR_TYPES["MPVMode"])
    assert is_available(hub, SENSOR_TYPES["SN"])
    assert is_available(hub, SWITCH_TYPES["PowerOnOff"])
