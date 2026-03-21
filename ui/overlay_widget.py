"""
Overlay Widget - Always-On-Top System Monitor
Floating widget in top-right corner showing CPU, RAM, GPU usage
No window frame, always visible, draggable
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time

try:
    import psutil
except ImportError:
    psutil = None

try:
    from core.hardware_sensors import get_gpu_usage
except ImportError:
    get_gpu_usage = None


class OverlayWidget:
    """
    Floating overlay widget showing system stats
    - Always on top
    - No window frame
    - Draggable
    - Auto-updating every 2 seconds
    """

    def __init__(self):
        self.root = tk.Tk()

        # Window configuration
        self.root.title("PC Workman Monitor")
        self.root.overrideredirect(True)  # Remove window frame
        self.root.attributes('-topmost', True)  # Always on top
        self.root.attributes('-alpha', 0.95)  # Slight transparency

        # Widget size
        self.width = 210
        self.height = 40

        # Position in top-right corner (with 20px margin)
        screen_width = self.root.winfo_screenwidth()
        x = screen_width - self.width - 20
        y = 20
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        # Dragging support
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0

        self._build_ui()
        self._start_update_loop()

    def _build_ui(self):
        """Build widget UI"""
        # Main container (dark background like in screenshot)
        self.container = tk.Frame(self.root, bg="#1a1d29",
                                 highlightbackground="#2d3142",
                                 highlightthickness=1)
        self.container.pack(fill="both", expand=True)

        # Bind dragging
        self.container.bind("<Button-1>", self._start_drag)
        self.container.bind("<B1-Motion>", self._on_drag)
        self.container.bind("<ButtonRelease-1>", self._stop_drag)

        # Stats row
        stats_frame = tk.Frame(self.container, bg="#1a1d29")
        stats_frame.pack(expand=True, fill="both", padx=8, pady=8)

        # Font for labels
        label_font = tkfont.Font(family="Segoe UI", size=9, weight="normal")
        value_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        # CPU
        cpu_frame = tk.Frame(stats_frame, bg="#1a1d29")
        cpu_frame.pack(side="left", padx=5)

        tk.Label(cpu_frame, text="CPU:", font=label_font,
                bg="#1a1d29", fg="#94a3b8").pack(side="left")
        self.cpu_label = tk.Label(cpu_frame, text="0%", font=value_font,
                                 bg="#1a1d29", fg="#3b82f6")
        self.cpu_label.pack(side="left", padx=2)

        # RAM
        ram_frame = tk.Frame(stats_frame, bg="#1a1d29")
        ram_frame.pack(side="left", padx=5)

        tk.Label(ram_frame, text="RAM:", font=label_font,
                bg="#1a1d29", fg="#94a3b8").pack(side="left")
        self.ram_label = tk.Label(ram_frame, text="0%", font=value_font,
                                 bg="#1a1d29", fg="#10b981")
        self.ram_label.pack(side="left", padx=2)

        # GPU
        gpu_frame = tk.Frame(stats_frame, bg="#1a1d29")
        gpu_frame.pack(side="left", padx=5)

        tk.Label(gpu_frame, text="GPU:", font=label_font,
                bg="#1a1d29", fg="#94a3b8").pack(side="left")
        self.gpu_label = tk.Label(gpu_frame, text="0%", font=value_font,
                                 bg="#1a1d29", fg="#f59e0b")
        self.gpu_label.pack(side="left", padx=2)

        # Close button (small X in top-right)
        close_btn = tk.Label(self.container, text="✕", font=("Segoe UI", 10),
                           bg="#1a1d29", fg="#64748b", cursor="hand2",
                           padx=5, pady=2)
        close_btn.place(relx=1.0, x=-5, y=2, anchor="ne")
        close_btn.bind("<Button-1>", lambda e: self.close())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#64748b"))

        # Minimize button (small dash)
        minimize_btn = tk.Label(self.container, text="—", font=("Segoe UI", 8),
                              bg="#1a1d29", fg="#64748b", cursor="hand2",
                              padx=5, pady=2)
        minimize_btn.place(relx=1.0, x=-25, y=2, anchor="ne")
        minimize_btn.bind("<Button-1>", lambda e: self.toggle_minimize())
        minimize_btn.bind("<Enter>", lambda e: minimize_btn.config(fg="#06b6d4"))
        minimize_btn.bind("<Leave>", lambda e: minimize_btn.config(fg="#64748b"))

        self.minimized = False

    def _start_drag(self, event):
        """Start dragging"""
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def _on_drag(self, event):
        """Handle drag"""
        if self.dragging:
            x = self.root.winfo_x() + event.x - self.drag_start_x
            y = self.root.winfo_y() + event.y - self.drag_start_y
            self.root.geometry(f"+{x}+{y}")

    def _stop_drag(self, event):
        """Stop dragging"""
        self.dragging = False

    def toggle_minimize(self):
        """Toggle minimized state"""
        if self.minimized:
            # Restore
            self.root.geometry(f"{self.width}x{self.height}")
            self.minimized = False
        else:
            # Minimize (show only title bar area)
            self.root.geometry(f"{self.width}x{20}")
            self.minimized = True

    def _start_update_loop(self):
        """Start background update loop"""
        def update_stats():
            while True:
                try:
                    # Get system stats
                    cpu = psutil.cpu_percent(interval=0.5) if psutil else 0
                    ram = psutil.virtual_memory().percent if psutil else 0

                    # Get GPU usage
                    gpu = 0
                    if get_gpu_usage:
                        try:
                            gpu = get_gpu_usage()
                        except:
                            pass

                    # Update labels (thread-safe)
                    self.root.after(0, self._update_labels, cpu, ram, gpu)

                except Exception as e:
                    print(f"[OverlayWidget] Update error: {e}")

                time.sleep(2)  # Update every 2 seconds

        # Start update thread
        update_thread = threading.Thread(target=update_stats, daemon=True)
        update_thread.start()

    def _update_labels(self, cpu, ram, gpu):
        """Update labels with new values"""
        try:
            # Update text
            self.cpu_label.config(text=f"{int(cpu)}%")
            self.ram_label.config(text=f"{int(ram)}%")
            self.gpu_label.config(text=f"{int(gpu)}%")

            # Color coding based on usage
            # CPU
            if cpu > 80:
                self.cpu_label.config(fg="#ef4444")  # Red
            elif cpu > 50:
                self.cpu_label.config(fg="#f59e0b")  # Orange
            else:
                self.cpu_label.config(fg="#3b82f6")  # Blue

            # RAM
            if ram > 80:
                self.ram_label.config(fg="#ef4444")
            elif ram > 50:
                self.ram_label.config(fg="#f59e0b")
            else:
                self.ram_label.config(fg="#10b981")  # Green

            # GPU
            if gpu > 80:
                self.gpu_label.config(fg="#ef4444")
            elif gpu > 50:
                self.gpu_label.config(fg="#f59e0b")
            else:
                self.gpu_label.config(fg="#f59e0b")  # Orange default

        except Exception as e:
            print(f"[OverlayWidget] Label update error: {e}")

    def close(self):
        """Close widget"""
        self.root.quit()
        self.root.destroy()

    def run(self):
        """Run widget main loop"""
        self.root.mainloop()


def create_overlay_widget():
    """Create and run overlay widget"""
    widget = OverlayWidget()
    widget.run()


if __name__ == "__main__":
    # Test overlay widget
    create_overlay_widget()
