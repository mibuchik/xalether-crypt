#!/bin/bash

echo "============================================"
echo " XALETHER CRYPT v2.2 — Создание DEB пакета"
echo "============================================"

VERSION=$(cat version.txt)
PKG_NAME="xalether-crypt"
ARCH="amd64"

# Создание структуры пакета
mkdir -p deb-package/DEBIAN
mkdir -p deb-package/usr/bin
mkdir -p deb-package/usr/share/xalether-crypt
mkdir -p deb-package/usr/share/icons/hicolor/scalable/apps
mkdir -p deb-package/usr/share/applications

# Копирование исполняемого файла
cp dist/XaletherCrypt deb-package/usr/bin/xalether-crypt

# Создание .desktop файла
cat > deb-package/usr/share/applications/xalether-crypt.desktop << EOF
[Desktop Entry]
Version=1.0
Name=Xalether Crypt
Comment=Cascade File Encryption Tool
Exec=xalether-crypt
Icon=xalether-crypt
Terminal=false
Type=Application
Categories=Utility;Security;
EOF

# Создание control файла
cat > deb-package/DEBIAN/control << EOF
Package: $PKG_NAME
Version: $VERSION
Architecture: $ARCH
Maintainer: mibuchik <mibuchik@github>
Depends: libqt5gui5, libqt5widgets5, libqt5core5a
Description: Cascade File Encryption Tool with GUI
 Xalether Crypt is a modern GUI tool for cascade encryption
 of files and folders. Supports 8 algorithms, 4 KDF, 5 compression
 methods, file shredder and integrity verification.
EOF

# Создание скриптов установки
cat > deb-package/DEBIAN/postinst << 'EOF'
#!/bin/bash
set -e
# Обновление кэша .desktop файлов
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF

cat > deb-package/DEBIAN/postrm << 'EOF'
#!/bin/bash
set -e
# Обновление кэша .desktop файлов
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF

chmod 755 deb-package/DEBIAN/postinst
chmod 755 deb-package/DEBIAN/postrm

# Сборка пакета
dpkg-deb --build deb-package ${PKG_NAME}_${VERSION}_${ARCH}.deb

echo ""
echo "DEB пакет создан: ${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "Установка:"
echo "  sudo apt install ./${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "Удаление:"
echo "  sudo apt remove $PKG_NAME"