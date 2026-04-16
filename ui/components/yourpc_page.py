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
    elif tab_id == "health":
        _build_health(self, self.yourpc_content_frame)
    elif tab_id == "components":
        _build_components(self, self.yourpc_content_frame)
    elif tab_id == "efficiency":
        _build_efficiency(self, self.yourpc_content_frame)
    elif tab_id == "startup":
        _build_startup(self, self.yourpc_content_frame)
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

    # Row 1.5: System utilities (3 across)
    import subprocess as _sp
    row_sys = tk.Frame(left, bg="#0a0e14")
    row_sys.pack(fill="x", pady=(2, 0))
    for _ico, _title, _color, _cmd in [
        ("⚙️", "Device Manager", "#6b7280",
         lambda: _sp.Popen(["devmgmt.msc"], shell=True)),
        ("📊", "Task Manager",   "#6b7280",
         lambda: _sp.Popen(["taskmgr"])),
        ("💾", "Export Report",  "#6b7280",
         lambda: _export_health_report()),
    ]:
        _col_f = tk.Frame(row_sys, bg="#0a0e14")
        _col_f.pack(side="left", fill="both", expand=True, padx=1)
        _create_action_btn(_col_f, _ico, _title, _color, command=_cmd)

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
    try:
        from ui.pages.first_setup_drivers import _load_checklist, _CHECKLIST
        _cl = _load_checklist()
        _done = sum(1 for k, _ in _CHECKLIST if _cl.get(k, False))
        _total = len(_CHECKLIST)
        _badge_txt = f"{_done}/{_total} done"
        _badge_bg  = "#166534" if _done == _total else "#1e3a5f" if _done > 0 else "#6b1212"
        _sub_txt   = "All checks passed ✓" if _done == _total else f"{_total - _done} items pending"
    except Exception:
        _badge_txt, _badge_bg, _sub_txt = "Check", "#1e3a5f", "Driver health & startup control"
    _create_large_gradient_btn(
        left, "\U0001f680", "First Setup & Drivers",
        (239, 68, 68), (107, 33, 168),
        lambda: _nav_to("first_setup"),
        badge_text=_badge_txt, badge_bg=_badge_bg,
        sub_text=_sub_txt,
        tooltip=["Driver health  ·  Startup control", "Registry-based scan  ·  No admin needed"]
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


def _export_health_report():
    import json, datetime, subprocess as _sp
    try:
        report = {"generated_at": datetime.datetime.now().isoformat()}
        try:
            from core.hardware_detector import get_hardware_detector
            det = get_hardware_detector()
            if det.is_ready:
                report["hardware"] = det.get_data()
        except Exception:
            pass
        try:
            import psutil as _psu
            report["cpu_pct"] = _psu.cpu_percent(interval=0.1)
            mem = _psu.virtual_memory()
            report["ram_used_gb"] = round(mem.used / 1024 ** 3, 2)
            report["ram_total_gb"] = round(mem.total / 1024 ** 3, 2)
            report["ram_pct"] = mem.percent
            report["uptime_sec"] = int(__import__("time").time() - _psu.boot_time())
        except Exception:
            pass

        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "data", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(cache_dir, f"health_report_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        # Open folder in explorer so user can see the file
        _sp.Popen(["explorer", "/select,", path])
    except Exception as ex:
        print(f"[Export] Failed: {ex}")


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


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _make_scroll_frame(parent):
    """Returns (scrollable_frame, canvas) with mouse-wheel and full-width support."""
    BG = "#0a0e14"
    canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                      bg="#000000", troughcolor=BG, activebackground="#1a1d24", width=6)
    sf = tk.Frame(canvas, bg=BG)
    sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    win_id = canvas.create_window((0, 0), window=sf, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)

    # Keep inner frame as wide as the canvas
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width - 2))

    def _mw(event):
        try:
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
    canvas.bind_all("<MouseWheel>", _mw, add="+")

    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    return sf, canvas


def _sec_hdr(parent, text):
    """Compact section divider label."""
    row = tk.Frame(parent, bg="#0a0e14")
    row.pack(fill="x", padx=8, pady=(6, 1))
    tk.Label(row, text=text, font=("Segoe UI", 6, "bold"),
             bg="#0a0e14", fg="#4b5563").pack(side="left")
    tk.Frame(row, bg="#1f2937", height=1).pack(side="left", fill="x", expand=True, padx=6)


def _spec_row(parent, label, value, value_color="#e2e8f0", bg="#1a1d24"):
    """Single key-value row inside a card."""
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=6, pady=0)
    tk.Label(row, text=label, font=("Segoe UI", 7), bg=bg,
             fg="#6b7280", anchor="w", width=16).pack(side="left")
    tk.Label(row, text=value, font=("Segoe UI", 7, "bold"), bg=bg,
             fg=value_color, anchor="w").pack(side="left")


