"""Install, update and uninstall the resume-writer app (no git binary required)."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from . import config, proc, state

Progress = Callable[[str], None]


class PythonNotFound(RuntimeError):
    pass


def _py_version(exe: str) -> Optional[tuple]:
    try:
        out = subprocess.run(
            [exe, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
            capture_output=True, text=True, timeout=15, **proc.popen_kwargs(),
        )
        if out.returncode == 0:
            major, minor = out.stdout.strip().split(".")
            return int(major), int(minor)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def find_system_python() -> str:
    """Locate a Python >= MIN_PYTHON on PATH; raise PythonNotFound otherwise."""
    candidates = []
    for name in ("python", "python3"):
        found = shutil.which(name)
        if found:
            candidates.append(found)
    if not getattr(sys, "frozen", False):
        candidates.append(sys.executable)  # running from source
    for exe in dict.fromkeys(candidates):
        ver = _py_version(exe)
        if ver and ver >= config.MIN_PYTHON:
            return exe
    need = ".".join(map(str, config.MIN_PYTHON))
    raise PythonNotFound(
        f"Python {need} or newer is required but was not found on PATH.\n\n"
        f"Install Python {need}+ from python.org and tick 'Add Python to PATH', "
        f"then start this launcher again."
    )


def _on_rm_error(func, path, _exc):  # read-only files (.git objects) on Windows
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        raise


def remove_tree(path: Path) -> None:
    """rmtree with retries; Windows may briefly hold file locks after a process exits."""
    if not path.exists():
        return
    last: Optional[Exception] = None
    for _ in range(5):
        try:
            shutil.rmtree(path, onerror=_on_rm_error)
            return
        except OSError as exc:
            last = exc
            time.sleep(0.6)
    raise RuntimeError(f"Could not remove {path}: {last}")


class _LogStream:
    """File-like adapter so dulwich progress lands in the log."""

    def __init__(self, log):
        self.log = log

    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode("utf-8", "replace")
        self.log.write(data)

    def flush(self):
        self.log.flush()


def _open_log(name: str):
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    return open(config.LOG_DIR / name, "a", encoding="utf-8")


def _ensure_ca_bundle() -> None:
    """Use certifi's CA bundle so HTTPS works regardless of the OS trust store."""
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except ImportError:
        pass


def _head_commit(code_dir: Path) -> str:
    from dulwich.repo import Repo

    with Repo(str(code_dir)) as repo:
        return repo.head().decode()


def _pip_install(code_dir: Path, log) -> None:
    py = config.venv_python(code_dir)
    proc.run_logged(
        [py, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=code_dir, log=log, env=proc.clean_env(code_dir / ".venv"),
    )


def install(progress: Progress) -> state.State:
    from dulwich import porcelain

    _ensure_ca_bundle()

    python = find_system_python()
    code_dir = config.INSTALL_DIR
    config.BASE_DIR.mkdir(parents=True, exist_ok=True)
    with _open_log("install.log") as log:
        try:
            progress("Downloading ResumeWriter…")
            remove_tree(code_dir)  # leftovers of a failed earlier attempt
            porcelain.clone(
                config.REPO_URL, str(code_dir), branch=config.BRANCH.encode(),
                errstream=_LogStream(log),
            )
            progress("Creating virtual environment…")
            proc.run_logged([python, "-m", "venv", ".venv"], cwd=code_dir, log=log,
                            env=proc.clean_env())
            progress("Installing dependencies (this can take a few minutes)…")
            _pip_install(code_dir, log)
            return state.mark_installed(code_dir, _head_commit(code_dir))
        except Exception:
            remove_tree(code_dir)  # leave nothing half-installed
            raise


def update(progress: Progress) -> state.State:
    """Fast-forward the checkout to origin/<branch> and refresh dependencies."""
    from dulwich import porcelain

    _ensure_ca_bundle()
    from dulwich.repo import Repo

    st = state.load()
    code_dir = st.code_dir
    with _open_log("update.log") as log:
        progress("Fetching latest changes…")
        porcelain.fetch(str(code_dir), "origin",
                        errstream=_LogStream(log))
        with Repo(str(code_dir)) as repo:
            try:
                target = repo.refs[b"refs/remotes/origin/" + config.BRANCH.encode()]
            except KeyError:
                raise RuntimeError("Could not determine the latest commit on origin/main.")
        progress("Applying update…")
        porcelain.reset(str(code_dir), "hard", target.decode())
        progress("Updating dependencies…")
        _pip_install(code_dir, log)
        return state.mark_installed(code_dir, _head_commit(code_dir))


def uninstall() -> None:
    st = state.load()
    code_dir = Path(st.install_path) if st.install_path else config.INSTALL_DIR
    # Safety: only ever delete inside the launcher's own directory.
    if config.BASE_DIR.resolve() in code_dir.resolve().parents:
        remove_tree(code_dir)
    state.mark_uninstalled()


def env_present(code_dir: Path) -> bool:
    return (code_dir / ".env").is_file()


def delete_all_data() -> None:
    """Remove everything the launcher owns: install dir, state, logs."""
    base = config.BASE_DIR.resolve()
    if len(base.parts) < 3:  # refuse to ever wipe a root-like path
        raise RuntimeError(f"Refusing to delete unsafe path: {base}")
    remove_tree(base)
