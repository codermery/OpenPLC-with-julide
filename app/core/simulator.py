"""Simulation client and environment behavior."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import SimulationSettings
from app.core.io_model import DigitalInputs, DigitalOutputs, Telemetry


@dataclass(slots=True)
class SimulationFlags:
    auto_run: bool = False
    force_robot_at_gate: bool = False
    force_barrier_open_fb: bool = False
    force_barrier_closed_fb: bool = False
    force_robot_passed: bool = False
    force_fault: bool = False


class Simulator:
    def __init__(self, settings: SimulationSettings) -> None:
        self.settings = settings
        self.flags = SimulationFlags()
        self._pass_elapsed = 0.0

    def reset_cycle(self, telemetry: Telemetry, inputs: DigitalInputs) -> None:
        telemetry.distance_cm = self.settings.distance_start_cm
        telemetry.robot_speed_pwm = 0
        telemetry.robot_slowing_down = False
        telemetry.barrier_servo_angle = 0.0
        inputs.robot_at_gate = False
        inputs.robot_passed = False
        inputs.barrier_open_fb = False
        inputs.barrier_closed_fb = True
        self._pass_elapsed = 0.0

    def reset_to_initial_closed_state(self, telemetry: Telemetry, inputs: DigitalInputs) -> None:
        self.flags.auto_run = False
        self.reset_cycle(telemetry, inputs)

    def step(
        self,
        dt_s: float,
        inputs: DigitalInputs,
        outputs: DigitalOutputs,
        telemetry: Telemetry,
    ) -> None:
        if telemetry.current_state in {"WAITING_PERMISSION", "PERMISSION_DENIED"}:
            telemetry.robot_speed_pwm = 0

        if self.flags.auto_run and telemetry.current_state in {"SYSTEM_READY", "VEHICLE_APPROACHING", "READY", "ROBOT_APPROACHING"}:
            telemetry.distance_cm = max(0.0, telemetry.distance_cm - (12.0 * dt_s))

        telemetry.robot_slowing_down = telemetry.distance_cm <= self.settings.slow_distance_cm
        if telemetry.robot_slowing_down:
            telemetry.robot_speed_pwm = self.settings.slow_robot_speed_pwm
        else:
            telemetry.robot_speed_pwm = self.settings.normal_robot_speed_pwm

        if telemetry.distance_cm <= self.settings.stop_distance_cm:
            inputs.robot_at_gate = True
            telemetry.robot_speed_pwm = 0
        elif not self.flags.force_robot_at_gate:
            inputs.robot_at_gate = False

        if self.flags.force_robot_at_gate:
            inputs.robot_at_gate = True

        if outputs.barrier_open_cmd:
            telemetry.barrier_servo_angle = min(90.0, telemetry.barrier_servo_angle + self.settings.servo_step_deg_per_scan)
        elif outputs.barrier_close_cmd and inputs.robot_passed:
            telemetry.barrier_servo_angle = max(0.0, telemetry.barrier_servo_angle - self.settings.servo_step_deg_per_scan)

        inputs.barrier_open_fb = telemetry.barrier_servo_angle >= 90.0 or self.flags.force_barrier_open_fb
        inputs.barrier_closed_fb = telemetry.barrier_servo_angle <= 0.0 or self.flags.force_barrier_closed_fb

        if outputs.robot_pass_permission:
            self._pass_elapsed += dt_s
            telemetry.robot_speed_pwm = self.settings.slow_robot_speed_pwm
        else:
            self._pass_elapsed = 0.0

        if self._pass_elapsed >= self.settings.pass_duration_s or self.flags.force_robot_passed:
            inputs.robot_passed = True
        elif not self.flags.force_robot_passed:
            inputs.robot_passed = False
