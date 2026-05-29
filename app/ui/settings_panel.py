"""Settings panel for runtime configurable parameters."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import AppConfig, RUNTIME_HARDWARE_MODE, RUNTIME_SIMULATION_MODE


class SettingsPanel(QWidget):
    apply_settings = Signal(dict)
    refresh_ports = Signal()
    connect_serial = Signal()
    disconnect_serial = Signal()

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.port_combo = QComboBox()
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4", "COM5"])
        self.port_combo.setCurrentText(config.serial.default_port)

        self.runtime_mode_combo = QComboBox()
        self.runtime_mode_combo.addItem("Simulation Mode", RUNTIME_SIMULATION_MODE)
        self.runtime_mode_combo.addItem("Hardware Mode", RUNTIME_HARDWARE_MODE)
        current_mode_idx = self.runtime_mode_combo.findData(config.runtime_mode)
        self.runtime_mode_combo.setCurrentIndex(max(0, current_mode_idx))

        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setRange(1200, 921600)
        self.baudrate_spin.setValue(config.serial.baudrate)

        self.open_timeout = QDoubleSpinBox()
        self.open_timeout.setRange(0.1, 60.0)
        self.open_timeout.setValue(config.timer.open_timeout_s)
        self.open_timeout.setSuffix(" s")

        self.close_timeout = QDoubleSpinBox()
        self.close_timeout.setRange(0.1, 60.0)
        self.close_timeout.setValue(config.timer.close_timeout_s)
        self.close_timeout.setSuffix(" s")

        self.pass_timeout = QDoubleSpinBox()
        self.pass_timeout.setRange(0.1, 60.0)
        self.pass_timeout.setValue(config.timer.pass_timeout_s)
        self.pass_timeout.setSuffix(" s")

        self.gate_settle = QDoubleSpinBox()
        self.gate_settle.setRange(0.1, 10.0)
        self.gate_settle.setValue(config.timer.gate_settle_delay_s)
        self.gate_settle.setSuffix(" s")

        self.normal_speed = QSpinBox()
        self.normal_speed.setRange(0, 255)
        self.normal_speed.setValue(config.simulation.normal_robot_speed_pwm)

        self.slow_speed = QSpinBox()
        self.slow_speed.setRange(0, 255)
        self.slow_speed.setValue(config.simulation.slow_robot_speed_pwm)

        self.stop_distance = QDoubleSpinBox()
        self.stop_distance.setRange(0.1, 200.0)
        self.stop_distance.setValue(config.simulation.stop_distance_cm)
        self.stop_distance.setSuffix(" cm")

        self.slow_distance = QDoubleSpinBox()
        self.slow_distance.setRange(0.1, 200.0)
        self.slow_distance.setValue(config.simulation.slow_distance_cm)
        self.slow_distance.setSuffix(" cm")
        self.auto_approve_demo_check = QCheckBox("Auto approve demo")
        self.auto_approve_demo_check.setChecked(config.simulation.auto_approve_demo)

        self.connection_status = QLabel("Serial: DISCONNECTED")
        self.connection_status.setObjectName("Subtitle")

        form.addRow("Serial Port", self.port_combo)
        form.addRow("Runtime Mode", self.runtime_mode_combo)
        form.addRow("Baudrate", self.baudrate_spin)
        form.addRow("Serial Status", self.connection_status)
        form.addRow("Open Timeout", self.open_timeout)
        form.addRow("Close Timeout", self.close_timeout)
        form.addRow("Pass Timeout", self.pass_timeout)
        form.addRow("Gate Settle Delay", self.gate_settle)
        form.addRow("Normal Robot PWM", self.normal_speed)
        form.addRow("Slow Robot PWM", self.slow_speed)
        form.addRow("Stop Distance", self.stop_distance)
        form.addRow("Slow Distance", self.slow_distance)
        form.addRow("Demo", self.auto_approve_demo_check)
        root.addLayout(form)

        debug_form = QFormLayout()
        self.last_rx_label = QLabel("-")
        self.last_tx_label = QLabel("-")
        self.rx_count_label = QLabel("0")
        self.tx_count_label = QLabel("0")
        self.parse_error_count_label = QLabel("0")
        self.connection_uptime_label = QLabel("0.0 s")
        debug_form.addRow("Last RX JSON", self.last_rx_label)
        debug_form.addRow("Last TX JSON", self.last_tx_label)
        debug_form.addRow("RX Count", self.rx_count_label)
        debug_form.addRow("TX Count", self.tx_count_label)
        debug_form.addRow("Parse Error Count", self.parse_error_count_label)
        debug_form.addRow("Connection Uptime", self.connection_uptime_label)
        root.addLayout(debug_form)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Ports")
        connect_btn = QPushButton("Connect")
        disconnect_btn = QPushButton("Disconnect")
        apply_btn = QPushButton("Apply Settings")
        refresh_btn.clicked.connect(self.refresh_ports.emit)
        connect_btn.clicked.connect(self.connect_serial.emit)
        disconnect_btn.clicked.connect(self.disconnect_serial.emit)
        apply_btn.clicked.connect(self._emit_settings)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(connect_btn)
        btn_row.addWidget(disconnect_btn)
        btn_row.addWidget(apply_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)
        root.addStretch(1)

        self._connect_btn = connect_btn
        self._disconnect_btn = disconnect_btn
        self.runtime_mode_combo.currentIndexChanged.connect(self._update_mode_ui)
        self._update_mode_ui()

    def _emit_settings(self) -> None:
        payload = {
            "port": self.port_combo.currentText(),
            "baudrate": self.baudrate_spin.value(),
            "runtime_mode": self.runtime_mode_combo.currentData(),
            "open_timeout_s": self.open_timeout.value(),
            "close_timeout_s": self.close_timeout.value(),
            "pass_timeout_s": self.pass_timeout.value(),
            "gate_settle_delay_s": self.gate_settle.value(),
            "normal_robot_speed_pwm": self.normal_speed.value(),
            "slow_robot_speed_pwm": self.slow_speed.value(),
            "stop_distance_cm": self.stop_distance.value(),
            "slow_distance_cm": self.slow_distance.value(),
            "auto_approve_demo": self.auto_approve_demo_check.isChecked(),
        }
        self.apply_settings.emit(payload)

    def set_serial_status(self, connected: bool, error: str = "") -> None:
        if connected:
            self.connection_status.setText("Serial: CONNECTED")
            return
        if error:
            self.connection_status.setText(f"Serial: DISCONNECTED ({error})")
            return
        self.connection_status.setText("Serial: DISCONNECTED")

    def _update_mode_ui(self) -> None:
        is_hardware_mode = self.runtime_mode_combo.currentData() == RUNTIME_HARDWARE_MODE
        self._connect_btn.setEnabled(is_hardware_mode)
        self._disconnect_btn.setEnabled(is_hardware_mode)

    def update_serial_debug(
        self,
        *,
        last_rx: str,
        last_tx: str,
        rx_count: int,
        tx_count: int,
        parse_error_count: int,
        uptime_s: float,
    ) -> None:
        self.last_rx_label.setText(last_rx or "-")
        self.last_tx_label.setText(last_tx or "-")
        self.rx_count_label.setText(str(rx_count))
        self.tx_count_label.setText(str(tx_count))
        self.parse_error_count_label.setText(str(parse_error_count))
        self.connection_uptime_label.setText(f"{uptime_s:.1f} s")
