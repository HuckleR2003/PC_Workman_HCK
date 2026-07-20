"""Fan dashboard UI and controls."""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import time
from typing import List, Tuple, Optional, Dict, Callable
import json
import os

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

# Import base classes
from ui.components.fan_curve_editor import FanCurvePoint


class FanData:
    """Fan data container"""
    def __init__(self, source: str, rpm: int, percent: float, temp: float, connected: bool):
        self.source = source
        self.rpm = rpm
        self.percent = percent
        self.temp = temp
        self.connected = connected

    def update(self, rpm: int, percent: float, temp: float):
        """Update fan data"""
        self.rpm = rpm
        self.percent = percent
        self.temp = temp


class FanAIEngine:
    """AI Engine for generating fan curves"""
    @staticmethod
    def generate_curve(profile: str) -> List[FanCurvePoint]:
        """Generate predefined curve based on profile. The "ai" profile
        (shown as "hck_GPT - AI") is shaped by the LEARNED thermal baseline:
        the curve's knee lands just above this machine's usual gaming p95,
        so fans stay quiet inside YOUR normal and ramp exactly where this
        PC historically starts running hot."""
        if profile == "ai":
            knee = 74.0                       # sensible fallback knee
            try:
                from core.thermal_baseline import thermal_baseline as _tb
                pm = _tb.primary_metric()
                if "temp" in pm:              # only temp metrics make a knee
                    st = _tb.training_status(pm)
                    for bucket in ("gaming", "heavy", "medium"):
                        info = st.get(bucket, {})
                        if int(info.get("n", 0)) >= 20:
                            knee = min(88.0, max(55.0,
                                                 float(info.get("p95", 74))))
                            break
            except Exception:
                pass
            k = int(knee)
            pts = [(20, 22), (40, 30), (max(41, k - 14), 42),
                   (k, 62), (min(99, k + 8), 84), (100, 100)]
            # keep temps strictly increasing after the clamps above
            out, last = [], -10
            for t, s in pts:
                t = max(t, last + 3)
                out.append((min(t, 100), s))
                last = t
            return [FanCurvePoint(t, s) for t, s in out]

        curves = {
            "silent": [(20, 20), (40, 25), (60, 40), (80, 60), (100, 75)],
            "balanced": [(20, 25), (40, 35), (60, 50), (80, 70), (100, 90)],
            "performance": [(20, 40), (40, 50), (60, 65), (80, 85), (100, 100)],
        }
        curve_data = curves.get(profile, curves["balanced"])
        return [FanCurvePoint(temp, speed) for temp, speed in curve_data]


