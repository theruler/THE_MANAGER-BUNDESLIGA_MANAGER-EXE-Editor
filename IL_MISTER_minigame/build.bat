@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --windowed --upx-dir . ^
  --name il_mister ^
  --add-data "data\campo.png;." ^
  --add-data "data\tabellone.png;." ^
  --add-data "data\lang\mister_lang_it.py;." ^
  --add-data "data\lang\mister_lang_it.py;." ^
  --add-data "data\lang\mister_lang_it.py;." ^
  --paths . ^
  il_mister.py
echo.
echo Fatto: dist\il_mister.exe
pause
