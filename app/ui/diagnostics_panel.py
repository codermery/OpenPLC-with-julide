"""PLC diagnostics panel for internal runtime details."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget

from app.core.io_model import PlcSnapshot


class DiagnosticsPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.state_label = QLabel("-")
        self.scan_label = QLabel("-")
        self.mode_label = QLabel("-")
        self.cycle_label = QLabel("-")
        self.flags_label = QLabel("-")
        self.timer_label = QLabel("-")
        form.addRow("Current internal state", self.state_label)
        form.addRow("PLC scan time", self.scan_label)
        form.addRow("Mode", self.mode_label)
        form.addRow("Cycle counter", self.cycle_label)
        form.addRow("Internal flags", self.flags_label)
        form.addRow("Timer status", self.timer_label)
        root.addLayout(form)
        root.addStretch(1)

    def update_snapshot(self, snapshot: PlcSnapshot, timer_status: str, internal_flags: str) -> None:
        self.state_label.setText(snapshot.telemetry.current_state)
        self.scan_label.setText(f"{snapshot.telemetry.plc_scan_time_ms:.2f} ms")
        self.mode_label.setText(snapshot.telemetry.mode)
        self.cycle_label.setText(str(snapshot.telemetry.cycle_counter))
        self.flags_label.setText(internal_flags)
        self.timer_label.setText(timer_status)
