# hck_gpt/tooltip.py
"""
Tooltip widget for displaying process information
"""

import tkinter as tk
from ui.theme import THEME


class ProcessTooltip:
    """
    Shows tooltip on hover over process names
    """
    
    def __init__(self, parent):
        self.parent = parent
        self.tooltip_window = None
        self.current_process = None
    
    def show(self, event, process_name, tooltip_text):
        """
        Show tooltip at mouse position
        
        Args:
            event: Mouse event
            process_name: Process name for title
            tooltip_text: Formatted text to display
        """
        if not tooltip_text:
            return
        
        # Destroy old tooltip if exists
        self.hide()
        
        self.current_process = process_name
        
        # Create tooltip window
        self.tooltip_window = tk.Toplevel(self.parent)
        self.tooltip_window.wm_overrideredirect(True)  # No window decorations
        self.tooltip_window.wm_attributes("-topmost", True)  # Always on top
        
        # Position near mouse
        x = event.x_root + 20
        y = event.y_root + 10
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create frame with border
        frame = tk.Frame(
            self.tooltip_window,
            bg=THEME["bg_panel"],
            highlightbackground=THEME["accent2"],
            highlightthickness=2,
            padx=12,
            pady=8
        )
        frame.pack()
        
        # Add text
        label = tk.Label(
            frame,
            text=tooltip_text,
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            font=("Consolas", 9),
            justify="left"
        )
        label.pack()
    
    def hide(self):
        """Hide and destroy tooltip"""
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None
            self.current_process = None