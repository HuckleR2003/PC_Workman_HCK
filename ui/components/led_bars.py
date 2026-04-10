# ui/components/led_bars.py
"""
LED-style segment bars for CPU/GPU/RAM usage.
Scalable, color-mapped, neon-styled segments like MSI Afterburner.
Also provides AnimatedBar — a smooth ease-out progress bar usable anywhere.
"""

import tkinter as tk
from ui.theme import THEME


class AnimatedBar:
    """
    Smooth animated progress bar with ease-out interpolation.
    Usage:
        bar = AnimatedBar(parent, fill_color="#3b82f6", height=5)
        bar.bg_frame.pack(...)   # place the bar in layout
        bar.set_target(75.0)     # animate to 75%
    """

    _EASE = 0.18          # fraction of gap closed per frame (ease-out)
    _FRAME_MS = 16        # ~60 fps
    _SNAP = 0.004         # snap to target when closer than 0.4%

    def __init__(self, parent, fill_color, bg_color="#0f1117", height=5):
        self._current = 0.0
        self._target = 0.0
        self._animating = False

        self.bg_frame = tk.Frame(parent, bg=bg_color, height=height)
        self._fill = tk.Frame(self.bg_frame, bg=fill_color, height=height)
        self._fill.place(x=0, y=0, relwidth=0.0, relheight=1.0)

    def set_target(self, pct: float):
        """Set target percentage 0–100 and start animating if not already."""
        self._target = max(0.0, min(100.0, pct)) / 100.0
        if not self._animating:
            self._animating = True
            self._step()

    def _step(self):
        diff = self._target - self._current
        if abs(diff) < self._SNAP:
            self._current = self._target
            self._animating = False
            try:
                self._fill.place(relwidth=self._current)
            except Exception:
                pass
            return
        self._current += diff * self._EASE
        try:
            self._fill.place(relwidth=self._current)
            self._fill.after(self._FRAME_MS, self._step)
        except Exception:
            self._animating = False

class LEDSegmentBar:
    def __init__(self, parent, label, color_map, segments=18, height=22):
        """
        parent     : tk widget
        label      : text (CPU/GPU/RAM)
        color_map  : list of segment colors (from low to high)
        segments   : number of LED segments
        height     : height of the bar
        """
        self.segments = segments
        self.color_map = color_map
        self.height = height
        
        # Outer frame
        self.frame = tk.Frame(parent, bg=THEME["bg_panel"])
        
        # Label
        self.lbl = tk.Label(self.frame, text=label,
                            font=("Consolas", 9, "bold"),
                            fg=THEME["muted"], bg=THEME["bg_panel"])
        self.lbl.pack(anchor="w", padx=6, pady=(2,0))
        
        # Canvas for segments
        self.canvas = tk.Canvas(
            self.frame,
            height=self.height,
            bg=THEME["bg_panel"],
            highlightthickness=0
        )
        self.canvas.pack(fill="x", padx=6, pady=(0,6))

        # Create segment rectangles
        self.segment_ids = []
        self._build_segments()

    def _build_segments(self):
        self.canvas.delete("all")
        full_width = max(self.canvas.winfo_width(), 200)
        seg_w = full_width / self.segments
        for i in range(self.segments):
            x1 = seg_w * i + 1
            x2 = seg_w * (i + 1) - 1
            seg = self.canvas.create_rectangle(
                x1, 0, x2, self.height,
                fill="#111", outline="#060606"
            )
            self.segment_ids.append(seg)

    def update(self, percent):
        """
        Update LED segments based on percent (0–100)
        """
        # rebuild segments if resized
        if len(self.segment_ids) != self.segments:
            self._build_segments()

        active = int((percent / 100.0) * self.segments)

        for i, seg in enumerate(self.segment_ids):
            if i < active:
                # pick color from color map depending on segment index
                color_index = int((i / max(1, self.segments - 1)) * (len(self.color_map) - 1))
                color = self.color_map[color_index]
                self.canvas.itemconfig(seg, fill=color, outline=color)
            else:
                self.canvas.itemconfig(seg, fill="#111", outline="#060606")

        # redraw
        try:
            self.canvas.update_idletasks()
        except:
            pass
