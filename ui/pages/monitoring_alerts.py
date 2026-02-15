"""
MONITORING & ALERTS - Time-Travel Statistics Center
Temperature & Voltage monitoring with historical charts, spike detection,
and adaptive learning patterns.
"""

import tkinter as tk
import time
import math
from datetime import datetime, timedelta

BG = "#0a0e14"
PANEL = "#111827"
BORDER = "#1f2937"
ACCENT = "#f59e0b"
TEXT = "#e5e7eb"
MUTED = "#6b7280"


def build_monitoring_alerts_page(self, parent):
    """Build the full Monitoring & Alerts page"""
    main = tk.Frame(parent, bg=BG)
    main.pack(fill="both", expand=True)

    # Scrollable container
    canvas = tk.Canvas(main, bg=BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(main, orient="vertical", command=canvas.yview,
                             bg="#000000", troughcolor=BG, width=8)
    scrollable = tk.Frame(canvas, bg=BG)

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Page header
    _build_page_header(scrollable)

    # Temperature Monitor section
    temp_section = _build_temperature_section(scrollable)

    # Voltage Monitor section
    volt_section = _build_voltage_section(scrollable)

    # Events / Alerts log
    _build_alerts_log(scrollable)

    # Start auto-refresh
    _start_data_refresh(parent, temp_section, volt_section)


def _build_page_header(parent):
    """Page header with status indicator"""
    header = tk.Frame(parent, bg=PANEL)
    header.pack(fill="x", padx=15, pady=(10, 8))

    inner = tk.Frame(header, bg=PANEL)
    inner.pack(fill="x", padx=15, pady=12)

    tk.Label(inner, text="⚠", font=("Segoe UI", 20), bg=PANEL,
             fg=ACCENT).pack(side="left")

    title_frame = tk.Frame(inner, bg=PANEL)
    title_frame.pack(side="left", padx=(12, 0))

    tk.Label(title_frame, text="Monitoring & Alerts", font=("Segoe UI Semibold", 13),
             bg=PANEL, fg=TEXT).pack(anchor="w")
    tk.Label(title_frame, text="Time-Travel Statistics Center",
             font=("Segoe UI", 8), bg=PANEL, fg=MUTED).pack(anchor="w")

    # Right side status
    status_frame = tk.Frame(inner, bg=PANEL)
    status_frame.pack(side="right")

    # Engine status
    engine_ok = False
    record_count = 0
    try:
        from hck_stats_engine.db_manager import db_manager
        engine_ok = db_manager.is_ready
        if engine_ok:
            conn = db_manager.get_connection()
            if conn:
                record_count = conn.execute("SELECT COUNT(*) FROM minute_stats").fetchone()[0]
    except Exception:
        pass

    status_text = "● ACTIVE" if engine_ok else "● OFFLINE"
    status_color = "#10b981" if engine_ok else "#ef4444"
    tk.Label(status_frame, text=status_text, font=("Consolas", 8, "bold"),
             bg=PANEL, fg=status_color).pack(anchor="e")

    if record_count > 0:
        tk.Label(status_frame, text=f"{record_count:,} data points",
                 font=("Consolas", 7), bg=PANEL, fg=MUTED).pack(anchor="e")


def _build_temperature_section(parent):
    """Temperature monitoring section with chart and stats"""
    section = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                       highlightbackground=BORDER)
    section.pack(fill="x", padx=15, pady=(0, 8))

    # Section header
    hdr = tk.Frame(section, bg="#1a1500")
    hdr.pack(fill="x")

    tk.Label(hdr, text="🌡️ TEMPERATURE MONITOR", font=("Consolas", 9, "bold"),
             bg="#1a1500", fg="#f59e0b", padx=10, pady=6).pack(side="left")

    # Time scale buttons
    btn_frame = tk.Frame(hdr, bg="#1a1500")
    btn_frame.pack(side="right", padx=10, pady=4)

    section._time_scale = "1D"
    scale_btns = {}

    for scale in ["1D", "3D", "1W", "1M"]:
        btn = tk.Label(btn_frame, text=scale, font=("Consolas", 7, "bold"),
                       bg="#0a0c10" if scale != "1D" else "#f59e0b",
                       fg="#6b7280" if scale != "1D" else "#000000",
                       padx=6, pady=2, cursor="hand2")
        btn.pack(side="left", padx=1)
        scale_btns[scale] = btn

        def _on_scale(e, s=scale):
            section._time_scale = s
            for k, b in scale_btns.items():
                if k == s:
                    b.config(bg="#f59e0b", fg="#000000")
                else:
                    b.config(bg="#0a0c10", fg="#6b7280")
            _refresh_temp_chart(section)

        btn.bind("<Button-1>", _on_scale)

    # Content area (chart + stats side by side)
    content = tk.Frame(section, bg=PANEL)
    content.pack(fill="x", padx=8, pady=6)

    # Chart (left - 65% width)
    chart_frame = tk.Frame(content, bg="#080a0e")
    chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

    chart_canvas = tk.Canvas(chart_frame, bg="#080a0e", height=130,
                             highlightthickness=0)
    chart_canvas.pack(fill="x", padx=2, pady=2)
    section._chart_canvas = chart_canvas
    section._chart_data = []

    # Tooltip label (hidden by default)
    tooltip_lbl = tk.Label(chart_frame, text="", font=("Consolas", 7),
                           bg="#1e293b", fg="#ffffff", padx=4, pady=2)
    section._tooltip = tooltip_lbl

    # Stats panel (right - 35% width)
    stats_frame = tk.Frame(content, bg="#0d1117", width=160)
    stats_frame.pack(side="right", fill="y")
    stats_frame.pack_propagate(False)

    section._stats_frame = stats_frame
    _build_temp_stats(stats_frame)

    # Learning status bar
    learn_bar = tk.Frame(section, bg=PANEL)
    learn_bar.pack(fill="x", padx=8, pady=(0, 6))

    # Gradient label (yellow → green)
    learn_icon = tk.Label(learn_bar, text="🧠", font=("Segoe UI", 8),
                          bg=PANEL)
    learn_icon.pack(side="left")

    tk.Label(learn_bar, text="PC Workman learns your device temperature patterns",
             font=("Segoe UI", 7), bg=PANEL, fg="#94a3b8").pack(side="left", padx=(4, 8))

    # Status badge
    status_badge = tk.Label(learn_bar, text="No regular problems",
                            font=("Consolas", 7, "bold"), bg="#0d2818", fg="#4ade80",
                            padx=8, pady=1)
    status_badge.pack(side="right")
    section._temp_status_badge = status_badge

    return section


