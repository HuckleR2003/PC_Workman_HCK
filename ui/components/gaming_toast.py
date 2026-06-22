# ui/components/gaming_toast.py
"""
Gaming launch toast — subtle 2-second notification when a game is detected.

Shows in bottom-right corner, no buttons, auto-dismisses with a progress bar.
Can be disabled from Settings -> Notifications -> Gaming launch reminders.

Per-game messages are bilingual (pl/en) and may carry MULTIPLE variants — one is
picked at random each launch, so the same game can greet you differently.

Public API
----------
show_gaming_toast(root, exe_name, lang='pl')
    -> Called when a game exe is detected starting.
       Reads settings to check if feature is enabled.
"""
from __future__ import annotations

import random
import tkinter as tk
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

# ── Per-game custom messages ──────────────────────────────────────────────────
# exe_name_lower -> {"pl": [(title, subtitle|None), ...], "en": [...]}
#   title:    main bold line
#   subtitle: smaller flavour text (None = skip)
# Multiple entries per language = a random variant is shown each launch.
_Variant = tuple  # (title, subtitle|None)
_GAME_DB: dict[str, dict[str, list[tuple[str, Optional[str]]]]] = {
    # ── FPS / competitive ─────────────────────────────────────────────────────
    "cs2.exe": {
        "pl": [("Powodzenia na turnieju!", "CS2 uruchomione."),
               ("Czas na kilka headshotów!", "CS2 · clutch or kick")],
        "en": [("Good luck at the tournament!", "CS2 launched."),
               ("Time for some headshots!", "CS2 · clutch or kick")],
    },
    "csgo.exe": {
        "pl": [("Graj na maksa!", "CS:GO uruchomione.")],
        "en": [("Give it your all!", "CS:GO launched.")],
    },
    "valorant.exe": {
        "pl": [("Dobrej gry!", "Valorant odpalony."),
               ("Pokaż im swojego Jett!", "Valorant")],
        "en": [("Have a good one!", "Valorant launched."),
               ("Show them your Jett!", "Valorant")],
    },
    "r5apex.exe": {
        "pl": [("Ratuj druzyne!", "Apex Legends")],
        "en": [("Carry the squad!", "Apex Legends")],
    },
    "overwatch.exe": {
        "pl": [("Push the payload!", "Overwatch")],
        "en": [("Push the payload!", "Overwatch")],
    },
    "helldivers2.exe": {
        "pl": [("Za Super-Ziemię!", "Helldivers 2"),
               ("Szerz demokrację!", "Helldivers 2")],
        "en": [("For Super Earth!", "Helldivers 2"),
               ("Spread democracy!", "Helldivers 2")],
    },
    "fortniteclient-win64-shipping.exe": {
        "pl": [("Po Victory Royale!", "Fortnite")],
        "en": [("Go get that Victory Royale!", "Fortnite")],
    },
    "tslgame.exe": {
        "pl": [("Winner winner, chicken dinner!", "PUBG")],
        "en": [("Winner winner, chicken dinner!", "PUBG")],
    },
    "rocketleague.exe": {
        "pl": [("Gol! ...albo własna bramka.", "Rocket League")],
        "en": [("Goal! ...or an own goal.", "Rocket League")],
    },
    # ── MOBA ──────────────────────────────────────────────────────────────────
    "league of legends.exe": {
        "pl": [("Walkę z Nerdami czas zacząć...", "League of Legends")],
        "en": [("Let the battle with the Nerds begin...", "League of Legends")],
    },
    "dota2.exe": {
        "pl": [("Powodzenia, dobrej zabawy!", "Dota 2")],
        "en": [("Good luck, have fun!", "Dota 2")],
    },
    # ── Cozy / simulation ─────────────────────────────────────────────────────
    "stardewvalley.exe": {
        "pl": [("Odświeżmy farmę po dziadku!", "Stardew Valley")],
        "en": [("Let's revive grandpa's farm!", "Stardew Valley")],
    },
    "planet zoo.exe": {
        "pl": [("Czy wychodujesz dziś jakiegoś albinoska?", "Planet Zoo"),
               ("Jaki wybieg udało ci się dzisiaj zbudować?", "Planet Zoo")],
        "en": [("Breeding an albino today?", "Planet Zoo"),
               ("What habitat will you build today?", "Planet Zoo")],
    },
    "cities skylines 2.exe": {
        "pl": [("Czas budować miasto!", "Cities: Skylines II")],
        "en": [("Time to build a city!", "Cities: Skylines II")],
    },
    "sims4.exe": {
        "pl": [("Zyj, zyj, zyj!", "The Sims 4")],
        "en": [("Live, laugh, Sim!", "The Sims 4")],
    },
    "terraria.exe": {
        "pl": [("Jakiś boss dziś będzie bity?", "Terraria"),
               ("Kopiemy w głąb?", "Terraria")],
        "en": [("Fighting a boss today?", "Terraria"),
               ("Digging deep today?", "Terraria")],
    },
    "factorygame.exe": {
        "pl": [("Optymalizuj fabrykę... i bez spaghetti!", "Satisfactory")],
        "en": [("Optimize the factory... no spaghetti!", "Satisfactory")],
    },
    "factorio.exe": {
        "pl": [("Fabryka musi rosnąć.", "Factorio")],
        "en": [("The factory must grow.", "Factorio")],
    },
    # ── RPG / story ───────────────────────────────────────────────────────────
    "witcher3.exe": {
        "pl": [("Dzikie Łowy czekają!", "Wiedźmin 3")],
        "en": [("The Wild Hunt awaits!", "The Witcher 3")],
    },
    "cyberpunk2077.exe": {
        "pl": [("Night City wita!", "Cyberpunk 2077")],
        "en": [("Welcome to Night City!", "Cyberpunk 2077")],
    },
    "eldenring.exe": {
        "pl": [("Powodzenia w Pomiędzyziemiu!", "Elden Ring · Tarnished")],
        "en": [("Good luck in the Lands Between!", "Elden Ring · Tarnished")],
    },
    "baldursgate3.exe": {
        "pl": [("Dobrej przygody!", "Baldur's Gate 3")],
        "en": [("Have a great adventure!", "Baldur's Gate 3")],
    },
    "starfield.exe": {
        "pl": [("Odkrywaj gwiazdy!", "Starfield")],
        "en": [("Explore the stars!", "Starfield")],
    },
    "hades.exe": {
        "pl": [("Ucieczka z podziemi, próba #∞", "Hades")],
        "en": [("Escaping the underworld, attempt #∞", "Hades")],
    },
    "hades2.exe": {
        "pl": [("Ucieczka z podziemi, próba #∞", "Hades II")],
        "en": [("Escaping the underworld, attempt #∞", "Hades II")],
    },
    "hollow_knight.exe": {
        "pl": [("Hallownest czeka!", "Hollow Knight")],
        "en": [("Hallownest awaits!", "Hollow Knight")],
    },
    "gta5.exe": {
        "pl": [("Witaj w Los Santos!", "GTA V")],
        "en": [("Welcome to Los Santos!", "GTA V")],
    },
    "rdr2.exe": {
        "pl": [("Dziki Zachód wzywa, kowboju.", "Red Dead Redemption 2")],
        "en": [("The Wild West is calling, cowboy.", "Red Dead Redemption 2")],
    },
    # ── Survival / sandbox ────────────────────────────────────────────────────
    "rust.exe": {
        "pl": [("Nie daj się zabić... za bardzo.", "Rust")],
        "en": [("Try not to get killed... too much.", "Rust")],
    },
    "minecraft.exe": {
        "pl": [("Kopiemy diamenty?", "Minecraft"),
               ("Czas budować!", "Minecraft")],
        "en": [("Mining diamonds today?", "Minecraft"),
               ("Time to build!", "Minecraft")],
    },
    "valheim.exe": {
        "pl": [("Podbij krainę Wikingów!", "Valheim")],
        "en": [("Conquer the Viking realm!", "Valheim")],
    },
    "palworld.exe": {
        "pl": [("Łap, hoduj... i do roboty!", "Palworld")],
        "en": [("Catch 'em, breed 'em... back to work!", "Palworld")],
    },
    "sotgame.exe": {
        "pl": [("Po skarby, piracie!", "Sea of Thieves")],
        "en": [("Set sail for treasure, pirate!", "Sea of Thieves")],
    },
    "nms.exe": {
        "pl": [("Odkrywaj nowe światy!", "No Man's Sky")],
        "en": [("Explore new worlds!", "No Man's Sky")],
    },
    # ── Racing ────────────────────────────────────────────────────────────────
    "forza_horizon5.exe": {
        "pl": [("Gaz do dechy!", "Forza Horizon 5")],
        "en": [("Pedal to the metal!", "Forza Horizon 5")],
    },
    "assettocorsa.exe": {
        "pl": [("Na tor!", "Assetto Corsa")],
        "en": [("Hit the track!", "Assetto Corsa")],
    },
    # ── Strategy ──────────────────────────────────────────────────────────────
    "ck3.exe": {
        "pl": [("Dynastia nie zbuduje się sama!", "Crusader Kings III")],
        "en": [("The dynasty won't build itself!", "Crusader Kings III")],
    },
    "eu4.exe": {
        "pl": [("Europa czeka!", "Europa Universalis IV")],
        "en": [("Europe awaits!", "Europa Universalis IV")],
    },
    "stellaris.exe": {
        "pl": [("Podbij galaktykę!", "Stellaris")],
        "en": [("Conquer the galaxy!", "Stellaris")],
    },
    # ── Horror / tense ────────────────────────────────────────────────────────
    "re4.exe": {
        "pl": [("Leon, ratuj księżniczkę!", "Resident Evil 4")],
        "en": [("Leon, save the princess!", "Resident Evil 4")],
    },
    "phasmophobia.exe": {
        "pl": [("Duuuuchy!", "Phasmophobia")],
        "en": [("Ghoooosts!", "Phasmophobia")],
    },
    "deadbydaylight.exe": {
        "pl": [("Uciekaj albo poluj!", "Dead by Daylight")],
        "en": [("Run or hunt!", "Dead by Daylight")],
    },
}

