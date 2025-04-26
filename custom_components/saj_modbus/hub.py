"""Modified 'SAJ Modbus Hub' to support R6 registers"""

"""SAJ Modbus Hub."""

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from voluptuous.validators import Number
import logging
import threading
from datetime import datetime, timedelta
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
                self.read_modbus_r6_realtime_data
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

    def read_modbus_r6_realtime_data(self) -> dict:
        """Read realtime data from R6 inverter."""
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
    
        DEVICE_STATUSSES = {
            0: "Initialize",
            1: "Waiting",
            2: "Normal",
            3: "Off-Grid",
            4: "Grid with Load",
            5: "Fault",
            6: "Upgrading",
            7: "Debug",
            8: "Auto-Check",
            9: "Reset",
        }
    
        data["mpvstatus"] = DEVICE_STATUSSES.get(mpvmode, "Unknown")
    
        # Fault messages
        faultMsg0 = registers[5] << 16 | registers[6]  # 0x4005 + 0x4006
        faultMsg1 = registers[7] << 16 | registers[8]  # 0x4007 + 0x4008
        faultMsg2 = registers[9] << 16 | registers[10]  # 0x4009 + 0x400A
    
        faultMsg = []
        faultMsg.extend(self.translate_fault_code_to_messages(faultMsg0, FAULT_MESSAGES[0].items()))
        faultMsg.extend(self.translate_fault_code_to_messages(faultMsg1, FAULT_MESSAGES[1].items()))
        faultMsg.extend(self.translate_fault_code_to_messages(faultMsg2, FAULT_MESSAGES[2].items()))
        data["faultmsg"] = ", ".join(faultMsg).strip()[0:254]
    
        # PV Values
        data["pv1volt"] = round(registers[113] * 0.1, 1)  # 0x4071
        data["pv1curr"] = round(registers[114] * 0.01, 2)  # 0x4072
        data["pv1power"] = round(registers[115], 0)        # 0x4073
    
        data["pv2volt"] = round(registers[116] * 0.1, 1)   # 0x4074
        data["pv2curr"] = round(registers[117] * 0.01, 2)  # 0x4075
        data["pv2power"] = round(registers[118], 0)        # 0x4076
    
        data["pv3volt"] = round(registers[119] * 0.1, 1)   # 0x4077
        data["pv3curr"] = round(registers[120] * 0.01, 2)  # 0x4078
        data["pv3power"] = round(registers[121], 0)        # 0x4079
    
        # Bus Voltage
        data["busvolt"] = round(registers[103] * 0.1, 1)  # 0x4067 BusVoltMaster
    
        # Temperatures
        data["invtempc"] = round(self.convert_to_signed(registers[16]) * 0.1, 1)  # 0x4010 SinkTempC
    
        # Earth Leakage Current
        data["gfci"] = self.convert_to_signed(registers[18])  # 0x4012 GFCI
    

        # Phase measurements (l1 - RGrid)
        data["l1volt"] = round(registers[49] * 0.1, 1)  # 0x4031 RGridVolt
        data["l1curr"] = round(self.convert_to_signed(registers[50]) * 0.01, 2)  # 0x4032
        data["l1freq"] = round(registers[51] * 0.01, 2)  # 0x4033
        data["l1dci"] = self.convert_to_signed(registers[52])  # 0x4034
        data["l1power"] = self.convert_to_signed(registers[53])  # 0x4035
        data["l1pf"] = round(self.convert_to_signed(registers[55]) * 0.001, 3)  # 0x4037 (phase PF)
    
        # Phase measurements (l2 - SGrid)
        data["l2volt"] = round(registers[56] * 0.1, 1)  # 0x4038 SGridVolt
        data["l2curr"] = round(self.convert_to_signed(registers[57]) * 0.01, 2)  # 0x4039
        data["l2freq"] = round(registers[58] * 0.01, 2)  # 0x403A
        data["l2dci"] = self.convert_to_signed(registers[59])  # 0x403B
        data["l2power"] = self.convert_to_signed(registers[60])  # 0x403C
        data["l2pf"] = round(self.convert_to_signed(registers[62]) * 0.001, 3)  # 0x403E (phase PF)

        # Phase measurements (l3 - TGrid)
        data["l3volt"] = round(registers[63] * 0.1, 1)  # 0x403F TGridVolt
        data["l3curr"] = round(self.convert_to_signed(registers[64]) * 0.01, 2)  # 0x4040
        data["l3freq"] = round(registers[65] * 0.01, 2)  # 0x4041
        data["l3dci"] = self.convert_to_signed(registers[66])  # 0x4042
        data["l3power"] = self.convert_to_signed(registers[67])  # 0x4043
        data["l3pf"] = round(self.convert_to_signed(registers[69]) * 0.001, 3)  # 0x4045 (phase PF)

        # Isolation resistances
        data["iso1"] = registers[19]  # 0x4013
        data["iso2"] = registers[20]  # 0x4014
        data["iso3"] = registers[21]  # 0x4015
        data["iso4"] = registers[22]  # 0x4016
    
        # Energy counters
        data["todayenergy"] = round((registers[191] << 16 | registers[192]) * 0.01, 2)  # 0x40BF
        data["monthenergy"] = round((registers[193] << 16 | registers[194]) * 0.01, 2)  # 0x40C1
        data["yearenergy"] = round((registers[195] << 16 | registers[196]) * 0.01, 2)   # 0x40C3
        data["totalenergy"] = round((registers[197] << 16 | registers[198]) * 0.01, 2)  # 0x40C5
    
        # Working hours
        data["todayhour"] = round(registers[188] * 0.1, 1)  # 0x40BC
        data["totalhour"] = round((registers[189] << 16 | registers[190]) * 0.1, 1)  # 0x40BD
    
        # Error count
        data["errorcount"] = registers[15]  # 0x400F
    
        # Datetime
        data["datetime"] = self.parse_datetime(registers[0:4])  # from 0x4000
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
