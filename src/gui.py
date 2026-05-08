#!/usr/bin/env python3
"""
XALETHER CRYPT v2.1 — PyQt5 GUI.
Тёмная тема: #1A1A1A / #8A5CF5.
Интерактивные настройки: конструктор цепочки шифров, выбор KDF, сжатия, пресеты.
"""

import copy, os, shutil, tempfile
from datetime import datetime, timedelta
from typing import List, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QRadioButton, QButtonGroup, QTabWidget, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox, QFrame,
    QSpinBox, QSizePolicy, QStatusBar, QListWidget, QListWidgetItem,
    QComboBox, QAbstractItemView, QScrollArea,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QDragEnterEvent, QDropEvent

from crypto import (
    XaletherChaos, save_password_hash, verify_password, is_first_run,
    read_metadata, CIPHER_INFO, CIPHER_REGISTRY, KDF_INFO, COMPRESS_INFO,
    PRESETS, DEFAULT_CONFIG,
)
from permissions import generate_permission_code, create_permission, get_active_permissions
from utils import (
    folder_to_zip, zip_to_folder,
    save_history_entry, load_history,
    load_settings, save_settings, generate_password,
)


# ─── Стиль ────────────────────────────────────────────────────────────────────

STYLESHEET = """
QWidget {
    background-color: #1A1A1A; color: #E3E3E3;
    font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px;
}
QMainWindow, QDialog { background-color: #1A1A1A; }
QLabel { color: #E3E3E3; background: transparent; }

QPushButton {
    background-color: #2D2D2D; color: #E3E3E3;
    border: 1px solid #444; border-radius: 6px; padding: 7px 16px;
}
QPushButton:hover   { background-color: #8A5CF5; border-color: #8A5CF5; color: #FFF; }
QPushButton:pressed { background-color: #7040E0; }
QPushButton:disabled{ color: #555; border-color: #2D2D2D; background: #1E1E1E; }
QPushButton#accent  { background-color: #8A5CF5; color: #FFF; border: none; font-weight: bold; }
QPushButton#accent:hover   { background-color: #9D70F5; }
QPushButton#accent:pressed { background-color: #7040E0; }
QPushButton#preset  { padding: 6px 12px; font-size: 12px; border-radius: 5px; }
QPushButton#danger  { background-color: #3D1515; border-color: #6B2020; color: #FF6B6B; }
QPushButton#danger:hover { background-color: #6B2020; }

QLineEdit {
    background-color: #242424; color: #E3E3E3;
    border: 1px solid #444; border-radius: 6px; padding: 7px 12px;
    selection-background-color: #8A5CF5;
}
QLineEdit:focus { border-color: #8A5CF5; }

QTextEdit {
    background-color: #111; color: #D0D0D0; border: 1px solid #333; border-radius: 4px;
    font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace; font-size: 12px;
    selection-background-color: #8A5CF5;
}

QListWidget {
    background-color: #141414; color: #E3E3E3;
    border: 1px solid #333; border-radius: 4px; font-size: 12px;
}
QListWidget::item         { padding: 5px 8px; border-bottom: 1px solid #222; }
QListWidget::item:selected{ background-color: #3A2580; color: #FFF; }
QListWidget::item:hover   { background-color: #242424; }

QComboBox {
    background-color: #242424; color: #E3E3E3;
    border: 1px solid #444; border-radius: 5px; padding: 5px 10px;
}
QComboBox:focus { border-color: #8A5CF5; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #242424; color: #E3E3E3; border: 1px solid #555;
    selection-background-color: #8A5CF5;
}

QTabWidget::pane { border: 1px solid #333; background: #1A1A1A; }
QTabBar::tab {
    background: #242424; color: #888; border: 1px solid #333;
    border-bottom: none; padding: 8px 18px; margin-right: 2px;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
}
QTabBar::tab:selected { background: #1A1A1A; color: #8A5CF5; border-bottom: 2px solid #8A5CF5; }
QTabBar::tab:hover    { color: #E3E3E3; }

QCheckBox, QRadioButton { color: #E3E3E3; spacing: 8px; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px; border: 1px solid #555; border-radius: 3px; background: #242424;
}
QCheckBox::indicator:checked { background: #8A5CF5; border-color: #8A5CF5; }
QRadioButton::indicator { border-radius: 8px; }
QRadioButton::indicator:checked { background: #8A5CF5; border-color: #8A5CF5; }

QProgressBar {
    background: #242424; border: 1px solid #333; border-radius: 4px;
    text-align: center; color: #E3E3E3; font-size: 11px; min-height: 16px;
}
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6030D0, stop:1 #8A5CF5); border-radius: 3px; }

QGroupBox {
    color: #8A5CF5; border: 1px solid #333; border-radius: 6px;
    margin-top: 12px; padding-top: 10px; font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; background: #1A1A1A; }

QSpinBox {
    background: #242424; color: #E3E3E3; border: 1px solid #444; border-radius: 4px; padding: 4px 8px;
}
QSpinBox::up-button, QSpinBox::down-button { background: #333; width: 16px; border: none; }

QScrollBar:vertical { background: #1A1A1A; width: 7px; border: none; }
QScrollBar::handle:vertical { background: #444; border-radius: 3px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #8A5CF5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QStatusBar { background: #111; color: #666; font-size: 11px; border-top: 1px solid #2D2D2D; }
QStatusBar::item { border: none; }

QFrame#drop_zone        { border: 2px dashed #444; border-radius: 10px; background: #202020; }
QFrame#drop_zone_active { border: 2px dashed #8A5CF5; border-radius: 10px; background: #1E1530; }
QFrame#config_card      { border: 1px solid #333; border-radius: 6px; background: #141414; }
QFrame#separator        { background-color: #333; max-height: 1px; }
"""

