"""Single-screen tkinter launcher UI (dark theme, burgundy accents)."""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from . import config, installer, proc, state
from .settings import SettingsWindow
from .runner import Runner

from .theme import (ACCENT, ACCENT_BRIGHT, BAD, BG, BORDER, FG, FG_LOG, FONT, MUTED, OFF, OK,
                    PANEL, WARN, apply_theme)

LOG_FILES = {"Server": "server.log", "GUI": "gui.log", "Install": "install.log",
             "Update": "update.log"}

SERVER_TEXT = {
    "running": ("running", OK), "starting": ("starting…", WARN),
    "external": (f"running (existing instance on port {config.SERVER_PORT})", OK),
    "exited": ("stopped unexpectedly — see logs", BAD), "stopped": ("stopped", OFF),
}
GUI_TEXT = {
    "running": ("running", OK), "exited": ("exited — see logs", BAD), "stopped": ("stopped", OFF),
}



class App(tk.Tk):
    BASE_H = 440
    LOG_H = 230

    def __init__(self, restart: Callable[[], None]):
        super().__init__()
        self.title("ResumeWriter Launcher")
        self.geometry(f"540x{self.BASE_H}")
        self.minsize(500, 400)
        apply_theme(self)
        self._restart = restart
        self._busy = False
        self._logs_visible = False
        self._last_log_text = None
        self._results: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self.state_ = state.load()
        self.runner: Optional[Runner] = None
        self._tiles: dict[str, ttk.Button] = {}

        if not self.state_.installed:
            try:
                installer.find_system_python()
            except installer.PythonNotFound as exc:
                self.withdraw()
                messagebox.showerror("Python required", str(exc))
                self.destroy()
                sys.exit(1)

        ttk.Label(self, text="ResumeWriter", style="Title.TLabel").pack(pady=(16, 4))
        self.gear = ttk.Button(self, text="\u2699", style="Icon.TButton", width=3,
                               command=lambda: self._open_settings())
        self.tile_frame = ttk.Frame(self)
        self.tile_frame.pack(fill="both", expand=True, padx=20, pady=8)

        self.activity = ttk.Label(self, text="", anchor="center", style="Muted.TLabel")
        self.activity.pack(fill="x", padx=20)
        self.state_row = ttk.Frame(self)
        self.state_row.pack(pady=(2, 4))
        self.server_lbl = tk.Label(self.state_row, bg=BG, font=(FONT, 10))
        self.gui_lbl = tk.Label(self.state_row, bg=BG, font=(FONT, 10))
        self.server_lbl.pack(side="left", padx=10)
        self.gui_lbl.pack(side="left", padx=10)
        self.bar = ttk.Progressbar(self, mode="indeterminate")
        self.bar.pack(fill="x", padx=20, pady=(2, 6))

        self.footer = ttk.Frame(self)
        self.footer.pack(fill="x", padx=20, pady=(0, 12), side="bottom")
        self.log_btn = ttk.Button(self.footer, text="Show logs", command=self._toggle_logs)
        self.log_btn.pack(side="left")
        ttk.Button(self.footer, text="Open log file", command=self._open_log_file).pack(
            side="right")

        # Log panel (hidden until toggled)
        self.log_frame = ttk.Frame(self)
        top = ttk.Frame(self.log_frame)
        top.pack(fill="x", pady=(0, 4))
        ttk.Label(top, text="Log:", style="Muted.TLabel").pack(side="left")
        self.log_choice = tk.StringVar(value="Server" if self.state_.installed else "Install")
        combo = ttk.Combobox(top, textvariable=self.log_choice, values=list(LOG_FILES),
                             state="readonly", width=10)
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_logs(force=True))
        body = ttk.Frame(self.log_frame)
        body.pack(fill="both", expand=True)
        self.log_text = tk.Text(body, height=9, bg=PANEL, fg=FG_LOG, insertbackground=FG, bd=0,
                                highlightthickness=0, wrap="none", state="disabled",
                                font=("Consolas" if sys.platform == "win32" else "Menlo", 9),
                                selectbackground=BORDER)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_tiles()
        self.after(300, self._startup)
        self._poll_id = self.after(500, self._poll)

    def destroy(self) -> None:
        try:
            self.after_cancel(self._poll_id)
        except (AttributeError, tk.TclError):
            pass
        super().destroy()

    # ---- layout ------------------------------------------------------
    def _build_tiles(self) -> None:
        for child in self.tile_frame.winfo_children():
            child.destroy()
        self._tiles.clear()
        f = self.tile_frame
        for i in range(2):
            f.columnconfigure(i, weight=1, uniform="c")
            f.rowconfigure(i, weight=1, uniform="r")
        if not self.state_.installed:
            self.gear.place_forget()
            self._tile("install", "Install", self._on_install, 0, 0)
            self._tiles["install"].grid_configure(columnspan=2, rowspan=2)
            self._set_status("ResumeWriter is not installed.")
            self._update_tiles()
            return
        self.gear.place(relx=1.0, x=-12, y=12, anchor="ne")
        self._tile("server", "Run Server", self._on_server, 0, 0)
        self._tile("gui", "Run GUI", self._on_gui, 0, 1)
        self._tile("update", "Update", self._on_update, 1, 0)
        self._tile("uninstall", "Uninstall", self._on_uninstall, 1, 1, danger=True)
        self._set_status("Ready")
        self._update_tiles()

    def _tile(self, key, text, cmd, row, col, danger=False) -> None:
        style = "Danger.Tile.TButton" if danger else "Tile.TButton"
        b = ttk.Button(self.tile_frame, text=text, style=style, command=cmd)
        b.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        self._tiles[key] = b

    def _set_status(self, text: str) -> None:
        self.activity.config(text=text)

    def _update_tiles(self) -> None:
        for b in (*self._tiles.values(), self.gear):
            b.state(["disabled"] if self._busy else ["!disabled"])
        if not self.runner:
            self.server_lbl.config(text="")
            self.gui_lbl.config(text="")
            return
        sv = self.runner.server_state()
        gu = self.runner.gui_state()
        if "server" in self._tiles:
            self._tiles["server"].config(
                text="Stop Server" if sv in ("running", "starting", "external") else "Run Server")
            self._tiles["gui"].config(text="Stop GUI" if gu == "running" else "Run GUI")
        stext, scol = SERVER_TEXT[sv]
        gtext, gcol = GUI_TEXT[gu]
        self.server_lbl.config(text=f"● Server: {stext}", fg=scol)
        self.gui_lbl.config(text=f"● GUI: {gtext}", fg=gcol)

    def _poll(self) -> None:
        while True:
            try:
                self._results.get_nowait()()
            except queue.Empty:
                break
        self._update_tiles()
        if self._logs_visible:
            self._refresh_logs()
        self._poll_id = self.after(1000, self._poll)

    # ---- logs --------------------------------------------------------
    def _log_path(self):
        return config.LOG_DIR / LOG_FILES[self.log_choice.get()]

    def _toggle_logs(self) -> None:
        self._logs_visible = not self._logs_visible
        w = self.winfo_width()
        if self._logs_visible:
            self.log_frame.pack(fill="both", padx=20, pady=(0, 6), before=self.footer)
            self.log_btn.config(text="Hide logs")
            self.geometry(f"{w}x{self.winfo_height() + self.LOG_H}")
            self._refresh_logs(force=True)
        else:
            self.log_frame.pack_forget()
            self.log_btn.config(text="Show logs")
            self.geometry(f"{w}x{max(self.BASE_H, self.winfo_height() - self.LOG_H)}")

    def _refresh_logs(self, force: bool = False) -> None:
        path = self._log_path()
        try:
            with open(path, "rb") as fh:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 60_000))
                text = fh.read().decode("utf-8", "replace")
            text = "\n".join(text.splitlines()[-400:])
        except OSError:
            text = "(no log yet)"
        if text == self._last_log_text and not force:
            return
        self._last_log_text = text
        at_bottom = self.log_text.yview()[1] > 0.98
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", text)
        self.log_text.config(state="disabled")
        if at_bottom or force:
            self.log_text.see("end")

    def _show_log(self, name: str) -> None:
        self.log_choice.set(name)
        if self._logs_visible:
            self._refresh_logs(force=True)

    def _open_log_file(self) -> None:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = self._log_path()
        path.touch(exist_ok=True)
        proc.open_path(path)

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
                    self._set_status("Ready")
                    done(result)
                self._update_tiles()

            self._results.put(finish)

        threading.Thread(target=target, daemon=True).start()

    def _error(self, exc: Exception) -> None:
        self._set_status("Something went wrong — see logs.")
        messagebox.showerror("Error", f"{exc}\n\nDetails are in the logs:\n{config.LOG_DIR}")

    def _progress(self, text: str) -> None:
        self._results.put(lambda: self._set_status(text))

    # ---- startup -----------------------------------------------------
    def _startup(self) -> None:
        if not self.state_.installed:
            if config.AUTO_INSTALL_ON_FIRST_RUN and not self.state_.auto_install_attempted:
                state.mark_auto_install_attempted()  # at most once, even if it fails
                self.state_.auto_install_attempted = True
                self._on_install()
            return
        self._activate()
        if not installer.env_present(self.state_.code_dir):
            self._open_settings(first_run=True)
        else:
            self._autostart_server()

    def _activate(self) -> None:
        """Equivalent of 'cd <code dir>; activate .venv' — all commands use the venv python."""
        self.runner = Runner(self.state_.code_dir)
        self._update_tiles()

    def _autostart_server(self) -> None:
        if self.runner:
            self.runner.start_server()  # no-op if already running or port is taken
            self._update_tiles()

    # ---- install ------------------------------------------------------
    def _on_install(self) -> None:
        self._show_log("Install")
        self._run_task(lambda: installer.install(self._progress), self._installed, "Installing…")

    def _installed(self, st) -> None:
        self.state_ = st
        self._activate()
        self._show_log("Server")
        self._build_tiles()
        self._open_settings(first_run=True)

    def _open_settings(self, first_run: bool = False) -> None:
        if not self.state_.installed or getattr(self, "_settings_open", False):
            return
        self._settings_open = True
        had_env = installer.env_present(self.state_.code_dir)

        def closed(saved: bool) -> None:
            self._settings_open = False
            if not self.runner:
                return
            sv = self.runner.server_state()
            if saved and sv in ("running", "starting"):
                messagebox.showinfo("Settings saved",
                                    "Saved. Restart the server for the changes to take effect.")
            elif installer.env_present(self.state_.code_dir) and (
                not had_env or sv == "exited"
            ):
                self._autostart_server()
            elif first_run and not installer.env_present(self.state_.code_dir):
                self._set_status("No .env yet — open Settings (⚙) to add your configuration.")

        SettingsWindow(self, self.state_.code_dir, first_run, closed)

    # ---- server / gui ------------------------------------------------
    def _on_server(self) -> None:
        r = self.runner
        if r.server_state() in ("running", "starting", "external"):
            if r.server_is_external():
                pid = r.external_server_pid()
                what = f"process {pid}" if pid else "the process"
                if not messagebox.askyesno(
                    "Stop server",
                    f"This server was not started by the launcher (port {config.SERVER_PORT}).\n"
                    f"Stop {what}?",
                ):
                    return
            self._show_log("Server")
            self._run_task(self._stop_server, lambda _: None, "Stopping server…")
        else:
            self._show_log("Server")
            r.start_server()
            self._update_tiles()

    def _stop_server(self) -> None:
        r = self.runner
        r.stop_gui()  # the GUI is useless without the server
        r.stop_server()
        if r.server_is_external() and not r.stop_external_server():
            raise RuntimeError(f"Could not stop the process using port {config.SERVER_PORT}.")

    def _on_gui(self) -> None:
        r = self.runner
        if r.gui_running():
            self._run_task(r.stop_gui, lambda _: None, "Stopping GUI…")
            return
        server_up = r.server_state() in ("running", "external")

        def work():
            # start_server() is a no-op if our server is already up/starting or the port is held.
            if r.server_state() != "running" and r.server_state() != "external":
                r.start_server()
                if not r.wait_for_server():
                    raise RuntimeError(
                        "The server did not start. Check that your .env is correct "
                        "and see the server log."
                    )
            r.start_gui()

        self._show_log("GUI")
        self._run_task(work, lambda _: None,
                       "Starting GUI…" if server_up else "Waiting for server, then starting GUI…")

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

        self._show_log("Update")
        self._run_task(work, lambda _: self._restart(), "Updating…")

    def _confirm_uninstall(self):
        """Themed confirm dialog with a 'keep settings' checkbox. Returns None or keep(bool)."""
        dlg = tk.Toplevel(self)
        dlg.title("Uninstall")
        dlg.configure(bg=BG)
        dlg.transient(self)
        dlg.resizable(False, False)
        keep = tk.BooleanVar(value=False)
        result = {"ok": False}
        body = ttk.Frame(dlg, padding=18)
        body.pack()
        ttk.Label(body, wraplength=380, justify="left",
                  text="Remove ResumeWriter and everything in its install folder?\n"
                       "This cannot be undone.").pack(anchor="w")
        ttk.Checkbutton(body, text="Keep my settings (.env) for a future install",
                        variable=keep).pack(anchor="w", pady=(12, 2))
        ttk.Label(body, wraplength=380, justify="left", style="Muted.TLabel",
                  text="A private copy is stored in the launcher's folder and used to prefill "
                       "Settings next time. It is deleted once you save your settings again, "
                       "or if you uninstall without this option.").pack(anchor="w")
        row = ttk.Frame(body)
        row.pack(fill="x", pady=(16, 0))

        def ok():
            result["ok"] = True
            dlg.destroy()

        ttk.Button(row, text="Uninstall", command=ok).pack(side="right")
        ttk.Button(row, text="Cancel", command=dlg.destroy).pack(side="right", padx=8)
        dlg.grab_set()
        self.wait_window(dlg)
        return keep.get() if result["ok"] else None

    def _on_uninstall(self) -> None:
        keep = self._confirm_uninstall()
        if keep is None:
            return

        def work():
            self.runner.stop_all()
            if self.runner.server_is_external():
                self.runner.stop_external_server()
            installer.uninstall(keep_settings=keep)

        def done(_):
            self.state_ = state.load()
            self.runner = None
            self._build_tiles()
            self._update_tiles()

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
