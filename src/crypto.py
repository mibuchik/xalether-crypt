#!/usr/bin/env python3
"""
XALETHER CRYPT v2.1 — Модульная каскадная криптосистема.

Шифры: AES-256-GCM · ChaCha20-Poly1305 · AES-256-SIV
       AES-256-CBC · AES-256-CTR · Camellia-256-CBC

KDF:   PBKDF2-SHA256 · PBKDF2-SHA512 · scrypt · Argon2id

Сжатие: none · zlib-1 · zlib-9 · bz2 · lzma
"""

import os, gc, zlib, bz2, lzma, json, hashlib, secrets, tempfile
import hmac as _hmac
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305, AESSIV
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt



from utils import get_hwid
from permissions import use_permission

# ─── Константы ───────────────────────────────────────────────────────────────

SALT_SIZE  = 16
KEY_BLOCK  = 64          # байт ключевого материала на один слой
CHUNK_SIZE = 32 * 1024 * 1024   # 32 МБ — размер блока потокового шифрования
CONFIG_FILE = os.path.expanduser("~/.xalether_crypt_config.json")
AAD = b'XALETHER_CRYPT_V2'

ProgressCallback = Optional[Callable[[int], None]]


# ─── Паддинг ─────────────────────────────────────────────────────────────────

def _pad(data: bytes, block: int = 16) -> bytes:
    n = block - (len(data) % block)
    return data + bytes([n] * n)

def _unpad(data: bytes, block: int = 16) -> bytes:
    n = data[-1]
    return data[:-n] if (1 <= n <= block and data[-n:] == bytes([n] * n)) else data


# ─── Абстрактный слой шифрования ─────────────────────────────────────────────

class CipherLayer(ABC):
    id: str
    label: str
    description: str
    security: str   # Low / Medium / High / Overkill

    @abstractmethod
    def encrypt(self, key_block: bytes, data: bytes) -> bytes: ...

    @abstractmethod
    def decrypt(self, key_block: bytes, data: bytes) -> bytes: ...


# ─── Реализации шифров ────────────────────────────────────────────────────────

class AesGcmLayer(CipherLayer):
    id = "aes-gcm";   label = "AES-256-GCM"
    description = "NIST/FIPS стандарт · аппаратное ускорение (AES-NI) · 128-бит тег"
    security = "High"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        n = os.urandom(12)
        return n + AESGCM(kb[:32]).encrypt(n, data, AAD)

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        return AESGCM(kb[:32]).decrypt(data[:12], data[12:], AAD)


class ChaCha20Layer(CipherLayer):
    id = "chacha20";  label = "ChaCha20-Poly1305"
    description = "IETF RFC 8439 · быстрый на ARM/мобильных без AES-NI · 128-бит тег"
    security = "High"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        n = os.urandom(12)
        return n + ChaCha20Poly1305(kb[:32]).encrypt(n, data, AAD)

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        return ChaCha20Poly1305(kb[:32]).decrypt(data[:12], data[12:], AAD)


class AesSivLayer(CipherLayer):
    id = "aes-siv";   label = "AES-256-SIV"
    description = "Детерминированное AEAD · устойчиво к повтору nonce · двойной AES"
    security = "High"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        return AESSIV(kb[:64]).encrypt(data, [AAD])   # нет nonce, тег 16 байт

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        return AESSIV(kb[:64]).decrypt(data, [AAD])


class AesCbcLayer(CipherLayer):
    id = "aes-cbc";   label = "AES-256-CBC + HMAC-SHA256"
    description = "Классический блочный режим · Encrypt-then-MAC · FIPS 140-2 совместим"
    security = "Medium"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        iv = os.urandom(16)
        enc = Cipher(algorithms.AES(ek), modes.CBC(iv), backend=default_backend()).encryptor()
        ct  = enc.update(_pad(data)) + enc.finalize()
        tag = _hmac.new(mk, iv + ct + AAD, hashlib.sha256).digest()
        return iv + tag + ct                 # 16 + 32 + padded

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        iv, tag, ct = data[:16], data[16:48], data[48:]
        exp = _hmac.new(mk, iv + ct + AAD, hashlib.sha256).digest()
        if not _hmac.compare_digest(exp, tag):
            raise ValueError("AES-CBC: ошибка аутентификации")
        dec = Cipher(algorithms.AES(ek), modes.CBC(iv), backend=default_backend()).decryptor()
        return _unpad(dec.update(ct) + dec.finalize())


