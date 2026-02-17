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

# Session start (set when module loads — close enough to app start)
_SESSION_START = time.time()


def get_session_start():
    return _SESSION_START


class TodayReportWindow:
    """Toplevel window showing a detailed Today Report."""

    def __init__(self, parent):
        self.parent = parent
        self.win = tk.Toplevel(parent)
        self.win.title("hck_GPT — Today Report")
        self.win.configure(bg=BG)
        self.win.geometry("520x680")
        self.win.resizable(False, False)

        # Try to set as tool window (Windows)
        try:
            self.win.attributes("-toolwindow", False)
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
            "session_uptime": time.time() - _SESSION_START,
            "total_uptime_hours": 0,
            "cpu_avg": 0, "gpu_avg": 0, "ram_avg": 0,
            "cpu_timeline": [], "gpu_timeline": [], "ram_timeline": [],
            "top_system": [],
            "top_apps": [],
            "alerts_count": {"total": 0, "critical": 0, "warning": 0},
            "has_data": False,
        }

        try:
            from hck_stats_engine.query_api import query_api
            from hck_stats_engine.events import event_detector

            # Today's usage range
            now = time.time()
            today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()

            # Usage timeline for chart
            usage = query_api.get_usage_for_range(today_start, now, max_points=60)
            if usage:
                data["has_data"] = True
                data["cpu_timeline"] = [d.get("cpu_avg", 0) for d in usage]
                data["gpu_timeline"] = [d.get("gpu_avg", 0) for d in usage]
                data["ram_timeline"] = [d.get("ram_avg", 0) for d in usage]

                # Averages from today
                cpu_vals = [d.get("cpu_avg", 0) for d in usage if d.get("cpu_avg") is not None]
                gpu_vals = [d.get("gpu_avg", 0) for d in usage if d.get("gpu_avg") is not None]
                ram_vals = [d.get("ram_avg", 0) for d in usage if d.get("ram_avg") is not None]

                if cpu_vals:
                    data["cpu_avg"] = sum(cpu_vals) / len(cpu_vals)
                if gpu_vals:
                    data["gpu_avg"] = sum(gpu_vals) / len(gpu_vals)
                if ram_vals:
                    data["ram_avg"] = sum(ram_vals) / len(ram_vals)

            # Total uptime from summary
            summary = query_api.get_summary_stats(days=9999)
            if summary:
                data["total_uptime_hours"] = summary.get("total_uptime_hours", 0)

            # Top processes today
            today_str = datetime.now().strftime("%Y-%m-%d")
            procs = query_api.get_process_daily_breakdown(today_str, top_n=20)

            # Classify into system vs apps
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

            # Alerts
            data["alerts_count"] = event_detector.get_active_alerts_count()

        except Exception:
            traceback.print_exc()

        return data

    def _build(self, data):
        """Build the full report UI."""
        # Scrollable container
        outer = tk.Frame(self.win, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                                 bg=BG2, troughcolor=BG, width=8)
        self.content = tk.Frame(canvas, bg=BG)

        self.content.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.content, anchor="nw", width=505)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        self.win.protocol("WM_DELETE_WINDOW", lambda: self._on_close(canvas))

        c = self.content
        pad = {"padx": 14, "pady": (0, 0)}

        # ========== HEADER ==========
        self._build_header(c)

        # ========== SECTION 1: UPTIME ==========
        self._section_label(c, "⏱  UPTIME")
        self._build_uptime(c, data)

        # ========== SECTION 2: CHART + AVERAGES ==========
        self._section_label(c, "📊  TODAY'S USAGE")
        self._build_chart(c, data)

        # ========== SECTION 3: TOP SYSTEM PROCESSES ==========
        self._section_label(c, "⚙️  TOP 5 SYSTEM PROCESSES")
        self._build_process_list(c, data["top_system"], is_system=True)

        # ========== SECTION 4: TOP APPS ==========
        self._section_label(c, "🚀  TOP 5 APPS / GAMES / BROWSERS")
        self._build_process_list(c, data["top_apps"], is_system=False)

        # ========== SECTION 5: ALERTS STATUS ==========
        self._build_alerts_status(c, data)

        # Footer
        tk.Frame(c, bg=BG, height=12).pack()

    def _on_close(self, canvas):
        """Unbind mousewheel and destroy."""
        try:
            canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass
        self.win.destroy()

    # ================================================================
    # HEADER
    # ================================================================
    def _build_header(self, parent):
        """Gradient header banner."""
        header_h = 44
        header = tk.Canvas(parent, height=header_h, bg=BG, highlightthickness=0)
        header.pack(fill="x")

        # Rainbow gradient
        colors = [
            "#7f3ef5", "#9540ED", "#AB45E8", "#C154DC",
            "#D865C0", "#EE76A4", "#FF7B89", "#FF7B59",
            "#FF6A2F", "#fbbf24", "#22c55e", "#00ffc8"
        ]
        w = 520
        step_w = w / len(colors)
        for i, color in enumerate(colors):
            x0 = int(i * step_w)
            x1 = int(x0 + step_w) + 1
            header.create_rectangle(x0, 0, x1, header_h, fill=color, outline=color)

        header.create_text(
            w // 2, header_h // 2,
            text="TODAY REPORT",
            font=("Segoe UI", 16, "bold"),
            fill="#ffffff"
        )

        # Date
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        sub = tk.Label(parent, text=date_str, bg=BG, fg=MUTED,
                       font=("Consolas", 9))
        sub.pack(pady=(4, 6))

    # ================================================================
    # SECTION LABEL
    # ================================================================
    def _section_label(self, parent, text):
        """Colored section header."""
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", padx=14, pady=(10, 2))

        # Accent bar
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
        session_secs = data["session_uptime"]
        session_str = self._fmt_duration(session_secs)

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
        row2.pack(fill="x", padx=10, pady=(2, 6))
        tk.Label(row2, text="Lifetime uptime:", bg=BG2, fg=MUTED,
                 font=("Consolas", 10)).pack(side="left")
        tk.Label(row2, text=total_str, bg=BG2, fg=PURPLE,
                 font=("Consolas", 10, "bold")).pack(side="left", padx=(6, 0))

    # ================================================================
    # CHART + AVERAGES
    # ================================================================
    def _build_chart(self, parent, data):
        """Mini chart with CPU/GPU/RAM lines + averages on the right."""
        container = tk.Frame(parent, bg=BG2)
        container.pack(fill="x", padx=14, pady=(2, 4))

        chart_w = 340
        chart_h = 80
        avg_w = 140

        row = tk.Frame(container, bg=BG2)
        row.pack(fill="x", padx=4, pady=6)

        # Canvas chart
        chart = tk.Canvas(row, width=chart_w, height=chart_h,
                          bg=BG3, highlightthickness=0)
        chart.pack(side="left", padx=(4, 0))

        # Draw grid lines
        for y_pct in [25, 50, 75]:
            y = chart_h - (y_pct / 100 * chart_h)
            chart.create_line(0, y, chart_w, y, fill="#1a1d24", dash=(2, 4))

        # Draw data lines
        datasets = [
            (data["cpu_timeline"], CPU_COLOR, "CPU"),
            (data["gpu_timeline"], GPU_COLOR, "GPU"),
            (data["ram_timeline"], RAM_COLOR, "RAM"),
        ]

        for values, color, label in datasets:
            if not values or len(values) < 2:
                continue
            points = []
            n = len(values)
            for i, val in enumerate(values):
                x = (i / max(n - 1, 1)) * chart_w
                y = chart_h - (min(val, 100) / 100 * chart_h)
                points.append(x)
                points.append(y)

            if len(points) >= 4:
                chart.create_line(*points, fill=color, width=2, smooth=True)

        # Legend inside chart
        chart.create_text(6, 6, anchor="nw", text="CPU", fill=CPU_COLOR,
                          font=("Consolas", 7, "bold"))
        chart.create_text(36, 6, anchor="nw", text="GPU", fill=GPU_COLOR,
                          font=("Consolas", 7, "bold"))
        chart.create_text(66, 6, anchor="nw", text="RAM", fill=RAM_COLOR,
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
                 font=("Consolas", 10, "bold")).pack(pady=(4, 6))

        self._avg_row(avg_frame, "CPU", data["cpu_avg"], CPU_COLOR)
        self._avg_row(avg_frame, "GPU", data["gpu_avg"], GPU_COLOR)
        self._avg_row(avg_frame, "RAM", data["ram_avg"], RAM_COLOR)

    def _avg_row(self, parent, label, value, color):
        """Single average metric row."""
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill="x", padx=6, pady=1)

        tk.Label(row, text=f"{label}:", bg=BG2, fg=MUTED,
                 font=("Consolas", 9)).pack(side="left")

        val_str = f"{value:.1f}%" if value > 0 else "—"
        tk.Label(row, text=val_str, bg=BG2, fg=color,
                 font=("Consolas", 10, "bold")).pack(side="right")

    # ================================================================
    # PROCESS LIST
    # ================================================================
    def _build_process_list(self, parent, processes, is_system=False):
        """Compact process list with colored bars."""
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
            cpu = proc.get("cpu_avg", 0)
            ram_mb = proc.get("ram_avg_mb", 0)
            category = proc.get("_category", proc.get("category", ""))

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
            stats_color = RED if cpu > 50 else RAM_COLOR if cpu > 20 else MUTED
            tk.Label(row, text=stats_text, bg=BG2, fg=stats_color,
                     font=("Consolas", 8)).pack(side="right")

        tk.Frame(frame, bg=BG2, height=4).pack()

    # ================================================================
    # ALERTS STATUS
    # ================================================================
    def _build_alerts_status(self, parent, data):
        """Yellow status banner for temp & voltage alerts."""
        alerts = data["alerts_count"]
        total = alerts.get("total", 0)
        critical = alerts.get("critical", 0)

        container = tk.Frame(parent, bg=BG)
        container.pack(fill="x", padx=14, pady=(10, 4))

        # Status banner
        if total == 0:
            banner_bg = "#2d2a00"  # dark yellow
            banner_fg = YELLOW
            status_text = "TEMP & VOLTAGES: NO ALERTS ✅"
        elif critical > 0:
            banner_bg = "#3d0a0a"  # dark red
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
    # HELPERS
    # ================================================================
    def _fmt_duration(self, seconds):
        """Format seconds into readable uptime string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        minutes = int(seconds // 60)
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}h {mins}min"
        return f"{mins}min"


def open_today_report(parent):
    """Convenience function to open the report window."""
    try:
        TodayReportWindow(parent)
    except Exception:
        traceback.print_exc()
