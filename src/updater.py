#!/usr/bin/env python3
"""
Автообновление XALETHER CRYPT.
Проверяет version.txt на GitHub, скачивает zip с main ветки.
"""

import json
import os
import sys
import zipfile
import tempfile
import shutil
import urllib.request
import urllib.error
from typing import Optional, Tuple

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar

VERSION     = "2.1.0"
REPO        = "mibuchik/xalether-crypt"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO}/main/version.txt"
DOWNLOAD_URL= f"https://github.com/{REPO}/archive/refs/heads/main.zip"
RELEASES_URL= f"https://github.com/{REPO}/releases"

_HEADERS = {"User-Agent": f"XALETHER-CRYPT/{VERSION}"}


def _parse_ver(s: str) -> Tuple[int, ...]:
    try:
        return tuple(int(x) for x in s.strip().lstrip("v").split("."))
    except Exception:
        return (0,)


def is_newer(remote: str) -> bool:
    return _parse_ver(remote) > _parse_ver(VERSION)


# ─── Фоновая проверка ────────────────────────────────────────────────────────

class UpdateChecker(QThread):
    """Тихо проверяет наличие обновления. Запускается при старте приложения."""

    update_available = pyqtSignal(str)   # новая версия (строка)
    up_to_date       = pyqtSignal()
    failed           = pyqtSignal(str)

    def run(self) -> None:
        try:
            req = urllib.request.Request(VERSION_URL, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=6) as resp:
                remote_ver = resp.read().decode().strip()
            if is_newer(remote_ver):
                self.update_available.emit(remote_ver)
            else:
                self.up_to_date.emit()
        except urllib.error.URLError as e:
            self.failed.emit(f"Нет соединения: {e.reason}")
        except Exception as e:
            self.failed.emit(str(e))


# ─── Фоновая загрузка ────────────────────────────────────────────────────────

class UpdateDownloader(QThread):
    """Скачивает архив с GitHub и распаковывает рядом с текущей папкой."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)   # путь к распакованной папке
    error    = pyqtSignal(str)

    def run(self) -> None:
        try:
            self.progress.emit(2)
            req = urllib.request.Request(DOWNLOAD_URL, headers=_HEADERS)

            # Скачиваем во временный файл с отслеживанием прогресса
            tmp = tempfile.mktemp(suffix=".zip")
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                done  = 0
                with open(tmp, "wb") as f:
                    while True:
                        chunk = resp.read(16384)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self.progress.emit(5 + int(done / total * 75))

            self.progress.emit(82)

            # Распаковываем рядом с текущим проектом
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parent       = os.path.dirname(project_root)
            out_dir      = os.path.join(parent, "xalether-crypt-update")

            if os.path.exists(out_dir):
                shutil.rmtree(out_dir)

            with zipfile.ZipFile(tmp, "r") as zf:
                # GitHub zip содержит папку вида "repo-main/"
                top = zf.namelist()[0].split("/")[0]
                zf.extractall(parent)
                extracted = os.path.join(parent, top)
                os.rename(extracted, out_dir)

            os.remove(tmp)
            self.progress.emit(100)
            self.finished.emit(out_dir)

        except Exception as exc:
            self.error.emit(str(exc))


# ─── Диалог обновления ────────────────────────────────────────────────────────

class UpdateDialog(QDialog):
    """Показывает прогресс загрузки и инструкцию по установке."""

    def __init__(self, new_ver: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Обновление XALETHER CRYPT")
        self.setFixedSize(480, 240)
        self.setModal(True)
        self._new_ver = new_ver
        self._downloader: Optional[UpdateDownloader] = None
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        title = QLabel(f"Доступна версия {self._new_ver}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #8A5CF5;")
        lay.addWidget(title)

        self._info = QLabel(
            f"Текущая: v{VERSION}  →  Новая: v{self._new_ver}\n"
            "Приложение скачает архив с GitHub и распакует его рядом\n"
            "с текущей папкой проекта."
        )
        self._info.setStyleSheet("color: #AAA; font-size: 12px;")
        self._info.setWordWrap(True)
        lay.addWidget(self._info)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(14)
        self._bar.setVisible(False)
        lay.addWidget(self._bar)

        btn_row = QHBoxLayout()
        self._dl_btn = QPushButton("⬇ Скачать и установить")
        self._dl_btn.setObjectName("accent")
        self._dl_btn.clicked.connect(self._start_download)
        skip_btn = QPushButton("Позже")
        skip_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._dl_btn)
        btn_row.addWidget(skip_btn)
        lay.addLayout(btn_row)

    def _start_download(self) -> None:
        self._dl_btn.setEnabled(False)
        self._bar.setVisible(True)
        self._info.setText("Загрузка…")

        self._downloader = UpdateDownloader()
        self._downloader.progress.connect(self._bar.setValue)
        self._downloader.finished.connect(self._on_done)
        self._downloader.error.connect(self._on_err)
        self._downloader.start()

    def _on_done(self, path: str) -> None:
        self._info.setText(
            f"✅ Готово!\n\nНовая версия распакована в:\n{path}\n\n"
            "Закройте приложение и запустите новую версию:\n"
            f"python {os.path.join(path, 'src', 'main.py')}"
        )
        self._dl_btn.setText("Закрыть")
        self._dl_btn.setEnabled(True)
        self._dl_btn.clicked.disconnect()
        self._dl_btn.clicked.connect(self.accept)

    def _on_err(self, err: str) -> None:
        self._info.setText(f"❌ Ошибка: {err}")
        self._dl_btn.setText("Повторить")
        self._dl_btn.setEnabled(True)
        self._dl_btn.clicked.disconnect()
        self._dl_btn.clicked.connect(self._start_download)
