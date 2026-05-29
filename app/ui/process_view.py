"""Animated process view for robot and barrier."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.core.io_model import PlcSnapshot


class ProcessView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(380)
        self.setMaximumHeight(380)
        self.snapshot = PlcSnapshot()

    def update_snapshot(self, snapshot: PlcSnapshot) -> None:
        self.snapshot = snapshot
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        painter.fillRect(rect, QColor("#0e1a2b"))
        if self.snapshot.outputs.alarm:
            painter.setPen(QPen(QColor("#ff5f5f"), 4))
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 10, 10)
            painter.fillRect(10, 8, rect.width() - 20, 28, QColor(80, 20, 24, 210))
            painter.setPen(QColor("#ff98a4"))
            painter.drawText(20, 27, "WARNING: ALARM ACTIVE")

        lane_y = rect.height() * 0.70
        left_x = 20
        gate_zone_x = rect.width() * 0.58
        pass_zone_x = rect.width() * 0.76
        painter.setPen(QPen(QColor("#20324d"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(int(gate_zone_x), int(lane_y - 95), int(gate_zone_x), int(lane_y + 32))
        painter.drawLine(int(pass_zone_x), int(lane_y - 95), int(pass_zone_x), int(lane_y + 32))
        painter.setPen(QColor("#8ea4c8"))
        painter.drawText(int(left_x), int(lane_y - 74), "ROBOT ZONE")
        painter.drawText(int(gate_zone_x + 6), int(lane_y - 74), "BARRIER")
        painter.drawText(int(pass_zone_x + 6), int(lane_y - 74), "PASS ZONE")

        painter.setPen(QPen(QColor("#3f577d"), 3))
        painter.drawLine(20, int(lane_y), rect.width() - 20, int(lane_y))

        barrier_base_x = rect.width() * 0.62
        barrier_base_y = lane_y
        painter.setBrush(QColor("#415a83"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(int(barrier_base_x - 10), int(barrier_base_y - 60), 20, 60)

        angle_deg = self.snapshot.telemetry.barrier_servo_angle
        rad = math.radians(180 - angle_deg)
        arm_len = 120
        end_x = barrier_base_x + arm_len * math.cos(rad)
        end_y = barrier_base_y - arm_len * math.sin(rad)
        painter.setPen(QPen(QColor("#ffd166"), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(barrier_base_x, barrier_base_y - 50), QPointF(end_x, end_y - 50))

        distance = max(0.0, min(50.0, self.snapshot.telemetry.distance_cm))
        robot_x = 40 + ((50.0 - distance) / 50.0) * (barrier_base_x - 110)
        robot_rect = QRectF(robot_x, lane_y - 45, 70, 35)
        if self.snapshot.inputs.robot_at_gate:
            painter.setPen(QPen(QColor("#3ea2ff"), 3))
            painter.setBrush(QColor(62, 162, 255, 40))
            painter.drawRoundedRect(robot_rect.adjusted(-8, -8, 8, 8), 12, 12)
        painter.setPen(QPen(QColor("#7ec8ff"), 2))
        painter.setBrush(QColor("#1f426e"))
        painter.drawRoundedRect(robot_rect, 8, 8)
        painter.setPen(QColor("#dbe9ff"))
        painter.drawText(robot_rect, Qt.AlignmentFlag.AlignCenter, "ROBOT")

        indicator_y = lane_y - 16
        indicator_start_x = 30
        indicator_end_x = barrier_base_x - 20
        painter.setPen(QPen(QColor("#47648f"), 2))
        painter.drawLine(int(indicator_start_x), int(indicator_y), int(indicator_end_x), int(indicator_y))
        marker_x = indicator_start_x + ((50.0 - distance) / 50.0) * (indicator_end_x - indicator_start_x)
        painter.setBrush(QColor("#54d2ff"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(marker_x, indicator_y), 6, 6)
        painter.setPen(QColor("#9ac6f6"))
        painter.drawText(int(indicator_start_x), int(indicator_y - 8), "Distance Indicator")

        lamp_x = rect.width() * 0.80
        lamp_y = 50
        lamp_colors = [
            QColor("#ff3b3b") if self.snapshot.outputs.red_light else QColor("#4f2a2a"),
            QColor("#f4cf37") if self.snapshot.outputs.yellow_light else QColor("#564c1f"),
            QColor("#34d17e") if self.snapshot.outputs.green_light else QColor("#20452f"),
        ]
        for idx, color in enumerate(lamp_colors):
            painter.setBrush(color)
            painter.setPen(QPen(QColor("#20314c"), 2))
            painter.drawEllipse(int(lamp_x), int(lamp_y + idx * 34), 30, 30)

        painter.setPen(QColor("#d8e8ff"))
        state = self.snapshot.telemetry.current_state
        status = "Sistem hazır"
        if state in {"VEHICLE_APPROACHING", "ROBOT_APPROACHING"}:
            status = "Araç kapıya yaklaşıyor"
        elif state in {"GATE_OCCUPIED", "WAITING_PERMISSION"}:
            status = "Kapı önü dolu - Erişim izni isteniyor"
        elif state == "PERMISSION_GRANTED":
            status = "Erişim izni verildi - bariyer açılıyor"
        elif state == "PERMISSION_DENIED":
            status = "İzin reddedildi"
        elif state == "BARRIER_OPENING":
            status = "Bariyer açılıyor"
        elif state in {"BARRIER_OPEN", "PASS_ALLOWED"}:
            status = "Bariyer açık"
        elif state == "VEHICLE_PASSING":
            status = "Bariyer açık - geçiş yapılıyor"
        elif state == "BARRIER_CLOSING":
            status = "Araç geçti - bariyer kapanıyor"
        elif state == "CYCLE_COMPLETE":
            status = "Çevrim tamamlandı - bariyer kapalı"
        elif state == "EMERGENCY_STOP":
            status = "Acil stop aktif"
        elif state == "FAULT":
            status = "Hata durumu"
        painter.drawText(20, 28, status)
