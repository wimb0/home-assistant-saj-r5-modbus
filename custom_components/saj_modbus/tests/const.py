"""Constants for SAJ Modbus tests."""
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL

from custom_components.saj_modbus.const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
)

MOCK_CONFIG = {
    CONF_NAME: DEFAULT_NAME,
    CONF_HOST: "192.168.99.11",
    CONF_PORT: DEFAULT_PORT,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}
