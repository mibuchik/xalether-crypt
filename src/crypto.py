#!/usr/bin/env python3
"""
Каскадное шифрование XALETHER CRYPT v2.0.
Алгоритм: AES-256-GCM → ChaCha20-Poly1305
Деривация ключей: PBKDF2-SHA256, 500 000 итераций
"""

import os
import gc
import zlib
import json
import secrets
import hashlib
from typing import Callable, Optional, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from utils import get_hwid
from permissions import use_permission

SALT_SIZE = 16
CONFIG_FILE = os.path.expanduser("~/.xalether_crypt_config.json")

ProgressCallback = Optional[Callable[[int], None]]


# ─── Пароль ──────────────────────────────────────────────────────────────────

def save_password_hash(password: str) -> None:
    """Сохраняет хеш мастер-пароля (PBKDF2-SHA256, 200 000 итераций)."""
    salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000, 32)
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"salt": salt.hex(), "hash": h.hex()}, f)


def verify_password(password: str) -> bool:
    """Проверяет мастер-пароль по сохранённому хешу."""
    if not os.path.exists(CONFIG_FILE):
        return False
    with open(CONFIG_FILE, 'r') as f:
        cfg = json.load(f)
    salt = bytes.fromhex(cfg["salt"])
    stored = bytes.fromhex(cfg["hash"])
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000, 32)
    return h == stored


def is_first_run() -> bool:
    """True, если конфиг-файл ещё не создан."""
    return not os.path.exists(CONFIG_FILE)


# ─── Шифратор ─────────────────────────────────────────────────────────────────

