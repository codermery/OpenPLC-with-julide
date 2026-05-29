"""Application entry point for PLC Barrier HMI."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

# Suppress verbose pymodbus internal logs — errors are shown in the GUI log panel
logging.getLogger("pymodbus").setLevel(logging.CRITICAL)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
