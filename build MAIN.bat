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
  --add-data "data\lang\savegame_de.py;.\data\lang" ^
  --add-data "data\lang\savegame_en.py;.\data\lang" ^
  --add-data "data\lang\savegame_it.py;.\data\lang" ^
  --add-data "data\lang\savegame_fr.py;.\data\lang" ^
  --add-data "data\lang\savegame_es.py;.\data\lang" ^
  --upx-dir "e:\westwood" ^
  --exclude-module "numpy" ^
  --paths . ^
  main.py
pause