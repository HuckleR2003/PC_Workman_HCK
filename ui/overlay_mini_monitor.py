"""
Overlay Mini-Monitor - Always-on-top system stats panel
Runs as a separate Tk root window (independent from main app)
Positioned in top-right corner of Windows desktop
"""

import tkinter as tk
import time
import threading

try:
    import psutil
except ImportError:
    psutil = None


class OverlayMiniMonitor:
    """Standalone overlay using its own Tk root (not Toplevel of main app)"""

    def __init__(self, monitor=None, root=None):
        self.monitor = monitor
        self.running = False
        self.session_samples = []
        self.max_samples = 300

        if root:
            self.root = root
            self._owns_root = False
        else:
            self.root = tk.Tk()
            self._owns_root = True

        self.root.title("")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.92)

        # Remove from taskbar on Windows
        self.root.attributes('-toolwindow', True)

        self._position_window()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

    def _position_window(self):
        w, h = 220, 42
        sx = self.root.winfo_screenwidth()
        x = sx - w - 8
        y = 6
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        main = tk.Frame(self.root, bg="#0a0c10", bd=0, relief="flat",
                        highlightthickness=1, highlightbackground="#1e293b")
        main.pack(fill="both", expand=True)

        main.bind("<Button-1>", self._start_drag)
        main.bind("<B1-Motion>", self._drag)

        top = tk.Frame(main, bg="#0a0c10")
        top.pack(fill="x", padx=6, pady=(4, 0))

        self.cpu_lbl = tk.Label(top, text="CPU 0%", font=("Consolas", 8, "bold"),
                                bg="#0a0c10", fg="#3b82f6")
        self.cpu_lbl.pack(side="left")

        self.ram_lbl = tk.Label(top, text="RAM 0%", font=("Consolas", 8, "bold"),
                                bg="#0a0c10", fg="#10b981")
        self.ram_lbl.pack(side="left", padx=(8, 0))

        self.gpu_lbl = tk.Label(top, text="GPU 0%", font=("Consolas", 8, "bold"),
                                bg="#0a0c10", fg="#f59e0b")
        self.gpu_lbl.pack(side="left", padx=(8, 0))

        close_btn = tk.Label(top, text="x", font=("Consolas", 8, "bold"),
                             bg="#0a0c10", fg="#334155", cursor="hand2", padx=2)
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.stop())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#334155"))

        bottom = tk.Frame(main, bg="#0a0c10")
        bottom.pack(fill="x", padx=6, pady=(0, 3))

        self.avg_lbl = tk.Label(bottom, text="AVG  C:0%  R:0%  G:0%",
                                font=("Consolas", 6), bg="#0a0c10", fg="#475569")
        self.avg_lbl.pack(side="left")

    def _start_drag(self, event):
        self._dx = event.x
        self._dy = event.y

    def _drag(self, event):
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _get_current_sample(self):
        if self.monitor and hasattr(self.monitor, "read_snapshot"):
            snap = self.monitor.read_snapshot()
            return {
                "timestamp": snap.get("timestamp", time.time()),
                "cpu_percent": snap.get("cpu_percent", 0.0),
                "ram_percent": snap.get("ram_percent", 0.0),
                "gpu_percent": snap.get("gpu_percent", 0.0),
            }

        if psutil:
            try:
                return {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "ram_percent": psutil.virtual_memory().percent,
                    "gpu_percent": 0.0,
                }
            except Exception:
                pass
        return None

    def _update_loop(self):
        if not self.running:
            return

        try:
            sample = self._get_current_sample()
            if sample:
                self.session_samples.append(sample)
                if len(self.session_samples) > self.max_samples:
                    self.session_samples.pop(0)

                cpu = sample.get("cpu_percent", 0)
                ram = sample.get("ram_percent", 0)
                gpu = sample.get("gpu_percent", 0)

                n = len(self.session_samples)
                avg_c = sum(s.get("cpu_percent", 0) for s in self.session_samples) / n
                avg_r = sum(s.get("ram_percent", 0) for s in self.session_samples) / n
                avg_g = sum(s.get("gpu_percent", 0) for s in self.session_samples) / n

                self.cpu_lbl.config(text=f"CPU {int(cpu)}%")
                self.ram_lbl.config(text=f"RAM {int(ram)}%")
                self.gpu_lbl.config(text=f"GPU {int(gpu)}%")
                self.avg_lbl.config(text=f"AVG  C:{int(avg_c)}%  R:{int(avg_r)}%  G:{int(avg_g)}%")

                self.cpu_lbl.config(fg="#ef4444" if cpu > 80 else "#f59e0b" if cpu > 50 else "#3b82f6")
                self.ram_lbl.config(fg="#ef4444" if ram > 85 else "#f59e0b" if ram > 70 else "#10b981")
                self.gpu_lbl.config(fg="#ef4444" if gpu > 80 else "#f59e0b" if gpu > 50 else "#f59e0b")

        except Exception:
            pass

        if self.running:
            self.root.after(500, self._update_loop)

    def run(self):
        self.running = True
        self.root.after(100, self._update_loop)
        if self._owns_root:
            self.root.mainloop()

    def stop(self):
        self.running = False
        try:
            self.root.withdraw()
        except Exception:
            pass


# Global reference for the overlay running in main app's Tk
_overlay_instance = None


def launch_overlay_in_main_tk(main_root, monitor=None):
    """Launch overlay as a Toplevel of the main Tk root.
    This keeps it in the same mainloop but as a separate desktop window."""
    global _overlay_instance

    # If already running, just show it
    if _overlay_instance and _overlay_instance.running:
        try:
            _overlay_instance.root.deiconify()
            _overlay_instance.root.lift()
            return _overlay_instance
        except Exception:
            pass

    top = tk.Toplevel(main_root)
    overlay = OverlayMiniMonitor(monitor=monitor, root=top)
    overlay._owns_root = False
    overlay.running = True
    overlay.root.after(100, overlay._update_loop)
    _overlay_instance = overlay
    return overlay


def create_overlay_monitor(monitor=None):
    overlay = OverlayMiniMonitor(monitor=monitor)
    overlay.run()
