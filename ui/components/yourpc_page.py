"""
MY PC - Hardware & Health
"""

import tkinter as tk
import os
import time

try:
    import psutil
except ImportError:
    psutil = None

try:
    from ui.components.pro_info_table import ProInfoTable
except ImportError:
    ProInfoTable = None


class InfoTooltip:
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
    main = tk.Frame(parent, bg="#0a0e14")
    main.pack(fill="both", expand=True)

    self.yourpc_tabs = {}
    self.yourpc_active_tab = None
    self.yourpc_content_frame = None

    nav_bar = tk.Frame(main, bg="#0f1117", height=28)
    nav_bar.pack(fill="x")
    nav_bar.pack_propagate(False)

    tabs_frame = tk.Frame(nav_bar, bg="#0f1117")
    tabs_frame.pack(side="left", fill="y")

    for text, tab_id in [("Central", "central"), ("Efficiency", "efficiency"),
                          ("Health", "health"), ("Components", "components"), ("Startup", "startup")]:
        _create_tab(self, tabs_frame, text, tab_id)

    self.yourpc_content_frame = tk.Frame(main, bg="#0a0e14")
    self.yourpc_content_frame.pack(fill="both", expand=True)

    _show_tab(self, "central")


def _create_tab(self, parent, text, tab_id):
    tab = tk.Label(parent, text=text.upper(), font=("Segoe UI", 7, "bold"),
                   bg="#0f1117", fg="#6b7280", padx=8, pady=4, cursor="hand2")
    tab.pack(side="left")
    self.yourpc_tabs[tab_id] = tab

    tab.bind("<Button-1>", lambda e: _show_tab(self, tab_id))
    tab.bind("<Enter>", lambda e: tab.config(fg="#ffffff", bg="#1f2937") if self.yourpc_active_tab != tab_id else None)
    tab.bind("<Leave>", lambda e: tab.config(fg="#6b7280", bg="#0f1117") if self.yourpc_active_tab != tab_id else None)


def _show_tab(self, tab_id):
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
    container = tk.Frame(parent, bg="#0a0e14")
    container.pack(fill="both", expand=True)

    left = tk.Frame(container, bg="#0a0e14")
    left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

    tk.Label(left, text="QUICK ACTIONS", font=("Segoe UI", 6, "bold"),
             bg="#0a0e14", fg="#4b5563").pack(anchor="w", pady=(0, 3))

    def _nav_to(page_id, subpage_id=None):
        if hasattr(self, '_handle_sidebar_navigation'):
            self._handle_sidebar_navigation(page_id, subpage_id)
            if hasattr(self, 'sidebar') and self.sidebar:
                self.sidebar.set_active_page(page_id, subpage_id)

    # Row 1: two small buttons side by side
    row1 = tk.Frame(left, bg="#0a0e14")
    row1.pack(fill="x")
    r1_left = tk.Frame(row1, bg="#0a0e14")
    r1_left.pack(side="left", fill="both", expand=True, padx=(0, 1))
    r1_right = tk.Frame(row1, bg="#0a0e14")
    r1_right.pack(side="left", fill="both", expand=True, padx=(1, 0))

    _create_action_btn(r1_left, "\U0001f4cb", "Health Report", "#3b82f6", None,
                       ["Advanced PC health report.", "Component history in one place."],
                       lambda: _nav_to("my_pc", "health"))
    _create_action_btn(r1_right, "\U0001f5d1\ufe0f", "Cleanup", "#ef4444", None,
                       ["Cleanup tools.", "Combined power in one place!"],
                       lambda: _nav_to("optimization", "services"))

    # Row 2: LARGE - STATS & ALERTS (yellow gradient)
    _create_large_gradient_btn(
        left, "\u26a0", "STATS & ALERTS",
        (184, 134, 11), (251, 191, 36),
        lambda: _nav_to("monitoring_alerts", "alerts"),
        badge_text="NO ALERTS", badge_bg="#166534",
        tooltip=["Monthly statistics overview.", "Watch temp & voltage spikes."]
    )

    # Row 3: LARGE - Optimization & Services (dark yellow -> dark red)
    _create_large_gradient_btn(
        left, "\u26a1", "Optimization & Services",
        (139, 105, 20), (127, 29, 29),
        lambda: _nav_to("optimization"),
        tooltip=["Hardware optimization tools.", "Automatic daily operations."]
    )

    # Row 4: LARGE - First Setup & Drivers (red -> purple)
    _create_large_gradient_btn(
        left, "\U0001f680", "First Setup & Drivers",
        (239, 68, 68), (107, 33, 168),
        lambda: _nav_to("optimization", "wizard"),
        badge_text="Great", badge_bg="#166534",
        sub_text="Not need to do",
        tooltip=["DRIVER'S UPDATE - All in ONE", "USELESS SERVICES OFF"]
    )

    # Row 5: small full-width - Stability Tests
    _create_action_btn(left, "\U0001f6e1", "Stability Tests", "#10b981", None,
                       ["PC Workman internal diagnostics.", "File integrity, engine status, logs."],
                       lambda: _open_stability_tests(self))

    # Row 6: small full-width - Your Account
    _create_action_btn(left, "\U0001f464", "Your Account - Details", "#8b5cf6", None,
                       ["Account details and preferences.", "Manage your PC Workman profile."],
                       None)

    right = tk.Frame(container, bg="#0a0e27", width=408)
    right.pack(side="right", fill="y", padx=5, pady=5)
    right.pack_propagate(False)

    _build_hey_user_table(self, right)


