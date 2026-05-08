# XALETHER CRYPT v2.1

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-41CD52?logo=qt)
![Version](https://img.shields.io/badge/version-2.1.0-8A5CF5)
![Ciphers](https://img.shields.io/badge/шифров-9-orange)
![License](https://img.shields.io/badge/License-MIT-green)

Инструмент каскадного шифрования файлов и папок с современным GUI на PyQt5.  
Поддерживает **9 алгоритмов**, **4 KDF**, **5 методов сжатия** и настраиваемые цепочки.

---

## Возможности

| Функция | Описание |
|---|---|
| 🔐 9 алгоритмов шифрования | AES-GCM, ChaCha20, SIV, CBC, CTR, CFB, Camellia, XChaCha20, 3DES |
| 🔗 Каскадные цепочки | Любая комбинация и порядок — через конструктор в настройках |
| 🔑 4 алгоритма KDF | PBKDF2-SHA256/512, scrypt, Argon2id |
| 🗜 5 методов сжатия | none, zlib (fast/max), bz2, lzma |
| ⚡ 5 пресетов | Fast / Standard / Paranoid / Ultra / Хаос |
| 📁 Поддержка папок | ZIP-архивация → шифрование, автораспаковка при расшифровке |
| 🔒 Личный режим | Привязка к HWID текущего ПК |
| 📤 Режим передачи | Без ограничений — любой с паролем |
| 🎫 Разрешения | Одноразовые коды (XAL-XXXX-XXXX-XXXX), 24 ч |
| ⬇ Drag-and-Drop | Перетаскивание файлов и папок прямо в окно |
| 🔄 Авто-обновление | Проверка новой версии при запуске, загрузка одной кнопкой |
| 🔑 Генератор паролей | Криптографически стойкие, настраиваемый набор символов |
| 📋 История операций | `~/.xalether_history.json` |
| ⚙ Настройки | Сохраняются в `~/.xalether_settings.json` |
| 🧵 Многопоточность | Шифрование в фоне через QThread — GUI не замерзает |

---

## Алгоритмы шифрования

| ID | Название | Тип | Аутентификация | Безопасность |
|---|---|---|---|---|
| `aes-gcm` | AES-256-GCM | AEAD | 128-бит тег | ✓ Высокая |
| `chacha20` | ChaCha20-Poly1305 | AEAD | 128-бит тег | ✓ Высокая |
| `aes-siv` | AES-256-SIV | AEAD | Nonce-misuse resistant | ✓ Высокая |
| `aes-cbc` | AES-256-CBC | CBC + HMAC-SHA256 | Encrypt-then-MAC | ◎ Средняя |
| `aes-ctr` | AES-256-CTR | CTR + HMAC-SHA3-256 | Encrypt-then-MAC | ◎ Средняя |
| `aes-cfb` | AES-256-CFB | CFB + HMAC-SHA256 | Самосинхронизирующийся | ◎ Средняя |
| `camellia` | Camellia-256-CBC | CBC + HMAC-SHA3-256 | Другое семейство алгоритмов | ✓ Высокая |
| `xchacha20` | XChaCha20 | +HMAC-SHA3-512 | Нонс 24 байта | ✓ Высокая |
| `3des` | 3DES-CBC | Legacy + HMAC-SHA256 | ~112 бит эффективно | ⚠ Устарело |

---

## KDF (деривация ключей)

| Алгоритм | Описание | RAM |
|---|---|---|
| PBKDF2-SHA256 | NIST-стандарт, настраиваемые итерации | < 1 МБ |
| PBKDF2-SHA512 | Тяжелее на 64-бит CPU, SHA-512 хеш | < 1 МБ |
| scrypt | Memory-hard, сложно для ASIC/GPU | 64 МБ |
| **Argon2id ★** | PHC Winner 2015, защита от GPU и side-channel | 64-256 МБ |

---

## Пресеты

| Пресет | Цепочка | KDF | Сжатие |
|---|---|---|---|
| ⚡ Быстрый | AES-256-GCM | PBKDF2 100k | zlib-fast |
| 🔒 Стандартный | AES-GCM → ChaCha20 | PBKDF2 500k | zlib-max |
| 🛡 Параноид | AES → ChaCha20 → Camellia | scrypt | bz2 |
| ☢ Ультра | AES → ChaCha20 → Camellia → AES-SIV | Argon2id | lzma |
| 🌀 Хаос | AES-CBC → XChaCha20 → AES-CTR → Camellia → ChaCha20 | Argon2id 256 МБ | lzma |

---

## Быстрый старт

```bash
# 1. Клонировать
git clone https://github.com/mibuchik/xalether-crypt.git
cd xalether-crypt

# 2. Зависимости
pip install -r requirements.txt

# 3. Запуск
python src/main.py
```

---

## Автообновление

При каждом запуске приложение в фоне проверяет `version.txt` на GitHub.  
Если доступна новая версия — появляется жёлтый баннер с кнопкой **Скачать**.

Нажатие скачивает архив с `main` ветки, распаковывает рядом с текущей папкой  
и показывает путь к новой версии. Никаких сторонних зависимостей.

---

## Структура проекта

```
xalether-crypt/
├── src/
│   ├── main.py          # Точка входа
│   ├── crypto.py        # 9 шифров, 4 KDF, 5 сжатий, пресеты
│   ├── gui.py           # PyQt5 интерфейс + автообновление
│   ├── updater.py       # Проверка и загрузка обновлений
│   ├── permissions.py   # Одноразовые коды разрешений
│   ├── utils.py         # ZIP, история, генератор паролей
│   └── test_crypto.py   # Тесты всех алгоритмов
├── assets/
├── version.txt          # Текущая версия (используется автообновлением)
├── requirements.txt
├── build.bat
└── README.md
```

---

## Формат файла `.xalether`

```
[4 bytes]  длина JSON метаданных
[N bytes]  JSON: version, mode, cipher_chain, kdf, compression, noise_size, hwid
[16 bytes] соль PBKDF2/scrypt/Argon2id
[M bytes]  зашифрованные данные (noise_size байт шума + каскад шифров)
```

---

## Сборка в .exe (Windows)

```bat
build.bat
```

Результат: `dist/XaletherCrypt.exe` — без Python, без зависимостей.

---

## ⚠ Предупреждение о безопасности

- **Мастер-пароль не восстанавливается.** Потеря = потеря данных.
- Файлы в режиме «Личный» открываются только на исходном ПК.
- Коды разрешений одноразовые — после использования удаляются.
- 3DES помечен как Legacy — используйте только для совместимости.
- Не передавайте мастер-пароль вместе с зашифрованными файлами.

---

## Лицензия

MIT
