"""SAJ Modbus Hub."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusError,
    ModbusExceptionError,
    ModbusTimeoutError,
)

from .const import (
    ATTR_MANUFACTURER,
    DEVICE_STATUSSES,
    DOMAIN,
    FAULT_MESSAGES,
)
from .inverter import UNIT_ID, SajR5Inverter, create_connection

_LOGGER = logging.getLogger(__name__)

type SajConfigEntry = ConfigEntry[SAJModbusHub]

# The refusals that mean the registers are not in the device's map. Every
# other exception response describes a request that failed, not one that can
# never succeed, so those propagate and fail the poll.
_ABSENT = (IllegalFunctionError, IllegalDataAddressError)

# Consecutive timeouts before the link is treated as stuck rather than slow.
_STUCK_AFTER_TIMEOUTS = 3


def translate_fault_code_to_messages(
    fault_code: int, fault_messages: dict[int, str]
) -> list[str]:
    """Translate faultcodes to readable messages."""
    if not fault_code:
        return []
    return [mesg for code, mesg in fault_messages.items() if fault_code & code]


class SAJModbusHub(DataUpdateCoordinator[None]):
    """Coordinator polling a SAJ R5 inverter over modbus-connection."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SajConfigEntry,
        name: str,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        """Initialize the Modbus hub."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
        )

        self._connection = create_connection(host, port)
        self.device = SajR5Inverter(self._connection.for_unit(UNIT_ID))
        self._info_read = False
        self._power_limit: float = 110.0
        # Consecutive poll timeouts; reset by any poll that reaches the device.
        self._timeouts = 0
        # Optional components this inverter answered "not in my map" for;
        # asking again every poll would be pure waste.
        self._absent: set[str] = set()
        # Resolved once by freeze_identity() after the first refresh and never
        # again: entities bake it into their unique ids at construction, so it
        # must not change under them if a later poll finally reads the serial.
        self._identifier = name

    @property
    def serial_number(self) -> str | None:
        """The inverter's serial number, once the info registers have been read."""
        serial = self.device.info.sn
        return serial or None

    @property
    def identifier(self) -> str:
        """The stable key entity unique ids and the device are built from."""
        return self._identifier

    @callback
    def freeze_identity(self) -> str:
        """Pin this hub's identity, preferring the serial over the name.

        Installs predating the serial-based identity, and firmware that does
        not serve the info registers, keep the user-chosen name.
        """
        self._identifier = self.serial_number or self.name
        return self._identifier

    @property
    def device_info(self) -> DeviceInfo:
        """Device registry entry for this inverter."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.identifier)},
            name=self.name,
            manufacturer=ATTR_MANUFACTURER,
            serial_number=self.serial_number,
        )

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        await self._connection.close()

    def _note_absent(self, component: str, err: ModbusExceptionError) -> None:
        """Record a component the inverter does not serve."""
        self._absent.add(component)
        _LOGGER.info(
            "This inverter does not serve the %s registers at %s, so they stay "
            "unavailable and are not read again",
            component,
            err.block,
        )

    async def _async_note_timeout(self) -> None:
        """Count a timeout, and drop the link once it looks stuck.

        A wedged serial-to-network bridge keeps its socket open while Modbus
        stops answering, and a timeout does not touch the transport. One
        timeout is only a slow reply, so wait for a few before dropping the
        link; the next request opens a fresh one over the same components.
        """
        self._timeouts += 1
        if self._timeouts < _STUCK_AFTER_TIMEOUTS:
            return
        _LOGGER.debug("Dropping a stuck link after %d timeouts", self._timeouts)
        self._timeouts = 0
        await self._connection.disconnect()

    async def _async_update_data(self) -> None:
        """Refresh the inverter's components; entities read them directly."""
        try:
            # Static inverter info is read once. Some firmware variants do not
            # serve the info and power-state registers at all; tolerate that,
            # as the previous pymodbus code did.
            if not self._info_read and "info" not in self._absent:
                try:
                    await self.device.info.async_update()
                except _ABSENT as ex:
                    self._note_absent("info", ex)
                else:
                    self._info_read = True
            await self.device.realtime.async_update()
            if "power" not in self._absent:
                try:
                    await self.device.power.async_update()
                except _ABSENT as ex:
                    self._note_absent("power", ex)
        except ModbusTimeoutError as ex:
            await self._async_note_timeout()
            raise UpdateFailed(f"Failed to fetch realtime data: {ex}") from ex
        except ModbusError as ex:
            raise UpdateFailed(f"Failed to fetch realtime data: {ex}") from ex

        self._timeouts = 0

        if messages := self.fault_messages:
            _LOGGER.error("Fault message: %s", ", ".join(messages))

    @property
    def absent_components(self) -> set[str]:
        """Components this inverter does not serve."""
        return set(self._absent)

    @property
    def mpvstatus(self) -> str:
        """The inverter's working mode as a readable status."""
        return DEVICE_STATUSSES.get(self.device.realtime.mpvmode, "Unknown")

    @property
    def fault_messages(self) -> list[str]:
        """Every fault the inverter is currently reporting."""
        realtime = self.device.realtime
        return [
            message
            for fault_code, messages in (
                (realtime.faultmsg0, FAULT_MESSAGES[0]),
                (realtime.faultmsg1, FAULT_MESSAGES[1]),
                (realtime.faultmsg2, FAULT_MESSAGES[2]),
            )
            for message in translate_fault_code_to_messages(fault_code or 0, messages)
        ]

    @property
    def faultmsg(self) -> str:
        """The reported faults as one string, capped to fit a state value."""
        return ", ".join(self.fault_messages).strip()[:254]

    @property
    def poweronoff(self) -> bool | None:
        """Whether the inverter is switched on, as last read from the device."""
        return self.device.power.poweronoff

    @property
    def limitpower(self) -> float:
        """The active power limit.

        Write-only on this inverter, so this is the last value written rather
        than anything read back from the device.
        """
        return self._power_limit

    async def async_set_power_on_off(self, value: bool) -> bool:
        """Set the power on/off on the inverter."""
        try:
            await self.device.power.write("poweronoff", value)
        except ModbusError as ex:
            _LOGGER.error("Failed to set power on/off: %s", ex)
            return False
        return True

    async def async_set_limit_power(self, value: float) -> bool:
        """Set the power limit on the inverter."""
        if self.limiter_is_disabled():
            return False

        try:
            await self.device.settings.write("limitpower", value)
        except ModbusError as ex:
            _LOGGER.error("Failed to set limitpower: %s", ex)
            return False
        self._power_limit = value
        self.async_update_listeners()
        return True

    async def async_set_date_and_time(self, date_time: datetime | None = None) -> None:
        """Set the time and date on the inverter."""
        if date_time is None:
            date_time = datetime.now()
        await self.device.settings.write("datetime", date_time)

    def limiter_is_disabled(self) -> bool:
        """Return True if the limiter entity is disabled, False otherwise."""
        ent_reg = entity_registry.async_get(self.hass)
        limiter_entity_id = ent_reg.async_get_entity_id(
            NUMBER_DOMAIN, DOMAIN, f"{self.identifier}_limitpower"
        )
        if (
            limiter_entity_id is None
            or (ent_reg_entry := ent_reg.async_get(limiter_entity_id)) is None
        ):
            return True
        return ent_reg_entry.disabled