def _create_action_btn(parent, icon, title, color, badge=None, tooltip=None, command=None):
    row = tk.Frame(parent, bg="#1a1d24", height=23)
    row.pack(fill="x", pady=1)
    row.pack_propagate(False)

    btn = tk.Frame(row, bg="#1a1d24", cursor="hand2")
    btn.pack(side="left", fill="both", expand=True)

    icon_lbl = tk.Label(btn, text=icon, font=("Segoe UI", 8), bg="#1a1d24", fg=color)
    icon_lbl.pack(side="left", padx=(5, 3))

    title_lbl = tk.Label(btn, text=title, font=("Segoe UI", 8, "bold"), bg="#1a1d24", fg="#e5e7eb")
    title_lbl.pack(side="left")

    if badge:
        badge_lbl = tk.Label(btn, text=badge, font=("Segoe UI", 6, "bold"),
                            bg="#166534", fg="#ffffff", padx=4)
        badge_lbl.pack(side="left", padx=(5, 0))

    info_btn = tk.Label(row, text="i", font=("Segoe UI", 7, "bold"),
                        bg="#0a0a0a", fg="#6b7280", width=2, cursor="hand2")
    info_btn.pack(side="right", fill="y")

    if tooltip:
        InfoTooltip(info_btn, tooltip)

    info_btn.bind("<Enter>", lambda e: info_btn.config(bg="#3b82f6", fg="#ffffff"))
    info_btn.bind("<Leave>", lambda e: info_btn.config(bg="#0a0a0a", fg="#6b7280"))

    if command:
        btn.bind("<Button-1>", lambda e: command())
        icon_lbl.bind("<Button-1>", lambda e: command())
        title_lbl.bind("<Button-1>", lambda e: command())

    def on_enter(e):
        btn.config(bg="#7f1d1d")
        icon_lbl.config(bg="#7f1d1d")
        title_lbl.config(bg="#7f1d1d")

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


