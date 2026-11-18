"""Tests for R6 family support: detection, register maps and per-type setup."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit, WriteEvent
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_modbus.const import (
    CONF_INVERTER_TYPE,
    CONF_SLAVE_ID,
    DOMAIN,
    FAMILY_R5,
    FAMILY_R6_HIGH,
    FAMILY_R6_HYBRID,
    NUMBER_TYPES,
    SENSORS_BY_FAMILY,
    SWITCH_TYPES,
)
from custom_components.saj_modbus.hub import SAJModbusHub
from custom_components.saj_modbus.inverter import (
    UNIT_ID,
    ProbeResult,
    R6HighData,
    R6HybridData,
    SajR5Inverter,
    UpdateReport,
    detect_family,
)
from tests.conftest import R6_HYBRID_PROBE, R6_HIGH_PROBE

WRITE_MULTIPLE_REGISTERS = 0x10
R5_BLOCK = 0x100


def make_hub(device: SajR5Inverter) -> SAJModbusHub:
    """Build a hub around ``device`` without running its connecting __init__."""
    hub = SAJModbusHub.__new__(SAJModbusHub)
    hub.device = device
    hub.name = "SAJ"
    hub._identifier = "R5"
    hub._power_limit = 110.0
    hub._timeouts = 0
    hub._report = UpdateReport(set(), {})
    hub._listeners = {}
    hub.last_update_success = True
    return hub


# -- family detection ---------------------------------------------------------


async def test_detect_family_known_r5_devtype_needs_no_probe(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """A documented R5 device type decides without probing other blocks."""
    assert await detect_family(mock_modbus_unit, 0x13) == FAMILY_R5
    assert all(
        event.address != R6_HYBRID_PROBE for event in mock_modbus_unit.read_events
    )


async def test_detect_family_probes_r6_hybrid_block(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """An unknown device type answering 0x4004 is an R6 3-15K hybrid."""
    assert await detect_family(mock_modbus_unit, 0x99) == FAMILY_R6_HYBRID


async def test_detect_family_probes_r6_high_block(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """When 0x4004 refuses but 0x6013 answers, it is an R6 17-50K / C6."""
    mock_modbus_unit.fail_read(R6_HYBRID_PROBE, IllegalDataAddressError())

    assert await detect_family(mock_modbus_unit, 0x99) == FAMILY_R6_HIGH


async def test_detect_family_falls_back_to_the_r5_block(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Only the 0x100 block answering means a PLUS / R5."""
    mock_modbus_unit.fail_read(R6_HYBRID_PROBE, IllegalDataAddressError())
    mock_modbus_unit.fail_read(R6_HIGH_PROBE, IllegalDataAddressError())

    assert await detect_family(mock_modbus_unit, 0x99) == FAMILY_R5


