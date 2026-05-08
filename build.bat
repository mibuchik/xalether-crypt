@echo off
echo ============================================
echo  XALETHER CRYPT v2.0 — Сборка в .exe
echo ============================================

pip install -r requirements.txt

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "XaletherCrypt" ^
  --add-data "assets;assets" ^
  src/main.py

echo.
echo Готово! Файл: dist\XaletherCrypt.exe
pause
