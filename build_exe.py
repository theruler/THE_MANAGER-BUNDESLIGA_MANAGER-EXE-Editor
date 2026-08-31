"""Reproducible PyInstaller build for the end-user release.

Developer tool only - never imported by the application.

Produces:

    release/THE MANAGER - Bundesliga Manager String-Editor/
    |- THE MANAGER - Bundesliga Manager String-Editor.exe
    |- data/
       |- char-mapping.json      (byte-identical copy of the developer source)
       |- deepl_key.txt          (always created empty)
       |- lang/lang_{en,de,es,fr,it}.py   (byte-identical, user-replaceable)

English is additionally embedded into the executable with ``--add-data`` under
``data/lang``.  Under PyInstaller onefile that copy lives in the temporary
extraction area (``sys._MEIPASS``) and is NOT placed next to the executable, so
``i18n`` reaches it through its own ``_bundle_dir()`` rather than through the
program directory.  The external file always wins; the embedded one only
answers when the external English pack is missing or damaged.  Both are
produced here from the same source file, so they can never drift apart.

The script never modifies a runtime/source file, never touches a reference EXE,
never runs the produced executable and never reads or writes an API key.
"""

import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROJECT = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(PROJECT, "main.py")
APP_NAME = "THE MANAGER - Bundesliga Manager String-Editor"
EXE_NAME = APP_NAME + ".exe"
# Exactly this superseded intermediate release is removed - no generic sweep.
OBSOLETE_RELEASE_NAME = "THE MANAGER - Bundesliga Manager EXE-Editor"
ICON_REL = os.path.join("assets", "THE_MANAGER_String_Editor.ico")
SRC_CONFIG = os.path.join(PROJECT, "data", "char-mapping.json")
SRC_LAYOUT = os.path.join(PROJECT, "data", "layout-reference.json")
SRC_ICON = os.path.join(PROJECT, ICON_REL)
RELEASE_ROOT = os.path.join(PROJECT, "release")
RELEASE_DIR = os.path.join(RELEASE_ROOT, APP_NAME)
RELEASE_DATA = os.path.join(RELEASE_DIR, "data")

LANG_CODES = ("en", "de", "es", "fr", "it")
FALLBACK_LANG = "en"
# Bundle target of the embedded English pack.  Forward slashes on purpose:
# this is a path inside the archive, not on this filesystem.
LANG_BUNDLE_TARGET = "data/lang"
SRC_LANG = os.path.join(PROJECT, "data", "lang")
SRC_LANG_EN = os.path.join(SRC_LANG, f"lang_{FALLBACK_LANG}.py")
PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z_0-9]*)")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def read_lang(path, code):
    """Read one language file statically.  The file is parsed, never imported.

    Importing would run the file and could pull a stale copy from ``sys.path``;
    the build must judge exactly the bytes it is about to ship.
    """
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), path)
    name = None
    table = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target = getattr(node.targets[0], "id", "")
        if target == "LANG_NAME":
            name = ast.literal_eval(node.value)
        elif target == f"TEXTS_{code.upper()}":
            keys = [ast.literal_eval(key) for key in node.value.keys]
            duplicates = sorted({k for k in keys if keys.count(k) > 1})
            if duplicates:
                raise SystemExit(f"Duplicate key in {path}: {duplicates}")
            values = [ast.literal_eval(v) for v in node.value.values]
            table = dict(zip(keys, values))
    if not isinstance(name, str) or not name:
        raise SystemExit(f"LANG_NAME missing or empty: {path}")
    if not table:
        raise SystemExit(f"TEXTS_{code.upper()} missing or empty: {path}")
    for key, value in table.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise SystemExit(f"Non-string entry {key!r} in {path}")
    return name, table


def verify_languages():
    """Every pack must exist and share one key space and one placeholder set.

    A build that shipped a pack with a missing key would produce raw keys in
    the user interface, so this is a hard precondition, not a warning.
    """
    tables = {}
    for code in LANG_CODES:
        path = os.path.join(SRC_LANG, f"lang_{code}.py")
        if not os.path.isfile(path):
            raise SystemExit(f"Language source missing: {path}")
        name, table = read_lang(path, code)
        tables[code] = table
        print(f"      lang_{code}.py  {sha256(path)}  "
              f"{len(table)} keys  ({name})")
    reference = set(tables[FALLBACK_LANG])
    for code in LANG_CODES:
        if set(tables[code]) != reference:
            missing = sorted(reference - set(tables[code]))
            extra = sorted(set(tables[code]) - reference)
            raise SystemExit(
                f"Key space of lang_{code}.py differs from "
                f"lang_{FALLBACK_LANG}.py: missing={missing[:5]} "
                f"extra={extra[:5]}")
    for key in sorted(reference):
        expected = sorted(PLACEHOLDER.findall(tables[FALLBACK_LANG][key]))
        for code in LANG_CODES:
            found = sorted(PLACEHOLDER.findall(tables[code][key]))
            if found != expected:
                raise SystemExit(
                    f"Placeholder mismatch for {key!r} in lang_{code}.py: "
                    f"{found} instead of {expected}")
    return len(reference)


