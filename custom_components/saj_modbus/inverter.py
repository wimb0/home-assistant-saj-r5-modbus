"""Device model for the SAJ R5 inverter, built on modbus-connection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
    ModbusSerialParams,
    ModbusTcpParams,
    ModbusTimeoutError,
    ModbusUnit,
)
from modbus_connection.model import (
    Component,
    ComponentGroup,
    RegisterField,
    boolean,
    gauge,
    int32,
    integer,
    string,
    uint32,
)
from modbus_connection.tmodbus import ModbusConnection

from .const import FAMILIES, FAMILY_R5, FAMILY_R6_HIGH, FAMILY_R6_HYBRID

_LOGGER = logging.getLogger(__name__)

# The R5 responds on a fixed station address; it is not user-configurable.
UNIT_ID = 1
MODBUS_TIMEOUT = 5

# The refusals that mean the registers are not in this inverter's map. Every
# other exception response says the registers are there and the read failed,
# so those propagate.
_NOT_SERVED = (IllegalFunctionError, IllegalDataAddressError)

# DeviceType (0x8F00) values the documents assign to the PLUS / R5 families.
_R5_DEVTYPES = frozenset({0x11, 0x12, 0x13, 0x14, 0x15, 0x21, 0x22})

# One probe register per family, tried in order when the device type is not
# one of the known R5 values: R6 3-15K answers 0x4004, R6 17-50K / C6 answers
# 0x6013, PLUS / R5 answers 0x100.
_FAMILY_PROBES = (
    (0x4004, FAMILY_R6_HYBRID),
    (0x6013, FAMILY_R6_HIGH),
    (0x100, FAMILY_R5),
)

# Every component attribute a poll may refresh, in read order. A timeout on
# the first one ends the poll, so the block worth waiting for leads. The
# information is static, so setup reads it and polling never does.
_POLLED = ("realtime", "power")


async def detect_family(unit: ModbusUnit, devtype: int | None) -> str:
    """Work out which inverter family sits behind ``unit``.

    A known R5 device type decides immediately; anything else is settled by
    probing one realtime register per family and seeing which block answers.
    When nothing refuses, the R5 block is the default.
    """
    if devtype in _R5_DEVTYPES:
        return FAMILY_R5
    for address, family in _FAMILY_PROBES:
        try:
            await unit.read_holding_registers(address, 1)
        except _NOT_SERVED:
            continue
        return family
    return FAMILY_R5


@dataclass(frozen=True)
class ProbeResult:
    """What the config flow learns from an inverter before creating an entry."""

    serial: str
    family: str
    devtype: int | None


@dataclass(frozen=True)
class UpdateReport:
    """What one poll refreshed, by the device's component attribute names.

    A failed component kept its previous values and did not notify; the error
    that failed it rides along. An inverter that answered nothing at all is
    never in here — the update raises rather than reporting total silence.
    """

    updated: set[str]
    failed: dict[str, ModbusError]

    @property
    def complete(self) -> bool:
        """Whether every polled component refreshed."""
        return not self.failed


def create_connection(host: str, port: int) -> ModbusConnection:
    """Create a TCP inverter connection, shared by entry setup and the config flow."""
    return ModbusConnection(
        ModbusTcpParams(host=host, port=port), timeout=MODBUS_TIMEOUT
    )


def create_serial_connection(
    device: str,
    baudrate: int = 9600,
    bytesize: int = 8,
    parity: str = "N",
    stopbits: int = 1,
) -> ModbusConnection:
    """Create a serial (RTU) inverter connection.

    ``device`` is a local port (``/dev/ttyUSB0``) or a serial-over-network
    URL (``socket://host:port``, ``rfc2217://host:port``). Framing is fixed
    to RTU: that is what the SAJ RS485 port speaks.
    """
    return ModbusConnection(
        ModbusSerialParams(
            device=device,
            baudrate=baudrate,
            bytesize=bytesize,  # type: ignore[arg-type]
            parity=parity,  # type: ignore[arg-type]
            stopbits=stopbits,  # type: ignore[arg-type]
            framer="rtu",
        ),
        timeout=MODBUS_TIMEOUT,
    )


def params_from_config(data: dict[str, Any]) -> ModbusTcpParams | ModbusSerialParams:
    """Build backend-neutral connection params from a config entry's data.

    Entries written before serial support have no connection type and are TCP.
    Serial line settings are fixed to 8 data bits, no parity and 1 stop bit;
    only the port and the baud rate come from the entry.
    """
    from .const import (  # deferred: const only imports this module for typing
        CONF_BAUDRATE,
        CONF_CONNECTION_TYPE,
        CONF_SERIAL_PORT,
        CONNECTION_TYPE_SERIAL,
        DEFAULT_BAUDRATE,
        DEFAULT_BYTESIZE,
        DEFAULT_PARITY,
        DEFAULT_STOPBITS,
        DEFAULT_PORT,
    )
    from homeassistant.const import CONF_HOST, CONF_PORT

    if data.get(CONF_CONNECTION_TYPE) == CONNECTION_TYPE_SERIAL:
        return ModbusSerialParams(
            device=data[CONF_SERIAL_PORT],
            baudrate=data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
            bytesize=DEFAULT_BYTESIZE,  # type: ignore[arg-type]
            parity=DEFAULT_PARITY,  # type: ignore[arg-type]
            stopbits=DEFAULT_STOPBITS,  # type: ignore[arg-type]
            framer="rtu",
        )
    return ModbusTcpParams(host=data[CONF_HOST], port=data.get(CONF_PORT, DEFAULT_PORT))


class DateTimeField(RegisterField[datetime]):
    """The inverter's clock: year word, then month/day, hour/minute, second bytes."""

    def decode(
        self, words: list[int], scale_exponent: int | None = None
    ) -> datetime | None:
        """Decode the packed clock registers into a local-timezone datetime."""
        try:
            return datetime(
                year=words[0],
                month=words[1] >> 8,
                day=words[1] & 0xFF,
                hour=words[2] >> 8,
                minute=words[2] & 0xFF,
                second=words[3] >> 8,
            ).astimezone()
        except ValueError:
            # An unset or corrupted clock (e.g. year 0) is not a datetime.
            return None

    def encode(self, value: Any, scale_exponent: int | None = None) -> list[int]:
        """Pack a datetime into the inverter's clock register layout."""
        return [
            value.year,
            (value.month << 8) + value.day,
            (value.hour << 8) + value.minute,
            value.second << 8,
        ]


class InverterInfo(Component):
    """Static device information, read once at setup."""

    devtype = integer(0x8F00, signed=False)
    subtype = integer(0x8F01, signed=False)
    commver = gauge(0x8F02, 0.001, signed=False)
    sn = string(0x8F03, 10)
    pc = string(0x8F0D, 10)
    dv = gauge(0x8F17, 0.001, signed=False)
    mcv = gauge(0x8F18, 0.001, signed=False)
    scv = gauge(0x8F19, 0.001, signed=False)
    disphwversion = gauge(0x8F1A, 0.001, signed=False)
    ctrlhwversion = gauge(0x8F1B, 0.001, signed=False)
    powerhwversion = gauge(0x8F1C, 0.001, signed=False)


class RealtimeData(Component):
    """Realtime inverter data, polled every update cycle."""

    mpvmode = integer(0x100, signed=False)
    faultmsg0 = uint32(0x101)
    faultmsg1 = uint32(0x103)
    faultmsg2 = uint32(0x105)
    pv1volt = gauge(0x107, 0.1, signed=False)
    pv1curr = gauge(0x108, 0.01, signed=False)
    pv1power = integer(0x109, signed=False)
    pv2volt = gauge(0x10A, 0.1, signed=False)
    pv2curr = gauge(0x10B, 0.01, signed=False)
    pv2power = integer(0x10C, signed=False)
    pv3volt = gauge(0x10D, 0.1, signed=False)
    pv3curr = gauge(0x10E, 0.01, signed=False)
    pv3power = integer(0x10F, signed=False)
    busvolt = gauge(0x110, 0.1, signed=False)
    invtempc = gauge(0x111, 0.1)
    gfci = integer(0x112)
    power = integer(0x113, signed=False)
    qpower = integer(0x114)
    pf = gauge(0x115, 0.001)
    l1volt = gauge(0x116, 0.1, signed=False)
    l1curr = gauge(0x117, 0.01, signed=False)
    l1freq = gauge(0x118, 0.01, signed=False)
    l1dci = integer(0x119)
    l1power = integer(0x11A, signed=False)
    l1pf = gauge(0x11B, 0.001)
    l2volt = gauge(0x11C, 0.1, signed=False)
    l2curr = gauge(0x11D, 0.01, signed=False)
    l2freq = gauge(0x11E, 0.01, signed=False)
    l2dci = integer(0x11F)
    l2power = integer(0x120, signed=False)
    l2pf = gauge(0x121, 0.001)
    l3volt = gauge(0x122, 0.1, signed=False)
    l3curr = gauge(0x123, 0.01, signed=False)
    l3freq = gauge(0x124, 0.01, signed=False)
    l3dci = integer(0x125)
    l3power = integer(0x126, signed=False)
    l3pf = gauge(0x127, 0.001)
    iso1 = integer(0x128, signed=False)
    iso2 = integer(0x129, signed=False)
    iso3 = integer(0x12A, signed=False)
    iso4 = integer(0x12B, signed=False)
    todayenergy = gauge(0x12C, 0.01, signed=False)
    monthenergy = uint32(0x12D, scale=0.01)
    yearenergy = uint32(0x12F, scale=0.01)
    totalenergy = uint32(0x131, scale=0.01)
    todayhour = gauge(0x133, 0.1, signed=False)
    totalhour = uint32(0x134, scale=0.1)
    errorcount = integer(0x136, signed=False)
    datetime = DateTimeField(0x137, count=4)


class R6HybridData(Component):
    """R6 3-15K (hybrid) realtime data, block 0x4000-0x40FD."""

    datetime = DateTimeField(0x4000, count=4)
    mpvmode = integer(0x4004, signed=False)
    hfaultmsg = uint32(0x4005)
    mfaultmsg = uint32(0x4007)
    mfaultmsg2 = uint32(0x4009)
    bmsfaultmsg = uint32(0x400B)
    errorcount = integer(0x400F, signed=False)
    sinktempc = gauge(0x4010, 0.1)
    ambtempc = gauge(0x4011, 0.1)
    gfci = integer(0x4012)
    iso1 = integer(0x4013, signed=False)
    iso2 = integer(0x4014, signed=False)
    iso3 = integer(0x4015, signed=False)
    iso4 = integer(0x4016, signed=False)
    conntime = integer(0x4019, signed=False)
    batstatusdisp = integer(0x4027, signed=False)
    busvoltmaster = gauge(0x4067, 0.1, signed=False)
    busvoltslave = gauge(0x4068, 0.1, signed=False)
    batvolt = gauge(0x4069, 0.1, signed=False)
    batcurr = gauge(0x406A, 0.01)
    batpower = integer(0x406D)
    battempc = gauge(0x406E, 0.1)
    batsoc = gauge(0x406F, 0.01, signed=False)
    pvconsumpwatt = integer(0x4099)
    gridconsumpwatt = integer(0x409A)
    gridfeedinpvwatt = integer(0x409B)
    gridfeedinbatwatt = integer(0x409C)
    batconsumpwatt = integer(0x409D)
    batchgpvwatt = integer(0x409E)
    batchggridwatt = integer(0x409F)
    systotalloadwatt = integer(0x40A0)
    totalpvpower = integer(0x40A5)
    totalbatterypower = integer(0x40A6)
    totalgridpowerwatt = integer(0x40A7)
    totalinvpowerwatt = integer(0x40A9)
    sysgridpowerwall = integer(0x40AD)
    todayhour = gauge(0x40BC, 0.1, signed=False)
    totalhour = uint32(0x40BD, scale=0.1)
    todaypvenergy = uint32(0x40BF, scale=0.01)
    monthpvenergy = uint32(0x40C1, scale=0.01)
    yearpvenergy = uint32(0x40C3, scale=0.01)
    totalpvenergy = uint32(0x40C5, scale=0.01)
    todaybatchgenergy = uint32(0x40C7, scale=0.01)
    monthbatchgenergy = uint32(0x40C9, scale=0.01)
    yearbatchgenergy = uint32(0x40CB, scale=0.01)
    totalbatchgenergy = uint32(0x40CD, scale=0.01)
    todaybatdisenergy = uint32(0x40CF, scale=0.01)
    monthbatdisenergy = uint32(0x40D1, scale=0.01)
    yearbatdisenergy = uint32(0x40D3, scale=0.01)
    totalbatdisenergy = uint32(0x40D5, scale=0.01)
    todayinvgenenergy = uint32(0x40D7, scale=0.01)
    monthinvgenenergy = uint32(0x40D9, scale=0.01)
    yearinvgenenergy = uint32(0x40DB, scale=0.01)
    totalinvgenenergy = uint32(0x40DD, scale=0.01)
    todaytotalloadenergy = uint32(0x40DF, scale=0.01)
    monthtotalloadenergy = uint32(0x40E1, scale=0.01)
    yeartotalloadenergy = uint32(0x40E3, scale=0.01)
    totaltotalloadenergy = uint32(0x40E5, scale=0.01)
    todaysellenergy = uint32(0x40EF, scale=0.01)
    monthsellenergy = uint32(0x40F1, scale=0.01)
    yearsellenergy = uint32(0x40F3, scale=0.01)
    totalsellenergy = uint32(0x40F5, scale=0.01)
    todayfeedinenergy = uint32(0x40F7, scale=0.01)
    monthfeedinenergy = uint32(0x40F9, scale=0.01)
    yearfeedinenergy = uint32(0x40FB, scale=0.01)
    totalfeedinenergy = uint32(0x40FD, scale=0.01)

    for _ph, _base in (("r", 0x4031), ("s", 0x4038), ("t", 0x403F)):
        locals()[f"{_ph}gridvolt"] = gauge(_base, 0.1, signed=False)
        locals()[f"{_ph}gridcurr"] = gauge(_base + 1, 0.01)
        locals()[f"{_ph}gridfreq"] = gauge(_base + 2, 0.01, signed=False)
        locals()[f"{_ph}gridpowerwatt"] = integer(_base + 4)
    for _ph, _base in (("r", 0x4046), ("s", 0x404B), ("t", 0x4050)):
        locals()[f"{_ph}invvolt"] = gauge(_base, 0.1, signed=False)
        locals()[f"{_ph}invcurr"] = gauge(_base + 1, 0.01)
        locals()[f"{_ph}invpowerwatt"] = integer(_base + 3)
    for _ph, _base in (("r", 0x4055), ("s", 0x405B), ("t", 0x4061)):
        locals()[f"{_ph}outvolt"] = gauge(_base, 0.1, signed=False)
        locals()[f"{_ph}outcurr"] = gauge(_base + 1, 0.01)
        locals()[f"{_ph}outfreq"] = gauge(_base + 2, 0.01, signed=False)
        locals()[f"{_ph}outpowerwatt"] = integer(_base + 4)
    for _pv, _base in ((1, 0x4071), (2, 0x4074), (3, 0x4077), (4, 0x407A)):
        locals()[f"pv{_pv}volt"] = gauge(_base, 0.1, signed=False)
        locals()[f"pv{_pv}curr"] = gauge(_base + 1, 0.01, signed=False)
        locals()[f"pv{_pv}power"] = integer(_base + 2, signed=False)
    for _pv in range(1, 5):
        for _str in range(1, 5):
            locals()[f"pv{_pv}strcurr{_str}"] = gauge(
                0x407D + (_pv - 1) * 4 + (_str - 1), 0.01, signed=False
            )


class R6HighData(Component):
    """R6 17-50K / C6 realtime data, block 0x6000-0x6080."""

    datetime = DateTimeField(0x6000, count=4)
    totalenergy = uint32(0x6004, scale=0.01)
    yearenergy = uint32(0x6006, scale=0.01)
    monthenergy = uint32(0x6008, scale=0.01)
    todayenergy = uint32(0x600A, scale=0.01)
    totalhour = uint32(0x600C, scale=0.1)
    todayhour = gauge(0x600E, 0.1, signed=False)
    errorcount = integer(0x600F, signed=False)
    mpvmode = integer(0x6013, signed=False)
    faultmsg0 = uint32(0x6014)
    faultmsg1 = uint32(0x6016)
    faultmsg2 = uint32(0x6018)
    conntime = integer(0x601A, signed=False)
    power = uint32(0x601D)
    qpower = int32(0x601F)
    pf = gauge(0x6021, 0.001)
    nevolt = gauge(0x6034, 0.1, signed=False)
    gfci = integer(0x6035)
    busvolt = gauge(0x6036, 0.1, signed=False)
    busvoltm = gauge(0x6037, 0.1, signed=False)
    invtempc1 = gauge(0x6038, 0.1)
    invtempc_l1 = gauge(0x6039, 0.1)
    invtempc_l2 = gauge(0x603A, 0.1)
    invtempc_l3 = gauge(0x603B, 0.1)
    invtempc_cavity = gauge(0x603C, 0.1)
    iso1 = integer(0x6041, signed=False)
    iso2 = integer(0x6042, signed=False)
    iso3 = integer(0x6043, signed=False)
    iso4 = integer(0x6044, signed=False)

    for _ph, _base in (("l1", 0x6022), ("l2", 0x6028), ("l3", 0x602E)):
        locals()[f"{_ph}volt"] = gauge(_base, 0.1, signed=False)
        locals()[f"{_ph}curr"] = gauge(_base + 1, 0.01, signed=False)
        locals()[f"{_ph}freq"] = gauge(_base + 2, 0.01, signed=False)
        locals()[f"{_ph}dci"] = integer(_base + 3)
        locals()[f"{_ph}power"] = integer(_base + 4, signed=False)
        locals()[f"{_ph}pf"] = gauge(_base + 5, 0.001)
    for _pv in range(1, 7):
        _base = 0x6045 + 3 * (_pv - 1)
        locals()[f"pv{_pv}volt"] = gauge(_base, 0.1, signed=False)
        locals()[f"pv{_pv}curr"] = gauge(_base + 1, 0.01, signed=False)
        locals()[f"pv{_pv}power"] = integer(_base + 2, signed=False)
    for _pv in range(7, 13):
        _base = 0x6063 + 3 * (_pv - 7)
        locals()[f"pv{_pv}volt"] = gauge(_base, 0.1, signed=False)
        locals()[f"pv{_pv}curr"] = gauge(_base + 1, 0.01, signed=False)
        locals()[f"pv{_pv}power"] = integer(_base + 2, signed=False)
    for _pv in range(1, 7):
        locals()[f"pv{_pv}strcurr1"] = gauge(0x6057 + 2 * (_pv - 1), 0.01, signed=False)
        locals()[f"pv{_pv}strcurr2"] = gauge(0x6058 + 2 * (_pv - 1), 0.01, signed=False)
    for _pv in range(7, 13):
        locals()[f"pv{_pv}strcurr1"] = gauge(0x6075 + 2 * (_pv - 7), 0.01, signed=False)
        locals()[f"pv{_pv}strcurr2"] = gauge(0x6076 + 2 * (_pv - 7), 0.01, signed=False)


class PowerState(Component):
    """Remote power on/off, read and written at 0x1037.

    Its own component so a firmware that rejects this register only loses the
    switch, not the whole poll. The R5 only accepts FC16 writes, hence force_fc16.
    PLUS / R5 and R6 17-50K / C6 share this register.
    """

    poweronoff = boolean(0x1037, writable=True, force_fc16=True)


class R6StopState(Component):
    """R6 3-15K remote stop, read and written at 0x340C.

    Inverted compared to 0x1037: 1 means power off, 0 means power on.
    """

    inverterstop = boolean(0x340C, writable=True, force_fc16=True)


class Settings(Component):
    """Write-only control registers; never polled, only written."""

    limitpower = gauge(0x801F, 0.1, writable=True, force_fc16=True)
    datetime = DateTimeField(0x8020, count=4, writable=True)


class R6HybridSettings(Component):
    """R6 3-15K write-only settings: power limit 0x340B, clock 0x8020."""

    limitpower = gauge(0x340B, 0.1, writable=True, force_fc16=True)
    datetime = DateTimeField(0x8020, count=4, writable=True)


class R6HighSettings(Component):
    """R6 17-50K / C6 write-only settings: power limit 0x101C, clock 0x8020."""

    limitpower = gauge(0x101C, 0.1, writable=True, force_fc16=True)
    datetime = DateTimeField(0x8020, count=4, writable=True)


class SajR5Inverter:
    """A SAJ inverter on a Modbus unit, of one detected family.

    The family picks the register map: PLUS / R5 read the 0x100 block, R6
    3-15K hybrids the 0x4000 block and R6 17-50K / C6 the 0x6000 block, each
    with their own power and settings registers. Reading has two phases.
    ``async_setup`` runs once: it detects the family (unless the config entry
    already says), reads the static information and finds out which optional
    components this firmware serves. ``async_update`` then runs every
    interval over the components setup settled on — what the inverter serves
    cannot change between two polls.
    """

    def __init__(self, unit: ModbusUnit, family: str | None = None) -> None:
        """Initialize the device's components on ``unit``.

        ``family`` comes from the config entry; when it is None the family is
        detected in ``async_setup`` and the components are rebuilt then.
        """
        self._unit = unit
        # An unknown stored type is treated as "not known" and re-detected.
        self._family_known = family in FAMILIES
        self.family: str = family if family in FAMILIES else FAMILY_R5
        self.absent: frozenset[str] = frozenset()
        # None until async_setup has run, so a failed setup is retried.
        self._polled: list[str] | None = None
        self._build(self.family)

    def _build(self, family: str) -> None:
        """(Re)build the family's components on this device's unit.

        The info component survives a rebuild: detection reads it first, and
        its values (serial, device type) are what identity is built from.
        """
        if family not in FAMILIES:
            family = FAMILY_R5
        self.family = family
        self.info = getattr(self, "info", None) or InverterInfo(self._unit)
        if family == FAMILY_R6_HYBRID:
            self.realtime: Component = R6HybridData(self._unit)
            self.power = R6StopState(self._unit)
            self.settings = R6HybridSettings(self._unit)
        elif family == FAMILY_R6_HIGH:
            self.realtime = R6HighData(self._unit)
            self.power = PowerState(self._unit)
            self.settings = R6HighSettings(self._unit)
        else:
            self.realtime = RealtimeData(self._unit)
            self.power = PowerState(self._unit)
            self.settings = Settings(self._unit)
        self.absent = frozenset()
        self._polled = None
        self._readable = ComponentGroup(
            self._unit, [self.info, self.realtime, self.power]
        )

    @property
    def components(self) -> dict[str, Component]:
        """Every component of this device, by the name diagnostics reports."""
        return {
            "info": self.info,
            "realtime": self.realtime,
            "power": self.power,
            "settings": self.settings,
        }

    @classmethod
    async def async_probe(cls, unit: ModbusUnit) -> ProbeResult:
        """Read the inverter's identity: serial, family and device type."""
        info = InverterInfo(unit)
        await info.async_update()
        family = await detect_family(unit, info.devtype)
        return ProbeResult(info.sn or "", family, info.devtype)

    @classmethod
    async def async_probe_connection(cls, connection: ModbusConnection) -> ProbeResult:
        """Probe over an already-built connection, closing it afterwards."""
        try:
            return await cls.async_probe(connection.for_unit(UNIT_ID))
        finally:
            await connection.close()

    async def async_setup(self) -> None:
        """Detect the family if needed, then read what this firmware serves.

        Some firmware revisions do not serve the information or power-state
        registers. A refusal of those is not a failure of setup; anything else
        is, and propagates.
        """
        absent = set()
        probes: list[tuple[str, Component]] = []
        if not self._family_known:
            try:
                await self.info.async_update()
            except _NOT_SERVED:
                absent.add("info")
            self._build(await detect_family(self._unit, self.info.devtype))
        else:
            probes.append(("info", self.info))
        probes.append(("power", self.power))
        for name, component in probes:
            try:
                await component.async_update()
            except _NOT_SERVED as ex:
                absent.add(name)
                _LOGGER.info(
                    "This inverter does not serve the %s registers at %s, so "
                    "they stay unavailable and are not read again",
                    name,
                    ex.block,
                )
        self.absent = frozenset(absent)
        self._polled = [name for name in _POLLED if name not in absent]
        readable = [getattr(self, name) for name in self._polled]
        if "info" not in absent:
            readable.insert(0, self.info)
        self._readable = ComponentGroup(self._unit, readable)

    async def async_update(self) -> UpdateReport:
        """Read every polled component, one at a time.

        A component whose read fails keeps its previous values while the rest
        still refresh, so one slow block cannot blank the whole inverter.
        Listeners fire only once every component has been tried, and only for
        the ones that refreshed. A failure of the link itself raises
        ``ModbusConnectionError`` rather than reporting partial silence, and so
        does a first component that times out: nothing has answered yet, so
        reading on would only pay the same timeout again.
        """
        if self._polled is None:
            await self.async_setup()
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name in self._polled or ():
            component: Component = getattr(self, name)
            try:
                await component.async_update(notify=False)
            except ModbusConnectionError:
                raise
            except ModbusTimeoutError as err:
                if not updated and not failed:
                    raise  # nothing answered; the rest would only time out too
                failed[name] = err
            except ModbusError as err:
                failed[name] = err
            else:
                updated.add(name)
        for name in updated:
            fresh: Component = getattr(self, name)
            fresh.notify()
        return UpdateReport(updated, failed)

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Read the raw registers backing every readable component.

        The fields refresh but no listener fires: a diagnostics download is not
        a poll, and should not write a state for every entity off the cycle.
        """
        return await self._readable.async_read_raw(notify=False)
