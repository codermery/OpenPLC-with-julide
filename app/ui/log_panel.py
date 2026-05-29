"""Event log panel with CSV export."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.event_logger import LogEntry


class LogPanel(QWidget):
    export_clicked = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["timestamp", "level", "source", "message"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        export_btn = QPushButton("Export Logs")
        export_btn.clicked.connect(self.export_clicked.emit)
        actions.addWidget(export_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

    def update_logs(self, entries: list[LogEntry]) -> None:
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry.timestamp))
            self.table.setItem(row, 1, QTableWidgetItem(entry.level))
            self.table.setItem(row, 2, QTableWidgetItem(entry.source))
            self.table.setItem(row, 3, QTableWidgetItem(entry.message))
        self.table.scrollToBottom()
