# ui/overlay_mini_monitor.py
"""
Overlay Mini-Monitor  - always-on-top desktop panel
• Compact bar: CPU / RAM / GPU with fill-banners + session averages
• Expandable process list (top 6 by RAM) with KILL / FREEZE actions
• Draggable, borderless, semi-transparent
"""
from __future__ import annotations

import tkinter as tk
import time
import os
from collections import deque
from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None


# ── Process library (optional) ────────────────────────────────────────────────

try:
    _lib_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "hck_gpt", "process_library.py")
    )
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("_proc_lib_mod", _lib_path)
    _mod  = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _PROC_LIB = _mod.ProcessLibrary()
except Exception:
    _PROC_LIB = None


# ── Palette ───────────────────────────────────────────────────────────────────

_BG          = "#080b10"
_BORDER      = "#1a2436"
_HEADER_BG   = "#0b0f16"

# Bar track backgrounds - very dark, colour-tinted so they read as "CPU blue space"
_CPU_TRACK   = "#0c1728"
_RAM_TRACK   = "#091810"
_GPU_TRACK   = "#181000"

# Bar fill - normal load (delicate, not saturated)
_CPU_FILL    = "#2563a8"    # soft blue
_RAM_FILL    = "#157248"    # soft emerald
_GPU_FILL    = "#8a6200"    # soft amber

# Fill overrides for warm / critical thresholds
_WARM_FILL   = "#a06800"    # deep amber
_CRIT_FILL   = "#b52020"    # dark red

# Labels / chrome
_LABEL_COL   = "#c9cdd5"    # near-white label text  (modern, clean)
_AVG_COL     = "#3d4e62"
_CLOSE_COL   = "#2e3d52"
_CLOSE_HOV   = "#ef4444"
_ARROW_COL   = "#8e1136"    # bordeaux expand arrow
_ARROW_HOV   = "#e11d48"

# Process panel
_PROC_BG     = "#0f0a24"
_PROC_BORDER = "#2a1058"
_PROC_RAM_FG = "#fbbf24"
_PROC_NAME   = "#dde3ec"

_KILL_BG     = "#1a1828"
_KILL_FG     = "#e04040"
_KILL_HOV    = "#6e1010"
_FREEZE_BG   = "#1a1828"
_FREEZE_FG   = "#7a8fa8"
_FREEZE_HOV  = "#283448"


# ── Font system ───────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# ── Fonts ─────────────────────────────────────────────────────────────────────

_F_LABEL     = ("Segoe UI Light",    7)     # CPU / RAM / GPU header text (Light = intentional)
_F_AVG       = (_BODY,               6)     # AVG row - compact
_F_CLOSE     = (_BODY,               9)     # ×
_F_ARROW     = (_BODY,              10)     # ▾ / ▴
_F_PROC_RAM  = ("Segoe UI Black",    7)     # Black weight = intentional
_F_PROC_NAME = (_HDR,                7)
_F_BTN       = (_HDR,                6)     # compact kill/freeze


# ── Geometry ─────────────────────────────────────────────────────────────────

_BAR_H       = 5                    # fill-bar height (px)
_W           = 175                  # ≈45 % narrower than the original 318
_H_COLLAPSED = 46                   # ≈15 % shorter than original 54
_PROC_ROWS   = 6
_ROW_H       = 30
_H_EXPANDED  = _H_COLLAPSED + 5 + _PROC_ROWS * _ROW_H + 5    # ≈ 236


# ── Widget helpers ────────────────────────────────────────────────────────────

