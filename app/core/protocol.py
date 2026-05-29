"""JSON line protocol helpers for serial communication."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.core.io_model import DigitalOutputs


def encode_plc_output(outputs: DigitalOutputs) -> str:
    msg = {
        "type": "plc_out",
        "barrier_open_cmd": outputs.barrier_open_cmd,
        "barrier_close_cmd": outputs.barrier_close_cmd,
        "robot_pass_permission": outputs.robot_pass_permission,
        "red_light": outputs.red_light,
        "yellow_light": outputs.yellow_light,
        "green_light": outputs.green_light,
        "alarm": outputs.alarm,
    }
    return json.dumps(msg, ensure_ascii=True)


def encode_operator_command(
    *,
    start: bool,
    stop: bool,
    reset: bool,
    emergency_stop: bool,
    manual_open: bool,
    manual_close: bool,
    mode: str,
) -> str:
    msg = {
        "type": "operator_cmd",
        "start": bool(start),
        "stop": bool(stop),
        "reset": bool(reset),
        "emergency_stop": bool(emergency_stop),
        "manual_open": bool(manual_open),
        "manual_close": bool(manual_close),
        "mode": "MANUAL" if str(mode).upper() == "MANUAL" else "AUTO",
    }
    return json.dumps(msg, ensure_ascii=True)


def decode_json_line(raw: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return None
