"""Ladder logic panel showing static rungs with active highlighting."""

from __future__ import annotations

from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QWidget


RUNG_TEXT = {
    1: "Rung 001 - System Enable\n|--[ START ]--[/ E_STOP ]--[/ FAULT ]----------------( READY )",
    2: "Rung 002 - Barrier Open Command\n|--[ ROBOT_AT_GATE ]--[ READY ]----------------------( BARRIER_OPEN_CMD )",
    3: "Rung 003 - Pass Permission\n|--[ BARRIER_OPEN_FB ]--[ TON T_GATE_SETTLE ]--------( ROBOT_PASS_PERMISSION )",
    4: "Rung 004 - Barrier Close Command\n|--[ ROBOT_PASSED ]----------------------------------( BARRIER_CLOSE_CMD )",
    5: "Rung 005 - Fault Detection\n|--[ OPEN_TIMEOUT ]--+-------------------------------( FAULT )\n|--[ CLOSE_TIMEOUT ]-|\n|--[ PASS_TIMEOUT ]--|",
    6: "Rung 006 - Emergency Stop\n|--[ EMERGENCY_STOP ]--------------------------------( SAFE_SHUTDOWN )",
}


class LadderView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        self.update_active(set())

    def update_active(self, active_rungs: set[int]) -> None:
        lines: list[str] = [
            "<html><body style='font-family:Consolas; font-size:11pt;'>",
        ]
        for idx in range(1, 7):
            if idx in active_rungs and idx == 5:
                bg = "#5a1f28"
                fg = "#ff9aa7"
            elif idx in active_rungs:
                bg = "#153827"
                fg = "#91ffb5"
            else:
                bg = "#0f1a2d"
                fg = "#a8b7cf"
            block = (
                f"<pre style='background:{bg}; color:{fg}; padding:10px; border-radius:8px; border:1px solid #2c4268;'>"
                f"{RUNG_TEXT[idx]}</pre>"
            )
            lines.append(block)
        lines.append("</body></html>")
        self.text.setHtml("".join(lines))
