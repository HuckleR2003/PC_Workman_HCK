import tkinter as tk
import subprocess
import threading
import os
import json
import time
import atexit

try:
    from core.turbo_manager import (
        turbo_services, turbo_processes, turbo_power,
        PROFILES, _SVC_LABELS, IDLE_SECONDS_DEFAULT,
    )
    _TURBO_MGR_OK = True
except Exception:
    _TURBO_MGR_OK = False
    turbo_services = turbo_processes = turbo_power = None
    PROFILES = {}
    _SVC_LABELS = {}
    IDLE_SECONDS_DEFAULT = 300

try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except Exception:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_F    = _UIF    # body / UI text
_M    = _MONOF  # monospace / numbers
_BODY = _UIF
_MONO = _MONOF

# Page-level navigation callback (set in build_optimization_page) so nested card
# builders can jump to another page — e.g. the MANAGER 'i' -> Services Manager.
_NAV = {"cb": None}

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#080b10"
CARD    = "#0e1118"
CARD2   = "#0a0d15"
SURFACE = "#111520"
BORDER  = "#161d2c"
BORDER2 = "#1e2840"
LINE    = "#141826"
TEXT    = "#c4cfdf"
MUTED   = "#3d4a60"
DIM     = "#1e2838"
AMBER   = "#f59e0b"
EMERALD = "#10b981"
VIOLET  = "#8b5cf6"
BLUE    = "#3b82f6"
RED     = "#ef4444"
BORD    = "#991b1b"   # bordeaux for "ON TURBO" slider
BORD_L  = "#c62828"   # bordeaux light

_TOTAL  = 14   # +1 Background App Hibernation

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = os.path.dirname(_sys.executable) if getattr(_sys, "frozen", False) \
               else os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))

_PREFS_PATH = os.path.join(_APP_DIR, "settings", "user_prefs.json")

