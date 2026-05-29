"""Alarm panel with acknowledge and reset support."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.event_logger import AlarmEntry


class AlarmPanel(QWidget):
    acknowledge_clicked = Signal()
    reset_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["timestamp", "severity", "message", "acknowledged"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.ack_btn = QPushButton("ACKNOWLEDGE")
        self.reset_btn = QPushButton("RESET FAULT")
        self.reset_btn.setObjectName("DangerButton")
        self.ack_btn.clicked.connect(self.acknowledge_clicked.emit)
        self.reset_btn.clicked.connect(self.reset_clicked.emit)
        actions.addWidget(self.ack_btn)
        actions.addWidget(self.reset_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

    def update_alarms(self, alarms: list[AlarmEntry]) -> None:
        self.table.setRowCount(len(alarms))
        for row, alarm in enumerate(alarms):
            self.table.setItem(row, 0, QTableWidgetItem(alarm.timestamp))
            self.table.setItem(row, 1, QTableWidgetItem(alarm.severity))
            self.table.setItem(row, 2, QTableWidgetItem(alarm.message))
            self.table.setItem(row, 3, QTableWidgetItem(str(alarm.acknowledged)))
