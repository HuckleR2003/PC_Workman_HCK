"""
MONITORING & ALERTS - Time-Travel Statistics Center
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Innovations in this redesign:
  1. Adaptive Baseline Band      - learned mean ±σ shaded on every chart
  2. Anomaly Decay Visualisation - spike highlights fade as pattern becomes "normal"
  3. Health Rings                - 3 concentric arc gauges (thermal / memory / load)
  4. 30-Day Anomaly Calendar     - clickable heatmap, anomaly density per day
  5. Alert Timeline Strip        - thin horizontal event strip below each chart
  6. Session Overview Bar        - 5 live metric cards at the top
  7. Contextual Tooltips         - "XX°C (Y % above usual for this time)"
"""

import tkinter as tk
import time
import math
import threading
from datetime import datetime, timedelta

# ── Interactive chart component ───────────────────────────────────────────────
try:
    from ui.components.interactive_chart import InteractiveChart as _IChart
    _HAS_ICHART = True
except ImportError:
    _HAS_ICHART = False
    _IChart     = None

# ── Intelligence modules (graceful fallback if missing) ───────────────────────
try:
    from core.thermal_baseline import thermal_baseline as _thermal_bl
    _HAS_THERMAL_BL = True
except ImportError:
    _HAS_THERMAL_BL = False
    _thermal_bl     = None

try:
    from core.voltage_analyzer import voltage_analyzer as _volt_az, RAILS as _VOLT_RAILS
    _HAS_VOLT_AZ = True
except ImportError:
    _HAS_VOLT_AZ = False
    _volt_az     = None
    _VOLT_RAILS  = {}

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Palette ────────────────────────────────────────────────────────────────────
BG      = "#060911"
PANEL   = "#0c1018"
PANEL2  = "#10151e"
BORDER  = "#1a2030"
TEXT    = "#e2e8f0"
MUTED   = "#6b7280"
DIM     = "#74839a"   # readable dim (was #374151 — barely visible on dark)

TEMP_C  = "#f59e0b"    # amber  - temperature
LOAD_C  = "#3b82f6"    # blue   - CPU load
RAM_C   = "#10b981"    # emerald - RAM
GPU_C   = "#f97316"    # orange - GPU
VOLT_C  = "#8b5cf6"    # violet - voltage / multi
CAL_C   = "#7c3aed"    # purple - calendar
ALERT_C = "#ef4444"    # red    - alerts
OK_C    = "#22c55e"    # green  - healthy
WARN_C  = "#f59e0b"    # amber  - warning
CRIT_C  = "#ef4444"    # red    - critical


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def build_monitoring_alerts_page(self, parent):
    main = tk.Frame(parent, bg=BG)
    main.pack(fill="both", expand=True)

    canvas = tk.Canvas(main, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(main, orient="vertical", command=canvas.yview,
                      bg=BG, troughcolor=BG, width=5)
    sf = tk.Frame(canvas, bg=BG)
    sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win_id = canvas.create_window((0, 0), window=sf, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

    def _wheel(event):
        try:
            # Interactive charts (Temperature / Voltage-Load) zoom on the wheel
            # via their own canvas binding. bind_all fires IN ADDITION to that
            # widget binding, so without this guard the page scrolled while the
            # chart zoomed - wheel felt broken over charts. If the widget under
            # the cursor handles the wheel itself, leave it alone.
            w = event.widget
            if isinstance(w, tk.Canvas) and w.bind("<MouseWheel>"):
                return
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
    # No add="+": overwrite the previous page's global wheel handler instead
    # of stacking a dead one per page visit.
    canvas.bind_all("<MouseWheel>", _wheel)

    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # ── Header (contains HEALTH + ANOMALIES badges) ───────────────────────────
    rings_cv, score_ref, health_lbl, anom_lbl = _build_page_header(sf)

    # ── Learning status bar ───────────────────────────────────────────────────
    _build_learning_center(sf)

    # ── Temperature section ───────────────────────────────────────────────────
    temp_sec = _build_temperature_section(sf)

    # ── Voltage / Load section ────────────────────────────────────────────────
    load_sec = _build_load_section(sf)

    # ── Voltage Rails (SPC) ───────────────────────────────────────────────────
    volt_sec = _build_voltage_section(sf)

    # ── 30-day Anomaly Calendar ───────────────────────────────────────────────
    _build_anomaly_calendar(sf)

    # ── Events log ────────────────────────────────────────────────────────────
    _build_alerts_log(sf)

    # ── Kick off baseline rebuilds immediately (async) ────────────────────────
    if _HAS_THERMAL_BL:
        _thermal_bl.maybe_rebuild(60.0)
    if _HAS_VOLT_AZ:
        _volt_az.maybe_rebuild(60.0)

    # ── Auto-refresh ─────────────────────────────────────────────────────────
    _start_refresh(parent, rings_cv, score_ref, health_lbl, anom_lbl,
                   temp_sec, load_sec, volt_sec)


# ──────────────────────────────────────────────────────────────────────────────
# 1. PAGE HEADER - with health rings
# ──────────────────────────────────────────────────────────────────────────────

def _build_page_header(parent):
    hdr = tk.Frame(parent, bg=PANEL)
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=TEMP_C, height=2).pack(fill="x")

    body = tk.Frame(hdr, bg=PANEL)
    body.pack(fill="x", padx=20, pady=12)

    # Pack RIGHT items first so left block fills remaining space correctly

    # ── Far right: health score (arc gauge + labeled component bars) ─────────
    rings_cv = tk.Canvas(body, width=214, height=84,
                         bg=PANEL, highlightthickness=0)
    rings_cv.pack(side="right", padx=(0, 10))
    score_ref = [90]
    _draw_health_rings(rings_cv, 84, 90, 70, 55)

    # ── Centre: HEALTH + ANOMALIES mini badges (stacked vertically) ──────────
    mid = tk.Frame(body, bg=PANEL)
    mid.pack(side="right", padx=(0, 22), anchor="center")

    # HEALTH badge
    h_out = tk.Frame(mid, bg=BORDER)
    h_out.pack(fill="x", pady=(0, 5))
    h_in = tk.Frame(h_out, bg="#081a0a")
    h_in.pack(padx=1, pady=1)
    tk.Label(h_in, text="HEALTH", font=(_MONO, 7, "bold"),
             bg="#081a0a", fg=DIM).pack(anchor="w", padx=8, pady=(4, 0))
    health_lbl = tk.Label(h_in, text="--", font=(_MONO, 13, "bold"),
                          bg="#081a0a", fg=OK_C)
    health_lbl.pack(anchor="w", padx=8, pady=(0, 4))

    # ANOMALIES badge
    a_out = tk.Frame(mid, bg=BORDER)
    a_out.pack(fill="x")
    a_in = tk.Frame(a_out, bg="#0f0820")
    a_in.pack(padx=1, pady=1)
    tk.Label(a_in, text="ANOMALIES", font=(_MONO, 7, "bold"),
             bg="#0f0820", fg=DIM).pack(anchor="w", padx=8, pady=(4, 0))
    anom_lbl = tk.Label(a_in, text="0", font=(_MONO, 13, "bold"),
                        bg="#0f0820", fg=VOLT_C)
    anom_lbl.pack(anchor="w", padx=8, pady=(0, 4))

    # ── Left: title + status (fills remaining space) ─────────────────────────
    left = tk.Frame(body, bg=PANEL)
    left.pack(side="left", fill="both", expand=True)

    top_row = tk.Frame(left, bg=PANEL)
    top_row.pack(anchor="w")
    tk.Label(top_row, text="◈", font=(_BODY, 14),
             bg=PANEL, fg=TEMP_C).pack(side="left")
    tk.Label(top_row, text="  MONITORING & ALERTS",
             font=(_MONO, 12, "bold"),
             bg=PANEL, fg=TEXT).pack(side="left")

    engine_ok    = False
    record_count = 0
    try:
        from hck_stats_engine.db_manager import db_manager
        engine_ok = db_manager.is_ready
        if engine_ok:
            conn = db_manager.get_connection()
            if conn:
                record_count = conn.execute(
                    "SELECT COUNT(*) FROM minute_stats").fetchone()[0]
    except Exception:
        pass

    status_col = OK_C if engine_ok else CRIT_C
    status_txt = "● ACTIVE" if engine_ok else "● OFFLINE"
    tk.Label(left, text=status_txt, font=(_MONO, 8, "bold"),
             bg=PANEL, fg=status_col).pack(anchor="w", pady=(4, 0))
    if record_count:
        tk.Label(left,
                 text=f"Time-Travel Statistics Center  ·  {record_count:,} data points",
                 font=(_BODY, 8), bg=PANEL, fg=MUTED).pack(anchor="w")

    tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
    return rings_cv, score_ref, health_lbl, anom_lbl


def _draw_health_rings(canvas, size, thermal, memory, load):
    """Health score widget: one clean arc gauge (overall) + three labeled
    component bars. Replaced the three concentric rings, which overlapped
    into an unreadable blob at 80 px."""
    canvas.delete("all")
    W = canvas.winfo_width()
    if W <= 1:
        W = int(canvas["width"])
    H = canvas.winfo_height()
    if H <= 1:
        H = int(canvas["height"])

    avg   = int(round((thermal + memory + load) / 3))
    a_col = OK_C if avg >= 80 else WARN_C if avg >= 55 else CRIT_C

    # ── Left: single arc gauge with the overall score ─────────────────────────
    r  = 28
    cx = 10 + r
    cy = H // 2
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                      start=225, extent=-270,
                      outline="#1c2433", width=7, style="arc")
    canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                      start=225,
                      extent=-(270 * max(0, min(100, avg)) / 100),
                      outline=a_col, width=7, style="arc")
    canvas.create_text(cx, cy - 3, text=str(avg),
                       font=(_MONO, 15, "bold"), fill=a_col)
    canvas.create_text(cx, cy + 15, text="SCORE",
                       font=(_MONO, 6), fill=DIM)

    # ── Right: three labeled component bars ───────────────────────────────────
    bx = cx + r + 16
    bw = W - bx - 8
    rows = [("Thermal", thermal, TEMP_C),
            ("Memory",  memory,  RAM_C),
            ("Load",    load,    LOAD_C)]
    for i, (name, val, base_col) in enumerate(rows):
        y = cy - 24 + i * 24
        v = max(0, min(100, int(val)))
        v_col = OK_C if v >= 80 else WARN_C if v >= 55 else CRIT_C
        canvas.create_text(bx, y, text=name, anchor="w",
                           font=(_BODY, 7), fill=MUTED)
        canvas.create_text(W - 8, y, text=str(v), anchor="e",
                           font=(_MONO, 8, "bold"), fill=v_col)
        canvas.create_rectangle(bx, y + 6, bx + bw, y + 11,
                                fill="#161c28", outline="")
        fw = int(bw * v / 100)
        if fw > 0:
            canvas.create_rectangle(bx, y + 6, bx + fw, y + 11,
                                    fill=base_col, outline="")


