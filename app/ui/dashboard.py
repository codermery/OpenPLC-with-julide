"""Simplified operator dashboard."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.core.io_model import PlcSnapshot
from app.ui.process_view import ProcessView


class StatusCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-weight: 700; font-size: 11pt;")
        self.value = QLabel("-")
        self.value.setStyleSheet("font-size: 12pt; font-weight: 700; color: #d7e8ff;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        self.setMinimumHeight(88)
        self.setMaximumHeight(88)

    def set_value(self, text: str) -> None:
        self.value.setText(text)


class StepBadge(QLabel):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(32)
        self.setMaximumHeight(32)
        self.setMinimumWidth(150)
        self.setMaximumWidth(150)
        self.setStyleSheet("background:#2a3345;border:1px solid #4e607d;border-radius:8px;color:#9fb2cb;font-weight:700;")

    def set_state(self, level: str) -> None:
        palette = {
            "done": "background:#153b2a;border:1px solid #3ddc97;color:#9fffc0;",
            "active": "background:#1e3659;border:1px solid #66a9ff;color:#d5e9ff;",
            "waiting": "background:#2a3345;border:1px solid #4e607d;color:#9fb2cb;",
            "alarm": "background:#4d1f28;border:1px solid #ff6b7c;color:#ffd5dc;",
        }
        self.setStyleSheet(f"{palette.get(level, palette['waiting'])}border-radius:8px;font-weight:700;")


class DashboardPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.step_labels = [
            StepBadge("1 Kapı Önü"),
            StepBadge("2 İzin Talebi"),
            StepBadge("3 İzin"),
            StepBadge("4 Bariyer Açık"),
            StepBadge("5 Geçiş"),
            StepBadge("6 Bariyer Kapalı"),
        ]
        step_row = QHBoxLayout()
        for step in self.step_labels:
            step_row.addWidget(step)
        step_row.addStretch(1)
        layout.addLayout(step_row)

        self.process_status = QLabel("Sistem beklemede")
        self.process_status.setMinimumHeight(32)
        self.process_status.setStyleSheet("font-size:12pt;font-weight:700;color:#bcd5f5;")
        layout.addWidget(self.process_status)

        self.process_view = ProcessView()
        layout.addWidget(self.process_view)

        cards_grid = QGridLayout()
        self.cards = {
            "system": StatusCard("Sistem Durumu"),
            "gate": StatusCard("Kapı Önü"),
            "permission": StatusCard("Erişim İzni"),
            "barrier": StatusCard("Bariyer Durumu"),
            "pass": StatusCard("Geçiş Durumu"),
            "alarm": StatusCard("Alarm"),
        }
        for idx, key in enumerate(["system", "gate", "permission", "barrier", "pass", "alarm"]):
            cards_grid.addWidget(self.cards[key], idx // 3, idx % 3)
        layout.addLayout(cards_grid)
        layout.addStretch(1)

    def update_snapshot(self, snapshot: PlcSnapshot) -> None:
        self.process_view.update_snapshot(snapshot)
        state = snapshot.telemetry.current_state
        state_to_step = {
            "IDLE": 0,
            "SYSTEM_READY": 0,
            "VEHICLE_APPROACHING": 0,
            "GATE_OCCUPIED": 1,
            "WAITING_PERMISSION": 1,
            "PERMISSION_GRANTED": 2,
            "BARRIER_OPENING": 3,
            "BARRIER_OPEN": 3,
            "PASS_ALLOWED": 4,
            "VEHICLE_PASSING": 4,
            "VEHICLE_PASSED": 4,
            "BARRIER_CLOSING": 5,
            "CYCLE_COMPLETE": 5,
        }
        active_idx = state_to_step.get(state, 0)
        for idx, badge in enumerate(self.step_labels):
            if snapshot.outputs.alarm or state in {"FAULT", "EMERGENCY_STOP"}:
                badge.set_state("alarm" if idx == active_idx else "waiting")
            elif idx < active_idx:
                badge.set_state("done")
            elif idx == active_idx:
                badge.set_state("active")
            else:
                badge.set_state("waiting")

        gate = "Dolu" if snapshot.inputs.robot_at_gate else "Boş"
        permission = "Bekliyor"
        if state == "PERMISSION_GRANTED" or snapshot.outputs.robot_pass_permission:
            permission = "Verildi"
        elif state == "PERMISSION_DENIED":
            permission = "Reddedildi"
        barrier = "Kapalı"
        if state == "BARRIER_OPENING":
            barrier = "Açılıyor"
        elif state in {"BARRIER_OPEN", "PASS_ALLOWED", "VEHICLE_PASSING", "VEHICLE_PASSED"}:
            barrier = "Açık"
        elif state == "BARRIER_CLOSING":
            barrier = "Kapanıyor"
        passing = "Bekliyor"
        if state == "VEHICLE_PASSING":
            passing = "Geçiyor"
        elif state in {"VEHICLE_PASSED", "CYCLE_COMPLETE"}:
            passing = "Geçti"
        system = "Hazır"
        if state in {"VEHICLE_APPROACHING", "ROBOT_APPROACHING", "GATE_OCCUPIED", "WAITING_PERMISSION", "PERMISSION_GRANTED", "BARRIER_OPENING", "BARRIER_OPEN", "PASS_ALLOWED", "VEHICLE_PASSING", "BARRIER_CLOSING"}:
            system = "Çalışıyor"
        if state == "EMERGENCY_STOP":
            system = "Acil Stop"
        elif state == "FAULT":
            system = "Hata"

        self.cards["system"].set_value(system)
        self.cards["gate"].set_value(gate)
        self.cards["permission"].set_value(permission)
        self.cards["barrier"].set_value(barrier)
        self.cards["pass"].set_value(passing)
        self.cards["alarm"].set_value("Var" if snapshot.outputs.alarm else "Yok")

        message = "Sistem hazır"
        if state in {"VEHICLE_APPROACHING", "ROBOT_APPROACHING"}:
            message = "Araç kapıya yaklaşıyor"
        elif state in {"GATE_OCCUPIED", "WAITING_PERMISSION"}:
            message = "Kapı önü dolu - Erişim izni isteniyor"
        elif state == "PERMISSION_GRANTED":
            message = "Erişim izni verildi - bariyer açılıyor"
        elif state == "PERMISSION_DENIED":
            message = "İzin reddedildi"
        elif state == "BARRIER_OPENING":
            message = "Bariyer açılıyor"
        elif state in {"BARRIER_OPEN", "PASS_ALLOWED"}:
            message = "Bariyer açık"
        elif state == "VEHICLE_PASSING":
            message = "Bariyer açık - geçiş yapılıyor"
        elif state == "BARRIER_CLOSING":
            message = "Araç geçti - bariyer kapanıyor"
        elif state == "CYCLE_COMPLETE":
            message = "Çevrim tamamlandı - bariyer kapalı"
        elif state == "EMERGENCY_STOP":
            message = "Acil stop aktif"
        elif state == "FAULT":
            message = "Hata durumu"
        self.process_status.setText(message)
