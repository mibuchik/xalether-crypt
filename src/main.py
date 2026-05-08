#!/usr/bin/env python3
"""XALETHER CRYPT v2.2 — точка входа. Запуск: python src/main.py"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from gui import STYLESHEET, LoginDialog, MainWindow


def main() -> None:
    # CLI-аргументы для запуска из контекстного меню Проводника
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--encrypt", metavar="FILE", default=None,
                        help="Зашифровать указанный файл/папку")
    parser.add_argument("--decrypt", metavar="FILE", default=None,
                        help="Расшифровать указанный .xalether файл")
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setApplicationName("XALETHER CRYPT")
    app.setApplicationVersion("2.2")

    login = LoginDialog()
    if login.exec_() != LoginDialog.Accepted:
        sys.exit(0)

    window = MainWindow(login.password)
    window.show()

    # Автозапуск операции из контекстного меню
    if args.encrypt:
        path = args.encrypt
        op   = "encrypt_folder" if os.path.isdir(path) else "encrypt_file"
        QTimer.singleShot(400, lambda: window._run_operation(op, path))

    elif args.decrypt:
        path = args.decrypt
        try:
            from crypto import read_metadata
            meta = read_metadata(path)
            op   = "decrypt_folder" if meta.get("content_type") == "folder" else "decrypt_file"
        except Exception:
            op = "decrypt_file"
        QTimer.singleShot(400, lambda: window._run_operation(op, path))

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
