"""
In-Game Overlay  -  configurable translucent HUD that floats over borderless games.
=====================================================================================
Driven by the GAMING configurator (settings/gaming_overlay.json -> chosen metrics).
Layered tool-window with WS_EX_NOACTIVATE so it never steals focus from the game;
-topmost so it stays visible. Left/right-click cycles it through the four corners.

Values are LIVE from hck_gpt.data.live_sensors (fed by the running app), with a psutil
fallback for CPU/RAM. FPS reads from RTSS shared memory (core.fps_monitor) when MSI
Afterburner / RivaTuner is running, otherwise "--". Per-pixel alpha (transparent panel
+ crisp text) is the next visual upgrade; today it uses a stable whole-window
translucency, the same approach the mini-overlay and chart tooltip use.
"""
from __future__ import annotations

import sys
import tkinter as tk
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None

try:
    from utils.fonts import MONO as _MONOF
except ImportError:
    _MONOF = "Consolas"
_HDR = "Segoe UI Semibold"

_MARGIN = 12
_CORNERS = ("TR", "TL", "BL", "BR")   # right-top -> left-top -> left-bottom -> right-bottom

# Table layout: each component is a ROW (label left, value cells to the right),
# mirroring the default mockup (CPU | % | temp / GPU | % | temp / RAM ...).
_ROW_ORDER = ["CPU", "GPU", "RAM", "Voltage"]
_GROUP = {
    "cpu_pct": "CPU", "cpu_temp": "CPU", "cpu_mhz": "CPU", "cpu_power": "CPU",
    "gpu_pct": "GPU", "gpu_temp": "GPU", "gpu_vram": "GPU", "gpu_power": "GPU",
    "ram_pct": "RAM", "ram_gb": "RAM",
    "v12": "Voltage",
}
ROW_COLOR = {"CPU": "#3b82f6", "GPU": "#22c55e", "RAM": "#eab308", "Voltage": "#f59e0b"}
ROW_LABEL = {"CPU": "CPU", "GPU": "GPU", "RAM": "RAM", "Voltage": "12V"}
# FPS is NOT a left row - it renders as a tall box on the RIGHT, spanning the rows.
_FPS_COLOR = "#a78bfa"

# ── Style (shared with the configurator) ──────────────────────────────────────
STYLE_SIZES  = {"S": (8, 9, 13), "M": (9, 11, 16), "L": (11, 14, 20)}   # label/value/fps pt
STYLE_THEMES = {                                                        # panel/value/separator
    "dark":     ("#0a0d14", "#e8edf4", "#1a2436"),
    "slate":    ("#1e293b", "#f1f5f9", "#3a4a63"),
    "contrast": ("#000000", "#ffffff", "#333333"),
}
DEFAULT_STYLE = {"size": "M", "opacity": 80, "theme": "dark"}


def resolve_style(style):
    """Return (label_pt, value_pt, fps_pt, panel_bg, value_fg, sep, alpha) from a
    style dict, filling defaults. Shared so preview and overlay match exactly."""
    s = {**DEFAULT_STYLE, **(style or {})}
    lp, vp, fp = STYLE_SIZES.get(s.get("size"), STYLE_SIZES["M"])
    panel, value, sep = STYLE_THEMES.get(s.get("theme"), STYLE_THEMES["dark"])
    alpha = max(0.30, min(0.97, float(s.get("opacity", 80)) / 100.0))
    return lp, vp, fp, panel, value, sep, alpha


def group_rows(metrics):
    """Group metric ids into overlay rows: [(label, color, [mids]), ...].
    One row per component in fixed order; only non-empty rows returned. Shared
    by the live overlay and the configurator preview so both look identical."""
    rows = []
    for grp in _ROW_ORDER:
        mids = [m for m in metrics if _GROUP.get(m) == grp]
        if mids:
            rows.append((ROW_LABEL[grp], ROW_COLOR[grp], mids))
    return rows


def _snap() -> dict:
    try:
        from hck_gpt.data.live_sensors import snapshot
        return snapshot()
    except Exception:
        return {}


def _fmt_value(mid: str, snap: dict) -> str:
    """Live value string for one metric (live_sensors first, psutil fallback)."""
    def num(key):
        x = snap.get(key)
        return x if isinstance(x, (int, float)) and x >= 0 else None

    if mid == "cpu_pct":
        x = num("cpu_load")
        if x is None and psutil:
            try:
                x = psutil.cpu_percent(interval=None)
            except Exception:
                x = None
        return f"{int(x)}%" if x is not None else "--"
    if mid == "cpu_temp":
        x = num("cpu_temp");  return f"{int(x)}°C" if x else "--"
    if mid == "cpu_mhz":
        x = num("cpu_mhz");   return f"{x/1000:.1f}GHz" if x else "--"
    if mid == "cpu_power":
        x = num("cpu_power"); return f"{int(x)}W" if x else "--"
    if mid == "gpu_pct":
        x = num("gpu_load");  return f"{int(x)}%" if x is not None else "--"
    if mid == "gpu_temp":
        x = num("gpu_temp");  return f"{int(x)}°C" if x else "--"
    if mid == "gpu_vram":
        x = num("gpu_vram_mb"); return f"{x/1024:.1f}GB" if x else "--"
    if mid == "gpu_power":
        x = num("gpu_power"); return f"{int(x)}W" if x else "--"
    if mid == "ram_pct" and psutil:
        try:
            return f"{int(psutil.virtual_memory().percent)}%"
        except Exception:
            return "--"
    if mid == "ram_gb" and psutil:
        try:
            return f"{psutil.virtual_memory().used / 1073741824:.1f}GB"
        except Exception:
            return "--"
    if mid == "v12":
        x = num("mb_volt_12v"); return f"{x:.2f}V" if x else "--"
    if mid == "fps":
        try:
            from core.fps_monitor import read_fps
            f = read_fps()
            return str(int(round(f))) if f else "--"
        except Exception:
            return "--"
    return "--"


