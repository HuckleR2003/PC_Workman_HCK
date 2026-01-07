"""
Overlay Mini-Monitor - Always-on-top system stats display
Displays in top-right corner of screen, above all windows
"""

import tkinter as tk
import psutil
import time


class OverlayMiniMonitor:
    """
    Always-on-top mini monitor window
    Shows CPU/RAM/GPU stats in top-right corner of screen
    """

    def __init__(self, monitor=None):
        self.monitor = monitor
        self.running = False

        # Session tracking for averages
        self.session_samples = []
        self.max_samples = 300  # Last 300 samples (~2 minutes at 0.4s interval)

        # Create window
        self.root = tk.Toplevel()
        self.root.title("PC Workman Monitor")

        # Window properties - ALWAYS ON TOP!
        self.root.overrideredirect(True)  # No window decorations
        self.root.attributes('-topmost', True)  # Always on top
        self.root.attributes('-alpha', 0.95)  # Slightly transparent

        # Position in top-right corner
        self._position_window()

        # Build UI
        self._build_ui()

        # Handle close
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

    def _position_window(self):
        """Position window in top-right corner of screen"""
        # Window size
        width = 180
        height = 80

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Position: 10px from right edge, 10px from top
        x = screen_width - width - 10
        y = 10

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        """Build monitor UI - CYBERPUNK STYLE! 💎"""
        # Main container
        main = tk.Frame(self.root, bg="#0f1117", relief="flat", bd=0)
        main.pack(fill="both", expand=True, padx=2, pady=2)

        # Header with drag handle
        header = tk.Frame(main, bg="#1a1d24", cursor="fleur")
        header.pack(fill="x")

        tk.Label(
            header,
            text="⚡ PC STATS",
            font=("Segoe UI Semibold", 8, "bold"),
            bg="#1a1d24",
            fg="#8b5cf6"
        ).pack(side="left", padx=6, pady=3)

        # Close button
        close_btn = tk.Label(
            header,
            text="✕",
            font=("Segoe UI", 9),
            bg="#1a1d24",
            fg="#64748b",
            cursor="hand2"
        )
        close_btn.pack(side="right", padx=6)
        close_btn.bind("<Button-1>", lambda e: self.stop())

        # Make header draggable
        header.bind("<Button-1>", self._start_drag)
        header.bind("<B1-Motion>", self._drag)

        # === LIVE STATS ===
        stats_frame = tk.Frame(main, bg="#0f1117")
        stats_frame.pack(fill="both", expand=True, padx=6, pady=(3, 1))

        # CPU row
        cpu_row = tk.Frame(stats_frame, bg="#0f1117")
        cpu_row.pack(fill="x", pady=1)

        tk.Label(
            cpu_row,
            text="CPU:",
            font=("Segoe UI Semibold", 7),
            bg="#0f1117",
            fg="#64748b",
            width=4,
            anchor="w"
        ).pack(side="left")

        self.cpu_label = tk.Label(
            cpu_row,
            text="0%",
            font=("Consolas", 8, "bold"),
            bg="#0f1117",
            fg="#3b82f6"  # Blue
        )
        self.cpu_label.pack(side="left", padx=3)

        self.cpu_avg_label = tk.Label(
            cpu_row,
            text="avg: 0%",
            font=("Consolas", 6),
            bg="#0f1117",
            fg="#64748b"
        )
        self.cpu_avg_label.pack(side="right")

        # RAM row
        ram_row = tk.Frame(stats_frame, bg="#0f1117")
        ram_row.pack(fill="x", pady=1)

        tk.Label(
            ram_row,
            text="RAM:",
            font=("Segoe UI Semibold", 7),
            bg="#0f1117",
            fg="#64748b",
            width=4,
            anchor="w"
        ).pack(side="left")

        self.ram_label = tk.Label(
            ram_row,
            text="0%",
            font=("Consolas", 8, "bold"),
            bg="#0f1117",
            fg="#10b981"  # Green
        )
        self.ram_label.pack(side="left", padx=3)

        self.ram_avg_label = tk.Label(
            ram_row,
            text="avg: 0%",
            font=("Consolas", 6),
            bg="#0f1117",
            fg="#64748b"
        )
        self.ram_avg_label.pack(side="right")

        # GPU row
        gpu_row = tk.Frame(stats_frame, bg="#0f1117")
        gpu_row.pack(fill="x", pady=1)

        tk.Label(
            gpu_row,
            text="GPU:",
            font=("Segoe UI Semibold", 7),
            bg="#0f1117",
            fg="#64748b",
            width=4,
            anchor="w"
        ).pack(side="left")

        self.gpu_label = tk.Label(
            gpu_row,
            text="0%",
            font=("Consolas", 8, "bold"),
            bg="#0f1117",
            fg="#f59e0b"  # Orange
        )
        self.gpu_label.pack(side="left", padx=3)

        self.gpu_avg_label = tk.Label(
            gpu_row,
            text="avg: 0%",
            font=("Consolas", 6),
            bg="#0f1117",
            fg="#64748b"
        )
        self.gpu_avg_label.pack(side="right")

    def _start_drag(self, event):
        """Start dragging window"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _drag(self, event):
        """Drag window to new position"""
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def _get_current_sample(self):
        """Get current system stats"""
        if self.monitor and hasattr(self.monitor, "read_snapshot"):
            return self.monitor.read_snapshot()

        # Fallback to psutil
        try:
            return {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_percent": psutil.virtual_memory().percent,
                "gpu_percent": 0.0  # TODO: GPU detection
            }
        except:
            return None

    def _update_loop(self):
        """Update loop - runs every 0.4s"""
        if not self.running:
            return

        try:
            # Get current sample
            sample = self._get_current_sample()

            if sample:
                # Add to session samples
                self.session_samples.append(sample)

                # Keep only last N samples
                if len(self.session_samples) > self.max_samples:
                    self.session_samples.pop(0)

                # Calculate averages
                avg_cpu = sum(s.get("cpu_percent", 0) for s in self.session_samples) / len(self.session_samples)
                avg_ram = sum(s.get("ram_percent", 0) for s in self.session_samples) / len(self.session_samples)
                avg_gpu = sum(s.get("gpu_percent", 0) for s in self.session_samples) / len(self.session_samples)

                # Update labels
                cpu = sample.get("cpu_percent", 0)
                ram = sample.get("ram_percent", 0)
                gpu = sample.get("gpu_percent", 0)

                self.cpu_label.config(text=f"{int(cpu)}%")
                self.ram_label.config(text=f"{int(ram)}%")
                self.gpu_label.config(text=f"{int(gpu)}%")

                self.cpu_avg_label.config(text=f"avg: {int(avg_cpu)}%")
                self.ram_avg_label.config(text=f"avg: {int(avg_ram)}%")
                self.gpu_avg_label.config(text=f"avg: {int(avg_gpu)}%")

        except Exception as e:
            print(f"[OverlayMonitor] Update error: {e}")

        # Schedule next update
        if self.running:
            self.root.after(400, self._update_loop)  # 0.4s = 400ms

    def run(self):
        """Start monitor"""
        self.running = True
        self.root.after(100, self._update_loop)  # Start after 100ms
        self.root.mainloop()

    def stop(self):
        """Stop monitor"""
        self.running = False
        try:
            self.root.destroy()
        except:
            pass


def create_overlay_monitor(monitor=None):
    """
    Create and run overlay monitor

    Args:
        monitor: Optional monitor instance to use for data
    """
    overlay = OverlayMiniMonitor(monitor=monitor)
    overlay.run()


if __name__ == "__main__":
    # Test standalone
    create_overlay_monitor()
