# ui/pages/fan_control/usage_stats.py
"""
PC Workman - FANS Usage Statistics page.

One chart of MEASURED fan speed over a selectable range, or an empty state.

Until 2026-11-14 this page filled 12 hours of "history" with
random.randint() at open and kept adding random steps every 5 seconds.
The history now comes from core.fan_sensors, which stores only what the
sensor daemon reported while PC Workman was running.
"""
from utils.fonts import UI as _FONT_UI, HDR as _FONT_HDR, HEAVY as _FONT_HEAVY, LIGHT as _FONT_LIGHT  # noqa: F401
import tkinter as tk

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = _FONT_UI, "Consolas"
_HDR  = _FONT_HDR
_BODY = _UIF
_MONO = _MONOF

try:
    from utils.i18n import t as _t
except Exception:                                   # pragma: no cover
    def _t(key, default=None, **kw):
        return default if default is not None else key

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from ui.components.empty_state import build_empty_state

try:
    from core.fan_sensors import SAMPLE_INTERVAL_S as _FAN_SAMPLE_S
except Exception:                                   # pragma: no cover
    _FAN_SAMPLE_S = 5


class FansUsageStatsPage:
    """
    Measured fan speed over time.
    - Selectable range: NOW (1 min), 1Hr, 3Hrs, 12Hrs
    - One line per fan the sensor reports
    """

    COLORS = {
        "bg": "#0a0e14",
        "card_bg": "#111827",
        "card_border": "#1f2937",
        "text": "#e5e7eb",
        "text_muted": "#6b7280",
        "accent_green": "#10b981",
        "accent_blue": "#3b82f6",
        "accent_purple": "#8b5cf6",
        "accent_orange": "#f59e0b",
        "btn_active": "#1f2937",
        "btn_inactive": "#0d1117",
        "chart_bg": "#0d1117",
        "grid_color": "#1f2937",
    }
    _LINE_COLORS = ("#3b82f6", "#f59e0b", "#8b5cf6", "#10b981",
                    "#ef4444", "#22d3ee")

    # History resolution. The range windows below convert to a sample count
    # using THIS interval (an older version divided by 60 and NOW resolved to
    # a single point). Must equal core.fan_sensors.SAMPLE_INTERVAL_S.
    _SAMPLE_INTERVAL_S = _FAN_SAMPLE_S

    TIME_RANGES = {
        "NOW": {"label": "NOW", "seconds": 60, "description": "Last 1 minute"},
        "1HR": {"label": "1Hr", "seconds": 3600, "description": "Last 1 hour"},
        "3HRS": {"label": "3Hrs", "seconds": 10800, "description": "Last 3 hours"},
        "12HRS": {"label": "12Hrs", "seconds": 43200, "description": "Last 12 hours"},
    }

    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor = monitor
        self.current_range = "NOW"
        self.range_buttons = {}
        self._state = None              # "empty" | "collecting" | "chart"
        self._fig = self._ax = self._canvas = None
        self._build_page()
        self._tick()

    # ── Data ─────────────────────────────────────────────────────────────────
    def _series(self) -> dict:
        try:
            from core import fan_sensors
            return fan_sensors.history(
                self.TIME_RANGES[self.current_range]["seconds"])
        except Exception:
            return {}

    @staticmethod
    def _sensor_present() -> bool:
        try:
            from core import fan_sensors
            return bool(fan_sensors.measured())
        except Exception:
            return False

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build_page(self):
        header = tk.Frame(self.parent, bg=self.COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(15, 5))
        tk.Label(header, text="USAGE STATISTICS", font=(_HDR, 16, "bold"),
                 bg=self.COLORS["bg"], fg=self.COLORS["text"]).pack(side="left")
        tk.Label(header, text=_t("fan_control.usage_subtitle",
                                 "Measured fan speed over time"),
                 font=(_BODY, 10), bg=self.COLORS["bg"],
                 fg=self.COLORS["text_muted"]).pack(side="left", padx=(15, 0))

        self._selector_host = tk.Frame(self.parent, bg=self.COLORS["bg"])
        self._selector_host.pack(fill="x")
        self._body = tk.Frame(self.parent, bg=self.COLORS["bg"])
        self._body.pack(fill="both", expand=True)

    def _build_time_selector(self):
        selector_frame = tk.Frame(self._selector_host, bg=self.COLORS["bg"])
        selector_frame.pack(fill="x", padx=20, pady=(10, 5))
        tk.Label(selector_frame, text="TIME RANGE:", font=(_HDR, 9),
                 bg=self.COLORS["bg"],
                 fg=self.COLORS["text_muted"]).pack(side="left", padx=(0, 15))
        buttons_frame = tk.Frame(selector_frame, bg=self.COLORS["bg"])
        buttons_frame.pack(side="left")
        self.range_buttons = {}
        for range_id, range_data in self.TIME_RANGES.items():
            on = range_id == self.current_range
            btn = tk.Label(
                buttons_frame, text=range_data["label"], font=(_HDR, 10),
                bg=self.COLORS["btn_active"] if on else self.COLORS["btn_inactive"],
                fg=self.COLORS["accent_green"] if on else self.COLORS["text_muted"],
                padx=15, pady=6, cursor="hand2")
            btn.pack(side="left", padx=2)
            self.range_buttons[range_id] = btn
            btn.bind("<Button-1>", lambda e=None, rid=range_id: self._select_range(rid))
        self.range_description = tk.Label(
            selector_frame,
            text=self.TIME_RANGES[self.current_range]["description"],
            font=(_BODY, 9), bg=self.COLORS["bg"],
            fg=self.COLORS["text_muted"])
        self.range_description.pack(side="left", padx=(20, 0))

    def _select_range(self, range_id):
        if range_id == self.current_range:
            return
        for rid, btn in self.range_buttons.items():
            on = rid == range_id
            btn.config(
                bg=self.COLORS["btn_active"] if on else self.COLORS["btn_inactive"],
                fg=self.COLORS["accent_green"] if on else self.COLORS["text_muted"])
        self.current_range = range_id
        self.range_description.config(
            text=self.TIME_RANGES[range_id]["description"])
        self._redraw()

    def _clear(self):
        for host in (self._selector_host, self._body):
            for w in host.winfo_children():
                try:
                    w.destroy()
                except Exception:
                    pass
        self._fig = self._ax = self._canvas = None

    def _show_empty(self, collecting: bool):
        self._clear()
        if collecting:
            title = _t("fan_control.usage_title", "Usage Statistics")
            body = _t("fan_control.hist_collecting",
                      "Collecting the first samples.")
            accent = self.COLORS["accent_green"]
        else:
            title = _t("fan_control.hist_empty_title", "No fan history yet")
            body = _t("fan_control.hist_empty_body",
                      "The chart draws measured fan speed only.")
            accent = self.COLORS["accent_orange"]
        build_empty_state(self._body, title=title, body=body,
                          note=_t("fan_control.hist_since_start",
                                  "History is kept while PC Workman is running."),
                          accent=accent, bg=self.COLORS["bg"])

    def _show_chart(self):
        self._clear()
        self._build_time_selector()
        card = tk.Frame(self._body, bg=self.COLORS["card_bg"])
        card.pack(fill="both", expand=True, padx=20, pady=10)
        if not HAS_MATPLOTLIB:
            tk.Label(card, text="(Matplotlib required for charts)",
                     font=(_BODY, 9), bg=self.COLORS["card_bg"],
                     fg=self.COLORS["text_muted"]).pack(pady=20)
            return
        self._fig = Figure(figsize=(6, 2.6), dpi=100,
                           facecolor=self.COLORS["chart_bg"])
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, card)
        self._canvas.get_tk_widget().pack(fill="both", expand=True,
                                          padx=10, pady=10)
        self._redraw()

    def _redraw(self):
        if self._ax is None:
            return
        ax = self._ax
        ax.clear()
        ax.set_facecolor(self.COLORS["chart_bg"])
        seconds = self.TIME_RANGES[self.current_range]["seconds"]
        # x axis is real time ("minutes ago"), so fans that were detected at
        # different moments line up instead of being stretched to one width
        unit, div = ("s", 1.0) if seconds <= 120 else ("min", 60.0)
        try:
            from core import fan_sensors
            series = fan_sensors.history_xy(seconds)
        except Exception:
            series = {}
        for i, (name, pts) in enumerate(sorted(series.items())):
            color = self._LINE_COLORS[i % len(self._LINE_COLORS)]
            ax.plot([-ago / div for ago, _ in pts], [rpm for _, rpm in pts],
                    color=color, linewidth=1.5,
                    label=f"{name}  {pts[-1][1]} RPM")
        ax.set_xlim(-seconds / div, 0)
        ax.set_ylim(bottom=0)
        ax.tick_params(colors=self.COLORS["text_muted"], labelsize=7)
        ax.set_xlabel(f"{unit} ago", color=self.COLORS["text_muted"],
                      fontsize=7, labelpad=2)
        ax.xaxis.set_major_formatter(
            lambda v, _pos: f"{abs(v):g}")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("bottom", "left"):
            ax.spines[side].set_color(self.COLORS["grid_color"])
        ax.grid(True, alpha=0.2, color=self.COLORS["grid_color"])
        if ax.get_legend_handles_labels()[0]:
            # legend sits ABOVE the plot: inside it covered the lines
            leg = ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.01),
                            ncol=4, fontsize=7, frameon=False,
                            borderaxespad=0.0, handlelength=1.4)
            for txt in leg.get_texts():
                txt.set_color(self.COLORS["text"])
        try:
            self._fig.tight_layout(pad=0.6)
            self._canvas.draw_idle()
        except Exception:
            pass

    # ── Refresh ──────────────────────────────────────────────────────────────
    def _tick(self):
        try:
            if not self.parent.winfo_exists():
                return
            if self._series():
                state = "chart"
            elif self._sensor_present():
                state = "collecting"
            else:
                state = "empty"
            if state != self._state:
                self._state = state
                if state == "chart":
                    self._show_chart()
                else:
                    self._show_empty(collecting=(state == "collecting"))
            elif state == "chart":
                self._redraw()
            self.parent.after(self._SAMPLE_INTERVAL_S * 1000, self._tick)
        except tk.TclError:
            pass                                    # widget destroyed


def create_fans_usage_stats_page(parent, monitor=None):
    """Factory function for the Usage Statistics page."""
    return FansUsageStatsPage(parent, monitor)
