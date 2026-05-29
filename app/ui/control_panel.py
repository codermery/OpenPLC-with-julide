"""Control panel with grouped operator and simulation controls."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(slots=True)
class ControlAction:
    action: str
    value: bool | str | None = None


class ControlPanel(QWidget):
    command_issued = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.setMinimumHeight(220)
        self.setMaximumHeight(260)

        self._buttons: dict[str, QPushButton] = {}

        operator_group = QGroupBox("Operator Controls")
        operator_group.setMinimumHeight(170)
        operator_group.setMaximumHeight(170)
        operator_grid = QGridLayout(operator_group)
        self._build_buttons(
            operator_grid,
            [
                ("SİSTEMİ BAŞLAT", "start"),
                ("ERİŞİM İZNİ VER", "permission_grant"),
                ("ERİŞİMİ REDDET", "permission_deny"),
                ("DEMO ÇEVRİMİ BAŞLAT", "demo_cycle_start"),
                ("RESET", "reset"),
                ("ACİL STOP", "emergency_stop"),
            ],
        )
        layout.addWidget(operator_group)

        self.sim_tools_container = QGroupBox("Simulation Tools")
        self.sim_tools_container.setMinimumHeight(60)
        self.sim_tools_container.setMaximumHeight(60)
        sim_grid = QGridLayout(self.sim_tools_container)
        self._build_buttons(
            sim_grid,
            [
                ("FORCE ROBOT AT GATE", "force_robot_at_gate"),
                ("MANUAL OPEN BARRIER", "manual_open"),
                ("MANUAL CLOSE BARRIER", "manual_close"),
            ],
        )
        layout.addWidget(self.sim_tools_container)
        layout.addStretch(1)

    def _build_buttons(self, grid: QGridLayout, buttons: list[tuple[str, str]]) -> None:
        for idx, (label, action) in enumerate(buttons):
            btn = QPushButton(label)
            if action == "emergency_stop":
                btn.setObjectName("DangerButton")
            btn.clicked.connect(lambda _=False, a=action: self.command_issued.emit(ControlAction(a)))
            grid.addWidget(btn, idx // 2, idx % 2)
            self._buttons[action] = btn

    def set_controls_enabled(self, enabled: bool, keep_actions: set[str] | None = None) -> None:
        allowed = keep_actions or set()
        for action, button in self._buttons.items():
            button.setEnabled(enabled or action in allowed)

    def set_actions_enabled(self, actions: set[str], enabled: bool) -> None:
        for action in actions:
            button = self._buttons.get(action)
            if button is not None:
                button.setEnabled(enabled)

    def set_simulation_tools_enabled(self, enabled: bool) -> None:
        for action in {
            "force_robot_at_gate",
            "manual_open",
            "manual_close",
        }:
            button = self._buttons.get(action)
            if button is None:
                continue
            button.setEnabled(enabled)
            button.setToolTip("" if enabled else "Available only in Simulation Mode")

    def set_estop_active(self, active: bool) -> None:
        estop_btn = self._buttons.get("emergency_stop")
        if estop_btn is not None:
            estop_btn.setText("RELEASE E-STOP" if active else "EMERGENCY STOP")
        if active:
            for action in {"start", "permission_grant", "permission_deny", "demo_cycle_start", "manual_open", "manual_close"}:
                button = self._buttons.get(action)
                if button is not None:
                    button.setEnabled(False)

    def set_hardware_commands_enabled(self, enabled: bool) -> None:
        for action in {"start", "permission_grant", "permission_deny", "demo_cycle_start", "reset", "manual_open", "manual_close", "emergency_stop"}:
            button = self._buttons.get(action)
            if button is not None:
                button.setEnabled(enabled)
