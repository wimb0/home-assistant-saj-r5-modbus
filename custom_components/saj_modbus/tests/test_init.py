"""Test the SAJ Modbus integration."""
from unittest.mock import AsyncMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.saj_modbus.const import DOMAIN
from .const import MOCK_CONFIG


async def test_setup_unload_and_reload_entry(
    hass: HomeAssistant, mock_saj_modbus_hub: AsyncMock
) -> None:
    """Test setting up and removing the integration."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="test-entry",
    )
    config_entry.add_to_hass(hass)

    # Setup the integration
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    device_registry = dr.async_get(hass)
    assert device_registry.async_get_device(
        identifiers={(DOMAIN, MOCK_CONFIG["name"])}
    )

    # Unload the integration
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