SECURITY_COLORS = {
    "Low":     ("#FF6B6B", "⚠"),
    "Medium":  ("#FFB347", "◎"),
    "High":    ("#4CAF50", "✓"),
    "Overkill":("#8A5CF5", "★"),
}


# ─── Drop-зона ────────────────────────────────────────────────────────────────

class DropZone(QFrame):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("drop_zone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setContentsMargins(20, 12, 20, 12)

        self._icon = QLabel("⬇", self)
        self._icon.setAlignment(Qt.AlignCenter)
        self._icon.setStyleSheet("font-size: 26px; color: #555; background: transparent;")

        self._text = QLabel("Перетащите файл или папку  ·  или нажмите для выбора", self)
        self._text.setAlignment(Qt.AlignCenter)
        self._text.setStyleSheet("color: #555; font-size: 12px; background: transparent;")

        lay.addWidget(self._icon)
        lay.addWidget(self._text)

    def mousePressEvent(self, _e) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Выберите файл")
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.setObjectName("drop_zone_active")
            self.style().polish(self)
            self._icon.setText("✨")

    def dragLeaveEvent(self, _e) -> None:
        self._reset()

    def dropEvent(self, e) -> None:
        self._reset()
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)

    def _reset(self) -> None:
        self.setObjectName("drop_zone")
        self.style().polish(self)
        self._icon.setText("⬇")


# ─── Рабочий поток ────────────────────────────────────────────────────────────

class CryptoWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str, dict)
    error    = pyqtSignal(str)

    def __init__(self, operation: str, password: str, path: str,
                 cipher_config: dict, **kwargs) -> None:
        super().__init__()
        self.operation     = operation
        self.password      = password
        self.path          = path
        self.cipher_config = cipher_config
        self.kwargs        = kwargs

    def run(self) -> None:
        try:
            out, meta = getattr(self, f"_{self.operation}")()
            self.finished.emit(out, meta)
        except Exception as exc:
            self.error.emit(str(exc))

    def _encrypt_file(self):
        crypt = XaletherChaos(self.password, config=self.cipher_config)
        return crypt.encrypt_file(
            self.path,
            mode=self.kwargs.get("mode", "transfer"),
            permission_code=self.kwargs.get("permission_code"),
            remove_original=self.kwargs.get("remove_original", False),
            content_type="file",
            progress_cb=self.progress.emit,
        )

    def _decrypt_file(self):
        crypt = XaletherChaos(self.password, config=self.cipher_config)
        return crypt.decrypt_file(
            self.path, self.password,
            permission_code=self.kwargs.get("permission_code"),
            remove_encrypted=self.kwargs.get("remove_encrypted", False),
            progress_cb=self.progress.emit,
        )

    def _encrypt_folder(self):
        self.progress.emit(5)
        zip_path = folder_to_zip(self.path)
        self.progress.emit(30)
        crypt = XaletherChaos(self.password, config=self.cipher_config)
        out, meta = crypt.encrypt_file(
            zip_path, output=self.path + ".xalether",
            mode=self.kwargs.get("mode", "transfer"),
            permission_code=self.kwargs.get("permission_code"),
            remove_original=False, content_type="folder",
            progress_cb=lambda p: self.progress.emit(30 + int(p * 0.6)),
        )
        os.remove(zip_path)
        if self.kwargs.get("remove_original", False):
            shutil.rmtree(self.path)
        self.progress.emit(100)
        return out, meta

    def _decrypt_folder(self):
        self.progress.emit(5)
        zip_path = tempfile.mktemp(suffix=".zip")
        crypt = XaletherChaos(self.password, config=self.cipher_config)
        _, meta = crypt.decrypt_file(
            self.path, self.password,
            permission_code=self.kwargs.get("permission_code"),
            output=zip_path, remove_encrypted=False,
            progress_cb=lambda p: self.progress.emit(5 + int(p * 0.55)),
        )
        self.progress.emit(65)
        out_dir = self.path[:-9] if self.path.endswith(".xalether") else self.path + "_decrypted"
        zip_to_folder(zip_path, out_dir)
        os.remove(zip_path)
        if self.kwargs.get("remove_encrypted", False):
            os.remove(self.path)
        self.progress.emit(100)
        return out_dir, meta