class AesCtrLayer(CipherLayer):
    id = "aes-ctr";   label = "AES-256-CTR + HMAC-SHA3-256"
    description = "Потоковый режим · без паддинга · SHA-3 аутентификация"
    security = "Medium"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        n = os.urandom(16)
        enc = Cipher(algorithms.AES(ek), modes.CTR(n), backend=default_backend()).encryptor()
        ct  = enc.update(data) + enc.finalize()
        tag = hashlib.sha3_256(mk + n + ct + AAD).digest()
        return n + tag + ct                  # 16 + 32 + len(data)

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        n, tag, ct = data[:16], data[16:48], data[48:]
        exp = hashlib.sha3_256(mk + n + ct + AAD).digest()
        if not _hmac.compare_digest(exp, tag):
            raise ValueError("AES-CTR: ошибка аутентификации")
        dec = Cipher(algorithms.AES(ek), modes.CTR(n), backend=default_backend()).decryptor()
        return dec.update(ct) + dec.finalize()


class CamelliaCbcLayer(CipherLayer):
    id = "camellia";  label = "Camellia-256-CBC + HMAC-SHA3-256"
    description = "Японский стандарт (NTT/Mitsubishi) · ISO/IEC 18033-3 · другое семейство алгоритмов"
    security = "High"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        iv = os.urandom(16)
        enc = Cipher(algorithms.Camellia(ek), modes.CBC(iv), backend=default_backend()).encryptor()
        ct  = enc.update(_pad(data)) + enc.finalize()
        tag = hashlib.sha3_256(mk + iv + ct + AAD).digest()
        return iv + tag + ct

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        iv, tag, ct = data[:16], data[16:48], data[48:]
        exp = hashlib.sha3_256(mk + iv + ct + AAD).digest()
        if not _hmac.compare_digest(exp, tag):
            raise ValueError("Camellia: ошибка аутентификации")
        dec = Cipher(algorithms.Camellia(ek), modes.CBC(iv), backend=default_backend()).decryptor()
        return _unpad(dec.update(ct) + dec.finalize())


class XChaCha20Layer(CipherLayer):
    """XChaCha20: субключ из первых 12 байт нонса, остаток — nonce для ChaCha20."""
    id = "xchacha20"; label = "XChaCha20 + HMAC-SHA3-512"
    description = "Расширенный нонс 24 байта · HMAC-SHA3-512 · меньше коллизий nonce"
    security = "High"

    @staticmethod
    def _derive_subkey(key: bytes, seed12: bytes) -> bytes:
        return hashlib.sha3_256(key + seed12 + b"xchacha20_subkey").digest()

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        # nonce24 = [12 bytes subkey seed] + [12 bytes ChaCha20 nonce]
        nonce24 = os.urandom(24)
        subkey  = self._derive_subkey(ek, nonce24[:12])
        ct = ChaCha20Poly1305(subkey).encrypt(nonce24[12:], data, AAD)
        tag = hashlib.sha3_512(mk + nonce24 + ct + AAD).digest()
        return nonce24 + tag + ct            # 24 + 64 + ciphertext

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        nonce24, tag, ct = data[:24], data[24:88], data[88:]
        exp = hashlib.sha3_512(mk + nonce24 + ct + AAD).digest()
        if not _hmac.compare_digest(exp, tag):
            raise ValueError("XChaCha20: ошибка аутентификации")
        subkey = self._derive_subkey(ek, nonce24[:12])
        return ChaCha20Poly1305(subkey).decrypt(nonce24[12:], ct, AAD)


