"""I/O monitor panel."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class IOPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Address", "Tag Name", "Description", "Value", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def update_data(self, io_map: dict) -> None:
        self.table.setRowCount(len(io_map))
        for row, (address, data) in enumerate(io_map.items()):
            value = bool(data["value"])
            self.table.setItem(row, 0, QTableWidgetItem(address))
            self.table.setItem(row, 1, QTableWidgetItem(str(data["name"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(data["desc"])))
            self.table.setItem(row, 3, QTableWidgetItem("TRUE" if value else "FALSE"))
            self.table.setItem(row, 4, QTableWidgetItem("ACTIVE" if value else "INACTIVE"))