# ── Prefs helpers ─────────────────────────────────────────────────────────────
def _load_prefs():
    try:
        with open(_PREFS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_opt(**kw):
    try:
        os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
        p = _load_prefs()
        o = p.get("optimization", {})
        o.update(kw)
        p["optimization"] = o
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
    except Exception:
        pass

# ── RAM state ─────────────────────────────────────────────────────────────────
_RAM = {
    "active": False, "stop_flag": False,
    "threshold": 75, "consecutive_high": 0,
    "result_lbl": None, "prog_lbl": None,
}

# ── RAM Flush exclusion list — exe names (lowercase) that are never flushed ──
_RAM_EXCLUDE: set = set()

# ── Turbo Power Plan state ────────────────────────────────────────────────────
_TPP = {
    "active":       False,   # currently using Turbo PC plan
    "auto":         False,   # auto-monitor on
    "on_turbo":     False,   # trigger on TURBO mode
    "stop_flag":    False,
    "original_guid": None,
    "turbo_guid":    None,
    "status_lbl":    None,
}
_TURBO_PC_NAME = "Turbo PC"

def _init():
    o = _load_prefs().get("optimization", {})
    _RAM["active"]    = bool(o.get("ram_auto", False))
    _RAM["threshold"] = int(o.get("ram_threshold", 75))
    _TPP["auto"]      = bool(o.get("tpp_auto", False))
    _TPP["on_turbo"]  = bool(o.get("tpp_on_turbo", False))
    saved = o.get("ram_flush_exclude", [])
    _RAM_EXCLUDE.update(n.lower() for n in saved if isinstance(n, str))

_init()


def _save_exclude():
    _save_opt(ram_flush_exclude=sorted(_RAM_EXCLUDE))
_ACTION_BTNS: dict = {}


# ═════════════════════════════════════════════════════════════════════════════
# TURBO POWER PLAN LOGIC
# ═════════════════════════════════════════════════════════════════════════════

def _is_admin() -> bool:
    """Return True if the process has admin/elevated privileges."""
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def _pp_list() -> dict:
    """Return {name: guid} of all available power plans (language-agnostic).
    Binary mode + safe UTF-8 decode avoids Polish OEM codepage issues."""
    plans = {}
    try:
        r = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in r.stdout.decode("utf-8", errors="replace").splitlines():
            parts = line.strip().split()
            for i, p in enumerate(parts):
                if len(p) == 36 and p.count("-") == 4:
                    # Everything after the GUID, strip parens / asterisk
                    name_part = " ".join(parts[i+1:]).strip("()*").strip()
                    if name_part:
                        plans[name_part] = p
                    break   # one GUID per line
    except Exception:
        pass
    return plans

def _pp_active_guid() -> str | None:
    try:
        r = subprocess.run(
            ["powercfg", "/getactivescheme"],
            capture_output=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for p in r.stdout.decode("utf-8", errors="replace").split():
            if len(p) == 36 and p.count("-") == 4:
                return p
    except Exception:
        pass
    return None

def _pp_set(guid: str) -> bool:
    try:
        r = subprocess.run(
            ["powercfg", "/setactive", guid],
            capture_output=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return r.returncode == 0
    except Exception:
        return False

def _pp_create_turbo() -> str | None:
    """
    Duplicate High Performance (or Ultimate Performance) plan and rename
    it to 'Turbo PC'.  Returns the new GUID or None on failure.
    Requires admin rights on Windows.
    """
    # Try HP first, fall back to Ultimate Performance
    CANDIDATE_GUIDS = [
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",   # High Performance
        "e9a42b02-d5df-448d-aa00-03f14749eb61",    # Ultimate Performance
    ]
    try:
        # Already exists?
        plans = _pp_list()
        if _TURBO_PC_NAME in plans:
            return plans[_TURBO_PC_NAME]

        new_guid = None
        for src_guid in CANDIDATE_GUIDS:
            r = subprocess.run(
                ["powercfg", "/duplicatescheme", src_guid],
                capture_output=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for tok in r.stdout.decode("utf-8", errors="replace").split():
                if len(tok) == 36 and tok.count("-") == 4 and tok.lower() != src_guid.lower():
                    new_guid = tok
                    break
            if new_guid:
                break

        if not new_guid:
            return None

        # Rename to "Turbo PC"
        subprocess.run(
            ["powercfg", "/changename", new_guid, _TURBO_PC_NAME,
             "PC Workman - custom high-performance profile"],
            capture_output=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return new_guid
    except Exception:
        return None

def _tpp_run() -> tuple[bool, str]:
    """Activate Turbo PC plan. Creates it if needed."""
    # Admin check
    if not _is_admin():
        return False, "Needs admin - restart as Administrator"

    # Save original plan
    if not _TPP["original_guid"]:
        _TPP["original_guid"] = _pp_active_guid()

    # Get or create Turbo PC plan
    if not _TPP["turbo_guid"]:
        # Maybe it was created in a previous session
        plans = _pp_list()
        if _TURBO_PC_NAME in plans:
            _TPP["turbo_guid"] = plans[_TURBO_PC_NAME]
        else:
            guid = _pp_create_turbo()
            if not guid:
                return False, "Plan creation failed"
            _TPP["turbo_guid"] = guid

    ok = _pp_set(_TPP["turbo_guid"])
    if ok:
        _TPP["active"] = True
        # ── Apply hibernation turbo behaviors ─────────────────────────────────
        try:
            from import_core import COMPONENTS
            hibm = COMPONENTS.get("core.hibernation_manager")
            if hibm:
                hibm.apply_turbo_behaviors()
        except Exception:
            pass
        return True, "Turbo PC  active ✓"
    return False, "Activation failed"

def _tpp_restore() -> tuple[bool, str]:
    """Restore original power plan."""
    guid = _TPP["original_guid"] or "381b4222-f694-41f0-9685-ff5bb260df2e"
    ok = _pp_set(guid)
    if ok:
        _TPP["active"] = False
        # ── Restore hibernation-slept apps ────────────────────────────────────
        try:
            from import_core import COMPONENTS
            hibm = COMPONENTS.get("core.hibernation_manager")
            if hibm:
                hibm.restore_turbo_apps()
        except Exception:
            pass
        return True, "Balanced restored ✓"
    return False, "Restore failed"

def _tpp_monitor_loop(status_lbl):
    """Background monitor: activate Turbo PC when TURBO mode is on."""
    while not _TPP["stop_flag"]:
        try:
            if _TPP["on_turbo"]:
                # Check TURBO flag from prefs
                turbo_on = bool(_load_prefs().get("turbo_active", False))
                if turbo_on and not _TPP["active"]:
                    ok, msg = _tpp_run()
                    if status_lbl and status_lbl.winfo_exists():
                        status_lbl.after(0, lambda m=msg: status_lbl.config(
                            text=m, fg=EMERALD if "active" in m else RED))
                elif not turbo_on and _TPP["active"]:
                    ok, msg = _tpp_restore()
                    if status_lbl and status_lbl.winfo_exists():
                        status_lbl.after(0, lambda m=msg: status_lbl.config(
                            text=m, fg=MUTED))
        except Exception:
            pass
        time.sleep(5)

# Restore on app exit
def _tpp_atexit():
    if _TPP["active"]:
        _tpp_restore()
atexit.register(_tpp_atexit)


# ═════════════════════════════════════════════════════════════════════════════
# MASTER TURBO SWITCH  - driven by the Main Dashboard "Turbo Boost" button
# ═════════════════════════════════════════════════════════════════════════════

def _set_turbo_flag(on: bool) -> None:
    """Persist the master TURBO flag at top level (read by feature monitors)."""
    try:
        os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
        p = _load_prefs()
        p["turbo_active"] = bool(on)
        with open(_PREFS_PATH, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
    except Exception:
        pass


def is_turbo_active() -> bool:
    """Current master TURBO state (persisted)."""
    return bool(_load_prefs().get("turbo_active", False))


def set_turbo_active(on: bool) -> dict:
    """Master TURBO switch. Persists the flag and directly activates / restores
    every feature the user set to fire on TURBO — works whether or not the
    Optimization page is open (idempotent; safe to call repeatedly).

    Returns {'on': bool, 'applied': [(feature, ok), ...], 'admin': bool}.
    """
    on = bool(on)
    _set_turbo_flag(on)
    applied: list[tuple[str, bool]] = []
    o = _load_prefs().get("optimization", {})

    # Turbo Power Plan (also applies hibernation turbo behaviors via _tpp_run)
    if o.get("tpp_on_turbo", False):
        if on and not _TPP["active"]:
            ok, _ = _tpp_run();     applied.append(("Turbo Power Plan", ok))
        elif not on and _TPP["active"]:
            ok, _ = _tpp_restore(); applied.append(("Turbo Power Plan", ok))

    return {"on": on, "applied": applied, "admin": _is_admin()}


# ═════════════════════════════════════════════════════════════════════════════
# DRAWING HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _blend_hex(c1: str, c2: str, t: float) -> str:
    """Blend hex colour c1 towards c2 by factor t  (0=c1, 1=c2)."""
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    return (f"#{int(r1+(r2-r1)*t):02x}"
            f"{int(g1+(g2-g1)*t):02x}"
            f"{int(b1+(b2-b1)*t):02x}")

def _hex(r, g, b):
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"

def _sep(parent, color=LINE):
    tk.Frame(parent, bg=color, height=1).pack(fill="x")

def _ico_power(c, s, p=None, bg=CARD):
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    m = s // 2
    cv.create_arc(2, 2, s-2, s-2, start=45, extent=270, style="arc",
                  outline=c, width=1)
    cv.create_line(m, 1, m, m+1, fill=c, width=1)
    return cv

def _ico_globe(c, s, p=None, bg=CARD):
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    cv.create_oval(1, 1, s-1, s-1, outline=c, width=1)
    cv.create_line(1, s//2, s-1, s//2, fill=c, width=1)
    cv.create_line(s//2, 1, s//2, s-1, fill=c, width=1)
    return cv

def _ico_trash(c, s, p=None, bg=CARD):
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    m = s // 2
    cv.create_rectangle(3, 4, s-3, s-1, outline=c, width=1)
    cv.create_line(1, 3, s-1, 3, fill=c, width=1)
    cv.create_line(m, 1, m, 4, fill=c, width=1)
    return cv

def _ico_arrow(c, s, p=None, bg=CARD):
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    m = s // 2
    cv.create_line(m, 1, m, s-2, fill=c, width=2)
    cv.create_line(m, 1, 2, m, fill=c, width=1)
    cv.create_line(m, 1, s-2, m, fill=c, width=1)
    return cv

def _ico_ram(c, s, p=None, bg=CARD):
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    cv.create_rectangle(1, 3, s-1, s-3, outline=c, width=1)
    for x in [3, 6, 9]:
        cv.create_rectangle(x, 1, x+2, 3, fill=c, outline="")
    return cv

def _ico_bolt(c, s, p=None, bg=CARD):
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    pts = [s*0.6, 1, 3, s*0.55, s*0.5, s*0.55, s*0.9, s-1, s*0.4, s*0.5, s*0.55, s*0.5]
    cv.create_polygon(pts, fill=c, outline="")
    return cv

def _icv(parent, fn, bg=CARD, size=13):
    """Create icon widget directly in *parent* with correct bg."""
    return fn(MUTED, size, p=parent, bg=bg)

def _pill_cv(cv, active: bool, W: int, H: int, on_color=EMERALD):
    cv.delete("all")
    r = H // 2
    track = "#0d1520" if not active else "#052014"
    cv.create_arc(0, 0, H, H, start=90, extent=180, fill=track, outline="")
    cv.create_arc(W-H, 0, W, H, start=270, extent=180, fill=track, outline="")
    cv.create_rectangle(r, 0, W-r, H, fill=track, outline="")
    knob_x = W - r - 2 if active else r + 2
    knob_col = on_color if active else MUTED
    cv.create_oval(knob_x - r + 2, 2, knob_x + r - 2, H - 2,
                   fill=knob_col, outline="")

def _section_label(parent, text):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=(0, 6))
    tk.Label(row, text=text, font=(_HDR, 7),
             bg=BG, fg=MUTED).pack(side="left")
    tk.Frame(row, bg=LINE, height=1).pack(
        side="left", fill="x", expand=True, padx=8)


# ═════════════════════════════════════════════════════════════════════════════
# HERO HEADER
# ═════════════════════════════════════════════════════════════════════════════

def _build_hero_header(parent, back_fn=None):
    hero = tk.Canvas(parent, bg=BG, height=64, highlightthickness=0)
    hero.pack(fill="x")

    def _draw_hero(e=None):
        hero.delete("all")
        W = hero.winfo_width()
        if W < 10:
            return
        H = 64
        # Gradient bands
        for y in range(H):
            t = y / H
            r = int(8   + (18 - 8)   * t)
            g = int(11  + (22 - 11)  * t)
            b = int(16  + (38 - 16)  * t)
            hero.create_line(0, y, W, y, fill=_hex(r, g, b))
        # Accent line
        hero.create_line(0, H-1, W, H-1, fill=BORDER2)
        # Side accent bar
        hero.create_rectangle(0, 0, 3, H, fill=VIOLET, outline="")
        # Title + subtitle
        hero.create_text(18, 18, text="OPTIMIZATION", anchor="w",
                         font=(_HDR, 13), fill=TEXT)
        hero.create_text(18, 38, text="Features, automation & power management",
                         anchor="w", font=(_F, 8), fill=MUTED)
        # Feature count badge
        hero.create_rectangle(W - 90, 22, W - 8, 42,
                               fill="#0a0f1a", outline=BORDER2)
        hero.create_text(W - 49, 32,
                          text=f"2 / {_TOTAL}  active",
                          font=(_M, 6), fill=DIM)
        # Back link — quiet, bottom-right (only when back_fn provided)
        if back_fn:
            hero.create_text(W - 10, 57, text="‹ Dashboard",
                             anchor="e", font=(_F, 7), fill="#273448",
                             tags="back_nav")

    hero.bind("<Configure>", _draw_hero)

    if back_fn:
        hero.tag_bind("back_nav", "<Button-1>", lambda e: back_fn())
        hero.tag_bind("back_nav", "<Enter>",
                      lambda e: hero.itemconfig("back_nav", fill="#8b5cf6"))
        hero.tag_bind("back_nav", "<Leave>",
                      lambda e: hero.itemconfig("back_nav", fill="#273448"))


# ═════════════════════════════════════════════════════════════════════════════
# SNAPSHOT STRIP  (kept from original)
# ═════════════════════════════════════════════════════════════════════════════

def _build_snapshot_strip(parent):
    """CPU / RAM / Disk live tile strip - redraws every 1 second."""
    strip = tk.Frame(parent, bg=SURFACE,
                     highlightbackground=BORDER, highlightthickness=1)
    strip.pack(fill="x", padx=12, pady=(0, 8))

    # Pre-compute blended fill colours (9 % of accent over SURFACE #111520)
    _sr, _sg, _sb = 0x11, 0x15, 0x20
    def _fill(col, t=0.09):
        cr, cg, cb = int(col[1:3], 16), int(col[3:5], 16), int(col[5:7], 16)
        return (f"#{int(_sr+(cr-_sr)*t):02x}"
                f"{int(_sg+(cg-_sg)*t):02x}"
                f"{int(_sb+(cb-_sb)*t):02x}")

    metric_defs = [
        ("CPU",  AMBER,   "cpu"),
        ("RAM",  BLUE,    "ram"),
        ("C:\\", EMERALD, "disk"),
    ]
    _canvases: list = []  # (canvas, col, fill_col, key)

    for i, (lbl, col, _key) in enumerate(metric_defs):
        if i:
            tk.Frame(strip, bg=BORDER, width=1).pack(side="left", fill="y", pady=6)

        cv = tk.Canvas(strip, bg=SURFACE, highlightthickness=0, height=44)
        cv.pack(side="left", expand=True, fill="x")
        _canvases.append((cv, col, _fill(col), lbl, _key))

    def _redraw_cv(_cv, _col, _fc, _lbl, pct):
        _cv.delete("all")
        W, H = _cv.winfo_width(), _cv.winfo_height()
        if W < 4 or H < 4:
            return
        fw = int(W * pct / 100)
        if fw > 0:
            _cv.create_rectangle(0, 0, fw, H, fill=_fc, outline="")
        mid = H // 2
        _cv.create_text(12, mid - 7, text=_lbl, anchor="w",
                        fill=MUTED, font=(_F, 6))
        _cv.create_text(12, mid + 8, text=f"{pct:.0f}%", anchor="w",
                        fill=_col, font=(_F, 9, "bold"))

    # Bind Configure for initial draw (correct width after layout)
    for cv, col, fc, lbl, _key in _canvases:
        cv.bind("<Configure>",
                lambda e, _c=cv, _co=col, _f=fc, _l=lbl: _redraw_cv(_c, _co, _f, _l, 0))

    def _refresh():
        try:
            import psutil
            cpu_v  = psutil.cpu_percent(interval=None)
            ram_v  = psutil.virtual_memory().percent
            disk_v = psutil.disk_usage("C:\\").percent
        except Exception:
            cpu_v = ram_v = disk_v = 0.0
        vals = {"cpu": cpu_v, "ram": ram_v, "disk": disk_v}

        for cv, col, fc, lbl, key in _canvases:
            try:
                if cv.winfo_exists():
                    _redraw_cv(cv, col, fc, lbl, vals.get(key, 0))
            except Exception:
                pass

        # Reschedule while strip is alive
        try:
            if strip.winfo_exists():
                strip.after(1000, _refresh)
        except Exception:
            pass

    strip.after(600, _refresh)  # first tick after UI settles


# ═════════════════════════════════════════════════════════════════════════════
# QUICK ACTIONS  (left panel)
# ═════════════════════════════════════════════════════════════════════════════

def _build_quick_actions(parent, nav_callback=None):
    """
    4 Quick Actions:
      1. Startup Apps Manager  -> navigate to startup_manager
      2. Services Manager      -> navigate to services_manager
      3. Disk Defragmenter     -> open dfrgui
      4. Weekly Perf Report    -> open report Toplevel
    """
    _section_label(parent, "QUICK  ACTIONS")

    wrap = tk.Frame(parent, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1)
    wrap.pack(fill="x", pady=(4, 0))

    # Status bar (shared)
    status_lbl = tk.Label(wrap, text="",
                          font=(_M, 5), bg="#0a0d14", fg=MUTED,
                          pady=2, padx=8, anchor="w")
    status_lbl.pack(fill="x")

    # ── Action definitions ────────────────────────────────────────────────────
    #   kind: "nav" | "run" | "report"
    _QA = [
        {"key": "startup", "label": "Startup Apps",  "sub": "Manager",
         "color": EMERALD, "icon": _ico_arrow,
         "kind": "nav",  "page": "startup_manager", "btn": "OPEN"},

        {"key": "services", "label": "Services",     "sub": "Manager",
         "color": VIOLET,  "icon": _ico_power,
         "kind": "nav",  "page": "services_manager", "btn": "OPEN"},

        {"key": "defrag",   "label": "Disk",         "sub": "Defragmenter",
         "color": "#6b7a8d", "icon": _ico_trash,
         "kind": "run",  "fn": _run_defrag, "btn": "RUN"},

        {"key": "report",   "label": "Weekly Performance", "sub": "Report",
         "color": EMERALD,  "icon": _ico_arrow,
         "kind": "report", "btn": "VIEW",
         "row_bg": "#081410"},   # dark green background
    ]

    for i, qa in enumerate(_QA):
        if i > 0:
            _sep(wrap, LINE)

        row_bg = qa.get("row_bg", CARD)
        row = tk.Frame(wrap, bg=row_bg)
        row.pack(fill="x")

        col   = qa["color"]
        label = qa["label"]
        sub   = qa["sub"]
        btn_t = qa["btn"]

        # ── Left accent bar (4 px - 70 % wider than original 2 px) ───────────
        tk.Frame(row, bg=col, width=4).pack(side="left", fill="y")

        # Icon
        _icv(row, qa["icon"], bg=row_bg, size=11).pack(
            side="left", padx=(7, 5), pady=7)

        # Text block: label + subtitle
        txt = tk.Frame(row, bg=row_bg)
        txt.pack(side="left", fill="both", expand=True)
        tk.Label(txt, text=label, font=(_HDR, 7),
                 bg=row_bg, fg="#a0b4cc" if row_bg == CARD else "#4aaa70",
                 anchor="w").pack(anchor="w", pady=(4, 0))
        if sub:
            tk.Label(txt, text=sub, font=(_F, 6),
                     bg=row_bg, fg=MUTED, anchor="w").pack(anchor="w", pady=(0, 4))

        # RUN / OPEN / VIEW button  (slightly larger: padx=10, pady=4)
        btn = tk.Label(row, text=btn_t, font=(_HDR, 6),
                       bg=row_bg, fg=col, cursor="hand2",
                       padx=10, pady=4,
                       highlightbackground=col, highlightthickness=1)
        btn.pack(side="right", padx=8, pady=6)
        _ACTION_BTNS[qa["key"]] = (btn, col)

        # ── Bind action ───────────────────────────────────────────────────────
        kind = qa["kind"]

        if kind == "nav":
            page_id = qa["page"]
            def _mk_nav(pid, b, c, bg):
                def _h(e=None):
                    if nav_callback:
                        nav_callback(pid)
                    else:
                        # Fallback: show page id in status
                        if status_lbl.winfo_exists():
                            status_lbl.config(text=f"Navigate -> {pid}")
                return _h
            btn.bind("<Button-1>", _mk_nav(page_id, btn, col, row_bg))

        elif kind == "run":
            fn  = qa["fn"]
            def _mk_run(f, b, c, orig_lbl):
                def _h(e=None):
                    b.config(text="...", fg=MUTED, bg="#0a0d14",
                             highlightbackground=BORDER)
                    def _bg():
                        ok, msg = f()
                        t2, c2 = ("DONE", EMERALD) if ok else ("FAIL", RED)
                        bg2 = "#0a1a10" if ok else "#1a0a0a"
                        if b.winfo_exists():
                            b.after(0, lambda: b.config(
                                text=t2, fg=c2, highlightbackground=c2, bg=bg2))
                        if status_lbl.winfo_exists():
                            status_lbl.after(0, lambda:
                                status_lbl.config(text=msg, fg=c2))
                        time.sleep(3)
                        if b.winfo_exists():
                            b.after(0, lambda: b.config(
                                text=orig_lbl, fg=c, bg=CARD,
                                highlightbackground=c))
                    threading.Thread(target=_bg, daemon=True).start()
                return _h
            btn.bind("<Button-1>", _mk_run(fn, btn, col, btn_t))

        elif kind == "report":
            def _mk_report(b):
                def _h(e=None):
                    root_w = b.winfo_toplevel()
                    _show_weekly_report(root_w)
                return _h
            btn.bind("<Button-1>", _mk_report(btn))

        btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#ffffff"))
        btn.bind("<Leave>", lambda e, b=btn, c=col: b.config(fg=c))


# ─────────────────────────────────────────────────────────────────────────────
# LIVE NOW  - compact auto-refresh mini-bars for the left sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _build_live_mini(parent):
    """CPU / RAM / GPU live bars - updates every 2 s via after()."""
    _section_label(parent, "LIVE  NOW")

    wrap = tk.Frame(parent, bg=CARD,
                    highlightbackground=BORDER, highlightthickness=1)
    wrap.pack(fill="x", pady=(4, 0))

    _metrics = [("CPU", AMBER), ("RAM", BLUE), ("GPU", VIOLET)]
    _val_lbls: dict = {}
    _bar_cvs:  dict = {}

    for idx, (name, col) in enumerate(_metrics):
        if idx:
            _sep(wrap, LINE)
        row = tk.Frame(wrap, bg=CARD)
        row.pack(fill="x", padx=8, pady=(5, 0))

        # Label row: name  •••  value
        hdr = tk.Frame(row, bg=CARD)
        hdr.pack(fill="x")
        tk.Label(hdr, text=name, font=(_F, 5, "bold"),
                 bg=CARD, fg=MUTED).pack(side="left")
        vl = tk.Label(hdr, text="-", font=(_M, 5),
                      bg=CARD, fg=col)
        vl.pack(side="right")
        _val_lbls[name] = vl

        # Thin progress bar
        bar_bg = tk.Frame(row, bg=BORDER, height=2)
        bar_bg.pack(fill="x", pady=(2, 5))
        barcv = tk.Canvas(bar_bg, bg=BORDER, height=2, highlightthickness=0)
        barcv.pack(fill="x")
        _bar_cvs[name] = (barcv, col)

    def _refresh():
        try:
            import psutil
            cpu_p = psutil.cpu_percent(0)
            ram_p = psutil.virtual_memory().percent
            gpu_p = 0.0
            try:
                from hck_gpt.data.live_sensors import get as _ls_get
                gpu_p = float(_ls_get("gpu_load") or 0)
            except Exception:
                pass
            vals = {"CPU": cpu_p, "RAM": ram_p, "GPU": gpu_p}
            for nm, (barcv, col) in _bar_cvs.items():
                pct = vals.get(nm, 0)
                if _val_lbls[nm].winfo_exists():
                    _val_lbls[nm].config(text=f"{pct:.0f}%")
                if barcv.winfo_exists():
                    barcv.delete("all")
                    W = barcv.winfo_width()
                    if W > 2:
                        fw = max(1, int(W * pct / 100))
                        barcv.create_rectangle(0, 0, fw, 2,
                                               fill=col, outline="")
        except Exception:
            pass
        # Reschedule only if widget still alive
        try:
            if _val_lbls["CPU"].winfo_exists():
                _val_lbls["CPU"].after(2000, _refresh)
        except Exception:
            pass

    wrap.after(800, _refresh)   # first tick after UI settles


# ═════════════════════════════════════════════════════════════════════════════
# CUSTOM EXPAND BUILDERS  - rich content for TURBO Service Stop & Process Guard
# ═════════════════════════════════════════════════════════════════════════════

def _build_svc_expand(parent: tk.Frame, card: tk.Frame) -> None:
    """TURBO Service Stop expanded panel: profile chips -> service list -> stop/restore."""
    _BG  = "#090c14"
    _BD  = "#19243a"
    _MUT = "#334560"
    _DARK = "#060910"

    # ── Profile selector ──────────────────────────────────────────────────────
    top = tk.Frame(parent, bg=_BG)
    top.pack(fill="x", padx=10, pady=(8, 4))
    tk.Label(top, text="PROFILE", font=(_HDR, 6),
             bg=_BG, fg=_MUT).pack(side="left", padx=(0, 8))

    _sel   = {"key": "gaming"}
    _chips: dict = {}

    svc_rows:  dict = {}   # svc -> status Label
    count_lbl = tk.Label(parent, text="", font=(_HDR, 7),
                         bg=_BG, fg=_MUT, anchor="w")
    count_lbl.pack(anchor="w", padx=10, pady=(0, 2))

    list_frame = tk.Frame(parent, bg=_DARK,
                          highlightbackground=_BD, highlightthickness=1)
    list_frame.pack(fill="x", padx=10, pady=(0, 6))

    def _redraw_list(pkey):
        for w in list_frame.winfo_children():
            w.destroy()
        svc_rows.clear()
        # Read the EFFECTIVE list (user overrides > preset) so MANAGER and any
        # edits made in the Services Manager configurator show up here too.
        svcs = (turbo_services.get_profile_services(pkey)
                if (_TURBO_MGR_OK and turbo_services) else [])
        pcolor = PROFILES.get(pkey, {}).get("color", BORD_L) if _TURBO_MGR_OK else BORD_L
        count_lbl.config(text=f"{len(svcs)} services  ->  will stop",
                         fg=pcolor)
        for svc in svcs[:9]:
            row = tk.Frame(list_frame, bg=_DARK)
            row.pack(fill="x", padx=6, pady=1)
            tk.Label(row, text="─", font=(_BODY, 6),
                     bg=_DARK, fg=_BD).pack(side="left")
            friendly = _SVC_LABELS.get(svc, svc)
            tk.Label(row, text=friendly, font=(_F, 6),
                     bg=_DARK, fg="#3e5878", anchor="w",
                     ).pack(side="left", padx=(4, 0), fill="x", expand=True)
            sl = tk.Label(row, text="", font=(_F, 5), bg=_DARK, fg=_MUT)
            sl.pack(side="right", padx=4)
            svc_rows[svc] = sl
        if len(svcs) > 9:
            tk.Label(list_frame, text=f"  + {len(svcs) - 9} more services…",
                     font=(_F, 5), bg=_DARK, fg=_MUT, anchor="w",
                     pady=2).pack(anchor="w", padx=6)
        elif not svcs:
            tk.Label(list_frame, text="  (turbo_manager not available)",
                     font=(_F, 6), bg=_DARK, fg=_MUT, pady=4).pack(anchor="w", padx=6)
        card.update_idletasks()

    def _sel_profile(pkey):
        _sel["key"] = pkey
        if _TURBO_MGR_OK and turbo_services:
            turbo_services.set_active_profile(pkey)   # sync with Services Manager
        pdata = PROFILES.get(pkey, {}) if _TURBO_MGR_OK else {}
        pcol  = pdata.get("color", BORD_L)
        pbg   = pdata.get("bg",    "#0a0812")
        for k2, (ch2, c2, _) in _chips.items():
            is_me = (k2 == pkey)
            if k2 == "manager":
                # MANAGER stays on a white background; selection shown as violet border
                ch2.config(bg="#f5f5f5", fg="#0a0a0a",
                           highlightbackground="#8b5cf6" if is_me else "#cfd2d6")
            else:
                ch2.config(
                    bg    = pdata.get("bg", pbg) if is_me else _BG,
                    fg    = pcol if is_me else _MUT,
                    highlightbackground = pcol if is_me else _BD,
                )
        _redraw_list(pkey)

    for pkey, pdata in (PROFILES.items() if _TURBO_MGR_OK else []):
        pcol = pdata["color"]
        is_mgr = (pkey == "manager")
        ch = tk.Label(top, text=pdata["label"].upper(),
                      font=(_HDR, 6), cursor="hand2", padx=9, pady=3,
                      bg="#f5f5f5" if is_mgr else _BG,
                      fg="#0a0a0a" if is_mgr else _MUT,
                      highlightbackground="#cfd2d6" if is_mgr else _BD,
                      highlightthickness=1)
        ch.pack(side="left", padx=(2, 0) if is_mgr else 2)
        _chips[pkey] = (ch, pcol, pdata.get("bg", _BG))
        ch.bind("<Button-1>", lambda e, k=pkey: _sel_profile(k))
        if is_mgr:
            # Clickable info badge — jumps to the Services Manager configurator
            info = tk.Label(top, text="ⓘ", font=(_HDR, 7), bg=_BG,
                            fg="#8b5cf6", cursor="hand2")
            info.pack(side="left", padx=(0, 2))
            info.bind("<Button-1>",
                      lambda e: _NAV["cb"]("services_manager") if _NAV["cb"] else None)
            info.bind("<Enter>", lambda e, w=info: w.config(fg="#c4b5fd"))
            info.bind("<Leave>", lambda e, w=info: w.config(fg="#8b5cf6"))

    _sel_profile(turbo_services.get_active_profile()
                 if (_TURBO_MGR_OK and turbo_services) else "gaming")  # active profile (synced)

    # ── Action row ────────────────────────────────────────────────────────────
    btn_row = tk.Frame(parent, bg=_BG)
    btn_row.pack(fill="x", padx=10, pady=(0, 4))

    act_lbl = tk.Label(btn_row, text="",
                       font=(_F, 6), bg=_BG, fg=_MUT, anchor="w")
    act_lbl.pack(side="left", fill="x", expand=True)

    restore_btn = tk.Label(btn_row, text="RESTORE  ALL",
                           font=(_HDR, 6),
                           bg=_BG, fg=_MUT, cursor="hand2",
                           padx=8, pady=3,
                           highlightbackground=_BD, highlightthickness=1)
    restore_btn.pack(side="right", padx=(4, 0))

    stop_btn = tk.Label(btn_row, text="STOP  PROFILE",
                        font=(_HDR, 6),
                        bg="#130508", fg=BORD_L, cursor="hand2",
                        padx=8, pady=3,
                        highlightbackground=BORD, highlightthickness=1)
    stop_btn.pack(side="right")

    if not (_TURBO_MGR_OK and turbo_services and turbo_services.is_admin):
        tk.Label(parent,
                 text="⚠  Requires Administrator - restart PC Workman as Admin",
                 font=(_F, 6), bg=_BG, fg=AMBER, anchor="w",
                 ).pack(anchor="w", padx=10, pady=(0, 6))
    else:
        tk.Frame(parent, bg=_BD, height=1).pack(fill="x", padx=10, pady=(0, 6))

    # Wire buttons
    def _do_stop(e=None):
        if not (_TURBO_MGR_OK and turbo_services):
            act_lbl.config(text="turbo_manager unavailable", fg=RED)
            return
        if not turbo_services.is_admin:
            act_lbl.config(text="Needs Administrator rights", fg=AMBER)
            return
        stop_btn.config(text="stopping…", fg=MUTED)
        def _bg():
            results = turbo_services.stop_profile(_sel["key"])
            ok_n = sum(1 for _, ok, _ in results if ok)
            col  = BORD_L if ok_n > 0 else MUTED
            msg  = f"{ok_n} services stopped"
            for svc, sl in svc_rows.items():
                hit = next((ok for s, ok, _ in results if s == svc), None)
                if sl.winfo_exists():
                    sl.after(0, lambda lb=sl, h=hit: lb.config(
                        text="✓ stopped" if h else "", fg=BORD_L if h else _MUT))
            if stop_btn.winfo_exists():
                stop_btn.after(0, lambda: stop_btn.config(
                    text="STOP  PROFILE", fg=BORD_L))
            if act_lbl.winfo_exists():
                act_lbl.after(0, lambda: act_lbl.config(text=msg, fg=col))
        threading.Thread(target=_bg, daemon=True).start()

    def _do_restore(e=None):
        if not (_TURBO_MGR_OK and turbo_services):
            return
        restore_btn.config(text="restoring…", fg=MUTED)
        def _bg():
            results = turbo_services.restore_all()
            ok_n = sum(1 for _, ok, _ in results if ok)
            msg  = (f"{ok_n} services restored" if ok_n
                    else "Nothing to restore - already running")
            col  = EMERALD if ok_n else _MUT
            for sl in svc_rows.values():
                if sl.winfo_exists():
                    sl.after(0, lambda lb=sl: lb.config(text=""))
            if restore_btn.winfo_exists():
                restore_btn.after(0, lambda: restore_btn.config(
                    text="RESTORE  ALL", fg=_MUT))
            if act_lbl.winfo_exists():
                act_lbl.after(0, lambda: act_lbl.config(text=msg, fg=col))
        threading.Thread(target=_bg, daemon=True).start()

    stop_btn.bind("<Button-1>", _do_stop)
    restore_btn.bind("<Button-1>", _do_restore)
    stop_btn.bind("<Enter>", lambda e: stop_btn.config(fg="#ffffff"))
    stop_btn.bind("<Leave>", lambda e: stop_btn.config(fg=BORD_L))
    restore_btn.bind("<Enter>", lambda e: restore_btn.config(fg=EMERALD))
    restore_btn.bind("<Leave>", lambda e: restore_btn.config(fg=_MUT))


def _build_guard_expand(parent: tk.Frame, card: tk.Frame) -> None:
    """Process Guard expanded panel: idle threshold -> auto-suspend -> live process list."""
    _BG   = "#090c14"
    _BD   = "#19243a"
    _MUT  = "#334560"
    _DARK = "#060910"

    # ── Idle threshold chips ──────────────────────────────────────────────────
    thr_row = tk.Frame(parent, bg=_BG)
    thr_row.pack(fill="x", padx=10, pady=(8, 4))
    tk.Label(thr_row, text="IDLE THRESHOLD", font=(_HDR, 6),
             bg=_BG, fg=_MUT).pack(side="left", padx=(0, 8))

    _thr_chips: dict = {}
    _thresh = {"secs": IDLE_SECONDS_DEFAULT}

    def _sel_thr(secs):
        _thresh["secs"] = secs
        if _TURBO_MGR_OK and turbo_processes:
            turbo_processes.idle_threshold = secs
        for s, (ch, _) in _thr_chips.items():
            is_me = (s == secs)
            ch.config(
                bg    = "#0d1128" if is_me else _BG,
                fg    = VIOLET    if is_me else _MUT,
                highlightbackground = VIOLET if is_me else _BD,
            )

    for lbl, secs in [("3 MIN", 180), ("5 MIN", 300), ("10 MIN", 600)]:
        ch = tk.Label(thr_row, text=lbl, font=(_HDR, 6),
                      bg=_BG, fg=_MUT, cursor="hand2",
                      padx=8, pady=3,
                      highlightbackground=_BD, highlightthickness=1)
        ch.pack(side="left", padx=2)
        _thr_chips[secs] = (ch, VIOLET)
        ch.bind("<Button-1>", lambda e, s=secs: _sel_thr(s))
    _sel_thr(300)  # default 5 min

    # ── AUTO toggle row ───────────────────────────────────────────────────────
    auto_row = tk.Frame(parent, bg=_BG)
    auto_row.pack(fill="x", padx=10, pady=(0, 6))
    tk.Label(auto_row, text="AUTO SUSPEND", font=(_HDR, 6),
             bg=_BG, fg=_MUT).pack(side="left", padx=(0, 8))

    auto_pill = tk.Canvas(auto_row, width=32, height=15,
                          bg=_BG, highlightthickness=0, cursor="hand2")
    auto_pill.pack(side="left")
    _pill_cv(auto_pill, False, 32, 15, VIOLET)

    mon_lbl = tk.Label(auto_row, text="inactive",
                       font=(_F, 6), bg=_BG, fg=_MUT)
    mon_lbl.pack(side="left", padx=(8, 0))

    tk.Frame(auto_row, bg=_BD, width=1).pack(side="left", fill="y", padx=10)

    # Security notice
    sec_lbl = tk.Label(auto_row, text="✓ anti-spoof check",
                       font=(_F, 6), bg=_BG, fg="#1e4030")
    sec_lbl.pack(side="left")

    # ── Process list ──────────────────────────────────────────────────────────
    tk.Frame(parent, bg=_BD, height=1).pack(fill="x", padx=10)

    list_hdr = tk.Frame(parent, bg=_BG)
    list_hdr.pack(fill="x", padx=10, pady=(4, 0))
    count_lbl = tk.Label(list_hdr, text="0 processes suspended",
                         font=(_HDR, 7), bg=_BG, fg=_MUT)
    count_lbl.pack(side="left")

    resume_all_btn = tk.Label(list_hdr, text="RESUME ALL",
                              font=(_HDR, 6),
                              bg=_BG, fg=_MUT, cursor="hand2",
                              padx=6, pady=2,
                              highlightbackground=_BD, highlightthickness=1)
    resume_all_btn.pack(side="right")

    proc_frame = tk.Frame(parent, bg=_DARK,
                          highlightbackground=_BD, highlightthickness=1)
    proc_frame.pack(fill="x", padx=10, pady=(2, 8))

    tk.Label(proc_frame,
             text="  No suspended processes   -   toggle AUTO SUSPEND to begin",
             font=(_F, 6), bg=_DARK, fg=_MUT, anchor="w", pady=5
             ).pack(fill="x")

    def _refresh():
        for w in proc_frame.winfo_children():
            w.destroy()
        procs = turbo_processes.suspended_list if (_TURBO_MGR_OK and turbo_processes) else []
        n = len(procs)
        count_lbl.config(
            text=f"{n} process{'es' if n != 1 else ''}  suspended",
            fg=VIOLET if n else _MUT)
        if not procs:
            tk.Label(proc_frame,
                     text="  No suspended processes   -   toggle AUTO SUSPEND to begin",
                     font=(_F, 6), bg=_DARK, fg=_MUT, anchor="w", pady=5
                     ).pack(fill="x")
            return
        for info in procs[:8]:
            pid  = info["pid"]
            name = info["name"]
            idle = info["idle_seconds"]
            susp = info.get("suspicious", False)
            row = tk.Frame(proc_frame, bg=_DARK)
            row.pack(fill="x", padx=6, pady=1)
            dot_c = AMBER if susp else VIOLET
            tk.Label(row, text="●", font=(_BODY, 6),
                     bg=_DARK, fg=dot_c).pack(side="left")
            nm_lbl = tk.Label(row, text=name, font=(_F, 6),
                              bg=_DARK, fg="#3e5878", anchor="w")
            nm_lbl.pack(side="left", padx=(3, 0), fill="x", expand=True)
            if susp:
                tk.Label(row, text="⚠", font=(_BODY, 6),
                         bg=_DARK, fg=AMBER).pack(side="left", padx=2)
            idle_m = max(0, idle) // 60
            tk.Label(row, text=f"{idle_m}m idle",
                     font=(_F, 5), bg=_DARK, fg=_MUT).pack(side="left", padx=4)
            rb = tk.Label(row, text="▶ RESUME",
                          font=(_HDR, 5),
                          bg=_DARK, fg=VIOLET, cursor="hand2",
                          padx=5, pady=1,
                          highlightbackground=VIOLET, highlightthickness=1)
            rb.pack(side="right", padx=(0, 2))
            rb.bind("<Button-1>",
                    lambda e, p=pid: (turbo_processes.resume(p), _refresh()))
            rb.bind("<Enter>", lambda e, b=rb: b.config(fg="#ffffff"))
            rb.bind("<Leave>", lambda e, b=rb: b.config(fg=VIOLET))
        if len(procs) > 8:
            tk.Label(proc_frame, text=f"  + {len(procs) - 8} more…",
                     font=(_F, 5), bg=_DARK, fg=_MUT, anchor="w"
                     ).pack(anchor="w", padx=6)
        card.update_idletasks()

    # Auto-suspend toggle
    _auto = {"on": False}

    def _toggle_auto(e=None):
        if not (_TURBO_MGR_OK and turbo_processes):
            mon_lbl.config(text="unavailable", fg=RED)
            return
        _auto["on"] = not _auto["on"]
        _pill_cv(auto_pill, _auto["on"], 32, 15, VIOLET)
        if _auto["on"]:
            turbo_processes.start(_thresh["secs"])
            mon_lbl.config(text="monitoring…", fg=VIOLET)
            sec_lbl.config(fg=EMERALD)
            _tick()
        else:
            turbo_processes.stop()
            mon_lbl.config(text="inactive", fg=_MUT)
            sec_lbl.config(fg="#1e4030")
            _refresh()

    def _tick():
        if not _auto["on"]:
            return
        try:
            if proc_frame.winfo_exists():
                _refresh()
                proc_frame.after(4000, _tick)
        except Exception:
            pass

    def _resume_all(e=None):
        if _TURBO_MGR_OK and turbo_processes:
            n = turbo_processes.resume_all()
            _refresh()
            count_lbl.config(text=f"{n} resumed ✓", fg=EMERALD)

    auto_pill.bind("<Button-1>", _toggle_auto)
    resume_all_btn.bind("<Button-1>", _resume_all)
    resume_all_btn.bind("<Enter>", lambda e: resume_all_btn.config(fg=EMERALD))
    resume_all_btn.bind("<Leave>", lambda e: resume_all_btn.config(fg=_MUT))


# ═════════════════════════════════════════════════════════════════════════════
# BACKGROUND APP HIBERNATION - expanded panel
# ═════════════════════════════════════════════════════════════════════════════

def _build_hibernation_expand(parent: tk.Frame, card: tk.Frame) -> None:
    """
    Background App Hibernation expanded panel.
    Tab 1 - Unused Apps: Sleep/Ignore per process; TURBO Configure mode shows
            per-process Behaviour on TURBO selector (None / Low Priority / Freeze).
    Tab 2 - Ignored Apps: list with Remove button.
    Turbo behaviors are automatically applied when Turbo PP activates.
    """
    _BG    = "#090c14"
    _BD    = "#1a2540"   # slightly lighter border for contrast
    _MUT   = "#4d6888"   # readable muted (was #334560 — nearly invisible)
    _SOFT  = "#6b85a0"   # secondary text (readable on dark)
    _DARK  = "#060910"
    _TEAL  = "#14b8a6"
    _TEALM = "#0f766e"

    # ── Load backends lazily ──────────────────────────────────────────────────
    try:
        from import_core import COMPONENTS
        _tracker = COMPONENTS.get("core.app_activity_tracker")
        _hibm    = COMPONENTS.get("core.hibernation_manager")
    except Exception:
        _tracker = _hibm = None

    # ── State ─────────────────────────────────────────────────────────────────
    _thresh      = {"min": 15}
    _turbo_mode  = {"on": False}   # True → show Turbo Configure selectors per row
    _thr_chips:  dict = {}

    def _sel_thr(minutes):
        _thresh["min"] = minutes
        for m, ch in _thr_chips.items():
            is_me = (m == minutes)
            ch.config(
                bg=("#0d1128" if is_me else _BG),
                fg=(_TEAL    if is_me else _MUT),
                highlightbackground=(_TEAL if is_me else _BD),
            )

    # ── Threshold chips ───────────────────────────────────────────────────────
    thr_row = tk.Frame(parent, bg=_BG)
    thr_row.pack(fill="x", padx=10, pady=(8, 4))
    tk.Label(thr_row, text="INACTIVE SINCE", font=(_HDR, 6),
             bg=_BG, fg=_MUT).pack(side="left", padx=(0, 8))

    for lbl, mins in [("10 MIN", 10), ("15 MIN", 15), ("30 MIN", 30)]:
        ch = tk.Label(thr_row, text=lbl, font=(_HDR, 6),
                      bg=_BG, fg=_MUT, cursor="hand2",
                      padx=8, pady=3,
                      highlightbackground=_BD, highlightthickness=1)
        ch.pack(side="left", padx=2)
        _thr_chips[mins] = ch
        ch.bind("<Button-1>", lambda e, m=mins: (_sel_thr(m), _refresh_unused()))
    _sel_thr(15)

    # ── TURBO Configure button ─────────────────────────────────────────────────
    turbo_cfg_btn = tk.Label(
        thr_row,
        text="TURBO Configure",
        font=(_HDR, 6),
        bg=_BG,
        fg=BORD,
        cursor="hand2",
        padx=8, pady=3,
        highlightbackground=BORD, highlightthickness=1,
    )
    turbo_cfg_btn.pack(side="right")

    def _toggle_turbo_cfg(e=None):
        _turbo_mode["on"] = not _turbo_mode["on"]
        on = _turbo_mode["on"]
        turbo_cfg_btn.config(
            bg="#1a0508" if on else _BG,
            fg=BORD_L if on else BORD,
            highlightbackground=BORD_L if on else BORD,
        )
        _refresh_unused()

    turbo_cfg_btn.bind("<Button-1>", _toggle_turbo_cfg)
    turbo_cfg_btn.bind("<Enter>",
                       lambda e: turbo_cfg_btn.config(fg=BORD_L) if not _turbo_mode["on"] else None)
    turbo_cfg_btn.bind("<Leave>",
                       lambda e: turbo_cfg_btn.config(fg=BORD) if not _turbo_mode["on"] else None)

    # ── Tab bar ───────────────────────────────────────────────────────────────
    tk.Frame(parent, bg=_BD, height=1).pack(fill="x", padx=10, pady=(4, 0))

    tab_row = tk.Frame(parent, bg=_BG)
    tab_row.pack(fill="x", padx=10)

    _tab = {"active": "unused"}
    _tab_btns: dict = {}

    tab_pages: dict = {}

    def _switch_tab(name):
        _tab["active"] = name
        for n, btn in _tab_btns.items():
            btn.config(
                fg=_TEAL if n == name else _MUT,
                font=(_HDR, 6) if n == name else (_F, 6),
            )
        for n, pg in tab_pages.items():
            if n == name:
                pg.pack(fill="both", expand=True)
            else:
                pg.pack_forget()
        if name == "unused":
            _refresh_unused()
        else:
            _refresh_ignored()

    for tab_id, tab_lbl in [("unused", "Unused Apps"), ("ignored", "Ignored")]:
        btn = tk.Label(tab_row, text=tab_lbl, font=(_F, 6),
                       bg=_BG, fg=_MUT, cursor="hand2",
                       padx=10, pady=5)
        btn.pack(side="left")
        _tab_btns[tab_id] = btn
        btn.bind("<Button-1>", lambda e, n=tab_id: _switch_tab(n))

    # Refresh button (right side of tab bar)
    ref_btn = tk.Label(tab_row, text="↻ REFRESH", font=(_HDR, 5),
                       bg=_BG, fg=_MUT, cursor="hand2",
                       padx=6, pady=3,
                       highlightbackground=_BD, highlightthickness=1)
    ref_btn.pack(side="right", pady=3)
    ref_btn.bind("<Button-1>", lambda e: (
        _refresh_unused() if _tab["active"] == "unused" else _refresh_ignored()))
    ref_btn.bind("<Enter>", lambda e: ref_btn.config(fg=_TEAL))
    ref_btn.bind("<Leave>", lambda e: ref_btn.config(fg=_MUT))

    tk.Frame(parent, bg=_BD, height=1).pack(fill="x", padx=10)

    # ── PAGE: Unused Apps ─────────────────────────────────────────────────────
    page_unused = tk.Frame(parent, bg=_BG)

    summary_lbl = tk.Label(page_unused,
                           text="Aplikacje nieaktywne od dłuższego czasu — możesz je uśpić lub skonfigurować tryb Turbo.",
                           font=(_F, 6), bg=_BG, fg=_SOFT,
                           anchor="w", justify="left")
    summary_lbl.pack(fill="x", padx=10, pady=(4, 2))

    # Column headers
    col_hdr = tk.Frame(page_unused, bg=_BG)
    col_hdr.pack(fill="x", padx=10, pady=(0, 2))
    for col_txt in ["APLIKACJA", "NIEAKTYWNA", "RAM", "CPU"]:
        tk.Label(col_hdr, text=col_txt, font=(_HDR, 5),
                 bg=_BG, fg="#3a5470",
                 anchor="w").pack(side="left", padx=(0, 8))

    list_frame = tk.Frame(page_unused, bg=_DARK,
                          highlightbackground=_BD, highlightthickness=1)
    list_frame.pack(fill="x", padx=10, pady=(0, 6))

    def _refresh_unused():
        for w in list_frame.winfo_children():
            w.destroy()

        if not _tracker or not _hibm:
            tk.Label(list_frame,
                     text="  Hibernation system unavailable",
                     font=(_F, 6), bg=_DARK, fg=RED, anchor="w", pady=5
                     ).pack(fill="x")
            return

        apps = _tracker.get_idle_apps(idle_threshold_min=_thresh["min"])
        apps = [a for a in apps if not _hibm.is_ignored(a["exe"])]

        if not apps:
            tk.Label(list_frame,
                     text=f"  Brak nieaktywnych aplikacji przez {_thresh['min']}+ minut",
                     font=(_F, 6), bg=_DARK, fg=_SOFT, anchor="w", pady=6
                     ).pack(fill="x")
            try:
                card.update_idletasks()
            except Exception:
                pass
            return

        in_turbo_cfg = _turbo_mode["on"]

        for app in apps[:10]:
            pid      = app["pid"]
            name     = app["name"]
            exe      = app["exe"]
            idle_min = app["idle_min"]
            ram_mb   = app["ram_mb"]
            cpu_avg  = app["cpu_avg"]
            is_sleeping = _hibm.is_sleeping(pid)

            row = tk.Frame(list_frame, bg=_DARK)
            row.pack(fill="x", padx=4, pady=2)

            # ── Status dot ──────────────────────────────────────────────────
            dot_color = BORD_L if is_sleeping else _TEAL
            tk.Label(row, text="●", font=(_BODY, 5),
                     bg=_DARK, fg=dot_color).pack(side="left", padx=(2, 0))

            # ── Process name ────────────────────────────────────────────────
            tk.Label(row, text=name, font=(_F, 6),
                     bg=_DARK, fg="#6080a0", anchor="w", width=16
                     ).pack(side="left", padx=(3, 0))

            # ── Metrics ─────────────────────────────────────────────────────
            tk.Label(row, text=f"{idle_min}m", font=(_M, 5),
                     bg=_DARK, fg=_SOFT, width=4, anchor="center"
                     ).pack(side="left", padx=1)
            tk.Label(row, text=f"{ram_mb}MB", font=(_M, 5),
                     bg=_DARK, fg=AMBER if ram_mb > 300 else _SOFT, width=5, anchor="center"
                     ).pack(side="left", padx=1)
            tk.Label(row, text=f"{cpu_avg:.1f}%", font=(_M, 5),
                     bg=_DARK, fg=_SOFT, width=4, anchor="center"
                     ).pack(side="left", padx=1)

            # ── Right-side actions ───────────────────────────────────────────
            btn_f = tk.Frame(row, bg=_DARK)
            btn_f.pack(side="right", padx=(0, 2))

            if in_turbo_cfg:
                # ── TURBO Configure mode: show behaviour selector ────────────
                tk.Label(btn_f, text="Behaviour on TURBO:",
                         font=(_F, 5), bg=_DARK, fg=BORD_L,
                         ).pack(side="left", padx=(0, 4))

                current_beh = _hibm.get_turbo_behavior(exe)
                _beh = {"val": current_beh}

                def _make_beh_btn(parent, label, value, exe=exe, _b=_beh):
                    is_active = (_b["val"] == value)
                    _fg = {
                        "none":   _MUT if not is_active else _SOFT,
                        "low":    _TEAL if is_active else _MUT,
                        "freeze": BORD_L if is_active else _MUT,
                    }[value]
                    _bd = {
                        "none":   _BD,
                        "low":    _TEALM if is_active else _BD,
                        "freeze": BORD if is_active else _BD,
                    }[value]
                    _bg = {
                        "none":   _DARK,
                        "low":    "#041412" if is_active else _DARK,
                        "freeze": "#1a0508" if is_active else _DARK,
                    }[value]
                    btn = tk.Label(parent, text=label, font=(_HDR, 5),
                                   bg=_bg, fg=_fg, cursor="hand2",
                                   padx=5, pady=1,
                                   highlightbackground=_bd, highlightthickness=1)
                    btn.pack(side="left", padx=1)

                    def _on_click(e, v=value, ex=exe, _bstate=_beh):
                        _bstate["val"] = v
                        if _hibm:
                            _hibm.set_turbo_behavior(ex, v)
                        _refresh_unused()

                    btn.bind("<Button-1>", _on_click)
                    btn.bind("<Enter>", lambda e, b=btn: b.config(fg="#c4cfdf"))
                    btn.bind("<Leave>", lambda e, b=btn: b.config(fg=_fg))
                    return btn

                _make_beh_btn(btn_f, "—",             "none")
                _make_beh_btn(btn_f, "LOW PRIORITY",  "low")
                _make_beh_btn(btn_f, "FREEZE",        "freeze")

            elif is_sleeping:
                # ── Sleeping: show WAKE ──────────────────────────────────────
                wake_btn = tk.Label(btn_f, text="▶ WAKE",
                                    font=(_HDR, 5),
                                    bg=_DARK, fg=_TEAL, cursor="hand2",
                                    padx=5, pady=1,
                                    highlightbackground=_TEALM, highlightthickness=1)
                wake_btn.pack(side="right", padx=2)

                def _do_wake(e, p=pid):
                    if _hibm:
                        _hibm.wake_app(p)
                    if _tracker:
                        _tracker.mark_active(p)
                    _refresh_unused()

                wake_btn.bind("<Button-1>", _do_wake)
                wake_btn.bind("<Enter>", lambda e, b=wake_btn: b.config(fg="#ffffff"))
                wake_btn.bind("<Leave>", lambda e, b=wake_btn: b.config(fg=_TEAL))

            else:
                # ── Normal mode: SLEEP + IGNORE ──────────────────────────────
                ign_btn = tk.Label(btn_f, text="IGNORE",
                                   font=(_HDR, 5),
                                   bg=_DARK, fg=_MUT, cursor="hand2",
                                   padx=5, pady=1,
                                   highlightbackground=_BD, highlightthickness=1)
                ign_btn.pack(side="right", padx=(2, 0))

                def _do_ignore(e, ex=exe):
                    if _hibm:
                        _hibm.add_ignored(ex)
                    _refresh_unused()

                ign_btn.bind("<Button-1>", _do_ignore)
                ign_btn.bind("<Enter>", lambda e, b=ign_btn: b.config(fg=AMBER))
                ign_btn.bind("<Leave>", lambda e, b=ign_btn: b.config(fg=_MUT))

                slp_btn = tk.Label(btn_f, text="SLEEP",
                                   font=(_HDR, 5),
                                   bg=_DARK, fg=_TEAL, cursor="hand2",
                                   padx=5, pady=1,
                                   highlightbackground=_TEALM, highlightthickness=1)
                slp_btn.pack(side="right", padx=2)

                def _do_sleep(e, p=pid, n=name, ex=exe):
                    beh = _hibm.get_turbo_behavior(ex) if _hibm else "low"
                    if beh == "none":
                        beh = "low"
                    if _hibm:
                        _hibm.sleep_app(p, n, ex, beh)
                    _refresh_unused()

                slp_btn.bind("<Button-1>", _do_sleep)
                slp_btn.bind("<Enter>", lambda e, b=slp_btn: b.config(fg="#ffffff"))
                slp_btn.bind("<Leave>", lambda e, b=slp_btn: b.config(fg=_TEAL))

        if len(apps) > 10:
            tk.Label(list_frame, text=f"  + {len(apps) - 10} więcej…",
                     font=(_F, 5), bg=_DARK, fg=_SOFT, anchor="w"
                     ).pack(anchor="w", padx=6, pady=2)

        try:
            card.update_idletasks()
        except Exception:
            pass

    # ── PAGE: Ignored Apps ────────────────────────────────────────────────────
    page_ignored = tk.Frame(parent, bg=_BG)

    ign_header = tk.Label(page_ignored,
                          text="Aplikacje oznaczone jako ignorowane — nie będą proponowane do uśpienia.",
                          font=(_F, 6), bg=_BG, fg=_SOFT,
                          anchor="w", justify="left")
    ign_header.pack(fill="x", padx=10, pady=(4, 2))

    ign_frame = tk.Frame(page_ignored, bg=_DARK,
                         highlightbackground=_BD, highlightthickness=1)
    ign_frame.pack(fill="x", padx=10, pady=(0, 6))

    def _refresh_ignored():
        for w in ign_frame.winfo_children():
            w.destroy()
        ignored = _hibm.ignored if _hibm else set()
        if not ignored:
            tk.Label(ign_frame, text="  Ignore list is empty",
                     font=(_F, 6), bg=_DARK, fg=_SOFT,
                     anchor="w", pady=5).pack(fill="x")
            return
        for exe_name in sorted(ignored):
            row = tk.Frame(ign_frame, bg=_DARK)
            row.pack(fill="x", padx=4, pady=2)
            tk.Label(row, text="◌", font=(_BODY, 6),
                     bg=_DARK, fg=_MUT).pack(side="left")
            tk.Label(row, text=exe_name, font=(_F, 6),
                     bg=_DARK, fg=_SOFT, anchor="w"
                     ).pack(side="left", padx=(3, 0), fill="x", expand=True)
            rm_btn = tk.Label(row, text="REMOVE",
                              font=(_HDR, 5),
                              bg=_DARK, fg=_MUT, cursor="hand2",
                              padx=5, pady=1,
                              highlightbackground=_BD, highlightthickness=1)
            rm_btn.pack(side="right", padx=2)

            def _do_remove(e, ex=exe_name):
                if _hibm:
                    _hibm.remove_ignored(ex)
                _refresh_ignored()

            rm_btn.bind("<Button-1>", _do_remove)
            rm_btn.bind("<Enter>", lambda e, b=rm_btn: b.config(fg=EMERALD))
            rm_btn.bind("<Leave>", lambda e, b=rm_btn: b.config(fg=_MUT))
        try:
            card.update_idletasks()
        except Exception:
            pass

    # ── Register pages and init ───────────────────────────────────────────────
    tab_pages["unused"]  = page_unused
    tab_pages["ignored"] = page_ignored

    _switch_tab("unused")


# ═════════════════════════════════════════════════════════════════════════════
# FEATURE CARD BUILDER  - 2-column grid, [i] expandable panel
# ═════════════════════════════════════════════════════════════════════════════

def _build_features_grid(parent):
    """
    Build feature cards in a 2-column responsive grid.
    Each card has:  accent bar | title + desc | [i] button
    Clicking [i] expands the card to show: info text + RUN btn + AUTO + ON TURBO sliders
    """
    # ── Header row ────────────────────────────────────────────────────────────
    hdr_row = tk.Frame(parent, bg=BG)
    hdr_row.pack(fill="x", pady=(0, 8))
    tk.Label(hdr_row, text="FEATURES",
             font=(_F, 6, "bold"), bg=BG, fg=MUTED).pack(side="left")
    tk.Frame(hdr_row, bg=LINE, height=1).pack(
        side="left", fill="x", expand=True, padx=8)
    tk.Label(hdr_row, text=f"2 / {_TOTAL}  active",
             font=(_M, 6), bg=BG, fg=DIM).pack(side="right")

    # ── Feature definitions ───────────────────────────────────────────────────
    features = [
        {
            "key":     "ram_flush",
            "title":   "Auto RAM Flush",
            "desc":    "Free working-set memory when usage is high",
            "color":   VIOLET,
            "icon":    _ico_ram,
            "ready":   True,
            "info":    (
                "Forces Windows to trim the working set of all running processes,\n"
                "releasing unused physical memory back to the system pool.\n"
                "Triggers automatically when RAM stays above threshold for 30 s."
            ),
            "run_label": "FLUSH  RAM",
            "run_color": VIOLET,
        },
        {
            "key":     "turbo_pp",
            "title":   "Turbo Power Plan",
            "desc":    "Auto-switch to custom 'Turbo PC' plan on demand",
            "color":   BORD_L,
            "icon":    _ico_bolt,
            "ready":   True,
            "info":    (
                "Creates a custom 'Turbo PC' plan based on High Performance.\n"
                "CPU stays at max frequency - no throttling.\n"
                "App exit auto-restores your original plan.\n"
                "Requires Administrator rights."
            ),
            "run_label": "ACTIVATE",
            "run_color": BORD_L,
        },
        # ── TURBO - ready ─────────────────────────────────────────────────────
        {
            "key":   "turbo_svc",
            "title": "TURBO Service Stop",
            "desc":  "Kill non-essential services by profile",
            "color": BORD_L,
            "icon":  _ico_power,
            "ready": True,
            "info":  "",
            "run_label": "",
            "run_color": BORD_L,
            "custom_expand": _build_svc_expand,
        },
        {
            "key":   "proc_guard",
            "title": "Process Guard",
            "desc":  "Suspend idle background processes",
            "color": VIOLET,
            "icon":  _ico_globe,
            "ready": True,
            "info":  "",
            "run_label": "",
            "run_color": VIOLET,
            "custom_expand": _build_guard_expand,
        },
        {
            "key":   "app_hibernation",
            "title": "App Hibernation",
            "desc":  "Uśpij aplikacje nieużywane od X minut",
            "color": "#14b8a6",
            "icon":  _ico_power,
            "ready": True,
            "info":  "",
            "run_label": "",
            "run_color": "#14b8a6",
            "custom_expand": _build_hibernation_expand,
        },
        # ── SOON ──────────────────────────────────────────────────────────────
        {"key": "cpu_throttle", "title": "CPU Throttle Guard",
         "desc": "Prevent thermal throttling automatically",
         "color": AMBER,   "icon": _ico_power, "ready": False,
         "info": "Monitors CPU frequency ratio and adjusts TDP limits\nto keep clocks stable during sustained workloads.",
         "run_label": "RUN", "run_color": AMBER},
        {"key": "browser_cache", "title": "Browser Cache Cleaner",
         "desc": "Periodically clear browser cache files",
         "color": BLUE,    "icon": _ico_glob_feat, "ready": False,
         "info": "Auto-clears Chrome, Firefox and Edge disk cache\nafter configurable idle period to reclaim disk space.",
         "run_label": "RUN", "run_color": BLUE},
        # startup_opt -> moved to Quick Actions (Startup Manager)
        {"key": "bg_limiter",   "title": "Background Limiter",
         "desc": "Cap CPU for non-foreground processes",
         "color": VIOLET,  "icon": _ico_arrow, "ready": False,
         "info": "Uses Windows job objects to throttle background process\nCPU share, freeing headroom for the active app.",
         "run_label": "RUN", "run_color": VIOLET},
        # defrag_mon -> moved to Quick Actions (Disk Defragmenter)
        {"key": "net_reset",    "title": "Network Adapter Reset",
         "desc": "Reset adapter stack on connectivity issues",
         "color": BLUE,    "icon": _ico_glob_feat, "ready": False,
         "info": "Runs netsh winsock reset and flushes DNS to resolve\nstale network states without a full reboot.",
         "run_label": "RUN", "run_color": BLUE},
        {"key": "reg_clean",    "title": "Registry Junk Cleaner",
         "desc": "Remove orphaned registry keys",
         "color": RED,     "icon": _ico_trash, "ready": False,
         "info": "Scans for invalid uninstall records and broken file\ntype associations. Preview before applying.",
         "run_label": "RUN", "run_color": RED},
        {"key": "gpu_watchdog", "title": "GPU Driver Watchdog",
         "desc": "Detect and restart hung GPU driver",
         "color": AMBER,   "icon": _ico_power, "ready": False,
         "info": "Polls GPU state via nvidia-smi / WMI and triggers\na TDR reset if the driver stops responding.",
         "run_label": "RUN", "run_color": AMBER},
        {"key": "log_rotate",   "title": "Log File Rotation",
         "desc": "Auto-prune old log files to save disk space",
         "color": "#6b7280", "icon": _ico_trash, "ready": False,
         "info": "Monitors the app log folder and compresses / deletes\nentries older than the configured retention period.",
         "run_label": "RUN", "run_color": "#6b7280"},
        {"key": "dns_nightly",  "title": "DNS Auto-Flush",
         "desc": "Nightly DNS cache flush on schedule",
         "color": BLUE,    "icon": _ico_glob_feat, "ready": False,
         "info": "Schedules a silent DNS flush every night at 03:00\nto prevent stale cache entries from breaking browsing.",
         "run_label": "RUN", "run_color": BLUE},
        # perf_report -> moved to Quick Actions (Weekly Perf Report)
        {"key": "fw_monitor",   "title": "Firewall Health",
         "desc": "Verify Windows Firewall is active and healthy",
         "color": RED,     "icon": _ico_power, "ready": False,
         "info": "Queries netsh advfirewall state and alerts if any\nprofile (Domain / Private / Public) is disabled.",
         "run_label": "RUN", "run_color": RED},
    ]

    # ── Scrollable area ───────────────────────────────────────────────────────
    outer = tk.Frame(parent, bg=BG)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                      bg="#000", troughcolor=BG, width=7)
    grid_frame = tk.Frame(canvas, bg=BG)

    _cwin = canvas.create_window((0, 0), window=grid_frame, anchor="nw")
    # Keep grid_frame as wide as the canvas so columns fill properly
    canvas.bind("<Configure>",
        lambda e: canvas.itemconfigure(_cwin, width=e.width))
    # Update scroll region whenever grid_frame height changes
    grid_frame.bind("<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.configure(yscrollcommand=sb.set)

    # Page-level wheel binding WITHOUT add="+": overwrites the previous page's
    # handler instead of stacking a new global one per visit (the old
    # bind_all(add="+") accumulated dead handlers for the whole session).
    def _on_wheel(e):
        try:
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * e.delta / 120), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _on_wheel)

    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # ── Build pairs ───────────────────────────────────────────────────────────
    grid_frame.columnconfigure(0, weight=1, uniform="feat")
    grid_frame.columnconfigure(1, weight=1, uniform="feat")

    for idx, feat in enumerate(features):
        col = idx % 2
        row = idx // 2
        _build_feature_card(grid_frame, feat, row, col)


def _ico_glob_feat(c, s, p=None, bg=CARD2):
    """Globe icon - same as _ico_globe but with CARD2 default bg."""
    cv = tk.Canvas(p, width=s, height=s, bg=bg, highlightthickness=0)
    cv.create_oval(1, 1, s-1, s-1, outline=c, width=1)
    cv.create_line(1, s//2, s-1, s//2, fill=c, width=1)
    cv.create_line(s//2, 1, s//2, s-1, fill=c, width=1)
    return cv


def _build_feature_card(parent, feat: dict, grid_row: int, grid_col: int):
    """
    One feature card with:
      - compact view: accent | icon | title + desc | [i]
      - expanded view: adds info text + RUN btn + AUTO + ON TURBO sliders
    """
    key        = feat["key"]
    title      = feat["title"]
    desc       = feat["desc"]
    color      = feat["color"]
    icon_fn    = feat["icon"]
    ready      = feat["ready"]
    info_text  = feat["info"]
    run_label  = feat["run_label"]
    run_color  = feat["run_color"]

    # Outer wrapper - padded cell
    outer = tk.Frame(parent, bg=BG)
    outer.grid(row=grid_row, column=grid_col, sticky="nsew",
               padx=(0 if grid_col else 0, 4 if grid_col == 0 else 0),
               pady=4)
    outer.columnconfigure(0, weight=1)

    # Card frame
    card = tk.Frame(outer, bg=CARD2,
                    highlightbackground=BORDER, highlightthickness=1)
    card.pack(fill="both", expand=True, padx=(0, 3 if grid_col == 0 else 0))

    # ── Top accent bar ────────────────────────────────────────────────────────
    tk.Frame(card, bg=color, height=2).pack(fill="x")

    # ── Compact row ───────────────────────────────────────────────────────────
    compact = tk.Frame(card, bg=CARD2)
    compact.pack(fill="x", padx=8, pady=(6, 5))

    # Left accent line
    tk.Frame(compact, bg=color, width=2).pack(side="left", fill="y", padx=(0, 7))

    # Icon - created directly inside compact with the right color and bg
    ic_col = color if ready else MUTED
    ic = icon_fn(ic_col, 12, p=compact, bg=CARD2)
    ic.pack(side="left", padx=(0, 6))

    # Title + desc
    txt_frame = tk.Frame(compact, bg=CARD2)
    txt_frame.pack(side="left", fill="both", expand=True)
    title_col = TEXT if ready else "#5a6a82"
    tk.Label(txt_frame, text=title, font=(_HDR, 8),
             bg=CARD2, fg=title_col, anchor="w").pack(anchor="w")
    tk.Label(txt_frame, text=desc, font=(_F, 7),
             bg=CARD2, fg="#556070" if not ready else "#7a96b2",
             anchor="w").pack(anchor="w")

    # [i] button - gray, toggles highlight
    info_btn = tk.Label(compact, text=" i ",
                        font=(_HDR, 7),
                        bg="#161d2c", fg="#4a5568",
                        cursor="hand2", padx=5, pady=3,
                        highlightbackground="#1e2840", highlightthickness=1)
    info_btn.pack(side="right", padx=(6, 0))

    # ── Expansion panel ───────────────────────────────────────────────────────
    expand_frame = tk.Frame(card, bg="#090c14")
    sep_line     = tk.Frame(card, bg=BORDER2, height=1)

    custom_fn = feat.get("custom_expand")

    if custom_fn:
        # Custom cards build their own content; no generic widgets needed
        custom_fn(expand_frame, card)
        auto_pill = turbo_pill = run_btn = status_lbl = None
        auto_state = turbo_state = {}
    else:
        # Standard expand: info text + AUTO/TURBO sliders + RUN button
        info_inner = tk.Frame(expand_frame, bg="#090c14")
        info_inner.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(info_inner, text=info_text,
                 font=(_F, 7), bg="#090c14", fg="#7a9cbf",
                 justify="left", anchor="w",
                 wraplength=260).pack(anchor="w")

        ctrl = tk.Frame(expand_frame, bg="#090c14")
        ctrl.pack(fill="x", padx=10, pady=(4, 10))

        auto_state = {"on": False}
        auto_frame = tk.Frame(ctrl, bg="#090c14")
        auto_frame.pack(side="left")
        tk.Label(auto_frame, text="AUTO", font=(_HDR, 6),
                 bg="#090c14", fg=MUTED).pack(side="left", padx=(0, 3))
        auto_pill = tk.Canvas(auto_frame, width=32, height=15,
                              bg="#090c14", highlightthickness=0,
                              cursor="hand2" if ready else "arrow")
        auto_pill.pack(side="left")
        _pill_cv(auto_pill, False, 32, 15, EMERALD)

        tk.Frame(ctrl, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)
        turbo_state = {"on": False}
        turbo_frame = tk.Frame(ctrl, bg="#090c14")
        turbo_frame.pack(side="left")
        tk.Label(turbo_frame, text="ON  TURBO", font=(_HDR, 6),
                 bg="#090c14", fg=MUTED).pack(side="left", padx=(0, 3))
        turbo_pill = tk.Canvas(turbo_frame, width=32, height=15,
                               bg="#090c14", highlightthickness=0,
                               cursor="hand2" if ready else "arrow")
        turbo_pill.pack(side="left")
        _pill_cv(turbo_pill, False, 32, 15, BORD_L)

        status_lbl = tk.Label(ctrl, text="",
                              font=(_M, 6), bg="#090c14", fg=MUTED,
                              anchor="w")
        status_lbl.pack(side="left", fill="x", expand=True, padx=(8, 0))

        run_btn = tk.Label(ctrl,
                           text=run_label if ready else "SOON",
                           font=(_M, 6, "bold"),
                           bg="#0e1520" if ready else "#0a0d14",
                           fg=run_color if ready else DIM,
                           cursor="hand2" if ready else "arrow",
                           padx=10, pady=4,
                           highlightbackground=run_color if ready else BORDER,
                           highlightthickness=1)
        run_btn.pack(side="right")

    # ── State toggle logic ────────────────────────────────────────────────────
    _expanded = {"open": False}

    def _toggle_expand(e=None):
        if _expanded["open"]:
            sep_line.pack_forget()
            expand_frame.pack_forget()
            info_btn.config(bg="#161d2c", fg="#4a5568",
                            highlightbackground="#1e2840")
        else:
            sep_line.pack(fill="x")
            expand_frame.pack(fill="x")
            info_btn.config(bg="#1a2a40", fg="#7dd3fc",
                            highlightbackground=BLUE)
        _expanded["open"] = not _expanded["open"]
        # Force grid_frame to recalculate so canvas scrollregion updates
        card.update_idletasks()

    info_btn.bind("<Button-1>", _toggle_expand)
    info_btn.bind("<Enter>",
                  lambda e: info_btn.config(fg="#93c5fd") if not _expanded["open"] else None)
    info_btn.bind("<Leave>",
                  lambda e: info_btn.config(fg="#4a5568") if not _expanded["open"] else None)

    # ── Feature-specific logic (only for standard expand cards) ──────────────
    if not custom_fn:
        if key == "ram_flush":
            _wire_ram_flush(run_btn, auto_pill, auto_state,
                            turbo_pill, turbo_state, status_lbl, run_color,
                            expand_frame)
        elif key == "turbo_pp":
            _wire_turbo_pp(run_btn, auto_pill, auto_state,
                           turbo_pill, turbo_state, status_lbl, run_color)


def _build_exclusion_panel(parent):
    """
    Expandable process exclusion panel for RAM Flush.
    Processes in _RAM_EXCLUDE are skipped by _do_ram_flush().
    Exclusions persist to user_prefs.json.
    """
    _EX_BG   = "#07080f"
    _EX_ROW  = "#0c0d16"
    _EX_BORD = "#141828"
    _EX_ON   = "#200810"   # excluded row background (dark bordeaux)
    _EX_HDR  = "#0d0e18"

    wrap = tk.Frame(parent, bg=_EX_BG, highlightthickness=1,
                    highlightbackground=_EX_BORD)
    wrap.pack(fill="x", padx=0, pady=(6, 0))

    # ── Header bar ──────────────────────────────────────────────
    hdr = tk.Frame(wrap, bg=_EX_HDR)
    hdr.pack(fill="x")

    count_lbl = tk.Label(hdr, text=f"PROCESS EXCLUSIONS  ·  {len(_RAM_EXCLUDE)} protected",
                         font=(_HDR, 6), bg=_EX_HDR, fg=MUTED, anchor="w",
                         padx=8, pady=4)
    count_lbl.pack(side="left", fill="x", expand=True)

    refresh_btn = tk.Label(hdr, text="↺ Refresh",
                           font=(_MONO, 6), bg=_EX_HDR, fg="#334455",
                           cursor="hand2", padx=8, pady=4)
    refresh_btn.pack(side="right")

    hint = tk.Label(wrap,
                    text="  Click a process to protect it from flush. Click again to unprotect.",
                    font=(_F, 6), bg=_EX_BG, fg=MUTED, anchor="w", pady=2)
    hint.pack(fill="x")

    # ── Scrollable process list ──────────────────────────────────
    list_frame = tk.Frame(wrap, bg=_EX_BG)
    list_frame.pack(fill="x", padx=4, pady=(0, 4))

    _row_widgets: dict = {}

    def _refresh_list():
        for w in list_frame.winfo_children():
            w.destroy()
        _row_widgets.clear()

        try:
            import psutil as _ps
            procs = {}
            for p in _ps.process_iter(["pid", "name"]):
                try:
                    nm = p.info["name"]
                    if not nm or p.pid <= 4:
                        continue
                    key = nm.lower()
                    if key not in procs:
                        procs[key] = nm
                except Exception:
                    continue
        except Exception:
            procs = {}

        # Excluded first (even if not running), then rest alphabetical
        excluded_names  = sorted(_RAM_EXCLUDE)
        running_names   = sorted(k for k in procs if k not in _RAM_EXCLUDE)
        ordered = [(nm, True) for nm in excluded_names] + \
                  [(nm, False) for nm in running_names]

        for exe_lower, is_excluded in ordered:
            display_name = procs.get(exe_lower, exe_lower)
            is_running   = exe_lower in procs

            row_bg = _EX_ON if is_excluded else _EX_ROW

            row = tk.Frame(list_frame, bg=row_bg, highlightthickness=1,
                           highlightbackground=_EX_BORD, cursor="hand2")
            row.pack(fill="x", pady=1)

            # Toggle indicator
            mark = tk.Label(row, text="✕" if is_excluded else " ",
                            font=(_MONO, 8, "bold"), bg=row_bg,
                            fg=BORD_L if is_excluded else "#1e2838",
                            width=2, padx=4)
            mark.pack(side="left", pady=3)

            # Process name
            name_col = BORD_L if is_excluded else (TEXT if is_running else MUTED)
            name_lbl = tk.Label(row, text=display_name[:36],
                                font=(_F, 7), bg=row_bg, fg=name_col,
                                anchor="w")
            name_lbl.pack(side="left", fill="x", expand=True, pady=3)

            # Running / saved badge
            if is_running:
                badge_fg  = BORD_L if is_excluded else EMERALD
                badge_txt = "PROTECTED" if is_excluded else "● running"
            else:
                badge_fg  = BORD_L
                badge_txt = "PROTECTED · offline"

            badge = tk.Label(row, text=badge_txt,
                             font=(_MONO, 5, "bold"), bg=row_bg,
                             fg=badge_fg, padx=6)
            badge.pack(side="right", pady=3)

            _row_widgets[exe_lower] = (row, mark, name_lbl, badge)

            def _toggle(e, k=exe_lower):
                if k in _RAM_EXCLUDE:
                    _RAM_EXCLUDE.discard(k)
                else:
                    _RAM_EXCLUDE.add(k)
                _save_exclude()
                count_lbl.config(
                    text=f"PROCESS EXCLUSIONS  ·  {len(_RAM_EXCLUDE)} protected")
                _refresh_list()

            for w in (row, mark, name_lbl, badge):
                w.bind("<Button-1>", _toggle)

            def _on_enter(e, r=row, ex=is_excluded):
                try:
                    r.config(highlightbackground=BORD_L if ex else BORDER2)
                except Exception:
                    pass

            def _on_leave(e, r=row):
                try:
                    r.config(highlightbackground=_EX_BORD)
                except Exception:
                    pass

            row.bind("<Enter>", _on_enter)
            row.bind("<Leave>", _on_leave)

        if not ordered:
            tk.Label(list_frame,
                     text="  No processes detected. Click Refresh.",
                     font=(_F, 7), bg=_EX_BG, fg=MUTED, pady=6
                     ).pack(fill="x")

    refresh_btn.bind("<Button-1>", lambda e: _refresh_list())
    refresh_btn.bind("<Enter>",
                     lambda e: refresh_btn.config(fg=EMERALD))
    refresh_btn.bind("<Leave>",
                     lambda e: refresh_btn.config(fg="#334455"))

    wrap.after(200, _refresh_list)
    return wrap


def _wire_ram_flush(run_btn, auto_pill, auto_state,
                    turbo_pill, turbo_state, status_lbl, run_color,
                    expand_frame=None):
    """Wire RAM flush card controls."""
    prefs = _load_prefs().get("optimization", {})
    auto_state["on"] = bool(prefs.get("ram_auto", False))
    _pill_cv(auto_pill, auto_state["on"], 32, 15, EMERALD)

    def _run(e=None):
        run_btn.config(text="...", fg=MUTED, bg="#0a0d14")
        def _bg():
            ok, msg, before, after = _do_ram_flush()
            freed = after - before
            d = f"Freed {freed} MB" if freed > 0 else msg
            col = EMERALD if ok else RED
            if run_btn.winfo_exists():
                run_btn.after(0, lambda: run_btn.config(
                    text="DONE", fg=col, bg="#061210",
                    highlightbackground=col))
            if status_lbl.winfo_exists():
                status_lbl.after(0, lambda: status_lbl.config(text=d, fg=col))
            time.sleep(3)
            if run_btn.winfo_exists():
                run_btn.after(0, lambda: run_btn.config(
                    text="FLUSH  RAM", fg=run_color,
                    bg="#0e1520", highlightbackground=run_color))
        threading.Thread(target=_bg, daemon=True).start()

    def _toggle_auto(e=None):
        auto_state["on"] = not auto_state["on"]
        _pill_cv(auto_pill, auto_state["on"], 32, 15, EMERALD)
        _RAM["active"] = auto_state["on"]
        _save_opt(ram_auto=auto_state["on"])
        if auto_state["on"]:
            _RAM["stop_flag"] = False
            threading.Thread(
                target=_ram_monitor_loop,
                args=(status_lbl, status_lbl),
                daemon=True).start()
        else:
            _RAM["stop_flag"] = True

    run_btn.bind("<Button-1>", _run)
    auto_pill.bind("<Button-1>", _toggle_auto)

    # Append exclusion panel to the card's expand frame
    if expand_frame is not None:
        try:
            _build_exclusion_panel(expand_frame)
        except Exception:
            pass


def _wire_turbo_pp(run_btn, auto_pill, auto_state,
                   turbo_pill, turbo_state, status_lbl, run_color):
    """Wire Turbo Power Plan card controls."""
    auto_state["on"]   = _TPP["auto"]
    turbo_state["on"]  = _TPP["on_turbo"]
    _TPP["status_lbl"] = status_lbl
    _pill_cv(auto_pill,  auto_state["on"],  32, 15, EMERALD)
    _pill_cv(turbo_pill, turbo_state["on"], 32, 15, BORD_L)

    def _run(e=None):
        if _TPP["active"]:
            run_btn.config(text="...", fg=MUTED)
            def _bg_restore():
                ok, msg = _tpp_restore()
                if run_btn.winfo_exists():
                    run_btn.after(0, lambda: run_btn.config(
                        text="ACTIVATE", fg=run_color,
                        highlightbackground=run_color, bg="#0e1520"))
                if status_lbl.winfo_exists():
                    status_lbl.after(0, lambda: status_lbl.config(
                        text=msg, fg=MUTED))
            threading.Thread(target=_bg_restore, daemon=True).start()
        else:
            run_btn.config(text="...", fg=MUTED)
            def _bg_activate():
                ok, msg = _tpp_run()
                col = EMERALD if ok else RED
                btn_lbl = "DEACTIVATE" if ok else "ACTIVATE"
                if run_btn.winfo_exists():
                    run_btn.after(0, lambda: run_btn.config(
                        text=btn_lbl, fg=col,
                        highlightbackground=col,
                        bg="#061210" if ok else "#1a0a0a"))
                if status_lbl.winfo_exists():
                    status_lbl.after(0, lambda: status_lbl.config(
                        text=msg, fg=col))
            threading.Thread(target=_bg_activate, daemon=True).start()

    def _toggle_auto(e=None):
        auto_state["on"] = not auto_state["on"]
        _TPP["auto"] = auto_state["on"]
        _pill_cv(auto_pill, auto_state["on"], 32, 15, EMERALD)
        _save_opt(tpp_auto=auto_state["on"])
        if auto_state["on"]:
            _TPP["stop_flag"] = False
            threading.Thread(
                target=_tpp_monitor_loop,
                args=(status_lbl,),
                daemon=True).start()
        else:
            _TPP["stop_flag"] = True

    def _toggle_turbo(e=None):
        turbo_state["on"] = not turbo_state["on"]
        _TPP["on_turbo"] = turbo_state["on"]
        _pill_cv(turbo_pill, turbo_state["on"], 32, 15, BORD_L)
        _save_opt(tpp_on_turbo=turbo_state["on"])

    run_btn.bind("<Button-1>", _run)
    auto_pill.bind("<Button-1>", _toggle_auto)
    turbo_pill.bind("<Button-1>", _toggle_turbo)
    run_btn.bind("<Enter>", lambda e: run_btn.config(fg="#ffffff"))
    run_btn.bind("<Leave>", lambda e: run_btn.config(
        fg=EMERALD if _TPP["active"] else run_color))

    # Start auto-monitor if it was on from prefs
    if _TPP["auto"]:
        threading.Thread(
            target=_tpp_monitor_loop, args=(status_lbl,), daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════════
# MAIN PAGE BUILDER
# ═════════════════════════════════════════════════════════════════════════════

def build_optimization_page(self, parent):
    root_frame = tk.Frame(parent, bg=BG)
    root_frame.pack(fill="both", expand=True)

    _nav = getattr(self, "_switch_to_page", None)
    _NAV["cb"] = _nav
    _back_fn = (lambda: _nav("dashboard")) if _nav else None
    _build_hero_header(root_frame, back_fn=_back_fn)
    _build_snapshot_strip(root_frame)

    body = tk.Frame(root_frame, bg=BG)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # LEFT: Quick Actions (210px - ~21 % narrower, giving Features more room)
    left = tk.Frame(body, bg=BG, width=210)
    left.pack(side="left", fill="y", padx=(0, 8))
    left.pack_propagate(False)

    # RIGHT: Feature cards grid
    right = tk.Frame(body, bg=BG)
    right.pack(side="left", fill="both", expand=True)

    _build_quick_actions(left, nav_callback=getattr(self, "_switch_to_page", None))
    _build_live_mini(left)
    _build_features_grid(right)


# ═════════════════════════════════════════════════════════════════════════════
# RAM FLUSH LOGIC  (unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def _do_ram_flush():
    import psutil, ctypes
    before = int(psutil.virtual_memory().available / 1048576)
    try:
        cmd = ctypes.c_int(4)
        ctypes.windll.ntdll.NtSetSystemInformation(
            80, ctypes.byref(cmd), ctypes.sizeof(cmd))
    except Exception:
        pass
    try:
        ctypes.windll.kernel32.SetSystemFileCacheSize(
            ctypes.c_size_t(0xFFFFFFFF), ctypes.c_size_t(0xFFFFFFFF), 0)
    except Exception:
        pass
    count = skipped = 0
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            pid  = proc.pid
            name = (proc.info.get("name") or "").lower()
            if pid <= 4:
                continue
            if name and name in _RAM_EXCLUDE:
                skipped += 1
                continue
            try:
                h = ctypes.windll.kernel32.OpenProcess(0x0100 | 0x0400, False, pid)
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    count += 1
            except Exception:
                pass
    except Exception:
        pass
    time.sleep(0.8)
    after = int(psutil.virtual_memory().available / 1048576)
    freed = after - before
    skip_note = f"  ·  {skipped} protected" if skipped else ""
    if freed > 0:
        return True, f"Freed {freed} MB  ({count} procs{skip_note})", before, after
    elif count > 0:
        return True, f"Flushed {count} procs (limited perms{skip_note})", before, after
    return False, "No effect - admin rights needed", before, after


def _ram_monitor_loop(result_lbl, prog_lbl):
    import psutil
    TRIGGER, STEP = 30, 10
    while not _RAM["stop_flag"]:
        try:
            pct = psutil.virtual_memory().percent
            if pct > _RAM["threshold"]:
                _RAM["consecutive_high"] = min(_RAM["consecutive_high"] + STEP, TRIGGER)
                s = _RAM["consecutive_high"]
                if prog_lbl and prog_lbl.winfo_exists():
                    prog_lbl.after(0, lambda v=s: prog_lbl.config(
                        text=f"high  {v}s/{TRIGGER}s", fg=AMBER))
                if _RAM["consecutive_high"] >= TRIGGER:
                    _RAM["consecutive_high"] = 0
                    ok, msg, before, after = _do_ram_flush()
                    freed = after - before
                    d = f"Freed {freed} MB" if freed > 0 else msg
                    if result_lbl and result_lbl.winfo_exists():
                        result_lbl.after(0, lambda v=d: result_lbl.config(
                            text=v, fg=EMERALD if freed > 0 else MUTED))
                    if prog_lbl and prog_lbl.winfo_exists():
                        prog_lbl.after(0, lambda: prog_lbl.config(text=""))
            else:
                _RAM["consecutive_high"] = 0
                if prog_lbl and prog_lbl.winfo_exists():
                    prog_lbl.after(0, lambda: prog_lbl.config(text=""))
        except Exception:
            pass
        time.sleep(STEP)


# ═════════════════════════════════════════════════════════════════════════════
# QUICK ACTION HELPERS  (unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def _run_defrag() -> tuple[bool, str]:
    """Open Windows Disk Defragmenter GUI."""
    try:
        subprocess.Popen(
            ["dfrgui"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, "Disk Defragmenter opened"
    except Exception as ex:
        return False, str(ex)[:50]


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY PERFORMANCE REPORT
# ─────────────────────────────────────────────────────────────────────────────

def _build_weekly_chart(parent, gr: int, gc: int,
                        title: str, vals: list,
                        week_labels: list,
                        color: str,
                        colspan: int = 1,
                        day_counts: list | None = None) -> None:
    """
    Bar chart cell in a grid.  vals/week_labels - N items, oldest -> newest.
    Fixed 0-100 % scale so all charts are visually comparable.
    Latest bar = full color + bright cap.  Older bars progressively dimmer.
    Area fill under trend line, dashed trend line, data-density badges.
    """
    _CARD = "#0c0f18"
    _BD   = "#151e2e"
    _MUT  = "#263650"
    _GRID = "#0e1320"

    cell = tk.Frame(parent, bg=_CARD,
                    highlightbackground=_BD, highlightthickness=1)
    cell.grid(row=gr, column=gc, columnspan=colspan, sticky="nsew",
              padx=(0 if gc == 0 else 5, 0),
              pady=(0 if gr == 0 else 7, 0))

    # ── Title row ────────────────────────────────────────────────────────────
    th = tk.Frame(cell, bg=_CARD)
    th.pack(fill="x", padx=10, pady=(8, 2))

    dot = tk.Canvas(th, width=8, height=8, bg=_CARD, highlightthickness=0)
    dot.pack(side="left", padx=(0, 6))
    dot.create_oval(1, 1, 7, 7, fill=color, outline="")

    tk.Label(th, text=title, font=(_HDR, 8),
             bg=_CARD, fg="#9fb4cc").pack(side="left")

    cur_val = vals[-1] if vals else 0
    if cur_val > 0:
        tk.Label(th, text=f"{cur_val:.0f}%",
                 font=(_HDR, 10), bg=_CARD, fg=color
                 ).pack(side="right")
        tk.Label(th, text="NOW ->",
                 font=(_BODY, 5), bg=_CARD, fg=_MUT
                 ).pack(side="right", padx=(0, 4))

    # ── Chart canvas ─────────────────────────────────────────────────────────
    cv = tk.Canvas(cell, bg=_CARD, highlightthickness=0, height=118)
    cv.pack(fill="x", padx=6, pady=(0, 8))

    def _draw(e=None, _cv=cv, _vals=vals, _lbls=week_labels,
              _col=color, _dcounts=day_counts):
        _cv.delete("all")
        W = _cv.winfo_width()
        H = _cv.winfo_height()
        if W < 20 or H < 20:
            return

        pad_l   = 26
        pad_r   = 8
        pad_bot = 22   # slightly taller for day-count badge
        pad_top = 14
        chart_w  = W - pad_l - pad_r
        chart_h  = H - pad_bot - pad_top
        baseline = H - pad_bot

        # Baseline
        _cv.create_line(pad_l, baseline, W - pad_r, baseline, fill=_BD, width=1)

        # Grid lines at 25 / 50 / 75 / 100 % (fixed scale)
        for pct in [25, 50, 75, 100]:
            y = baseline - int(chart_h * pct / 100)
            _cv.create_line(pad_l, y, W - pad_r, y, fill=_GRID, width=1)
            _cv.create_text(pad_l - 3, y, text=str(pct),
                            anchor="e", font=(_BODY, 5), fill=_MUT)

        n_bars  = len(_vals)
        slot_w  = chart_w / n_bars
        bar_w   = max(5, int(slot_w * 0.52))
        trend   = []

        for i, (val, lbl) in enumerate(zip(_vals, _lbls)):
            cx = pad_l + int(slot_w * (i + 0.5))
            is_now = (i == n_bars - 1)

            # Progressive dim: latest = 0 %, oldest ≈ 72 %
            t_dim = ((n_bars - 1 - i) / (n_bars - 1)) * 0.72 if n_bars > 1 else 0
            fill  = _blend_hex(_col, "#0c1020", t_dim)

            bh = int(chart_h * min(val, 100) / 100) if val > 0 else 0
            x1, x2 = cx - bar_w // 2, cx + bar_w // 2
            y1, y2  = baseline - bh, baseline

            # Outer glow for current week
            if is_now and bh > 2:
                g = _blend_hex(_col, "#000000", 0.68)
                _cv.create_rectangle(x1 - 2, y1, x2 + 2, y2, fill=g, outline="")
            if bh > 0:
                _cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")
                # Bright top cap on current week
                if is_now:
                    cap = _blend_hex(_col, "#ffffff", 0.28)
                    _cv.create_rectangle(x1, y1, x2, y1 + 2, fill=cap, outline="")

            # Value label above bar
            if val > 0:
                lc  = _col if is_now else _MUT
                fnt = (_BODY, 6, "bold") if is_now else (_BODY, 5)
                ty  = baseline - bh - 4 if bh > 0 else baseline - 4
                _cv.create_text(cx, ty, text=f"{val:.0f}%",
                                font=fnt, fill=lc, anchor="s")

            # X label (week label)
            lc2  = _col if is_now else _MUT
            fnt2 = (_HDR, 6) if is_now else (_BODY, 5)
            _cv.create_text(cx, baseline + 3, text=lbl,
                            font=fnt2, fill=lc2, anchor="n")

            # Day-count badge (e.g. "7d") below week label
            if _dcounts and i < len(_dcounts) and _dcounts[i] > 0:
                dc_col = _blend_hex(_col, "#000000", 0.62)
                _cv.create_text(cx, baseline + 13,
                                text=f"{_dcounts[i]}d",
                                font=(_BODY, 4), fill=dc_col, anchor="n")

            if val > 0:
                trend.append((cx, baseline - bh))

        # ── Area fill under trend line (very subtle) ──────────────────────
        if len(trend) >= 2:
            area_pts  = [trend[0]] + trend + [trend[-1]]
            flat_area = []
            for x, y in area_pts:
                flat_area.extend([x, y])
            # anchor the fill to baseline
            flat_area[-2] = trend[-1][0]
            flat_area[-1] = baseline
            flat_area.insert(0, baseline)
            flat_area.insert(0, trend[0][0])

            area_col = _blend_hex(_col, "#000000", 0.88)
            _cv.create_polygon(flat_area, fill=area_col, outline="", smooth=False)

        # ── Dashed trend line connecting bar tops ─────────────────────────
        if len(trend) >= 2:
            tc = _blend_hex(_col, "#000000", 0.48)
            for j in range(len(trend) - 1):
                _cv.create_line(trend[j][0], trend[j][1],
                                trend[j+1][0], trend[j+1][1],
                                fill=tc, width=1, dash=(3, 4))
            # Highlight dot at current (last) bar top
            lx, ly = trend[-1]
            _cv.create_oval(lx - 3, ly - 3, lx + 3, ly + 3,
                            fill=color, outline="")

    cv.bind("<Configure>", _draw)


def _generate_report_summary(week_data: list, n_weeks: int = 6) -> str:
    """1-sentence summary of n_weeks data. Used in footer and TXT export."""
    def _wa(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(sum(vs) / len(vs), 1) if vs else 0.0

    def _wm(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(max(vs), 1) if vs else 0.0

    parts = []

    ca = [_wa(w, "cpu_avg") for w in range(n_weeks)]
    vc = [v for v in ca if v > 0]
    if len(vc) >= 2:
        delta = vc[-1] - vc[0]
        if delta > 5:
            parts.append(f"CPU up +{delta:.0f}% vs {n_weeks} weeks ago (now {vc[-1]:.0f}%).")
        elif delta < -5:
            parts.append(f"CPU down {abs(delta):.0f}% vs {n_weeks} weeks ago (now {vc[-1]:.0f}%).")
        else:
            parts.append(f"CPU stable around {sum(vc)/len(vc):.0f}% avg.")

    ga = [_wa(w, "gpu_avg") for w in range(n_weeks)]
    vg = [v for v in ga if v > 0]
    if vg:
        bw = ga.index(max(ga)) + 1
        parts.append(f"GPU busiest in W{bw} ({max(vg):.0f}% avg).")

    ra = [_wa(w, "ram_avg") for w in range(n_weeks)]
    vr = [v for v in ra if v > 0]
    if vr:
        cur = vr[-1]
        if cur > 80:
            parts.append(f"RAM at {cur:.0f}% - consider freeing background apps.")
        else:
            parts.append(f"RAM healthy at {cur:.0f}%.")

    peaks = [_wm(w, "cpu_max") for w in range(n_weeks)]
    mp = max(peaks) if peaks else 0
    if mp > 90:
        pw = peaks.index(mp) + 1
        parts.append(f"CPU spiked {mp:.0f}% in W{pw}.")

    if not parts:
        return "No historical data yet - PC Workman needs a few days of data to build this report."

    return "   ·   ".join(parts)


def _export_report(win, week_data: list, week_labels: list, n_weeks: int = 6):
    """Save plain-text report to a user-chosen path."""
    import datetime
    import tkinter.filedialog as _fd

    path = _fd.asksaveasfilename(
        parent=win,
        defaultextension=".txt",
        filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        initialfile=f"pc_workman_report_{datetime.date.today()}.txt",
        title="Save Performance Report",
    )
    if not path:
        return

    def _wa(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(sum(vs) / len(vs), 1) if vs else 0.0

    def _wm(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(max(vs), 1) if vs else 0.0

    lines = [
        "PC Workman HCK - Weekly Performance Report",
        f"Generated : {datetime.datetime.now().strftime('%Y-%m-%d  %H:%M')}",
        f"Period    : {n_weeks}-week overview",
        "=" * 58,
    ]
    for wi in range(n_weeks):
        lines.append(f"\n{week_labels[wi]}")
        lines.append(f"  CPU  avg {_wa(wi,'cpu_avg'):5.1f}%   peak {_wm(wi,'cpu_max'):5.1f}%")
        lines.append(f"  GPU  avg {_wa(wi,'gpu_avg'):5.1f}%   peak {_wm(wi,'gpu_max'):5.1f}%")
        lines.append(f"  RAM  avg {_wa(wi,'ram_avg'):5.1f}%   peak {_wm(wi,'ram_max'):5.1f}%")

    lines.append("\n" + "=" * 58)
    lines.append(_generate_report_summary(week_data, n_weeks))

    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except Exception:
        pass


def _build_insight_card(parent, col_idx: int, name: str, color: str,
                        cur_avg: float, prev_avg: float, week_max: float,
                        _R_CARD: str, _R_BD: str, _R_TXT: str, _R_MUT: str,
                        weekly_vals: list | None = None):
    """Compact metric status card: name | big number | trend | peak | badge | sparkline."""
    card = tk.Frame(parent, bg=_R_CARD,
                    highlightbackground=_R_BD, highlightthickness=1)
    card.grid(row=0, column=col_idx, sticky="nsew",
              padx=(0 if col_idx == 0 else 6, 0))

    # Left color stripe
    tk.Frame(card, bg=color, width=3).pack(side="left", fill="y")

    inner = tk.Frame(card, bg=_R_CARD)
    inner.pack(side="left", fill="both", expand=True, padx=10, pady=7)

    # Metric name
    tk.Label(inner, text=name, font=(_HDR, 7),
             bg=_R_CARD, fg=color).pack(anchor="w")

    # Big avg number + delta arrow
    num_row = tk.Frame(inner, bg=_R_CARD)
    num_row.pack(anchor="w")

    avg_str = f"{cur_avg:.0f}%" if cur_avg > 0 else "-"
    tk.Label(num_row, text=avg_str, font=(_HDR, 16),
             bg=_R_CARD, fg=_R_TXT).pack(side="left")

    if cur_avg > 0 and prev_avg > 0:
        delta = cur_avg - prev_avg
        if delta > 3:
            arr, arr_col = f" ▲ +{delta:.0f}%", RED
        elif delta < -3:
            arr, arr_col = f" ▼ {delta:.0f}%", EMERALD
        else:
            arr, arr_col = " - stable", _R_MUT
        tk.Label(num_row, text=arr, font=(_BODY, 7),
                 bg=_R_CARD, fg=arr_col).pack(side="left", pady=(8, 0))

    # Peak + status badge row
    badge_row = tk.Frame(inner, bg=_R_CARD)
    badge_row.pack(anchor="w", pady=(2, 0))

    if week_max > 0:
        tk.Label(badge_row, text=f"peak {week_max:.0f}%",
                 font=(_BODY, 6), bg=_R_CARD, fg=_R_MUT).pack(side="left")

    if cur_avg > 0:
        if cur_avg < 60:
            st, sc = "NORMAL", EMERALD
        elif cur_avg < 80:
            st, sc = "ELEVATED", AMBER
        else:
            st, sc = "HIGH", RED
        sb = _blend_hex(sc, "#000000", 0.84)
        tk.Label(badge_row, text=f"  {st}  ",
                 font=(_HDR, 5),
                 bg=sb, fg=sc, padx=3, pady=1).pack(side="left", padx=(6, 0))

    # ── Mini sparkline (6-week trend) ────────────────────────────────────
    if weekly_vals and len(weekly_vals) >= 2:
        spk_frame = tk.Frame(inner, bg=_R_CARD)
        spk_frame.pack(fill="x", pady=(5, 0))

        # "6W TREND" label
        tk.Label(spk_frame, text="6W TREND",
                 font=(_BODY, 5), bg=_R_CARD, fg=_R_MUT).pack(anchor="w")

        spk = tk.Canvas(spk_frame, bg=_blend_hex(_R_CARD, "#ffffff", 0.03),
                        height=22, highlightthickness=0)
        spk.pack(fill="x")

        def _draw_spark(e=None, _s=spk, _v=list(weekly_vals), _c=color):
            _s.delete("all")
            W = _s.winfo_width()
            H = _s.winfo_height()
            if W < 16 or H < 8:
                return
            valid = [v for v in _v if v > 0]
            if len(valid) < 2:
                _s.create_text(W // 2, H // 2, text="no data",
                               font=(_BODY, 4), fill=_R_MUT, anchor="center")
                return
            hi  = max(valid) or 1
            lo  = min(valid)
            rng = hi - lo if hi != lo else hi

            padx, pady = 5, 3
            W2 = W - padx * 2
            H2 = H - pady * 2
            n  = len(_v)

            pts = []
            for i, v in enumerate(_v):
                if v > 0:
                    x = padx + (i / (n - 1)) * W2
                    y = pady + (1 - (v - lo) / rng) * H2
                    pts.append((x, y))

            # Area fill under spark line
            if len(pts) >= 2:
                poly_flat = [pts[0][0], H]
                for px2, py2 in pts:
                    poly_flat += [px2, py2]
                poly_flat += [pts[-1][0], H]
                area_c = _blend_hex(_c, "#000000", 0.82)
                _s.create_polygon(poly_flat, fill=area_c, outline="")

            # Line
            line_c = _blend_hex(_c, "#000000", 0.38)
            for j in range(len(pts) - 1):
                _s.create_line(pts[j][0], pts[j][1],
                               pts[j+1][0], pts[j+1][1],
                               fill=line_c, width=1)
            # Dot at current week
            if pts:
                lx, ly = pts[-1]
                _s.create_oval(lx - 2, ly - 2, lx + 2, ly + 2,
                               fill=_c, outline="")

        spk.bind("<Configure>", _draw_spark)


def _build_highlight_card(parent, week_data: list, wa_fn, wm_fn,
                          n_weeks: int,
                          _R_CARD: str, _R_BD: str, _R_MUT: str):
    """Key Highlights card - occupies (row=1, col=1) in the charts grid."""
    cell = tk.Frame(parent, bg=_R_CARD,
                    highlightbackground=_R_BD, highlightthickness=1)
    cell.grid(row=1, column=1, sticky="nsew", padx=5, pady=7)

    th = tk.Frame(cell, bg=_R_CARD)
    th.pack(fill="x", padx=10, pady=(8, 4))

    dot = tk.Canvas(th, width=8, height=8, bg=_R_CARD, highlightthickness=0)
    dot.pack(side="left", padx=(0, 6))
    dot.create_oval(1, 1, 7, 7, fill=VIOLET, outline="")
    tk.Label(th, text="KEY  HIGHLIGHTS", font=(_HDR, 8),
             bg=_R_CARD, fg="#8ba0bc").pack(side="left")

    # Separator line
    tk.Frame(cell, bg=_R_BD, height=1).pack(fill="x", padx=10)

    inner = tk.Frame(cell, bg=_R_CARD)
    inner.pack(fill="both", expand=True, padx=10, pady=(6, 10))

    bullets: list[tuple[str, str]] = []  # (color, text)

    # ── CPU trend ────────────────────────────────────────────────────────────
    ca = [wa_fn(w, "cpu_avg") for w in range(n_weeks)]
    vc = [v for v in ca if v > 0]
    if len(vc) >= 2:
        delta = vc[-1] - vc[0]
        if delta > 5:
            bullets.append((AMBER, f"CPU ▲ +{delta:.0f}% vs {n_weeks}w ago"))
        elif delta < -5:
            bullets.append((EMERALD, f"CPU ▼ {abs(delta):.0f}% vs {n_weeks}w ago"))
        else:
            bullets.append((MUTED, f"CPU stable  ~{sum(vc)/len(vc):.0f}% avg"))

    # ── Best CPU week ────────────────────────────────────────────────────────
    if vc:
        best_idx = ca.index(min(ca[i] for i in range(n_weeks) if ca[i] > 0))
        best_val  = ca[best_idx]
        is_recent = best_idx >= n_weeks - 2
        if best_val > 0:
            wlbl = "this week" if best_idx == n_weeks - 1 else f"W{best_idx + 1}"
            bullets.append((EMERALD if is_recent else MUTED,
                            f"Best CPU week: {wlbl}  ({best_val:.0f}%)"))

    # ── RAM pressure ────────────────────────────────────────────────────────
    ra = [wa_fn(w, "ram_avg") for w in range(n_weeks)]
    vr = [v for v in ra if v > 0]
    if vr:
        avg_ram = sum(vr) / len(vr)
        peak_ram = max(wm_fn(w, "ram_max") for w in range(n_weeks))
        if avg_ram > 80:
            bullets.append((RED,    f"RAM consistently high  avg {avg_ram:.0f}%"))
        elif avg_ram > 65:
            bullets.append((AMBER,  f"RAM moderate pressure  avg {avg_ram:.0f}%"))
        else:
            bullets.append((EMERALD, f"RAM healthy  avg {avg_ram:.0f}%"))
        if peak_ram > 90:
            bullets.append((RED, f"RAM peaked {peak_ram:.0f}% - check memory"))

    # ── GPU busiest week ────────────────────────────────────────────────────
    ga = [wa_fn(w, "gpu_avg") for w in range(n_weeks)]
    vg = [v for v in ga if v > 0]
    if vg:
        bw_idx = ga.index(max(ga))
        bw_lbl = "this week" if bw_idx == n_weeks - 1 else f"W{bw_idx + 1}"
        bullets.append((VIOLET, f"GPU busiest: {bw_lbl}  ({max(vg):.0f}%)"))
    elif not vg:
        bullets.append((MUTED, "GPU: no data recorded (integrated?)"))

    # ── CPU peak spike ───────────────────────────────────────────────────────
    peaks = [wm_fn(w, "cpu_max") for w in range(n_weeks)]
    mp = max((p for p in peaks if p > 0), default=0)
    if mp > 90:
        pw = peaks.index(mp) + 1
        bullets.append((RED, f"CPU spiked {mp:.0f}%  in W{pw}  - investigate"))
    elif mp > 0:
        bullets.append((MUTED, f"CPU peak: {mp:.0f}%  (no alarms)"))

    # ── Total data density ───────────────────────────────────────────────────
    total_days = sum(
        1 for w in range(n_weeks)
        for d in week_data[w] if d.get("date_str")
    )
    bullets.append((MUTED, f"{total_days} days of data  ·  {n_weeks}-week span"))

    if not bullets:
        tk.Label(inner,
                 text="Not enough data yet.\nRun PC Workman a few\nweeks to see insights.",
                 font=(_BODY, 7), bg=_R_CARD, fg=_R_MUT,
                 justify="left").pack(anchor="w")
        return

    for bul_col, text in bullets[:7]:
        row = tk.Frame(inner, bg=_R_CARD)
        row.pack(fill="x", pady=(0, 4))

        dot2 = tk.Canvas(row, width=6, height=6, bg=_R_CARD, highlightthickness=0)
        dot2.pack(side="left", pady=1, padx=(0, 7))
        dot2.create_oval(0, 0, 6, 6, fill=bul_col, outline="")

        tk.Label(row, text=text, font=(_BODY, 7),
                 bg=_R_CARD, fg="#6a8aaa", anchor="w",
                 wraplength=140).pack(side="left", fill="x", expand=True)


def _show_weekly_report(root_win) -> None:
    """Open the 6-week performance report Toplevel - 5 charts + highlights."""
    import datetime

    _N = 6   # weeks

    # ── Data - read from minute_avg.csv, aggregate into daily summaries ────────
    import csv as _csv
    import sys as _sys

    def _load_daily_from_csv() -> list:
        """Read minute_avg.csv and return list of {date_str, cpu_avg, ram_avg, gpu_avg}."""
        _base = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        path = os.path.join(_base, "data", "logs", "minute_avg.csv")
        if not os.path.exists(path):
            return []
        daily: dict = {}
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                for row in _csv.DictReader(fh):
                    ts = row.get("iso_time", "")
                    if len(ts) < 10:
                        continue
                    date = ts[:10]
                    try:
                        cpu = float(row.get("cpu_avg", 0) or 0)
                        ram = float(row.get("ram_avg", 0) or 0)
                        gpu = float(row.get("gpu_avg", 0) or 0)
                    except (ValueError, TypeError):
                        continue
                    if date not in daily:
                        daily[date] = {"cpu": [], "ram": [], "gpu": []}
                    daily[date]["cpu"].append(cpu)
                    daily[date]["ram"].append(ram)
                    daily[date]["gpu"].append(gpu)
        except Exception:
            return []

        def _avg(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0.0

        return sorted(
            [
                {
                    "date_str": d,
                    "cpu_avg":  _avg(v["cpu"]),
                    "ram_avg":  _avg(v["ram"]),
                    "gpu_avg":  _avg(v["gpu"]),
                    "cpu_max":  round(max(v["cpu"]), 1) if v["cpu"] else 0.0,
                    "ram_max":  round(max(v["ram"]), 1) if v["ram"] else 0.0,
                    "gpu_max":  round(max(v["gpu"]), 1) if v["gpu"] else 0.0,
                }
                for d, v in daily.items()
            ],
            key=lambda r: r["date_str"],
        )

    raw = _load_daily_from_csv()

    # Also try metrics_store and merge (fills in gpu_temp, etc. if available)
    try:
        from hck_gpt.data.metrics_store import metrics_store as _ms
        ms_raw = _ms.daily_summary(days=_N * 7)
        if ms_raw:
            ms_dict = {r["date_str"]: r for r in ms_raw if r.get("date_str")}
            for r in raw:
                if r["date_str"] in ms_dict:
                    r.update({k: v for k, v in ms_dict[r["date_str"]].items()
                               if k not in r or r[k] == 0})
    except Exception:
        pass

    raw = sorted(raw, key=lambda r: r.get("date_str", ""))
    while len(raw) < _N * 7:
        raw.insert(0, {})
    raw = raw[-(_N * 7):]
    week_data = [raw[w * 7:(w + 1) * 7] for w in range(_N)]

    def _week_label_short(wi):
        days = [d for d in week_data[wi] if d.get("date_str")]
        if not days:
            return f"W{wi + 1}"
        return "NOW" if wi == _N - 1 else days[0]["date_str"][5:]

    def _week_label_full(wi):
        days = [d for d in week_data[wi] if d.get("date_str")]
        if not days:
            return f"Week {wi + 1}  -  no data"
        span = f"{days[0]['date_str'][5:]} -> {days[-1]['date_str'][5:]}"
        return f"Current   {span}" if wi == _N - 1 else f"W{wi + 1}   {span}"

    short_lbls = [_week_label_short(w) for w in range(_N)]
    full_labels = [_week_label_full(w) for w in range(_N)]

    def _wa(wi, col):
        vs = [d.get(col, 0.0) for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(sum(vs) / len(vs), 1) if vs else 0.0

    def _wm(wi, col):
        vs = [d.get(col, 0.0) for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(max(vs), 1) if vs else 0.0

    _CPU = AMBER
    _GPU = VIOLET
    _RAM = BLUE

    # Date range for header
    start_days = [d for d in week_data[0] if d.get("date_str")]
    end_days   = [d for d in week_data[-1] if d.get("date_str")]
    if start_days and end_days:
        date_range = f"{start_days[0]['date_str']}  ->  {end_days[-1]['date_str']}"
    else:
        date_range = "Last 6 weeks"

    # ── Theme ─────────────────────────────────────────────────────────────────
    _W_BG   = "#07090e"
    _W_CARD = "#0c0f18"
    _W_BD   = "#151e2e"
    _W_TXT  = "#c4cfdf"
    _W_MUT  = "#2a3a54"
    _W_SOFT = "#4a6080"

    # ── Window ────────────────────────────────────────────────────────────────
    win = tk.Toplevel(root_win)
    win.title("Weekly Performance Report - PC Workman HCK")
    win.geometry("1040x720+60+40")
    win.resizable(True, True)
    win.minsize(860, 600)
    win.configure(bg=_W_BG)
    win.grab_set()

    # ── Gradient header ────────────────────────────────────────────────────────
    hdr = tk.Canvas(win, bg="#07090e", height=72, highlightthickness=0)
    hdr.pack(fill="x")

    def _draw_hdr(e=None):
        hdr.delete("all")
        Wh = hdr.winfo_width()
        H  = 72
        for y in range(H):
            t = y / H
            r = int(7  + (15 - 7)  * t)
            g = int(9  + (20 - 9)  * t)
            b = int(14 + (30 - 14) * t)
            hdr.create_line(0, y, Wh, y, fill=_hex(r, g, b))
        hdr.create_line(0, H - 1, Wh, H - 1, fill=_W_BD)
        # Violet left accent bar (fading out)
        hdr.create_rectangle(0, 0, 4, H, fill=VIOLET, outline="")
        hdr.create_rectangle(4, 0, 6, H,
                             fill=_blend_hex(VIOLET, "#0c0f18", 0.7), outline="")
        # Title
        hdr.create_text(22, 22, text="WEEKLY PERFORMANCE REPORT",
                        anchor="w", font=(_HDR, 14), fill=_W_TXT)
        hdr.create_text(22, 46,
                        text=f"PC Workman HCK   ·   {date_range}   ·   6-week overview",
                        anchor="w", font=(_BODY, 8), fill=_W_MUT)
        # Badge
        bx = Wh - 130
        hdr.create_rectangle(bx, 20, bx + 108, 40,
                             fill="#0d1428", outline=_W_BD)
        hdr.create_text(bx + 54, 30, text="6 WEEKS  ·  HISTORY",
                        font=(_HDR, 6), fill=_W_SOFT, anchor="center")
        # ✕
        hdr.create_text(Wh - 16, 36, text="✕", anchor="center",
                        font=(_BODY, 13), fill=_W_MUT, tags="close_x")

    hdr.bind("<Configure>", _draw_hdr)
    hdr.tag_bind("close_x", "<Button-1>", lambda e: win.destroy())
    hdr.tag_bind("close_x", "<Enter>",
                 lambda e: hdr.itemconfig("close_x", fill=RED))
    hdr.tag_bind("close_x", "<Leave>",
                 lambda e: hdr.itemconfig("close_x", fill=_W_MUT))

    # ── Week timeline strip ────────────────────────────────────────────────────
    wk_cv = tk.Canvas(win, bg="#0b0e16", height=28, highlightthickness=0)
    wk_cv.pack(fill="x")

    def _draw_wk(e=None):
        wk_cv.delete("all")
        Ww = wk_cv.winfo_width()
        if Ww < 10:
            return
        slot = Ww / _N
        for wi in range(_N):
            cx = int(slot * (wi + 0.5))
            is_now = (wi == _N - 1)
            if wi > 0:
                wk_cv.create_line(int(slot * wi), 4, int(slot * wi), 24,
                                  fill=_W_BD)
            fg  = _W_TXT  if is_now else _W_SOFT
            fnt = (_HDR, 7) if is_now else (_BODY, 6)
            wk_cv.create_text(cx, 13, text=full_labels[wi],
                              font=fnt, fill=fg, anchor="center")
            if is_now:
                wk_cv.create_oval(cx - 3, 22, cx + 3, 28,
                                  fill=VIOLET, outline="")

    wk_cv.bind("<Configure>", _draw_wk)
    tk.Frame(win, bg=_W_BD, height=1).pack(fill="x")

    # ── Charts grid ────────────────────────────────────────────────────────────
    # Layout:  row 0 -> CPU avg  |  GPU avg  |  RAM avg
    #          row 1 -> CPU peak |  highlights card  |  RAM peak
    charts_outer = tk.Frame(win, bg=_W_BG)
    charts_outer.pack(fill="both", expand=True, padx=12, pady=(10, 4))
    for c in range(3):
        charts_outer.columnconfigure(c, weight=1)
    charts_outer.rowconfigure(0, weight=1)
    charts_outer.rowconfigure(1, weight=1)

    # Day counts per week (for density badge inside charts)
    day_counts = [sum(1 for d in week_data[w] if d.get("date_str")) for w in range(_N)]

    chart_specs = [
        (0, 0, "CPU  -  Average %",
         [_wa(w, "cpu_avg") for w in range(_N)], _CPU),
        (0, 1, "GPU  -  Average %",
         [_wa(w, "gpu_avg") for w in range(_N)], _GPU),
        (0, 2, "RAM  -  Average %",
         [_wa(w, "ram_avg") for w in range(_N)], _RAM),
        (1, 0, "CPU  -  Peak %",
         [_wm(w, "cpu_max") for w in range(_N)], _CPU),
        (1, 2, "RAM  -  Peak %",
         [_wm(w, "ram_max") for w in range(_N)], _RAM),
    ]

    for gr, gc, title, vals, col in chart_specs:
        _build_weekly_chart(charts_outer, gr, gc, title, vals, short_lbls, col,
                            day_counts=day_counts)

    # Highlights card in (1, 1)
    _build_highlight_card(charts_outer, week_data, _wa, _wm, _N,
                          _W_CARD, _W_BD, _W_MUT)

    # ── Insight strip - 3 metric cards ────────────────────────────────────────
    tk.Frame(win, bg=_W_BD, height=1).pack(fill="x", padx=12)
    ins_outer = tk.Frame(win, bg=_W_BG)
    ins_outer.pack(fill="x", padx=12, pady=(6, 0))
    for c in range(3):
        ins_outer.columnconfigure(c, weight=1)

    _metrics_ins = [
        ("CPU", _CPU,
         _wa(_N - 1, "cpu_avg"), _wa(_N - 2, "cpu_avg"), _wm(_N - 1, "cpu_max"),
         [_wa(w, "cpu_avg") for w in range(_N)]),
        ("GPU", _GPU,
         _wa(_N - 1, "gpu_avg"), _wa(_N - 2, "gpu_avg"), _wm(_N - 1, "gpu_max"),
         [_wa(w, "gpu_avg") for w in range(_N)]),
        ("RAM", _RAM,
         _wa(_N - 1, "ram_avg"), _wa(_N - 2, "ram_avg"), _wm(_N - 1, "ram_max"),
         [_wa(w, "ram_avg") for w in range(_N)]),
    ]
    for ci, (nm, col, cur, prev, peak, wvals) in enumerate(_metrics_ins):
        _build_insight_card(ins_outer, ci, nm, col, cur, prev, peak,
                            _W_CARD, _W_BD, _W_TXT, _W_MUT,
                            weekly_vals=wvals)

    # ── Footer ────────────────────────────────────────────────────────────────
    tk.Frame(win, bg=_W_BD, height=1).pack(fill="x", pady=(5, 0))
    footer = tk.Frame(win, bg="#090c14")
    footer.pack(fill="x")

    summary = _generate_report_summary(week_data, _N)
    tk.Label(footer, text=summary,
             font=(_BODY, 7), bg="#090c14", fg="#3d5878",
             justify="left", anchor="w", wraplength=700,
             ).pack(side="left", padx=14, pady=8, fill="x", expand=True)

    btn_row = tk.Frame(footer, bg="#090c14")
    btn_row.pack(side="right", padx=12, pady=7)

    close_btn = tk.Label(btn_row, text="  CLOSE  ",
                         font=(_HDR, 7),
                         bg="#0f1520", fg=_W_SOFT, cursor="hand2",
                         padx=8, pady=4,
                         highlightbackground=_W_BD, highlightthickness=1)
    close_btn.pack(side="right", padx=(4, 0))
    close_btn.bind("<Button-1>", lambda e: win.destroy())
    close_btn.bind("<Enter>", lambda e: close_btn.config(fg=_W_TXT))
    close_btn.bind("<Leave>", lambda e: close_btn.config(fg=_W_SOFT))

    exp_btn = tk.Label(btn_row, text="  EXPORT .TXT  ",
                       font=(_HDR, 7),
                       bg="#0f1a2a", fg=BLUE, cursor="hand2",
                       padx=8, pady=4,
                       highlightbackground="#1e3a5f", highlightthickness=1)
    exp_btn.pack(side="right", padx=(0, 4))
    exp_btn.bind("<Button-1>",
                 lambda e: _export_report(win, week_data, full_labels, _N))
    exp_btn.bind("<Enter>", lambda e: exp_btn.config(fg="#93c5fd"))
    exp_btn.bind("<Leave>", lambda e: exp_btn.config(fg=BLUE))
