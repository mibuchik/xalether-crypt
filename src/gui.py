#!/usr/bin/env python3
"""
XALETHER CRYPT v2.0 — PyQt5 GUI.
Тёмная тема: фон #1A1A1A, акцент #8A5CF5.
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QRadioButton, QButtonGroup, QTabWidget, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox, QFrame,
    QSpinBox, QSizePolicy, QStatusBar,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent, QIcon

from crypto import XaletherChaos, save_password_hash, verify_password, is_first_run, read_metadata
from permissions import generate_permission_code, create_permission, get_active_permissions
from utils import (
    folder_to_zip, zip_to_folder,
    save_history_entry, load_history,
    load_settings, save_settings, generate_password,
)


# ─── Таблица стилей ───────────────────────────────────────────────────────────

STYLESHEET = """
QWidget {
    background-color: #1A1A1A;
    color: #E3E3E3;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: #1A1A1A; }
QLabel { color: #E3E3E3; background: transparent; }

QPushButton {
    background-color: #2D2D2D;
    color: #E3E3E3;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
}
QPushButton:hover  { background-color: #8A5CF5; border-color: #8A5CF5; color: #FFF; }
QPushButton:pressed { background-color: #7040E0; }
QPushButton:disabled { color: #555; border-color: #2D2D2D; }

QPushButton#accent {
    background-color: #8A5CF5; color: #FFF; border: none; font-weight: bold;
}
QPushButton#accent:hover  { background-color: #9D70F5; }
QPushButton#accent:pressed { background-color: #7040E0; }

QLineEdit {
    background-color: #242424;
    color: #E3E3E3;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: #8A5CF5;
}
QLineEdit:focus { border-color: #8A5CF5; }

QTextEdit {
    background-color: #111;
    color: #D0D0D0;
    border: 1px solid #333;
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    selection-background-color: #8A5CF5;
}

QTabWidget::pane { border: 1px solid #333; background: #1A1A1A; }
QTabBar::tab {
    background: #242424; color: #888;
    border: 1px solid #333; border-bottom: none;
    padding: 8px 20px; margin-right: 2px;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #1A1A1A; color: #8A5CF5; border-bottom: 2px solid #8A5CF5; }
QTabBar::tab:hover { color: #E3E3E3; }

QCheckBox, QRadioButton { color: #E3E3E3; spacing: 8px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 1px solid #555; border-radius: 3px; background: #242424;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #8A5CF5; border-color: #8A5CF5;
    image: none;
}
QRadioButton::indicator { border-radius: 8px; }

QProgressBar {
    background: #242424; border: 1px solid #333; border-radius: 4px;
    text-align: center; color: #E3E3E3; font-size: 11px; min-height: 18px;
}
QProgressBar::chunk { background: #8A5CF5; border-radius: 3px; }

QGroupBox {
    color: #8A5CF5; border: 1px solid #333; border-radius: 6px;
    margin-top: 12px; padding-top: 10px; font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 4px; background: #1A1A1A;
}

QSpinBox {
    background: #242424; color: #E3E3E3; border: 1px solid #444; border-radius: 4px; padding: 4px 8px;
}
QSpinBox::up-button, QSpinBox::down-button { background: #333; width: 16px; border: none; }

QScrollBar:vertical { background: #1A1A1A; width: 8px; border: none; }
QScrollBar::handle:vertical { background: #444; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #8A5CF5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QStatusBar { background: #111; color: #666; font-size: 11px; }
QStatusBar::item { border: none; }
"""


# ─── Виджет Drag-and-Drop ─────────────────────────────────────────────────────

class DropZone(QFrame):
    """Зона перетаскивания файлов и папок."""

    files_dropped = pyqtSignal(list)

    _STYLE_IDLE = """
        QFrame { border: 2px dashed #444; border-radius: 10px; background: #202020; }
        QLabel { color: #666; }
    """
    _STYLE_HOVER = """
        QFrame { border: 2px dashed #8A5CF5; border-radius: 10px; background: #1E1530; }
        QLabel { color: #8A5CF5; }
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(self._STYLE_IDLE)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(20, 15, 20, 15)

        self._icon = QLabel("⬇", self)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setStyleSheet("font-size: 28px; color: #555; background: transparent;")

        self._text = QLabel("Перетащите файл или папку сюда\nили нажмите для выбора", self)
        self._text.setAlignment(Qt.AlignCenter)
        self._text.setStyleSheet("color: #555; font-size: 12px; background: transparent;")

        layout.addWidget(self._icon)
        layout.addWidget(self._text)

    # ── событие одиночного клика: открываем диалог ──────────────────────────
    def mousePressEvent(self, _event) -> None:
        paths = QFileDialog.getOpenFileNames(self, "Выберите файл")[0]
        if paths:
            self.files_dropped.emit(paths)

    # ── drag-and-drop ────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._STYLE_HOVER)
            self._icon.setText("✨")

    def dragLeaveEvent(self, _event) -> None:
        self.setStyleSheet(self._STYLE_IDLE)
        self._icon.setText("⬇")

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet(self._STYLE_IDLE)
        self._icon.setText("⬇")
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)


# ─── Рабочий поток (шифрование / расшифровка) ─────────────────────────────────

class CryptoWorker(QThread):
    """Выполняет криптографические операции в фоне."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str, dict)  # (output_path, metadata)
    error = pyqtSignal(str)

    def __init__(
        self,
        operation: str,
        password: str,
        path: str,
        **kwargs,
    ) -> None:
        super().__init__()
        self.operation = operation  # encrypt_file | decrypt_file | encrypt_folder | decrypt_folder
        self.password = password
        self.path = path
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            result, meta = getattr(self, f"_{self.operation}")()
            self.finished.emit(result, meta)
        except Exception as exc:
            self.error.emit(str(exc))

    # ── четыре операции ─────────────────────────────────────────────────────

    def _encrypt_file(self):
        crypt = XaletherChaos(self.password)
        return crypt.encrypt_file(
            self.path,
            mode=self.kwargs.get("mode", "transfer"),
            permission_code=self.kwargs.get("permission_code"),
            remove_original=self.kwargs.get("remove_original", False),
            content_type="file",
            progress_cb=self.progress.emit,
        )

    def _decrypt_file(self):
        crypt = XaletherChaos(self.password)
        return crypt.decrypt_file(
            self.path,
            self.password,
            permission_code=self.kwargs.get("permission_code"),
            remove_encrypted=self.kwargs.get("remove_encrypted", False),
            progress_cb=self.progress.emit,
        )

    def _encrypt_folder(self):
        self.progress.emit(5)
        zip_path = folder_to_zip(self.path)
        self.progress.emit(35)

        crypt = XaletherChaos(self.password)
        output = self.path + '.xalether'
        result, meta = crypt.encrypt_file(
            zip_path,
            output=output,
            mode=self.kwargs.get("mode", "transfer"),
            permission_code=self.kwargs.get("permission_code"),
            remove_original=False,
            content_type="folder",
            progress_cb=lambda p: self.progress.emit(35 + int(p * 0.55)),
        )
        os.remove(zip_path)
        self.progress.emit(95)

        if self.kwargs.get("remove_original", False):
            shutil.rmtree(self.path)
        self.progress.emit(100)
        return result, meta

    def _decrypt_folder(self):
        self.progress.emit(5)
        zip_path = tempfile.mktemp(suffix='.zip')
        crypt = XaletherChaos(self.password)
        _, meta = crypt.decrypt_file(
            self.path,
            self.password,
            permission_code=self.kwargs.get("permission_code"),
            output=zip_path,
            remove_encrypted=False,
            progress_cb=lambda p: self.progress.emit(5 + int(p * 0.55)),
        )
        self.progress.emit(65)

        out_folder = self.path[:-9] if self.path.endswith('.xalether') else self.path + '_decrypted'
        zip_to_folder(zip_path, out_folder)
        os.remove(zip_path)
        self.progress.emit(95)

        if self.kwargs.get("remove_encrypted", False):
            os.remove(self.path)
        self.progress.emit(100)
        return out_folder, meta


# ─── Диалог ввода кода разрешения ─────────────────────────────────────────────

class PermissionCodeDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Код разрешения")
        self.setFixedSize(400, 160)
        self.setModal(True)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        lay.addWidget(QLabel("Введите код разрешения:"))

        self.entry = QLineEdit()
        self.entry.setPlaceholderText("XAL-XXXX-XXXX-XXXX")
        self.entry.setAlignment(Qt.AlignCenter)
        font = QFont("JetBrains Mono, Consolas, Courier New")
        font.setPointSize(13)
        self.entry.setFont(font)
        lay.addWidget(self.entry)

        btn = QPushButton("Подтвердить")
        btn.setObjectName("accent")
        btn.clicked.connect(self.accept)
        self.entry.returnPressed.connect(self.accept)
        lay.addWidget(btn)

    def get_code(self) -> str:
        return self.entry.text().strip().upper()


# ─── Окно входа ───────────────────────────────────────────────────────────────

class LoginDialog(QDialog):
    """Первый запуск: создание мастер-пароля. Обычный вход: проверка."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XALETHER CRYPT v2.0")
        self.setFixedSize(460, 340)
        self.setModal(True)
        self.password: str = ""
        self._first = is_first_run()
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 30, 40, 30)
        lay.setSpacing(14)

        title = QLabel("XALETHER CRYPT v2.0")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #8A5CF5;")
        lay.addWidget(title)

        subtitle_text = (
            "Первый запуск — создайте мастер-пароль"
            if self._first else
            "Введите мастер-пароль для входа"
        )
        sub = QLabel(subtitle_text)
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #666; font-size: 12px;")
        lay.addWidget(sub)

        self._pass = QLineEdit()
        self._pass.setEchoMode(QLineEdit.Password)
        self._pass.setPlaceholderText("Пароль")
        self._pass.setAlignment(Qt.AlignCenter)
        self._pass.returnPressed.connect(self._login)
        lay.addWidget(self._pass)

        if self._first:
            self._confirm = QLineEdit()
            self._confirm.setEchoMode(QLineEdit.Password)
            self._confirm.setPlaceholderText("Повторите пароль")
            self._confirm.setAlignment(Qt.AlignCenter)
            self._confirm.returnPressed.connect(self._login)
            lay.addWidget(self._confirm)
        else:
            self._confirm = None

        btn = QPushButton("СОЗДАТЬ" if self._first else "ВОЙТИ")
        btn.setObjectName("accent")
        btn.setFixedHeight(42)
        btn.clicked.connect(self._login)
        lay.addWidget(btn)

        self._pass.setFocus()

    def _login(self) -> None:
        pwd = self._pass.text()
        if self._first:
            if pwd != self._confirm.text():
                QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
                return
            if len(pwd) < 6:
                QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
                return
            save_password_hash(pwd)
        else:
            if not verify_password(pwd):
                QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                return
        self.password = pwd
        self.accept()


# ─── Главное окно ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, password: str) -> None:
        super().__init__()
        self.password = password
        self._worker: Optional[CryptoWorker] = None
        self.settings = load_settings()

        self.setWindowTitle("XALETHER CRYPT v2.0")
        self.resize(860, 720)
        self._build_ui()

    # ── сборка интерфейса ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 10)
        root.setSpacing(10)

        # Заголовок
        title = QLabel("XALETHER CRYPT v2.0")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #8A5CF5;")
        root.addWidget(title)

        sub = QLabel("AES-256-GCM → ChaCha20-Poly1305  |  Файлы + Папки")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #555; font-size: 11px;")
        root.addWidget(sub)

        # Прогресс-бар (глобальный)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("")
        self.progress.setFixedHeight(10)
        root.addWidget(self.progress)

        # Вкладки
        tabs = QTabWidget()
        root.addWidget(tabs)

        self._build_crypto_tab(tabs)
        self._build_permissions_tab(tabs)
        self._build_passgen_tab(tabs)
        self._build_settings_tab(tabs)
        self._build_log_tab(tabs)

        # Статус-бар
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._set_status("Готов")

    # ── вкладка Шифрование ───────────────────────────────────────────────────

    def _build_crypto_tab(self, tabs: QTabWidget) -> None:
        page = QWidget()
        tabs.addTab(page, "🔒  Шифрование")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(14)

        # Drop-зона
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        lay.addWidget(self.drop_zone)

        # Режим шифрования
        mode_box = QGroupBox("Режим шифрования")
        mode_lay = QVBoxLayout(mode_box)
        mode_lay.setSpacing(6)

        self._mode_group = QButtonGroup(self)
        for label, value in [
            ("🔒  Личный — только этот компьютер", "personal"),
            ("📤  Передача — без ограничений", "transfer"),
            ("🎫  С разрешением — одноразовый код", "permission"),
        ]:
            rb = QRadioButton(label)
            rb.setProperty("mode_value", value)
            if value == self.settings.get("default_mode", "transfer"):
                rb.setChecked(True)
            self._mode_group.addButton(rb)
            mode_lay.addWidget(rb)
        lay.addWidget(mode_box)

        # Опции
        opts_box = QGroupBox("Параметры")
        opts_lay = QVBoxLayout(opts_box)
        self._rm_orig = QCheckBox("Удалять оригинал после шифрования")
        self._rm_orig.setChecked(self.settings.get("remove_original", True))
        self._rm_enc = QCheckBox("Удалять .xalether после расшифровки")
        self._rm_enc.setChecked(self.settings.get("remove_encrypted", True))
        opts_lay.addWidget(self._rm_orig)
        opts_lay.addWidget(self._rm_enc)
        lay.addWidget(opts_box)

        # Кнопки операций
        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(8)
        for text, slot in [
            ("🔒 Зашифровать файл", self._encrypt_file),
            ("🔓 Расшифровать", self._decrypt_auto),
            ("📁 Зашифровать папку", self._encrypt_folder),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(38)
            b.clicked.connect(slot)
            btn_lay.addWidget(b)
        lay.addLayout(btn_lay)
        lay.addStretch()

    # ── вкладка Разрешения ───────────────────────────────────────────────────

    def _build_permissions_tab(self, tabs: QTabWidget) -> None:
        page = QWidget()
        tabs.addTab(page, "🎫  Разрешения")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 16)

        lbl = QLabel("Активные коды разрешений")
        lbl.setStyleSheet("color: #8A5CF5; font-size: 14px; font-weight: bold;")
        lay.addWidget(lbl)

        self._perms_view = QTextEdit()
        self._perms_view.setReadOnly(True)
        lay.addWidget(self._perms_view)

        btn = QPushButton("🔄  Обновить")
        btn.setFixedWidth(140)
        btn.clicked.connect(self._refresh_permissions)
        lay.addWidget(btn)

        self._refresh_permissions()

    # ── вкладка Генератор паролей ────────────────────────────────────────────

    def _build_passgen_tab(self, tabs: QTabWidget) -> None:
        page = QWidget()
        tabs.addTab(page, "🔑  Генератор")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lbl = QLabel("Генератор надёжных паролей")
        lbl.setStyleSheet("color: #8A5CF5; font-size: 14px; font-weight: bold;")
        lay.addWidget(lbl)

        # Длина
        len_lay = QHBoxLayout()
        len_lay.addWidget(QLabel("Длина:"))
        self._pass_len = QSpinBox()
        self._pass_len.setRange(6, 128)
        self._pass_len.setValue(20)
        self._pass_len.setFixedWidth(70)
        len_lay.addWidget(self._pass_len)
        len_lay.addStretch()
        lay.addLayout(len_lay)

        # Опции набора символов
        self._pg_upper = QCheckBox("Заглавные (A-Z)")
        self._pg_lower = QCheckBox("Строчные (a-z)")
        self._pg_digits = QCheckBox("Цифры (0-9)")
        self._pg_special = QCheckBox("Спецсимволы (!@#…)")
        for cb in (self._pg_upper, self._pg_lower, self._pg_digits, self._pg_special):
            cb.setChecked(True)
            lay.addWidget(cb)

        # Вывод пароля
        self._gen_output = QLineEdit()
        self._gen_output.setReadOnly(True)
        self._gen_output.setAlignment(Qt.AlignCenter)
        mono = QFont("JetBrains Mono, Consolas, Courier New")
        mono.setPointSize(14)
        self._gen_output.setFont(mono)
        self._gen_output.setFixedHeight(44)
        lay.addWidget(self._gen_output)

        # Кнопки
        btn_row = QHBoxLayout()
        gen_btn = QPushButton("⚡ Сгенерировать")
        gen_btn.setObjectName("accent")
        gen_btn.clicked.connect(self._generate_password)
        copy_btn = QPushButton("📋 Копировать")
        copy_btn.clicked.connect(self._copy_password)
        btn_row.addWidget(gen_btn)
        btn_row.addWidget(copy_btn)
        lay.addLayout(btn_row)
        lay.addStretch()

        self._generate_password()

    # ── вкладка Настройки ────────────────────────────────────────────────────

    def _build_settings_tab(self, tabs: QTabWidget) -> None:
        page = QWidget()
        tabs.addTab(page, "⚙️  Настройки")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(10)

        info = QTextEdit()
        info.setReadOnly(True)
        info.setHtml("""
<style>
  body { background: #111; color: #D0D0D0; font-family: 'Consolas', monospace; font-size: 12px; }
  h3 { color: #8A5CF5; margin-bottom: 4px; }
  td { padding: 3px 12px; }
  .key { color: #8A5CF5; }
  .val { color: #4CAF50; }
</style>
<body>
<h3>XALETHER CRYPT v2.0</h3>
<table>
  <tr><td class="key">Шифрование:</td><td class="val">AES-256-GCM → ChaCha20-Poly1305</td></tr>
  <tr><td class="key">KDF:</td><td class="val">PBKDF2-SHA256, 500 000 итераций</td></tr>
  <tr><td class="key">Соль:</td><td class="val">16 байт (случайная)</td></tr>
  <tr><td class="key">AAD:</td><td class="val">XALETHER_CRYPT_V2</td></tr>
  <tr><td class="key">Папки:</td><td class="val">ZIP-архив → шифрование</td></tr>
</table>
<br>
<h3>Режимы</h3>
<table>
  <tr><td class="key">Личный</td><td>Привязан к HWID — не работает на другом ПК</td></tr>
  <tr><td class="key">Передача</td><td>Без ограничений — любой с паролем</td></tr>
  <tr><td class="key">Разрешение</td><td>Одноразовый код, 24 часа действия</td></tr>
</table>
<br>
<b style="color:#e57373;">⚠  Мастер-пароль НЕ восстанавливается!</b>
</body>
""")
        lay.addWidget(info)

        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.clicked.connect(self._save_settings)
        lay.addWidget(save_btn)

    # ── вкладка Лог ─────────────────────────────────────────────────────────

    def _build_log_tab(self, tabs: QTabWidget) -> None:
        page = QWidget()
        tabs.addTab(page, "📋  Лог")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 12, 16, 12)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        lay.addWidget(self._log_view)

        clear_btn = QPushButton("🗑  Очистить")
        clear_btn.setFixedWidth(120)
        clear_btn.clicked.connect(self._log_view.clear)
        lay.addWidget(clear_btn)

        self._log("Готов. AES-256-GCM → ChaCha20-Poly1305")

    # ── вспомогательные методы ───────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_view.append(f'<span style="color:#555">[{ts}]</span> {msg}')

    def _set_status(self, text: str) -> None:
        self.status.showMessage(text)

    def _get_mode(self) -> str:
        for btn in self._mode_group.buttons():
            if btn.isChecked():
                return btn.property("mode_value")
        return "transfer"

    def _refresh_permissions(self) -> None:
        perms = get_active_permissions()
        self._perms_view.clear()
        if not perms:
            self._perms_view.setPlainText("Нет активных кодов разрешений.")
            return
        lines = []
        for code, data in perms.items():
            expires = datetime.fromisoformat(data["expires"])
            hours = max(0, int((expires - datetime.now()).total_seconds() // 3600))
            lines.append(f"Код:    {code}")
            lines.append(f"  Использован: {data['used']}/{data['max_uses']}")
            lines.append(f"  Истекает:    через ~{hours} ч.")
            if data.get("used_by"):
                hwid = data["used_by"][-1]["hwid"][:20]
                lines.append(f"  Последний:   {hwid}...")
            lines.append("─" * 44)
        self._perms_view.setPlainText('\n'.join(lines))

    def _generate_password(self) -> None:
        pwd = generate_password(
            length=self._pass_len.value(),
            use_upper=self._pg_upper.isChecked(),
            use_lower=self._pg_lower.isChecked(),
            use_digits=self._pg_digits.isChecked(),
            use_special=self._pg_special.isChecked(),
        )
        self._gen_output.setText(pwd)

    def _copy_password(self) -> None:
        text = self._gen_output.text()
        if text:
            QApplication.clipboard().setText(text)
            self._set_status("Пароль скопирован в буфер обмена")

    def _save_settings(self) -> None:
        self.settings["remove_original"] = self._rm_orig.isChecked()
        self.settings["remove_encrypted"] = self._rm_enc.isChecked()
        self.settings["default_mode"] = self._get_mode()
        save_settings(self.settings)
        self._set_status("Настройки сохранены")

    # ── drag-and-drop обработчик ─────────────────────────────────────────────

    def _on_files_dropped(self, paths: list) -> None:
        if not paths:
            return
        path = paths[0]
        if os.path.isdir(path):
            self._run_operation("encrypt_folder", path)
        else:
            self._run_operation("encrypt_file", path)

    # ── кнопки операций ─────────────────────────────────────────────────────

    def _encrypt_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл")
        if path:
            self._run_operation("encrypt_file", path)

    def _decrypt_auto(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите .xalether файл",
            filter="Xalether (*.xalether);;Все файлы (*)"
        )
        if not path:
            return
        try:
            meta = read_metadata(path)
        except Exception:
            meta = {}
        op = "decrypt_folder" if meta.get("content_type") == "folder" else "decrypt_file"
        self._run_operation(op, path)

    def _encrypt_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self._run_operation("encrypt_folder", folder)

    # ── запуск рабочего потока ───────────────────────────────────────────────

    def _run_operation(self, operation: str, path: str) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Занято", "Дождитесь завершения текущей операции.")
            return

        mode = self._get_mode()
        permission_code: Optional[str] = None

        # Генерируем код разрешения при нужном режиме
        if mode == "permission" and operation.startswith("encrypt"):
            permission_code = generate_permission_code()
            create_permission(permission_code, max_uses=1, hours_valid=24)

        # При расшифровке с кодом — запрашиваем его у пользователя
        if operation.startswith("decrypt"):
            try:
                meta = read_metadata(path)
                if meta.get("mode") == "permission":
                    dlg = PermissionCodeDialog(self)
                    if dlg.exec_() != QDialog.Accepted:
                        return
                    permission_code = dlg.get_code()
                    if not permission_code:
                        return
            except Exception:
                pass

        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self._set_status(f"Выполняется: {operation.replace('_', ' ')}…")
        self._log(f"▶ {operation.replace('_', ' ')}: {os.path.basename(path)}")

        self._worker = CryptoWorker(
            operation=operation,
            password=self.password,
            path=path,
            mode=mode,
            permission_code=permission_code,
            remove_original=self._rm_orig.isChecked(),
            remove_encrypted=self._rm_enc.isChecked(),
        )
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(lambda out, m: self._on_done(out, m, operation, path, permission_code))
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # ── обработчики сигналов потока ──────────────────────────────────────────

    def _on_done(self, output: str, meta: dict, operation: str, original: str, perm_code: Optional[str]) -> None:
        self.progress.setValue(100)
        self._refresh_permissions()
        mode = meta.get("mode", "transfer")
        save_history_entry(operation, original, mode, success=True)

        msg = f"Готово!\n\n📂 {output}"
        if perm_code and operation.startswith("encrypt"):
            QApplication.clipboard().setText(perm_code)
            msg += f"\n\n🎫 Код разрешения:\n{perm_code}\n\n(скопирован в буфер)"

        self._log(f"✅ {os.path.basename(output)}")
        self._set_status("Готово")
        self.progress.setFormat("")
        QMessageBox.information(self, "Успех", msg)

    def _on_error(self, error: str) -> None:
        self.progress.setValue(0)
        self.progress.setFormat("")
        self._set_status("Ошибка")
        self._log(f"❌ {error}")
        QMessageBox.critical(self, "Ошибка", error)