def _build_temp_stats(parent):
    """Build temperature statistics panel"""
    tk.Label(parent, text="STATISTICS", font=("Consolas", 7, "bold"),
             bg="#0d1117", fg="#f59e0b", pady=3).pack(fill="x")

    stats = [
        ("Today AVG", "--", "#e5e7eb", "temp_today_avg"),
        ("Lifetime AVG", "--", "#94a3b8", "temp_lifetime_avg"),
        ("Max Safe", "85°C", "#ef4444", "temp_max_safe"),
        ("Current", "--", "#3b82f6", "temp_current"),
        ("Today MAX", "--", "#f59e0b", "temp_today_max"),
        ("Spikes (24h)", "0", "#f59e0b", "temp_spikes"),
    ]

    for label, value, color, key in stats:
        row = tk.Frame(parent, bg="#0d1117")
        row.pack(fill="x", padx=6, pady=1)
        tk.Label(row, text=label, font=("Consolas", 6), bg="#0d1117",
                 fg=MUTED, anchor="w").pack(side="left")
        val_lbl = tk.Label(row, text=value, font=("Consolas", 7, "bold"),
                           bg="#0d1117", fg=color, anchor="e")
        val_lbl.pack(side="right")
        parent.__dict__[key] = val_lbl


def _build_voltage_section(parent):
    """Voltage monitoring section with multi-line chart"""
    section = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                       highlightbackground=BORDER)
    section.pack(fill="x", padx=15, pady=(0, 8))

    # Section header
    hdr = tk.Frame(section, bg="#0d0a1a")
    hdr.pack(fill="x")

    tk.Label(hdr, text="⚡ VOLTAGE MONITOR", font=("Consolas", 9, "bold"),
             bg="#0d0a1a", fg="#8b5cf6", padx=10, pady=6).pack(side="left")

    # Time scale buttons
    btn_frame = tk.Frame(hdr, bg="#0d0a1a")
    btn_frame.pack(side="right", padx=10, pady=4)

    section._time_scale = "1D"
    scale_btns = {}

    for scale in ["1D", "3D", "1W", "1M"]:
        btn = tk.Label(btn_frame, text=scale, font=("Consolas", 7, "bold"),
                       bg="#0a0c10" if scale != "1D" else "#8b5cf6",
                       fg="#6b7280" if scale != "1D" else "#ffffff",
                       padx=6, pady=2, cursor="hand2")
        btn.pack(side="left", padx=1)
        scale_btns[scale] = btn

        def _on_scale(e, s=scale):
            section._time_scale = s
            for k, b in scale_btns.items():
                if k == s:
                    b.config(bg="#8b5cf6", fg="#ffffff")
                else:
                    b.config(bg="#0a0c10", fg="#6b7280")
            _refresh_volt_chart(section)

        btn.bind("<Button-1>", _on_scale)

    # Content area
    content = tk.Frame(section, bg=PANEL)
    content.pack(fill="x", padx=8, pady=6)

    # Chart (left)
    chart_frame = tk.Frame(content, bg="#080a0e")
    chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

    chart_canvas = tk.Canvas(chart_frame, bg="#080a0e", height=130,
                             highlightthickness=0)
    chart_canvas.pack(fill="x", padx=2, pady=2)
    section._chart_canvas = chart_canvas
    section._chart_data = []

    # Legend
    legend_frame = tk.Frame(chart_frame, bg="#080a0e")
    legend_frame.pack(fill="x", padx=4, pady=(0, 2))

    voltage_colors = {"CPU Load": "#3b82f6", "RAM Usage": "#10b981", "GPU Load": "#f59e0b"}
    for name, color in voltage_colors.items():
        tk.Label(legend_frame, text="●", font=("Consolas", 6),
                 bg="#080a0e", fg=color).pack(side="left", padx=(0, 1))
        tk.Label(legend_frame, text=name, font=("Consolas", 6),
                 bg="#080a0e", fg=MUTED).pack(side="left", padx=(0, 8))

    # Stats panel (right)
    stats_frame = tk.Frame(content, bg="#0d1117", width=160)
    stats_frame.pack(side="right", fill="y")
    stats_frame.pack_propagate(False)

    section._stats_frame = stats_frame
    _build_voltage_stats(stats_frame)

    # Learning status bar
    learn_bar = tk.Frame(section, bg=PANEL)
    learn_bar.pack(fill="x", padx=8, pady=(0, 6))

    learn_icon = tk.Label(learn_bar, text="🧠", font=("Segoe UI", 8), bg=PANEL)
    learn_icon.pack(side="left")

    tk.Label(learn_bar, text="PC Workman learns your device load patterns",
             font=("Segoe UI", 7), bg=PANEL, fg="#94a3b8").pack(side="left", padx=(4, 8))

    status_badge = tk.Label(learn_bar, text="No regular problems",
                            font=("Consolas", 7, "bold"), bg="#0d2818", fg="#4ade80",
                            padx=8, pady=1)
    status_badge.pack(side="right")
    section._volt_status_badge = status_badge

    return section


