"""Qt stylesheet and color utilities for industrial dark theme."""

from __future__ import annotations


APP_STYLESHEET = """
QWidget {
    background-color: #0a1220;
    color: #d7e2f0;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10pt;
}
QMainWindow {
    background-color: #080e18;
}
QFrame#Card, QGroupBox#Card {
    background-color: #111b2e;
    border: 1px solid #1f3154;
    border-radius: 10px;
}
QLabel#Title {
    font-size: 22pt;
    font-weight: 700;
    color: #e6f0ff;
}
QLabel#Subtitle {
    font-size: 10pt;
    color: #8fa6c7;
}
QPushButton {
    background-color: #183055;
    border: 1px solid #2d4f7a;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #20406f;
}
QPushButton:pressed {
    background-color: #162f52;
}
QPushButton#DangerButton {
    background-color: #8a1928;
    border: 1px solid #c3354b;
}
QPushButton#DangerButton:hover {
    background-color: #a32132;
}
QGroupBox {
    border: 1px solid #2b4065;
    border-radius: 8px;
    margin-top: 10px;
    padding: 10px 8px 8px 8px;
    background-color: #0f1a2c;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #9fb8da;
    font-weight: 600;
}
QToolButton {
    background-color: #152843;
    border: 1px solid #2f4c77;
    border-radius: 6px;
    padding: 7px 10px;
    font-weight: 600;
    text-align: left;
}
QToolButton:hover {
    background-color: #1b3456;
}
QPushButton#SidebarButton {
    text-align: left;
    padding: 10px;
    border-radius: 8px;
}
QPushButton#SidebarButton:checked {
    background-color: #2a4a78;
    border: 1px solid #4f7fbf;
}
QTableWidget {
    background-color: #101a2c;
    alternate-background-color: #0d1628;
    border: 1px solid #243b63;
    gridline-color: #243b63;
}
QHeaderView::section {
    background-color: #172845;
    color: #d7e2f0;
    border: 1px solid #243b63;
    padding: 6px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0f1b30;
    border: 1px solid #2e4f7e;
    border-radius: 6px;
    padding: 6px;
}
QPlainTextEdit {
    background-color: #0d1728;
    border: 1px solid #2b4a78;
    border-radius: 6px;
}
QStatusBar {
    background-color: #0d1728;
}
"""


def status_color(active: bool) -> str:
    return "#24c57a" if active else "#7f8ba0"
