# ui/pages/base_page.py
"""
Base class for all pages/tabs.
"""

import tkinter as tk


class BasePage:
    """
    Base class for application pages.
    Provides a consistent interface and shared functionality.
    """

    COLORS = {
        "bg": "#0a0e14",
        "card_bg": "#111827",
        "card_border": "#1f2937",
        "text": "#e5e7eb",
        "text_muted": "#6b7280",
        "accent_green": "#10b981",
        "accent_blue": "#3b82f6",
        "accent_purple": "#8b5cf6",
        "accent_orange": "#f59e0b",
    }

    def __init__(self, parent, app=None, monitor=None):
        """
        Args:
            parent: Parent widget (`tk.Frame`)
            app: Main application reference
            monitor: System monitor reference
        """
        self.parent = parent
        self.app = app
        self.monitor = monitor
        self.frame = None
        self._running = True

        self._build()

    def _build(self):
        """Build page content (override in subclasses)."""
        self.frame = tk.Frame(self.parent, bg=self.COLORS["bg"])
        self.frame.pack(fill="both", expand=True)

    def destroy(self):
        """Destroy page and stop updates."""
        self._running = False
        if self.frame:
            self.frame.destroy()

    def _create_header(self, title, subtitle=""):
        """Create page header."""
        header = tk.Frame(self.frame, bg=self.COLORS["bg"])
        header.pack(fill="x", padx=20, pady=(15, 10))

        tk.Label(
            header,
            text=title,
            font=("Segoe UI Semibold", 16, "bold"),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"]
        ).pack(side="left")

        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                font=("Segoe UI", 10),
                bg=self.COLORS["bg"],
                fg=self.COLORS["text_muted"]
            ).pack(side="left", padx=(15, 0))

        return header

    def _create_card(self, parent, title=None):
        """Create a card with optional title."""
        card = tk.Frame(parent, bg=self.COLORS["card_bg"])

        if title:
            tk.Label(
                card,
                text=title,
                font=("Segoe UI Semibold", 10),
                bg=self.COLORS["card_bg"],
                fg=self.COLORS["text"]
            ).pack(anchor="w", padx=15, pady=(10, 5))

        return card