def _lerp_color(c1, c2, t):
    """Interpolate between two RGB tuples"""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _create_large_gradient_btn(parent, icon, title, grad_start, grad_end, command=None,
                                badge_text=None, badge_bg="#166534", sub_text=None, tooltip=None):
    """Create a large gradient button with optional badge and sub-text"""
    BORDER_COLOR = "#2a2d34"
    HEIGHT = 42

    outer = tk.Frame(parent, bg=BORDER_COLOR, bd=0, highlightthickness=1,
                     highlightbackground=BORDER_COLOR)
    outer.pack(fill="x", pady=2)

    canvas = tk.Canvas(outer, height=HEIGHT, bg="#1a1d24", highlightthickness=0,
                       cursor="hand2")
    canvas.pack(fill="x")

    def _draw_gradient(bright=1.0):
        canvas.delete("gradient")
        w = canvas.winfo_width()
        if w < 10:
            w = 400
        for x in range(0, w, 2):
            t = x / max(w - 1, 1)
            r, g, b = _lerp_color(grad_start, grad_end, t)
            r = min(255, int(r * bright))
            g = min(255, int(g * bright))
            b = min(255, int(b * bright))
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_rectangle(x, 0, x + 2, HEIGHT, fill=color, outline=color, tags="gradient")

    def _draw_content():
        canvas.delete("content")
        w = canvas.winfo_width()
        if w < 10:
            w = 400

        # Icon + title (left side)
        canvas.create_text(
            12, HEIGHT // 2,
            text=icon, font=("Segoe UI", 11),
            fill="#ffffff", anchor="w", tags="content"
        )
        canvas.create_text(
            32, HEIGHT // 2,
            text=title, font=("Segoe UI", 10, "bold"),
            fill="#ffffff", anchor="w", tags="content"
        )

        # Badge (right side)
        if badge_text:
            bx = w - 12
            # Badge background
            text_w = len(badge_text) * 6 + 12
            pad_y = 4
            if sub_text:
                pad_y = 2
            canvas.create_rectangle(
                bx - text_w, HEIGHT // 2 - 9 - (3 if sub_text else 0),
                bx, HEIGHT // 2 + 9 - (3 if sub_text else 0),
                fill=badge_bg, outline=badge_bg, tags="content"
            )
            canvas.create_text(
                bx - text_w // 2, HEIGHT // 2 - (3 if sub_text else 0),
                text=badge_text, font=("Segoe UI", 6, "bold"),
                fill="#ffffff", tags="content"
            )
            if sub_text:
                canvas.create_text(
                    bx - text_w // 2, HEIGHT // 2 + 12,
                    text=sub_text, font=("Segoe UI", 5),
                    fill="#9ca3af", tags="content"
                )

    def _on_configure(e=None):
        _draw_gradient()
        _draw_content()

    canvas.bind("<Configure>", _on_configure)

    # Hover effects
    def _on_enter(e=None):
        _draw_gradient(bright=1.15)
        _draw_content()

    def _on_leave(e=None):
        _draw_gradient(bright=1.0)
        _draw_content()

    canvas.bind("<Enter>", _on_enter)
    canvas.bind("<Leave>", _on_leave)

    if command:
        canvas.bind("<Button-1>", lambda e: command())

    # Info button on the right edge
    info_btn = tk.Label(outer, text="i", font=("Segoe UI", 7, "bold"),
                        bg="#0a0a0a", fg="#6b7280", width=2, cursor="hand2")
    info_btn.place(relx=1.0, rely=0.0, anchor="ne", relheight=1.0)

    if tooltip:
        InfoTooltip(info_btn, tooltip)

    info_btn.bind("<Enter>", lambda e: info_btn.config(bg="#3b82f6", fg="#ffffff"))
    info_btn.bind("<Leave>", lambda e: info_btn.config(bg="#0a0a0a", fg="#6b7280"))