def _make_stat_cell(
    parent: tk.Widget,
    label: str,
    fill_color: str,
    track_color: str,
    col: int,
) -> dict:
    """
    One stat column (in a 3-column grid): label on top, fill-banner below.
    Returns a dict with the fill-frame ref so the update loop can animate it.
    """
    cell = tk.Frame(parent, bg=_HEADER_BG)
    cell.grid(row=0, column=col, sticky="ew", padx=(2 if col else 0, 2))

    # Label - white-ish, light weight, centred
    tk.Label(
        cell, text=label,
        font=_F_LABEL,
        bg=_HEADER_BG, fg=_LABEL_COL,
        anchor="center",
    ).pack(fill="x")

    # Track (dark background)
    track = tk.Frame(cell, bg=track_color, height=_BAR_H)
    track.pack(fill="x", pady=(2, 0))
    track.pack_propagate(False)

    # Fill banner - width driven by place(relwidth=…) in update loop
    fill = tk.Frame(track, bg=fill_color, height=_BAR_H)
    fill.place(x=0, y=0, relwidth=0.0, relheight=1.0)

    return {"fill": fill, "base_color": fill_color}


def _update_bar(cell: dict, pct: float, color: str) -> None:
    """Animate fill-banner width + colour."""
    if cell:
        cell["fill"].place(relwidth=min(max(pct / 100.0, 0.0), 1.0))
        cell["fill"].config(bg=color)


# ── Main class ────────────────────────────────────────────────────────────────

