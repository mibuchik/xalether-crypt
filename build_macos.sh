#!/bin/bash

echo "============================================"
echo " XALETHER CRYPT v2.2 — Сборка для macOS"
echo "============================================"

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Очистка предыдущих сборок
rm -rf dist build

# Сборка с помощью PyInstaller
pyinstaller \
  --onefile \
  --name "XaletherCrypt" \
  --add-data "assets:assets" \
  src/main.py

echo ""
echo "Готово! Файл: dist/XaletherCrypt"
echo ""
echo "Для запуска: ./dist/XaletherCrypt"