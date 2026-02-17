# hck_gpt/report_window.py
"""
Today Report — Rich visual report window for hck_GPT.
Shows uptime, usage chart, top processes, and alert status.
Canvas-based rendering with colored sections and mini-chart.
"""

import tkinter as tk
import time
import traceback
from datetime import datetime, timedelta

# Theme colors (inline to avoid circular imports)
BG = "#0b0d10"
BG2 = "#0f1114"
BG3 = "#151920"
TEXT = "#e6eef6"
MUTED = "#91a1ab"
ACCENT = "#00ffc8"
CPU_COLOR = "#d94545"
GPU_COLOR = "#4b9aff"
RAM_COLOR = "#ffd24a"
YELLOW = "#fbbf24"
GREEN = "#22c55e"
RED = "#ef4444"
PURPLE = "#a855f7"

# Singleton reference to prevent multiple windows
_active_window = None


class TodayReportWindow:
    """Toplevel window showing a detailed Today Report."""

    def __init__(self, parent):
        global _active_window

        # Close existing window if open
        if _active_window is not None:
            try:
                _active_window.win.destroy()
            except Exception:
                pass
            _active_window = None

        self.parent = parent
        self._scroll_canvas = None  # For cleanup

        self.win = tk.Toplevel(parent)
        self.win.title("hck_GPT — Today Report")
        self.win.configure(bg=BG)
        self.win.geometry("520x700")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        _active_window = self

        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass

        # Gather data
        data = self._gather_data()

        # Build UI
        self._build(data)

        # Center on parent
        self.win.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 260
            py = parent.winfo_rooty() + 30
            self.win.geometry(f"+{px}+{py}")
        except Exception:
            pass

    def _gather_data(self):
        """Collect all data for the report."""
        data = {
            "session_uptime": 0,
            "total_uptime_hours": 0,
            "days_tracked": 0,
            "cpu_avg": 0, "gpu_avg": 0, "ram_avg": 0,
            "cpu_max": 0, "gpu_max": 0, "ram_max": 0,
            "cpu_timeline": [], "gpu_timeline": [], "ram_timeline": [],
            "timeline_timestamps": [],
            "top_system": [],
            "top_apps": [],
            "alerts_count": {"total": 0, "critical": 0, "warning": 0, "info": 0},
            "has_data": False,
            "data_points": 0,
            "generated_at": datetime.now().strftime("%H:%M:%S"),
        }

        # Session uptime from InsightsEngine
        try:
            from hck_gpt.insights import insights_engine
            data["session_uptime"] = insights_engine.get_session_uptime()
        except Exception:
            pass

        try:
            from hck_stats_engine.query_api import query_api
            from hck_stats_engine.events import event_detector

            # Today's usage range
            now = time.time()
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0).timestamp()

            # Usage timeline for chart
            usage = query_api.get_usage_for_range(today_start, now, max_points=60)
            if usage:
                data["has_data"] = True
                data["data_points"] = len(usage)
                data["cpu_timeline"] = [d.get("cpu_avg", 0) or 0 for d in usage]
                data["gpu_timeline"] = [d.get("gpu_avg", 0) or 0 for d in usage]
                data["ram_timeline"] = [d.get("ram_avg", 0) or 0 for d in usage]
                data["timeline_timestamps"] = [d.get("timestamp", 0) for d in usage]

                cpu_vals = [v for v in data["cpu_timeline"] if v is not None]
                gpu_vals = [v for v in data["gpu_timeline"] if v is not None]
                ram_vals = [v for v in data["ram_timeline"] if v is not None]

                if cpu_vals:
                    data["cpu_avg"] = sum(cpu_vals) / len(cpu_vals)
                    data["cpu_max"] = max(cpu_vals)
                if gpu_vals:
                    data["gpu_avg"] = sum(gpu_vals) / len(gpu_vals)
                    data["gpu_max"] = max(gpu_vals)
                if ram_vals:
                    data["ram_avg"] = sum(ram_vals) / len(ram_vals)
                    data["ram_max"] = max(ram_vals)

            # Total uptime & tracking info
            summary = query_api.get_summary_stats(days=9999)
            if summary:
                data["total_uptime_hours"] = summary.get("total_uptime_hours", 0)
                data["days_tracked"] = summary.get("days_with_data", 0)

            # Date range
            date_range = query_api.get_available_date_range()
            if date_range:
                data["days_tracked"] = date_range.get("total_days", 0)

            # Top processes today
            today_str = datetime.now().strftime("%Y-%m-%d")
            procs = query_api.get_process_daily_breakdown(today_str, top_n=20)

            # Classify
            try:
                from core.process_classifier import classifier
                for p in procs:
                    name = p.get("process_name", "")
                    info = classifier.classify_process(name)
                    p["_type"] = info.get("type", "unknown")
                    p["_display"] = info.get("display_name", name)
                    p["_category"] = info.get("category", "")
            except Exception:
                for p in procs:
                    p["_type"] = "unknown"
                    p["_display"] = p.get("display_name", p.get("process_name", "?"))
                    p["_category"] = p.get("category", "")

            data["top_system"] = [
                p for p in procs if p["_type"] == "system"
            ][:5]

            data["top_apps"] = [
                p for p in procs if p["_type"] in ("browser", "program", "unknown")
                and p.get("cpu_avg", 0) > 0.5
            ][:5]

            data["alerts_count"] = event_detector.get_active_alerts_count()

        except Exception:
            traceback.print_exc()

        return data

    def _build(self, data):
        """Build the full report UI."""
        outer = tk.Frame(self.win, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                                 bg=BG2, troughcolor=BG, width=8)
        self.content = tk.Frame(canvas, bg=BG)
        self._scroll_canvas = canvas

        self.content.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.content, anchor="nw", width=505)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Scoped mousewheel (only when hovering this window)
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        def _bind_wheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(event):
            try:
                canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        c = self.content

        # ========== HEADER ==========
        self._build_header(c, data)

        # ========== UPTIME ==========
        self._section_label(c, "⏱  UPTIME & DATA COLLECTION")
        self._build_uptime(c, data)

        # ========== CHART + AVERAGES ==========
        self._section_label(c, "📊  TODAY'S USAGE")
        self._build_chart(c, data)

        # ========== TOP SYSTEM PROCESSES ==========
        self._section_label(c, "⚙️  TOP 5 SYSTEM PROCESSES")
        self._build_process_list(c, data["top_system"], is_system=True)

        # ========== TOP APPS ==========
        self._section_label(c, "🚀  TOP 5 APPS / GAMES / BROWSERS")
        self._build_process_list(c, data["top_apps"], is_system=False)

        # ========== ALERTS STATUS ==========
        self._build_alerts_status(c, data)

        # ========== FOOTER ==========
        self._build_footer(c, data)

    def _on_close(self):
        """Clean close: unbind mousewheel, clear singleton, destroy."""
        global _active_window
        try:
            if self._scroll_canvas:
                self._scroll_canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        _active_window = None
        try:
            self.win.destroy()
        except Exception:
            pass

    # ================================================================
    # HEADER
    # ================================================================
    def _build_header(self, parent, data):
        """Smooth gradient header banner."""
        header_h = 44
        header = tk.Canvas(parent, height=header_h, bg=BG, highlightthickness=0)
        header.pack(fill="x")

        # Smooth rainbow gradient (pixel-level fade)
        w = 520
        anchors = [
            (0.00, (127, 62, 245)),   # Purple
            (0.15, (171, 69, 232)),   # Violet
            (0.30, (216, 101, 192)),  # Pink
            (0.45, (255, 123, 89)),   # Salmon
            (0.60, (255, 106, 47)),   # Orange
            (0.75, (251, 191, 36)),   # Yellow
            (0.90, (34, 197, 94)),    # Green
            (1.00, (0, 255, 200)),    # Mint
        ]

        strip_w = 3
        for x in range(0, w, strip_w):
            t = x / max(w - 1, 1)
            color = self._interpolate_anchors(anchors, t)
            header.create_rectangle(x, 0, x + strip_w + 1, header_h,
                                    fill=color, outline=color)

        header.create_text(
            w // 2, header_h // 2,
            text="TODAY REPORT",
            font=("Segoe UI", 16, "bold"),
            fill="#ffffff"
        )

        # Date + time
        date_str = datetime.now().strftime("%A, %B %d, %Y  •  %H:%M")
        sub = tk.Label(parent, text=date_str, bg=BG, fg=MUTED,
                       font=("Consolas", 9))
        sub.pack(pady=(4, 2))

    # ================================================================
    # SECTION LABEL
    # ================================================================
    def _section_label(self, parent, text):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", padx=14, pady=(10, 2))
        tk.Frame(frame, bg=ACCENT, width=3, height=14).pack(side="left", padx=(0, 8))
        tk.Label(frame, text=text, bg=BG, fg=ACCENT,
                 font=("Consolas", 10, "bold")).pack(side="left")

    # ================================================================
    # UPTIME
    # ================================================================
    def _build_uptime(self, parent, data):
        frame = tk.Frame(parent, bg=BG2)
        frame.pack(fill="x", padx=14, pady=(2, 4))

        # Session uptime
        session_str = self._fmt_duration(data["session_uptime"])
        row1 = tk.Frame(frame, bg=BG2)
        row1.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(row1, text="Session uptime:", bg=BG2, fg=MUTED,
                 font=("Consolas", 10)).pack(side="left")
        tk.Label(row1, text=session_str, bg=BG2, fg=ACCENT,
                 font=("Consolas", 10, "bold")).pack(side="left", padx=(6, 0))

        # Total uptime
        total_h = data["total_uptime_hours"]
        if total_h > 0:
            if total_h >= 24:
                days = total_h / 24
                total_str = f"{days:.1f} days ({total_h:.0f}h)"
            else:
                total_str = f"{total_h:.1f} hours"
        else:
            total_str = "Collecting data..."

        row2 = tk.Frame(frame, bg=BG2)
        row2.pack(fill="x", padx=10, pady=(2, 2))
        tk.Label(row2, text="Lifetime uptime:", bg=BG2, fg=MUTED,
                 font=("Consolas", 10)).pack(side="left")
        tk.Label(row2, text=total_str, bg=BG2, fg=PURPLE,
                 font=("Consolas", 10, "bold")).pack(side="left", padx=(6, 0))

        # Data collection status
        days_tracked = data.get("days_tracked", 0)
        points = data.get("data_points", 0)

        row3 = tk.Frame(frame, bg=BG2)
        row3.pack(fill="x", padx=10, pady=(2, 6))
        tk.Label(row3, text="Data tracked:", bg=BG2, fg=MUTED,
                 font=("Consolas", 10)).pack(side="left")

        if days_tracked > 0:
            info_str = f"{days_tracked} day{'s' if days_tracked != 1 else ''}"
            if points > 0:
                info_str += f" • {points} data points today"
            tk.Label(row3, text=info_str, bg=BG2, fg=GPU_COLOR,
                     font=("Consolas", 10, "bold")).pack(side="left", padx=(6, 0))
        else:
            tk.Label(row3, text="Just started — collecting...", bg=BG2, fg=RAM_COLOR,
                     font=("Consolas", 10)).pack(side="left", padx=(6, 0))

    # ================================================================
    # CHART + AVERAGES
    # ================================================================
    def _build_chart(self, parent, data):
        container = tk.Frame(parent, bg=BG2)
        container.pack(fill="x", padx=14, pady=(2, 4))

        chart_w = 340
        chart_h = 90
        avg_w = 140

        row = tk.Frame(container, bg=BG2)
        row.pack(fill="x", padx=4, pady=6)

        # Canvas chart
        chart = tk.Canvas(row, width=chart_w, height=chart_h,
                          bg=BG3, highlightthickness=0)
        chart.pack(side="left", padx=(4, 0))

        # Grid lines + Y-axis labels
        for y_pct in [25, 50, 75, 100]:
            y = chart_h - (y_pct / 100 * (chart_h - 10)) - 5
            chart.create_line(24, y, chart_w, y, fill="#1a1d24", dash=(2, 4))
            chart.create_text(20, y, anchor="e", text=f"{y_pct}%",
                              fill="#2a2d34", font=("Consolas", 6))

        # Chart area (offset for Y-axis labels)
        cx0 = 26
        cx_w = chart_w - cx0

        # Data lines
        datasets = [
            (data["cpu_timeline"], CPU_COLOR),
            (data["gpu_timeline"], GPU_COLOR),
            (data["ram_timeline"], RAM_COLOR),
        ]

        for values, color in datasets:
            if not values or len(values) < 2:
                continue
            points = []
            n = len(values)
            for i, val in enumerate(values):
                x = cx0 + (i / max(n - 1, 1)) * cx_w
                y = chart_h - 5 - (min(val, 100) / 100 * (chart_h - 10))
                points.append(x)
                points.append(y)

            if len(points) >= 4:
                chart.create_line(*points, fill=color, width=2, smooth=True)

        # Time labels on X axis
        timestamps = data.get("timeline_timestamps", [])
        if timestamps and len(timestamps) >= 2:
            t_start = datetime.fromtimestamp(timestamps[0]).strftime("%H:%M")
            t_end = datetime.fromtimestamp(timestamps[-1]).strftime("%H:%M")
            chart.create_text(cx0, chart_h - 1, anchor="sw", text=t_start,
                              fill="#2a2d34", font=("Consolas", 6))
            chart.create_text(chart_w - 2, chart_h - 1, anchor="se", text=t_end,
                              fill="#2a2d34", font=("Consolas", 6))

        # Legend
        chart.create_text(cx0 + 2, 4, anchor="nw", text="CPU", fill=CPU_COLOR,
                          font=("Consolas", 7, "bold"))
        chart.create_text(cx0 + 32, 4, anchor="nw", text="GPU", fill=GPU_COLOR,
                          font=("Consolas", 7, "bold"))
        chart.create_text(cx0 + 62, 4, anchor="nw", text="RAM", fill=RAM_COLOR,
                          font=("Consolas", 7, "bold"))

        # No data overlay
        if not data["has_data"]:
            chart.create_text(chart_w // 2, chart_h // 2,
                              text="Collecting data...",
                              fill=MUTED, font=("Consolas", 10))

        # Averages panel (right side)
        avg_frame = tk.Frame(row, bg=BG2, width=avg_w)
        avg_frame.pack(side="right", fill="y", padx=(8, 4))
        avg_frame.pack_propagate(False)

        tk.Label(avg_frame, text="Averages", bg=BG2, fg=TEXT,
                 font=("Consolas", 10, "bold")).pack(pady=(4, 4))

        self._avg_row(avg_frame, "CPU", data["cpu_avg"], CPU_COLOR)
        self._avg_row(avg_frame, "GPU", data["gpu_avg"], GPU_COLOR)
        self._avg_row(avg_frame, "RAM", data["ram_avg"], RAM_COLOR)

        # Peaks (small)
        tk.Frame(avg_frame, bg="#1a1d24", height=1).pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(avg_frame, text="Peaks", bg=BG2, fg=MUTED,
                 font=("Consolas", 8)).pack()

        self._avg_row(avg_frame, "CPU", data["cpu_max"], CPU_COLOR, small=True)
        self._avg_row(avg_frame, "GPU", data["gpu_max"], GPU_COLOR, small=True)
        self._avg_row(avg_frame, "RAM", data["ram_max"], RAM_COLOR, small=True)

    def _avg_row(self, parent, label, value, color, small=False):
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill="x", padx=6, pady=0 if small else 1)

        font_size = 8 if small else 9
        val_size = 9 if small else 10

        tk.Label(row, text=f"{label}:", bg=BG2, fg=MUTED,
                 font=("Consolas", font_size)).pack(side="left")

        val_str = f"{value:.1f}%" if value > 0 else "—"
        tk.Label(row, text=val_str, bg=BG2, fg=color,
                 font=("Consolas", val_size, "bold")).pack(side="right")

    # ================================================================
    # PROCESS LIST
    # ================================================================
    def _build_process_list(self, parent, processes, is_system=False):
        frame = tk.Frame(parent, bg=BG2)
        frame.pack(fill="x", padx=14, pady=(2, 4))

        if not processes:
            tk.Label(frame, text="  No data yet — keep the app running!",
                     bg=BG2, fg=MUTED, font=("Consolas", 9)).pack(
                         anchor="w", padx=8, pady=6)
            return

        for i, proc in enumerate(processes):
            name = proc.get("_display", proc.get("display_name",
                            proc.get("process_name", "?")))
            # Truncate long names
            if len(name) > 22:
                name = name[:20] + ".."

            cpu = proc.get("cpu_avg", 0)
            ram_mb = proc.get("ram_avg_mb", 0)
            category = proc.get("_category", proc.get("category", ""))
            active = proc.get("total_active_seconds", proc.get("active_seconds", 0))

            row = tk.Frame(frame, bg=BG2)
            row.pack(fill="x", padx=8, pady=1)

            # Rank
            rank_color = ACCENT if i == 0 else TEXT
            tk.Label(row, text=f"{i+1}.", bg=BG2, fg=rank_color,
                     font=("Consolas", 9, "bold"), width=3).pack(side="left")

            # Name
            tk.Label(row, text=name, bg=BG2, fg=TEXT,
                     font=("Consolas", 9), anchor="w").pack(side="left")

            # Category badge for apps
            if not is_system and category and category not in ("Unknown", "System"):
                badge_colors = {
                    "Gaming": ("#7f1d1d", RED),
                    "Browser": ("#1a365d", GPU_COLOR),
                    "Development": ("#1a2e1a", GREEN),
                    "Communication": ("#2d1b4e", PURPLE),
                    "Media": ("#3d2b00", RAM_COLOR),
                }
                bg_c, fg_c = badge_colors.get(category, (BG3, MUTED))
                tk.Label(row, text=f" {category} ", bg=bg_c, fg=fg_c,
                         font=("Consolas", 7)).pack(side="left", padx=(4, 0))

            # Stats (right side)
            stats_text = f"CPU {cpu:.1f}%  RAM {ram_mb:.0f}MB"
            if active and active > 60:
                time_str = self._fmt_duration(active)
                stats_text += f"  {time_str}"

            stats_color = RED if cpu > 50 else RAM_COLOR if cpu > 20 else MUTED
            tk.Label(row, text=stats_text, bg=BG2, fg=stats_color,
                     font=("Consolas", 8)).pack(side="right")

        tk.Frame(frame, bg=BG2, height=4).pack()

    # ================================================================
    # ALERTS STATUS
    # ================================================================
    def _build_alerts_status(self, parent, data):
        alerts = data["alerts_count"]
        total = alerts.get("total", 0)
        critical = alerts.get("critical", 0)

        container = tk.Frame(parent, bg=BG)
        container.pack(fill="x", padx=14, pady=(10, 4))

        if total == 0:
            banner_bg = "#2d2a00"
            banner_fg = YELLOW
            status_text = "TEMP & VOLTAGES: NO ALERTS ✅"
        elif critical > 0:
            banner_bg = "#3d0a0a"
            banner_fg = RED
            status_text = f"TEMP & VOLTAGES: {critical} CRITICAL ALERT{'S' if critical > 1 else ''} 🔴"
        else:
            banner_bg = "#2d2a00"
            banner_fg = YELLOW
            status_text = f"TEMP & VOLTAGES: {total} WARNING{'S' if total > 1 else ''} ⚠️"

        banner = tk.Frame(container, bg=banner_bg)
        banner.pack(fill="x")

        tk.Label(banner, text=status_text, bg=banner_bg, fg=banner_fg,
                 font=("Consolas", 11, "bold")).pack(pady=8)

    # ================================================================
    # FOOTER
    # ================================================================
    def _build_footer(self, parent, data):
        """Footer with generation timestamp and refresh button."""
        footer = tk.Frame(parent, bg=BG)
        footer.pack(fill="x", padx=14, pady=(6, 8))

        # Timestamp
        gen_time = data.get("generated_at", "?")
        tk.Label(footer, text=f"Generated at {gen_time}",
                 bg=BG, fg="#2a2d34", font=("Consolas", 8)).pack(side="left")

        # Refresh button
        refresh_btn = tk.Button(
            footer, text="🔄 Refresh", bg=BG2, fg=ACCENT,
            activebackground=BG3, activeforeground=ACCENT,
            font=("Consolas", 8, "bold"), bd=0, padx=10, pady=2,
            command=self._refresh, cursor="hand2"
        )
        refresh_btn.pack(side="right")

    def _refresh(self):
        """Rebuild the report with fresh data."""
        try:
            # Destroy old content
            for widget in self.win.winfo_children():
                widget.destroy()

            # Rebuild
            data = self._gather_data()
            self._build(data)
        except Exception:
            traceback.print_exc()

    # ================================================================
    # HELPERS
    # ================================================================
    def _fmt_duration(self, seconds):
        if not seconds:
            return "0s"
        seconds = float(seconds)
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}min"
        return f"{mins}min"

    def _interpolate_anchors(self, anchors, t):
        """Interpolate between color anchor points."""
        for j in range(len(anchors) - 1):
            if anchors[j][0] <= t <= anchors[j + 1][0]:
                seg_t = (t - anchors[j][0]) / (anchors[j + 1][0] - anchors[j][0])
                c0 = anchors[j][1]
                c1 = anchors[j + 1][1]
                r = int(c0[0] + (c1[0] - c0[0]) * seg_t)
                g = int(c0[1] + (c1[1] - c0[1]) * seg_t)
                b = int(c0[2] + (c1[2] - c0[2]) * seg_t)
                return f"#{r:02x}{g:02x}{b:02x}"
        c = anchors[-1][1]
        return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def open_today_report(parent):
    """Convenience function to open the report window."""
    try:
        TodayReportWindow(parent)
    except Exception:
        traceback.print_exc()
