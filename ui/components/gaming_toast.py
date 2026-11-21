# ui/components/gaming_toast.py
"""
Gaming launch toast - subtle 2-second notification when a game is detected.

Shows in bottom-right corner, no buttons, auto-dismisses with a progress bar.
Can be disabled from Settings -> Notifications -> Gaming launch reminders.

The games and their messages live in data/games.json (core/game_library.py):
own messages, a genre pool for the rest, and a "first time on this PC" line.

Public API
----------
show_gaming_toast(root, exe_name, lang='pl')
    -> Called when a game exe is detected starting.
       Reads settings to check if feature is enabled.
"""
from __future__ import annotations

from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import tkinter as tk
from typing import Callable, List, Optional

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = _FONT_UI, "Consolas"
_HDR  = _FONT_HDR
_BODY = _UIF
_MONO = _MONOF

# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = "#0b0e16"
_BORDER   = "#1c2534"
_TEXT     = "#e2e8f0"
_MUTED    = "#8a97ab"
_BAR_BG   = "#111827"
_EDGE_PAD = 18        # px from screen edge
_TOAST_W  = 300       # width
_TOAST_H  = 72        # height (compact - no buttons)
_TOAST_MAX_W = 460    # widest, at 100 %; a longer title wraps
_DURATION = 2200      # ms until auto-dismiss
_SLIDE_MS = 220       # slide-in animation duration
_BAR_H    = 3         # progress bar height

# ── Games and messages ────────────────────────────────────────────────────────
# The game list moved to data/games.json and core/game_library.py (2026-11-20):
# about 230 games with a genre and messages, genre pools for the rest, a
# different line the first time a game is seen on this PC.


def _canon(exe_lower: str) -> str:
    """The game's first .exe name in the library (one name per game)."""
    try:
        from core.game_library import by_exe
        g = by_exe(exe_lower)
        if g and g.get("exe"):
            return g["exe"][0]
    except Exception:
        pass
    return exe_lower


def _is_known(exe_lower: str) -> bool:
    try:
        from core.game_library import known_exes
        return exe_lower in known_exes(strict=True)
    except Exception:
        return False


def _pick(exe_lower: str, lang: str, exe_path: Optional[str] = None,
          first: Optional[bool] = False) -> tuple:
    """(title, subtitle, accent). first=None asks the library."""
    try:
        from core.game_library import message
        return message(exe_lower, lang, exe_path=exe_path, first=first)
    except Exception:
        return ("Dobrej zabawy!" if lang == "pl" else "Good luck, have fun!", None, "#3b82f6")