def _build_voltage_stats(parent):
    """Build voltage/load statistics panel"""
    tk.Label(parent, text="LOAD STATS", font=("Consolas", 7, "bold"),
             bg="#0d1117", fg="#8b5cf6", pady=3).pack(fill="x")

    stats = [
        ("CPU Today AVG", "--", "#3b82f6", "volt_cpu_avg"),
        ("RAM Today AVG", "--", "#10b981", "volt_ram_avg"),
        ("GPU Today AVG", "--", "#f59e0b", "volt_gpu_avg"),
        ("CPU Peak (24h)", "--", "#ef4444", "volt_cpu_peak"),
        ("Anomalies", "0", "#f59e0b", "volt_anomalies"),
        ("Uptime Today", "--", "#94a3b8", "volt_uptime"),
    ]

    for label, value, color, key in stats:
        row = tk.Frame(parent, bg="#0d1117")
        row.pack(fill="x", padx=6, pady=1)
        tk.Label(row, text=label, font=("Consolas", 6), bg="#0d1117",
                 fg=MUTED, anchor="w").pack(side="left")
        val_lbl = tk.Label(row, text=value, font=("Consolas", 7, "bold"),
                           bg="#0d1117", fg=color, anchor="e")
        val_lbl.pack(side="right")
        parent.__dict__[key] = val_lbl


