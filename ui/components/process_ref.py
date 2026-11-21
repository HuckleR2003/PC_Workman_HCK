"""ui.components.process_ref - one way to point at a process (2026-11-20).

There were three process tooltips (ui/components/process_tooltip.py,
hck_gpt/tooltip.py and one inside yourpc_page.py) and Activity Memory had
none. Every list of processes now uses this:

    process_ref.bind([row, name_label, value_label], "opera.exe", win)

  hover         the row turns a dark lime-to-violet tint and, after a short
                pause, a card shows what the process is (process library)
                and how it lives here (recorded history: every day for N
                days, N of the last 7)
  click         when the window has a Process Center: a note in the top
                right, "Click twice to open the Process Center", for 2 s
  second click  within 2 s: opens the Process Center on that process

Without a Process Center (until phase 2) a click does nothing extra.
"""
from __future__ import annotations

import time
import tkinter as tk

from utils.fonts import UI as _BODY, MONO as _MONO

HOVER_BG = "#31265a"        # the row under the cursor (50% stronger, Marcin 2026-11-20)
ACCENT_FROM = "#3f6212"     # dark lime  (card edge, left)
ACCENT_TO = "#4c1d95"       # dark violet (card edge, right)
CARD_BG = "#0f1219"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
HINT_ACCENT = "#a3e635"

SHOW_DELAY_MS = 350
DOUBLE_WINDOW_S = 2.0

_TXT = {
    "hint_pre": {"pl": "Kliknij dwa razy, by przejść do ", "en": "Click twice to open the "},
    "hint_name": {"pl": "Centrum informacji o procesach", "en": "Process Center"},
    "unknown": {"pl": "Nie ma go jeszcze w bazie procesów.", "en": "Not in the process library yet."},
    "here": {"pl": "Na tym komputerze: ", "en": "On this PC: "},
}


def _lang() -> str:
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(key: str) -> str:
    return _TXT[key][_lang()]


