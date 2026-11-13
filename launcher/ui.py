"""Single-screen tkinter launcher UI."""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from . import config, installer, proc, state
from .runner import Runner


class App(tk.Tk):
    def __init__(self, restart: Callable[[], None]):
        super().__init__()
        self.title("ResumeWriter Launcher")
        self.geometry("520x400")
        self.minsize(480, 380)
        self._restart = restart
        self._busy = False
        self._results: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.state_ = state.load()
        self.runner: Optional[Runner] = None
        self._tiles: dict[str, ttk.Button] = {}

        style = ttk.Style(self)
        style.configure("Tile.TButton", font=("Segoe UI", 13, "bold"), padding=(10, 26))

        if not self.state_.installed:
            try:
                installer.find_system_python()
            except installer.PythonNotFound as exc:
                self.withdraw()
                messagebox.showerror("Python required", str(exc))
                self.destroy()
                sys.exit(1)

        ttk.Label(self, text="ResumeWriter", font=("Segoe UI", 18, "bold")).pack(pady=(16, 4))
        self.tile_frame = ttk.Frame(self)
        self.tile_frame.pack(fill="both", expand=True, padx=20, pady=8)
        self.status = ttk.Label(self, text="", anchor="center")
        self.status.pack(fill="x", padx=20)
        self.bar = ttk.Progressbar(self, mode="indeterminate")
        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=20, pady=(6, 12))
        self.bar.pack(fill="x", padx=20, before=footer)
        ttk.Button(footer, text="View logs", command=self._open_logs).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_tiles()
        self.after(300, self._startup)
        self.after(500, self._poll)

    # ---- layout ------------------------------------------------------
    def _build_tiles(self) -> None:
        for child in self.tile_frame.winfo_children():
            child.destroy()
        self._tiles.clear()
        f = self.tile_frame
        if not self.state_.installed:
            f.columnconfigure(0, weight=1)
            f.rowconfigure(0, weight=1)
            self._tile("install", "Install", self._on_install, 0, 0)
            self._set_status("ResumeWriter is not installed.")
            return
        for i in range(2):
            f.columnconfigure(i, weight=1, uniform="c")
            f.rowconfigure(i, weight=1, uniform="r")
        self._tile("server", "Run Server", self._on_server, 0, 0)
        self._tile("gui", "Run GUI", self._on_gui, 0, 1)
        self._tile("update", "Update", self._on_update, 1, 0)
        self._tile("uninstall", "Uninstall", self._on_uninstall, 1, 1)
        self._update_tiles()

    def _tile(self, key, text, cmd, row, col) -> None:
        b = ttk.Button(self.tile_frame, text=text, style="Tile.TButton", command=cmd)
        b.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        self._tiles[key] = b

    def _set_status(self, text: str) -> None:
        self.status.config(text=text)

    def _update_tiles(self) -> None:
        if not self.runner:
            return
        server = self.runner.server_running()
        gui = self.runner.gui_running()
        st = "disabled" if self._busy else "normal"
        for b in self._tiles.values():
            b.state(["!disabled"] if st == "normal" else ["disabled"])
        if "server" in self._tiles:
            self._tiles["server"].config(text="Stop Server" if server else "Run Server")
            self._tiles["gui"].config(text="Stop GUI" if gui else "Run GUI")

    def _poll(self) -> None:
        while True:
            try:
                self._results.get_nowait()()
            except queue.Empty:
                break
        self._update_tiles()
        self.after(1000, self._poll)

    # ---- background tasks --------------------------------------------
    def _run_task(self, work: Callable[[], object], done: Callable[[object], None],
                  busy_text: str) -> None:
        self._busy = True
        self._set_status(busy_text)
        self.bar.start(12)
        self._update_tiles()

        def target():
            try:
                result: object = work()
                err = None
            except Exception as exc:  # surfaced to the user, details in logs
                result, err = None, exc

            def finish():
                self._busy = False
                self.bar.stop()
                if err is not None:
                    self._error(err)
                else:
                    done(result)
                self._update_tiles()

            self._results.put(finish)

        threading.Thread(target=target, daemon=True).start()

    def _error(self, exc: Exception) -> None:
        self._set_status("Something went wrong.")
        messagebox.showerror("Error", f"{exc}\n\nDetails are in the logs:\n{config.LOG_DIR}")

    def _open_logs(self) -> None:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        proc.open_path(config.LOG_DIR)

    # ---- startup -----------------------------------------------------
    def _startup(self) -> None:
        if not self.state_.installed:
            return
        self._activate()
        if not installer.env_present(self.state_.code_dir):
            self._env_dialog(self._autostart_server)
        else:
            self._autostart_server()

    def _activate(self) -> None:
        """Equivalent of 'cd <code dir>; activate .venv' — all commands use the venv python."""
        self.runner = Runner(self.state_.code_dir)
        self._update_tiles()

    def _autostart_server(self) -> None:
        if not self.runner:
            return
        if self.runner.start_server() == "external":
            self._set_status(
                f"Port {config.SERVER_PORT} is in use — using the server already running there."
            )
        else:
            self._set_status("Server starting…")

    # ---- install -----------------------------------------------------
    def _on_install(self) -> None:
        self._run_task(
            lambda: installer.install(self._progress),
            self._installed,
            "Installing…",
        )

    def _progress(self, text: str) -> None:
        self._results.put(lambda: self._set_status(text))

    def _installed(self, st) -> None:
        self.state_ = st
        self._activate()
        self._env_dialog(lambda: (self._build_tiles(), self._autostart_server()))

    def _env_dialog(self, on_finish: Callable[[], None]) -> None:
        code_dir = self.state_.code_dir
        dlg = tk.Toplevel(self)
        dlg.title("Add your .env file")
        dlg.transient(self)
        dlg.resizable(False, False)
        body = ttk.Frame(dlg, padding=18)
        body.pack()
        ttk.Label(
            body, wraplength=440, justify="left",
            text="ResumeWriter is installed. Copy your .env file into the folder below "
                 "(replacing any existing one). Note: .env.example is not enough — "
                 "the file must be named .env.",
        ).pack(anchor="w")
        path_var = tk.StringVar(value=str(code_dir))
        entry = ttk.Entry(body, textvariable=path_var, state="readonly", width=62)
        entry.pack(fill="x", pady=10)
        status = ttk.Label(body)
        status.pack(anchor="w")
        row = ttk.Frame(body)
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Open folder", command=lambda: proc.open_path(code_dir)).pack(side="left")

        def finish():
            if not installer.env_present(code_dir):
                if not messagebox.askyesno(
                    "No .env found", "No .env file was found yet. Finish anyway?", parent=dlg
                ):
                    return
            dlg.destroy()
            on_finish()

        ttk.Button(row, text="Finish", command=finish).pack(side="right")
        dlg.protocol("WM_DELETE_WINDOW", finish)

        def check():
            if not dlg.winfo_exists():
                return
            ok = installer.env_present(code_dir)
            status.config(text=".env found ✓" if ok else ".env not found yet")
            dlg.after(1000, check)

        check()
        dlg.grab_set()

    # ---- server / gui ------------------------------------------------
    def _on_server(self) -> None:
        r = self.runner
        if r.server_running():
            if r.server_is_external():
                pid = r.external_server_pid()
                what = f"process {pid}" if pid else "the process"
                if not messagebox.askyesno(
                    "Stop server",
                    f"This server was not started by the launcher (port {config.SERVER_PORT}).\n"
                    f"Stop {what}?",
                ):
                    return
            self._run_task(self._stop_server, lambda _: self._set_status("Server stopped."),
                           "Stopping server…")
        else:
            self._set_status(
                "Server starting…" if r.start_server() == "started"
                else f"Using the server already running on port {config.SERVER_PORT}."
            )

    def _stop_server(self) -> None:
        r = self.runner
        r.stop_gui()  # the GUI is useless without the server
        r.stop_server()
        if r.server_is_external() and not r.stop_external_server():
            raise RuntimeError(f"Could not stop the process using port {config.SERVER_PORT}.")

    def _on_gui(self) -> None:
        r = self.runner
        if r.gui_running():
            self._run_task(r.stop_gui, lambda _: self._set_status("GUI stopped."), "Stopping GUI…")
            return

        def work():
            if not r.server_running():
                r.start_server()
                if not r.wait_for_server():
                    raise RuntimeError(
                        "The server did not start. Check that your .env is correct "
                        "and see the server log."
                    )
            r.start_gui()

        self._run_task(work, lambda _: self._set_status("GUI started."), "Starting server and GUI…")

    # ---- update / uninstall ------------------------------------------
    def _on_update(self) -> None:
        if not messagebox.askyesno(
            "Update", "Update ResumeWriter to the latest version?\n"
                      "The server and GUI will be stopped and the launcher will restart."
        ):
            return

        def work():
            self.runner.stop_all()
            return installer.update(self._progress)

        self._run_task(work, lambda _: self._restart(), "Updating…")

    def _on_uninstall(self) -> None:
        if not messagebox.askyesno(
            "Uninstall", "Remove ResumeWriter and everything in its folder (including your "
                         ".env)?\nThis cannot be undone.", icon="warning",
        ):
            return

        def work():
            self.runner.stop_all()
            if self.runner.server_is_external():
                self.runner.stop_external_server()
            installer.uninstall()

        def done(_):
            self.state_ = state.load()
            self.runner = None
            self._build_tiles()

        self._run_task(work, done, "Uninstalling…")

    # ---- shutdown ----------------------------------------------------
    def _on_close(self) -> None:
        if self._busy and not messagebox.askokcancel(
            "Quit", "An operation is still running. Quit anyway?"
        ):
            return
        self._set_status("Stopping services…")
        self.update_idletasks()
        if self.runner:
            self.runner.stop_all()
        self.destroy()