# ──────────────────────────────────────────────────────────────────────────────
# 2. SESSION OVERVIEW BAR
# ──────────────────────────────────────────────────────────────────────────────

def _build_session_overview(parent):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", padx=15, pady=(10, 4))

    cards_spec = [
        ("CPU TEMP", "--",  TEMP_C, "ov_cpu_temp"),
        ("RAM",      "--",  RAM_C,  "ov_ram"),
        ("GPU TEMP", "--",  GPU_C,  "ov_gpu_temp"),
        ("HEALTH",   "--",  OK_C,   "ov_health"),
        ("ANOMALIES","0",   VOLT_C, "ov_anomalies"),
    ]

    for title, val, col, key in cards_spec:
        outer = tk.Frame(row, bg=BORDER)
        outer.pack(side="left", fill="both", expand=True, padx=(0, 4))
        card = tk.Frame(outer, bg=PANEL)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(card, bg=col, height=2).pack(fill="x")
        body = tk.Frame(card, bg=PANEL)
        body.pack(fill="x", padx=8, pady=6)
        tk.Label(body, text=title, font=(_MONO, 7, "bold"),
                 bg=PANEL, fg=DIM).pack(anchor="w")
        lbl = tk.Label(body, text=val, font=(_MONO, 13, "bold"),
                       bg=PANEL, fg=col)
        lbl.pack(anchor="w")
        setattr(row, key, lbl)

    return row


# ──────────────────────────────────────────────────────────────────────────────
# 3. TEMPERATURE SECTION
# ──────────────────────────────────────────────────────────────────────────────

def _build_temperature_section(parent):
    section = _make_section(parent)

    # Header
    hdr = tk.Frame(section, bg="#1a1200")
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=TEMP_C, height=2).pack(fill="x")
    hdr_body = tk.Frame(hdr, bg="#1a1200")
    hdr_body.pack(fill="x", padx=10, pady=5)
    tk.Label(hdr_body, text="🌡  TEMPERATURE MONITOR",
             font=(_MONO, 9, "bold"),
             bg="#1a1200", fg=TEMP_C).pack(side="left")

    # Workload badge (updated by refresh)
    workload_lbl = tk.Label(hdr_body, text="Workload: detecting…",
                            font=(_MONO, 7), bg="#1a1200", fg=MUTED)
    workload_lbl.pack(side="left", padx=(14, 0))

    # Scale buttons
    scale_frame, scale_var = _build_scale_buttons(
        hdr_body, color=TEMP_C,
        callback=lambda s: _refresh_temp(section))
    section._temp_scale = scale_var

    # Content
    content = tk.Frame(section, bg=PANEL)
    content.pack(fill="x", padx=8, pady=6)

    chart_frame = tk.Frame(content, bg="#050809")
    chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

    if _HAS_ICHART:
        ic = _IChart(chart_frame, height=150, minimap=True,
                     y_min_range=8.0, label="")
        section._ichart_temp = ic
        # Keep legacy refs so existing code that checks _chart_canvas still works
        section._chart_canvas = ic.canvas
        section._chart_data   = []
        # No separate timeline strip needed — anomalies shown as markers on chart
        section._timeline_cv  = None
    else:
        chart_cv = tk.Canvas(chart_frame, bg="#050809", height=128, highlightthickness=0)
        chart_cv.pack(fill="x", padx=2, pady=2)
        section._chart_canvas = chart_cv
        section._chart_data   = []
        tl_cv = tk.Canvas(chart_frame, bg="#03050a", height=22, highlightthickness=0)
        tl_cv.pack(fill="x")
        section._timeline_cv  = tl_cv
        section._ichart_temp  = None

    # Stats panel
    stats_f = tk.Frame(content, bg=PANEL2, width=165)
    stats_f.pack(side="right", fill="y")
    stats_f.pack_propagate(False)
    section._stats_frame = stats_f
    _build_temp_stats(stats_f)

    # Learn bar
    learn_bar = tk.Frame(section, bg=PANEL)
    learn_bar.pack(fill="x", padx=8, pady=(0, 6))
    tk.Label(learn_bar, text="🧠", font=(_BODY, 8), bg=PANEL).pack(side="left")
    tk.Label(learn_bar, text="Adapts to your device's temperature patterns over time",
             font=(_BODY, 7), bg=PANEL, fg="#94a3b8").pack(side="left", padx=(4, 8))
    badge = tk.Label(learn_bar, text="No regular problems",
                     font=(_MONO, 7, "bold"),
                     bg="#0d2818", fg="#4ade80", padx=8, pady=1)
    badge.pack(side="right")
    section._temp_badge  = badge
    section._workload_lbl = workload_lbl

    return section


def _build_temp_stats(parent):
    tk.Label(parent, text="STATISTICS",
             font=(_MONO, 8, "bold"),
             bg=PANEL2, fg=TEMP_C, pady=5).pack(fill="x")

    stats = [
        ("Today AVG",    "--",   TEXT,   "temp_today_avg"),
        ("Lifetime AVG", "--",   MUTED,  "temp_lifetime_avg"),
        ("Max safe",     "85°C", CRIT_C, "temp_max_safe"),
        ("Current",      "--",   LOAD_C, "temp_current"),
        ("Today MAX",    "--",   WARN_C, "temp_today_max"),
        ("Spikes (24 h)","0",    WARN_C, "temp_spikes"),
        ("Trend",        "->",    MUTED,  "temp_trend"),
    ]
    for label, value, col, key in stats:
        row = tk.Frame(parent, bg=PANEL2)
        row.pack(fill="x", padx=6, pady=2)
        tk.Label(row, text=label, font=(_MONO, 8),
                 bg=PANEL2, fg=TEXT, anchor="w").pack(side="left")
        lbl = tk.Label(row, text=value, font=(_MONO, 9, "bold"),
                       bg=PANEL2, fg=col, anchor="e")
        lbl.pack(side="right")
        setattr(parent, key, lbl)


# ──────────────────────────────────────────────────────────────────────────────
# 4. LOAD SECTION (CPU / RAM / GPU multi-line)
# ──────────────────────────────────────────────────────────────────────────────

def _build_load_section(parent):
    section = _make_section(parent)

    hdr = tk.Frame(section, bg="#08101a")
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=LOAD_C, height=2).pack(fill="x")
    hdr_body = tk.Frame(hdr, bg="#08101a")
    hdr_body.pack(fill="x", padx=10, pady=5)
    tk.Label(hdr_body, text="⚡  VOLTAGE / LOAD MONITOR",
             font=(_MONO, 9, "bold"),
             bg="#08101a", fg=LOAD_C).pack(side="left")

    scale_frame, scale_var = _build_scale_buttons(
        hdr_body, color=LOAD_C,
        callback=lambda s: _refresh_load(section))
    section._load_scale = scale_var

    content = tk.Frame(section, bg=PANEL)
    content.pack(fill="x", padx=8, pady=6)

    chart_frame = tk.Frame(content, bg="#050809")
    chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

    if _HAS_ICHART:
        ic_load = _IChart(chart_frame, height=150, minimap=True,
                          y_min_range=10.0)
        section._ichart_load  = ic_load
        section._chart_canvas = ic_load.canvas
        section._chart_data   = []
        section._timeline_cv  = None
    else:
        chart_cv = tk.Canvas(chart_frame, bg="#050809", height=128, highlightthickness=0)
        chart_cv.pack(fill="x", padx=2, pady=2)
        section._chart_canvas = chart_cv
        section._chart_data   = []
        section._ichart_load  = None

        # Legend (only for static version)
        legend = tk.Frame(chart_frame, bg="#050809")
        legend.pack(fill="x", padx=4, pady=(0, 3))
        for name, col in [("CPU", LOAD_C), ("RAM", RAM_C), ("GPU", GPU_C)]:
            tk.Label(legend, text="●", font=(_MONO, 7),
                     bg="#050809", fg=col).pack(side="left", padx=(0, 1))
            tk.Label(legend, text=name, font=(_MONO, 7),
                     bg="#050809", fg=MUTED).pack(side="left", padx=(0, 8))

        tl_cv = tk.Canvas(chart_frame, bg="#03050a", height=22, highlightthickness=0)
        tl_cv.pack(fill="x")
        section._timeline_cv = tl_cv

    # Legend for interactive version (separate row, always shown)
    if _HAS_ICHART:
        leg = tk.Frame(chart_frame, bg="#050809")
        leg.pack(fill="x", padx=4, pady=(0, 2))
        for name, col in [("CPU", LOAD_C), ("RAM", RAM_C), ("GPU", GPU_C)]:
            tk.Label(leg, text="●", font=(_MONO, 7),
                     bg="#050809", fg=col).pack(side="left", padx=(0, 1))
            tk.Label(leg, text=name, font=(_MONO, 7),
                     bg="#050809", fg=MUTED).pack(side="left", padx=(0, 8))

    stats_f = tk.Frame(content, bg=PANEL2, width=165)
    stats_f.pack(side="right", fill="y")
    stats_f.pack_propagate(False)
    section._stats_frame = stats_f
    _build_load_stats(stats_f)

    learn_bar = tk.Frame(section, bg=PANEL)
    learn_bar.pack(fill="x", padx=8, pady=(0, 6))
    tk.Label(learn_bar, text="🧠", font=(_BODY, 8), bg=PANEL).pack(side="left")
    tk.Label(learn_bar, text="Learns normal load patterns - unusual spikes stand out more over time",
             font=(_BODY, 7), bg=PANEL, fg="#94a3b8").pack(side="left", padx=(4, 8))
    badge = tk.Label(learn_bar, text="No load anomalies",
                     font=(_MONO, 7, "bold"),
                     bg="#0d2818", fg="#4ade80", padx=8, pady=1)
    badge.pack(side="right")
    section._load_badge = badge

    return section


def _build_load_stats(parent):
    tk.Label(parent, text="LOAD STATS",
             font=(_MONO, 8, "bold"),
             bg=PANEL2, fg=LOAD_C, pady=5).pack(fill="x")

    stats = [
        ("CPU Today AVG", "--", LOAD_C, "load_cpu_avg"),
        ("RAM Today AVG", "--", RAM_C,  "load_ram_avg"),
        ("GPU Today AVG", "--", GPU_C,  "load_gpu_avg"),
        ("CPU Peak (24h)","--", CRIT_C, "load_cpu_peak"),
        ("RAM Peak (24h)","--", CRIT_C, "load_ram_peak"),
        ("Anomalies",     "0",  WARN_C, "load_anomalies"),
        ("Uptime today",  "--", MUTED,  "load_uptime"),
    ]
    for label, value, col, key in stats:
        row = tk.Frame(parent, bg=PANEL2)
        row.pack(fill="x", padx=6, pady=2)
        tk.Label(row, text=label, font=(_MONO, 8),
                 bg=PANEL2, fg=TEXT, anchor="w").pack(side="left")
        lbl = tk.Label(row, text=value, font=(_MONO, 9, "bold"),
                       bg=PANEL2, fg=col, anchor="e")
        lbl.pack(side="right")
        setattr(parent, key, lbl)