# ─── Вспомогательные диалоги ─────────────────────────────────────────────────

class PermissionCodeDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Код разрешения")
        self.setFixedSize(400, 155)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)
        lay.addWidget(QLabel("Введите код разрешения:"))
        self.entry = QLineEdit()
        self.entry.setPlaceholderText("XAL-XXXX-XXXX-XXXX")
        self.entry.setAlignment(Qt.AlignCenter)
        self.entry.setFont(QFont("Consolas,Courier New", 13))
        self.entry.returnPressed.connect(self.accept)
        lay.addWidget(self.entry)
        btn = QPushButton("Подтвердить")
        btn.setObjectName("accent")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)

    def get_code(self) -> str:
        return self.entry.text().strip().upper()


# ─── Окно входа ───────────────────────────────────────────────────────────────

class LoginDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("XALETHER CRYPT v2.1")
        self.setFixedSize(460, 340)
        self.password: str = ""
        self._first = is_first_run()
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 30, 40, 30)
        lay.setSpacing(14)

        t = QLabel("XALETHER CRYPT v2.1")
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet("font-size: 22px; font-weight: bold; color: #8A5CF5;")
        lay.addWidget(t)

        s = QLabel("Создайте мастер-пароль" if self._first else "Введите мастер-пароль")
        s.setAlignment(Qt.AlignCenter)
        s.setStyleSheet("color: #666; font-size: 12px;")
        lay.addWidget(s)

        self._pw = QLineEdit()
        self._pw.setEchoMode(QLineEdit.Password)
        self._pw.setPlaceholderText("Пароль")
        self._pw.setAlignment(Qt.AlignCenter)
        self._pw.returnPressed.connect(self._login)
        lay.addWidget(self._pw)

        self._cf: Optional[QLineEdit] = None
        if self._first:
            self._cf = QLineEdit()
            self._cf.setEchoMode(QLineEdit.Password)
            self._cf.setPlaceholderText("Повторите пароль")
            self._cf.setAlignment(Qt.AlignCenter)
            self._cf.returnPressed.connect(self._login)
            lay.addWidget(self._cf)

        btn = QPushButton("СОЗДАТЬ" if self._first else "ВОЙТИ")
        btn.setObjectName("accent")
        btn.setFixedHeight(42)
        btn.clicked.connect(self._login)
        lay.addWidget(btn)
        self._pw.setFocus()

    def _login(self) -> None:
        pwd = self._pw.text()
        if self._first:
            if self._cf and pwd != self._cf.text():
                QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
                return
            if len(pwd) < 6:
                QMessageBox.warning(self, "Ошибка", "Минимум 6 символов")
                return
            save_password_hash(pwd)
        else:
            if not verify_password(pwd):
                QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                return
        self.password = pwd
        self.accept()


# ─── Конструктор цепочки шифров ───────────────────────────────────────────────