def _card(parent, title, icon, accent="#3b82f6", width=None):
    """Titled card frame. Returns inner frame."""
    outer = tk.Frame(parent, bg="#1a1d24",
                     highlightbackground="#2a2d34", highlightthickness=1)
    if width:
        outer.config(width=width)
        outer.pack_propagate(False)

    hdr = tk.Frame(outer, bg=accent, height=18)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text=f"{icon} {title}", font=("Segoe UI", 7, "bold"),
             bg=accent, fg="#ffffff", padx=6).pack(side="left", fill="y")

    inner = tk.Frame(outer, bg="#1a1d24")
    inner.pack(fill="both", expand=True, pady=2)
    return outer, inner


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH TAB
# ─────────────────────────────────────────────────────────────────────────────

def _build_health(self, parent):
    """Health tab — live component health overview, uptime, recent events."""
    BG = "#0a0e14"
    sf, _ = _make_scroll_frame(parent)
    refs = {}

    # ── Row 1: 4 metric cards ─────────────────────────────
    _sec_hdr(sf, "COMPONENT STATUS")
    cards_row = tk.Frame(sf, bg=BG)
    cards_row.pack(fill="x", padx=8, pady=2)

    _card_defs = [
        ("cpu_temp", "CPU TEMP", "🔥"),
        ("gpu_temp", "GPU TEMP", "🖥"),
        ("ram_pct",  "RAM",      "💾"),
        ("disk_pct", "DISK",     "🗄"),
    ]
    for key, label, icon in _card_defs:
        col = tk.Frame(cards_row, bg="#1a1d24",
                       highlightbackground="#2a2d34", highlightthickness=1)
        col.pack(side="left", fill="both", expand=True, padx=2)
        tk.Label(col, text=icon, font=("Segoe UI", 13), bg="#1a1d24",
                 fg="#94a3b8").pack(pady=(5, 0))
        tk.Label(col, text=label, font=("Segoe UI", 6, "bold"),
                 bg="#1a1d24", fg="#4b5563").pack()
        val_lbl = tk.Label(col, text="—", font=("Segoe UI", 13, "bold"),
                           bg="#1a1d24", fg="#10b981")
        val_lbl.pack(pady=(1, 0))
        status_lbl = tk.Label(col, text=" ", font=("Segoe UI", 6),
                               bg="#1a1d24", fg="#6b7280", pady=3)
        status_lbl.pack()
        refs[key] = (val_lbl, status_lbl)

    # ── Row 2: Health score gauge + uptime panel ───────────
    _sec_hdr(sf, "HEALTH SCORE  ·  UPTIME")
    mid_row = tk.Frame(sf, bg=BG)
    mid_row.pack(fill="x", padx=8, pady=2)

    # Score gauge (left)
    gauge_outer = tk.Frame(mid_row, bg="#1a1d24", width=110,
                           highlightbackground="#2a2d34", highlightthickness=1)
    gauge_outer.pack(side="left", fill="y", padx=(0, 4))
    gauge_outer.pack_propagate(False)
    tk.Label(gauge_outer, text="HEALTH SCORE", font=("Segoe UI", 6, "bold"),
             bg="#1a1d24", fg="#4b5563").pack(pady=(4, 0))
    score_canvas = tk.Canvas(gauge_outer, width=80, height=46,
                             bg="#1a1d24", highlightthickness=0)
    score_canvas.pack()
    score_lbl = tk.Label(gauge_outer, text="—", font=("Segoe UI", 14, "bold"),
                         bg="#1a1d24", fg="#10b981")
    score_lbl.pack()
    score_sub = tk.Label(gauge_outer, text=" ", font=("Segoe UI", 6),
                         bg="#1a1d24", fg="#6b7280", pady=3)
    score_sub.pack()
    refs["score_canvas"] = score_canvas
    refs["score_lbl"] = score_lbl
    refs["score_sub"] = score_sub

    # Uptime + alerts (right)
    right_col = tk.Frame(mid_row, bg=BG)
    right_col.pack(side="left", fill="both", expand=True)

    up_card = tk.Frame(right_col, bg="#1a1d24",
                       highlightbackground="#2a2d34", highlightthickness=1)
    up_card.pack(fill="x", pady=(0, 3))
    tk.Label(up_card, text="UPTIME", font=("Segoe UI", 6, "bold"),
             bg="#1a1d24", fg="#4b5563", pady=2).pack(anchor="w", padx=8)
    for key, label in [("session_up", "Session"), ("lifetime_up", "Lifetime (all-time)")]:
        row = tk.Frame(up_card, bg="#1a1d24")
        row.pack(fill="x", padx=8, pady=1)
        tk.Label(row, text=label, font=("Segoe UI", 7), bg="#1a1d24",
                 fg="#6b7280", width=18, anchor="w").pack(side="left")
        lbl = tk.Label(row, text="—", font=("Segoe UI", 7, "bold"),
                       bg="#1a1d24", fg="#94a3b8")
        lbl.pack(side="left")
        refs[key] = lbl
    tk.Frame(up_card, bg="#1a1d24", height=3).pack()

    # Alerts summary
    alerts_card = tk.Frame(right_col, bg="#1a1d24",
                           highlightbackground="#2a2d34", highlightthickness=1)
    alerts_card.pack(fill="x")
    tk.Label(alerts_card, text="ALERTS (last 24h)", font=("Segoe UI", 6, "bold"),
             bg="#1a1d24", fg="#4b5563", pady=2).pack(anchor="w", padx=8)
    alerts_row = tk.Frame(alerts_card, bg="#1a1d24")
    alerts_row.pack(fill="x", padx=8, pady=(0, 4))
    for key, label, color in [
        ("alerts_critical", "Critical", "#ef4444"),
        ("alerts_warning",  "Warning",  "#f59e0b"),
        ("alerts_info",     "Info",     "#6b7280"),
    ]:
        col_f = tk.Frame(alerts_row, bg="#1a1d24")
        col_f.pack(side="left", padx=8)
        cnt_lbl = tk.Label(col_f, text="—", font=("Segoe UI", 13, "bold"),
                           bg="#1a1d24", fg=color)
        cnt_lbl.pack()
        tk.Label(col_f, text=label, font=("Segoe UI", 6), bg="#1a1d24",
                 fg="#6b7280").pack()
        refs[key] = cnt_lbl

    # ── Row 3: Recent events table ─────────────────────────
    _sec_hdr(sf, "RECENT EVENTS")
    events_outer = tk.Frame(sf, bg="#0f1117",
                            highlightbackground="#2a2d34", highlightthickness=1)
    events_outer.pack(fill="x", padx=8, pady=2)

    hdr_bar = tk.Frame(events_outer, bg="#111827")
    hdr_bar.pack(fill="x")
    for col_txt, col_w in [("TIME", 10), ("SEV", 8), ("METRIC", 10), ("DESCRIPTION", 36)]:
        tk.Label(hdr_bar, text=col_txt, font=("Segoe UI", 6, "bold"),
                 bg="#111827", fg="#4b5563", width=col_w, anchor="w").pack(side="left", padx=2)

    refs["events_outer"] = events_outer
    refs["events_populated"] = False

    # ── Live refresh loop ──────────────────────────────────
    def _refresh():
        if not parent.winfo_exists():
            return
        try:
            _health_refresh(refs)
        except Exception:
            pass
        parent.after(2000, _refresh)

    parent.after(300, _refresh)


