import tkinter as tk
import subprocess
import threading
import os
import json
import tempfile
import time
import math
import atexit

try:
    from utils.fonts import UI as _F, MONO as _M
except Exception:
    _F, _M = "Segoe UI", "Consolas"

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

_TOTAL  = 11   # 14 − 3 moved to Quick Actions (startup_opt, defrag_mon, perf_report)

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
    "run_cv": None, "run_draw": None,
}

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

_init()
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
    """Return {name: guid} of all available power plans (language-agnostic)."""
    plans = {}
    try:
        r = subprocess.run(
            ["powercfg", "/list"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in r.stdout.splitlines():
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
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for p in r.stdout.split():
            if len(p) == 36 and p.count("-") == 4:
                return p
    except Exception:
        pass
    return None

def _pp_set(guid: str) -> bool:
    try:
        r = subprocess.run(
            ["powercfg", "/setactive", guid],
            capture_output=True, text=True, timeout=5,
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
                capture_output=True, text=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for tok in r.stdout.split():
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
             "PC Workman — custom high-performance profile"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return new_guid
    except Exception:
        return None

def _tpp_run() -> tuple[bool, str]:
    """Activate Turbo PC plan. Creates it if needed."""
    # Admin check
    if not _is_admin():
        return False, "Needs admin — restart as Administrator"

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
        return True, "Turbo PC  active ✓"
    return False, "Activation failed"

def _tpp_restore() -> tuple[bool, str]:
    """Restore original power plan."""
    guid = _TPP["original_guid"] or "381b4222-f694-41f0-9685-ff5bb260df2e"
    ok = _pp_set(guid)
    if ok:
        _TPP["active"] = False
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
# DRAWING HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _blend_hex(c1: str, c2: str, t: float) -> str:
    """Blend hex colour c1 towards c2 by factor t  (0=c1, 1=c2)."""
    r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
    return (f"#{int(r1+(r2-r1)*t):02x}"
            f"{int(g1+(g2-g1)*t):02x}"
            f"{int(b1+(b2-b1)*t):02x}")

def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

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
    tk.Label(row, text=text, font=("Segoe UI Semibold", 7),
             bg=BG, fg=MUTED).pack(side="left")
    tk.Frame(row, bg=LINE, height=1).pack(
        side="left", fill="x", expand=True, padx=8)


# ═════════════════════════════════════════════════════════════════════════════
# HERO HEADER
# ═════════════════════════════════════════════════════════════════════════════

def _build_hero_header(parent):
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
        # Side accent bars
        hero.create_rectangle(0, 0, 3, H, fill=VIOLET, outline="")
        # Text
        hero.create_text(18, 18, text="OPTIMIZATION", anchor="w",
                         font=("Segoe UI Semibold", 13), fill=TEXT)
        hero.create_text(18, 38, text="Features, automation & power management",
                         anchor="w", font=(_F, 8), fill=MUTED)
        # Feature count badge
        hero.create_rectangle(W - 90, 22, W - 8, 42,
                               fill="#0a0f1a", outline=BORDER2)
        hero.create_text(W - 49, 32,
                          text=f"2 / {_TOTAL}  active",
                          font=(_M, 6), fill=DIM)

    hero.bind("<Configure>", _draw_hero)


# ═════════════════════════════════════════════════════════════════════════════
# SNAPSHOT STRIP  (kept from original)
# ═════════════════════════════════════════════════════════════════════════════

def _build_snapshot_strip(parent):
    try:
        import psutil
        cpu_v  = psutil.cpu_percent(0.1)
        ram_v  = psutil.virtual_memory().percent
        disk_v = psutil.disk_usage("C:\\").percent
    except Exception:
        cpu_v = ram_v = disk_v = 0.0

    stats = [
        ("CPU",  f"{cpu_v:.0f}%",  AMBER,   cpu_v),
        ("RAM",  f"{ram_v:.0f}%",  BLUE,    ram_v),
        ("C:\\", f"{disk_v:.0f}%", EMERALD, disk_v),
    ]

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

    for i, (lbl, val, col, pct) in enumerate(stats):
        if i:
            tk.Frame(strip, bg=BORDER, width=1).pack(side="left", fill="y", pady=6)

        # Canvas = bg fill bar + text — avoids Label-bg clipping the fill
        cv = tk.Canvas(strip, bg=SURFACE, highlightthickness=0, height=44)
        cv.pack(side="left", expand=True, fill="x")

        fc = _fill(col)

        def _draw(e=None, _cv=cv, _lbl=lbl, _val=val,
                  _col=col, _pct=pct, _fc=fc):
            _cv.delete("all")
            W, H = _cv.winfo_width(), _cv.winfo_height()
            if W < 4 or H < 4:
                return
            fw = int(W * _pct / 100)
            if fw > 0:
                _cv.create_rectangle(0, 0, fw, H, fill=_fc, outline="")
            px = 12
            mid = H // 2
            _cv.create_text(px, mid - 7, text=_lbl, anchor="w",
                            fill=MUTED, font=(_F, 6))
            _cv.create_text(px, mid + 8, text=_val, anchor="w",
                            fill=_col,  font=(_F, 9, "bold"))

        cv.bind("<Configure>", _draw)


# ═════════════════════════════════════════════════════════════════════════════
# QUICK ACTIONS  (left panel)
# ═════════════════════════════════════════════════════════════════════════════

def _build_quick_actions(parent, nav_callback=None):
    """
    4 Quick Actions:
      1. Startup Apps Manager  → navigate to startup_manager
      2. Services Manager      → navigate to services_manager
      3. Disk Defragmenter     → open dfrgui
      4. Weekly Perf Report    → open report Toplevel
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

        {"key": "report",   "label": "Weekly Perf",  "sub": "Report",
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

        # ── Left accent bar (4 px — 70 % wider than original 2 px) ───────────
        tk.Frame(row, bg=col, width=4).pack(side="left", fill="y")

        # Icon
        _icv(row, qa["icon"], bg=row_bg, size=11).pack(
            side="left", padx=(7, 5), pady=7)

        # Text block: label + subtitle
        txt = tk.Frame(row, bg=row_bg)
        txt.pack(side="left", fill="both", expand=True)
        tk.Label(txt, text=label, font=("Segoe UI Semibold", 7),
                 bg=row_bg, fg="#a0b4cc" if row_bg == CARD else "#4aaa70",
                 anchor="w").pack(anchor="w", pady=(4, 0))
        if sub:
            tk.Label(txt, text=sub, font=(_F, 6),
                     bg=row_bg, fg=MUTED, anchor="w").pack(anchor="w", pady=(0, 4))

        # RUN / OPEN / VIEW button  (slightly larger: padx=10, pady=4)
        btn = tk.Label(row, text=btn_t, font=("Segoe UI Semibold", 6),
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
                            status_lbl.config(text=f"Navigate → {pid}")
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
# LIVE NOW  — compact auto-refresh mini-bars for the left sidebar
# ─────────────────────────────────────────────────────────────────────────────

def _build_live_mini(parent):
    """CPU / RAM / GPU live bars — updates every 2 s via after()."""
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
        vl = tk.Label(hdr, text="—", font=(_M, 5),
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
# FEATURE CARD BUILDER  — 2-column grid, [i] expandable panel
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
                "CPU stays at max frequency — no throttling.\n"
                "App exit auto-restores your original plan.\n"
                "Requires Administrator rights."
            ),
            "run_label": "ACTIVATE",
            "run_color": BORD_L,
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
        # startup_opt → moved to Quick Actions (Startup Manager)
        {"key": "bg_limiter",   "title": "Background Limiter",
         "desc": "Cap CPU for non-foreground processes",
         "color": VIOLET,  "icon": _ico_arrow, "ready": False,
         "info": "Uses Windows job objects to throttle background process\nCPU share, freeing headroom for the active app.",
         "run_label": "RUN", "run_color": VIOLET},
        # defrag_mon → moved to Quick Actions (Disk Defragmenter)
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
        # perf_report → moved to Quick Actions (Weekly Perf Report)
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
    canvas.bind_all("<MouseWheel>",
        lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"), add="+")

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
    """Globe icon — same as _ico_globe but with CARD2 default bg."""
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

    # Outer wrapper — padded cell
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

    # Icon — created directly inside compact with the right color and bg
    ic_col = color if ready else MUTED
    ic = icon_fn(ic_col, 12, p=compact, bg=CARD2)
    ic.pack(side="left", padx=(0, 6))

    # Title + desc
    txt_frame = tk.Frame(compact, bg=CARD2)
    txt_frame.pack(side="left", fill="both", expand=True)
    title_col = TEXT if ready else "#4a5a72"
    tk.Label(txt_frame, text=title, font=("Segoe UI Semibold", 8),
             bg=CARD2, fg=title_col, anchor="w").pack(anchor="w")
    tk.Label(txt_frame, text=desc, font=(_F, 7),
             bg=CARD2, fg="#4a5a72" if not ready else "#6a80a0",
             anchor="w").pack(anchor="w")

    # [i] button — gray, toggles highlight
    info_btn = tk.Label(compact, text=" i ",
                        font=("Segoe UI Semibold", 7),
                        bg="#161d2c", fg="#4a5568",
                        cursor="hand2", padx=5, pady=3,
                        highlightbackground="#1e2840", highlightthickness=1)
    info_btn.pack(side="right", padx=(6, 0))

    # ── Expansion panel ───────────────────────────────────────────────────────
    expand_frame = tk.Frame(card, bg="#090c14")
    # Initially hidden — shown on [i] click

    # Separator
    sep_line = tk.Frame(card, bg=BORDER2, height=1)

    # Info text
    info_inner = tk.Frame(expand_frame, bg="#090c14")
    info_inner.pack(fill="x", padx=10, pady=(8, 4))
    tk.Label(info_inner, text=info_text,
             font=(_F, 7), bg="#090c14", fg="#6a86a8",
             justify="left", anchor="w",
             wraplength=260).pack(anchor="w")

    # Controls row: AUTO slider | ON TURBO slider | RUN button
    ctrl = tk.Frame(expand_frame, bg="#090c14")
    ctrl.pack(fill="x", padx=10, pady=(4, 10))

    # AUTO toggle
    auto_state = {"on": False}
    auto_frame = tk.Frame(ctrl, bg="#090c14")
    auto_frame.pack(side="left")
    tk.Label(auto_frame, text="AUTO", font=("Segoe UI Semibold", 6),
             bg="#090c14", fg=MUTED).pack(side="left", padx=(0, 3))
    auto_pill = tk.Canvas(auto_frame, width=32, height=15,
                          bg="#090c14", highlightthickness=0,
                          cursor="hand2" if ready else "arrow")
    auto_pill.pack(side="left")
    _pill_cv(auto_pill, False, 32, 15, EMERALD)

    # ON TURBO toggle
    tk.Frame(ctrl, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)
    turbo_state = {"on": False}
    turbo_frame = tk.Frame(ctrl, bg="#090c14")
    turbo_frame.pack(side="left")
    tk.Label(turbo_frame, text="ON  TURBO", font=("Segoe UI Semibold", 6),
             bg="#090c14", fg=MUTED).pack(side="left", padx=(0, 3))
    turbo_pill = tk.Canvas(turbo_frame, width=32, height=15,
                           bg="#090c14", highlightthickness=0,
                           cursor="hand2" if ready else "arrow")
    turbo_pill.pack(side="left")
    _pill_cv(turbo_pill, False, 32, 15, BORD_L)

    # Status label
    status_lbl = tk.Label(ctrl, text="",
                          font=(_M, 6), bg="#090c14", fg=MUTED,
                          anchor="w")
    status_lbl.pack(side="left", fill="x", expand=True, padx=(8, 0))

    # RUN button
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

    # ── Feature-specific logic ────────────────────────────────────────────────
    if key == "ram_flush":
        _wire_ram_flush(run_btn, auto_pill, auto_state,
                        turbo_pill, turbo_state, status_lbl, run_color)
    elif key == "turbo_pp":
        _wire_turbo_pp(run_btn, auto_pill, auto_state,
                       turbo_pill, turbo_state, status_lbl, run_color)


def _wire_ram_flush(run_btn, auto_pill, auto_state,
                    turbo_pill, turbo_state, status_lbl, run_color):
    """Wire RAM flush card controls."""
    # Load prefs
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
                args=(status_lbl, status_lbl, None, lambda s: None),
                daemon=True).start()
        else:
            _RAM["stop_flag"] = True

    run_btn.bind("<Button-1>", _run)
    auto_pill.bind("<Button-1>", _toggle_auto)


def _wire_turbo_pp(run_btn, auto_pill, auto_state,
                   turbo_pill, turbo_state, status_lbl, run_color):
    """Wire Turbo Power Plan card controls."""
    prefs = _load_prefs().get("optimization", {})
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
                col = EMERALD if ok else RED
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

    _build_hero_header(root_frame)
    _build_snapshot_strip(root_frame)

    body = tk.Frame(root_frame, bg=BG)
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # LEFT: Quick Actions (210px — ~21 % narrower, giving Features more room)
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
    count = 0
    try:
        for proc in psutil.process_iter(["pid"]):
            pid = proc.pid
            if pid <= 4:
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
    if freed > 0:
        return True, f"Freed {freed} MB  ({count} procs)", before, after
    elif count > 0:
        return True, f"Flushed {count} procs (limited perms)", before, after
    return False, "No effect — admin rights needed", before, after


def _ram_monitor_loop(result_lbl, prog_lbl, run_cv, draw_run):
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

def _set_high_performance():
    try:
        r = subprocess.run(
            ["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
            capture_output=True, text=True, timeout=5)
        return (True, "High Performance plan activated.") if r.returncode == 0 \
               else (False, f"powercfg: {r.stderr.strip()[:50]}")
    except Exception as ex:
        return False, str(ex)[:50]

def _flush_dns():
    try:
        r = subprocess.run(["ipconfig", "/flushdns"],
                           capture_output=True, text=True, timeout=5)
        return (True, "DNS cache flushed.") if r.returncode == 0 \
               else (False, f"ipconfig: {r.stderr.strip()[:50]}")
    except Exception as ex:
        return False, str(ex)[:50]

def _clear_temp():
    import shutil
    removed = 0
    try:
        for name in os.listdir(tempfile.gettempdir()):
            path = os.path.join(tempfile.gettempdir(), name)
            try:
                if os.path.isfile(path):
                    os.unlink(path); removed += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True); removed += 1
            except Exception:
                pass
        return True, f"Cleared {removed} temp items."
    except Exception as ex:
        return False, str(ex)[:50]

def _boost_priority():
    try:
        import psutil, ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        fg = pid.value
        if fg and fg > 4:
            proc = psutil.Process(fg)
            proc.nice(psutil.HIGH_PRIORITY_CLASS)
            return True, f"Boosted: {proc.name()[:20]} (PID {fg})"
        return False, "No foreground process."
    except Exception as ex:
        return False, str(ex)[:50]


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
                        title: str, vals: list[float],
                        week_labels: list[str],
                        color: str) -> None:
    """
    One bar chart cell placed in a grid.
    vals        — 4 floats (week 1..4 oldest→newest)
    week_labels — 4 short strings, e.g. ["W1\n05-01", ...]
    """
    _BG   = "#0a0d15"
    _CARD = "#0e1218"
    _BD   = "#1a2235"
    _MUT  = "#2a3a50"
    _GRID = "#111825"

    cell = tk.Frame(parent, bg=_CARD,
                    highlightbackground=_BD, highlightthickness=1)
    cell.grid(row=gr, column=gc, sticky="nsew",
              padx=(0 if gc == 0 else 4, 0),
              pady=(0 if gr == 0 else 6, 0))

    # Title
    th = tk.Frame(cell, bg=_CARD)
    th.pack(fill="x", padx=8, pady=(6, 2))
    tk.Label(th, text=title, font=("Segoe UI Semibold", 8),
             bg=_CARD, fg=color).pack(side="left")
    max_v = max(vals) if any(v > 0 for v in vals) else 0
    if max_v > 0:
        tk.Label(th, text=f"peak {max_v:.0f}%",
                 font=("Segoe UI", 6), bg=_CARD, fg=_MUT).pack(side="right")

    # Chart canvas
    cv = tk.Canvas(cell, bg=_CARD, highlightthickness=0, height=110)
    cv.pack(fill="x", expand=False, padx=6, pady=(2, 8))

    max_val = max(vals) if any(v > 0 for v in vals) else 100.0

    def _draw(e=None,
              _cv=cv, _vals=vals, _lbls=week_labels,
              _col=color, _mx=max_val):
        _cv.delete("all")
        W = _cv.winfo_width()
        H = _cv.winfo_height()
        if W < 20 or H < 20:
            return

        n        = 4
        pad_l    = 26    # left margin (y-axis labels)
        pad_r    = 8
        pad_bot  = 20    # x-axis labels
        pad_top  = 16    # value labels
        chart_w  = W - pad_l - pad_r
        chart_h  = H - pad_bot - pad_top
        baseline = H - pad_bot

        # Horizontal grid lines at 25 / 50 / 75 / 100 %
        for pct in [25, 50, 75, 100]:
            y = baseline - int(chart_h * pct / 100)
            _cv.create_line(pad_l, y, W - pad_r, y, fill=_GRID, width=1)
            _cv.create_text(pad_l - 3, y, text=f"{pct}", anchor="e",
                            font=("Segoe UI", 5), fill=_MUT)

        # Bars
        slot_w = chart_w / n
        bar_w  = max(6, int(slot_w * 0.55))

        for i, (val, lbl) in enumerate(_zip4(_vals, _lbls)):
            cx = pad_l + int(slot_w * (i + 0.5))
            bh = int(chart_h * val / _mx) if _mx > 0 else 0
            x1, x2 = cx - bar_w//2, cx + bar_w//2
            y1, y2  = baseline - bh, baseline

            is_now = (i == 3)
            fill   = _col if is_now else _blend_hex(_col, "#0d1220", 0.55)
            # Bar shadow/glow for latest week
            if is_now and bh > 0:
                _cv.create_rectangle(x1+1, y1+1, x2+1, y2+1,
                                     fill=_blend_hex(_col, "#000000", 0.7),
                                     outline="")
            if bh > 0:
                _cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")

            # Value label
            if val > 0:
                label_col = _col if is_now else _MUT
                _cv.create_text(cx, y1 - 3, text=f"{val:.0f}%",
                                font=("Segoe UI", 6, "bold") if is_now
                                     else ("Segoe UI", 5),
                                fill=label_col, anchor="s")

            # X-axis label
            short = lbl.split("\n")[0]
            _cv.create_text(cx, baseline + 3, text=short,
                            font=("Segoe UI Semibold" if is_now else "Segoe UI", 6),
                            fill=_col if is_now else _MUT, anchor="n")

    cv.bind("<Configure>", _draw)


def _zip4(a, b):
    """zip of two exactly-4 sequences."""
    return list(zip(a, b))


def _generate_report_summary(week_data: list[list[dict]]) -> str:
    """Return a 1-paragraph AI-style text summary of 4-week data."""
    def _wa(wi, col):   # week average
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(sum(vs)/len(vs), 1) if vs else 0.0

    def _wm(wi, col):   # week max
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(max(vs), 1) if vs else 0.0

    parts = []

    # CPU trend
    ca = [_wa(w, "cpu_avg") for w in range(4)]
    vc = [v for v in ca if v > 0]
    if len(vc) >= 2:
        delta = vc[-1] - vc[0]
        if delta > 5:
            parts.append(f"CPU load trended UP +{delta:.0f}% over 4 weeks (now avg {vc[-1]:.0f}%).")
        elif delta < -5:
            parts.append(f"CPU load dropped {abs(delta):.0f}% over 4 weeks (now avg {vc[-1]:.0f}%).")
        else:
            parts.append(f"CPU load stayed stable around {sum(vc)/len(vc):.0f}% average.")

    # GPU — busiest week
    ga = [_wa(w, "gpu_avg") for w in range(4)]
    vg = [v for v in ga if v > 0]
    if vg:
        bw = ga.index(max(ga)) + 1
        parts.append(f"GPU was most active in Week {bw} (avg {max(vg):.0f}%).")

    # RAM pressure
    ra = [_wa(w, "ram_avg") for w in range(4)]
    vr = [v for v in ra if v > 0]
    if vr:
        cur = vr[-1]
        if cur > 80:
            parts.append(
                f"HIGH RAM pressure — current week avg {cur:.0f}%."
                "  Consider closing background apps or adding RAM.")
        else:
            parts.append(f"RAM healthy at {cur:.0f}% avg this week.")

    # CPU spike warning
    peaks = [_wm(w, "cpu_max") for w in range(4)]
    mp = max(peaks) if peaks else 0
    if mp > 90:
        pw = peaks.index(mp) + 1
        parts.append(
            f"CPU peaked at {mp:.0f}% in Week {pw} — check for heavy workloads.")

    if not parts:
        return ("No historical data yet.  "
                "PC Workman needs a few days of running to populate this report.")

    return "   ".join(parts)


def _export_report(win, week_data, week_labels):
    """Save a plain-text report to a user-chosen path."""
    import datetime
    import tkinter.filedialog as _fd

    path = _fd.asksaveasfilename(
        parent=win,
        defaultextension=".txt",
        filetypes=[("Text file", "*.txt"), ("All files", "*.*")],
        initialfile=f"pc_workman_report_{datetime.date.today()}.txt",
        title="Save Weekly Report",
    )
    if not path:
        return

    def _wa(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(sum(vs)/len(vs), 1) if vs else 0.0

    def _wm(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(max(vs), 1) if vs else 0.0

    lines = [
        "PC Workman HCK — Weekly Performance Report",
        f"Generated : {datetime.datetime.now().strftime('%Y-%m-%d  %H:%M')}",
        "=" * 56,
    ]
    for wi in range(4):
        lines.append(f"\n{week_labels[wi]}")
        lines.append(f"  CPU  avg {_wa(wi,'cpu_avg'):5.1f}%   peak {_wm(wi,'cpu_max'):5.1f}%")
        lines.append(f"  GPU  avg {_wa(wi,'gpu_avg'):5.1f}%   peak {_wm(wi,'gpu_max'):5.1f}%")
        lines.append(f"  RAM  avg {_wa(wi,'ram_avg'):5.1f}%   peak {_wm(wi,'ram_max'):5.1f}%")

    lines.append("\n" + "=" * 56)
    lines.append(_generate_report_summary(week_data))

    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    except Exception:
        pass


def _show_weekly_report(root_win) -> None:
    """Open the 4-week performance report Toplevel with 6 charts."""
    import datetime

    # ── Gather data ────────────────────────────────────────────────────────────
    raw: list[dict] = []
    try:
        from hck_gpt.data.metrics_store import metrics_store as _ms
        raw = _ms.daily_summary(days=28)
    except Exception:
        pass

    raw = sorted(raw, key=lambda r: r.get("date_str", ""))
    while len(raw) < 28:
        raw.insert(0, {})
    raw = raw[-28:]

    week_data = [raw[w*7:(w+1)*7] for w in range(4)]   # w=0 oldest

    def _week_label(wi):
        days = [d for d in week_data[wi] if d.get("date_str")]
        if days:
            return (f"Week {wi+1}   "
                    f"{days[0]['date_str'][5:]}  →  {days[-1]['date_str'][5:]}")
        return f"Week {wi+1}   no data"

    week_labels = [_week_label(w) for w in range(4)]

    def _wa(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(sum(vs)/len(vs), 1) if vs else 0.0

    def _wm(wi, col):
        vs = [d[col] for d in week_data[wi] if (d or {}).get(col, -1) >= 0]
        return round(max(vs), 1) if vs else 0.0

    # Pre-compute chart data
    _CPU  = AMBER
    _GPU  = VIOLET
    _RAM  = BLUE
    short_lbls = [f"W{i+1}" for i in range(4)]

    chart_specs = [
        # (row, col, title, vals, color)
        (0, 0, "CPU  —  Average %",
         [_wa(w, "cpu_avg") for w in range(4)], _CPU),
        (0, 1, "GPU  —  Average %",
         [_wa(w, "gpu_avg") for w in range(4)], _GPU),
        (0, 2, "RAM  —  Average %",
         [_wa(w, "ram_avg") for w in range(4)], _RAM),
        (1, 0, "CPU  —  Peak %",
         [_wm(w, "cpu_max") for w in range(4)], _CPU),
        (1, 1, "GPU  —  Peak %",
         [_wm(w, "gpu_max") for w in range(4)], _GPU),
        (1, 2, "RAM  —  Peak %",
         [_wm(w, "ram_max") for w in range(4)], _RAM),
    ]

    # ── Window ─────────────────────────────────────────────────────────────────
    _R_BG  = "#070a0f"
    _R_BD  = "#161e2e"
    _R_TXT = "#c4cfdf"
    _R_MUT = "#2e3e56"
    _ACCNT = "#8b5cf6"

    win = tk.Toplevel(root_win)
    win.title("Weekly Performance Report — PC Workman")
    win.geometry("940x660+80+60")
    win.resizable(False, False)
    win.configure(bg=_R_BG)
    win.grab_set()

    # Header ──────────────────────────────────────────────────────────────────
    hdr = tk.Canvas(win, bg="#090d18", height=54, highlightthickness=0)
    hdr.pack(fill="x")

    def _draw_hdr(e=None):
        hdr.delete("all")
        Wh = hdr.winfo_width()
        hdr.create_rectangle(0, 0, 4, 54, fill=_ACCNT, outline="")
        hdr.create_text(18, 14, text="WEEKLY PERFORMANCE REPORT",
                        anchor="w", font=("Segoe UI Semibold", 12), fill=_R_TXT)
        now_s = datetime.datetime.now().strftime("%d.%m.%Y  %H:%M")
        hdr.create_text(18, 36, text=f"PC Workman HCK  ·  {now_s}  ·  Last 4 weeks",
                        anchor="w", font=("Segoe UI", 8), fill=_R_MUT)
        # ✕ button
        hdr.create_text(Wh - 18, 27, text="✕", anchor="center",
                        font=("Segoe UI", 13), fill="#2e3e56", tags="close_hdr")
    hdr.bind("<Configure>", _draw_hdr)
    hdr.tag_bind("close_hdr", "<Button-1>", lambda e: win.destroy())
    hdr.tag_bind("close_hdr", "<Enter>",
                 lambda e: hdr.itemconfig("close_hdr", fill="#ef4444"))
    hdr.tag_bind("close_hdr", "<Leave>",
                 lambda e: hdr.itemconfig("close_hdr", fill="#2e3e56"))

    # Week labels strip ───────────────────────────────────────────────────────
    wk_strip = tk.Frame(win, bg="#0c1018")
    wk_strip.pack(fill="x")
    for wi in range(4):
        if wi:
            tk.Frame(wk_strip, bg=_R_BD, width=1).pack(side="left", fill="y")
        f = tk.Frame(wk_strip, bg="#0c1018")
        f.pack(side="left", expand=True, fill="x")
        fg_col = _ACCNT if wi == 3 else _R_MUT
        tk.Label(f, text=week_labels[wi],
                 font=("Segoe UI Semibold" if wi == 3 else "Segoe UI", 7),
                 bg="#0c1018", fg=fg_col, pady=5).pack()
    tk.Frame(win, bg=_R_BD, height=1).pack(fill="x")

    # 6 Charts grid ───────────────────────────────────────────────────────────
    charts_outer = tk.Frame(win, bg=_R_BG)
    charts_outer.pack(fill="both", expand=True, padx=10, pady=(8, 4))
    charts_outer.columnconfigure(0, weight=1)
    charts_outer.columnconfigure(1, weight=1)
    charts_outer.columnconfigure(2, weight=1)
    charts_outer.rowconfigure(0, weight=1)
    charts_outer.rowconfigure(1, weight=1)

    for gr, gc, title, vals, col in chart_specs:
        _build_weekly_chart(charts_outer, gr, gc,
                            title, vals, short_lbls, col)

    # Summary bar ─────────────────────────────────────────────────────────────
    tk.Frame(win, bg=_R_BD, height=1).pack(fill="x", padx=10)
    footer = tk.Frame(win, bg="#090c14")
    footer.pack(fill="x", padx=10, pady=(5, 8))

    summary = _generate_report_summary(week_data)
    tk.Label(footer, text=summary,
             font=("Segoe UI", 7), bg="#090c14", fg="#4a6888",
             justify="left", anchor="w", wraplength=720).pack(
                 side="left", padx=12, pady=6, fill="x", expand=True)

    exp_btn = tk.Label(footer, text="EXPORT  .TXT",
                       font=("Segoe UI Semibold", 7),
                       bg="#0f1a2a", fg=BLUE, cursor="hand2",
                       padx=10, pady=5,
                       highlightbackground="#1e3a5f", highlightthickness=1)
    exp_btn.pack(side="right", padx=(6, 12), pady=6)
    exp_btn.bind("<Button-1>",
                 lambda e: _export_report(win, week_data, week_labels))
    exp_btn.bind("<Enter>", lambda e: exp_btn.config(fg="#93c5fd"))
    exp_btn.bind("<Leave>", lambda e: exp_btn.config(fg=BLUE))
