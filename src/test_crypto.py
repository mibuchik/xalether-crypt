#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto import (
    CIPHER_REGISTRY, CIPHER_INFO, KDF_INFO, COMPRESS_INFO,
    PRESETS, DEFAULT_CONFIG, XaletherChaos,
    compress_data, decompress_data,
)

data = b"XALETHER TEST 2025 " * 30

print(f"Шифров: {len(CIPHER_REGISTRY)}  -> {list(CIPHER_REGISTRY.keys())}")
print(f"KDF:    {list(KDF_INFO.keys())}")
print(f"Сжатие: {list(COMPRESS_INFO.keys())}")
print()

all_ok = True

# Тест каждого шифра по отдельности
for cid, layer in CIPHER_REGISTRY.items():
    kb = os.urandom(64)
    ct = layer.encrypt(kb, data)
    rt = layer.decrypt(kb, ct)
    ok = rt == data
    all_ok = all_ok and ok
    status = "OK" if ok else "FAIL"
    print(f"  {cid:<16}: {status}  ({len(ct)} bytes)")

print()

# Тест сжатия
for method in COMPRESS_INFO:
    c = compress_data(data, method)
    d = decompress_data(c, method)
    ok = d == data
    all_ok = all_ok and ok
    print(f"  compress/{method:<8}: {'OK' if ok else 'FAIL'}  ({len(data)} -> {len(c)} bytes)")

print()

# Тест каскадов (пресеты с быстрым KDF)
for pid, preset in PRESETS.items():
    cfg = {
        "cipher_chain": preset["cipher_chain"],
        "kdf": {"type": "pbkdf2-sha256", "iterations": 50000},
        "compression": "zlib-1",
    }
    c = XaletherChaos("testpass", config=cfg)
    enc, meta = c.encrypt(data)
    dec = c.decrypt(enc, meta)
    ok = dec == data
    all_ok = all_ok and ok
    chain_str = " -> ".join(meta["cipher_chain"])
    print(f"  Preset [{pid:<12}]: {'OK' if ok else 'FAIL'}  {chain_str}")

print()
print("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED!")
sys.exit(0 if all_ok else 1)
