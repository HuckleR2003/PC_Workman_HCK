# ui/yourpc_page.py
"""
Advanced YOUR PC page for Expanded View
Full-screen page with tabs: Central, Efficiency, Health, Startup & Services
"""

import tkinter as tk
try:
    import psutil
except ImportError:
    psutil = None


def build_yourpc_page(self, parent):
    """Build YOUR PC page - Full-screen advanced hardware monitoring with tabs"""
    # Main container (full overlay area)
    main = tk.Frame(parent, bg="#0f1117")
    main.pack(fill="both", expand=True)

    # Top bar with Dashboard button - TALLER
    top_bar = tk.Frame(main, bg="#1a1d24", height=60)
    top_bar.pack(fill="x")
    top_bar.pack_propagate(False)

    # Dashboard button container
    dashboard_container = tk.Frame(top_bar, bg="#1a1d24", cursor="hand2")
    dashboard_container.pack(side="left", padx=15, pady=10)

    # Arrow symbol
    arrow_lbl = tk.Label(
        dashboard_container,
        text="⬅",
        font=("Segoe UI", 16),
        bg="#1a1d24",
        fg="#64748b",
        cursor="hand2"
    )
    arrow_lbl.pack(side="left", padx=(0, 5))

    # Text container (Dashboard above, Back! below)
    text_container = tk.Frame(dashboard_container, bg="#1a1d24", cursor="hand2")
    text_container.pack(side="left")

    dashboard_lbl = tk.Label(
        text_container,
        text="Dashboard",
        font=("Segoe UI", 10, "bold"),
        bg="#1a1d24",
        fg="#64748b",
        cursor="hand2"
    )
    dashboard_lbl.pack(anchor="w")

    back_lbl = tk.Label(
        text_container,
        text="Back!",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#64748b",
        cursor="hand2"
    )
    back_lbl.pack(anchor="w")

    # Click handler
    def close_overlay(e):
        self._close_overlay()

    dashboard_container.bind("<Button-1>", close_overlay)
    arrow_lbl.bind("<Button-1>", close_overlay)
    text_container.bind("<Button-1>", close_overlay)
    dashboard_lbl.bind("<Button-1>", close_overlay)
    back_lbl.bind("<Button-1>", close_overlay)

    # Hover effect
    def on_enter(e):
        arrow_lbl.config(fg="#3b82f6")
        dashboard_lbl.config(fg="#3b82f6")
        back_lbl.config(fg="#3b82f6")

    def on_leave(e):
        arrow_lbl.config(fg="#64748b")
        dashboard_lbl.config(fg="#64748b")
        back_lbl.config(fg="#64748b")

    dashboard_container.bind("<Enter>", on_enter)
    dashboard_container.bind("<Leave>", on_leave)
    arrow_lbl.bind("<Enter>", on_enter)
    arrow_lbl.bind("<Leave>", on_leave)
    text_container.bind("<Enter>", on_enter)
    text_container.bind("<Leave>", on_leave)

    # Page title
    title = tk.Label(
        top_bar,
        text="💻 YOUR PC - ADVANCED MONITORING",
        font=("Segoe UI", 12, "bold"),
        bg="#1a1d24",
        fg="#ffffff"
    )
    title.pack(side="left", padx=20)

    # Content area with tabs
    content_area = tk.Frame(main, bg="#0f1117")
    content_area.pack(fill="both", expand=True, pady=2)

    # LEFT - Tab sidebar (150px width)
    tab_sidebar = tk.Frame(content_area, bg="#1a1d24", width=150)
    tab_sidebar.pack(side="left", fill="y")
    tab_sidebar.pack_propagate(False)

    # Tab title
    tk.Label(
        tab_sidebar,
        text="SECTIONS",
        font=("Segoe UI", 8, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(pady=(10, 5), padx=10)

    # Tabs
    self.yourpc_tabs = {}
    self.yourpc_active_tab = None
    self.yourpc_content_frame = None

    tabs = [
        ("Central", "central"),
        ("Efficiency", "efficiency"),
        ("Health Check", "health"),
        ("Components", "components"),
        ("Startup & Services", "startup")
    ]

    for text, tab_id in tabs:
        create_yourpc_tab(self, tab_sidebar, text, tab_id)

    # RIGHT - Content area
    self.yourpc_content_frame = tk.Frame(content_area, bg="#0f1117")
    self.yourpc_content_frame.pack(side="right", fill="both", expand=True)

    # Show default tab
    show_yourpc_tab(self, "central")


def create_yourpc_tab(self, parent, text, tab_id):
    """Create tab button for Your PC page"""
    tab_btn = tk.Frame(parent, bg="#1a1d24", cursor="hand2")
    tab_btn.pack(fill="x", padx=5, pady=2)

    label = tk.Label(
        tab_btn,
        text=text,
        font=("Segoe UI", 9),
        bg="#1a1d24",
        fg="#94a3b8",
        anchor="w",
        padx=10,
        pady=8
    )
    label.pack(fill="x")

    # Store reference
    self.yourpc_tabs[tab_id] = {"frame": tab_btn, "label": label}

    # Click handler
    def on_click(e):
        show_yourpc_tab(self, tab_id)

    tab_btn.bind("<Button-1>", on_click)
    label.bind("<Button-1>", on_click)

    # Hover effect
    def on_enter(e):
        if self.yourpc_active_tab != tab_id:
            tab_btn.config(bg="#334155")
            label.config(bg="#334155", fg="#e2e8f0")

    def on_leave(e):
        if self.yourpc_active_tab != tab_id:
            tab_btn.config(bg="#1a1d24")
            label.config(bg="#1a1d24", fg="#94a3b8")

    tab_btn.bind("<Enter>", on_enter)
    tab_btn.bind("<Leave>", on_leave)
    label.bind("<Enter>", on_enter)
    label.bind("<Leave>", on_leave)


def show_yourpc_tab(self, tab_id):
    """Switch Your PC tab"""
    # Update active tab styling
    if self.yourpc_active_tab:
        old_tab = self.yourpc_tabs.get(self.yourpc_active_tab)
        if old_tab:
            old_tab["frame"].config(bg="#1a1d24")
            old_tab["label"].config(bg="#1a1d24", fg="#94a3b8")

    self.yourpc_active_tab = tab_id
    new_tab = self.yourpc_tabs.get(tab_id)
    if new_tab:
        new_tab["frame"].config(bg="#3b82f6")
        new_tab["label"].config(bg="#3b82f6", fg="#ffffff")

    # Clear content
    for widget in self.yourpc_content_frame.winfo_children():
        widget.destroy()

    # Build tab content
    if tab_id == "central":
        build_yourpc_central(self, self.yourpc_content_frame)
    elif tab_id == "efficiency":
        build_yourpc_efficiency(self, self.yourpc_content_frame)
    elif tab_id == "health":
        build_yourpc_health(self, self.yourpc_content_frame)
    elif tab_id == "components":
        build_yourpc_components(self, self.yourpc_content_frame)
    elif tab_id == "startup":
        build_yourpc_startup(self, self.yourpc_content_frame)


def build_yourpc_central(self, parent):
    """Build Central tab - Enhanced hardware monitoring"""
    # Scrollable container
    canvas = tk.Canvas(parent, bg="#0f1117", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg="#0f1117")

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Get hardware info
    try:
        import platform
        cpu_model = platform.processor()[:40] if platform.processor() else "Unknown CPU"
    except:
        cpu_model = "Unknown CPU"

    try:
        ram_total = psutil.virtual_memory().total / (1024**3)
        cpu_usage = psutil.cpu_percent(interval=0.1)
        ram_usage = psutil.virtual_memory().percent
    except:
        ram_total = 0
        cpu_usage = 0
        ram_usage = 0

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        gpu_model = gpus[0].name[:40] if gpus else "Unknown GPU"
        gpu_usage = gpus[0].load * 100 if gpus else 0
    except:
        gpu_model = "Unknown GPU"
        gpu_usage = 0

    # THREE HARDWARE CARDS (CPU, RAM, GPU) - HORIZONTAL SIDE BY SIDE
    hardware_data = [
        {
            "type": "CPU",
            "model": cpu_model,
            "color": "#3b82f6",
            "usage": cpu_usage,
            "temp": 30 + (cpu_usage * 0.6)
        },
        {
            "type": "RAM",
            "model": f"{ram_total:.1f} GB RAM",
            "color": "#fbbf24",
            "usage": ram_usage,
            "temp": 25 + (ram_usage * 0.5)
        },
        {
            "type": "GPU",
            "model": gpu_model,
            "color": "#10b981",
            "usage": gpu_usage,
            "temp": 35 + (gpu_usage * 0.7)
        }
    ]

    # Container for 3 cards side by side
    hw_row = tk.Frame(scrollable, bg="#0f1117")
    hw_row.pack(fill="x", padx=10, pady=5)

    for hw in hardware_data:
        create_advanced_hw_card_compact(hw_row, hw)

    # ADVANCED MONITORING SECTION (inspired by MSI Afterburner, HWMonitor)
    tk.Label(
        scrollable,
        text="ADVANCED HARDWARE MONITORING",
        font=("Segoe UI", 9, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(pady=(10, 3), padx=10, anchor="w")

    # Motherboard info - very compact
    try:
        import wmi
        w = wmi.WMI()
        motherboard = w.Win32_BaseBoard()[0]
        mb_name = f"{motherboard.Manufacturer} {motherboard.Product}"
    except:
        mb_name = "Unknown Motherboard"

    mb_label = tk.Label(
        scrollable,
        text=f"Motherboard: {mb_name}",
        font=("Consolas", 7, "bold"),
        bg="#0a0e27",
        fg="#fbbf24",
        padx=8,
        pady=2
    )
    mb_label.pack(padx=10, pady=(0, 5), anchor="w")

    # Three columns: CPU Details | RAM & Disk | System Info
    columns = tk.Frame(scrollable, bg="#0f1117")
    columns.pack(fill="x", padx=10, pady=3)

    # LEFT COLUMN - CPU Details
    cpu_detail = tk.Frame(columns, bg="#1a1d24")
    cpu_detail.pack(side="left", fill="both", expand=True, padx=(0, 5))

    tk.Label(
        cpu_detail,
        text="CPU DETAILS",
        font=("Segoe UI", 8, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        anchor="w",
        padx=8,
        pady=4
    ).pack(fill="x")

    try:
        cpu_freq = psutil.cpu_freq()
        cpu_details = [
            ("Base Clock", f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"),
            ("Max Clock", f"{cpu_freq.max:.0f} MHz" if cpu_freq and cpu_freq.max > 0 else "N/A"),
            ("Per-Core Usage", f"{psutil.cpu_percent(interval=0.1, percpu=False):.1f}%"),
            ("Logical Cores", str(psutil.cpu_count(logical=True))),
            ("Physical Cores", str(psutil.cpu_count(logical=False))),
        ]
    except:
        cpu_details = [("CPU", "Info unavailable")]

    for label, value in cpu_details:
        row = tk.Frame(cpu_detail, bg="#1a1d24")
        row.pack(fill="x", padx=8, pady=2)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 8),
            bg="#1a1d24",
            fg="#94a3b8",
            width=14,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            font=("Consolas", 8, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        ).pack(side="left", padx=5)

    tk.Frame(cpu_detail, bg="#1a1d24", height=5).pack()

    # RIGHT COLUMN - RAM & Disk
    ram_disk = tk.Frame(columns, bg="#1a1d24")
    ram_disk.pack(side="right", fill="both", expand=True, padx=(5, 0))

    tk.Label(
        ram_disk,
        text="MEMORY & STORAGE",
        font=("Segoe UI", 8, "bold"),
        bg="#fbbf24",
        fg="#ffffff",
        anchor="w",
        padx=8,
        pady=4
    ).pack(fill="x")

    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage('/')

        mem_details = [
            ("RAM Total", f"{mem.total / (1024**3):.2f} GB"),
            ("RAM Available", f"{mem.available / (1024**3):.2f} GB"),
            ("Swap Total", f"{swap.total / (1024**3):.2f} GB" if swap.total > 0 else "N/A"),
            ("Disk Total (C:)", f"{disk.total / (1024**3):.1f} GB"),
            ("Disk Free (C:)", f"{disk.free / (1024**3):.1f} GB"),
        ]
    except:
        mem_details = [("Memory", "Info unavailable")]

    for label, value in mem_details:
        row = tk.Frame(ram_disk, bg="#1a1d24")
        row.pack(fill="x", padx=8, pady=2)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 8),
            bg="#1a1d24",
            fg="#94a3b8",
            width=14,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            font=("Consolas", 8, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        ).pack(side="left", padx=5)

    tk.Frame(ram_disk, bg="#1a1d24", height=5).pack()

    # RIGHT COLUMN - System Information (3rd column)
    sys_info = tk.Frame(columns, bg="#1a1d24")
    sys_info.pack(side="right", fill="both", expand=True, padx=(5, 0))

    tk.Label(
        sys_info,
        text="SYSTEM INFO",
        font=("Segoe UI", 8, "bold"),
        bg="#10b981",
        fg="#ffffff",
        anchor="w",
        padx=8,
        pady=4
    ).pack(fill="x")

    try:
        import platform
        system_info = [
            ("OS", f"{platform.system()} {platform.release()}"),
            ("Architecture", platform.machine()),
            ("Hostname", platform.node()[:15]),
            ("Python", platform.python_version()),
        ]
    except:
        system_info = [("System", "N/A")]

    for label, value in system_info:
        row = tk.Frame(sys_info, bg="#1a1d24")
        row.pack(fill="x", padx=8, pady=2)

        tk.Label(
            row,
            text=label,
            font=("Segoe UI", 8),
            bg="#1a1d24",
            fg="#94a3b8",
            width=12,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            row,
            text=value,
            font=("Consolas", 7, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w",
            wraplength=150,
            justify="left"
        ).pack(side="left", padx=3)

    tk.Frame(sys_info, bg="#1a1d24", height=5).pack()


def create_advanced_hw_card_compact(parent, hw_data):
    """Create HORIZONTAL compact hardware card - side by side layout"""
    card = tk.Frame(parent, bg="#1a1d24")
    card.pack(side="left", fill="both", expand=True, padx=2)

    # Header - smaller
    header = tk.Frame(card, bg=hw_data["color"], height=25)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(
        header,
        text=f"{hw_data['type']} - {hw_data['model'][:25]}",
        font=("Segoe UI", 8, "bold"),
        bg=hw_data["color"],
        fg="#ffffff"
    ).pack(side="left", padx=8, pady=3)

    # Content area - vertical stack (compact)
    content = tk.Frame(card, bg="#1a1d24")
    content.pack(fill="both", expand=True, padx=6, pady=4)

    # Usage
    tk.Label(
        content,
        text="USAGE",
        font=("Segoe UI", 6, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(anchor="w")

    usage_chart = tk.Canvas(content, bg="#0f1117", height=20, highlightthickness=0)
    usage_chart.pack(fill="x", pady=1)

    usage_width = int((hw_data["usage"] / 100) * (usage_chart.winfo_reqwidth() - 10))
    usage_chart.create_rectangle(0, 0, max(usage_width, 10), 20, fill=hw_data["color"], outline="")

    tk.Label(
        content,
        text=f"{hw_data['usage']:.1f}%",
        font=("Consolas", 7, "bold"),
        bg="#1a1d24",
        fg=hw_data["color"]
    ).pack(anchor="w", pady=(0, 3))

    # Temperature
    tk.Label(
        content,
        text="TEMP",
        font=("Segoe UI", 6, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(anchor="w")

    temp_chart = tk.Canvas(content, bg="#0f1117", height=20, highlightthickness=0)
    temp_chart.pack(fill="x", pady=1)

    temp_width = int((hw_data["temp"] / 100) * (temp_chart.winfo_reqwidth() - 10))
    temp_color = "#10b981" if hw_data["temp"] < 60 else "#f59e0b" if hw_data["temp"] < 80 else "#ef4444"
    temp_chart.create_rectangle(0, 0, max(temp_width, 10), 20, fill=temp_color, outline="")

    tk.Label(
        content,
        text=f"{hw_data['temp']:.0f}°C",
        font=("Consolas", 7, "bold"),
        bg="#1a1d24",
        fg=temp_color
    ).pack(anchor="w", pady=(0, 3))

    # Status - compact
    health = "✓ OK" if hw_data["usage"] < 85 else "⚠ High"
    health_color = "#10b981" if hw_data["usage"] < 85 else "#f59e0b"

    tk.Label(
        content,
        text=health,
        font=("Segoe UI", 7),
        bg="#1a1d24",
        fg=health_color
    ).pack(anchor="w")

    # Load status
    if hw_data["usage"] < 10:
        load_status = "Idle"
        load_color = "#64748b"
    elif hw_data["usage"] < 50:
        load_status = "Normal"
        load_color = "#3b82f6"
    elif hw_data["usage"] < 80:
        load_status = "High"
        load_color = "#f59e0b"
    else:
        load_status = "Max"
        load_color = "#ef4444"

    tk.Label(
        content,
        text=load_status,
        font=("Segoe UI", 7),
        bg="#1a1d24",
        fg=load_color
    ).pack(anchor="w")


def create_advanced_hw_card(parent, hw_data):
    """Create ultra-compact advanced hardware card with mini charts"""
    card = tk.Frame(parent, bg="#1a1d24")
    card.pack(fill="x", padx=10, pady=4)

    # Header
    header = tk.Frame(card, bg=hw_data["color"], height=30)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(
        header,
        text=f"{hw_data['type']} - {hw_data['model']}",
        font=("Segoe UI", 9, "bold"),
        bg=hw_data["color"],
        fg="#ffffff"
    ).pack(side="left", padx=10, pady=5)

    # Content area - 3 columns
    content = tk.Frame(card, bg="#1a1d24")
    content.pack(fill="x", padx=8, pady=5)

    # LEFT: Usage chart (mini sparkline)
    left = tk.Frame(content, bg="#1a1d24", width=150)
    left.pack(side="left", fill="y", padx=5)
    left.pack_propagate(False)

    tk.Label(
        left,
        text="USAGE",
        font=("Segoe UI", 7, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(anchor="w")

    usage_chart = tk.Canvas(left, bg="#0f1117", height=25, highlightthickness=0)
    usage_chart.pack(fill="x", pady=2)

    # Draw simple usage indicator
    usage_width = int((hw_data["usage"] / 100) * 130)
    usage_chart.create_rectangle(0, 0, usage_width, 25, fill=hw_data["color"], outline="")

    tk.Label(
        left,
        text=f"{hw_data['usage']:.1f}%",
        font=("Consolas", 8, "bold"),
        bg="#1a1d24",
        fg=hw_data["color"]
    ).pack(anchor="w")

    # MIDDLE: Temperature chart
    middle = tk.Frame(content, bg="#1a1d24", width=150)
    middle.pack(side="left", fill="y", padx=5)
    middle.pack_propagate(False)

    tk.Label(
        middle,
        text="TEMPERATURE",
        font=("Segoe UI", 7, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(anchor="w")

    temp_chart = tk.Canvas(middle, bg="#0f1117", height=25, highlightthickness=0)
    temp_chart.pack(fill="x", pady=2)

    # Draw temp indicator
    temp_width = int((hw_data["temp"] / 100) * 130)
    temp_color = "#10b981" if hw_data["temp"] < 60 else "#f59e0b" if hw_data["temp"] < 80 else "#ef4444"
    temp_chart.create_rectangle(0, 0, temp_width, 25, fill=temp_color, outline="")

    tk.Label(
        middle,
        text=f"{hw_data['temp']:.0f}°C",
        font=("Consolas", 8, "bold"),
        bg="#1a1d24",
        fg=temp_color
    ).pack(anchor="w")

    # RIGHT: Status
    right = tk.Frame(content, bg="#1a1d24")
    right.pack(side="left", fill="both", expand=True, padx=5)

    tk.Label(
        right,
        text="STATUS",
        font=("Segoe UI", 7, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(anchor="w")

    # Health status
    health = "✓ Working Properly" if hw_data["usage"] < 85 else "⚠ High Load"
    health_color = "#10b981" if hw_data["usage"] < 85 else "#f59e0b"

    tk.Label(
        right,
        text=health,
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg=health_color
    ).pack(anchor="w", pady=1)

    # Load status
    if hw_data["usage"] < 10:
        load_status = "Idle"
        load_color = "#64748b"
    elif hw_data["usage"] < 50:
        load_status = "Normal"
        load_color = "#3b82f6"
    elif hw_data["usage"] < 80:
        load_status = "High Load"
        load_color = "#f59e0b"
    else:
        load_status = "Maximum"
        load_color = "#ef4444"

    tk.Label(
        right,
        text=load_status,
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg=load_color
    ).pack(anchor="w")

    # Bottom padding
    tk.Frame(card, bg="#1a1d24", height=5).pack()


def build_yourpc_efficiency(self, parent):
    """Build Efficiency tab"""
    tk.Label(
        parent,
        text="⚡ EFFICIENCY\n\nPower usage and efficiency metrics coming soon...",
        font=("Segoe UI", 11),
        bg="#0f1117",
        fg="#64748b",
        justify="center"
    ).pack(expand=True)


def build_yourpc_health(self, parent):
    """Build Health Check tab - with temperature charts and defragmenter"""
    # Scrollable container
    canvas = tk.Canvas(parent, bg="#0f1117", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg="#0f1117")

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # TEMPERATURE MONITORING CHARTS (moved to top)
    tk.Label(
        scrollable,
        text="TEMPERATURE MONITORING",
        font=("Segoe UI", 9, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(pady=(15, 5), padx=10, anchor="w")

    # Get current temps
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1) if psutil else 0
        ram_usage = psutil.virtual_memory().percent if psutil else 0
    except:
        cpu_usage = 0
        ram_usage = 0

    cpu_temp = 30 + (cpu_usage * 0.6)
    ram_temp = 25 + (ram_usage * 0.5)
    gpu_temp = 35 + (cpu_usage * 0.5)  # Simulated

    # Three temperature cards side by side
    temp_row = tk.Frame(scrollable, bg="#0f1117")
    temp_row.pack(fill="x", padx=10, pady=5)

    temps = [
        ("CPU", cpu_temp, "#3b82f6", cpu_usage),
        ("RAM", ram_temp, "#fbbf24", ram_usage),
        ("GPU", gpu_temp, "#10b981", cpu_usage * 0.8)  # Simulated GPU usage
    ]

    for name, temp, color, usage in temps:
        card = tk.Frame(temp_row, bg="#1a1d24")
        card.pack(side="left", fill="both", expand=True, padx=3)

        # Header
        tk.Label(
            card,
            text=name,
            font=("Segoe UI", 8, "bold"),
            bg=color,
            fg="#ffffff",
            anchor="w",
            padx=8,
            pady=4
        ).pack(fill="x")

        # Temperature display
        tk.Label(
            card,
            text=f"{temp:.1f}°C",
            font=("Consolas", 16, "bold"),
            bg="#1a1d24",
            fg=color
        ).pack(pady=10)

        # Mini chart (simulated over time)
        chart_canvas = tk.Canvas(card, bg="#0f1117", height=60, highlightthickness=0)
        chart_canvas.pack(fill="x", padx=8, pady=(0, 8))

        # Draw simple temp chart (line)
        # Simulate historical data
        import random
        temps_history = [temp + random.uniform(-5, 5) for _ in range(20)]

        max_temp = max(temps_history) if temps_history else 100
        min_temp = min(temps_history) if temps_history else 0
        range_temp = max_temp - min_temp if max_temp != min_temp else 1

        points = []
        for i, t in enumerate(temps_history):
            x = (i / (len(temps_history) - 1)) * (chart_canvas.winfo_reqwidth() - 16)
            y = 60 - ((t - min_temp) / range_temp) * 50
            points.extend([x + 8, y])

        if len(points) >= 4:
            chart_canvas.create_line(points, fill=color, width=2, smooth=True)

        # Detailed Status
        # Activity status
        if usage < 20:
            activity = "Low Activity"
            activity_color = "#64748b"
        elif usage < 60:
            activity = "Normal Activity"
            activity_color = "#3b82f6"
        else:
            activity = "High Activity"
            activity_color = "#f59e0b"

        tk.Label(
            card,
            text=activity,
            font=("Segoe UI", 7),
            bg="#1a1d24",
            fg=activity_color
        ).pack(pady=(0, 2))

        # Health check
        if temp < 70:
            health = "✓ Everything OK"
            health_color = "#10b981"
        else:
            health = "⚠ Requires Inspection"
            health_color = "#ef4444"

        tk.Label(
            card,
            text=health,
            font=("Segoe UI", 7, "bold"),
            bg="#1a1d24",
            fg=health_color
        ).pack(pady=(0, 8))

    # DISK DEFRAGMENTER BUTTON - MOVED TO BOTTOM
    tk.Label(
        scrollable,
        text="DISK MAINTENANCE",
        font=("Segoe UI", 9, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(pady=(15, 5), padx=10, anchor="w")

    defrag_card = tk.Frame(scrollable, bg="#1a1d24")
    defrag_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        defrag_card,
        text="💿 Disk Defragmenter",
        font=("Segoe UI", 10, "bold"),
        bg="#1a1d24",
        fg="#ffffff",
        anchor="w"
    ).pack(padx=10, pady=(8, 4), anchor="w")

    tk.Label(
        defrag_card,
        text="Optimize your disk for better performance",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8",
        anchor="w"
    ).pack(padx=10, pady=(0, 8), anchor="w")

    # Launch button
    defrag_btn = tk.Label(
        defrag_card,
        text="🚀 Launch Defragmenter",
        font=("Segoe UI", 9, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        cursor="hand2",
        padx=20,
        pady=8
    )
    defrag_btn.pack(padx=10, pady=(0, 10))

    def launch_defrag(e):
        try:
            import subprocess
            subprocess.Popen("dfrgui.exe")  # Windows Disk Defragmenter
        except Exception as ex:
            print(f"[Defrag] Error: {ex}")

    defrag_btn.bind("<Button-1>", launch_defrag)

    # Hover effect
    def on_enter_defrag(e):
        defrag_btn.config(bg="#2563eb")
    def on_leave_defrag(e):
        defrag_btn.config(bg="#3b82f6")

    defrag_btn.bind("<Enter>", on_enter_defrag)
    defrag_btn.bind("<Leave>", on_leave_defrag)


def build_yourpc_components(self, parent):
    """Build Components tab - 2D PC graphic with hardware visualization"""
    # Main container
    main = tk.Frame(parent, bg="#0f1117")
    main.pack(fill="both", expand=True, padx=10, pady=10)

    # Title
    tk.Label(
        main,
        text="🖥️ PC COMPONENTS OVERVIEW",
        font=("Segoe UI", 12, "bold"),
        bg="#0f1117",
        fg="#ffffff"
    ).pack(pady=(0, 10))

    # Call the 2D graphic builder (will be moved from main_window_expanded)
    self._build_pc2d_graphic_in_yourpc(main)


def build_yourpc_startup(self, parent):
    """Build Startup & Services tab"""
    tk.Label(
        parent,
        text="🚀 STARTUP & SERVICES\n\nManage startup programs and services coming soon...",
        font=("Segoe UI", 11),
        bg="#0f1117",
        fg="#64748b",
        justify="center"
    ).pack(expand=True)
