"""Read and write .env files (KEY=VALUE) in a python-dotenv compatible way."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

from . import config

KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
HEADER = "# Managed by ResumeWriter Launcher (Settings)\n"
Pairs = List[Tuple[str, str]]


def _unescape(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            out.append({"n": "\n", "r": "\r", "t": "\t"}.get(nxt, nxt))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def parse(text: str) -> Pairs:
    """Parse .env text into ordered (key, value) pairs; later duplicates win."""
    values: dict = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[7:].lstrip()
        if "=" not in s:
            continue
        key, val = s.split("=", 1)
        key, val = key.strip(), val.strip()
        if not key:
            continue
        if val[:1] == '"':
            m = re.match(r'"((?:[^"\\]|\\.)*)"', val)
            val = _unescape(m.group(1)) if m else val[1:]
        elif val[:1] == "'":
            end = val.find("'", 1)
            val = val[1:end] if end != -1 else val[1:]
        else:
            val = re.split(r"\s+#", val, maxsplit=1)[0].rstrip()
        values.pop(key, None)  # keep position of the last occurrence
        values[key] = val
    return list(values.items())


def _quote(v: str) -> str:
    if v == "":
        return ""
    if "${" in v and "'" not in v and "\n" not in v and "\r" not in v:
        return f"'{v}'"  # single quotes: no variable expansion
    if v != v.strip() or any(c in v for c in ' \t#"\'\\\n\r`$'):
        esc = v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
        return f'"{esc}"'
    return v


def serialize(pairs: Pairs) -> str:
    return HEADER + "".join(f"{k}={_quote(v)}\n" for k, v in pairs)


def load_for_edit(code_dir: Path) -> Tuple[Pairs, str]:
    """Pairs to show in the editor and where they came from:
    'env', 'backup' (kept from a previous uninstall), 'example' or 'empty'."""
    for path, source in (
        (code_dir / ".env", "env"),
        (config.SETTINGS_BACKUP, "backup"),
        (code_dir / ".env.example", "example"),
    ):
        if path.is_file():
            try:
                return parse(path.read_text(encoding="utf-8-sig")), source
            except (OSError, UnicodeDecodeError):
                continue
    return [], "empty"


def backup_env(code_dir: Path) -> bool:
    """Copy <code_dir>/.env to the launcher's own folder (private permissions)."""
    src = code_dir / ".env"
    if not src.is_file():
        return False
    config.BASE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, config.SETTINGS_BACKUP)
    try:
        os.chmod(config.SETTINGS_BACKUP, 0o600)
    except OSError:
        pass
    return True


def discard_backup() -> None:
    try:
        config.SETTINGS_BACKUP.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def validate(pairs: Pairs) -> str:
    """Return an error message, or '' if the pairs are valid."""
    seen = set()
    for key, _ in pairs:
        if not KEY_RE.match(key):
            return f"Invalid variable name: {key!r}. Use letters, digits and underscores, " \
                   "not starting with a digit."
        if key in seen:
            return f"Duplicate variable: {key}"
        seen.add(key)
    return ""


def save(code_dir: Path, pairs: Pairs) -> Path:
    path = code_dir / ".env"
    tmp = code_dir / ".env.tmp"
    tmp.write_text(serialize(pairs), encoding="utf-8", newline="\n")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)
    return path
