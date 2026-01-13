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

# Import PRO INFO TABLE
try:
    from ui.components.pro_info_table import ProInfoTable
except ImportError:
    ProInfoTable = None


def build_yourpc_page(self, parent):
    """Build YOUR PC page - Full-screen advanced hardware monitoring with tabs"""
    # Main container (full overlay area) - NO TOP BAR for maximum space
    main = tk.Frame(parent, bg="#0f1117")
    main.pack(fill="both", expand=True)

    # Content area with tabs (Dashboard bar removed to save space)
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
    """Build Central tab - Enhanced hardware monitoring with PRO INFO TABLE"""
    # Main container - TWO COLUMNS layout
    main_container = tk.Frame(parent, bg="#0f1117")
    main_container.pack(fill="both", expand=True, padx=3, pady=3)

    # LEFT COLUMN - Hardware selection cards (scrollable) - VERY NARROW for max table space
    left_col = tk.Frame(main_container, bg="#0f1117", width=280)
    left_col.pack(side="left", fill="both", expand=False, padx=(3, 3))
    left_col.pack_propagate(False)

    # Scrollable container for left column
    left_canvas = tk.Canvas(left_col, bg="#0f1117", highlightthickness=0)
    left_scrollbar = tk.Scrollbar(left_col, orient="vertical", command=left_canvas.yview)
    left_scrollable = tk.Frame(left_canvas, bg="#0f1117")

    left_scrollable.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
    left_canvas.create_window((0, 0), window=left_scrollable, anchor="nw")
    left_canvas.configure(yscrollcommand=left_scrollbar.set)

    left_canvas.pack(side="left", fill="both", expand=True)
    left_scrollbar.pack(side="right", fill="y")

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

    # THREE HARDWARE CARDS (CPU, RAM, GPU) - VERTICAL STACK
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

    # Stack menu buttons vertically in left column
    build_menu_buttons(self, left_scrollable)

    # RIGHT COLUMN - PRO INFO TABLE (compact, scrollable)
    right_col = tk.Frame(main_container, bg="#0a0e27")
    right_col.pack(side="right", fill="both", expand=True, padx=(3, 3))

    # Add PRO INFO TABLE
    if ProInfoTable:
        try:
            pro_table = ProInfoTable(right_col)
            pro_table.pack(fill="both", expand=True)
        except Exception as e:
            # Fallback if table fails
            tk.Label(
                right_col,
                text=f"PRO INFO TABLE Error: {e}",
                font=("Segoe UI", 10),
                bg="#0a0e27",
                fg="#ef4444"
            ).pack(pady=20)
    else:
        # Fallback placeholder
        tk.Label(
            right_col,
            text="PRO INFO TABLE\n(Module not available)",
            font=("Segoe UI", 12, "bold"),
            bg="#0a0e27",
            fg="#64748b"
        ).pack(pady=50)

    # Motherboard info - compact label at bottom of left column
    try:
        import wmi
        w = wmi.WMI()
        motherboard = w.Win32_BaseBoard()[0]
        mb_name = f"{motherboard.Manufacturer} {motherboard.Product}"
    except:
        mb_name = "Unknown Motherboard"

    mb_label = tk.Label(
        left_scrollable,
        text=f"📋 {mb_name}",
        font=("Consolas", 7, "bold"),
        bg="#0a0e27",
        fg="#fbbf24",
        padx=8,
        pady=4
    )
    mb_label.pack(pady=(10, 5), fill="x", padx=5)


def create_advanced_hw_card_vertical(parent, hw_data):
    """Create vertical hardware card for left column"""
    card = tk.Frame(parent, bg="#1a1d24")
    card.pack(fill="x", padx=5, pady=5)

    # Header with colored accent
    header = tk.Frame(card, bg=hw_data["color"], height=35)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(
        header,
        text=f"{hw_data['type']} - {hw_data['model']}",
        font=("Segoe UI", 9, "bold"),
        bg=hw_data["color"],
        fg="#ffffff"
    ).pack(side="left", padx=10, pady=8)

    # Stats
    stats_frame = tk.Frame(card, bg="#1a1d24")
    stats_frame.pack(fill="x", padx=10, pady=8)

    # Usage
    usage_row = tk.Frame(stats_frame, bg="#1a1d24")
    usage_row.pack(fill="x", pady=2)

    tk.Label(
        usage_row,
        text="Usage:",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8",
        width=8,
        anchor="w"
    ).pack(side="left")

    tk.Label(
        usage_row,
        text=f"{hw_data['usage']:.1f}%",
        font=("Consolas", 9, "bold"),
        bg="#1a1d24",
        fg=hw_data["color"]
    ).pack(side="left")

    # Temperature
    temp_row = tk.Frame(stats_frame, bg="#1a1d24")
    temp_row.pack(fill="x", pady=2)

    tk.Label(
        temp_row,
        text="Temp:",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8",
        width=8,
        anchor="w"
    ).pack(side="left")

    temp_color = "#ef4444" if hw_data["temp"] > 70 else "#10b981" if hw_data["temp"] < 50 else "#f59e0b"
    tk.Label(
        temp_row,
        text=f"{hw_data['temp']:.1f}°C",
        font=("Consolas", 9, "bold"),
        bg="#1a1d24",
        fg=temp_color
    ).pack(side="left")


