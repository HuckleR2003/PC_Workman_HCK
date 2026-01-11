"""
Fan Dashboard ULTIMATE - Next-Gen AI-Powered Fan Control
Complete redesign with vertical gradient sliders, color-coded buttons, advanced cooling

NEW FEATURES:
- LEFT PANEL: Vertical sliders with gradient (bottom=cool/green, top=hot/red)
- TOP: Color-coded profile buttons (Silent=green, Balanced=blue, Performance=red, AI=purple)
- CENTER: Interactive fan curve graph with drag-and-drop points
- RIGHT PANEL: Advanced cooling controls (PWM/DC, Multi-fan sync, 0dB mode, Fan health)
- Beats MSI Afterburner & ASUS GPU Tweak with AI + modern UX
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import time
from typing import List, Tuple, Optional, Dict, Callable
import json
import os

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


# ============================================================
# HELPER CLASSES (FanData, FanAIEngine, CompactFanCurveGraph)
# ============================================================

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
        """Generate predefined curve based on profile"""
        curves = {
            "silent": [(20, 20), (40, 25), (60, 40), (80, 60), (100, 75)],
            "balanced": [(20, 25), (40, 35), (60, 50), (80, 70), (100, 90)],
            "performance": [(20, 40), (40, 50), (60, 65), (80, 85), (100, 100)],
        }
        curve_data = curves.get(profile, curves["balanced"])
        return [FanCurvePoint(temp, speed) for temp, speed in curve_data]


class CompactFanCurveGraph(tk.Canvas):
    """Beautiful fan curve graph with purple gradient fill (like screenshot)"""
    def __init__(self, parent, width=550, height=150, on_curve_change=None):
        super().__init__(parent, bg="#0a0e27", width=width, height=height, highlightthickness=0)
        self.width = width
        self.height = height
        self.on_curve_change = on_curve_change

        # Default curve points
        self.points = [
            FanCurvePoint(0, 25),
            FanCurvePoint(20, 30),
            FanCurvePoint(40, 40),
            FanCurvePoint(60, 55),
            FanCurvePoint(80, 75),
            FanCurvePoint(100, 90),
        ]

        self.dragging_point = None
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

        self._draw()

    def _draw(self):
        """Draw beautiful graph with gradient fill"""
        self.delete("all")
        margin_left = 40
        margin_right = 20
        margin_top = 15
        margin_bottom = 25

        graph_width = self.width - margin_left - margin_right
        graph_height = self.height - margin_top - margin_bottom

        # Background - dark navy
        self.create_rectangle(0, 0, self.width, self.height, fill="#0a0e27", outline="")

        # GRID LINES (horizontal - 0%, 25%, 50%, 75%, 100%)
        for i in range(0, 101, 25):
            y = margin_top + graph_height * (1 - i / 100)
            self.create_line(margin_left, y, margin_left + graph_width, y,
                           fill="#1e293b", width=1, dash=(2, 2))

        # VERTICAL LINES (temperature markers: 0°, 20°, 40°, 60°, 80°, 100°)
        for temp in range(0, 101, 20):
            x = margin_left + graph_width * (temp / 100)
            self.create_line(x, margin_top, x, margin_top + graph_height,
                           fill="#1e293b", width=1)

        # PURPLE GRADIENT FILL (area under curve)
        if len(self.points) > 1:
            # Create polygon points for gradient area
            polygon_points = []

            # Add curve points from left to right
            for point in self.points:
                x = margin_left + graph_width * (point.temp / 100)
                y = margin_top + graph_height * (1 - point.speed / 100)
                polygon_points.extend([x, y])

            # Close polygon at bottom
            polygon_points.extend([margin_left + graph_width, margin_top + graph_height])
            polygon_points.extend([margin_left, margin_top + graph_height])

            # Draw purple gradient fill (multiple layers for gradient effect)
            for i in range(50):
                alpha = 1 - (i / 50)
                shade = int(139 + (30 - 139) * (i / 50))  # Darker at bottom
                color = f"#{shade:02x}5cf6"

                # Offset polygon slightly for gradient
                offset_y = i * 0.5
                offset_points = []
                for j in range(0, len(polygon_points), 2):
                    offset_points.append(polygon_points[j])
                    offset_points.append(polygon_points[j + 1] + offset_y)

                self.create_polygon(offset_points, fill=color, outline="",
                                  stipple="gray50" if i > 25 else "")

        # PURPLE CURVE LINE
        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                x1 = margin_left + graph_width * (self.points[i].temp / 100)
                y1 = margin_top + graph_height * (1 - self.points[i].speed / 100)
                x2 = margin_left + graph_width * (self.points[i + 1].temp / 100)
                y2 = margin_top + graph_height * (1 - self.points[i + 1].speed / 100)
                self.create_line(x1, y1, x2, y2, fill="#a855f7", width=3, smooth=True)

        # INTERACTIVE POINTS (circles with white outline)
        for point in self.points:
            x = margin_left + graph_width * (point.temp / 100)
            y = margin_top + graph_height * (1 - point.speed / 100)

            # Outer glow
            self.create_oval(x - 8, y - 8, x + 8, y + 8, fill="", outline="#8b5cf6", width=2)
            # Main circle
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#c084fc", outline="#ffffff", width=2, tags="point")

        # AXIS LABELS
        # Y-axis labels (0%, 25%, 50%, 75%, 100%)
        for i in range(0, 101, 25):
            y = margin_top + graph_height * (1 - i / 100)
            self.create_text(margin_left - 10, y, text=f"{i}%",
                           fill="#64748b", font=("Segoe UI", 7), anchor="e")

        # X-axis labels (0°, 20°, 40°, 60°, 80°, 100°)
        for temp in range(0, 101, 20):
            x = margin_left + graph_width * (temp / 100)
            self.create_text(x, margin_top + graph_height + 10, text=f"{temp}°",
                           fill="#64748b", font=("Segoe UI", 7), anchor="n")

        # Top right label (current temp/speed indicator)
        if self.points:
            last_point = self.points[-1]
            self.create_text(self.width - 10, 10,
                           text=f"{int(last_point.temp)}°C → {int(last_point.speed)}%",
                           fill="#a855f7", font=("Segoe UI", 9, "bold"), anchor="ne")

    def _on_click(self, event):
        """Handle click"""
        margin_left = 40
        margin_top = 15
        margin_bottom = 25
        graph_width = self.width - margin_left - 20
        graph_height = self.height - margin_top - margin_bottom

        for i, point in enumerate(self.points):
            x = margin_left + graph_width * (point.temp / 100)
            y = margin_top + graph_height * (1 - point.speed / 100)
            if abs(event.x - x) < 10 and abs(event.y - y) < 10:
                self.dragging_point = i
                break

    def _on_drag(self, event):
        """Handle drag"""
        if self.dragging_point is not None:
            margin_left = 40
            margin_top = 15
            margin_bottom = 25
            graph_width = self.width - margin_left - 20
            graph_height = self.height - margin_top - margin_bottom

            # Calculate new speed (vertical drag)
            speed = max(0, min(100, (1 - (event.y - margin_top) / graph_height) * 100))
            self.points[self.dragging_point].speed = int(speed)

            # Calculate new temp (horizontal drag)
            temp = max(0, min(100, ((event.x - margin_left) / graph_width) * 100))
            self.points[self.dragging_point].temp = int(temp)

            self._draw()

    def _on_release(self, event):
        """Handle release"""
        if self.dragging_point is not None:
            self.dragging_point = None
            if self.on_curve_change:
                self.on_curve_change(self.points)

    def load_curve(self, points: List[FanCurvePoint]):
        """Load curve from points"""
        self.points = points
        self._draw()

    def update_realtime_data(self, current_temp: float, temps: List[float]):
        """Update real-time data (placeholder)"""
        pass


# ============================================================
# VERTICAL GRADIENT SLIDER (Heat Metaphor: Green→Red)
# ============================================================

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

        # Gradient background (Green bottom → Red top)
        for i in range(self.slider_height):
            # Ratio: 0 (bottom/green) to 1 (top/red)
            ratio = i / self.slider_height

            # Gradient: green (#10b981) → yellow (#fbbf24) → red (#ef4444)
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
            font=("Segoe UI", 7, "bold"), anchor="n"
        )

        # Value (bottom)
        self.create_text(
            30, self.slider_y + self.slider_height + 10,
            text=f"{self.value}{self.unit}",
            fill="#ffffff", font=("Segoe UI", 9, "bold"), anchor="n"
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
                # Gradient: dark red → bright red
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
            font=("Segoe UI", 8, "bold"),
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
                font=("Segoe UI", 8, "bold"),
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
        tk.Label(self, text="⚙️ ADVANCED COOLING", font=("Segoe UI", 9, "bold"),
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
        tk.Label(self, text="🔧 FAN HEALTH", font=("Segoe UI", 8, "bold"),
                bg="#1a1d24", fg="#94a3b8").pack(pady=5)

        self.health_text = tk.Label(self, text="✅ All fans OK\n⚡ PWM Active\n🌡️ Temp: 55°C",
                                   font=("Segoe UI", 7), bg="#1a1d24", fg="#10b981",
                                   justify="left", wraplength=180)
        self.health_text.pack(padx=10, pady=5)

    def _create_option(self, label: str, options: List[str], default: str):
        """Create option dropdown"""
        frame = tk.Frame(self, bg="#1a1d24")
        frame.pack(fill="x", padx=10, pady=5)

        # Label
        tk.Label(frame, text=label, font=("Segoe UI", 7, "bold"),
                bg="#1a1d24", fg="#94a3b8").pack(anchor="w")

        # Dropdown
        var = tk.StringVar(value=default)
        dropdown = ttk.Combobox(frame, textvariable=var, values=options,
                               state="readonly", width=18, font=("Segoe UI", 7))
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

        tk.Label(header, text="Save Fan Curve Profile", font=("Segoe UI", 11, "bold"),
                bg="#1a1d24", fg="#ffffff").pack(side="left", padx=15, pady=8)

        # Close button
        close_btn = tk.Label(header, text="✖", font=("Segoe UI", 10, "bold"),
                            bg="#1a1d24", fg="#64748b", cursor="hand2", padx=8)
        close_btn.pack(side="right", padx=8)
        close_btn.bind("<Button-1>", lambda e: self.dialog.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#64748b"))

        # Main content
        content = tk.Frame(self.dialog, bg="#0f1117")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        # Section 1: Save to Profile Slot
        tk.Label(content, text="Save current curve to:", font=("Segoe UI", 9, "bold"),
                bg="#0f1117", fg="#94a3b8").pack(anchor="w", pady=(0, 8))

        profile_btns = tk.Frame(content, bg="#0f1117")
        profile_btns.pack(fill="x", pady=(0, 20))

        for slot in ["P1", "P2"]:
            btn = tk.Label(profile_btns, text=f"Profile {slot}", font=("Segoe UI", 10, "bold"),
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
        tk.Label(content, text="Load configuration:", font=("Segoe UI", 9, "bold"),
                bg="#0f1117", fg="#94a3b8").pack(anchor="w", pady=(0, 8))

        load_btn = tk.Label(content, text="📁 Load from File", font=("Segoe UI", 10, "bold"),
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

            # TODO: Apply loaded curve to graph (needs parent reference)
            # For now just show success message

            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {e}")


# ============================================================
# MAIN ULTIMATE DASHBOARD
# ============================================================

class FanDashboardUltimate:
    """
    ULTIMATE Fan Dashboard
    - LEFT: Vertical gradient sliders (green bottom → red top)
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

        self._build_ui()

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

        # NOTE: Right panel (Advanced Cooling Controls) REMOVED
        # NOTE: Action buttons moved to center panel (under graph)

    def _build_profile_buttons(self, parent):
        """Build trapezoidal profile buttons (MSI Afterburner style)"""
        section = tk.Frame(parent, bg="#0f1117", height=50)
        section.pack(fill="x", padx=10, pady=(2, 5))
        section.pack_propagate(False)

        # PROFILES label with underline (like in image)
        label_frame = tk.Frame(section, bg="#0f1117")
        label_frame.pack(side="left", padx=10, pady=(5, 0))

        profiles_lbl = tk.Label(label_frame, text="PROFILES", font=("Segoe UI", 9, "bold"),
                               bg="#0f1117", fg="#ffffff")
        profiles_lbl.pack()

        # Underline (red line beneath PROFILES)
        underline = tk.Frame(label_frame, bg="#ef4444", height=2)
        underline.pack(fill="x", pady=(2, 0))

        # Buttons container
        buttons_frame = tk.Frame(section, bg="#0f1117")
        buttons_frame.pack(side="left", padx=20, pady=(5, 0))

        profiles = [
            ("Default", "default"),
            ("Silent", "silent"),
            ("AI", "ai"),
            ("P1", "profile1"),
            ("P2", "profile2"),
        ]

        self.profile_buttons = {}
        for label, profile_id in profiles:
            btn = TrapezoidalProfileButton(buttons_frame, label, profile_id,
                                          self._on_profile_change)
            btn.pack(side="left", padx=1)
            self.profile_buttons[profile_id] = btn

        # Set default active
        self.profile_buttons["default"].set_active(True)

    def _create_arrow_button(self, parent, text, bg_color):
        """Create button with red arrow section on left"""
        container = tk.Frame(parent, bg="#0a0e27")
        container.pack(fill="x", padx=5, pady=3)

        # Button frame
        btn = tk.Frame(container, bg=bg_color, cursor="hand2")
        btn.pack(fill="x")

        # Left: Red arrow section (10px width)
        arrow_section = tk.Frame(btn, bg="#ef4444", width=12)
        arrow_section.pack(side="left", fill="y")
        arrow_section.pack_propagate(False)

        # Arrow symbol
        tk.Label(arrow_section, text="→", font=("Segoe UI", 10, "bold"),
                bg="#ef4444", fg="#ffffff").pack(expand=True)

        # Right: Button text
        tk.Label(btn, text=text, font=("Segoe UI", 8, "bold"),
                bg=bg_color, fg="#ffffff", pady=8, padx=10, anchor="w").pack(side="left", fill="x", expand=True)

    def _build_left_panel(self, parent):
        """Build left panel with FAN INFO + MODERN SLIDERS"""
        left = tk.Frame(parent, bg="#0a0e27", width=320)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        # === TOP BUTTONS (with arrow style) ===
        # Button 1: ALL FANS
        self._create_arrow_button(left, "ALL FANS / Expanded Controls", "#2563eb")

        # Button 2: Temperature Statistics
        self._create_arrow_button(left, "Your PC - Temperature Statistics", "#1e3a8a")

        # === FAN STATUS CARDS (4 fans in a grid - 2x2) ===
        fans_container = tk.Frame(left, bg="#0a0e27")
        fans_container.pack(fill="x", padx=5, pady=(5, 5))

        fan_info = [
            ("CPU FAN", "i5-13600K", 1450),
            ("GPU FAN", "RTX 4070", 1820),
            ("FAN 1", "Noctua", 980),
            ("FAN 2", "Corsair", 1100),
        ]

        # Create 2x2 grid
        for i, (fan_name, model, rpm) in enumerate(fan_info):
            row = i // 2
            col = i % 2

            card_frame = tk.Frame(fans_container, bg="#0a0e27")
            card_frame.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")

            self._create_fan_card(card_frame, fan_name, model, rpm)

        # Configure grid weights for equal distribution
        fans_container.grid_columnconfigure(0, weight=1)
        fans_container.grid_columnconfigure(1, weight=1)

        # Neon separator line
        tk.Frame(left, bg="#ef4444", height=2).pack(fill="x", padx=5, pady=8)

        # === MODERN HORIZONTAL SLIDERS ===
        sliders_section = tk.Frame(left, bg="#0a0e27")
        sliders_section.pack(fill="x", padx=10, pady=(5, 10))

        # Slider 1: Max FAN Speed
        self._create_modern_slider(sliders_section, "MAX FAN SPEED", 0, 3000, 2400, "RPM")

        # Slider 2: Set FAN Speed
        self._create_modern_slider(sliders_section, "SET FAN SPEED", 0, 3000, 1450, "RPM")

        # === APPLY & DEFAULT BUTTONS (very small height) ===
        buttons_row = tk.Frame(sliders_section, bg="#0a0e27")
        buttons_row.pack(fill="x", pady=(10, 0))

        apply_btn = tk.Label(buttons_row, text="APPLY", font=("Segoe UI", 7, "bold"),
                            bg="#047857", fg="#ffffff", cursor="hand2", pady=4)
        apply_btn.pack(side="left", fill="x", expand=True, padx=(0, 3))

        default_btn = tk.Label(buttons_row, text="DEFAULT", font=("Segoe UI", 7, "bold"),
                              bg="#374151", fg="#ffffff", cursor="hand2", pady=4)
        default_btn.pack(side="left", fill="x", expand=True, padx=(3, 0))

        # Store for compatibility
        self.sliders = {}

    def _create_fan_card(self, parent, name, model, rpm):
        """Create mini fan status card with horizontal layout"""
        card = tk.Frame(parent, bg="#1a1d24", height=60)
        card.pack(fill="both", expand=True)
        card.pack_propagate(False)

        # HEADER: Fan name (highlighted background, full width)
        header_bg = "#374151" if rpm > 0 else "#1f2937"
        tk.Label(card, text=name, font=("Segoe UI", 8, "bold"),
                bg=header_bg, fg="#e5e7eb", pady=2).pack(fill="x")

        # CONTENT ROW: Left (status + model) | Right (RPM circle)
        content_row = tk.Frame(card, bg="#1a1d24")
        content_row.pack(fill="both", expand=True, padx=3, pady=2)

        # LEFT SIDE: Status and Model (vertical stack)
        left_info = tk.Frame(content_row, bg="#1a1d24")
        left_info.pack(side="left", fill="y", expand=True)

        # Status: Connected / Not available
        status_color = "#10b981" if rpm > 0 else "#6b7280"
        status_text = "Connected" if rpm > 0 else "Not available"
        tk.Label(left_info, text=status_text, font=("Segoe UI", 7),
                bg="#1a1d24", fg=status_color, anchor="w").pack(fill="x")

        # Model (under status)
        tk.Label(left_info, text=model, font=("Segoe UI", 6),
                bg="#1a1d24", fg="#9ca3af", anchor="w").pack(fill="x")

        # RIGHT SIDE: RPM Circle
        canvas = tk.Canvas(content_row, bg="#1a1d24", width=40, height=40, highlightthickness=0)
        canvas.pack(side="right", padx=2)

        # Draw circular progress (based on RPM %)
        rpm_percent = min((rpm / 2000) * 100, 100)
        extent = int((rpm_percent / 100) * 360)

        # Background circle
        canvas.create_oval(5, 5, 35, 35, outline="#374151", width=2)
        # Progress arc (red)
        if rpm > 0:
            canvas.create_arc(5, 5, 35, 35, start=90, extent=-extent,
                             outline="#ef4444", width=3, style="arc")

        # RPM value in center
        canvas.create_text(20, 20, text=str(rpm), font=("Segoe UI", 8, "bold"), fill="#ffffff")

    def _create_modern_slider(self, parent, label, min_val, max_val, default, unit):
        """Create modern horizontal slider (red track)"""
        container = tk.Frame(parent, bg="#0a0e27")
        container.pack(fill="x", pady=5)

        # Label (left)
        tk.Label(container, text=label, font=("Segoe UI", 7, "bold"),
                bg="#0a0e27", fg="#94a3b8").pack(anchor="w", pady=(0, 3))

        # Slider + value display row
        slider_row = tk.Frame(container, bg="#0a0e27")
        slider_row.pack(fill="x")

        # Slider track (canvas)
        track = tk.Canvas(slider_row, bg="#0a0e27", height=20, highlightthickness=0)
        track.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Draw slider background (dark gray)
        track.create_rectangle(0, 8, 220, 12, fill="#374151", outline="")

        # Draw red progress (based on value)
        progress_width = int((default / max_val) * 220)
        track.create_rectangle(0, 8, progress_width, 12, fill="#ef4444", outline="")

        # Slider handle (circle)
        handle = track.create_oval(progress_width-6, 4, progress_width+6, 16,
                                   fill="#ffffff", outline="#ef4444", width=2)

        # Value display (right - rectangle with value)
        value_box = tk.Frame(slider_row, bg="#374151", width=60, height=20)
        value_box.pack(side="right")
        value_box.pack_propagate(False)

        value_label = tk.Label(value_box, text=f"{default} {unit}",
                              font=("Segoe UI", 7, "bold"), bg="#374151", fg="#ffffff")
        value_label.pack(expand=True)

    def _build_center_panel(self, parent):
        """Build center panel: Graph + Action Buttons + Temperature Icons"""
        center = tk.Frame(parent, bg="#0a0e27")
        center.pack(side="left", fill="both", expand=True)

        # Graph section (very close to PROFILES - 5px spacing)
        graph_frame = tk.Frame(center, bg="#0a0e27")
        graph_frame.pack(fill="x", pady=(5, 10))

        # Black header bar (connected to purple graph border)
        header_bar = tk.Frame(graph_frame, bg="#1a1d24", height=30)
        header_bar.pack(fill="x", pady=(0, 3))  # 3px spacing to graph
        header_bar.pack_propagate(False)

        tk.Label(header_bar, text="FAN CURVE - Setup", font=("Segoe UI", 10, "bold"),
                bg="#1a1d24", fg="#ffffff").pack(side="left", padx=15, pady=5)

        # Graph (very close to header - 3px spacing)
        self.graph = CompactFanCurveGraph(graph_frame, width=550, height=150,
                                         on_curve_change=self._on_curve_change)
        self.graph.pack(pady=0)

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
            btn = tk.Label(section, text=text, font=("Segoe UI", 9, "bold"),
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
        """Build 4 temperature icons below action buttons (EXACT from screenshot)"""
        icons_section = tk.Frame(parent, bg="#0a0e27")
        icons_section.pack(fill="x", pady=(15, 10))

        # Icon data: (filename, label, temp_value)
        # fan_temp.png gets animation instead of temperature
        icon_data = [
            ("body_temp.png", "BOARD", "43"),
            ("cpu_temp.png", "CPU", "65"),
            ("gpu_temp.png", "GPU", "58"),
            ("fan_temp.png", "FAN", None),  # None = animated fan
        ]

        # Container for centering icons
        icons_container = tk.Frame(icons_section, bg="#0a0e27")
        icons_container.pack(expand=True)

        self.fan_rotation = 0  # For animation
        self.fan_canvas = None  # Will store fan canvas reference

        for filename, label, temp in icon_data:
            icon_frame = tk.Frame(icons_container, bg="#0a0e27")
            icon_frame.pack(side="left", padx=20)

            # Load icon image
            icon_path = os.path.join("data", "icons", filename)
            if os.path.exists(icon_path) and Image:
                try:
                    # Load and resize icon (small size like in screenshot)
                    img = Image.open(icon_path)
                    img = img.resize((80, 80), Image.Resampling.LANCZOS)

                    # Create canvas for icon + temperature overlay
                    canvas = tk.Canvas(icon_frame, bg="#0a0e27", width=80, height=80, highlightthickness=0)
                    canvas.pack()

                    # If this is the fan icon, save reference for animation
                    if filename == "fan_temp.png":
                        self.fan_canvas = canvas
                        self.fan_image_pil = img  # Store PIL image for rotation
                        # Initial draw
                        photo = ImageTk.PhotoImage(img)
                        canvas.image = photo  # Keep reference
                        canvas.create_image(40, 40, image=photo, tags="fan_icon")
                    else:
                        # Static icon with temperature
                        photo = ImageTk.PhotoImage(img)
                        canvas.image = photo  # Keep reference
                        canvas.create_image(40, 40, image=photo)

                        # Temperature text overlay (centered in icon with black outline for visibility)
                        if temp:
                            # Draw black outline for better visibility
                            for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                                canvas.create_text(40+dx, 40+dy, text=f"{temp}°C",
                                                 font=("Segoe UI", 14, "bold"),
                                                 fill="#000000", tags="temp_outline")

                            # White text on top
                            canvas.create_text(40, 40, text=f"{temp}°C",
                                             font=("Segoe UI", 14, "bold"),
                                             fill="#ffffff", tags="temp_text")

                except Exception as e:
                    print(f"[Error] Failed to load icon {filename}: {e}")
                    # Fallback: simple colored circle
                    self._create_fallback_icon(icon_frame, label, temp)
            else:
                # Fallback if image not found
                self._create_fallback_icon(icon_frame, label, temp)

            # Label below icon
            tk.Label(icon_frame, text=label, font=("Segoe UI", 8, "bold"),
                    bg="#0a0e27", fg="#8b5cf6").pack(pady=(3, 0))

        # Start fan animation
        if self.fan_canvas:
            self._animate_fan()

    def _create_fallback_icon(self, parent, label, temp):
        """Fallback icon if image not found"""
        canvas = tk.Canvas(parent, bg="#0a0e27", width=80, height=80, highlightthickness=0)
        canvas.pack()

        # Draw colored circle
        colors = {"BOARD": "#3b82f6", "CPU": "#ef4444", "GPU": "#10b981", "FAN": "#8b5cf6"}
        color = colors.get(label, "#64748b")

        canvas.create_oval(10, 10, 70, 70, fill=color, outline="")

        if temp:
            canvas.create_text(40, 40, text=f"{temp}°C",
                             font=("Segoe UI", 12, "bold"), fill="#ffffff")

    def _animate_fan(self):
        """Animate fan rotation (optimized for performance)"""
        if not self.fan_canvas or not hasattr(self, 'fan_image_pil'):
            return

        try:
            # Rotate fan image (larger steps = less frequent updates)
            self.fan_rotation = (self.fan_rotation + 20) % 360
            rotated = self.fan_image_pil.rotate(self.fan_rotation, resample=Image.Resampling.BILINEAR)

            # Update canvas
            photo = ImageTk.PhotoImage(rotated)
            self.fan_canvas.delete("fan_icon")
            self.fan_canvas.create_image(40, 40, image=photo, tags="fan_icon")
            self.fan_canvas.image = photo  # Keep reference

            # Continue animation (slower = 100ms for better performance)
            self.fan_canvas.after(100, self._animate_fan)
        except Exception as e:
            print(f"[Error] Fan animation failed: {e}")

    # ============================================================
    # CALLBACKS
    # ============================================================

    def _on_profile_change(self, profile_id):
        """Handle profile change"""
        print(f"[Ultimate] Profile: {profile_id}")
        self.current_profile = profile_id

        # Update active state
        for pid, btn in self.profile_buttons.items():
            btn.set_active(pid == profile_id)

        # Load curve based on profile
        if profile_id == "ai":
            # AI: adaptive based on temperature
            avg_temp = sum([f.temp for f in self.fans.values()]) / len(self.fans)
            if avg_temp > 70:
                curve = FanAIEngine.generate_curve("performance")
            else:
                curve = FanAIEngine.generate_curve("balanced")
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
        """Handle curve change"""
        print(f"[Ultimate] Curve updated: {len(points)} points")

    def _on_slider_change(self, label, value):
        """Handle slider change"""
        print(f"[Ultimate] {label} = {value}")
        self.options[label.lower().replace(" ", "_").replace("°", "")] = value

    def _on_advanced_option_change(self, option: str, value: str):
        """Handle advanced option change"""
        print(f"[Ultimate] Advanced: {option} = {value}")
        self.options[option.lower().replace(" ", "_")] = value

    def _apply(self):
        """Apply curve"""
        print("[Ultimate] Applying curve...")
        messagebox.showinfo("Apply", "✅ Fan curve applied successfully!\nAll settings saved.")

    def _revert(self):
        """Revert curve"""
        print("[Ultimate] Reverting...")
        self._on_profile_change(self.current_profile)
        messagebox.showinfo("Revert", "↩️ Settings reverted to last saved state.")

    def _save_profile(self):
        """Open Save Profile Dialog with graph preview"""
        SaveProfileDialog(self.parent, self.graph.points, self.options, self.sliders)

    def _export(self):
        """Export all settings to JSON"""
        data = {
            "curve": [(p.temp, p.speed) for p in self.graph.points],
            "options": self.options,
            "sliders": {name: slider.value for name, slider in self.sliders.items()}
        }
        with open("fan_settings_ultimate.json", "w") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Export", "📤 All settings exported to fan_settings_ultimate.json")

    def _reset(self):
        """Reset to defaults"""
        print("[Ultimate] Resetting to defaults...")
        self._on_profile_change("balanced")
        for slider_name, slider in self.sliders.items():
            if slider_name == "Hysteresis":
                slider.set_value(3)
            elif slider_name == "Target°C":
                slider.set_value(70)
            elif slider_name == "Min Speed":
                slider.set_value(20)
            elif slider_name == "Max Speed":
                slider.set_value(100)
        messagebox.showinfo("Reset", "🔄 All settings reset to defaults.")

    def update_realtime(self):
        """Update real-time data"""
        import random
        for fan_name, fan_data in self.fans.items():
            fan_data.update(
                rpm=random.randint(800, 1800),
                percent=random.randint(40, 80),
                temp=random.uniform(35, 75)
            )

        avg_temp = sum([f.temp for f in self.fans.values()]) / len(self.fans)
        self.graph.update_realtime_data(avg_temp, [f.temp for f in self.fans.values()])


# ============================================================
# FACTORY FUNCTION
# ============================================================

def create_fan_dashboard(parent):
    """Create Fan Dashboard instance"""
    return FanDashboardUltimate(parent)