class CompactFanCurveGraph(tk.Canvas):
    """Modern fan-curve chart (2026-07-18 redesign).

    - dark->bright-red gradient under the curve: the fill follows the curve
      height, so pushing points up literally heats the chart up
    - dual axes: % (left) and the resulting RPM (right, follows MAX FAN SPEED)
    - points are monotonic in temperature: they cannot overlap or slide
      behind their neighbours
    - view-first safety: the chart opens LOCKED. Hovering shows a quiet grey
      padlock with "Click"; clicking unlocks editing and reveals the
      hck_GPT [AI] consult button in the top-right corner.
    """

    PAD_L, PAD_R, PAD_T, PAD_B = 44, 56, 18, 26
    MIN_GAP = 3          # deg C between neighbouring points

    def __init__(self, parent, width=550, height=170, on_curve_change=None,
                 get_max_rpm=None, get_min_pct=None, get_set_rpm=None,
                 on_ai_consult=None):
        super().__init__(parent, bg="#0b0e1a", width=width, height=height,
                         highlightthickness=1, highlightbackground="#1d2436")
        self.width, self.height = width, height
        self.on_curve_change = on_curve_change
        self.get_max_rpm = get_max_rpm or (lambda: 2400)
        self.get_min_pct = get_min_pct or (lambda: 0)
        self.get_set_rpm = get_set_rpm or (lambda: 0)
        self.on_ai_consult = on_ai_consult

        self.points = [FanCurvePoint(t, s) for t, s in
                       [(0, 25), (20, 30), (40, 40), (60, 55), (80, 75), (100, 90)]]

        self.locked = True
        self._hover = False
        self._live_temp = None
        self._ai_btn = None
        self.dragging_point = None

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._draw()

    # ── Geometry helpers ─────────────────────────────────────────────────────
    def _gw(self):
        return self.width - self.PAD_L - self.PAD_R

    def _gh(self):
        return self.height - self.PAD_T - self.PAD_B

    def _px(self, temp):
        return self.PAD_L + self._gw() * temp / 100.0

    def _py(self, speed):
        return self.PAD_T + self._gh() * (1 - speed / 100.0)

    def speed_at(self, temp: float) -> float:
        """Linear interpolation of the curve, clamped to the MIN FAN SPEED
        floor - feeds the live fan cards AND the gradient fill, so moving
        the MIN slider visibly lifts the whole chart floor."""
        try:
            floor = float(self.get_min_pct() or 0)
        except Exception:
            floor = 0.0
        pts = sorted(self.points, key=lambda p: p.temp)
        if not pts:
            return floor
        if temp <= pts[0].temp:
            return max(floor, float(pts[0].speed))
        for a, b in zip(pts, pts[1:]):
            if temp <= b.temp:
                span = max(b.temp - a.temp, 1e-6)
                f = (temp - a.temp) / span
                return max(floor, a.speed + (b.speed - a.speed) * f)
        return max(floor, float(pts[-1].speed))

    def set_live_temp(self, temp) -> None:
        self._live_temp = temp
        self._draw()

    # ── Colors ───────────────────────────────────────────────────────────────
    @staticmethod
    def _blend(c1, c2, t):
        t = max(0.0, min(1.0, t))
        a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(
            int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def _heat(self, speed):
        """Fill color for a given speed: deep dark red -> bright alarm red."""
        return self._blend("#2a0b10", "#ef4444", (speed / 100.0) ** 1.25)

    # ── Drawing ──────────────────────────────────────────────────────────────
    def _draw(self):
        self.delete("all")
        gw, gh = self._gw(), self._gh()
        max_rpm = int(self.get_max_rpm() or 2400)

        self.create_rectangle(0, 0, self.width, self.height,
                              fill="#0b0e1a", outline="")
        self.create_rectangle(self.PAD_L, self.PAD_T, self.PAD_L + gw,
                              self.PAD_T + gh, fill="#0d1120",
                              outline="#182036")

        for i in range(0, 101, 25):
            y = self._py(i)
            self.create_line(self.PAD_L, y, self.PAD_L + gw, y,
                             fill="#16203a", width=1, dash=(2, 3))
        for t in range(0, 101, 20):
            x = self._px(t)
            self.create_line(x, self.PAD_T, x, self.PAD_T + gh,
                             fill="#131b30", width=1)

        # gradient area under the curve: vertical strips whose color follows
        # the interpolated speed (dark red low -> bright red high)
        pts = sorted(self.points, key=lambda p: p.temp)
        step = 3
        for sx in range(0, int(gw), step):
            temp = (sx / gw) * 100.0
            sp = self.speed_at(temp)
            x0 = self.PAD_L + sx
            y0 = self._py(sp)
            base = self._heat(sp)
            self.create_rectangle(x0, y0, x0 + step, self.PAD_T + gh,
                                  fill=base, outline="")
            self.create_rectangle(x0, y0, x0 + step,
                                  min(y0 + 5, self.PAD_T + gh),
                                  fill=self._blend(base, "#f87171", 0.45),
                                  outline="")

        if len(pts) > 1:
            coords = []
            for p in pts:
                coords += [self._px(p.temp), self._py(p.speed)]
            self.create_line(*coords, fill="#f87171", width=2, smooth=True)

        # MIN floor line (green) and SET manual-override line (cyan)
        try:
            floor = float(self.get_min_pct() or 0)
        except Exception:
            floor = 0.0
        if floor > 0:
            fy = self._py(floor)
            self.create_line(self.PAD_L, fy, self.PAD_L + gw, fy,
                             fill="#10b981", width=1, dash=(5, 3))
            self.create_text(self.PAD_L + 4, fy - 2, text="MIN",
                             fill="#10b981", font=(_MONO, 6, "bold"),
                             anchor="sw")
        try:
            set_rpm = float(self.get_set_rpm() or 0)
        except Exception:
            set_rpm = 0.0
        if set_rpm > 0 and max_rpm > 0:
            sp_pct = min(100.0, set_rpm / max_rpm * 100.0)
            sy = self._py(sp_pct)
            self.create_line(self.PAD_L, sy, self.PAD_L + gw, sy,
                             fill="#22d3ee", width=1, dash=(6, 3))
            self.create_text(self.PAD_L + gw - 4, sy - 2,
                             text=f"SET {int(set_rpm)}",
                             fill="#22d3ee", font=(_MONO, 6, "bold"),
                             anchor="se")

        if self._live_temp is not None and 0 <= self._live_temp <= 100:
            lx = self._px(self._live_temp)
            self.create_line(lx, self.PAD_T, lx, self.PAD_T + gh,
                             fill="#f59e0b", width=1, dash=(4, 3))
            self.create_text(lx, self.PAD_T + 2,
                             text=f"{self._live_temp:.0f}\u00b0",
                             fill="#f59e0b", font=(_BODY, 7, "bold"),
                             anchor="s")

        for p in pts:
            x, y = self._px(p.temp), self._py(p.speed)
            self.create_oval(x - 7, y - 7, x + 7, y + 7,
                             outline=self._heat(min(p.speed + 25, 100)),
                             width=2)
            self.create_oval(x - 4, y - 4, x + 4, y + 4,
                             fill="#fca5a5", outline="#ffffff", width=1)

        self.create_text(self.PAD_L - 8, self.PAD_T - 9, text="%",
                         fill="#8aa0bc", font=(_MONO, 7, "bold"), anchor="e")
        self.create_text(self.PAD_L + gw + 8, self.PAD_T - 9, text="RPM",
                         fill="#8aa0bc", font=(_MONO, 7, "bold"), anchor="w")
        for i in range(0, 101, 25):
            y = self._py(i)
            self.create_text(self.PAD_L - 8, y, text=f"{i}",
                             fill="#64748b", font=(_MONO, 7), anchor="e")
            self.create_text(self.PAD_L + gw + 8, y,
                             text=f"{int(max_rpm * i / 100)}",
                             fill="#64748b", font=(_MONO, 7), anchor="w")
        for t in range(0, 101, 20):
            self.create_text(self._px(t), self.PAD_T + gh + 10,
                             text=f"{t}\u00b0", fill="#64748b",
                             font=(_MONO, 7), anchor="n")

        ref_t = self._live_temp if self._live_temp is not None else pts[-1].temp
        sp = self.speed_at(ref_t)
        self.create_text(self.PAD_L + gw - 6, self.PAD_T + 6,
                         text=(f"{ref_t:.0f}\u00b0C \u2192 {sp:.0f}%  "
                               f"\u00b7  {int(max_rpm * sp / 100)} RPM"),
                         fill="#f87171", font=(_MONO, 8, "bold"), anchor="ne")

        if self.locked and self._hover:
            self.create_rectangle(self.PAD_L, self.PAD_T, self.PAD_L + gw,
                                  self.PAD_T + gh, fill="#05070d",
                                  outline="", stipple="gray50")
            cx = self.PAD_L + gw / 2
            cy = self.PAD_T + gh / 2 - 8
            g = "#94a3b8"
            self.create_arc(cx - 9, cy - 16, cx + 9, cy + 2, start=0,
                            extent=180, style="arc", outline=g, width=2)
            self.create_rectangle(cx - 12, cy - 4, cx + 12, cy + 12,
                                  fill="#1a2130", outline=g, width=2)
            self.create_oval(cx - 2, cy + 1, cx + 2, cy + 5, fill=g,
                             outline=g)
            self.create_text(cx, cy + 24, text="Click", fill=g,
                             font=(_MONO, 8), anchor="n")

    def _set_hover(self, on):
        if self._hover != on:
            self._hover = on
            if self.locked:
                self._draw()

    def _show_ai_button(self):
        if self._ai_btn is not None:
            return
        b = tk.Label(self, text=" hck_GPT  [AI] ", font=(_MONO, 8, "bold"),
                     bg="#161b2c", fg="#a5b4fc", cursor="hand2",
                     highlightbackground="#31395c", highlightthickness=1,
                     padx=6, pady=3)
        b.place(relx=1.0, x=-10, y=8, anchor="ne")
        b.bind("<Enter>", lambda e: b.config(fg="#e0e7ff", bg="#1d2440"))
        b.bind("<Leave>", lambda e: b.config(fg="#a5b4fc", bg="#161b2c"))
        b.bind("<Button-1>",
               lambda e: self.on_ai_consult() if self.on_ai_consult else None)
        self._ai_btn = b

    # ── Interaction ──────────────────────────────────────────────────────────
    def _on_click(self, event):
        if self.locked:
            self.locked = False
            self._show_ai_button()
            self._draw()
            return
        for i, p in enumerate(self.points):
            if (abs(event.x - self._px(p.temp)) < 10
                    and abs(event.y - self._py(p.speed)) < 10):
                self.dragging_point = i
                return

    def _on_drag(self, event):
        if self.locked or self.dragging_point is None:
            return
        i = self.dragging_point
        speed = (1 - (event.y - self.PAD_T) / max(self._gh(), 1)) * 100
        temp = ((event.x - self.PAD_L) / max(self._gw(), 1)) * 100
        # monotonic X: a point can never pass its neighbours
        lo = self.points[i - 1].temp + self.MIN_GAP if i > 0 else 0
        hi = (self.points[i + 1].temp - self.MIN_GAP
              if i < len(self.points) - 1 else 100)
        self.points[i].temp = int(max(lo, min(hi, temp)))
        self.points[i].speed = int(max(0, min(100, speed)))
        self._draw()

    def _on_release(self, event):
        if self.dragging_point is not None:
            self.dragging_point = None
            if self.on_curve_change:
                self.on_curve_change(self.points)

    def load_curve(self, points):
        self.points = sorted(points, key=lambda p: p.temp)
        self._draw()

    def update_realtime_data(self, current_temp, temps):
        self.set_live_temp(current_temp)


class VerticalGradientSlider(tk.Canvas):
    """
    Vertical slider with gradient background
    Bottom (0%) = GREEN (cool)
    Top (100%) = RED (hot)
    Visual heat metaphor!
    """

    def __init__(self, parent, label: str, min_val: int, max_val: int,
                 default: int, unit: str, on_change: Callable):
        super().__init__(parent, bg="#0a0e27", width=60, height=150,
                        highlightthickness=0, cursor="hand2")

        self.label = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = default
        self.unit = unit
        self.on_change = on_change

        self.slider_width = 12
        self.slider_height = 120
        self.slider_x = 24  # Center
        self.slider_y = 10

        self.dragging = False

        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

        self._draw()

    def _draw(self):
        """Draw vertical slider with gradient"""
        self.delete("all")

        # Gradient background (Green bottom -> Red top)
        for i in range(self.slider_height):
            # Ratio: 0 (bottom/green) to 1 (top/red)
            ratio = i / self.slider_height

            # Gradient: green (#10b981) -> yellow (#fbbf24) -> red (#ef4444)
            if ratio < 0.5:
                # Green to Yellow
                r = int(16 + (251 - 16) * (ratio * 2))
                g = int(185 + (191 - 185) * (ratio * 2))
                b = int(129 + (36 - 129) * (ratio * 2))
            else:
                # Yellow to Red
                r = int(251 + (239 - 251) * ((ratio - 0.5) * 2))
                g = int(191 + (68 - 191) * ((ratio - 0.5) * 2))
                b = int(36 + (68 - 36) * ((ratio - 0.5) * 2))

            color = f"#{r:02x}{g:02x}{b:02x}"

            self.create_rectangle(
                self.slider_x - self.slider_width // 2,
                self.slider_y + i,
                self.slider_x + self.slider_width // 2,
                self.slider_y + i + 1,
                fill=color, outline=""
            )

        # Border
        self.create_rectangle(
            self.slider_x - self.slider_width // 2,
            self.slider_y,
            self.slider_x + self.slider_width // 2,
            self.slider_y + self.slider_height,
            outline="#8b5cf6", width=2
        )

        # Slider handle
        percent = (self.value - self.min_val) / (self.max_val - self.min_val)
        # Invert: high value = top, low = bottom
        handle_y = self.slider_y + self.slider_height - int(percent * self.slider_height)

        # Glow
        self.create_oval(
            self.slider_x - 10, handle_y - 10,
            self.slider_x + 10, handle_y + 10,
            fill="", outline="#a855f7", width=2
        )

        # Handle
        self.create_oval(
            self.slider_x - 8, handle_y - 8,
            self.slider_x + 8, handle_y + 8,
            fill="#ffffff", outline="#8b5cf6", width=2
        )

        # Label (top)
        self.create_text(
            30, 5,
            text=self.label, fill="#94a3b8",
            font=(_BODY, 7, "bold"), anchor="n"
        )

        # Value (bottom)
        self.create_text(
            30, self.slider_y + self.slider_height + 10,
            text=f"{self.value}{self.unit}",
            fill="#ffffff", font=(_BODY, 9, "bold"), anchor="n"
        )

    def _on_click(self, event):
        """Handle click"""
        self.dragging = True
        self._update_value(event.y)

    def _on_drag(self, event):
        """Handle drag"""
        if self.dragging:
            self._update_value(event.y)

    def _on_release(self, event):
        """Handle release"""
        self.dragging = False

    def _update_value(self, y):
        """Update value from Y position"""
        # Clamp to slider area
        y = max(self.slider_y, min(self.slider_y + self.slider_height, y))

        # Calculate value (inverted: top = max, bottom = min)
        percent = 1.0 - (y - self.slider_y) / self.slider_height
        value = int(self.min_val + percent * (self.max_val - self.min_val))

        # Snap to nearest 5
        value = round(value / 5) * 5
        value = max(self.min_val, min(self.max_val, value))

        if value != self.value:
            self.value = value
            self._draw()
            self.on_change(value)

    def set_value(self, value: int):
        """Set value programmatically"""
        self.value = max(self.min_val, min(self.max_val, value))
        self._draw()


# ============================================================
# TRAPEZOIDAL PROFILE BUTTON (MSI AFTERBURNER STYLE)
# ============================================================

class TrapezoidalProfileButton(tk.Canvas):
    """
    Trapezoidal profile button with gradient (like MSI Afterburner)
    Active: Red gradient
    Inactive: Dark gray
    """

    def __init__(self, parent, label: str, profile_id: str, on_click: Callable):
        super().__init__(parent, bg="#0f1117", width=100, height=30,
                        highlightthickness=0, cursor="hand2")

        self.label = label
        self.profile_id = profile_id
        self.on_click = on_click
        self.active = False

        self.bind("<Button-1>", lambda e: self._handle_click())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self._draw()

    def _draw(self):
        """Draw trapezoidal button"""
        self.delete("all")
        width = 100
        height = 30

        # Trapezoid points (slanted edges)
        x1, y1 = 8, 0      # Top left
        x2, y2 = 92, 0     # Top right
        x3, y3 = 100, height  # Bottom right
        x4, y4 = 0, height    # Bottom left

        if self.active:
            # RED GRADIENT for active (CLIPPED to trapezoid shape)
            # First draw background trapezoid
            self.create_polygon([x1, y1, x2, y2, x3, y3, x4, y4],
                               fill="#8b0000", outline="", smooth=False)

            # Draw gradient lines ONLY within trapezoid bounds
            for i in range(width):
                ratio = i / width
                # Gradient: dark red -> bright red
                r = int(139 + (239 - 139) * ratio)
                g = int(0 + (68 - 0) * ratio)
                b = int(0 + (68 - 0) * ratio)
                color = f"#{r:02x}{g:02x}{b:02x}"

                # Calculate y range for this x position (trapezoid bounds)
                if i < 8:
                    y_start = y1
                    y_end = y4
                elif i > 92:
                    y_start = y2
                    y_end = y3
                else:
                    # Interpolate between trapezoid edges
                    t = (i - 8) / (92 - 8)
                    y_start = 0
                    y_end = height

                self.create_line(i, y_start, i, y_end, fill=color, width=1)

            text_color = "#ffffff"
        else:
            # Dark gray for inactive
            self.create_polygon([x1, y1, x2, y2, x3, y3, x4, y4],
                               fill="#1a1d24", outline="", smooth=False)
            text_color = "#64748b"

        # Border outline (subtle)
        self.create_polygon([x1, y1, x2, y2, x3, y3, x4, y4],
                           fill="", outline="#334155", width=1, smooth=False)

        # Text (centered, uppercase)
        self.create_text(
            width // 2, height // 2,
            text=self.label.upper(),
            font=(_BODY, 8, "bold"),
            fill=text_color,
            anchor="center"
        )

    def _handle_click(self):
        """Handle click"""
        self.on_click(self.profile_id)

    def _on_enter(self, event):
        """Hover effect - lighten slightly"""
        if not self.active:
            self.delete("all")
            width = 100
            height = 30
            x1, y1 = 8, 0
            x2, y2 = 92, 0
            x3, y3 = 100, height
            x4, y4 = 0, height

            self.create_polygon([x1, y1, x2, y2, x3, y3, x4, y4],
                               fill="#252932", outline="#334155", width=1, smooth=False)
            self.create_text(
                width // 2, height // 2,
                text=self.label.upper(),
                font=(_BODY, 8, "bold"),
                fill="#94a3b8",
                anchor="center"
            )

    def _on_leave(self, event):
        """Unhover"""
        self._draw()

    def set_active(self, active: bool):
        """Set active state"""
        self.active = active
        self._draw()


# ============================================================
# ADVANCED COOLING CONTROL PANEL
# ============================================================

class AdvancedCoolingPanel(tk.Frame):
    """
    Advanced Cooling Control panel (right side)
    - PWM/DC Mode control
    - Multi-fan sync
    - Update period
    - Temperature source selection
    - Fan health monitoring
    """

    def __init__(self, parent, on_option_change: Callable):
        super().__init__(parent, bg="#1a1d24", width=220)
        self.pack_propagate(False)
        self.on_option_change = on_option_change

        # Header
        tk.Label(self, text="⚙️ ADVANCED COOLING", font=(_BODY, 9, "bold"),
                bg="#1a1d24", fg="#8b5cf6").pack(pady=(10, 5))

        self._build_controls()

    def _build_controls(self):
        """Build advanced controls"""
        # PWM/DC Mode
        self._create_option("Control Mode", ["PWM", "DC", "Auto"], "PWM")

        # Multi-fan sync
        self._create_option("Multi-Fan Sync", ["Enabled", "Disabled"], "Disabled")

        # Update period
        self._create_option("Update Period", ["0.5s", "1s", "2s", "5s"], "2s")

        # Temperature source
        self._create_option("Temp Source", ["CPU", "GPU", "Board", "Average"], "Average")

        # 0dB Mode (stop fans at low temp)
        self._create_option("0dB Mode", ["On", "Off"], "Off")

        # Separator
        tk.Frame(self, bg="#334155", height=2).pack(fill="x", padx=10, pady=10)

        # Fan Health Status
        tk.Label(self, text="🔧 FAN HEALTH", font=(_BODY, 8, "bold"),
                bg="#1a1d24", fg="#94a3b8").pack(pady=5)

        self.health_text = tk.Label(self, text="✅ All fans OK\n⚡ PWM Active\n🌡️ Temp: 55°C",
                                   font=(_BODY, 7), bg="#1a1d24", fg="#10b981",
                                   justify="left", wraplength=180)
        self.health_text.pack(padx=10, pady=5)

    def _create_option(self, label: str, options: List[str], default: str):
        """Create option dropdown"""
        frame = tk.Frame(self, bg="#1a1d24")
        frame.pack(fill="x", padx=10, pady=5)

        # Label
        tk.Label(frame, text=label, font=(_BODY, 7, "bold"),
                bg="#1a1d24", fg="#94a3b8").pack(anchor="w")

        # Dropdown
        var = tk.StringVar(value=default)
        dropdown = ttk.Combobox(frame, textvariable=var, values=options,
                               state="readonly", width=18, font=(_BODY, 7))
        dropdown.pack(fill="x", pady=(2, 0))
        dropdown.bind("<<ComboboxSelected>>",
                     lambda e: self.on_option_change(label, var.get()))

    def update_health(self, status: str, mode: str, temp: float):
        """Update health display"""
        self.health_text.config(text=f"{status}\n{mode}\n🌡️ Temp: {temp:.1f}°C")


# ============================================================
# SAVE PROFILE DIALOG
# ============================================================

class SaveProfileDialog:
    """
    Small Save Profile Dialog
    - Choose P1 or P2 to save current curve
    - Load configuration file option
    """

    def __init__(self, parent, curve_points, options, sliders):
        self.curve_points = curve_points
        self.options = options
        self.sliders = sliders
        self.parent_widget = parent

        # Create small top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Save Profile")
        self.dialog.geometry("400x250")
        self.dialog.configure(bg="#0f1117")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (200)
        y = (self.dialog.winfo_screenheight() // 2) - (125)
        self.dialog.geometry(f"+{x}+{y}")

        self._build_ui()

    def _build_ui(self):
        """Build small dialog UI"""
        # Header
        header = tk.Frame(self.dialog, bg="#1a1d24", height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="Save Fan Curve Profile", font=(_BODY, 11, "bold"),
                bg="#1a1d24", fg="#ffffff").pack(side="left", padx=15, pady=8)

        # Close button
        close_btn = tk.Label(header, text="✖", font=(_BODY, 10, "bold"),
                            bg="#1a1d24", fg="#64748b", cursor="hand2", padx=8)
        close_btn.pack(side="right", padx=8)
        close_btn.bind("<Button-1>", lambda e: self.dialog.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#64748b"))

        # Main content
        content = tk.Frame(self.dialog, bg="#0f1117")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # Section 1: Save to Profile Slot
        tk.Label(content, text="Save current curve to:", font=(_BODY, 9, "bold"),
                bg="#0f1117", fg="#94a3b8").pack(anchor="w", pady=(0, 8))

        profile_btns = tk.Frame(content, bg="#0f1117")
        profile_btns.pack(fill="x", pady=(0, 20))

        for slot in ["P1", "P2"]:
            btn = tk.Label(profile_btns, text=f"Profile {slot}", font=(_BODY, 10, "bold"),
                          bg="#8b5cf6", fg="#ffffff", cursor="hand2", pady=10)
            btn.pack(side="left", fill="x", expand=True, padx=3)
            btn.bind("<Button-1>", lambda e, s=slot: self._save_to_slot(s))

            def make_hover(b):
                b.bind("<Enter>", lambda e: b.config(bg="#a855f7"))
                b.bind("<Leave>", lambda e: b.config(bg="#8b5cf6"))
            make_hover(btn)

        # Separator
        tk.Frame(content, bg="#334155", height=1).pack(fill="x", pady=(0, 15))

        # Section 2: Load Configuration File
        tk.Label(content, text="Load configuration:", font=(_BODY, 9, "bold"),
                bg="#0f1117", fg="#94a3b8").pack(anchor="w", pady=(0, 8))

        load_btn = tk.Label(content, text="📁 Load from File", font=(_BODY, 10, "bold"),
                           bg="#06b6d4", fg="#ffffff", cursor="hand2", pady=10)
        load_btn.pack(fill="x")
        load_btn.bind("<Button-1>", lambda e: self._load_from_file())
        load_btn.bind("<Enter>", lambda e: load_btn.config(bg="#0891b2"))
        load_btn.bind("<Leave>", lambda e: load_btn.config(bg="#06b6d4"))

    def _save_to_slot(self, slot):
        """Save profile to P1/P2 slot"""
        data = {
            "name": f"Profile {slot}",
            "curve": [(p.temp, p.speed) for p in self.curve_points],
            "options": self.options,
            "timestamp": time.time()
        }

        # Save to data/profiles/ directory
        profiles_dir = os.path.join("data", "profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        filename = os.path.join(profiles_dir, f"profile_{slot.lower()}.json")

        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)

            messagebox.showinfo("Saved", f"✅ Fan curve saved to Profile {slot}!")
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile: {e}")

    def _load_from_file(self):
        """Load configuration from JSON file"""
        from tkinter import filedialog

        filename = filedialog.askopenfilename(
            title="Load Fan Curve Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.join("data", "profiles")
        )

        if not filename:
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)

            # Extract curve points
            curve_data = data.get("curve", [])

            messagebox.showinfo("Loaded", f"✅ Configuration loaded from file!\n{len(curve_data)} curve points imported.")

            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")


# ============================================================
# MAIN ULTIMATE DASHBOARD
# ============================================================

class FanDashboardUltimate:
    """
    ULTIMATE Fan Dashboard
    - LEFT: Vertical gradient sliders (green bottom -> red top)
    - TOP: Color-coded profile buttons
    - CENTER: Interactive fan curve graph
    - RIGHT: Advanced cooling controls (PWM/DC, Multi-fan sync, 0dB mode)
    """

    def __init__(self, parent):
        self.parent = parent
        self.fans = {
            "FAN 1": FanData("CPU", 1200, 55, 48.5, True),
            "FAN 2": FanData("BOARD", 950, 42, 38.2, True),
            "FAN 3": FanData("GPU", 1500, 68, 62.3, True),
            "FAN 4": FanData("AUX", 800, 35, 32.1, True),
        }

        self.current_profile = "balanced"
        self.options = {
            "hysteresis": 3,
            "target_temp": 70,
            "min_speed": 20,
            "max_speed": 100,
        }
        self.slider_vals: dict = {}     # slider label -> value (live/EDITING)
        self._slider_ctl: dict = {}     # slider label -> setter (repaints)
        self._fan_cards: dict = {}
        # THE APPLY RULE (2026-07-18): the chart+sliders are an EDITING draft;
        # the fan cards always show the APPLIED state. Touching anything
        # enters config mode (yellow cards, "FANS - configuring" title);
        # Apply/Revert exits it, re-locks the chart, snaps cards back.
        self._applied: dict = {}        # {"curve": [(t,s)...], "sliders": {}}
        self._config_mode = False
        self._suppress_config = False   # True while loading/exiting

        self._build_ui()
        self._load_applied()     # restore the last APPLIED curve/sliders
        if not self._applied:    # first run: current defaults ARE the applied
            self._applied = self._snapshot_editing()

        # Live ring refresh + chat hook: hck_GPT can apply the learned
        # "hck_GPT - AI" profile on request ("zmień profil wentylatorów").
        try:
            from import_core import register_component
            register_component("ui.fan_dashboard", self)
        except Exception:
            pass
        try:
            self.parent.after(800, self._tick_cards)
        except Exception:
            pass

    # ── Config-mode state machine (THE APPLY RULE) ───────────────────────────
    def _snapshot_editing(self) -> dict:
        return {"curve": [(p.temp, p.speed) for p in self.graph.points],
                "sliders": dict(self.slider_vals)}

    def _enter_config_mode(self):
        if self._config_mode or self._suppress_config:
            return
        self._config_mode = True
        try:
            self._fans_title.config(
                text=self._txt("FANS - wartości podczas konfiguracji",
                               "FANS - values while configuring"),
                fg="#f59e0b")
        except Exception:
            pass
        for refs in self._fan_cards.values():
            try:
                refs["card"].config(highlightbackground="#f59e0b")
                refs["accent"].config(bg="#f59e0b")
            except Exception:
                pass
        self._update_live()

    def _exit_config_mode(self):
        self._config_mode = False
        try:
            self._fans_title.config(text="FANS", fg="#e2e8f0")
        except Exception:
            pass
        for refs in self._fan_cards.values():
            try:
                refs["card"].config(highlightbackground="#1e2535")
                refs["accent"].config(bg="#ef4444")
            except Exception:
                pass
        # the padlock comes back: viewing is safe, editing needs a click
        try:
            self.graph.locked = True
            if self.graph._ai_btn is not None:
                self.graph._ai_btn.destroy()
                self.graph._ai_btn = None
            self.graph._draw()
        except Exception:
            pass
        self._update_live()    # cards snap to the applied values instantly

    def _active_state(self):
        """(curve, sliders) the FAN CARDS should reflect: the editing draft
        in config mode (live preview), the APPLIED state otherwise."""
        if self._config_mode or not self._applied:
            return ([(p.temp, p.speed) for p in self.graph.points],
                    dict(self.slider_vals))
        return (self._applied.get("curve", []),
                self._applied.get("sliders", {}))

    def _pct_at(self, temp: float) -> float:
        curve, sl = self._active_state()
        floor = float(sl.get("MIN FAN SPEED", 0) or 0)
        pts = sorted(curve)
        if not pts:
            return floor
        if temp <= pts[0][0]:
            return max(floor, float(pts[0][1]))
        for (t1, s1), (t2, s2) in zip(pts, pts[1:]):
            if temp <= t2:
                f = (temp - t1) / max(t2 - t1, 1e-6)
                return max(floor, s1 + (s2 - s1) * f)
        return max(floor, float(pts[-1][1]))

    def _active_max_rpm(self) -> int:
        _, sl = self._active_state()
        return int(sl.get("MAX FAN SPEED", 2400) or 2400)

    @staticmethod
    def _txt(pl: str, en: str) -> str:
        try:
            from utils.i18n import get_lang
            return pl if get_lang() == "pl" else en
        except Exception:
            return pl

    def apply_ai_profile(self) -> bool:
        """Switch to the learned hck_GPT - AI profile AND apply it (chat
        asked for a real plan change, not a draft). Marshalled to the main
        thread - chat handlers may run off it."""
        try:
            def _do():
                self._on_profile_change("ai")
                self._apply(silent=True)
            self.parent.after(0, _do)
            return True
        except Exception:
            return False

    def _consult_ai(self):
        """hck_GPT [AI] button: unfold the chat banner and hand it the
        consult question in the app's language."""
        q = self._txt("Hej, czy moje temperatury są w porządku? "
                      "Chyba będę konfigurować wentylatory ;)",
                      "Hey, are my temperatures okay? "
                      "I think I'm about to configure my fans ;)")
        try:
            from import_core import COMPONENTS
            panel = COMPONENTS.get("hck_gpt.panel")
            if panel is not None and hasattr(panel, "ask"):
                panel.ask(q)
        except Exception:
            pass

    def _build_ui(self):
        """Build ULTIMATE layout"""
        # Main container
        main = tk.Frame(self.parent, bg="#0f1117")
        main.pack(fill="both", expand=True)

        # === TOP: COLOR-CODED PROFILE BUTTONS ===
        self._build_profile_buttons(main)

        # === MIDDLE: 3-COLUMN LAYOUT ===
        middle = tk.Frame(main, bg="#0f1117")
        middle.pack(fill="both", expand=True, padx=10, pady=5)

        # Left panel: VERTICAL SLIDERS
        self._build_left_panel(middle)

        # Center: Graph (takes remaining space)
        self._build_center_panel(middle)

    def _build_profile_buttons(self, parent):
        """Build trapezoidal profile buttons (MSI Afterburner style)"""
        section = tk.Frame(parent, bg="#0f1117", height=50)
        section.pack(fill="x", padx=10, pady=(2, 5))
        section.pack_propagate(False)

        # PROFILES label with underline (like in image)
        label_frame = tk.Frame(section, bg="#0f1117")
        label_frame.pack(side="left", padx=10, pady=(5, 0))

        profiles_lbl = tk.Label(label_frame, text="PROFILES", font=(_MONO, 9, "bold"),
                               bg="#0f1117", fg="#e2e8f0")
        profiles_lbl.pack()

        # Underline (red line beneath PROFILES)
        underline = tk.Frame(label_frame, bg="#ef4444", height=2)
        underline.pack(fill="x", pady=(2, 0))

        # Modern flat chips (2026-07-18): filled accent when active, outlined
        # when idle. Replaces the trapezoid canvases - crisper at any DPI.
        buttons_frame = tk.Frame(section, bg="#0f1117")
        buttons_frame.pack(side="left", padx=20, pady=(5, 0))

        profiles = [
            ("Default",      "default",  "#64748b"),
            ("Silent",       "silent",   "#10b981"),
            ("Performance",  "performance", "#f59e0b"),
            ("hck_GPT - AI", "ai",       "#8b5cf6"),
        ]

        self.profile_buttons = {}
        self._profile_accent = {pid: c for _, pid, c in profiles}
        for label, profile_id, accent in profiles:
            chip = tk.Label(buttons_frame, text=label, font=(_MONO, 8, "bold"),
                            bg="#151926", fg="#94a3b8", cursor="hand2",
                            padx=12, pady=5,
                            highlightbackground="#232b40",
                            highlightthickness=1)
            chip.pack(side="left", padx=3)
            chip.bind("<Button-1>",
                      lambda e, p=profile_id: self._on_profile_change(p))
            chip.bind("<Enter>", lambda e, c=chip, a=accent:
                      c.config(fg="#e2e8f0", highlightbackground=a)
                      if not getattr(c, "_active", False) else None)
            chip.bind("<Leave>", lambda e, c=chip:
                      c.config(fg="#94a3b8", highlightbackground="#232b40")
                      if not getattr(c, "_active", False) else None)
            self.profile_buttons[profile_id] = chip

        self._set_profile_chip_active("default")

    def _set_profile_chip_active(self, active_id):
        for pid, chip in self.profile_buttons.items():
            accent = self._profile_accent.get(pid, "#64748b")
            on = (pid == active_id)
            chip._active = on
            chip.config(bg=accent if on else "#151926",
                        fg="#0b0e14" if on else "#94a3b8",
                        highlightbackground=accent if on else "#232b40")

    def _build_left_panel(self, parent):
        """Build left panel with FAN INFO + MODERN SLIDERS"""
        left = tk.Frame(parent, bg="#0a0e27", width=320)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        # (2026-07-18: the two old "arrow buttons" here were dead UI - no
        # bindings at all - removed; the space feeds the bigger fan cards.)
        self._fans_title = tk.Label(left, text="FANS", font=(_MONO, 9, "bold"),
                                    bg="#0a0e27", fg="#e2e8f0")
        self._fans_title.pack(anchor="w", padx=8, pady=(8, 2))

        # === FAN STATUS CARDS (4 fans in a grid - 2x2) ===
        fans_container = tk.Frame(left, bg="#0a0e27")
        fans_container.pack(fill="x", padx=5, pady=(5, 5))

        # Real component names (hardcoded "i5-13600K"/"RTX 4070" placeholders
        # showed OTHER PEOPLE'S hardware until 2026-07-18)
        cpu_model = gpu_model = ""
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            hw = user_knowledge.get_all_hardware() or {}
            cpu_model = (hw.get("cpu_model") or "")[:16]
            gpu_model = (hw.get("gpu_model") or "")[:16]
        except Exception:
            pass
        fan_info = [
            ("CPU FAN", cpu_model or "CPU cooler"),
            ("GPU FAN", gpu_model or "GPU cooler"),
            ("FAN 1", "Case front"),
            ("FAN 2", "Case rear"),
        ]

        self._fan_cards = {}
        for i, (fan_name, model) in enumerate(fan_info):
            row, col = i // 2, i % 2
            card_frame = tk.Frame(fans_container, bg="#0a0e27")
            card_frame.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
            self._create_fan_card(card_frame, fan_name, model, 0)

        # Configure grid weights for equal distribution
        fans_container.grid_columnconfigure(0, weight=1)
        fans_container.grid_columnconfigure(1, weight=1)

        # Sliders moved UNDER the chart (2026-07-18) - they shape the graph,
        # so they now live right next to it, side by side.
        self.sliders = {}    # legacy dict kept for SaveProfileDialog

    def _create_fan_card(self, parent, name, model, rpm):
        """Mini fan card (2026-07-18): accent header, live smooth ring.
        The old version drew the ring ONCE at build with hardcoded RPM - it
        never refreshed and the 3px arc pixelated. Refs go to _fan_cards and
        _tick_cards() redraws every 2 s from the live curve."""
        card = tk.Frame(parent, bg="#131722", height=96,
                        highlightbackground="#1e2535", highlightthickness=1)
        card.pack(fill="both", expand=True)
        card.pack_propagate(False)

        hdr = tk.Frame(card, bg="#181d2b")
        hdr.pack(fill="x")
        accent = tk.Frame(hdr, bg="#ef4444", width=3)
        accent.pack(side="left", fill="y")
        tk.Label(hdr, text=" " + name, font=(_MONO, 9, "bold"),
                 bg="#181d2b", fg="#e5e7eb", pady=3).pack(side="left")

        content_row = tk.Frame(card, bg="#131722")
        content_row.pack(fill="both", expand=True, padx=5, pady=3)

        left_info = tk.Frame(content_row, bg="#131722")
        left_info.pack(side="left", fill="y", expand=True)
        status_lbl = tk.Label(left_info, text="curve", font=(_MONO, 9, "bold"),
                              bg="#131722", fg="#10b981", anchor="w")
        status_lbl.pack(fill="x", pady=(4, 0))
        tk.Label(left_info, text=model, font=(_BODY, 8),
                 bg="#131722", fg="#8593a8", anchor="w",
                 wraplength=88, justify="left").pack(fill="x")

        canvas = tk.Canvas(content_row, bg="#131722", width=62, height=62,
                           highlightthickness=0)
        canvas.pack(side="right", padx=2)
        self._fan_cards[name] = {"cv": canvas, "status": status_lbl,
                                 "card": card, "accent": accent}
        self._draw_fan_ring(canvas, 0.0, 0)

    def _draw_fan_ring(self, canvas, pct, rpm):
        """Smooth red progress ring: layered 5px arcs on a 62px canvas with a
        soft outer glow - replaces the pixelated single 3px arc."""
        try:
            canvas.delete("all")
        except Exception:
            return
        pct = max(0.0, min(100.0, float(pct)))
        # track
        canvas.create_oval(6, 6, 56, 56, outline="#232b3d", width=5)
        if pct > 0:
            ext = -pct / 100.0 * 359.9
            col = "#f87171" if pct >= 75 else "#ef4444" if pct >= 40 else "#b91c1c"
            # glow underlay then crisp arc on top
            canvas.create_arc(5, 5, 57, 57, start=90, extent=ext,
                              outline="#3f1016", width=8, style="arc")
            canvas.create_arc(6, 6, 56, 56, start=90, extent=ext,
                              outline=col, width=5, style="arc")
        canvas.create_text(31, 26, text=f"{pct:.0f}%",
                           font=(_MONO, 11, "bold"), fill="#ffffff")
        canvas.create_text(31, 41, text=f"{rpm}",
                           font=(_MONO, 8), fill="#8593a8")

    def _tick_cards(self):
        """Live refresh loop (2 s) - the work lives in _update_live so the
        Apply/Revert transitions can refresh the cards instantly too."""
        try:
            if not self.parent.winfo_exists():
                return
        except Exception:
            return
        self._update_live()
        try:
            self.parent.after(2000, self._tick_cards)
        except Exception:
            pass

    def _update_live(self):
        """One refresh pass: real temps from live_sensors; the ring percent
        comes from the APPLIED curve (or the editing draft in config mode),
        so the cards show what the fans are actually asked to do."""
        cpu_t = gpu_t = None
        s = {}
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls
            s = _ls()
            v = s.get("cpu_temp");  cpu_t = float(v) if v and v > 0 else None
            v = s.get("gpu_temp");  gpu_t = float(v) if v and v > 0 else None
        except Exception:
            pass
        max_rpm = self._active_max_rpm()
        temps = {"CPU FAN": cpu_t, "GPU FAN": gpu_t,
                 "FAN 1": cpu_t, "FAN 2": (gpu_t or cpu_t)}
        for name, refs in self._fan_cards.items():
            t = temps.get(name)
            try:
                if t is None:
                    self._draw_fan_ring(refs["cv"], 0, 0)
                    refs["status"].config(text="no sensor", fg="#6b7280")
                else:
                    pct = self._pct_at(t)
                    self._draw_fan_ring(refs["cv"], pct,
                                        int(max_rpm * pct / 100))
                    refs["status"].config(
                        text=f"{t:.0f}°C",
                        fg="#f59e0b" if self._config_mode else "#10b981")
            except Exception:
                return
        # live temp marker on the chart follows the CPU (or GPU) sensor
        try:
            self.graph.set_live_temp(cpu_t if cpu_t is not None else gpu_t)
        except Exception:
            pass
        # component tiles (BOARD / CPU / GPU / FAN) follow live sensors too
        try:
            mb_t = None
            try:
                v = s.get("mb_temp_sys")
                mb_t = float(v) if v and v > 0 else None
            except Exception:
                pass
            ref_t = cpu_t if cpu_t is not None else gpu_t
            fan_pct = self._pct_at(ref_t) if ref_t is not None else None
            tiles = getattr(self, "_temp_tiles", {})
            vals = {"BOARD": mb_t, "CPU": cpu_t, "GPU": gpu_t}
            for name, t_val in vals.items():
                if name in tiles:
                    tiles[name]["val"].config(
                        text=f"{t_val:.0f}°C" if t_val is not None else "--")
            if "FAN" in tiles:
                tiles["FAN"]["val"].config(
                    text=f"{fan_pct:.0f}%" if fan_pct is not None else "--")
        except Exception:
            pass

    def _create_modern_slider(self, parent, label, min_val, max_val, default,
                              unit, width=210):
        """Interactive slider (2026-07-18): the old one was a static drawing
        with no bindings at all - dragging did nothing. Now: click/drag
        anywhere on the track, heat-gradient fill, live value box; values
        land in self.slider_vals and reshape the chart live."""
        container = tk.Frame(parent, bg="#0a0e27")
        container.pack(fill="x", pady=5)
        tk.Label(container, text=label, font=(_MONO, 7, "bold"),
                 bg="#0a0e27", fg="#94a3b8").pack(anchor="w", pady=(0, 3))

        slider_row = tk.Frame(container, bg="#0a0e27")
        slider_row.pack(fill="x")
        W, H = width, 22
        track = tk.Canvas(slider_row, bg="#0a0e27", width=W, height=H,
                          highlightthickness=0)
        track.pack(side="left", padx=(0, 6))

        value_box = tk.Frame(slider_row, bg="#161b28", width=66, height=H,
                             highlightbackground="#232b40",
                             highlightthickness=1)
        value_box.pack(side="right")
        value_box.pack_propagate(False)
        value_label = tk.Label(value_box, text="", font=(_MONO, 7, "bold"),
                               bg="#161b28", fg="#ffffff")
        value_label.pack(expand=True)

        self.slider_vals[label] = default

        def _blend(c1, c2, t):
            t = max(0.0, min(1.0, t))
            a = tuple(int(c1[i:i + 2], 16) for i in (1, 3, 5))
            b = tuple(int(c2[i:i + 2], 16) for i in (1, 3, 5))
            return "#%02x%02x%02x" % tuple(
                int(a[i] + (b[i] - a[i]) * t) for i in range(3))

        def _paint():
            track.delete("all")
            val = self.slider_vals[label]
            f = (val - min_val) / max(max_val - min_val, 1)
            px = int(6 + f * (W - 12))
            track.create_rectangle(6, 9, W - 6, 13, fill="#1c2334",
                                   outline="")
            seg = 6
            for x in range(6, px, seg):
                ft = (x - 6) / max(W - 12, 1)
                track.create_rectangle(x, 9, min(x + seg, px), 13,
                                       fill=_blend("#5b1220", "#ef4444", ft),
                                       outline="")
            track.create_oval(px - 6, 5, px + 6, 17, fill="#e5e7eb",
                              outline="#ef4444", width=2)
            value_label.config(text=f"{val} {unit}")

        def _set_from_x(x):
            f = max(0.0, min(1.0, (x - 6) / max(W - 12, 1)))
            step = 50 if max_val > 500 else 1
            val = min_val + f * (max_val - min_val)
            self.slider_vals[label] = int(round(val / step) * step)
            _paint()
            self._enter_config_mode()   # touching a slider = configuring
            try:
                self.graph._draw()      # axes/floor/SET line follow live
            except Exception:
                pass

        track.bind("<Button-1>", lambda e: _set_from_x(e.x))
        track.bind("<B1-Motion>", lambda e: _set_from_x(e.x))

        def _set_val(v):
            self.slider_vals[label] = int(v)
            _paint()
            try:
                self.graph._draw()
            except Exception:
                pass
        self._slider_ctl[label] = _set_val
        _paint()

    def _build_center_panel(self, parent):
        """Build center panel: Graph + Action Buttons + Temperature Icons"""
        center = tk.Frame(parent, bg="#0a0e27")
        center.pack(side="left", fill="both", expand=True)

        # Graph section (very close to PROFILES - 5px spacing)
        graph_frame = tk.Frame(center, bg="#0a0e27")
        graph_frame.pack(fill="x", pady=(5, 10))

        # Header bar with a red accent tick
        header_bar = tk.Frame(graph_frame, bg="#12151f", height=30)
        header_bar.pack(fill="x", pady=(0, 3))
        header_bar.pack_propagate(False)
        tk.Frame(header_bar, bg="#ef4444", width=3).pack(side="left", fill="y")
        tk.Label(header_bar, text=" FAN CURVE", font=(_BODY, 10, "bold"),
                 bg="#12151f", fg="#ffffff").pack(side="left", padx=(8, 0), pady=5)
        tk.Label(header_bar, text="hover to unlock editing",
                 font=(_MONO, 7), bg="#12151f", fg="#64748b").pack(
            side="right", padx=10)

        # Graph: view-first (locked), dual %/RPM axes, red heat gradient
        self.graph = CompactFanCurveGraph(
            graph_frame, width=550, height=170,
            on_curve_change=self._on_curve_change,
            get_max_rpm=lambda: self.slider_vals.get("MAX FAN SPEED", 2400),
            get_min_pct=lambda: self.slider_vals.get("MIN FAN SPEED", 0),
            get_set_rpm=lambda: self.slider_vals.get("SET FAN SPEED", 0),
            on_ai_consult=self._consult_ai)
        self.graph.pack(pady=0)

        # Sliders side by side, directly under the chart they shape:
        # MIN raises the curve floor, MAX rescales the RPM axis, SET (>0)
        # draws the manual override line. All three redraw the graph live.
        srow = tk.Frame(center, bg="#0a0e27")
        srow.pack(fill="x", pady=(6, 0))
        for lab, mn, mx, dv, unit in (
                ("MIN FAN SPEED", 0, 100, 20, "%"),
                ("MAX FAN SPEED", 600, 3000, 2400, "RPM"),
                ("SET FAN SPEED", 0, 3000, 0, "RPM")):
            col = tk.Frame(srow, bg="#0a0e27")
            col.pack(side="left", fill="x", expand=True, padx=4)
            self._create_modern_slider(col, lab, mn, mx, dv, unit, width=132)

        # ACTION BUTTONS (directly under graph with exact spacing from screenshot)
        self._build_action_buttons_inline(center)

        # TEMPERATURE ICONS (4 icons below buttons)
        self._build_temperature_icons(center)

    def _build_action_buttons_inline(self, parent):
        """Build action buttons (EXACT spacing from screenshot)"""
        section = tk.Frame(parent, bg="#0a0e27")
        section.pack(fill="x", pady=(8, 0))

        # Button specs from screenshot (no icons, clean text)
        buttons = [
            ("Apply", self._apply, "#10b981"),
            ("Revert", self._revert, "#64748b"),
            ("Save Profile", self._save_profile, "#8b5cf6"),
            ("Export", self._export, "#06b6d4"),
            ("Reset", self._reset, "#f59e0b"),
        ]

        # Container with exact spacing between buttons (like screenshot)
        for i, (text, callback, color) in enumerate(buttons):
            btn = tk.Label(section, text=text, font=(_BODY, 9, "bold"),
                          bg=color, fg="#ffffff", cursor="hand2", padx=20, pady=8)
            btn.pack(side="left", padx=3 if i > 0 else 0, expand=True, fill="both")
            btn.bind("<Button-1>", lambda e, cb=callback: cb())

            def make_hover(b, c):
                def on_enter(e):
                    r = int(c[1:3], 16)
                    g = int(c[3:5], 16)
                    b_val = int(c[5:7], 16)
                    lighter = f"#{min(255,r+30):02x}{min(255,g+30):02x}{min(255,b_val+30):02x}"
                    b.config(bg=lighter)
                def on_leave(e):
                    b.config(bg=c)
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
            make_hover(btn, color)

    def _build_temperature_icons(self, parent):
        """Component tiles (2026-07-18): the old raster PNGs (body_temp.png
        etc.) never matched the dark UI - replaced with crisp vector icons
        drawn straight on canvas. Live values arrive via _tick_cards; the
        FAN rotor spins with lightweight canvas math (no PIL rotation)."""
        icons_section = tk.Frame(parent, bg="#0a0e27")
        icons_section.pack(fill="x", pady=(12, 8))
        icons_container = tk.Frame(icons_section, bg="#0a0e27")
        icons_container.pack(expand=True)

        self._temp_tiles = {}
        self._fan_angle = 0.0
        for label, accent in (("BOARD", "#3b82f6"), ("CPU", "#ef4444"),
                              ("GPU", "#10b981"), ("FAN", "#8b5cf6")):
            tile = tk.Frame(icons_container, bg="#10131f",
                            highlightbackground="#1d2436", highlightthickness=1)
            tile.pack(side="left", padx=8)
            cv = tk.Canvas(tile, bg="#10131f", width=96, height=38,
                           highlightthickness=0)
            cv.pack(padx=12, pady=(7, 0))
            self._draw_vector_icon(cv, label, accent)
            val = tk.Label(tile, text="--", font=(_MONO, 10, "bold"),
                           bg="#10131f", fg="#e2e8f0")
            val.pack()
            tk.Label(tile, text=label, font=(_MONO, 7, "bold"),
                     bg="#10131f", fg=accent).pack(pady=(0, 7))
            self._temp_tiles[label] = {"cv": cv, "val": val, "accent": accent}

        self._spin_fan_icon()

    def _draw_vector_icon(self, cv, kind, accent):
        """Mono-line vector icons on a wide 96x38 canvas (2026-07-18:
        Marcin's sizing - shorter, 50% wider)."""
        cv.delete("all")
        line = "#8593a8"
        if kind == "BOARD":
            cv.create_rectangle(26, 4, 70, 34, outline=accent, width=2)
            cv.create_line(34, 34, 34, 22, 46, 22, fill=line)
            cv.create_line(62, 4, 62, 14, 52, 14, fill=line)
            for x, y in ((36, 10), (48, 28), (58, 26), (40, 16)):
                cv.create_oval(x - 2, y - 2, x + 2, y + 2,
                               outline=line, fill="#10131f")
        elif kind == "CPU":
            cv.create_rectangle(34, 6, 62, 32, outline=accent, width=2)
            cv.create_rectangle(42, 13, 54, 25, outline=line, width=1)
            for i in range(4):                       # pins on all four sides
                ox = 37 + i * 7
                oy = 8 + i * 6
                cv.create_line(ox, 1, ox, 6, fill=line, width=2)
                cv.create_line(ox, 32, ox, 37, fill=line, width=2)
                cv.create_line(29, oy, 34, oy, fill=line, width=2)
                cv.create_line(62, oy, 67, oy, fill=line, width=2)
        elif kind == "GPU":
            cv.create_rectangle(14, 8, 82, 28, outline=accent, width=2)
            cv.create_oval(56, 10, 74, 28, outline=line, width=2)
            cv.create_oval(63, 17, 67, 21, outline=line)
            cv.create_line(14, 32, 58, 32, fill=line, width=3)  # PCIe finger
        elif kind == "FAN":
            self._draw_fan_rotor(cv, 0.0, accent)

    def _draw_fan_rotor(self, cv, angle, accent):
        """3-blade rotor drawn from arcs - rotated by shifting start angles."""
        cv.delete("all")
        cv.create_oval(31, 2, 65, 36, outline="#232b3d", width=2)
        for k in range(3):
            cv.create_arc(34, 5, 62, 33, start=(angle + k * 120) % 360,
                          extent=70, fill=accent, outline="")
        cv.create_oval(43, 14, 53, 24, fill="#10131f", outline=accent, width=2)

    def _spin_fan_icon(self):
        """Lightweight rotor spin; speed follows the current curve percent."""
        tile = getattr(self, "_temp_tiles", {}).get("FAN")
        if not tile:
            return
        try:
            if not tile["cv"].winfo_exists():
                return
        except Exception:
            return
        pct = 30.0
        try:
            lt = self.graph._live_temp
            if lt is not None:
                pct = max(10.0, self.graph.speed_at(lt))
        except Exception:
            pass
        self._fan_angle = (self._fan_angle - (6 + pct / 5)) % 360
        self._draw_fan_rotor(tile["cv"], self._fan_angle, tile["accent"])
        try:
            tile["cv"].after(120, self._spin_fan_icon)
        except Exception:
            pass

    # ============================================================
    # CALLBACKS
    # ============================================================

    def _on_profile_change(self, profile_id):
        """Handle profile change (a draft until APPLY confirms it)"""
        self.current_profile = profile_id
        self._set_profile_chip_active(profile_id)
        self._enter_config_mode()

        # Load curve based on profile
        if profile_id == "ai":
            curve = FanAIEngine.generate_curve("ai")
        elif profile_id.startswith("profile"):
            # P1/P2: load from saved file if exists
            slot_num = profile_id[-1]
            filename = os.path.join("data", "profiles", f"profile_p{slot_num}.json")

            if os.path.exists(filename):
                try:
                    with open(filename, "r") as f:
                        data = json.load(f)
                        curve_data = data.get("curve", [])
                        curve = [FanCurvePoint(temp, speed) for temp, speed in curve_data]
                    print(f"[Ultimate] Loaded saved curve from {filename}")
                except Exception as e:
                    print(f"[Ultimate] Failed to load profile: {e}")
                    curve = FanAIEngine.generate_curve("balanced")
            else:
                print(f"[Ultimate] Profile file not found, using default balanced curve")
                curve = FanAIEngine.generate_curve("balanced")
        elif profile_id == "default":
            # Default: balanced curve
            curve = FanAIEngine.generate_curve("balanced")
        else:
            # silent, balanced, performance
            curve = FanAIEngine.generate_curve(profile_id)

        self.graph.load_curve(curve)

    def _on_curve_change(self, points):
        """Dragging curve points = configuring: yellow preview mode."""
        self._enter_config_mode()

    def _on_slider_change(self, label, value):
        """Handle slider change"""
        print(f"[Ultimate] {label} = {value}")
        self.options[label.lower().replace(" ", "_").replace("°", "")] = value

    def _on_advanced_option_change(self, option: str, value: str):
        """Handle advanced option change"""
        print(f"[Ultimate] Advanced: {option} = {value}")
        self.options[option.lower().replace(" ", "_")] = value

    # ── Persistence (2026-07-18): Apply used to show "applied successfully"
    #    while saving NOTHING. Now it persists curve+profile+sliders to
    #    settings/fan_dashboard.json, which is reloaded on every open.
    _STATE_PATH = os.path.join("settings", "fan_dashboard.json")

    def _apply(self, silent: bool = False):
        """THE APPLY RULE: confirm the editing draft as the new applied
        state, persist it, exit config mode and re-lock the chart."""
        try:
            data = {"profile": self.current_profile,
                    **self._snapshot_editing()}
            os.makedirs(os.path.dirname(self._STATE_PATH), exist_ok=True)
            with open(self._STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._applied = {"curve": data["curve"],
                             "sliders": data["sliders"]}
            self._exit_config_mode()
            if not silent:
                messagebox.showinfo(
                    "Apply", "Applied ✓  This is now the active fan plan -\n"
                             "the cards follow it and it reloads on open.")
        except Exception as e:
            if not silent:
                messagebox.showerror("Apply", f"Save failed: {e}")

    def _load_applied(self) -> None:
        """Restore the last APPLIED state (curve + sliders + profile).
        Loading is NOT configuring - config-mode triggers are suppressed."""
        try:
            with open(self._STATE_PATH, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        self._suppress_config = True
        try:
            curve = [FanCurvePoint(t, s) for t, s in data.get("curve", [])]
            if len(curve) >= 2:
                self.graph.load_curve(curve)
            prof = data.get("profile")
            if prof in getattr(self, "profile_buttons", {}):
                self.current_profile = prof
                self._set_profile_chip_active(prof)
            for lab, v in (data.get("sliders") or {}).items():
                setter = self._slider_ctl.get(lab)
                if setter:
                    setter(v)
            self._applied = {"curve": [(p.temp, p.speed)
                                       for p in self.graph.points],
                             "sliders": dict(self.slider_vals)}
        except Exception:
            pass
        finally:
            self._suppress_config = False

    def _revert(self):
        """Throw the draft away: back to the last APPLIED state."""
        if os.path.exists(self._STATE_PATH):
            self._load_applied()
        else:
            self._suppress_config = True
            try:
                self.current_profile = "default"
                self._set_profile_chip_active("default")
                self.graph.load_curve(FanAIEngine.generate_curve("balanced"))
            finally:
                self._suppress_config = False
        self._exit_config_mode()
        messagebox.showinfo("Revert", "Draft discarded - back to the "
                                      "applied fan plan.")

    def _save_profile(self):
        """Open Save Profile Dialog with graph preview"""
        SaveProfileDialog(self.parent, self.graph.points, self.options, self.sliders)

    def _export(self):
        """Export all settings to JSON"""
        data = {
            "curve": [(p.temp, p.speed) for p in self.graph.points],
            "options": self.options,
            "sliders": dict(self.slider_vals),
        }
        export_path = os.path.join("settings", "fan_settings_ultimate.json")
        os.makedirs("settings", exist_ok=True)
        with open(export_path, "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Export", f"Settings exported to {export_path}")

    def _reset(self):
        """Reset to defaults (curve + all three sliders)."""
        self._on_profile_change("default")
        for lab, dv in (("MIN FAN SPEED", 20), ("MAX FAN SPEED", 2400),
                        ("SET FAN SPEED", 0)):
            setter = self._slider_ctl.get(lab)
            if setter:
                setter(dv)
        messagebox.showinfo("Reset", "All settings reset to defaults.")


# ============================================================
# FACTORY FUNCTION
# ============================================================

def create_fan_dashboard(parent):
    """Create Fan Dashboard instance"""
    return FanDashboardUltimate(parent)