def _build_alerts_log(parent):
    """Build recent alerts/events log"""
    section = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                       highlightbackground=BORDER)
    section.pack(fill="x", padx=15, pady=(0, 10))

    hdr = tk.Frame(section, bg="#1a0a0a")
    hdr.pack(fill="x")
    tk.Label(hdr, text="🔔 RECENT EVENTS", font=("Consolas", 9, "bold"),
             bg="#1a0a0a", fg="#ef4444", padx=10, pady=6).pack(side="left")

    container = tk.Frame(section, bg=PANEL)
    container.pack(fill="x", padx=8, pady=6)

    events = []
    try:
        from hck_stats_engine.query_api import query_api
        events = query_api.get_events(limit=8)
    except Exception:
        pass

    if events:
        for evt in events[:8]:
            row = tk.Frame(container, bg="#0d1117")
            row.pack(fill="x", pady=1)

            ts = evt.get('timestamp', 0)
            time_str = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "--:--"
            severity = evt.get('severity', 'info')
            message = evt.get('message', 'Unknown event')[:50]

            sev_color = {"info": "#3b82f6", "warning": "#f59e0b", "critical": "#ef4444"}.get(severity, "#6b7280")
            sev_text = severity.upper()[:4]

            tk.Label(row, text=time_str, font=("Consolas", 7),
                     bg="#0d1117", fg=MUTED, width=5).pack(side="left", padx=2)
            tk.Label(row, text=sev_text, font=("Consolas", 6, "bold"),
                     bg=sev_color, fg="#000000" if severity != "info" else "#ffffff",
                     width=4, padx=2).pack(side="left", padx=2)
            tk.Label(row, text=message, font=("Consolas", 7),
                     bg="#0d1117", fg=TEXT, anchor="w").pack(side="left", padx=4, fill="x", expand=True)
    else:
        tk.Label(container, text="No events recorded yet. PC Workman is monitoring...",
                 font=("Consolas", 7), bg="#0d1117", fg=MUTED, pady=8).pack(fill="x")


# ========== CHART DRAWING ==========