# ──────────────────────────────────────────────────────────────────────────────
# LEARNING STATUS BAR
# ──────────────────────────────────────────────────────────────────────────────

_LEVEL_COLORS = {
    "no_data":     ("#1a1a1a", "#374151"),
    "initializing":("#1a1000", "#78350f"),
    "learning":    ("#1a1400", "#d97706"),
    "basic":       ("#0d1f0d", "#16a34a"),
    "trained":     ("#0a2010", "#22c55e"),
    "calibrated":  ("#061808", "#4ade80"),
}

_LC_BUCKETS = [("idle", "Idle"), ("light", "Light"), ("medium", "Medium"),
               ("heavy", "Heavy"), ("gaming", "Gaming")]


def _build_learning_center(parent):
    """At-a-glance view of what PC Workman has learned: thermal baselines per
    workload + voltage SPC baselines + overall progress. The Rebuild button is a
    live self-check that the learning engines are actually working."""
    if not _HAS_THERMAL_BL and not _HAS_VOLT_AZ:
        return

    section = _make_section(parent)
    tk.Frame(section, bg="#6366f1", height=2).pack(fill="x")

    hdr = tk.Frame(section, bg=PANEL)
    hdr.pack(fill="x", padx=12, pady=(8, 2))
    tk.Label(hdr, text="🧠", font=(_BODY, 11), bg=PANEL).pack(side="left")
    tk.Label(hdr, text=" WHAT PC WORKMAN HAS LEARNED", font=(_HDR, 9),
             bg=PANEL, fg="#a5b4fc").pack(side="left")

    pct_lbl = tk.Label(hdr, text="", font=(_MONO, 8, "bold"), bg=PANEL, fg=DIM)
    pct_lbl.pack(side="right", padx=(8, 0))
    psu_lbl = tk.Label(hdr, text="", font=(_MONO, 8, "bold"), bg=PANEL, fg=DIM)
    psu_lbl.pack(side="right", padx=(8, 0))
    upd_lbl = tk.Label(hdr, text="", font=(_MONO, 7), bg=PANEL, fg=DIM)
    upd_lbl.pack(side="right", padx=(8, 0))
    reb = tk.Label(hdr, text="↻ Rebuild", font=(_MONO, 7, "bold"),
                   bg="#13182a", fg="#818cf8", cursor="hand2", padx=8, pady=2)
    reb.pack(side="right", padx=(8, 0))

    body = tk.Frame(section, bg=PANEL)
    body.pack(fill="x", padx=12, pady=(2, 4))

    tk.Label(section,
             text="ℹ The longer it runs, the better it knows YOUR normal — "
                  "and the smarter the temperature & voltage alerts become.",
             font=(_BODY, 7), bg=PANEL, fg=MUTED, anchor="w",
             wraplength=720, justify="left").pack(fill="x", padx=12, pady=(0, 8))

    def _populate():
        for w in body.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        body.grid_columnconfigure(0, weight=1, uniform="lc")
        body.grid_columnconfigure(1, weight=1, uniform="lc")
        left  = tk.Frame(body, bg=PANEL)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = tk.Frame(body, bg=PANEL)
        right.grid(row=0, column=1, sticky="nsew")
        _lc_thermal(left)
        _lc_voltage(right)
        if _HAS_THERMAL_BL:
            p = _thermal_bl.overall_training_pct()
            pct_lbl.config(text=f"{p}% learned",
                           fg=OK_C if p >= 80 else WARN_C if p >= 40 else "#6366f1")
            upd_lbl.config(text=f"rebuilt {_thermal_bl.last_update_str()}")
        if _HAS_VOLT_AZ and _volt_az.is_data_available():
            try:
                hs = _volt_az.overall_health_score()
                psu_lbl.config(text=f"PSU {hs}%",
                               fg=OK_C if hs >= 80 else WARN_C if hs >= 50 else "#ef4444")
            except Exception:
                psu_lbl.config(text="")
        else:
            psu_lbl.config(text="")

    def _rebuild(_=None):
        reb.config(text="↻ …", fg=DIM)

        def _bg():
            try:
                if _HAS_THERMAL_BL:
                    _thermal_bl.rebuild(force=True)
                if _HAS_VOLT_AZ:
                    _volt_az.rebuild(force=True)
            except Exception:
                pass
            try:
                if section.winfo_exists():
                    section.after(0, lambda: (_populate(),
                                              reb.config(text="↻ Rebuild", fg="#818cf8")))
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True, name="lc-rebuild").start()

    reb.bind("<Button-1>", _rebuild)
    reb.bind("<Enter>", lambda e: reb.config(fg="#c4b5fd") if "…" not in reb.cget("text") else None)
    reb.bind("<Leave>", lambda e: reb.config(fg="#818cf8") if "…" not in reb.cget("text") else None)

    _populate()
    return section


def _lc_thermal(parent):
    if not _HAS_THERMAL_BL:
        tk.Label(parent, text="LEARNING  ·  per workload", font=(_MONO, 7, "bold"),
                 bg=PANEL, fg=TEMP_C).pack(anchor="w", pady=(0, 3))
        tk.Label(parent, text="learning engine unavailable", font=(_BODY, 7),
                 bg=PANEL, fg=MUTED).pack(anchor="w")
        return
    # The primary metric is whatever this machine can actually learn:
    # CPU temp (needs LHM) -> GPU temp (NVIDIA) -> CPU load (always). So the bars
    # fill for EVERYONE, not just users running LibreHardwareMonitor.
    try:
        pm   = _thermal_bl.primary_metric()
        unit = _thermal_bl.metric_unit(pm)
        head = _thermal_bl.metric_label(pm).upper()
        avail = _thermal_bl.available_metrics()
    except Exception:
        pm, unit, head, avail = "cpu_temp", "°C", "CPU TEMP", []

    tk.Label(parent, text=f"{head}  ·  per workload", font=(_MONO, 7, "bold"),
             bg=PANEL, fg=TEMP_C).pack(anchor="w", pady=(0, 3))
    status = _thermal_bl.training_status(pm)
    for bk, label in _LC_BUCKETS:
        info  = status.get(bk, {})
        level = info.get("level", "no_data")
        n     = int(info.get("n", 0))
        tp    = int(info.get("training_pct", 0))
        _, fg_c = _LEVEL_COLORS.get(level, _LEVEL_COLORS["no_data"])

        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, font=(_MONO, 7), bg=PANEL, fg=TEXT,
                 width=7, anchor="w").pack(side="left")
        cv = tk.Canvas(row, width=96, height=8, bg=PANEL, highlightthickness=0)
        cv.pack(side="left", padx=(0, 6))
        cv.create_rectangle(0, 2, 96, 7, fill="#161c28", outline="")
        fw = int(96 * min(max(tp, 0), 100) / 100)
        if fw > 0:
            cv.create_rectangle(0, 2, fw, 7, fill=fg_c, outline="")
        detail = (f"{info.get('p5', 0):.0f}–{info.get('p95', 0):.0f}{unit}"
                  if n >= 20 else f"{n * 5 / 60:.1f}h obs")
        tk.Label(row, text=detail, font=(_MONO, 7), bg=PANEL, fg=MUTED,
                 width=9, anchor="w").pack(side="left")
        tk.Label(row, text=level, font=(_MONO, 7), bg=PANEL, fg=fg_c,
                 anchor="w").pack(side="left")

    # Time counter: how long we've been observing + hours of real machine time
    try:
        since = _thermal_bl.learning_since_str()
        hrs   = _thermal_bl.total_observed_hours()
        tk.Label(parent,
                 text=f"⏱ Learning for {since}  ·  {hrs:.0f}h of your machine observed",
                 font=(_BODY, 7), bg=PANEL, fg="#8aa0bc", anchor="w").pack(anchor="w", pady=(3, 0))
    except Exception:
        pass

    # Honest unlock hint when the richest signal (CPU temp) isn't available
    if "cpu_temp" not in avail:
        tk.Label(parent,
                 text="↳ CPU temp: run LibreHardwareMonitor to unlock",
                 font=(_BODY, 6), bg=PANEL, fg=MUTED, anchor="w").pack(anchor="w", pady=(2, 0))


def _lc_voltage(parent):
    tk.Label(parent, text="VOLTAGE  ·  SPC baselines", font=(_MONO, 7, "bold"),
             bg=PANEL, fg=VOLT_C).pack(anchor="w", pady=(0, 3))
    if not (_HAS_VOLT_AZ and _volt_az.is_data_available()):
        tk.Label(parent, text="⚡ Needs LibreHardwareMonitor to learn rails",
                 font=(_BODY, 7), bg=PANEL, fg=MUTED).pack(anchor="w", pady=4)
        return
    stats = _volt_az.get_rail_stats()
    for key, meta in _VOLT_RAILS.items():
        rs  = stats.get(key)
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=meta["label"], font=(_MONO, 7), bg=PANEL, fg=TEXT,
                 width=5, anchor="w").pack(side="left")
        if rs and rs.has_data:
            _, sev = rs.health_label()
            _, scol = _SEVERITY_BADGE.get(sev, _SEVERITY_BADGE["none"])
            band = rs.normal_band
            half = (band[1] - band[0]) / 2 if band else 0
            tk.Label(row, text="●", font=(_MONO, 7), bg=PANEL,
                     fg=scol).pack(side="left", padx=(0, 4))
            tk.Label(row, text=f"{rs.median:.3f}V", font=(_MONO, 7, "bold"),
                     bg=PANEL, fg=VOLT_C).pack(side="left")
            tk.Label(row, text=f"  ±{half:.3f}", font=(_MONO, 7),
                     bg=PANEL, fg=MUTED).pack(side="left")
        else:
            tk.Label(row, text="learning…", font=(_MONO, 7),
                     bg=PANEL, fg=DIM).pack(side="left", padx=(0, 4))
    tk.Label(parent, text=f"{_volt_az.snapshot_count():,} snapshots learned",
             font=(_MONO, 7), bg=PANEL, fg=DIM).pack(anchor="w", pady=(2, 0))


# ──────────────────────────────────────────────────────────────────────────────
# VOLTAGE RAILS SECTION (SPC)
# ──────────────────────────────────────────────────────────────────────────────

_SEVERITY_BADGE = {
    "ok":    ("#0d2818", "#4ade80"),
    "watch": ("#142010", "#22c55e"),
    "warn":  ("#2a1800", "#f59e0b"),
    "crit":  ("#2a0808", "#ef4444"),
    "none":  ("#1a1a1a", "#374151"),
}


