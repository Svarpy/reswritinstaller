"""Cross-platform subprocess helpers: hidden windows, env, tree kill, ports."""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

IS_WIN = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


def popen_kwargs() -> dict:
    """Keyword args so a child runs without opening a console window."""
    if IS_WIN:
        return {"creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def clean_env(venv_dir: Optional[Path] = None) -> dict:
    """Environment equivalent to 'activating' venv_dir, minus launcher pollution."""
    env = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH", "_MEIPASS2", "PYINSTALLER_RESET_ENVIRONMENT"):
        env.pop(key, None)
    if getattr(sys, "frozen", False):  # PyInstaller on Linux rewrites this
        orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if orig is not None:
            env["LD_LIBRARY_PATH"] = orig
        else:
            env.pop("LD_LIBRARY_PATH", None)
    if venv_dir is not None:
        bindir = venv_dir / ("Scripts" if IS_WIN else "bin")
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def run_logged(args: Sequence[str], cwd: Optional[Path], log, env: Optional[dict] = None) -> None:
    """Run a command to completion, streaming output to `log` (a text file)."""
    log.write(f"\n$ {' '.join(map(str, args))}\n")
    log.flush()
    proc = subprocess.run(
        list(map(str, args)), cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, **popen_kwargs(),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(map(str, args))}")


def kill_tree(pid: int, group: bool = True) -> None:
    """Terminate a process and its children. On POSIX, group=True signals the whole
    process group (only valid for processes we started in their own session);
    group=False signals just that PID (use for processes we did not start)."""
    if IS_WIN:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
        return
    try:
        if group:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


def force_kill_tree(pid: int) -> None:
    if IS_WIN:
        kill_tree(pid)
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def pid_on_port(port: int) -> Optional[int]:
    """PID listening on a local TCP port, or None if it cannot be determined."""
    try:
        if IS_WIN:
            out = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                creationflags=CREATE_NO_WINDOW,
            ).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
                    return int(parts[4])
            return None
        out = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True
        ).stdout.split()
        return int(out[0]) if out else None
    except (OSError, ValueError):
        return None


def open_path(path: Path) -> None:
    """Open a file/folder in the OS file manager / default app."""
    if IS_WIN:
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def make_kill_on_close_job() -> Optional[object]:
    """Windows only: a job object that kills assigned children when the launcher dies
    (even on force-close). Returns the job handle (keep it alive) or None."""
    if not IS_WIN:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class BASIC(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class EXT(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BASIC), ("IoInfo", IO),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        info = EXT()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)
        ):
            return None
        return job
    except Exception:
        return None


def assign_to_job(job, pid: int) -> None:
    if not IS_WIN or not job:
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1F0FFF, False, pid)  # PROCESS_ALL_ACCESS
        if handle:
            kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), handle)
            kernel32.CloseHandle(handle)
    except Exception:
        pass
