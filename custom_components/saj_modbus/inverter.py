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
    ModbusTcpParams,
    ModbusUnit,
)
from modbus_connection.model import (
    Component,
    ComponentGroup,
    RegisterField,
    boolean,
    gauge,
    integer,
    string,
    uint32,
)
from modbus_connection.tmodbus import ModbusConnection

_LOGGER = logging.getLogger(__name__)

# The R5 responds on a fixed station address; it is not user-configurable.
UNIT_ID = 1
MODBUS_TIMEOUT = 5

# The refusals that mean the registers are not in this inverter's map. Every
# other exception response says the registers are there and the read failed,
# so those propagate.
_NOT_SERVED = (IllegalFunctionError, IllegalDataAddressError)

# Every component attribute a poll may refresh, in read order. The information
# is static, so setup reads it and polling never does.
_POLLED = ("realtime", "power")


@dataclass(frozen=True)
class UpdateReport:
    """What one poll refreshed, by the device's component attribute names.

    A failed component kept its previous values and did not notify; the error
    that failed it rides along. A dead link is never in here — the update
    raises ``ModbusConnectionError`` instead of reporting partial silence.
    """

    updated: set[str]
    failed: dict[str, ModbusError]

    @property
    def complete(self) -> bool:
        """Whether every polled component refreshed."""
        return not self.failed


def create_connection(host: str, port: int) -> ModbusConnection:
    """Create an inverter connection, shared by entry setup and the config flow."""
    return ModbusConnection(
        ModbusTcpParams(host=host, port=port), timeout=MODBUS_TIMEOUT
    )


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


class PowerState(Component):
    """Remote power on/off, read and written at 0x1037.

    Its own component so a firmware that rejects this register only loses the
    switch, not the whole poll. The R5 only accepts FC16 writes, hence force_fc16.
    """

    poweronoff = boolean(0x1037, writable=True, force_fc16=True)


class Settings(Component):
    """Write-only control registers; never polled, only written."""

    limitpower = gauge(0x801F, 0.1, writable=True, force_fc16=True)
    datetime = DateTimeField(0x8020, count=4, writable=True)


class SajR5Inverter:
    """A SAJ R5 inverter on a Modbus unit.

    Reading it has two phases. ``async_setup`` runs once: it reads the static
    information and finds out which optional components this firmware serves.
    ``async_update`` then runs every interval over the components setup
    settled on — what the inverter serves cannot change between two polls.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        """Initialize the device's components on ``unit``."""
        self._unit = unit
        self.info = InverterInfo(unit)
        self.realtime = RealtimeData(unit)
        self.power = PowerState(unit)
        self.settings = Settings(unit)
        self.absent: frozenset[str] = frozenset()
        # None until async_setup has run, so a failed setup is retried.
        self._polled: list[str] | None = None
        self._readable = ComponentGroup(unit, [self.info, self.realtime, self.power])

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
    async def async_probe(cls, unit: ModbusUnit) -> str:
        """Read the inverter's serial number, proving it is reachable."""
        info = InverterInfo(unit)
        await info.async_update()
        return info.sn or ""

    async def async_setup(self) -> None:
        """Read the static data and learn which optional components exist.

        Some firmware revisions do not serve the information or power-state
        registers. A refusal of those is not a failure of setup; anything else
        is, and propagates.
        """
        absent = set()
        for name, component in (("info", self.info), ("power", self.power)):
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
        ``ModbusConnectionError`` rather than reporting partial silence.
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
            except ModbusError as err:
                failed[name] = err
            else:
                updated.add(name)
        for name in updated:
            fresh: Component = getattr(self, name)
            fresh.notify()
        return UpdateReport(updated, failed)

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Read the raw registers backing every readable component."""
        return await self._readable.async_read_raw()
