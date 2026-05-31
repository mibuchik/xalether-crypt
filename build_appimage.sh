#!/bin/bash

echo "============================================"
echo " XALETHER CRYPT v2.2 — Сборка AppImage"
echo "============================================"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей для AppImage
pip install -r requirements.txt
pip install appimage-builder

# Создание структуры для AppImage
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/icons
mkdir -p AppDir/usr/share/applications

# Копирование ассетов
cp -r assets AppDir/usr/share/

# Создание .desktop файла
cat > AppDir/usr/share/applications/xalether-crypt.desktop << EOF
[Desktop Entry]
Name=Xalether Crypt
Comment=Cascade File Encryption Tool
Exec=xalether-crypt
Icon=xalether-crypt
Terminal=false
Type=Application
Categories=Utility;Security;
EOF

# Создание скрипта запуска
cat > AppDir/usr/bin/xalether-crypt << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
APPDIR="\${SCRIPT_DIR%/usr/bin}"
cd "\$APPDIR"

# Активация Python окружения
if [ -f "\$APPDIR/usr/venv/bin/activate" ]; then
    source "\$APPDIR/usr/venv/bin/activate"
fi

# Запуск приложения
exec python3 "\$APPDIR/usr/share/xalether-crypt/main.py"
EOF
chmod +x AppDir/usr/bin/xalether-crypt

# Копирование исходного кода
cp -r src/* AppDir/usr/share/xalether-crypt/

# Создание AppRun
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"

cd "$HERE"
exec ./usr/bin/xalether-crypt "$@"
EOF
chmod +x AppDir/AppRun

echo ""
echo "Структура AppImage создана в AppDir/"
echo "Для создания AppImage используйте:"
echo "  appimage-builder --generate AppDir"
echo "или"
echo "  appimagetool AppDir XaletherCrypt-x86_64.AppImage"