def _build_voltage_section(parent):
    """
    Three-column SPC voltage section.
    Shows real-time charts + learned control limits for 12V, 5V, 3.3V rails.
    Requires LHM/OHM; shows informational placeholder otherwise.
    """
    section = _make_section(parent)

    # ── Section header ────────────────────────────────────────────────────────
    hdr = tk.Frame(section, bg="#0a0f1a")
    hdr.pack(fill="x")
    tk.Frame(hdr, bg=VOLT_C, height=2).pack(fill="x")

    hdr_body = tk.Frame(hdr, bg="#0a0f1a")
    hdr_body.pack(fill="x", padx=10, pady=6)
    tk.Label(hdr_body, text="⚡  VOLTAGE RAILS  —  Statistical Process Control",
             font=(_MONO, 9, "bold"),
             bg="#0a0f1a", fg=VOLT_C).pack(side="left")

    if _HAS_VOLT_AZ:
        snap_n = _volt_az.snapshot_count()
        src_lbl = (f"{snap_n:,} snapshots · LHM" if snap_n
                   else "Awaiting LHM data")
        tk.Label(hdr_body,
                 text=src_lbl,
                 font=(_MONO, 7), bg="#0a0f1a", fg=DIM).pack(side="right")
        if snap_n:
            last_str = _volt_az.last_update_str()
            tk.Label(hdr_body,
                     text=f"rebuilt {last_str}",
                     font=(_MONO, 7), bg="#0a0f1a", fg=DIM
                     ).pack(side="right", padx=(0, 10))

    # ── Content ───────────────────────────────────────────────────────────────
    content = tk.Frame(section, bg=PANEL)
    content.pack(fill="x", padx=8, pady=6)
    section._volt_content = content

    # Check data availability
    data_available = (_HAS_VOLT_AZ and _volt_az.is_data_available())

    if not data_available:
        _build_voltage_no_data(content)
    else:
        _build_voltage_rail_columns(section, content)

    # Learn bar at bottom
    learn_bar = tk.Frame(section, bg=PANEL)
    learn_bar.pack(fill="x", padx=8, pady=(0, 6))
    if _HAS_VOLT_AZ:
        tk.Label(learn_bar, text="⚗", font=(_BODY, 8), bg=PANEL).pack(side="left")
        tk.Label(learn_bar,
                 text="Learns your hardware's natural voltage variance — "
                      "flags only statistically unusual deviations",
                 font=(_BODY, 7), bg=PANEL, fg="#94a3b8").pack(side="left", padx=(4, 8))
        section._volt_badge = tk.Label(
            learn_bar,
            text="Initializing…" if not data_available else "Analyzing…",
            font=(_MONO, 7, "bold"),
            bg="#0d1020", fg=VOLT_C, padx=8, pady=1)
        section._volt_badge.pack(side="right")

    return section


def _build_voltage_no_data(parent):
    """Placeholder shown when no LHM voltage data is available."""
    pad = tk.Frame(parent, bg=PANEL)
    pad.pack(fill="x", padx=20, pady=18)

    tk.Label(pad,
             text="⚠  No voltage sensor data available",
             font=(_MONO, 9, "bold"), bg=PANEL, fg=DIM).pack(anchor="w")
    tk.Label(pad,
             text="Voltage monitoring requires LibreHardwareMonitor (LHM) or OpenHardwareMonitor (OHM).\n"
                  "Once running, PC Workman automatically reads 12V / 5V / 3.3V rails and starts\n"
                  "building statistical baselines.  Anomaly detection begins after ~50 snapshots (≈4h).",
             font=(_BODY, 8), bg=PANEL, fg=MUTED,
             justify="left").pack(anchor="w", pady=(6, 0))
    tk.Label(pad,
             text="DeepMonitor stores a snapshot every 5 minutes — baseline learning is fully automatic.",
             font=(_BODY, 7, "italic"), bg=PANEL, fg=DIM
             ).pack(anchor="w", pady=(4, 0))


def _build_voltage_rail_columns(section, parent):
    """Three side-by-side rail sub-panels."""
    if not _HAS_VOLT_AZ:
        return

    stats = _volt_az.get_rail_stats()

    cols_frame = tk.Frame(parent, bg=PANEL)
    cols_frame.pack(fill="x")

    section._volt_canvases = {}
    section._volt_stat_labels = {}

    for i, (rail_key, meta) in enumerate(_VOLT_RAILS.items()):
        rs  = stats.get(rail_key)
        col = meta["color"]

        # Column container
        col_outer = tk.Frame(cols_frame, bg=BORDER)
        col_outer.pack(side="left", fill="both", expand=True,
                       padx=(0 if i == 0 else 4, 0))
        col_frame = tk.Frame(col_outer, bg=PANEL2)
        col_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Rail header
        rail_hdr = tk.Frame(col_frame, bg=PANEL2)
        rail_hdr.pack(fill="x", padx=6, pady=(5, 2))
        tk.Label(rail_hdr,
                 text=f"◈ {meta['label']}",
                 font=(_MONO, 8, "bold"),
                 bg=PANEL2, fg=col).pack(side="left")
        tk.Label(rail_hdr,
                 text=f"nom. {meta['nominal']:.1f}V",
                 font=(_MONO, 7), bg=PANEL2, fg=DIM).pack(side="right")

        # Chart canvas
        cv = tk.Canvas(col_frame, bg="#030508",
                       height=90, highlightthickness=0)
        cv.pack(fill="x", padx=4, pady=(0, 2))
        section._volt_canvases[rail_key] = cv

        # Stats block
        sf = tk.Frame(col_frame, bg=PANEL2)
        sf.pack(fill="x", padx=6, pady=(0, 4))

        lbls = {}
        stat_rows = [
            ("median",  "Median",  "V", col),
            ("mad",     "MAD",     "V", DIM),
            ("ucl",     "UCL",     "V", CRIT_C),
            ("lcl",     "LCL",     "V", CRIT_C),
            ("n_snap",  "Samples", "",  DIM),
        ]
        for key2, label2, unit2, fg2 in stat_rows:
            r = tk.Frame(sf, bg=PANEL2)
            r.pack(fill="x")
            tk.Label(r, text=label2,
                     font=(_MONO, 7), bg=PANEL2, fg=TEXT,
                     anchor="w").pack(side="left")
            v_str = ("--" if rs is None or not rs.has_data
                     else f"{getattr(rs, key2.replace('n_snap','n'), '--'):.4f}"
                     if unit2 == "V"
                     else f"{rs.n:,}" if key2 == "n_snap"
                     else "--")
            lbl = tk.Label(r, text=v_str,
                           font=(_MONO, 7, "bold"),
                           bg=PANEL2, fg=fg2, anchor="e")
            lbl.pack(side="right")
            lbls[key2] = lbl

        # Health badge
        hl_text, hl_sev = rs.health_label() if rs else ("No data", "none")
        bg_b, fg_b = _SEVERITY_BADGE.get(hl_sev, _SEVERITY_BADGE["none"])
        badge = tk.Label(col_frame,
                         text=hl_text,
                         font=(_MONO, 7, "bold"),
                         bg=bg_b, fg=fg_b, padx=8, pady=2)
        badge.pack(fill="x", padx=6, pady=(0, 5))
        lbls["_badge"] = badge
        lbls["_badge_frame"] = col_frame   # for re-styling on update

        section._volt_stat_labels[rail_key] = lbls


def _draw_voltage_chart(canvas, timeline, rail_key, stats, height=90):
    """
    SPC-style voltage chart with tight Y-axis scaling.

    Visual layers (bottom to top):
        1. ATX spec band   (very dark grey background region)
        2. Green band      ±Z_WATCH×K×MAD  (normal operating range)
        3. Amber lines     warn_hi / warn_lo  (dashed)
        4. Red lines       UCL / LCL         (dashed)
        5. Nominal dotted  reference line
        6. Blue/amber line actual voltage values
        7. Anomaly dots    red filled circles on z > 2.5 points
        8. Y-axis labels
    """
    canvas.delete("all")
    w = canvas.winfo_width() or 300

    if not timeline or stats is None or not stats.has_data:
        canvas.create_text(w // 2, height // 2,
                           text="Collecting data…",
                           fill=MUTED, font=(_MONO, 7))
        return

    vals = [float(r.get(rail_key, -1.0) or -1.0) for r in timeline]
    valid = [(i, v) for i, v in enumerate(vals) if v > 0]
    if len(valid) < 2:
        canvas.create_text(w // 2, height // 2,
                           text="Not enough data",
                           fill=MUTED, font=(_MONO, 7))
        return

    h   = height
    PL, PR, PT, PB = 36, 6, 8, 16
    cw  = w - PL - PR
    ch  = h - PT - PB
    n   = len(timeline)

    # ── Y range: nominal ± 10 % (to give visual context around ATX spec) ──────
    nom  = stats.nominal
    ylo  = nom * 0.90
    yhi  = nom * 1.10
    # Expand if data goes outside that window
    data_lo = min(v for _, v in valid)
    data_hi = max(v for _, v in valid)
    ylo  = min(ylo, data_lo - (yhi - ylo) * 0.05)
    yhi  = max(yhi, data_hi + (yhi - ylo) * 0.05)
    yrng = yhi - ylo or 0.001

    def vy(v): return PT + ch * (1.0 - (v - ylo) / yrng)
    def vx(i): return PL + (i / max(n - 1, 1)) * cw

    # ── 1. ATX spec band (very dark) ─────────────────────────────────────────
    y_atx_lo = vy(stats.atx_lo)
    y_atx_hi = vy(stats.atx_hi)
    canvas.create_rectangle(PL, y_atx_hi, w - PR, y_atx_lo,
                             fill="#080f08", outline="")

    # ── 2. Normal band (±Z_WATCH × K × MAD) ──────────────────────────────────
    nlo, nhi = stats.normal_band
    if ylo < nhi < yhi and ylo < nlo < yhi:
        canvas.create_rectangle(PL, vy(nhi), w - PR, vy(nlo),
                                 fill="#0a2010", outline="")

    # ── 3. Warn lines ─────────────────────────────────────────────────────────
    for vv in (stats.warn_hi, stats.warn_lo):
        if ylo <= vv <= yhi:
            y = vy(vv)
            canvas.create_line(PL, y, w - PR, y,
                                fill="#78350f", width=1, dash=(4, 4))

    # ── 4. UCL / LCL ─────────────────────────────────────────────────────────
    for vv in (stats.ucl, stats.lcl):
        if ylo <= vv <= yhi:
            y = vy(vv)
            canvas.create_line(PL, y, w - PR, y,
                                fill="#7f1d1d", width=1, dash=(3, 5))

    # ── 5. Nominal line ───────────────────────────────────────────────────────
    yn = vy(nom)
    canvas.create_line(PL, yn, w - PR, yn,
                        fill="#1e3a1e", width=1, dash=(6, 4))

    # ── Grid lines + Y-axis labels ─────────────────────────────────────────────
    for tick_v in (ylo, (ylo + yhi) / 2, yhi):
        yt = vy(tick_v)
        canvas.create_line(PL, yt, w - PR, yt, fill="#0d1217", width=1)
        canvas.create_text(PL - 3, yt,
                           text=f"{tick_v:.2f}",
                           fill=DIM, font=(_MONO, 7), anchor="e")

    # ── 6. Voltage line ───────────────────────────────────────────────────────
    meta = _VOLT_RAILS.get(rail_key, {})
    line_col = meta.get("color", VOLT_C)
    pts = []
    for i, row in enumerate(timeline):
        v = float(row.get(rail_key, -1.0) or -1.0)
        if v <= 0:
            continue
        clipped = max(ylo, min(yhi, v))
        pts += [vx(i), vy(clipped)]
    if len(pts) >= 4:
        canvas.create_line(pts, fill=line_col, width=1, smooth=False)

    # ── 7. Anomaly dots ───────────────────────────────────────────────────────
    for i, row in enumerate(timeline):
        v = float(row.get(rail_key, -1.0) or -1.0)
        if v <= 0:
            continue
        mz = stats.modified_z(v)
        if abs(mz) > 2.5:
            dot_col = CRIT_C if abs(mz) > 3.5 else WARN_C
            px, py  = vx(i), vy(max(ylo, min(yhi, v)))
            r_dot   = 3 if abs(mz) > 3.5 else 2
            canvas.create_oval(px - r_dot, py - r_dot,
                                px + r_dot, py + r_dot,
                                fill=dot_col, outline="#ffffff", width=1)

    # ── Time axis bookmarks ───────────────────────────────────────────────────
    ts_list = [r.get("ts", 0) for r in timeline if r.get("ts")]
    if len(ts_list) >= 2:
        for frac in (0.0, 0.5, 1.0):
            ts_v = ts_list[0] + (ts_list[-1] - ts_list[0]) * frac
            tx   = PL + frac * cw
            canvas.create_text(tx, h - 4,
                                text=datetime.fromtimestamp(ts_v).strftime("%H:%M"),
                                fill=DIM, font=(_MONO, 7),
                                anchor=("w" if frac == 0 else
                                        "e" if frac == 1.0 else "center"))


