#!/usr/bin/env python3
"""
Интеграция XALETHER CRYPT с контекстным меню Windows.
Использует HKEY_CURRENT_USER\\Software\\Classes — не требует прав администратора.
"""

import os
import sys
from typing import Tuple

try:
    import winreg as _wr
    _OK = True
except ImportError:
    _OK = False  # не Windows

_HKCU   = _wr.HKEY_CURRENT_USER if _OK else None
_BASE   = r"Software\Classes"
_SHELLS = [r"*\shell", r"Directory\shell"]
_ENC    = "XaletherEncrypt"
_DEC    = "XaletherDecrypt"


def _py() -> str:
    return sys.executable


def _main() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")


def _cmd(action: str) -> str:
    return f'"{_py()}" "{_main()}" --{action} "%1"'


# ─── Публичный API ────────────────────────────────────────────────────────────

def is_installed() -> bool:
    if not _OK:
        return False
    try:
        key = _wr.OpenKey(_HKCU, rf"{_BASE}\*\shell\{_ENC}")
        _wr.CloseKey(key)
        return True
    except Exception:
        return False


def install() -> Tuple[bool, str]:
    if not _OK:
        return False, "winreg недоступен — только Windows"
    try:
        for shell in _SHELLS:
            for name, label, action in [
                (_ENC, "Зашифровать Xalether", "encrypt"),
                (_DEC, "Расшифровать Xalether", "decrypt"),
            ]:
                kp  = rf"{_BASE}\{shell}\{name}"
                key = _wr.CreateKey(_HKCU, kp)
                _wr.SetValueEx(key, "",     0, _wr.REG_SZ, label)
                _wr.SetValueEx(key, "Icon", 0, _wr.REG_SZ, _py())
                cmd = _wr.CreateKey(key, "command")
                _wr.SetValueEx(cmd, "", 0, _wr.REG_SZ, _cmd(action))
                _wr.CloseKey(cmd)
                _wr.CloseKey(key)
        return True, "Контекстное меню успешно добавлено"
    except Exception as e:
        return False, f"Ошибка регистрации: {e}"


def uninstall() -> Tuple[bool, str]:
    if not _OK:
        return False, "winreg недоступен — только Windows"
    try:
        for shell in _SHELLS:
            for name in [_ENC, _DEC]:
                base = rf"{_BASE}\{shell}\{name}"
                for sub in ["command", ""]:
                    try:
                        _wr.DeleteKey(_HKCU, rf"{base}\{sub}" if sub else base)
                    except FileNotFoundError:
                        pass
        return True, "Контекстное меню удалено"
    except Exception as e:
        return False, f"Ошибка удаления: {e}"


def generate_reg_files(out_dir: str) -> Tuple[str, str]:
    """Создаёт install/uninstall .reg файлы с текущими путями Python и main.py."""
    py_esc   = _py().replace("\\", "\\\\")
    main_esc = _main().replace("\\", "\\\\")
    enc_val  = f'\\"{py_esc}\\" \\"{main_esc}\\" --encrypt \\"%1\\"'
    dec_val  = f'\\"{py_esc}\\" \\"{main_esc}\\" --decrypt \\"%1\\"'

    inst_lines = ["Windows Registry Editor Version 5.00", ""]
    unin_lines = ["Windows Registry Editor Version 5.00", ""]

    for shell in [r"*\shell", r"Directory\shell"]:
        inst_lines += [
            f"[HKEY_CURRENT_USER\\Software\\Classes\\{shell}\\{_ENC}]",
            f'@="Зашифровать Xalether"',
            f'"Icon"="{py_esc}"',
            "",
            f"[HKEY_CURRENT_USER\\Software\\Classes\\{shell}\\{_ENC}\\command]",
            f'@="{enc_val}"',
            "",
            f"[HKEY_CURRENT_USER\\Software\\Classes\\{shell}\\{_DEC}]",
            f'@="Расшифровать Xalether"',
            f'"Icon"="{py_esc}"',
            "",
            f"[HKEY_CURRENT_USER\\Software\\Classes\\{shell}\\{_DEC}\\command]",
            f'@="{dec_val}"',
            "",
        ]
        unin_lines += [
            f"[-HKEY_CURRENT_USER\\Software\\Classes\\{shell}\\{_ENC}]",
            f"[-HKEY_CURRENT_USER\\Software\\Classes\\{shell}\\{_DEC}]",
            "",
        ]

    inst_path = os.path.join(out_dir, "install_context_menu.reg")
    unin_path = os.path.join(out_dir, "uninstall_context_menu.reg")
    for path, lines in [(inst_path, inst_lines), (unin_path, unin_lines)]:
        with open(path, "w", encoding="utf-16") as f:
            f.write("\r\n".join(lines))
    return inst_path, unin_path
