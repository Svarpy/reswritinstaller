"""Entry point: single-instance guard, then the UI."""
from __future__ import annotations

import socket
import subprocess
import sys
import time

from . import config, proc


def _acquire_lock(wait: float = 0.0):
    end = time.time() + wait
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", config.LOCK_PORT))
            return s
        except OSError:
            s.close()
            if time.time() >= end:
                return None
            time.sleep(0.2)


def main() -> None:
    wait = 8.0 if "--restarted" in sys.argv else 0.0  # old instance is still exiting
    lock = _acquire_lock(wait)
    if lock is None:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("ResumeWriter Launcher", "The launcher is already running.")
        return

    holder = {"lock": lock}

    def restart() -> None:
        holder["lock"].close()
        cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "launcher"]
        env = proc.clean_env()
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"  # fresh unpack for onefile builds
        subprocess.Popen(cmd + ["--restarted"], env=env, **proc.popen_kwargs())
        app.destroy()

    from .ui import App

    app = App(restart)
    app.mainloop()
