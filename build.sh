#!/bin/bash

echo "============================================"
echo " XALETHER CRYPT v2.2 — Сборка для Linux"
echo "============================================"

# Установка зависимостей
pip install -r requirements.txt

# Сборка с помощью PyInstaller
pyinstaller \
  --onefile \
  --name "XaletherCrypt" \
  --add-data "assets:assets" \
  src/main.py

echo ""
echo "Готово! Файл: dist/XaletherCrypt"
echo ""