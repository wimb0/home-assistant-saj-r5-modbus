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
