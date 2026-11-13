"""Static configuration and per-user paths for the ResumeWriter launcher."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ResumeWriter"

# Repository (public today; token support can be added in git_ops later).
REPO_URL = "https://github.com/Svarpy/resume-writer-yck.git"
BRANCH = "main"
APP_DIR_NAME = "resume-writer-yck"

# Matches `requires-python` of the resume-writer project.
MIN_PYTHON = (3, 10)

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765
SERVER_MODULE = "resume_server"
GUI_MODULE = "resume_gui"

# Localhost port used only as a single-instance lock for the launcher itself.
LOCK_PORT = 48765


def base_dir() -> Path:
    """Per-user directory owned by the launcher (state, logs, installed app)."""
    override = os.environ.get("RESUME_LAUNCHER_HOME")  # used by tests
    if override:
        return Path(override)
    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        root = str(Path.home() / "Library" / "Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(root) / APP_NAME


BASE_DIR = base_dir()
INSTALL_DIR = BASE_DIR / APP_DIR_NAME
STATE_FILE = BASE_DIR / "state.json"
LOG_DIR = BASE_DIR / "logs"


def venv_python(code_dir: Path) -> Path:
    if sys.platform == "win32":
        return code_dir / ".venv" / "Scripts" / "python.exe"
    return code_dir / ".venv" / "bin" / "python"
