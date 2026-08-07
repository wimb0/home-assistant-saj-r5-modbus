"""Tests for the serial-number identity of the hub."""

from unittest.mock import MagicMock

from custom_components.saj_modbus.entity import SajEntity
from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.const import DOMAIN, SENSOR_TYPES


def make_hub(inverter_data: dict) -> SAJModbusHub:
    """Build a hub without running its Modbus-touching __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub.inverter_data = inverter_data
    hub._attr_name = "SAJ"
    hub.name = "SAJ"
    return hub


def test_identity_prefers_serial() -> None:
    """Once the serial is known, it is the identity."""
    hub = make_hub({"sn": "R5-3K-S2SN01"})

    assert hub.serial_number == "R5-3K-S2SN01"
    assert hub.identifier == "R5-3K-S2SN01"
    assert hub.device_info["identifiers"] == {(DOMAIN, "R5-3K-S2SN01")}
    assert hub.device_info["serial_number"] == "R5-3K-S2SN01"
    assert hub.device_info["name"] == "SAJ"


def test_identity_falls_back_to_name() -> None:
    """Without a readable info block, identity stays name-based."""
    for inverter_data in ({}, {"sn": ""}, {"sn": None}):
        hub = make_hub(inverter_data)

        assert hub.serial_number is None
        assert hub.identifier == "SAJ"
        assert hub.device_info["identifiers"] == {(DOMAIN, "SAJ")}
        assert hub.device_info["serial_number"] is None


def test_entity_unique_id_uses_identifier() -> None:
    """Entity unique ids are built from the hub identifier, not the name."""
    hub = MagicMock()
    hub.identifier = "R5-3K-S2SN01"
    hub.device_info = {"identifiers": {(DOMAIN, "R5-3K-S2SN01")}}

    entity = SajEntity(hub, SENSOR_TYPES["PV1Volt"])

    assert entity.unique_id == "R5-3K-S2SN01_pv1volt"
