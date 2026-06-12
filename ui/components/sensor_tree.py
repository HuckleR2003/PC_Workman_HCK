"""
Sensor Tree Component - HWMonitor Style Hierarchical Display
Beautiful, expandable tree view of all hardware sensors
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable, Optional

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF


class SensorTreeView:
    """
    HWMonitor-style sensor tree with expandable categories
    """

    def __init__(self, parent, hardware_sensors, on_sensor_right_click: Optional[Callable] = None):
        """
        Args:
            parent: Parent tkinter widget
            hardware_sensors: HardwareSensors instance
            on_sensor_right_click: Callback(category, sensor_name, sensor_data)
        """
        self.parent = parent
        self.hardware_sensors = hardware_sensors
        self.on_sensor_right_click = on_sensor_right_click

        # Tracking
        self.category_frames = {}
        self.sensor_labels = {}

        self._build_ui()

    def _build_ui(self):
        """Build sensor tree UI"""
        # Container with scrollbar
        self.container = tk.Frame(self.parent, bg="#0f1117")
        self.container.pack(fill="both", expand=True)

        # Canvas + Scrollbar
        self.canvas = tk.Canvas(self.container, bg="#0f1117", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg="#0f1117")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Build initial tree
        self.refresh()

    def refresh(self):
        """Refresh sensor tree data"""
        # Get fresh sensor data
        tree = self.hardware_sensors.get_sensor_tree()

        # Update UI
        for category, data in tree.items():
            self._update_category(category, data)

    def _update_category(self, category: str, data: Dict[str, Any]):
        """Update or create category in tree"""
        if category not in self.category_frames:
            # Create new category
            self._create_category(category, data)
        else:
            # Update existing sensors
            self._update_sensors(category, data)

    def _create_category(self, category: str, data: Dict[str, Any]):
        """Create new category frame with sensors"""
        # Category container
        cat_container = tk.Frame(self.scrollable_frame, bg="#0f1117")
        cat_container.pack(fill="x", padx=10, pady=5)

        # Category header (clickable to expand/collapse)
        header = tk.Frame(cat_container, bg="#1a1d24", cursor="hand2")
        header.pack(fill="x")

        # Expand/collapse icon + label
        header_content = tk.Frame(header, bg="#1a1d24")
        header_content.pack(fill="x", padx=12, pady=10)

        # Icon (▼ expanded, ▶ collapsed)
        icon_label = tk.Label(
            header_content,
            text="▼",
            font=(_BODY, 10),
            bg="#1a1d24",
            fg="#8b5cf6"
        )
        icon_label.pack(side="left", padx=(0, 8))

        # Category name
        name_label = tk.Label(
            header_content,
            text=f"{category} - {data['name']}",
            font=("Segoe UI Semibold", 11, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)

        # Sensors container (collapsible)
        sensors_frame = tk.Frame(cat_container, bg="#0f1117")
        sensors_frame.pack(fill="x", padx=5, pady=(5, 0))

        # Track state
        state = {'expanded': True}

        def toggle_expand(e=None):
            state['expanded'] = not state['expanded']
            if state['expanded']:
                sensors_frame.pack(fill="x", padx=5, pady=(5, 0))
                icon_label.config(text="▼")
            else:
                sensors_frame.pack_forget()
                icon_label.config(text="▶")

        # Bind click to header
        header.bind("<Button-1>", toggle_expand)
        header_content.bind("<Button-1>", toggle_expand)
        icon_label.bind("<Button-1>", toggle_expand)
        name_label.bind("<Button-1>", toggle_expand)

        # Create sensor rows
        sensor_row_widgets = {}
        for sensor_name, sensor_data in data.get('sensors', {}).items():
            row_widgets = self._create_sensor_row(sensors_frame, category, sensor_name, sensor_data)
            sensor_row_widgets[sensor_name] = row_widgets

        # Store references
        self.category_frames[category] = {
            'container': cat_container,
            'header': header,
            'icon': icon_label,
            'sensors_frame': sensors_frame,
            'sensor_rows': sensor_row_widgets,
            'state': state
        }

    def _create_sensor_row(self, parent, category: str, sensor_name: str, sensor_data: Dict[str, Any]):
        """Create single sensor row"""
        row = tk.Frame(parent, bg="#0f1117")
        row.pack(fill="x", pady=2)

        # Indent
        indent = tk.Frame(row, bg="#0f1117", width=20)
        indent.pack(side="left")

        # Bullet point
        bullet = tk.Label(
            row,
            text="├─",
            font=("Courier", 10),
            bg="#0f1117",
            fg="#64748b"
        )
        bullet.pack(side="left", padx=(0, 8))

        # Sensor name
        name_label = tk.Label(
            row,
            text=sensor_name + ":",
            font=(_BODY, 9),
            bg="#0f1117",
            fg="#cbd5e1",
            anchor="w",
            width=25
        )
        name_label.pack(side="left")

        # Sensor value (color-coded)
        color = self.hardware_sensors.get_sensor_color(sensor_data['type'], sensor_data['raw'])
        value_label = tk.Label(
            row,
            text=sensor_data['value'],
            font=(_MONO, 9, "bold"),
            bg="#0f1117",
            fg=color,
            anchor="w",
            width=20
        )
        value_label.pack(side="left", padx=(10, 0))

        # Max column (packed right -> appears further left than min)
        max_val_label = tk.Label(
            row,
            text=sensor_data.get('max', '-'),
            font=(_MONO, 8),
            bg="#0f1117",
            fg="#374151",
            anchor="e",
            width=9
        )
        max_val_label.pack(side="right", padx=(0, 8))
        max_hdr = tk.Label(row, text="max:", font=(_BODY, 7), bg="#0f1117", fg="#1f2937", width=4)
        max_hdr.pack(side="right")

        # Min column
        min_val_label = tk.Label(
            row,
            text=sensor_data.get('min', '-'),
            font=(_MONO, 8),
            bg="#0f1117",
            fg="#374151",
            anchor="e",
            width=9
        )
        min_val_label.pack(side="right", padx=(0, 2))
        min_hdr = tk.Label(row, text="min:", font=(_BODY, 7), bg="#0f1117", fg="#1f2937", width=4)
        min_hdr.pack(side="right", padx=(12, 0))

        # Right-click menu
        if self.on_sensor_right_click:
            def on_right_click(e):
                self.on_sensor_right_click(category, sensor_name, sensor_data)

            row.bind("<Button-3>", on_right_click)

        # Hover effect
        _hover_widgets = [row, bullet, name_label, value_label, min_hdr, min_val_label, max_hdr, max_val_label]

        def on_enter(e):
            for w in _hover_widgets:
                w.config(bg="#1a1d24")

        def on_leave(e):
            for w in _hover_widgets:
                w.config(bg="#0f1117")

        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

        return {
            'row': row,
            'value_label': value_label,
            'min_val_label': min_val_label,
            'max_val_label': max_val_label,
            'color': color
        }

    def _update_sensors(self, category: str, data: Dict[str, Any]):
        """Update sensor values in existing category"""
        cat_frame = self.category_frames.get(category)
        if not cat_frame:
            return

        sensor_rows = cat_frame['sensor_rows']

        for sensor_name, sensor_data in data.get('sensors', {}).items():
            if sensor_name in sensor_rows:
                # Update existing sensor
                row_widgets = sensor_rows[sensor_name]
                value_label = row_widgets['value_label']

                # Update value
                value_label.config(text=sensor_data['value'])

                # Update color
                color = self.hardware_sensors.get_sensor_color(sensor_data['type'], sensor_data['raw'])
                value_label.config(fg=color)

            else:
                # New sensor appeared - add it
                sensors_frame = cat_frame['sensors_frame']
                row_widgets = self._create_sensor_row(sensors_frame, category, sensor_name, sensor_data)
                sensor_rows[sensor_name] = row_widgets


def create_sensor_tree_page(parent, hardware_sensors, on_sensor_right_click=None):
    """
    Create sensor tree page

    Args:
        parent: Parent widget
        hardware_sensors: HardwareSensors instance
        on_sensor_right_click: Optional callback for right-click menu

    Returns:
        SensorTreeView instance
    """
    # Header
    header = tk.Frame(parent, bg="#1a1d24")
    header.pack(fill="x", padx=20, pady=(20, 10))

    tk.Label(
        header,
        text="🌲 Hardware Sensors",
        font=("Segoe UI Light", 20, "bold"),
        bg="#1a1d24",
        fg="#ffffff"
    ).pack(side="left", padx=15, pady=15)

    # Refresh button
    refresh_btn = tk.Label(
        header,
        text="🔄 Refresh",
        font=("Segoe UI Semibold", 9, "bold"),
        bg="#1e293b",
        fg="#94a3b8",
        cursor="hand2",
        padx=12,
        pady=6
    )
    refresh_btn.pack(side="right", padx=15, pady=15)

    # Hover effect for refresh button
    def on_enter(e):
        refresh_btn.config(bg="#334155", fg="#e2e8f0")
    def on_leave(e):
        refresh_btn.config(bg="#1e293b", fg="#94a3b8")

    refresh_btn.bind("<Enter>", on_enter)
    refresh_btn.bind("<Leave>", on_leave)

    # Info text
    info = tk.Label(
        header,
        text="Right-click sensor -> Add to Dashboard / System Tray",
        font=(_BODY, 8),
        bg="#1a1d24",
        fg="#64748b"
    )
    info.pack(side="right", padx=15)

    # Sensor tree
    tree_frame = tk.Frame(parent, bg="#0f1117")
    tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    tree_view = SensorTreeView(tree_frame, hardware_sensors, on_sensor_right_click)

    # Bind refresh button
    refresh_btn.bind("<Button-1>", lambda e: tree_view.refresh())

    return tree_view


if __name__ == "__main__":
    # Test sensor tree
    from core.hardware_sensors import HardwareSensors

    root = tk.Tk()
    root.title("Sensor Tree Test")
    root.geometry("800x600")
    root.configure(bg="#0f1117")

    sensors = HardwareSensors()

    def on_right_click(category, sensor_name, sensor_data):
        print(f"Right-clicked: {category} -> {sensor_name} = {sensor_data['value']}")

    tree = create_sensor_tree_page(root, sensors, on_right_click)

    # Auto-refresh every 2 seconds
    def auto_refresh():
        tree.refresh()
        root.after(2000, auto_refresh)

    auto_refresh()

    root.mainloop()
