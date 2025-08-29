"""Common fixtures for the SAJ Modbus tests."""
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from custom_components.saj_modbus.const import DOMAIN

from .const import MOCK_CONFIG


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.saj_modbus.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_saj_modbus_hub() -> Generator[AsyncMock, None, None]:
    """Mock a SAJModbusHub successful setup."""
    with patch(
        "custom_components.saj_modbus.hub.SAJModbusHub",
        autospec=True,
    ) as hub_mock:
        hub = hub_mock.return_value
        hub.inverter_data = {"sn": "TEST-SN"}
        hub.data = {"power": 100}
        hub.async_config_entry_first_refresh.return_value = None
        yield hub