def _load_app_settings() -> dict:
    try:
        import os, json
        from utils.paths import APP_DIR
        path = os.path.join(APP_DIR, "settings", "app_settings.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class _GamingToast:
    """Minimal auto-dismissing gaming notification."""

    def __init__(self, root: tk.Misc, title: str, subtitle: Optional[str],
                 accent: str):
        self._root   = root
        self._accent = accent
        self._alive  = True

        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes("-alpha", 0.0)
        try:
            self._win.attributes("-toolwindow", True)
        except Exception:
            pass
        self._win.configure(bg=_BORDER)

        # ── Content ──────────────────────────────────────────────────────────
        inner = tk.Frame(self._win, bg=_BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        # Accent left bar
        tk.Frame(inner, bg=accent, width=3).pack(side="left", fill="y")

        body = tk.Frame(inner, bg=_BG)
        body.pack(side="left", fill="both", expand=True, padx=(10, 10), pady=(10, 6))

        # Controller icon + title
        title_row = tk.Frame(body, bg=_BG)
        title_row.pack(anchor="w")

        tk.Label(title_row, text="🎮", font=(_BODY, 10),
                 bg=_BG).pack(side="left", padx=(0, 5))
        # the widest a toast gets; a longer title wraps instead of being cut
        self._max_w = int(_TOAST_MAX_W * self._scale(root))
        tk.Label(title_row, text=title, font=(_HDR, 9), bg=_BG, fg=_TEXT,
                 justify="left", wraplength=self._max_w - 70).pack(side="left")

        if subtitle:
            tk.Label(body, text=subtitle, font=(_BODY, 8),
                     bg=_BG, fg=_MUTED, anchor="w").pack(anchor="w", pady=(1, 0))

        # Progress bar canvas
        # width=1: a Canvas asks for ~380 px by default and would set the
        # toast's width; it stretches to the toast with fill="x" anyway
        self._bar_canvas = tk.Canvas(inner, height=_BAR_H, width=1, bg=_BAR_BG,
                                     highlightthickness=0)
        self._bar_canvas.pack(side="bottom", fill="x")

        # Position + size
        # 2026-11-20: a fixed 300 x 72 cut longer titles on both sides (and
        # more of them at 125 % scaling); the toast now fits its text
        self._win.update_idletasks()
        sc = self._scale(root)
        self._w = min(self._max_w, max(int(_TOAST_W * sc), self._win.winfo_reqwidth() + 4))
        self._h = max(int(_TOAST_H * sc), self._win.winfo_reqheight() + 2)
        self._win.geometry(f"{self._w}x{self._h}")
        self._reposition()

        # Slide in + progress bar
        self._slide_in()

    @staticmethod
    def _scale(root) -> float:
        """1.0 at 100 % Windows scaling, 1.25 at 125 %..."""
        try:
            return max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
        except Exception:
            return 1.0

    def _reposition(self):
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        x  = sw - self._w - _EDGE_PAD
        y  = sh - self._h - _EDGE_PAD - 40  # above taskbar approx
        self._win.geometry(f"+{x}+{y}")

    # ── Slide-in animation ────────────────────────────────────────────────────
    def _slide_in(self):
        self._anim_step = 0
        self._anim_total = int(_SLIDE_MS / 16)
        self._slide_tick()

    def _slide_tick(self):
        if not self._alive:
            return
        try:
            if not self._win.winfo_exists():
                return
        except Exception:
            return
        self._anim_step += 1
        t = min(self._anim_step / self._anim_total, 1.0)
        ease = 1.0 - (1.0 - t) ** 3     # ease-out cubic
        self._win.attributes("-alpha", ease * 0.94)
        if t < 1.0:
            self._win.after(16, self._slide_tick)
        else:
            self._start_progress()

    # ── Progress bar ─────────────────────────────────────────────────────────
    def _start_progress(self):
        self._prog_step  = 0
        self._prog_total = int(_DURATION / 16)
        self._bar_canvas.update_idletasks()
        self._bar_w = self._bar_canvas.winfo_width() or self._w
        self._bar_id = self._bar_canvas.create_rectangle(
            0, 0, self._bar_w, _BAR_H, fill=self._accent, outline=""
        )
        self._progress_tick()

    def _progress_tick(self):
        if not self._alive:
            return
        try:
            if not self._win.winfo_exists():
                return
        except Exception:
            return
        self._prog_step += 1
        ratio = 1.0 - (self._prog_step / self._prog_total)
        w = max(0, int(self._bar_w * ratio))
        self._bar_canvas.coords(self._bar_id, 0, 0, w, _BAR_H)
        if self._prog_step < self._prog_total:
            self._win.after(16, self._progress_tick)
        else:
            self._slide_out()

    # ── Slide-out animation ───────────────────────────────────────────────────
    def _slide_out(self):
        self._out_step  = 0
        self._out_total = int(_SLIDE_MS / 16)
        self._slide_out_tick()

    def _slide_out_tick(self):
        if not self._alive:
            return
        try:
            if not self._win.winfo_exists():
                return
        except Exception:
            return
        self._out_step += 1
        t    = min(self._out_step / self._out_total, 1.0)
        ease = t ** 2                     # ease-in
        self._win.attributes("-alpha", (1.0 - ease) * 0.94)
        if t < 1.0:
            self._win.after(16, self._slide_out_tick)
        else:
            self._alive = False
            try:
                self._win.destroy()
            except Exception:
                pass


# ── Game watcher thread ───────────────────────────────────────────────────────

class GamingToastWatcher:
    """
    Background thread that monitors running processes.
    When a known game exe appears that wasn't running before,
    shows a gaming toast (if enabled in settings).
    """

    def __init__(self):
        self._running     = False
        self._seen:  set  = set()   # exe names already greeted this session
        self._active: set = set()   # currently running known game executables
        self._observers: List[Callable[[str, str, str], None]] = []
        self._paths: dict = {}      # exe -> its path, for Steam games
        self._root: Optional[tk.Misc] = None
        self._lang  = "pl"

    def register_game_observer(
            self, fn: Callable[[str, str, str], None]) -> None:
        """Observe game start/end without creating another process poller.

        Callback signature: ``fn(event, exe, label)`` where event is ``start``
        or ``end``. Duplicate registration is ignored.
        """
        if callable(fn) and fn not in self._observers:
            self._observers.append(fn)

    def start(self, root: tk.Misc, lang: str = "pl") -> None:
        if self._running:
            return
        self._root   = root
        self._lang   = lang
        self._running = True
        import threading
        threading.Thread(target=self._loop, daemon=True,
                         name="gaming_toast_watcher").start()

    def stop(self) -> None:
        self._running = False

    def set_lang(self, lang: str) -> None:
        self._lang = lang

    def _is_enabled(self) -> bool:
        return _load_app_settings().get("gaming_launch_toast", True)

    def _loop(self) -> None:
        import time
        time.sleep(8)   # let app settle on startup
        while self._running:
            try:
                self._check()
            except Exception:
                pass
            time.sleep(4)   # poll every 4 s

    def _check(self) -> None:
        try:
            import psutil as _ps
            running = set()
            # Known names, plus anything started from a game library folder
            # (Steam, Epic, GOG...): BeamNG.drive was on no list, so its
            # sessions got no start note and no recap (2026-11-16).
            try:
                from core.game_detect import is_game as _is_game
            except Exception:
                _is_game = None
            for proc in _ps.process_iter(["name", "pid"]):
                try:
                    name = (proc.info["name"] or "").lower()
                except Exception:
                    continue
                if name in ("javaw.exe", "java.exe"):
                    # Minecraft Java Edition (2026-11-20): javaw.exe with
                    # Minecraft on its command line greets as Minecraft
                    try:
                        from core.game_detect import is_minecraft_java
                        if is_minecraft_java(proc.info.get("pid")):
                            running.add("minecraft.exe")
                    except Exception:
                        pass
                    continue
                if _is_known(name) or (_is_game is not None
                                       and _is_game(name, pid=proc.info.get("pid"))):
                    running.add(name)
                    if name not in self._paths:
                        # once per game: the Steam folder names the game
                        try:
                            self._paths[name] = proc.exe()
                        except Exception:
                            self._paths[name] = None

            started = running - self._active
            ended = self._active - running
            self._active = running
            enabled = self._is_enabled()
            for name in sorted(started):
                self._notify("start", name)
            if enabled:
                # Preserve the original switch behaviour: enabling launch
                # reminders while a game is already open may still greet it.
                for name in sorted(running):
                    if name in self._seen:
                        continue
                    self._seen.add(name)
                    self._fire(name)
            for name in sorted(ended):
                self._notify("end", name)
            # still running: lets the session recorder move the end forward
            for name in sorted(running - started):
                self._notify("tick", name)
        except Exception:
            pass

    def _notify(self, event: str, exe_lower: str) -> None:
        canonical = _canon(exe_lower)
        label = canonical.rsplit(".exe", 1)[0].replace("_", " ")
        for fn in list(self._observers):
            try:
                fn(event, exe_lower, label)
            except Exception:
                continue

    def _fire(self, exe_lower: str) -> None:
        if self._root is None:
            return
        try:
            from core.game_library import is_first_time, mark_seen
            first = is_first_time(exe_lower)
            mark_seen(exe_lower)
        except Exception:
            first = False
        title, subtitle, accent = _pick(exe_lower, self._lang, self._paths.get(exe_lower), first)
        # the watcher's thread only queues the toast; the main window's
        # pump builds it on the UI thread (ui/bg.py, 2026-11-21)
        from ui import bg as _bg_ui
        _bg_ui.post(lambda w=self, t=title, s=subtitle, a=accent:
                    _GamingToast(w._root, t, s, a) if w._root is not None else None)


# Singleton watcher - imported and started from startup.py
gaming_watcher = GamingToastWatcher()


# ── Public helper ─────────────────────────────────────────────────────────────

def show_gaming_toast(root: tk.Misc, exe_name: str, lang: str = "pl") -> None:
    """
    Manually trigger a gaming toast for a given exe name.
    Useful for testing or manual trigger from process monitor.
    """
    title, subtitle, accent = _pick(exe_name.lower(), lang)
    _GamingToast(root, title, subtitle, accent)
