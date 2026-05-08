#!/usr/bin/env python3
"""Утилиты: ZIP-архивация, история, генератор паролей, настройки."""

import os
import json
import platform
import uuid
import zipfile
import tempfile
import secrets
import string
from datetime import datetime
from typing import List, Optional

HISTORY_FILE = os.path.expanduser("~/.xalether_history.json")
SETTINGS_FILE = os.path.expanduser("~/.xalether_settings.json")


def get_hwid() -> str:
    """Уникальный идентификатор компьютера."""
    try:
        return str(uuid.getnode()) + platform.processor()
    except Exception:
        return "UNKNOWN_HWID"


def folder_to_zip(folder_path: str) -> str:
    """Упаковывает папку во временный ZIP и возвращает путь."""
    zip_path = tempfile.mktemp(suffix='.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                arc_name = os.path.relpath(full_path, folder_path)
                zf.write(full_path, arc_name)
    return zip_path


def zip_to_folder(zip_path: str, output_folder: str) -> None:
    """Распаковывает ZIP в папку."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(output_folder)


def load_history() -> List[dict]:
    """Загружает историю операций."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history_entry(operation: str, filename: str, mode: str, success: bool) -> None:
    """Добавляет запись в историю (не более 100 последних)."""
    history = load_history()
    history.append({
        "time": datetime.now().isoformat(),
        "operation": operation,
        "filename": os.path.basename(filename),
        "mode": mode,
        "success": success,
    })
    history = history[-100:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_settings() -> dict:
    """Загружает настройки с дефолтами."""
    defaults: dict = {
        "remove_original": True,
        "remove_encrypted": True,
        "default_mode": "transfer",
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults


def save_settings(settings: dict) -> None:
    """Сохраняет настройки."""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
) -> str:
    """Генерирует криптографически стойкий пароль."""
    pool = ""
    required: List[str] = []
    if use_upper:
        pool += string.ascii_uppercase
        required.append(secrets.choice(string.ascii_uppercase))
    if use_lower:
        pool += string.ascii_lowercase
        required.append(secrets.choice(string.ascii_lowercase))
    if use_digits:
        pool += string.digits
        required.append(secrets.choice(string.digits))
    if use_special:
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        pool += special
        required.append(secrets.choice(special))
    if not pool:
        pool = string.ascii_letters + string.digits

    filler = [secrets.choice(pool) for _ in range(max(0, length - len(required)))]
    password = required + filler
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)
