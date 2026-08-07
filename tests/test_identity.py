"""Tests for the serial-number identity of the hub."""

from unittest.mock import MagicMock

from custom_components.saj_modbus.const import DOMAIN, SENSOR_TYPES
from custom_components.saj_modbus.entity import SajEntity
from custom_components.saj_modbus.hub import SAJModbusHub


def make_hub(inverter_data: dict) -> SAJModbusHub:
    """Build a hub without running its Modbus-touching __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub.inverter_data = inverter_data
    hub.name = "SAJ"
    hub._identifier = "SAJ"
    return hub


def test_identity_prefers_serial() -> None:
    """Once the serial is known, freezing adopts it."""
    hub = make_hub({"sn": "R5-3K-S2SN01"})

    assert hub.serial_number == "R5-3K-S2SN01"
    assert hub.freeze_identity() == "R5-3K-S2SN01"
    assert hub.identifier == "R5-3K-S2SN01"
    assert hub.device_info["identifiers"] == {(DOMAIN, "R5-3K-S2SN01")}
    assert hub.device_info["serial_number"] == "R5-3K-S2SN01"
    assert hub.device_info["name"] == "SAJ"


def test_identity_falls_back_to_name() -> None:
    """Without a readable info block, identity stays name-based."""
    for inverter_data in ({}, {"sn": ""}, {"sn": None}):
        hub = make_hub(inverter_data)
        hub.freeze_identity()

        assert hub.serial_number is None
        assert hub.identifier == "SAJ"
        assert hub.device_info["identifiers"] == {(DOMAIN, "SAJ")}
        assert hub.device_info["serial_number"] is None


def test_identity_does_not_change_after_freezing() -> None:
    """A serial arriving on a later poll must not move the frozen identity.

    Entities bake the identifier into their unique ids when they are built,
    so a mid-session change would orphan every one of them.
    """
    hub = make_hub({})
    hub.freeze_identity()

    hub.inverter_data = {"sn": "R5-3K-S2SN01"}

    assert hub.serial_number == "R5-3K-S2SN01"
    assert hub.identifier == "SAJ"
    assert hub.device_info["identifiers"] == {(DOMAIN, "SAJ")}


def test_entity_unique_id_uses_identifier() -> None:
    """Entity unique ids are built from the hub identifier, not the name."""
    hub = MagicMock()
    hub.identifier = "R5-3K-S2SN01"
    hub.device_info = {"identifiers": {(DOMAIN, "R5-3K-S2SN01")}}

    entity = SajEntity(hub, SENSOR_TYPES["PV1Volt"])

    assert entity.unique_id == "R5-3K-S2SN01_pv1volt"