class Aes256CfbLayer(CipherLayer):
    id = "aes-cfb";   label = "AES-256-CFB + HMAC-SHA256"
    description = "Самосинхронизирующийся потоковый режим · устойчив к потере блоков"
    security = "Medium"

    def encrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        iv = os.urandom(16)
        enc = Cipher(algorithms.AES(ek), modes.CFB(iv), backend=default_backend()).encryptor()
        ct  = enc.update(data) + enc.finalize()
        tag = _hmac.new(mk, iv + ct + AAD, hashlib.sha256).digest()
        return iv + tag + ct

    def decrypt(self, kb: bytes, data: bytes) -> bytes:
        ek, mk = kb[:32], kb[32:64]
        iv, tag, ct = data[:16], data[16:48], data[48:]
        exp = _hmac.new(mk, iv + ct + AAD, hashlib.sha256).digest()
        if not _hmac.compare_digest(exp, tag):
            raise ValueError("AES-CFB: ошибка аутентификации")
        dec = Cipher(algorithms.AES(ek), modes.CFB(iv), backend=default_backend()).decryptor()
        return dec.update(ct) + dec.finalize()





# ─── Реестр ───────────────────────────────────────────────────────────────────

CIPHER_REGISTRY: Dict[str, CipherLayer] = {
    c.id: c for c in [
        AesGcmLayer(), ChaCha20Layer(), AesSivLayer(),
        AesCbcLayer(), AesCtrLayer(), Aes256CfbLayer(),
        CamelliaCbcLayer(), XChaCha20Layer(),
    ]
}

CIPHER_INFO: Dict[str, dict] = {
    cid: {"label": c.label, "description": c.description, "security": c.security}
    for cid, c in CIPHER_REGISTRY.items()
}


# ─── KDF ──────────────────────────────────────────────────────────────────────

def derive_key(password: str, salt: bytes, length: int, kdf_cfg: dict) -> bytes:
    """Выводит ключевой материал из пароля. Поддерживает 4 алгоритма."""
    ktype = kdf_cfg.get("type", "pbkdf2-sha256")

    if ktype == "pbkdf2-sha256":
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt,
                                   kdf_cfg.get("iterations", 500_000), length)
    if ktype == "pbkdf2-sha512":
        return hashlib.pbkdf2_hmac("sha512", password.encode(), salt,
                                   kdf_cfg.get("iterations", 300_000), length)
    if ktype == "scrypt":
        kdf = Scrypt(salt=salt, length=length,
                     n=kdf_cfg.get("n", 65536), r=8, p=1,
                     backend=default_backend())
        return kdf.derive(password.encode())
    if ktype == "argon2id":
        try:
            from argon2.low_level import hash_secret_raw, Type
            return hash_secret_raw(
                password.encode(), salt,
                time_cost=kdf_cfg.get("time_cost", 3),
                memory_cost=kdf_cfg.get("memory_cost", 65536),
                parallelism=kdf_cfg.get("parallelism", 4),
                hash_len=length,
                type=Type.ID,
            )
        except ImportError:
            # Fallback если argon2-cffi не установлен
            kdf = Scrypt(salt=salt, length=length, n=65536, r=8, p=1, backend=default_backend())
            return kdf.derive(password.encode())

    raise ValueError(f"Неизвестный KDF: {ktype}")


KDF_INFO = {
    "pbkdf2-sha256": {
        "label": "PBKDF2-SHA256",
        "description": "NIST-стандарт · настраиваемые итерации · быстрый",
        "has_iterations": True,
    },
    "pbkdf2-sha512": {
        "label": "PBKDF2-SHA512",
        "description": "SHA-512 хеш · тяжелее SHA-256 · хорошо на 64-бит CPU",
        "has_iterations": True,
    },
    "scrypt": {
        "label": "scrypt",
        "description": "Memory-hard · 64 МБ ОЗУ · сложно для ASIC/GPU атак",
        "has_iterations": False,
    },
    "argon2id": {
        "label": "Argon2id ★ (лучший)",
        "description": "Password Hashing Competition winner · защита от GPU и side-channel",
        "has_iterations": False,
    },
}


