# ResumeWriter Launcher

A small single-window desktop app (Python + tkinter) that installs, runs, updates and
uninstalls [resume-writer-yck](https://github.com/Svarpy/resume-writer-yck).

- **Install:** clones the repo (pure-Python `dulwich`, no git needed), creates `.venv`,
  runs `pip install -r requirements.txt`, then opens **Settings**.
- **Settings (⚙, top-right, only when installed):** edit environment variables as key/value rows
  (prefilled from `.env.example` on first run), add new ones, and Save. The launcher writes
  `.env` into the install folder for you — no copying files around. Values are masked by default.
- **Run Server / Run GUI:** `python -m resume_server` / `python -m resume_gui`, always with the
  venv's Python, with no console window. The server auto-starts with the launcher; the GUI starts
  the server first if needed. If port 8765 is already taken, the existing server is reused.
- **Update:** fetches `origin/main`, hard-resets to it, refreshes dependencies, restarts the launcher.
- **Uninstall:** stops everything, deletes the install folder, resets state.
- Closing the launcher stops the server and GUI.
- **Status line:** always shows live Server and GUI state (starting / running / stopped / exited).
- **Logs:** "Show logs" opens an in-app log viewer (Server, GUI, Install, Update); "Open log file"
  opens the selected file in your default editor.
- Dark theme with burgundy text and muted-gold accents (native message boxes follow the OS theme).

Requires Python 3.10+ on PATH (only needed for the first install).

## Where things live
| What | Windows | macOS | Linux |
|---|---|---|---|
| Base dir | `%LOCALAPPDATA%\ResumeWriter` | `~/Library/Application Support/ResumeWriter` | `~/.local/share/ResumeWriter` |

Inside: `resume-writer-yck/` (the app), `state.json`, `logs/`.

## Run from source / build
```bash
pip install -r requirements.txt
python -m launcher

pip install -r requirements-build.txt
python build/build.py      # -> dist/ResumeWriterLauncher/ (one-folder; needed for MSIX/Store)
```
PyInstaller cannot cross-compile. `.github/workflows/build.yml` builds the Windows `.exe` (one-folder, zipped) on a
Windows runner: pushing a merge/push to `main` whose commit message contains a version (e.g. `Release v1.0`) also publishes
a GitHub release; any other push or manual run uploads it as a
workflow artifact.
Set `RESUME_LAUNCHER_HOME` to use a different base dir (handy for testing).
Repo URL, branch and port live in `launcher/config.py`.

## Privacy
See [PRIVACY.md](PRIVACY.md). The launcher collects no data and has no telemetry.