def _refresh_voltage(section):
    """Pull latest voltage history, rebuild charts and update stat labels."""
    if not _HAS_VOLT_AZ:
        return

    canvases  = getattr(section, "_volt_canvases",    {})
    stat_lbls = getattr(section, "_volt_stat_labels", {})
    if not canvases:
        return

    # Load last 24h (scale could be added later)
    timeline, events = _volt_az.analyze_history(hours=24)
    stats_all        = _volt_az.get_rail_stats()

    # ── Update each rail column ───────────────────────────────────────────────
    anom_total = 0
    for rail_key, cv in canvases.items():
        rs = stats_all.get(rail_key)
        try:
            if not cv.winfo_exists():
                continue
        except Exception:
            continue

        cv.bind("<Configure>",
                lambda e, t=timeline, rk=rail_key, s=rs:
                    _draw_voltage_chart(e.widget, t, rk, s))
        _draw_voltage_chart(cv, timeline, rail_key, rs)

        # Update stat labels
        lbls = stat_lbls.get(rail_key, {})
        if rs and rs.has_data:
            nlo, nhi = rs.normal_band
            for key2, val2 in [
                ("median",  f"{rs.median:.4f}"),
                ("mad",     f"{rs.mad:.4f}"),
                ("ucl",     f"{rs.ucl:.4f}"),
                ("lcl",     f"{rs.lcl:.4f}"),
                ("n_snap",  f"{rs.n:,}"),
            ]:
                lbl = lbls.get(key2)
                if lbl:
                    try:
                        lbl.config(text=val2)
                    except Exception:
                        pass

        # Update health badge
        hl_text, hl_sev = rs.health_label() if rs else ("No data", "none")
        bg_b, fg_b = _SEVERITY_BADGE.get(hl_sev, _SEVERITY_BADGE["none"])
        badge = lbls.get("_badge")
        if badge:
            try:
                badge.config(text=hl_text, bg=bg_b, fg=fg_b)
            except Exception:
                pass

        if rs:
            anom_total += rs.anomaly_count

    # ── Update section badge ──────────────────────────────────────────────────
    if hasattr(section, "_volt_badge"):
        # Count non-suppressed critical/warning events in timeline
        real_events = [e for e in events if not e.suppressed
                       and e.severity in ("critical", "warning")]
        n_crit = sum(1 for e in real_events if e.severity == "critical")
        if n_crit:
            section._volt_badge.config(
                text=f"⚠ {n_crit} critical anomaly" + ("s" if n_crit > 1 else ""),
                bg="#2a0808", fg=CRIT_C)
        elif real_events:
            section._volt_badge.config(
                text=f"{len(real_events)} warnings (24h)",
                bg="#2a1800", fg=WARN_C)
        elif _volt_az.is_data_available():
            section._volt_badge.config(
                text="All rails within normal bounds",
                bg="#0d2818", fg="#4ade80")
        else:
            section._volt_badge.config(
                text="Awaiting LHM data",
                bg="#0d1020", fg=VOLT_C)


# ──────────────────────────────────────────────────────────────────────────────
# 5. 30-DAY ANOMALY CALENDAR HEATMAP
# ──────────────────────────────────────────────────────────────────────────────

def _build_anomaly_calendar(parent):
    section = tk.Frame(parent, bg=PANEL)
    section.pack(fill="x", padx=15, pady=(0, 8))
    tk.Frame(section, bg=CAL_C, height=2).pack(fill="x")

    hdr = tk.Frame(section, bg="#0a081a")
    hdr.pack(fill="x")
    hdr_body = tk.Frame(hdr, bg="#0a081a")
    hdr_body.pack(fill="x", padx=10, pady=5)
    tk.Label(hdr_body, text="◈  ANOMALY CALENDAR  -  30 days",
             font=(_MONO, 8, "bold"),
             bg="#0a081a", fg="#a78bfa").pack(side="left")
    tk.Label(hdr_body, text="Lighter = more anomalies that day",
             font=(_BODY, 7), bg="#0a081a", fg=DIM).pack(side="right")

    body = tk.Frame(section, bg=PANEL)
    body.pack(fill="x", padx=12, pady=8)

    # Load data
    anomaly_by_day: dict[int, int] = {}
    try:
        now = time.time()
        from hck_stats_engine.query_api import query_api
        for i in range(30):
            start_ts = now - (29 - i) * 86400
            end_ts   = start_ts + 86400
            data = query_api.get_usage_for_range(start_ts, end_ts, max_points=120)
            if data:
                vals   = [d.get("cpu_avg", 0) or 0 for d in data]
                mean_v = sum(vals) / len(vals) if vals else 50
                var_v  = sum((v - mean_v) ** 2 for v in vals) / max(1, len(vals))
                std_v  = math.sqrt(var_v) if var_v > 0 else 1
                anomaly_by_day[i] = sum(1 for v in vals if v > mean_v + 2 * std_v)
    except Exception:
        pass

    # Draw cells
    cells_row = tk.Frame(body, bg=PANEL)
    cells_row.pack(fill="x")

    for i in range(30):
        day_date  = datetime.now() - timedelta(days=29 - i)
        anomalies = anomaly_by_day.get(i, 0)

        # Color tiers
        if anomalies == 0:
            bg_c, bd_c, fg_c = "#0d1117", "#1e293b", DIM
        elif anomalies <= 3:
            bg_c, bd_c, fg_c = "#112318", "#4ade80", "#4ade80"
        elif anomalies <= 8:
            bg_c, bd_c, fg_c = "#1e1400", "#f59e0b", "#f59e0b"
        else:
            bg_c, bd_c, fg_c = "#1e0808", "#ef4444", "#ef4444"

        cell_out = tk.Frame(cells_row, bg=bd_c)
        cell_out.pack(side="left", padx=2)
        cell_in  = tk.Frame(cell_out, bg=bg_c, width=24, height=26)
        cell_in.pack(padx=1, pady=1)
        cell_in.pack_propagate(False)

        day_n = str(day_date.day)
        lbl   = tk.Label(cell_in, text=day_n,
                         font=(_MONO, 7), bg=bg_c, fg=fg_c, cursor="hand2")
        lbl.pack(expand=True)

        def _enter(e, f=cell_in, b="#1e293b", lbl=lbl, old=bg_c, fg=fg_c):
            f.config(bg=b)
            lbl.config(bg=b)

        def _leave(e, f=cell_in, b=bg_c, lbl=lbl, fg=fg_c):
            f.config(bg=b)
            lbl.config(bg=b)

        lbl.bind("<Enter>", _enter)
        lbl.bind("<Leave>", _leave)

    # Legend
    legend = tk.Frame(body, bg=PANEL)
    legend.pack(fill="x", pady=(6, 0))
    tk.Label(legend, text="Clean", font=(_MONO, 7), bg=PANEL, fg=DIM).pack(side="left", padx=(0, 6))
    for col, txt in [("#4ade80", "Mild"), ("#f59e0b", "Moderate"), ("#ef4444", "Heavy")]:
        dot = tk.Frame(legend, bg=col, width=8, height=8)
        dot.pack(side="left", padx=(0, 2))
        tk.Label(legend, text=txt, font=(_MONO, 7),
                 bg=PANEL, fg=col).pack(side="left", padx=(0, 8))


# ──────────────────────────────────────────────────────────────────────────────
# 6. EVENTS / ALERTS LOG
# ──────────────────────────────────────────────────────────────────────────────

def _build_alerts_log(parent):
    section = tk.Frame(parent, bg=PANEL)
    section.pack(fill="x", padx=15, pady=(0, 16))
    tk.Frame(section, bg=ALERT_C, height=2).pack(fill="x")

    hdr = tk.Frame(section, bg="#12080a")
    hdr.pack(fill="x")
    hdr_b = tk.Frame(hdr, bg="#12080a")
    hdr_b.pack(fill="x", padx=10, pady=5)
    tk.Label(hdr_b, text="🔔  RECENT EVENTS",
             font=(_MONO, 9, "bold"),
             bg="#12080a", fg=ALERT_C).pack(side="left")
    tk.Label(hdr_b, text="last 10 entries",
             font=(_BODY, 7), bg="#12080a", fg=DIM).pack(side="right")

    container = tk.Frame(section, bg=PANEL)
    container.pack(fill="x", padx=8, pady=6)

    events = []
    try:
        from hck_stats_engine.query_api import query_api
        events = query_api.get_events(limit=10)
    except Exception:
        pass

    if events:
        for evt in events:
            _render_event_row(container, evt)
    else:
        tk.Label(container,
                 text="No events recorded yet - PC Workman is monitoring your system…",
                 font=(_MONO, 7), bg=PANEL2, fg=MUTED,
                 padx=12, pady=10).pack(fill="x")


