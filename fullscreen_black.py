"""
fullscreen_black.py

Launch a borderless fullscreen black window on the second monitor (Windows).
- ESC will close the window.
- If no second monitor is found, it falls back to the primary.

Uses only the Python stdlib (ctypes + tkinter).
"""
from __future__ import annotations

import sys
import ctypes
from ctypes import wintypes
import tkinter as tk


def get_monitors() -> list[dict]:
    """Return a list of monitors with (left, top, right, bottom, width, height, primary).
    Uses Win32 EnumDisplayMonitors / GetMonitorInfo.
    """
    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    monitors: list[dict] = []

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p
    )

    def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        res = user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        if not res:
            return True
        r = mi.rcMonitor
        left, top, right, bottom = r.left, r.top, r.right, r.bottom
        monitors.append({
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
            "primary": bool(mi.dwFlags & 1),
        })
        return True

    enum_proc = MonitorEnumProc(_callback)
    if not user32.EnumDisplayMonitors(0, 0, enum_proc, 0):
        # Fallback: try using GetSystemMetrics
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        monitors.append({"left": 0, "top": 0, "right": w, "bottom": h, "width": w, "height": h, "primary": True})
    return monitors


def cover_monitor(monitor_index: int = 1):
    monitors = get_monitors()
    if not monitors:
        print("No monitors detected.")
        sys.exit(1)

    if monitor_index < 0 or monitor_index >= len(monitors):
        print(f"Requested monitor {monitor_index} not found, falling back to primary (0).")
        monitor = monitors[0]
    else:
        monitor = monitors[monitor_index]

    left = monitor["left"]
    top = monitor["top"]
    width = monitor["width"]
    height = monitor["height"]

    # On Windows, set the AppUserModelID so the taskbar groups the window with the exe icon
    try:
        if sys.platform == 'win32':
            try:
                from pathlib import Path as _P
                if getattr(sys, 'frozen', False):
                    exe_stem = _P(sys.executable).stem
                    _appid = f"com.{exe_stem}"
                else:
                    _appid = 'com.blackcontroller.dev'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_appid)
            except Exception:
                pass
    except Exception:
        pass

    root = tk.Tk()
    try:
        # Attempt to set the window icon explicitly so the taskbar uses it
        if sys.platform == 'win32':
            from ctypes import windll
            ico = os.path.join(os.path.dirname(__file__), 'icon.ico')
            if os.path.exists(ico):
                LR_LOADFROMFILE = 0x00000010
                IMAGE_ICON = 1
                hicon = windll.user32.LoadImageW(None, ico, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
                if hicon:
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1
                    windll.user32.SendMessageW(root.winfo_id(), WM_SETICON, ICON_SMALL, hicon)
                    windll.user32.SendMessageW(root.winfo_id(), WM_SETICON, ICON_BIG, hicon)
    except Exception:
        pass
    # set runtime icon if provided
    try:
        import os
        ico = os.path.join(os.path.dirname(__file__), 'icon.ico')
        if os.path.exists(ico):
            root.iconbitmap(ico)
    except Exception:
        print("Failed to set window icon.")
        pass
    # Remove window decorations
    root.overrideredirect(True)
    # Make sure it appears on top
    root.attributes("-topmost", True)
    # Set black background
    root.configure(background="#000000")

    # Place window exactly on the target monitor and force size
    geometry = f"{width}x{height}+{left}+{top}"
    root.geometry(geometry)

    # Create a full-size black canvas to be absolutely sure every pixel is black
    canvas = tk.Canvas(root, width=width, height=height, highlightthickness=0)
    canvas.pack()
    canvas.configure(background="#000000")

    # Grab keyboard to listen for ESC to exit
    def on_key(event):
        if event.keysym == "Escape":
            root.destroy()

    root.bind_all("<Key>", on_key)

    # Ensure window covers taskbar and other top-level windows by using SetWindowPos
    try:
        user32 = ctypes.windll.user32
        SWP_SHOWWINDOW = 0x0040
        HWND_TOPMOST = -1
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        # Force position and size
        user32.SetWindowPos(hwnd, HWND_TOPMOST, left, top, width, height, SWP_SHOWWINDOW)
    except Exception:
        # If anything goes wrong with ctypes calls, continue — the tkinter window should still appear
        pass

    # Provide a small instruction on the primary monitor or console
    print(f"Showing black fullscreen on monitor at {left},{top} {width}x{height}. Press ESC to close.")

    root.mainloop()


if __name__ == "__main__":
    # Default: try to use second monitor (index 1). If not available, falls back.
    target_index = 1
    # Allow selecting monitor via first argument (0-based)
    if len(sys.argv) > 1:
        try:
            target_index = int(sys.argv[1])
        except ValueError:
            pass
    cover_monitor(target_index)
