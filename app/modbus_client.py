"""Modbus TCP client for OpenPLC gate controller ESP8266."""

from __future__ import annotations

import time
from typing import Any

try:
    from pymodbus.client import ModbusTcpClient
    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False

# Physical relay output coils 0-3 (active-low)
COIL_Q_READY = 0          # %QX0.0  K1 READY
COIL_Q_REQUEST = 1        # %QX0.1  K2 REQUEST
COIL_Q_PASS_ALLOWED = 2   # %QX0.2  K3 PASS_ALLOWED
COIL_Q_EMERGENCY = 3      # %QX0.3  K4 EMERGENCY

# Status bits 4-7
COIL_STATUS_READY = 4         # %QX0.4
COIL_STATUS_REQUEST = 5       # %QX0.5
COIL_STATUS_PASS_ALLOWED = 6  # %QX0.6
COIL_STATUS_EMERGENCY = 7     # %QX0.7

# Command bits 8-12
COIL_CMD_ROBOT_REQUEST = 8    # %QX1.0
COIL_CMD_HMI_ALLOW = 9        # %QX1.1
COIL_CMD_ROBOT_PASSED = 10    # %QX1.2
COIL_CMD_EMERGENCY = 11       # %QX1.3
COIL_CMD_RESET = 12           # %QX1.4


class OpenPLCModbusClient:
    def __init__(
        self,
        host: str = "192.168.137.218",
        port: int = 502,
        device_id: int = 0,
        timeout: float = 3.0,
    ) -> None:
        self.host = host
        self.port = port
        self.device_id = device_id
        self.timeout = timeout
        self._client: Any = None
        self._connected = False

    def connect(self) -> bool:
        if not PYMODBUS_AVAILABLE:
            return False
        self.disconnect()
        try:
            self._client = ModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            ok = self._client.connect()
            self._connected = bool(ok)
            return self._connected
        except Exception:
            self._connected = False
            self._client = None
            return False

    def disconnect(self) -> None:
        self._connected = False
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    def read_status(self) -> dict[str, bool]:
        """Read status coils 4-7. Returns empty dict on failure."""
        if not self.is_connected():
            return {}
        try:
            result = self._client.read_coils(
                address=COIL_STATUS_READY,
                count=4,
                device_id=self.device_id,
            )
            if hasattr(result, "isError") and result.isError():
                self._connected = False
                return {}
            bits = result.bits
            return {
                "STATUS_READY": bool(bits[0]),
                "STATUS_REQUEST": bool(bits[1]),
                "STATUS_PASS_ALLOWED": bool(bits[2]),
                "STATUS_EMERGENCY": bool(bits[3]),
            }
        except Exception:
            self._connected = False
            return {}

    def read_outputs(self) -> dict[str, bool]:
        """Read physical relay output coils 0-3. Active-low logic is inverted here."""
        if not self.is_connected():
            return {}
        try:
            result = self._client.read_coils(
                address=COIL_Q_READY,
                count=4,
                device_id=self.device_id,
            )
            if hasattr(result, "isError") and result.isError():
                return {}
            bits = result.bits
            return {
                "K1_READY": not bool(bits[0]),
                "K2_REQUEST": not bool(bits[1]),
                "K3_PASS_ALLOWED": not bool(bits[2]),
                "K4_EMERGENCY": not bool(bits[3]),
            }
        except Exception:
            return {}

    def write_coil(self, address: int, value: bool) -> bool:
        """Write a single coil. Used by GUI with QTimer.singleShot for non-blocking pulses."""
        if not self.is_connected():
            return False
        try:
            result = self._client.write_coil(
                address=address,
                value=bool(value),
                device_id=self.device_id,
            )
            if hasattr(result, "isError") and result.isError():
                return False
            return True
        except Exception:
            self._connected = False
            return False

    def pulse_coil(self, address: int, duration: float = 0.3) -> bool:
        """Blocking pulse: write True, sleep, write False. For test scripts only."""
        if not self.write_coil(address, True):
            return False
        time.sleep(duration)
        return self.write_coil(address, False)

    def allow(self) -> bool:
        """CMD_HMI_ALLOW coil 9, 1000 ms pulse. Blocking — use write_coil+QTimer in GUI."""
        return self.pulse_coil(COIL_CMD_HMI_ALLOW, 1.0)

    def emergency(self) -> bool:
        """CMD_EMERGENCY coil 11, 300 ms pulse. Blocking — use write_coil+QTimer in GUI."""
        return self.pulse_coil(COIL_CMD_EMERGENCY, 0.3)

    def reset(self) -> bool:
        """CMD_RESET coil 12, 300 ms pulse. Blocking — use write_coil+QTimer in GUI."""
        return self.pulse_coil(COIL_CMD_RESET, 0.3)

    def robot_request(self) -> bool:
        """CMD_ROBOT_REQUEST coil 8, 300 ms pulse. Debug/test use."""
        return self.pulse_coil(COIL_CMD_ROBOT_REQUEST, 0.3)

    def robot_passed(self) -> bool:
        """CMD_ROBOT_PASSED coil 10, 300 ms pulse. Debug/test use."""
        return self.pulse_coil(COIL_CMD_ROBOT_PASSED, 0.3)

    @staticmethod
    def get_state_name(status: dict[str, bool]) -> str:
        """Derive logical state name from status coils dict."""
        if not status:
            return "UNKNOWN"
        if status.get("STATUS_EMERGENCY"):
            return "EMERGENCY"
        if status.get("STATUS_PASS_ALLOWED"):
            return "PASS_ALLOWED"
        if status.get("STATUS_REQUEST"):
            return "REQUEST"
        if status.get("STATUS_READY"):
            return "READY"
        return "UNKNOWN"
