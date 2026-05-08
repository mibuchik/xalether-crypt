#!/usr/bin/env python3
"""XALETHER CRYPT v2.0 — точка входа. Запуск: python src/main.py"""

import sys
import os

# Добавляем src/ в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from gui import STYLESHEET, LoginDialog, MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("XALETHER CRYPT")
    app.setApplicationVersion("2.0")

    login = LoginDialog()
    if login.exec_() != LoginDialog.Accepted:
        sys.exit(0)

    window = MainWindow(login.password)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