# ─── Сжатие ───────────────────────────────────────────────────────────────────

def compress_data(data: bytes, method: str) -> bytes:
    if method == "none":   return data
    if method == "zlib-1": return zlib.compress(data, 1)
    if method == "zlib-9": return zlib.compress(data, 9)
    if method == "bz2":    return bz2.compress(data, 9)
    if method == "lzma":   return lzma.compress(data, preset=6)
    return zlib.compress(data, 9)

def decompress_data(data: bytes, method: str) -> bytes:
    if method == "none":              return data
    if method in ("zlib-1","zlib-9"): return zlib.decompress(data)
    if method == "bz2":               return bz2.decompress(data)
    if method == "lzma":              return lzma.decompress(data)
    return zlib.decompress(data)

COMPRESS_INFO = {
    "none":   {"label": "Без сжатия",    "description": "Максимальная скорость"},
    "zlib-1": {"label": "zlib (быстрый)","description": "Быстрое сжатие ~300 МБ/с"},
    "zlib-9": {"label": "zlib (макс)",   "description": "Лучший уровень zlib"},
    "bz2":    {"label": "bz2",           "description": "Лучше zlib, медленнее"},
    "lzma":   {"label": "LZMA",          "description": "Максимальное сжатие, самый медленный"},
}


# ─── Пресеты ──────────────────────────────────────────────────────────────────

PRESETS = {
    "fast": {
        "label": "Быстрый", "icon": "⚡",
        "cipher_chain": ["aes-gcm"],
        "kdf": {"type": "pbkdf2-sha256", "iterations": 100_000},
        "compression": "zlib-1",
        "description": "AES-256-GCM · PBKDF2-100k · zlib-fast",
    },
    "standard": {
        "label": "Стандартный", "icon": "🔒",
        "cipher_chain": ["aes-gcm", "chacha20"],
        "kdf": {"type": "pbkdf2-sha256", "iterations": 500_000},
        "compression": "zlib-9",
        "description": "AES-GCM → ChaCha20 · PBKDF2-500k · zlib",
    },
    "paranoid": {
        "label": "Параноид", "icon": "🛡",
        "cipher_chain": ["aes-gcm", "chacha20", "camellia"],
        "kdf": {"type": "scrypt", "n": 65536},
        "compression": "bz2",
        "description": "AES → ChaCha20 → Camellia · scrypt · bz2",
    },
    "ultra": {
        "label": "Ультра", "icon": "☢",
        "cipher_chain": ["aes-gcm", "chacha20", "camellia", "aes-siv"],
        "kdf": {"type": "argon2id", "time_cost": 4, "memory_cost": 131072, "parallelism": 4},
        "compression": "lzma",
        "description": "4 слоя · Argon2id · LZMA",
    },
    "asymmetric": {
        "label": "Хаос", "icon": "🌀",
        "cipher_chain": ["aes-cbc", "xchacha20", "aes-ctr", "camellia", "chacha20"],
        "kdf": {"type": "argon2id", "time_cost": 5, "memory_cost": 262144, "parallelism": 8},
        "compression": "lzma",
        "description": "5 разных слоёв · Argon2id-256MB · LZMA",
    },
}

DEFAULT_CONFIG = {
    "cipher_chain": ["aes-gcm", "chacha20"],
    "kdf": {"type": "pbkdf2-sha256", "iterations": 500_000},
    "compression": "zlib-9",
}


# ─── Пароль ───────────────────────────────────────────────────────────────────

def save_password_hash(password: str) -> None:
    salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000, 32)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"salt": salt.hex(), "hash": h.hex()}, f)

def verify_password(password: str) -> bool:
    if not os.path.exists(CONFIG_FILE):
        return False
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    salt   = bytes.fromhex(cfg["salt"])
    stored = bytes.fromhex(cfg["hash"])
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000, 32)
    return _hmac.compare_digest(h, stored)

def is_first_run() -> bool:
    return not os.path.exists(CONFIG_FILE)