def _blend(c1: str, c2: str, k: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def card_lines(process_name: str) -> tuple[str, list[str]]:
    """(title, lines) for the hover card. Kept apart from Tk for tests."""
    title = process_name
    lines: list[str] = []
    try:
        from hck_gpt.process_library import process_library
        info = process_library.get_process_info(process_name)
    except Exception:
        info = None
    if info:
        title = info.get("name") or process_name
        vendor = info.get("vendor")
        if vendor:
            lines.append(vendor)
        if info.get("description"):
            lines.append(info["description"])
        tail = []
        if info.get("typical_cpu"):
            tail.append(f"CPU {info['typical_cpu']}")
        if info.get("typical_ram"):
            tail.append(f"RAM {info['typical_ram']}")
        if tail:
            lines.append("  ·  ".join(tail))
    else:
        lines.append(_tx("unknown"))
    try:
        from core.process_history import presence, describe
        lines.append(_tx("here") + describe(presence(process_name), _lang()))
    except Exception:
        pass
    return title, lines


class _Card:
    """One shared hover card for the whole program."""

    win = None

    @classmethod
    def show(cls, anchor, process_name, x_root, y_root):
        cls.hide()
        title, lines = card_lines(process_name)
        top = tk.Toplevel(anchor)
        top.wm_overrideredirect(True)
        try:
            top.wm_attributes("-topmost", True)
        except Exception:
            pass
        edge = tk.Canvas(top, height=3, highlightthickness=0, bg=CARD_BG)
        edge.pack(fill="x")
        body = tk.Frame(top, bg=CARD_BG, padx=12, pady=8)
        body.pack(fill="both")
        tk.Label(body, text=title, font=(_BODY, 9, "bold"), bg=CARD_BG, fg=TEXT,
                 anchor="w").pack(fill="x")
        tk.Label(body, text=process_name, font=(_MONO, 7), bg=CARD_BG, fg=MUTED,
                 anchor="w").pack(fill="x", pady=(0, 4))
        for ln in lines:
            tk.Label(body, text=ln, font=(_BODY, 8), bg=CARD_BG, fg=TEXT, anchor="w",
                     justify="left", wraplength=320).pack(fill="x")
        top.update_idletasks()
        w = top.winfo_reqwidth()
        for i in range(0, w, 4):
            edge.create_rectangle(i, 0, i + 4, 3, outline="",
                                  fill=_blend(ACCENT_FROM, ACCENT_TO, i / max(w, 1)))
        sw = top.winfo_screenwidth()
        x = min(x_root + 18, sw - w - 8)
        top.wm_geometry(f"+{x}+{y_root + 14}")
        cls.win = top

    @classmethod
    def hide(cls):
        if cls.win is not None:
            try:
                cls.win.destroy()
            except Exception:
                pass
            cls.win = None


class _Hint:
    """'Click twice to open the Process Center' in the window's top right."""

    win = None
    after = None

    @classmethod
    def show(cls, root):
        cls.hide()
        top = tk.Toplevel(root)
        top.wm_overrideredirect(True)
        try:
            top.wm_attributes("-topmost", True)
        except Exception:
            pass
        f = tk.Frame(top, bg="#11151d", highlightthickness=1,
                     highlightbackground=ACCENT_TO, padx=10, pady=6)
        f.pack()
        tk.Label(f, text=_tx("hint_pre"), font=(_BODY, 8), bg="#11151d",
                 fg=TEXT).pack(side="left")
        tk.Label(f, text=_tx("hint_name"), font=(_BODY, 8, "bold"), bg="#11151d",
                 fg=HINT_ACCENT).pack(side="left")
        top.update_idletasks()
        try:
            rx = root.winfo_rootx() + root.winfo_width() - top.winfo_reqwidth() - 16
            ry = root.winfo_rooty() + 12
        except Exception:
            rx, ry = 40, 40
        top.wm_geometry(f"+{rx}+{ry}")
        cls.win = top
        cls.after = root.after(int(DOUBLE_WINDOW_S * 1000), cls.hide)

    @classmethod
    def hide(cls):
        if cls.win is not None:
            try:
                if cls.after:
                    cls.win.after_cancel(cls.after)
            except Exception:
                pass
            try:
                cls.win.destroy()
            except Exception:
                pass
        cls.win, cls.after = None, None


def _center(win):
    fn = getattr(win, "open_process_center", None)
    return fn if callable(fn) else None


def bind(widgets, process_name, win=None) -> None:
    """Make a row of widgets point at one process. The first widget is the
    row: its background and every child's change together on hover.
    process_name may be a function returning the current name, for rows
    that show a different process on every refresh (Dashboard TOP 5)."""
    if not widgets or not process_name:
        return
    name_of = process_name if callable(process_name) else (lambda: process_name)
    widgets = [w for w in widgets if w is not None]
    row = widgets[0]
    state = {"bg": {}, "after": None, "last_click": 0.0}

    def _paint(on):
        for w in widgets:
            try:
                if on:
                    state["bg"].setdefault(w, w.cget("bg"))
                    w.config(bg=HOVER_BG)
                elif w in state["bg"]:
                    w.config(bg=state["bg"][w])
            except Exception:
                pass

    def _enter(e=None):
        _paint(True)
        if state["after"]:
            try:
                row.after_cancel(state["after"])
            except Exception:
                pass
        name = name_of()
        if not name:
            return
        x, y = (e.x_root, e.y_root) if e is not None else (row.winfo_rootx(), row.winfo_rooty())
        state["after"] = row.after(SHOW_DELAY_MS, lambda: _Card.show(row, name, x, y))

    def _leave(e=None):
        # leaving a child into its own row is not leaving the row
        try:
            under = row.winfo_containing(row.winfo_pointerx(), row.winfo_pointery())
        except Exception:
            under = None
        if under is not None and (under is row or str(under).startswith(str(row) + ".")):
            return
        _paint(False)
        if state["after"]:
            try:
                row.after_cancel(state["after"])
            except Exception:
                pass
            state["after"] = None
        _Card.hide()

    def _click(e=None):
        open_fn = _center(win)
        name = name_of()
        if open_fn is None or not name:
            return
        now = time.time()
        if now - state["last_click"] <= DOUBLE_WINDOW_S:
            state["last_click"] = 0.0
            _Hint.hide()
            _Card.hide()
            open_fn(name)
            return
        state["last_click"] = now
        try:
            _Hint.show(row.winfo_toplevel())
        except Exception:
            pass

    for w in widgets:
        try:
            w.bind("<Enter>", _enter, add="+")
            w.bind("<Leave>", _leave, add="+")
            w.bind("<Button-1>", _click, add="+")
            if _center(win):
                w.config(cursor="hand2")
        except Exception:
            pass