def _draw_area_chart(canvas, data, key, color, height=130, highlight_spikes=True):
    """Draw filled area chart with spike highlighting on canvas"""
    canvas.delete("all")

    if not data:
        canvas.create_text(canvas.winfo_width() // 2, height // 2,
                          text="Collecting data...", fill=MUTED,
                          font=("Consolas", 8))
        return

    w = canvas.winfo_width()
    if w < 10:
        w = 400

    h = height
    pad_top = 15
    pad_bottom = 18
    pad_left = 30
    pad_right = 10
    chart_h = h - pad_top - pad_bottom
    chart_w = w - pad_left - pad_right

    values = [d.get(key, 0) or 0 for d in data]
    n = len(values)
    if n < 2:
        return

    max_val = max(values) if max(values) > 0 else 100
    min_val = min(values)

    # Scale range with headroom
    val_range = max_val - min_val
    if val_range < 5:
        val_range = 10
        min_val = max(0, min_val - 5)
    max_val = min_val + val_range * 1.15

    # Grid lines
    for i in range(5):
        y = pad_top + (i / 4) * chart_h
        canvas.create_line(pad_left, y, w - pad_right, y, fill="#1a1d24", width=1)
        grid_val = max_val - (i / 4) * (max_val - min_val)
        canvas.create_text(pad_left - 3, y, text=f"{grid_val:.0f}",
                          fill=MUTED, font=("Consolas", 5), anchor="e")

    # Detect spikes (values > mean + 1.5 * std)
    mean_val = sum(values) / n
    variance = sum((v - mean_val) ** 2 for v in values) / n
    std_val = math.sqrt(variance) if variance > 0 else 1
    spike_threshold = mean_val + 1.5 * std_val

    # Build coordinate points
    points = []
    spike_ranges = []
    in_spike = False
    spike_start = 0

    for i, val in enumerate(values):
        x = pad_left + (i / (n - 1)) * chart_w
        y = pad_top + (1 - (val - min_val) / (max_val - min_val)) * chart_h
        y = max(pad_top, min(pad_top + chart_h, y))
        points.append((x, y))

        # Track spike regions
        if highlight_spikes:
            if val > spike_threshold and not in_spike:
                in_spike = True
                spike_start = i
            elif val <= spike_threshold and in_spike:
                in_spike = False
                spike_ranges.append((spike_start, i))

    if in_spike:
        spike_ranges.append((spike_start, n - 1))

    # Draw spike highlight regions (yellow glow)
    for start, end in spike_ranges:
        sx = pad_left + (start / (n - 1)) * chart_w
        ex = pad_left + (end / (n - 1)) * chart_w
        # Gradient yellow highlight
        canvas.create_rectangle(sx, pad_top, ex, pad_top + chart_h,
                               fill="#1a1800", outline="")
        # Top accent
        canvas.create_line(sx, pad_top, ex, pad_top, fill="#f59e0b", width=2)

    # Draw filled area
    fill_points = []
    fill_points.append((pad_left, pad_top + chart_h))
    fill_points.extend(points)
    fill_points.append((pad_left + chart_w, pad_top + chart_h))

    flat_fill = []
    for p in fill_points:
        flat_fill.extend(p)

    # Semi-transparent fill
    fill_color = _darker_color(color)
    canvas.create_polygon(flat_fill, fill=fill_color, outline="", smooth=True)

    # Draw line
    flat_line = []
    for p in points:
        flat_line.extend(p)
    canvas.create_line(flat_line, fill=color, width=2, smooth=True)

    # Time axis labels
    if data:
        first_ts = data[0].get('timestamp', 0)
        last_ts = data[-1].get('timestamp', 0)
        if first_ts and last_ts:
            for frac in [0, 0.25, 0.5, 0.75, 1.0]:
                ts = first_ts + (last_ts - first_ts) * frac
                x = pad_left + frac * chart_w
                time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
                canvas.create_text(x, h - 5, text=time_str,
                                  fill=MUTED, font=("Consolas", 5))

    # Bind hover for tooltip
    def _on_hover(event):
        mx = event.x
        if mx < pad_left or mx > pad_left + chart_w or not data:
            return
        idx = int(((mx - pad_left) / chart_w) * (n - 1))
        idx = max(0, min(idx, n - 1))
        d = data[idx]
        ts = d.get('timestamp', 0)
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--"
        val = values[idx]
        cpu = d.get('cpu_avg', 0) or 0
        ram = d.get('ram_avg', 0) or 0
        gpu = d.get('gpu_avg', 0) or 0
        temp = d.get('cpu_temp', None)
        temp_str = f"  Temp:{temp:.0f}°" if temp else ""
        tip = f"{time_str}  {key}:{val:.1f}  CPU:{cpu:.0f}% RAM:{ram:.0f}% GPU:{gpu:.0f}%{temp_str}"

        canvas.delete("hover_dot")
        px, py = points[idx]
        canvas.create_oval(px - 3, py - 3, px + 3, py + 3, fill=color,
                          outline="#ffffff", width=1, tags="hover_dot")

        # Position tooltip
        tip_x = min(mx + 10, w - 200)
        tip_y = max(event.y - 20, 5)
        canvas.delete("hover_tip")
        canvas.create_rectangle(tip_x - 2, tip_y - 2, tip_x + len(tip) * 5 + 6, tip_y + 14,
                               fill="#1e293b", outline="#334155", tags="hover_tip")
        canvas.create_text(tip_x + 3, tip_y + 6, text=tip, fill="#ffffff",
                          font=("Consolas", 6), anchor="w", tags="hover_tip")

    def _on_leave(event):
        canvas.delete("hover_dot")
        canvas.delete("hover_tip")

    canvas.bind("<Motion>", _on_hover)
    canvas.bind("<Leave>", _on_leave)