def read_metadata(filepath: str) -> dict:
    with open(filepath, "rb") as f:
        meta_len = int.from_bytes(f.read(4), "big")
        return json.loads(f.read(meta_len).decode())


# ─── Обратная совместимость (v2.0) ────────────────────────────────────────────

def _decrypt_v2_legacy(password: str, salt: bytes, data: bytes) -> bytes:
    """Расшифровывает старые файлы формата v2.0."""
    master = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 500_000, 64)
    aes_key, chacha_key = master[:32], master[32:64]

    inner: Optional[bytes] = None
    for pos in range(min(96, len(data) - 28)):
        try:
            nonce = data[pos:pos + 12]
            inner = ChaCha20Poly1305(chacha_key).decrypt(nonce, data[pos + 12:], AAD)
            break
        except Exception:
            continue
    if inner is None:
        raise ValueError("v2.0: невозможно расшифровать")

    iv_aes, tag, ct = inner[:12], inner[12:28], inner[28:]
    dec = Cipher(algorithms.AES(aes_key), modes.GCM(iv_aes, tag), backend=default_backend()).decryptor()
    dec.authenticate_additional_data(AAD)
    padded = dec.update(ct) + dec.finalize()
    pad_len = padded[-1]
    raw = padded[:-pad_len] if 1 <= pad_len <= 16 else padded
    return zlib.decompress(raw)


# ─── Главный класс ────────────────────────────────────────────────────────────