def _build_hey_user_table(self, parent):
    """Build Hey-USER panel with cropped Hardware Table (MOTHERBOARD + CPU)"""
    import socket
    import subprocess

    BG = "#0a0e27"

    # Scrollable container for the cropped table
    canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                             bg="#000000", troughcolor=BG, activebackground="#1a1d24", width=8)
    scrollable = tk.Frame(canvas, bg=BG)

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Mouse wheel scrolling
    def _on_mousewheel(event):
        try:
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _on_mousewheel, add="+")

    # "Show Full Table" button at the very bottom (outside scroll)
    btn_frame = tk.Frame(parent, bg=BG)
    btn_frame.pack(side="bottom", fill="x", padx=5, pady=5)

    more_btn = tk.Label(btn_frame, text="Show Full Table", font=("Segoe UI", 8, "bold"),
                        bg="#374151", fg="#ffffff", pady=6, cursor="hand2")
    more_btn.pack(fill="x")
    more_btn.bind("<Enter>", lambda e: more_btn.config(bg="#4b5563"))
    more_btn.bind("<Leave>", lambda e: more_btn.config(bg="#374151"))
    more_btn.bind("<Button-1>", lambda e: _show_full_table_popup(self, parent))

    # Pack canvas (after button so button is at bottom)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # === USER HEADER (image or fallback) ===
    header_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "icons", "info_header.png")

    try:
        computer_name = socket.gethostname()
    except Exception:
        computer_name = "DESKTOP"

    try:
        from PIL import Image, ImageTk
        if os.path.exists(header_path):
            img = Image.open(header_path)
            img = img.resize((800, 24), Image.Resampling.LANCZOS)
            hdr_canvas = tk.Canvas(scrollable, bg=BG, height=24, highlightthickness=0)
            hdr_canvas.pack(fill="x", pady=(0, 1))
            photo = ImageTk.PhotoImage(img)
            hdr_canvas.create_image(0, 0, image=photo, anchor="nw")
            hdr_canvas.image = photo
            hdr_canvas.create_text(175, 12, text="Hey - USER",
                                   font=("Segoe UI", 9, "bold"), fill="#ffffff", anchor="center")
            hdr_canvas.create_text(525, 12, text=computer_name,
                                   font=("Segoe UI", 9, "bold"), fill="#ffffff", anchor="center")
        else:
            raise FileNotFoundError
    except Exception:
        hdr = tk.Frame(scrollable, bg="#1e3a5f")
        hdr.pack(fill="x")
        tk.Label(hdr, text="Hey - USER", font=("Segoe UI Semibold", 10),
                 bg="#1e3a5f", fg="#ffffff", pady=6).pack(side="left", padx=10)
        tk.Label(hdr, text=computer_name, font=("Segoe UI Semibold", 10),
                 bg="#1e3a5f", fg="#ffffff", pady=6).pack(side="right", padx=10)

    # === MOTHERBOARD SECTION (trapezoid header) ===
    _build_trapezoid_header(scrollable, "⚡ MOTHERBOARD", "#3b82f6")

    # Motherboard model badge
    try:
        result = subprocess.run(["wmic", "baseboard", "get", "product"],
                               capture_output=True, text=True, timeout=3)
        mb_model = result.stdout.strip().split('\n')[1].strip()[:15] if result.stdout else "Unknown"
    except Exception:
        mb_model = "Unknown"

    mb_content = tk.Frame(scrollable, bg="#1a1d24", highlightbackground="#3b82f6",
                          highlightthickness=2)
    mb_content.pack(fill="x", pady=(0, 0))

    mb_left = tk.Frame(mb_content, bg="#1a1d24")
    mb_left.pack(side="left", fill="both", expand=True, padx=1, pady=1)
    mb_right = tk.Frame(mb_content, bg="#1a1d24")
    mb_right.pack(side="left", fill="both", expand=True, padx=1, pady=1)

    # VOLTAGE sub-table
    _build_mini_data_table(mb_left, "⚡ VOLTAGE", [
        ("+12V", "12.096", "12.000", "12.192"),
        ("+5V", "5.040", "5.000", "5.080"),
        ("+3.3V", "3.312", "3.280", "3.344"),
        ("DDR4", "1.200", "1.195", "1.210"),
    ])

    # TEMPERATURE sub-table
    _build_mini_data_table(mb_right, "🌡️ TEMPERATURE", [
        ("CPU Core", "45°", "38°", "67°"),
        ("CPU Socket", "42°", "35°", "58°"),
        ("SYS", "38°", "32°", "45°"),
    ])

    # DISK SPACE & FANS strip
    _build_disk_fans_strip(scrollable)

    # === CPU SECTION (trapezoid header) ===
    _build_trapezoid_header(scrollable, "🔥 CPU", "#3b82f6")

    # CPU model badge
    try:
        import platform
        cpu_name = platform.processor()
        if not cpu_name or len(cpu_name) < 5:
            r = subprocess.run(["wmic", "cpu", "get", "name"],
                              capture_output=True, text=True, timeout=3)
            cpu_name = r.stdout.strip().split('\n')[1].strip() if r.stdout else "N/A"
        cpu_short = cpu_name[:25]
    except Exception:
        cpu_short = "N/A"

    cpu_content = tk.Frame(scrollable, bg="#1a1d24", highlightbackground="#3b82f6",
                           highlightthickness=2)
    cpu_content.pack(fill="x", pady=(0, 0))

    cpu_top = tk.Frame(cpu_content, bg="#1a1d24")
    cpu_top.pack(fill="x", padx=1, pady=1)

    cpu_left = tk.Frame(cpu_top, bg="#1a1d24")
    cpu_left.pack(side="left", fill="both", expand=True)

    sep = tk.Frame(cpu_top, bg="#2d3142", width=6)
    sep.pack(side="left", fill="y", padx=2)

    cpu_right = tk.Frame(cpu_top, bg="#1a1d24")
    cpu_right.pack(side="left", fill="both", expand=True)

    # CPU VOLTAGE
    _build_mini_data_table(cpu_left, "⚡ VOLTAGE", [
        ("IA Offset", "--", "--", "--"),
        ("GT Offset", "--", "--", "--"),
        ("LLC/Ring", "--", "--", "--"),
        ("Sys Agent", "--", "--", "--"),
        ("V/O (Max)", "--", "--", "--"),
    ])

    # CPU TEMPERATURE
    cpu_temps = []
    try:
        from core.hardware_sensors import get_cpu_temp
        if get_cpu_temp:
            t = get_cpu_temp()
            cpu_temps = [
                ("Package", f"{t:.0f}°", "--", f"{t:.0f}°"),
                ("Core Max", f"{t:.0f}°", "--", f"{t:.0f}°"),
            ]
    except Exception:
        pass

    if not cpu_temps:
        cpu_temps = [
            ("Package", "--", "--", "--"),
            ("Core Max", "--", "--", "--"),
        ]

    # Add core rows
    if psutil:
        n_cores = psutil.cpu_count(logical=False) or 4
        for i in range(min(n_cores, 6)):
            cpu_temps.append((f"Core #{i}", "--", "--", "--"))

    _build_mini_data_table(cpu_right, "🌡️ TEMPERATURE", cpu_temps)

    # CPU bottom: POWER | CLOCKS
    cpu_bottom = tk.Frame(cpu_content, bg="#1a1d24")
    cpu_bottom.pack(fill="x", padx=1, pady=(2, 1))

    cpu_pwr = tk.Frame(cpu_bottom, bg="#1a1d24")
    cpu_pwr.pack(side="left", fill="both", expand=True, padx=(0, 2))

    cpu_clk = tk.Frame(cpu_bottom, bg="#1a1d24")
    cpu_clk.pack(side="left", fill="both", expand=True, padx=(2, 0))

    _build_mini_data_table(cpu_pwr, "⚙️ POWER", [
        ("Package", "--", "--", "--"),
        ("IA Cores", "--", "--", "--"),
    ])

    # CPU clocks with real frequency
    clock_rows = []
    if psutil:
        freq = psutil.cpu_freq()
        if freq:
            cur_mhz = f"{int(freq.current)}"
            max_mhz = f"{int(freq.max)}" if freq.max else "--"
            min_mhz = f"{int(freq.min)}" if freq.min else "--"
            n_cores = psutil.cpu_count(logical=False) or 4
            for i in range(min(n_cores, 4)):
                clock_rows.append((f"Core #{i}", cur_mhz, min_mhz, max_mhz))

    if not clock_rows:
        clock_rows = [
            ("Core #0", "--", "--", "--"),
            ("Core #1", "--", "--", "--"),
        ]

    _build_mini_data_table(cpu_clk, "🎨 CLOCKS", clock_rows)