class InGameOverlay:
    def __init__(self, metrics, style=None, root: Optional[tk.Misc] = None):
        self.metrics = list(metrics) or ["cpu_pct", "gpu_pct", "ram_pct"]
        (self._fs_l, self._fs_v, self._fs_f,
         self._panel, self._value, self._sep, alpha) = resolve_style(style)
        self._owns   = root is None
        self.root    = root if root is not None else tk.Tk()
        self.running = False
        self._corner = 0
        self._cells: list = []

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", alpha)
        self.root.attributes("-toolwindow", True)
        self.root.configure(bg=self._panel)

        self._build()
        self.root.update_idletasks()
        self._noactivate()
        self._to_corner()
        # Bind ONLY our own widget tree - never bind_all (it leaks clicks from the
        # whole PC Workman app and would make the overlay jump on any click).
        self._bind_corner(self.root)

    def _build(self):
        wrap = tk.Frame(self.root, bg=self._panel, padx=8, pady=5)
        wrap.pack()
        self._cells = []

        rows = group_rows(self.metrics)
        if not rows and "fps" not in self.metrics:
            rows = [("CPU", ROW_COLOR["CPU"], ["cpu_pct"])]

        left = tk.Frame(wrap, bg=self._panel)
        left.pack(side="left")
        for r, (label, color, mids) in enumerate(rows):
            tk.Label(left, text=label, font=(_HDR, self._fs_l, "bold"),
                     bg=self._panel, fg=color, anchor="w").grid(
                         row=r, column=0, sticky="w", padx=(0, 10), pady=1)
            for c, mid in enumerate(mids):
                val = tk.Label(left, text="--", font=(_MONOF, self._fs_v, "bold"),
                               bg=self._panel, fg=self._value, anchor="e")
                val.grid(row=r, column=c + 1, sticky="e", padx=(0, 8), pady=1)
                self._cells.append((mid, val))

        # FPS as a tall box on the right, spanning the height of the rows.
        if "fps" in self.metrics:
            tk.Frame(wrap, bg=self._sep, width=1).pack(side="left", fill="y", padx=8)
            fb = tk.Frame(wrap, bg=self._panel)
            fb.pack(side="left", fill="y")
            tk.Label(fb, text="FPS", font=(_HDR, self._fs_l, "bold"), bg=self._panel,
                     fg=_FPS_COLOR).pack(expand=True)
            fval = tk.Label(fb, text="--", font=(_MONOF, self._fs_f, "bold"),
                            bg=self._panel, fg=self._value)
            fval.pack(expand=True)
            self._cells.append(("fps", fval))

    def _noactivate(self):
        if not sys.platform.startswith("win"):
            return
        try:
            import ctypes
            GWL_EXSTYLE, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW = -20, 0x08000000, 0x00000080
            u = ctypes.windll.user32
            hwnd = u.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            cur = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, cur | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
        except Exception as exc:
            print(f"[ingame-overlay] NOACTIVATE failed: {exc}")

    def _bind_corner(self, widget):
        """Left/right-click cycles corners - bound on the overlay's widgets only."""
        widget.bind("<Button-1>", self._next_corner)
        widget.bind("<Button-3>", self._next_corner)
        for ch in widget.winfo_children():
            self._bind_corner(ch)

    def _next_corner(self, _=None):
        self._corner = (self._corner + 1) % len(_CORNERS)
        self._to_corner()

    def _to_corner(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        right, bottom = sw - w - _MARGIN, sh - h - _MARGIN
        pos = {"TR": (right, _MARGIN), "TL": (_MARGIN, _MARGIN),
               "BL": (_MARGIN, bottom), "BR": (right, bottom)}[_CORNERS[self._corner]]
        self.root.geometry(f"+{pos[0]}+{pos[1]}")

    def _update(self):
        if not self.running:
            return
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        snap = _snap()
        for mid, lbl in self._cells:
            try:
                lbl.config(text=_fmt_value(mid, snap))
            except Exception:
                pass
        if self.running:
            self.root.after(1000, self._update)

    def start(self):
        self.running = True
        self.root.after(150, self._update)
        if self._owns:
            self.root.mainloop()

    def stop(self):
        self.running = False
        try:
            self.root.destroy()
        except Exception:
            pass


# ── Singleton launchers ───────────────────────────────────────────────────────
_instance: Optional[InGameOverlay] = None


def launch_ingame_overlay(main_root: tk.Misc, metrics, style=None) -> InGameOverlay:
    """Launch (or relaunch) the in-game overlay as a Toplevel of the main Tk root."""
    global _instance
    if _instance and getattr(_instance, "running", False):
        try:
            _instance.stop()
        except Exception:
            pass
    top = tk.Toplevel(main_root)
    ov  = InGameOverlay(metrics, style=style, root=top)
    ov.running = True
    ov.root.after(150, ov._update)
    _instance = ov
    return ov


def stop_ingame_overlay() -> None:
    global _instance
    if _instance:
        try:
            _instance.stop()
        except Exception:
            pass
    _instance = None


def is_running() -> bool:
    return bool(_instance and getattr(_instance, "running", False))
