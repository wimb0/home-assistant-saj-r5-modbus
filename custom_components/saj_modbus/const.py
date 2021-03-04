DOMAIN = "saj_modbus"
DEFAULT_NAME = "saj"
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_PORT = 2020
CONF_SAJEDGE_HUB = "saj_hub"
ATTR_STATUS_DESCRIPTION = "status_description"
ATTR_MANUFACTURER = "SAJ"

SENSOR_TYPES = {
    "MPVMode": ["Inverter working mode", "mpvmode", None, None],
    "FaultMSG": ["Inverter error message", "faultmsg",  None, None"],
    "PV1Volt": ["PV1 voltage", "pv1volt", "V", None],
    "PV1Curr": ["PV1 total current", "pv1curr", "A", "mdi:current-ac"],
    "PV1Power": ["PV1 power", "pv1power", "W", "mdi:solar-power"],
    "PV2Volt": ["PV2 voltage", "pv2volt", "V", None],
    "PV2Curr": ["PV2 total current", "pv2curr", "A", "mdi:current-ac"],
    "PV2Power": ["PV2 power", "pv2power", "W", "mdi:solar-power"],
    "PV3Volt": ["PV3 voltage", "pv3volt", "V", None],
    "PV3Curr": ["PV3 total current", "pv3curr", "A", "mdi:current-ac"],
    "PV3Power": ["PV3 power", "pv3power", "W", "mdi:solar-power"],
    "BusVolt": ["BUS voltage", "busvolt", "V", None],
    "InvTempC": ["Inverter temperature", "invtempc", "°C", None],
    "GFCI": ["GFCI", "gfci", "mA", "mdi:current-dc"],
    "Power": ["Active power of inverter total output", "power", "W", "mdi:solar-power"],
    "QPower": ["Reactive power of inverter total output", "qpower", "VAR", None],
    "PF": ["Total power factor of inverter", "pf",  None, None"],
    "L1Volt": ["L1 voltage", "l1volt", "V", None],
    "L1Curr": ["L1 current", "l1curr", "A", "mdi:current-ac"],
    "L1Freq": ["L1 frequency", "l1freq", "Hz", None],
    "L1DCI": ["L1 DC component", "l1dci", "mA", "mdi:current-dc"],
    "L1Power": ["L1 power", "l1power", "W", "mdi:solar-power"],   
    "L1PF": ["L1 power factor", "l1pf",  None, None"],
    "L2Volt": ["L2 voltage", "l2volt", "V", None],
    "L2Curr": ["L2 current", "l2curr", "A", "mdi:current-ac"],
    "L2Freq": ["L2 frequency", "l2frew", "Hz", None],
    "L2DCI": ["L2 DC component", "l2dci", "mA", "mdi:current-dc"],
    "L2Power": ["L2 power", "l2power", "W", "mdi:solar-power"],   
    "L2PF": ["L2 power factor", "l2pf",  None, None"],
    "L3Volt": ["L3 voltage", "l3volt", "V", None],
    "L3Curr": ["L3 current", "l3curr", "A", "mdi:current-ac"],
    "L3Freq": ["L3 frequency", "l3frew", "Hz", None],
    "L3DCI": ["L3 DC component", "l3dci", "mA", "mdi:current-dc"],
    "L3Power": ["L3 power", "l3power", "W", "mdi:solar-power"],   
    "L3PF": ["L3 power factor", "l3pf",  None, None"],
    "ISO1": ["PV1+_ISO", "iso1", "kΩ", None"],
    "ISO2": ["PV2+_ISO", "iso2", "kΩ", None"],
    "ISO3": ["PV3+_ISO", "iso3", "kΩ", None"],
    "ISO4": ["PV__ISO", "iso4", "kΩ", None"],
    "TodayEnergy": ["Power generation on current day", "todayenergy", "kWh", None],   
    "MonthEnergy": ["Power generation in current month", "monthenergy", "kWh", None],   
    "YearEnergy": ["Power generation in current year", "yearenergy", "kWh", None],   
    "TotalEnergy": ["Total power generation", "totalenergy", "kWh", None],
    "TodayHour": ["Daily working hours", "todayhour", "h", None],
    "TotalHour": ["Total working hours", "totalhour", "h", None],
    "ErrorCount": ["Error count", "errorcount", None, None],   
    "Time": ["Current time", "time", None, None],   
}

DEVICE_STATUSSES = {
    0: "Not Connected"
    1: "Waiting",
    2: "Normal",
    3: "Error",
    4: "Upgrading",
}
