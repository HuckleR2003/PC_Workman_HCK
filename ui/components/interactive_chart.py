"""
InteractiveChart - PC Workman HCK  v1.7.8
==========================================
Professional interactive line-chart widget built on tkinter.Canvas.

Interaction model
-----------------
    Pan        left-drag  → scroll the data window left / right
    Zoom       scroll-wheel  →  zoom in/out around the cursor X position
    Reset      double-click  →  show all data (zoom 1×)
    Crosshair  mouse move  →  dotted X+Y lines + live value bubble
    Pin        single click  →  anchor a detailed tooltip on the nearest
                                data point; persists until clicked elsewhere
                                or Escape is pressed
    Minimap    18-px strip below chart  →  overview of full data range;
               click or drag to jump/pan the main view

Usage
-----
    from ui.components.interactive_chart import InteractiveChart

    chart = InteractiveChart(parent, height=150)
    chart.set_series([
        {"values": [30.1, 35.2, ...], "color": "#f59e0b", "label": "CPU"},
        {"values": [45.0, 48.0, ...], "color": "#10b981", "label": "GPU"},
    ])
    chart.set_timestamps([ts1, ts2, ...])        # Unix-epoch floats; optional
    chart.set_baseline(mean=45.0, lo=38.0, hi=62.0)  # optional learned band
    chart.set_anomalies([                        # optional event markers
        {"idx": 14, "severity": "warning", "reason": "4% above idle baseline"},
        {"idx": 31, "severity": "critical", "reason": "Isolated spike z=4.2"},
    ])
    chart.draw()
"""
from __future__ import annotations

import tkinter as tk
from datetime import datetime

# ── Font system ───────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_BODY = _UIF
_MONO = _MONOF

# ── Palette ───────────────────────────────────────────────────────────────────
_C = {
    "bg":        "#050809",
    "bg_mm":     "#030507",
    "grid":      "#0d1520",
    "text":      "#374151",
    "base_band": "#0a1a0c",
    "base_line": "#163220",
    "cross":     "#1a3050",
    "pin_bg":    "#0f172a",
    "pin_bd":    "#334155",
    "pin_fg":    "#e2e8f0",
    "mm_sel":    "#1e3a5f",
    "reset_fg":  "#374151",
    "reset_hov": "#6366f1",
}

_SEV_COL = {
    "info":     "#3b82f6",
    "warning":  "#f59e0b",
    "warn":     "#f59e0b",
    "critical": "#ef4444",
    "crit":     "#ef4444",
}

_AREA_DARK = {
    "#3b82f6": "#040c1a",
    "#fbbf24": "#120e00",
    "#10b981": "#030f08",
    "#f59e0b": "#120b00",
    "#f97316": "#130600",
    "#8b5cf6": "#0b0618",
    "#ef4444": "#180404",
    "#a78bfa": "#080415",
    "#6366f1": "#060518",
}


def _area_fill(color: str) -> str:
    if color in _AREA_DARK:
        return _AREA_DARK[color]
    try:
        r = int(int(color[1:3], 16) * 0.12)
        g = int(int(color[3:5], 16) * 0.12)
        b = int(int(color[5:7], 16) * 0.12)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#0d1117"


# ── Main class ────────────────────────────────────────────────────────────────

