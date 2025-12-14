# ui/expandable_list.py
"""
Expandable Process List Widget
Shows TOP5 by default, can expand to show more
"""

import tkinter as tk
from tkinter import ttk
from ui.theme import THEME


class ExpandableProcessList:
    """Expandable list widget for process display"""

    def __init__(self, parent, title, list_type='user'):
        """
        Args:
            parent: Parent widget
            title: List title
            list_type: 'user' or 'system'
        """
        self.parent = parent
        self.title = title
        self.list_type = list_type
        self.is_expanded = False
        self.all_processes = []

        # Main frame
        self.frame = tk.Frame(parent, bg=THEME["bg_panel"])

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build expandable list UI"""
        # Header with expand button
        header_frame = tk.Frame(self.frame, bg=THEME["accent"])
        header_frame.pack(fill="x")

        # Title
        self.title_label = tk.Label(
            header_frame,
            text=self.title,
            font=("Consolas", 10, "bold"),
            bg=THEME["accent"],
            fg=THEME["bg_panel"],
            anchor="w"
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Expand/Collapse button
        self.expand_btn = tk.Label(
            header_frame,
            text="▼ More",
            font=("Consolas", 9),
            bg=THEME["accent"],
            fg=THEME["bg_panel"],
            cursor="hand2",
            padx=8
        )
        self.expand_btn.pack(side="right")
        self.expand_btn.bind("<Button-1>", lambda e: self.toggle_expand())

        # Process list text widget
        self.list_text = tk.Text(
            self.frame,
            bg=THEME["bg_panel"],
            fg=THEME["muted"],
            bd=0,
            font=("Consolas", 9),
            wrap="none",
            height=6  # Default: TOP5
        )
        self.list_text.pack(fill="both", padx=8, pady=6, expand=True)
        self.list_text.config(state="disabled")

        # Configure tags
        self.list_text.tag_config("header", foreground=THEME["text"], font=("Consolas", 9, "bold"))
        self.list_text.tag_config("cpu_color", foreground=THEME["cpu"])
        self.list_text.tag_config("ram_color", foreground=THEME["ram"])
        self.list_text.tag_config("rival", foreground="#FFB000", font=("Consolas", 9, "bold"))
        self.list_text.tag_config("critical", foreground="#FF4444")

    def toggle_expand(self):
        """Toggle expand/collapse"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.expand_btn.config(text="▲ Less")
            self.list_text.config(height=15)  # Show more
            self._render_processes(self.all_processes)
        else:
            self.expand_btn.config(text="▼ More")
            self.list_text.config(height=6)  # Show TOP5
            self._render_processes(self.all_processes[:5])

    def update_processes(self, processes):
        """
        Update process list

        Args:
            processes: List of process dicts
        """
        self.all_processes = processes

        # Show TOP5 or all based on expand state
        if self.is_expanded:
            self._render_processes(processes)
        else:
            self._render_processes(processes[:5])

    def _render_processes(self, processes):
        """Render process list"""
        self.list_text.config(state="normal")
        self.list_text.delete("1.0", "end")

        if not processes:
            self.list_text.insert("end", "\n  No processes to display")
            self.list_text.config(state="disabled")
            return

        # Header
        if self.list_type == 'user':
            header = f"{'#':<3} {'Process':<20} {'CPU':<9} {' ':1} {'RAM':<9}\n"
        else:
            header = f"{'#':<3} {'Process':<18} {'CPU':<6} {'RAM':<8}\n"

        self.list_text.insert("end", header, ("header",))

        # Processes
        for i, proc in enumerate(processes, start=1):
            if self.list_type == 'user':
                line = self._format_user_process(i, proc)
            else:
                line = self._format_system_process(i, proc)

            self.list_text.insert("end", line)

        # Color CPU and RAM values
        self._apply_color_tags()

        self.list_text.config(state="disabled")

    def _format_user_process(self, index, proc):
        """Format user process line"""
        icon = proc.get('icon', '📦')
        name = proc.get('display_name', proc.get('name', 'unknown'))[:18]
        cpu = int(proc.get('cpu_percent', 0))
        ram_mb = int(proc.get('ram_MB', 0))
        is_rival = proc.get('is_rival', False)

        cpu_bar = self._make_bar_5(cpu)
        ram_bar = self._make_bar_5(min(ram_mb / 10, 100))

        rival_tag = " 💪" if is_rival else ""

        return f"{index:<3} {icon} {name:<16} {cpu_bar:<5} {cpu:>3d}%   {ram_bar:<5} {ram_mb:>4d}MB{rival_tag}\n"

    def _format_system_process(self, index, proc):
        """Format system process line"""
        icon = proc.get('icon', '⚙️')
        name = proc.get('display_name', proc.get('name', 'unknown'))[:14]
        cpu = int(proc.get('cpu_percent', 0))
        ram_mb = int(proc.get('ram_MB', 0))

        return f"{index:<3} {icon} {name:<14}  {cpu:>3d}%   {ram_mb:>4d}MB\n"

    def _make_bar_5(self, value):
        """Create 5-segment bar"""
        value = max(0, min(100, value))
        filled = int((value / 100) * 5)
        return "█" * filled + "░" * (5 - filled)

    def _apply_color_tags(self):
        """Apply color tags to CPU and RAM values"""
        import re
        content = self.list_text.get("1.0", "end")

        # Find CPU percentages
        cpu_positions = [(m.start(), m.end()) for m in re.finditer(r"\d+%", content)]
        for start, end in cpu_positions:
            self.list_text.tag_add("cpu_color", f"1.0+{start}c", f"1.0+{end}c")

        # Find RAM values
        ram_positions = [(m.start(), m.end()) for m in re.finditer(r"\d+MB", content)]
        for start, end in ram_positions:
            self.list_text.tag_add("ram_color", f"1.0+{start}c", f"1.0+{end}c")

        # Find rival emoji
        rival_positions = [(m.start(), m.end()) for m in re.finditer(r"💪", content)]
        for start, end in rival_positions:
            self.list_text.tag_add("rival", f"1.0+{start}c", f"1.0+{end}c")

    def pack(self, **kwargs):
        """Pack the frame"""
        self.frame.pack(**kwargs)

    def place(self, **kwargs):
        """Place the frame"""
        self.frame.place(**kwargs)

    def grid(self, **kwargs):
        """Grid the frame"""
        self.frame.grid(**kwargs)
