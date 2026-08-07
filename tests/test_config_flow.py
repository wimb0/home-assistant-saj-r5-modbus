"""Tests for the SAJ Modbus config flow helpers."""

import pytest

from custom_components.saj_modbus.config_flow import host_valid


@pytest.mark.parametrize(
    "host",
    [
        "192.168.1.50",
        "::1",
        "2001:db8::1",
        "inverter",
        "inverter.local",
        "saj-r5.example.com",
        "example.com.",
    ],
)
def test_host_valid(host: str) -> None:
    """IP addresses and hostnames are accepted."""
    assert host_valid(host)


@pytest.mark.parametrize(
    "host",
    [
        "",
        " ",
        "-inverter",
        "inverter-",
        "inverter..local",
        "inverter/local",
        "192.168.1.999",
        "a" * 64,
    ],
)
def test_host_invalid(host: str) -> None:
    """Malformed hosts are rejected."""
    assert not host_valid(host)
