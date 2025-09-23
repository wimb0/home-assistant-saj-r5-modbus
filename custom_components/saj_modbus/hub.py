"""Modified 'SAJ Modbus Hub' to support R6 registers."""

import logging
import threading
from datetime import datetime, timedelta

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.pdu import ModbusPDU

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
        self._power_limit: float = 220.0
        self._power_on_off: bool = False

    async def async_setup(self) -> None:
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
            # If inverter_data is empty, fetch it.
            if not self.inverter_data:
                await self.async_setup()

            realtime_data = await self.hass.async_add_executor_job(
                self.read_modbus_r6_realtime_data
            )
            power_state = await self.hass.async_add_executor_job(
                self.read_modbus_inverter_power_state
            )
            combined_data = {**self.inverter_data, **realtime_data, **power_state}
            combined_data["limitpower"] = self._power_limit
            combined_data["poweronoff"] = self._power_on_off
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
                address=address, count=count, device_id=unit
            )

    def _write_registers(self, unit: int, address: int, values: list[int]) -> ModbusPDU:
        """Write registers."""
        with self._lock:
            return self._client.write_registers(
                address=address, values=values, device_id=unit
            )

    def convert_to_signed(self, value: int) -> int:
        """Convert unsigned integers to signed integers."""
        if value >= 0x8000:
            return value - 0x10000
        return value

    def parse_datetime(self, registers: list[int]) -> datetime:
        """Extract date and time values from registers."""
        year = registers[0]
        month = registers[1] >> 8
        day = registers[1] & 0xFF
        hour = registers[2] >> 8
        minute = registers[2] & 0xFF
        second = registers[3] >> 8

        timevalues = f"{year}{month:02}{day:02}{hour:02}{minute:02}{second:02}"
        date_time_obj = datetime.strptime(timevalues, "%Y%m%d%H%M%S").astimezone()
        return date_time_obj

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

    def read_modbus_r6_realtime_data(self) -> dict[str, int | float | str]:
        """Read realtime data from inverter."""
        # Read in two batches due to Modbus limit of 125 registers
        first_read = self._read_holding_registers(unit=1, address=0x4000, count=125)
        second_read = self._read_holding_registers(unit=1, address=0x407D, count=121)

        if first_read.isError() or second_read.isError():
            return {}

        registers = first_read.registers + second_read.registers
        data = {}
        # MPV Mode
        mpvmode = registers[4]  # 0x4004
        data["mpvmode"] = mpvmode

        data["mpvstatus"] = DEVICE_STATUSSES.get(mpvmode, "Unknown")

        # Fault messages
        faultMsg0 = registers[5] << 16 | registers[6]  # 0x4005 + 0x4006
        faultMsg1 = registers[7] << 16 | registers[8]  # 0x4007 + 0x4008
        _faultMsg2 = registers[9] << 16 | registers[10]  # 0x4009 + 0x400A

        fault_messages_list = self.translate_fault_code_to_messages(
            faultMsg0, list(FAULT_MESSAGES[0].items())
        )
        fault_messages_list.extend(
            self.translate_fault_code_to_messages(
                faultMsg1, list(FAULT_MESSAGES[1].items())
            )
        )
        data["faultmsg"] = ", ".join(fault_messages_list).strip()[:254]
        if fault_messages_list:
            _LOGGER.error("Fault message: %s", ", ".join(fault_messages_list).strip())

        # PV Values
        data["pv1volt"] = round(registers[113] * 0.1, 1)  # 0x4071
        data["pv1curr"] = round(registers[114] * 0.01, 2)  # 0x4072
        data["pv1power"] = round(registers[115], 0)  # 0x4073

        data["pv2volt"] = round(registers[116] * 0.1, 1)  # 0x4074
        data["pv2curr"] = round(registers[117] * 0.01, 2)  # 0x4075
        data["pv2power"] = round(registers[118], 0)  # 0x4076

        data["pv3volt"] = round(registers[119] * 0.1, 1)  # 0x4077
        data["pv3curr"] = round(registers[120] * 0.01, 2)  # 0x4078
        data["pv3power"] = round(registers[121], 0)  # 0x4079

        # Bus Voltage
        data["busvolt"] = round(registers[103] * 0.1, 1)  # 0x4067 BusVoltMaster

        # Temperatures
        data["invtempc"] = round(
            self.convert_to_signed(registers[16]) * 0.1, 1
        )  # 0x4010 SinkTempC

        # Earth Leakage Current
        data["gfci"] = self.convert_to_signed(registers[18])  # 0x4012 GFCI

        # Phase measurements (l1 - RGrid)
        data["l1volt"] = round(registers[49] * 0.1, 1)  # 0x4031 RGridVolt
        data["l1curr"] = round(
            self.convert_to_signed(registers[50]) * 0.01, 2
        )  # 0x4032
        data["l1freq"] = round(registers[51] * 0.01, 2)  # 0x4033
        data["l1dci"] = self.convert_to_signed(registers[52])  # 0x4034
        data["l1power"] = self.convert_to_signed(registers[53])  # 0x4035
        data["l1pf"] = round(
            self.convert_to_signed(registers[55]) * 0.001, 3
        )  # 0x4037 (phase PF)

        # Phase measurements (l2 - SGrid)
        data["l2volt"] = round(registers[56] * 0.1, 1)  # 0x4038 SGridVolt
        data["l2curr"] = round(
            self.convert_to_signed(registers[57]) * 0.01, 2
        )  # 0x4039
        data["l2freq"] = round(registers[58] * 0.01, 2)  # 0x403A
        data["l2dci"] = self.convert_to_signed(registers[59])  # 0x403B
        data["l2power"] = self.convert_to_signed(registers[60])  # 0x403C
        data["l2pf"] = round(
            self.convert_to_signed(registers[62]) * 0.001, 3
        )  # 0x403E (phase PF)

        # Phase measurements (l3 - TGrid)
        data["l3volt"] = round(registers[63] * 0.1, 1)  # 0x403F TGridVolt
        data["l3curr"] = round(
            self.convert_to_signed(registers[64]) * 0.01, 2
        )  # 0x4040
        data["l3freq"] = round(registers[65] * 0.01, 2)  # 0x4041
        data["l3dci"] = self.convert_to_signed(registers[66])  # 0x4042
        data["l3power"] = self.convert_to_signed(registers[67])  # 0x4043
        data["l3pf"] = round(
            self.convert_to_signed(registers[69]) * 0.001, 3
        )  # 0x4045 (phase PF)

        # Isolation resistances
        data["iso1"] = registers[19]  # 0x4013
        data["iso2"] = registers[20]  # 0x4014
        data["iso3"] = registers[21]  # 0x4015
        data["iso4"] = registers[22]  # 0x4016

        # Energy counters
        data["todayenergy"] = round(
            (registers[191] << 16 | registers[192]) * 0.01, 2
        )  # 0x40BF
        data["monthenergy"] = round(
            (registers[193] << 16 | registers[194]) * 0.01, 2
        )  # 0x40C1
        data["yearenergy"] = round(
            (registers[195] << 16 | registers[196]) * 0.01, 2
        )  # 0x40C3
        data["totalenergy"] = round(
            (registers[197] << 16 | registers[198]) * 0.01, 2
        )  # 0x40C5

        # Working hours
        data["todayhour"] = round(registers[188] * 0.1, 1)  # 0x40BC
        data["totalhour"] = round(
            (registers[189] << 16 | registers[190]) * 0.1, 1
        )  # 0x40BD

        # Error count
        data["errorcount"] = registers[15]  # 0x400F

        # Datetime
        data["datetime"] = self.parse_datetime(registers[0:4])  # from 0x4000
        return data

    def read_modbus_inverter_power_state(self) -> dict[str, bool]:
        """Read the power state from the inverter."""
        power_state_data = self._read_holding_registers(unit=1, address=0x1037, count=1)
        if power_state_data.isError():
            _LOGGER.debug("Error reading power state data")
            return {}
        self._power_on_off = power_state_data.registers[0] == 1
        return {"poweronoff": self._power_on_off}

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
        """Write the power limit to the inverter."""
        response = self._write_registers(
            unit=1, address=0x801F, values=[int(value * 10)]
        )
        if response.isError():
            _LOGGER.error("Failed to set limitpower")
            return False
        return True

    def _write_power_on_off_sync(self, value: bool) -> bool:
        """Write the power on/off command to the inverter."""
        # According to the documentation, address 0x1037 is used for remote power on/off
        # 0: power off, 1: power on
        register_value = 1 if value else 0
        response = self._write_registers(
            unit=1, address=0x1037, values=[register_value]
        )
        if response.isError():
            _LOGGER.error("Failed to set power on/off")
            return False
        return True

    async def async_set_power_on_off(self, value: bool) -> bool:
        """Set the power on/off on the inverter."""
        if await self.hass.async_add_executor_job(self._write_power_on_off_sync, value):
            self._power_on_off = value
            if self.data:
                new_data = self.data.copy()
                new_data["poweronoff"] = value
                self.async_set_updated_data(new_data)
            return True
        return False

    async def async_set_limit_power(self, value: float) -> bool:
        """Set the power limit on the inverter."""
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
        if (
            limiter_entity_id is None
            or (ent_reg_entry := ent_reg.async_get(limiter_entity_id)) is None
        ):
            return True
        return ent_reg_entry.disabled