async def test_detect_family_defaults_to_r5_when_everything_refuses(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """No block answering at all still yields the R5 default."""
    for address in (R6_HYBRID_PROBE, R6_HIGH_PROBE, R5_BLOCK):
        mock_modbus_unit.fail_read(address, IllegalDataAddressError())

    assert await detect_family(mock_modbus_unit, None) == FAMILY_R5


async def test_probe_detects_r6_hybrid(
    mock_modbus_unit: MockModbusUnit, info_registers: dict
) -> None:
    """The config flow probe reports the detected family next to the serial."""
    mock_modbus_unit.holding.update(info_registers)

    probe = await SajR5Inverter.async_probe(mock_modbus_unit)

    assert probe.family == FAMILY_R6_HYBRID
    assert probe.serial == "R5-3K-S2SN01"


# -- R6 register maps ----------------------------------------------------------


async def test_r6_hybrid_data_decodes(
    mock_modbus_unit: MockModbusUnit, r6_hybrid_registers: dict
) -> None:
    """The 0x4000 block decodes battery, PV and energy values."""
    mock_modbus_unit.holding.update(r6_hybrid_registers)
    data = R6HybridData(mock_modbus_unit)

    await data.async_update()

    assert data.mpvmode == 4
    assert data.mfaultmsg == 1
    assert data.errorcount == 5
    assert data.sinktempc == 45.0
    assert data.ambtempc == 30.1
    assert data.batvolt == 51.2
    assert data.batcurr == -1.2
    assert data.batpower == -300
    assert data.battempc == 28.0
    assert data.batsoc == 75.5
    assert data.pv1volt == 305.0
    assert data.pv1curr == 5.12
    assert data.pv1power == 1500
    assert data.pv1strcurr1 == 5.11
    assert data.totalpvpower == 1560
    assert data.todaypvenergy == 12.34
    assert data.totalpvenergy == 78900.0


async def test_r6_hybrid_read_plan_stays_inside_the_4000_block(
    mock_modbus_unit: MockModbusUnit, r6_hybrid_registers: dict
) -> None:
    """The 0x4000 block is wider than one request, so it splits into blocks."""
    mock_modbus_unit.holding.update(r6_hybrid_registers)
    data = R6HybridData(mock_modbus_unit)

    await data.async_update()

    blocks = [(event.address, event.count) for event in mock_modbus_unit.read_events]
    assert len(blocks) > 1
    assert all(
        address >= 0x4000 and address + count - 1 <= 0x40FE for address, count in blocks
    )
    assert all(count <= 125 for _, count in blocks)


async def test_r6_high_data_decodes(
    mock_modbus_unit: MockModbusUnit, r6_high_registers: dict
) -> None:
    """The 0x6000 block decodes totals, output and PV values."""
    mock_modbus_unit.holding.update(r6_high_registers)
    data = R6HighData(mock_modbus_unit)

    await data.async_update()

    assert data.mpvmode == 2
    assert data.faultmsg0 == 1
    assert data.totalenergy == 789.10
    assert data.power == 2790
    assert data.l1volt == 230.1
    assert data.l1curr == 4.02
    assert data.l1power == 921
    assert data.pv1volt == 305.0
    assert data.pv1strcurr1 == 5.12


# -- setup with detection ------------------------------------------------------


async def test_setup_detects_family_and_rebuilds(
    mock_modbus_unit: MockModbusUnit, info_registers: dict, r6_hybrid_registers: dict
) -> None:
    """An entry without a stored type gets the detected family's components."""
    mock_modbus_unit.holding.update(info_registers)
    mock_modbus_unit.holding.update(r6_hybrid_registers)
    device = SajR5Inverter(mock_modbus_unit)

    await device.async_setup()

    assert device.family == FAMILY_R6_HYBRID
    assert isinstance(device.realtime, R6HybridData)
    assert device.info.sn == "R5-3K-S2SN01"  # info survived the rebuild

    mock_modbus_unit.read_events.clear()
    report = await device.async_update()

    assert report.updated == {"realtime", "power"}
    reads = [event.address for event in mock_modbus_unit.read_events]
    assert R5_BLOCK not in reads
    assert any(0x4000 <= address <= 0x40FE for address in reads)


async def test_setup_keeps_stored_family(
    r6_high_device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """A stored family is trusted; no detection probes are issued."""
    await r6_high_device.async_setup()

    assert r6_high_device.family == FAMILY_R6_HIGH
    assert isinstance(r6_high_device.realtime, R6HighData)
    assert all(
        event.address not in (R6_HYBRID_PROBE, R6_HIGH_PROBE)
        for event in mock_modbus_unit.read_events
    )


# -- hub behaviour per family --------------------------------------------------


async def test_hybrid_hub_power_status_and_faults(
    hass: HomeAssistant,
    r6_hybrid_device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """The R6 hybrid reads its inverted stop bit and its own fault table."""
    device = r6_hybrid_device
    await device.async_setup()
    await device.async_update()
    hub = make_hub(device)
    hub.hass = hass

    assert hub.family == FAMILY_R6_HYBRID
    assert hub.poweronoff is True  # inverterstop 0x340C = 0 means on
    assert hub.mpvstatus == "Grid + load (battery)"
    assert hub.is_generating is True  # mode 4 generates
    assert hub.fault_messages == ["Code 33: Bus Voltage High"]

    mock_modbus_unit.holding[0x340C] = 1
    await device.power.async_update()
    assert hub.poweronoff is False

    mock_modbus_unit.holding[0x4004] = 1  # Waiting: not generating
    await device.realtime.async_update()
    assert hub.is_generating is False
    assert hub.mpvstatus == "Waiting"


async def test_hybrid_hub_writes_stop_bit_inverted(
    hass: HomeAssistant,
    r6_hybrid_device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """Turning the hybrid off writes 1 to 0x340C, with FC16."""
    device = r6_hybrid_device
    await device.async_setup()
    hub = make_hub(device)
    hub.hass = hass
    events: list[WriteEvent] = []
    mock_modbus_unit.on_write(events.append)

    assert await hub.async_set_power_on_off(False) is True

    assert events == [WriteEvent("holding", 0x340C, [1], WRITE_MULTIPLE_REGISTERS)]


async def test_hybrid_hub_writes_its_own_limit_register(
    hass: HomeAssistant,
    r6_hybrid_device: SajR5Inverter,
    mock_modbus_unit: MockModbusUnit,
) -> None:
    """The hybrid power limit lives at 0x340B, in tenths of a percent."""
    device = r6_hybrid_device
    await device.async_setup()
    await device.async_update()
    hub = make_hub(device)
    hub.hass = hass
    er.async_get(hass).async_get_or_create(
        "number", DOMAIN, f"{hub.identifier}_limitpower"
    )

    assert await hub.async_set_limit_power(55.5) is True

    assert mock_modbus_unit.holding[0x340B] == 555
    assert hub.limitpower == 55.5


async def test_r6_high_hub_uses_1037_and_101c(
    hass: HomeAssistant, r6_high_device: SajR5Inverter, mock_modbus_unit: MockModbusUnit
) -> None:
    """R6 17-50K / C6 shares 0x1037 for on/off and limits at 0x101C."""
    device = r6_high_device
    await device.async_setup()
    await device.async_update()
    hub = make_hub(device)
    hub.hass = hass
    er.async_get(hass).async_get_or_create(
        "number", DOMAIN, f"{hub.identifier}_limitpower"
    )
    events: list[WriteEvent] = []
    mock_modbus_unit.on_write(events.append)

    assert hub.family == FAMILY_R6_HIGH
    assert hub.poweronoff is True
    assert hub.mpvstatus == "Normal"
    assert hub.fault_messages == ["Code 33: Master Bus Voltage High"]

    assert await hub.async_set_power_on_off(False) is True
    assert events == [WriteEvent("holding", 0x1037, [0], WRITE_MULTIPLE_REGISTERS)]

    assert await hub.async_set_limit_power(55.5) is True
    assert mock_modbus_unit.holding[0x101C] == 555


# -- entity descriptions per family --------------------------------------------


async def test_r6_hybrid_descriptions_resolve(
    r6_hybrid_device: SajR5Inverter,
) -> None:
    """Every hybrid entity description reads its value off the device model."""
    await r6_hybrid_device.async_setup()
    await r6_hybrid_device.async_update()
    hub = make_hub(r6_hybrid_device)
    sensor_types, counter_types = SENSORS_BY_FAMILY[FAMILY_R6_HYBRID]

    values = {
        description.key: description.value_fn(hub)
        for descriptions in (
            sensor_types,
            counter_types,
            NUMBER_TYPES,
            SWITCH_TYPES,
        )
        for description in descriptions.values()
    }

    assert values["batsoc"] == 75.5
    assert values["batpower"] == -300
    assert values["pv1strcurr1"] == 5.11
    assert values["totalpvenergy"] == 78900.0
    assert values["poweronoff"] is True
    assert values["limitpower"] == 110.0


async def test_r6_high_descriptions_resolve(
    r6_high_device: SajR5Inverter,
) -> None:
    """Every R6 17-50K / C6 entity description reads its value off the model."""
    await r6_high_device.async_setup()
    await r6_high_device.async_update()
    hub = make_hub(r6_high_device)
    sensor_types, counter_types = SENSORS_BY_FAMILY[FAMILY_R6_HIGH]

    values = {
        description.key: description.value_fn(hub)
        for descriptions in (
            sensor_types,
            counter_types,
            NUMBER_TYPES,
            SWITCH_TYPES,
        )
        for description in descriptions.values()
    }

    assert values["power"] == 2790
    assert values["totalenergy"] == 789.10
    assert values["pv1strcurr1"] == 5.12
    assert values["poweronoff"] is True


# -- end-to-end setup per family ------------------------------------------------


def _mock_connection(info_registers: dict, registers: dict) -> MockModbusConnection:
    """Serve the given registers wherever the hub opens a connection."""
    connection = MockModbusConnection()
    unit = connection.for_unit(UNIT_ID)
    unit.holding.update(info_registers)
    unit.holding.update(registers)
    return connection


async def test_setup_r6_hybrid_entry(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    info_registers: dict,
    r6_hybrid_registers: dict,
    serial: str,
) -> None:
    """An entry whose type says R6 hybrid gets the hybrid's entities only."""
    connection = _mock_connection(info_registers, r6_hybrid_registers)
    with (
        patch(
            "custom_components.saj_modbus.hub.ModbusConnection",
            return_value=connection,
        ),
        patch(
            "custom_components.saj_modbus.hub.create_connection",
            return_value=connection,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=4,
            data={
                CONF_HOST: "192.168.1.10",
                CONF_PORT: 502,
                CONF_NAME: "SAJ",
                CONF_SLAVE_ID: 1,
                CONF_INVERTER_TYPE: FAMILY_R6_HYBRID,
            },
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    batsoc = registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_batsoc")
    assert batsoc is not None
    state = hass.states.get(batsoc)
    assert state is not None
    assert state.state == "75.5"
    # R5-only entities are not created for a hybrid.
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_l1volt") is None
    # The hybrid's own settings are there: limit power number, on/off switch.
    assert (
        registry.async_get_entity_id("number", DOMAIN, f"{serial}_limitpower")
        is not None
    )
    assert (
        registry.async_get_entity_id("switch", DOMAIN, f"{serial}_poweronoff")
        is not None
    )


async def test_setup_stamps_detected_family_on_old_entries(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    info_registers: dict,
    realtime_registers: dict,
) -> None:
    """Entries predating type detection learn the family at first setup."""
    connection = _mock_connection(info_registers, realtime_registers)
    connection.for_unit(UNIT_ID).fail_read(R6_HYBRID_PROBE, IllegalDataAddressError())
    connection.for_unit(UNIT_ID).fail_read(R6_HIGH_PROBE, IllegalDataAddressError())
    with (
        patch(
            "custom_components.saj_modbus.hub.ModbusConnection",
            return_value=connection,
        ),
        patch(
            "custom_components.saj_modbus.hub.create_connection",
            return_value=connection,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=4,
            data={
                CONF_HOST: "192.168.1.10",
                CONF_PORT: 502,
                CONF_NAME: "SAJ",
                CONF_SLAVE_ID: 1,
            },
        )
        entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data[CONF_INVERTER_TYPE] == FAMILY_R5


# -- config flow ----------------------------------------------------------------


async def test_tcp_flow_stores_detected_family(
    hass: HomeAssistant,
    enable_custom_integrations: None,
    info_registers: dict,
) -> None:
    """The config flow detects the family and stores it on the new entry."""
    probe = ProbeResult(serial="R6-3K-0001", family=FAMILY_R6_HYBRID, devtype=0x31)
    connection = MockModbusConnection()
    connection.for_unit(UNIT_ID).holding.update(info_registers)
    with (
        patch(
            "custom_components.saj_modbus.config_flow.async_probe", return_value=probe
        ),
        patch(
            "custom_components.saj_modbus.hub.ModbusConnection",
            return_value=connection,
        ),
        patch(
            "custom_components.saj_modbus.hub.create_connection",
            return_value=connection,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] == FlowResultType.MENU

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "tcp"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "tcp"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "SAJ",
                CONF_HOST: "192.168.1.10",
                CONF_PORT: 502,
                CONF_SLAVE_ID: 1,
                CONF_SCAN_INTERVAL: 60,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_INVERTER_TYPE] == FAMILY_R6_HYBRID
    assert result["data"][CONF_HOST] == "192.168.1.10"
