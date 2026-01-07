"""
Live Hardware Graphs Component - MSI Afterburner Style
Real-time scrolling graphs for CPU, GPU, RAM, and Temperatures
"""

import tkinter as tk
from collections import deque
from typing import Dict, List, Optional, Tuple
import time


class LiveGraph:
    """
    Single live scrolling graph (MSI Afterburner style)
    """

    def __init__(self, parent, title: str, color: str, max_value: float = 100.0,
                 unit: str = "%", width: int = 400, height: int = 120):
        """
        Args:
            parent: Parent tkinter widget
            title: Graph title
            color: Line color (hex)
            max_value: Maximum Y value
            unit: Unit string (%, °C, MHz, etc.)
            width: Canvas width
            height: Canvas height
        """
        self.parent = parent
        self.title = title
        self.color = color
        self.max_value = max_value
        self.unit = unit
        self.width = width
        self.height = height

        # Data storage (150 points = 30 seconds at 5 FPS)
        self.max_points = 150
        self.data = deque([0.0] * self.max_points, maxlen=self.max_points)

        # Graph area dimensions
        self.graph_padding = 40
        self.graph_width = width - self.graph_padding * 2
        self.graph_height = height - 40

        self._build_ui()

    def _build_ui(self):
        """Build graph UI"""
        # Container
        self.container = tk.Frame(self.parent, bg="#1a1d24")
        self.container.pack(fill="x", padx=10, pady=5)

        # Header
        header = tk.Frame(self.container, bg="#1a1d24")
        header.pack(fill="x", padx=10, pady=(10, 5))

        # Title
        tk.Label(
            header,
            text=self.title,
            font=("Segoe UI Semibold", 10, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        ).pack(side="left")

        # Current value label
        self.value_label = tk.Label(
            header,
            text=f"0 {self.unit}",
            font=("Consolas", 10, "bold"),
            bg="#1a1d24",
            fg=self.color,
            anchor="e"
        )
        self.value_label.pack(side="right")

        # Min/Max labels
        stats_frame = tk.Frame(header, bg="#1a1d24")
        stats_frame.pack(side="right", padx=15)

        self.min_label = tk.Label(
            stats_frame,
            text="Min: 0",
            font=("Consolas", 8),
            bg="#1a1d24",
            fg="#64748b"
        )
        self.min_label.pack(side="left", padx=5)

        self.max_label = tk.Label(
            stats_frame,
            text="Max: 0",
            font=("Consolas", 8),
            bg="#1a1d24",
            fg="#64748b"
        )
        self.max_label.pack(side="left", padx=5)

        self.avg_label = tk.Label(
            stats_frame,
            text="Avg: 0",
            font=("Consolas", 8),
            bg="#1a1d24",
            fg="#64748b"
        )
        self.avg_label.pack(side="left", padx=5)

        # Canvas for graph
        self.canvas = tk.Canvas(
            self.container,
            bg="#0f1117",
            width=self.width,
            height=self.height,
            highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=(0, 10))

        # Draw initial grid
        self._draw_grid()

    def _draw_grid(self):
        """Draw grid lines and labels"""
        # Vertical grid lines (time)
        for i in range(0, self.graph_width + 1, 50):
            x = self.graph_padding + i
            self.canvas.create_line(
                x, 20, x, 20 + self.graph_height,
                fill="#1e293b",
                width=1
            )

        # Horizontal grid lines (values)
        for i in range(0, 5):
            y = 20 + (self.graph_height * i / 4)
            self.canvas.create_line(
                self.graph_padding, y,
                self.graph_padding + self.graph_width, y,
                fill="#1e293b",
                width=1
            )

            # Y-axis labels
            value = int(self.max_value * (1 - i / 4))
            self.canvas.create_text(
                self.graph_padding - 10, y,
                text=str(value),
                fill="#64748b",
                font=("Consolas", 8),
                anchor="e"
            )

        # Border
        self.canvas.create_rectangle(
            self.graph_padding, 20,
            self.graph_padding + self.graph_width, 20 + self.graph_height,
            outline=self.color,
            width=2
        )

    def update(self, value: float):
        """
        Update graph with new value

        Args:
            value: New data point
        """
        # Add new value
        self.data.append(value)

        # Update current value label
        self.value_label.config(text=f"{int(value)} {self.unit}")

        # Update stats
        if len(self.data) > 0:
            data_list = list(self.data)
            min_val = min(data_list)
            max_val = max(data_list)
            avg_val = sum(data_list) / len(data_list)

            self.min_label.config(text=f"Min: {int(min_val)}")
            self.max_label.config(text=f"Max: {int(max_val)}")
            self.avg_label.config(text=f"Avg: {int(avg_val)}")

        # Redraw graph
        self._redraw_graph()

    def _redraw_graph(self):
        """Redraw entire graph"""
        # Clear previous graph (keep grid)
        self.canvas.delete("graph_line")

        # Draw line graph
        points = []
        for i, value in enumerate(self.data):
            x = self.graph_padding + (i * self.graph_width / (self.max_points - 1))
            y_ratio = min(value / self.max_value, 1.0)
            y = 20 + self.graph_height - (y_ratio * self.graph_height)
            points.append((x, y))

        # Draw line
        if len(points) > 1:
            self.canvas.create_line(
                points,
                fill=self.color,
                width=2,
                smooth=True,
                tags="graph_line"
            )

            # Fill area under graph
            fill_points = points + [
                (self.graph_padding + self.graph_width, 20 + self.graph_height),
                (self.graph_padding, 20 + self.graph_height)
            ]
            self.canvas.create_polygon(
                fill_points,
                fill=self.color,
                outline="",
                stipple="gray25",
                tags="graph_line"
            )


class HardwareGraphsPanel:
    """
    Panel with multiple live hardware graphs (MSI Afterburner style)
    """

    def __init__(self, parent, monitor):
        """
        Args:
            parent: Parent tkinter widget
            monitor: HardwareMonitor instance
        """
        self.parent = parent
        self.monitor = monitor

        # Graphs
        self.graphs = {}

        self._build_ui()

    def _build_ui(self):
        """Build graphs panel UI"""
        # Scrollable container
        container = tk.Frame(self.parent, bg="#0f1117")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg="#0f1117", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

        scrollable_frame = tk.Frame(canvas, bg="#0f1117")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Create graphs
        self.graphs['cpu'] = LiveGraph(
            scrollable_frame,
            "🔵 CPU Usage",
            "#3b82f6",
            max_value=100.0,
            unit="%"
        )

        self.graphs['cpu_temp'] = LiveGraph(
            scrollable_frame,
            "🌡️ CPU Temperature",
            "#f59e0b",
            max_value=100.0,
            unit="°C"
        )

        self.graphs['gpu'] = LiveGraph(
            scrollable_frame,
            "🟢 GPU Usage",
            "#10b981",
            max_value=100.0,
            unit="%"
        )

        self.graphs['gpu_temp'] = LiveGraph(
            scrollable_frame,
            "🌡️ GPU Temperature",
            "#ef4444",
            max_value=100.0,
            unit="°C"
        )

        self.graphs['ram'] = LiveGraph(
            scrollable_frame,
            "🟡 RAM Usage",
            "#fbbf24",
            max_value=100.0,
            unit="%"
        )

        # Info footer
        info = tk.Label(
            scrollable_frame,
            text="📊 Live graphs update every 0.2s | 150 data points (30 seconds history)",
            font=("Segoe UI", 8),
            bg="#0f1117",
            fg="#64748b"
        )
        info.pack(pady=20)

    def update(self, sample: Dict):
        """
        Update all graphs with new sample

        Args:
            sample: Hardware sample dict
        """
        self.graphs['cpu'].update(sample.get('cpu_percent', 0))
        self.graphs['cpu_temp'].update(sample.get('cpu_temp', 0))
        self.graphs['gpu'].update(sample.get('gpu_percent', 0))
        self.graphs['gpu_temp'].update(sample.get('gpu_temp', 0))
        self.graphs['ram'].update(sample.get('ram_percent', 0))


def create_graphs_page(parent, monitor):
    """
    Create hardware graphs page

    Args:
        parent: Parent widget
        monitor: HardwareMonitor instance

    Returns:
        HardwareGraphsPanel instance
    """
    # Header
    header = tk.Frame(parent, bg="#1a1d24")
    header.pack(fill="x", padx=20, pady=(20, 10))

    tk.Label(
        header,
        text="📊 Live Hardware Graphs",
        font=("Segoe UI Light", 20, "bold"),
        bg="#1a1d24",
        fg="#ffffff"
    ).pack(side="left", padx=15, pady=15)

    # Info
    tk.Label(
        header,
        text="MSI Afterburner Style - Real-time monitoring",
        font=("Segoe UI", 9),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(side="left", padx=15)

    # Graphs panel
    graphs_frame = tk.Frame(parent, bg="#0f1117")
    graphs_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    panel = HardwareGraphsPanel(graphs_frame, monitor)

    return panel