class CipherChainEditor(QWidget):
    """
    Виджет для интерактивного построения цепочки шифров.
    Показывает текущую цепочку, позволяет добавлять/удалять/перемещать слои.
    """
    changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Список текущей цепочки
        self._list = QListWidget()
        self._list.setFixedHeight(140)
        self._list.setDragDropMode(QAbstractItemView.InternalMove)
        self._list.model().rowsMoved.connect(lambda: self.changed.emit())
        root.addWidget(self._list)

        # Строка кнопок управления
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)

        self._combo = QComboBox()
        for cid, info in CIPHER_INFO.items():
            sec   = info["security"]
            color, mark = SECURITY_COLORS.get(sec, ("#888", ""))
            self._combo.addItem(f"{mark} {info['label']}", cid)
        ctrl.addWidget(self._combo, 1)

        add_btn = QPushButton("+ Добавить")
        add_btn.clicked.connect(self._add)
        ctrl.addWidget(add_btn)

        del_btn = QPushButton("✕ Удалить")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._remove)
        ctrl.addWidget(del_btn)

        up_btn = QPushButton("↑")
        up_btn.setFixedWidth(32)
        up_btn.clicked.connect(self._move_up)
        ctrl.addWidget(up_btn)

        dn_btn = QPushButton("↓")
        dn_btn.setFixedWidth(32)
        dn_btn.clicked.connect(self._move_down)
        ctrl.addWidget(dn_btn)

        root.addLayout(ctrl)

        # Подсказка к выбранному шифру
        self._desc = QLabel("")
        self._desc.setStyleSheet("color: #666; font-size: 11px;")
        self._desc.setWordWrap(True)
        root.addWidget(self._desc)

        self._list.currentItemChanged.connect(self._on_select)
        self._combo.currentIndexChanged.connect(self._on_combo_change)
        self._on_combo_change()

    def _on_combo_change(self) -> None:
        cid  = self._combo.currentData()
        info = CIPHER_INFO.get(cid, {})
        self._desc.setText(info.get("description", ""))

    def _on_select(self, item, _prev) -> None:
        if item:
            cid  = item.data(Qt.UserRole)
            info = CIPHER_INFO.get(cid, {})
            self._desc.setText(info.get("description", ""))

    def _make_item(self, cid: str) -> QListWidgetItem:
        info = CIPHER_INFO.get(cid, {"label": cid, "security": "Medium"})
        sec  = info["security"]
        color, mark = SECURITY_COLORS.get(sec, ("#888", ""))
        item = QListWidgetItem(f"  {mark}  {info['label']}")
        item.setData(Qt.UserRole, cid)
        item.setForeground(__import__("PyQt5.QtGui", fromlist=["QColor"]).QColor(color))
        return item

    def _add(self) -> None:
        cid = self._combo.currentData()
        if cid:
            self._list.addItem(self._make_item(cid))
            self.changed.emit()

    def _remove(self) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
            self.changed.emit()

    def _move_up(self) -> None:
        r = self._list.currentRow()
        if r > 0:
            item = self._list.takeItem(r)
            self._list.insertItem(r - 1, item)
            self._list.setCurrentRow(r - 1)
            self.changed.emit()

    def _move_down(self) -> None:
        r = self._list.currentRow()
        if r < self._list.count() - 1:
            item = self._list.takeItem(r)
            self._list.insertItem(r + 1, item)
            self._list.setCurrentRow(r + 1)
            self.changed.emit()

    # ── API ─────────────────────────────────────────────────────────────────

    def get_chain(self) -> List[str]:
        return [self._list.item(i).data(Qt.UserRole) for i in range(self._list.count())]

    def set_chain(self, chain: List[str]) -> None:
        self._list.clear()
        for cid in chain:
            self._list.addItem(self._make_item(cid))
        self.changed.emit()


