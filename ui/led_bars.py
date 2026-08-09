# ui/led_bars.py
"""
LED-style segment bars for CPU/GPU/RAM usage.
Scalable, color-mapped, neon-styled segments like MSI Afterburner.
"""

import tkinter as tk
from ui.theme import THEME

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
