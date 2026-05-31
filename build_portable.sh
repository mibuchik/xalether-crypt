#!/bin/bash

echo "============================================"
echo " XALETHER CRYPT v2.2 — Портативная версия"
echo "============================================"

VERSION=$(cat version.txt)
TAR_NAME="XaletherCrypt-v${VERSION}-Linux-Portable.tar.gz"

# Создание структуры
mkdir -p portable/XaletherCrypt

# Копирование исполняемого файла
cp dist/XaletherCrypt portable/XaletherCrypt/

# Создание скрипта установки
cat > portable/XaletherCrypt/install.sh << 'EOF'
#!/bin/bash
echo "Установка Xalether Crypt v2.2"
echo "=============================="

INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"

# Создание директорий
mkdir -p "$INSTALL_DIR" "$DESKTOP_DIR" "$ICON_DIR"

# Копирование файла
cp "$(dirname "$0")/XaletherCrypt" "$INSTALL_DIR/xalether-crypt"
chmod +x "$INSTALL_DIR/xalether-crypt"

# Создание .desktop файла
cat > "$DESKTOP_DIR/xalether-crypt.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Name=Xalether Crypt
Comment=Cascade File Encryption Tool
Exec=$INSTALL_DIR/xalether-crypt
Icon=security-high
Terminal=false
Type=Application
Categories=Utility;Security;
DESKTOP

# Добавление в PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo "Добавьте в ~/.bashrc или ~/.zshrc:"
    echo "export PATH=\"\$PATH:$INSTALL_DIR\""
fi

echo ""
echo "Установка завершена!"
echo "Запуск: xalether-crypt"
echo "Или: $INSTALL_DIR/xalether-crypt"
EOF

chmod +x portable/XaletherCrypt/install.sh

# Создание README
cat > portable/XaletherCrypt/README.txt << EOF
XALETHER CRYPT v${VERSION} - Портативная версия для Linux
==========================================================

Файлы:
- XaletherCrypt     - Исполняемый файл (54 MB)
- install.sh        - Скрипт установки

Установка:
1. Распакуйте архив: tar -xzf ${TAR_NAME}
2. Перейдите в папку: cd XaletherCrypt
3. Запустите установку: ./install.sh

Или просто запустите напрямую:
./XaletherCrypt

Примечание:
- Файл самодостаточный, не требует установки Python
- Поддерживает 8 алгоритмов шифрования, 4 KDF, 5 методов сжатия
- С графическим интерфейсом PyQt5
EOF

# Создание архива
tar -czf "${TAR_NAME}" -C portable XaletherCrypt

echo ""
echo "Создан портативный архив: ${TAR_NAME}"
echo ""
echo "Использование:"
echo "  tar -xzf ${TAR_NAME}"
echo "  cd XaletherCrypt"
echo "  ./install.sh      # Установить в ~/.local/bin"
echo "  ./XaletherCrypt   # Запустить напрямую"
echo ""
echo "Размер архива:"
du -h "${TAR_NAME}"