def _health_refresh(refs):
    """Update all health tab widgets. Called on the main thread via after()."""
    try:
        import psutil as _psu
        cpu_pct = _psu.cpu_percent(interval=None)
        mem = _psu.virtual_memory()
        ram_pct = mem.percent
    except Exception:
        cpu_pct, ram_pct = 0.0, 0.0

    try:
        from core.hardware_sensors import get_cpu_temp, get_gpu_temp
        cpu_temp = get_cpu_temp() or (35 + cpu_pct * 0.4)
        gpu_temp = get_gpu_temp()
    except Exception:
        cpu_temp = 35 + cpu_pct * 0.4
        gpu_temp = 0.0

    disk_pct = 0.0
    try:
        import psutil as _psu2
        for p in _psu2.disk_partitions():
            try:
                u = _psu2.disk_usage(p.mountpoint)
                if u.percent > disk_pct:
                    disk_pct = u.percent
            except Exception:
                pass
    except Exception:
        pass

    def _temp_col(t):
        if t >= 90: return "#ef4444"
        if t >= 85: return "#f97316"
        if t >= 70: return "#fbbf24"
        return "#10b981"

    def _pct_col(p):
        if p >= 95: return "#ef4444"
        if p >= 85: return "#f97316"
        if p >= 75: return "#fbbf24"
        return "#10b981"

    def _temp_status(t):
        if t >= 90: return "CRITICAL"
        if t >= 85: return "HOT"
        if t >= 70: return "WARM"
        return "COOL"

    def _pct_status(p):
        if p >= 95: return "CRITICAL"
        if p >= 85: return "HIGH"
        if p >= 75: return "MODERATE"
        return "NORMAL"

    card_vals = {
        "cpu_temp": (f"{cpu_temp:.0f}°C", _temp_col(cpu_temp), _temp_status(cpu_temp)),
        "gpu_temp": (f"{gpu_temp:.0f}°C" if gpu_temp else "N/A",
                     _temp_col(gpu_temp) if gpu_temp else "#6b7280",
                     _temp_status(gpu_temp) if gpu_temp else "N/A"),
        "ram_pct":  (f"{ram_pct:.0f}%", _pct_col(ram_pct), _pct_status(ram_pct)),
        "disk_pct": (f"{disk_pct:.0f}%", _pct_col(disk_pct), _pct_status(disk_pct)),
    }
    for key, (val, color, status) in card_vals.items():
        if key in refs:
            try:
                v_lbl, s_lbl = refs[key]
                if v_lbl.winfo_exists():
                    v_lbl.config(text=val, fg=color)
                    s_lbl.config(text=status)
            except Exception:
                pass

    # Health score
    score = 100
    if cpu_temp >= 90: score -= 20
    elif cpu_temp >= 85: score -= 12
    elif cpu_temp >= 70: score -= 5
    if gpu_temp and gpu_temp >= 90: score -= 20
    elif gpu_temp and gpu_temp >= 85: score -= 12
    elif gpu_temp and gpu_temp >= 70: score -= 5
    if ram_pct >= 95: score -= 15
    elif ram_pct >= 85: score -= 8
    elif ram_pct >= 75: score -= 4
    if disk_pct >= 95: score -= 10
    elif disk_pct >= 85: score -= 5
    score = max(0, min(100, score))
    sc_col = "#10b981" if score >= 80 else "#fbbf24" if score >= 60 else "#ef4444"
    sc_txt = "GOOD" if score >= 80 else "FAIR" if score >= 60 else "POOR"
    try:
        sc = refs["score_canvas"]
        if sc.winfo_exists():
            sc.delete("all")
            # Background arc
            sc.create_arc(8, 4, 72, 44, start=200, extent=-160,
                          style="arc", outline="#2a2d34", width=5)
            # Filled arc
            sc.create_arc(8, 4, 72, 44, start=200, extent=-int(160 * score / 100),
                          style="arc", outline=sc_col, width=5)
        refs["score_lbl"].config(text=str(score), fg=sc_col)
        refs["score_sub"].config(text=sc_txt)
    except Exception:
        pass

    # Uptime
    try:
        import psutil as _pu3, time as _t
        boot_ts = _pu3.boot_time()
        sec = int(_t.time() - boot_ts)
        h, m = sec // 3600, (sec % 3600) // 60
        session_str = f"{h}h {m}m"
    except Exception:
        session_str = "N/A"

    lifetime_str = session_str
    try:
        from hck_stats_engine.query_api import query_api
        lt = query_api.get_lifetime_uptime() if hasattr(query_api, "get_lifetime_uptime") else None
        if lt:
            lh, lm = int(lt // 3600), int((lt % 3600) // 60)
            lifetime_str = f"{lh}h {lm}m"
    except Exception:
        pass

    for key, val in [("session_up", session_str), ("lifetime_up", lifetime_str)]:
        try:
            lbl = refs.get(key)
            if lbl and lbl.winfo_exists():
                lbl.config(text=val)
        except Exception:
            pass

    # Alerts
    try:
        from hck_stats_engine.events import event_detector
        counts = event_detector.get_active_alerts_count()
        for key, sev in [("alerts_critical", "critical"),
                         ("alerts_warning", "warning"),
                         ("alerts_info", "info")]:
            lbl = refs.get(key)
            if lbl and lbl.winfo_exists():
                lbl.config(text=str(counts.get(sev, 0)))
    except Exception:
        pass

    # Events table (populate once)
    if not refs.get("events_populated"):
        try:
            _populate_events_table(refs["events_outer"])
            refs["events_populated"] = True
        except Exception:
            pass


def _populate_events_table(parent):
    """Query recent events from SQLite and render rows."""
    events = []
    try:
        from hck_stats_engine.db_manager import db_manager
        if db_manager.is_ready:
            conn = db_manager.get_connection()
            if conn:
                rows = conn.execute(
                    "SELECT timestamp, severity, metric, description "
                    "FROM events ORDER BY timestamp DESC LIMIT 10"
                ).fetchall()
                import datetime
                for r in rows:
                    ts = r["timestamp"]
                    dt = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                    events.append({
                        "time": dt,
                        "severity": r["severity"] or "",
                        "metric": r["metric"] or "",
                        "description": (r["description"] or "")[:50],
                    })
    except Exception:
        pass

    if not events:
        tk.Label(parent, text="No events recorded yet.", font=("Segoe UI", 7),
                 bg="#0f1117", fg="#4b5563", pady=6).pack()
        return

    sev_colors = {"critical": "#ef4444", "warning": "#f59e0b", "info": "#6b7280"}
    for ev in events:
        row = tk.Frame(parent, bg="#0f1117")
        row.pack(fill="x")
        sc = sev_colors.get(ev["severity"], "#6b7280")
        for text, w, fg in [
            (ev["time"], 10, "#6b7280"),
            (ev["severity"][:4].upper(), 8, sc),
            (ev["metric"][:10], 10, "#94a3b8"),
            (ev["description"][:46], 36, "#64748b"),
        ]:
            tk.Label(row, text=text, font=("Segoe UI", 6), bg="#0f1117",
                     fg=fg, width=w, anchor="w").pack(side="left", padx=2)


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENTS TAB
# ─────────────────────────────────────────────────────────────────────────────

def _build_components(self, parent):
    """Components tab — detailed hardware specs via hardware_detector."""
    BG = "#0a0e14"
    sf, _ = _make_scroll_frame(parent)

    # Loading state
    loading_lbl = tk.Label(sf, text="Scanning hardware…", font=("Segoe UI", 9),
                           bg=BG, fg="#4b5563")
    loading_lbl.pack(pady=20)

    def _on_scan_done(data):
        if not parent.winfo_exists():
            return
        parent.after(0, lambda: _render_components(sf, loading_lbl, data))

    try:
        from core.hardware_detector import get_hardware_detector
        det = get_hardware_detector()
        if det.is_ready:
            _on_scan_done(det.get_data())
        else:
            det.scan_async(on_done=_on_scan_done)
    except Exception as ex:
        loading_lbl.config(text=f"Hardware scan failed: {ex}", fg="#ef4444")


def _render_components(sf, loading_lbl, data):
    """Render component cards after scan completes."""
    try:
        if loading_lbl.winfo_exists():
            loading_lbl.destroy()
    except Exception:
        pass

    BG = "#0a0e14"
    cpu = data.get("cpu", {})
    gpu = data.get("gpu", {})
    ram = data.get("ram", {})
    storage = data.get("storage", {})
    mb = data.get("motherboard", {})

    # ── CPU + GPU row ──────────────────────────────────────
    _sec_hdr(sf, "PROCESSOR  ·  GRAPHICS")
    row1 = tk.Frame(sf, bg=BG)
    row1.pack(fill="x", padx=8, pady=2)

    cpu_outer, cpu_inner = _card(row1, "CPU", "🔥", "#3b82f6")
    cpu_outer.pack(side="left", fill="both", expand=True, padx=(0, 3))
    _spec_row(cpu_inner, "Name", cpu.get("name", "N/A"))
    cores_p = cpu.get("cores_physical", 0)
    cores_l = cpu.get("cores_logical", 0)
    _spec_row(cpu_inner, "Cores / Threads", f"{cores_p}C / {cores_l}T" if cores_p else "N/A")
    freq_cur = cpu.get("freq_current_mhz", 0)
    freq_max = cpu.get("freq_max_mhz", 0)
    _spec_row(cpu_inner, "Freq (cur / max)",
              f"{freq_cur} / {freq_max} MHz" if freq_cur else "N/A")
    _spec_row(cpu_inner, "Arch", cpu.get("architecture", "N/A"))
    tk.Frame(cpu_inner, bg="#1a1d24", height=3).pack()

    gpu_outer, gpu_inner = _card(row1, "GPU", "🖥", "#8b5cf6")
    gpu_outer.pack(side="left", fill="both", expand=True)
    _spec_row(gpu_inner, "Name", gpu.get("name", "N/A"))
    vram = gpu.get("vram_mb", 0)
    _spec_row(gpu_inner, "VRAM", f"{vram / 1024:.1f} GB" if vram else "N/A")
    _spec_row(gpu_inner, "Driver ver", gpu.get("driver_version", "N/A") or "N/A")
    _spec_row(gpu_inner, "Driver date", gpu.get("driver_date", "N/A") or "N/A")
    tk.Frame(gpu_inner, bg="#1a1d24", height=3).pack()

    # ── RAM + Storage row ──────────────────────────────────
    _sec_hdr(sf, "MEMORY  ·  STORAGE")
    row2 = tk.Frame(sf, bg=BG)
    row2.pack(fill="x", padx=8, pady=2)

    ram_outer, ram_inner = _card(row2, "RAM", "💾", "#10b981")
    ram_outer.pack(side="left", fill="both", expand=True, padx=(0, 3))
    _spec_row(ram_inner, "Total", f"{ram.get('total_gb', 0):.1f} GB")
    _spec_row(ram_inner, "Used", f"{ram.get('used_gb', 0):.1f} GB ({ram.get('percent', 0):.0f}%)",
              value_color=_pct_color_str(ram.get("percent", 0)))
    speed = ram.get("speed_mhz", 0)
    _spec_row(ram_inner, "Speed", f"{speed} MHz" if speed else "N/A")
    _spec_row(ram_inner, "Form factor", ram.get("form_factor", "N/A") or "N/A")
    slots = ram.get("slots_used", 0)
    _spec_row(ram_inner, "Modules", f"{slots} slot(s) used" if slots else "N/A")
    tk.Frame(ram_inner, bg="#1a1d24", height=3).pack()

    st_outer, st_inner = _card(row2, "Storage", "🗄", "#f59e0b")
    st_outer.pack(side="left", fill="both", expand=True)
    drives = storage.get("drives", [])
    parts = storage.get("partitions", [])
    if drives:
        for d in drives:
            model = d.get("model", "Unknown")[:22]
            size = d.get("size_gb", 0)
            _spec_row(st_inner, model, f"{size:.0f} GB" if size else "N/A")
    else:
        _spec_row(st_inner, "Drives", "N/A")
    if parts:
        tk.Frame(st_inner, bg="#2a2d34", height=1).pack(fill="x", padx=4, pady=2)
        for p in parts[:4]:
            dev = p.get("device", "?")[0] + ":"
            pct = p.get("percent", 0)
            free = p.get("free_gb", 0)
            _spec_row(st_inner, dev, f"{pct:.0f}%  {free:.1f} GB free",
                      value_color=_pct_color_str(pct))
    tk.Frame(st_inner, bg="#1a1d24", height=3).pack()

    # ── Motherboard ────────────────────────────────────────
    _sec_hdr(sf, "MOTHERBOARD")
    mb_row = tk.Frame(sf, bg=BG)
    mb_row.pack(fill="x", padx=8, pady=2)
    mb_outer, mb_inner = _card(mb_row, "Motherboard", "⚡", "#ef4444")
    mb_outer.pack(fill="x")
    mb_name = " ".join(filter(None, [mb.get("manufacturer", ""), mb.get("product", "")])) or "N/A"
    _spec_row(mb_inner, "Model", mb_name)
    _spec_row(mb_inner, "Version", mb.get("version", "N/A") or "N/A")
    tk.Frame(mb_inner, bg="#1a1d24", height=4).pack()


def _pct_color_str(pct: float) -> str:
    if pct >= 95: return "#ef4444"
    if pct >= 85: return "#f97316"
    if pct >= 75: return "#fbbf24"
    return "#10b981"


# ─────────────────────────────────────────────────────────────────────────────
# EFFICIENCY TAB
# ─────────────────────────────────────────────────────────────────────────────

def _build_efficiency(self, parent):
    """Efficiency tab — live top process consumers + power plan."""
    BG = "#0a0e14"
    sf, _ = _make_scroll_frame(parent)
    refs = {}

    # ── CPU Frequency bar ──────────────────────────────────
    _sec_hdr(sf, "CPU FREQUENCY")
    freq_frame = tk.Frame(sf, bg="#1a1d24",
                          highlightbackground="#2a2d34", highlightthickness=1)
    freq_frame.pack(fill="x", padx=8, pady=2)
    freq_bar_canvas = tk.Canvas(freq_frame, height=12, bg="#1a1d24",
                                highlightthickness=0)
    freq_bar_canvas.pack(fill="x", padx=6, pady=4)
    freq_lbl = tk.Label(freq_frame, text="—", font=("Segoe UI", 6),
                        bg="#1a1d24", fg="#94a3b8", pady=2)
    freq_lbl.pack(anchor="e", padx=8)
    refs["freq_bar"] = freq_bar_canvas
    refs["freq_lbl"] = freq_lbl

    # ── Top CPU consumers ──────────────────────────────────
    _sec_hdr(sf, "TOP CPU CONSUMERS")
    cpu_frame = tk.Frame(sf, bg="#0f1117",
                         highlightbackground="#2a2d34", highlightthickness=1)
    cpu_frame.pack(fill="x", padx=8, pady=2)
    refs["cpu_procs_frame"] = cpu_frame

    # ── Top RAM consumers ──────────────────────────────────
    _sec_hdr(sf, "TOP RAM CONSUMERS")
    ram_frame = tk.Frame(sf, bg="#0f1117",
                         highlightbackground="#2a2d34", highlightthickness=1)
    ram_frame.pack(fill="x", padx=8, pady=2)
    refs["ram_procs_frame"] = ram_frame

    # ── Power plan ─────────────────────────────────────────
    _sec_hdr(sf, "POWER PLAN")
    pwr_frame = tk.Frame(sf, bg="#1a1d24",
                         highlightbackground="#2a2d34", highlightthickness=1)
    pwr_frame.pack(fill="x", padx=8, pady=2)
    pwr_lbl = tk.Label(pwr_frame, text="Detecting…", font=("Segoe UI", 8, "bold"),
                       bg="#1a1d24", fg="#94a3b8", pady=6)
    pwr_lbl.pack(anchor="w", padx=10)
    refs["pwr_lbl"] = pwr_lbl

    def _load_power_plan():
        try:
            import subprocess
            r = subprocess.run(["powercfg", "/getactivescheme"],
                               capture_output=True, text=True, timeout=3)
            line = r.stdout.strip()
            if "(" in line and ")" in line:
                name = line[line.rfind("(") + 1:line.rfind(")")]
            else:
                name = line[-30:] if line else "N/A"
        except Exception:
            name = "N/A"
        if parent.winfo_exists():
            parent.after(0, lambda: pwr_lbl.config(text=name) if pwr_lbl.winfo_exists() else None)

    import threading as _thr
    _thr.Thread(target=_load_power_plan, daemon=True).start()

    # ── Live refresh ───────────────────────────────────────
    def _refresh():
        if not parent.winfo_exists():
            return
        try:
            _efficiency_refresh(refs)
        except Exception:
            pass
        parent.after(2000, _refresh)

    parent.after(300, _refresh)


def _efficiency_refresh(refs):
    """Update efficiency tab widgets."""
    try:
        import psutil as _psu

        # CPU frequency bar
        freq = _psu.cpu_freq()
        if freq:
            cur, max_f = freq.current, freq.max or freq.current
            pct = min(1.0, cur / max_f) if max_f else 0.5
            fc = refs.get("freq_bar")
            if fc and fc.winfo_exists():
                w = fc.winfo_width() or 200
                fc.delete("all")
                fc.create_rectangle(0, 0, w, 12, fill="#1f2937", outline="")
                bar_col = "#3b82f6" if pct < 0.8 else "#f59e0b" if pct < 0.95 else "#ef4444"
                fc.create_rectangle(0, 0, int(w * pct), 12, fill=bar_col, outline="")
            fl = refs.get("freq_lbl")
            if fl and fl.winfo_exists():
                fl.config(text=f"{cur:.0f} MHz  /  {max_f:.0f} MHz max")

        # Top CPU processes
        cpu_f = refs.get("cpu_procs_frame")
        if cpu_f and cpu_f.winfo_exists():
            for w in cpu_f.winfo_children():
                w.destroy()
            procs = sorted(_psu.process_iter(["name", "cpu_percent"]),
                           key=lambda p: p.info.get("cpu_percent", 0) or 0,
                           reverse=True)[:6]
            _render_proc_rows(cpu_f, procs, "cpu_percent", "%", "#3b82f6")

        # Top RAM processes
        ram_f = refs.get("ram_procs_frame")
        if ram_f and ram_f.winfo_exists():
            for w in ram_f.winfo_children():
                w.destroy()
            procs = sorted(_psu.process_iter(["name", "memory_percent"]),
                           key=lambda p: p.info.get("memory_percent", 0) or 0,
                           reverse=True)[:6]
            _render_proc_rows(ram_f, procs, "memory_percent", "%", "#10b981")
    except Exception:
        pass


def _render_proc_rows(parent, procs, metric_key, unit, bar_color):
    """Render process rows with mini usage bars."""
    BG = "#0f1117"
    hdr = tk.Frame(parent, bg="#111827")
    hdr.pack(fill="x")
    tk.Label(hdr, text="PROCESS", font=("Segoe UI", 6, "bold"),
             bg="#111827", fg="#4b5563", width=24, anchor="w").pack(side="left", padx=4)
    tk.Label(hdr, text="USAGE", font=("Segoe UI", 6, "bold"),
             bg="#111827", fg="#4b5563").pack(side="right", padx=4)

    for proc in procs:
        try:
            name = (proc.info.get("name", "?") or "?")[:22]
            val = proc.info.get(metric_key, 0) or 0
        except Exception:
            continue
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=0)
        tk.Label(row, text=name, font=("Segoe UI", 7), bg=BG,
                 fg="#94a3b8", width=24, anchor="w").pack(side="left", padx=4)
        bar_outer = tk.Frame(row, bg="#1f2937", height=8)
        bar_outer.pack(side="left", fill="x", expand=True, padx=4, pady=3)
        bar_outer.update_idletasks()
        bar_w = max(1, int((val / 100) * 120))
        bar_inner = tk.Frame(bar_outer, bg=bar_color, width=bar_w, height=8)
        bar_inner.place(x=0, y=0, relheight=1.0)
        tk.Label(row, text=f"{val:.1f}{unit}", font=("Segoe UI", 6, "bold"),
                 bg=BG, fg="#e2e8f0", width=7, anchor="e").pack(side="right", padx=4)


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP TAB
# ─────────────────────────────────────────────────────────────────────────────

