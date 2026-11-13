# ResumeWriter Launcher

A small single-window desktop app (Python + tkinter) that installs, runs, updates and
uninstalls [resume-writer-yck](https://github.com/Svarpy/resume-writer-yck).

- **Install:** clones the repo (pure-Python `dulwich`, no git needed), creates `.venv`,
  runs `pip install -r requirements.txt`, then asks you to drop your `.env` into the code folder.
- **Run Server / Run GUI:** `python -m resume_server` / `python -m resume_gui`, always with the
  venv's Python, with no console window. The server auto-starts with the launcher; the GUI starts
  the server first if needed. If port 8765 is already taken, the existing server is reused.
- **Update:** fetches `origin/main`, hard-resets to it, refreshes dependencies, restarts the launcher.
- **Uninstall:** stops everything, deletes the install folder, resets state.
- Closing the launcher stops the server and GUI.
- **Status line:** always shows live Server and GUI state (starting / running / stopped / exited).
- **Logs:** "Show logs" opens an in-app log viewer (Server, GUI, Install, Update); "Open log file"
  opens the selected file in your default editor.
- **Delete Launcher** (only shown while ResumeWriter is not installed): removes all launcher data
  (install dir, state, logs) and the launcher itself. On Windows the launcher deletes itself just
  after closing; if it cannot, you are told which file to delete manually.
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
python build/build.py      # -> dist/ResumeWriterLauncher(.exe)
```
PyInstaller cannot cross-compile. `.github/workflows/build.yml` builds the Windows `.exe` on a
Windows runner: pushing a `v*` tag attaches it to a GitHub release; a manual run uploads it as a
workflow artifact.
Set `RESUME_LAUNCHER_HOME` to use a different base dir (handy for testing).
Repo URL, branch and port live in `launcher/config.py`.
