"""HTTP client for OpenPLC gate controller ESP8266."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from app.state_model import PlcStatus


@dataclass(slots=True)
class PlcClientResult:
    ok: bool
    status: PlcStatus | None = None
    message: str = ""
    http_status: int | None = None


class OpenPlcClient:
    def __init__(self, base_url: str = "http://192.168.4.1", timeout_s: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._session = requests.Session()

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def get_status(self) -> PlcClientResult:
        return self._get_json("/status")

    def allow_passage(self) -> PlcClientResult:
        return self._get_json("/hmi/allow")

    def emergency_on(self) -> PlcClientResult:
        return self._get_json("/hmi/emergency_on")

    def reset(self) -> PlcClientResult:
        return self._get_json("/hmi/reset")

    def manual_open(self) -> PlcClientResult:
        return self._get_json("/hmi/manual/open")

    def manual_close(self) -> PlcClientResult:
        return self._get_json("/hmi/manual/close")

    def _get_json(self, path: str) -> PlcClientResult:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, timeout=self.timeout_s)
            if resp.status_code != 200:
                return PlcClientResult(
                    ok=False,
                    message=f"HTTP {resp.status_code}: {url}",
                    http_status=resp.status_code,
                )
            raw: dict[str, Any] = resp.json()
            status = PlcStatus.from_json(raw) if path == "/status" else None
            return PlcClientResult(ok=True, status=status, message=f"OK: {path}", http_status=resp.status_code)
        except requests.Timeout:
            return PlcClientResult(ok=False, message=f"Timeout: {url}")
        except requests.RequestException as exc:
            return PlcClientResult(ok=False, message=f"Request error: {exc}")
        except ValueError:
            return PlcClientResult(ok=False, message=f"Invalid JSON: {url}")
