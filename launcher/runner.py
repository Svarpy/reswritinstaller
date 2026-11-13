"""Start/stop the server and GUI using the venv's Python."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from . import config, proc


class Runner:
    def __init__(self, code_dir: Path):
        self.code_dir = code_dir
        self.venv_dir = code_dir / ".venv"
        self.python = config.venv_python(code_dir)
        self._procs: Dict[str, subprocess.Popen] = {}
        self.exit_codes: Dict[str, int] = {}  # unexpected exits (not user-initiated stops)
        self._job = proc.make_kill_on_close_job()

    # ---- state -------------------------------------------------------
    def _alive(self, name: str) -> bool:
        p = self._procs.get(name)
        if p is not None and p.poll() is not None:
            self.exit_codes[name] = p.returncode
            del self._procs[name]
            return False
        return p is not None

    def server_port_open(self) -> bool:
        return proc.port_open(config.SERVER_HOST, config.SERVER_PORT)

    def server_running(self) -> bool:
        """True for our own server or any other instance holding the port."""
        return self._alive("server") or self.server_port_open()

    def server_is_external(self) -> bool:
        return not self._alive("server") and self.server_port_open()

    def gui_running(self) -> bool:
        return self._alive("gui")

    def server_state(self) -> str:
        """'running' | 'starting' | 'external' | 'exited' | 'stopped'."""
        if self._alive("server"):
            return "running" if self.server_port_open() else "starting"
        if self.server_port_open():
            return "external"
        return "exited" if "server" in self.exit_codes else "stopped"

    def gui_state(self) -> str:
        """'running' | 'exited' | 'stopped'."""
        if self._alive("gui"):
            return "running"
        return "exited" if "gui" in self.exit_codes else "stopped"

    # ---- start / stop ------------------------------------------------
    def _start(self, name: str, module: str) -> None:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.exit_codes.pop(name, None)
        log = open(config.LOG_DIR / f"{name}.log", "ab")
        log.write(f"\n--- starting python -m {module} ---\n".encode())
        log.flush()
        p = subprocess.Popen(
            [str(self.python), "-m", module], cwd=self.code_dir,
            env=proc.clean_env(self.venv_dir), stdout=log, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, **proc.popen_kwargs(),
        )
        log.close()
        proc.assign_to_job(self._job, p.pid)
        self._procs[name] = p

    def start_server(self) -> str:
        """Returns 'started', or 'external' if something already holds the port."""
        if self._alive("server"):
            return "started"
        if self.server_port_open():
            return "external"
        self._start("server", config.SERVER_MODULE)
        return "started"

    def wait_for_server(self, timeout: float = 30.0) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.server_port_open():
                return True
            p = self._procs.get("server")
            if p is not None and p.poll() is not None:
                return False  # crashed during startup
            time.sleep(0.25)
        return False

    def start_gui(self) -> None:
        if not self._alive("gui"):
            self._start("gui", config.GUI_MODULE)

    def _stop(self, name: str) -> None:
        p = self._procs.pop(name, None)
        if p is None or p.poll() is not None:
            return
        proc.kill_tree(p.pid)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.force_kill_tree(p.pid)

    def stop_gui(self) -> None:
        self._stop("gui")

    def stop_server(self) -> None:
        """Stops our own server process only (see stop_external_server)."""
        self._stop("server")

    def external_server_pid(self) -> Optional[int]:
        return proc.pid_on_port(config.SERVER_PORT) if self.server_is_external() else None

    def stop_external_server(self) -> bool:
        pid = self.external_server_pid()
        if pid is None:
            return False
        proc.kill_tree(pid, group=False)
        end = time.time() + 5
        while time.time() < end and self.server_port_open():
            time.sleep(0.2)
        return not self.server_port_open()

    def stop_all(self) -> None:
        self.stop_gui()
        self.stop_server()
