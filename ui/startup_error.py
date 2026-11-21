# ui/startup_error.py
"""
The window the user sees when something is wrong (2026-11-14).

It replaces the diagnostic console. One plain sentence about what happened,
the technical details underneath, and two buttons that make a bug report a
ten-second job: "Copy details" and "Open log".

Two uses:
  fatal      the app could not start. No main window exists, so this builds
             its own Tk root and blocks until closed.
  non-fatal  the app is running but a component failed to load. Shown once
             as a child of the main window, does not block anything.

The strings live here and not in locales/*.json on purpose: this window has
to work when the locale files, the settings or half the app are the thing
that broke. If Tk itself is unusable it falls back to a native message box.
"""
from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import os
import sys

_TEXT = {
    "en": {
        "fatal_title": "PC Workman could not start",
        "fatal_lead": "Something stopped PC Workman during startup. "
                      "Nothing on your computer was changed.",
        "warn_title": "PC Workman started with problems",
        "warn_lead": "PC Workman is running, but some parts did not load. "
                     "Features that depend on them may be missing.",
        "what": "What happened",
        "details": "Details",
        "copy": "Copy details",
        "copied": "Copied",
        "open_log": "Open log",
        "close": "Close",
        "hint": "To report this, press \"Copy details\" and paste it into "
                "your message.",
        # Summaries, passed by key from startup.py (see show_startup_error).
        "sum_core": "A core part of the program could not be loaded.",
        "sum_ui": "The interface could not be loaded.",
        "sum_window": "The main window could not be created or stopped "
                      "working.",
        "sum_unexpected": "PC Workman stopped because of an unexpected error.",
    },
    "pl": {
        "fatal_title": "PC Workman nie mógł się uruchomić",
        "fatal_lead": "Coś zatrzymało PC Workmana podczas uruchamiania. "
                      "Nic na Twoim komputerze nie zostało zmienione.",
        "warn_title": "PC Workman uruchomił się z problemami",
        "warn_lead": "PC Workman działa, ale część elementów się nie "
                     "wczytała. Funkcje, które od nich zależą, mogą nie "
                     "działać.",
        "what": "Co się stało",
        "details": "Szczegóły",
        "copy": "Kopiuj szczegóły",
        "copied": "Skopiowano",
        "open_log": "Otwórz log",
        "close": "Zamknij",
        "hint": "Aby to zgłosić, kliknij „Kopiuj szczegóły” i wklej "
                "do wiadomości.",
        "sum_core": "Nie udało się wczytać podstawowej części programu.",
        "sum_ui": "Nie udało się wczytać interfejsu.",
        "sum_window": "Nie udało się utworzyć głównego okna albo przestało "
                      "ono działać.",
        "sum_unexpected": "PC Workman zatrzymał się z powodu "
                          "nieoczekiwanego błędu.",
    },
}

_BG, _PANEL, _FG, _SUB = "#0b0d12", "#141821", "#e5e7eb", "#9ca3af"
_RED, _AMBER = "#c0182a", "#f59e0b"


def _lang() -> str:
    """Saved UI language, read straight from the settings file: i18n may not
    have been initialised yet when startup fails."""
    try:
        import json
        from utils.paths import APP_DIR
        with open(os.path.join(APP_DIR, "settings", "app_settings.json"),
                  encoding="utf-8") as f:
            lang = str(json.load(f).get("language", "en")).lower()
        return "pl" if lang.startswith("pl") else "en"
    except Exception:
        return "en"


def build_report(summary: str, details: str = "") -> str:
    """Everything a bug report needs, as one block of plain text."""
    try:
        from utils.app_version import APP_VERSION
    except Exception:
        APP_VERSION = "?"
    try:
        import platform
        system = f"Windows {platform.version()} ({platform.machine()})"
    except Exception:
        system = "?"
    try:
        from utils import diag_console
        mode, tail = diag_console.MODE, diag_console.read_log_tail()
    except Exception:
        mode, tail = "?", ""
    parts = [
        f"PC Workman {APP_VERSION}",
        f"System: {system}",
        f"Build: {'exe' if getattr(sys, 'frozen', False) else 'source'}, "
        f"mode: {mode}",
        "",
        f"Problem: {summary}",
    ]
    if details:
        parts += ["", details.rstrip()]
    if tail:
        parts += ["", "--- startup.log (end) ---", tail.rstrip()]
    return "\n".join(parts)


def _open_log() -> None:
    try:
        from utils import diag_console
        path = diag_console.startup_log_path()
        if os.path.exists(path):
            os.startfile(path)                      # noqa: S606 (our own log)
        else:
            os.startfile(os.path.dirname(path))     # noqa: S606
    except Exception:
        pass


def _native_box(title: str, text: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)  # MB_ICONERROR
    except Exception:
        pass