class XaletherChaos:
    """
    Каскадный шифратор файлов.

    Порядок шифрования:
      1. zlib-сжатие
      2. Паддинг до 16 байт
      3. AES-256-GCM (с AAD 'XALETHER_CRYPT_V2')
      4. ChaCha20-Poly1305 (с AAD 'XALETHER_CRYPT_V2')
      5. Добавление случайного шума в начало (16-79 байт)
    """

    def __init__(self, password: str, salt: Optional[bytes] = None) -> None:
        self.salt = salt if salt else secrets.token_bytes(SALT_SIZE)
        master = hashlib.pbkdf2_hmac('sha256', password.encode(), self.salt, 500_000, 64)
        self.aes_key: bytes = master[0:32]
        self.chacha_key: bytes = master[32:64]

    def __del__(self) -> None:
        if hasattr(self, 'aes_key'):
            self.aes_key = b'\x00' * 32
        if hasattr(self, 'chacha_key'):
            self.chacha_key = b'\x00' * 32
        gc.collect()

    # ── внутренние хелперы ───────────────────────────────────────────────────

    @staticmethod
    def _pad(data: bytes, block_size: int = 16) -> bytes:
        pad_len = block_size - (len(data) % block_size)
        return data + bytes([pad_len] * pad_len)

    @staticmethod
    def _unpad(data: bytes) -> bytes:
        pad_len = data[-1]
        return data if pad_len > 16 else data[:-pad_len]

    # ── шифрование / расшифровка ─────────────────────────────────────────────

    def encrypt(
        self,
        data: bytes,
        mode: str = "transfer",
        permission_code: Optional[str] = None,
        content_type: str = "file",
    ) -> Tuple[bytes, dict]:
        """Шифрует сырые байты, возвращает (шифртекст, метаданные)."""
        data = zlib.compress(data, 9)

        # Слой 1: AES-256-GCM
        iv_aes = secrets.token_bytes(12)
        enc = Cipher(
            algorithms.AES(self.aes_key), modes.GCM(iv_aes), backend=default_backend()
        ).encryptor()
        enc.authenticate_additional_data(b'XALETHER_CRYPT_V2')
        data = enc.update(self._pad(data)) + enc.finalize()
        data = iv_aes + enc.tag + data

        # Слой 2: ChaCha20-Poly1305
        iv_cc = secrets.token_bytes(12)
        chacha = ChaCha20Poly1305(self.chacha_key)
        data = iv_cc + chacha.encrypt(iv_cc, data, b'XALETHER_CRYPT_V2')

        # Случайный шум в начале (затрудняет анализ структуры файла)
        noise = secrets.token_bytes(secrets.randbelow(64) + 16)

        metadata = {
            "version": "2.0",
            "mode": mode,
            "content_type": content_type,
            "hwid": get_hwid() if mode == "personal" else None,
            "permission_code": permission_code if mode == "permission" else None,
        }
        return noise + data, metadata

    def decrypt(self, data: bytes) -> bytes:
        """
        Расшифровывает шифртекст.
        Скользящим окном ищет начало ChaCha20-nonce (пропускает шум).
        """
        inner: Optional[bytes] = None
        for pos in range(min(96, len(data) - 12)):
            try:
                iv_cc = data[pos:pos + 12]
                inner = ChaCha20Poly1305(self.chacha_key).decrypt(
                    iv_cc, data[pos + 12:], b'XALETHER_CRYPT_V2'
                )
                break
            except Exception:
                continue

        if inner is None:
            raise ValueError("Неверный пароль или файл повреждён")

        iv_aes = inner[:12]
        tag = inner[12:28]
        ciphertext = inner[28:]
        dec = Cipher(
            algorithms.AES(self.aes_key), modes.GCM(iv_aes, tag), backend=default_backend()
        ).decryptor()
        dec.authenticate_additional_data(b'XALETHER_CRYPT_V2')
        return zlib.decompress(self._unpad(dec.update(ciphertext) + dec.finalize()))

    # ── файловые операции ────────────────────────────────────────────────────

    def encrypt_file(
        self,
        filepath: str,
        output: Optional[str] = None,
        mode: str = "transfer",
        permission_code: Optional[str] = None,
        remove_original: bool = False,
        content_type: str = "file",
        progress_cb: ProgressCallback = None,
    ) -> Tuple[str, dict]:
        """Шифрует файл и записывает результат в .xalether."""
        with open(filepath, 'rb') as f:
            data = f.read()
        if progress_cb:
            progress_cb(15)

        encrypted, metadata = self.encrypt(data, mode, permission_code, content_type)
        if progress_cb:
            progress_cb(75)

        if output is None:
            output = filepath + '.xalether'

        meta_json = json.dumps(metadata).encode()
        with open(output, 'wb') as f:
            f.write(len(meta_json).to_bytes(4, 'big'))
            f.write(meta_json)
            f.write(self.salt)
            f.write(encrypted)
        if progress_cb:
            progress_cb(92)

        if remove_original:
            os.remove(filepath)
        if progress_cb:
            progress_cb(100)

        return output, metadata

    def decrypt_file(
        self,
        filepath: str,
        password: str,
        permission_code: Optional[str] = None,
        output: Optional[str] = None,
        remove_encrypted: bool = False,
        progress_cb: ProgressCallback = None,
    ) -> Tuple[str, dict]:
        """Расшифровывает .xalether файл. Проверяет HWID и коды разрешений."""
        with open(filepath, 'rb') as f:
            meta_len = int.from_bytes(f.read(4), 'big')
            metadata = json.loads(f.read(meta_len).decode())
            salt = f.read(SALT_SIZE)
            encrypted = f.read()
        if progress_cb:
            progress_cb(15)

        mode = metadata.get("mode", "transfer")
        if mode == "personal" and metadata.get("hwid") != get_hwid():
            raise ValueError("Файл привязан к другому компьютеру")
        if mode == "permission":
            if not permission_code:
                raise ValueError("Требуется код разрешения")
            if not use_permission(permission_code, get_hwid()):
                raise ValueError("Неверный или просроченный код разрешения")
        if progress_cb:
            progress_cb(30)

        # Деривируем ключи из соли, хранящейся в файле
        decryptor = XaletherChaos(password, salt)
        decrypted = decryptor.decrypt(encrypted)
        if progress_cb:
            progress_cb(85)

        if output is None:
            output = filepath[:-9] if filepath.endswith('.xalether') else filepath + '.decrypted'

        with open(output, 'wb') as f:
            f.write(decrypted)

        if remove_encrypted:
            os.remove(filepath)
        if progress_cb:
            progress_cb(100)

        return output, metadata


def read_metadata(filepath: str) -> dict:
    """Читает метаданные из .xalether файла без расшифровки."""
    with open(filepath, 'rb') as f:
        meta_len = int.from_bytes(f.read(4), 'big')
        return json.loads(f.read(meta_len).decode())