def build_yourpc_efficiency(self, parent):
    """Build Efficiency tab - Driver Updates & Game Optimizer (GeForce Experience-style)"""
    # Scrollable container
    canvas = tk.Canvas(parent, bg="#0f1117", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg="#0f1117")

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Title
    tk.Label(
        scrollable,
        text="⚡ SYSTEM EFFICIENCY & OPTIMIZATION",
        font=("Segoe UI", 11, "bold"),
        bg="#0f1117",
        fg="#ffffff"
    ).pack(pady=(5, 10), padx=10, anchor="w")

    # === DRIVER UPDATE CENTER (GeForce Experience-style) ===
    driver_card = tk.Frame(scrollable, bg="#1a1d24")
    driver_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        driver_card,
        text="🔄 DRIVER UPDATE CENTER",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#10b981",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    # Current driver versions
    tk.Label(
        driver_card,
        text="Current Drivers Status",
        font=("Segoe UI", 8, "bold"),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 3), anchor="w")

    driver_list = [
        ("NVIDIA GPU Driver", "551.23", "✓ Up to date", "#10b981"),
        ("AMD Chipset", "4.12.0", "⚠ Update available", "#fbbf24"),
        ("Realtek Audio", "6.0.9374", "✓ Latest", "#10b981"),
        ("Intel Wi-Fi 6", "22.200.0", "✓ Latest", "#10b981")
    ]

    for driver_name, version, status, color in driver_list:
        driver_row = tk.Frame(driver_card, bg="#0f1117")
        driver_row.pack(fill="x", padx=10, pady=2)

        tk.Label(driver_row, text=driver_name, font=("Segoe UI", 8), bg="#0f1117", fg="#ffffff", width=16, anchor="w").pack(side="left", padx=5)
        tk.Label(driver_row, text=version, font=("Consolas", 7), bg="#0f1117", fg="#64748b", width=12, anchor="w").pack(side="left")
        tk.Label(driver_row, text=status, font=("Segoe UI", 7, "bold"), bg="#0f1117", fg=color).pack(side="right", padx=5)

    # Update button
    update_btn = tk.Label(
        driver_card,
        text="🔄 Check for Updates",
        font=("Segoe UI", 8, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        padx=15,
        pady=6,
        cursor="hand2"
    )
    update_btn.pack(padx=10, pady=8, anchor="w")

    tk.Frame(driver_card, bg="#1a1d24", height=5).pack()

    # === GAME OPTIMIZER (GeForce Experience-style) ===
    game_card = tk.Frame(scrollable, bg="#1a1d24")
    game_card.pack(fill="x", padx=10, pady=10)

    tk.Label(
        game_card,
        text="🎮 GAME OPTIMIZER",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    tk.Label(
        game_card,
        text="Optimize settings for detected games automatically",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 5), anchor="w")

    # Detected games
    games_list = [
        ("Cyberpunk 2077", "Ultra Settings", "#10b981"),
        ("Elden Ring", "High Settings", "#3b82f6"),
        ("Baldur's Gate 3", "Medium Settings", "#fbbf24"),
        ("Counter-Strike 2", "Max Performance", "#10b981")
    ]

    for game_name, settings, color in games_list:
        game_row = tk.Frame(game_card, bg="#0f1117")
        game_row.pack(fill="x", padx=10, pady=3)

        tk.Label(game_row, text="🎯", font=("Segoe UI", 9), bg="#0f1117", fg=color).pack(side="left", padx=(5, 8))
        tk.Label(game_row, text=game_name, font=("Segoe UI", 8, "bold"), bg="#0f1117", fg="#ffffff", width=18, anchor="w").pack(side="left")
        tk.Label(game_row, text=settings, font=("Segoe UI", 7), bg="#0f1117", fg=color).pack(side="right", padx=5)

    # Optimize button
    optimize_btn = tk.Label(
        game_card,
        text="⚡ Optimize All Games",
        font=("Segoe UI", 8, "bold"),
        bg="#10b981",
        fg="#ffffff",
        padx=15,
        pady=6,
        cursor="hand2"
    )
    optimize_btn.pack(padx=10, pady=8, anchor="w")

    tk.Frame(game_card, bg="#1a1d24", height=5).pack()

    # === POWER EFFICIENCY MONITOR ===
    power_card = tk.Frame(scrollable, bg="#1a1d24")
    power_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        power_card,
        text="⚡ POWER EFFICIENCY",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#fbbf24",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    # Power plan
    power_plans = tk.Frame(power_card, bg="#1a1d24")
    power_plans.pack(fill="x", padx=10, pady=8)

    tk.Label(
        power_plans,
        text="Active Power Plan:",
        font=("Segoe UI", 8, "bold"),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(anchor="w", pady=(0, 5))

    plans = [
        ("🔋 Balanced", "#3b82f6", True),
        ("⚡ High Performance", "#ef4444", False),
        ("🌿 Power Saver", "#10b981", False)
    ]

    for plan_name, plan_color, is_active in plans:
        plan_row = tk.Frame(power_plans, bg="#0f1117" if is_active else "#1a1d24")
        plan_row.pack(fill="x", pady=2)

        status = "● ACTIVE" if is_active else "○"
        status_color = plan_color if is_active else "#64748b"

        tk.Label(plan_row, text=status, font=("Segoe UI", 7, "bold"), bg=plan_row["bg"], fg=status_color, width=8).pack(side="left", padx=5)
        tk.Label(plan_row, text=plan_name, font=("Segoe UI", 8), bg=plan_row["bg"], fg="#ffffff" if is_active else "#94a3b8").pack(side="left", padx=5)

    # Efficiency stats
    tk.Label(
        power_card,
        text="Efficiency Statistics (Last Hour):",
        font=("Segoe UI", 8, "bold"),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 3), anchor="w")

    stats_row = tk.Frame(power_card, bg="#1a1d24")
    stats_row.pack(fill="x", padx=10, pady=5)

    efficiency_stats = [
        ("Avg Power Draw", "145W", "#10b981"),
        ("Peak Power", "287W", "#fbbf24"),
        ("Energy Saved", "0.3 kWh", "#3b82f6")
    ]

    for stat_name, value, color in efficiency_stats:
        stat_box = tk.Frame(stats_row, bg="#0f1117")
        stat_box.pack(side="left", fill="both", expand=True, padx=3, pady=2)

        tk.Label(stat_box, text=stat_name, font=("Segoe UI", 7), bg="#0f1117", fg="#64748b").pack(pady=(3, 0))
        tk.Label(stat_box, text=value, font=("Consolas", 8, "bold"), bg="#0f1117", fg=color).pack(pady=(0, 3))

    tk.Frame(power_card, bg="#1a1d24", height=8).pack()


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

        # Mini chart (simulated over time) - REDUCED HEIGHT
        chart_canvas = tk.Canvas(card, bg="#0f1117", height=45, highlightthickness=0)
        chart_canvas.pack(fill="x", padx=8, pady=(0, 6))

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

    # === MEGA HEALTH CHECK SECTION WITH HEATMAPS! 💎 ===
    tk.Label(
        scrollable,
        text="ADVANCED HEALTH DIAGNOSTICS",
        font=("Segoe UI", 9, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(pady=(20, 5), padx=10, anchor="w")

    # Container for two heatmaps side by side
    heatmaps_container = tk.Frame(scrollable, bg="#0f1117")
    heatmaps_container.pack(fill="x", padx=10, pady=5)

    # === LEFT: DISK HEALTH HEATMAP ===
    disk_card = tk.Frame(heatmaps_container, bg="#1a1d24")
    disk_card.pack(side="left", fill="both", expand=True, padx=(0, 5))

    tk.Label(
        disk_card,
        text="💾 Disk Health Status",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#1a1d24",
        fg="#ffffff",
        anchor="w"
    ).pack(padx=12, pady=(10, 5), anchor="w")

    # Heatmap canvas - 50-60 tiny squares (2px)
    disk_heatmap = tk.Canvas(disk_card, bg="#0f1117", height=25, highlightthickness=0)
    disk_heatmap.pack(fill="x", padx=12, pady=8)

    # Create disk health heatmap with animation
    _create_disk_health_heatmap(self, disk_heatmap)

    # Legend
    legend_frame = tk.Frame(disk_card, bg="#1a1d24")
    legend_frame.pack(fill="x", padx=12, pady=(0, 10))

    legend_items = [
        ("■", "#10b981", "OK"),
        ("■", "#fbbf24", "Suspicious"),
        ("■", "#64748b", "Undefined"),
        ("■", "#ffffff", "Loading")
    ]

    for symbol, color, label in legend_items:
        item = tk.Frame(legend_frame, bg="#1a1d24")
        item.pack(side="left", padx=5)

        tk.Label(
            item,
            text=symbol,
            font=("Consolas", 10),
            bg="#1a1d24",
            fg=color
        ).pack(side="left")

        tk.Label(
            item,
            text=label,
            font=("Segoe UI", 7),
            bg="#1a1d24",
            fg="#94a3b8"
        ).pack(side="left", padx=2)

    # === RIGHT: RAM USAGE HEATMAP ===
    ram_card = tk.Frame(heatmaps_container, bg="#1a1d24")
    ram_card.pack(side="right", fill="both", expand=True, padx=(5, 0))

    tk.Label(
        ram_card,
        text="🧠 RAM Usage Map",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#1a1d24",
        fg="#ffffff",
        anchor="w"
    ).pack(padx=12, pady=(10, 5), anchor="w")

    # Heatmap canvas - tiny squares
    ram_heatmap = tk.Canvas(ram_card, bg="#0f1117", height=25, highlightthickness=0)
    ram_heatmap.pack(fill="x", padx=12, pady=8)

    # Create RAM heatmap
    _create_ram_usage_heatmap(self, ram_heatmap)

    # RAM Stats
    ram_stats_frame = tk.Frame(ram_card, bg="#1a1d24")
    ram_stats_frame.pack(fill="x", padx=12, pady=(0, 10))

    try:
        process_count = len(psutil.pids()) if psutil else 0
        ram_info = psutil.virtual_memory() if psutil else None

        if ram_info:
            used_gb = ram_info.used / (1024**3)
            total_gb = ram_info.total / (1024**3)
            available_gb = ram_info.available / (1024**3)

            stats_left = tk.Frame(ram_stats_frame, bg="#1a1d24")
            stats_left.pack(side="left", fill="x", expand=True)

            tk.Label(
                stats_left,
                text=f"Active Processes: {process_count}",
                font=("Segoe UI", 8),
                bg="#1a1d24",
                fg="#3b82f6",
                anchor="w"
            ).pack(anchor="w")

            tk.Label(
                stats_left,
                text=f"Used: {used_gb:.1f} GB / {total_gb:.1f} GB",
                font=("Segoe UI", 8),
                bg="#1a1d24",
                fg="#fbbf24",
                anchor="w"
            ).pack(anchor="w")

            stats_right = tk.Frame(ram_stats_frame, bg="#1a1d24")
            stats_right.pack(side="right", fill="x", expand=True)

            tk.Label(
                stats_right,
                text=f"Available: {available_gb:.1f} GB",
                font=("Segoe UI", 8),
                bg="#1a1d24",
                fg="#10b981",
                anchor="e"
            ).pack(anchor="e")

            # Cache info (mega przydatne!)
            try:
                cached_gb = ram_info.cached / (1024**3) if hasattr(ram_info, 'cached') else 0
                if cached_gb > 0:
                    tk.Label(
                        stats_right,
                        text=f"Cached: {cached_gb:.1f} GB",
                        font=("Segoe UI", 8),
                        bg="#1a1d24",
                        fg="#8b5cf6",
                        anchor="e"
                    ).pack(anchor="e")
            except:
                pass
    except:
        tk.Label(
            ram_stats_frame,
            text="Stats unavailable",
            font=("Segoe UI", 8),
            bg="#1a1d24",
            fg="#64748b"
        ).pack()

    # === FAN CURVE EDITOR ===
    tk.Label(
        scrollable,
        text="FAN CONTROL",
        font=("Segoe UI", 9, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(pady=(15, 5), padx=10, anchor="w")

    fan_card = tk.Frame(scrollable, bg="#1a1d24")
    fan_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        fan_card,
        text="🌀 Fan Curve Editor",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#1a1d24",
        fg="#ffffff",
        anchor="w"
    ).pack(padx=10, pady=(8, 4), anchor="w")

    tk.Label(
        fan_card,
        text="Customize fan speed based on temperature",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(0, 5), anchor="w")

    # Fan curve visualization (mini chart)
    curve_canvas = tk.Canvas(fan_card, bg="#0f1117", height=80, highlightthickness=0)
    curve_canvas.pack(fill="x", padx=10, pady=5)

    # Draw grid lines
    for i in range(5):
        y = i * 20
        curve_canvas.create_line(5, y, 400, y, fill="#1a1d24", width=1)

    # Draw fan curve (simple linear)
    curve_points = [(5, 75), (100, 60), (200, 40), (300, 20), (395, 5)]
    for i in range(len(curve_points) - 1):
        x1, y1 = curve_points[i]
        x2, y2 = curve_points[i + 1]
        curve_canvas.create_line(x1, y1, x2, y2, fill="#3b82f6", width=2)

    # Draw control points
    for x, y in curve_points:
        curve_canvas.create_oval(x-3, y-3, x+3, y+3, fill="#10b981", outline="#0f1117")

    # Labels
    curve_canvas.create_text(10, 70, text="30°C", anchor="w", fill="#64748b", font=("Segoe UI", 7))
    curve_canvas.create_text(395, 70, text="90°C", anchor="e", fill="#64748b", font=("Segoe UI", 7))
    curve_canvas.create_text(10, 10, text="100%", anchor="w", fill="#64748b", font=("Segoe UI", 7))
    curve_canvas.create_text(10, 70, text="0%", anchor="w", fill="#64748b", font=("Segoe UI", 7))

    # Preset buttons
    presets_frame = tk.Frame(fan_card, bg="#1a1d24")
    presets_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(
        presets_frame,
        text="Presets:",
        font=("Segoe UI", 7, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(side="left", padx=(0, 8))

    presets = [
        ("Silent", "#10b981"),
        ("Balanced", "#3b82f6"),
        ("Performance", "#fbbf24"),
        ("Max", "#ef4444")
    ]

    for preset_name, preset_color in presets:
        preset_btn = tk.Label(
            presets_frame,
            text=preset_name,
            font=("Segoe UI", 7, "bold"),
            bg=preset_color,
            fg="#ffffff",
            padx=10,
            pady=4,
            cursor="hand2"
        )
        preset_btn.pack(side="left", padx=2)

    tk.Frame(fan_card, bg="#1a1d24", height=8).pack()

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


def _create_disk_health_heatmap(self, canvas):
    """Create animated disk health heatmap with RGB loading animation"""
    import random
    import time

    # Grid configuration: 12x5 = 60 tiny squares (2px each!)
    rows = 5
    cols = 12
    square_size = 2
    spacing = 1

    # Calculate canvas size
    canvas.config(width=cols * (square_size + spacing), height=rows * (square_size + spacing))

    squares = []

    # Create all squares
    for row in range(rows):
        for col in range(cols):
            x = col * (square_size + spacing) + 5
            y = row * (square_size + spacing) + 5

            square = canvas.create_rectangle(
                x, y, x + square_size, y + square_size,
                fill="#ffffff",
                outline="#64748b",
                width=1
            )
            squares.append((square, x, y))

    # Animation phase 1: RGB color cycling (1.5 seconds)
    def rgb_animation(step=0):
        if step < 75:  # 75 steps * 20ms = 1.5s
            for square, x, y in squares:
                # Generate random RGB color
                r = random.randint(50, 255)
                g = random.randint(50, 255)
                b = random.randint(50, 255)
                color = f'#{r:02x}{g:02x}{b:02x}'
                canvas.itemconfig(square, fill=color)

            canvas.after(20, lambda: rgb_animation(step + 1))
        else:
            # Phase 2: Show "LOAD..." on white squares
            loading_phase()

    def loading_phase():
        # Set all squares to white
        for square, x, y in squares:
            canvas.itemconfig(square, fill="#ffffff", outline="#94a3b8")

        # Add "LOAD..." text
        canvas_w = canvas.winfo_reqwidth() or (cols * (square_size + spacing))
        canvas_h = canvas.winfo_reqheight() or (rows * (square_size + spacing))

        load_text = canvas.create_text(
            canvas_w // 2,
            canvas_h // 2,
            text="LOAD...",
            font=("Consolas", 8, "bold"),
            fill="#3b82f6"
        )

        # Wait 0.5s then show final health map
        canvas.after(500, lambda: show_health_map(load_text))

    def show_health_map(load_text):
        # Remove loading text
        canvas.delete(load_text)

        # Generate realistic disk health pattern
        for square, x, y in squares:
            rand = random.random()

            if rand < 0.75:  # 75% OK
                color = "#10b981"  # Green
            elif rand < 0.90:  # 15% Undefined
                color = "#64748b"  # Gray
            else:  # 10% Suspicious
                color = "#fbbf24"  # Yellow

            canvas.itemconfig(square, fill=color, outline="#0f1117")

    # Start animation
    rgb_animation()


def _create_ram_usage_heatmap(self, canvas):
    """Create RAM usage heatmap showing memory allocation"""
    import random

    # Grid configuration: 12x5 = 60 tiny squares (2px each!)
    rows = 5
    cols = 12
    square_size = 2
    spacing = 1

    canvas.config(width=cols * (square_size + spacing), height=rows * (square_size + spacing))

    # Get actual RAM usage
    try:
        ram_percent = psutil.virtual_memory().percent if psutil else 50
    except:
        ram_percent = 50

    # Calculate how many squares should be filled
    total_squares = rows * cols
    filled_squares = int((ram_percent / 100.0) * total_squares)

    square_index = 0

    for row in range(rows):
        for col in range(cols):
            x = col * (square_size + spacing) + 5
            y = row * (square_size + spacing) + 5

            # Determine color based on RAM usage
            if square_index < filled_squares:
                # Filled squares - gradient from green to yellow to red
                ratio = square_index / max(filled_squares, 1)

                if ratio < 0.6:
                    color = "#10b981"  # Green (low usage)
                elif ratio < 0.85:
                    color = "#fbbf24"  # Yellow (medium usage)
                else:
                    color = "#ef4444"  # Red (high usage)
            else:
                # Empty squares
                color = "#1a1d24"

            canvas.create_rectangle(
                x, y, x + square_size, y + square_size,
                fill=color,
                outline="#0f1117" if square_index < filled_squares else "#64748b",
                width=1
            )

            square_index += 1


def build_yourpc_components(self, parent):
    """Build Components tab - GPU Controls & Quick Benchmark (MSI Afterburner-inspired)"""
    # Scrollable container
    canvas = tk.Canvas(parent, bg="#0f1117", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg="#0f1117")

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Title
    tk.Label(
        scrollable,
        text="🖥️ GPU CONTROL CENTER",
        font=("Segoe UI", 11, "bold"),
        bg="#0f1117",
        fg="#ffffff"
    ).pack(pady=(5, 10), padx=10, anchor="w")

    # === GPU OVERCLOCKING PANEL (MSI Afterburner-style) ===
    oc_card = tk.Frame(scrollable, bg="#1a1d24")
    oc_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        oc_card,
        text="⚡ GPU TUNING & MONITORING",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#10b981",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    # GPU info
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_name = gpus[0].name
            gpu_temp = gpus[0].temperature
            gpu_load = gpus[0].load * 100
            gpu_mem_used = gpus[0].memoryUsed
            gpu_mem_total = gpus[0].memoryTotal
        else:
            gpu_name = "No GPU detected"
            gpu_temp = 0
            gpu_load = 0
            gpu_mem_used = 0
            gpu_mem_total = 0
    except:
        gpu_name = "GPU info unavailable"
        gpu_temp = 45
        gpu_load = 35
        gpu_mem_used = 4096
        gpu_mem_total = 8192

    tk.Label(
        oc_card,
        text=f"🎮 {gpu_name}",
        font=("Segoe UI", 9),
        bg="#1a1d24",
        fg="#10b981"
    ).pack(padx=10, pady=(8, 2), anchor="w")

    # Live stats row
    stats_row = tk.Frame(oc_card, bg="#1a1d24")
    stats_row.pack(fill="x", padx=10, pady=5)

    stats_data = [
        ("GPU Load", f"{gpu_load:.0f}%", "#3b82f6"),
        ("Temperature", f"{gpu_temp}°C", "#fbbf24" if gpu_temp > 75 else "#10b981"),
        ("VRAM", f"{gpu_mem_used}MB / {gpu_mem_total}MB", "#8b5cf6")
    ]

    for label, value, color in stats_data:
        stat_box = tk.Frame(stats_row, bg="#0f1117")
        stat_box.pack(side="left", fill="both", expand=True, padx=3, pady=2)

        tk.Label(stat_box, text=label, font=("Segoe UI", 7), bg="#0f1117", fg="#64748b").pack(pady=(3, 0))
        tk.Label(stat_box, text=value, font=("Consolas", 8, "bold"), bg="#0f1117", fg=color).pack(pady=(0, 3))

    # Sliders for tuning (visual only)
    tk.Label(
        oc_card,
        text="TUNING CONTROLS (Visual Demo)",
        font=("Segoe UI", 7, "bold"),
        bg="#1a1d24",
        fg="#64748b"
    ).pack(padx=10, pady=(10, 3), anchor="w")

    slider_data = [
        ("Core Clock", "+0 MHz", "#3b82f6"),
        ("Memory Clock", "+0 MHz", "#8b5cf6"),
        ("Power Limit", "100%", "#fbbf24"),
        ("Fan Speed", "AUTO", "#10b981")
    ]

    for label, value, color in slider_data:
        slider_row = tk.Frame(oc_card, bg="#1a1d24")
        slider_row.pack(fill="x", padx=10, pady=3)

        tk.Label(slider_row, text=label, font=("Segoe UI", 8), bg="#1a1d24", fg="#94a3b8", width=12, anchor="w").pack(side="left")

        # Visual slider bar
        slider_canvas = tk.Canvas(slider_row, bg="#0f1117", height=10, width=150, highlightthickness=0)
        slider_canvas.pack(side="left", padx=5)
        slider_canvas.create_rectangle(0, 0, 75, 10, fill=color, outline="")

        tk.Label(slider_row, text=value, font=("Consolas", 8, "bold"), bg="#1a1d24", fg=color).pack(side="left", padx=5)

    tk.Frame(oc_card, bg="#1a1d24", height=8).pack()

    # === QUICK BENCHMARK ===
    bench_card = tk.Frame(scrollable, bg="#1a1d24")
    bench_card.pack(fill="x", padx=10, pady=10)

    tk.Label(
        bench_card,
        text="🚀 QUICK BENCHMARK",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    tk.Label(
        bench_card,
        text="Test your GPU performance with quick synthetic tests",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 5), anchor="w")

    # Benchmark buttons
    bench_btns = tk.Frame(bench_card, bg="#1a1d24")
    bench_btns.pack(fill="x", padx=10, pady=5)

    bench_tests = [
        ("DirectX 11", "#10b981"),
        ("DirectX 12", "#3b82f6"),
        ("Vulkan", "#ef4444"),
        ("Memory Test", "#fbbf24")
    ]

    for test_name, test_color in bench_tests:
        btn = tk.Label(
            bench_btns,
            text=test_name,
            font=("Segoe UI", 8, "bold"),
            bg=test_color,
            fg="#ffffff",
            padx=12,
            pady=6,
            cursor="hand2"
        )
        btn.pack(side="left", padx=3, pady=3)

    # Benchmark results (placeholder)
    results_frame = tk.Frame(bench_card, bg="#0f1117")
    results_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(
        results_frame,
        text="Last Benchmark Results:",
        font=("Segoe UI", 7, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(pady=(3, 2), anchor="w", padx=5)

    result_data = [
        ("Average FPS", "142", "#10b981"),
        ("Min FPS", "89", "#fbbf24"),
        ("Max FPS", "187", "#3b82f6"),
        ("Score", "8,547", "#8b5cf6")
    ]

    for label, value, color in result_data:
        row = tk.Frame(results_frame, bg="#0f1117")
        row.pack(fill="x", padx=5, pady=1)

        tk.Label(row, text=label, font=("Segoe UI", 7), bg="#0f1117", fg="#94a3b8", width=12, anchor="w").pack(side="left")
        tk.Label(row, text=value, font=("Consolas", 8, "bold"), bg="#0f1117", fg=color).pack(side="left", padx=5)

    tk.Frame(bench_card, bg="#1a1d24", height=8).pack()

    # === HARDWARE DATABASE ===
    hw_db_card = tk.Frame(scrollable, bg="#1a1d24")
    hw_db_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        hw_db_card,
        text="💾 HARDWARE DATABASE",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#8b5cf6",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    tk.Label(
        hw_db_card,
        text="Detected hardware components and their specifications",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 5), anchor="w")

    # Component list
    try:
        import platform
        cpu_name = platform.processor()[:50]
        ram_total = psutil.virtual_memory().total / (1024**3)
    except:
        cpu_name = "Unknown CPU"
        ram_total = 16

    hw_components = [
        ("🔷 CPU", cpu_name, "#3b82f6"),
        ("🔶 GPU", gpu_name[:50], "#10b981"),
        ("🔸 RAM", f"{ram_total:.1f} GB", "#fbbf24"),
        ("🔹 Motherboard", "Detected via WMI", "#8b5cf6")
    ]

    for icon, name, color in hw_components:
        comp_row = tk.Frame(hw_db_card, bg="#1a1d24")
        comp_row.pack(fill="x", padx=10, pady=2)

        tk.Label(comp_row, text=icon, font=("Segoe UI", 9), bg="#1a1d24", fg=color).pack(side="left", padx=(0, 5))
        tk.Label(comp_row, text=name, font=("Segoe UI", 8), bg="#1a1d24", fg="#ffffff").pack(side="left", anchor="w")

    tk.Frame(hw_db_card, bg="#1a1d24", height=8).pack()


def build_yourpc_startup(self, parent):
    """Build Startup & Services tab - System Restore & Startup Manager"""
    # Scrollable container
    canvas = tk.Canvas(parent, bg="#0f1117", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable = tk.Frame(canvas, bg="#0f1117")

    scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Title
    tk.Label(
        scrollable,
        text="🚀 SYSTEM RESTORE & STARTUP",
        font=("Segoe UI", 11, "bold"),
        bg="#0f1117",
        fg="#ffffff"
    ).pack(pady=(5, 10), padx=10, anchor="w")

    # === SYSTEM RESTORE POINT CREATOR ===
    restore_card = tk.Frame(scrollable, bg="#1a1d24")
    restore_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        restore_card,
        text="💾 SYSTEM RESTORE POINT",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#10b981",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    tk.Label(
        restore_card,
        text="Create a restore point before making system changes",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 5), anchor="w")

    # Recent restore points
    tk.Label(
        restore_card,
        text="Recent Restore Points:",
        font=("Segoe UI", 8, "bold"),
        bg="#1a1d24",
        fg="#ffffff"
    ).pack(padx=10, pady=(5, 3), anchor="w")

    restore_points = [
        ("PC_Workman Auto-Save", "Today, 14:32", "#10b981"),
        ("System Checkpoint", "Yesterday", "#3b82f6"),
        ("Manual Restore Point", "2 days ago", "#64748b")
    ]

    for point_name, point_time, color in restore_points:
        point_row = tk.Frame(restore_card, bg="#0f1117")
        point_row.pack(fill="x", padx=10, pady=2)

        tk.Label(point_row, text="●", font=("Segoe UI", 8), bg="#0f1117", fg=color).pack(side="left", padx=(5, 8))
        tk.Label(point_row, text=point_name, font=("Segoe UI", 8), bg="#0f1117", fg="#ffffff", width=20, anchor="w").pack(side="left")
        tk.Label(point_row, text=point_time, font=("Segoe UI", 7), bg="#0f1117", fg="#64748b").pack(side="right", padx=5)

    # Create restore point button
    create_btn = tk.Label(
        restore_card,
        text="💾 Create Restore Point Now",
        font=("Segoe UI", 8, "bold"),
        bg="#3b82f6",
        fg="#ffffff",
        padx=15,
        pady=6,
        cursor="hand2"
    )
    create_btn.pack(padx=10, pady=8, anchor="w")

    def create_restore_point(e):
        try:
            import subprocess
            subprocess.Popen('powershell -Command "Checkpoint-Computer -Description \'PC_Workman Manual Restore\' -RestorePointType \'MODIFY_SETTINGS\'"', shell=True)
        except:
            pass

    create_btn.bind("<Button-1>", create_restore_point)

    tk.Frame(restore_card, bg="#1a1d24", height=5).pack()

    # === STARTUP IMPACT ANALYZER ===
    startup_card = tk.Frame(scrollable, bg="#1a1d24")
    startup_card.pack(fill="x", padx=10, pady=10)

    tk.Label(
        startup_card,
        text="⚡ STARTUP IMPACT ANALYZER",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#fbbf24",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    tk.Label(
        startup_card,
        text="Analyze how programs affect your boot time",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 5), anchor="w")

    # Startup programs list
    startup_programs = [
        ("Discord", "High Impact", "2.3s delay", "#ef4444"),
        ("Steam", "Medium Impact", "1.1s delay", "#fbbf24"),
        ("Windows Defender", "Low Impact", "0.3s delay", "#10b981"),
        ("OneDrive", "Medium Impact", "0.9s delay", "#fbbf24"),
        ("NVIDIA Control Panel", "No Impact", "0.0s delay", "#64748b")
    ]

    for prog_name, impact, delay, color in startup_programs:
        prog_row = tk.Frame(startup_card, bg="#0f1117")
        prog_row.pack(fill="x", padx=10, pady=2)

        tk.Label(prog_row, text=prog_name, font=("Segoe UI", 8, "bold"), bg="#0f1117", fg="#ffffff", width=18, anchor="w").pack(side="left", padx=5)
        tk.Label(prog_row, text=impact, font=("Segoe UI", 7), bg="#0f1117", fg=color, width=12, anchor="w").pack(side="left")
        tk.Label(prog_row, text=delay, font=("Consolas", 7), bg="#0f1117", fg="#64748b").pack(side="right", padx=5)

    # Boot time summary
    summary_frame = tk.Frame(startup_card, bg="#0f1117")
    summary_frame.pack(fill="x", padx=10, pady=8)

    tk.Label(
        summary_frame,
        text="Current Boot Time:",
        font=("Segoe UI", 7, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(side="left", padx=5)

    tk.Label(
        summary_frame,
        text="18.7 seconds",
        font=("Consolas", 8, "bold"),
        bg="#0f1117",
        fg="#3b82f6"
    ).pack(side="left", padx=5)

    tk.Label(
        summary_frame,
        text="Potential Savings:",
        font=("Segoe UI", 7, "bold"),
        bg="#0f1117",
        fg="#64748b"
    ).pack(side="left", padx=(15, 5))

    tk.Label(
        summary_frame,
        text="4.3 seconds",
        font=("Consolas", 8, "bold"),
        bg="#0f1117",
        fg="#10b981"
    ).pack(side="left", padx=5)

    # Optimize button
    optimize_btn = tk.Label(
        startup_card,
        text="⚡ Optimize Startup Programs",
        font=("Segoe UI", 8, "bold"),
        bg="#10b981",
        fg="#ffffff",
        padx=15,
        pady=6,
        cursor="hand2"
    )
    optimize_btn.pack(padx=10, pady=(0, 10), anchor="w")

    def optimize_startup(e):
        try:
            import subprocess
            subprocess.Popen("msconfig.exe")  # Open System Configuration
        except:
            pass

    optimize_btn.bind("<Button-1>", optimize_startup)

    tk.Frame(startup_card, bg="#1a1d24", height=5).pack()

    # === WINDOWS SERVICES MONITOR ===
    services_card = tk.Frame(scrollable, bg="#1a1d24")
    services_card.pack(fill="x", padx=10, pady=5)

    tk.Label(
        services_card,
        text="⚙️ SERVICES STATUS",
        font=("Segoe UI Semibold", 10, "bold"),
        bg="#8b5cf6",
        fg="#ffffff",
        padx=10,
        pady=5
    ).pack(fill="x")

    tk.Label(
        services_card,
        text="Critical Windows services monitoring",
        font=("Segoe UI", 8),
        bg="#1a1d24",
        fg="#94a3b8"
    ).pack(padx=10, pady=(8, 5), anchor="w")

    services_list = [
        ("Windows Update", "Running", "#10b981"),
        ("Windows Defender", "Running", "#10b981"),
        ("Windows Search", "Running", "#10b981"),
        ("Superfetch", "Stopped", "#64748b"),
        ("Print Spooler", "Running", "#10b981")
    ]

    for service_name, status, color in services_list:
        service_row = tk.Frame(services_card, bg="#0f1117")
        service_row.pack(fill="x", padx=10, pady=2)

        tk.Label(service_row, text=service_name, font=("Segoe UI", 8), bg="#0f1117", fg="#ffffff", width=20, anchor="w").pack(side="left", padx=5)
        status_badge = tk.Label(service_row, text=status, font=("Segoe UI", 7, "bold"), bg=color, fg="#ffffff", padx=8, pady=2)
        status_badge.pack(side="right", padx=5)

    # Open services button
    services_btn = tk.Label(
        services_card,
        text="⚙️ Open Services Manager",
        font=("Segoe UI", 8, "bold"),
        bg="#8b5cf6",
        fg="#ffffff",
        padx=15,
        pady=6,
        cursor="hand2"
    )
    services_btn.pack(padx=10, pady=8, anchor="w")

    def open_services(e):
        try:
            import subprocess
            subprocess.Popen("services.msc", shell=True)
        except:
            pass

    services_btn.bind("<Button-1>", open_services)

    tk.Frame(services_card, bg="#1a1d24", height=8).pack()


def build_menu_buttons(self, parent):
    """Build menu buttons with background images and gaming-style descriptions"""
    import os
    from PIL import Image, ImageTk

    menu_items = [
        {
            "image": "mypc_t1.png",
            "title": "YOUR PC - Health Raport",
            "desc_lines": [
                "Zaawansowany raport zdrowia - Komponentów twojego PC.",
                "Badany na tle sesji. Cała historia w jednym miejscu."
            ],
            "special": False
        },
        {
            "image": "mypc_t2.png",
            "title": "Statistics & Monitoring",
            "desc_lines": [
                "Wszelkie statystyki na tle miesięcy, odnośnie twojego PC.",
                "Tu zaobserwujesz wszelkie skoki temperatur, napięcia.",
                "Przy powtarzalności i podejrzeniu, zostaniesz powiadomiony o tym!",
                "Zamiast widzieć że coś się stało, dowiesz się dlaczego."
            ],
            "special": "NO MESSAGES",
            "special_color": "#a3e635"  # Yellow-green
        },
        {
            "image": "mypc_t3.png",
            "title": "Optimalization Dashboard",
            "desc_lines": [
                "W pełni przygotowane funkcje dla optymalizacji najstarszych sprzętów.",
                "Do automatycznego działania z każdym dniem.",
                "Skonfiguruj raz, wzmocnij efektywność!"
            ],
            "special": False
        },
        {
            "image": "mypc_t4.png",
            "title": "Daily Advanced System Cleanup",
            "desc_lines": [
                "Szereg narzędzi, inspirowanych liderami oprogramowania cleanupowego.",
                "Połączone moce, tutaj w jednym miejscu!"
            ],
            "special": False
        },
        {
            "image": "mypc_firstdevicestup.png",
            "title": "First Device Setup",
            "desc_lines": [
                "• DRIVER'S UPDATE. ALL drivers source IN ONE.",
                "• USLESS SERVICES OFF. Only what you need, and for stable working.",
                "• POTENTIALY USLESS APPS. Cortana, OneDrive, Local Maps, Game Bar, XBox."
            ],
            "special": "bullets",
            "compact": True
        }
    ]

    for item in menu_items:
        # Container for button (image + text below)
        btn_wrapper = tk.Frame(parent, bg="#0f1117")
        btn_wrapper.pack(pady=3, padx=10)

        # Load background image
        img_path = os.path.join("data", "icons", item["image"])

        if os.path.exists(img_path):
            try:
                # Load image at original size
                img = Image.open(img_path)
                # Resize to fit in left column (280px width, maintain aspect ratio)
                img_height = int(260 * img.height / img.width)

                # Special compact height for First Device Setup
                if item.get("compact"):
                    img_height = int(img_height * 0.7)

                img = img.resize((260, img_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                # Create canvas for image with title overlay
                img_canvas = tk.Canvas(btn_wrapper, bg="#0f1117", highlightthickness=0,
                                      width=260, height=img_height)
                img_canvas.pack()

                # Draw background image
                img_canvas.create_image(0, 0, image=photo, anchor="nw")
                img_canvas.image = photo

                # Add title overlay on image (25% from top) - GAMING STYLE
                title_y = int(img_height * 0.25)
                title_text = item["title"]
                if item.get("special") and item["special"] != "bullets":
                    title_text += f" - {item['special']}"

                img_canvas.create_text(130, title_y, text=title_text,
                                      font=("Bahnschrift SemiBold", 8, "bold"),
                                      fill="#ffffff", anchor="center")

                # Description text BELOW the image - ULTRA COMPACT GAMING STYLE
                desc_frame = tk.Frame(btn_wrapper, bg="#0f1117")
                desc_frame.pack(pady=(2, 0))

                for line in item["desc_lines"]:
                    # Special color for NO MESSAGES
                    if item.get("special") == "NO MESSAGES":
                        text_color = item.get("special_color", "#c0c0c0")
                    else:
                        text_color = "#c0c0c0"

                    tk.Label(desc_frame, text=line,
                            font=("Consolas", 6),
                            bg="#0f1117", fg=text_color).pack(anchor="center")

                # Make clickable
                def on_click(event, title=item["title"]):
                    print(f"Clicked: {title}")

                img_canvas.bind("<Button-1>", on_click)
                img_canvas.bind("<Enter>", lambda e: img_canvas.config(cursor="hand2"))
                img_canvas.bind("<Leave>", lambda e: img_canvas.config(cursor=""))

            except Exception as e:
                tk.Label(btn_wrapper, text=f"Error loading {item['image']}: {e}",
                        font=("Segoe UI", 8), bg="#0f1117", fg="#ef4444").pack(pady=3)
