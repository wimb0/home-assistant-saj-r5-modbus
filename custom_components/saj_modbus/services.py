"""SAJ Modbus services."""

import logging

import voluptuous as vol

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

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


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the SAJ Modbus integration."""

    async def async_set_date_time(service_call: ServiceCall) -> None:
        """Service handler to set the date and time on the inverter."""
        device_registry = dr.async_get(hass)
        device_id = service_call.data[ATTR_DEVICE_ID]
        date_time = service_call.data.get(ATTR_DATETIME)

        device_entry = device_registry.async_get(device_id)
        if not device_entry:
            raise HomeAssistantError(f"Device not found: {device_id}")

        # Vind de config entry die bij dit apparaat hoort
        config_entry_id = next(iter(device_entry.config_entries))
        config_entry = hass.config_entries.async_get_entry(config_entry_id)

        if not config_entry or not hasattr(config_entry, "runtime_data"):
            raise HomeAssistantError(f"Config entry not found for device: {device_id}")

        hub: SAJModbusHub | None = config_entry.runtime_data.get("hub")
        if not hub:
            raise HomeAssistantError(f"Hub not found for device: {device_id}")

        try:
            await hass.async_add_executor_job(hub.set_date_and_time, date_time)
        except Exception as ex:
            _LOGGER.error("Error setting date and time on inverter: %s", ex)
            raise HomeAssistantError(
                f"Error setting date and time on inverter: {ex}"
            ) from ex

    hass.services.async_register(
        SAJ_DOMAIN,
        SERVICE_SET_DATE_TIME,
        async_set_date_time,
        schema=SERVICE_SET_DATE_TIME_SCHEMA,
    )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload SAJ Modbus services."""
    hass.services.async_remove(SAJ_DOMAIN, SERVICE_SET_DATE_TIME)