_EVT_METRIC_LBL = {"cpu": "CPU", "ram": "RAM", "gpu": "GPU",
                   "cpu_temp": "CPU temp", "gpu_temp": "GPU temp",
                   "disk": "Disk", "network": "Network"}


def _event_message(evt: dict) -> str:
    """Human-readable line for an event row.

    The DB column is `description` - the old code read a non-existent
    `message` key, so every event rendered as "Unknown event" while the
    full type/metric/value/baseline sat unused in the dict.
    """
    etype  = (evt.get("event_type") or "").strip().lower()
    metric = (evt.get("metric") or "").strip().lower()
    val    = evt.get("value")
    base   = evt.get("baseline")
    m_lbl  = _EVT_METRIC_LBL.get(metric, metric.upper())
    unit   = "°C" if "temp" in metric else "%"

    # Spikes: compose a clean line from the structured columns
    if etype == "spike" and metric and val is not None:
        txt = f"{m_lbl} spike: {val:.0f}{unit}"
        if base is not None:
            txt += f"  (usual {base:.0f}{unit}, +{val - base:.0f})"
        return txt

    desc = (evt.get("description") or "").strip()
    if desc:
        return desc
    if etype:
        nice = etype.replace("_", " ").capitalize()
        return f"{nice} · {m_lbl}" if metric else nice
    return "System event"


def _render_event_row(parent, evt: dict):
    sev        = evt.get("severity", "info")
    sev_colors = {"info": LOAD_C, "warning": WARN_C, "critical": CRIT_C}
    sev_col    = sev_colors.get(sev, MUTED)
    ts         = evt.get("timestamp", 0)
    time_str   = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "--:--"
    day_str    = datetime.fromtimestamp(ts).strftime("%a") if ts else "---"
    message    = _event_message(evt)[:64]

    row = tk.Frame(parent, bg=PANEL2)
    row.pack(fill="x", pady=1)

    # Severity stripe
    tk.Frame(row, bg=sev_col, width=3).pack(side="left", fill="y")

    # Time
    time_f = tk.Frame(row, bg=PANEL2)
    time_f.pack(side="left", padx=(6, 0))
    tk.Label(time_f, text=time_str, font=(_MONO, 8, "bold"),
             bg=PANEL2, fg=TEXT).pack(anchor="w")
    tk.Label(time_f, text=day_str, font=(_MONO, 7),
             bg=PANEL2, fg=MUTED).pack(anchor="w")

    # Badge
    badge_bg = "#0c1e30" if sev == "info" else "#2a1800" if sev == "warning" else "#2a0808"
    tk.Label(row, text=sev.upper()[:4],
             font=(_MONO, 7, "bold"),
             bg=badge_bg, fg=sev_col, padx=6, pady=2).pack(side="left", padx=6)

    # Message
    tk.Label(row, text=message, font=(_BODY, 8),
             bg=PANEL2, fg="#94a3b8", anchor="w").pack(
        side="left", fill="x", expand=True, padx=(0, 8), pady=5)


# ──────────────────────────────────────────────────────────────────────────────
# CHART DRAWING - Adaptive baseline + anomaly decay
# ──────────────────────────────────────────────────────────────────────────────

def _draw_adaptive_chart(canvas, data, key, color, height=150,
                          ext_mean=None, ext_lo=None, ext_hi=None):
    """
    Area chart with:
      • Shaded baseline band (mean ±σ) - learned normal zone
      • Anomaly fade: frequently-seen spikes get a more muted highlight
      • Contextual hover tooltip: "58.3°C (12 % above usual)"
    """
    canvas.delete("all")
    w = canvas.winfo_width() or 500

    if not data:
        canvas.create_text(w // 2, height // 2, text="Collecting data…",
                           fill=MUTED, font=(_MONO, 8))
        return

    h   = height
    PL, PR, PT, PB = 32, 8, 12, 20
    cw  = w - PL - PR
    ch  = h - PT - PB

    values = [float(d.get(key, 0) or 0) for d in data]
    n      = len(values)
    if n < 2:
        return

    # Use externally supplied baseline (from ThermalBaseline) when available,
    # otherwise fall back to the simple window mean±σ.
    if ext_mean is not None and ext_lo is not None and ext_hi is not None:
        mean    = ext_mean
        sigma_w = (ext_hi - ext_lo) / 3.0 if (ext_hi - ext_lo) > 0 else 5.0
        base_lo = ext_lo
        base_hi = ext_hi
        thresh  = ext_hi
    else:
        mean, sigma_w = _compute_adaptive(values)
        base_lo = max(0, mean - sigma_w)
        base_hi = mean + sigma_w * 1.5
        thresh  = base_hi

    vmin  = max(0, min(values) * 0.95)
    vmax  = max(values) * 1.08 if max(values) > 0 else 100
    if base_hi > vmax:
        vmax = base_hi * 1.05
    vrange = vmax - vmin or 1

    def vy(v):
        return PT + ch * (1 - (v - vmin) / vrange)

    def vx(i):
        return PL + (i / max(n - 1, 1)) * cw

    # Grid
    for step in [0, 25, 50, 75, 100]:
        v = vmin + vrange * step / 100
        y = vy(v)
        canvas.create_line(PL, y, w - PR, y, fill="#111820", width=1)
        canvas.create_text(PL - 3, y, text=f"{v:.0f}",
                           fill=DIM, font=(_MONO, 7), anchor="e")

    # ── Adaptive baseline band ────────────────────────────────────────────────
    band_pts = ([PL, vy(base_lo)] +
                [coord for i in range(n) for coord in (vx(i), vy(base_lo))] +
                [vx(n - 1), vy(base_hi)] +
                [coord for i in range(n - 1, -1, -1) for coord in (vx(i), vy(base_hi))])
    canvas.create_polygon(band_pts, fill="#0a1f10", outline="", smooth=False)

    # Mean dashed line
    canvas.create_line(PL, vy(mean), w - PR, vy(mean),
                       fill="#163220", width=1, dash=(5, 4))

    # ── Anomaly zones with fade (decay learning) ─────────────────────────────
    spike_count = sum(1 for v in values if v > thresh)
    spike_ratio = spike_count / max(n, 1)
    # 0 = new spike (bright), 1 = fully learned (very faded)
    decay = min(0.95, spike_ratio * 8)

    if decay < 0.25:
        fill_anom, line_anom = "#2a1800", "#f59e0b"
    elif decay < 0.6:
        fill_anom, line_anom = "#1a1100", "#78350f"
    else:
        fill_anom, line_anom = "#110d00", "#451a03"

    in_spike = False
    sp_start = 0
    for i, v in enumerate(values):
        if v > thresh and not in_spike:
            in_spike, sp_start = True, i
        elif (v <= thresh or i == n - 1) and in_spike:
            in_spike = False
            sx, ex = vx(sp_start), vx(i)
            canvas.create_rectangle(sx, PT, ex, PT + ch,
                                    fill=fill_anom, outline="")
            canvas.create_line(sx, PT, sx, PT + ch, fill=line_anom, width=1)

    # ── Filled area ────────────────────────────────────────────────────────────
    area = [PL, PT + ch]
    for i, v in enumerate(values):
        area += [vx(i), vy(v)]
    area += [vx(n - 1), PT + ch]
    canvas.create_polygon(area, fill=_darker(color), outline="", smooth=True)

    # ── Main line ──────────────────────────────────────────────────────────────
    line_pts = [coord for i, v in enumerate(values) for coord in (vx(i), vy(v))]
    canvas.create_line(line_pts, fill=color, width=2, smooth=True)

    # ── Time axis ─────────────────────────────────────────────────────────────
    _draw_time_axis(canvas, data, PL, w - PR, h)

    # ── Contextual hover tooltip ───────────────────────────────────────────────
    points = [(vx(i), vy(v)) for i, v in enumerate(values)]

    def _hover(event):
        if event.x < PL or event.x > PL + cw:
            return
        idx  = int(((event.x - PL) / cw) * (n - 1))
        idx  = max(0, min(idx, n - 1))
        val  = values[idx]
        diff = val - mean
        pct  = abs(diff / mean * 100) if mean else 0
        dir_ = "above" if diff >= 0 else "below"
        ts   = data[idx].get("timestamp", 0)
        t_s  = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--"
        tip  = f"{t_s}  {val:.1f}  ({pct:.0f}% {dir_} usual)"

        canvas.delete("hover_dot")
        px, py = points[idx]
        canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                           fill=color, outline="#ffffff", width=1, tags="hover_dot")

        tip_x = min(event.x + 10, w - len(tip) * 5 - 8)
        tip_y = max(event.y - 22, 4)
        canvas.delete("hover_tip")
        canvas.create_rectangle(tip_x - 2, tip_y - 2,
                                 tip_x + len(tip) * 5 + 8, tip_y + 14,
                                 fill="#1e293b", outline="#334155", tags="hover_tip")
        canvas.create_text(tip_x + 4, tip_y + 6, text=tip,
                           fill="#ffffff", font=(_MONO, 7),
                           anchor="w", tags="hover_tip")

    def _leave(event):
        canvas.delete("hover_dot")
        canvas.delete("hover_tip")

    canvas.bind("<Motion>", _hover)
    canvas.bind("<Leave>",  _leave)


