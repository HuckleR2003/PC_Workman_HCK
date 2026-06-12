# ui/components/sidebar_nav.py
"""
PC Workman - Sidebar Navigation Component (Snyk Evo Style)
Fixed sidebar with hierarchical navigation and HCK_Labs branding.
"""

import tkinter as tk
from tkinter import ttk
import os

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from ui.theme import THEME
from utils.i18n import t, register_on_change, unregister_on_change

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF


class SidebarNav:
    """
    Fixed Snyk Evo-style navigation sidebar.
    - HCK_Labs logo at the top
    - Hierarchical navigation with categories and subcategories
    - Hover effects and active states
    """

    # Snyk Evo-style colors (dark theme)
    COLORS = {
        "bg": "#0d0f12",           # Very dark background
        "bg_hover": "#1a1d24",     # Hover background
        "bg_active": "#1f2937",    # Active item
        "text": "#9ca3af",         # Gray text
        "text_hover": "#e5e7eb",   # Lighter hover text
        "text_active": "#ffffff",  # Active text
        "accent": "#f472b6",       # Pink accent (Snyk-like)
        "accent_icon": "#ec4899",  # Accent icon color
        "separator": "#1f2937",    # Separator
        "subitem_bg": "#0d0f12",   # Subcategory background
    }

    def __init__(self, parent, width=180, on_navigate=None):
        """
        Args:
            parent: Tkinter parent widget
            width: Sidebar width (default: 180px)
            on_navigate: Navigation callback (page_id, subpage_id)
        """
        self.parent = parent
        self.width = width
        self.on_navigate = on_navigate
        self.active_item = "dashboard"  # Default active page
        self.expanded_categories = set()  # Expanded categories
        self.item_widgets = {}  # Widget references
        self.logo_image = None  # Logo image reference

        # Auto-hide state
        self._auto_hide       = False
        self._auto_hide_delay = 3000   # ms before collapsing
        self._collapse_timer  = None
        self._collapsed       = False

        # Main sidebar frame
        self.frame = tk.Frame(
            parent,
            bg=self.COLORS["bg"],
            width=width
        )
        self.frame.pack_propagate(False)

        # Build content
        self._build_logo()
        self._build_separator()
        self._build_navigation()
        self._build_bottom_section()

        # Register for live language changes
        register_on_change(self.rebuild_nav)

    def _build_logo(self):
        """Build top logo section."""
        logo_frame = tk.Frame(self.frame, bg=self.COLORS["bg"], height=60, cursor="hand2")
        logo_frame.pack(fill="x", pady=(15, 10))
        logo_frame.pack_propagate(False)

        logo_container = tk.Frame(logo_frame, bg=self.COLORS["bg"], cursor="hand2")
        logo_container.pack(pady=10, padx=15, anchor="w")

        icon_lbl = tk.Label(
            logo_container,
            text="◈",
            font=(_BODY, 18),
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent"],
            cursor="hand2"
        )
        icon_lbl.pack(side="left", padx=(0, 8))

        hck_lbl = tk.Label(
            logo_container,
            text="HCK",
            font=("Segoe UI Semibold", 15, "bold"),
            bg=self.COLORS["bg"],
            fg="#ffffff",
            cursor="hand2"
        )
        hck_lbl.pack(side="left")

        labs_lbl = tk.Label(
            logo_container,
            text="_Labs",
            font=(_BODY, 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            cursor="hand2"
        )
        labs_lbl.pack(side="left", pady=(3, 0))

        def _go_dashboard(e=None):
            self._set_active("dashboard")
            if self.on_navigate:
                self.on_navigate("dashboard", None)

        for w in [logo_frame, logo_container, icon_lbl, hck_lbl, labs_lbl]:
            w.bind("<Button-1>", _go_dashboard)

    def _build_separator(self):
        """Build separator below logo."""
        sep = tk.Frame(self.frame, bg=self.COLORS["separator"], height=1)
        sep.pack(fill="x", padx=12, pady=(0, 10))

    def _nav_structure(self) -> list:
        """Return the navigation tree using translated labels."""
        return [
            {
                "id": "dashboard",
                "label": t("nav.dashboard"),
                "icon": "⌂",
                "subitems": None
            },
            {
                "id": "monitoring_alerts",
                "label": t("nav.monitoring"),
                "icon": "⚠",
                "subitems": [
                    ("temperature", t("nav.monitoring_temperature")),
                    ("voltage",     t("nav.monitoring_voltage")),
                    ("alerts",      t("nav.monitoring_alerts")),
                ]
            },
            {
                "id": "my_pc",
                "label": t("nav.my_pc"),
                "icon": "▣",
                "subitems": [
                    ("central",    t("nav.my_pc_central")),
                    ("efficiency", t("nav.my_pc_efficiency")),
                    ("sensors",    t("nav.my_pc_sensors")),
                    ("health",     t("nav.my_pc_health")),
                ]
            },
            {
                "id": "first_setup",
                "label": t("nav.setup"),
                "icon": "⚙",
                "subitems": None
            },
            {
                "id": "fan_control",
                "label": t("nav.fan_control"),
                "icon": "❊",
                "subitems": [
                    ("fan_dashboard",    t("nav.fan_control_dashboard")),
                    ("fans_hardware",    t("nav.fan_control_hardware")),
                    ("usage_statistics", t("nav.fan_control_usage")),
                ]
            },
            {
                "id": "optimization",
                "label": t("nav.optimization"),
                "icon": "⚡",
                "subitems": [
                    ("services", t("nav.optimization_services")),
                    ("startup",  t("nav.optimization_startup")),
                    ("wizard",   t("nav.optimization_wizard")),
                ]
            },
            {
                "id": "statistics",
                "label": t("nav.statistics"),
                "icon": "▤",
                "subitems": [
                    ("stats_today",   t("nav.statistics_today")),
                    ("stats_weekly",  t("nav.statistics_weekly")),
                    ("stats_monthly", t("nav.statistics_monthly")),
                ]
            },
        ]

    def _build_navigation(self):
        """Build main navigation."""
        # Navigation container
        self.nav_container = tk.Frame(self.frame, bg=self.COLORS["bg"])
        self.nav_container.pack(fill="both", expand=True, padx=0)

        # Build navigation items
        for item in self._nav_structure():
            self._create_nav_item(item)

    def _create_nav_item(self, item):
        """Create a single navigation item (can include subitems)."""
        item_id = item["id"]
        has_subitems = item["subitems"] is not None

        # Main item container
        item_frame = tk.Frame(self.nav_container, bg=self.COLORS["bg"])
        item_frame.pack(fill="x")

        # Main button
        btn = tk.Frame(item_frame, bg=self.COLORS["bg"], cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)

        # Inner container with padding
        inner = tk.Frame(btn, bg=self.COLORS["bg"])
        inner.pack(fill="x", padx=10, pady=8)

        # Icon
        icon_label = tk.Label(
            inner,
            text=item["icon"],
            font=(_BODY, 11),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            width=2
        )
        icon_label.pack(side="left")

        # Text
        text_label = tk.Label(
            inner,
            text=item["label"],
            font=(_BODY, 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            anchor="w"
        )
        text_label.pack(side="left", padx=(5, 0), fill="x", expand=True)

        # Expand arrow (if subitems exist)
        arrow_label = None
        if has_subitems:
            arrow_label = tk.Label(
                inner,
                text="›",
                font=(_BODY, 12),
                bg=self.COLORS["bg"],
                fg=self.COLORS["text"]
            )
            arrow_label.pack(side="right")

        # Subitems container (hidden by default)
        subitems_frame = None
        if has_subitems:
            subitems_frame = tk.Frame(item_frame, bg=self.COLORS["bg"])
            # Deliberately not packed yet; shown on expand

            for sub_id, sub_label in item["subitems"]:
                self._create_subitem(subitems_frame, item_id, sub_id, sub_label)

        # Store references
        self.item_widgets[item_id] = {
            "btn": btn,
            "inner": inner,
            "icon": icon_label,
            "text": text_label,
            "arrow": arrow_label,
            "subitems_frame": subitems_frame,
            "has_subitems": has_subitems
        }

        # Event handlers
        def on_click(e, iid=item_id):
            self._handle_item_click(iid)

        def on_enter(e, iid=item_id):
            self._handle_item_hover(iid, True)

        def on_leave(e, iid=item_id):
            self._handle_item_hover(iid, False)

        # Bind events to all item widgets
        for widget in [btn, inner, icon_label, text_label]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        if arrow_label:
            arrow_label.bind("<Button-1>", on_click)
            arrow_label.bind("<Enter>", on_enter)
            arrow_label.bind("<Leave>", on_leave)

    def _create_subitem(self, parent, parent_id, sub_id, label):
        """Create a subcategory item."""
        full_id = f"{parent_id}.{sub_id}"

        btn = tk.Frame(parent, bg=self.COLORS["bg"], cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)

        inner = tk.Frame(btn, bg=self.COLORS["bg"])
        inner.pack(fill="x", padx=(30, 10), pady=6)  # Increased left padding

        # Subitem label
        text_label = tk.Label(
            inner,
            text=label,
            font=(_BODY, 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            anchor="w"
        )
        text_label.pack(side="left", fill="x", expand=True)

        # Store references
        self.item_widgets[full_id] = {
            "btn": btn,
            "inner": inner,
            "text": text_label,
            "is_subitem": True
        }

        # Event handlers
        def on_click(e, fid=full_id):
            self._handle_subitem_click(fid)

        def on_enter(e, fid=full_id):
            self._handle_subitem_hover(fid, True)

        def on_leave(e, fid=full_id):
            self._handle_subitem_hover(fid, False)

        for widget in [btn, inner, text_label]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def _handle_item_click(self, item_id):
        """Handle top-level navigation item click."""
        widgets = self.item_widgets.get(item_id)
        if not widgets:
            return

        if widgets["has_subitems"]:
            # Toggle expanded state
            if item_id in self.expanded_categories:
                self._collapse_category(item_id)
            else:
                self._expand_category(item_id)
        else:
            # Navigate to page
            self._set_active(item_id)
            if self.on_navigate:
                self.on_navigate(item_id, None)

    def _handle_subitem_click(self, full_id):
        """Handle subitem click."""
        print(f"[SidebarNav] Subitem clicked: {full_id}")
        parts = full_id.split(".")
        parent_id = parts[0]
        sub_id = parts[1] if len(parts) > 1 else None

        self._set_active(full_id)
        if self.on_navigate:
            print(f"[SidebarNav] Calling callback with: {parent_id}, {sub_id}")
            self.on_navigate(parent_id, sub_id)
        else:
            print("[SidebarNav] WARNING: No callback set!")

    def _expand_category(self, item_id):
        """Expand category, auto-collapsing any other currently-open section."""
        # Collapse all other expanded categories first
        for other_id in list(self.expanded_categories):
            if other_id != item_id:
                self._collapse_category(other_id)

        widgets = self.item_widgets.get(item_id)
        if not widgets or not widgets["subitems_frame"]:
            return

        self.expanded_categories.add(item_id)
        widgets["subitems_frame"].pack(fill="x")

        # Rotate arrow
        if widgets["arrow"]:
            widgets["arrow"].config(text="⌄")

    def _collapse_category(self, item_id):
        """Collapse category."""
        widgets = self.item_widgets.get(item_id)
        if not widgets or not widgets["subitems_frame"]:
            return

        self.expanded_categories.discard(item_id)
        widgets["subitems_frame"].pack_forget()

        # Restore arrow
        if widgets["arrow"]:
            widgets["arrow"].config(text="›")

    def _set_active(self, item_id):
        """Set active item."""
        # Clear previous active state
        self._clear_active_states()

        self.active_item = item_id

        # Apply new active state
        widgets = self.item_widgets.get(item_id)
        if widgets:
            bg = self.COLORS["bg_active"]
            fg = self.COLORS["text_active"]

            widgets["btn"].config(bg=bg)
            widgets["inner"].config(bg=bg)
            widgets["text"].config(bg=bg, fg=fg)

            if widgets.get("icon"):
                widgets["icon"].config(bg=bg, fg=self.COLORS["accent"])
            if widgets.get("arrow"):
                widgets["arrow"].config(bg=bg, fg=fg)

    def _clear_active_states(self):
        """Clear all active states."""
        bg = self.COLORS["bg"]
        fg = self.COLORS["text"]

        for item_id, widgets in self.item_widgets.items():
            widgets["btn"].config(bg=bg)
            widgets["inner"].config(bg=bg)
            widgets["text"].config(bg=bg, fg=fg)

            if widgets.get("icon"):
                widgets["icon"].config(bg=bg, fg=fg)
            if widgets.get("arrow"):
                widgets["arrow"].config(bg=bg, fg=fg)

    def _handle_item_hover(self, item_id, entering):
        """Handle hover on top-level item."""
        if item_id == self.active_item:
            return  # Keep active item styling unchanged

        widgets = self.item_widgets.get(item_id)
        if not widgets:
            return

        if entering:
            bg = self.COLORS["bg_hover"]
            fg = self.COLORS["text_hover"]
        else:
            bg = self.COLORS["bg"]
            fg = self.COLORS["text"]

        widgets["btn"].config(bg=bg)
        widgets["inner"].config(bg=bg)
        widgets["text"].config(bg=bg, fg=fg)

        if widgets.get("icon"):
            widgets["icon"].config(bg=bg, fg=fg if not entering else self.COLORS["accent_icon"])
        if widgets.get("arrow"):
            widgets["arrow"].config(bg=bg, fg=fg)

    def _handle_subitem_hover(self, full_id, entering):
        """Handle hover on subitem."""
        if full_id == self.active_item:
            return

        widgets = self.item_widgets.get(full_id)
        if not widgets:
            return

        if entering:
            bg = self.COLORS["bg_hover"]
            fg = self.COLORS["text_hover"]
        else:
            bg = self.COLORS["bg"]
            fg = self.COLORS["text"]

        widgets["btn"].config(bg=bg)
        widgets["inner"].config(bg=bg)
        widgets["text"].config(bg=bg, fg=fg)

    def _build_bottom_section(self):
        """Build bottom sidebar section — Settings only (Pinned removed)."""
        # Separator
        sep = tk.Frame(self.frame, bg=self.COLORS["separator"], height=1)
        sep.pack(fill="x", padx=12, pady=10, side="bottom")

        # Bottom items container
        bottom = tk.Frame(self.frame, bg=self.COLORS["bg"])
        bottom.pack(fill="x", side="bottom", pady=(0, 15))

        # Settings (only item at the bottom)
        self._create_bottom_item(bottom, "settings", "⚙", t("nav.settings"))

    def _create_bottom_item(self, parent, item_id, icon, label):
        """Create an item in bottom section."""
        btn = tk.Frame(parent, bg=self.COLORS["bg"], cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)

        inner = tk.Frame(btn, bg=self.COLORS["bg"])
        inner.pack(fill="x", padx=10, pady=8)

        icon_label = tk.Label(
            inner,
            text=icon,
            font=(_BODY, 11),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            width=2
        )
        icon_label.pack(side="left")

        text_label = tk.Label(
            inner,
            text=label,
            font=(_BODY, 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            anchor="w"
        )
        text_label.pack(side="left", padx=(5, 0))

        self.item_widgets[item_id] = {
            "btn": btn,
            "inner": inner,
            "icon": icon_label,
            "text": text_label,
            "has_subitems": False
        }

        def on_click(e, iid=item_id):
            self._set_active(iid)
            if self.on_navigate:
                self.on_navigate(iid, None)

        def on_enter(e, iid=item_id):
            self._handle_item_hover(iid, True)

        def on_leave(e, iid=item_id):
            self._handle_item_hover(iid, False)

        for widget in [btn, inner, icon_label, text_label]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

    def rebuild_nav(self) -> None:
        """
        Destroy and recreate the navigation container with translated labels.
        Called automatically when the active language changes.
        Also rebuilds the bottom section so Settings / Pinned labels update.
        """
        # ── Rebuild main nav ───────────────────────────────────────────────────
        if hasattr(self, "nav_container") and self.nav_container.winfo_exists():
            self.nav_container.destroy()
        self.item_widgets.clear()
        self._build_navigation()

        # ── Rebuild bottom section ─────────────────────────────────────────────
        # The bottom frame is identified by the last two pack slaves with
        # side="bottom".  Simplest approach: find and destroy both the separator
        # and the bottom container, then rebuild.
        slaves = self.frame.pack_slaves()
        # Collect bottom-packed slaves (separator + bottom container)
        for slave in slaves:
            pack_info = slave.pack_info()
            if pack_info.get("side") == "bottom":
                slave.destroy()
        self._build_bottom_section()

        # Restore active state (subitems_frame visibility included)
        if self.active_item:
            # Re-expand parent category if a subitem was active
            if "." in self.active_item:
                parent_id = self.active_item.split(".")[0]
                if parent_id in self.expanded_categories:
                    self._expand_category(parent_id)
            self._set_active(self.active_item)

    def destroy(self) -> None:
        """Clean up language-change callback registration."""
        unregister_on_change(self.rebuild_nav)
        try:
            self.frame.destroy()
        except Exception:
            pass

    def pack(self, **kwargs):
        """Pack sidebar widget."""
        self.frame.pack(**kwargs)

    def place(self, **kwargs):
        """Place sidebar widget."""
        self.frame.place(**kwargs)

    def grid(self, **kwargs):
        """Grid sidebar widget."""
        self.frame.grid(**kwargs)

    def set_active_page(self, page_id, subpage_id=None):
        """Set active page programmatically."""
        if subpage_id:
            full_id = f"{page_id}.{subpage_id}"
            # Expand category if not already expanded
            if page_id not in self.expanded_categories:
                self._expand_category(page_id)
            self._set_active(full_id)
        else:
            self._set_active(page_id)

    # ── Auto-hide sidebar ─────────────────────────────────────────────────────

    def set_auto_hide(self, enabled: bool, delay_ms: int = 500) -> None:
        """
        Enable / disable mouse-leave auto-collapse.
        Collapses to 48 px icon rail after delay_ms (default 500 ms)
        of the cursor being outside the sidebar frame.
        Activates immediately on enable — no need to switch pages first.
        """
        self._auto_hide       = enabled
        self._auto_hide_delay = delay_ms

        if enabled:
            self.frame.bind("<Leave>", self._on_sidebar_leave)
            self.frame.bind("<Enter>", self._on_sidebar_enter)
            # Immediate effect: check whether cursor is already outside and start timer
            try:
                px = self.frame.winfo_pointerx()
                py = self.frame.winfo_pointery()
                sx = self.frame.winfo_rootx()
                sy = self.frame.winfo_rooty()
                sw = self.frame.winfo_width()
                sh = self.frame.winfo_height()
                if not (sx <= px <= sx + sw and sy <= py <= sy + sh):
                    self._cancel_auto_collapse()
                    self._collapse_timer = self.frame.after(
                        self._auto_hide_delay, self._collapse_sidebar
                    )
            except Exception:
                pass
        else:
            self.frame.unbind("<Leave>")
            self.frame.unbind("<Enter>")
            self._cancel_auto_collapse()
            if self._collapsed:
                self._expand_sidebar()

    def _on_sidebar_leave(self, event) -> None:
        """Fires when pointer leaves the sidebar frame or any child widget."""
        # Verify the cursor actually left the sidebar bounding box
        sx = self.frame.winfo_rootx()
        sy = self.frame.winfo_rooty()
        sw = self.frame.winfo_width()
        sh = self.frame.winfo_height()
        if sx <= event.x_root <= sx + sw and sy <= event.y_root <= sy + sh:
            return  # still inside - child widget boundary noise
        self._cancel_auto_collapse()
        self._collapse_timer = self.frame.after(
            self._auto_hide_delay, self._collapse_sidebar
        )

    def _on_sidebar_enter(self, event) -> None:
        """Fires when pointer enters the sidebar - cancel pending collapse and expand."""
        self._cancel_auto_collapse()
        if self._collapsed:
            self._expand_sidebar()

    def _cancel_auto_collapse(self) -> None:
        if self._collapse_timer is not None:
            try:
                self.frame.after_cancel(self._collapse_timer)
            except Exception:
                pass
            self._collapse_timer = None

    def _collapse_sidebar(self) -> None:
        """Shrink sidebar to icon-rail width (48 px)."""
        if not self._auto_hide:
            return
        self._collapsed = True
        try:
            self.frame.config(width=48)
        except Exception:
            pass

    def _expand_sidebar(self) -> None:
        """Restore sidebar to full width."""
        self._collapsed = False
        try:
            self.frame.config(width=self.width)
        except Exception:
            pass
