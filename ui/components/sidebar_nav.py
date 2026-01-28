# ui/components/sidebar_nav.py
"""
PC Workman - Sidebar Navigation Component (Snyk Evo Style)
Stały sidebar z hierarchiczną nawigacją i logo HCK_Labs
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


class SidebarNav:
    """
    Stały sidebar nawigacyjny w stylu Snyk Evo
    - Logo HCK_Labs u góry
    - Hierarchiczna nawigacja z kategoriami i podkategoriami
    - Hover effects i active states
    """

    # Kolory w stylu Snyk Evo (ciemny motyw)
    COLORS = {
        "bg": "#0d0f12",           # Bardzo ciemne tło
        "bg_hover": "#1a1d24",     # Hover tło
        "bg_active": "#1f2937",    # Aktywny element
        "text": "#9ca3af",         # Szary tekst
        "text_hover": "#e5e7eb",   # Jaśniejszy tekst na hover
        "text_active": "#ffffff",  # Biały tekst dla aktywnych
        "accent": "#f472b6",       # Różowy akcent (jak Snyk)
        "accent_icon": "#ec4899",  # Ikona akcentu
        "separator": "#1f2937",    # Separator
        "subitem_bg": "#0d0f12",   # Tło podkategorii
    }

    def __init__(self, parent, width=180, on_navigate=None):
        """
        Args:
            parent: Rodzic Tkinter
            width: Szerokość sidebara (domyślnie 180px)
            on_navigate: Callback wywoływany przy nawigacji (page_id, subpage_id)
        """
        self.parent = parent
        self.width = width
        self.on_navigate = on_navigate
        self.active_item = "dashboard"  # Domyślnie aktywny
        self.expanded_categories = set()  # Kategorie z rozwiniętymi podkategoriami
        self.item_widgets = {}  # Przechowuje referencje do widgetów
        self.logo_image = None  # Referencja do obrazka logo

        # Główny frame sidebara
        self.frame = tk.Frame(
            parent,
            bg=self.COLORS["bg"],
            width=width
        )
        self.frame.pack_propagate(False)

        # Buduj zawartość
        self._build_logo()
        self._build_separator()
        self._build_navigation()
        self._build_bottom_section()

    def _build_logo(self):
        """Buduje sekcję logo u góry - tekstowe logo w stylu Snyk Evo"""
        logo_frame = tk.Frame(self.frame, bg=self.COLORS["bg"], height=60)
        logo_frame.pack(fill="x", pady=(15, 10))
        logo_frame.pack_propagate(False)

        # Tekstowe logo w stylu Snyk Evo
        logo_container = tk.Frame(logo_frame, bg=self.COLORS["bg"])
        logo_container.pack(pady=10, padx=15, anchor="w")

        # Ikona "evo" style (jak na grafice Snyk)
        tk.Label(
            logo_container,
            text="◈",
            font=("Segoe UI", 18),
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent"]
        ).pack(side="left", padx=(0, 8))

        # Tekst HCK (bold, biały)
        tk.Label(
            logo_container,
            text="HCK",
            font=("Segoe UI Semibold", 15, "bold"),
            bg=self.COLORS["bg"],
            fg="#ffffff"
        ).pack(side="left")

        # Tekst _Labs (mniejszy, szary)
        tk.Label(
            logo_container,
            text="_Labs",
            font=("Segoe UI", 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"]
        ).pack(side="left", pady=(3, 0))

    def _build_separator(self):
        """Buduje separator pod logo"""
        sep = tk.Frame(self.frame, bg=self.COLORS["separator"], height=1)
        sep.pack(fill="x", padx=12, pady=(0, 10))

    def _build_navigation(self):
        """Buduje główną nawigację"""
        # Kontener na nawigację (scrollowalny)
        self.nav_container = tk.Frame(self.frame, bg=self.COLORS["bg"])
        self.nav_container.pack(fill="both", expand=True, padx=0)

        # Definicja struktury nawigacji
        nav_structure = [
            {
                "id": "dashboard",
                "label": "Dashboard",
                "icon": "⌂",
                "subitems": None
            },
            {
                "id": "monitoring_alerts",
                "label": "MONITORING & ALERTS",
                "icon": "⚠",
                "subitems": [
                    ("realtime", "Real-time"),
                    ("processes", "Processes"),
                    ("alerts", "Alerts"),
                    ("overlay", "Overlay"),
                ]
            },
            {
                "id": "my_pc",
                "label": "My PC",
                "icon": "▣",
                "subitems": [
                    ("central", "Central"),
                    ("efficiency", "Efficiency"),
                    ("sensors", "Sensors"),
                    ("health", "Health"),
                ]
            },
            {
                "id": "fan_control",
                "label": "Fan Control",
                "icon": "❊",
                "subitems": [
                    ("fan_dashboard", "Dashboard"),
                    ("fans_hardware", "FANS - Hardware Info"),
                    ("usage_statistics", "Usage Statistics"),
                ]
            },
            {
                "id": "optimization",
                "label": "Optimization",
                "icon": "⚡",
                "subitems": [
                    ("services", "Services"),
                    ("startup", "Startup"),
                    ("wizard", "Wizard"),
                ]
            },
            {
                "id": "statistics",
                "label": "Statistics",
                "icon": "▤",
                "subitems": [
                    ("stats_today", "Today"),
                    ("stats_weekly", "Weekly"),
                    ("stats_monthly", "Monthly"),
                ]
            },
        ]

        # Buduj elementy nawigacji
        for item in nav_structure:
            self._create_nav_item(item)

    def _create_nav_item(self, item):
        """Tworzy pojedynczy element nawigacji (może mieć podkategorie)"""
        item_id = item["id"]
        has_subitems = item["subitems"] is not None

        # Główny kontener elementu
        item_frame = tk.Frame(self.nav_container, bg=self.COLORS["bg"])
        item_frame.pack(fill="x")

        # Przycisk główny
        btn = tk.Frame(item_frame, bg=self.COLORS["bg"], cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)

        # Wewnętrzny kontener z paddingiem
        inner = tk.Frame(btn, bg=self.COLORS["bg"])
        inner.pack(fill="x", padx=10, pady=8)

        # Ikona
        icon_label = tk.Label(
            inner,
            text=item["icon"],
            font=("Segoe UI", 11),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            width=2
        )
        icon_label.pack(side="left")

        # Tekst
        text_label = tk.Label(
            inner,
            text=item["label"],
            font=("Segoe UI", 10),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            anchor="w"
        )
        text_label.pack(side="left", padx=(5, 0), fill="x", expand=True)

        # Strzałka rozwijania (jeśli ma podkategorie)
        arrow_label = None
        if has_subitems:
            arrow_label = tk.Label(
                inner,
                text="›",
                font=("Segoe UI", 12),
                bg=self.COLORS["bg"],
                fg=self.COLORS["text"]
            )
            arrow_label.pack(side="right")

        # Kontener na podkategorie (ukryty domyślnie)
        subitems_frame = None
        if has_subitems:
            subitems_frame = tk.Frame(item_frame, bg=self.COLORS["bg"])
            # Nie pakujemy - będzie pokazany po rozwinięciu

            for sub_id, sub_label in item["subitems"]:
                self._create_subitem(subitems_frame, item_id, sub_id, sub_label)

        # Przechowaj referencje
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

        # Binduj eventy do wszystkich elementów
        for widget in [btn, inner, icon_label, text_label]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        if arrow_label:
            arrow_label.bind("<Button-1>", on_click)
            arrow_label.bind("<Enter>", on_enter)
            arrow_label.bind("<Leave>", on_leave)

    def _create_subitem(self, parent, parent_id, sub_id, label):
        """Tworzy element podkategorii"""
        full_id = f"{parent_id}.{sub_id}"

        btn = tk.Frame(parent, bg=self.COLORS["bg"], cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)

        inner = tk.Frame(btn, bg=self.COLORS["bg"])
        inner.pack(fill="x", padx=(30, 10), pady=6)  # Większy lewy padding

        # Tekst podkategorii
        text_label = tk.Label(
            inner,
            text=label,
            font=("Segoe UI", 9),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            anchor="w"
        )
        text_label.pack(side="left", fill="x", expand=True)

        # Przechowaj referencje
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
        """Obsługa kliknięcia w element nawigacji"""
        widgets = self.item_widgets.get(item_id)
        if not widgets:
            return

        if widgets["has_subitems"]:
            # Toggle rozwinięcia
            if item_id in self.expanded_categories:
                self._collapse_category(item_id)
            else:
                self._expand_category(item_id)
        else:
            # Nawiguj do strony
            self._set_active(item_id)
            if self.on_navigate:
                self.on_navigate(item_id, None)

    def _handle_subitem_click(self, full_id):
        """Obsługa kliknięcia w podkategorię"""
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
        """Rozwija kategorię"""
        widgets = self.item_widgets.get(item_id)
        if not widgets or not widgets["subitems_frame"]:
            return

        self.expanded_categories.add(item_id)
        widgets["subitems_frame"].pack(fill="x")

        # Obróć strzałkę
        if widgets["arrow"]:
            widgets["arrow"].config(text="⌄")

    def _collapse_category(self, item_id):
        """Zwija kategorię"""
        widgets = self.item_widgets.get(item_id)
        if not widgets or not widgets["subitems_frame"]:
            return

        self.expanded_categories.discard(item_id)
        widgets["subitems_frame"].pack_forget()

        # Przywróć strzałkę
        if widgets["arrow"]:
            widgets["arrow"].config(text="›")

    def _set_active(self, item_id):
        """Ustawia aktywny element"""
        # Usuń poprzedni aktywny stan
        self._clear_active_states()

        self.active_item = item_id

        # Ustaw nowy aktywny stan
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
        """Czyści wszystkie aktywne stany"""
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
        """Obsługa hover na elemencie"""
        if item_id == self.active_item:
            return  # Nie zmieniaj aktywnego elementu

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
        """Obsługa hover na podkategorii"""
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
        """Buduje dolną sekcję sidebara (Pinned, Settings)"""
        # Separator
        sep = tk.Frame(self.frame, bg=self.COLORS["separator"], height=1)
        sep.pack(fill="x", padx=12, pady=10, side="bottom")

        # Kontener na dolne elementy
        bottom = tk.Frame(self.frame, bg=self.COLORS["bg"])
        bottom.pack(fill="x", side="bottom", pady=(0, 15))

        # Settings
        self._create_bottom_item(bottom, "settings", "⚙", "Settings")

        # Pinned
        self._create_bottom_item(bottom, "pinned", "📌", "Pinned")

    def _create_bottom_item(self, parent, item_id, icon, label):
        """Tworzy element w dolnej sekcji"""
        btn = tk.Frame(parent, bg=self.COLORS["bg"], cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)

        inner = tk.Frame(btn, bg=self.COLORS["bg"])
        inner.pack(fill="x", padx=10, pady=8)

        icon_label = tk.Label(
            inner,
            text=icon,
            font=("Segoe UI", 11),
            bg=self.COLORS["bg"],
            fg=self.COLORS["text"],
            width=2
        )
        icon_label.pack(side="left")

        text_label = tk.Label(
            inner,
            text=label,
            font=("Segoe UI", 10),
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

    def pack(self, **kwargs):
        """Pakuje sidebar"""
        self.frame.pack(**kwargs)

    def place(self, **kwargs):
        """Umieszcza sidebar"""
        self.frame.place(**kwargs)

    def grid(self, **kwargs):
        """Griduje sidebar"""
        self.frame.grid(**kwargs)

    def set_active_page(self, page_id, subpage_id=None):
        """Programowo ustawia aktywną stronę"""
        if subpage_id:
            full_id = f"{page_id}.{subpage_id}"
            # Rozwiń kategorię jeśli nie jest rozwinięta
            if page_id not in self.expanded_categories:
                self._expand_category(page_id)
            self._set_active(full_id)
        else:
            self._set_active(page_id)