def _draw_multi_line_chart(canvas, data, keys_colors, height=130):
    """Draw multiple lines on same chart (for voltage/load comparison)"""
    canvas.delete("all")

    if not data:
        canvas.create_text(canvas.winfo_width() // 2, height // 2,
                          text="Collecting data...", fill=MUTED,
                          font=("Consolas", 8))
        return

    w = canvas.winfo_width()
    if w < 10:
        w = 400

    h = height
    pad_top = 15
    pad_bottom = 18
    pad_left = 30
    pad_right = 10
    chart_h = h - pad_top - pad_bottom
    chart_w = w - pad_left - pad_right

    n = len(data)
    if n < 2:
        return

    # Grid lines (0-100 scale for percentages)
    for i in range(5):
        y = pad_top + (i / 4) * chart_h
        canvas.create_line(pad_left, y, w - pad_right, y, fill="#1a1d24", width=1)
        grid_val = 100 - (i / 4) * 100
        canvas.create_text(pad_left - 3, y, text=f"{grid_val:.0f}",
                          fill=MUTED, font=("Consolas", 5), anchor="e")

    # Detect anomalies across all metrics
    for key, color in keys_colors:
        values = [d.get(key, 0) or 0 for d in data]
        mean_v = sum(values) / n
        variance = sum((v - mean_v) ** 2 for v in values) / n
        std_v = math.sqrt(variance) if variance > 0 else 1
        spike_thresh = mean_v + 2 * std_v

        # Highlight anomaly regions
        in_spike = False
        spike_start = 0
        for i, val in enumerate(values):
            if val > spike_thresh and not in_spike:
                in_spike = True
                spike_start = i
            elif val <= spike_thresh and in_spike:
                in_spike = False
                sx = pad_left + (spike_start / (n - 1)) * chart_w
                ex = pad_left + (i / (n - 1)) * chart_w
                canvas.create_rectangle(sx, pad_top, ex, pad_top + chart_h,
                                       fill="#1a1800", outline="")

    # Draw lines
    all_points = {}
    for key, color in keys_colors:
        values = [d.get(key, 0) or 0 for d in data]
        points = []
        for i, val in enumerate(values):
            x = pad_left + (i / (n - 1)) * chart_w
            y = pad_top + (1 - val / 100) * chart_h
            y = max(pad_top, min(pad_top + chart_h, y))
            points.append((x, y))

        all_points[key] = points

        flat = []
        for p in points:
            flat.extend(p)
        canvas.create_line(flat, fill=color, width=1.5, smooth=True)

    # Time axis
    if data:
        first_ts = data[0].get('timestamp', 0)
        last_ts = data[-1].get('timestamp', 0)
        if first_ts and last_ts:
            for frac in [0, 0.25, 0.5, 0.75, 1.0]:
                ts = first_ts + (last_ts - first_ts) * frac
                x = pad_left + frac * chart_w
                time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
                canvas.create_text(x, h - 5, text=time_str,
                                  fill=MUTED, font=("Consolas", 5))

    # Hover tooltip showing all values
    def _on_hover(event):
        mx = event.x
        if mx < pad_left or mx > pad_left + chart_w or not data:
            return
        idx = int(((mx - pad_left) / chart_w) * (n - 1))
        idx = max(0, min(idx, n - 1))
        d = data[idx]
        ts = d.get('timestamp', 0)
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "--"

        parts = [time_str]
        canvas.delete("hover_dot")
        for key, color in keys_colors:
            val = d.get(key, 0) or 0
            short_key = key.replace("_avg", "").upper()
            parts.append(f"{short_key}:{val:.1f}%")
            if key in all_points and idx < len(all_points[key]):
                px, py = all_points[key][idx]
                canvas.create_oval(px - 2, py - 2, px + 2, py + 2,
                                  fill=color, outline="#ffffff", width=1, tags="hover_dot")

        tip = "  ".join(parts)
        tip_x = min(mx + 10, w - 200)
        tip_y = max(event.y - 20, 5)
        canvas.delete("hover_tip")
        canvas.create_rectangle(tip_x - 2, tip_y - 2, tip_x + len(tip) * 5 + 6, tip_y + 14,
                               fill="#1e293b", outline="#334155", tags="hover_tip")
        canvas.create_text(tip_x + 3, tip_y + 6, text=tip, fill="#ffffff",
                          font=("Consolas", 6), anchor="w", tags="hover_tip")

    def _on_leave(event):
        canvas.delete("hover_dot")
        canvas.delete("hover_tip")

    canvas.bind("<Motion>", _on_hover)
    canvas.bind("<Leave>", _on_leave)


