"""SAJ Modbus Hub."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError

from .const import (
    DEVICE_STATUSSES,
    DOMAIN,
    FAULT_MESSAGES,
)
from .inverter import SajR5Inverter, component_values

_LOGGER = logging.getLogger(__name__)


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
        entry: ConfigEntry,
        name: str,
        device: SajR5Inverter,
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

        self.device = device
        self.inverter_data: dict[str, int | float | str] = {}
        self._power_limit: float = 110.0

    async def _async_update_data(self) -> dict[str, int | float | str]:
        """Fetch realtime data from the inverter."""
        try:
            # Static inverter info is fetched once and cached.
            if not self.inverter_data:
                await self.device.info.async_update()
                self.inverter_data = component_values(self.device.info)
            await self.device.realtime.async_update()
        except ModbusError as ex:
            raise UpdateFailed(f"Failed to fetch realtime data: {ex}") from ex

        data = {**self.inverter_data, **self._realtime_values()}
        data["limitpower"] = self._power_limit
        return data

    def _realtime_values(self) -> dict[str, int | float | str]:
        """Return the realtime component's values with derived fields."""
        data = component_values(self.device.realtime)
        mpvmode = data["mpvmode"]
        data["mpvstatus"] = DEVICE_STATUSSES.get(mpvmode, "Unknown")
        fault_messages_list = [
            message
            for index in range(3)
            for message in translate_fault_code_to_messages(
                data.pop(f"faultmsg{index}") or 0, FAULT_MESSAGES[index]
            )
        ]
        data["faultmsg"] = ", ".join(fault_messages_list).strip()[:254]
        if fault_messages_list:
            _LOGGER.error("Fault message: %s", ", ".join(fault_messages_list).strip())
        return data

    async def async_set_power_on_off(self, value: bool) -> bool:
        """Set the power on/off on the inverter."""
        try:
            await self.device.realtime.write("poweronoff", value)
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
            NUMBER_DOMAIN, DOMAIN, f"{self.name}_limitpower"
        )
        if (
            limiter_entity_id is None
            or (ent_reg_entry := ent_reg.async_get(limiter_entity_id)) is None
        ):
            return True
        return ent_reg_entry.disabled
