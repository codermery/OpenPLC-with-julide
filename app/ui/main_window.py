"""Main window for OpenPLC Modbus TCP HMI."""

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

from app.modbus_client import (
    COIL_CMD_EMERGENCY,
    COIL_CMD_HMI_ALLOW,
    COIL_CMD_RESET,
    COIL_CMD_ROBOT_PASSED,
    COIL_CMD_ROBOT_REQUEST,
    OpenPLCModbusClient,
)
from app.styles import APP_STYLESHEET
from app.ui.widgets import BarrierWidget, StatusCard

_POLL_INTERVAL_MS = 500
_RECONNECT_TICKS = 10  # attempt reconnect every 10 poll ticks (5 s)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OpenPLC Factory Gate HMI - Jülide Robot Kapı Kontrol")
        self.resize(1300, 860)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(APP_STYLESHEET)

        self.client = OpenPLCModbusClient(host="192.168.137.218", port=502, device_id=0, timeout=3.0)
        self._last_state_name = "DISCONNECTED"
        self._connected = False
        self._reconnect_ticks = 0

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        main.addWidget(self._build_header())
        main.addWidget(self._build_cards())
        main.addWidget(self._build_actions())
        main.addWidget(self._build_debug())
        main.addWidget(self._build_log())

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(_POLL_INTERVAL_MS)
        self.poll_timer.timeout.connect(self._poll_status)
        self.poll_timer.start()
        self._log("INFO", "UI başlatıldı")
        QTimer.singleShot(300, self._do_connect)

    # ------------------------------------------------------------------ #
    # Layout builders                                                      #
    # ------------------------------------------------------------------ #

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)

        title = QLabel("OpenPLC Factory Gate HMI - Jülide Robot Kapı Kontrol")
        title.setObjectName("Title")
        subtitle = QLabel("ESP8266 / OpenPLC / Modbus TCP / PC HMI")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        self.conn_label = QLabel("PLC: Bağlantı Yok")
        self.conn_label.setMinimumWidth(220)
        self.ip_input = QLineEdit("192.168.137.218")
        self.ip_input.setMinimumWidth(190)
        self.port_input = QLineEdit("502")
        self.port_input.setMinimumWidth(60)
        self.refresh_btn = QPushButton("Bağlan / Yenile")
        self.refresh_btn.clicked.connect(self._connect_and_poll)
        self.disconnect_btn = QPushButton("Bağlantıyı Kes")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.last_update_label = QLabel("Son güncelleme: -")
        self.modbus_label = QLabel("Modbus: -")

        row.addWidget(self.conn_label)
        row.addWidget(QLabel("PLC Host:"))
        row.addWidget(self.ip_input)
        row.addWidget(QLabel("Port:"))
        row.addWidget(self.port_input)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.disconnect_btn)
        row.addWidget(self.last_update_label)
        row.addWidget(self.modbus_label)
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
        self.allow_btn.clicked.connect(
            lambda: self._cmd_pulse(COIL_CMD_HMI_ALLOW, 1000, "HMI_ALLOW")
        )
        self.emergency_btn = QPushButton("Acil Stop")
        self.emergency_btn.setObjectName("DangerButton")
        self.emergency_btn.clicked.connect(
            lambda: self._cmd_pulse(COIL_CMD_EMERGENCY, 300, "EMERGENCY")
        )
        self.reset_btn = QPushButton("Reset / Hazır Moda Al")
        self.reset_btn.clicked.connect(
            lambda: self._cmd_pulse(COIL_CMD_RESET, 300, "RESET")
        )

        for btn in [self.allow_btn, self.emergency_btn, self.reset_btn]:
            layout.addWidget(btn)
        layout.addStretch(1)
        return frame

    def _build_debug(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QHBoxLayout(frame)

        lbl = QLabel("Debug / Simülasyon:")
        lbl.setStyleSheet("font-weight: 700; color: #9fb2cb;")
        self.sim_request_btn = QPushButton("Simulate Robot Request")
        self.sim_request_btn.clicked.connect(
            lambda: self._cmd_pulse(COIL_CMD_ROBOT_REQUEST, 300, "ROBOT_REQUEST (sim)")
        )
        self.sim_passed_btn = QPushButton("Simulate Robot Passed")
        self.sim_passed_btn.clicked.connect(
            lambda: self._cmd_pulse(COIL_CMD_ROBOT_PASSED, 300, "ROBOT_PASSED (sim)")
        )

        layout.addWidget(lbl)
        layout.addWidget(self.sim_request_btn)
        layout.addWidget(self.sim_passed_btn)
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

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #

    def _log(self, level: str, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.appendPlainText(f"[{ts}] [{level}] {message}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    # ------------------------------------------------------------------ #
    # Connection management                                                #
    # ------------------------------------------------------------------ #

    def _connect_and_poll(self) -> None:
        host = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            port = 502
        self.client.host = host
        self.client.port = port
        self._do_connect()

    def _do_connect(self) -> None:
        self._log("MODBUS", f"Bağlanılıyor: {self.client.host}:{self.client.port}")
        ok = self.client.connect()
        if ok:
            self._connected = True
            self._reconnect_ticks = 0
            self.conn_label.setText("PLC: Bağlı")
            self.conn_label.setStyleSheet("color: #53d17b; font-weight: 700;")
            self.modbus_label.setText("Modbus: OK")
            self._log("MODBUS", f"Bağlantı kuruldu: {self.client.host}:{self.client.port}")
        else:
            self._connected = False
            self.conn_label.setText("PLC: Bağlantı Yok")
            self.conn_label.setStyleSheet("color: #ff6b7c; font-weight: 700;")
            self.modbus_label.setText("Modbus: HATA")
            self._log("ERROR", f"Bağlantı başarısız: {self.client.host}:{self.client.port}")
        self._set_buttons_enabled(ok)

    def _disconnect(self) -> None:
        self.client.disconnect()
        self._connected = False
        self.conn_label.setText("PLC: Bağlantı Kesildi")
        self.conn_label.setStyleSheet("color: #9aa3b3; font-weight: 700;")
        self.modbus_label.setText("Modbus: -")
        self._log("MODBUS", "Bağlantı kesildi")
        self._set_buttons_enabled(False)

    # ------------------------------------------------------------------ #
    # Status polling                                                       #
    # ------------------------------------------------------------------ #

    def _poll_status(self) -> None:
        if not self.client.is_connected():
            self._reconnect_ticks += 1
            if self._reconnect_ticks >= _RECONNECT_TICKS:
                self._reconnect_ticks = 0
                self._do_connect()
            if self._connected:
                self._connected = False
                self.conn_label.setText("PLC: Bağlantı Yok")
                self.conn_label.setStyleSheet("color: #ff6b7c; font-weight: 700;")
                self.modbus_label.setText("Modbus: HATA")
                self._log("WARN", "PLC bağlantısı koptu")
                self._set_buttons_enabled(False)
                self.system_card.set_value("DISCONNECTED", "#9aa3b3")
                self.big_message.setText("PLC bağlantısı yok")
            return

        status_coils = self.client.read_status()
        output_coils = self.client.read_outputs()

        if not status_coils:
            if self._connected:
                self._connected = False
                self.conn_label.setText("PLC: Hata")
                self.conn_label.setStyleSheet("color: #ff6b7c; font-weight: 700;")
                self.modbus_label.setText("Modbus: HATA")
                self._log("ERROR", "PLC status okunamadı")
                self._set_buttons_enabled(False)
                self.system_card.set_value("ERROR", "#ff6b7c")
                self.big_message.setText("PLC'den status okunamadı")
            return

        self._reconnect_ticks = 0
        if not self._connected:
            self._connected = True
            self.conn_label.setText("PLC: Bağlı")
            self.conn_label.setStyleSheet("color: #53d17b; font-weight: 700;")
            self.modbus_label.setText("Modbus: OK")
            self._log("MODBUS", "PLC bağlantısı yeniden kuruldu")
            self._set_buttons_enabled(True)

        self.last_update_label.setText(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")

        state_name = OpenPLCModbusClient.get_state_name(status_coils)
        if state_name != self._last_state_name:
            self._log("STATE", f"{self._last_state_name} -> {state_name}")
            self._last_state_name = state_name

        self._update_cards(state_name, status_coils, output_coils)
        self._update_button_states(state_name, status_coils.get("STATUS_EMERGENCY", False))

    def _update_cards(
        self,
        state_name: str,
        status_coils: dict[str, bool],
        output_coils: dict[str, bool],
    ) -> None:
        state_color = {
            "READY": "#6fa8ff",
            "REQUEST": "#ffd166",
            "PASS_ALLOWED": "#53d17b",
            "EMERGENCY": "#ff6b7c",
        }.get(state_name, "#9fb2cb")
        self.system_card.set_value(state_name, state_color)

        robot_req = status_coils.get("STATUS_REQUEST", False)
        pass_ok = status_coils.get("STATUS_PASS_ALLOWED", False)

        self.robot_card.set_value(
            f"REQUEST: {'EVET' if robot_req else 'HAYIR'}",
            "#ffd166" if robot_req else "#dbe8ff",
        )
        self.barrier_card.set_value(
            "Açık" if pass_ok else "Kapalı",
            "#53d17b" if pass_ok else "#dbe8ff",
        )

        k1 = output_coils.get("K1_READY", False)
        k2 = output_coils.get("K2_REQUEST", False)
        k3 = output_coils.get("K3_PASS_ALLOWED", False)
        k4 = output_coils.get("K4_EMERGENCY", False)
        self.relay_card.set_value(
            f"K1:{'ON' if k1 else 'OFF'}  K2:{'ON' if k2 else 'OFF'}  K3:{'ON' if k3 else 'OFF'}  K4:{'ON' if k4 else 'OFF'}",
            "#dbe8ff",
        )

        messages = {
            "READY": "Sistem hazır. Kapı kapalı. Robot bekleniyor.",
            "REQUEST": "Jülide kapıda bekliyor. Geçiş izni gerekli.",
            "PASS_ALLOWED": "Geçiş izni verildi. Bariyer açık. Robot geçiyor...",
            "EMERGENCY": "ACİL DURUM / HATA. Geçiş izni kapalı.",
            "UNKNOWN": "PLC'den tutarsız/boş status geldi.",
        }
        self.big_message.setText(messages.get(state_name, messages["UNKNOWN"]))
        self.barrier_widget.set_angle(90 if pass_ok else 0)

    # ------------------------------------------------------------------ #
    # Button state helpers                                                 #
    # ------------------------------------------------------------------ #

    def _set_buttons_enabled(self, connected: bool) -> None:
        for btn in [self.allow_btn, self.reset_btn, self.sim_request_btn, self.sim_passed_btn]:
            btn.setEnabled(connected)
        self.emergency_btn.setEnabled(True)

    def _update_button_states(self, state_name: str, emergency: bool) -> None:
        request_mode = state_name == "REQUEST"
        emergency_mode = state_name == "EMERGENCY" or emergency
        pass_allowed_mode = state_name == "PASS_ALLOWED"

        self.allow_btn.setEnabled(request_mode and not emergency_mode and not pass_allowed_mode)
        self.reset_btn.setEnabled(emergency_mode or pass_allowed_mode or state_name == "REQUEST")
        self.emergency_btn.setEnabled(True)
        self.sim_request_btn.setEnabled(not emergency_mode)
        self.sim_passed_btn.setEnabled(pass_allowed_mode)

    # ------------------------------------------------------------------ #
    # Command dispatch                                                     #
    # ------------------------------------------------------------------ #

    def _cmd_pulse(self, coil: int, duration_ms: int, name: str) -> None:
        """Non-blocking coil pulse: write True, schedule False via QTimer.singleShot."""
        ok = self.client.write_coil(coil, True)
        if ok:
            QTimer.singleShot(duration_ms, lambda: self.client.write_coil(coil, False))
            self._log("CMD", f"{name} komutu gönderildi")
        else:
            self._log("ERROR", f"{name} komutu gönderilemedi — Modbus hatası")