def _darker_color(hex_color):
    """Get a darker, more transparent version of a hex color"""
    color_map = {
        "#3b82f6": "#0c1a3d",
        "#10b981": "#0a2a1e",
        "#f59e0b": "#2a1a05",
        "#ef4444": "#2a0a0a",
        "#8b5cf6": "#1a0e3d",
    }
    return color_map.get(hex_color, "#0d1117")


# ========== DATA LOADING ==========

def _get_time_range(scale):
    """Get start/end timestamps for a time scale"""
    now = time.time()
    ranges = {
        "1D": 86400,
        "3D": 86400 * 3,
        "1W": 86400 * 7,
        "1M": 86400 * 30,
    }
    delta = ranges.get(scale, 86400)
    return now - delta, now


def _load_chart_data(scale):
    """Load data from stats engine for given time scale"""
    start_ts, end_ts = _get_time_range(scale)
    try:
        from hck_stats_engine.query_api import query_api
        data = query_api.get_usage_for_range(start_ts, end_ts, max_points=300)
        return data if data else []
    except Exception:
        return []


def _refresh_temp_chart(section):
    """Refresh temperature chart with current data"""
    data = _load_chart_data(section._time_scale)
    section._chart_data = data

    # Use cpu_temp if available, otherwise estimate from CPU load
    display_data = []
    for d in data:
        temp = d.get('cpu_temp', None)
        if temp is None or temp == 0:
            cpu = d.get('cpu_avg', 0) or 0
            temp = 35 + cpu * 0.5
        display_data.append({**d, 'display_temp': temp})

    section._chart_data = display_data
    _draw_area_chart(section._chart_canvas, display_data, 'display_temp', "#f59e0b")
    _update_temp_stats(section, display_data)


def _refresh_volt_chart(section):
    """Refresh voltage/load chart with current data"""
    data = _load_chart_data(section._time_scale)
    section._chart_data = data

    keys_colors = [("cpu_avg", "#3b82f6"), ("ram_avg", "#10b981"), ("gpu_avg", "#f59e0b")]
    _draw_multi_line_chart(section._chart_canvas, data, keys_colors)
    _update_volt_stats(section, data)


def _update_temp_stats(section, data):
    """Update temperature statistics panel"""
    stats_frame = section._stats_frame

    if not data:
        return

    temps = [d.get('display_temp', 0) for d in data if d.get('display_temp')]
    if not temps:
        return

    today_avg = sum(temps) / len(temps)
    today_max = max(temps)

    # Current temp
    current = temps[-1] if temps else 0

    # Lifetime average from database
    lifetime_avg = today_avg
    try:
        from hck_stats_engine.query_api import query_api
        summary = query_api.get_summary_stats(days=3650)
        if summary and summary.get('avg_cpu', 0) > 0:
            lifetime_avg = 35 + summary['avg_cpu'] * 0.5
    except Exception:
        pass

    # Spike count (temps > mean + 2 * std)
    mean_t = sum(temps) / len(temps)
    var_t = sum((t - mean_t) ** 2 for t in temps) / len(temps)
    std_t = math.sqrt(var_t) if var_t > 0 else 1
    spikes = sum(1 for t in temps if t > mean_t + 2 * std_t)

    if hasattr(stats_frame, 'temp_today_avg'):
        stats_frame.temp_today_avg.config(text=f"{today_avg:.1f}°C")
    if hasattr(stats_frame, 'temp_lifetime_avg'):
        stats_frame.temp_lifetime_avg.config(text=f"{lifetime_avg:.1f}°C")
    if hasattr(stats_frame, 'temp_current'):
        color = "#ef4444" if current > 80 else "#f59e0b" if current > 65 else "#3b82f6"
        stats_frame.temp_current.config(text=f"{current:.1f}°C", fg=color)
    if hasattr(stats_frame, 'temp_today_max'):
        stats_frame.temp_today_max.config(text=f"{today_max:.1f}°C")
    if hasattr(stats_frame, 'temp_spikes'):
        stats_frame.temp_spikes.config(text=str(spikes))

    # Update learning badge
    if hasattr(section, '_temp_status_badge'):
        if spikes > 5:
            section._temp_status_badge.config(text="Frequent spikes detected",
                                              bg="#2a1a05", fg="#f59e0b")
        elif today_max > 85:
            section._temp_status_badge.config(text="High temps detected",
                                              bg="#2a0a0a", fg="#ef4444")
        else:
            section._temp_status_badge.config(text="No regular problems",
                                              bg="#0d2818", fg="#4ade80")