class XaletherChaos:
    """
    Каскадный шифратор файлов v2.1.

    Порядок шифрования:
      1. compress(data)
      2. layer[0].encrypt  (innermost)
      3. layer[1].encrypt
         ...
      N. layer[N-1].encrypt  (outermost)
      noise prepend

    Расшифровка — строго наоборот.
    """

    def __init__(
        self,
        password: str,
        salt: Optional[bytes] = None,
        config: Optional[dict] = None,
    ) -> None:
        self.config = config or DEFAULT_CONFIG.copy()
        self.salt   = salt if salt else secrets.token_bytes(SALT_SIZE)

        chain = self.config["cipher_chain"]
        master = derive_key(
            password, self.salt,
            KEY_BLOCK * max(1, len(chain)),
            self.config.get("kdf", {"type": "pbkdf2-sha256", "iterations": 500_000}),
        )
        self._keys: List[bytes] = [
            master[i * KEY_BLOCK:(i + 1) * KEY_BLOCK] for i in range(len(chain))
        ]

    def __del__(self) -> None:
        if hasattr(self, "_keys"):
            self._keys = []
        gc.collect()

    # ── потоковые чанки ───────────────────────────────────────────────────────

    def _encrypt_chunk(self, chunk_data: bytes, compression: str) -> bytes:
        """Сжимает и каскадно шифрует один чанк. Каждый вызов даёт случайный nonce."""
        data = compress_data(chunk_data, compression)
        chain = self.config["cipher_chain"]
        for i, cid in enumerate(chain):
            data = CIPHER_REGISTRY[cid].encrypt(self._keys[i], data)
        return data

    def _decrypt_chunk(self, chunk_data: bytes, compression: str) -> bytes:
        """Каскадно расшифровывает и разжимает один чанк."""
        data = chunk_data
        chain = self.config["cipher_chain"]
        for i in range(len(chain) - 1, -1, -1):
            layer = CIPHER_REGISTRY.get(chain[i])
            if layer is None:
                raise ValueError(f"Неизвестный шифр: {chain[i]}")
            data = layer.decrypt(self._keys[i], data)
        return decompress_data(data, compression)

    # ── шифрование ────────────────────────────────────────────────────────────

    def encrypt(
        self,
        data: bytes,
        mode: str = "transfer",
        permission_code: Optional[str] = None,
        content_type: str = "file",
    ) -> Tuple[bytes, dict]:
        chain = self.config["cipher_chain"]
        compression = self.config.get("compression", "zlib-9")

        data = compress_data(data, compression)
        for i, cid in enumerate(chain):
            data = CIPHER_REGISTRY[cid].encrypt(self._keys[i], data)

        noise_size = secrets.randbelow(64) + 16
        noise = secrets.token_bytes(noise_size)

        metadata = {
            "version": "2.1",
            "mode": mode,
            "content_type": content_type,
            "cipher_chain": chain,
            "kdf": self.config.get("kdf"),
            "compression": compression,
            "noise_size": noise_size,
            "hwid": get_hwid() if mode == "personal" else None,
            "permission_code": permission_code if mode == "permission" else None,
        }
        return noise + data, metadata

    def decrypt(self, data: bytes, metadata: dict) -> bytes:
        noise_size = metadata.get("noise_size", 0)
        chain      = metadata["cipher_chain"]
        compression= metadata.get("compression", "zlib-9")

        data = data[noise_size:]
        for i in range(len(chain) - 1, -1, -1):
            layer = CIPHER_REGISTRY.get(chain[i])
            if layer is None:
                raise ValueError(f"Неизвестный шифр: {chain[i]}")
            data = layer.decrypt(self._keys[i], data)

        return decompress_data(data, compression)

    # ── файловые операции ─────────────────────────────────────────────────────

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
        chain = self.config["cipher_chain"]
        compression = self.config.get("compression", "zlib-9")

        file_size = os.path.getsize(filepath)
        num_chunks = max(1, (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE) if file_size > 0 else 1

        metadata = {
            "version": "2.1",
            "chunked": True,
            "num_chunks": num_chunks,
            "mode": mode,
            "content_type": content_type,
            "cipher_chain": chain,
            "kdf": self.config.get("kdf"),
            "compression": compression,
            "noise_size": 0,
            "hwid": get_hwid() if mode == "personal" else None,
            "permission_code": permission_code if mode == "permission" else None,
        }

        if output is None:
            output = filepath + ".xalether"

        # Первый проход: SHA-256 оригинального файла
        sha_hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                blk = f.read(CHUNK_SIZE)
                if not blk:
                    break
                sha_hasher.update(blk)
        metadata["sha256"] = sha_hasher.hexdigest()

        meta_json = json.dumps(metadata).encode()

        with open(filepath, "rb") as fin, open(output, "wb") as fout:
            fout.write(len(meta_json).to_bytes(4, "big"))
            fout.write(meta_json)
            fout.write(self.salt)

            bytes_done = 0
            chunk_idx = 0
            while True:
                chunk = fin.read(CHUNK_SIZE)
                if not chunk:
                    break
                enc_chunk = self._encrypt_chunk(chunk, compression)
                fout.write(len(enc_chunk).to_bytes(4, "big"))
                fout.write(enc_chunk)
                bytes_done += len(chunk)
                chunk_idx += 1
                if progress_cb and file_size > 0:
                    progress_cb(int(bytes_done / file_size * 95))

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
        # Read only the header — don't load the whole file into RAM
        with open(filepath, "rb") as f:
            meta_len_int = int.from_bytes(f.read(4), "big")
            metadata     = json.loads(f.read(meta_len_int).decode())
            salt         = f.read(SALT_SIZE)
        header_end = 4 + meta_len_int + SALT_SIZE
        if progress_cb: progress_cb(10)

        mode = metadata.get("mode", "transfer")
        if mode == "personal" and metadata.get("hwid") != get_hwid():
            raise ValueError("Файл привязан к другому компьютеру")
        if mode == "permission":
            if not permission_code:
                raise ValueError("Требуется код разрешения")
            if not use_permission(permission_code, get_hwid()):
                raise ValueError("Неверный или просроченный код разрешения")
        if progress_cb: progress_cb(20)

        if output is None:
            output = filepath[:-9] if filepath.endswith(".xalether") else filepath + ".decrypted"

        version = metadata.get("version", "2.0")

        if version == "2.0":
            # Старый формат — читаем целиком (файлы небольшие)
            with open(filepath, "rb") as f:
                f.seek(header_end)
                encrypted = f.read()
            decrypted = _decrypt_v2_legacy(password, salt, encrypted)
            with open(output, "wb") as f:
                f.write(decrypted)

        elif metadata.get("chunked"):
            # Новый потоковый формат — читаем по чанкам
            config = {
                "cipher_chain": metadata["cipher_chain"],
                "kdf":          metadata["kdf"],
                "compression":  metadata.get("compression", "zlib-9"),
            }
            dec = XaletherChaos(password, salt, config)
            if progress_cb: progress_cb(30)

            compression = metadata.get("compression", "zlib-9")
            num_chunks  = metadata.get("num_chunks", 0)
            noise_size  = metadata.get("noise_size", 0)

            verify_hash = metadata.get("sha256")
            sha_hasher  = hashlib.sha256() if verify_hash else None

            with open(filepath, "rb") as fin, open(output, "wb") as fout:
                fin.seek(header_end + noise_size)
                for i in range(num_chunks):
                    sz_raw = fin.read(4)
                    if len(sz_raw) < 4:
                        raise ValueError(f"Неожиданный конец файла (чанк {i}/{num_chunks})")
                    chunk_size = int.from_bytes(sz_raw, "big")
                    enc_chunk  = fin.read(chunk_size)
                    dec_chunk  = dec._decrypt_chunk(enc_chunk, compression)
                    if sha_hasher:
                        sha_hasher.update(dec_chunk)
                    fout.write(dec_chunk)
                    if progress_cb and num_chunks > 0:
                        progress_cb(30 + int((i + 1) / num_chunks * 60))

            if sha_hasher and sha_hasher.hexdigest() != verify_hash:
                try:
                    os.remove(output)
                except Exception:
                    pass
                raise ValueError(
                    "⚠️ Файл повреждён или изменён!\n"
                    f"Ожидаемый SHA-256:  {verify_hash[:32]}…\n"
                    f"Полученный SHA-256: {sha_hasher.hexdigest()[:32]}…"
                )

        else:
            # Не-chunked v2.1 (файлы зашифрованные старой версией программы)
            with open(filepath, "rb") as f:
                f.seek(header_end)
                encrypted = f.read()
            config = {
                "cipher_chain": metadata["cipher_chain"],
                "kdf":          metadata["kdf"],
                "compression":  metadata.get("compression", "zlib-9"),
            }
            dec = XaletherChaos(password, salt, config)
            if progress_cb: progress_cb(50)
            decrypted = dec.decrypt(encrypted, metadata)
            with open(output, "wb") as f:
                f.write(decrypted)

        if remove_encrypted:
            os.remove(filepath)
        if progress_cb: progress_cb(100)
        return output, metadata


# ─── Проверка целостности ─────────────────────────────────────────────────────

def verify_integrity(
    filepath: str,
    password: str,
    progress_cb: ProgressCallback = None,
) -> Tuple[bool, str]:
    """
    Проверяет SHA-256 целостность .xalether файла.
    Расшифровывает во временный файл, вычисляет хеш, сравнивает с метаданными.
    Возвращает (ok: bool, message: str).
    """
    try:
        meta = read_metadata(filepath)
    except Exception as e:
        return False, f"Не удалось прочитать метаданные: {e}"

    if not meta.get("sha256"):
        return False, (
            "SHA-256 отсутствует в метаданных.\n"
            "Файл создан старой версией XALETHER CRYPT (до v2.2)."
        )

    tmp = tempfile.mktemp(suffix=".xal_verify")
    try:
        # decrypt_file не использует self для ключей — создаём минимальный экземпляр
        instance = object.__new__(XaletherChaos)
        instance.config = DEFAULT_CONFIG.copy()
        instance._keys  = []
        instance.salt   = b"\x00" * SALT_SIZE
        instance.decrypt_file(filepath, password, output=tmp, progress_cb=progress_cb)
        return True, "✅ Файл целый — SHA-256 совпадает"
    except ValueError as e:
        msg = str(e)
        if "повреждён" in msg or "SHA-256" in msg or "изменён" in msg:
            return False, msg
        return False, f"Ошибка расшифровки: {msg}"
    except Exception as e:
        return False, f"Ошибка верификации: {e}"
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
