"""Configuration values for the PLC barrier HMI application."""

from __future__ import annotations

from dataclasses import dataclass, field

RUNTIME_SIMULATION_MODE = "SIMULATION_MODE"
RUNTIME_HARDWARE_MODE = "HARDWARE_MODE"


@dataclass(slots=True)
class TimerSettings:
    open_timeout_s: float = 5.0
    close_timeout_s: float = 5.0
    pass_timeout_s: float = 8.0
    gate_settle_delay_s: float = 1.0
    cycle_complete_delay_s: float = 2.0


@dataclass(slots=True)
class SimulationSettings:
    distance_start_cm: float = 50.0
    slow_distance_cm: float = 10.0
    stop_distance_cm: float = 5.0
    normal_robot_speed_pwm: int = 140
    slow_robot_speed_pwm: int = 70
    servo_step_deg_per_scan: float = 3.5
    pass_duration_s: float = 2.5
    auto_approve_demo: bool = False


@dataclass(slots=True)
class SerialSettings:
    default_port: str = "COM3"
    baudrate: int = 115200
    enabled: bool = False


@dataclass(slots=True)
class AppConfig:
    scan_interval_ms: int = 100
    default_mode: str = "AUTO"
    runtime_mode: str = RUNTIME_SIMULATION_MODE
    timer: TimerSettings = field(default_factory=TimerSettings)
    simulation: SimulationSettings = field(default_factory=SimulationSettings)
    serial: SerialSettings = field(default_factory=SerialSettings)


DEFAULT_CONFIG = AppConfig()
