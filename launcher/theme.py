"""Dark theme: near-black background, burgundy text, muted-gold accents."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ---- palette: near-black background, burgundy text, muted-gold accents --------
BG = "#120d0e"
PANEL = "#1c1416"
TILE = "#221719"
TILE_HOVER = "#2e1b20"
BORDER = "#4a3a2a"         # dim gold hairline
ACCENT = "#c8a96a"         # classy muted gold
ACCENT_BRIGHT = "#e0c68c"
FG = "#d9566f"             # burgundy text (lightened enough to read on dark)
FG_LOG = "#e07a90"
MUTED = "#9c5f6d"
DISABLED_FG = "#5e3b44"
OK, WARN, BAD, OFF = "#8fb89a", "#c8a96a", "#f0647c", "#7a6368"

FONT = "Segoe UI"
def apply_theme(root: tk.Tk) -> None:
    root.configure(bg=BG)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL, bordercolor=BORDER,
                lightcolor=BG, darkcolor=BG, troughcolor=PANEL, focuscolor=BG)
    s.configure("TFrame", background=BG)
    s.configure("TLabel", background=BG, foreground=FG)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("Title.TLabel", font=(FONT, 22, "bold"), foreground=ACCENT)
    s.configure("TButton", background=PANEL, foreground=FG, padding=(10, 5), borderwidth=1,
                bordercolor=BORDER)
    s.map("TButton", background=[("active", TILE_HOVER), ("disabled", PANEL)],
          foreground=[("active", ACCENT), ("disabled", DISABLED_FG)],
          bordercolor=[("active", ACCENT)])
    s.configure("Tile.TButton", background=TILE, foreground=FG, font=(FONT, 13, "bold"),
                padding=(10, 26), borderwidth=1, bordercolor=BORDER)
    s.map("Tile.TButton",
          background=[("disabled", PANEL), ("pressed", BORDER), ("active", TILE_HOVER)],
          foreground=[("disabled", DISABLED_FG), ("active", ACCENT_BRIGHT)],
          bordercolor=[("disabled", PANEL), ("active", ACCENT)])
    s.configure("Danger.Tile.TButton", background="#1f0f12", foreground="#e0586c")
    s.map("Danger.Tile.TButton",
          background=[("disabled", PANEL), ("pressed", BORDER), ("active", "#2c1015")],
          foreground=[("disabled", DISABLED_FG), ("active", "#f0647c")],
          bordercolor=[("disabled", PANEL), ("active", "#f0647c")])
    s.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL,
                bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT)
    s.configure("TEntry", fieldbackground=PANEL, foreground=FG, insertcolor=FG)
    s.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=FG,
                arrowcolor=ACCENT, selectbackground=PANEL, selectforeground=FG)
    s.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", FG)])
    root.option_add("*TCombobox*Listbox.background", PANEL)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", BORDER)
    root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_BRIGHT)
    s.configure("TCheckbutton", background=BG, foreground=MUTED)
    s.map("TCheckbutton", background=[("active", BG)], foreground=[("active", ACCENT_BRIGHT)])
    s.configure("Icon.TButton", font=(FONT, 15), padding=(8, 2), background=BG, borderwidth=0)
    s.map("Icon.TButton", background=[("active", TILE_HOVER)], foreground=[("active", ACCENT_BRIGHT), ("disabled", DISABLED_FG)])
    s.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG, arrowcolor=ACCENT,
                bordercolor=BG)
