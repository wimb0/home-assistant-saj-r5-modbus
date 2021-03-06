"""The SAJ Modbus Integration."""
import asyncio
import logging
import threading
from datetime import timedelta
from typing import Optional

import voluptuous as vol
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.exceptions import ConnectionException

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_time_interval
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_STATUSSES,
)

_LOGGER = logging.getLogger(__name__)

SAJ_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: SAJ_MODBUS_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = ["sensor"]


async def async_setup(hass, config):
    """Set up the SAJ modbus component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up a SAJ mobus."""
    host = entry.data[CONF_HOST]
    name = entry.data[CONF_NAME]
    port = entry.data[CONF_PORT]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    hub = SAJModbusHub(
        hass, name, host, port, scan_interval
    )
    """Register the hub."""
    hass.data[DOMAIN][name] = {"hub": hub}

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    return True


async def async_unload_entry(hass, entry):
    """Unload SAJ mobus entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(
                    entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.data["name"])
    return True


class SAJModbusHub:
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
        scan_interval,
    ):
        """Initialize the Modbus hub."""
        self._hass = hass
        self._client = ModbusTcpClient(host=host, port=port, timeout=5)
        self._lock = threading.Lock()
        self._name = name
        self._scan_interval = timedelta(seconds=scan_interval)
        self._unsub_interval_method = None
        self._sensors = []
        self.data = {}

    @callback
    def async_add_saj_sensor(self, update_callback):
        """Listen for data updates."""
        # This is the first sensor, set up interval.
        if not self._sensors:
            self.connect()
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self.async_refresh_modbus_data, self._scan_interval
            )

        self._sensors.append(update_callback)

    @callback
    def async_remove_saj_sensor(self, update_callback):
        """Remove data update."""
        self._sensors.remove(update_callback)

        if not self._sensors:
            """stop the interval timer upon removal of last sensor"""
            self._unsub_interval_method()
            self._unsub_interval_method = None
            self.close()

    async def async_refresh_modbus_data(self, _now: Optional[int] = None) -> None:
        """Time to update."""
        if not self._sensors:
            return

        update_result = self.read_modbus_data()

        if update_result:
            for update_callback in self._sensors:
                update_callback()

    @property
    def name(self):
        """Return the name of this hub."""
        return self._name

    def close(self):
        """Disconnect client."""
        with self._lock:
            self._client.close()

    def connect(self):
        """Connect client."""
        with self._lock:
            self._client.connect()

    def read_holding_registers(self, unit, address, count):
        """Read holding registers."""
        with self._lock:
            kwargs = {"unit": unit} if unit else {}
            return self._client.read_holding_registers(address, count, **kwargs)

    def calculate_value(self, value, sf):
        return value * 10 ** sf

    def read_modbus_data(self):
        return (
            self.read_modbus_inverter_data()
            and self.read_modbus_realtime_data()
        )

    def read_modbus_inverter_data(self):
        inverter_data = self.read_holding_registers(
            unit=1, address=36608, count=29)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )

            devtype = decoder.decode_16bit_uint()
            self.data["devtype"] = devtype
            subtype = decoder.decode_16bit_uint()
            self.data["subtype"] = devtype
            commver = decoder.decode_16bit_uint()
            self.data["commver"] = round(commver * 0.001, 3)

            sn = decoder.decode_string(20).decode('ascii')
            self.data["sn"] = str(sn)
            pc = decoder.decode_string(20).decode('ascii')
            self.data["pc"] = str(pc)

            dv = decoder.decode_16bit_uint()
            self.data["dv"] = round(dv * 0.001, 3)
            mcv = decoder.decode_16bit_uint()
            self.data["mcv"] = round(mcv * 0.001, 3)
            scv = decoder.decode_16bit_uint()
            self.data["scv"] = round(scv * 0.001, 3)
            disphwversion = decoder.decode_16bit_uint()
            self.data["disphwversion"] = round(disphwversion * 0.001, 3)
            ctrlhwversion = decoder.decode_16bit_uint()
            self.data["ctrlhwversion"] = round(ctrlhwversion * 0.001, 3)
            powerhwversion = decoder.decode_16bit_uint()
            self.data["powerhwversion"] = round(powerhwversion * 0.001, 3)

            return True
        else:
            return False

    def read_modbus_realtime_data(self):
        realtime_data = self.read_holding_registers(
            unit=1, address=256, count=60)
        if not realtime_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                realtime_data.registers, byteorder=Endian.Big
            )

            mpvmode = decoder.decode_16bit_uint()
            self.data["mpvmode"] = mpvmode

            if mpvmode in DEVICE_STATUSSES:
                self.data["mpvstatus"] = DEVICE_STATUSSES[mpvmode]
            else:
                self.data["mpvstatus"] = "Unknown"

            # TODO: read fault message
            # faultmsg = decoder.decode_16bit_uint()
            # skip 6 registers
            decoder.skip_bytes(12)

            pv1volt = decoder.decode_16bit_uint()
            pv1curr = decoder.decode_16bit_uint()
            pv1power = decoder.decode_16bit_uint()
            self.data["pv1volt"] = round(pv1volt * 0.1, 1)
            self.data["pv1curr"] = round(pv1curr * 0.01, 2)
            self.data["pv1power"] = round(pv1power * 1, 0)

            pv2volt = decoder.decode_16bit_uint()
            pv2curr = decoder.decode_16bit_uint()
            pv2power = decoder.decode_16bit_uint()
            self.data["pv2volt"] = round(pv2volt * 0.1, 1)
            self.data["pv2curr"] = round(pv2curr * 0.01, 2)
            self.data["pv2power"] = round(pv2power * 1, 0)

            pv3volt = decoder.decode_16bit_uint()
            pv3curr = decoder.decode_16bit_uint()
            pv3power = decoder.decode_16bit_uint()
            self.data["pv3volt"] = round(pv3volt * 0.1, 1)
            self.data["pv3curr"] = round(pv3curr * 0.01, 2)
            self.data["pv3power"] = round(pv3power * 1, 0)

            busvolt = decoder.decode_16bit_uint()
            self.data["busvolt"] = round(busvolt * 0.1, 1)

            invtempc = decoder.decode_16bit_int()
            self.data["invtempc"] = round(invtempc * 0.1, 1)

            gfci = decoder.decode_16bit_int()
            self.data["gfci"] = gfci

            power = decoder.decode_16bit_uint()
            self.data["power"] = power

            qpower = decoder.decode_16bit_int()
            self.data["qpower"] = qpower

            pf = decoder.decode_16bit_int()
            self.data["pf"] = round(pf * 0.001, 3)

            l1volt = decoder.decode_16bit_uint()
            l1curr = decoder.decode_16bit_uint()
            l1freq = decoder.decode_16bit_uint()
            l1dci = decoder.decode_16bit_int()
            l1power = decoder.decode_16bit_uint()
            l1pf = decoder.decode_16bit_int()
            self.data["l1volt"] = round(l1volt * 0.1, 1)
            self.data["l1curr"] = round(l1curr * 0.01, 2)
            self.data["l1freq"] = round(l1freq * 0.01, 2)
            self.data["l1dci"] = l1dci
            self.data["l1power"] = l1power
            self.data["l1pf"] = round(l1pf * 0.001, 3)

            l2volt = decoder.decode_16bit_uint()
            l2curr = decoder.decode_16bit_uint()
            l2freq = decoder.decode_16bit_uint()
            l2dci = decoder.decode_16bit_int()
            l2power = decoder.decode_16bit_uint()
            l2pf = decoder.decode_16bit_int()
            self.data["l2volt"] = round(l2volt * 0.1, 1)
            self.data["l2curr"] = round(l2curr * 0.01, 2)
            self.data["l2freq"] = round(l2freq * 0.01, 2)
            self.data["l2dci"] = l2dci
            self.data["l2power"] = l2power
            self.data["l2pf"] = round(l2pf * 0.001, 3)

            l3volt = decoder.decode_16bit_uint()
            l3curr = decoder.decode_16bit_uint()
            l3freq = decoder.decode_16bit_uint()
            l3dci = decoder.decode_16bit_int()
            l3power = decoder.decode_16bit_uint()
            l3pf = decoder.decode_16bit_int()
            self.data["l3volt"] = round(l3volt * 0.1, 1)
            self.data["l3curr"] = round(l3curr * 0.01, 2)
            self.data["l3freq"] = round(l3freq * 0.01, 2)
            self.data["l3dci"] = l3dci
            self.data["l3power"] = l3power
            self.data["l3pf"] = round(l3pf * 0.001, 3)

            iso1 = decoder.decode_16bit_uint()
            iso2 = decoder.decode_16bit_uint()
            iso3 = decoder.decode_16bit_uint()
            iso4 = decoder.decode_16bit_uint()
            self.data["iso1"] = iso1
            self.data["iso2"] = iso2
            self.data["iso3"] = iso3
            self.data["iso4"] = iso4

            todayenergy = decoder.decode_16bit_uint()
            monthenergy = decoder.decode_32bit_uint()
            yearenergy = decoder.decode_32bit_uint()
            totalenergy = decoder.decode_32bit_uint()
            self.data["todayenergy"] = round(todayenergy * 0.01, 2)
            self.data["monthenergy"] = round(monthenergy * 0.01, 2)
            self.data["yearenergy"] = round(yearenergy * 0.01, 2)
            self.data["totalenergy"] = round(totalenergy * 0.01, 2)

            todayhour = decoder.decode_16bit_uint()
            self.data["todayhour"] = round(todayhour * 0.1, 1)
            totalhour = decoder.decode_32bit_uint()
            self.data["totalhour"] = round(totalhour * 0.1, 1)

            errorcount = decoder.decode_16bit_uint()
            self.data["errorcount"] = errorcount

            return True
        else:
            return False
