# ui/components/gaming_toast.py
"""
Gaming launch toast — subtle 2-second notification when a game is detected.

Shows in bottom-right corner, no buttons, auto-dismisses with a progress bar.
Can be disabled from Settings -> Notifications -> Gaming launch reminders.

Public API
----------
show_gaming_toast(root, exe_name, lang='pl')
    -> Called when a game exe is detected starting.
       Reads settings to check if feature is enabled.
"""
from __future__ import annotations

import tkinter as tk
import math
from typing import Optional

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = "#0b0e16"
_BORDER   = "#1c2534"
_TEXT     = "#e2e8f0"
_MUTED    = "#64748b"
_BAR_BG   = "#111827"
_EDGE_PAD = 18        # px from screen edge
_TOAST_W  = 300       # width
_TOAST_H  = 72        # height (compact - no buttons)
_DURATION = 2200      # ms until auto-dismiss
_SLIDE_MS = 220       # slide-in animation duration
_BAR_H    = 3         # progress bar height

# ── Per-game custom messages (exe_name_lower -> (title, subtitle)) ────────────
# title: main bold line
# subtitle: smaller flavour text (None = skip)
_GAME_DB: dict[str, tuple[str, Optional[str]]] = {
    # FPS / competitive
    "cs2.exe":                  ("Powodzenia na turnieju!", "CS2 uruchomione."),
    "csgo.exe":                 ("Graj na maksa!", "CS:GO uruchomione."),
    "valorant.exe":             ("Dobrej gry!", "Valorant odpalony."),
    "r5apex.exe":               ("Ratuj druzyne!", "Apex Legends uruchomiony."),
    "overwatch.exe":            ("Push the payload!", "Overwatch uruchomiony."),
    # MOBA
    "league of legends.exe":    ("Walkę z Nerdami czas zacząć...", "League of Legends"),
    "leagueoflegends.exe":      ("Walkę z Nerdami czas zacząć...", "League of Legends"),
    "dota2.exe":                ("Good luck, have fun!", "Dota 2 uruchomiona."),
    # Cozy / simulation
    "stardewvalley.exe":        ("Odświeżmy Farmę po dziadku!", "Stardew Valley"),
    "planet zoo.exe":           ("Czas zająć się zwierzakami!", "Planet Zoo · Nie zapomnij o TURBO"),
    "planetzoo.exe":            ("Czas zająć się zwierzakami!", "Planet Zoo · Nie zapomnij o TURBO"),
    "cities skylines 2.exe":   ("Czas budować miasto!", "Cities Skylines 2"),
    "citiesskylines2.exe":     ("Czas budować miasto!", "Cities Skylines 2"),
    "sims4.exe":                ("Zyj zyj zyj!", "The Sims 4"),
    # RPG / Story
    "witcher3.exe":             ("Dzikie Łowy czekają!", "Wiedźmin 3"),
    "cyberpunk2077.exe":        ("Night City wita!", "Cyberpunk 2077"),
    "eldenring.exe":            ("Powodzenia w Pomiędzyziemiu!", "Elden Ring · Tarnished"),
    "baldursgate3.exe":        ("Dobrej przygody!", "Baldur's Gate 3"),
    "starfield.exe":           ("Odkrywaj gwiazdy!", "Starfield"),
    # Survival / sandbox
    "rust.exe":                ("Nie daj sie zabic za bardzo!", "Rust"),
    "minecraft.exe":           ("Czas budować!", "Minecraft"),
    "valheim.exe":             ("Podbij Wikingów!", "Valheim"),
    # Racing
    "forza_horizon5.exe":      ("Gaz do dechy!", "Forza Horizon 5"),
    "assettocorsa.exe":        ("Na tor!", "Assetto Corsa"),
    # Strategy
    "ck3.exe":                 ("Dynastia nie zbuduje się sama!", "Crusader Kings III"),
    "eu4.exe":                 ("Europa czeka!", "Europa Universalis IV"),
    "stellaris.exe":           ("Podbij galaktyke!", "Stellaris"),
    # Horror / tense
    "re4.exe":                 ("Leon, salvar la princesa!", "Resident Evil 4"),
    "phasmophobia.exe":        ("Duuuuchy!", "Phasmophobia"),
    "deadbydaylight.exe":     ("Uciekaj albo poluj!", "Dead by Daylight"),
}

