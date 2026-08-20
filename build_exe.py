import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from i18n import tr

PROJECT = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(PROJECT, "main.py")
APP_NAME = "THE MANAGER - Bundesliga Manager String-Editor"
EXE_NAME = APP_NAME + ".exe"
OBSOLETE_RELEASE_NAME = "THE MANAGER - Bundesliga Manager EXE-Editor"
ICON_REL = os.path.join("assets", "THE_MANAGER_String_Editor.ico")
SRC_CONFIG = os.path.join(PROJECT, "data", "char-mapping.json")
SRC_ICON = os.path.join(PROJECT, ICON_REL)
RELEASE_ROOT = os.path.join(PROJECT, "release")
RELEASE_DIR = os.path.join(RELEASE_ROOT, APP_NAME)
RELEASE_DATA = os.path.join(RELEASE_DIR, "data")


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def main():
    if not os.path.isfile(ENTRY):
        raise SystemExit(tr("build.err.no_entry", path=ENTRY))
    if not os.path.isfile(SRC_CONFIG):
        raise SystemExit(tr("build.err.no_config", path=SRC_CONFIG))
    if not os.path.isfile(SRC_ICON):
        raise SystemExit(tr("build.err.no_icon", path=SRC_ICON))

    config_hash = sha256(SRC_CONFIG)
    config_size = os.path.getsize(SRC_CONFIG)
    print(tr("build.step.config", hash=config_hash, size=config_size))
    print(tr("build.step.icon", hash=sha256(SRC_ICON), size=os.path.getsize(SRC_ICON)))

    work = tempfile.mkdtemp(prefix="pyi_build_")
    dist = os.path.join(work, "dist")
    try:
        command = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--noconfirm",
            "--clean",
            "--name", APP_NAME,
            "--add-data", f"{SRC_ICON}{os.pathsep}assets",
            "--distpath", dist,
            "--workpath", os.path.join(work, "build"),
            "--specpath", work,
            ENTRY,
        ]
        print(tr("build.step.command", cmd=" ".join(command)))
        result = subprocess.run(command, cwd=PROJECT)
        if result.returncode != 0:
            raise SystemExit(tr("build.err.pyi_failed", code=result.returncode))

        built = os.path.join(dist, EXE_NAME)
        if not os.path.isfile(built):
            raise SystemExit(tr("build.err.no_exe", path=built))
        print(tr("build.step.built", hash=sha256(built), size=os.path.getsize(built)))

        obsolete = os.path.join(RELEASE_ROOT, OBSOLETE_RELEASE_NAME)
        if os.path.isdir(obsolete):
            shutil.rmtree(obsolete)
            print(tr("build.step.removed_obsolete", name=OBSOLETE_RELEASE_NAME))
        if os.path.isdir(RELEASE_DIR):
            shutil.rmtree(RELEASE_DIR)
        os.makedirs(RELEASE_DATA)
        shutil.copy2(built, os.path.join(RELEASE_DIR, EXE_NAME))
        print(tr("build.step.release_exe", path=os.path.join(RELEASE_DIR, EXE_NAME)))

        target_config = os.path.join(RELEASE_DATA, "char-mapping.json")
        shutil.copyfile(SRC_CONFIG, target_config)
        if sha256(target_config) != config_hash:
            raise SystemExit(tr("build.err.config_mismatch"))
        print(tr("build.step.config_verified", hash=config_hash))

        key_path = os.path.join(RELEASE_DATA, "deepl_key.txt")
        with open(key_path, "wb"):
            pass
        if os.path.getsize(key_path) != 0:
            raise SystemExit(tr("build.err.key_nonempty"))
        print(tr("build.step.key_file"))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print(tr("build.step.release_header"))
    for root, dirs, files in os.walk(RELEASE_DIR):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(root, name)
            print(f"  {os.path.relpath(full, RELEASE_ROOT)}  {os.path.getsize(full)} B")


if __name__ == "__main__":
    main()
