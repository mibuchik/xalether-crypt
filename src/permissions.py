#!/usr/bin/env python3
"""Система разрешений: генерация одноразовых кодов, проверка, учёт использований."""

import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

PERMISSIONS_FILE = os.path.expanduser("~/.xalether_permissions.json")


def generate_permission_code() -> str:
    """Генерирует уникальный код вида XAL-XXXX-XXXX-XXXX."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = ''.join(secrets.choice(chars) for _ in range(12))
    return f"XAL-{code[:4]}-{code[4:8]}-{code[8:12]}"


def load_permissions() -> Dict[str, dict]:
    """Загружает все коды разрешений из файла."""
    if os.path.exists(PERMISSIONS_FILE):
        try:
            with open(PERMISSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_permissions(perms: Dict[str, dict]) -> None:
    """Сохраняет коды разрешений."""
    with open(PERMISSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(perms, f, indent=2, ensure_ascii=False)


def create_permission(
    code: str,
    max_uses: int = 1,
    hours_valid: int = 24,
    hwid: Optional[str] = None,
) -> None:
    """Создаёт новый код разрешения."""
    perms = load_permissions()
    perms[code] = {
        "created": datetime.now().isoformat(),
        "expires": (datetime.now() + timedelta(hours=hours_valid)).isoformat(),
        "max_uses": max_uses,
        "used": 0,
        "used_by": [],
        "hwid": hwid,
    }
    save_permissions(perms)


def use_permission(code: str, hwid: str) -> bool:
    """
    Использует код разрешения.
    Возвращает True при успехе, False при ошибке/истечении.
    """
    perms = load_permissions()
    if code not in perms:
        return False

    perm = perms[code]
    expires = datetime.fromisoformat(perm["expires"])

    if datetime.now() > expires:
        del perms[code]
        save_permissions(perms)
        return False
    if perm.get("hwid") and perm["hwid"] != hwid:
        return False
    if perm["used"] >= perm["max_uses"]:
        return False

    perm["used"] += 1
    perm["used_by"].append({"hwid": hwid, "time": datetime.now().isoformat()})

    if perm["used"] >= perm["max_uses"]:
        del perms[code]
    else:
        perms[code] = perm
    save_permissions(perms)
    return True


def get_active_permissions() -> Dict[str, dict]:
    """Возвращает только действующие (не истёкшие) коды."""
    perms = load_permissions()
    now = datetime.now()
    expired = [c for c, d in perms.items() if datetime.fromisoformat(d["expires"]) < now]
    for c in expired:
        del perms[c]
    if expired:
        save_permissions(perms)
    return perms