def _build_trapezoid_header(parent, text, color):
    """Draw trapezoid section header matching ProInfoTable style"""
    canvas = tk.Canvas(parent, bg="#0a0e27", height=18, highlightthickness=0)
    canvas.pack(fill="x", pady=(1, 0))

    def _draw(event=None):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
        skew = 8
        points = [skew, 0, w - skew, 0, w, h, 0, h]
        canvas.create_polygon(points, fill=color, outline="#000000", width=2)
        canvas.create_text(w // 2, h // 2, text=text,
                          fill="#ffffff", font=("Segoe UI", 7, "bold"))

    canvas.bind("<Configure>", _draw)


def _build_mini_data_table(parent, title, rows):
    """Build compact data table with CURRENT/MIN/MAX columns (ProInfoTable style)"""
    # Yellow title bar
    title_bar = tk.Frame(parent, bg="#fbbf24", height=12)
    title_bar.pack(fill="x")
    title_bar.pack_propagate(False)
    tk.Label(title_bar, text=title, font=("Segoe UI", 6, "bold"),
             bg="#fbbf24", fg="#000000").pack(side="left", padx=5)
    tk.Label(title_bar, text="OK", font=("Segoe UI", 6, "bold"),
             bg="#10b981", fg="#ffffff", padx=12, pady=1).pack(side="right", padx=2)

    # Column headers
    hdr_bar = tk.Frame(parent, bg="#000000")
    hdr_bar.pack(fill="x")
    tk.Label(hdr_bar, text="", width=10, bg="#000000", font=("Segoe UI", 5)).pack(side="left")
    for col in ["CURRENT", "MIN", "MAX"]:
        tk.Label(hdr_bar, text=col, width=7, bg="#000000", fg="#64748b",
                 font=("Segoe UI", 5, "bold")).pack(side="left", padx=1)

    # Data rows
    container = tk.Frame(parent, bg="#0f1117")
    container.pack(fill="x")

    for row_data in rows:
        row = tk.Frame(container, bg="#0f1117")
        row.pack(fill="x", pady=0)
        label = row_data[0]
        vals = row_data[1:]

        tk.Label(row, text=label, font=("Segoe UI", 6), bg="#0f1117", fg="#94a3b8",
                 anchor="w", width=10).pack(side="left", padx=1)

        for val in vals:
            tk.Label(row, text=val, font=("Segoe UI", 6, "bold"),
                     bg="#000000", fg="#ffffff", width=7).pack(side="left", padx=1)


