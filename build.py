"""
build.py

Advanced packaging helper:
- Converts `icon.png` -> `icon.ico` using `make_icon.py` if present
- Cleans previous build artifacts (build/, dist/, .spec)
- Runs PyInstaller with deterministic options

Usage:
    python build.py

This is intended for CI and local reproducible builds.
"""
from pathlib import Path
import subprocess
import sys
import shutil


ROOT = Path(__file__).parent


def clean():
    for name in ("build", "dist", "black_controller.spec"):
        p = ROOT / name
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()


def make_icon_if_needed():
    src = ROOT / "icon.png"
    dst = ROOT / "icon.ico"
    if src.exists():
        print(f"Converting {src} -> {dst}")
        subprocess.check_call([sys.executable, str(ROOT / "make_icon.py"), str(src)])
    else:
        print("No icon.png found; skipping icon generation.")


def run_pyinstaller():
    name = "black_controller"
    icon = ROOT / "icon.ico"
    # Build command so that --icon <icon.ico> appears before the script path
    cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--noconfirm", "--name", name, "--noconsole"]
    if icon.exists():
        cmd += ["--icon", str(icon)]
    cmd += [str(ROOT / "black_controller.py")]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    clean()
    make_icon_if_needed()
    run_pyinstaller()


if __name__ == "__main__":
    main()
