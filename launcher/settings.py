"""Settings window: edit the app's .env as key/value rows."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, List

from . import envfile
from .theme import BG, FG, FONT, MUTED, OK, PANEL, WARN


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, code_dir: Path, first_run: bool,
                 on_close: Callable[[bool], None]):
        super().__init__(parent)
        self.code_dir = code_dir
        self._on_close = on_close
        self._rows: List[dict] = []
        self._show_values = tk.BooleanVar(value=False)
        self._saved = False
        self.title("Settings")
        self.configure(bg=BG)
        self.geometry("640x540")
        self.minsize(560, 420)
        self.transient(parent)

        pairs, source = envfile.load_for_edit(code_dir)
        if source == "env":
            note = "Environment variables for ResumeWriter (stored in its .env file)."
        elif source == "example":
            note = ("Prefilled from .env.example — fill in your values, then press Save "
                    "to create your .env.")
        else:
            note = "No variables yet — add them below, then press Save to create your .env."
        if first_run:
            note = "ResumeWriter is installed. " + note

        ttk.Label(self, text="Settings", font=(FONT, 16, "bold")).pack(
            anchor="w", padx=16, pady=(14, 0))
        ttk.Label(self, text=note, style="Muted.TLabel", wraplength=600, justify="left").pack(
            anchor="w", padx=16, pady=(2, 8))

        head = ttk.Frame(self)
        head.pack(fill="x", padx=16)
        head.columnconfigure(0, weight=2, uniform="k")
        head.columnconfigure(1, weight=3, uniform="k")
        ttk.Label(head, text="Key", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text="Value", style="Muted.TLabel").grid(row=0, column=1, sticky="w",
                                                                   padx=(6, 0))

        # Scrollable rows
        holder = ttk.Frame(self)
        holder.pack(fill="both", expand=True, padx=16, pady=(2, 6))
        self.canvas = tk.Canvas(holder, bg=BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.rows_frame = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>", lambda _e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.rows_frame.columnconfigure(0, weight=2, uniform="k")
        self.rows_frame.columnconfigure(1, weight=3, uniform="k")
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", lambda _e: self.canvas.yview_scroll(-2, "units"))
        self.bind_all("<Button-5>", lambda _e: self.canvas.yview_scroll(2, "units"))

        for k, v in pairs:
            self._add_row(k, v)
        if not pairs:
            self._add_row()

        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=16, pady=(4, 14))
        ttk.Button(bar, text="+ Add variable", command=lambda: self._add_row(focus=True)).pack(
            side="left")
        ttk.Checkbutton(bar, text="Show values", variable=self._show_values,
                        command=self._apply_mask, style="TCheckbutton").pack(side="left", padx=12)
        ttk.Button(bar, text="Save", command=self._save).pack(side="right")
        ttk.Button(bar, text="Cancel", command=self._cancel).pack(side="right", padx=8)
        self.status = tk.Label(self, bg=BG, fg=MUTED, font=(FONT, 9))
        self.status.pack(anchor="w", padx=16, pady=(0, 8))

        self._initial = self._current_pairs()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.grab_set()
        self.focus_set()

    # ---- rows --------------------------------------------------------
    def _wheel(self, event) -> None:
        step = -1 if event.delta > 0 else 1
        if sys.platform == "win32":
            step = int(-event.delta / 120) or step
        self.canvas.yview_scroll(step, "units")

    def _add_row(self, key: str = "", value: str = "", focus: bool = False) -> None:
        r = len(self._rows)
        kvar, vvar = tk.StringVar(value=key), tk.StringVar(value=value)
        kent = ttk.Entry(self.rows_frame, textvariable=kvar)
        vent = ttk.Entry(self.rows_frame, textvariable=vvar,
                         show="" if self._show_values.get() else "•")
        kent.grid(row=r, column=0, sticky="ew", pady=3)
        vent.grid(row=r, column=1, sticky="ew", padx=(6, 0), pady=3)
        rm = ttk.Button(self.rows_frame, text="✕", width=3)
        rm.grid(row=r, column=2, padx=(6, 0))
        row = {"k": kvar, "v": vvar, "kent": kent, "vent": vent, "rm": rm}
        rm.configure(command=lambda row=row: self._remove_row(row))
        self._rows.append(row)
        if focus:
            self.update_idletasks()
            self.canvas.yview_moveto(1.0)
            kent.focus_set()

    def _remove_row(self, row: dict) -> None:
        for w in ("kent", "vent", "rm"):
            row[w].destroy()
        self._rows.remove(row)

    def _apply_mask(self) -> None:
        for row in self._rows:
            row["vent"].configure(show="" if self._show_values.get() else "•")

    def _current_pairs(self):
        """(key, value) per row, skipping rows left completely empty."""
        out = [(row["k"].get().strip(), row["v"].get()) for row in self._rows]
        return [p for p in out if p != ("", "")]

    # ---- actions -----------------------------------------------------
    def _save(self) -> None:
        pairs = self._current_pairs()
        for k, _ in pairs:
            if not k:
                messagebox.showerror("Settings", "A value has no key. Add a key or remove the row.",
                                     parent=self)
                return
        err = envfile.validate(pairs)
        if err:
            messagebox.showerror("Settings", err, parent=self)
            return
        try:
            envfile.save(self.code_dir, pairs)
        except OSError as exc:
            messagebox.showerror("Settings", f"Could not save .env:\n{exc}", parent=self)
            return
        self._saved = True
        self._finish()

    def _cancel(self) -> None:
        if self._current_pairs() != self._initial and not messagebox.askyesno(
            "Discard changes?", "You have unsaved changes. Close without saving?", parent=self
        ):
            return
        self._finish()

    def _finish(self) -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(seq)
        self.grab_release()
        self.destroy()
        self._on_close(self._saved)
