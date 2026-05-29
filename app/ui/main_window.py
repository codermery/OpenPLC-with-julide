"""Main window for OpenPLC HTTP-based HMI."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.plc_client import OpenPlcClient, PlcClientResult
from app.state_model import PlcStatus
from app.styles import APP_STYLESHEET
from app.ui.widgets import BarrierWidget, StatusCard


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OpenPLC Factory Gate HMI - Jülide Robot Kapı Kontrol")
        self.resize(1300, 860)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(APP_STYLESHEET)

        self.client = OpenPlcClient("http://192.168.4.1", timeout_s=1.0)
        self._last_state_name = "DISCONNECTED"
        self._connected = False
        self._last_status = PlcStatus.disconnected()

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        main.addWidget(self._build_header())
        main.addWidget(self._build_cards())
        main.addWidget(self._build_actions())
        main.addWidget(self._build_log())

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self._poll_status)
        self.poll_timer.start()
        self._log("INFO", "UI started")

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)

        title = QLabel("OpenPLC Factory Gate HMI - Jülide Robot Kapı Kontrol")
        title.setObjectName("Title")
        subtitle = QLabel("ESP8266 / OpenPLC / PC HMI")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        self.conn_label = QLabel("PLC: Disconnected")
        self.conn_label.setMinimumWidth(220)
        self.ip_input = QLineEdit("http://192.168.4.1")
        self.ip_input.setMinimumWidth(260)
        self.refresh_btn = QPushButton("Bağlan / Yenile")
        self.refresh_btn.clicked.connect(self._connect_and_poll)
        self.last_update_label = QLabel("Son güncelleme: -")
        self.http_label = QLabel("HTTP: -")
        row.addWidget(self.conn_label)
        row.addWidget(QLabel("PLC IP:"))
        row.addWidget(self.ip_input)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.last_update_label)
        row.addWidget(self.http_label)
        row.addStretch(1)
        layout.addLayout(row)
        return frame

    def _build_cards(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QGridLayout(frame)

        self.system_card = StatusCard("Sistem Durumu")
        self.robot_card = StatusCard("Robot Durumu")
        self.barrier_card = StatusCard("Bariyer Durumu")
        self.relay_card = StatusCard("Röle Durumları")
        self.big_message = QLabel("Sistem hazır. Kapı kapalı. Robot bekleniyor.")
        self.big_message.setStyleSheet("font-size: 13pt; font-weight: 700; color: #d8e8ff;")
        self.barrier_widget = BarrierWidget()

        layout.addWidget(self.system_card, 0, 0)
        layout.addWidget(self.robot_card, 0, 1)
        layout.addWidget(self.barrier_card, 1, 0)
        layout.addWidget(self.relay_card, 1, 1)
        layout.addWidget(self.big_message, 2, 0, 1, 2)
        layout.addWidget(self.barrier_widget, 3, 0, 1, 2)
        return frame

    def _build_actions(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QHBoxLayout(frame)

        self.allow_btn = QPushButton("Geçiş İzni Ver")
        self.allow_btn.clicked.connect(lambda: self._send_command("allow"))
        self.emergency_btn = QPushButton("Acil Stop")
        self.emergency_btn.setObjectName("DangerButton")
        self.emergency_btn.clicked.connect(lambda: self._send_command("emergency_on"))
        self.reset_btn = QPushButton("Reset / Hazır Moda Al")
        self.reset_btn.clicked.connect(lambda: self._send_command("reset"))
        self.manual_open_btn = QPushButton("Manuel Aç")
        self.manual_open_btn.clicked.connect(lambda: self._send_command("manual_open"))
        self.manual_close_btn = QPushButton("Manuel Kapat")
        self.manual_close_btn.clicked.connect(lambda: self._send_command("manual_close"))

        for btn in [self.allow_btn, self.emergency_btn, self.reset_btn, self.manual_open_btn, self.manual_close_btn]:
            layout.addWidget(btn)
        layout.addStretch(1)
        return frame

    def _build_log(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        label = QLabel("Olay Günlüğü")
        label.setStyleSheet("font-weight: 700; font-size: 11pt;")
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(170)
        self.log_box.setMaximumHeight(220)
        layout.addWidget(label)
        layout.addWidget(self.log_box)
        return frame

    def _log(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{ts}] {level}: {message}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _connect_and_poll(self) -> None:
        self.client.set_base_url(self.ip_input.text().strip())
        self._poll_status()

    def _poll_status(self) -> None:
        result = self.client.get_status()
        self._apply_status_result(result)

    def _apply_status_result(self, result: PlcClientResult) -> None:
        if not result.ok or result.status is None:
            if self._connected:
                self._log("WARN", "PLC bağlantısı koptu")
            self._connected = False
            self.conn_label.setText("PLC: Disconnected")
            self.http_label.setText("HTTP: ERROR")
            self.last_update_label.setText("Son güncelleme: -")
            self._set_buttons_enabled(False)
            self.system_card.set_value("DISCONNECTED", "#9aa3b3")
            self.big_message.setText("PLC bağlantısı yok")
            return

        status = result.status
        if not self._connected:
            self._log("INFO", "PLC bağlantısı kuruldu")
        self._connected = True
        self._last_status = status
        self.conn_label.setText("PLC: Connected")
        self.http_label.setText("HTTP: OK")
        self.last_update_label.setText(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")

        if status.state_name != self._last_state_name:
            self._log("INFO", f"State changed: {self._last_state_name} -> {status.state_name}")
            self._last_state_name = status.state_name
        if status.last_robot_id and status.last_robot_id != "-":
            self._log("INFO", f"robot id: {status.last_robot_id}")

        state_color = {
            "READY": "#6fa8ff",
            "REQUEST": "#ffd166",
            "PASS_ALLOWED": "#53d17b",
            "EMERGENCY": "#ff6b7c",
        }.get(status.state_name, "#9fb2cb")
        self.system_card.set_value(status.state_name, state_color)
        self.robot_card.set_value(
            f"id={status.last_robot_id} | request={status.robot_request}",
            "#ffd166" if status.robot_request else "#dbe8ff",
        )
        self.barrier_card.set_value(
            f"{'Açık' if status.barrier_open else 'Kapalı'} | {status.servo_angle}°",
            "#53d17b" if status.barrier_open else "#dbe8ff",
        )
        self.relay_card.set_value(
            (
                f"K1:{'ON' if status.relays.k1_ready_blue else 'OFF'} "
                f"K2:{'ON' if status.relays.k2_request_yellow else 'OFF'} "
                f"K3:{'ON' if status.relays.k3_pass_green else 'OFF'} "
                f"K4:{'ON' if status.relays.k4_emergency_red else 'OFF'}"
            ),
            "#dbe8ff",
        )
        self.barrier_widget.set_angle(status.servo_angle)

        msg = "Sistem hazır. Kapı kapalı. Robot bekleniyor."
        if status.state_name == "REQUEST":
            msg = "Jülide kapıda bekliyor. Geçiş izni gerekli."
        elif status.state_name == "PASS_ALLOWED":
            msg = "Geçiş izni verildi. Bariyer açık. Robot geçiyor..."
        elif status.state_name == "EMERGENCY":
            msg = "ACİL DURUM / HATA. Geçiş izni kapalı."
        self.big_message.setText(msg)
        self._set_buttons_enabled(True)

    def _set_buttons_enabled(self, connected: bool) -> None:
        if not connected:
            self.allow_btn.setEnabled(False)
            self.reset_btn.setEnabled(False)
            self.manual_open_btn.setEnabled(False)
            self.manual_close_btn.setEnabled(False)
            self.emergency_btn.setEnabled(True)
            return
        status = self._last_status
        request_mode = status.state_name == "REQUEST"
        emergency_mode = status.state_name == "EMERGENCY" or status.emergency
        pass_allowed_mode = status.state_name == "PASS_ALLOWED"
        self.allow_btn.setEnabled(request_mode and not emergency_mode and not pass_allowed_mode)
        self.manual_open_btn.setEnabled(not emergency_mode)
        self.manual_close_btn.setEnabled(True)
        self.reset_btn.setEnabled(emergency_mode or pass_allowed_mode or status.state_name == "REQUEST")
        self.emergency_btn.setEnabled(True)

    def _send_command(self, command: str) -> None:
        actions = {
            "allow": self.client.allow_passage,
            "emergency_on": self.client.emergency_on,
            "reset": self.client.reset,
            "manual_open": self.client.manual_open,
            "manual_close": self.client.manual_close,
        }
        fn = actions.get(command)
        if fn is None:
            return
        result = fn()
        if result.ok:
            self._log("INFO", f"Command sent: {command}")
        else:
            self._log("ERROR", result.message or f"Command failed: {command}")
        self._poll_status()
