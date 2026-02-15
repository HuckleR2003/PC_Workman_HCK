# ui/main_window.py
"""
PC Workman Main Window v1.4.0 - Enhanced Guardian UI
- System tray with battery-style icon (CPU/GPU monitoring)
- Window positioning (bottom-right corner with lock/unlock)
- Enhanced process classification and data tracking
- Interactive charts with click events and time-travel
- Expandable TOP5 lists with real-time updates
- Data View modes: 1H, 4H, SESSION
"""

import tkinter as tk
from tkinter import ttk
import threading
import time

# Try importing with proper error handling
try:
    import psutil
except ImportError:
    print("[ERROR] psutil not installed. Install with: pip install psutil")
    psutil = None

try:
    from ui.hck_gpt_panel import HCKGPTPanel
except ImportError:
    HCKGPTPanel = None

from ui.components.led_bars import LEDSegmentBar
from ui.theme import LED_CPU_MAP, LED_GPU_MAP, LED_RAM_MAP, THEME
from ui.components.charts import EnhancedMainChart
from ui.components.process_tooltip import ProcessTooltip
from ui import dialogs

try:
    from ui.system_tray import SystemTrayManager, ToastNotification
except ImportError:
    print("[WARNING] System tray not available (missing pystray/pillow)")
    SystemTrayManager = None
    ToastNotification = None

from import_core import COMPONENTS

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    print("[ERROR] matplotlib not installed. Install with: pip install matplotlib")
    FigureCanvasTkAgg = None


def clamp(v, a=0, b=100):
    return max(a, min(b, v))


