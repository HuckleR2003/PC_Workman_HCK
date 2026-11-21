# ui/diag_window.py
"""
The diagnostic console as a PC Workman window (2026-11-15).

Settings > "Show diagnostic console at startup" opens this instead of a cmd
window: same look as the startup error window, a large log area that fills
live while the program loads, and it closes by itself 3 seconds after the
main window is ready. "Keep open" stops the countdown.

Why its own thread and its own Tk: it has to be on screen BEFORE the main
window exists (that is the whole point: watching the startup), and the main
window is built on the main thread much later. The splash screen already
works the same way. Lines reach it through a queue; the window polls the
queue on its own thread, so no Tk call ever crosses threads.

`--console` still opens a real console. That one is for the case where Tk
itself cannot start, and then this window could not start either.
"""
from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import os
import queue
import threading

_BG, _PANEL, _FG, _SUB = "#0b0d12", "#141821", "#e5e7eb", "#9ca3af"
_ACCENT = "#8b5cf6"
_LINE_COLORS = {"[+]": "#34d399", "[!]": "#f59e0b", "[-]": "#f87171",
                "[~]": "#7c8aa5", "[i]": "#60a5fa", "[*]": "#cbd5e1"}

_TEXT = {
    "en": {"title": "PC Workman - diagnostic console",
           "lead": "What PC Workman loads while it starts.",
           "closing": "Closes in {n} s", "ready": "Ready",
           "keep": "Keep open", "kept": "Stays open",
           "copy": "Copy log", "copied": "Copied",
           "open_log": "Open log", "close": "Close"},
    "pl": {"title": "PC Workman - konsola diagnostyczna",
           "lead": "Co PC Workman wczytuje podczas uruchamiania.",
           "closing": "Zamknięcie za {n} s", "ready": "Gotowe",
           "keep": "Zostaw otwartą", "kept": "Zostaje otwarta",
           "copy": "Kopiuj log", "copied": "Skopiowano",
           "open_log": "Otwórz log", "close": "Zamknij"},
}

_state = {"thread": None, "queue": queue.Queue(), "close_in": None,
          "close_now": threading.Event(), "pinned": False}


def _lang() -> str:
    try:
        import json
        from utils.paths import APP_DIR
        with open(os.path.join(APP_DIR, "settings", "app_settings.json"),
                  encoding="utf-8") as f:
            return "pl" if str(json.load(f).get("language", "en")).lower() \
                .startswith("pl") else "en"
    except Exception:
        return "en"


def feed(text: str) -> None:
    """Called by utils.diag_console for every chunk the app prints. Nothing
    is queued once the window is gone, so a long session never piles up."""
    if is_open():
        _state["queue"].put(text)


def is_open() -> bool:
    t = _state["thread"]
    return bool(t and t.is_alive())


def close_after(ms: int) -> None:
    """Start the countdown (from any thread)."""
    _state["queue"].put(("__close_after__", int(ms)))


def close_now() -> None:
    _state["close_now"].set()


def start(initial_text: str = "") -> bool:
    """Open the window on its own thread. Returns False if it could not."""
    if is_open():
        return True
    ready = threading.Event()
    result = {"ok": False}

    def _run():
        try:
            _build_and_loop(initial_text, ready, result)
        except Exception:
            result["ok"] = False
        finally:
            ready.set()
            # The Tk objects of this window form reference cycles (callbacks
            # hold the window, the window holds the callbacks). If the main
            # thread's garbage collector frees them, Tcl aborts the process:
            # "Tcl_AsyncDelete: async handler deleted by the wrong thread"
            # (seen 2026-11-15, exit code 3). Collect them HERE, on the
            # thread that created them.
            import gc
            gc.collect()

    t = threading.Thread(target=_run, daemon=True, name="diag-window")
    _state["thread"] = t
    t.start()
    ready.wait(5.0)
    return result["ok"]