def main():
    if not os.path.isfile(ENTRY):
        raise SystemExit(f"Entrypoint missing: {ENTRY}")
    if not os.path.isfile(SRC_CONFIG):
        raise SystemExit(f"Config source missing: {SRC_CONFIG}")
    if not os.path.isfile(SRC_ICON):
        raise SystemExit(f"Icon resource missing: {SRC_ICON}")

    config_hash = sha256(SRC_CONFIG)
    layout_hash = sha256(SRC_LAYOUT) if os.path.isfile(SRC_LAYOUT) else None
    config_size = os.path.getsize(SRC_CONFIG)
    print(f"[1/7] config source  {config_hash}  {config_size} B")
    print(f"      icon source    {sha256(SRC_ICON)}  {os.path.getsize(SRC_ICON)} B")

    key_count = verify_languages()
    print(f"[2/7] language pack verified  {len(LANG_CODES)} files  "
          f"{key_count} keys each")

    work = tempfile.mkdtemp(prefix="pyi_build_")
    dist = os.path.join(work, "dist")
    try:
        # The embedded English fallback.  It must land under data/lang inside
        # the bundle, because that is where i18n._bundle_dir() looks for it.
        lang_data = f"{SRC_LANG_EN}{os.pathsep}{LANG_BUNDLE_TARGET}"
        if not lang_data.endswith(os.pathsep + LANG_BUNDLE_TARGET):
            raise SystemExit(
                f"Embedded English fallback must target {LANG_BUNDLE_TARGET}")
        command = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--noconfirm",
            "--clean",
            "--name", APP_NAME,
            "--add-data", f"{SRC_ICON}{os.pathsep}assets",
            "--add-data", lang_data,
            "--distpath", dist,
            "--workpath", os.path.join(work, "build"),
            "--specpath", work,
            ENTRY,
        ]
        if lang_data not in command:
            raise SystemExit("Embedded English fallback missing from the build")
        print("[3/7] " + " ".join(command))
        result = subprocess.run(command, cwd=PROJECT)
        if result.returncode != 0:
            raise SystemExit(f"PyInstaller failed with exit code {result.returncode}")

        built = os.path.join(dist, EXE_NAME)
        if not os.path.isfile(built):
            raise SystemExit(f"Expected executable not produced: {built}")
        print(f"[4/7] built  {sha256(built)}  {os.path.getsize(built)} B")

        obsolete = os.path.join(RELEASE_ROOT, OBSOLETE_RELEASE_NAME)
        if os.path.isdir(obsolete):
            shutil.rmtree(obsolete)
            print(f"      removed superseded release: {OBSOLETE_RELEASE_NAME}")
        if os.path.isdir(RELEASE_DIR):
            shutil.rmtree(RELEASE_DIR)
        os.makedirs(RELEASE_DATA)
        shutil.copy2(built, os.path.join(RELEASE_DIR, EXE_NAME))
        print(f"[5/7] release exe -> {os.path.join(RELEASE_DIR, EXE_NAME)}")

        target_config = os.path.join(RELEASE_DATA, "char-mapping.json")
        shutil.copyfile(SRC_CONFIG, target_config)
        if sha256(target_config) != config_hash:
            raise SystemExit("Release config is not byte-identical to the source")
        print(f"[6/7] release config verified  {config_hash}")

        release_lang = os.path.join(RELEASE_DATA, "lang")
        os.makedirs(release_lang)
        for code in LANG_CODES:
            source = os.path.join(SRC_LANG, f"lang_{code}.py")
            target = os.path.join(release_lang, f"lang_{code}.py")
            shutil.copyfile(source, target)
            if sha256(target) != sha256(source):
                raise SystemExit(
                    f"Release lang_{code}.py is not byte-identical to the source")
        print(f"      release language pack verified  {len(LANG_CODES)} files")

        if layout_hash:
            target_layout = os.path.join(RELEASE_DATA, "layout-reference.json")
            shutil.copyfile(SRC_LAYOUT, target_layout)
            if sha256(target_layout) != layout_hash:
                raise SystemExit("Release layout reference is not byte-identical to the source")
            print(f"      layout reference verified  {layout_hash}")
        else:
            print("      layout reference absent - preflight falls back to the old behaviour")

        key_path = os.path.join(RELEASE_DATA, "deepl_key.txt")
        with open(key_path, "wb"):
            pass
        if os.path.getsize(key_path) != 0:
            raise SystemExit("deepl_key.txt must be empty")
        print("[7/7] release deepl_key.txt  0 B")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("\nRelease:")
    for root, dirs, files in os.walk(RELEASE_DIR):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            print(f"  {os.path.relpath(full, RELEASE_ROOT)}  {os.path.getsize(full)} B")


if __name__ == "__main__":
    main()
