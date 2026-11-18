"""Constants for SAJ R5 Inverter Modbus."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfReactivePower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)


DOMAIN = "saj_modbus"
DEFAULT_NAME = "SAJ"
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_PORT = 502
CONF_SAJ_HUB = "saj_hub"
ATTR_MANUFACTURER = "SAJ Electric"

# Transport selection. Historical entries have neither key and are TCP.
CONF_CONNECTION_TYPE = "connection_type"
CONNECTION_TYPE_TCP = "tcp"
CONNECTION_TYPE_SERIAL = "serial"

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_BYTESIZE = "bytesize"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_SLAVE_ID = "slave_id"

# Inverter family, detected at config time and stored on the entry. It picks
# which register map and settings the integration uses.
CONF_INVERTER_TYPE = "inverter_type"
FAMILY_R5 = "r5"  # PLUS / R5 / Sununo / Suntrio: 0x100 realtime block
FAMILY_R6_HYBRID = "r6_hybrid"  # R6 3-15K hybrid: 0x4000 realtime block
FAMILY_R6_HIGH = "r6_high"  # R6 17-50K / C6: 0x6000 realtime block
FAMILIES = (FAMILY_R5, FAMILY_R6_HYBRID, FAMILY_R6_HIGH)
FAMILY_LABELS = {
    FAMILY_R5: "PLUS / R5",
    FAMILY_R6_HYBRID: "R6 3-15K (hybrid)",
    FAMILY_R6_HIGH: "R6 17-50K / C6",
}

DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = "N"
DEFAULT_STOPBITS = 1
DEFAULT_SLAVE_ID = 1
MIN_SLAVE_ID = 1
MAX_SLAVE_ID = 247
SERIAL_BAUDRATES = (9600, 115200)

if TYPE_CHECKING:
    from .hub import SAJModbusHub


@dataclass(frozen=True, kw_only=True)
class SajModbusNumberEntityDescription(NumberEntityDescription):
    """A class that describes SAJ number entities."""

    value_fn: Callable[[SAJModbusHub], Any]
    # The device component this entity reads. An entity naming a component the
    # inverter does not serve is never created, and one naming a component a
    # poll failed to read goes unavailable until it reads again.
    component: str = "realtime"


NUMBER_TYPES: dict[str, list[SajModbusNumberEntityDescription]] = {
    "LimitPower": SajModbusNumberEntityDescription(
        name="Limit Power",
        native_max_value=110,
        native_min_value=0,
        key="limitpower",
        value_fn=lambda hub: hub.limitpower,
        # Write-only on this inverter: never polled, so never stale.
        component="settings",
        icon="mdi:solar-power",
        native_unit_of_measurement="%",
    )
}


@dataclass(frozen=True, kw_only=True)
class SajModbusSwitchEntityDescription(SwitchEntityDescription):
    """A class that describes SAJ switch entities."""

    value_fn: Callable[[SAJModbusHub], Any]
    # The device component this entity reads. An entity naming a component the
    # inverter does not serve is never created, and one naming a component a
    # poll failed to read goes unavailable until it reads again.
    component: str = "realtime"


SWITCH_TYPES: dict[str, list[SajModbusSwitchEntityDescription]] = {
    "PowerOnOff": SajModbusSwitchEntityDescription(
        name="Power On Off",
        key="poweronoff",
        value_fn=lambda hub: hub.poweronoff,
        component="power",
        icon="mdi:power",
        entity_registry_enabled_default=False,
    )
}


# The state classes Home Assistant keeps long-term statistics for.
STATISTICS_STATE_CLASSES = (
    SensorStateClass.TOTAL,
    SensorStateClass.TOTAL_INCREASING,
)


@dataclass(frozen=True, kw_only=True)
class SajModbusSensorEntityDescription(SensorEntityDescription):
    """A class that describes SAJ sensor entities."""

    value_fn: Callable[[SAJModbusHub], Any]
    # The device component this entity reads. An entity naming a component the
    # inverter does not serve is never created, and one naming a component a
    # poll failed to read goes unavailable until it reads again.
    component: str = "realtime"


COUNTER_SENSOR_TYPES: dict[str, list[SajModbusSensorEntityDescription]] = {
    "TodayEnergy": SajModbusSensorEntityDescription(
        name="Power generation on current day",
        key="todayenergy",
        value_fn=lambda hub: hub.device.realtime.todayenergy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "MonthEnergy": SajModbusSensorEntityDescription(
        name="Power generation in current month",
        key="monthenergy",
        value_fn=lambda hub: hub.device.realtime.monthenergy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
    ),
    "YearEnergy": SajModbusSensorEntityDescription(
        name="Power generation in current year",
        key="yearenergy",
        value_fn=lambda hub: hub.device.realtime.yearenergy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
    ),
    "TotalEnergy": SajModbusSensorEntityDescription(
        name="Total power generation",
        key="totalenergy",
        value_fn=lambda hub: hub.device.realtime.totalenergy,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "TodayHour": SajModbusSensorEntityDescription(
        name="Daily working hours",
        key="todayhour",
        value_fn=lambda hub: hub.device.realtime.todayhour,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:progress-clock",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "TotalHour": SajModbusSensorEntityDescription(
        name="Total working hours",
        key="totalhour",
        value_fn=lambda hub: hub.device.realtime.totalhour,
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:progress-clock",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
}

SENSOR_TYPES: dict[str, list[SajModbusSensorEntityDescription]] = {
    "DevType": SajModbusSensorEntityDescription(
        name="Device Type",
        key="devtype",
        value_fn=lambda hub: hub.device.info.devtype,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "SubType": SajModbusSensorEntityDescription(
        name="Sub Type",
        key="subtype",
        value_fn=lambda hub: hub.device.info.subtype,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "CommVer": SajModbusSensorEntityDescription(
        name="Comms Protocol Version",
        key="commver",
        value_fn=lambda hub: hub.device.info.commver,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "SN": SajModbusSensorEntityDescription(
        name="Serial Number",
        key="sn",
        value_fn=lambda hub: hub.device.info.sn,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "PC": SajModbusSensorEntityDescription(
        name="Product Code",
        key="pc",
        value_fn=lambda hub: hub.device.info.pc,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "DV": SajModbusSensorEntityDescription(
        name="Display Software Version",
        key="dv",
        value_fn=lambda hub: hub.device.info.dv,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "MCV": SajModbusSensorEntityDescription(
        name="Master Ctrl Software Version",
        key="mcv",
        value_fn=lambda hub: hub.device.info.mcv,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "SCV": SajModbusSensorEntityDescription(
        name="Slave Ctrl Software Version",
        key="scv",
        value_fn=lambda hub: hub.device.info.scv,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "DispHWVersion": SajModbusSensorEntityDescription(
        name="Display Board Hardware Version",
        key="disphwversion",
        value_fn=lambda hub: hub.device.info.disphwversion,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "CtrlHWVersion": SajModbusSensorEntityDescription(
        name="Control Board Hardware Version",
        key="ctrlhwversion",
        value_fn=lambda hub: hub.device.info.ctrlhwversion,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "PowerHWVersion": SajModbusSensorEntityDescription(
        name="Power Board Hardware Version",
        key="powerhwversion",
        value_fn=lambda hub: hub.device.info.powerhwversion,
        component="info",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    "MPVStatus": SajModbusSensorEntityDescription(
        name="Inverter status",
        key="mpvstatus",
        value_fn=lambda hub: hub.mpvstatus,
        icon="mdi:information-outline",
    ),
    "MPVMode": SajModbusSensorEntityDescription(
        name="Inverter working mode",
        key="mpvmode",
        value_fn=lambda hub: hub.device.realtime.mpvmode,
        icon="mdi:information-outline",
    ),
    "FaultMSG": SajModbusSensorEntityDescription(
        name="Inverter error message",
        key="faultmsg",
        value_fn=lambda hub: hub.faultmsg,
        icon="mdi:message-alert-outline",
    ),
    "DateTime": SajModbusSensorEntityDescription(
        name="Inverter date and time",
        device_class=SensorDeviceClass.TIMESTAMP,
        key="datetime",
        value_fn=lambda hub: hub.device.realtime.datetime,
        icon="mdi:clock-outline",
        entity_registry_enabled_default=False,
    ),
    "PV1Volt": SajModbusSensorEntityDescription(
        name="PV1 voltage",
        key="pv1volt",
        value_fn=lambda hub: hub.device.realtime.pv1volt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "PV1Curr": SajModbusSensorEntityDescription(
        name="PV1 total current",
        key="pv1curr",
        value_fn=lambda hub: hub.device.realtime.pv1curr,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "PV1Power": SajModbusSensorEntityDescription(
        name="PV1 power",
        key="pv1power",
        value_fn=lambda hub: hub.device.realtime.pv1power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV2Volt": SajModbusSensorEntityDescription(
        name="PV2 voltage",
        key="pv2volt",
        value_fn=lambda hub: hub.device.realtime.pv2volt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "PV2Curr": SajModbusSensorEntityDescription(
        name="PV2 total current",
        key="pv2curr",
        value_fn=lambda hub: hub.device.realtime.pv2curr,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "PV2Power": SajModbusSensorEntityDescription(
        name="PV2 power",
        key="pv2power",
        value_fn=lambda hub: hub.device.realtime.pv2power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PV3Volt": SajModbusSensorEntityDescription(
        name="PV3 voltage",
        key="pv3volt",
        value_fn=lambda hub: hub.device.realtime.pv3volt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "PV3Curr": SajModbusSensorEntityDescription(
        name="PV3 total current",
        key="pv3curr",
        value_fn=lambda hub: hub.device.realtime.pv3curr,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "PV3Power": SajModbusSensorEntityDescription(
        name="PV3 power",
        key="pv3power",
        value_fn=lambda hub: hub.device.realtime.pv3power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "BusVolt": SajModbusSensorEntityDescription(
        name="BUS voltage",
        key="busvolt",
        value_fn=lambda hub: hub.device.realtime.busvolt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "InvTempC": SajModbusSensorEntityDescription(
        name="Inverter temperature",
        key="invtempc",
        value_fn=lambda hub: hub.device.realtime.invtempc,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "GFCI": SajModbusSensorEntityDescription(
        name="GFCI",
        key="gfci",
        value_fn=lambda hub: hub.device.realtime.gfci,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        icon="mdi:current-dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "Power": SajModbusSensorEntityDescription(
        name="Active power of inverter total output",
        key="power",
        value_fn=lambda hub: hub.device.realtime.power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "QPower": SajModbusSensorEntityDescription(
        name="Reactive power of inverter total output",
        key="qpower",
        value_fn=lambda hub: hub.device.realtime.qpower,
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        icon="mdi:flash",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "PF": SajModbusSensorEntityDescription(
        name="Total power factor of inverter",
        key="pf",
        value_fn=lambda hub: hub.device.realtime.pf,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L1Volt": SajModbusSensorEntityDescription(
        name="L1 voltage",
        key="l1volt",
        value_fn=lambda hub: hub.device.realtime.l1volt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L1Curr": SajModbusSensorEntityDescription(
        name="L1 current",
        key="l1curr",
        value_fn=lambda hub: hub.device.realtime.l1curr,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L1Freq": SajModbusSensorEntityDescription(
        name="L1 frequency",
        key="l1freq",
        value_fn=lambda hub: hub.device.realtime.l1freq,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L1DCI": SajModbusSensorEntityDescription(
        name="L1 DC component",
        key="l1dci",
        value_fn=lambda hub: hub.device.realtime.l1dci,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        icon="mdi:current-dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L1Power": SajModbusSensorEntityDescription(
        name="L1 power",
        key="l1power",
        value_fn=lambda hub: hub.device.realtime.l1power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L1PF": SajModbusSensorEntityDescription(
        name="L1 power factor",
        key="l1pf",
        value_fn=lambda hub: hub.device.realtime.l1pf,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L2Volt": SajModbusSensorEntityDescription(
        name="L2 voltage",
        key="l2volt",
        value_fn=lambda hub: hub.device.realtime.l2volt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L2Curr": SajModbusSensorEntityDescription(
        name="L2 current",
        key="l2curr",
        value_fn=lambda hub: hub.device.realtime.l2curr,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L2Freq": SajModbusSensorEntityDescription(
        name="L2 frequency",
        key="l2freq",
        value_fn=lambda hub: hub.device.realtime.l2freq,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L2DCI": SajModbusSensorEntityDescription(
        name="L2 DC component",
        key="l2dci",
        value_fn=lambda hub: hub.device.realtime.l2dci,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        icon="mdi:current-dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L2Power": SajModbusSensorEntityDescription(
        name="L2 power",
        key="l2power",
        value_fn=lambda hub: hub.device.realtime.l2power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L2PF": SajModbusSensorEntityDescription(
        name="L2 power factor",
        key="l2pf",
        value_fn=lambda hub: hub.device.realtime.l2pf,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L3Volt": SajModbusSensorEntityDescription(
        name="L3 voltage",
        key="l3volt",
        value_fn=lambda hub: hub.device.realtime.l3volt,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L3Curr": SajModbusSensorEntityDescription(
        name="L3 current",
        key="l3curr",
        value_fn=lambda hub: hub.device.realtime.l3curr,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L3Freq": SajModbusSensorEntityDescription(
        name="L3 frequency",
        key="l3freq",
        value_fn=lambda hub: hub.device.realtime.l3freq,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L3DCI": SajModbusSensorEntityDescription(
        name="L3 DC component",
        key="l3dci",
        value_fn=lambda hub: hub.device.realtime.l3dci,
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        icon="mdi:current-dc",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "L3Power": SajModbusSensorEntityDescription(
        name="L3 power",
        key="l3power",
        value_fn=lambda hub: hub.device.realtime.l3power,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "L3PF": SajModbusSensorEntityDescription(
        name="L3 power factor",
        key="l3pf",
        value_fn=lambda hub: hub.device.realtime.l3pf,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "ISO1": SajModbusSensorEntityDescription(
        name="PV1+_ISO",
        key="iso1",
        value_fn=lambda hub: hub.device.realtime.iso1,
        native_unit_of_measurement="kΩ",
        icon="mdi:omega",
        entity_registry_enabled_default=False,
    ),
    "ISO2": SajModbusSensorEntityDescription(
        name="PV2+_ISO",
        key="iso2",
        value_fn=lambda hub: hub.device.realtime.iso2,
        native_unit_of_measurement="kΩ",
        icon="mdi:omega",
        entity_registry_enabled_default=False,
    ),
    "ISO3": SajModbusSensorEntityDescription(
        name="PV3+_ISO",
        key="iso3",
        value_fn=lambda hub: hub.device.realtime.iso3,
        native_unit_of_measurement="kΩ",
        icon="mdi:omega",
        entity_registry_enabled_default=False,
    ),
    "ISO4": SajModbusSensorEntityDescription(
        name="PV__ISO",
        key="iso4",
        value_fn=lambda hub: hub.device.realtime.iso4,
        native_unit_of_measurement="kΩ",
        icon="mdi:omega",
        entity_registry_enabled_default=False,
    ),
    "ErrorCount": SajModbusSensorEntityDescription(
        name="Error count",
        key="errorcount",
        value_fn=lambda hub: hub.device.realtime.errorcount,
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
}

DEVICE_STATUSSES = {
    0: "Not Connected",
    1: "Waiting",
    2: "Normal",
    3: "Error",
    4: "Upgrading",
}

FAULT_MESSAGES = {
    0: {
        0x80000000: "Code 81: Lost Communication D<->C",
        0x00080000: "Code 48: Master Fan4 Error",
        0x00040000: "Code 47: Master Fan3 Error",
        0x00020000: "Code 46: Master Fan2 Error",
        0x00010000: "Code 45: Master Fan1 Error",
        0x00002000: "Code 43: Master HW Phase3 Current High",
        0x00001000: "Code 42: Master HW Phase2 Current High",
        0x00000800: "Code 41: Master HW Phase1 Current High",
        0x00000400: "Code 40: Master HWPV2 Current High",
        0x00000200: "Code 39: Master HWPV1 Current High",
        0x00000100: "Code 38: Master HWBus Voltage High",
        0x00000010: "Code 37: Master Phase3 Current High",
        0x00000008: "Code 36: Master Phase2 Current High",
        0x00000004: "Code 35: Master Phase1 Current High",
        0x00000002: "Code 34: Master Bus Voltage Low",
        0x00000001: "Code 33: Master Bus Voltage High",
    },
    1: {
        0x80000000: "Code 32: Master Bus Voltage Balance Error",
        0x40000000: "Code 31: Master ISO Error",
        0x20000000: "Code 30: Master Phase3 DCI Error",
        0x10000000: "Code 29: Master Phase2 DCI Error",
        0x08000000: "Code 28: Master Phase1 DCI Error",
        0x04000000: "Code 27: Master GFCI Error",
        0x02000000: "Code 26: Master Phase3 No Grid Error",
        0x01000000: "Code 25: Master Phase2 No Grid Error",
        0x00800000: "Code 24: Master Phase1 No Grid Error",
        0x00400000: "Code 23: Master Phase3 Frequency Low",
        0x00200000: "Code 22: Master Phase3 Frequency High",
        0x00100000: "Code 21: Master Phase2 Frequency Low",
        0x00080000: "Code 20: Master Phase2 Frequency High",
        0x00040000: "Code 19: Master Phase1 Frequency Low",
        0x00020000: "Code 18: Master Phase1 Frequency High",
        0x00010000: "Code 17: Master Phase3 Voltage 10Min High",
        0x00008000: "Code 16: Master Phase2 Voltage 10Min High",
        0x00004000: "Code 15: Master Phase1 Voltage 10Min High",
        0x00002000: "Code 14: Master Phase3 Voltage Low",
        0x00001000: "Code 13: Master Phase3 Voltage High",
        0x00000800: "Code 12: Master Phase2 Voltage Low",
        0x00000400: "Code 11: Master Phase2 Voltage High",
        0x00000200: "Code 10: Master Phase1 Voltage Low",
        0x00000100: "Code 09: Master Phase1 Voltage High",
        0x00000080: "Code 08: Master Current Sensor Error",
        0x00000040: "Code 07: Master DCI Device Error",
        0x00000020: "Code 06: Master GFCI Device Error",
        0x00000010: "Code 05: Master Lost Communication M<->S",
        0x00000008: "Code 04: Master Temperature Low Error",
        0x00000004: "Code 03: Master Temperature High Error",
        0x00000002: "Code 02: Master EEPROM Error",
        0x00000001: "Code 01: Master Relay Error",
    },
    2: {
        0x40000000: "Code 80: Slave PV Voltage High Error",
        0x20000000: "Code 79: Slave PV2 Current High Error",
        0x10000000: "Code 78: Slave PV1 Current High Error",
        0x08000000: "Code 77: Slave PV2 Voltage High Error",
        0x04000000: "Code 76: Slave PV1 Voltage High Error",
        0x02000000: "Code 75: Slave Phase3 No Grid Error",
        0x01000000: "Code 74: Slave Phase2 No Grid Error",
        0x00800000: "Code 73: Slave Phase1 No Grid Error",
        0x00400000: "Code 72: Slave Phase3 Frequency Low",
        0x00200000: "Code 71: Slave Phase3 Frequency High",
        0x00100000: "Code 70: Slave Phase2 Frequency Low",
        0x00080000: "Code 69: Slave Phase2 Frequency High",
        0x00040000: "Code 68: Slave Phase1 Frequency Low",
        0x00020000: "Code 67: Slave Phase1 Frequency High",
        0x00010000: "Code 66: Slave Phase3 Voltage Low",
        0x00008000: "Code 65: Slave Phase3 Voltage High",
        0x00004000: "Code 64: Slave Phase2 Voltage Low",
        0x00002000: "Code 63: Slave Phase2 Voltage High",
        0x00001000: "Code 62: Slave Phase1 Voltage Low",
        0x00000800: "Code 61: Slave Phase1 Voltage High",
        0x00000400: "Code 60: Slave Phase3 DCI Consis Error",
        0x00000200: "Code 59: Slave Phase2 DCI Consis Error",
        0x00000100: "Code 58: Slave Phase1 DCI Consis Error",
        0x00000080: "Code 57: Slave GFCI Consis Error",
        0x00000040: "Code 56: Slave Phase3 Frequency Consis Error",
        0x00000020: "Code 55: Slave Phase2 Frequency Consis Error",
        0x00000010: "Code 54: Slave Phase1 Frequency Consis Error",
        0x00000008: "Code 53: Slave Phase3 Voltage Consis Error",
        0x00000004: "Code 52: Slave Phase2 Voltage Consis Error",
        0x00000002: "Code 51: Slave Phase1 Voltage Consis Error",
        0x00000001: "Code 50: Slave Lost Communication between M<->S",
    },
}

# R6 3-15K (hybrid) working modes, register 0x4004.
R6_HYBRID_STATUSES = {
    0: "Initialize",
    1: "Waiting",
    2: "Normal",
    3: "Off-grid (battery)",
    4: "Grid + load (battery)",
    5: "Error",
    6: "Upgrading",
    7: "Debug",
    8: "Auto-check",
    9: "Reset",
}

# R6 3-15K fault registers 0x4005/0x4007/0x4009, one bit per fault code.
R6_HYBRID_FAULT_MESSAGES = (
    {  # 0x4005 HFaultMSG: display board / HMI
        0x00000001: "Code 50: Lost Communication H<->M",
        0x00000002: "Code 51: Meter Lost Communication",
        0x00000004: "Code 52: HMI EEPROM Error",
        0x00000008: "Code 53: HMI RTC Error",
        0x00000010: "Code 54: BMS Device Error",
        0x00000020: "Code 55: BMS Lost Communication",
        0x00000040: "Code 56: CT Device Error",
        0x00000080: "Code 57: AFCI Lost Communication",
        0x00000800: "Code 61: R-Phase Grid Voltage High",
        0x00001000: "Code 62: R-Phase Grid Voltage Low",
        0x00002000: "Code 63: S-Phase Grid Voltage High",
        0x00004000: "Code 64: S-Phase Grid Voltage Low",
        0x00008000: "Code 65: T-Phase Grid Voltage High",
        0x00010000: "Code 66: T-Phase Grid Voltage Low",
        0x00020000: "Code 67: Grid Frequency High",
        0x00040000: "Code 68: Grid Frequency Low",
        0x00800000: "Code 73: No Grid",
        0x01000000: "Code 74: PV Input Mode Error",
        0x02000000: "Code 75: PV Hardware Current High",
        0x04000000: "Code 76: PV Voltage High",
        0x08000000: "Code 77: BUS Hardware Voltage High",
        0x80000000: "Code 82: Lost Communication H<->M",
    },
    {  # 0x4007 MFaultMSG: master controller
        0x00000001: "Code 33: Bus Voltage High",
        0x00000002: "Code 34: Bus Voltage Low",
        0x00000004: "Code 35: Grid Phase Error",
        0x00000008: "Code 36: PV Voltage High",
        0x00000010: "Code 37: Islanding Error",
        0x00000020: "Code 83: Arc Device Error",
        0x00000040: "Code 84: PV Input Error",
        0x00000080: "Code 49: Lost Communication DSP<->Meter",
        0x00000100: "Code 38: HW Bus Voltage High",
        0x00000200: "Code 39: HW PV Current High",
        0x00000800: "Code 41: HW Inverter Current High",
        0x00004000: "Code 44: Grid NE Voltage Error",
        0x00008000: "Code 86: DRM0 Error",
        0x00010000: "Code 45: Fan1 Error",
        0x00020000: "Code 46: Fan2 Error",
        0x00040000: "Code 47: Fan3 Error",
        0x00080000: "Code 48: Fan4 Error",
        0x00100000: "Code 87: Arc Error",
        0x00200000: "Code 88: SW PV Current High",
        0x00400000: "Code 89: Battery Voltage High",
        0x00800000: "Code 90: Battery Current High",
        0x01000000: "Code 91: Battery Charge Voltage High",
        0x02000000: "Code 92: Battery Overload",
        0x04000000: "Code 93: Battery Soft-Connect Timeout",
        0x08000000: "Code 94: Output Overload",
        0x10000000: "Code 95: Battery Open Circuit",
        0x20000000: "Code 96: Battery Discharge Voltage Low",
        0x40000000: "Code 85: Authority Expired",
        0x80000000: "Code 81: Lost Communication D<->C",
    },
    {  # 0x4009 MFaultMSG2: master controller 2
        0x00000001: "Code 01: Relay Error",
        0x00000002: "Code 02: EEPROM Error",
        0x00000004: "Code 03: Temperature High",
        0x00000008: "Code 04: Temperature Low",
        0x00000010: "Code 05: Lost Communication M<->S",
        0x00000020: "Code 06: GFCI Device Error",
        0x00000040: "Code 07: DCI Device Error",
        0x00000080: "Code 08: Current Sensor Error",
        0x00000100: "Code 09: Phase1 Voltage High",
        0x00000200: "Code 10: Phase1 Voltage Low",
        0x00000400: "Code 11: Phase2 Voltage High",
        0x00000800: "Code 12: Phase2 Voltage Low",
        0x00001000: "Code 13: Phase3 Voltage High",
        0x00002000: "Code 14: Phase3 Voltage Low",
        0x00004000: "Code 15: Voltage 10Min High",
        0x00008000: "Code 16: Off-Grid Voltage Low",
        0x00020000: "Code 18: Grid Frequency High",
        0x00040000: "Code 19: Grid Frequency Low",
        0x00400000: "Code 21: Phase1 DCV High",
        0x00800000: "Code 22: Phase2 DCV High",
        0x01000000: "Code 23: Phase3 DCV High",
        0x02000000: "Code 24: No Grid Error",
        0x04000000: "Code 27: GFCI Error",
        0x08000000: "Code 28: Phase1 DCI High",
        0x10000000: "Code 29: Phase2 DCI High",
        0x20000000: "Code 30: Phase3 DCI High",
        0x40000000: "Code 31: ISO Error",
        0x80000000: "Code 32: Bus Voltage Balance Error",
    },
)

# R6 17-50K / C6 fault registers 0x6014-0x6019 (three 32-bit words).
R6_HIGH_FAULT_MESSAGES = {
    0: {
        0x80000000: "Code 81: Lost Communication D<->C",
        0x00100000: "Code 87: Master Arc Error",
        0x00080000: "Code 48: Master Fan4 Error",
        0x00040000: "Code 47: Master Fan3 Error",
        0x00020000: "Code 46: Master Fan2 Error",
        0x00010000: "Code 45: Master Fan1 Error",
        0x00008000: "Code 86: Master DRM0 Error",
        0x00004000: "Code 44: Master Grid NE Voltage Error",
        0x00002000: "Code 43: Master DC SPD Error",
        0x00001000: "Code 42: Master AC SPD Error",
        0x00000800: "Code 41: Master HW Current High",
        0x00000200: "Code 39: Master HW PV Current High",
        0x00000100: "Code 38: Master HW Bus Voltage High",
        0x00000040: "Code 84: Master PV Input Error",
        0x00000020: "Code 83: Master Arc Device Error",
        0x00000010: "Code 37: Master Islanding Error",
        0x00000008: "Code 36: Master PV Voltage High",
        0x00000004: "Code 35: Master Grid Phase Error",
        0x00000002: "Code 34: Master Bus Voltage Low",
        0x00000001: "Code 33: Master Bus Voltage High",
    },
    1: {
        0x80000000: "Code 32: Master Bus Voltage Balance Error",
        0x40000000: "Code 31: Master ISO Error",
        0x20000000: "Code 30: Master Phase3 DCI Error",
        0x10000000: "Code 29: Master Phase2 DCI Error",
        0x08000000: "Code 28: Master Phase1 DCI Error",
        0x04000000: "Code 27: Master GFCI Error",
        0x00800000: "Code 24: Master No Grid Error",
        0x00040000: "Code 19: Master Frequency Low",
        0x00020000: "Code 18: Master Frequency High",
        0x00004000: "Code 15: Master Voltage 10Min High",
        0x00002000: "Code 14: Master Phase3 Voltage Low",
        0x00001000: "Code 13: Master Phase3 Voltage High",
        0x00000800: "Code 12: Master Phase2 Voltage Low",
        0x00000400: "Code 11: Master Phase2 Voltage High",
        0x00000200: "Code 10: Master Phase1 Voltage Low",
        0x00000100: "Code 09: Master Phase1 Voltage High",
        0x00000080: "Code 08: Master Current Sensor Error",
        0x00000040: "Code 07: Master DCI Device Error",
        0x00000020: "Code 06: Master GFCI Device Error",
        0x00000008: "Code 04: Master Temperature Low Error",
        0x00000004: "Code 03: Master Temperature High Error",
        0x00000002: "Code 02: Master EEPROM Error",
        0x00000001: "Code 01: Master Relay Error",
    },
    2: {
        0x04000000: "Code 76: Slave PV Voltage High Error",
        0x02000000: "Code 75: HW PV Current High Error",
        0x01000000: "Code 74: PV Input Mode Error",
        0x00800000: "Code 73: Slave No Grid Error",
        0x00040000: "Code 68: Slave Frequency Low",
        0x00020000: "Code 67: Slave Frequency High",
        0x00010000: "Code 66: Slave Phase3 Voltage Low",
        0x00008000: "Code 65: Slave Phase3 Voltage High",
        0x00004000: "Code 64: Slave Phase2 Voltage Low",
        0x00002000: "Code 63: Slave Phase2 Voltage High",
        0x00001000: "Code 62: Slave Phase1 Voltage Low",
        0x00000800: "Code 61: Slave Phase1 Voltage High",
    },
}


def _rt_sensor(
    key: str,
    attr: str,
    name: str,
    *,
    unit: str | None = None,
    device_class: SensorDeviceClass | None = None,
    state_class: SensorStateClass | None = None,
    icon: str | None = None,
    enabled_default: bool = False,
) -> SajModbusSensorEntityDescription:
    """Build a sensor reading ``attr`` off the inverter's realtime component."""
    return SajModbusSensorEntityDescription(
        name=name,
        key=key,
        value_fn=lambda hub, a=attr: getattr(hub.device.realtime, a),
        component="realtime",
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=state_class,
        icon=icon,
        entity_registry_enabled_default=enabled_default,
    )


