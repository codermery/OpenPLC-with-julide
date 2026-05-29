"""Fake ESP8266/OpenPLC serial emulator for hardware mode testing."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass

import serial


@dataclass(slots=True)
class FakePlcState:
    state: str = "READY"
    mode: str = "AUTO"
    robot_at_gate: bool = False
    barrier_open_fb: bool = False
    barrier_closed_fb: bool = True
    robot_passed: bool = False
    emergency_stop: bool = False
    barrier_open_cmd: bool = False
    barrier_close_cmd: bool = False
    robot_pass_permission: bool = False
    red_light: bool = True
    yellow_light: bool = False
    green_light: bool = False
    alarm: bool = False
    distance_cm: float = 50.0
    robot_speed_pwm: int = 0
    barrier_servo_angle: int = 0
    plc_scan_time_ms: int = 100
    cycle_counter: int = 0
    uptime_sec: int = 0
    last_transition: float = 0.0
    running: bool = False


def _status_payload(s: FakePlcState) -> dict:
    return {
        "type": "plc_status",
        "state": s.state,
        "mode": s.mode,
        "inputs": {
            "robot_at_gate": s.robot_at_gate,
            "barrier_open_fb": s.barrier_open_fb,
            "barrier_closed_fb": s.barrier_closed_fb,
            "robot_passed": s.robot_passed,
            "emergency_stop": s.emergency_stop,
        },
        "outputs": {
            "barrier_open_cmd": s.barrier_open_cmd,
            "barrier_close_cmd": s.barrier_close_cmd,
            "robot_pass_permission": s.robot_pass_permission,
            "red_light": s.red_light,
            "yellow_light": s.yellow_light,
            "green_light": s.green_light,
            "alarm": s.alarm,
        },
        "telemetry": {
            "distance_cm": s.distance_cm,
            "robot_speed_pwm": s.robot_speed_pwm,
            "barrier_servo_angle": s.barrier_servo_angle,
            "plc_scan_time_ms": s.plc_scan_time_ms,
            "cycle_counter": s.cycle_counter,
            "uptime_sec": s.uptime_sec,
        },
        "alarms": ["Emergency stop active"] if s.emergency_stop else [],
    }


def _safe_outputs(s: FakePlcState) -> None:
    s.barrier_open_cmd = False
    s.barrier_close_cmd = False
    s.robot_pass_permission = False
    s.red_light = True
    s.yellow_light = False
    s.green_light = False
    s.alarm = s.emergency_stop


def _transition_cycle(s: FakePlcState, now: float) -> None:
    if not s.running or s.emergency_stop:
        return
    if (now - s.last_transition) < 1.0:
        return
    s.last_transition = now

    if s.state == "READY":
        s.state = "ROBOT_AT_GATE"
        s.robot_at_gate = True
        s.distance_cm = 4.5
        s.yellow_light = True
    elif s.state == "ROBOT_AT_GATE":
        s.state = "BARRIER_OPENING"
        s.barrier_open_cmd = True
        s.barrier_close_cmd = False
        s.barrier_closed_fb = False
    elif s.state == "BARRIER_OPENING":
        s.state = "BARRIER_OPEN"
        s.barrier_servo_angle = 90
        s.barrier_open_fb = True
        s.barrier_open_cmd = False
    elif s.state == "BARRIER_OPEN":
        s.state = "PASS_ALLOWED"
        s.robot_pass_permission = True
        s.green_light = True
        s.red_light = False
        s.yellow_light = False
    elif s.state == "PASS_ALLOWED":
        s.state = "ROBOT_PASSING"
        s.robot_passed = True
        s.robot_pass_permission = False
        s.yellow_light = True
        s.green_light = False
    elif s.state == "ROBOT_PASSING":
        s.state = "BARRIER_CLOSING"
        s.barrier_close_cmd = True
        s.barrier_open_fb = False
        s.barrier_servo_angle = 30
    elif s.state == "BARRIER_CLOSING":
        s.state = "CYCLE_COMPLETE"
        s.barrier_servo_angle = 0
        s.barrier_close_cmd = False
        s.barrier_closed_fb = True
        s.robot_at_gate = False
    elif s.state == "CYCLE_COMPLETE":
        s.state = "READY"
        s.red_light = True
        s.yellow_light = False
        s.robot_passed = False
        s.distance_cm = 50.0
        s.cycle_counter += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fake ESP/OpenPLC serial endpoint")
    parser.add_argument("--port", required=True, help="Serial port to open (example: COM6)")
    parser.add_argument("--baudrate", type=int, default=115200)
    args = parser.parse_args()

    state = FakePlcState(last_transition=time.perf_counter())
    boot = time.perf_counter()
    ser = serial.Serial(args.port, args.baudrate, timeout=0.05)
    print(f"[fake-esp] listening on {args.port} @ {args.baudrate}")
    print("[fake-esp] Use com0com/VSPE virtual COM pair on Windows (example COM5<->COM6)")
    try:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
            if raw:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    msg = {}
                if msg.get("type") == "operator_cmd":
                    state.mode = "MANUAL" if str(msg.get("mode", "AUTO")).upper() == "MANUAL" else "AUTO"
                    if bool(msg.get("emergency_stop", False)):
                        state.emergency_stop = True
                        state.running = False
                        state.state = "EMERGENCY_STOP"
                        _safe_outputs(state)
                    if bool(msg.get("reset", False)) and not bool(msg.get("emergency_stop", False)):
                        state.emergency_stop = False
                        state.running = False
                        state.state = "READY"
                        state.robot_at_gate = False
                        state.barrier_open_fb = False
                        state.barrier_closed_fb = True
                        state.robot_passed = False
                        state.distance_cm = 50.0
                        state.barrier_servo_angle = 0
                        _safe_outputs(state)
                    if bool(msg.get("start", False)) and not state.emergency_stop:
                        state.running = True
                        if state.state in {"READY", "IDLE"}:
                            state.state = "READY"
                    if bool(msg.get("stop", False)):
                        state.running = False
                        state.state = "READY"
                        _safe_outputs(state)
                    if bool(msg.get("manual_open", False)) and state.mode == "MANUAL" and not state.emergency_stop:
                        state.barrier_open_cmd = True
                        state.barrier_close_cmd = False
                        state.barrier_servo_angle = 90
                        state.barrier_open_fb = True
                        state.barrier_closed_fb = False
                    if bool(msg.get("manual_close", False)) and state.mode == "MANUAL" and not state.emergency_stop:
                        state.barrier_close_cmd = True
                        state.barrier_open_cmd = False
                        state.barrier_servo_angle = 0
                        state.barrier_closed_fb = True
                        state.barrier_open_fb = False

            now = time.perf_counter()
            state.uptime_sec = int(now - boot)
            _transition_cycle(state, now)
            ser.write((json.dumps(_status_payload(state), ensure_ascii=True) + "\n").encode("utf-8"))
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("[fake-esp] stopped")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    raise SystemExit(main())
