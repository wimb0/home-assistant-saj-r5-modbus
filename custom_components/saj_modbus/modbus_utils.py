import asyncio
import logging
import inspect
from typing import Any, Awaitable, Callable, List, Optional, Union

from pymodbus.exceptions import ConnectionException, ModbusIOException

from .const import ModbusClient, Lock

_LOGGER = logging.getLogger(__name__)

# Set to True to enable detailed Modbus read attempt logging, False to disable
ENABLE_DETAILED_MODBUS_READ_LOGGING = False

class ReconnectionNeededError(Exception):
    """Indicates that a reconnect is needed due to communication failure."""
    pass

# Global Modbus config storage
class ModbusGlobalConfig:
    host: Optional[str] = None
    port: Optional[int] = None

def set_modbus_config(host: str, port: int) -> None:
    ModbusGlobalConfig.host = host
    ModbusGlobalConfig.port = port
    _LOGGER.debug(f"Global Modbus config set: {host}:{port}")

async def _exponential_backoff(attempt: int, base: float, cap: float) -> None:
    delay = min(base * 2 ** (attempt - 1), cap)
    _LOGGER.debug(f"Backoff: waiting {delay:.2f}s before retry #{attempt}")
    await asyncio.sleep(delay)

async def _retry_with_backoff(
    func: Callable[[], Awaitable[Any]],
    should_retry: Callable[[Exception], bool],
    retries: int,
    base_delay: float,
    cap: float,
    on_retry: Optional[Callable[[int, Exception], Awaitable[None]]] = None,
    task_name: str = "Task"
) -> Any:
    last_exception: Exception
    for attempt in range(1, retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if not should_retry(e):
                _LOGGER.error("Non-retriable exception occurred", exc_info=True)
                raise
            _LOGGER.warning(f"[{task_name}] Attempt {attempt} failed: {e}", exc_info=(attempt == retries))
            if on_retry:
                await on_retry(attempt, e)
            if attempt < retries:
                await _exponential_backoff(attempt, base_delay, cap)
    _LOGGER.warning(f"[{task_name}] All {retries} attempts failed: {last_exception}")
    raise last_exception

class ModbusConnection:
    """Async context manager for Modbus TCP connections with auto-connect and close."""
    def __init__(
        self,
        client: ModbusClient,
        host: str,
        port: int,
        max_retries: int = 3,
        timeout: float = 10.0,
        backoff_base: float = 2.0
    ):
        self._client = client
        self._host = host
        self._port = port
        self._max_retries = max_retries
        self._timeout = timeout
        self._backoff_base = backoff_base

    async def __aenter__(self) -> ModbusClient:
        await self.connect()
        return self._client

    async def __aexit__(
        self, exc_type: Any, exc: Any, tb: Any
    ) -> None:
        try:
            timeout = self._timeout or 5.0
            async with asyncio.timeout(timeout):
                close_fn = getattr(self._client, "close", None)
                if close_fn:
                    if inspect.iscoroutinefunction(close_fn):
                        await close_fn()
                    else:
                        close_fn()
        except Exception:
            _LOGGER.warning("Error closing Modbus connection", exc_info=True)

    async def connect(self) -> None:
        async def do_connect():
            await asyncio.wait_for(
                self._client.connect(), timeout=self._timeout
            )
            if not self._client.connected:
                raise ConnectionException("Connection failed")
            return True

        async def on_retry(attempt: int, e: Exception) -> None:
            _LOGGER.info(f"Reconnect attempt {attempt} after error: {e}")

        await _retry_with_backoff(
            func=do_connect,
            should_retry=lambda e: isinstance(e, ConnectionException),
            retries=self._max_retries,
            base_delay=self._backoff_base,
            cap=self._backoff_base ** self._max_retries,
            on_retry=on_retry,
            task_name="Modbus-Connect"
        )

# Default retry settings
DEFAULT_READ_RETRIES = 3
DEFAULT_READ_BASE_DELAY = 2.0
DEFAULT_READ_CAP_DELAY = 10.0

DEFAULT_WRITE_RETRIES = 2
DEFAULT_WRITE_BASE_DELAY = 1.0
DEFAULT_WRITE_CAP_DELAY = 5.0

async def _ensure_connected(
    client: ModbusClient,
    operation_name: str
) -> None:
    """Ensure the client is connected before performing an operation."""
    host = ModbusGlobalConfig.host
    port = ModbusGlobalConfig.port
    
    if not client.connected:
        if host is None or port is None:
            raise ReconnectionNeededError("Client not connected and no host/port available")
        _LOGGER.info(f"Client not connected, reconnecting before {operation_name}...")
        async with ModbusConnection(client, host, port):
            _LOGGER.info(f"Reconnect before {operation_name} successful")

def _create_retry_handlers(client: ModbusClient, operation_name: str):
    """Create standard retry handlers for Modbus operations."""
    host = ModbusGlobalConfig.host
    port = ModbusGlobalConfig.port
    
    def should_retry(e: Exception) -> bool:
        return isinstance(e, (ConnectionException, ModbusIOException))

    async def on_retry(attempt: int, e: Exception) -> None:
        if isinstance(e, ConnectionException) and host and port:
            _LOGGER.info(f"Connection lost during {operation_name}, attempting reconnect")
            async with ModbusConnection(client, host, port):
                _LOGGER.info(f"Reconnect during {operation_name} successful")
    
    return should_retry, on_retry

async def _perform_modbus_operation(
    client: ModbusClient,
    lock: Lock,
    unit: int,
    operation: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    Performs a Modbus operation, setting the unit_id on the client.
    This is a workaround for Home Assistant's ModbusClientMixin,
    as 'slave'/'device_id' keyword arguments are not accepted in method calls.
    """
    async with lock:
        client.unit_id = unit
        return await operation(*args, **kwargs)

async def try_read_registers(
    client: ModbusClient,
    lock: Lock,
    unit: int,
    address: int,
    count: int,
    max_retries: int = DEFAULT_READ_RETRIES,
    base_delay: float = DEFAULT_READ_BASE_DELAY,
    cap_delay: float = DEFAULT_READ_CAP_DELAY,
) -> List[int]:
    await _ensure_connected(client, "read")

    should_retry, on_retry = _create_retry_handlers(client, "read")
    
    async def read_once():
        response = await _perform_modbus_operation(
            client, lock, unit, client.read_holding_registers, address=address, count=count
        )

        # Detect specific exception error early
        if response.isError():
            exc_code = getattr(response, "exception_code", None)
            if exc_code == 1:  # Illegal Function (Exception Code 1)
                raise ValueError("Unsupported register (Exception response 131 / 0)")
            raise ModbusIOException("General Modbus read error")

        if not hasattr(response, "registers"):
            raise ModbusIOException("No registers in response")

        return response.registers  # type: ignore
    
    async def on_read_retry(attempt: int, e: Exception) -> None:
        _LOGGER.warning(f"[Modbus-Read] Retry {attempt} after error: {e}")
        await on_retry(attempt, e)

    return await _retry_with_backoff(
        func=read_once,
        should_retry=should_retry,
        retries=max_retries,
        base_delay=base_delay,
        cap=cap_delay,
        on_retry=on_read_retry,
        task_name="Modbus-Read"
    )


async def try_write_registers(
    client: ModbusClient,
    lock: Lock,
    unit: int,
    address: int,
    values: Union[int, List[int]],
    max_retries: int = DEFAULT_WRITE_RETRIES,
    base_delay: float = DEFAULT_WRITE_BASE_DELAY,
    cap_delay: float = DEFAULT_WRITE_CAP_DELAY,
) -> bool:
    await _ensure_connected(client, "write")
    should_retry, on_retry = _create_retry_handlers(client, "write")
    
    is_single = isinstance(values, int)

    async def write_once() -> bool:
        if is_single:
            result = await _perform_modbus_operation(
                client, lock, unit, client.write_register, address=address, value=values
            )
        else:
            result = await _perform_modbus_operation(
                client, lock, unit, client.write_registers, address=address, values=values
            )
        if result.isError():
            raise ModbusIOException("Write response error")
        return True

    return await _retry_with_backoff(
        func=write_once,
        should_retry=should_retry,
        retries=max_retries,
        base_delay=base_delay,
        cap=cap_delay,
        on_retry=on_retry,
        task_name="Modbus-Write"
    )