# Default messages when game not in DB
_DEFAULT_PL = ("Dobrej zabawy!", None)
_DEFAULT_EN = ("Good luck, have fun!", None)

# Accent colours per category (matched by exe fragments)
_ACCENT_FPS      = "#ef4444"   # red - competitive
_ACCENT_COZY     = "#10b981"   # green - relaxing
_ACCENT_RPG      = "#8b5cf6"   # violet - epic
_ACCENT_DEFAULT  = "#3b82f6"   # blue - default

_ACCENT_MAP: dict[str, str] = {
    "cs2": _ACCENT_FPS, "csgo": _ACCENT_FPS, "valorant": _ACCENT_FPS,
    "apex": _ACCENT_FPS, "overwatch": _ACCENT_FPS,
    "league": _ACCENT_FPS, "dota": _ACCENT_FPS,
    "stardew": _ACCENT_COZY, "planet zoo": _ACCENT_COZY, "planetzoo": _ACCENT_COZY,
    "sims": _ACCENT_COZY, "cities": _ACCENT_COZY,
    "witcher": _ACCENT_RPG, "cyberpunk": _ACCENT_RPG, "eldenring": _ACCENT_RPG,
    "baldurs": _ACCENT_RPG, "starfield": _ACCENT_RPG, "ck3": _ACCENT_RPG,
}


def _get_accent(exe_lower: str) -> str:
    for frag, col in _ACCENT_MAP.items():
        if frag in exe_lower:
            return col
    return _ACCENT_DEFAULT


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
        tk.Label(title_row, text=title,
                 font=(_HDR, 9), bg=_BG, fg=_TEXT).pack(side="left")

        if subtitle:
            tk.Label(body, text=subtitle, font=(_BODY, 8),
                     bg=_BG, fg=_MUTED, anchor="w").pack(anchor="w", pady=(1, 0))

        # Progress bar canvas
        self._bar_canvas = tk.Canvas(inner, height=_BAR_H, bg=_BAR_BG,
                                     highlightthickness=0)
        self._bar_canvas.pack(side="bottom", fill="x")

        # Position + size
        self._win.update_idletasks()
        self._win.geometry(f"{_TOAST_W}x{_TOAST_H}")
        self._reposition()

        # Slide in + progress bar
        self._slide_in()

    def _reposition(self):
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        x  = sw - _TOAST_W - _EDGE_PAD
        y  = sh - _TOAST_H - _EDGE_PAD - 40  # above taskbar approx
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
        self._bar_w = self._bar_canvas.winfo_width() or _TOAST_W
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
        self._seen:  set  = set()   # exe names seen this session
        self._root: Optional[tk.Misc] = None
        self._lang  = "pl"

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
        if not self._is_enabled():
            return
        try:
            import psutil as _ps
            for proc in _ps.process_iter(["name"]):
                try:
                    name = (proc.info["name"] or "").lower()
                except Exception:
                    continue
                if name in _GAME_DB and name not in self._seen:
                    self._seen.add(name)
                    self._fire(name)
        except Exception:
            pass

    def _fire(self, exe_lower: str) -> None:
        if self._root is None:
            return
        title, subtitle = _GAME_DB.get(exe_lower, (
            _DEFAULT_PL[0] if self._lang == "pl" else _DEFAULT_EN[0], None
        ))
        accent = _get_accent(exe_lower)
        try:
            self._root.after(
                0,
                lambda t=title, s=subtitle, a=accent:
                    _GamingToast(self._root, t, s, a)
            )
        except Exception:
            pass


# Singleton watcher — imported and started from startup.py
gaming_watcher = GamingToastWatcher()


# ── Public helper ─────────────────────────────────────────────────────────────

def show_gaming_toast(root: tk.Misc, exe_name: str, lang: str = "pl") -> None:
    """
    Manually trigger a gaming toast for a given exe name.
    Useful for testing or manual trigger from process monitor.
    """
    exe_lower = exe_name.lower()
    title, subtitle = _GAME_DB.get(exe_lower, (
        _DEFAULT_PL[0] if lang == "pl" else _DEFAULT_EN[0], None
    ))
    _GamingToast(root, title, subtitle, _get_accent(exe_lower))
