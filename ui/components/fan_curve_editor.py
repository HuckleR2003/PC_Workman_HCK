"""
Fan Curve Editor Component - MSI Afterburner / EVGA Precision Style
Visual drag-and-drop fan curve editor with presets
"""

import tkinter as tk
from typing import List, Tuple, Optional, Dict, Callable
import json
import os


class FanCurvePoint:
    """Single point on fan curve"""
    def __init__(self, temp: int, speed: int):
        self.temp = temp  # Temperature in °C
        self.speed = speed  # Fan speed in %


class FanCurveEditor:
    """
    Visual fan curve editor with drag-and-drop points
    """

    def __init__(self, parent, on_curve_change: Optional[Callable] = None):
        """
        Args:
            parent: Parent tkinter widget
            on_curve_change: Callback(curve_points) when curve changes
        """
        self.parent = parent
        self.on_curve_change = on_curve_change

        # Canvas dimensions
        self.width = 600
        self.height = 400
        self.padding = 60

        self.graph_width = self.width - self.padding * 2
        self.graph_height = self.height - self.padding * 2

        # Fan curve points (temp, speed)
        self.points = [
            FanCurvePoint(30, 30),
            FanCurvePoint(50, 50),
            FanCurvePoint(70, 70),
            FanCurvePoint(90, 100)
        ]

        # Dragging state
        self.dragging_point = None
        self.point_radius = 8

        self._build_ui()
        self._draw_curve()

    def _build_ui(self):
        """Build editor UI"""
        # Container
        self.container = tk.Frame(self.parent, bg="#1a1d24")
        self.container.pack(fill="both", expand=True, padx=20, pady=10)

        # Header
        header = tk.Frame(self.container, bg="#1a1d24")
        header.pack(fill="x", padx=15, pady=15)

        tk.Label(
            header,
            text="🌀 Fan Curve Editor",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(side="left")

        # Preset buttons
        presets_frame = tk.Frame(header, bg="#1a1d24")
        presets_frame.pack(side="right")

        presets = [
            ("Silent", self._load_silent_preset),
            ("Balanced", self._load_balanced_preset),
            ("Performance", self._load_performance_preset),
            ("Aggressive", self._load_aggressive_preset),
        ]

        for name, callback in presets:
            btn = tk.Label(
                presets_frame,
                text=name,
                font=("Segoe UI Semibold", 9, "bold"),
                bg="#1e293b",
                fg="#94a3b8",
                cursor="hand2",
                padx=12,
                pady=6
            )
            btn.pack(side="left", padx=5)
            btn.bind("<Button-1>", lambda e, cb=callback: cb())

            # Hover effect
            def make_hover(b):
                def on_enter(e):
                    b.config(bg="#334155", fg="#e2e8f0")
                def on_leave(e):
                    b.config(bg="#1e293b", fg="#94a3b8")
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
            make_hover(btn)

        # Canvas
        self.canvas = tk.Canvas(
            self.container,
            bg="#0f1117",
            width=self.width,
            height=self.height,
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(padx=15, pady=15)

        # Bind mouse events
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)

        # Info
        self.info_label = tk.Label(
            self.container,
            text="💡 Drag points to adjust curve | Click to add points | Right-click to remove",
            font=("Segoe UI", 9),
            bg="#1a1d24",
            fg="#64748b"
        )
        self.info_label.pack(pady=10)

        # Current point info
        self.point_info = tk.Label(
            self.container,
            text="",
            font=("Consolas", 10, "bold"),
            bg="#1a1d24",
            fg="#8b5cf6"
        )
        self.point_info.pack(pady=5)

    def _draw_curve(self):
        """Draw fan curve graph"""
        self.canvas.delete("all")

        # Draw grid
        self._draw_grid()

        # Draw curve line
        self._draw_curve_line()

        # Draw points
        self._draw_points()

    def _draw_grid(self):
        """Draw background grid and labels"""
        # Vertical lines (temperature)
        for temp in range(0, 101, 10):
            x = self.padding + (temp / 100.0) * self.graph_width

            self.canvas.create_line(
                x, self.padding,
                x, self.padding + self.graph_height,
                fill="#1e293b" if temp % 20 == 0 else "#1a1d24",
                width=2 if temp % 20 == 0 else 1
            )

            # Labels every 20°C
            if temp % 20 == 0:
                self.canvas.create_text(
                    x, self.padding + self.graph_height + 15,
                    text=f"{temp}°C",
                    fill="#64748b",
                    font=("Consolas", 9)
                )

        # Horizontal lines (fan speed)
        for speed in range(0, 101, 10):
            y = self.padding + self.graph_height - (speed / 100.0) * self.graph_height

            self.canvas.create_line(
                self.padding, y,
                self.padding + self.graph_width, y,
                fill="#1e293b" if speed % 20 == 0 else "#1a1d24",
                width=2 if speed % 20 == 0 else 1
            )

            # Labels every 20%
            if speed % 20 == 0:
                self.canvas.create_text(
                    self.padding - 20, y,
                    text=f"{speed}%",
                    fill="#64748b",
                    font=("Consolas", 9)
                )

        # Axis labels
        self.canvas.create_text(
            self.width // 2, self.padding + self.graph_height + 40,
            text="Temperature (°C)",
            fill="#ffffff",
            font=("Segoe UI", 10, "bold")
        )

        self.canvas.create_text(
            15, self.height // 2,
            text="Fan Speed (%)",
            fill="#ffffff",
            font=("Segoe UI", 10, "bold"),
            angle=90
        )

        # Border
        self.canvas.create_rectangle(
            self.padding, self.padding,
            self.padding + self.graph_width,
            self.padding + self.graph_height,
            outline="#8b5cf6",
            width=3
        )

    def _draw_curve_line(self):
        """Draw smooth curve through points"""
        if len(self.points) < 2:
            return

        # Sort points by temperature
        sorted_points = sorted(self.points, key=lambda p: p.temp)

        # Convert to canvas coordinates
        coords = []
        for point in sorted_points:
            x = self.padding + (point.temp / 100.0) * self.graph_width
            y = self.padding + self.graph_height - (point.speed / 100.0) * self.graph_height
            coords.append((x, y))

        # Draw line
        if len(coords) > 1:
            self.canvas.create_line(
                coords,
                fill="#8b5cf6",
                width=3,
                smooth=True,
                tags="curve_line"
            )

            # Fill area under curve
            fill_coords = [(self.padding, self.padding + self.graph_height)] + coords + \
                          [(self.padding + self.graph_width, self.padding + self.graph_height)]
            self.canvas.create_polygon(
                fill_coords,
                fill="#8b5cf6",
                outline="",
                stipple="gray25",
                tags="curve_line"
            )

    def _draw_points(self):
        """Draw draggable points"""
        for i, point in enumerate(self.points):
            x = self.padding + (point.temp / 100.0) * self.graph_width
            y = self.padding + self.graph_height - (point.speed / 100.0) * self.graph_height

            # Point circle
            self.canvas.create_oval(
                x - self.point_radius, y - self.point_radius,
                x + self.point_radius, y + self.point_radius,
                fill="#a855f7",
                outline="#ffffff",
                width=2,
                tags=f"point_{i}"
            )

            # Point label
            self.canvas.create_text(
                x, y - self.point_radius - 15,
                text=f"{point.temp}°C\n{point.speed}%",
                fill="#a855f7",
                font=("Consolas", 8, "bold"),
                tags=f"point_{i}_label"
            )

    def _on_mouse_down(self, event):
        """Handle mouse down"""
        # Check if clicking on existing point
        for i, point in enumerate(self.points):
            x = self.padding + (point.temp / 100.0) * self.graph_width
            y = self.padding + self.graph_height - (point.speed / 100.0) * self.graph_height

            dist = ((event.x - x)**2 + (event.y - y)**2)**0.5
            if dist < self.point_radius + 5:
                self.dragging_point = i
                self.canvas.config(cursor="hand2")
                return

        # If not clicking point, add new point
        temp = ((event.x - self.padding) / self.graph_width) * 100
        speed = ((self.padding + self.graph_height - event.y) / self.graph_height) * 100

        # Clamp values
        temp = max(0, min(100, temp))
        speed = max(0, min(100, speed))

        # Add point
        self.points.append(FanCurvePoint(int(temp), int(speed)))
        self._draw_curve()
        self._notify_change()

    def _on_mouse_drag(self, event):
        """Handle mouse drag"""
        if self.dragging_point is None:
            return

        # Calculate new position
        temp = ((event.x - self.padding) / self.graph_width) * 100
        speed = ((self.padding + self.graph_height - event.y) / self.graph_height) * 100

        # Clamp values
        temp = max(0, min(100, temp))
        speed = max(0, min(100, speed))

        # Update point
        self.points[self.dragging_point].temp = int(temp)
        self.points[self.dragging_point].speed = int(speed)

        # Update point info
        self.point_info.config(
            text=f"Point {self.dragging_point + 1}: {int(temp)}°C → {int(speed)}%"
        )

        # Redraw
        self._draw_curve()

    def _on_mouse_up(self, event):
        """Handle mouse up"""
        if self.dragging_point is not None:
            self._notify_change()
        self.dragging_point = None
        self.canvas.config(cursor="crosshair")
        self.point_info.config(text="")

    def _notify_change(self):
        """Notify callback of curve change"""
        if self.on_curve_change:
            self.on_curve_change(self.points)

    def _load_silent_preset(self):
        """Load Silent preset (low RPM, quiet)"""
        self.points = [
            FanCurvePoint(0, 20),
            FanCurvePoint(40, 30),
            FanCurvePoint(60, 50),
            FanCurvePoint(80, 70),
            FanCurvePoint(100, 85)
        ]
        self._draw_curve()
        self._notify_change()
        print("[FanCurve] Loaded Silent preset")

    def _load_balanced_preset(self):
        """Load Balanced preset (default)"""
        self.points = [
            FanCurvePoint(0, 30),
            FanCurvePoint(50, 50),
            FanCurvePoint(70, 70),
            FanCurvePoint(90, 100)
        ]
        self._draw_curve()
        self._notify_change()
        print("[FanCurve] Loaded Balanced preset")

    def _load_performance_preset(self):
        """Load Performance preset (higher RPM)"""
        self.points = [
            FanCurvePoint(0, 40),
            FanCurvePoint(40, 60),
            FanCurvePoint(60, 80),
            FanCurvePoint(80, 100)
        ]
        self._draw_curve()
        self._notify_change()
        print("[FanCurve] Loaded Performance preset")

    def _load_aggressive_preset(self):
        """Load Aggressive preset (max cooling)"""
        self.points = [
            FanCurvePoint(0, 50),
            FanCurvePoint(30, 70),
            FanCurvePoint(50, 85),
            FanCurvePoint(70, 100)
        ]
        self._draw_curve()
        self._notify_change()
        print("[FanCurve] Loaded Aggressive preset")

    def get_curve_data(self) -> List[Tuple[int, int]]:
        """Get curve data as list of (temp, speed) tuples"""
        sorted_points = sorted(self.points, key=lambda p: p.temp)
        return [(p.temp, p.speed) for p in sorted_points]

    def save_curve(self, filename: str):
        """Save curve to JSON file"""
        data = self.get_curve_data()
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[FanCurve] Saved curve to {filename}")

    def load_curve(self, filename: str):
        """Load curve from JSON file"""
        if not os.path.exists(filename):
            print(f"[FanCurve] File not found: {filename}")
            return

        with open(filename, 'r') as f:
            data = json.load(f)

        self.points = [FanCurvePoint(temp, speed) for temp, speed in data]
        self._draw_curve()
        self._notify_change()
        print(f"[FanCurve] Loaded curve from {filename}")


def create_fan_curve_page(parent, on_curve_change=None):
    """
    Create fan curve editor page

    Args:
        parent: Parent widget
        on_curve_change: Callback when curve changes

    Returns:
        FanCurveEditor instance
    """
    # Header
    header = tk.Frame(parent, bg="#1a1d24")
    header.pack(fill="x", padx=20, pady=(20, 10))

    tk.Label(
        header,
        text="🌀 Fan Curve Editor",
        font=("Segoe UI Light", 20, "bold"),
        bg="#1a1d24",
        fg="#ffffff"
    ).pack(side="left", padx=15, pady=15)

    # Warning
    warning = tk.Frame(header, bg="#451a03", bd=0)
    warning.pack(side="right", padx=15)

    warning_inner = tk.Frame(warning, bg="#451a03")
    warning_inner.pack(padx=10, pady=5)

    tk.Label(
        warning_inner,
        text="⚠️ EXPERIMENTAL: Fan control requires admin rights and compatible hardware",
        font=("Segoe UI", 8),
        bg="#451a03",
        fg="#fb923c",
        anchor="w"
    ).pack()

    # Editor
    editor_frame = tk.Frame(parent, bg="#0f1117")
    editor_frame.pack(fill="both", expand=True)

    editor = FanCurveEditor(editor_frame, on_curve_change)

    # Control buttons
    controls = tk.Frame(parent, bg="#1a1d24")
    controls.pack(fill="x", padx=20, pady=20)

    buttons = [
        ("💾 Save Curve", lambda: editor.save_curve("fan_curve.json")),
        ("📂 Load Curve", lambda: editor.load_curve("fan_curve.json")),
        ("🔄 Reset to Default", editor._load_balanced_preset),
    ]

    for text, callback in buttons:
        btn = tk.Label(
            controls,
            text=text,
            font=("Segoe UI Semibold", 10, "bold"),
            bg="#1e293b",
            fg="#94a3b8",
            cursor="hand2",
            padx=20,
            pady=10
        )
        btn.pack(side="left", padx=10)
        btn.bind("<Button-1>", lambda e, cb=callback: cb())

        # Hover effect
        def make_hover(b):
            def on_enter(e):
                b.config(bg="#334155", fg="#e2e8f0")
            def on_leave(e):
                b.config(bg="#1e293b", fg="#94a3b8")
            b.bind("<Enter>", on_enter)
            b.bind("<Leave>", on_leave)
        make_hover(btn)

    return editor