# ─── Главное окно ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, password: str) -> None:
        super().__init__()
        self.password = password
        self._worker: Optional[CryptoWorker] = None

        self.settings = load_settings()
        self._cipher_config: dict = copy.deepcopy(
            self.settings.get("cipher_config", DEFAULT_CONFIG)
        )

        self.setWindowTitle("XALETHER CRYPT v2.1")
        self.resize(900, 760)
        self._build_ui()

    @property
    def cipher_config(self) -> dict:
        return self._cipher_config

    # ── строим UI ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 14, 20, 8)
        root.setSpacing(8)

        title = QLabel("XALETHER CRYPT v2.1")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 25px; font-weight: bold; color: #8A5CF5;")
        root.addWidget(title)

        sub = QLabel("Каскадное шифрование · 9 алгоритмов · 4 KDF · настраиваемые цепочки")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #555; font-size: 11px;")
        root.addWidget(sub)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        root.addWidget(self.progress)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        self._build_crypto_tab()
        self._build_settings_tab()
        self._build_permissions_tab()
        self._build_passgen_tab()
        self._build_log_tab()

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self._set_status("Готов")
        self._update_config_card()

    # ── вкладка Шифрование ────────────────────────────────────────────────────

    def _build_crypto_tab(self) -> None:
        page = QWidget()
        self._tabs.addTab(page, "🔒  Шифрование")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        # Drop-зона
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_drop)
        lay.addWidget(self.drop_zone)

        # Режим шифрования + карточка конфига — рядом
        row = QHBoxLayout()
        row.setSpacing(12)

        mode_box = QGroupBox("Режим")
        mode_lay = QVBoxLayout(mode_box)
        mode_lay.setSpacing(5)
        self._mode_grp = QButtonGroup(self)
        for label, val in [
            ("🔒  Личный — только этот ПК", "personal"),
            ("📤  Передача — без ограничений", "transfer"),
            ("🎫  Разрешение — одноразовый код", "permission"),
        ]:
            rb = QRadioButton(label)
            rb.setProperty("mode_val", val)
            if val == self.settings.get("default_mode", "transfer"):
                rb.setChecked(True)
            self._mode_grp.addButton(rb)
            mode_lay.addWidget(rb)
        row.addWidget(mode_box)

        # Карточка текущей конфигурации шифрования
        self._config_card = QFrame()
        self._config_card.setObjectName("config_card")
        card_lay = QVBoxLayout(self._config_card)
        card_lay.setContentsMargins(12, 8, 12, 8)
        card_lay.setSpacing(3)
        card_title = QLabel("Текущая конфигурация")
        card_title.setStyleSheet("color: #8A5CF5; font-weight: bold; font-size: 11px;")
        self._card_chain = QLabel("...")
        self._card_chain.setStyleSheet("color: #E3E3E3; font-size: 12px;")
        self._card_chain.setWordWrap(True)
        self._card_kdf = QLabel("...")
        self._card_kdf.setStyleSheet("color: #888; font-size: 11px;")
        self._card_compress = QLabel("...")
        self._card_compress.setStyleSheet("color: #888; font-size: 11px;")
        card_lay.addWidget(card_title)
        card_lay.addWidget(self._card_chain)
        card_lay.addWidget(self._card_kdf)
        card_lay.addWidget(self._card_compress)
        card_lay.addStretch()
        row.addWidget(self._config_card, 1)
        lay.addLayout(row)

        # Опции
        opts_box = QGroupBox("Параметры")
        opts_lay = QHBoxLayout(opts_box)
        self._rm_orig = QCheckBox("Удалять оригинал после шифрования")
        self._rm_orig.setChecked(self.settings.get("remove_original", True))
        self._rm_enc  = QCheckBox("Удалять .xalether после расшифровки")
        self._rm_enc.setChecked(self.settings.get("remove_encrypted", True))
        opts_lay.addWidget(self._rm_orig)
        opts_lay.addWidget(self._rm_enc)
        lay.addWidget(opts_box)

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        for text, slot in [
            ("🔒 Зашифровать файл", self._encrypt_file),
            ("🔓 Расшифровать", self._decrypt_auto),
            ("📁 Зашифровать папку", self._encrypt_folder),
        ]:
            b = QPushButton(text)
            b.setFixedHeight(38)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        lay.addLayout(btn_row)
        lay.addStretch()

    # ── вкладка Настройки (интерактивные) ────────────────────────────────────

    def _build_settings_tab(self) -> None:
        outer = QWidget()
        self._tabs.addTab(outer, "⚙️  Настройки")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        page = QWidget()
        scroll.setWidget(page)

        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.addWidget(scroll)

        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(14)

        # ── Пресеты ──────────────────────────────────────────────────────────
        pbox = QGroupBox("Пресеты")
        play = QHBoxLayout(pbox)
        play.setSpacing(8)
        for pid, info in PRESETS.items():
            b = QPushButton(f"{info['icon']} {info['label']}")
            b.setObjectName("preset")
            b.setToolTip(info["description"])
            b.clicked.connect(lambda _, p=pid: self._apply_preset(p))
            play.addWidget(b)
        lay.addWidget(pbox)

        # ── Цепочка шифров ───────────────────────────────────────────────────
        chain_box = QGroupBox("Цепочка шифров  (drag to reorder)")
        chain_lay = QVBoxLayout(chain_box)
        self._chain_editor = CipherChainEditor()
        self._chain_editor.set_chain(self._cipher_config["cipher_chain"])
        self._chain_editor.changed.connect(self._on_chain_changed)
        chain_lay.addWidget(self._chain_editor)

        hint = QLabel("Шифры применяются слева-направо. Последний — внешний слой.")
        hint.setStyleSheet("color: #555; font-size: 11px;")
        chain_lay.addWidget(hint)
        lay.addWidget(chain_box)

        # ── KDF ──────────────────────────────────────────────────────────────
        kdf_box = QGroupBox("Алгоритм деривации ключей (KDF)")
        kdf_lay = QVBoxLayout(kdf_box)
        kdf_lay.setSpacing(6)

        self._kdf_grp = QButtonGroup(self)
        cur_kdf = self._cipher_config.get("kdf", {}).get("type", "pbkdf2-sha256")
        for kid, kinfo in KDF_INFO.items():
            rb = QRadioButton(kinfo["label"])
            rb.setProperty("kdf_id", kid)
            rb.setToolTip(kinfo["description"])
            if kid == cur_kdf:
                rb.setChecked(True)
            rb.toggled.connect(self._on_kdf_changed)
            self._kdf_grp.addButton(rb)
            kdf_lay.addWidget(rb)

        # Итерации (для PBKDF2)
        iter_row = QHBoxLayout()
        iter_row.addWidget(QLabel("Итерации:"))
        self._iter_spin = QSpinBox()
        self._iter_spin.setRange(50_000, 5_000_000)
        self._iter_spin.setSingleStep(50_000)
        self._iter_spin.setValue(
            self._cipher_config.get("kdf", {}).get("iterations", 500_000)
        )
        self._iter_spin.setFixedWidth(110)
        self._iter_spin.valueChanged.connect(self._on_iter_changed)
        iter_row.addWidget(self._iter_spin)
        iter_row.addStretch()
        self._iter_row_widget = QWidget()
        self._iter_row_widget.setLayout(iter_row)
        kdf_lay.addWidget(self._iter_row_widget)
        lay.addWidget(kdf_box)
        self._refresh_iter_visibility()

        # ── Сжатие ───────────────────────────────────────────────────────────
        comp_box = QGroupBox("Сжатие данных")
        comp_lay = QVBoxLayout(comp_box)
        comp_lay.setSpacing(4)
        self._comp_grp = QButtonGroup(self)
        cur_comp = self._cipher_config.get("compression", "zlib-9")
        for cid, cinfo in COMPRESS_INFO.items():
            rb = QRadioButton(f"{cinfo['label']}  —  {cinfo['description']}")
            rb.setProperty("comp_id", cid)
            if cid == cur_comp:
                rb.setChecked(True)
            rb.toggled.connect(self._on_comp_changed)
            self._comp_grp.addButton(rb)
            comp_lay.addWidget(rb)
        lay.addWidget(comp_box)

        # ── Сводка ──────────────────────────────────────────────────────────
        summary_box = QGroupBox("Текущая конфигурация")
        summary_lay = QVBoxLayout(summary_box)
        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            "font-family: 'Consolas','Courier New',monospace; font-size: 12px; color: #CCC;"
        )
        self._summary_lbl.setWordWrap(True)
        summary_lay.addWidget(self._summary_lbl)
        lay.addWidget(summary_box)

        # ── Кнопка сохранения ────────────────────────────────────────────────
        save_btn = QPushButton("💾  Сохранить настройки")
        save_btn.setObjectName("accent")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_settings)
        lay.addWidget(save_btn)
        lay.addStretch()

        self._refresh_summary()

    # ── вкладка Разрешения ────────────────────────────────────────────────────

    def _build_permissions_tab(self) -> None:
        page = QWidget()
        self._tabs.addTab(page, "🎫  Разрешения")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 14, 18, 14)

        lbl = QLabel("Активные коды разрешений")
        lbl.setStyleSheet("color: #8A5CF5; font-size: 14px; font-weight: bold;")
        lay.addWidget(lbl)

        self._perms_view = QTextEdit()
        self._perms_view.setReadOnly(True)
        lay.addWidget(self._perms_view)

        btn = QPushButton("🔄  Обновить")
        btn.setFixedWidth(130)
        btn.clicked.connect(self._refresh_permissions)
        lay.addWidget(btn)
        self._refresh_permissions()

    # ── вкладка Генератор паролей ─────────────────────────────────────────────

    def _build_passgen_tab(self) -> None:
        page = QWidget()
        self._tabs.addTab(page, "🔑  Генератор")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(12)

        lbl = QLabel("Генератор надёжных паролей")
        lbl.setStyleSheet("color: #8A5CF5; font-size: 14px; font-weight: bold;")
        lay.addWidget(lbl)

        len_row = QHBoxLayout()
        len_row.addWidget(QLabel("Длина:"))
        self._pass_len = QSpinBox()
        self._pass_len.setRange(6, 128)
        self._pass_len.setValue(20)
        self._pass_len.setFixedWidth(70)
        len_row.addWidget(self._pass_len)
        len_row.addStretch()
        lay.addLayout(len_row)

        self._pg_upper   = QCheckBox("Заглавные  A-Z")
        self._pg_lower   = QCheckBox("Строчные   a-z")
        self._pg_digits  = QCheckBox("Цифры      0-9")
        self._pg_special = QCheckBox("Спецсимволы  !@#$…")
        for cb in (self._pg_upper, self._pg_lower, self._pg_digits, self._pg_special):
            cb.setChecked(True)
            lay.addWidget(cb)

        self._gen_out = QLineEdit()
        self._gen_out.setReadOnly(True)
        self._gen_out.setAlignment(Qt.AlignCenter)
        self._gen_out.setFont(QFont("JetBrains Mono,Consolas,Courier New", 14))
        self._gen_out.setFixedHeight(46)
        lay.addWidget(self._gen_out)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
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

    # ── вкладка Лог ───────────────────────────────────────────────────────────

    def _build_log_tab(self) -> None:
        page = QWidget()
        self._tabs.addTab(page, "📋  Лог")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(14, 10, 14, 10)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        lay.addWidget(self._log_view)
        clr = QPushButton("🗑  Очистить")
        clr.setFixedWidth(120)
        clr.clicked.connect(self._log_view.clear)
        lay.addWidget(clr)
        self._log("XALETHER CRYPT v2.1 готов")

    # ── логика настроек ───────────────────────────────────────────────────────

    def _apply_preset(self, pid: str) -> None:
        p = PRESETS[pid]
        self._cipher_config = {
            "cipher_chain": list(p["cipher_chain"]),
            "kdf":          dict(p["kdf"]),
            "compression":  p["compression"],
        }
        # Синхронизируем UI
        self._chain_editor.set_chain(self._cipher_config["cipher_chain"])
        kdf_type = self._cipher_config["kdf"]["type"]
        for btn in self._kdf_grp.buttons():
            btn.setChecked(btn.property("kdf_id") == kdf_type)
        comp_id = self._cipher_config["compression"]
        for btn in self._comp_grp.buttons():
            btn.setChecked(btn.property("comp_id") == comp_id)
        iters = self._cipher_config["kdf"].get("iterations", 500_000)
        self._iter_spin.setValue(iters)
        self._refresh_iter_visibility()
        self._refresh_summary()
        self._update_config_card()
        self._log(f"Пресет применён: {p['label']} — {p['description']}")

    def _on_chain_changed(self) -> None:
        self._cipher_config["cipher_chain"] = self._chain_editor.get_chain()
        self._refresh_summary()
        self._update_config_card()

    def _on_kdf_changed(self) -> None:
        for btn in self._kdf_grp.buttons():
            if btn.isChecked():
                kdf_id = btn.property("kdf_id")
                iters  = self._iter_spin.value()
                self._cipher_config["kdf"] = {"type": kdf_id, "iterations": iters}
                break
        self._refresh_iter_visibility()
        self._refresh_summary()

    def _on_iter_changed(self, val: int) -> None:
        if "kdf" in self._cipher_config:
            self._cipher_config["kdf"]["iterations"] = val
        self._refresh_summary()

    def _on_comp_changed(self) -> None:
        for btn in self._comp_grp.buttons():
            if btn.isChecked():
                self._cipher_config["compression"] = btn.property("comp_id")
                break
        self._refresh_summary()
        self._update_config_card()

    def _refresh_iter_visibility(self) -> None:
        kdf_type = self._cipher_config.get("kdf", {}).get("type", "pbkdf2-sha256")
        show = KDF_INFO.get(kdf_type, {}).get("has_iterations", True)
        self._iter_row_widget.setVisible(show)

    def _refresh_summary(self) -> None:
        chain = self._cipher_config.get("cipher_chain", [])
        kdf   = self._cipher_config.get("kdf", {})
        comp  = self._cipher_config.get("compression", "zlib-9")

        labels = [CIPHER_INFO.get(c, {}).get("label", c) for c in chain]
        chain_str = " → ".join(labels) if labels else "⚠ Нет шифров (данные не шифруются!)"
        kdf_label = KDF_INFO.get(kdf.get("type",""), {}).get("label", kdf.get("type","?"))
        iters = kdf.get("iterations")
        kdf_str = f"{kdf_label}" + (f", {iters:,} итераций" if iters else "")
        comp_str  = COMPRESS_INFO.get(comp, {}).get("label", comp)

        text = (
            f"Цепочка:  {chain_str}\n"
            f"KDF:      {kdf_str}\n"
            f"Сжатие:   {comp_str}\n"
            f"Слоёв:    {len(chain)}"
        )
        if hasattr(self, "_summary_lbl"):
            self._summary_lbl.setText(text)

    def _update_config_card(self) -> None:
        """Обновляет карточку конфига на вкладке Шифрование."""
        if not hasattr(self, "_card_chain"):
            return
        chain = self._cipher_config.get("cipher_chain", [])
        kdf   = self._cipher_config.get("kdf", {})
        comp  = self._cipher_config.get("compression", "zlib-9")

        labels = [CIPHER_INFO.get(c, {}).get("label", c) for c in chain]
        self._card_chain.setText(" → ".join(labels) if labels else "—")
        kdf_label = KDF_INFO.get(kdf.get("type",""), {}).get("label", kdf.get("type","?"))
        iters = kdf.get("iterations")
        self._card_kdf.setText(kdf_label + (f"  {iters:,} iter" if iters else ""))
        self._card_compress.setText("Сжатие: " + COMPRESS_INFO.get(comp, {}).get("label", comp))

    def _save_settings(self) -> None:
        chain = self._cipher_config.get("cipher_chain", [])
        if not chain:
            QMessageBox.warning(self, "Предупреждение",
                "Цепочка шифров пуста! Добавьте хотя бы один алгоритм.")
            return
        self.settings["remove_original"]  = self._rm_orig.isChecked()
        self.settings["remove_encrypted"] = self._rm_enc.isChecked()
        self.settings["default_mode"]     = self._get_mode()
        self.settings["cipher_config"]    = copy.deepcopy(self._cipher_config)
        save_settings(self.settings)
        self._set_status("Настройки сохранены")
        self._log("Настройки сохранены")

    # ── вспомогательные методы ────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_view.append(f'<span style="color:#555">[{ts}]</span>  {msg}')

    def _set_status(self, text: str) -> None:
        self.status.showMessage(text)

    def _get_mode(self) -> str:
        for btn in self._mode_grp.buttons():
            if btn.isChecked():
                return btn.property("mode_val")
        return "transfer"

    def _refresh_permissions(self) -> None:
        perms = get_active_permissions()
        self._perms_view.clear()
        if not perms:
            self._perms_view.setPlainText("Нет активных кодов разрешений.")
            return
        lines = []
        for code, d in perms.items():
            exp = datetime.fromisoformat(d["expires"])
            hrs = max(0, int((exp - datetime.now()).total_seconds() // 3600))
            lines += [
                f"Код:         {code}",
                f"  Использован: {d['used']}/{d['max_uses']}",
                f"  Истекает:    ~{hrs} ч.",
                "─" * 44,
            ]
        self._perms_view.setPlainText('\n'.join(lines))

    def _generate_password(self) -> None:
        self._gen_out.setText(generate_password(
            length=self._pass_len.value(),
            use_upper=self._pg_upper.isChecked(),
            use_lower=self._pg_lower.isChecked(),
            use_digits=self._pg_digits.isChecked(),
            use_special=self._pg_special.isChecked(),
        ))

    def _copy_password(self) -> None:
        text = self._gen_out.text()
        if text:
            QApplication.clipboard().setText(text)
            self._set_status("Пароль скопирован")

    # ── drag-and-drop ─────────────────────────────────────────────────────────

    def _on_drop(self, paths: list) -> None:
        if not paths:
            return
        path = paths[0]
        op = "encrypt_folder" if os.path.isdir(path) else "encrypt_file"
        self._run_operation(op, path)

    # ── кнопки ───────────────────────────────────────────────────────────────

    def _encrypt_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл")
        if path:
            self._run_operation("encrypt_file", path)

    def _decrypt_auto(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите .xalether", filter="Xalether (*.xalether);;Все (*)"
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

    # ── запуск потока ─────────────────────────────────────────────────────────

    def _run_operation(self, operation: str, path: str) -> None:
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Занято", "Дождитесь завершения операции.")
            return

        chain = self._cipher_config.get("cipher_chain", [])
        if not chain and operation.startswith("encrypt"):
            QMessageBox.warning(self, "Ошибка",
                "Цепочка шифров пуста! Настройте алгоритмы во вкладке Настройки.")
            return

        mode = self._get_mode()
        perm_code: Optional[str] = None

        if mode == "permission" and operation.startswith("encrypt"):
            perm_code = generate_permission_code()
            create_permission(perm_code, max_uses=1, hours_valid=24)

        if operation.startswith("decrypt"):
            try:
                meta = read_metadata(path)
                if meta.get("mode") == "permission":
                    dlg = PermissionCodeDialog(self)
                    if dlg.exec_() != QDialog.Accepted:
                        return
                    perm_code = dlg.get_code()
                    if not perm_code:
                        return
            except Exception:
                pass

        self.progress.setValue(0)
        self._set_status(f"▶ {operation.replace('_', ' ')}…")
        self._log(f"▶ {operation.replace('_', ' ')}: {os.path.basename(path)}")

        self._worker = CryptoWorker(
            operation=operation,
            password=self.password,
            path=path,
            cipher_config=copy.deepcopy(self._cipher_config),
            mode=mode,
            permission_code=perm_code,
            remove_original=self._rm_orig.isChecked(),
            remove_encrypted=self._rm_enc.isChecked(),
        )
        self._worker.progress.connect(self.progress.setValue)
        self._worker.finished.connect(
            lambda out, m: self._on_done(out, m, operation, path, perm_code)
        )
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, output: str, meta: dict, op: str, orig: str,
                 perm_code: Optional[str]) -> None:
        self.progress.setValue(100)
        self._refresh_permissions()
        save_history_entry(op, orig, meta.get("mode", "?"), success=True)

        chain = meta.get("cipher_chain", [])
        chain_str = " → ".join(CIPHER_INFO.get(c, {}).get("label", c) for c in chain)
        msg = f"Готово!\n\n📂 {output}"
        if chain_str:
            msg += f"\n\n🔗 {chain_str}"
        if perm_code and op.startswith("encrypt"):
            QApplication.clipboard().setText(perm_code)
            msg += f"\n\n🎫 Код:\n{perm_code}\n(скопирован)"

        self._log(f"✅ {os.path.basename(output)}  [{chain_str}]")
        self._set_status("Готово")
        QMessageBox.information(self, "Успех", msg)

    def _on_error(self, err: str) -> None:
        self.progress.setValue(0)
        self._set_status("Ошибка")
        self._log(f"❌ {err}")
        QMessageBox.critical(self, "Ошибка", err)