def _build_startup(self, parent):
    """Startup tab — read-only registry startup program list."""
    BG = "#0a0e14"
    sf, _ = _make_scroll_frame(parent)

    loading_lbl = tk.Label(sf, text="Reading startup entries…", font=("Segoe UI", 8),
                           bg=BG, fg="#4b5563", pady=10)
    loading_lbl.pack()

    def _load():
        entries = _read_startup_registry()
        if parent.winfo_exists():
            parent.after(0, lambda: _render_startup(sf, loading_lbl, entries, self))

    import threading as _thr
    _thr.Thread(target=_load, daemon=True).start()


def _read_startup_registry() -> list:
    """Return list of {'name', 'command', 'source'} from Run keys."""
    entries = []
    try:
        import winreg
        keys = [
            (winreg.HKEY_CURRENT_USER,
             r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        ]
        for hive, path, label in keys:
            try:
                key = winreg.OpenKey(hive, path)
                i = 0
                while True:
                    try:
                        name, cmd, _ = winreg.EnumValue(key, i)
                        entries.append({
                            "name": name,
                            "command": cmd[:60],
                            "source": label,
                        })
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                pass
    except Exception:
        pass
    return entries


def _render_startup(sf, loading_lbl, entries, self_ref):
    """Render startup list after registry read."""
    try:
        if loading_lbl.winfo_exists():
            loading_lbl.destroy()
    except Exception:
        pass

    BG = "#0a0e14"
    count = len(entries)
    color = "#ef4444" if count > 12 else "#f59e0b" if count > 8 else "#10b981"

    # Count badge row
    badge_row = tk.Frame(sf, bg=BG)
    badge_row.pack(fill="x", padx=8, pady=(4, 2))
    tk.Label(badge_row, text=f"{count} startup items found",
             font=("Segoe UI", 9, "bold"), bg=BG, fg=color).pack(side="left")

    if count > 8:
        hint = "   High startup count may slow boot time."
        tk.Label(badge_row, text=hint, font=("Segoe UI", 7), bg=BG,
                 fg="#6b7280").pack(side="left")

    # Table header
    hdr = tk.Frame(sf, bg="#111827")
    hdr.pack(fill="x", padx=8)
    for col_txt, col_w in [("NAME", 22), ("SOURCE", 6), ("COMMAND", 40)]:
        tk.Label(hdr, text=col_txt, font=("Segoe UI", 6, "bold"),
                 bg="#111827", fg="#4b5563", width=col_w, anchor="w").pack(side="left", padx=3)

    # Rows
    table = tk.Frame(sf, bg="#0f1117", highlightbackground="#2a2d34",
                     highlightthickness=1)
    table.pack(fill="x", padx=8, pady=(0, 4))

    if not entries:
        tk.Label(table, text="No startup items found in registry.",
                 font=("Segoe UI", 7), bg="#0f1117", fg="#4b5563", pady=8).pack()
    else:
        for i, e in enumerate(entries):
            row_bg = "#0f1117" if i % 2 == 0 else "#111827"
            row = tk.Frame(table, bg=row_bg)
            row.pack(fill="x")
            src_col = "#3b82f6" if e["source"] == "HKCU" else "#8b5cf6"
            for text, w, fg in [
                (e["name"][:22], 22, "#e2e8f0"),
                (e["source"], 6, src_col),
                (e["command"][:40], 40, "#6b7280"),
            ]:
                tk.Label(row, text=text, font=("Segoe UI", 7), bg=row_bg,
                         fg=fg, width=w, anchor="w").pack(side="left", padx=3, pady=1)

    # "Manage in Setup & Drivers" button
    tk.Frame(sf, bg=BG, height=4).pack()
    manage_btn = tk.Label(sf, text="Manage startup in  Setup & Drivers →",
                          font=("Segoe UI", 8, "bold"), bg="#1e3a5f",
                          fg="#93c5fd", cursor="hand2", pady=6)
    manage_btn.pack(fill="x", padx=8, pady=2)

    def _goto_setup():
        try:
            if hasattr(self_ref, "_handle_sidebar_navigation"):
                self_ref._handle_sidebar_navigation("first_setup", None)
                if hasattr(self_ref, "sidebar") and self_ref.sidebar:
                    self_ref.sidebar.set_active_page("first_setup", None)
        except Exception:
            pass

    manage_btn.bind("<Button-1>", lambda e: _goto_setup())
    manage_btn.bind("<Enter>", lambda e: manage_btn.config(bg="#1d4ed8"))
    manage_btn.bind("<Leave>", lambda e: manage_btn.config(bg="#1e3a5f"))