class OverlayMiniMonitor:
    """Standalone overlay using its own Tk root (or a Toplevel of the main app)."""

    def __init__(self, monitor=None, root: Optional[tk.Misc] = None):
        self.monitor  = monitor
        self.running  = False

        # O(1) rolling sample buffer + running sums
        self._samples: deque = deque(maxlen=300)
        self._sum_cpu: float = 0.0
        self._sum_ram: float = 0.0
        self._sum_gpu: float = 0.0

        self._expanded    = False
        self._proc_rows: list = []

        if root:
            self.root      = root
            self._owns_root = False
        else:
            self.root      = tk.Tk()
            self._owns_root = True

        self.root.title("")
        self.root.overrideredirect(True)
        # topmost removed — was causing interference with games and fullscreen apps
        self.root.attributes("-alpha",      0.86)   # ~8 % more transparent than before
        self.root.attributes("-toolwindow", True)   # hide from taskbar

        self._position_window()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.stop)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _position_window(self):
        sx = self.root.winfo_screenwidth()
        self.root.geometry(f"{_W}x{_H_COLLAPSED}+{sx - _W - 8}+6")

    def _bind_drag(self, widget: tk.Widget):
        widget.bind("<Button-1>",  self._start_drag)
        widget.bind("<B1-Motion>", self._drag)

    def _build_ui(self):
        # 1-px border via outer frame bg colour
        self._outer = tk.Frame(self.root, bg=_BORDER, highlightthickness=0)
        self._outer.pack(fill="both", expand=True)
        self._bind_drag(self._outer)

        self._inner = tk.Frame(self._outer, bg=_HEADER_BG)
        self._inner.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_stats_bar()
        self._build_avg_row()
        self._build_process_panel()

    def _build_stats_bar(self):
        """Top area: 3 equal stat columns + arrow + close on the right."""
        bar = tk.Frame(self._inner, bg=_HEADER_BG)
        bar.pack(fill="x", padx=6, pady=(5, 2))
        self._bind_drag(bar)

        # ── Right controls (close + arrow) - packed first so they own fixed space ──
        ctrl = tk.Frame(bar, bg=_HEADER_BG)
        ctrl.pack(side="right")

        close = tk.Label(ctrl, text="×", font=_F_CLOSE,
                         bg=_HEADER_BG, fg=_CLOSE_COL, cursor="hand2", padx=2)
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: self.stop())
        close.bind("<Enter>",    lambda e: close.config(fg=_CLOSE_HOV))
        close.bind("<Leave>",    lambda e: close.config(fg=_CLOSE_COL))

        self._arrow = tk.Label(ctrl, text="▾", font=_F_ARROW,
                               bg=_HEADER_BG, fg=_ARROW_COL, cursor="hand2", padx=3)
        self._arrow.pack(side="right")
        self._arrow.bind("<Button-1>", self._toggle_expand)
        self._arrow.bind("<Enter>",    lambda e: self._arrow.config(fg=_ARROW_HOV))
        self._arrow.bind("<Leave>",    lambda e: self._arrow.config(fg=_ARROW_COL))

        # ── Three equal-width stat cells (grid with uniform weight) ──────────
        stats = tk.Frame(bar, bg=_HEADER_BG)
        stats.pack(side="left", fill="x", expand=True)
        stats.columnconfigure(0, weight=1, uniform="stat")
        stats.columnconfigure(1, weight=1, uniform="stat")
        stats.columnconfigure(2, weight=1, uniform="stat")
        self._bind_drag(stats)

        self._cpu_val = _make_stat_cell(stats, "CPU", _CPU_FILL, _CPU_TRACK, col=0)
        self._ram_val = _make_stat_cell(stats, "RAM", _RAM_FILL, _RAM_TRACK, col=1)
        self._gpu_val = _make_stat_cell(stats, "GPU", _GPU_FILL, _GPU_TRACK, col=2)

    def _build_avg_row(self):
        """Compact one-line session averages."""
        avg_bar = tk.Frame(self._inner, bg=_HEADER_BG)
        avg_bar.pack(fill="x", padx=6, pady=(0, 5))
        self._bind_drag(avg_bar)

        self._avg_lbl = tk.Label(
            avg_bar,
            text="AVG  C:0%  R:0%  G:0%",
            font=_F_AVG,
            bg=_HEADER_BG, fg=_AVG_COL,
            anchor="center",
        )
        self._avg_lbl.pack(fill="x")

    def _build_process_panel(self):
        """Expandable process list - hidden by default."""
        self._sep = tk.Frame(self._inner, bg=_PROC_BORDER, height=1)
        self._proc_frame = tk.Frame(self._inner, bg=_PROC_BG)

        self._proc_row_widgets: list[dict] = []
        for i in range(_PROC_ROWS):
            row = self._make_proc_row(self._proc_frame, i)
            row["frame"].pack(fill="x")
            if i < _PROC_ROWS - 1:
                tk.Frame(self._proc_frame, bg=_PROC_BORDER, height=1).pack(fill="x")
            self._proc_row_widgets.append(row)

    # ── Process row factory ───────────────────────────────────────────────────

    def _make_proc_row(self, parent: tk.Widget, idx: int) -> dict:
        frame = tk.Frame(parent, bg=_PROC_BG, height=_ROW_H)
        frame.pack_propagate(False)

        left = tk.Frame(frame, bg=_PROC_BG)
        left.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=2)

        ram_lbl = tk.Label(
            left, text="",
            font=_F_PROC_RAM, bg=_PROC_BG, fg=_PROC_RAM_FG,
            anchor="w", width=5,
        )
        ram_lbl.pack(side="left")

        name_lbl = tk.Label(
            left, text="-",
            font=_F_PROC_NAME, bg=_PROC_BG, fg=_PROC_NAME,
            anchor="w",
        )
        name_lbl.pack(side="left", padx=(3, 0))

        right = tk.Frame(frame, bg=_PROC_BG)
        right.pack(side="right", padx=(0, 4), pady=4)

        kill_btn = tk.Label(
            right, text="KILL",
            font=_F_BTN, bg=_KILL_BG, fg=_KILL_FG,
            cursor="hand2", padx=5, pady=2,
        )
        kill_btn.pack(side="right", padx=(3, 0))
        kill_btn.bind("<Enter>", lambda e, b=kill_btn: b.config(bg=_KILL_HOV))
        kill_btn.bind("<Leave>", lambda e, b=kill_btn: b.config(bg=_KILL_BG))

        freeze_btn = tk.Label(
            right, text="FREEZE",
            font=_F_BTN, bg=_FREEZE_BG, fg=_FREEZE_FG,
            cursor="hand2", padx=5, pady=2,
        )
        freeze_btn.pack(side="right")
        freeze_btn.bind("<Enter>", lambda e, b=freeze_btn: b.config(bg=_FREEZE_HOV))
        freeze_btn.bind("<Leave>", lambda e, b=freeze_btn: b.config(bg=_FREEZE_BG))

        return {
            "frame":      frame,
            "ram_lbl":    ram_lbl,
            "name_lbl":   name_lbl,
            "kill_btn":   kill_btn,
            "freeze_btn": freeze_btn,
            "pid":        None,
        }

    # ── Expand / Collapse ─────────────────────────────────────────────────────

    def _toggle_expand(self, _=None):
        if self._expanded:
            self._collapse()
        else:
            self._expand()

    def _expand(self):
        self._expanded = True
        self._arrow.config(text="▴")
        self._sep.pack(fill="x")
        self._proc_frame.pack(fill="x")
        self.root.geometry(
            f"{_W}x{_H_EXPANDED}+{self.root.winfo_x()}+{self.root.winfo_y()}"
        )
        self._refresh_process_list()

    def _collapse(self):
        self._expanded = False
        self._arrow.config(text="▾")
        self._proc_frame.pack_forget()
        self._sep.pack_forget()
        self.root.geometry(
            f"{_W}x{_H_COLLAPSED}+{self.root.winfo_x()}+{self.root.winfo_y()}"
        )

    # ── Process list ──────────────────────────────────────────────────────────

    def _top_processes(self) -> list[dict]:
        if not psutil:
            return []
        procs = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    info = p.info
                    mem  = info.get("memory_percent") or 0.0
                    if mem > 0:
                        procs.append({
                            "pid":  info["pid"],
                            "name": info["name"] or "unknown",
                            "ram":  round(mem, 1),
                        })
                    if len(procs) >= 128:
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        procs.sort(key=lambda x: x["ram"], reverse=True)
        return procs[:_PROC_ROWS]

    def _refresh_process_list(self):
        procs = self._top_processes()
        for i, row in enumerate(self._proc_row_widgets):
            if i < len(procs):
                p    = procs[i]
                pid  = p["pid"]
                name = p["name"].lower()
                ram  = p["ram"]

                display_name = p["name"]
                if _PROC_LIB:
                    info = _PROC_LIB.get_process_info(name)
                    if info and info.get("name"):
                        display_name = info["name"]

                row["pid"] = pid
                row["ram_lbl"].config(text=f"{ram:4.1f}%")
                row["name_lbl"].config(text=display_name[:14])
                row["frame"].config(bg=_PROC_BG)

                row["kill_btn"].bind(
                    "<Button-1>",
                    lambda e, p=pid, r=row: self._kill_process(p, r),
                )
                row["freeze_btn"].bind(
                    "<Button-1>",
                    lambda e, p=pid, r=row: self._freeze_process(p, r),
                )
            else:
                row["pid"] = None
                row["ram_lbl"].config(text="")
                row["name_lbl"].config(text="-")
                row["kill_btn"].unbind("<Button-1>")
                row["freeze_btn"].unbind("<Button-1>")

    # ── Process actions ───────────────────────────────────────────────────────

    def _kill_process(self, pid: int, row: dict):
        if not psutil or not pid:
            return
        try:
            psutil.Process(pid).kill()
            row["frame"].config(bg="#3b0000")
            self.root.after(400, self._refresh_process_list)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            print(f"[Overlay] kill {pid}: {exc}")

    def _freeze_process(self, pid: int, row: dict):
        if not psutil or not pid:
            return
        try:
            proc   = psutil.Process(pid)
            status = proc.status()
            if status == psutil.STATUS_STOPPED:
                proc.resume()
                row["freeze_btn"].config(fg=_FREEZE_FG, bg=_FREEZE_BG)
            else:
                proc.suspend()
                row["freeze_btn"].config(fg="#fbbf24", bg="#2d2200")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            print(f"[Overlay] freeze {pid}: {exc}")

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _start_drag(self, event):
        self._dx = event.x
        self._dy = event.y

    def _drag(self, event):
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    # ── Data ──────────────────────────────────────────────────────────────────

    def _get_sample(self) -> Optional[dict]:
        if self.monitor and hasattr(self.monitor, "read_snapshot"):
            snap = self.monitor.read_snapshot()
            return {
                "timestamp":   snap.get("timestamp",   time.time()),
                "cpu_percent": snap.get("cpu_percent",  0.0),
                "ram_percent": snap.get("ram_percent",  0.0),
                "gpu_percent": snap.get("gpu_percent",  0.0),
            }
        if psutil:
            try:
                return {
                    "timestamp":   time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "ram_percent": psutil.virtual_memory().percent,
                    "gpu_percent": 0.0,
                }
            except Exception:
                pass
        return None

    # ── Update loop ───────────────────────────────────────────────────────────

    def _update_loop(self):
        if not self.running:
            return
        try:
            sample = self._get_sample()
            if sample:
                # O(1) rolling buffer - subtract evicted oldest, add new
                if len(self._samples) == self._samples.maxlen:
                    oldest = self._samples[0]
                    self._sum_cpu -= oldest["cpu_percent"]
                    self._sum_ram -= oldest["ram_percent"]
                    self._sum_gpu -= oldest["gpu_percent"]
                self._samples.append(sample)
                self._sum_cpu += sample["cpu_percent"]
                self._sum_ram += sample["ram_percent"]
                self._sum_gpu += sample["gpu_percent"]

                cpu = sample["cpu_percent"]
                ram = sample["ram_percent"]
                gpu = sample["gpu_percent"]

                n     = len(self._samples)
                avg_c = self._sum_cpu / n
                avg_r = self._sum_ram / n
                avg_g = self._sum_gpu / n

                # Fill-banner colour thresholds
                def _bar_color(val: float, base: str) -> str:
                    if val > 85:
                        return _CRIT_FILL
                    if val > 55:
                        return _WARM_FILL
                    return base

                _update_bar(self._cpu_val, cpu, _bar_color(cpu, _CPU_FILL))
                _update_bar(self._ram_val, ram, _bar_color(ram, _RAM_FILL))
                _update_bar(self._gpu_val, gpu, _bar_color(gpu, _GPU_FILL))

                self._avg_lbl.config(
                    text=f"AVG  C:{int(avg_c)}%  R:{int(avg_r)}%  G:{int(avg_g)}%"
                )

                # Refresh process list every ~2 s (every 4 ticks @ 500 ms)
                if self._expanded and len(self._samples) % 4 == 0:
                    self._refresh_process_list()

        except Exception:
            pass

        if self.running:
            self.root.after(500, self._update_loop)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

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


# ── Public launchers ──────────────────────────────────────────────────────────

_overlay_instance: Optional[OverlayMiniMonitor] = None


def launch_overlay_in_main_tk(
    main_root: tk.Misc,
    monitor=None,
) -> OverlayMiniMonitor:
    """Launch the overlay as a Toplevel of the main Tk root. Reuses running instance."""
    global _overlay_instance

    if _overlay_instance and _overlay_instance.running:
        try:
            _overlay_instance.root.deiconify()
            _overlay_instance.root.lift()
            return _overlay_instance
        except Exception:
            pass

    top     = tk.Toplevel(main_root)
    overlay = OverlayMiniMonitor(monitor=monitor, root=top)
    overlay._owns_root = False
    overlay.running    = True
    overlay.root.after(100, overlay._update_loop)
    _overlay_instance  = overlay
    return overlay


def create_overlay_monitor(monitor=None) -> None:
    """Standalone entry point - creates its own Tk root."""
    overlay = OverlayMiniMonitor(monitor=monitor)
    overlay.run()