class InteractiveChart:
    """
    Professional interactive line-chart for Tkinter.
    All state is internal; canvas is re-drawn on every interaction event.
    Thread-safe: all bindings run on the Tkinter main thread.
    """

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(
        self,
        parent:       tk.Widget,
        height:       int   = 150,
        bg:           str   = _C["bg"],
        minimap:      bool  = True,
        y_min_range:  float = 5.0,
        label:        str   = "",
        bar_mode:     bool  = False,
    ) -> None:
        self._height      = height
        self._bg          = bg
        self._minimap     = minimap
        self._y_min_range = y_min_range
        self._label       = label
        self._bar_mode    = bar_mode

        # ── Data ──────────────────────────────────────────────────────────────
        self._series:     list[dict]  = []
        self._timestamps: list[float] = []
        self._baseline:   dict | None = None
        self._anomalies:  list[dict]  = []

        # ── View state (data-index space) ─────────────────────────────────────
        self._view_lo: float = 0.0
        self._view_hi: float = 0.0

        # ── Interaction state ─────────────────────────────────────────────────
        self._drag_x:      int | None = None
        self._drag_moved:  bool       = False
        self._pin_idx:     int | None = None
        self._mm_drag:     bool       = False

        # ── Bar animation state ───────────────────────────────────────────────
        self._bar_anim_ease: float     = 1.0
        self._bar_anim_t0:   float     = 0.0
        self._bar_anim_id:   int|None  = None
        self._bar_prev_n:    int       = 0

        # ── Layout margins (constant) ─────────────────────────────────────────
        self._PL, self._PR, self._PT, self._PB = 42, 8, 10, 20

        # ── Widgets ───────────────────────────────────────────────────────────
        self._frame = tk.Frame(parent, bg=bg)
        self._frame.pack(fill="x")

        self.canvas = tk.Canvas(
            self._frame, bg=bg, height=height,
            highlightthickness=0, cursor="crosshair"
        )
        self.canvas.pack(fill="x")

        if minimap:
            self._mm_cv = tk.Canvas(
                self._frame, bg=_C["bg_mm"],
                height=18, highlightthickness=0, cursor="hand2"
            )
            self._mm_cv.pack(fill="x", pady=(1, 0))
        else:
            self._mm_cv = None

        # Control bar: chart label + zoom info + reset button
        ctrl = tk.Frame(self._frame, bg=bg)
        ctrl.pack(fill="x", pady=(1, 0))
        if label:
            tk.Label(ctrl, text=label, font=(_MONO, 6, "bold"),
                     bg=bg, fg="#74839a").pack(side="left", padx=6)

        reset_btn = tk.Label(ctrl, text="⟲ reset",
                             font=(_MONO, 6), bg=bg, fg=_C["reset_fg"],
                             cursor="hand2")
        reset_btn.pack(side="right", padx=(0, 6))
        reset_btn.bind("<Button-1>", lambda e: self.reset_view())
        reset_btn.bind("<Enter>",    lambda e: reset_btn.config(fg=_C["reset_hov"]))
        reset_btn.bind("<Leave>",    lambda e: reset_btn.config(fg=_C["reset_fg"]))

        self._zoom_lbl = tk.Label(ctrl, text="",
                                  font=(_MONO, 6), bg=bg, fg=_C["text"])
        self._zoom_lbl.pack(side="right", padx=(0, 4))

        self._bind_events()

    # ── Public data API ───────────────────────────────────────────────────────

    def set_series(self, series: list[dict]) -> "InteractiveChart":
        """series = [{"values": [...float|None], "color": "#hex", "label": str}]"""
        prev_n = self._n()
        self._series = series
        self._reset_view_to_all()
        if self._bar_mode and self._n() > prev_n:
            self._start_bar_anim()
        return self

    def update_series_values(self, series: list[dict]) -> "InteractiveChart":
        """Update series data WITHOUT resetting the pan/zoom view (for live append updates)."""
        prev_n = self._n()
        self._series = series
        if self._bar_mode and self._n() > prev_n:
            self._start_bar_anim()
        return self

    def set_timestamps(self, ts_list: list[float]) -> "InteractiveChart":
        self._timestamps = ts_list
        return self

    def set_baseline(self, mean: float, lo: float, hi: float) -> "InteractiveChart":
        self._baseline = {"mean": mean, "lo": lo, "hi": hi}
        return self

    def clear_baseline(self) -> "InteractiveChart":
        self._baseline = None
        return self

    def set_anomalies(self, anomalies: list[dict]) -> "InteractiveChart":
        """anomalies = [{"idx": int, "severity": str, "reason": str, "type": str}]"""
        self._anomalies = anomalies
        return self

    def draw(self) -> None:
        """Render the current view. Call after updating data."""
        self._redraw()

    def reset_view(self) -> None:
        self._reset_view_to_all()
        self._pin_idx = None
        self._redraw()

    # ── View helpers ──────────────────────────────────────────────────────────

    def _n(self) -> int:
        if not self._series:
            return 0
        return max(len(s.get("values", [])) for s in self._series)

    def _reset_view_to_all(self) -> None:
        n = self._n()
        self._view_lo = 0.0
        self._view_hi = max(0.0, float(n - 1))

    # ── Bar-mode animation ────────────────────────────────────────────────────

    def _start_bar_anim(self) -> None:
        import time as _time
        if self._bar_anim_id is not None:
            try:
                self.canvas.after_cancel(self._bar_anim_id)
            except Exception:
                pass
        self._bar_anim_ease = 0.0
        self._bar_anim_t0   = _time.perf_counter()
        self._bar_anim_id   = self.canvas.after(16, self._tick_bar_anim)

    def _tick_bar_anim(self) -> None:
        import time as _time
        try:
            if not self.canvas.winfo_exists():
                self._bar_anim_id = None
                return
        except Exception:
            self._bar_anim_id = None
            return
        elapsed = _time.perf_counter() - self._bar_anim_t0
        t = min(elapsed / 0.55, 1.0)
        self._bar_anim_ease = 1.0 - (1.0 - t) ** 3   # ease-out cubic
        self._redraw()
        if t < 1.0:
            self._bar_anim_id = self.canvas.after(16, self._tick_bar_anim)
        else:
            self._bar_anim_ease = 1.0
            self._bar_anim_id   = None

    def _clamp(self) -> None:
        n = self._n()
        if n < 2:
            return
        span = max(4.0, self._view_hi - self._view_lo)
        if self._view_lo < 0:
            self._view_hi -= self._view_lo
            self._view_lo  = 0.0
        if self._view_hi > n - 1:
            self._view_lo -= self._view_hi - (n - 1)
            self._view_hi  = float(n - 1)
        self._view_lo = max(0.0, self._view_lo)
        self._view_hi = min(float(n - 1), self._view_hi)
        # Enforce minimum span
        if self._view_hi - self._view_lo < 4.0:
            self._view_hi = min(float(n - 1), self._view_lo + 4.0)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _redraw(self) -> None:
        try:
            if not self.canvas.winfo_exists():
                return
        except Exception:
            return
        self._draw_main()
        if self._mm_cv:
            try:
                if self._mm_cv.winfo_exists():
                    self._draw_minimap()
            except Exception:
                pass
        self._update_zoom_label()

    def _draw_main(self) -> None:
        cv = self.canvas
        cv.delete("all")
        W = cv.winfo_width() or 400
        H = self._height
        n = self._n()

        if n < 2 or not self._series:
            cv.create_text(W // 2, H // 2, text="Collecting data…",
                           fill=_C["text"], font=(_MONO, 8))
            return

        PL, PR, PT, PB = self._PL, self._PR, self._PT, self._PB
        cw = W - PL - PR
        ch = H - PT - PB

        lo = max(0,     int(self._view_lo))
        hi = min(n - 1, int(self._view_hi) + 1)

        if self._bar_mode:
            self._draw_bars(cv, W, H, n, lo, hi, PL, PR, PT, ch)
            return

        # ── Y range from visible data ─────────────────────────────────────────
        all_vis = []
        for s in self._series:
            vals = s.get("values", [])
            all_vis += [v for v in vals[lo:hi + 1] if v is not None]
        if self._baseline:
            all_vis += [self._baseline["lo"], self._baseline["hi"]]
        if not all_vis:
            return

        ylo = min(all_vis)
        yhi = max(all_vis)
        if yhi - ylo < self._y_min_range:
            mid = (ylo + yhi) / 2
            ylo = mid - self._y_min_range / 2
            yhi = mid + self._y_min_range / 2
        pad = (yhi - ylo) * 0.05
        ylo -= pad;  yhi += pad
        yrng = max(yhi - ylo, 0.001)

        def vy(v: float) -> float:
            return PT + ch * (1.0 - (v - ylo) / yrng)

        def vx(idx: float) -> float:
            frac = (idx - self._view_lo) / max(self._view_hi - self._view_lo, 1)
            return PL + frac * cw

        # ── Grid ──────────────────────────────────────────────────────────────
        n_ticks = 5
        for i in range(n_ticks + 1):
            v = ylo + yrng * i / n_ticks
            y = vy(v)
            cv.create_line(PL, y, W - PR, y, fill=_C["grid"], width=1)
            label_str = f"{v:.1f}" if yrng < 5 else f"{v:.0f}"
            cv.create_text(PL - 4, y, text=label_str,
                           fill=_C["text"], font=(_MONO, 5), anchor="e")

        # ── Baseline band ─────────────────────────────────────────────────────
        if self._baseline:
            bl   = self._baseline
            y_bl = vy(bl["lo"])
            y_bh = vy(bl["hi"])
            cv.create_rectangle(PL, y_bh, W - PR, y_bl,
                                 fill=_C["base_band"], outline="")
            cv.create_line(PL, vy(bl["mean"]), W - PR, vy(bl["mean"]),
                           fill=_C["base_line"], width=1, dash=(6, 4))

        # ── Anomaly zone backgrounds ───────────────────────────────────────────
        for anom in self._anomalies:
            idx = anom.get("idx", -1)
            if lo <= idx <= hi:
                sev = anom.get("severity", "warning")
                col = _SEV_COL.get(sev, "#f59e0b")
                px  = vx(idx)
                cv.create_rectangle(px - 1, PT, px + 1, PT + ch,
                                     fill=col, outline="")

        # ── Series: filled area + line ────────────────────────────────────────
        for s in self._series:
            vals = s.get("values", [])
            col  = s.get("color", "#3b82f6")

            line_pts = []
            for i in range(lo, min(hi + 1, len(vals))):
                v = vals[i]
                if v is None:
                    continue
                line_pts += [vx(i), vy(v)]

            if len(line_pts) >= 4:
                area = [PL, PT + ch] + line_pts + [line_pts[-2], PT + ch]
                cv.create_polygon(area, fill=_area_fill(col), outline="", smooth=True)
                cv.create_line(line_pts, fill=col, width=2, smooth=True)

        # ── Anomaly dots (on top) ─────────────────────────────────────────────
        for anom in self._anomalies:
            idx = anom.get("idx", -1)
            sev = anom.get("severity", "warning")
            if lo <= idx <= hi:
                col = _SEV_COL.get(sev, "#f59e0b")
                y_vals = [
                    s["values"][idx]
                    for s in self._series
                    if idx < len(s.get("values", []))
                    and s["values"][idx] is not None
                ]
                if y_vals:
                    r  = 4 if sev in ("critical", "crit") else 3
                    px = vx(idx)
                    py = vy(y_vals[0])
                    cv.create_oval(px - r, py - r, px + r, py + r,
                                   fill=col, outline="#ffffff", width=1)

        # ── Pinned tooltip ────────────────────────────────────────────────────
        if self._pin_idx is not None and lo <= self._pin_idx <= hi:
            self._draw_pin_tooltip(cv, self._pin_idx, vx, vy, lo, hi, W, H,
                                   PL, PR, PT, ch)

        # ── Time axis ─────────────────────────────────────────────────────────
        if self._timestamps:
            ts_lo = self._timestamps[lo] if lo < len(self._timestamps) else 0
            ts_hi = self._timestamps[min(hi, len(self._timestamps) - 1)]
            if ts_lo and ts_hi and ts_hi > ts_lo:
                fmt = "%H:%M" if (ts_hi - ts_lo) < 86400 else "%d/%m %H:%M"
                for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
                    ts_v = ts_lo + (ts_hi - ts_lo) * frac
                    ax   = PL + frac * cw
                    anch = ("w" if frac == 0.0 else "e" if frac == 1.0 else "center")
                    cv.create_text(ax, H - 5,
                                   text=datetime.fromtimestamp(ts_v).strftime(fmt),
                                   fill=_C["text"], font=(_MONO, 5), anchor=anch)

    def _draw_bars(self, cv, W, H, n, lo, hi, PL, PR, PT, ch) -> None:
        """Bar-mode rendering: overlapping vertical bars (CPU → RAM → GPU, last on top).
        Newest bar grows in via ease-out cubic animation."""
        bottom_y = PT + ch

        def vy(v: float) -> float:
            return PT + ch * (1.0 - max(0.0, min(100.0, v)) / 100.0)

        def vx(idx: float) -> float:
            frac = (idx - self._view_lo) / max(self._view_hi - self._view_lo, 1)
            return PL + frac * (W - PL - self._PR)

        # Grid lines at 25 / 50 / 75 / 100 %
        for pct in (25, 50, 75, 100):
            y = vy(pct)
            cv.create_line(PL, y, W - self._PR, y, fill=_C["grid"], width=1)
            cv.create_text(PL - 4, y, text=str(pct), fill=_C["text"],
                           font=(_MONO, 5), anchor="e")

        visible_n = hi - lo + 1
        slot_px   = (W - PL - self._PR) / max(visible_n, 1)
        bar_half  = max(1.5, slot_px * 0.43)
        newest    = n - 1
        ease      = self._bar_anim_ease

        # Draw each series in order: first series deepest, last on top
        for s in self._series:
            vals = s.get("values", [])
            col  = s.get("color", "#3b82f6")
            for i in range(lo, min(hi + 1, len(vals))):
                v = vals[i]
                if v is None:
                    continue
                # Apply ease-out growth animation on the newest bar only
                if i == newest and ease < 1.0:
                    v = v * ease
                bar_top = vy(v)
                if bar_top >= bottom_y:
                    continue
                x_c = vx(i)
                cv.create_rectangle(
                    x_c - bar_half, bar_top,
                    x_c + bar_half, bottom_y,
                    fill=col, outline="",
                )

        # Pinned tooltip (reuses existing helper with adapted coords)
        if self._pin_idx is not None and lo <= self._pin_idx <= hi:
            self._draw_pin_tooltip(cv, self._pin_idx, vx, vy, lo, hi,
                                   W, H, PL, self._PR, PT, ch)

        # Time axis
        if self._timestamps:
            ts_lo = self._timestamps[lo] if lo < len(self._timestamps) else 0
            ts_hi = self._timestamps[min(hi, len(self._timestamps) - 1)]
            if ts_lo and ts_hi and ts_hi > ts_lo:
                fmt = "%H:%M" if (ts_hi - ts_lo) < 86400 else "%d/%m %H:%M"
                for frac_t in (0.0, 0.25, 0.5, 0.75, 1.0):
                    ts_v = ts_lo + (ts_hi - ts_lo) * frac_t
                    ax   = PL + frac_t * (W - PL - self._PR)
                    anch = "w" if frac_t == 0.0 else ("e" if frac_t == 1.0 else "center")
                    cv.create_text(ax, H - 5,
                                   text=datetime.fromtimestamp(ts_v).strftime(fmt),
                                   fill=_C["text"], font=(_MONO, 5), anchor=anch)

    def _draw_pin_tooltip(self, cv, idx, vx, vy, lo, hi, W, H, PL, PR, PT, ch):
        px = vx(idx)
        # Vertical anchor line
        cv.create_line(px, PT, px, PT + ch,
                       fill="#334155", width=1, dash=(2, 2))

        lines: list[tuple[str, str]] = []

        # Timestamp
        if idx < len(self._timestamps) and self._timestamps[idx]:
            ts_str = datetime.fromtimestamp(
                self._timestamps[idx]).strftime("%d/%m  %H:%M:%S")
            lines.append(("#64748b", ts_str))

        # Series values + dots
        for s in self._series:
            vals  = s.get("values", [])
            col   = s.get("color", "#3b82f6")
            label = s.get("label", "")
            if idx < len(vals) and vals[idx] is not None:
                v  = vals[idx]
                py = vy(v)
                cv.create_oval(px - 4, py - 4, px + 4, py + 4,
                               fill=col, outline="#ffffff", width=1)
                lines.append((col, f"{label}: {v:.2f}"))

        # Baseline context
        if self._baseline and lines:
            first_v = None
            for s in self._series:
                vals = s.get("values", [])
                if idx < len(vals) and vals[idx] is not None:
                    first_v = vals[idx]
                    break
            if first_v is not None:
                bl   = self._baseline
                diff = first_v - bl["mean"]
                pct  = abs(diff / bl["mean"] * 100) if bl["mean"] else 0
                dir_ = "▲" if diff >= 0 else "▼"
                col  = "#f59e0b" if pct > 10 else "#64748b"
                lines.append((col, f"{dir_} {pct:.0f}% vs learned baseline"))

        # Anomaly reason
        for anom in self._anomalies:
            if anom.get("idx") == idx:
                sev    = anom.get("severity", "warning")
                reason = anom.get("reason", "")
                atype  = anom.get("type", "")
                col    = _SEV_COL.get(sev, "#f59e0b")
                if atype:
                    lines.append((col, f"[{atype}]  {reason}" if reason else f"[{atype}]"))
                elif reason:
                    lines.append((col, f"⚠ {reason}"))

        if not lines:
            return

        # Render tooltip box
        char_w = 5
        max_len = max(len(t) for _, t in lines)
        TW = max_len * char_w + 20
        TH = len(lines) * 15 + 12

        tx = min(px + 14, W - PR - TW - 6)
        ty = max(PT + 4, PT + ch // 2 - TH // 2)
        if ty + TH > PT + ch - 4:
            ty = PT + ch - TH - 8

        # Shadow
        cv.create_rectangle(tx - 2, ty - 2, tx + TW + 2, ty + TH + 2,
                             fill="#020406", outline="")
        # Background
        cv.create_rectangle(tx - 3, ty - 3, tx + TW, ty + TH,
                             fill=_C["pin_bg"], outline=_C["pin_bd"])

        for j, (col, text) in enumerate(lines):
            cv.create_text(tx, ty + j * 15 + 7,
                           text=text, fill=col,
                           font=(_MONO, 6), anchor="w")

    def _draw_minimap(self) -> None:
        mm = self._mm_cv
        mm.delete("all")
        W  = mm.winfo_width() or 400
        H  = 18
        n  = self._n()
        if n < 2:
            return

        all_vals = [
            v for s in self._series
            for v in s.get("values", []) if v is not None
        ]
        if not all_vals:
            return

        ylo = min(all_vals)
        yhi = max(all_vals)
        if yhi == ylo:
            yhi = ylo + 1

        def mmy(v):
            return 2 + (H - 4) * (1.0 - (v - ylo) / (yhi - ylo))

        def mmx(i):
            return int(i / max(n - 1, 1) * W)

        for s in self._series:
            vals = s.get("values", [])
            col  = s.get("color", _C["mm_sel"])
            pts  = []
            for i, v in enumerate(vals):
                if v is not None:
                    pts += [mmx(i), mmy(v)]
            if len(pts) >= 4:
                mm.create_line(pts, fill=col, width=1)

        # Selection overlay
        x_lo = max(0,     int(self._view_lo / max(n - 1, 1) * W))
        x_hi = min(W - 1, int(self._view_hi / max(n - 1, 1) * W))
        mm.create_rectangle(0, 0, x_lo, H,
                             fill="#010204", outline="", stipple="gray25")
        mm.create_rectangle(x_hi, 0, W, H,
                             fill="#010204", outline="", stipple="gray25")
        mm.create_rectangle(x_lo, 1, x_hi, H - 1,
                             fill="", outline=_C["mm_sel"], width=2)

    def _update_zoom_label(self) -> None:
        n    = self._n()
        span = max(1.0, self._view_hi - self._view_lo + 1)
        if n > 0 and span < n - 1:
            pct = int(span / n * 100)
            self._zoom_lbl.config(text=f"{100 / (span / n):.1f}× zoom  ·  {pct}% visible")
        else:
            self._zoom_lbl.config(text="")

    # ── Event bindings ────────────────────────────────────────────────────────

    def _bind_events(self) -> None:
        cv = self.canvas
        cv.bind("<ButtonPress-1>",   self._on_press)
        cv.bind("<B1-Motion>",       self._on_drag)
        cv.bind("<ButtonRelease-1>", self._on_release)
        cv.bind("<Double-Button-1>", self._on_double)
        cv.bind("<MouseWheel>",      self._on_scroll)
        cv.bind("<Motion>",          self._on_motion)
        cv.bind("<Leave>",           self._on_leave)
        cv.bind("<Configure>",       lambda e: self._redraw())
        cv.bind("<Key-Escape>",      lambda e: self._unpin())

        if self._mm_cv:
            self._mm_cv.bind("<ButtonPress-1>",   self._on_mm_press)
            self._mm_cv.bind("<B1-Motion>",       self._on_mm_drag)
            self._mm_cv.bind("<ButtonRelease-1>", lambda e: setattr(self, "_mm_drag", False))
            self._mm_cv.bind("<Configure>",       lambda e: self._draw_minimap())

    def _on_press(self, e: tk.Event) -> None:
        self._drag_x     = e.x
        self._drag_moved = False

    def _on_drag(self, e: tk.Event) -> None:
        if self._drag_x is None:
            return
        delta_px = self._drag_x - e.x
        if abs(delta_px) > 2:
            self._drag_moved = True
        self._drag_x = e.x
        W  = self.canvas.winfo_width() or 400
        cw = W - self._PL - self._PR
        span  = max(self._view_hi - self._view_lo, 1)
        shift = delta_px / max(cw, 1) * span
        self._view_lo += shift
        self._view_hi += shift
        self._clamp()
        self._pin_idx = None
        self._redraw()

    def _on_release(self, e: tk.Event) -> None:
        if not self._drag_moved:
            self._click_pin(e.x, e.y)
        self._drag_x     = None
        self._drag_moved = False

    def _on_double(self, e: tk.Event) -> None:
        self.reset_view()

    def _on_scroll(self, e: tk.Event) -> None:
        n = self._n()
        if n < 2:
            return
        W  = self.canvas.winfo_width() or 400
        PL, PR = self._PL, self._PR
        cw = W - PL - PR
        span = max(self._view_hi - self._view_lo, 1)
        frac = max(0.0, min(1.0, (e.x - PL) / max(cw, 1)))
        pivot = self._view_lo + frac * span
        factor = 0.75 if e.delta > 0 else (1.0 / 0.75)
        new_span = max(4.0, min(float(n - 1), span * factor))
        self._view_lo = pivot - frac * new_span
        self._view_hi = pivot + (1 - frac) * new_span
        self._clamp()
        self._pin_idx = None
        self._redraw()

    def _on_motion(self, e: tk.Event) -> None:
        if self._pin_idx is not None:
            return
        self._redraw()
        self._draw_crosshair(e.x, e.y)

    def _on_leave(self, e: tk.Event) -> None:
        if self._pin_idx is None:
            self._redraw()

    def _on_mm_press(self, e: tk.Event) -> None:
        self._mm_drag = True
        self._mm_jump(e.x)

    def _on_mm_drag(self, e: tk.Event) -> None:
        if self._mm_drag:
            self._mm_jump(e.x)

    def _mm_jump(self, mx: int) -> None:
        n    = self._n()
        W    = self._mm_cv.winfo_width() or 400
        frac = max(0.0, min(1.0, mx / max(W, 1)))
        ctr  = frac * max(n - 1, 1)
        span = self._view_hi - self._view_lo
        self._view_lo = ctr - span / 2
        self._view_hi = ctr + span / 2
        self._clamp()
        self._redraw()

    # ── Crosshair ─────────────────────────────────────────────────────────────

    def _draw_crosshair(self, mx: int, my: int) -> None:
        cv = self.canvas
        W  = cv.winfo_width() or 400
        H  = self._height
        PL, PR, PT, PB = self._PL, self._PR, self._PT, self._PB
        cw = W - PL - PR
        ch = H - PT - PB

        if not (PL <= mx <= W - PR and PT <= my <= PT + ch):
            return

        frac = (mx - PL) / max(cw, 1)
        idx  = int(self._view_lo + frac * (self._view_hi - self._view_lo))
        n    = self._n()
        idx  = max(0, min(n - 1, idx))

        # Crosshair lines
        cv.create_line(mx, PT, mx, PT + ch,
                       fill=_C["cross"], width=1, dash=(3, 3))
        if not self._bar_mode:
            cv.create_line(PL, my, W - PR, my,
                           fill=_C["cross"], width=1, dash=(3, 3))

        # Live bubble
        parts = []
        for s in self._series:
            vals  = s.get("values", [])
            col   = s.get("color", "#3b82f6")
            label = s.get("label", "")
            if idx < len(vals) and vals[idx] is not None:
                v = vals[idx]
                parts.append(f"{label}: {int(round(v))}%" if self._bar_mode
                             else f"{label}: {v:.2f}")

        if not parts:
            return

        tip = "  ".join(parts)
        if idx < len(self._timestamps) and self._timestamps[idx]:
            tip = datetime.fromtimestamp(
                self._timestamps[idx]).strftime("%H:%M:%S") + "  " + tip

        TW = len(tip) * 5 + 16
        tx = min(mx + 10, W - PR - TW - 4)
        ty = max(PT + 3, my - 18)

        cv.create_rectangle(tx - 2, ty - 2, tx + TW, ty + 14,
                             fill=_C["pin_bg"], outline=_C["pin_bd"])
        cv.create_text(tx, ty + 5, text=tip,
                       fill=_C["pin_fg"], font=(_MONO, 6), anchor="w")

    # ── Pin ───────────────────────────────────────────────────────────────────

    def _click_pin(self, mx: int, my: int) -> None:
        W  = self.canvas.winfo_width() or 400
        PL, PR = self._PL, self._PR
        cw = W - PL - PR
        if not (PL <= mx <= W - PR):
            self._unpin()
            return
        frac = (mx - PL) / max(cw, 1)
        idx  = int(self._view_lo + frac * (self._view_hi - self._view_lo))
        n    = self._n()
        idx  = max(0, min(n - 1, idx))
        if self._pin_idx == idx:
            self._unpin()
        else:
            self._pin_idx = idx
        self._redraw()

    def _unpin(self) -> None:
        self._pin_idx = None
        self._redraw()
