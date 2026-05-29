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
from datetime import datetime, timedelta

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
DIM     = "#374151"

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
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _wheel, add="+")

    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # ── Header (contains HEALTH + ANOMALIES badges) ───────────────────────────
    rings_cv, score_ref, health_lbl, anom_lbl = _build_page_header(sf)

    # ── Temperature section ───────────────────────────────────────────────────
    temp_sec = _build_temperature_section(sf)

    # ── Voltage / Load section ────────────────────────────────────────────────
    load_sec = _build_load_section(sf)

    # ── 30-day Anomaly Calendar ───────────────────────────────────────────────
    _build_anomaly_calendar(sf)

    # ── Events log ────────────────────────────────────────────────────────────
    _build_alerts_log(sf)

    # ── Auto-refresh ─────────────────────────────────────────────────────────
    _start_refresh(parent, rings_cv, score_ref, health_lbl, anom_lbl, temp_sec, load_sec)


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

    # ── Far right: health rings ───────────────────────────────────────────────
    rings_size = 80
    rings_cv = tk.Canvas(body, width=rings_size, height=rings_size,
                         bg=PANEL, highlightthickness=0)
    rings_cv.pack(side="right", padx=(0, 10))
    score_ref = [90]
    _draw_health_rings(rings_cv, rings_size, 90, 70, 55)

    # ── Legend (left of rings) ────────────────────────────────────────────────
    leg = tk.Frame(body, bg=PANEL)
    leg.pack(side="right", padx=(0, 14), anchor="center")
    for label, col in [("Thermal", TEMP_C), ("Memory", RAM_C), ("Load", LOAD_C)]:
        r = tk.Frame(leg, bg=PANEL)
        r.pack(anchor="e")
        tk.Label(r, text="━", font=(_MONO, 8),
                 bg=PANEL, fg=col).pack(side="left")
        tk.Label(r, text=f" {label}", font=(_BODY, 8),
                 bg=PANEL, fg=MUTED).pack(side="left")

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
    """Three concentric arc gauges drawn outer-to-inner."""
    canvas.delete("all")
    cx = cy = size // 2

    rings = [
        (thermal, TEMP_C,  cx - 6,  8),   # outer - thermal
        (memory,  RAM_C,   cx - 14, 8),   # mid   - memory
        (load,    LOAD_C,  cx - 22, 8),   # inner - load
    ]

    for score, col, r, thick in rings:
        # Background arc (muted rail)
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=225, extent=-270,
                          outline=DIM, width=thick, style="arc")
        # Score arc
        ext    = -(270 * max(0, min(100, score)) / 100)
        s_col  = OK_C if score >= 80 else WARN_C if score >= 55 else CRIT_C
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                          start=225, extent=ext,
                          outline=s_col, width=thick, style="arc")

    # Centre score text
    avg_score = int((thermal + memory + load) / 3)
    s_col = OK_C if avg_score >= 80 else WARN_C if avg_score >= 55 else CRIT_C
    canvas.create_text(cx, cy - 4, text=str(avg_score),
                       font=(_MONO, 14, "bold"), fill=s_col)
    canvas.create_text(cx, cy + 10, text="SCORE",
                       font=(_MONO, 5), fill=DIM)


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
        tk.Label(body, text=title, font=(_MONO, 6, "bold"),
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

    chart_cv = tk.Canvas(chart_frame, bg="#050809", height=128, highlightthickness=0)
    chart_cv.pack(fill="x", padx=2, pady=2)
    section._chart_canvas = chart_cv
    section._chart_data    = []

    # Alert timeline strip
    tl_cv = tk.Canvas(chart_frame, bg="#03050a", height=22, highlightthickness=0)
    tl_cv.pack(fill="x")
    section._timeline_cv = tl_cv

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

    chart_cv = tk.Canvas(chart_frame, bg="#050809", height=128, highlightthickness=0)
    chart_cv.pack(fill="x", padx=2, pady=2)
    section._chart_canvas = chart_cv
    section._chart_data    = []

    # Legend
    legend = tk.Frame(chart_frame, bg="#050809")
    legend.pack(fill="x", padx=4, pady=(0, 3))
    for name, col in [("CPU", LOAD_C), ("RAM", RAM_C), ("GPU", GPU_C)]:
        tk.Label(legend, text="●", font=(_MONO, 6),
                 bg="#050809", fg=col).pack(side="left", padx=(0, 1))
        tk.Label(legend, text=name, font=(_MONO, 6),
                 bg="#050809", fg=MUTED).pack(side="left", padx=(0, 8))

    # Alert timeline
    tl_cv = tk.Canvas(chart_frame, bg="#03050a", height=22, highlightthickness=0)
    tl_cv.pack(fill="x")
    section._timeline_cv = tl_cv

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

        tooltip_txt = (f"{day_date.strftime('%b %d')}  "
                       f"{'no anomalies' if anomalies == 0 else f'{anomalies} anomalies'}")

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
    tk.Label(legend, text="Clean", font=(_MONO, 6), bg=PANEL, fg=DIM).pack(side="left", padx=(0, 6))
    for col, txt in [("#4ade80", "Mild"), ("#f59e0b", "Moderate"), ("#ef4444", "Heavy")]:
        dot = tk.Frame(legend, bg=col, width=8, height=8)
        dot.pack(side="left", padx=(0, 2))
        tk.Label(legend, text=txt, font=(_MONO, 6),
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


def _render_event_row(parent, evt: dict):
    sev        = evt.get("severity", "info")
    sev_colors = {"info": LOAD_C, "warning": WARN_C, "critical": CRIT_C}
    sev_col    = sev_colors.get(sev, MUTED)
    ts         = evt.get("timestamp", 0)
    time_str   = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "--:--"
    day_str    = datetime.fromtimestamp(ts).strftime("%a") if ts else "---"
    message    = evt.get("message", "Unknown event")[:60]

    row = tk.Frame(parent, bg=PANEL2)
    row.pack(fill="x", pady=1)

    # Severity stripe
    tk.Frame(row, bg=sev_col, width=3).pack(side="left", fill="y")

    # Time
    time_f = tk.Frame(row, bg=PANEL2)
    time_f.pack(side="left", padx=(6, 0))
    tk.Label(time_f, text=time_str, font=(_MONO, 8, "bold"),
             bg=PANEL2, fg=TEXT).pack(anchor="w")
    tk.Label(time_f, text=day_str, font=(_MONO, 6),
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

def _draw_adaptive_chart(canvas, data, key, color, height=150):
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

    mean, sigma = _compute_adaptive(values)
    base_lo = max(0, mean - sigma)
    base_hi = mean + sigma * 1.5
    thresh  = mean + sigma * 1.5      # same as base_hi

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
                           fill=DIM, font=(_MONO, 5), anchor="e")

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
                           fill="#ffffff", font=(_MONO, 6),
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
                           fill=DIM, font=(_MONO, 5), anchor="e")

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
                           fill="#ffffff", font=(_MONO, 6),
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
                           font=(_MONO, 5), fill="#1e293b", anchor=anch)


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
    _draw_adaptive_chart(section._chart_canvas, data, "display_temp", TEMP_C)

    # Timeline strip
    if hasattr(section, "_timeline_cv"):
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
    _draw_multi_load_chart(section._chart_canvas, data)

    if hasattr(section, "_timeline_cv"):
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

    cur_col = CRIT_C if cur > 80 else WARN_C if cur > 65 else LOAD_C

    for attr, val, kw in [
        ("temp_today_avg",    f"{avg:.1f}°C", {}),
        ("temp_current",      f"{cur:.1f}°C", {"fg": cur_col}),
        ("temp_today_max",    f"{mx:.1f}°C",  {}),
        ("temp_spikes",       str(spikes),    {}),
        ("temp_trend",        trend,          {}),
    ]:
        lbl = getattr(sf, attr, None)
        if lbl:
            lbl.config(text=val, **kw)

    # Workload badge
    if hasattr(section, "_workload_lbl"):
        wl, wl_col = _classify_workload(data)
        section._workload_lbl.config(text=f"Workload: {wl}", fg=wl_col)

    # Status badge
    if hasattr(section, "_temp_badge"):
        if spikes > 5 or mx > 85:
            col  = CRIT_C if mx > 85 else WARN_C
            bgc  = "#2a0a0a" if mx > 85 else "#2a1800"
            msg  = "High temps detected" if mx > 85 else "Frequent spikes"
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

def _start_refresh(parent, rings_cv, score_ref, health_lbl, anom_lbl, temp_sec, load_sec):
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
                           fill=DIM, font=(_MONO, 5))


def _darker(hex_color: str) -> str:
    _MAP = {
        TEMP_C: "#211000",
        LOAD_C: "#061228",
        RAM_C:  "#041a10",
        GPU_C:  "#1a0800",
        VOLT_C: "#120a28",
    }
    return _MAP.get(hex_color, "#0d1117")
