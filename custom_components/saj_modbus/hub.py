"""SAJ Modbus Hub."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import BlockReadError, ModbusError, ModbusTimeoutError

from .const import (
    ATTR_MANUFACTURER,
    DEVICE_STATUSSES,
    DOMAIN,
    FAULT_MESSAGES,
)
from .inverter import UNIT_ID, SajR5Inverter, component_values, create_connection

_LOGGER = logging.getLogger(__name__)

type SajConfigEntry = ConfigEntry[SAJModbusHub]

# Modbus exception codes meaning the registers are not in the device's map:
# illegal function (the device has no such function code) and illegal data
# address. Every other code describes a request that failed, not one that
# can never succeed.
_ABSENT_CODES = frozenset({1, 2})


def translate_fault_code_to_messages(
    fault_code: int, fault_messages: dict[int, str]
) -> list[str]:
    """Translate faultcodes to readable messages."""
    if not fault_code:
        return []
    return [mesg for code, mesg in fault_messages.items() if fault_code & code]


class SAJModbusHub(DataUpdateCoordinator[dict[str, int | float | str]]):
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

        self._host = host
        self._port = port
        self._connection = create_connection(host, port)
        self.device = SajR5Inverter(self._connection.for_unit(UNIT_ID))
        self.inverter_data: dict[str, int | float | str] = {}
        self._power_limit: float = 110.0
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
        serial = self.inverter_data.get("sn")
        return serial if isinstance(serial, str) and serial else None

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

    def _note_absent(self, component: str, err: BlockReadError) -> None:
        """Record a component the inverter does not serve, or re-raise.

        Only a structural rejection means the registers are not there. Every
        other exception code is transient (a device fault, or a busy or
        rejected request), so swallowing it would hide a real failure as a
        permanently missing sensor.

        Raises the original error if the rejection was not structural.
        """
        if err.exception_code not in _ABSENT_CODES:
            raise err
        self._absent.add(component)
        _LOGGER.info(
            "This inverter does not serve its %s registers, so they stay "
            "unavailable and are not read again: %s",
            component,
            err,
        )

    async def _async_recycle_connection(self) -> None:
        """Replace the connection after a timeout.

        A wedged serial-WiFi bridge can keep its TCP session alive while Modbus
        stops answering, and a timeout does not drop the transport — so a fresh
        connection is the only way to recover the next poll.
        """
        old = self._connection
        self._connection = create_connection(self._host, self._port)
        self.device = SajR5Inverter(self._connection.for_unit(UNIT_ID))
        await old.close()

    async def _async_update_data(self) -> dict[str, int | float | str]:
        """Fetch realtime data from the inverter."""
        try:
            # Static inverter info is fetched once and cached. Some firmware
            # variants do not serve the info and power-state registers at all;
            # tolerate that, as the previous pymodbus code did.
            if not self.inverter_data and "info" not in self._absent:
                try:
                    await self.device.info.async_update()
                except BlockReadError as ex:
                    self._note_absent("info", ex)
                else:
                    self.inverter_data = component_values(self.device.info)
            await self.device.realtime.async_update()
            if "power" not in self._absent:
                try:
                    await self.device.power.async_update()
                except BlockReadError as ex:
                    self._note_absent("power", ex)
        except ModbusTimeoutError as ex:
            await self._async_recycle_connection()
            raise UpdateFailed(f"Failed to fetch realtime data: {ex}") from ex
        except ModbusError as ex:
            raise UpdateFailed(f"Failed to fetch realtime data: {ex}") from ex

        data = {**self.inverter_data, **self._realtime_values()}
        data["poweronoff"] = self.device.power.poweronoff
        data["limitpower"] = self._power_limit
        return data

    def _realtime_values(self) -> dict[str, int | float | str]:
        """Return the realtime component's values with derived fields."""
        realtime = self.device.realtime
        data = component_values(realtime)
        data["mpvstatus"] = DEVICE_STATUSSES.get(realtime.mpvmode, "Unknown")
        fault_messages_list = [
            message
            for fault_code, messages in (
                (realtime.faultmsg0, FAULT_MESSAGES[0]),
                (realtime.faultmsg1, FAULT_MESSAGES[1]),
                (realtime.faultmsg2, FAULT_MESSAGES[2]),
            )
            for message in translate_fault_code_to_messages(fault_code or 0, messages)
        ]
        for name in ("faultmsg0", "faultmsg1", "faultmsg2"):
            data.pop(name)
        data["faultmsg"] = ", ".join(fault_messages_list).strip()[:254]
        if fault_messages_list:
            _LOGGER.error("Fault message: %s", ", ".join(fault_messages_list).strip())
        return data

    async def async_set_power_on_off(self, value: bool) -> bool:
        """Set the power on/off on the inverter."""
        try:
            await self.device.power.write("poweronoff", value)
        except ModbusError as ex:
            _LOGGER.error("Failed to set power on/off: %s", ex)
            return False
        if self.data:
            new_data = self.data.copy()
            new_data["poweronoff"] = value
            self.async_set_updated_data(new_data)
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
        if self.data:
            new_data = self.data.copy()
            new_data["limitpower"] = value
            self.async_set_updated_data(new_data)
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
