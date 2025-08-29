"""Common fixtures for the SAJ Modbus tests."""
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.saj_modbus.hub import SAJModbusHub


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
        hub.inverter_data = {
            "sn": "TEST-SERIALNUMBER",
            "devtype": 1,
            "subtype": 21,
            "commver": 1.0,
            "pc": "TEST-PRODUCTCODE",
            "dv": 2.0,
            "mcv": 3.0,
            "scv": 4.0,
            "disphwversion": 5.0,
            "ctrlhwversion": 6.0,
            "powerhwversion": 7.0,
        }
        hub.data = {
            "mpvmode": 2,  # Normal
            "power": 2811,
            "todayenergy": 10.5,
            "limitpower": 110.0,
            "poweronoff": 1,
            # Add other sensor values as needed
        }
        # To access the hub instance from the test
        SAJModbusHub.instance = hub
        yield hub