def _draw_multi_load_chart(canvas, data, height=150):
    """Multi-line load chart with per-metric adaptive baselines."""
    canvas.delete("all")
    w = canvas.winfo_width() or 500

    if not data:
        canvas.create_text(w // 2, height // 2, text="Collecting data…",
                           fill=MUTED, font=(_MONO, 8))
        return

    h   = height
    PL, PR, PT, PB = 32, 8, 12, 20
    cw  = w - PL - PR
    ch  = h - PT - PB
    n   = len(data)
    if n < 2:
        return

    def vx(i):   return PL + (i / max(n - 1, 1)) * cw
    def vy(v):   return PT + ch * (1 - max(0, min(100, v)) / 100)

    # Grid
    for step in [0, 25, 50, 75, 100]:
        y = vy(step)
        canvas.create_line(PL, y, w - PR, y, fill="#111820", width=1)
        canvas.create_text(PL - 3, y, text=str(step),
                           fill=DIM, font=(_MONO, 7), anchor="e")

    keys_cols = [("cpu_avg", LOAD_C), ("ram_avg", RAM_C), ("gpu_avg", GPU_C)]
    all_pts: dict[str, list] = {}

    for key, col in keys_cols:
        vals   = [float(d.get(key, 0) or 0) for d in data]
        mean_v, sigma_v = _compute_adaptive(vals)
        thresh_v = mean_v + sigma_v * 1.5

        # Anomaly zone (faded)
        in_sp, sp_start = False, 0
        for i, v in enumerate(vals):
            if v > thresh_v and not in_sp:
                in_sp, sp_start = True, i
            elif (v <= thresh_v or i == n - 1) and in_sp:
                in_sp = False
                canvas.create_rectangle(vx(sp_start), PT, vx(i), PT + ch,
                                        fill="#0e1220", outline="")

        pts = [(vx(i), vy(v)) for i, v in enumerate(vals)]
        all_pts[key] = pts
        flat = [coord for p in pts for coord in p]
        canvas.create_line(flat, fill=col, width=2, smooth=True)

    _draw_time_axis(canvas, data, PL, w - PR, h)

    # Hover tooltip showing all three values
    def _hover(event):
        if event.x < PL or event.x > PL + cw:
            return
        idx = int(((event.x - PL) / cw) * (n - 1))
        idx = max(0, min(idx, n - 1))
        d   = data[idx]
        ts  = d.get("timestamp", 0)
        t_s = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--"
        cpu = d.get("cpu_avg", 0) or 0
        ram = d.get("ram_avg", 0) or 0
        gpu = d.get("gpu_avg", 0) or 0
        tip = f"{t_s}  CPU:{cpu:.0f}%  RAM:{ram:.0f}%  GPU:{gpu:.0f}%"

        canvas.delete("hover_dot")
        for key, col in keys_cols:
            pts = all_pts.get(key, [])
            if idx < len(pts):
                px, py = pts[idx]
                canvas.create_oval(px - 2, py - 2, px + 2, py + 2,
                                   fill=col, outline="#ffffff", width=1, tags="hover_dot")

        tip_x = min(event.x + 10, w - len(tip) * 5 - 8)
        tip_y = max(event.y - 22, 4)
        canvas.delete("hover_tip")
        canvas.create_rectangle(tip_x - 2, tip_y - 2,
                                 tip_x + len(tip) * 5 + 8, tip_y + 14,
                                 fill="#1e293b", outline="#334155", tags="hover_tip")
        canvas.create_text(tip_x + 4, tip_y + 6, text=tip,
                           fill="#ffffff", font=(_MONO, 7),
                           anchor="w", tags="hover_tip")

    def _leave(event):
        canvas.delete("hover_dot")
        canvas.delete("hover_tip")

    canvas.bind("<Motion>", _hover)
    canvas.bind("<Leave>",  _leave)


