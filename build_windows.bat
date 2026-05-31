@echo off
echo ============================================
echo  XALETHER CRYPT v2.2 — Сборка для Windows
echo ============================================

REM Создание виртуального окружения
if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Установка зависимостей
pip install -r requirements.txt

REM Очистка предыдущих сборок
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Сборка с помощью PyInstaller
pyinstaller ^
  --onefile ^
  --name "XaletherCrypt" ^
  --add-data "assets;assets" ^
  --windowed ^
  src\main.py

echo.
echo Готово! Файл: dist\XaletherCrypt.exe
echo.
echo Для запуска: dist\XaletherCrypt.exe