# ui/pages/fan_control/hardware_info.py
"""
PC Workman - FANS Hardware Info page.

Shows fan speed that was MEASURED, or says that nothing is measuring it.

Until 2026-11-14 this page drew `random.randint()` values under the title
"Real-time fan monitoring" and listed cooler models ("Noctua NH-D15",
"Arctic P12", "be quiet!") that were typed into the source, not read from
the machine. Windows does not report fan speed to applications, so there is
exactly one honest source: a sensor daemon (LibreHardwareMonitor /
OpenHardwareMonitor), read through core.fan_sensors. No daemon, no numbers.
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

from ui.components.empty_state import build_empty_state

_REFRESH_MS = 2000


def _measured_fans() -> list:
    try:
        from core import fan_sensors
        return fan_sensors.measured()
    except Exception:
        return []


def _source_label() -> str:
    try:
        from core import fan_sensors
        return fan_sensors.source_label()
    except Exception:
        return ""


def real_temperatures() -> list:
    """[(label, text)] for what PC Workman does measure, with the CPU value
    flagged when it is an estimate. Used by the empty state so the page still
    tells the user something true."""
    out = []
    try:
        from hck_gpt.data.live_sensors import snapshot
        s = snapshot()
    except Exception:
        return out
    gpu = s.get("gpu_temp", -1)
    if s.get("gpu_ok") and gpu and gpu > 0:
        out.append(("GPU", f"{gpu:.0f}°C  ({_t('fan_control.temp_sensor', 'sensor')})"))
    cpu = s.get("cpu_temp", -1)
    if cpu and cpu > 0:
        kind = (_t("fan_control.temp_sensor", "sensor")
                if s.get("cpu_temp_src") == "sensor"
                else _t("fan_control.temp_estimated", "estimated"))
        out.append(("CPU", f"{cpu:.0f}°C  ({kind})"))
    return out


class FansHardwarePage:
    """Measured fans as cards, or an empty state. Re-checks every 2 s, so the
    page fills in by itself the moment a sensor daemon is started."""

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
    }

    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor = monitor
        self._shown_names = None        # tuple of fan names currently drawn
        self._rpm_labels = {}
        self._temp_labels = []
        self._build_page()
        self._tick()

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build_page(self):
        header = tk.Frame(self.parent, bg=self.COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(15, 4))
        tk.Label(header, text=_t("nav.fan_control_hardware", "FANS - Hardware Info"),
                 font=(_HDR, 16, "bold"), bg=self.COLORS["bg"],
                 fg=self.COLORS["text"]).pack(side="left")
        self._subtitle = tk.Label(header, text="", font=(_BODY, 10),
                                  bg=self.COLORS["bg"],
                                  fg=self.COLORS["text_muted"])
        self._subtitle.pack(side="left", padx=(15, 0))

        self._body = tk.Frame(self.parent, bg=self.COLORS["bg"])
        self._body.pack(fill="both", expand=True)

    def _clear_body(self):
        for w in self._body.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        self._rpm_labels = {}
        self._temp_labels = []

    def _build_empty(self):
        self._subtitle.config(
            text=_t("fan_control.hw_subtitle_none", "No sensor connected"))
        es = build_empty_state(
            self._body,
            title=_t("fan_control.no_sensor_title", "No fan speed sensor"),
            body=_t("fan_control.no_sensor_body",
                    "Windows does not report fan speed to applications."),
            note=_t("fan_control.no_sensor_note",
                    "Until then this page stays empty."),
            accent=self.COLORS["accent_orange"], bg=self.COLORS["bg"])
        tk.Label(es.extra, text=_t("fan_control.measured_now",
                                   "Measured right now").upper(),
                 font=(_BODY, 8, "bold"), bg=es.panel_bg,
                 fg=self.COLORS["accent_green"], anchor="w").pack(fill="x")
        self._temp_row = tk.Frame(es.extra, bg=es.panel_bg)
        self._temp_row.pack(fill="x", pady=(3, 0))
        self._panel_bg = es.panel_bg
        self._fill_temps()

    def _fill_temps(self):
        row = getattr(self, "_temp_row", None)
        if row is None:
            return
        try:
            for w in row.winfo_children():
                w.destroy()
            temps = real_temperatures()
            if not temps:
                tk.Label(row, text="-", font=(_MONO, 10), bg=self._panel_bg,
                         fg=self.COLORS["text_muted"]).pack(side="left")
            for label, text in temps:
                tk.Label(row, text=label, font=(_BODY, 9, "bold"),
                         bg=self._panel_bg,
                         fg=self.COLORS["text_muted"]).pack(side="left")
                tk.Label(row, text=text, font=(_MONO, 10, "bold"),
                         bg=self._panel_bg,
                         fg=self.COLORS["text"]).pack(side="left", padx=(6, 22))
        except Exception:
            pass

    def _build_fans(self, fans):
        self._subtitle.config(
            text=_t("fan_control.hw_subtitle_live", "Measured fan speed"))
        wrap = tk.Frame(self._body, bg=self.COLORS["bg"])
        wrap.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Label(wrap, text=_t("fan_control.fans_detected", "FANS DETECTED"),
                 font=(_HDR, 9), bg=self.COLORS["bg"],
                 fg=self.COLORS["accent_green"]).pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(wrap, bg=self.COLORS["bg"])
        grid.pack(fill="x")
        cols = 3
        for c in range(cols):
            grid.grid_columnconfigure(c, weight=1, uniform="fan")
        accents = (self.COLORS["accent_blue"], self.COLORS["accent_orange"],
                   self.COLORS["accent_purple"])
        for i, fan in enumerate(fans):
            card = tk.Frame(grid, bg=self.COLORS["card_bg"])
            card.grid(row=i // cols, column=i % cols, sticky="nsew",
                      padx=4, pady=4)
            tk.Frame(card, bg=accents[i % len(accents)],
                     height=2).pack(fill="x")
            inner = tk.Frame(card, bg=self.COLORS["card_bg"])
            inner.pack(fill="both", expand=True, padx=14, pady=10)
            tk.Label(inner, text=fan["name"], font=(_HDR, 10),
                     bg=self.COLORS["card_bg"], fg=self.COLORS["text"],
                     anchor="w").pack(fill="x")
            rpm = tk.Label(inner, text="", font=(_MONO, 17, "bold"),
                           bg=self.COLORS["card_bg"],
                           fg=accents[i % len(accents)], anchor="w")
            rpm.pack(fill="x")
            note = tk.Label(inner, text="", font=(_BODY, 8),
                            bg=self.COLORS["card_bg"],
                            fg=self.COLORS["text_muted"], anchor="w")
            note.pack(fill="x")
            self._rpm_labels[fan["name"]] = (rpm, note)

        src = _source_label() or "LibreHardwareMonitor"
        tk.Label(wrap, text=_t("fan_control.source_line",
                               "Read from {source}.", source=src),
                 font=(_BODY, 9), bg=self.COLORS["bg"],
                 fg=self.COLORS["text_muted"], anchor="w").pack(
                     fill="x", pady=(12, 0))
        self._update_values(fans)

    def _update_values(self, fans):
        for fan in fans:
            refs = self._rpm_labels.get(fan["name"])
            if not refs:
                continue
            rpm_lbl, note_lbl = refs
            rpm_lbl.config(text=f"{fan['rpm']} RPM")
            note_lbl.config(text=_t("fan_control.fan_stopped",
                                    "stopped or not connected")
                            if fan["rpm"] == 0 else "")

    # ── Refresh ──────────────────────────────────────────────────────────────
    def _tick(self):
        try:
            if not self.parent.winfo_exists():
                return
            fans = _measured_fans()
            names = tuple(f["name"] for f in fans)
            if names != self._shown_names:
                # sensor appeared, disappeared, or the set of fans changed
                self._shown_names = names
                self._clear_body()
                if fans:
                    self._build_fans(fans)
                else:
                    self._build_empty()
            elif fans:
                self._update_values(fans)
            else:
                self._fill_temps()
            self.parent.after(_REFRESH_MS, self._tick)
        except tk.TclError:
            pass                                    # widget destroyed


def create_fans_hardware_page(parent, monitor=None):
    """Factory function for FANS Hardware Info page."""
    return FansHardwarePage(parent, monitor)