def _update_volt_stats(section, data):
    """Update voltage/load statistics panel"""
    stats_frame = section._stats_frame

    if not data:
        return

    cpus = [d.get('cpu_avg', 0) or 0 for d in data]
    rams = [d.get('ram_avg', 0) or 0 for d in data]
    gpus = [d.get('gpu_avg', 0) or 0 for d in data]

    if not cpus:
        return

    cpu_avg = sum(cpus) / len(cpus)
    ram_avg = sum(rams) / len(rams)
    gpu_avg = sum(gpus) / len(gpus)
    cpu_peak = max(cpus)

    # Anomaly count
    mean_c = sum(cpus) / len(cpus)
    var_c = sum((v - mean_c) ** 2 for v in cpus) / len(cpus)
    std_c = math.sqrt(var_c) if var_c > 0 else 1
    anomalies = sum(1 for v in cpus if v > mean_c + 2 * std_c)

    # Uptime
    if data:
        first_ts = data[0].get('timestamp', 0)
        last_ts = data[-1].get('timestamp', 0)
        uptime_h = (last_ts - first_ts) / 3600 if last_ts > first_ts else 0
    else:
        uptime_h = 0

    if hasattr(stats_frame, 'volt_cpu_avg'):
        stats_frame.volt_cpu_avg.config(text=f"{cpu_avg:.1f}%")
    if hasattr(stats_frame, 'volt_ram_avg'):
        stats_frame.volt_ram_avg.config(text=f"{ram_avg:.1f}%")
    if hasattr(stats_frame, 'volt_gpu_avg'):
        stats_frame.volt_gpu_avg.config(text=f"{gpu_avg:.1f}%")
    if hasattr(stats_frame, 'volt_cpu_peak'):
        color = "#ef4444" if cpu_peak > 90 else "#f59e0b" if cpu_peak > 70 else "#3b82f6"
        stats_frame.volt_cpu_peak.config(text=f"{cpu_peak:.1f}%", fg=color)
    if hasattr(stats_frame, 'volt_anomalies'):
        stats_frame.volt_anomalies.config(text=str(anomalies))
    if hasattr(stats_frame, 'volt_uptime'):
        if uptime_h >= 24:
            stats_frame.volt_uptime.config(text=f"{uptime_h/24:.1f}d")
        else:
            stats_frame.volt_uptime.config(text=f"{uptime_h:.1f}h")

    # Update learning badge
    if hasattr(section, '_volt_status_badge'):
        if anomalies > 5:
            section._volt_status_badge.config(text="Load anomalies detected",
                                              bg="#2a1a05", fg="#f59e0b")
        else:
            section._volt_status_badge.config(text="No regular problems",
                                              bg="#0d2818", fg="#4ade80")


# ========== AUTO-REFRESH ==========

def _start_data_refresh(parent, temp_section, volt_section):
    """Start periodic data refresh for charts"""
    def _refresh():
        try:
            if not parent.winfo_exists():
                return
            _refresh_temp_chart(temp_section)
            _refresh_volt_chart(volt_section)
        except Exception:
            return

        try:
            if parent.winfo_exists():
                parent.after(30000, _refresh)
        except Exception:
            pass

    # Initial load after widget is rendered
    parent.after(500, _refresh)
