# ui/main_window.py
"""
UI for PC_Workman_HCK (Prototype v1.0.6 -> v1.0.6+)
- Adds mode buttons (NOW / 1H / 4H)
- NOW: last 30s per-second samples (chart)
- 1H: left small live meter (0.5s) + main chart shows last 60 minute-averages
- process lists show icons/labels (basic)
"""

import tkinter as tk
from tkinter import ttk
import threading, time
from import_core import COMPONENTS
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

EXCLUDE_PROCESSES = ['chrome', 'edge', 'opera', 'firefox', 'brave', 'steam', 'origin', 'epic', 'bethesda', 'ubisoft']
BROWSER_KEYS = ['chrome', 'edge', 'opera', 'firefox', 'brave']
GAME_KEYS = ['steam', 'origin', 'epic', 'bethesda', 'ubisoft']

# mapping keywords -> emoji/icon & label
ICON_MAP = {
    'explorer': '📁',
    'chrome': '⚔️',
    'firefox': '⚔️',
    'edge': '⚔️',
    'opera': '⚔️',
    'brave': '⚔️',
    'steam': '🎮',
    'origin': '🎮',
    'python': '🐍',
    'system idle': '🛌',
    'svchost': '⚙️'
}

def icon_for_name(name: str):
    if not name:
        return ''
    lower = name.lower()
    for k, icon in ICON_MAP.items():
        if k in lower:
            return icon
    return '🔹'

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PC Workman – HCK_Labs")
        self.root.geometry("1000x680")
        self.root.configure(bg="#1c1c1c")
        self.root.resizable(False, False)

        self.logger = COMPONENTS.get('core.logger')
        self.monitor = COMPONENTS.get('core.monitor')

        # mode: 'now' or '1h' or '4h'
        self.mode = 'now'

        self._build_layout()
        self._running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()

    def _build_layout(self):
        header = tk.Label(self.root, text="PC Workman - Resource Monitor (NOW)", font=("Consolas", 16, "bold"), fg="#00FFAA", bg="#1c1c1c")
        header.pack(pady=8)

        # mode buttons
        modes_frame = tk.Frame(self.root, bg="#1c1c1c")
        modes_frame.pack(pady=(0,8))
        self.btn_now = ttk.Button(modes_frame, text="NOW", command=lambda: self.set_mode('now'))
        self.btn_now.grid(row=0, column=0, padx=6)
        self.btn_1h = ttk.Button(modes_frame, text="1H", command=lambda: self.set_mode('1h'))
        self.btn_1h.grid(row=0, column=1, padx=6)
        self.btn_4h = ttk.Button(modes_frame, text="4H", command=lambda: self.set_mode('4h'))
        self.btn_4h.grid(row=0, column=2, padx=6)

        # top indicators
        top_frame = tk.Frame(self.root, bg="#1c1c1c")
        top_frame.pack(fill="x", pady=(4,6))
        self.cpu_label = tk.Label(top_frame, text="CPU: 0%", font=("Consolas", 12), fg="#FF5555", bg="#1c1c1c")
        self.cpu_label.pack(side="left", padx=12)
        self.gpu_label = tk.Label(top_frame, text="GPU: 0%", font=("Consolas", 12), fg="#5599FF", bg="#1c1c1c")
        self.gpu_label.pack(side="left", padx=12)
        self.ram_label = tk.Label(top_frame, text="RAM: 0%", font=("Consolas", 12), fg="#FFFF55", bg="#1c1c1c")
        self.ram_label.pack(side="left", padx=12)

        # chart area
        chart_frame = tk.Frame(self.root, bg="#1c1c1c")
        chart_frame.pack(fill="both", padx=10)

        # small left live meter (for '1h' view: shows current per-second)
        self.left_canvas = tk.Canvas(chart_frame, width=180, height=260, bg="#2b2b2b", highlightthickness=1)
        self.left_canvas.pack(side="left", padx=(0,10))
        self.left_canvas.create_text(90, 12, text="LIVE", font=("Consolas", 10, "bold"), fill="#ffffff")

        # main chart (matplotlib)
        self.fig = Figure(figsize=(8.0, 3.5), dpi=90, facecolor="#262626")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.set_ylim(0, 100)
        self.ax.grid(True, linestyle="--", color="#333333", linewidth=0.5)
        self.line_cpu, = self.ax.plot([], [], color="red", label="CPU %")
        self.line_ram, = self.ax.plot([], [], color="yellow", label="RAM %")
        self.line_gpu, = self.ax.plot([], [], color="blue", label="GPU %")
        self.ax.legend(facecolor="#1e1e1e", labelcolor="white", fontsize=8)
        canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        canvas.get_tk_widget().pack(side="left", padx=6)
        self.canvas = canvas

        # bottom: process lists
        bottom_frame = tk.Frame(self.root, bg="#1c1c1c")
        bottom_frame.pack(fill="x", pady=8, padx=10)

        # user processes
        self.user_frame = tk.Frame(bottom_frame, bg="#262626")
        self.user_frame.pack(side="left", padx=6)
        tk.Label(self.user_frame, text="TOP 5 - User Processes", font=("Consolas", 11, "bold"), fg="#00FFAA", bg="#262626").pack(anchor="w", padx=6, pady=6)
        self.user_text = tk.Text(self.user_frame, width=54, height=10, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 9))
        self.user_text.pack(padx=6, pady=(0,8))
        self.user_text.bind("<Button-1>", self._on_process_click)

        # system processes
        self.sys_frame = tk.Frame(bottom_frame, bg="#262626")
        self.sys_frame.pack(side="right", padx=6)
        tk.Label(self.sys_frame, text="TOP 5 - System Processes", font=("Consolas", 11, "bold"), fg="#00FFAA", bg="#262626").pack(anchor="w", padx=6, pady=6)
        self.sys_text = tk.Text(self.sys_frame, width=54, height=10, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 9))
        self.sys_text.pack(padx=6, pady=(0,8))
        self.sys_text.bind("<Button-1>", self._on_process_click)

        # bottom bar (hck-gpt placeholder)
        self.hckbar = tk.Frame(self.root, bg="#5c2f52", height=80)
        self.hckbar.pack(fill="x", side="bottom")
        self.hck_label = tk.Label(self.hckbar, text="hck_GPT:", fg="#ffefef", bg="#5c2f52", font=("Consolas", 14, "bold"))
        self.hck_label.pack(anchor="w", padx=8, pady=8)

    def set_mode(self, mode):
        if mode not in ('now', '1h', '4h'):
            return
        self.mode = mode
        # update header text for clarity
        header_text = f"PC Workman - Resource Monitor ({mode.upper()})"
        # find header label (first widget)
        try:
            hdr = self.root.winfo_children()[0]
            hdr.config(text=header_text)
        except Exception:
            pass

    def _update_loop(self):
        # update UI in background: live values every 0.5s, charts every 1s
        last_chart_update = 0
        while self._running:
            try:
                now = time.time()
                # live update 0.5s
                self._update_live_labels()
                if now - last_chart_update >= 1.0:
                    self._update_chart()
                    self._update_processes()
                    last_chart_update = now
                time.sleep(0.5)
            except Exception:
                time.sleep(0.5)

    def _update_live_labels(self):
        # show most recent per-second sample (if available)
        if not self.logger:
            return
        last = None
        samples = self.logger.get_last_n_samples(1)
        if samples:
            last = samples[-1]
        else:
            # fallback: read directly from monitor
            if self.monitor:
                s = self.monitor.read_snapshot()
                last = {
                    'cpu_percent': s.get('cpu_percent', 0.0),
                    'ram_percent': s.get('ram_percent', 0.0),
                    'gpu_percent': s.get('gpu_percent', 0.0)
                }
        if last:
            self.cpu_label.config(text=f"CPU: {round(last['cpu_percent'],1)}%")
            self.ram_label.config(text=f"RAM: {round(last['ram_percent'],1)}%")
            self.gpu_label.config(text=f"GPU: {round(last.get('gpu_percent',0.0),1)}%")

        # small left live meter redraw (bar style)
        try:
            self.left_canvas.delete("bar")
            if last:
                cpu = float(last['cpu_percent'])
                ram = float(last['ram_percent'])
            else:
                cpu = ram = 0.0
            # draw cpu bar
            w = 150; h = 200
            # background
            self.left_canvas.create_rectangle(10, 30, 10+w, 30+h, fill="#111111", outline="#444444", tags="bar")
            # CPU rectangle
            cpu_h = int((cpu/100.0)*h)
            self.left_canvas.create_rectangle(10, 30+h-cpu_h, 10+w-40, 30+h, fill="#ff4444", outline="", tags="bar")
            # RAM small overlay
            ram_h = int((ram/100.0)*h)
            self.left_canvas.create_rectangle(10+w-40, 30+h-ram_h, 10+w, 30+h, fill="#ffff66", outline="", tags="bar")
            # texts
            self.left_canvas.create_text(90, 16, text=f"Live — CPU {cpu:.1f}% / RAM {ram:.1f}%", fill="#ffffff", font=("Consolas", 9), tags="bar")
        except Exception:
            pass

    def _update_chart(self):
        if not self.logger:
            return
        try:
            if self.mode == 'now':
                samples = self.logger.get_last_seconds(30)
                if not samples:
                    return
                x = [s["timestamp"] for s in samples]
                cpu = [s["cpu_percent"] for s in samples]
                ram = [s["ram_percent"] for s in samples]
                gpu = [s["gpu_percent"] for s in samples]
                self.ax.clear()
                self.ax.set_facecolor("#1e1e1e")
                self.ax.set_ylim(0, 100)
                self.ax.plot(x, cpu, color="red", label="CPU %")
                self.ax.plot(x, ram, color="yellow", label="RAM %")
                self.ax.plot(x, gpu, color="blue", label="GPU %")
                self.ax.legend(facecolor="#1e1e1e", labelcolor="white", fontsize=8)
                self.ax.set_title("NOW — last 30s", color="white", fontsize=10)
                self.canvas.draw()
            elif self.mode == '1h':
                # get last 60 minute averages
                mins = self.logger.get_last_minutes(60)
                if not mins:
                    return
                x = [m["minute_ts"] for m in mins]
                cpu = [m["cpu_avg"] for m in mins]
                ram = [m["ram_avg"] for m in mins]
                gpu = [m["gpu_avg"] for m in mins]
                self.ax.clear()
                self.ax.set_facecolor("#1e1e1e")
                self.ax.set_ylim(0, 100)
                self.ax.plot(x, cpu, color="red", marker='o', label="CPU % (1m avg)")
                self.ax.plot(x, ram, color="yellow", marker='o', label="RAM % (1m avg)")
                self.ax.plot(x, gpu, color="blue", marker='o', label="GPU % (1m avg)")
                self.ax.legend(facecolor="#1e1e1e", labelcolor="white", fontsize=8)
                self.ax.set_title("1H — minute averages (last 60)", color="white", fontsize=10)
                self.canvas.draw()
            else:
                # placeholder 4h: reuse now for now
                samples = self.logger.get_last_seconds(30)
                if not samples:
                    return
                x = [s["timestamp"] for s in samples]
                cpu = [s["cpu_percent"] for s in samples]
                self.ax.clear()
                self.ax.plot(x, cpu, color="red", label="CPU %")
                self.ax.set_title("4H (placeholder) - showing NOW", color="white")
                self.canvas.draw()
        except Exception:
            pass

    def _update_processes(self):
        if not self.monitor:
            return
        # user top processes (exclude system-like)
        procs = self.monitor.top_processes(20, by="cpu+ram")
        user_procs = [p for p in procs if not any(ex in (p['name'] or '').lower() for ex in EXCLUDE_PROCESSES)]
        user_procs = user_procs[:5]
        # system-like processes (simple heuristic)
        sys_candidates = [p for p in procs if any(k in (p['name'] or '').lower() for k in ['system', 'svchost', 'dllhost', 'services'])]
        sys_procs = sys_candidates[:5]

        # populate user_text with icons
        self.user_text.delete("1.0", tk.END)
        for p in user_procs:
            name = p['name'] or 'unknown'
            icon = icon_for_name(name)
            line = f"{icon} {name:<28} CPU:{p['cpu_percent']:<6} RAM:{p['ram_MB']:.1f} MB\n"
            self.user_text.insert(tk.END, line)

        self.sys_text.delete("1.0", tk.END)
        for p in sys_procs:
            name = p['name'] or 'unknown'
            icon = icon_for_name(name)
            line = f"{icon} {name:<28} CPU:{p['cpu_percent']:<6} RAM:{p['ram_MB']:.1f} MB\n"
            self.sys_text.insert(tk.END, line)

    def _on_process_click(self, event):
        # show a small popup with line contents clicked
        widget = event.widget
        index = widget.index(f"@{event.x},{event.y}")
        line = widget.get(f"{index} linestart", f"{index} lineend")
        if not line.strip():
            return
        popup = tk.Toplevel(self.root)
        popup.title("Process details")
        popup.geometry("420x120")
        popup.configure(bg="#2b2b2b")
        tk.Label(popup, text="Details:", fg="#ffffff", bg="#2b2b2b", font=("Consolas", 11, "bold")).pack(anchor="w", padx=8, pady=6)
        tk.Label(popup, text=line, fg="#ffffff", bg="#2b2b2b", font=("Consolas", 10)).pack(anchor="w", padx=8, pady=6)
        # small hint for browsers/players
        lower = line.lower()
        hint = ""
        if any(k in lower for k in BROWSER_KEYS):
            hint = "Mocny rywal ;) (Przeglądarka)"
        elif any(k in lower for k in GAME_KEYS):
            hint = "Game / Launcher detected"
        if hint:
            tk.Label(popup, text=hint, fg="#ffd700", bg="#2b2b2b", font=("Consolas", 10, "italic")).pack(anchor="w", padx=8, pady=(4,0))

    def run(self):
        try:
            self.root.mainloop()
        finally:
            self._running = False
