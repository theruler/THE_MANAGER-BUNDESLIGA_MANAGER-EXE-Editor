@echo off
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
  --name "THE MANAGER Editor" ^
  --add-data "data\lang\lang_de.py;.\data\lang" ^
  --add-data "data\lang\lang_en.py;.\data\lang" ^
  --add-data "data\lang\lang_es.py;.\data\lang" ^
  --add-data "data\lang\lang_fr.py;.\data\lang" ^
  --add-data "data\lang\lang_it.py;.\data\lang" ^
  --add-data "data\lang\tore_lang_de.py;.\data\lang" ^
  --add-data "data\lang\tore_lang_en.py;.\data\lang" ^
  --add-data "data\lang\tore_lang_es.py;.\data\lang" ^
  --add-data "data\lang\tore_lang_fr.py;.\data\lang" ^
  --add-data "data\lang\tore_lang_it.py;.\data\lang" ^
  --upx-dir "c:\intel" ^
  --exclude-module "numpy" ^
  --paths . ^
  main.py
pause