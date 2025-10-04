"""
black_controller.py

Small controller GUI to open/close the fullscreen black window as a separate process.

Usage:
- Run `python black_controller.py` to show the controller window.
- The controller starts a child process which runs the fullscreen black window.

When packaged with PyInstaller as a single exe, the controller exe can spawn itself with
the `--child <index>` argument to show the fullscreen black window.
"""
from __future__ import annotations

import sys
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# Windows-specific: use Job Object to ensure child processes are killed when parent exits
try:
    import ctypes
    from ctypes import wintypes
    _have_job = True
except Exception:
    _have_job = False

# If running as a frozen exe, set the AppUserModelID as early as possible so
# Windows associates windows created later with the correct AppID.
if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    try:
        exe_stem = Path(sys.executable).stem
        _early_appid = f"com.{exe_stem}"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_early_appid)
    except Exception:
        pass


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def set_app_user_model_id(appid: str | None = None) -> None:
    """Set the Windows Application User Model ID so the taskbar uses the exe icon.
    No-op on non-Windows.
    """
    if sys.platform != "win32":
        return (None, False)
    try:
        if appid is None:
            # Prefer an appid derived from the executable name when frozen so pinned shortcuts
            # and the running process share the same id.
            if is_frozen():
                exe_stem = Path(sys.executable).stem
                appid = f"com.{exe_stem}"
            else:
                appid = "com.blackcontroller.dev"
        # Use wide char version
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        return (appid, True)
    except Exception:
        # best-effort
        return (appid if appid else None, False)


def set_window_icon_for_tk(root: tk.Tk) -> None:
    """Force the window's icon (both big and small) using Win32 APIs so the taskbar shows it.
    No-op on non-Windows or if icon.ico is missing.
    """
    if sys.platform != 'win32':
        return {"used_icon_file": False, "extracted_exe_icon": False, "sent": False}
    try:
        ico = Path(__file__).with_name('icon.ico')
        hwnd = root.winfo_id()
        user32 = ctypes.windll.user32
        LR_LOADFROMFILE = 0x00000010
        IMAGE_ICON = 1

        # Try loading icon.ico first
        if ico.exists():
            hicon = user32.LoadImageW(None, str(ico), IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
            if hicon:
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
                return {"used_icon_file": True, "extracted_exe_icon": False, "sent": True}

        # If icon.ico not present, and we're running frozen, try to extract icon from the exe
        if is_frozen():
            phicon_large = ctypes.c_void_p()
            phicon_small = ctypes.c_void_p()
            res = ctypes.windll.shell32.ExtractIconExW(str(sys.executable), 0, ctypes.byref(phicon_large), ctypes.byref(phicon_small), 1)
            if res > 0:
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                sent = False
                if phicon_small.value:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, phicon_small.value)
                    sent = True
                if phicon_large.value:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, phicon_large.value)
                    sent = True
                # Also set the window class icon (both big and small) which helps on some Windows versions
                try:
                    GCLP_HICON = -14
                    GCLP_HICONSM = -34
                    # SetClassLongPtrW requires HWND and the index; use SetClassLongPtrW if available
                    if hasattr(ctypes.windll.user32, 'SetClassLongPtrW'):
                        ctypes.windll.user32.SetClassLongPtrW(hwnd, GCLP_HICON, phicon_large.value)
                        ctypes.windll.user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, phicon_small.value if phicon_small.value else phicon_large.value)
                    else:
                        # Fallback for older Python/Win32: SetClassLongW
                        ctypes.windll.user32.SetClassLongW(hwnd, GCLP_HICON, phicon_large.value)
                        ctypes.windll.user32.SetClassLongW(hwnd, GCLP_HICONSM, phicon_small.value if phicon_small.value else phicon_large.value)
                except Exception:
                    pass
                return {"used_icon_file": False, "extracted_exe_icon": True, "sent": sent}

        return {"used_icon_file": False, "extracted_exe_icon": False, "sent": False}
    except Exception:
        # best-effort
        return {"used_icon_file": False, "extracted_exe_icon": False, "sent": False}


def run_child_mode_from_args():
    """If called with --child <index>, import the fullscreen module and run it.
    This allows the bundled exe to spawn itself in child mode.
    """
    import fullscreen_black

    # default index is 1
    idx = 1
    try:
        i = sys.argv.index("--child")
        if i + 1 < len(sys.argv):
            idx = int(sys.argv[i + 1])
    except ValueError:
        print("Invalid monitor index; falling back to 1.")
        pass

    fullscreen_black.cover_monitor(idx)


class ControllerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Black Screen Controller")
        # Try to set window icon if available
        try:
            ico = Path(__file__).with_name('icon.ico')
            if ico.exists():
                root.iconbitmap(str(ico))
        except Exception:
            pass
        root.geometry("320x140")

        frm = ttk.Frame(root, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Monitor index (0 = primary):").grid(column=0, row=0, sticky=tk.W)
        self.monitor_var = tk.IntVar(value=1)
        self.spin = ttk.Spinbox(frm, from_=0, to=10, textvariable=self.monitor_var, width=5)
        self.spin.grid(column=1, row=0, sticky=tk.W)

        self.open_btn = ttk.Button(frm, text="Open Black Screen", command=self.open_black)
        self.open_btn.grid(column=0, row=1, columnspan=2, pady=(8, 0), sticky=tk.EW)

        self.close_btn = ttk.Button(frm, text="Close Black Screen", command=self.close_black, state=tk.DISABLED)
        self.close_btn.grid(column=0, row=2, columnspan=2, pady=(6, 0), sticky=tk.EW)

        self.status_var = tk.StringVar(value="Status: closed")
        ttk.Label(frm, textvariable=self.status_var).grid(column=0, row=3, columnspan=2, pady=(8, 0), sticky=tk.W)

        self.quit_btn = ttk.Button(frm, text="Quit", command=self.quit)
        self.quit_btn.grid(column=0, row=4, columnspan=2, pady=(8, 0), sticky=tk.EW)

        # Diagnostics area
        self.diag_text = tk.Text(frm, height=6, width=36, wrap=tk.WORD)
        self.diag_text.grid(column=0, row=5, columnspan=2, pady=(8,0))
        self.diag_text.configure(state=tk.DISABLED)

        for child in frm.winfo_children():
            child.grid_configure(padx=4, pady=4)

        self.proc = None
        self._polling = False
        self._job = None
        # Initial diagnostics
        self.refresh_diagnostics()

    def refresh_diagnostics(self):
        # Show AppUserModelID and icon status
        self.diag_text.configure(state=tk.NORMAL)
        self.diag_text.delete('1.0', tk.END)
        appid, ok = set_app_user_model_id()
        self.diag_text.insert(tk.END, f"AppUserModelID: {appid}\n")
        self.diag_text.insert(tk.END, f"AppUserModelID set: {ok}\n")
        icon_status = set_window_icon_for_tk(self.root)
        self.diag_text.insert(tk.END, f"Icon file used: {icon_status.get('used_icon_file')}\n")
        self.diag_text.insert(tk.END, f"Extracted exe icon: {icon_status.get('extracted_exe_icon')}\n")
        self.diag_text.insert(tk.END, f"WM_SETICON sent: {icon_status.get('sent')}\n")
        self.diag_text.configure(state=tk.DISABLED)

    def _get_child_command(self, index: int) -> list[str]:
        # If running as a bundled exe, spawn the exe with --child
        if is_frozen():
            exe = sys.executable
            return [exe, "--child", str(index)]
        # Otherwise run the fullscreen_black.py with the current python executable
        script = Path(__file__).with_name("fullscreen_black.py")
        return [sys.executable, str(script), str(index)]

    def open_black(self):
        if self.proc is not None:
            return
        index = int(self.monitor_var.get())
        cmd = self._get_child_command(index)

        # Start the child process
        try:
            # On Windows, avoid creating a new console window when possible
            creationflags = 0
            self.proc = subprocess.Popen(cmd, creationflags=creationflags)
            # If on Windows, create a Job Object and assign the child to it so the OS
            # will terminate the child when this process exits.
            if _have_job and sys.platform == 'win32':
                try:
                    kernel32 = ctypes.windll.kernel32

                    # Define required structures
                    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                        _fields_ = [
                            ("PerProcessUserTimeLimit", ctypes.c_int64),
                            ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", wintypes.DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t),
                            ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t),
                            ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD),
                        ]

                    class IO_COUNTERS(ctypes.Structure):
                        _fields_ = [
                            ("ReadOperationCount", ctypes.c_uint64),
                            ("WriteOperationCount", ctypes.c_uint64),
                            ("OtherOperationCount", ctypes.c_uint64),
                            ("ReadTransferCount", ctypes.c_uint64),
                            ("WriteTransferCount", ctypes.c_uint64),
                            ("OtherTransferCount", ctypes.c_uint64),
                        ]

                    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                        _fields_ = [
                            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                            ("IoInfo", IO_COUNTERS),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t),
                        ]

                    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
                    JobObjectExtendedLimitInformation = 9

                    hJob = kernel32.CreateJobObjectW(None, None)
                    if hJob:
                        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                        res = kernel32.SetInformationJobObject(hJob, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info))
                        if res:
                            # Open process handle and assign it to the job
                            PROCESS_ALL_ACCESS = 0x1F0FFF
                            hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, self.proc.pid)
                            if hProcess:
                                ok = kernel32.AssignProcessToJobObject(hJob, hProcess)
                                if ok:
                                    # keep job handle alive on self so it closes when this process exits
                                    self._job = hJob
                                else:
                                    kernel32.CloseHandle(hJob)
                        else:
                            # couldn't set info, close job
                            kernel32.CloseHandle(hJob)
                except Exception:
                    print("Failed to set job object")
                    # Best-effort; if Job API calls fail, continue without it
                    pass
        except Exception as e:
            self.status_var.set(f"Failed to start: {e}")
            self.proc = None
            return

        self.status_var.set(f"Status: running (pid={self.proc.pid})")
        self.open_btn.config(state=tk.DISABLED)
        self.close_btn.config(state=tk.NORMAL)
        self._start_polling()

    def close_black(self):
        if not self.proc:
            return
        try:
            self.proc.terminate()
            # wait briefly
            for _ in range(10):
                ret = self.proc.poll()
                if ret is not None:
                    break
                time.sleep(0.1)
            if self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass
        finally:
            self._clear_proc()
        
        if getattr(self, '_job', None):
            try:
                ctypes.windll.kernel32.CloseHandle(self._job)
            except Exception:
                pass
            self._job = None

    def _start_polling(self):
        if self._polling:
            return
        self._polling = True
        self._poll()

    def _poll(self):
        if self.proc:
            if self.proc.poll() is not None:
                self._clear_proc()
                self._polling = False
                return
            else:
                # still running
                self.status_var.set(f"Status: running (pid={self.proc.pid})")
        self.root.after(500, self._poll)

    def quit(self):
        self.close_black()
        self.root.quit()


def main():
    # If a child flag is present, run the fullscreen directly (this happens when the controller spawns itself)
    if "--child" in sys.argv:
        run_child_mode_from_args()
        return
    # Set an app id on Windows so the taskbar uses the exe icon
    set_app_user_model_id()

    root = tk.Tk()
    # Force the window icon (taskbar) when possible
    set_window_icon_for_tk(root)
    app = ControllerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
