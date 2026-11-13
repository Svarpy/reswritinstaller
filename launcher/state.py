"""Persistent installed/uninstalled state, verified against the disk."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from . import config


@dataclass
class State:
    installed: bool = False
    install_path: str = ""
    commit: str = ""

    @property
    def code_dir(self) -> Path:
        return Path(self.install_path)


def _write(state: State) -> None:
    config.BASE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = config.STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
    os.replace(tmp, config.STATE_FILE)


def load() -> State:
    """Load state; self-heal to 'uninstalled' if the install vanished from disk."""
    try:
        data = json.loads(config.STATE_FILE.read_text(encoding="utf-8"))
        state = State(**{k: data.get(k, v) for k, v in asdict(State()).items()})
    except (OSError, ValueError, TypeError):
        state = State()
    if state.installed:
        code = state.code_dir
        if not (code.is_dir() and config.venv_python(code).exists()):
            state = State()
            _write(state)
    return state


def mark_installed(code_dir: Path, commit: str = "") -> State:
    state = State(installed=True, install_path=str(code_dir), commit=commit)
    _write(state)
    return state


def mark_uninstalled() -> State:
    state = State()
    _write(state)
    return state
