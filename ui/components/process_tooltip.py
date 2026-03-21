# ui/process_tooltip.py
"""
Shared Process Information Tooltip
Minimalistic hover tooltip with process definitions
"""

import tkinter as tk
from ui.theme import THEME
from core.process_definitions import get_process_definition


class ProcessTooltip:
    """
    Hover tooltip showing process information
    Shows when mouse enters info button, hides when mouse leaves
    """

    def __init__(self, parent):
        self.parent = parent
        self.tooltip_window = None
        self.current_process = None

    def show(self, process_name, x, y):
        """
        Show tooltip at cursor position

        Args:
            process_name: Process name (e.g., 'chrome.exe')
            x: X coordinate (screen)
            y: Y coordinate (screen)
        """
        # Don't recreate if same process
        if self.tooltip_window and self.current_process == process_name:
            return

        # Hide old tooltip
        self.hide()

        self.current_process = process_name

        # Get process definition
        definition = get_process_definition(process_name)

        # Create tooltip window
        self.tooltip_window = tk.Toplevel(self.parent)
        self.tooltip_window.wm_overrideredirect(True)  # No window decorations

        # Position tooltip to the LEFT of cursor to avoid going off-screen
        # Estimate tooltip width (~360px) and position it left of cursor
        tooltip_width = 360
        tooltip_x = x - tooltip_width - 10  # 10px left of cursor
        tooltip_y = y + 10  # Slightly below cursor

        # Make sure tooltip doesn't go off left edge of screen
        if tooltip_x < 0:
            tooltip_x = 10  # At least 10px from left edge

        self.tooltip_window.wm_geometry(f"+{tooltip_x}+{tooltip_y}")

        # Main frame
        frame = tk.Frame(
            self.tooltip_window,
            bg=THEME["bg_panel"],
            relief="solid",
            bd=1,
            highlightthickness=2,
            highlightbackground="#FF6B35"
        )
        frame.pack()

        # Content
        content = tk.Text(
            frame,
            bg=THEME["bg_panel"],
            fg=THEME["text"],
            font=("Segoe UI", 8),
            bd=0,
            wrap="word",
            padx=10,
            pady=8,
            width=45,
            height=10
        )
        content.pack()

        # Fill content
        content.insert("end", f"{definition['full_name']}\n", "title")
        content.insert("end", f"{process_name}\n\n", "subtitle")
        content.insert("end", f"Category: {definition['category']}\n\n", "bold")
        content.insert("end", f"{definition['description']}\n\n")
        content.insert("end", f"Purpose:\n", "bold")
        content.insert("end", f"{definition['purpose']}\n\n")
        if definition.get('warning'):
            content.insert("end", f"⚠ {definition['warning']}\n\n", "warning")
        content.insert("end", f"Developer: {definition['developer']}", "muted")

        # Configure tags
        content.tag_config("title", font=("Segoe UI", 9, "bold"), foreground=THEME["text"])
        content.tag_config("subtitle", font=("Consolas", 7), foreground=THEME["muted"])
        content.tag_config("bold", font=("Segoe UI", 8, "bold"))
        content.tag_config("warning", foreground="#FF6B35", font=("Segoe UI", 8, "bold"))
        content.tag_config("muted", foreground=THEME["muted"], font=("Segoe UI", 7))

        content.config(state="disabled")

    def hide(self):
        """Hide tooltip"""
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except:
                pass
            self.tooltip_window = None
            self.current_process = None
