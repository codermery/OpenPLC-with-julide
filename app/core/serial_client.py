"""Serial client wrapper for future ESP8266 communication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import serial
from serial import SerialException

from app.core.protocol import decode_json_line


@dataclass(slots=True)
class SerialStatus:
    connected: bool = False
    last_error: str = ""


class SerialClient:
    def __init__(self, port: str, baudrate: int = 115200) -> None:
        self.port = port
        self.baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self.status = SerialStatus()

    def connect(self) -> bool:
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=0.02)
            self.status.connected = True
            self.status.last_error = ""
            return True
        except (SerialException, OSError) as exc:
            self.status.connected = False
            self.status.last_error = str(exc)
            self._serial = None
            return False

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self.status.connected = False

    def send_line(self, payload: str) -> bool:
        if not self._serial or not self._serial.is_open:
            self.status.connected = False
            return False
        try:
            self._serial.write((payload + "\n").encode("utf-8"))
            return True
        except (SerialException, OSError) as exc:
            self.status.connected = False
            self.status.last_error = str(exc)
            return False

    def read_message(self) -> Optional[dict]:
        if not self._serial or not self._serial.is_open:
            return None
        try:
            line = self._serial.readline().decode("utf-8", errors="ignore")
            if not line.strip():
                return None
            msg = decode_json_line(line)
            if msg is None:
                self.status.last_error = "Malformed JSON line received"
            return msg
        except (SerialException, OSError, UnicodeError) as exc:
            self.status.connected = False
            self.status.last_error = str(exc)
            return None
