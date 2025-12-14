# ui/page_day_stats.py
"""
Day Stats Page - Windows Properties Style
Professional statistics page showing daily system usage
"""

import tkinter as tk
from tkinter import ttk
from ui.theme import THEME
from ui.process_tooltip import ProcessTooltip
import time
from datetime import datetime, timedelta


class DayStatsPage:
    """Professional Day Stats page with Windows Properties styling"""

    def __init__(self, parent, data_manager, classifier):
        self.parent = parent
        self.data_manager = data_manager
        self.classifier = classifier

        # Main frame
        self.frame = tk.Frame(parent, bg=THEME["bg_main"])

        # Tooltip for process info
        self.tooltip = ProcessTooltip(self.frame)

        # Process history for sparklines (stores last N samples per process)
        self.process_history = {}  # {process_name: [cpu1, cpu2, ...]}
        self.max_history = 15  # Keep last 15 samples for sparkline

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build Day Stats UI"""
        # Title
        title = tk.Label(
            self.frame,
            text="Daily Statistics",
            font=("Segoe UI", 16, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"],
            anchor="w"
        )
        title.pack(fill="x", padx=20, pady=(15, 5))

        subtitle = tk.Label(
            self.frame,
            text="System resource usage for today",
            font=("Segoe UI", 9),
            bg=THEME["bg_main"],
            fg=THEME["muted"],
            anchor="w"
        )
        subtitle.pack(fill="x", padx=20, pady=(0, 15))

        # Content container
        content = tk.Frame(self.frame, bg=THEME["bg_main"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Left column - Summary cards
        left_col = tk.Frame(content, bg=THEME["bg_main"])
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._build_summary_cards(left_col)

        # Right column - TOP processes
        right_col = tk.Frame(content, bg=THEME["bg_main"])
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        self._build_top_processes(right_col)

    def _build_summary_cards(self, parent):
        """Build minimalistic summary cards with icons"""
        # Session Duration Card
        card1 = self._create_property_card(
            parent,
            "⏱️ Session Duration",
            "00:00:00",
            ""
        )
        card1.pack(fill="x", pady=2)
        self.duration_value = card1

        # Total Samples Card
        card2 = self._create_property_card(
            parent,
            "📊 Data Points",
            "0",
            ""
        )
        card2.pack(fill="x", pady=2)
        self.samples_value = card2

        # Running Services Card
        card_services = self._create_property_card(
            parent,
            "⚙️ Running Services",
            "0/220",
            ""
        )
        card_services.pack(fill="x", pady=2)
        self.services_value = card_services

        # Average CPU Card
        card3 = self._create_property_card(
            parent,
            "⚡ Avg CPU",
            "0%",
            ""
        )
        card3.pack(fill="x", pady=2)
        self.avg_cpu_value = card3

        # Average RAM Card
        card4 = self._create_property_card(
            parent,
            "💾 Avg RAM",
            "0%",
            ""
        )
        card4.pack(fill="x", pady=2)
        self.avg_ram_value = card4

        # Average GPU Card
        card5 = self._create_property_card(
            parent,
            "🎮 Avg GPU",
            "0%",
            ""
        )
        card5.pack(fill="x", pady=2)
        self.avg_gpu_value = card5

    def _get_gradient_color(self, percentage):
        """Get gradient color based on percentage value"""
        if percentage < 30:
            return "#4ade80"  # Green
        elif percentage < 60:
            return "#fbbf24"  # Yellow
        elif percentage < 80:
            return "#fb923c"  # Orange
        else:
            return "#ef4444"  # Red

    def _create_property_card(self, parent, title, value, description):
        """Create card with gradient progress bar (modern style)"""
        card = tk.Frame(
            parent,
            bg=THEME["bg_panel"],
            relief="flat",
            bd=1,
            highlightthickness=1,
            highlightbackground="#2d3139",
            highlightcolor="#FF6B35"
        )

        # Title section
        title_frame = tk.Frame(card, bg=THEME["bg_panel"])
        title_frame.pack(fill="x", padx=10, pady=(6, 2))

        title_lbl = tk.Label(
            title_frame,
            text=title,
            font=("Segoe UI", 9),
            bg=THEME["bg_panel"],
            fg=THEME["muted"],
            anchor="w"
        )
        title_lbl.pack(side="left")

        # Value label (top right)
        value_lbl = tk.Label(
            title_frame,
            text=value,
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["accent"],
            anchor="e"
        )
        value_lbl.pack(side="right")

        # Progress bar container (only for percentage metrics)
        bar_container = tk.Frame(
            card,
            bg="#1a1d24",  # Dark background
            height=6,
            relief="flat"
        )
        bar_container.pack(fill="x", padx=10, pady=(0, 6))
        bar_container.pack_propagate(False)

        # Progress bar fill (will be updated dynamically)
        bar_fill = tk.Frame(
            bar_container,
            bg="#4ade80",  # Default green
            height=6
        )
        bar_fill.place(x=0, y=0, relwidth=0.0, relheight=1.0)

        # Add hover effects
        def on_enter(e):
            card.config(
                highlightbackground="#FF6B35",
                highlightthickness=2,
                relief="raised"
            )

        def on_leave(e):
            card.config(
                highlightbackground="#2d3139",
                highlightthickness=1,
                relief="flat"
            )

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

        # Store references for updating
        card.value_label = value_lbl
        card.progress_bar = bar_fill
        card.progress_container = bar_container

        return card

    def _build_top_processes(self, parent):
        """Build TOP processes section with info buttons"""
        header = tk.Label(
            parent,
            text="TOP Resource Consumers Today",
            font=("Segoe UI", 10, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            anchor="w"
        )
        header.pack(fill="x", padx=10, pady=(8, 5))

        # Scrollable container
        self.process_container = tk.Frame(parent, bg=THEME["bg_panel"])
        self.process_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Store process widgets
        self.process_widgets = []

    def update(self):
        """Update Day Stats data"""
        if not self.data_manager:
            return

        try:
            # Get session summary
            summary = self.data_manager.get_session_summary()

            # Update duration
            duration = summary.get('session_duration', 0)
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.duration_value.value_label.config(text=duration_str)

            # Update samples count
            samples = summary.get('total_snapshots', 0)
            self.samples_value.value_label.config(text=f"{samples:,}")

            # Update running services count
            try:
                import psutil
                # Count running processes (services + programs)
                running = len(psutil.pids())
                max_services = 220  # Typical max services on Windows
                self.services_value.value_label.config(text=f"{running}/{max_services}")
            except:
                self.services_value.value_label.config(text="N/A")

            # Get average usage (from logger if available)
            from import_core import COMPONENTS
            logger = COMPONENTS.get('core.logger')

            if logger:
                recent = logger.get_last_n_samples(300)
                if recent:
                    avg_cpu = sum(s.get('cpu_percent', 0) for s in recent) / len(recent)
                    avg_ram = sum(s.get('ram_percent', 0) for s in recent) / len(recent)
                    avg_gpu = sum(s.get('gpu_percent', 0) for s in recent) / len(recent)

                    # Update CPU with gradient progress bar
                    self.avg_cpu_value.value_label.config(text=f"{avg_cpu:.1f}%")
                    cpu_color = self._get_gradient_color(avg_cpu)
                    self.avg_cpu_value.value_label.config(fg=cpu_color)
                    self.avg_cpu_value.progress_bar.config(bg=cpu_color)
                    self.avg_cpu_value.progress_bar.place(relwidth=avg_cpu/100.0)

                    # Update RAM with gradient progress bar
                    self.avg_ram_value.value_label.config(text=f"{avg_ram:.1f}%")
                    ram_color = self._get_gradient_color(avg_ram)
                    self.avg_ram_value.value_label.config(fg=ram_color)
                    self.avg_ram_value.progress_bar.config(bg=ram_color)
                    self.avg_ram_value.progress_bar.place(relwidth=avg_ram/100.0)

                    # Update GPU with gradient progress bar
                    self.avg_gpu_value.value_label.config(text=f"{avg_gpu:.1f}%")
                    gpu_color = self._get_gradient_color(avg_gpu)
                    self.avg_gpu_value.value_label.config(fg=gpu_color)
                    self.avg_gpu_value.progress_bar.config(bg=gpu_color)
                    self.avg_gpu_value.progress_bar.place(relwidth=avg_gpu/100.0)

            # Update TOP processes
            self._update_top_processes()

        except Exception as e:
            print(f"[DayStats] Error updating: {e}")

    def _generate_sparkline(self, values):
        """Generate sparkline from CPU values using Unicode blocks"""
        if not values or len(values) == 0:
            return "▁" * 10  # Empty sparkline

        # Unicode block characters (8 levels)
        blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        # Normalize values to 0-7 range
        max_val = max(values) if max(values) > 0 else 1
        sparkline = ""

        for val in values:
            index = min(7, int((val / max_val) * 7))
            sparkline += blocks[index]

        # Pad with empty blocks if needed
        while len(sparkline) < 10:
            sparkline += "▁"

        return sparkline[:10]  # Limit to 10 characters

    def _update_process_history(self, process_name, cpu_value):
        """Update process CPU history for sparkline"""
        if process_name not in self.process_history:
            self.process_history[process_name] = []

        self.process_history[process_name].append(cpu_value)

        # Keep only last N samples
        if len(self.process_history[process_name]) > self.max_history:
            self.process_history[process_name] = self.process_history[process_name][-self.max_history:]

    def _get_status_indicator(self, cpu_percent):
        """Get colored status indicator based on CPU usage"""
        if cpu_percent > 80:
            return "🔴"  # High usage - red
        elif cpu_percent > 50:
            return "🟡"  # Medium usage - yellow
        elif cpu_percent > 0:
            return "🟢"  # Normal - green
        else:
            return "⚪"  # Inactive - white

    def _update_top_processes(self):
        """Update TOP processes list with info buttons"""
        if not self.data_manager:
            return

        try:
            # Clear old widgets
            for widget in self.process_widgets:
                widget.destroy()
            self.process_widgets = []

            # Get TOP processes by CPU
            top_procs = self.data_manager.get_top_processes_by_time(n=8, metric='cpu')

            # Create row for each process
            for i, proc in enumerate(top_procs, start=1):
                name = proc.get('display_name', proc.get('name', 'unknown'))
                proc_name = proc.get('name', 'unknown')
                avg_cpu = proc.get('avg_cpu', 0)
                avg_ram = proc.get('avg_ram', 0)
                icon = proc.get('icon', '')

                # Update process history for sparkline
                self._update_process_history(proc_name, avg_cpu)

                # Get sparkline and status indicator
                sparkline = self._generate_sparkline(self.process_history.get(proc_name, []))
                status = self._get_status_indicator(avg_cpu)

                # Row frame with subtle border
                row = tk.Frame(
                    self.process_container,
                    bg=THEME["bg_panel"],
                    highlightthickness=1,
                    highlightbackground="#1a1d24",
                    relief="flat"
                )
                row.pack(fill="x", pady=1, padx=2)

                # Process info (left side) with status indicator and sparkline
                info = tk.Label(
                    row,
                    text=f"{status} {i}. {icon}{name[:14]:14s} {sparkline} CPU:{avg_cpu:4.1f}%",
                    font=("Consolas", 8),
                    bg=THEME["bg_panel"],
                    fg=THEME["text"],
                    anchor="w"
                )
                info.pack(side="left", fill="x", expand=True, padx=5)

                # "Get full info" button (right side, MSI style)
                btn = tk.Label(
                    row,
                    text="ℹ",
                    font=("Consolas", 9, "bold"),
                    bg="#0a0c0e",
                    fg="#FFB84D",
                    cursor="hand2",
                    width=2,
                    relief="flat",
                    bd=1,
                    highlightthickness=1,
                    highlightbackground="#FF6B35"
                )
                btn.pack(side="right", padx=2)

                # Bind hover events for tooltip and row highlighting
                btn.bind("<Enter>", lambda e, p=proc_name, r=row, i=info: self._on_info_hover(e, p, r, i))
                btn.bind("<Leave>", lambda e, r=row, i=info: self._on_info_leave(e, r, i))

                self.process_widgets.append(row)

        except Exception as e:
            print(f"[DayStats] Error updating TOP processes: {e}")
            import traceback
            traceback.print_exc()

    def _on_info_hover(self, event, process_name, row, info_label):
        """Show tooltip and highlight row when hovering over info button"""
        # Show tooltip at cursor position
        self.tooltip.show(process_name, event.x_root, event.y_root)

        # Highlight entire row with purple gradient and glow border
        row.config(
            bg="#3d2a54",  # Dark purple gradient color
            highlightbackground="#a855f7",  # Purple glow border
            highlightthickness=2,
            relief="raised"
        )
        info_label.config(bg="#3d2a54")  # Match background

    def _on_info_leave(self, event, row, info_label):
        """Hide tooltip and restore row color when leaving info button"""
        # Hide tooltip
        self.tooltip.hide()

        # Restore original background and border
        row.config(
            bg=THEME["bg_panel"],
            highlightbackground="#1a1d24",
            highlightthickness=1,
            relief="flat"
        )
        info_label.config(bg=THEME["bg_panel"])

    def show(self):
        """Show the page"""
        self.frame.pack(fill="both", expand=True)
        self.update()

    def hide(self):
        """Hide the page"""
        self.frame.pack_forget()