def _draw_alert_timeline(canvas, data, key):
    """
    Thin strip below a chart showing alert events as vertical lines.
    Red = severe, amber = moderate.  Dots on the baseline at non-anomalous times.
    """
    canvas.delete("all")
    w = canvas.winfo_width() or 500
    h = 22

    if not data:
        return

    canvas.create_line(0, h // 2, w, h // 2, fill="#1a2030", width=1)

    values = [float(d.get(key, 0) or 0) for d in data]
    n      = len(values)
    if n < 2:
        return

    mean, sigma = _compute_adaptive(values)
    thresh  = mean + sigma * 1.5
    thresh2 = mean + sigma * 2.5

    first_ts = data[0].get("timestamp", 0)
    last_ts  = data[-1].get("timestamp", 0)
    if not (first_ts and last_ts and last_ts > first_ts):
        return

    for i, (d, v) in enumerate(zip(data, values)):
        ts   = d.get("timestamp", 0)
        if not ts:
            continue
        frac = (ts - first_ts) / (last_ts - first_ts)
        x    = int(frac * w)
        if v > thresh2:
            canvas.create_line(x, 2, x, h - 2, fill=CRIT_C, width=2)
        elif v > thresh:
            canvas.create_line(x, 4, x, h - 4, fill=WARN_C, width=1)

    # Time bookmarks
    for frac, ts_val in [(0, first_ts), (0.5, (first_ts + last_ts) / 2), (1, last_ts)]:
        x    = int(frac * w)
        t_s  = datetime.fromtimestamp(ts_val).strftime("%H:%M")
        anch = "w" if frac == 0 else ("e" if frac == 1 else "center")
        canvas.create_text(x, h - 4, text=t_s,
                           font=(_MONO, 7), fill="#1e293b", anchor=anch)


# ──────────────────────────────────────────────────────────────────────────────
# SCALE BUTTONS
# ──────────────────────────────────────────────────────────────────────────────

def _build_scale_buttons(parent, color, callback):
    frame = tk.Frame(parent, bg=parent["bg"])
    frame.pack(side="right", padx=8)

    var    = [("1D",)]
    btns   = {}

    for scale in ("1D", "3D", "1W", "1M"):
        active = (scale == "1D")
        btn = tk.Label(frame, text=scale,
                       font=(_MONO, 7, "bold"),
                       bg=color if active else "#0d1018",
                       fg="#000000" if active else MUTED,
                       padx=7, pady=2, cursor="hand2")
        btn.pack(side="left", padx=1)
        btns[scale] = btn

        def _click(e, s=scale):
            for k, b in btns.items():
                b.config(bg=color if k == s else "#0d1018",
                         fg="#000000" if k == s else MUTED)
            var[0] = (s,)
            callback(s)

        btn.bind("<Button-1>", _click)

    return frame, var


# ──────────────────────────────────────────────────────────────────────────────
# DATA & REFRESH
# ──────────────────────────────────────────────────────────────────────────────

def _load_data(scale: str) -> list:
    now  = time.time()
    span = {"1D": 86400, "3D": 259200, "1W": 604800, "1M": 2592000}.get(scale, 86400)
    try:
        from hck_stats_engine.query_api import query_api
        data = query_api.get_usage_for_range(now - span, now, max_points=350)
        return data or []
    except Exception:
        return []


def _compute_adaptive(values: list) -> tuple[float, float]:
    """Return (mean, sigma) for a list of numeric values."""
    if not values:
        return 50.0, 10.0
    mean = sum(values) / len(values)
    var  = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, math.sqrt(var) if var > 0 else 1.0


def _classify_workload(data: list) -> tuple[str, str]:
    if not data:
        return "Idle 🌙", DIM
    recent = data[-min(8, len(data)):]
    gpu    = sum(d.get("gpu_avg", 0) or 0 for d in recent) / len(recent)
    cpu    = sum(d.get("cpu_avg", 0) or 0 for d in recent) / len(recent)
    if gpu > 55:
        return "Gaming 🎮", GPU_C
    elif cpu > 50:
        return "Dev / Work 💻", LOAD_C
    elif cpu < 12:
        return "Idle 🌙", DIM
    return "Mixed 🔄", RAM_C


def _compute_health_scores(data: list) -> tuple[int, int, int]:
    """Return (thermal_score, memory_score, load_score) each 0–100."""
    if not data:
        return 85, 80, 80

    temps = [float(d.get("display_temp", d.get("cpu_temp", 0) or 0)) for d in data if d.get("cpu_temp")]
    cpus  = [float(d.get("cpu_avg", 0) or 0) for d in data]
    rams  = [float(d.get("ram_avg", 0) or 0) for d in data]

    # Thermal score
    th = 100
    if temps:
        mx = max(temps)
        av = sum(temps) / len(temps)
        if mx > 90: th -= 40
        elif mx > 82: th -= 25
        elif mx > 70: th -= 10
        if av > 65: th -= 10
    th = max(0, th)

    # Memory score
    mem = 100
    if rams:
        mx = max(rams)
        av = sum(rams) / len(rams)
        if mx > 92: mem -= 35
        elif mx > 80: mem -= 20
        elif mx > 65: mem -= 8
        if av > 55: mem -= 8
    mem = max(0, mem)

    # Load score
    ld = 100
    if cpus:
        mx = max(cpus)
        av = sum(cpus) / len(cpus)
        if mx > 95: ld -= 30
        elif mx > 80: ld -= 15
        elif mx > 65: ld -= 5
        _, sigma = _compute_adaptive(cpus)
        anom = sum(1 for v in cpus if v > av + sigma * 2)
        ld -= min(30, anom * 3)
    ld = max(0, ld)

    return th, mem, ld


def _refresh_temp(section):
    scale = (section._temp_scale[0][0] if isinstance(section._temp_scale[0], tuple)
             else section._temp_scale[0])
    data  = _load_data(scale)

    # Enrich with display_temp
    for d in data:
        if not d.get("cpu_temp"):
            d["display_temp"] = 35 + (d.get("cpu_avg", 0) or 0) * 0.5
        else:
            d["display_temp"] = float(d["cpu_temp"])

    section._chart_data = data

    # ── Thermal baseline: workload-context chart band ─────────────────────────
    ext_mean = ext_lo = ext_hi = None
    section._current_workload = "unknown"
    if _HAS_THERMAL_BL and data:
        # Classify workload from the most recent data points
        recent  = data[-min(8, len(data)):]
        avg_cpu = sum(d.get("cpu_avg", 0) or 0 for d in recent) / len(recent)
        avg_gpu = sum(d.get("gpu_avg", 0) or 0 for d in recent) / len(recent)
        bucket  = _thermal_bl.classify(avg_cpu, avg_gpu)
        bl_rng  = _thermal_bl.get_range(bucket)
        section._current_workload = bucket

        if bl_rng.is_usable:
            ext_mean = bl_rng.mean
            ext_lo   = bl_rng.p5
            ext_hi   = bl_rng.p95
            # Store range on section for stats display
            section._baseline_range  = bl_rng
        else:
            section._baseline_range = None
    else:
        section._baseline_range = None

    if _HAS_ICHART and getattr(section, "_ichart_temp", None):
        ic = section._ichart_temp
        vals = [d.get("display_temp") for d in data]
        ts   = [d.get("timestamp", 0) for d in data]

        # Compute anomaly markers for the chart
        mean_v, sig_v = _compute_adaptive(vals)
        anom_threshold = ext_hi if ext_hi else mean_v + sig_v * 1.5
        anom_markers = [
            {"idx": i, "severity": "critical" if v > anom_threshold + sig_v else "warning",
             "reason": (getattr(section, "_baseline_range", None).context_label(v)
                        if getattr(section, "_baseline_range", None) else ""),
             "type": "isolated_spike"}
            for i, v in enumerate(vals) if v and v > anom_threshold
        ]

        ic.set_series([{"values": vals, "color": TEMP_C, "label": "Temp °C"}])
        ic.set_timestamps(ts)
        if ext_mean is not None:
            ic.set_baseline(mean=ext_mean, lo=ext_lo, hi=ext_hi)
        else:
            ic.clear_baseline()
        ic.set_anomalies(anom_markers)
        ic.draw()
    else:
        _draw_adaptive_chart(section._chart_canvas, data, "display_temp", TEMP_C,
                             ext_mean=ext_mean, ext_lo=ext_lo, ext_hi=ext_hi)
        if hasattr(section, "_timeline_cv") and section._timeline_cv:
            section._timeline_cv.bind(
                "<Configure>",
                lambda e, d=data: _draw_alert_timeline(
                    section._timeline_cv, d, "display_temp"))
            _draw_alert_timeline(section._timeline_cv, data, "display_temp")

    _update_temp_stats(section, data)


def _refresh_load(section):
    scale = (section._load_scale[0][0] if isinstance(section._load_scale[0], tuple)
             else section._load_scale[0])
    data  = _load_data(scale)
    section._chart_data = data

    if _HAS_ICHART and getattr(section, "_ichart_load", None):
        ic  = section._ichart_load
        cpu = [d.get("cpu_avg") for d in data]
        ram = [d.get("ram_avg") for d in data]
        gpu = [d.get("gpu_avg") for d in data]
        ts  = [d.get("timestamp", 0) for d in data]

        # Anomaly markers on CPU series
        mean_c, sig_c = _compute_adaptive([v for v in cpu if v is not None])
        cpu_anom = [
            {"idx": i, "severity": "warning",
             "reason": f"CPU spike: {v:.0f}%", "type": "isolated_spike"}
            for i, v in enumerate(cpu) if v and v > mean_c + sig_c * 2
        ]
        ic.set_series([
            {"values": cpu, "color": LOAD_C, "label": "CPU%"},
            {"values": ram, "color": RAM_C,  "label": "RAM%"},
            {"values": gpu, "color": GPU_C,  "label": "GPU%"},
        ])
        ic.set_timestamps(ts)
        ic.clear_baseline()
        ic.set_anomalies(cpu_anom)
        ic.draw()
    else:
        _draw_multi_load_chart(section._chart_canvas, data)
        if hasattr(section, "_timeline_cv") and section._timeline_cv:
            _draw_alert_timeline(section._timeline_cv, data, "cpu_avg")

    _update_load_stats(section, data)


def _update_temp_stats(section, data):
    sf = section._stats_frame
    if not data:
        return

    temps = [d.get("display_temp", 0) for d in data if d.get("display_temp")]
    if not temps:
        return

    avg = sum(temps) / len(temps)
    mx  = max(temps)
    cur = temps[-1]
    mean, sigma = _compute_adaptive(temps)
    spikes = sum(1 for t in temps if t > mean + 1.5 * sigma)

    # Trend (last 10 vs first 10)
    trend = "->"
    if len(temps) >= 20:
        e1 = sum(temps[:10]) / 10
        e2 = sum(temps[-10:]) / 10
        trend = "↑" if e2 > e1 + 1 else ("↓" if e2 < e1 - 1 else "->")

    # ── Thermal baseline context-aware coloring ───────────────────────────────
    bl_rng = getattr(section, "_baseline_range", None)
    if bl_rng is not None:
        cl = bl_rng.classify_temp(cur)
        cur_col = (CRIT_C  if cl == "critical" else
                   CRIT_C  if cl == "high"     else
                   WARN_C  if cl == "elevated" else LOAD_C)
    else:
        cur_col = CRIT_C if cur > 80 else WARN_C if cur > 65 else LOAD_C

    # Lifetime avg label shows learned baseline when available
    lf_avg_val = (f"{bl_rng.mean:.1f}°C ±{bl_rng.sigma:.1f}"
                  if bl_rng and bl_rng.is_usable else "--")

    for attr, val, kw in [
        ("temp_today_avg",    f"{avg:.1f}°C",  {}),
        ("temp_lifetime_avg", lf_avg_val,       {"fg": MUTED}),
        ("temp_current",      f"{cur:.1f}°C",  {"fg": cur_col}),
        ("temp_today_max",    f"{mx:.1f}°C",   {}),
        ("temp_spikes",       str(spikes),      {}),
        ("temp_trend",        trend,            {}),
    ]:
        lbl = getattr(sf, attr, None)
        if lbl:
            lbl.config(text=val, **kw)

    # Workload badge — shows workload context
    wl, wl_col = _classify_workload(data)
    bucket_name = getattr(section, "_current_workload", "unknown").title()
    if hasattr(section, "_workload_lbl"):
        section._workload_lbl.config(
            text=f"Workload: {wl}  ·  Context: {bucket_name}", fg=wl_col)

    # Status badge — uses baseline context when trained, else fixed thresholds
    if hasattr(section, "_temp_badge"):
        if bl_rng and bl_rng.is_usable:
            cl = bl_rng.classify_temp(cur)
            if cl == "critical":
                section._temp_badge.config(
                    text=f"Critical — {bl_rng.context_label(cur)}",
                    bg="#2a0a0a", fg=CRIT_C)
            elif cl == "high":
                section._temp_badge.config(
                    text=f"High for {bucket_name}",
                    bg="#2a1800", fg=WARN_C)
            elif cl == "elevated":
                section._temp_badge.config(
                    text=f"Slightly elevated for {bucket_name}",
                    bg="#1a1400", fg=WARN_C)
            else:
                section._temp_badge.config(
                    text=f"Normal ({bucket_name}: {bl_rng.p5:.0f}–{bl_rng.p95:.0f}°C)",
                    bg="#0d2818", fg="#4ade80")
        else:
            if spikes > 5 or mx > 85:
                col = CRIT_C if mx > 85 else WARN_C
                bgc = "#2a0a0a" if mx > 85 else "#2a1800"
                msg = "High temps detected" if mx > 85 else "Frequent spikes"
                section._temp_badge.config(text=msg, bg=bgc, fg=col)
            else:
                section._temp_badge.config(text="No regular problems",
                                            bg="#0d2818", fg="#4ade80")


def _update_load_stats(section, data):
    sf = section._stats_frame
    if not data:
        return

    cpus = [float(d.get("cpu_avg", 0) or 0) for d in data]
    rams = [float(d.get("ram_avg", 0) or 0) for d in data]
    gpus = [float(d.get("gpu_avg", 0) or 0) for d in data]
    if not cpus:
        return

    cpu_avg  = sum(cpus) / len(cpus)
    ram_avg  = sum(rams) / len(rams)
    gpu_avg  = sum(gpus) / len(gpus)
    cpu_peak = max(cpus)
    ram_peak = max(rams)

    mean_c, sigma_c = _compute_adaptive(cpus)
    anomalies = sum(1 for v in cpus if v > mean_c + sigma_c * 2)

    if data:
        ft = data[0].get("timestamp", 0)
        lt = data[-1].get("timestamp", 0)
        up = (lt - ft) / 3600 if lt > ft else 0
        uptime = f"{up / 24:.1f}d" if up >= 24 else f"{up:.1f}h"
    else:
        uptime = "--"

    cpu_peak_col = CRIT_C if cpu_peak > 90 else WARN_C if cpu_peak > 70 else LOAD_C

    for attr, val, kw in [
        ("load_cpu_avg",   f"{cpu_avg:.1f}%",  {}),
        ("load_ram_avg",   f"{ram_avg:.1f}%",  {}),
        ("load_gpu_avg",   f"{gpu_avg:.1f}%",  {}),
        ("load_cpu_peak",  f"{cpu_peak:.1f}%", {"fg": cpu_peak_col}),
        ("load_ram_peak",  f"{ram_peak:.1f}%", {}),
        ("load_anomalies", str(anomalies),      {}),
        ("load_uptime",    uptime,              {}),
    ]:
        lbl = getattr(sf, attr, None)
        if lbl:
            lbl.config(text=val, **kw)

    if hasattr(section, "_load_badge"):
        if anomalies > 5:
            section._load_badge.config(text=f"{anomalies} load anomalies",
                                        bg="#2a1800", fg=WARN_C)
        else:
            section._load_badge.config(text="No load anomalies",
                                        bg="#0d2818", fg="#4ade80")


# ──────────────────────────────────────────────────────────────────────────────
# AUTO-REFRESH
# ──────────────────────────────────────────────────────────────────────────────

def _start_refresh(parent, rings_cv, score_ref, health_lbl, anom_lbl,
                   temp_sec, load_sec, volt_sec=None):
    def _do():
        try:
            if not parent.winfo_exists():
                return
        except Exception:
            return

        try:
            _refresh_temp(temp_sec)
        except Exception:
            pass
        try:
            _refresh_load(load_sec)
        except Exception:
            pass
        try:
            if volt_sec is not None:
                _refresh_voltage(volt_sec)
        except Exception:
            pass
        # Trigger async baseline rebuilds every refresh cycle (they self-throttle)
        if _HAS_THERMAL_BL:
            _thermal_bl.maybe_rebuild(300.0)
        if _HAS_VOLT_AZ:
            _volt_az.maybe_rebuild(300.0)

        # Update header health + anomaly badges + rings
        try:
            if temp_sec._chart_data:
                td   = temp_sec._chart_data
                cpus = [float(d.get("cpu_avg", 0) or 0) for d in td]

                mean_c, sigma_c = _compute_adaptive(cpus)
                anom_count = sum(1 for v in cpus if v > mean_c + sigma_c * 2)

                th, mem, ld = _compute_health_scores(td)
                avg_score   = (th + mem + ld) // 3
                score_ref[0] = avg_score

                _draw_health_rings(rings_cv, rings_cv.winfo_width() or 80, th, mem, ld)

                s_col = OK_C if avg_score >= 80 else WARN_C if avg_score >= 55 else CRIT_C
                a_col = OK_C if anom_count == 0 else WARN_C if anom_count < 5 else CRIT_C

                if health_lbl.winfo_exists():
                    health_lbl.config(text=str(avg_score), fg=s_col)
                if anom_lbl.winfo_exists():
                    anom_lbl.config(text=str(anom_count), fg=a_col)
        except Exception:
            pass

        try:
            if parent.winfo_exists():
                parent.after(30_000, _do)
        except Exception:
            pass

    parent.after(600, _do)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _make_section(parent) -> tk.Frame:
    """Bordered section frame."""
    f = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                 highlightbackground=BORDER)
    f.pack(fill="x", padx=15, pady=(0, 10))
    return f


def _draw_time_axis(canvas, data, x0, x1, h):
    """Draw 3–5 time labels along the bottom of a chart."""
    if not data:
        return
    first_ts = data[0].get("timestamp", 0)
    last_ts  = data[-1].get("timestamp", 0)
    if not (first_ts and last_ts and last_ts > first_ts):
        return
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        ts  = first_ts + (last_ts - first_ts) * frac
        x   = x0 + frac * (x1 - x0)
        fmt = "%H:%M" if (last_ts - first_ts) < 86400 else "%d/%m %H:%M"
        canvas.create_text(x, h - 5, text=datetime.fromtimestamp(ts).strftime(fmt),
                           fill=DIM, font=(_MONO, 7))


def _darker(hex_color: str) -> str:
    _MAP = {
        TEMP_C: "#211000",
        LOAD_C: "#061228",
        RAM_C:  "#041a10",
        GPU_C:  "#1a0800",
        VOLT_C: "#120a28",
    }
    return _MAP.get(hex_color, "#0d1117")
