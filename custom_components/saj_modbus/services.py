"""SAJ Modbus services."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr, config_validation as cv

from .const import DOMAIN as SAJ_DOMAIN

ATTR_DATETIME = "datetime"

SERVICE_SET_DATE_TIME = "set_datetime"

SERVICE_SET_DATE_TIME_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(ATTR_DEVICE_ID): str,
            vol.Optional(ATTR_DATETIME): cv.datetime,
        }
    )
)

SUPPORTED_SERVICES = (SERVICE_SET_DATE_TIME,)

SERVICE_TO_SCHEMA = {
    SERVICE_SET_DATE_TIME: SERVICE_SET_DATE_TIME_SCHEMA,
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for SAJ Modbus integration."""

    services = {
        SERVICE_SET_DATE_TIME: async_set_date_time,
    }

    async def async_call_service(service_call: ServiceCall) -> None:
        """Call correct SAJ Modbus service."""
        await services[service_call.service](hass, service_call.data)

    for service in SUPPORTED_SERVICES:
        hass.services.async_register(
            SAJ_DOMAIN,
            service,
            async_call_service,
            schema=SERVICE_TO_SCHEMA.get(service),
        )


@callback
def async_unload_services(hass: HomeAssistant) -> None:
    """Unload SAJ Modbus services."""
    for service in SUPPORTED_SERVICES:
        hass.services.async_remove(SAJ_DOMAIN, service)


async def async_set_date_time(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Set the date and time on the inverter."""
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(data[ATTR_DEVICE_ID])

    hub = hass.data[SAJ_DOMAIN][device_entry.name]["hub"]
    await hass.async_add_executor_job(
        hub.set_date_and_time, data.get(ATTR_DATETIME, None)
    )