def _build_and_loop(initial_text, ready, result):
    import tkinter as tk
    try:
        from utils.fonts import UI as _F, MONO as _M
    except Exception:
        _F, _M = _FONT_UI, "Consolas"
    tx = _TEXT[_lang()]

    win = tk.Tk()
    # This window opens FIRST, so tkinter would make it the default root:
    # every image or variable created later without an explicit master (the
    # splash logo, icons in the main window) would land in THIS interpreter,
    # on another thread, and fail ("image pyimage1 doesn't exist" - seen
    # 2026-11-15, the splash showed no logo). It must never be the default.
    if getattr(tk, "_default_root", None) is win:
        tk._default_root = None
    win.title(tx["title"])
    win.configure(bg=_BG)
    win.minsize(460, 260)
    try:
        from utils.paths import BUNDLE_DIR
        ico = os.path.join(BUNDLE_DIR, "data", "icons", "PCWorkman.ico")
        if os.path.exists(ico):
            win.iconbitmap(ico)
    except Exception:
        pass

    tk.Frame(win, bg=_ACCENT, height=4).pack(fill="x", side="top")
    body = tk.Frame(win, bg=_BG)
    body.pack(fill="both", expand=True, padx=16, pady=(12, 12))

    head = tk.Frame(body, bg=_BG)
    head.pack(fill="x")
    status = tk.Label(head, text="", font=(_F, 9, "bold"), bg=_BG, fg=_ACCENT)
    status.pack(side="right")
    tk.Label(head, text=tx["title"], font=(_FONT_HDR, 12), bg=_BG,
             fg=_FG, anchor="w").pack(side="left")
    tk.Label(body, text=tx["lead"], font=(_F, 9), bg=_BG, fg=_SUB,
             anchor="w").pack(fill="x", pady=(2, 8))

    # buttons packed before the log, so the log is what gives way
    bar = tk.Frame(body, bg=_BG)
    bar.pack(fill="x", side="bottom", pady=(10, 0))

    box = tk.Frame(body, bg=_PANEL)
    box.pack(fill="both", expand=True)
    sb = tk.Scrollbar(box)
    sb.pack(side="right", fill="y")
    log = tk.Text(box, wrap="none", font=(_M, 9), bg=_PANEL, fg=_FG,
                  relief="flat", bd=0, padx=10, pady=8, height=18,
                  insertbackground=_FG, yscrollcommand=sb.set)
    log.pack(side="left", fill="both", expand=True)
    sb.configure(command=log.yview)
    for prefix, color in _LINE_COLORS.items():
        log.tag_configure(prefix, foreground=color)
    log.configure(state="disabled")

    def _append(text):
        log.configure(state="normal")
        for line in text.splitlines(keepends=True):
            tag = next((p for p in _LINE_COLORS if line.lstrip().startswith(p)),
                       None)
            log.insert("end", line, tag or ())
        log.configure(state="disabled")
        log.see("end")

    def _btn(text, command, primary=False):
        return tk.Button(bar, text=text, command=command, font=(_F, 9, "bold"),
                         bg=_ACCENT if primary else _PANEL,
                         fg="#ffffff" if primary else _FG,
                         activebackground=_ACCENT, activeforeground="#ffffff",
                         relief="flat", bd=0, padx=14, pady=6, cursor="hand2")

    def _keep():
        _state["pinned"] = True
        _state["close_in"] = None
        keep_btn.configure(text=tx["kept"], state="disabled")
        status.configure(text=tx["ready"] if _ready["v"] else "")

    def _copy():
        try:
            win.clipboard_clear()
            win.clipboard_append(log.get("1.0", "end-1c"))
            win.update()
            copy_btn.configure(text=tx["copied"])
            win.after(1500, lambda: copy_btn.winfo_exists()
                      and copy_btn.configure(text=tx["copy"]))
        except Exception:
            pass

    def _open_log():
        try:
            from utils import diag_console
            os.startfile(diag_console.startup_log_path())   # noqa: S606
        except Exception:
            pass

    def _close():
        try:
            win.destroy()
        except Exception:
            pass

    keep_btn = _btn(tx["keep"], _keep, primary=True)
    keep_btn.pack(side="left")
    copy_btn = _btn(tx["copy"], _copy)
    copy_btn.pack(side="left", padx=(8, 0))
    _btn(tx["open_log"], _open_log).pack(side="left", padx=(8, 0))
    _btn(tx["close"], _close).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", _close)

    # bottom-left of the work area: never on top of the logo in the centre
    win.update_idletasks()
    w, h = 640, 400
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+24+{max(sh - h - 90, 0)}")

    if initial_text:
        _append(initial_text)

    _ready = {"v": False}

    def _poll():
        if _state["close_now"].is_set():
            _close()
            return
        try:
            while True:
                item = _state["queue"].get_nowait()
                if isinstance(item, tuple) and item[0] == "__close_after__":
                    _ready["v"] = True
                    if not _state["pinned"]:
                        _state["close_in"] = item[1]
                else:
                    _append(str(item))
        except queue.Empty:
            pass
        left = _state["close_in"]
        if left is not None:
            if left <= 0:
                _close()
                return
            status.configure(text=tx["closing"].format(n=(left + 999) // 1000))
            _state["close_in"] = left - 100
        try:
            win.after(100, _poll)
        except Exception:
            pass

    result["ok"] = True
    ready.set()
    win.after(100, _poll)
    win.mainloop()