def _build_disk_fans_strip(parent):
    """SPACE and BODY FANS info strips (ProInfoTable style)"""
    strip_frame = tk.Frame(parent, bg="#1a1d24", highlightbackground="#3b82f6",
                           highlightthickness=2)
    strip_frame.pack(fill="x", pady=(0, 3))

    # DISK SPACE
    space = tk.Frame(strip_frame, bg="#000000", height=16)
    space.pack(fill="x", pady=(1, 0))
    space.pack_propagate(False)
    tk.Label(space, text="SPACE", font=("Segoe UI", 6, "bold"),
             bg="#000000", fg="#fbbf24").pack(side="left", padx=8)
    tk.Label(space, text="|", font=("Segoe UI", 6), bg="#000000", fg="#64748b").pack(side="left", padx=2)

    if psutil:
        try:
            for part in psutil.disk_partitions()[:4]:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    pct = int(usage.percent)
                    color = "#ef4444" if pct > 90 else "#f59e0b" if pct > 75 else "#10b981"
                    tk.Label(space, text=f"{part.device[0]}:/ {pct}%", font=("Segoe UI", 6, "bold"),
                             bg="#000000", fg=color).pack(side="left", padx=5)
                except Exception:
                    pass
        except Exception:
            pass

    # BODY FANS
    fans = tk.Frame(strip_frame, bg="#000000", height=16)
    fans.pack(fill="x", pady=(1, 1))
    fans.pack_propagate(False)
    tk.Label(fans, text="BODY FANS", font=("Segoe UI", 6, "bold"),
             bg="#000000", fg="#fbbf24").pack(side="left", padx=8)
    tk.Label(fans, text="|", font=("Segoe UI", 6), bg="#000000", fg="#64748b").pack(side="left", padx=2)
    tk.Label(fans, text="CPU 560 RPM", font=("Segoe UI", 6),
             bg="#000000", fg="#ffffff").pack(side="left", padx=6)
    tk.Label(fans, text="BODYFAN 990 RPM", font=("Segoe UI", 6),
             bg="#000000", fg="#ffffff").pack(side="left", padx=6)


def _open_stability_tests(self):
    from ui.pages.stability_tests import build_stability_tests_page
    if hasattr(self, '_show_direct_page'):
        for w in self.content_frame.winfo_children():
            w.destroy()
        build_stability_tests_page(self, self.content_frame)
    elif hasattr(self, 'yourpc_content_frame'):
        for w in self.yourpc_content_frame.winfo_children():
            w.destroy()
        build_stability_tests_page(self, self.yourpc_content_frame)


def _show_full_table_popup(self, parent):
    popup = tk.Toplevel(parent)
    popup.title("Full Hardware Info")
    popup.geometry("500x600")
    popup.configure(bg="#0a0e27")
    popup.attributes("-topmost", True)

    popup.update_idletasks()
    x = parent.winfo_rootx() + 50
    y = parent.winfo_rooty() + 20
    popup.geometry(f"+{x}+{y}")

    header = tk.Frame(popup, bg="#1e3a5f")
    header.pack(fill="x")
    tk.Label(header, text="Full Hardware Table", font=("Segoe UI Semibold", 11),
             bg="#1e3a5f", fg="#ffffff", pady=8).pack(side="left", padx=10)

    close_btn = tk.Label(header, text="X", font=("Segoe UI", 12, "bold"),
                         bg="#1e3a5f", fg="#ffffff", padx=10, cursor="hand2")
    close_btn.pack(side="right", pady=5)
    close_btn.bind("<Button-1>", lambda e: popup.destroy())
    close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#ffffff"))

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
