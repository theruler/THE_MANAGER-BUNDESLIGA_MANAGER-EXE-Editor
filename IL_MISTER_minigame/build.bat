@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name il_mister ^
  --add-data "data\campo.png;.\data" ^
  --add-data "data\tabellone.png;.\data" ^
  --add-data "data\FLOW.FON;.\data" ^
  --add-data "data\MICRO4.FON;.\data" ^
  --add-data "data\mister-joy.png;.\data" ^
  --add-data "data\lang\mister_lang_it.py;.\data\lang" ^
  --add-data "data\lang\mister_lang_en.py;.\data\lang" ^
  --add-data "data\lang\mister_lang_de.py;.\data\lang" ^
  --upx-dir "e:\WESTWOOD" ^
  --exclude-module "tkinterdnd2" ^
  --exclude-module "wheel" ^
  --exclude-module "numpy" ^
  --paths . ^
  il_mister.py
echo.
echo Fatto: dist\il_mister.exe
pause
