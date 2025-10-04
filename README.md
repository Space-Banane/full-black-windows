# Fullscreen Black Window (Windows)

This small Python script opens a borderless fullscreen black window on a chosen monitor (defaults to the second monitor, index 1).

Files

- `fullscreen_black.py` — main script. Uses only stdlib (ctypes + tkinter).
 - `black_controller.py` — small controller GUI to open/close the black fullscreen as a separate process. Can be bundled into an exe which spawns itself in child mode.

Usage (PowerShell)

```powershell
# Run on the second monitor (default)
python .\fullscreen_black.py

# Or specify the monitor index (0-based). 0 = primary
python .\fullscreen_black.py 0
```

Controls

- Press ESC to close the black window.

Notes

- The script tries to cover the entire monitor including the taskbar. On some Windows setups the taskbar may remain on top; in that case try running the script from an elevated prompt.
- I couldn't run a live GUI test from this environment, so please run the script locally and tell me if you want additional behavior (e.g. timed auto-close, hotkey to toggle, fade-in/out).

Packaging into a single EXE with PyInstaller
-------------------------------------------

You can bundle the controller into a single Windows exe with PyInstaller. The controller exe will be able to spawn the fullscreen child by launching itself with the `--child` argument.

1. Install PyInstaller in your environment:

```powershell
pip install pyinstaller
```

2. Build a one-file exe for the controller (from the project root):

```powershell
pyinstaller --onefile --noconsole black_controller.py
```

Notes:
- `--onefile` bundles everything into a single exe. The exe will extract a temporary bundle at runtime.
- `--noconsole` prevents a console window from opening when the controller runs. Remove it if you want a console for debugging.
- The produced exe will spawn itself with `--child <index>` to show the fullscreen window. If you see issues with the window not becoming topmost, try running the exe as administrator.

After building, the exe will be in `dist\black_controller.exe`. Double-clicking it will show the controller UI. Clicking "Open Black Screen" launches the child fullscreen process which you'll be able to close from the controller or by pressing ESC in the fullscreen window.

CI / Releases
--------------

This repository includes a GitHub Actions workflow that builds a Windows exe and creates a GitHub Release when you push to the `main` branch.

How it works:
- Push to `main`.
- The `build` job runs on `windows-latest`, installs Python, runs PyInstaller to produce `dist\black_controller.exe`, and uploads the exe as an artifact.
- The `release` job downloads the artifact and creates a GitHub Release, attaching the exe.

To enable releases, simply push this repository to GitHub and ensure Actions are enabled for the repo. The default workflow uses the provided `GITHUB_TOKEN` so no extra secrets are required for basic releases.


## REPO INFO
This repo was made with GPT-5 Mini, as i wanted to test its capabilities.