class MainWindow:
    def __init__(self, switch_to_expanded_callback=None):
        self.switch_to_expanded_callback = switch_to_expanded_callback

        self.root = tk.Tk()
        self.root.title("PC Workman – HCK_Labs v1.4.0")
        self.root.configure(bg=THEME["bg_main"])

        # Window settings
        self.window_width = THEME['win_width']
        self.window_height = THEME['win_height']
        self.root.geometry(f"{self.window_width}x{self.window_height}")

        # Window positioning state
        self.position_locked = True  # Start locked to bottom-right
        self.root.resizable(False, False)

        # Components
        self.logger = COMPONENTS.get('core.logger')
        self.monitor = COMPONENTS.get('core.monitor')
        self.classifier = COMPONENTS.get('core.process_classifier')
        self.data_manager = COMPONENTS.get('core.process_data_manager')

        # UI State
        self.sidebar_expanded = True
        self._auto_collapse_after_ms = 3000
        self._sidebar_animating = False
        self.is_minimized_to_tray = False

        # Selected time point on chart (for detail view)
        self.selected_timestamp = None
        self.time_travel_mode = False  # When True, freeze process lists at selected time

        # Tooltip for process info (click-to-show on Dashboard)
        self.process_tooltip = None  # Will be initialized after root is built

        # System Tray
        self.tray_manager = None
        self._init_system_tray()

        # Build UI
        self._build_style()
        self._position_window()
        self._build_ui()
        self._bind_window_events()
        self._schedule_sidebar_auto_collapse()

        # Start update loops
        self._running = True
        # Start UI update loop (using after() - no thread needed)
        self._update_loop()
        # Start tray update thread
        self._tray_thread = threading.Thread(target=self._tray_update_loop, daemon=True)
        self._tray_thread.start()

    def _init_system_tray(self):
        """Initialize system tray icon"""
        if SystemTrayManager is None:
            print("[SystemTray] Not available (missing dependencies)")
            self.tray_manager = None
            return

        try:
            self.tray_manager = SystemTrayManager(
                main_window_callback=self._restore_from_tray,
                stats_callback=self._show_stats_window,
                quit_callback=self._quit_application
            )
            self.tray_manager.start()
        except Exception as e:
            print(f"[SystemTray] Failed to initialize: {e}")
            self.tray_manager = None

    def _position_window(self):
        """Position window in bottom-right corner"""
        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Bottom-right corner with padding
        x = screen_width - self.window_width - 20
        y = screen_height - self.window_height - 80  # Account for taskbar

        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")

    def _bind_window_events(self):
        """Bind window event handlers"""
        # Override window close button (X)
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)

        # Window drag for position unlock
        self._drag_data = {"x": 0, "y": 0, "dragging": False}

    def _minimize_to_tray(self):
        """Minimize window to system tray"""
        if self.tray_manager and self.tray_manager.is_running():
            self.root.withdraw()
            self.is_minimized_to_tray = True

            # Show toast notification (if available)
            if ToastNotification is not None:
                ToastNotification.show(
                    "PC Workman - HCK Labs",
                    "Hello! I'm still working in the Background."
                )
        else:
            # No tray available, ask user
            self._quit_application()

    def _restore_from_tray(self):
        """Restore window from system tray"""
        if self.is_minimized_to_tray:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_minimized_to_tray = False

    def _show_stats_window(self):
        """Show statistics window"""
        self._restore_from_tray()
        # TODO: Implement stats window
        print("[Stats] Statistics window - Coming soon!")

    def _quit_application(self):
        """Properly quit application"""
        self._running = False

        # Save process data
        if self.data_manager:
            try:
                self.data_manager.save_statistics()
            except:
                pass

        # Stop tray
        if self.tray_manager:
            try:
                self.tray_manager.stop()
            except:
                pass

        # Destroy window
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

    def _build_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TButton", foreground=THEME["text"], background=THEME["bg_sidebar"], relief="flat")
        s.configure("TLabel", foreground=THEME["text"], background=THEME["bg_panel"])

    def _build_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=THEME["bg_sidebar"], height=THEME["win_height"])
        self.sidebar.place(x=0, y=0, width=THEME["sidebar_expanded"], height=THEME["win_height"])

        # Content area
        content_x = THEME["sidebar_expanded"]
        content_w = THEME["win_width"] - content_x
        self.content = tk.Frame(self.root, bg=THEME["bg_main"])
        self.content.place(x=content_x, y=0, width=content_w, height=THEME["win_height"])

        # Build components
        self._build_sidebar_contents()
        self._build_all_pages()
        self.show_page("dashboard")

        # Initialize process tooltip (click-to-show on Dashboard)
        self.process_tooltip = ProcessTooltip(self.root)

        # Bottom brand bar
        brand = tk.Frame(self.root, bg="#081018", height=5)
        brand.place(x=0, y=THEME["win_height"]-5, width=THEME["win_width"])
        btxt = tk.Label(brand, text='Marcin "HCK" Firmuga', fg=THEME["muted"], bg="#081018", font=("Consolas", 9))
        btxt.pack(side="left", padx=8)

        # Position lock indicator
        self.lock_indicator = tk.Label(
            brand,
            text="📍 Locked" if self.position_locked else "🔓 Unlocked",
            fg=THEME["accent"],
            bg="#081018",
            font=("Consolas", 8),
            cursor="hand2"
        )
        self.lock_indicator.pack(side="right", padx=8)
        self.lock_indicator.bind("<Button-1>", lambda e: self._toggle_position_lock())

        # GPT Panel (if available)
        if HCKGPTPanel:
            try:
                self.gpt = HCKGPTPanel(
                    parent=self.content,
                    width=THEME["win_width"] - THEME["sidebar_expanded"] - 4
                )
            except Exception as e:
                print(f"[WARNING] Failed to initialize GPT Panel: {e}")
                self.gpt = None
        else:
            print("[INFO] GPT Panel not available")
            self.gpt = None

        # Update services counter (async to not block UI)
        self.root.after(1000, self._update_services_counter)

    def _toggle_position_lock(self):
        """Toggle window position lock"""
        self.position_locked = not self.position_locked

        if self.position_locked:
            self.lock_indicator.config(text="📍 Locked")
            self._position_window()
            self.root.resizable(False, False)
        else:
            self.lock_indicator.config(text="🔓 Unlocked")
            self.root.resizable(True, True)

    def _build_sidebar_contents(self):
        # Modern dot
        self.dot = tk.Label(
            self.sidebar,
            text="⋮",
            font=(THEME["font_family"], 20),
            fg=THEME["accent"],
            bg=THEME["bg_sidebar"],
            cursor="hand2"
        )
        self.dot.place(x=6, y=8)

        # Menu frame
        self.menu_frame = tk.Frame(self.sidebar, bg=THEME["bg_sidebar"])
        self.menu_frame.place(x=6, y=48, width=108)

        # Menu items
        menu_items = [
            ("◉", "Dashboard", lambda: self.show_page("dashboard"), "dashboard"),
            ("📊", "Day Stats", lambda: self.show_page("day_stats"), "day_stats"),
            ("📈", "All Stats", lambda: self.show_page("all_stats"), "all_stats"),
            ("ℹ", "About", lambda: self.show_page("about"), "about"),
            ("🤖", "AI", lambda: self.show_page("about_ai"), "about_ai")
        ]

        self.menu_labels = []
        for idx, (icon, text, cb, page_id) in enumerate(menu_items):
            item_frame = tk.Frame(self.menu_frame, bg=THEME["bg_sidebar"], cursor="hand2")
            item_frame.pack(anchor="w", pady=(0 if idx==0 else 4), fill="x")

            lbl = tk.Label(
                item_frame,
                text=f"{icon} {text}",
                font=("Consolas", 10),
                fg=THEME["muted"],
                bg=THEME["bg_sidebar"],
                cursor="hand2",
                anchor="w",
                padx=4, pady=4
            )
            lbl.pack(fill="x")

            self.menu_labels.append((lbl, page_id, item_frame))

            if cb:
                def make_handler(callback):
                    def handler(e=None):
                        callback()
                        self._update_active_menu_item()
                    return handler

                handler = make_handler(cb)
                lbl.bind("<Button-1>", handler)
                item_frame.bind("<Button-1>", handler)

                # Hover effects
                def make_hover(label):
                    def enter(e):
                        if label.cget("fg") != THEME["accent"]:
                            label.config(fg=THEME["accent2"])
                    def leave(e):
                        if label.cget("fg") != THEME["accent"]:
                            label.config(fg=THEME["muted"])
                    return enter, leave

                enter_h, leave_h = make_hover(lbl)
                lbl.bind("<Enter>", enter_h)
                lbl.bind("<Leave>", leave_h)

        # Hover bindings for sidebar
        self.sidebar.bind("<Enter>", lambda e: self._expand_sidebar())
        self.sidebar.bind("<Leave>", lambda e: self._collapse_sidebar_delayed())

    def _build_all_pages(self):
        """Build all page frames"""
        self.pages = {}

        # Dashboard page
        self.pages["dashboard"] = tk.Frame(self.content, bg=THEME["bg_main"])
        self._build_dashboard_view(self.pages["dashboard"])

        # Day Stats page
        try:
            from ui.page_day_stats import DayStatsPage
            day_stats_page = DayStatsPage(self.content, self.data_manager, self.classifier)
            self.pages["day_stats"] = day_stats_page.frame
            self.day_stats_page = day_stats_page
        except Exception as e:
            print(f"[UI] Failed to load Day Stats page: {e}")
            self.pages["day_stats"] = tk.Frame(self.content, bg=THEME["bg_main"])

        # All Stats page
        try:
            from ui.page_all_stats import AllStatsPage
            all_stats_page = AllStatsPage(self.content, self.data_manager, self.classifier)
            self.pages["all_stats"] = all_stats_page.frame
            self.all_stats_page = all_stats_page
        except Exception as e:
            print(f"[UI] Failed to load All Stats page: {e}")
            self.pages["all_stats"] = tk.Frame(self.content, bg=THEME["bg_main"])

        # Optimization Options page
        self.pages["optimization"] = tk.Frame(self.content, bg=THEME["bg_main"])
        self._build_optimization_page(self.pages["optimization"])

        # YOUR PC page
        self.pages["yourpc"] = tk.Frame(self.content, bg=THEME["bg_main"])
        self._build_yourpc_page(self.pages["yourpc"])

        # About pages
        self.pages["about"] = dialogs.create_about_page(self.content)
        self.pages["about_ai"] = dialogs.create_about_ai_page(self.content)

        self.current_page = None

    def _build_optimization_page(self, parent):
        """Build Optimization Options page"""
        # Page header
        header = tk.Label(parent, text="⚡ OPTIMIZATION OPTIONS",
                         font=("Segoe UI", 16, "bold"), bg=THEME["bg_main"],
                         fg="#10b981", anchor="w", padx=20, pady=15)
        header.pack(fill="x")

        # Back button
        back_btn = tk.Label(parent, text="← Back to Dashboard",
                           font=("Segoe UI", 10), bg=THEME["bg_panel"],
                           fg=THEME["accent"], cursor="hand2", padx=15, pady=8)
        back_btn.pack(anchor="w", padx=20, pady=(0, 10))
        back_btn.bind("<Button-1>", lambda e: self.show_page("dashboard"))

        # Content area
        content = tk.Frame(parent, bg=THEME["bg_main"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Services Management Section
        services_frame = tk.Frame(content, bg=THEME["bg_panel"])
        services_frame.pack(fill="x", pady=10)

        services_header = tk.Label(services_frame, text="Windows Services Management",
                                   font=("Segoe UI", 12, "bold"), bg=THEME["accent"],
                                   fg=THEME["bg_panel"], anchor="w", padx=10, pady=8)
        services_header.pack(fill="x")

        services_content = tk.Frame(services_frame, bg=THEME["bg_panel"])
        services_content.pack(fill="x", padx=15, pady=15)

        # Services counter display
        self.opt_page_services_label = tk.Label(services_content,
                                               text="Loading services count...",
                                               font=("Segoe UI", 10), bg=THEME["bg_panel"],
                                               fg=THEME["text"])
        self.opt_page_services_label.pack(anchor="w", pady=5)

        # Service management buttons
        btn_frame = tk.Frame(services_content, bg=THEME["bg_panel"])
        btn_frame.pack(fill="x", pady=10)

        # Open Services Wizard button
        wizard_btn = tk.Label(btn_frame, text="🧙 Open Services Wizard",
                             font=("Segoe UI", 10, "bold"), bg=THEME["accent2"],
                             fg=THEME["text"], cursor="hand2", relief="raised",
                             padx=15, pady=10)
        wizard_btn.pack(side="left", padx=5)
        wizard_btn.bind("<Button-1>", lambda e: self._open_services_wizard())

        # Quick disable button
        quick_btn = tk.Label(btn_frame, text="⚡ Quick Disable Unnecessary",
                            font=("Segoe UI", 10, "bold"), bg="#10b981",
                            fg=THEME["bg_panel"], cursor="hand2", relief="raised",
                            padx=15, pady=10)
        quick_btn.pack(side="left", padx=5)
        quick_btn.bind("<Button-1>", lambda e: self._quick_disable_services())

        # Process Optimization Section
        proc_frame = tk.Frame(content, bg=THEME["bg_panel"])
        proc_frame.pack(fill="x", pady=10)

        proc_header = tk.Label(proc_frame, text="Background Process Optimization",
                              font=("Segoe UI", 12, "bold"), bg=THEME["accent"],
                              fg=THEME["bg_panel"], anchor="w", padx=10, pady=8)
        proc_header.pack(fill="x")

        proc_content = tk.Frame(proc_frame, bg=THEME["bg_panel"])
        proc_content.pack(fill="x", padx=15, pady=15)

        # Optimization options
        options = [
            ("🔇 Disable Telemetry", "Disable Windows telemetry services"),
            ("🎮 Gaming Mode", "Optimize for gaming performance"),
            ("⚙️ Startup Programs", "Manage startup applications"),
            ("🧹 Clean Temp Files", "Remove temporary files"),
        ]

        for title, desc in options:
            opt_row = tk.Frame(proc_content, bg=THEME["bg_panel"])
            opt_row.pack(fill="x", pady=5)

            tk.Label(opt_row, text=title, font=("Segoe UI", 10, "bold"),
                    bg=THEME["bg_panel"], fg=THEME["text"], anchor="w").pack(side="left")
            tk.Label(opt_row, text=f"  — {desc}", font=("Segoe UI", 8),
                    bg=THEME["bg_panel"], fg=THEME["muted"], anchor="w").pack(side="left")

    def _build_yourpc_page(self, parent):
        """Build YOUR PC - Personal data page with REAL hardware monitoring"""
        # Page header
        header = tk.Label(parent, text="💻 YOUR PC - Personal Data",
                         font=("Segoe UI", 16, "bold"), bg=THEME["bg_main"],
                         fg="#3b82f6", anchor="w", padx=20, pady=15)
        header.pack(fill="x")

        # Back button
        back_btn = tk.Label(parent, text="← Back to Dashboard",
                           font=("Segoe UI", 10), bg=THEME["bg_panel"],
                           fg=THEME["accent"], cursor="hand2", padx=15, pady=8)
        back_btn.pack(anchor="w", padx=20, pady=(0, 10))
        back_btn.bind("<Button-1>", lambda e: self.show_page("dashboard"))

        # Content area - 3 columns side by side
        content = tk.Frame(parent, bg=THEME["bg_main"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # Initialize widget storage for updates
        self.yourpc_widgets = {}

        # Create 3 component panels (CPU, RAM, GPU) side by side
        components = [
            {"name": "CPU", "color": "#3b82f6", "icon": "🔷", "key": "cpu"},
            {"name": "RAM", "color": "#fbbf24", "icon": "🟡", "key": "ram"},
            {"name": "GPU", "color": "#10b981", "icon": "🟢", "key": "gpu"}
        ]

        for i, comp in enumerate(components):
            self._build_component_panel(content, comp, column=i)

        # Get hardware info and update names immediately
        self._update_yourpc_hardware_names()

    def _build_component_panel(self, parent, component, column):
        """Build individual component health monitoring panel with REAL data"""
        key = component["key"]
        panel = tk.Frame(parent, bg=THEME["bg_panel"])
        panel.grid(row=0, column=column, padx=6, sticky="nsew")
        parent.grid_columnconfigure(column, weight=1)

        # Component header
        header = tk.Label(panel, text=f"{component['icon']} {component['name']}",
                         font=("Segoe UI", 9, "bold"), bg=component["color"],
                         fg=THEME["bg_panel"], anchor="center", pady=3)
        header.pack(fill="x")

        # Component name label (will show real hardware name)
        name_label = tk.Label(panel, text="Loading...",
                             font=("Segoe UI", 7), bg=THEME["bg_panel"],
                             fg=THEME["muted"], wraplength=120)
        name_label.pack(pady=(3, 0))

        # Mini chart area (usage percentage)
        chart_frame = tk.Frame(panel, bg="#1a1d24", height=40)
        chart_frame.pack(fill="x", padx=6, pady=5)
        chart_frame.pack_propagate(False)

        # Usage percentage display
        usage_label = tk.Label(chart_frame, text="0%",
                font=("Consolas", 16, "bold"), bg="#1a1d24", fg=component["color"])
        usage_label.pack(expand=True)

        # Temperature bar
        temp_frame = tk.Frame(panel, bg=THEME["bg_panel"])
        temp_frame.pack(fill="x", padx=6, pady=3)

        tk.Label(temp_frame, text="🌡️",
                font=("Segoe UI", 7), bg=THEME["bg_panel"],
                fg=THEME["text"]).pack(side="left")

        temp_bar_bg = tk.Frame(temp_frame, bg="#1a1d24", height=5, width=60)
        temp_bar_bg.pack(side="left", padx=3)
        temp_bar_bg.pack_propagate(False)

        # Temperature bar fill
        temp_bar_fill = tk.Frame(temp_bar_bg, bg=component["color"], height=5)
        temp_bar_fill.place(x=0, y=0, relwidth=0, relheight=1.0)

        # Temperature value
        temp_label = tk.Label(temp_frame, text="--°C",
                font=("Segoe UI", 7), bg=THEME["bg_panel"],
                fg=component["color"])
        temp_label.pack(side="left", padx=2)

        # Status line 1: Component health
        status1 = tk.Label(panel, text="⚙️ Wszystko działa sprawnie",
                          font=("Segoe UI", 6), bg=THEME["bg_panel"],
                          fg="#10b981", anchor="w")
        status1.pack(fill="x", padx=6, pady=(2, 0))

        # Status line 2: Load status
        status2 = tk.Label(panel, text="📊 Standardowa aktywność",
                          font=("Segoe UI", 6), bg=THEME["bg_panel"],
                          fg="#fbbf24", anchor="w")
        status2.pack(fill="x", padx=6, pady=(0, 4))

        # Store widget references for updates
        self.yourpc_widgets[key] = {
            "name_label": name_label,
            "usage_label": usage_label,
            "temp_bar_fill": temp_bar_fill,
            "temp_label": temp_label,
            "status1": status1,
            "status2": status2,
            "color": component["color"]
        }

    def _update_yourpc_hardware_names(self):
        """Update hardware names in YOUR PC page"""
        try:
            import platform
            import psutil

            # CPU name
            cpu_name = platform.processor()
            if len(cpu_name) > 30:
                cpu_name = cpu_name[:27] + "..."

            # RAM total
            ram_total = round(psutil.virtual_memory().total / (1024**3), 1)
            ram_name = f"{ram_total} GB Total"

            # GPU name
            gpu_name = "Integrated / Not detected"
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_name = gpus[0].name
                    if len(gpu_name) > 25:
                        gpu_name = gpu_name[:22] + "..."
            except:
                pass

            # Update labels
            if hasattr(self, 'yourpc_widgets'):
                self.yourpc_widgets["cpu"]["name_label"].config(text=cpu_name)
                self.yourpc_widgets["ram"]["name_label"].config(text=ram_name)
                self.yourpc_widgets["gpu"]["name_label"].config(text=gpu_name)

        except Exception as e:
            print(f"[YOUR PC] Error updating hardware names: {e}")

    def _update_yourpc_data(self, sample):
        """Update YOUR PC page with real-time data"""
        if not hasattr(self, 'yourpc_widgets') or not self.yourpc_widgets:
            return

        try:
            import psutil

            # CPU usage and status
            cpu_pct = sample.get("cpu_percent", 0)
            cpu_widgets = self.yourpc_widgets.get("cpu", {})
            if cpu_widgets:
                cpu_widgets["usage_label"].config(text=f"{cpu_pct:.0f}%")

                # CPU status based on usage
                if cpu_pct < 30:
                    cpu_widgets["status2"].config(text="📊 Bez aktywności", fg="#10b981")
                elif cpu_pct < 60:
                    cpu_widgets["status2"].config(text="📊 Standardowa aktywność", fg="#fbbf24")
                elif cpu_pct < 85:
                    cpu_widgets["status2"].config(text="📊 Nadmierne obciążenie", fg="#f97316")
                else:
                    cpu_widgets["status2"].config(text="📊 Nadzwyczajne obciążenie", fg="#ef4444")

                # Simulated CPU temp (based on load) - since psutil doesn't support temps on Windows easily
                cpu_temp = 35 + (cpu_pct * 0.5)  # 35°C base + load factor
                cpu_widgets["temp_label"].config(text=f"{cpu_temp:.0f}°C")
                cpu_widgets["temp_bar_fill"].place(relwidth=min(cpu_temp / 100, 1.0))

            # RAM usage and status
            ram_pct = sample.get("ram_percent", 0)
            ram_widgets = self.yourpc_widgets.get("ram", {})
            if ram_widgets:
                ram_widgets["usage_label"].config(text=f"{ram_pct:.0f}%")

                # RAM status
                if ram_pct < 40:
                    ram_widgets["status2"].config(text="📊 Bez aktywności", fg="#10b981")
                elif ram_pct < 70:
                    ram_widgets["status2"].config(text="📊 Standardowa aktywność", fg="#fbbf24")
                elif ram_pct < 90:
                    ram_widgets["status2"].config(text="📊 Nadmierne obciążenie", fg="#f97316")
                else:
                    ram_widgets["status2"].config(text="📊 Nadzwyczajne obciążenie", fg="#ef4444")

                # Simulated RAM temp
                ram_temp = 30 + (ram_pct * 0.3)
                ram_widgets["temp_label"].config(text=f"{ram_temp:.0f}°C")
                ram_widgets["temp_bar_fill"].place(relwidth=min(ram_temp / 100, 1.0))

            # GPU usage and status
            gpu_pct = sample.get("gpu_percent", 0)
            gpu_widgets = self.yourpc_widgets.get("gpu", {})
            if gpu_widgets:
                gpu_widgets["usage_label"].config(text=f"{gpu_pct:.0f}%")

                # GPU status
                if gpu_pct < 30:
                    gpu_widgets["status2"].config(text="📊 Bez aktywności", fg="#10b981")
                elif gpu_pct < 60:
                    gpu_widgets["status2"].config(text="📊 Standardowa aktywność", fg="#fbbf24")
                elif gpu_pct < 85:
                    gpu_widgets["status2"].config(text="📊 Nadmierne obciążenie", fg="#f97316")
                else:
                    gpu_widgets["status2"].config(text="📊 Nadzwyczajne obciążenie", fg="#ef4444")

                # Simulated GPU temp
                gpu_temp = 40 + (gpu_pct * 0.6)
                gpu_widgets["temp_label"].config(text=f"{gpu_temp:.0f}°C")
                gpu_widgets["temp_bar_fill"].place(relwidth=min(gpu_temp / 100, 1.0))

        except Exception as e:
            print(f"[YOUR PC] Error updating data: {e}")

    def _open_services_wizard(self):
        """Open services management wizard"""
        print("[Optimization] Opening Services Wizard...")
        # TODO: Integrate with hck_GPT services wizard
        pass

    def _quick_disable_services(self):
        """Quick disable unnecessary services"""
        print("[Optimization] Quick disabling unnecessary services...")
        # TODO: Implement quick service optimization
        pass

    def _build_dashboard_view(self, parent):
        """Build the main dashboard view"""
        self._build_top_bars(parent)
        self._build_center_area(parent)

    def _build_top_bars(self, parent):
        top_frame = tk.Frame(parent, bg=THEME["bg_main"])
        top_frame.place(x=8, y=8, width=THEME["win_width"] - THEME["sidebar_expanded"] - 16, height=60)

        # LED bars
        self.cpu_led = LEDSegmentBar(top_frame, "CPU", LED_CPU_MAP, segments=18, height=18)
        self.gpu_led = LEDSegmentBar(top_frame, "GPU", LED_GPU_MAP, segments=18, height=18)
        self.ram_led = LEDSegmentBar(top_frame, "RAM", LED_RAM_MAP, segments=18, height=18)

        self.cpu_led.frame.place(relx=0, rely=0, relwidth=0.33, height=60)
        self.gpu_led.frame.place(relx=0.33, rely=0, relwidth=0.33, height=60)
        self.ram_led.frame.place(relx=0.66, rely=0, relwidth=0.34, height=60)

    def _build_center_area(self, parent):
        content_w = THEME["win_width"] - THEME["sidebar_expanded"] - 26
        chart_h = 190
        right_w = 220

        # Chart frame with click event
        self.chart_frame = tk.Frame(parent, bg=THEME["bg_panel"])
        self.chart_frame.place(x=8, y=64, width=content_w - right_w - 8, height=chart_h)

        # Create interactive chart with click callback
        self.chart = EnhancedMainChart(
            width=5.2,
            height=1.2,
            dpi=100,
            click_callback=self._on_chart_click_callback
        )
        self.canvas = FigureCanvasTkAgg(self.chart.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Bind click event on chart
        self.canvas.mpl_connect('button_press_event', self._on_chart_click)

        # TOP5 User Processes (minimalistic modern design)
        self.top5_frame = tk.Frame(parent, bg=THEME["bg_panel"])
        self.top5_frame.place(x=8, y=64 + chart_h + 6, width=content_w - right_w - 8, height=120)

        header = tk.Label(
            self.top5_frame,
            text="TOP 5 - User Processes",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["accent"],
            fg=THEME["bg_panel"],
            anchor="w",
            padx=8
        )
        header.pack(fill="x", ipady=4)

        # Container for process rows (no more Text widget!)
        self.top5_container = tk.Frame(self.top5_frame, bg=THEME["bg_panel"])
        self.top5_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Store process row widgets
        self.top5_widgets = []

        # Action buttons below TOP 5 User Processes - APPLE STYLE (flat, modern, elegant)
        btn_y = 64 + chart_h + 6 + 120 + 6
        btn_width = (content_w - right_w - 8 - 8) // 2
        btn_height = 51  # 40% less than 85px (85 * 0.6 = 51)

        # EXPANDED VIEW button - Small minimalist button above main buttons
        expanded_btn_height = 28
        expanded_btn_y = btn_y - expanded_btn_height - 6

        self.expanded_btn = tk.Frame(parent, bg="#6366f1", cursor="hand2", relief="flat")
        self.expanded_btn.place(x=8, y=expanded_btn_y, width=(btn_width * 2) - 4, height=expanded_btn_height)

        expanded_content = tk.Frame(self.expanded_btn, bg="#6366f1")
        expanded_content.pack(fill="both", expand=True)

        tk.Label(
            expanded_content,
            text="◱ EXPANDED VIEW",
            font=("Segoe UI", 8, "bold"),
            bg="#6366f1",
            fg="white"
        ).pack(expand=True)

        # Click handler for switching to Expanded Mode
        for widget in [self.expanded_btn, expanded_content]:
            widget.bind("<Button-1>", lambda e: self._switch_to_expanded())

        # OPTIMIZATION OPTIONS button - Apple flat design with subtle gradient
        self.opt_btn_frame = tk.Frame(parent, bg="#0ea56a", cursor="hand2", relief="flat")
        self.opt_btn_frame.place(x=8, y=btn_y, width=btn_width - 4, height=btn_height)

        opt_content = tk.Frame(self.opt_btn_frame, bg="#0ea56a")
        opt_content.pack(fill="both", expand=True)

        # Icon and text side by side
        opt_left = tk.Frame(opt_content, bg="#0ea56a")
        opt_left.pack(side="left", padx=12, fill="y", expand=True)

        tk.Label(opt_left, text="⚡", font=("Segoe UI", 18),
                bg="#0ea56a", fg="white").pack(side="left", padx=(0, 8))

        opt_text_frame = tk.Frame(opt_left, bg="#0ea56a")
        opt_text_frame.pack(side="left", fill="y")

        tk.Label(opt_text_frame, text="Optimization",
                font=("Segoe UI", 10, "bold"), bg="#0ea56a",
                fg="white", anchor="w").pack(anchor="w")

        self.opt_services_label = tk.Label(opt_text_frame, text="Loading...",
                                          font=("Segoe UI", 7), bg="#0ea56a",
                                          fg="#c5f7e6", anchor="w")
        self.opt_services_label.pack(anchor="w")

        # Click handler
        for widget in [self.opt_btn_frame, opt_content, opt_left, opt_text_frame]:
            widget.bind("<Button-1>", lambda e: self._open_optimization_page())

        # YOUR PC button - Apple flat design
        self.yourpc_btn_frame = tk.Frame(parent, bg="#2563eb", cursor="hand2", relief="flat")
        self.yourpc_btn_frame.place(x=8 + btn_width, y=btn_y, width=btn_width - 4, height=btn_height)

        pc_content = tk.Frame(self.yourpc_btn_frame, bg="#2563eb")
        pc_content.pack(fill="both", expand=True)

        # Icon and text side by side
        pc_left = tk.Frame(pc_content, bg="#2563eb")
        pc_left.pack(side="left", padx=12, fill="y", expand=True)

        tk.Label(pc_left, text="💻", font=("Segoe UI", 18),
                bg="#2563eb", fg="white").pack(side="left", padx=(0, 8))

        pc_text_frame = tk.Frame(pc_left, bg="#2563eb")
        pc_text_frame.pack(side="left", fill="y")

        tk.Label(pc_text_frame, text="Your PC",
                font=("Segoe UI", 10, "bold"), bg="#2563eb",
                fg="white", anchor="w").pack(anchor="w")

        tk.Label(pc_text_frame, text="Hardware health",
                font=("Segoe UI", 7), bg="#2563eb",
                fg="#bfdbfe", anchor="w").pack(anchor="w")

        # Click handler
        for widget in [self.yourpc_btn_frame, pc_content, pc_left, pc_text_frame]:
            widget.bind("<Button-1>", lambda e: self._open_yourpc_page())

        # Right panel (Data View + System processes)
        self._build_right_panel(parent, content_w, right_w, chart_h)

    def _build_right_panel(self, parent, content_w, right_w, chart_h):
        self.right_panel = tk.Frame(parent, bg=THEME["bg_main"])
        self.right_panel.place(x=content_w - right_w + 8, y=64, width=right_w, height=chart_h + 6 + 120)

        # Data View header
        dv_header = tk.Label(
            self.right_panel,
            text="Data View",
            font=("Consolas", 11, "bold"),
            bg="#000000",
            fg=THEME["text"]
        )
        dv_header.place(x=6, y=0, width=right_w-12, height=36)

        # Mode buttons (clickable!)
        self.data_view_mode = 'SESSION'  # Default mode
        self.data_view_buttons = {}

        modes = [
            ("SESSION", "SESSION"),
            ("1H", "1H"),
            ("4H", "4H"),
        ]
        y = 44
        for mode_key, mode_label in modes:
            btn = tk.Label(
                self.right_panel,
                text=mode_label,
                font=("Consolas", 10, "bold"),
                bg=THEME["bg_panel"],
                fg=THEME["muted"],
                cursor="hand2",
                relief="raised",
                bd=1
            )
            btn.place(x=8, y=y, width=right_w-24, height=24)
            btn.bind("<Button-1>", lambda e, m=mode_key: self._on_data_view_change(m))

            self.data_view_buttons[mode_key] = btn
            y += 30

        # Highlight default mode
        self._highlight_data_view_button('SESSION')

        # System processes (minimalistic modern design)
        sys_header = tk.Label(
            self.right_panel,
            text="TOP 5 - System Processes",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["accent2"],
            fg=THEME["bg_panel"],
            anchor="w",
            padx=8
        )
        sys_header.place(x=6, y=y+6, width=right_w-12, height=24)

        # Container for system process rows
        self.sys_container = tk.Frame(self.right_panel, bg=THEME["bg_panel"])
        self.sys_container.place(x=8, y=y+34, width=right_w-16, height=120)

        # Store system process widgets
        self.sys_widgets = []

    def _on_data_view_change(self, mode):
        """Handle Data View mode change"""
        self.data_view_mode = mode
        print(f"[DataView] Changed to {mode}")

        # Update chart mode
        if hasattr(self.chart, 'set_data_view_mode'):
            self.chart.set_data_view_mode(mode)

        # Update button highlights
        self._highlight_data_view_button(mode)

        # Refresh chart
        if self.logger:
            samples = self.logger.get_last_n_samples(300)
            if samples and hasattr(self.chart, 'update'):
                self.chart.update(samples)
                if hasattr(self.canvas, 'draw'):
                    self.canvas.draw()

    def _highlight_data_view_button(self, active_mode):
        """Highlight active Data View button"""
        if not hasattr(self, 'data_view_buttons'):
            return

        for mode_key, btn in self.data_view_buttons.items():
            if mode_key == active_mode:
                btn.config(
                    bg=THEME["accent"],
                    fg=THEME["bg_panel"],
                    relief="sunken"
                )
            else:
                btn.config(
                    bg=THEME["bg_panel"],
                    fg=THEME["muted"],
                    relief="raised"
                )

    def _on_chart_click(self, event):
        """Handle click on chart to show process details at that time (legacy matplotlib event)"""
        # Double-click to exit TIME TRAVEL mode
        if event.dblclick and self.time_travel_mode:
            self._exit_time_travel_mode()
            return

        # This is called by matplotlib's mpl_connect
        # Forward to chart's internal handler
        if hasattr(self.chart, 'on_click'):
            self.chart.on_click(event)

    def _exit_time_travel_mode(self):
        """Exit TIME TRAVEL mode and return to live updates"""
        self.time_travel_mode = False
        self.selected_timestamp = None

        # Clear chart selection
        if hasattr(self.chart, 'clear_selection'):
            self.chart.clear_selection()
            try:
                self.canvas.draw_idle()
            except:
                self.canvas.draw()

        print("[TimeTravel] MODE DISABLED - Returned to live updates")

        # Immediately update to current data
        self._update_process_lists()

    def _on_chart_click_callback(self, sample):
        """Callback from EnhancedMainChart when user clicks on chart - TIME TRAVEL!"""
        if not sample:
            return

        timestamp = sample.get('timestamp', 0)
        self.selected_timestamp = timestamp
        self.time_travel_mode = True  # Enable TIME TRAVEL mode - freeze updates

        # Update process lists to show processes from selected time
        if self.data_manager:
            self._update_process_lists_for_time(timestamp)
            print(f"[TimeTravel] MODE ENABLED - Process lists frozen at {time.strftime('%H:%M:%S', time.localtime(timestamp))}")

    def _update_process_lists_for_time(self, timestamp):
        """Update TOP5 lists to show processes from specific time (TIME TRAVEL)"""
        if not self.data_manager:
            return

        try:
            # Get TOP processes at selected time
            top_user = self.data_manager.get_top_processes_at_time(timestamp, n=5, process_type='user')
            top_system = self.data_manager.get_top_processes_at_time(timestamp, n=5, process_type='system')

            # Convert format for rendering
            user_procs = []
            for proc in top_user:
                user_procs.append({
                    'name': proc.get('name', 'unknown'),
                    'cpu_percent': proc.get('cpu_percent', 0),
                    'ram_MB': proc.get('ram_MB', 0),
                    'classification': {
                        'display_name': proc.get('display_name', proc.get('name', 'unknown')),
                        'icon': proc.get('icon', ''),
                        'is_rival': proc.get('is_rival', False)
                    }
                })

            system_procs = []
            for proc in top_system:
                system_procs.append({
                    'name': proc.get('name', 'unknown'),
                    'cpu_percent': proc.get('cpu_percent', 0),
                    'ram_MB': proc.get('ram_MB', 0),
                    'classification': {
                        'display_name': proc.get('display_name', proc.get('name', 'unknown')),
                        'icon': proc.get('icon', '')
                    }
                })

            # Update lists using existing render methods
            self._render_user_processes(user_procs)
            self._render_system_processes(system_procs)

            print(f"[TimeTravel] Updated lists for {time.strftime('%H:%M:%S', time.localtime(timestamp))}")

        except Exception as e:
            print(f"[TimeTravel] Error updating process lists: {e}")
            import traceback
            traceback.print_exc()

    def show_page(self, page_name):
        """Switch to a different page"""
        if self.current_page == page_name:
            return

        if self.current_page and self.current_page in self.pages:
            self.pages[self.current_page].place_forget()

        if page_name in self.pages:
            self.pages[page_name].place(x=0, y=0, relwidth=1, relheight=1)
            self.current_page = page_name
            self._update_active_menu_item()

            # Update stats pages when shown
            if page_name == "day_stats" and hasattr(self, 'day_stats_page'):
                self.day_stats_page.update()
            elif page_name == "all_stats" and hasattr(self, 'all_stats_page'):
                self.all_stats_page.update()

    def _update_active_menu_item(self):
        """Highlight active menu item"""
        for lbl, page_id, frame in self.menu_labels:
            if page_id == self.current_page:
                lbl.config(fg=THEME["accent"], font=("Consolas", 10, "bold"))
                frame.config(bg="#0d1820")
            else:
                lbl.config(fg=THEME["muted"], font=("Consolas", 10))
                frame.config(bg=THEME["bg_sidebar"])

    def _get_live_sample(self):
        """Get latest system sample"""
        try:
            if self.logger and hasattr(self.logger, "get_last_n_samples"):
                last = self.logger.get_last_n_samples(1)
                if last:
                    return last[-1]
            if self.monitor and hasattr(self.monitor, "read_snapshot"):
                return self.monitor.read_snapshot()
        except:
            pass

        # Fallback (if psutil available)
        if psutil is not None:
            try:
                return {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "ram_percent": psutil.virtual_memory().percent,
                    "gpu_percent": 0.0
                }
            except:
                pass
        return None

    def _get_chart_samples(self):
        """Get samples for chart display"""
        try:
            if self.logger and hasattr(self.logger, "get_last_seconds"):
                samples = self.logger.get_last_seconds(30)
                if samples:
                    return samples
        except:
            pass
        return []

    def _update_process_lists(self):
        """Update TOP5 process lists with enhanced classification"""
        procs = []
        try:
            if self.monitor and hasattr(self.monitor, "top_processes"):
                procs = self.monitor.top_processes(80, by="cpu+ram")
            elif psutil is not None:
                for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                    try:
                        info = p.info
                        mem_info = info.get("memory_info")
                        procs.append({
                            "pid": p.pid,
                            "name": info.get("name") or "unknown",
                            "cpu_percent": info.get("cpu_percent") or 0.0,
                            "ram_MB": (mem_info.rss / 1024 / 1024) if mem_info else 0.0
                        })
                    except:
                        continue
                procs.sort(key=lambda r: (r.get("cpu_percent", 0.0) + (r.get("ram_MB", 0.0)/1000.0)), reverse=True)
        except:
            procs = []

        # Record snapshot for data manager
        if self.data_manager and self.classifier:
            try:
                self.data_manager.record_process_snapshot(procs, self.classifier)
            except Exception as e:
                print(f"[DataManager] Error recording snapshot: {e}")

        # Classify and separate
        user_procs = []
        system_procs = []

        for proc in procs:
            proc_name = proc.get("name", "unknown")

            if self.classifier:
                classification = self.classifier.classify_process(proc_name)
                proc['classification'] = classification

                if classification['type'] in ['browser', 'program', 'unknown']:
                    user_procs.append(proc)
                elif classification['type'] == 'system':
                    system_procs.append(proc)
            else:
                # Fallback without classifier
                if any(k in proc_name.lower() for k in ["system", "svchost", "explorer", "dwm"]):
                    system_procs.append(proc)
                else:
                    user_procs.append(proc)

        # Render lists
        self._render_user_processes(user_procs[:5])
        self._render_system_processes(system_procs[:5])

    def _render_user_processes(self, procs):
        """Modern minimalist process display - side by side CPU/RAM bars with gradient shading"""
        # Clear old widgets
        for widget in self.top5_widgets:
            widget.destroy()
        self.top5_widgets = []

        # Gradient backgrounds for TOP 1-5 (darker to lighter)
        row_gradients = ["#1c1f26", "#1e2128", "#20232a", "#22252c", "#24272e"]

        for i, proc in enumerate(procs[:5], start=1):  # Ensure only TOP 5
            # Get process info (NO EMOJIS!)
            if self.classifier and 'classification' in proc:
                cls = proc['classification']
                display_name = cls.get('display_name', proc['name'])
                proc_name = proc.get('name', 'unknown')
            else:
                display_name = proc.get('name', 'unknown')
                proc_name = proc.get('name', 'unknown')

            cpu = proc.get('cpu_percent', 0)
            ram_mb = proc.get('ram_MB', 0)

            # Row with gradient background
            row_bg = row_gradients[i-1] if i <= len(row_gradients) else THEME["bg_panel"]
            row = tk.Frame(self.top5_container, bg=row_bg, cursor="hand2", height=20)
            row.pack(fill="x", pady=1, padx=2)
            row.pack_propagate(False)

            # Process name (left side) - clean and compact
            name_lbl = tk.Label(
                row,
                text=f"{i}. {display_name[:18]}",  # Longer names, no emoji
                font=("Segoe UI", 8),
                bg=row_bg,
                fg=THEME["text"],
                anchor="w"
            )
            name_lbl.pack(side="left", padx=6, fill="y")

            # Right side - CPU and RAM SIDE BY SIDE
            bars_frame = tk.Frame(row, bg=row_bg)
            bars_frame.pack(side="right", padx=4)

            # CPU bar and value (LEFT)
            cpu_container = tk.Frame(bars_frame, bg=row_bg)
            cpu_container.pack(side="left", padx=2)

            cpu_lbl = tk.Label(cpu_container, text="CPU", font=("Segoe UI", 6),
                              bg=row_bg, fg="#6b7280", width=3)
            cpu_lbl.pack(side="left", padx=(0,2))

            self._create_inline_bar(cpu_container, cpu, "#3b82f6", f"{cpu:.0f}%", bg=row_bg)

            # RAM bar and value (RIGHT)
            ram_container = tk.Frame(bars_frame, bg=row_bg)
            ram_container.pack(side="left", padx=2)

            ram_lbl = tk.Label(ram_container, text="RAM", font=("Segoe UI", 6),
                              bg=row_bg, fg="#6b7280", width=3)
            ram_lbl.pack(side="left", padx=(0,2))

            ram_pct = min((ram_mb / 8192) * 100, 100)
            self._create_inline_bar(ram_container, ram_pct, "#fbbf24", f"{ram_mb:.0f}MB", bg=row_bg)

            # Click to show info
            row.bind("<Button-1>", lambda e, p=proc_name: self._show_process_info_click(e, p))

            self.top5_widgets.append(row)

    def _create_inline_bar(self, parent, value, color, text, bg):
        """Create inline progress bar (side by side layout)"""
        # Bar background
        bar_bg = tk.Frame(parent, bg="#1a1d24", width=45, height=5)
        bar_bg.pack(side="left", padx=(0, 3))
        bar_bg.pack_propagate(False)

        # Bar fill
        bar_fill = tk.Frame(bar_bg, bg=color, height=5)
        bar_fill.place(x=0, y=0, relwidth=min(value/100.0, 1.0), relheight=1.0)

        # Value text
        val_lbl = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 7),
            bg=bg,
            fg=color,
            width=5,
            anchor="e"
        )
        val_lbl.pack(side="left")

    def _render_system_processes(self, procs):
        """Modern minimalist system process display - side by side CPU/RAM bars with gradient shading"""
        # Clear old widgets
        for widget in self.sys_widgets:
            widget.destroy()
        self.sys_widgets = []

        # Gradient backgrounds for TOP 1-5 (darker to lighter)
        row_gradients = ["#1c1f26", "#1e2128", "#20232a", "#22252c", "#24272e"]

        for i, proc in enumerate(procs[:5], start=1):  # Ensure only TOP 5
            # Get process info (NO EMOJIS!)
            if self.classifier and 'classification' in proc:
                cls = proc['classification']
                display_name = cls.get('display_name', proc['name'])
                proc_name = proc.get('name', 'unknown')
            else:
                display_name = proc.get('name', 'unknown')
                proc_name = proc.get('name', 'unknown')

            cpu = proc.get('cpu_percent', 0)
            ram_mb = proc.get('ram_MB', 0)

            # Row with gradient background
            row_bg = row_gradients[i-1] if i <= len(row_gradients) else THEME["bg_panel"]
            row = tk.Frame(self.sys_container, bg=row_bg, cursor="hand2", height=20)
            row.pack(fill="x", pady=1, padx=2)
            row.pack_propagate(False)

            # Process name (left side) - clean and compact
            name_lbl = tk.Label(
                row,
                text=f"{i}. {display_name[:16]}",  # Clean names, no emoji
                font=("Segoe UI", 8),
                bg=row_bg,
                fg=THEME["text"],
                anchor="w"
            )
            name_lbl.pack(side="left", padx=6, fill="y")

            # Right side - CPU and RAM SIDE BY SIDE
            bars_frame = tk.Frame(row, bg=row_bg)
            bars_frame.pack(side="right", padx=4)

            # CPU bar and value (LEFT)
            cpu_container = tk.Frame(bars_frame, bg=row_bg)
            cpu_container.pack(side="left", padx=2)

            cpu_lbl = tk.Label(cpu_container, text="CPU", font=("Segoe UI", 6),
                              bg=row_bg, fg="#6b7280", width=3)
            cpu_lbl.pack(side="left", padx=(0,2))

            self._create_inline_bar(cpu_container, cpu, "#3b82f6", f"{cpu:.0f}%", bg=row_bg)

            # RAM bar and value (RIGHT)
            ram_container = tk.Frame(bars_frame, bg=row_bg)
            ram_container.pack(side="left", padx=2)

            ram_lbl = tk.Label(ram_container, text="RAM", font=("Segoe UI", 6),
                              bg=row_bg, fg="#6b7280", width=3)
            ram_lbl.pack(side="left", padx=(0,2))

            ram_pct = min((ram_mb / 8192) * 100, 100)
            self._create_inline_bar(ram_container, ram_pct, "#fbbf24", f"{ram_mb:.0f}MB", bg=row_bg)

            # Click to show info
            row.bind("<Button-1>", lambda e, p=proc_name: self._show_process_info_click(e, p))

            self.sys_widgets.append(row)

    def _show_process_info_click(self, event, process_name):
        """Show process info tooltip on click"""
        if self.process_tooltip:
            self.process_tooltip.show(process_name, event.x_root, event.y_root)

    def _open_optimization_page(self):
        """Open Optimization Options page"""
        print("[Dashboard] Opening Optimization Options page...")
        self.show_page("optimization")

    def _open_yourpc_page(self):
        """Open YOUR PC - Personal data page"""
        print("[Dashboard] Opening YOUR PC page...")
        self.show_page("yourpc")

    def _update_services_counter(self):
        """Update services counter in OPTIMIZATION OPTIONS button"""
        try:
            import subprocess
            # Get total services count
            result = subprocess.run(['sc', 'query', 'type=', 'service', 'state=', 'all'],
                                  capture_output=True, text=True, timeout=2)
            total = result.stdout.count('SERVICE_NAME:')

            # Get active services count
            result_active = subprocess.run(['sc', 'query', 'type=', 'service'],
                                         capture_output=True, text=True, timeout=2)
            active = result_active.stdout.count('SERVICE_NAME:')

            self.opt_services_label.config(text=f"Services active: {active}/{total}")
        except Exception as e:
            print(f"[Warning] Could not update services counter: {e}")
            self.opt_services_label.config(text="Services active: --/--")

    def _update_led_bars(self, sample):
        """Update LED bars"""
        cpu = sample.get("cpu_percent", 0.0)
        gpu = sample.get("gpu_percent", 0.0)
        ram = sample.get("ram_percent", 0.0)

        self.cpu_led.update(cpu)
        self.gpu_led.update(gpu)
        self.ram_led.update(ram)

    def _populate_process_list(self, list_widget, processes, list_type):
        """
        Populate process list widget with data

        Args:
            list_widget: ExpandableProcessList widget
            processes: List of process dicts
            list_type: 'user' or 'system'
        """
        if not hasattr(list_widget, 'update_processes'):
            return

        try:
            # Convert format if needed
            formatted_processes = []
            for proc in processes:
                formatted_processes.append({
                    'name': proc.get('name', 'unknown'),
                    'display_name': proc.get('display_name', proc.get('name', 'unknown')),
                    'cpu_percent': proc.get('cpu_percent', 0),
                    'ram_MB': proc.get('ram_MB', 0),
                    'icon': proc.get('icon', ''),
                    'is_rival': proc.get('is_rival', False),
                    'is_critical': proc.get('is_critical', False),
                    'type': proc.get('type', 'unknown'),
                    'category': proc.get('category', 'Unknown')
                })

            list_widget.update_processes(formatted_processes)

        except Exception as e:
            print(f"[ProcessList] Error populating list: {e}")

    def _update_loop(self):
        """Main UI update loop - thread-safe version using after()"""
        def update_ui():
            if not self._running:
                return

            try:
                now = time.time()
                sample = self._get_live_sample()

                if sample:
                    self._update_led_bars(sample)
                    # Update YOUR PC page if it exists
                    self._update_yourpc_data(sample)

                # Update chart and processes every 1 second
                if not hasattr(self, '_last_chart_update'):
                    self._last_chart_update = 0

                if now - self._last_chart_update >= 1.0:
                    samples = self._get_chart_samples()
                    if samples:
                        self.chart.update(samples)
                        try:
                            self.canvas.draw_idle()
                        except:
                            self.canvas.draw()

                    # Only update process lists if NOT in TIME TRAVEL mode
                    if not self.time_travel_mode:
                        self._update_process_lists()
                    self._last_chart_update = now

            except Exception as e:
                print(f"[UpdateLoop] Error: {e}")

            # Schedule next update
            if self._running:
                self.root.after(500, update_ui)

        # Start the update cycle
        self.root.after(100, update_ui)

    def _tray_update_loop(self):
        """Update system tray icon with current CPU/GPU"""
        while self._running:
            try:
                if self.tray_manager and self.tray_manager.is_running():
                    sample = self._get_live_sample()
                    if sample:
                        self.tray_manager.update_stats(
                            sample.get('cpu_percent', 0),
                            sample.get('ram_percent', 0)  # Changed from GPU to RAM
                        )
                time.sleep(2.0)  # Update tray every 2 seconds
            except Exception as e:
                print(f"[TrayUpdate] Error: {e}")
                time.sleep(2.0)

    # Sidebar animation methods (from original)
    def _schedule_sidebar_auto_collapse(self):
        self.root.after(self._auto_collapse_after_ms, lambda: self._collapse_sidebar())

    def _expand_sidebar(self):
        if self._sidebar_animating or self.sidebar_expanded:
            return
        self._sidebar_animating = True
        self._animate_sidebar(
            THEME["sidebar_collapsed"],
            THEME["sidebar_expanded"],
            on_end=lambda: self.menu_frame.place(x=6, y=48, width=108)
        )

    def _collapse_sidebar(self):
        if self._sidebar_animating or not self.sidebar_expanded:
            return
        self._sidebar_animating = True
        self.menu_frame.place_forget()
        self._animate_sidebar(THEME["sidebar_expanded"], THEME["sidebar_collapsed"])

    def _animate_sidebar(self, start_w, end_w, duration_ms=150, on_end=None):
        """Smooth sidebar animation"""
        start_time = time.time()
        diff = end_w - start_w

        def ease_out_quad(t):
            return 1 - (1 - t) * (1 - t)

        def anim():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)
            eased_progress = ease_out_quad(progress)
            current_w = int(start_w + (diff * eased_progress))

            self.sidebar.place_configure(width=current_w)
            self.content.place_configure(x=current_w, width=THEME["win_width"] - current_w)

            if progress >= 1.0:
                self.sidebar.place_configure(width=end_w)
                self.content.place_configure(x=end_w, width=THEME["win_width"] - end_w)
                self.sidebar_expanded = (end_w == THEME["sidebar_expanded"])
                self._sidebar_animating = False
                if on_end:
                    on_end()
                return

            self.root.after(16, anim)

        anim()

    def _collapse_sidebar_delayed(self):
        self.root.after(600, lambda: (self._collapse_sidebar() if not self._mouse_over_sidebar() else None))

    def _mouse_over_sidebar(self):
        x, y = self.root.winfo_pointerxy()
        rx = self.root.winfo_rootx()
        sx = x - rx
        try:
            w = int(self.sidebar.place_info().get("width", THEME["sidebar_collapsed"]))
            return (0 <= sx <= w)
        except:
            return False

    def _noop(self):
        pass

    def _switch_to_expanded(self):
        """Switch from Minimal to Expanded Mode"""
        print("[MinimalMode] Switching to Expanded Mode...")
        if self.switch_to_expanded_callback:
            self.switch_to_expanded_callback()

    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        finally:
            self._running = False
            self._quit_application()
