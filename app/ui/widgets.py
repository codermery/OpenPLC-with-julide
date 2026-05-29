"""Reusable UI widgets for OpenPLC HMI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StatusCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size: 11pt; font-weight: 700;")
        self.value = QLabel("-")
        self.value.setStyleSheet("font-size: 15pt; font-weight: 700;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)

    def set_value(self, text: str, color: str = "#dbe8ff") -> None:
        self.value.setText(text)
        self.value.setStyleSheet(f"font-size: 15pt; font-weight: 700; color: {color};")


class BarrierWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._angle = 0
        self.setMinimumHeight(140)
        self.setMaximumHeight(160)

    def set_angle(self, angle: int) -> None:
        self._angle = max(0, min(90, int(angle)))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        painter.fillRect(rect, QColor("#0f1b2f"))
        base_x = rect.width() * 0.55
        base_y = rect.height() * 0.80
        painter.setBrush(QColor("#415a83"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(int(base_x - 8), int(base_y - 55), 16, 55)

        # 0 degree = horizontal (closed), 90 degree = vertical (open)
        import math

        rad = math.radians(180 - self._angle)
        arm_len = 110
        end_x = base_x + arm_len * math.cos(rad)
        end_y = base_y - 50 - arm_len * math.sin(rad)
        painter.setPen(QPen(QColor("#ffd166"), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(base_x), int(base_y - 50), int(end_x), int(end_y))
