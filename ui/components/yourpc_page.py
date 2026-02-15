# ui/yourpc_page.py
"""
MY PC - Hardware & Health
Matches exact design from screenshot
"""

import tkinter as tk
import os

try:
    import psutil
except ImportError:
    psutil = None

# Import PRO INFO TABLE for popup
try:
    from ui.components.pro_info_table import ProInfoTable
except ImportError:
    ProInfoTable = None


class InfoTooltip:
    """Tooltip for info button"""
    def __init__(self, widget, lines):
        self.widget = widget
        self.lines = lines
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, e=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 3
        y = self.widget.winfo_rooty()
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.attributes("-topmost", True)
        frame = tk.Frame(self.tip, bg="#1a1a2e", bd=1, relief="solid")
        frame.pack()
        for line in self.lines:
            tk.Label(frame, text=line, font=("Segoe UI", 7), bg="#1a1a2e",
                    fg="#e0e0e0", padx=6, pady=1).pack(anchor="w")

    def hide(self, e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def build_yourpc_page(self, parent):
    """Build MY PC page"""
    main = tk.Frame(parent, bg="#0a0e14")
    main.pack(fill="both", expand=True)

    # Store references
    self.yourpc_tabs = {}
    self.yourpc_active_tab = None
    self.yourpc_content_frame = None

    # Top navigation bar (compact)
    nav_bar = tk.Frame(main, bg="#0f1117", height=28)
    nav_bar.pack(fill="x")
    nav_bar.pack_propagate(False)

    tabs_frame = tk.Frame(nav_bar, bg="#0f1117")
    tabs_frame.pack(side="left", fill="y")

    for text, tab_id in [("Central", "central"), ("Efficiency", "efficiency"),
                          ("Health", "health"), ("Components", "components"), ("Startup", "startup")]:
        _create_tab(self, tabs_frame, text, tab_id)

    # Content area
    self.yourpc_content_frame = tk.Frame(main, bg="#0a0e14")
    self.yourpc_content_frame.pack(fill="both", expand=True)

    _show_tab(self, "central")


def _create_tab(self, parent, text, tab_id):
    """Create compact tab"""
    tab = tk.Label(parent, text=text.upper(), font=("Segoe UI", 7, "bold"),
                   bg="#0f1117", fg="#6b7280", padx=8, pady=4, cursor="hand2")
    tab.pack(side="left")
    self.yourpc_tabs[tab_id] = tab

    tab.bind("<Button-1>", lambda e: _show_tab(self, tab_id))
    tab.bind("<Enter>", lambda e: tab.config(fg="#ffffff", bg="#1f2937") if self.yourpc_active_tab != tab_id else None)
    tab.bind("<Leave>", lambda e: tab.config(fg="#6b7280", bg="#0f1117") if self.yourpc_active_tab != tab_id else None)


def _show_tab(self, tab_id):
    """Switch tab"""
    if self.yourpc_active_tab:
        self.yourpc_tabs[self.yourpc_active_tab].config(fg="#6b7280", bg="#0f1117")
    self.yourpc_active_tab = tab_id
    self.yourpc_tabs[tab_id].config(fg="#ffffff", bg="#3b82f6")

    for w in self.yourpc_content_frame.winfo_children():
        w.destroy()

    if tab_id == "central":
        _build_central(self, self.yourpc_content_frame)
    else:
        tk.Label(self.yourpc_content_frame, text=f"{tab_id.upper()} - Coming Soon",
                font=("Segoe UI", 12), bg="#0a0e14", fg="#6b7280").pack(pady=50)


def _build_central(self, parent):
    """Build Central tab - exact match to screenshot"""
    container = tk.Frame(parent, bg="#0a0e14")
    container.pack(fill="both", expand=True)

    # LEFT - Quick Actions (two columns: 3 + 2 buttons)
    left = tk.Frame(container, bg="#0a0e14")
    left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

    tk.Label(left, text="QUICK ACTIONS", font=("Segoe UI", 6, "bold"),
             bg="#0a0e14", fg="#4b5563").pack(anchor="w", pady=(0, 3))

    # Two columns frame
    columns = tk.Frame(left, bg="#0a0e14")
    columns.pack(fill="both", expand=True)

    # Column 1 (3 buttons)
    col1 = tk.Frame(columns, bg="#0a0e14")
    col1.pack(side="left", fill="both", expand=True, padx=(0, 2))

    # Column 2 (2 buttons)
    col2 = tk.Frame(columns, bg="#0a0e14")
    col2.pack(side="left", fill="both", expand=True, padx=(2, 0))

    # Menu items - Column 1 (3 items)
    col1_items = [
        ("📋", "Health Report", "#3b82f6", None, [
            "Zaawansowany raport zdrowia PC.",
            "Historia komponentów w jednym miejscu."
        ]),
        ("⚠", "STATS & ALERTS", "#f59e0b", "NO ALERTS", [
            "Statystyki na tle miesięcy.",
            "Obserwuj skoki temperatur i napięcia.",
            "Powiadomienia o podejrzanych akcjach!"
        ]),
        ("⚡", "Optimization", "#f59e0b", None, [
            "Funkcje optymalizacji dla sprzętu.",
            "Automatyczne działanie każdego dnia."
        ]),
    ]

    # Menu items - Column 2 (2 items)
    col2_items = [
        ("🗑️", "Cleanup", "#ef4444", None, [
            "Narzędzia cleanup.",
            "Połączone moce w jednym miejscu!"
        ]),
        ("🚀", "First Setup", "#8b5cf6", None, [
            "• DRIVER'S UPDATE - All in ONE",
            "• USELESS SERVICES OFF",
            "• REMOVE: Cortana, OneDrive"
        ])
    ]

    for icon, title, color, badge, tooltip in col1_items:
        _create_action_btn(col1, icon, title, color, badge, tooltip)

    for icon, title, color, badge, tooltip in col2_items:
        _create_action_btn(col2, icon, title, color, badge, tooltip)

    # RIGHT - Hey USER table (+20% = 408px)
    right = tk.Frame(container, bg="#0a0e27", width=408)
    right.pack(side="right", fill="y", padx=5, pady=5)
    right.pack_propagate(False)

    _build_hey_user_table(self, right)


def _create_action_btn(parent, icon, title, color, badge=None, tooltip=None):
    """Create compact action button (23px height = 25% bigger)"""
    row = tk.Frame(parent, bg="#1a1d24", height=23)
    row.pack(fill="x", pady=1)
    row.pack_propagate(False)

    # Main button area (clickable)
    btn = tk.Frame(row, bg="#1a1d24", cursor="hand2")
    btn.pack(side="left", fill="both", expand=True)

    # Icon
    icon_lbl = tk.Label(btn, text=icon, font=("Segoe UI", 8), bg="#1a1d24", fg=color)
    icon_lbl.pack(side="left", padx=(5, 3))

    # Title
    title_lbl = tk.Label(btn, text=title, font=("Segoe UI", 7), bg="#1a1d24", fg="#e5e7eb")
    title_lbl.pack(side="left")

    # Badge (NO ALERTS) if exists
    if badge:
        badge_lbl = tk.Label(btn, text=badge, font=("Segoe UI", 6, "bold"),
                            bg="#166534", fg="#ffffff", padx=4)
        badge_lbl.pack(side="left", padx=(5, 0))

    # Info button (small, black)
    info_btn = tk.Label(row, text="i", font=("Segoe UI", 7, "bold"),
                        bg="#0a0a0a", fg="#6b7280", width=2, cursor="hand2")
    info_btn.pack(side="right", fill="y")

    # Tooltip on info button
    if tooltip:
        InfoTooltip(info_btn, tooltip)

    # Hover effect on info button
    info_btn.bind("<Enter>", lambda e: info_btn.config(bg="#3b82f6", fg="#ffffff"))
    info_btn.bind("<Leave>", lambda e: info_btn.config(bg="#0a0a0a", fg="#6b7280"))

    # Hover effect on main button (red)
    def on_enter(e):
        btn.config(bg="#7f1d1d")
        icon_lbl.config(bg="#7f1d1d")
        title_lbl.config(bg="#7f1d1d")
        if badge:
            for w in btn.winfo_children():
                if hasattr(w, 'cget') and w.cget('text') == badge:
                    pass  # Keep badge color
                else:
                    try:
                        w.config(bg="#7f1d1d")
                    except:
                        pass

    def on_leave(e):
        btn.config(bg="#1a1d24")
        icon_lbl.config(bg="#1a1d24")
        title_lbl.config(bg="#1a1d24")

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    icon_lbl.bind("<Enter>", on_enter)
    icon_lbl.bind("<Leave>", on_leave)
    title_lbl.bind("<Enter>", on_enter)
    title_lbl.bind("<Leave>", on_leave)


def _build_hey_user_table(self, parent):
    """Build HEY USER table - EXACT match to screenshot"""
    # === HEADER: Hey - USER ===
    header = tk.Frame(parent, bg="#1e3a5f")
    header.pack(fill="x")
    tk.Label(header, text="Hey - USER", font=("Segoe UI Semibold", 10),
             bg="#1e3a5f", fg="#ffffff", pady=6).pack()

    # === MOTHERBOARD HEADER ===
    mb_header = tk.Frame(parent, bg="#2563eb")
    mb_header.pack(fill="x")

    tk.Label(mb_header, text="⚡ MOTHERBOARD", font=("Segoe UI", 8, "bold"),
             bg="#2563eb", fg="#ffffff", padx=10).pack(side="left", pady=3)

    # Get motherboard model
    try:
        import subprocess
        result = subprocess.run(["wmic", "baseboard", "get", "product"],
                               capture_output=True, text=True, timeout=3)
        mb_model = result.stdout.strip().split('\n')[1].strip()[:15] if result.stdout else "Unknown"
    except:
        mb_model = "Unknown"

    tk.Label(mb_header, text=mb_model, font=("Segoe UI", 8, "bold"),
             bg="#2563eb", fg="#ffffff", padx=10).pack(side="right", pady=3)

    # === TWO COLUMNS: VOLTAGE | TEMPERATURE ===
    columns = tk.Frame(parent, bg="#0a0e27")
    columns.pack(fill="x", padx=2, pady=2)
    columns.columnconfigure(0, weight=1)
    columns.columnconfigure(1, weight=1)

    # VOLTAGE column
    _build_voltage_column(columns, 0)

    # TEMPERATURE column
    _build_temperature_column(columns, 1)

    # === SPACE (Disk) ===
    _build_space_section(parent)

    # === BODY FANS ===
    _build_fans_section(parent)

    # === MORE INFO BUTTON ===
    more_frame = tk.Frame(parent, bg="#0a0e27")
    more_frame.pack(fill="x", padx=5, pady=5)

    more_btn = tk.Label(more_frame, text="📊 Show Full Table (popup)", font=("Segoe UI", 8),
                        bg="#374151", fg="#ffffff", pady=6, cursor="hand2")
    more_btn.pack(fill="x")

    more_btn.bind("<Enter>", lambda e: more_btn.config(bg="#4b5563"))
    more_btn.bind("<Leave>", lambda e: more_btn.config(bg="#374151"))
    more_btn.bind("<Button-1>", lambda e: _show_full_table_popup(self, parent))


def _build_voltage_column(parent, col):
    """Build VOLTAGE column"""
    frame = tk.Frame(parent, bg="#0f1420")
    frame.grid(row=0, column=col, sticky="nsew", padx=1)

    # Header with OK badge
    hdr = tk.Frame(frame, bg="#1a1d24")
    hdr.pack(fill="x")
    tk.Label(hdr, text="⚡ VOLTAGE", font=("Consolas", 7, "bold"),
             bg="#1a1d24", fg="#f59e0b").pack(side="left", padx=5, pady=2)
    tk.Label(hdr, text="OK", font=("Consolas", 6, "bold"),
             bg="#10b981", fg="#000000", padx=4).pack(side="right", padx=5, pady=2)

    # Column headers
    cols = tk.Frame(frame, bg="#0f1420")
    cols.pack(fill="x")
    for txt, w in [("", 8), ("CURRENT", 8), ("MIN", 6), ("MAX", 6)]:
        tk.Label(cols, text=txt, font=("Consolas", 5, "bold"), bg="#0f1420",
                fg="#6b7280", width=w).pack(side="left")

    # Voltage rows (simulated values)
    voltages = [
        ("+12V", "12.096", "12.000", "12.192"),
        ("+5V", "5.040", "5.000", "5.080"),
        ("+3.3V", "3.312", "3.280", "3.344"),
        ("DDR4", "1.200", "1.195", "1.210"),
    ]

    for name, cur, mn, mx in voltages:
        row = tk.Frame(frame, bg="#0f1420")
        row.pack(fill="x")
        tk.Label(row, text=name, font=("Consolas", 6), bg="#0f1420", fg="#f59e0b", width=8, anchor="w").pack(side="left")
        tk.Label(row, text=cur, font=("Consolas", 6), bg="#0f1420", fg="#ffffff", width=8).pack(side="left")
        tk.Label(row, text=mn, font=("Consolas", 6), bg="#0f1420", fg="#6b7280", width=6).pack(side="left")
        tk.Label(row, text=mx, font=("Consolas", 6), bg="#0f1420", fg="#6b7280", width=6).pack(side="left")


def _build_temperature_column(parent, col):
    """Build TEMPERATURE column"""
    frame = tk.Frame(parent, bg="#0f1420")
    frame.grid(row=0, column=col, sticky="nsew", padx=1)

    # Header with OK badge
    hdr = tk.Frame(frame, bg="#1a1d24")
    hdr.pack(fill="x")
    tk.Label(hdr, text="🌡 TEMPERATURE", font=("Consolas", 7, "bold"),
             bg="#1a1d24", fg="#ef4444").pack(side="left", padx=5, pady=2)
    tk.Label(hdr, text="OK", font=("Consolas", 6, "bold"),
             bg="#10b981", fg="#000000", padx=4).pack(side="right", padx=5, pady=2)

    # Column headers
    cols = tk.Frame(frame, bg="#0f1420")
    cols.pack(fill="x")
    for txt, w in [("", 10), ("CURRENT", 7), ("MIN", 5), ("MAX", 5)]:
        tk.Label(cols, text=txt, font=("Consolas", 5, "bold"), bg="#0f1420",
                fg="#6b7280", width=w).pack(side="left")

    # Temperature rows (simulated)
    temps = [
        ("CPU Core", "45", "38", "67"),
        ("CPU Socket", "42", "35", "58"),
        ("SYS", "38", "32", "45"),
    ]

    for name, cur, mn, mx in temps:
        row = tk.Frame(frame, bg="#0f1420")
        row.pack(fill="x")
        tk.Label(row, text=name, font=("Consolas", 6), bg="#0f1420", fg="#ef4444", width=10, anchor="w").pack(side="left")
        tk.Label(row, text=cur+"°", font=("Consolas", 6), bg="#0f1420", fg="#ffffff", width=7).pack(side="left")
        tk.Label(row, text=mn+"°", font=("Consolas", 6), bg="#0f1420", fg="#6b7280", width=5).pack(side="left")
        tk.Label(row, text=mx+"°", font=("Consolas", 6), bg="#0f1420", fg="#6b7280", width=5).pack(side="left")


def _build_space_section(parent):
    """Build SPACE (disk) section"""
    frame = tk.Frame(parent, bg="#1a1d24")
    frame.pack(fill="x", padx=2, pady=(2, 0))

    tk.Label(frame, text="SPACE", font=("Consolas", 6, "bold"),
             bg="#1a1d24", fg="#8b5cf6", padx=5).pack(side="left", pady=2)

    # Get disk usage
    try:
        if psutil:
            for part in psutil.disk_partitions()[:4]:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    pct = int(usage.percent)
                    drive = part.device[0]
                    color = "#ef4444" if pct > 90 else "#f59e0b" if pct > 75 else "#10b981"
                    tk.Label(frame, text=f"{drive}/{pct}%", font=("Consolas", 6),
                            bg="#1a1d24", fg=color, padx=3).pack(side="left", pady=2)
                except:
                    pass
    except:
        tk.Label(frame, text="C/--", font=("Consolas", 6), bg="#1a1d24", fg="#6b7280").pack(side="left")


def _build_fans_section(parent):
    """Build BODY FANS section"""
    frame = tk.Frame(parent, bg="#1a1d24")
    frame.pack(fill="x", padx=2, pady=(1, 0))

    tk.Label(frame, text="BODY FANS", font=("Consolas", 6, "bold"),
             bg="#1a1d24", fg="#06b6d4", padx=5).pack(side="left", pady=2)

    # Simulated fan speeds
    tk.Label(frame, text="CPU 560 RPM", font=("Consolas", 6),
             bg="#1a1d24", fg="#ffffff", padx=8).pack(side="left", pady=2)
    tk.Label(frame, text="BODYFAN 990 RPM", font=("Consolas", 6),
             bg="#1a1d24", fg="#ffffff", padx=8).pack(side="left", pady=2)


def _show_full_table_popup(self, parent):
    """Show full PRO INFO TABLE in a popup window"""
    popup = tk.Toplevel(parent)
    popup.title("Full Hardware Info")
    popup.geometry("500x600")
    popup.configure(bg="#0a0e27")
    popup.attributes("-topmost", True)

    # Center popup
    popup.update_idletasks()
    x = parent.winfo_rootx() + 50
    y = parent.winfo_rooty() + 20
    popup.geometry(f"+{x}+{y}")

    # Header
    header = tk.Frame(popup, bg="#1e3a5f")
    header.pack(fill="x")
    tk.Label(header, text="📊 Full Hardware Table", font=("Segoe UI Semibold", 11),
             bg="#1e3a5f", fg="#ffffff", pady=8).pack(side="left", padx=10)

    close_btn = tk.Label(header, text="✕", font=("Segoe UI", 12, "bold"),
                         bg="#1e3a5f", fg="#ffffff", padx=10, cursor="hand2")
    close_btn.pack(side="right", pady=5)
    close_btn.bind("<Button-1>", lambda e: popup.destroy())
    close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#ffffff"))

    # Content - PRO INFO TABLE
    content = tk.Frame(popup, bg="#0a0e27")
    content.pack(fill="both", expand=True, padx=5, pady=5)

    if ProInfoTable:
        try:
            table = ProInfoTable(content)
            table.pack(fill="both", expand=True)
        except Exception as e:
            tk.Label(content, text=f"Error: {e}", font=("Segoe UI", 10),
                    bg="#0a0e27", fg="#ef4444").pack(pady=50)
    else:
        tk.Label(content, text="PRO INFO TABLE not available",
                font=("Segoe UI", 10), bg="#0a0e27", fg="#6b7280").pack(pady=50)
