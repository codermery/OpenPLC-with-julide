"""State and timer primitives for PLC state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlcState(str, Enum):
    IDLE = "IDLE"
    SYSTEM_READY = "SYSTEM_READY"
    VEHICLE_APPROACHING = "VEHICLE_APPROACHING"
    GATE_OCCUPIED = "GATE_OCCUPIED"
    WAITING_PERMISSION = "WAITING_PERMISSION"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    READY = "READY"
    ROBOT_APPROACHING = "ROBOT_APPROACHING"
    ROBOT_AT_GATE = "ROBOT_AT_GATE"
    BARRIER_OPENING = "BARRIER_OPENING"
    BARRIER_OPEN = "BARRIER_OPEN"
    PASS_ALLOWED = "PASS_ALLOWED"
    VEHICLE_PASSING = "VEHICLE_PASSING"
    VEHICLE_PASSED = "VEHICLE_PASSED"
    ROBOT_PASSING = "ROBOT_PASSING"
    BARRIER_CLOSING = "BARRIER_CLOSING"
    CYCLE_COMPLETE = "CYCLE_COMPLETE"
    FAULT = "FAULT"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass(slots=True)
class TonTimer:
    """Simple TON (on-delay) timer."""

    preset_s: float
    elapsed_s: float = 0.0
    done: bool = False

    def update(self, inp: bool, dt_s: float) -> None:
        if inp:
            self.elapsed_s += dt_s
            self.done = self.elapsed_s >= self.preset_s
        else:
            self.elapsed_s = 0.0
            self.done = False

    def reset(self) -> None:
        self.elapsed_s = 0.0
        self.done = False
