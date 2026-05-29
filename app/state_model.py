"""State models for OpenPLC gate controller API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RelayState:
    k1_ready_blue: bool = False
    k2_request_yellow: bool = False
    k3_pass_green: bool = False
    k4_emergency_red: bool = False


@dataclass(slots=True)
class PlcStatus:
    device: str = "openplc_gate_controller"
    state: int = -1
    state_name: str = "DISCONNECTED"
    last_event: str = ""
    last_robot_id: str = "-"
    robot_request: bool = False
    pass_allowed: bool = False
    barrier_open: bool = False
    emergency: bool = False
    servo_angle: int = 0
    relays: RelayState = field(default_factory=RelayState)
    pins: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> "PlcStatus":
        relays_raw = raw.get("relays", {}) if isinstance(raw.get("relays"), dict) else {}
        return cls(
            device=str(raw.get("device", "openplc_gate_controller")),
            state=int(raw.get("state", -1)),
            state_name=str(raw.get("state_name", "UNKNOWN")),
            last_event=str(raw.get("last_event", "")),
            last_robot_id=str(raw.get("last_robot_id", "-")),
            robot_request=bool(raw.get("robot_request", False)),
            pass_allowed=bool(raw.get("pass_allowed", False)),
            barrier_open=bool(raw.get("barrier_open", False)),
            emergency=bool(raw.get("emergency", False)),
            servo_angle=int(raw.get("servo_angle", 0)),
            relays=RelayState(
                k1_ready_blue=bool(relays_raw.get("K1_ready_blue", False)),
                k2_request_yellow=bool(relays_raw.get("K2_request_yellow", False)),
                k3_pass_green=bool(relays_raw.get("K3_pass_green", False)),
                k4_emergency_red=bool(relays_raw.get("K4_emergency_red", False)),
            ),
            pins=raw.get("pins", {}) if isinstance(raw.get("pins"), dict) else {},
        )

    @classmethod
    def disconnected(cls) -> "PlcStatus":
        return cls()