def show_startup_error(summary: str, details: str = "", parent=None,
                       fatal: bool = True) -> None:
    """Show the window. Blocks when fatal, returns immediately otherwise.

    *summary* is either free text or one of the "sum_*" keys in _TEXT. A key
    is shown in the user's language; the report that gets copied always
    carries the English sentence, because we are the ones who read it.
    """
    tx = _TEXT[_lang()]
    title = tx["fatal_title"] if fatal else tx["warn_title"]
    lead = tx["fatal_lead"] if fatal else tx["warn_lead"]
    report = build_report(_TEXT["en"].get(summary, summary), details)
    summary = tx.get(summary, summary)

    try:
        import tkinter as tk
        try:
            from utils.fonts import UI as _F, MONO as _M
        except Exception:
            _F, _M = _FONT_UI, "Consolas"

        own_root = parent is None
        win = tk.Tk() if own_root else tk.Toplevel(parent)
        win.title(title)
        win.configure(bg=_BG)
        win.minsize(460, 320)
        try:
            from utils.paths import BUNDLE_DIR
            ico = os.path.join(BUNDLE_DIR, "data", "icons", "PCWorkman.ico")
            if os.path.exists(ico):
                win.iconbitmap(ico)
        except Exception:
            pass

        accent = _RED if fatal else _AMBER
        tk.Frame(win, bg=accent, height=4).pack(fill="x", side="top")

        body = tk.Frame(win, bg=_BG)
        body.pack(fill="both", expand=True, padx=18, pady=(14, 12))

        tk.Label(body, text=title, font=(_FONT_HDR, 13), bg=_BG,
                 fg=_FG, anchor="w").pack(fill="x")
        tk.Label(body, text=lead, font=(_F, 10), bg=_BG, fg=_SUB, anchor="w",
                 justify="left", wraplength=520).pack(fill="x", pady=(4, 10))

        tk.Label(body, text=tx["what"].upper(), font=(_F, 8, "bold"), bg=_BG,
                 fg=accent, anchor="w").pack(fill="x")
        tk.Label(body, text=summary, font=(_F, 10), bg=_BG, fg=_FG, anchor="w",
                 justify="left", wraplength=520).pack(fill="x", pady=(2, 10))

        # Buttons are packed before the text box so they keep their place
        # when the window is small: the text box takes what is left.
        bar = tk.Frame(body, bg=_BG)
        bar.pack(fill="x", side="bottom", pady=(10, 0))
        tk.Label(body, text=tx["hint"], font=(_F, 8), bg=_BG, fg=_SUB,
                 anchor="w", justify="left",
                 wraplength=520).pack(fill="x", side="bottom", pady=(6, 0))

        tk.Label(body, text=tx["details"].upper(), font=(_F, 8, "bold"),
                 bg=_BG, fg=_SUB, anchor="w").pack(fill="x")
        box = tk.Frame(body, bg=_PANEL)
        box.pack(fill="both", expand=True, pady=(2, 0))
        scroll = tk.Scrollbar(box)
        scroll.pack(side="right", fill="y")
        txt = tk.Text(box, height=9, wrap="word", font=(_M, 9), bg=_PANEL,
                      fg=_FG, relief="flat", bd=0, padx=8, pady=6,
                      insertbackground=_FG, yscrollcommand=scroll.set)
        txt.insert("1.0", report)
        txt.configure(state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        scroll.configure(command=txt.yview)

        def _btn(text, command, primary=False):
            return tk.Button(
                bar, text=text, command=command, font=(_F, 9, "bold"),
                bg=accent if primary else _PANEL, fg="#ffffff" if primary else _FG,
                activebackground=accent, activeforeground="#ffffff",
                relief="flat", bd=0, padx=14, pady=6, cursor="hand2")

        def _copy():
            try:
                win.clipboard_clear()
                win.clipboard_append(report)
                win.update()            # keep the clipboard after we close
                copy_btn.configure(text=tx["copied"])
                win.after(1500, lambda: copy_btn.winfo_exists()
                          and copy_btn.configure(text=tx["copy"]))
            except Exception:
                pass

        def _close():
            try:
                win.destroy()
            except Exception:
                pass

        copy_btn = _btn(tx["copy"], _copy, primary=True)
        copy_btn.pack(side="left")
        _btn(tx["open_log"], _open_log).pack(side="left", padx=(8, 0))
        _btn(tx["close"], _close).pack(side="right")

        win.protocol("WM_DELETE_WINDOW", _close)
        win.bind("<Escape>", lambda _e: _close())

        win.update_idletasks()
        w, h = max(win.winfo_reqwidth(), 580), max(win.winfo_reqheight(), 420)
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        w, h = min(w, sw - 40), min(h, sh - 80)
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{max((sh - h) // 3, 0)}")
        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(400, lambda: win.winfo_exists()
                      and win.attributes("-topmost", False))
            win.focus_force()
        except Exception:
            pass

        if own_root:
            win.mainloop()
    except Exception:
        _native_box(title, f"{lead}\n\n{summary}")
