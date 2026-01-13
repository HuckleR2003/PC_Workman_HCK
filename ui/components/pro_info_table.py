"""
PRO INFO TABLE - Ultra-Compact Hardware Monitoring
Inspired by HWMonitor but BETTER - trapezoid headers, color-coded sections
MOTHERBOARD → CPU → GPU with Voltage, Temperature, Power, Clocks
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import os
import socket

try:
    import psutil
except ImportError:
    psutil = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

try:
    from core.hardware_sensors import get_cpu_temp, get_gpu_temp, get_gpu_usage
except ImportError:
    get_cpu_temp = None
    get_gpu_temp = None
    get_gpu_usage = None


class TrapezoidHeader(tk.Canvas):
    """Trapezoid-shaped header (skewed edges like in design) - FLEXIBLE WIDTH"""

    def __init__(self, parent, text, bg_color, text_color="#ffffff", height=25):
        super().__init__(parent, bg="#0a0e27", height=height, highlightthickness=0)
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        # Bind to configure event to redraw when size changes
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        """Draw trapezoid shape"""
        self.delete("all")  # Clear previous drawing

        w = self.winfo_width()
        h = self.winfo_height()

        if w <= 1 or h <= 1:  # Not yet sized
            return

        # Trapezoid points (slanted left and right edges)
        skew = 8
        points = [
            skew, 0,           # Top left
            w - skew, 0,       # Top right
            w, h,              # Bottom right
            0, h               # Bottom left
        ]

        # Draw filled trapezoid
        self.create_polygon(points, fill=self.bg_color, outline="", smooth=False)

        # Draw border
        self.create_polygon(points, fill="", outline="#000000", width=2, smooth=False)

        # Draw text (centered) - ULTRA SMALL font
        self.create_text(w // 2, h // 2, text=self.text,
                        fill=self.text_color, font=("Segoe UI", 7, "bold"))


class ProInfoTable(tk.Frame):
    """
    Ultra-compact hardware monitoring table
    MOTHERBOARD / CPU / GPU sections with voltage, temp, power, clocks
    """

    def __init__(self, parent):
        super().__init__(parent, bg="#0a0e27")

        # Data storage (CURRENT / MIN / MAX)
        self.data = {
            "motherboard": {
                "voltage": {},
                "temperature": {},
                "fans": {}
            },
            "cpu": {
                "voltage": {},
                "temperature": {},
                "power": {},
                "clocks": {}
            },
            "gpu": {
                "voltage": {},
                "temperature": {},
                "power": {},
                "clocks": {}
            }
        }

        # Label references for updates
        self.labels = {}

        self._build_ui()
        self._start_update_thread()

    def _build_ui(self):
        """Build entire table structure with scrollbar"""
        # Scrollable canvas with black stylish scrollbar
        canvas = tk.Canvas(self, bg="#0a0e27", highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview,
                                bg="#000000", troughcolor="#0a0e27",
                                activebackground="#1a1d24", width=10)

        # Main container with minimal padding - ULTRA COMPACT
        main = tk.Frame(canvas, bg="#0a0e27")

        # Bind scrolling
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=main, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # USER HEADER (top banner)
        self._build_user_header(main)

        # MOTHERBOARD Section
        self._build_motherboard_section(main)

        # CPU Section
        self._build_cpu_section(main)

        # GPU Section
        self._build_gpu_section(main)

    def _build_user_header(self, parent):
        """Top banner with gradient image and overlaid text"""
        # Load header image
        header_path = os.path.join("data", "icons", "info_header.png")

        if os.path.exists(header_path) and Image:
            # Load and resize image to fit available width - ULTRA SMALL 24px
            img = Image.open(header_path)
            img = img.resize((800, 24), Image.Resampling.LANCZOS)

            # Create canvas for image + text overlay - FILL WIDTH, ULTRA COMPACT
            header_canvas = tk.Canvas(parent, bg="#0a0e27", height=24,
                                     highlightthickness=0)
            header_canvas.pack(fill="x", pady=(0, 1), expand=False)

            # Display image
            photo = ImageTk.PhotoImage(img)
            header_canvas.create_image(0, 0, image=photo, anchor="nw")
            header_canvas.image = photo  # Keep reference

            # Get computer name
            try:
                computer_name = socket.gethostname()
            except:
                computer_name = "DESKTOP"

            # Overlay text: "Hey - USER" on left (purple area) - ULTRA SMALL
            header_canvas.create_text(175, 12, text="Hey - USER",
                                    font=("Segoe UI", 9, "bold"),
                                    fill="#ffffff", anchor="center")

            # Overlay text: Computer name on right (blue area) - ULTRA SMALL
            header_canvas.create_text(525, 12, text=computer_name,
                                    font=("Segoe UI", 9, "bold"),
                                    fill="#ffffff", anchor="center")

        else:
            # Fallback if image not found - use simple colored frame
            header = tk.Frame(parent, bg="#9333ea", height=40)
            header.pack(fill="x", pady=(0, 5))
            header.pack_propagate(False)

            tk.Label(header, text="Hey - USER", font=("Segoe UI", 14, "bold"),
                    bg="#9333ea", fg="#ffffff").pack(side="left", padx=20)

            try:
                computer_name = socket.gethostname()
            except:
                computer_name = "DESKTOP"

            tk.Label(header, text=computer_name, font=("Segoe UI", 14, "bold"),
                    bg="#9333ea", fg="#ffffff").pack(side="right", padx=20)

    def _build_motherboard_section(self, parent):
        """MOTHERBOARD section with voltage, temperature, disk space, fans"""
        # Section header
        header = TrapezoidHeader(parent, "⚡ MOTHERBOARD", bg_color="#3b82f6",
                                height=18)
        header.pack(fill="x", pady=(1, 0))

        # Model badge (right aligned on header)
        model_label = tk.Label(parent, text="B750-M", font=("Segoe UI", 6, "bold"),
                              bg="#1e3a8a", fg="#ffffff", padx=8, pady=2)
        model_label.place(in_=header, relx=1.0, x=-5, rely=0.5, anchor="e")

        # Content frame
        content = tk.Frame(parent, bg="#1a1d24", highlightbackground="#3b82f6",
                          highlightthickness=2)
        content.pack(fill="x", pady=(0, 0))

        # Two main columns: Voltage | Temperature
        left_col = tk.Frame(content, bg="#1a1d24")
        left_col.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        right_col = tk.Frame(content, bg="#1a1d24")
        right_col.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        # === LEFT VOLTAGE COLUMN ===
        # Single column - no split
        # VOLTAGE: +12V, +5V, +3.3V, DDR4
        self._build_data_table(left_col, "⚡ VOLTAGE", [
            ("+12V", "mb_12v"),
            ("+5V", "mb_5v"),
            ("+3.3V", "mb_3v"),
            ("DDR4", "mb_ddr4"),
        ], show_ok_badge=True)

        # === RIGHT TEMPERATURE COLUMN ===
        # Single column - simplified
        # TEMPERATURE: CPU Core, CPU Socket, SYS
        self._build_data_table(right_col, "🌡️ TEMPERATURE", [
            ("CPU Core", "mb_cpu_core"),
            ("CPU Socket", "mb_cpu_socket"),
            ("SYS", "mb_sys"),
        ], show_ok_badge=True)

        # === DISK SPACE & FANS INFO (bottom strips) ===
        # Rectangle matching motherboard section width
        info_strip = tk.Frame(parent, bg="#1a1d24", highlightbackground="#3b82f6",
                             highlightthickness=2)
        info_strip.pack(fill="x", pady=(0, 3))

        # DISK SPACE & BODY FANS row (combined in one line)
        self._build_disk_and_fans_strip(info_strip)

    def _build_cpu_section(self, parent):
        """CPU section with voltage, temperature, power, clocks"""
        # Section header
        header = TrapezoidHeader(parent, "🔥 CPU", bg_color="#3b82f6",
                                height=18)
        header.pack(fill="x", pady=(1, 0))

        # Model badge
        model_label = tk.Label(parent, text="i5-11400F", font=("Segoe UI", 6, "bold"),
                              bg="#1e3a8a", fg="#ffffff", padx=8, pady=2)
        model_label.place(in_=header, relx=1.0, x=-5, rely=0.5, anchor="e")

        # Content frame
        content = tk.Frame(parent, bg="#1a1d24", highlightbackground="#3b82f6",
                          highlightthickness=2)
        content.pack(fill="x", pady=(0, 1))

        # Top row: Voltage | Gray Space | Temperature
        top_row = tk.Frame(content, bg="#1a1d24")
        top_row.pack(fill="x", padx=1, pady=1)

        # LEFT: VOLTAGE
        voltage_col = tk.Frame(top_row, bg="#1a1d24")
        voltage_col.pack(side="left", fill="both", expand=True)

        self._build_data_table(voltage_col, "⚡ VOLTAGE", [
            ("IA Offset", "cpu_ia_offset"),
            ("GT Offset", "cpu_gt_offset"),
            ("LLC/Ring Offset", "cpu_llc_offset"),
            ("System Agent Offset", "cpu_sa_offset"),
            ("V/O (Max)", "cpu_vo_max"),
        ], show_ok_badge=True)

        # MIDDLE: Gray separator space (like MOTHERBOARD)
        separator = tk.Frame(top_row, bg="#2d3142", width=8)
        separator.pack(side="left", fill="y", padx=3)

        # RIGHT: TEMPERATURE
        temp_col = tk.Frame(top_row, bg="#1a1d24")
        temp_col.pack(side="left", fill="both", expand=True)

        self._build_data_table(temp_col, "🌡️ TEMPERATURE", [
            ("Package", "cpu_package"),
            ("Core (Max)", "cpu_core_max"),
            ("Core #0", "cpu_core_0"),
            ("Core #1", "cpu_core_1"),
            ("Core #2", "cpu_core_2"),
            ("Core #3", "cpu_core_3"),
        ], show_ok_badge=True)

        # Bottom row: POWER and CLOCKS sections
        bottom_row = tk.Frame(content, bg="#1a1d24")
        bottom_row.pack(fill="x", padx=1, pady=(2, 1))

        # POWER section (left)
        power_col = tk.Frame(bottom_row, bg="#1a1d24")
        power_col.pack(side="left", fill="both", expand=True, padx=(0, 2))
        self._build_cpu_power_section(power_col)

        # CLOCKS section (right)
        clocks_col = tk.Frame(bottom_row, bg="#1a1d24")
        clocks_col.pack(side="left", fill="both", expand=True, padx=(2, 0))
        self._build_cpu_clocks_section(clocks_col)

    def _build_gpu_section(self, parent):
        """GPU section with voltage, temperature, power, clocks"""
        # Section header
        header = TrapezoidHeader(parent, "🎮 GPU", bg_color="#3b82f6",
                                height=18)
        header.pack(fill="x", pady=(1, 0))

        # Model badge
        model_label = tk.Label(parent, text="RTX 3050", font=("Segoe UI", 6, "bold"),
                              bg="#1e3a8a", fg="#ffffff", padx=8, pady=2)
        model_label.place(in_=header, relx=1.0, x=-5, rely=0.5, anchor="e")

        # Content frame
        content = tk.Frame(parent, bg="#1a1d24", highlightbackground="#3b82f6",
                          highlightthickness=2)
        content.pack(fill="x", pady=(0, 1))

        # Top row: VOLTAGE | TEMPERATURE
        top_row = tk.Frame(content, bg="#1a1d24")
        top_row.pack(fill="x", padx=1, pady=1)

        # LEFT: VOLTAGE
        voltage_col = tk.Frame(top_row, bg="#1a1d24")
        voltage_col.pack(side="left", fill="both", expand=True, padx=(0, 2))

        self._build_data_table(voltage_col, "⚡ VOLTAGE", [
            ("GPU", "gpu_voltage"),
            ("GPU Power", "gpu_power_voltage"),
        ], show_ok_badge=True)

        # RIGHT: TEMPERATURE
        temp_col = tk.Frame(top_row, bg="#1a1d24")
        temp_col.pack(side="left", fill="both", expand=True, padx=(2, 0))

        self._build_data_table(temp_col, "🌡️ TEMPERATURE", [
            ("GPU", "gpu_temp"),
            ("Hot Spot", "gpu_hot_spot"),
        ], show_ok_badge=True)

        # Bottom row: POWER | CLOCKS
        bottom_row = tk.Frame(content, bg="#1a1d24")
        bottom_row.pack(fill="x", padx=2, pady=(5, 2))

        # LEFT: POWER
        power_col = tk.Frame(bottom_row, bg="#1a1d24")
        power_col.pack(side="left", fill="both", expand=True, padx=(0, 2))
        self._build_gpu_power_section(power_col)

        # RIGHT: CLOCKS
        clocks_col = tk.Frame(bottom_row, bg="#1a1d24")
        clocks_col.pack(side="left", fill="both", expand=True, padx=(2, 0))
        self._build_gpu_clocks_section(clocks_col)

    def _build_data_table(self, parent, title, rows, show_ok_badge=False, compact=False, no_header=False):
        """Build compact data table with CURRENT/MIN/MAX columns"""
        # Title bar (skip if no_header)
        if not no_header and title:
            title_bar = tk.Frame(parent, bg="#fbbf24", height=12)
            title_bar.pack(fill="x")
            title_bar.pack_propagate(False)

            tk.Label(title_bar, text=title, font=("Segoe UI", 6, "bold"),
                    bg="#fbbf24", fg="#000000").pack(side="left", padx=5)

            if show_ok_badge:
                # OK badge always on the right side, 3x wider
                tk.Label(title_bar, text="OK", font=("Segoe UI", 6, "bold"),
                        bg="#10b981", fg="#ffffff", padx=12, pady=1).pack(side="right", padx=2)
        elif show_ok_badge:
            # Show OK badges even without header
            badge_bar = tk.Frame(parent, bg="#1a1d24", height=12)
            badge_bar.pack(fill="x")
            badge_bar.pack_propagate(False)

            # OK badge always on the right side, 3x wider
            tk.Label(badge_bar, text="OK", font=("Segoe UI", 6, "bold"),
                    bg="#10b981", fg="#ffffff", padx=12, pady=1).pack(side="right", padx=2)

        # Column headers (CURRENT / MIN / MAX) - only if not compact
        if not compact:
            headers_bar = tk.Frame(parent, bg="#000000")
            headers_bar.pack(fill="x")

            # Empty space for row labels
            tk.Label(headers_bar, text="", width=12, bg="#000000", fg="#ffffff",
                    font=("Segoe UI", 6)).pack(side="left")

            for col_name in ["CURRENT", "MIN", "MAX"]:
                tk.Label(headers_bar, text=col_name, width=8, bg="#000000", fg="#64748b",
                        font=("Segoe UI", 6, "bold")).pack(side="left", padx=1)

        # Data rows
        data_container = tk.Frame(parent, bg="#0f1117")
        data_container.pack(fill="x")

        for label, key in rows:
            self._create_data_row(data_container, label, key, compact=compact)

    def _create_data_row(self, parent, label, key, compact=False):
        """Create single data row with 3 values"""
        row = tk.Frame(parent, bg="#0f1117")
        row.pack(fill="x", pady=0)

        # Row label - SMALLER font
        tk.Label(row, text=label, font=("Segoe UI", 6), bg="#0f1117", fg="#94a3b8",
                anchor="w", width=12).pack(side="left", padx=1)

        # CURRENT / MIN / MAX values - SMALLER font
        for i, col_type in enumerate(["current", "min", "max"]):
            value_label = tk.Label(row, text="--", font=("Segoe UI", 6, "bold"),
                                  bg="#000000", fg="#ffffff", width=8)
            value_label.pack(side="left", padx=1)

            # Store reference
            self.labels[f"{key}_{col_type}"] = value_label

    def _build_disk_and_fans_strip(self, parent):
        """SPACE and BODY FANS in vertical layout (one under the other)"""
        # === DISK SPACE strip ===
        space_strip = tk.Frame(parent, bg="#000000", height=18)
        space_strip.pack(fill="x", pady=(1, 0))
        space_strip.pack_propagate(False)

        # SPACE section
        tk.Label(space_strip, text="SPACE", font=("Segoe UI", 7, "bold"),
                bg="#000000", fg="#fbbf24").pack(side="left", padx=10)

        tk.Label(space_strip, text="|", font=("Segoe UI", 7),
                bg="#000000", fg="#64748b").pack(side="left", padx=3)

        # Get disk usage
        if psutil:
            try:
                partitions = psutil.disk_partitions()
                for partition in partitions[:4]:  # Max 4 disks
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        percent = int(usage.percent)

                        # Color code based on usage
                        if percent > 90:
                            color = "#ef4444"  # Red
                        elif percent > 75:
                            color = "#f59e0b"  # Orange
                        else:
                            color = "#10b981"  # Green

                        drive_label = f"{partition.device[0]}:/ {percent}%"
                        tk.Label(space_strip, text=drive_label, font=("Segoe UI", 7, "bold"),
                                bg="#000000", fg=color).pack(side="left", padx=6)
                    except:
                        pass
            except:
                # Fallback
                tk.Label(space_strip, text="C:/ 65% | D:/ 90%", font=("Segoe UI", 7),
                        bg="#000000", fg="#ffffff").pack(side="left", padx=5)
        else:
            tk.Label(space_strip, text="C:/ 65% | D:/ 90%", font=("Segoe UI", 7),
                    bg="#000000", fg="#ffffff").pack(side="left", padx=5)

        # === BODY FANS strip (below SPACE) ===
        fans_strip = tk.Frame(parent, bg="#000000", height=18)
        fans_strip.pack(fill="x", pady=(1, 1))
        fans_strip.pack_propagate(False)

        # BODY FANS section
        tk.Label(fans_strip, text="BODY FANS", font=("Segoe UI", 7, "bold"),
                bg="#000000", fg="#fbbf24").pack(side="left", padx=10)

        tk.Label(fans_strip, text="|", font=("Segoe UI", 7),
                bg="#000000", fg="#64748b").pack(side="left", padx=3)

        # Fan entries (placeholder - will be updated with real data)
        fans = [
            ("CPU", "560 RPM"),
            ("BODYFAN", "990 RPM"),
        ]

        for fan_name, rpm in fans:
            tk.Label(fans_strip, text=f"{fan_name} {rpm}", font=("Segoe UI", 7),
                    bg="#000000", fg="#ffffff").pack(side="left", padx=8)

    def _build_cpu_power_section(self, parent):
        """CPU Power section - left column with Package and IA Cores"""
        # POWER header
        power_title = tk.Frame(parent, bg="#fbbf24", height=12)
        power_title.pack(fill="x")
        power_title.pack_propagate(False)

        tk.Label(power_title, text="⚙️ POWER", font=("Segoe UI", 6, "bold"),
                bg="#fbbf24", fg="#000000").pack(side="left", padx=5)

        # Column headers (CURRENT / MIN / MAX)
        headers_bar = tk.Frame(parent, bg="#000000")
        headers_bar.pack(fill="x")

        # Empty space for row labels
        tk.Label(headers_bar, text="", width=12, bg="#000000", fg="#ffffff",
                font=("Segoe UI", 6)).pack(side="left")

        for col_name in ["CURRENT", "MIN", "MAX"]:
            tk.Label(headers_bar, text=col_name, width=8, bg="#000000", fg="#64748b",
                    font=("Segoe UI", 6, "bold")).pack(side="left", padx=1)

        # Data rows
        data_container = tk.Frame(parent, bg="#0f1117")
        data_container.pack(fill="x")

        # Package row
        self._create_data_row(data_container, "Package", "cpu_power_package")

        # IA Cores row
        self._create_data_row(data_container, "IA Cores", "cpu_power_ia_cores")

    def _build_cpu_clocks_section(self, parent):
        """CPU Clocks section - right column with aligned core clocks"""
        # CLOCKS header
        clocks_title = tk.Frame(parent, bg="#fbbf24", height=12)
        clocks_title.pack(fill="x")
        clocks_title.pack_propagate(False)

        tk.Label(clocks_title, text="🎨 CLOCKS", font=("Segoe UI", 6, "bold"),
                bg="#fbbf24", fg="#000000").pack(side="left", padx=5)

        # Column headers (CURRENT / MIN / MAX)
        headers_bar = tk.Frame(parent, bg="#000000")
        headers_bar.pack(fill="x")

        # Empty space for row labels
        tk.Label(headers_bar, text="", width=12, bg="#000000", fg="#ffffff",
                font=("Segoe UI", 6)).pack(side="left")

        for col_name in ["CURRENT", "MIN", "MAX"]:
            tk.Label(headers_bar, text=col_name, width=8, bg="#000000", fg="#64748b",
                    font=("Segoe UI", 6, "bold")).pack(side="left", padx=1)

        # Data rows
        data_container = tk.Frame(parent, bg="#0f1117")
        data_container.pack(fill="x")

        # Core clocks
        self._create_data_row(data_container, "Core #0", "cpu_clock_0")
        self._create_data_row(data_container, "Core #1", "cpu_clock_1")
        self._create_data_row(data_container, "Core #2", "cpu_clock_2")
        self._create_data_row(data_container, "Core #3", "cpu_clock_3")

    def _build_gpu_power_section(self, parent):
        """GPU Power section"""
        # POWER header
        power_title = tk.Frame(parent, bg="#fbbf24", height=12)
        power_title.pack(fill="x")
        power_title.pack_propagate(False)

        tk.Label(power_title, text="⚙️ POWER", font=("Segoe UI", 6, "bold"),
                bg="#fbbf24", fg="#000000").pack(side="left", padx=5)

        # Column headers (CURRENT / MIN / MAX)
        headers_bar = tk.Frame(parent, bg="#000000")
        headers_bar.pack(fill="x")

        # Empty space for row labels
        tk.Label(headers_bar, text="", width=12, bg="#000000", fg="#ffffff",
                font=("Segoe UI", 6)).pack(side="left")

        for col_name in ["CURRENT", "MIN", "MAX"]:
            tk.Label(headers_bar, text=col_name, width=8, bg="#000000", fg="#64748b",
                    font=("Segoe UI", 6, "bold")).pack(side="left", padx=1)

        # Data rows
        data_container = tk.Frame(parent, bg="#0f1117")
        data_container.pack(fill="x")

        # Core Power Supply: 6.45 W, 5.61 W, 19.64 W
        self._create_data_row(data_container, "Core Power", "gpu_core_power")

        # PCIe+12V: 0.61 W, 0.20 W, 4.20 W
        self._create_data_row(data_container, "PCIe+12V", "gpu_pcie_12v")

        # 8-PIN: 12.02 W, 11.38 W, 29.06 W
        self._create_data_row(data_container, "8-PIN", "gpu_8pin")

    def _build_gpu_clocks_section(self, parent):
        """GPU Clocks section"""
        # CLOCKS header
        clocks_title = tk.Frame(parent, bg="#fbbf24", height=12)
        clocks_title.pack(fill="x")
        clocks_title.pack_propagate(False)

        tk.Label(clocks_title, text="🎨 CLOCKS", font=("Segoe UI", 6, "bold"),
                bg="#fbbf24", fg="#000000").pack(side="left", padx=5)

        # Column headers (CURRENT / MIN / MAX)
        headers_bar = tk.Frame(parent, bg="#000000")
        headers_bar.pack(fill="x")

        # Empty space for row labels
        tk.Label(headers_bar, text="", width=12, bg="#000000", fg="#ffffff",
                font=("Segoe UI", 6)).pack(side="left")

        for col_name in ["CURRENT", "MIN", "MAX"]:
            tk.Label(headers_bar, text=col_name, width=8, bg="#000000", fg="#64748b",
                    font=("Segoe UI", 6, "bold")).pack(side="left", padx=1)

        # Data rows
        data_container = tk.Frame(parent, bg="#0f1117")
        data_container.pack(fill="x")

        # Graphics: 210 MHz, 210 MHz, 1807 MHz
        self._create_data_row(data_container, "Graphics", "gpu_clock_graphics")

        # Memory: 405 MHz, 405 MHz, 7001 MHz
        self._create_data_row(data_container, "Memory", "gpu_clock_memory")

        # Video: 555 MHz, 555 MHz, 1605 MHz
        self._create_data_row(data_container, "Video", "gpu_clock_video")

    def _start_update_thread(self):
        """Start background thread to update values"""
        def update_loop():
            while True:
                try:
                    self._update_values()
                except Exception as e:
                    print(f"[ProInfoTable] Update error: {e}")

                time.sleep(2)  # Update every 2 seconds

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()

    def _update_values(self):
        """Update all values from sensors"""
        # Get CPU data
        if psutil:
            cpu_percent = psutil.cpu_percent()
            ram_percent = psutil.virtual_memory().percent

            # Update CPU temperature (example)
            if get_cpu_temp:
                try:
                    cpu_temp = get_cpu_temp()
                    self._update_label("cpu_package_current", f"{cpu_temp:.1f}°C")
                except:
                    pass

            # Update GPU temperature
            if get_gpu_temp:
                try:
                    gpu_temp = get_gpu_temp()
                    self._update_label("gpu_temp_current", f"{gpu_temp:.1f}°C")
                except:
                    pass

    def _update_label(self, key, value):
        """Update label value (thread-safe)"""
        if key in self.labels:
            try:
                self.labels[key].config(text=value)

                # Color coding for temperatures
                if "°C" in value:
                    temp = float(value.replace("°C", ""))
                    if temp > 80:
                        self.labels[key].config(fg="#ef4444")  # Red
                    elif temp > 60:
                        self.labels[key].config(fg="#f59e0b")  # Orange
                    else:
                        self.labels[key].config(fg="#10b981")  # Green
            except:
                pass


def create_pro_info_table(parent):
    """Factory function to create ProInfoTable"""
    return ProInfoTable(parent)


if __name__ == "__main__":
    # Test standalone
    root = tk.Tk()
    root.title("PRO INFO TABLE Test")
    root.geometry("750x900")
    root.configure(bg="#0a0e27")

    table = ProInfoTable(root)
    table.pack(fill="both", expand=True, padx=10, pady=10)

    root.mainloop()