# Alternate exe spellings -> canonical key (keeps _GAME_DB DRY).
_ALIASES: dict[str, str] = {
    "leagueoflegends.exe": "league of legends.exe",
    "planetzoo.exe":       "planet zoo.exe",
    "citiesskylines2.exe": "cities skylines 2.exe",
    "seaofthieves.exe":    "sotgame.exe",
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
    "apex": _ACCENT_FPS, "overwatch": _ACCENT_FPS, "helldivers": _ACCENT_FPS,
    "fortnite": _ACCENT_FPS, "tslgame": _ACCENT_FPS, "rocketleague": _ACCENT_FPS,
    "league": _ACCENT_FPS, "dota": _ACCENT_FPS,
    "stardew": _ACCENT_COZY, "planet zoo": _ACCENT_COZY, "planetzoo": _ACCENT_COZY,
    "sims": _ACCENT_COZY, "cities": _ACCENT_COZY, "terraria": _ACCENT_COZY,
    "factory": _ACCENT_COZY, "factorio": _ACCENT_COZY, "minecraft": _ACCENT_COZY,
    "palworld": _ACCENT_COZY, "valheim": _ACCENT_COZY, "sot": _ACCENT_COZY,
    "nms": _ACCENT_COZY, "stellaris": _ACCENT_COZY, "eu4": _ACCENT_COZY,
    "witcher": _ACCENT_RPG, "cyberpunk": _ACCENT_RPG, "eldenring": _ACCENT_RPG,
    "baldurs": _ACCENT_RPG, "starfield": _ACCENT_RPG, "ck3": _ACCENT_RPG,
    "hades": _ACCENT_RPG, "hollow": _ACCENT_RPG, "gta5": _ACCENT_RPG, "rdr2": _ACCENT_RPG,
}


def _canon(exe_lower: str) -> str:
    """Resolve an exe alias to its canonical _GAME_DB key."""
    return _ALIASES.get(exe_lower, exe_lower)


def _is_known(exe_lower: str) -> bool:
    return exe_lower in _GAME_DB or exe_lower in _ALIASES


def _pick(exe_lower: str, lang: str) -> tuple[str, Optional[str]]:
    """Pick one (title, subtitle) variant for this game + language at random."""
    entry = _GAME_DB.get(_canon(exe_lower))
    if not entry:
        return _DEFAULT_PL if lang == "pl" else _DEFAULT_EN
    variants = entry.get(lang) or entry.get("pl") or entry.get("en")
    if not variants:
        return _DEFAULT_PL if lang == "pl" else _DEFAULT_EN
    return random.choice(variants)


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
                if _is_known(name) and name not in self._seen:
                    self._seen.add(name)
                    self._fire(name)
        except Exception:
            pass

    def _fire(self, exe_lower: str) -> None:
        if self._root is None:
            return
        title, subtitle = _pick(exe_lower, self._lang)
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
    title, subtitle = _pick(exe_lower, lang)
    _GamingToast(root, title, subtitle, _get_accent(exe_lower))