def _energy_counter(
    key: str,
    attr: str,
    name: str,
    *,
    icon: str = "mdi:solar-power",
    enabled_default: bool = False,
) -> SajModbusSensorEntityDescription:
    """Build a kWh total Home Assistant keeps long-term statistics for."""
    return SajModbusSensorEntityDescription(
        name=name,
        key=key,
        value_fn=lambda hub, a=attr: getattr(hub.device.realtime, a),
        component="realtime",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon=icon,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=enabled_default,
    )


def _hour_counter(
    key: str, attr: str, name: str, *, enabled_default: bool = False
) -> SajModbusSensorEntityDescription:
    """Build a working-hours total Home Assistant keeps statistics for."""
    return SajModbusSensorEntityDescription(
        name=name,
        key=key,
        value_fn=lambda hub, a=attr: getattr(hub.device.realtime, a),
        component="realtime",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:progress-clock",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=enabled_default,
    )


# R6 3-15K (hybrid), realtime block 0x4000. The info registers are shared with
# every family, so those descriptions are reused from SENSOR_TYPES.
R6_HYBRID_SENSOR_TYPES: dict[str, SajModbusSensorEntityDescription] = {
    k: v for k, v in SENSOR_TYPES.items() if v.component == "info"
}
R6_HYBRID_SENSOR_TYPES.update(
    {
        "MPVStatus": SajModbusSensorEntityDescription(
            name="Inverter status",
            key="mpvstatus",
            value_fn=lambda hub: hub.mpvstatus,
            icon="mdi:information-outline",
        ),
        "MPVMode": _rt_sensor(
            "mpvmode",
            "mpvmode",
            "Inverter working mode",
            icon="mdi:information-outline",
        ),
        "FaultMSG": SajModbusSensorEntityDescription(
            name="Inverter error message",
            key="faultmsg",
            value_fn=lambda hub: hub.faultmsg,
            icon="mdi:message-alert-outline",
        ),
        "BMSFaultMSG": _rt_sensor(
            "bmsfaultmsg",
            "bmsfaultmsg",
            "BMS error message",
            icon="mdi:message-alert-outline",
        ),
        "ErrorCount": _rt_sensor(
            "errorcount",
            "errorcount",
            "Error count",
            icon="mdi:counter",
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "DateTime": SajModbusSensorEntityDescription(
            name="Inverter date and time",
            device_class=SensorDeviceClass.TIMESTAMP,
            key="datetime",
            value_fn=lambda hub: hub.device.realtime.datetime,
            icon="mdi:clock-outline",
            entity_registry_enabled_default=False,
        ),
        "SinkTempC": _rt_sensor(
            "sinktempc",
            "sinktempc",
            "Radiator temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "AmbTempC": _rt_sensor(
            "ambtempc",
            "ambtempc",
            "Ambient temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "BatTempC": _rt_sensor(
            "battempc",
            "battempc",
            "Battery temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "GFCI": _rt_sensor(
            "gfci",
            "gfci",
            "GFCI",
            unit=UnitOfElectricCurrent.MILLIAMPERE,
            icon="mdi:current-dc",
            device_class=SensorDeviceClass.CURRENT,
        ),
        "ConnTime": _rt_sensor(
            "conntime",
            "conntime",
            "Grid connection countdown",
            unit=UnitOfTime.SECONDS,
            device_class=SensorDeviceClass.DURATION,
        ),
        "BusVoltMaster": _rt_sensor(
            "busvoltmaster",
            "busvoltmaster",
            "BUS master voltage",
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        "BusVoltSlave": _rt_sensor(
            "busvoltslave",
            "busvoltslave",
            "BUS slave voltage",
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        "BatVolt": _rt_sensor(
            "batvolt",
            "batvolt",
            "Battery voltage",
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        "BatCurr": _rt_sensor(
            "batcurr",
            "batcurr",
            "Battery current",
            unit=UnitOfElectricCurrent.AMPERE,
            icon="mdi:current-dc",
            device_class=SensorDeviceClass.CURRENT,
        ),
        "BatPower": _rt_sensor(
            "batpower",
            "batpower",
            "Battery power",
            unit=UnitOfPower.WATT,
            icon="mdi:battery-charging",
            device_class=SensorDeviceClass.POWER,
            enabled_default=True,
        ),
        "BatSOC": _rt_sensor(
            "batsoc",
            "batsoc",
            "Battery state of charge",
            unit=PERCENTAGE,
            icon="mdi:battery",
            device_class=SensorDeviceClass.BATTERY,
            enabled_default=True,
        ),
        "BatStatus": _rt_sensor(
            "batstatusdisp",
            "batstatusdisp",
            "Battery operating status",
            icon="mdi:battery",
        ),
        "TotalPVPower": _rt_sensor(
            "totalpvpower",
            "totalpvpower",
            "PV total power",
            unit=UnitOfPower.WATT,
            icon="mdi:solar-power",
            device_class=SensorDeviceClass.POWER,
            enabled_default=True,
        ),
        "TotalBatteryPower": _rt_sensor(
            "totalbatterypower",
            "totalbatterypower",
            "Battery total power",
            unit=UnitOfPower.WATT,
            icon="mdi:battery-charging",
            device_class=SensorDeviceClass.POWER,
            enabled_default=True,
        ),
        "TotalGridPowerWatt": _rt_sensor(
            "totalgridpowerwatt",
            "totalgridpowerwatt",
            "Grid total active power",
            unit=UnitOfPower.WATT,
            icon="mdi:transmission-tower",
            device_class=SensorDeviceClass.POWER,
            enabled_default=True,
        ),
        "TotalInvPowerWatt": _rt_sensor(
            "totalinvpowerwatt",
            "totalinvpowerwatt",
            "Inverter total active power",
            unit=UnitOfPower.WATT,
            icon="mdi:solar-power",
            device_class=SensorDeviceClass.POWER,
            enabled_default=True,
        ),
        "SysTotalLoadWatt": _rt_sensor(
            "systotalloadwatt",
            "systotalloadwatt",
            "Total system load power",
            unit=UnitOfPower.WATT,
            icon="mdi:home-lightning-bolt",
            device_class=SensorDeviceClass.POWER,
            enabled_default=True,
        ),
        "SysGridPowerWall": _rt_sensor(
            "sysgridpowerwall",
            "sysgridpowerwall",
            "System grid power",
            unit=UnitOfPower.WATT,
            icon="mdi:transmission-tower",
            device_class=SensorDeviceClass.POWER,
        ),
        "PVConsumpWatt": _rt_sensor(
            "pvconsumpwatt",
            "pvconsumpwatt",
            "Power from PV to the load",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        "GridConsumpWatt": _rt_sensor(
            "gridconsumpwatt",
            "gridconsumpwatt",
            "Power from the grid to the load",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        "GridFeedInPVWatt": _rt_sensor(
            "gridfeedinpvwatt",
            "gridfeedinpvwatt",
            "Power from PV to the grid",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        "GridFeedInBatWatt": _rt_sensor(
            "gridfeedinbatwatt",
            "gridfeedinbatwatt",
            "Power from the battery to the grid",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        "BatConsumpWatt": _rt_sensor(
            "batconsumpwatt",
            "batconsumpwatt",
            "Power from the battery to the load",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        "BatChgPVWatt": _rt_sensor(
            "batchgpvwatt",
            "batchgpvwatt",
            "Charging power from PV to the battery",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
        "BatChgGridWatt": _rt_sensor(
            "batchggridwatt",
            "batchggridwatt",
            "Charging power from the grid to the battery",
            unit=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
        ),
    }
)
for _iso in range(1, 5):
    R6_HYBRID_SENSOR_TYPES[f"ISO{_iso}"] = _rt_sensor(
        f"iso{_iso}",
        f"iso{_iso}",
        f"PV{_iso}+_ISO" if _iso < 4 else "PV__ISO",
        unit="kΩ",
        icon="mdi:omega",
    )
for _ph, _label in (("r", "R"), ("s", "S"), ("t", "T")):
    R6_HYBRID_SENSOR_TYPES[f"{_label}GridVolt"] = _rt_sensor(
        f"{_ph}gridvolt",
        f"{_ph}gridvolt",
        f"{_label}-phase grid voltage",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}GridCurr"] = _rt_sensor(
        f"{_ph}gridcurr",
        f"{_ph}gridcurr",
        f"{_label}-phase grid current",
        unit=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}GridFreq"] = _rt_sensor(
        f"{_ph}gridfreq",
        f"{_ph}gridfreq",
        f"{_label}-phase grid frequency",
        unit=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}GridPower"] = _rt_sensor(
        f"{_ph}gridpowerwatt",
        f"{_ph}gridpowerwatt",
        f"{_label}-phase grid power",
        unit=UnitOfPower.WATT,
        icon="mdi:transmission-tower",
        device_class=SensorDeviceClass.POWER,
        enabled_default=True,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}InvVolt"] = _rt_sensor(
        f"{_ph}invvolt",
        f"{_ph}invvolt",
        f"{_label}-phase inverter voltage",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}InvCurr"] = _rt_sensor(
        f"{_ph}invcurr",
        f"{_ph}invcurr",
        f"{_label}-phase inverter current",
        unit=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}InvPower"] = _rt_sensor(
        f"{_ph}invpowerwatt",
        f"{_ph}invpowerwatt",
        f"{_label}-phase inverter power",
        unit=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}OutVolt"] = _rt_sensor(
        f"{_ph}outvolt",
        f"{_ph}outvolt",
        f"{_label}-phase output voltage",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}OutCurr"] = _rt_sensor(
        f"{_ph}outcurr",
        f"{_ph}outcurr",
        f"{_label}-phase output current",
        unit=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}OutFreq"] = _rt_sensor(
        f"{_ph}outfreq",
        f"{_ph}outfreq",
        f"{_label}-phase output frequency",
        unit=UnitOfFrequency.HERTZ,
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
    )
    R6_HYBRID_SENSOR_TYPES[f"{_label}OutPower"] = _rt_sensor(
        f"{_ph}outpowerwatt",
        f"{_ph}outpowerwatt",
        f"{_label}-phase output power",
        unit=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
    )
for _pv in range(1, 5):
    R6_HYBRID_SENSOR_TYPES[f"PV{_pv}Volt"] = _rt_sensor(
        f"pv{_pv}volt",
        f"pv{_pv}volt",
        f"PV{_pv} voltage",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    )
    R6_HYBRID_SENSOR_TYPES[f"PV{_pv}Curr"] = _rt_sensor(
        f"pv{_pv}curr",
        f"pv{_pv}curr",
        f"PV{_pv} total current",
        unit=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
    )
    R6_HYBRID_SENSOR_TYPES[f"PV{_pv}Power"] = _rt_sensor(
        f"pv{_pv}power",
        f"pv{_pv}power",
        f"PV{_pv} power",
        unit=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
        enabled_default=_pv == 1,
    )
    for _str in range(1, 5):
        R6_HYBRID_SENSOR_TYPES[f"PV{_pv}StrCurr{_str}"] = _rt_sensor(
            f"pv{_pv}strcurr{_str}",
            f"pv{_pv}strcurr{_str}",
            f"PV{_pv} string current {_str}",
            unit=UnitOfElectricCurrent.AMPERE,
            icon="mdi:current-dc",
            device_class=SensorDeviceClass.CURRENT,
        )

R6_HYBRID_COUNTER_SENSOR_TYPES: dict[str, SajModbusSensorEntityDescription] = {
    "TodayHour": _hour_counter(
        "todayhour", "todayhour", "Daily generating hours", enabled_default=True
    ),
    "TotalHour": _hour_counter(
        "totalhour", "totalhour", "Total generating hours", enabled_default=True
    ),
    "TodayPVEnergy": _energy_counter(
        "todaypvenergy",
        "todaypvenergy",
        "PV generation on current day",
        enabled_default=True,
    ),
    "MonthPVEnergy": _energy_counter(
        "monthpvenergy", "monthpvenergy", "PV generation in current month"
    ),
    "YearPVEnergy": _energy_counter(
        "yearpvenergy", "yearpvenergy", "PV generation in current year"
    ),
    "TotalPVEnergy": _energy_counter(
        "totalpvenergy", "totalpvenergy", "Total PV generation", enabled_default=True
    ),
    "TodayBatChgEnergy": _energy_counter(
        "todaybatchgenergy",
        "todaybatchgenergy",
        "Battery charged today",
        icon="mdi:battery-charging",
    ),
    "MonthBatChgEnergy": _energy_counter(
        "monthbatchgenergy",
        "monthbatchgenergy",
        "Battery charged in current month",
        icon="mdi:battery-charging",
    ),
    "YearBatChgEnergy": _energy_counter(
        "yearbatchgenergy",
        "yearbatchgenergy",
        "Battery charged in current year",
        icon="mdi:battery-charging",
    ),
    "TotalBatChgEnergy": _energy_counter(
        "totalbatchgenergy",
        "totalbatchgenergy",
        "Total battery charge",
        icon="mdi:battery-charging",
    ),
    "TodayBatDisEnergy": _energy_counter(
        "todaybatdisenergy",
        "todaybatdisenergy",
        "Battery discharged today",
        icon="mdi:battery-minus",
    ),
    "MonthBatDisEnergy": _energy_counter(
        "monthbatdisenergy",
        "monthbatdisenergy",
        "Battery discharged in current month",
        icon="mdi:battery-minus",
    ),
    "YearBatDisEnergy": _energy_counter(
        "yearbatdisenergy",
        "yearbatdisenergy",
        "Battery discharged in current year",
        icon="mdi:battery-minus",
    ),
    "TotalBatDisEnergy": _energy_counter(
        "totalbatdisenergy",
        "totalbatdisenergy",
        "Total battery discharge",
        icon="mdi:battery-minus",
    ),
    "TodayInvGenEnergy": _energy_counter(
        "todayinvgenenergy", "todayinvgenenergy", "Inverter generation on current day"
    ),
    "MonthInvGenEnergy": _energy_counter(
        "monthinvgenenergy", "monthinvgenenergy", "Inverter generation in current month"
    ),
    "YearInvGenEnergy": _energy_counter(
        "yearinvgenenergy", "yearinvgenenergy", "Inverter generation in current year"
    ),
    "TotalInvGenEnergy": _energy_counter(
        "totalinvgenenergy", "totalinvgenenergy", "Total inverter generation"
    ),
    "TodayLoadEnergy": _energy_counter(
        "todaytotalloadenergy",
        "todaytotalloadenergy",
        "Load consumption on current day",
        icon="mdi:home-lightning-bolt",
    ),
    "MonthLoadEnergy": _energy_counter(
        "monthtotalloadenergy",
        "monthtotalloadenergy",
        "Load consumption in current month",
        icon="mdi:home-lightning-bolt",
    ),
    "YearLoadEnergy": _energy_counter(
        "yeartotalloadenergy",
        "yeartotalloadenergy",
        "Load consumption in current year",
        icon="mdi:home-lightning-bolt",
    ),
    "TotalLoadEnergy": _energy_counter(
        "totaltotalloadenergy",
        "totaltotalloadenergy",
        "Total load consumption",
        icon="mdi:home-lightning-bolt",
    ),
    "TodaySellEnergy": _energy_counter(
        "todaysellenergy",
        "todaysellenergy",
        "Sold energy on current day",
        icon="mdi:transmission-tower-export",
    ),
    "MonthSellEnergy": _energy_counter(
        "monthsellenergy",
        "monthsellenergy",
        "Sold energy in current month",
        icon="mdi:transmission-tower-export",
    ),
    "YearSellEnergy": _energy_counter(
        "yearsellenergy",
        "yearsellenergy",
        "Sold energy in current year",
        icon="mdi:transmission-tower-export",
    ),
    "TotalSellEnergy": _energy_counter(
        "totalsellenergy",
        "totalsellenergy",
        "Total sold energy",
        icon="mdi:transmission-tower-export",
    ),
    "TodayFeedInEnergy": _energy_counter(
        "todayfeedinenergy",
        "todayfeedinenergy",
        "Feed-in energy on current day",
        icon="mdi:transmission-tower-import",
    ),
    "MonthFeedInEnergy": _energy_counter(
        "monthfeedinenergy",
        "monthfeedinenergy",
        "Feed-in energy in current month",
        icon="mdi:transmission-tower-import",
    ),
    "YearFeedInEnergy": _energy_counter(
        "yearfeedinenergy",
        "yearfeedinenergy",
        "Feed-in energy in current year",
        icon="mdi:transmission-tower-import",
    ),
    "TotalFeedInEnergy": _energy_counter(
        "totalfeedinenergy",
        "totalfeedinenergy",
        "Total feed-in energy",
        icon="mdi:transmission-tower-import",
    ),
}

# R6 17-50K / C6, realtime block 0x6000. It reuses the R5 descriptions whose
# field names exist on the R6 map (all but the single inverter temperature),
# and adds the R6-only inputs.
R6_HIGH_SENSOR_TYPES: dict[str, SajModbusSensorEntityDescription] = {
    k: v for k, v in SENSOR_TYPES.items() if k != "InvTempC"
}
R6_HIGH_SENSOR_TYPES.update(
    {
        "ConnTime": _rt_sensor(
            "conntime",
            "conntime",
            "Grid connection countdown",
            unit=UnitOfTime.SECONDS,
            device_class=SensorDeviceClass.DURATION,
        ),
        "NEVolt": _rt_sensor(
            "nevolt",
            "nevolt",
            "N-line voltage to earth",
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        "BusVoltM": _rt_sensor(
            "busvoltm",
            "busvoltm",
            "BUS mid-point voltage",
            unit=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
        ),
        "InvTempC1": _rt_sensor(
            "invtempc1",
            "invtempc1",
            "Radiator temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "InvTempCL1": _rt_sensor(
            "invtempc_l1",
            "invtempc_l1",
            "L1 phase temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "InvTempCL2": _rt_sensor(
            "invtempc_l2",
            "invtempc_l2",
            "L2 phase temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "InvTempCL3": _rt_sensor(
            "invtempc_l3",
            "invtempc_l3",
            "L3 phase temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
        "InvTempCCavity": _rt_sensor(
            "invtempc_cavity",
            "invtempc_cavity",
            "Cavity temperature",
            unit=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
        ),
    }
)
for _pv in range(4, 13):
    R6_HIGH_SENSOR_TYPES[f"PV{_pv}Volt"] = _rt_sensor(
        f"pv{_pv}volt",
        f"pv{_pv}volt",
        f"PV{_pv} voltage",
        unit=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
    )
    R6_HIGH_SENSOR_TYPES[f"PV{_pv}Curr"] = _rt_sensor(
        f"pv{_pv}curr",
        f"pv{_pv}curr",
        f"PV{_pv} current",
        unit=UnitOfElectricCurrent.AMPERE,
        icon="mdi:current-ac",
        device_class=SensorDeviceClass.CURRENT,
    )
    R6_HIGH_SENSOR_TYPES[f"PV{_pv}Power"] = _rt_sensor(
        f"pv{_pv}power",
        f"pv{_pv}power",
        f"PV{_pv} power",
        unit=UnitOfPower.WATT,
        icon="mdi:solar-power",
        device_class=SensorDeviceClass.POWER,
    )
for _pv in range(1, 13):
    for _str in (1, 2):
        R6_HIGH_SENSOR_TYPES[f"PV{_pv}StrCurr{_str}"] = _rt_sensor(
            f"pv{_pv}strcurr{_str}",
            f"pv{_pv}strcurr{_str}",
            f"PV{_pv} string current {_str}",
            unit=UnitOfElectricCurrent.AMPERE,
            icon="mdi:current-dc",
            device_class=SensorDeviceClass.CURRENT,
        )

# Which sensor sets an inverter family gets, picked by the detected family.
SENSORS_BY_FAMILY: dict[str, tuple[dict, dict]] = {
    FAMILY_R5: (SENSOR_TYPES, COUNTER_SENSOR_TYPES),
    FAMILY_R6_HYBRID: (R6_HYBRID_SENSOR_TYPES, R6_HYBRID_COUNTER_SENSOR_TYPES),
    FAMILY_R6_HIGH: (R6_HIGH_SENSOR_TYPES, COUNTER_SENSOR_TYPES),
}
