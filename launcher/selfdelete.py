"""Remove the launcher executable itself, where the OS allows it."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from . import proc


def launcher_path() -> Optional[Path]:
    """Path of the launcher to delete, or None when running from source."""
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:  # macOS: delete the whole .app bundle
        if parent.suffix == ".app":
            return parent
    return exe


def _onedir_internal(target: Path) -> Optional[Path]:
    """PyInstaller one-folder builds keep libraries in a sibling `_internal` folder."""
    internal = target.parent / "_internal"
    return internal if target.is_file() and internal.is_dir() else None


def schedule_delete() -> bool:
    """Delete (or schedule deletion of) the launcher. Returns True if it is gone or will
    be removed once this process exits; False means the user must delete it manually."""
    target = launcher_path()
    if target is None:
        return False
    internal = _onedir_internal(target)
    try:
        if proc.IS_WIN:
            # A running .exe is locked on Windows: a detached helper retries after we exit.
            bat = Path(tempfile.gettempdir()) / "resumewriter_remove_launcher.bat"
            bat.write_text(
                "@echo off\r\n"
                "for /l %%i in (1,1,30) do (\r\n"
                f'  del /f /q "{target}" >nul 2>&1\r\n'
                f'  if not exist "{target}" goto done\r\n'
                "  ping -n 2 127.0.0.1 >nul\r\n"
                ")\r\n"
                ":done\r\n"
                + (f'rmdir /s /q "{internal}" >nul 2>&1\r\n' if internal else "")
                + f'rmdir "{target.parent}" >nul 2>&1\r\n'  # only succeeds if now empty
                +
                '(goto) 2>nul & del "%~f0"\r\n',
                encoding="mbcs",
            )
            subprocess.Popen(
                ["cmd", "/c", str(bat)], close_fds=True,
                creationflags=proc.CREATE_NO_WINDOW | 0x00000008,  # DETACHED_PROCESS
            )
            return True
        if target.is_dir():
            shutil.rmtree(target)
        else:
            os.remove(target)  # unlinking a running binary is fine on POSIX
            if internal:
                shutil.rmtree(internal)
            try:
                target.parent.rmdir()  # only if now empty
            except OSError:
                pass
        return not target.exists()
    except OSError:
        return False
