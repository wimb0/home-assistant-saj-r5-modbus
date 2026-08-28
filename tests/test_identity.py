"""Tests for the serial-number identity of the hub."""

from modbus_connection.mock import MockModbusUnit

from custom_components.saj_modbus.const import DOMAIN, SENSOR_TYPES
from custom_components.saj_modbus.entity import SajEntity
from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.inverter import SajR5Inverter


def make_hub(device: SajR5Inverter) -> SAJModbusHub:
    """Build a hub around ``device`` without running its connecting __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub.device = device
    hub.name = "SAJ"
    hub._identifier = "SAJ"
    return hub


async def test_identity_prefers_serial(device: SajR5Inverter, serial: str) -> None:
    """Once the info registers are read, freezing adopts the serial."""
    await device.info.async_update()
    hub = make_hub(device)

    assert hub.serial_number == serial
    assert hub.freeze_identity() == serial
    assert hub.identifier == serial
    assert hub.device_info["identifiers"] == {(DOMAIN, serial)}
    assert hub.device_info["serial_number"] == serial
    assert hub.device_info["name"] == "SAJ"


def test_identity_falls_back_to_name(mock_modbus_unit: MockModbusUnit) -> None:
    """Without readable info registers, identity stays name-based."""
    hub = make_hub(SajR5Inverter(mock_modbus_unit))
    hub.freeze_identity()

    assert hub.serial_number is None
    assert hub.identifier == "SAJ"
    assert hub.device_info["identifiers"] == {(DOMAIN, "SAJ")}
    assert hub.device_info["serial_number"] is None


async def test_identity_does_not_change_after_freezing(
    device: SajR5Inverter, serial: str
) -> None:
    """A serial arriving on a later poll must not move the frozen identity.

    Entities bake the identifier into their unique ids when they are built,
    so a mid-session change would orphan every one of them.
    """
    hub = make_hub(device)
    hub.freeze_identity()

    await device.info.async_update()

    assert hub.serial_number == serial
    assert hub.identifier == "SAJ"
    assert hub.device_info["identifiers"] == {(DOMAIN, "SAJ")}


async def test_entity_unique_id_uses_identifier(
    device: SajR5Inverter, serial: str
) -> None:
    """Entity unique ids are built from the hub identifier, not the name."""
    await device.info.async_update()
    hub = make_hub(device)
    hub.freeze_identity()

    entity = SajEntity(hub, SENSOR_TYPES["PV1Volt"])

    assert entity.unique_id == f"{serial}_pv1volt"
