# XALETHER CRYPT v2.2

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-41CD52?logo=qt)
![Version](https://img.shields.io/badge/version-2.2.0-8A5CF5)
![Ciphers](https://img.shields.io/badge/шифров-9-orange)
![License](https://img.shields.io/badge/License-MIT-green)

Инструмент каскадного шифрования файлов и папок с современным GUI на PyQt5.  
Поддерживает **8 алгоритмов**, **4 KDF**, **5 методов сжатия**, **шредер** и **проверку целостности**.

---

## Возможности

| Функция | Описание |
|---|---|
| 🔐 8 алгоритмов шифрования | AES-GCM, ChaCha20, SIV, CBC, CTR, CFB, Camellia, XChaCha20 |
| 🔗 Каскадные цепочки | Любая комбинация и порядок — через конструктор в настройках |
| 🔑 4 алгоритма KDF | PBKDF2-SHA256/512, scrypt, Argon2id |
| 🗜 5 методов сжатия | none, zlib (fast/max), bz2, lzma |
| ⚡ 5 пресетов | Fast / Standard / Paranoid / Ultra / Хаос |
| 📁 Поддержка папок | ZIP-архивация → шифрование, автораспаковка при расшифровке |
| 🗑 Шредер | 3-проходное безвозвратное уничтожение файлов (нули → случ. → нули) |
| 🔍 Проверка целостности | SHA-256 в метаданных, верификация при расшифровке |
| 🖱 Контекстное меню | **УДАЛЕНО** |
| 🔒 Личный режим | Привязка к HWID текущего ПК |
| 📤 Режим передачи | Без ограничений — любой с паролем |
| 🎫 Разрешения | Одноразовые коды (XAL-XXXX-XXXX-XXXX), 24 ч |
| ⬇ Drag-and-Drop | Перетаскивание файлов и папок прямо в окно |
| 🔄 Авто-обновление | Проверка новой версии при запуске, загрузка одной кнопкой |
| 🔑 Генератор паролей | Криптографически стойкие, настраиваемый набор символов |
| 📋 История операций | `~/.xalether_history.json` |
| ⚙ Настройки | Сохраняются в `~/.xalether_settings.json` |
| 🧵 Многопоточность | Шифрование в фоне через QThread — GUI не замерзает |
| 📦 Потоковое шифрование | 32 МБ чанки — большие файлы без зависаний и переполнения RAM |

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

## 🗑 Шредер (безвозвратное уничтожение)

Два режима работы:

### А) При шифровании
Выберите **«Уничтожить (шредер)»** в группе «Оригинал после шифрования»:
1. Файл шифруется во временный файл
2. Оригинал перезаписывается **3 раза** (нули → случайные байты → нули)
3. Файл переименовывается 3 раза со случайными именами
4. Удаляется через `os.remove()`
5. Временный файл перемещается на место оригинала (`.xalether`)

### Б) Без шифрования
Кнопка **«🗑 Уничтожить файл»** на вкладке Шифрование — только шредер, без шифрования.

```python
# utils.py
shred_file(filepath: str, passes: int = 3, progress_cb=None) -> None
```

---

## 🔍 Проверка целостности

- **При шифровании**: SHA-256 оригинального файла записывается в метаданные `.xalether`
- **При расшифровке**: автоматически пересчитывается и сверяется
- **Кнопка «Проверить целостность»**: расшифровывает во временный файл, сверяет хеш, удаляет временный файл
- Результат: **✅ Файл целый** или **⚠️ Файл повреждён или изменён!**

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
и показывает путь к новой версии.

---

## Структура проекта

```
xalether-crypt/
├── src/
│   ├── main.py              # Точка входа
│   ├── crypto.py            # 8 шифров, 4 KDF, 5 сжатий, SHA-256, verify_integrity()
│   ├── gui.py               # PyQt5 интерфейс + шредер + проверка целостности
│   ├── updater.py           # Проверка и загрузка обновлений
│   ├── permissions.py       # Одноразовые коды разрешений
│   ├── utils.py             # ZIP, история, генератор паролей, shred_file()
│   └── test_crypto.py       # Тесты всех алгоритмов
├── assets/
├── version.txt              # Текущая версия (используется автообновлением)
├── requirements.txt
└── README.md
```

---

## Формат файла `.xalether`

```
[4 bytes]  длина JSON метаданных
[N bytes]  JSON: version, chunked, num_chunks, cipher_chain, kdf,
                 compression, sha256, mode, hwid, noise_size
[16 bytes] соль PBKDF2/scrypt/Argon2id
Для каждого чанка (32 МБ):
  [4 bytes]  размер зашифрованного чанка
  [M bytes]  сжатый + зашифрованный чанк
```

---



## ⚠ Предупреждение о безопасности

- **Мастер-пароль не восстанавливается.** Потеря = потеря данных.
- Файлы в режиме «Личный» открываются только на исходном ПК.
- Коды разрешений одноразовые — после использования удаляются.
- 3DES удалён как устаревший алгоритм.
- Шредер не гарантирует уничтожение на SSD с wear-leveling — используйте полное шифрование диска.
- Не передавайте мастер-пароль вместе с зашифрованными файлами.

---

## 📥 Скачать готовый исполняемый файл

Если вы не хотите собирать проект самостоятельно, скачайте готовый исполняемый файл для вашей ОС:

1. **Перейдите в [Releases](https://github.com/mibuchik/xalether-crypt/releases)**
2. **Скачайте файл для вашей системы:**
   - **Linux**: `XaletherCrypt-Linux`
   - **Windows**: `XaletherCrypt-Windows.exe`
   - **macOS**: `XaletherCrypt-macOS`
3. **Запустите файл:**
   - **Linux**: `chmod +x XaletherCrypt-Linux && ./XaletherCrypt-Linux`
   - **Windows**: Просто запустите `XaletherCrypt-Windows.exe`
   - **macOS**: `chmod +x XaletherCrypt-macOS && ./XaletherCrypt-macOS`

---

## 📦 Сборка из исходного кода

### Linux
```bash
git clone https://github.com/mibuchik/xalether-crypt.git
cd xalether-crypt
./build.sh
```

### Windows
```bash
git clone https://github.com/mibuchik/xalether-crypt.git
cd xalether-crypt
build_windows.bat
```

### macOS
```bash
git clone https://github.com/mibuchik/xalether-crypt.git
cd xalether-crypt
chmod +x build_macos.sh
./build_macos.sh
```

---

## Лицензия

MIT
