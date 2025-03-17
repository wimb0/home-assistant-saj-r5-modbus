"""SAJ Modbus Hub."""

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from voluptuous.validators import Number
import logging
import threading
from datetime import datetime, timedelta, timezone
from homeassistant.core import CALLBACK_TYPE, callback, HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.pdu import ModbusPDU

from .const import (
    DEVICE_STATUSSES,
    DOMAIN,
    FAULT_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)

class SAJModbusHub(DataUpdateCoordinator[dict]):
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str,
        port: Number,
        scan_interval: Number,
    ):
        """Initialize the Modbus hub."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=scan_interval),
        )

        self._client = ModbusTcpClient(host=host, port=port, timeout=5)
        self._lock = threading.Lock()

        self.inverter_data: dict = {}
        self.data: dict = {}

    @callback
    def async_remove_listener(self, update_callback: CALLBACK_TYPE) -> None:
        """Remove data update listener."""
        super().async_remove_listener(update_callback)

        """No listeners left then close connection"""
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
    def convert_to_signed(self, value):
        """Convert unsigned integers to signed integers."""
        if value >= 0x8000:
            return value - 0x10000
        else:
            return value

    def parse_datetime (self, registers: list[int]) -> str:
        """Extract date and time values from registers."""

        year = registers[0]  # yyyy
        month = registers[1] >> 8  # MM
        day = registers[1] & 0xFF  # dd
        hour = registers[2] >> 8  # HH
        minute = registers[2] & 0xFF  # mm
        second = registers[3] >> 8  # ss

        timevalues = f"{year}{month:02}{day:02}{hour:02}{minute:02}{second:02}"
        # Convert to datetime object
        date_time_obj = datetime.astimezone(datetime.strptime(timevalues, '%Y%m%d%H%M%S'))

        return(date_time_obj)

    async def _async_update_data(self) -> dict:
        realtime_data = {}
        try:
            """Inverter info is only fetched once"""
            if not self.inverter_data:
                self.inverter_data = await self.hass.async_add_executor_job(
                    self.read_modbus_inverter_data
                )
            """Read realtime data"""
            realtime_data = await self.hass.async_add_executor_job(
                self.read_modbus_r5_realtime_data
            )

        except (BrokenPipeError, ConnectionResetError, ConnectionException) as conerr:
            _LOGGER.error("Reading realtime data failed! Inverter is unreachable.")
            _LOGGER.debug("Connection error: %s", conerr)
            realtime_data["mpvmode"] = 0
            realtime_data["mpvstatus"] = DEVICE_STATUSSES[0]
            realtime_data["power"] = 0

        self.close()
        return {**self.inverter_data, **realtime_data}

    def read_modbus_inverter_data(self) -> dict:
        """Read data about inverter."""
        inverter_data = self._read_holding_registers(unit=1, address=0x8F00, count=29)

        if inverter_data.isError():
            return {}

        registers = inverter_data.registers
        data = {
            "devtype": registers[0],
            "subtype": registers[1],
            "commver": round(registers[2] * 0.001, 3),
            "sn": ''.join(chr(registers[i] >> 8) + chr(registers[i] & 0xFF) for i in range(3, 13)).rstrip('\x00'),
            "pc": ''.join(chr(registers[i] >> 8) + chr(registers[i] & 0xFF) for i in range(13, 23)).rstrip('\x00'),
            "dv": round(registers[23] * 0.001, 3),
            "mcv": round(registers[24] * 0.001, 3),
            "scv": round(registers[25] * 0.001, 3),
            "disphwversion": round(registers[26] * 0.001, 3),
            "ctrlhwversion": round(registers[27] * 0.001, 3),
            "powerhwversion": round(registers[28] * 0.001, 3)
        }

        return data

    def read_modbus_r5_realtime_data(self) -> dict:
        """Read realtime data from inverter."""
        realtime_data = self._read_holding_registers(unit=1, address=0x100, count=60)

        if realtime_data.isError():
            return {}

        registers = realtime_data.registers
        data = {}

        mpvmode = registers[0]
        data["mpvmode"] = mpvmode

        if mpvmode == 2:
            data["limitpower"] = (
                110
                if mpvmode != self.data.get("mpvmode")
                else self.data.get("limitpower")
            )

        DEVICE_STATUSSES = {
            0: "Not Connected",
            1: "Waiting",
            2: "Normal",
            3: "Error",
            4: "Upgrading",
        }

        data["mpvstatus"] = DEVICE_STATUSSES.get(mpvmode, "Unknown")

        faultMsg0 = registers[1] << 16 | registers[2]
        faultMsg1 = registers[3] << 16 | registers[4]
        faultMsg2 = registers[5] << 16 | registers[6]

        faultMsg = []
        faultMsg.extend(
            self.translate_fault_code_to_messages(faultMsg0, FAULT_MESSAGES[0].items())
        )
        faultMsg.extend(
            self.translate_fault_code_to_messages(faultMsg1, FAULT_MESSAGES[1].items())
        )
        faultMsg.extend(
            self.translate_fault_code_to_messages(faultMsg2, FAULT_MESSAGES[2].items())
        )

        # status value can hold max 255 chars in HA
        data["faultmsg"] = ", ".join(faultMsg).strip()[0:254]
        if faultMsg:
            _LOGGER.error("Fault message: " + ", ".join(faultMsg).strip())

        data["pv1volt"] = round(registers[7] * 0.1, 1)
        data["pv1curr"] = round(registers[8] * 0.01, 2)
        data["pv1power"] = round(registers[9] * 1, 0)

        data["pv2volt"] = round(registers[10] * 0.1, 1)
        data["pv2curr"] = round(registers[11] * 0.01, 2)
        data["pv2power"] = round(registers[12] * 1, 0)

        data["pv3volt"] = round(registers[13] * 0.1, 1)
        data["pv3curr"] = round(registers[14] * 0.01, 2)
        data["pv3power"] = round(registers[15] * 1, 0)

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
        data["monthenergy"] = round((registers[45] << 16 | registers[46]) * 0.01, 2)
        data["yearenergy"] = round((registers[47] << 16 | registers[48]) * 0.01, 2)
        data["totalenergy"] = round((registers[49] << 16 | registers[50]) * 0.01, 2)

        data["todayhour"] = round(registers[51] * 0.1, 1)
        data["totalhour"] = round((registers[52] << 16 | registers[53]) * 0.1, 1)

        data["errorcount"] = registers[54]
        data["datetime"] = self.parse_datetime(registers[55:60])

        return data

    def translate_fault_code_to_messages(
        self, fault_code: int, fault_messages: list
    ) -> list:
        """Translate faultcodes to readable messages."""
        messages = []
        if not fault_code:
            return messages

        for code, mesg in fault_messages:
            if fault_code & code:
                messages.append(mesg)

        return messages

    def limiter_is_disabled(self) -> bool:
        """Return True if the limiter entity is disabled, False otherwise."""
        ent_reg = entity_registry.async_get(self.hass)
        limiter_entity_id = ent_reg.async_get_entity_id(
            NUMBER_DOMAIN, DOMAIN, f"{self.name}_limitpower"
        )
        if (
            limiter_entity_id is None
            or (ent_reg_entry := ent_reg.async_get(limiter_entity_id)) is None
        ):
            return True
        return ent_reg_entry.disabled

    def set_limitpower(self, value: float) -> None:
        """Limit the power output of the inverter."""
        if self.limiter_is_disabled():
            return
        response = self._write_registers(
            unit=1, address=0x801F, values=[int(value * 10)]
        )
        if response.isError():
            return
        self.data["limitpower"] = value
        self.hass.add_job(self.async_update_listeners)

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

    def set_value(self, key: str, value: float) -> None:
        """Set value matching key."""
        if key == "limitpower":
            self.set_limitpower(value)
