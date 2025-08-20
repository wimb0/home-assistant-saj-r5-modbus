"""SAJ Modbus Hub."""

import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import cast

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.pdu import ModbusPDU
from voluptuous.validators import Number

from .const import (
    DEVICE_STATUSSES,
    DOMAIN,
    FAULT_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)


class SAJModbusHub(DataUpdateCoordinator[dict[str, int | float | str]]):
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str,
        port: int,
        scan_interval: int,
    ) -> None:
        """Initialize the Modbus hub."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
        )

        self._client = ModbusTcpClient(host=host, port=port, timeout=5)
        self._lock = threading.Lock()
        self.inverter_data: dict[str, int | float | str] = {}
        self._power_limit: float = 110.0

    async def _async_setup(self) -> None:
        """Fetch data that is needed only once."""
        try:
            self.inverter_data = await self.hass.async_add_executor_job(
                self.read_modbus_inverter_data
            )
        except (ConnectionException, ModbusException) as ex:
            raise UpdateFailed(f"Failed to fetch inverter data: {ex}") from ex

    async def _async_update_data(self) -> dict[str, int | float | str]:
        """Fetch realtime data from the inverter."""
        try:
            realtime_data = await self.hass.async_add_executor_job(
                self.read_modbus_r5_realtime_data
            )
            combined_data = {**self.inverter_data, **realtime_data}
            combined_data["limitpower"] = self._power_limit
            return combined_data
        except (ConnectionException, ModbusException) as ex:
            raise UpdateFailed(f"Failed to fetch realtime data: {ex}") from ex
        finally:
            self.close()

    @callback
    def async_remove_listener(self, update_callback: CALLBACK_TYPE) -> None:
        """Remove data update listener."""
        super().async_remove_listener(update_callback)
        if not self._listeners:
            self.close()

    def close(self) -> None:
        """Disconnect client."""
        with self._lock:
            self._client.close()

    def _read_holding_registers(self, unit, address, count):
        """Read holding registers."""
        with self._lock:
            return self._client.read_holding_registers(
                address=address, count=count, slave=unit
            )

    def _write_registers(self, unit: int, address: int, values: list[int]) -> ModbusPDU:
        """Write registers."""
        with self._lock:
            return self._client.write_registers(
                address=address, values=values, slave=unit
            )

    def convert_to_signed(self, value: int) -> int:
        """Convert unsigned integers to signed integers."""
        if value >= 0x8000:
            return value - 0x10000
        return value

    def parse_datetime(self, registers: list[int]) -> str:
        """Extract date and time values from registers."""
        year = registers[0]
        month = registers[1] >> 8
        day = registers[1] & 0xFF
        hour = registers[2] >> 8
        minute = registers[2] & 0xFF
        second = registers[3] >> 8

        timevalues = f"{year}{month:02}{day:02}{hour:02}{minute:02}{second:02}"
        date_time_obj = datetime.strptime(timevalues, "%Y%m%d%H%M%S").astimezone()
        return date_time_obj.isoformat()

    def read_modbus_inverter_data(self) -> dict[str, int | float | str]:
        """Read data about inverter."""
        inverter_data = self._read_holding_registers(unit=1, address=0x8F00, count=29)
        if inverter_data.isError():
            _LOGGER.debug("Error reading inverter data")
            return {}
        registers = inverter_data.registers
        data: dict[str, int | float | str] = {
            "devtype": registers[0],
            "subtype": registers[1],
            "commver": round(registers[2] * 0.001, 3),
            "sn": "".join(
                chr(registers[i] >> 8) + chr(registers[i] & 0xFF) for i in range(3, 13)
            ).rstrip("\x00"),
            "pc": "".join(
                chr(registers[i] >> 8) + chr(registers[i] & 0xFF) for i in range(13, 23)
            ).rstrip("\x00"),
            "dv": round(registers[23] * 0.001, 3),
            "mcv": round(registers[24] * 0.001, 3),
            "scv": round(registers[25] * 0.001, 3),
            "disphwversion": round(registers[26] * 0.001, 3),
            "ctrlhwversion": round(registers[27] * 0.001, 3),
            "powerhwversion": round(registers[28] * 0.001, 3),
        }
        return data


    def read_modbus_r5_realtime_data(self) -> dict[str, int | float | str]:
        """Read realtime data from inverter."""
        realtime_data = self._read_holding_registers(unit=1, address=0x100, count=60)
        if realtime_data.isError():
            _LOGGER.debug("Error reading realtime data")
            return {}
        registers = realtime_data.registers
        data: dict[str, int | float | str] = {}
        mpvmode = registers[0]
        data["mpvmode"] = mpvmode
        data["mpvstatus"] = DEVICE_STATUSSES.get(mpvmode, "Unknown")
        faultMsg0 = (registers[1] << 16) | registers[2]
        faultMsg1 = (registers[3] << 16) | registers[4]
        faultMsg2 = (registers[5] << 16) | registers[6]
        fault_messages_list = self.translate_fault_code_to_messages(
            faultMsg0, list(FAULT_MESSAGES[0].items())
        )
        fault_messages_list.extend(
            self.translate_fault_code_to_messages(
                faultMsg1, list(FAULT_MESSAGES[1].items())
            )
        )
        fault_messages_list.extend(
            self.translate_fault_code_to_messages(
                faultMsg2, list(FAULT_MESSAGES[2].items())
            )
        )
        data["faultmsg"] = ", ".join(fault_messages_list).strip()[:254]
        if fault_messages_list:
            _LOGGER.error("Fault message: %s", ", ".join(fault_messages_list).strip())
        data["pv1volt"] = round(registers[7] * 0.1, 1)
        data["pv1curr"] = round(registers[8] * 0.01, 2)
        data["pv1power"] = registers[9]
        data["pv2volt"] = round(registers[10] * 0.1, 1)
        data["pv2curr"] = round(registers[11] * 0.01, 2)
        data["pv2power"] = registers[12]
        data["pv3volt"] = round(registers[13] * 0.1, 1)
        data["pv3curr"] = round(registers[14] * 0.01, 2)
        data["pv3power"] = registers[15]
        data["busvolt"] = round(registers[16] * 0.1, 1)
        data["invtempc"] = round(self.convert_to_signed(registers[17]) * 0.1, 1)
        data["gfci"] = self.convert_to_signed(registers[18])
        data["power"] = registers[19]
        data["qpower"] = self.convert_to_signed(registers[20])
        data["pf"] = round(self.convert_to_signed(registers[21]) * 0.001, 3)
        data["l1volt"] = round(registers[22] * 0.1, 1)
        data["l1curr"] = round(registers[23] * 0.01, 2)
        data["l1freq"] = round(registers[24] * 0.01, 2)
        data["l1dci"] = self.convert_to_signed(registers[25])
        data["l1power"] = registers[26]
        data["l1pf"] = round(self.convert_to_signed(registers[27]) * 0.001, 3)
        data["l2volt"] = round(registers[28] * 0.1, 1)
        data["l2curr"] = round(registers[29] * 0.01, 2)
        data["l2freq"] = round(registers[30] * 0.01, 2)
        data["l2dci"] = self.convert_to_signed(registers[31])
        data["l2power"] = registers[32]
        data["l2pf"] = round(self.convert_to_signed(registers[33]) * 0.001, 3)
        data["l3volt"] = round(registers[34] * 0.1, 1)
        data["l3curr"] = round(registers[35] * 0.01, 2)
        data["l3freq"] = round(registers[36] * 0.01, 2)
        data["l3dci"] = self.convert_to_signed(registers[37])
        data["l3power"] = registers[38]
        data["l3pf"] = round(self.convert_to_signed(registers[39]) * 0.001, 3)
        data["iso1"] = registers[40]
        data["iso2"] = registers[41]
        data["iso3"] = registers[42]
        data["iso4"] = registers[43]
        data["todayenergy"] = round(registers[44] * 0.01, 2)
        data["monthenergy"] = round(((registers[45] << 16) | registers[46]) * 0.01, 2)
        data["yearenergy"] = round(((registers[47] << 16) | registers[48]) * 0.01, 2)
        data["totalenergy"] = round(((registers[49] << 16) | registers[50]) * 0.01, 2)
        data["todayhour"] = round(registers[51] * 0.1, 1)
        data["totalhour"] = round(((registers[52] << 16) | registers[53]) * 0.1, 1)
        data["errorcount"] = registers[54]
        data["datetime"] = self.parse_datetime(registers[55:60])
        return data

    def translate_fault_code_to_messages(
        self, fault_code: int, fault_messages: list[tuple[int, str]]
    ) -> list[str]:
        """Translate faultcodes to readable messages."""
        messages = []
        if not fault_code:
            return messages
        for code, mesg in fault_messages:
            if fault_code & code:
                messages.append(mesg)
        return messages

    def _write_limit_power_sync(self, value: float) -> bool:
        """(Synchronous) Helper to write the power limit to the inverter."""
        response = self._write_registers(unit=1, address=0x801F, values=[int(value * 10)])
        if response.isError():
            _LOGGER.error("Failed to set limitpower")
            return False
        return True

    async def async_set_limit_power(self, value: float) -> bool:
        """Asynchronously set the power limit on the inverter."""
        if self.limiter_is_disabled():
            return False

        if await self.hass.async_add_executor_job(self._write_limit_power_sync, value):
            self._power_limit = value
            if self.data:
                new_data = self.data.copy()
                new_data["limitpower"] = value
                self.async_set_updated_data(new_data)
            return True
        return False

    def set_date_and_time(self, date_time: datetime | None = None) -> None:
        """Set the time and date on the inverter."""
        if date_time is None:
            date_time = datetime.now()
        values = [
            date_time.year,
            (date_time.month << 8) + date_time.day,
            (date_time.hour << 8) + date_time.minute,
            (date_time.second << 8),
        ]
        response = self._write_registers(unit=1, address=0x8020, values=values)
        if response.isError():
            raise ModbusException("Error setting date and time")

    def limiter_is_disabled(self) -> bool:
        """Return True if the limiter entity is disabled, False otherwise."""
        ent_reg = entity_registry.async_get(self.hass)
        limiter_entity_id = ent_reg.async_get_entity_id(
            NUMBER_DOMAIN, DOMAIN, f"{self.name}_limitpower"
        )
        if limiter_entity_id is None or (
            ent_reg_entry := ent_reg.async_get(limiter_entity_id)
        ) is None:
            return True
        return ent_reg_entry.disabled
