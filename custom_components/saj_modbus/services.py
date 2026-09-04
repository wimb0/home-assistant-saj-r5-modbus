"""SAJ Modbus services."""

import logging

import voluptuous as vol

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusError

from .const import DOMAIN as SAJ_DOMAIN
from .hub import SAJModbusHub

_LOGGER = logging.getLogger(__name__)

ATTR_DATETIME = "datetime"
SERVICE_SET_DATE_TIME = "set_datetime"

SERVICE_SET_DATE_TIME_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_DEVICE_ID): cv.string,
            vol.Optional(ATTR_DATETIME): cv.datetime,
        }
    )
)


def _async_hub_for_device(hass: HomeAssistant, device_id: str) -> SAJModbusHub:
    """Return the loaded hub owning ``device_id``."""
    device_entry = dr.async_get(hass).async_get(device_id)
    if not device_entry:
        raise HomeAssistantError(f"Device not found: {device_id}")

    for config_entry_id in device_entry.config_entries:
        config_entry = hass.config_entries.async_get_entry(config_entry_id)
        if config_entry is None or config_entry.domain != SAJ_DOMAIN:
            continue
        hub: SAJModbusHub | None = getattr(config_entry, "runtime_data", None)
        if hub is not None:
            return hub

    raise HomeAssistantError(f"No loaded SAJ inverter for device: {device_id}")


async def _async_set_date_time(service_call: ServiceCall) -> None:
    """Service handler to set the date and time on the inverter."""
    hub = _async_hub_for_device(service_call.hass, service_call.data[ATTR_DEVICE_ID])
    try:
        await hub.async_set_date_and_time(service_call.data.get(ATTR_DATETIME))
    except ModbusError as ex:
        _LOGGER.error("Error setting date and time on inverter: %s", ex)
        raise HomeAssistantError(
            f"Error setting date and time on inverter: {ex}"
        ) from ex


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the SAJ Modbus services.

    Services are integration-wide, so this runs once from async_setup rather
    than per config entry — otherwise unloading one inverter would remove the
    service for every other one.
    """
    hass.services.async_register(
        SAJ_DOMAIN,
        SERVICE_SET_DATE_TIME,
        _async_set_date_time,
        schema=SERVICE_SET_DATE_TIME_SCHEMA,
    )
