"""PLC scan cycle engine with state machine and interlocks."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Set

from PySide6.QtCore import QObject, Signal

from app.config import AppConfig
from app.core.event_logger import AlarmManager, EventLogger
from app.core.io_model import DigitalInputs, DigitalOutputs, PlcSnapshot, Telemetry
from app.core.state_machine import PlcState, TonTimer


@dataclass(slots=True)
class OperatorCommand:
    start: bool = False
    stop: bool = False
    reset: bool = False
    emergency_stop: bool = False
    mode: str = "AUTO"
    manual_open: bool = False
    manual_close: bool = False
    force_fault: bool = False
    permission_grant: bool = False
    permission_deny: bool = False
    demo_cycle_start: bool = False


class PlcEngine(QObject):
    snapshot_updated = Signal(object)
    ladder_updated = Signal(object)

    def __init__(self, config: AppConfig, logger: EventLogger, alarm_manager: AlarmManager) -> None:
        super().__init__()
        self.config = config
        self.logger = logger
        self.alarm_manager = alarm_manager
        self.inputs = DigitalInputs()
        self.outputs = DigitalOutputs()
        self.telemetry = Telemetry(mode=config.default_mode)
        self.state = PlcState.IDLE
        self._start_time = time.perf_counter()
        self._active_rungs: Set[int] = set()
        self._operator = OperatorCommand(mode=config.default_mode)
        self._fault_active = False
        self._fault_message = ""
        self._estop_latched = False
        self._permission_granted = False
        self._permission_denied = False

        self.t_open_timeout = TonTimer(config.timer.open_timeout_s)
        self.t_close_timeout = TonTimer(config.timer.close_timeout_s)
        self.t_pass_timeout = TonTimer(config.timer.pass_timeout_s)
        self.t_gate_settle = TonTimer(config.timer.gate_settle_delay_s)
        self.t_cycle_complete = TonTimer(config.timer.cycle_complete_delay_s)

    @property
    def active_rungs(self) -> Set[int]:
        return set(self._active_rungs)

    def get_snapshot(self, sync_from_engine: bool = True) -> PlcSnapshot:
        if sync_from_engine:
            self.telemetry.current_state = self.state.value
            self.telemetry.mode = self._operator.mode
        self.telemetry.uptime_sec = time.perf_counter() - self._start_time
        return PlcSnapshot(self.inputs, self.outputs, self.telemetry)

    def set_mode(self, mode: str) -> None:
        self._operator.mode = mode
        self.logger.add("INFO", "HMI", f"Mode changed to {mode}")

    def apply_operator(self, cmd: OperatorCommand) -> None:
        self._operator = cmd
        self.inputs.system_start = cmd.start
        self.inputs.system_reset = cmd.reset
        self.inputs.emergency_stop = cmd.emergency_stop
        self.telemetry.mode = cmd.mode
        if cmd.permission_grant:
            self._permission_granted = True
            self._permission_denied = False
        if cmd.permission_deny:
            self._permission_denied = True
            self._permission_granted = False

    def reset_to_initial_closed_state(self) -> None:
        self.state = PlcState.IDLE
        self._permission_granted = False
        self._permission_denied = False
        self._fault_active = False
        self._fault_message = ""
        self._estop_latched = False

        self.inputs.robot_at_gate = False
        self.inputs.barrier_open_fb = False
        self.inputs.barrier_closed_fb = True
        self.inputs.robot_passed = False
        self.inputs.emergency_stop = False
        self.inputs.system_start = False
        self.inputs.system_reset = False

        self.outputs.barrier_open_cmd = False
        self.outputs.barrier_close_cmd = False
        self.outputs.robot_pass_permission = False
        self.outputs.red_light = True
        self.outputs.yellow_light = False
        self.outputs.green_light = False
        self.outputs.alarm = False

        self.telemetry.distance_cm = 50.0
        self.telemetry.robot_speed_pwm = 0
        self.telemetry.barrier_servo_angle = 0.0
        self.telemetry.current_state = PlcState.IDLE.value
        self.telemetry.robot_slowing_down = False
        self._reset_timers()

    def inject_fault(self, message: str) -> None:
        self._set_fault(message)

    def _set_fault(self, message: str) -> None:
        self._fault_active = True
        self._fault_message = message
        self.outputs.alarm = True
        self.alarm_manager.raise_alarm("HIGH", message)
        self.logger.add("ERROR", "PLC", message)
        self.state = PlcState.FAULT

    def _clear_fault(self) -> None:
        self._fault_active = False
        self._fault_message = ""
        self.outputs.alarm = False

    def _reset_timers(self) -> None:
        self.t_open_timeout.reset()
        self.t_close_timeout.reset()
        self.t_pass_timeout.reset()
        self.t_gate_settle.reset()
        self.t_cycle_complete.reset()

    def _set_safe_outputs(self) -> None:
        self.outputs.barrier_open_cmd = False
        self.outputs.barrier_close_cmd = False
        self.outputs.robot_pass_permission = False
        self.outputs.red_light = True
        self.outputs.yellow_light = False
        self.outputs.green_light = False

    def _apply_interlocks(self) -> None:
        if self.outputs.barrier_open_cmd and self.outputs.barrier_close_cmd:
            self.outputs.barrier_close_cmd = False
            self._set_fault("Interlock violation: open and close commands active together")

        if (not self._permission_granted) and self.state not in {PlcState.BARRIER_OPENING, PlcState.BARRIER_OPEN, PlcState.PASS_ALLOWED, PlcState.VEHICLE_PASSING, PlcState.VEHICLE_PASSED, PlcState.BARRIER_CLOSING}:
            self.outputs.barrier_open_cmd = False

        pass_allowed_guard = (
            self.inputs.barrier_open_fb
            and not self._fault_active
            and not self.inputs.emergency_stop
            and self._operator.mode in {"AUTO", "MANUAL", "SIMULATION"}
        )
        if not pass_allowed_guard:
            self.outputs.robot_pass_permission = False

        if not self.inputs.robot_passed:
            self.outputs.barrier_close_cmd = False

        if self.inputs.emergency_stop:
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.alarm = True

    def _update_rungs(self) -> None:
        rungs: Set[int] = set()
        if self.inputs.system_start and (not self.inputs.emergency_stop) and (not self._fault_active):
            rungs.add(1)
        if self.inputs.robot_at_gate and self.state in {PlcState.SYSTEM_READY, PlcState.VEHICLE_APPROACHING, PlcState.GATE_OCCUPIED}:
            rungs.add(2)
        if self.inputs.barrier_open_fb and self.t_gate_settle.done:
            rungs.add(3)
        if self.inputs.robot_passed:
            rungs.add(4)
        if self.t_open_timeout.done or self.t_close_timeout.done or self.t_pass_timeout.done:
            rungs.add(5)
        if self.inputs.emergency_stop:
            rungs.add(6)
        self._active_rungs = rungs

    def run_scan(self, dt_s: float) -> PlcSnapshot:
        scan_start = time.perf_counter()
        self._transition(dt_s)
        self._apply_interlocks()
        self._update_rungs()
        snapshot = self.get_snapshot()
        scan_elapsed = (time.perf_counter() - scan_start) * 1000.0
        self.telemetry.plc_scan_time_ms = round(scan_elapsed, 3)
        self.snapshot_updated.emit(snapshot)
        self.ladder_updated.emit(self.active_rungs)
        return snapshot

    def _transition(self, dt_s: float) -> None:
        if self._operator.force_fault:
            self._set_fault("Operator forced fault")

        if self.inputs.emergency_stop:
            if self.state != PlcState.EMERGENCY_STOP:
                self.logger.add("WARN", "PLC", "Emergency stop pressed")
                self.alarm_manager.raise_alarm("CRITICAL", "Emergency stop active")
            self._estop_latched = True
            self._fault_active = True
            self._fault_message = "Emergency stop latched"
            self.state = PlcState.EMERGENCY_STOP

        if self.state == PlcState.IDLE:
            self.outputs.red_light = True
            self.outputs.yellow_light = False
            self.outputs.green_light = False
            self.outputs.barrier_close_cmd = False
            self.outputs.barrier_open_cmd = False
            self.outputs.robot_pass_permission = False
            if self.inputs.system_start and not self.inputs.emergency_stop:
                self.logger.add("INFO", "PLC", "System started")
                self.state = PlcState.SYSTEM_READY
                self.outputs.barrier_close_cmd = False

        elif self.state in {PlcState.SYSTEM_READY, PlcState.READY}:
            self.outputs.red_light = True
            self.outputs.yellow_light = False
            self.outputs.green_light = False
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            if self.telemetry.mode in {"AUTO", "SIMULATION"}:
                self.state = PlcState.VEHICLE_APPROACHING
            if self.inputs.robot_at_gate:
                self.logger.add("INFO", "PLC", "Gate occupied, waiting permission")
                self.state = PlcState.GATE_OCCUPIED

        elif self.state in {PlcState.VEHICLE_APPROACHING, PlcState.ROBOT_APPROACHING}:
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.yellow_light = True
            if self.inputs.robot_at_gate:
                self.logger.add("INFO", "PLC", "Robot reached gate position")
                self.state = PlcState.GATE_OCCUPIED

        elif self.state in {PlcState.GATE_OCCUPIED, PlcState.WAITING_PERMISSION}:
            self.outputs.red_light = True
            self.outputs.yellow_light = True
            self.outputs.green_light = False
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.state = PlcState.WAITING_PERMISSION
            if self._permission_denied:
                self.logger.add("WARN", "PLC", "Permission denied")
                self.state = PlcState.PERMISSION_DENIED
            elif self._permission_granted:
                self.logger.add("INFO", "PLC", "Permission granted")
                self.state = PlcState.PERMISSION_GRANTED

        elif self.state == PlcState.PERMISSION_DENIED:
            self.outputs.red_light = True
            self.outputs.yellow_light = False
            self.outputs.green_light = False
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            if self.inputs.system_reset:
                self._permission_denied = False
                self.state = PlcState.SYSTEM_READY

        elif self.state in {PlcState.PERMISSION_GRANTED, PlcState.ROBOT_AT_GATE}:
            self.outputs.barrier_open_cmd = True
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.red_light = False
            self.outputs.yellow_light = True
            self.outputs.green_light = False
            self.logger.add("INFO", "PLC", "Barrier opening command activated")
            self.state = PlcState.BARRIER_OPENING

        elif self.state == PlcState.BARRIER_OPENING:
            self.outputs.barrier_open_cmd = True
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.red_light = False
            self.outputs.yellow_light = True
            self.outputs.green_light = False
            self.t_open_timeout.update(True, dt_s)
            if self.inputs.barrier_open_fb:
                self.t_open_timeout.reset()
                self.outputs.barrier_open_cmd = False
                self.logger.add("INFO", "PLC", "Barrier open feedback received")
                self.state = PlcState.BARRIER_OPEN
            elif self.t_open_timeout.done:
                self._set_fault("Barrier open timeout")

        elif self.state == PlcState.BARRIER_OPEN:
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.red_light = False
            self.outputs.yellow_light = False
            self.outputs.green_light = True
            self.t_gate_settle.update(True, dt_s)
            if self.t_gate_settle.done:
                self.state = PlcState.PASS_ALLOWED
                self.logger.add("INFO", "PLC", "Pass permission granted")

        elif self.state == PlcState.PASS_ALLOWED:
            self.outputs.robot_pass_permission = True
            self.outputs.green_light = True
            self.outputs.red_light = False
            self.outputs.yellow_light = False
            self.t_pass_timeout.update(True, dt_s)
            if self.inputs.robot_passed:
                self.t_pass_timeout.reset()
                self.state = PlcState.VEHICLE_PASSING
                self.logger.add("INFO", "PLC", "Robot passed barrier")
            elif self.t_pass_timeout.done:
                self._set_fault("Robot pass timeout")

        elif self.state in {PlcState.ROBOT_PASSING, PlcState.VEHICLE_PASSING}:
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = True
            self.outputs.green_light = True
            self.outputs.red_light = False
            self.outputs.yellow_light = False
            if self.inputs.robot_passed:
                self.outputs.robot_pass_permission = False
                self.state = PlcState.VEHICLE_PASSED
                self.logger.add("INFO", "PLC", "Barrier closing command activated")

        elif self.state == PlcState.VEHICLE_PASSED:
            self.outputs.barrier_open_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.green_light = False
            self.outputs.red_light = False
            self.outputs.yellow_light = True
            self.state = PlcState.BARRIER_CLOSING

        elif self.state == PlcState.BARRIER_CLOSING:
            if not self.inputs.robot_passed:
                self.outputs.barrier_open_cmd = False
                self.outputs.barrier_close_cmd = False
                self.outputs.robot_pass_permission = False
                return
            self.outputs.barrier_close_cmd = True
            self.outputs.barrier_open_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.red_light = False
            self.outputs.yellow_light = True
            self.outputs.green_light = False
            self.t_close_timeout.update(True, dt_s)
            if self.inputs.barrier_closed_fb:
                self.outputs.barrier_close_cmd = False
                self.t_close_timeout.reset()
                self.state = PlcState.CYCLE_COMPLETE
            elif self.t_close_timeout.done:
                self._set_fault("Barrier close timeout")

        elif self.state == PlcState.CYCLE_COMPLETE:
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.yellow_light = False
            self.outputs.red_light = True
            self.outputs.green_light = False
            self.telemetry.cycle_counter += 1
            self.t_cycle_complete.update(True, dt_s)
            if self.t_cycle_complete.done:
                self.logger.add("INFO", "PLC", "Cycle completed")
                self.t_cycle_complete.reset()
                self._permission_granted = False
                self._permission_denied = False
                self.state = PlcState.SYSTEM_READY

        elif self.state == PlcState.FAULT:
            self.outputs.alarm = True
            self.outputs.red_light = True
            self.outputs.yellow_light = False
            self.outputs.green_light = False
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            safe_state = (not self.inputs.robot_at_gate) and self.inputs.barrier_closed_fb
            if self.inputs.system_reset and (not self.inputs.emergency_stop) and safe_state:
                self.logger.add("INFO", "PLC", "Fault reset by operator")
                self.alarm_manager.raise_alarm("LOW", "Fault reset by operator")
                self._clear_fault()
                self._reset_timers()
                self._set_safe_outputs()
                self.state = PlcState.IDLE

        elif self.state == PlcState.EMERGENCY_STOP:
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.outputs.alarm = True
            self.outputs.red_light = True
            self.outputs.yellow_light = False
            self.outputs.green_light = False
            if not self.inputs.emergency_stop and self._estop_latched and (not self.inputs.system_reset):
                self.state = PlcState.FAULT
                self.logger.add("WARN", "PLC", "E-Stop released, reset required")
                self.alarm_manager.raise_alarm("HIGH", "E-Stop released. Reset required")
            elif self.inputs.system_reset and (not self.inputs.emergency_stop):
                self.logger.add("INFO", "PLC", "Emergency stop reset by operator")
                self.alarm_manager.raise_alarm("LOW", "Fault reset by operator")
                self._clear_fault()
                self._set_safe_outputs()
                self.state = PlcState.IDLE
                self._estop_latched = False

        if self._operator.stop:
            self.state = PlcState.IDLE
            self.outputs.barrier_open_cmd = False
            self.outputs.barrier_close_cmd = False
            self.outputs.robot_pass_permission = False
            self.logger.add("WARN", "PLC", "System stopped by operator")

    def io_map(self) -> Dict[str, Dict[str, object]]:
        return {
            "%IX0.0": {"name": "ROBOT_AT_GATE", "value": self.inputs.robot_at_gate, "desc": "Robot kapida"},
            "%IX0.1": {"name": "BARRIER_OPEN_FB", "value": self.inputs.barrier_open_fb, "desc": "Bariyer acik feedback"},
            "%IX0.2": {"name": "BARRIER_CLOSED_FB", "value": self.inputs.barrier_closed_fb, "desc": "Bariyer kapali feedback"},
            "%IX0.3": {"name": "ROBOT_PASSED", "value": self.inputs.robot_passed, "desc": "Robot gecis tamam"},
            "%IX0.4": {"name": "EMERGENCY_STOP", "value": self.inputs.emergency_stop, "desc": "Acil stop"},
            "%IX0.5": {"name": "SYSTEM_START", "value": self.inputs.system_start, "desc": "Sistem baslat"},
            "%IX0.6": {"name": "SYSTEM_RESET", "value": self.inputs.system_reset, "desc": "Sistem reset"},
            "%QX0.0": {"name": "BARRIER_OPEN_CMD", "value": self.outputs.barrier_open_cmd, "desc": "Bariyer ac komutu"},
            "%QX0.1": {"name": "BARRIER_CLOSE_CMD", "value": self.outputs.barrier_close_cmd, "desc": "Bariyer kapat komutu"},
            "%QX0.2": {"name": "ROBOT_PASS_PERMISSION", "value": self.outputs.robot_pass_permission, "desc": "Gecis izni"},
            "%QX0.3": {"name": "RED_LIGHT", "value": self.outputs.red_light, "desc": "Kirmizi lamba"},
            "%QX0.4": {"name": "YELLOW_LIGHT", "value": self.outputs.yellow_light, "desc": "Sari lamba"},
            "%QX0.5": {"name": "GREEN_LIGHT", "value": self.outputs.green_light, "desc": "Yesil lamba"},
            "%QX0.6": {"name": "ALARM", "value": self.outputs.alarm, "desc": "Alarm cikisi"},
        }
