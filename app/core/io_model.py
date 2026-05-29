"""I/O data model for PLC inputs, outputs and telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class DigitalInputs:
    robot_at_gate: bool = False
    barrier_open_fb: bool = False
    barrier_closed_fb: bool = True
    robot_passed: bool = False
    emergency_stop: bool = False
    system_start: bool = False
    system_reset: bool = False


@dataclass(slots=True)
class DigitalOutputs:
    barrier_open_cmd: bool = False
    barrier_close_cmd: bool = False
    robot_pass_permission: bool = False
    red_light: bool = True
    yellow_light: bool = False
    green_light: bool = False
    alarm: bool = False


@dataclass(slots=True)
class Telemetry:
    distance_cm: float = 50.0
    robot_speed_pwm: int = 0
    barrier_servo_angle: float = 0.0
    plc_scan_time_ms: float = 0.0
    uptime_sec: float = 0.0
    current_state: str = "IDLE"
    connection_status: str = "SIMULATION"
    mode: str = "AUTO"
    cycle_counter: int = 0
    robot_slowing_down: bool = False


@dataclass(slots=True)
class PlcSnapshot:
    inputs: DigitalInputs = field(default_factory=DigitalInputs)
    outputs: DigitalOutputs = field(default_factory=DigitalOutputs)
    telemetry: Telemetry = field(default_factory=Telemetry)
