# ui/main_window_expanded.py
"""
PC Workman - EXPANDED MODE (Main Window) v1.7.1
980x500 resolution, centered, full-featured interface
Full-featured interface with modern dark theme
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import os

# PIL for icon loading
try:
    from PIL import Image, ImageTk, ImageEnhance
except ImportError:
    Image = None
    ImageTk = None
    ImageEnhance = None

# Import with error handling
try:
    import psutil
except ImportError:
    psutil = None

from ui.theme import THEME
from ui.components.led_bars import LEDSegmentBar, AnimatedBar
from ui.components.sidebar_nav import SidebarNav
from ui.pages.fan_control import create_fans_hardware_page, create_fans_usage_stats_page

# YOUR PC page helper
from ui.components.yourpc_page import build_yourpc_page

# Process library tooltip
try:
    from hck_gpt.process_library import process_library as _proc_lib
    from hck_gpt.tooltip import ProcessTooltip
    _HAS_PROC_LIB = True
except ImportError:
    _HAS_PROC_LIB = False

# Fan Dashboard (Advanced cooling control)
from ui.components.fan_dashboard import create_fan_dashboard

# Overlay Widget (Floating Monitor)
try:
    from ui.overlay_widget import create_overlay_widget
except ImportError:
    create_overlay_widget = None

# Live Guide
try:
    from ui.guide.live_guide import LiveGuide as _LiveGuide
except ImportError:
    _LiveGuide = None

# System Tray
try:
    from ui.system_tray import SystemTrayManager, ToastNotification
except ImportError:
    print("[WARNING] System tray not available (missing pystray/pillow)")
    SystemTrayManager = None
    ToastNotification = None

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class ExpandedMainWindow:
    """
    Expanded Mode - Full-featured 980x500 window
    - Modern header with mode switcher
    - Session average bars (CPU/GPU/RAM)
    - Advanced chart
    - Category navigation
    - Dark theme with gradient accents
    """

    def __init__(self, data_manager=None, monitor=None, switch_to_minimal_callback=None, quit_callback=None):
        self.data_manager = data_manager
        self.monitor = monitor
        self.switch_to_minimal_callback = switch_to_minimal_callback
        self.quit_callback = quit_callback

        # Session averages tracking
        self.session_samples = []
        self.max_session_samples = 1000  # Keep last 1000 samples

        # Running flag
        self._running = False

        # Overlay panel system
        self.active_overlay = None
        self.overlay_frame = None

        # View switching system
        self.current_view = "dashboard"

        # ── Persistent LIVE chart buffer — survives view switches ─────────────
        # DO NOT reset in _build_dashboard_view(); data accumulates here forever.
        self.chart_data = {"cpu": [], "ram": [], "gpu": []}
        self.chart_max_samples = 100
        self.chart_filter = "LIVE"
        self._historical_chart_data = None
        self._chart_after_id = None

        # System Tray
        self.tray_manager = None
        self._init_system_tray()

        # Create root window
        self.root = tk.Tk()
        self.root.title("PC Workman - HCK Labs v1.7.1")
        self.root.geometry("1160x575")  # Expanded for sidebar (980 + 180)
        self.root.configure(bg=THEME["bg_main"])
        self.root.resizable(False, False)

        # Load navigation icons (AFTER root window creation)
        self.nav_icons = {}
        self.nav_icons_hover = {}
        self._load_navigation_icons()

        # Handle window close (X button) → minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Center window on screen
        self._center_window()

        # Build UI
        self._build_ui()

        # Start update loop - AFTER() BASED, NO THREADING
        self._running = True
        self._update_counter = 0
        self.root.after(100, self._update_loop)  # Start after 100ms

    def _load_navigation_icons(self):
        """Load PNG icons for navigation buttons with glow effect"""
        if not Image or not ImageTk:
            print("[Icons] PIL not available, icons won't load")
            return

        icon_map = {
            "your_pc": "your_pc.png",
            "optimization": "Boost.png",
            "statistics": "statistics.png",
            "fan_control": "fan_dashboard.png",
            "hck_labs": "send_hck.png",
            "guide": "Guide.png"
        }

        icons_dir = "data/icons"
        icon_size = (24, 24)  # Resize to 24x24

        for key, filename in icon_map.items():
            try:
                icon_path = os.path.join(icons_dir, filename)
                if not os.path.exists(icon_path):
                    print(f"[Icons] Not found: {icon_path}")
                    continue

                # Load and resize icon
                img = Image.open(icon_path)
                img = img.resize(icon_size, Image.Resampling.LANCZOS)
                self.nav_icons[key] = ImageTk.PhotoImage(img)

                # Create glowing version (brighten)
                enhancer = ImageEnhance.Brightness(img)
                img_bright = enhancer.enhance(1.5)  # 50% brighter
                self.nav_icons_hover[key] = ImageTk.PhotoImage(img_bright)

                print(f"[Icons] Loaded: {key} -> {filename}")
            except Exception as e:
                print(f"[Icons] Error loading {filename}: {e}")

    def _center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = 1160  # Expanded for sidebar (980 + 180)
        height = 575
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        """Build complete UI"""
        # MAIN CONTAINER (sidebar + content)
        self.main_container = tk.Frame(self.root, bg=THEME["bg_main"])
        self.main_container.pack(fill="both", expand=True)

        # LEFT SIDEBAR (Snyk Evo style) - 180px wide
        self.sidebar = SidebarNav(
            self.main_container,
            width=180,
            on_navigate=self._handle_sidebar_navigation
        )
        self.sidebar.pack(side="left", fill="y")

        # RIGHT CONTENT AREA
        self.content_area = tk.Frame(self.main_container, bg=THEME["bg_main"])
        self.content_area.pack(side="left", fill="both", expand=True)

        # Track current view
        self.current_view = "dashboard"
        self.dashboard_widgets = []  # Store dashboard widgets for show/hide

        # Build dashboard view (default)
        self._build_dashboard_view()

    def _build_dashboard_view(self):
        """Build the main dashboard view"""
        # HEADER (in content area)
        self._build_header()

        # SESSION AVERAGE BARS + NAVIGATION
        self._build_middle_section()

        # MAIN CONTENT AREA (chart, etc.)
        self._build_content_area()

        # HCK_GPT BANNER (bottom)
        self._build_hckgpt_banner()

    def _switch_to_page(self, page_id):
        """Switch content area to a specific page (replaces dashboard)"""
        print(f"[Switch] Switching to page: {page_id} (current: {self.current_view})")

        if self.current_view == page_id and page_id != "dashboard":
            return

        # Kill overlay immediately (no animation) to prevent race conditions
        if self.overlay_frame:
            try:
                self.overlay_frame.destroy()
            except Exception:
                pass
            self.overlay_frame = None
            self.active_overlay = None

        # Clear current content
        for widget in self.content_area.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        self.current_view = page_id

        # Build the new page
        if page_id == "dashboard":
            self._build_dashboard_view()
        elif page_id == "fans_hardware":
            self._build_fans_hardware_view()
        elif page_id == "fans_usage_stats":
            self._build_fans_usage_stats_view()
        elif page_id == "fan_control":
            self._build_fan_dashboard_view()
        elif page_id == "monitoring_alerts":
            self._build_monitoring_alerts_view()
        elif page_id == "first_setup":
            self._build_first_setup_view()
        elif page_id == "optimization":
            self._build_optimization_view()
        elif page_id == "startup_manager":
            self._build_startup_manager_view()
        elif page_id == "services_manager":
            self._build_services_manager_view()
        else:
            # For other pages, use the overlay system
            self._build_dashboard_view()
            self._show_overlay(page_id)

    def _build_page_header(self, title, subtitle=""):
        """Build a header for sub-pages with back button"""
        header = tk.Frame(self.content_area, bg="#0a0e14", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Back button
        back_btn = tk.Label(
            header,
            text="← Dashboard",
            font=("Segoe UI Semibold", 10),
            bg="#0a0e14",
            fg="#8b5cf6",
            cursor="hand2",
            padx=15
        )
        back_btn.pack(side="left", pady=15)

        def go_back_to_dashboard(e):
            self._switch_to_page("dashboard")
            # Update sidebar active state
            if hasattr(self, 'sidebar') and self.sidebar:
                self.sidebar.set_active_page("dashboard")

        back_btn.bind("<Button-1>", go_back_to_dashboard)

        # Hover effect
        def on_enter(e):
            back_btn.config(fg="#a78bfa")
        def on_leave(e):
            back_btn.config(fg="#8b5cf6")
        back_btn.bind("<Enter>", on_enter)
        back_btn.bind("<Leave>", on_leave)

        # Title
        tk.Label(
            header,
            text=title,
            font=("Segoe UI Semibold", 16, "bold"),
            bg="#0a0e14",
            fg="#ffffff"
        ).pack(side="left", padx=(20, 10), pady=15)

        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                font=("Segoe UI", 10),
                bg="#0a0e14",
                fg="#6b7280"
            ).pack(side="left", pady=15)

        return header

    def _build_fans_hardware_view(self):
        """Build FANS - Hardware Info as main view"""
        self._build_page_header("FANS - Hardware Info", "Real-time fan monitoring")

        # Content
        content = tk.Frame(self.content_area, bg="#0a0e14")
        content.pack(fill="both", expand=True)

        create_fans_hardware_page(content, self.monitor)

    def _build_fans_usage_stats_view(self):
        """Build Usage Statistics as main view"""
        self._build_page_header("Usage Statistics", "Fan intensity over time")

        # Content
        content = tk.Frame(self.content_area, bg="#0a0e14")
        content.pack(fill="both", expand=True)

        create_fans_usage_stats_page(content, self.monitor)

    def _build_fan_dashboard_view(self):
        """Build Fan Dashboard as main view"""
        self._build_page_header("Fan Dashboard", "Cooling control center")

        # Content - use existing fan dashboard
        content = tk.Frame(self.content_area, bg="#0f1117")
        content.pack(fill="both", expand=True)

        try:
            create_fan_dashboard(content)
        except Exception as e:
            print(f"[Fan Dashboard] Error: {e}")
            import traceback
            traceback.print_exc()
            tk.Label(
                content,
                text="Fan Dashboard loading...",
                font=("Segoe UI", 12),
                bg="#0f1117",
                fg="#6b7280"
            ).pack(pady=50)

    def _build_monitoring_alerts_view(self):
        """Build Monitoring & Alerts page with Time-Travel charts"""
        from ui.pages.monitoring_alerts import build_monitoring_alerts_page
        build_monitoring_alerts_page(self, self.content_area)

    def _build_first_setup_view(self):
        """Build First Setup & Drivers page — driver health, startup, checklist."""
        from ui.pages.first_setup_drivers import build_first_setup_page
        build_first_setup_page(self, self.content_area)

    def _build_optimization_view(self):
        self._build_page_header("Optimization & Services", "Boost, clean and automate your PC")
        try:
            from ui.pages.optimization_services import build_optimization_page
            build_optimization_page(self, self.content_area)
        except Exception as e:
            import traceback
            err = tk.Label(self.content_area, text=f"Failed to load page:\n{e}",
                           font=("Segoe UI", 10), bg="#0a0e14", fg="#ef4444",
                           justify="left", padx=20, pady=20)
            err.pack(anchor="nw")
            traceback.print_exc()

    def _build_startup_manager_view(self):
        """Build Startup Manager page."""
        self._build_page_header("Startup Manager", "Control which programs launch at boot")
        try:
            from ui.pages.startup_manager import build_startup_manager_page
            build_startup_manager_page(self, self.content_area)
        except Exception as e:
            import traceback
            tk.Label(self.content_area, text=f"Failed to load Startup Manager:\n{e}",
                     font=("Segoe UI", 10), bg="#0a0e14", fg="#ef4444",
                     justify="left", padx=20, pady=20).pack(anchor="nw")
            traceback.print_exc()

    def _build_services_manager_view(self):
        """Build Services Manager page."""
        self._build_page_header("Services Manager", "Manage Windows services & TURBO integration")
        try:
            from ui.pages.services_manager import build_services_manager_page
            build_services_manager_page(self, self.content_area)
        except Exception as e:
            import traceback
            tk.Label(self.content_area, text=f"Failed to load Services Manager:\n{e}",
                     font=("Segoe UI", 10), bg="#0a0e14", fg="#ef4444",
                     justify="left", padx=20, pady=20).pack(anchor="nw")
            traceback.print_exc()

    def _handle_sidebar_navigation(self, page_id, subpage_id=None):
        """Handle navigation from sidebar"""
        try:
            print(f"[Sidebar Nav] Navigate to: {page_id}" + (f".{subpage_id}" if subpage_id else ""), flush=True)

            # Pages that replace the entire content area (not overlay)
            direct_pages = {
                "dashboard": "dashboard",
                "fan_control.fans_hardware": "fans_hardware",
                "fan_control.usage_statistics": "fans_usage_stats",
                "fan_control.fan_dashboard": "fan_control",
                "fan_control": "fan_control",
                "monitoring_alerts": "monitoring_alerts",
                "monitoring_alerts.temperature": "monitoring_alerts",
                "monitoring_alerts.voltage": "monitoring_alerts",
                "monitoring_alerts.alerts": "monitoring_alerts",
                "first_setup": "first_setup",
                "first_setup.drivers": "first_setup",
                "first_setup.startup": "first_setup",
                "first_setup.checklist": "first_setup",
                "optimization": "optimization",
                "optimization.services": "optimization",
                "optimization.startup": "optimization",
                "optimization.wizard": "optimization",
                "startup_manager": "startup_manager",
                "services_manager": "services_manager",
            }

            # Build lookup key
            if subpage_id:
                full_id = f"{page_id}.{subpage_id}"
            else:
                full_id = page_id

            # Fast path: direct page switch
            if full_id in direct_pages:
                target = direct_pages[full_id]
                self.current_view = None  # Force rebuild
                self._switch_to_page(target)
                return
            if page_id in direct_pages:
                target = direct_pages[page_id]
                self.current_view = None  # Force rebuild
                self._switch_to_page(target)
                return

            # Map sidebar IDs to overlay pages
            page_map = {
                "my_pc": "your_pc",
                "my_pc.central": "your_pc",
                "my_pc.efficiency": "your_pc",
                "my_pc.sensors": "sensors",
                "my_pc.health": "your_pc",
                "optimization": "optimization",
                "optimization.services": "optimization",
                "optimization.startup": "optimization",
                "optimization.wizard": "optimization",
                "statistics": "statistics",
                "statistics.stats_today": "statistics",
                "statistics.stats_weekly": "statistics",
                "statistics.stats_monthly": "statistics",
                "settings": "settings",
                "pinned": None,
            }

            target = page_map.get(full_id, page_map.get(page_id))

            if target is None:
                self.current_view = None
                self._switch_to_page("dashboard")
                return

            # For overlay pages, ensure dashboard is active first
            if self.current_view != "dashboard":
                self.current_view = None
                self._switch_to_page("dashboard")

            self._show_overlay(target)

        except Exception as e:
            print(f"[Sidebar Nav] Error: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.current_view = None
                self._switch_to_page("dashboard")
            except Exception:
                pass

    def _build_hckgpt_banner(self):
        """Build hck_GPT panel at bottom of dashboard (uses shared HCKGPTPanel)"""
        try:
            from hck_gpt.panel import HCKGPTPanel
            content_w = self.content_area.winfo_width()
            if content_w < 100:
                content_w = 980
            self.gpt_panel = HCKGPTPanel(
                parent=self.content_area,
                width=content_w,
                collapsed_h=34,
                expanded_h=298,
                max_h=438
            )
            # Wire clickable nav links — [→ Optimization] / [→ Startup Manager]
            try:
                self.gpt_panel.register_nav_callback(
                    "Optimization",
                    lambda: self._switch_to_page("optimization")
                )
                self.gpt_panel.register_nav_callback(
                    "Startup Manager",
                    lambda: self._switch_to_page("startup_manager")
                )
            except Exception:
                pass
        except Exception as e:
            print(f"[hck_GPT] Panel init error: {e}")
            # Fallback: simple static banner
            banner = tk.Frame(self.content_area, bg="#8b5cf6", height=35)
            banner.pack(fill="x", side="bottom")
            banner.pack_propagate(False)
            tk.Label(banner, text="hck_GPT - Your PC master!",
                     font=("Segoe UI", 9, "bold"), bg="#8b5cf6", fg="#ffffff"
                     ).pack(side="left", padx=15, pady=5)

    def _build_header(self):
        """Build modern header with branding and mode switcher"""
        header = tk.Frame(self.content_area, bg="#0a0e27", height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Left side - Branding
        left_frame = tk.Frame(header, bg="#0a0e27")
        left_frame.pack(side="left", padx=20, fill="y")

        # Title
        title = tk.Label(
            left_frame,
            text="PC_WORKMAN",
            font=("Segoe UI Light", 22, "bold"),  # Light font for ultra-modern look, bigger!
            bg="#0a0e27",
            fg="#ffffff"
        )
        title.pack(side="left", pady=15)

        # Subtitle
        subtitle = tk.Label(
            left_frame,
            text="Your PC Masterdude",
            font=("Segoe UI Semilight", 13),  # Semilight for elegance!
            bg="#0a0e27",
            fg="#6366f1"
        )
        subtitle.pack(side="left", padx=(10, 0), pady=15)

        # Right side - Mini Monitor + Mode switcher
        right_frame = tk.Frame(header, bg="#0a0e27")
        right_frame.pack(side="right", padx=20, fill="y")

        # Minimal mode button
        mode_btn = tk.Label(
            right_frame,
            text="⚡ Minimal Mode",
            font=("Segoe UI Semibold", 10, "bold"),  # Semibold for modern punch!
            bg="#1e293b",
            fg="#94a3b8",
            cursor="hand2",
            padx=15,
            pady=8
        )
        mode_btn.pack(side="right", pady=12)
        mode_btn.bind("<Button-1>", lambda e: self._switch_to_minimal())

        # Hover effect
        def on_enter(e):
            mode_btn.config(bg="#334155", fg="#e2e8f0")
        def on_leave(e):
            mode_btn.config(bg="#1e293b", fg="#94a3b8")

        mode_btn.bind("<Enter>", on_enter)
        mode_btn.bind("<Leave>", on_leave)

    def _build_middle_section(self):
        """Build session average bars + category navigation"""
        middle = tk.Frame(self.content_area, bg=THEME["bg_main"], height=180)
        middle.pack(fill="x", side="top", padx=20, pady=(10, 0))
        middle.pack_propagate(False)

        # LEFT NAVIGATION
        left_nav = tk.Frame(middle, bg=THEME["bg_panel"], width=200)
        left_nav.pack(side="left", fill="y", padx=(0, 10))
        left_nav.pack_propagate(False)
        self.guide_left_nav = left_nav   # used by LiveGuide spotlight

        # Navigation buttons (left) — no section label, max space for buttons
        nav_buttons_left = [
            ("💻 My PC", "#3b82f6", "— Central"),
            ("📡 Monitoring", "#8b5cf6", "Centrum"),
            ("📊 AllMonitor", "#f97316", "see all min,max data"),
            ("⚡ Optimization", "#10b981", ""),
        ]

        for text, color, subtitle in nav_buttons_left:
            self._create_nav_button(left_nav, text, color, subtitle, pady=2)

        # CENTER - SESSION AVERAGE BARS
        center = tk.Frame(middle, bg=THEME["bg_main"])
        center.pack(side="left", fill="both", expand=True, padx=5)
        self.guide_middle_center = center   # used by LiveGuide spotlight

        # Title - MINIMAL SPACING
        tk.Label(
            center,
            text="SESSION AVERAGES",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"]
        ).pack(pady=(2, 5))

        # CPU Bar
        self._create_session_bar(center, "CPU", "#3b82f6", "#ef4444", "cpu")

        # GPU Bar
        self._create_session_bar(center, "GPU", "#10b981", "#64748b", "gpu")

        # RAM Bar
        self._create_session_bar(center, "RAM", "#fbbf24", "#1e40af", "ram")

        # YOUR PC - PERSONAL DATA section
        self._build_yourpc_section(center)

        # RIGHT NAVIGATION
        right_nav = tk.Frame(middle, bg=THEME["bg_panel"], width=200)
        right_nav.pack(side="right", fill="y", padx=(10, 0))
        right_nav.pack_propagate(False)
        self.guide_right_nav = right_nav   # used by LiveGuide spotlight

        # Navigation buttons (right) — no section label
        nav_buttons_right = [
            ("🌀 FAN Dashboard", "#8b5cf6", "— Central"),
            ("🚀 HCK_Labs", "#f59e0b", ""),
            ("📖 Guide", "#06b6d4", ""),
        ]

        for text, color, subtitle in nav_buttons_right:
            self._create_nav_button(right_nav, text, color, subtitle, pady=2)

    def _create_nav_button(self, parent, text, color, subtitle="", pady=4):
        """Dark gradient nav button: deep navy bg, bordeaux L-corner brackets, bold text."""
        btn_container = tk.Frame(parent, bg=THEME["bg_panel"])
        btn_container.pack(fill="x", padx=6, pady=pady)

        page_map = {
            "💻 My PC":         "your_pc",
            "📡 Monitoring":    "sensors",
            "📊 AllMonitor":    "live_graphs",
            "⚡ Optimization":  "optimization",
            "🌀 FAN Dashboard": "fan_control",
            "🚀 HCK_Labs":      "hck_labs",
            "📖 Guide":         "guide",
        }
        page_id    = page_map.get(text)
        clean_text = text.split(" ", 1)[-1] if " " in text else text

        # Accent color parsed to RGB for glow effect
        ac_r = int(color[1:3], 16)
        ac_g = int(color[3:5], 16)
        ac_b = int(color[5:7], 16)

        ICON_W  = 44          # left icon panel width
        CL      = 11          # corner bracket arm length (px)
        BW      = 2           # bracket stroke width (px)
        BD      = "#6b0a1a"   # bordeaux dark
        BL      = "#c0182a"   # crimson light
        BH      = "#e8253f"   # crimson hover

        btn_h = 58 if subtitle else 46
        canvas = tk.Canvas(btn_container, bg=THEME["bg_panel"],
                           height=btn_h, highlightthickness=0, cursor="hand2")
        canvas.pack(fill="x")

        def _redraw(hovered=False):
            canvas.delete("all")
            w = canvas.winfo_width()
            if w <= 1:
                return
            h = btn_h

            # ── Background gradient ───────────────────────────────────────────
            # Normal: very dark navy  |  Hover: dark accent colour bleeds in
            STRIP = 3
            # base dark colours (left → right endpoints)
            base0 = (0x08, 0x0b, 0x18)
            base1 = (0x10, 0x16, 0x26)
            # target hover colours: darkened accent (≈30% of accent, rest black)
            hov0  = (ac_r // 5, ac_g // 5, ac_b // 5)
            hov1  = (ac_r // 3, ac_g // 3, ac_b // 3)
            blend = 0.72 if hovered else 0.0   # 0=base only, 1=hover only

            for x in range(0, w, STRIP):
                t  = x / w
                # interpolate base left→right
                br = int(base0[0] + (base1[0] - base0[0]) * t)
                bg_ = int(base0[1] + (base1[1] - base0[1]) * t)
                bb = int(base0[2] + (base1[2] - base0[2]) * t)
                # interpolate hover left→right
                hr_ = int(hov0[0] + (hov1[0] - hov0[0]) * t)
                hg_ = int(hov0[1] + (hov1[1] - hov0[1]) * t)
                hb_ = int(hov0[2] + (hov1[2] - hov0[2]) * t)
                # blend
                r  = min(255, int(br + (hr_ - br) * blend))
                g_ = min(255, int(bg_ + (hg_ - bg_) * blend))
                b_ = min(255, int(bb + (hb_ - bb) * blend))
                canvas.create_rectangle(x, 0, x + STRIP, h,
                                        fill=f"#{r:02x}{g_:02x}{b_:02x}", outline="")

            # ── Icon panel (darkest left section) ────────────────────────────
            canvas.create_rectangle(0, 0, ICON_W, h, fill="#05070d", outline="")

            # 3-px left accent stripe in button accent colour
            canvas.create_rectangle(0, 0, 3, h, fill=color, outline="")

            # vector icon (drawn programmatically)
            _draw_page_icon(canvas, page_id, ICON_W // 2, h // 2, color)

            # thin separator after icon area
            canvas.create_rectangle(ICON_W, 4, ICON_W + 1, h - 4,
                                    fill="#1c2135", outline="")

            # ── Right-edge colour hint (subtle accent glow) ───────────────────
            GW = 22
            for i in range(GW):
                a  = (1 - i / GW) * 0.20
                xp = w - GW + i
                r2 = min(255, int(0x10 + (ac_r - 0x10) * a))
                g2 = min(255, int(0x16 + (ac_g - 0x16) * a))
                b2 = min(255, int(0x26 + (ac_b - 0x26) * a))
                canvas.create_line(xp, 0, xp, h,
                                   fill=f"#{r2:02x}{g2:02x}{b2:02x}")

            # ── Bottom accent line: bordeaux→crimson, right 55% of button ────
            lx0 = int(w * 0.45)
            lw  = w - lx0
            for x in range(lx0, w):
                t  = (x - lx0) / lw if lw else 0
                r3 = int(0x6b + (0xc0 - 0x6b) * t)
                g3 = int(0x0a + (0x18 - 0x0a) * t)
                b3 = int(0x1a + (0x2a - 0x1a) * t)
                canvas.create_line(x, h - 1, x + 1, h - 1,
                                   fill=f"#{r3:02x}{g3:02x}{b3:02x}")

            # ── Bottom-only L-corner brackets ────────────────────────────────
            bl     = BL if not hovered else BH
            tx_off = ICON_W + 5

            # Bottom-left  |_
            canvas.create_rectangle(tx_off,     h - 2 - CL, tx_off + BW, h - 2, fill=BD, outline="")
            canvas.create_rectangle(tx_off,     h - 2 - BW, tx_off + CL, h - 2, fill=BD, outline="")
            # Bottom-right  _|
            canvas.create_rectangle(w - 5 - BW, h - 2 - CL, w - 5, h - 2, fill=bl, outline="")
            canvas.create_rectangle(w - 5 - CL, h - 2 - BW, w - 5, h - 2, fill=bl, outline="")

            # ── Text — vertically centred with room to breathe ────────────────
            tx = ICON_W + 14
            if subtitle:
                # main text at 38% height, subtitle at 68%
                ty_main = int(h * 0.38)
                ty_sub  = int(h * 0.68)
            else:
                ty_main = h // 2

            # Drop shadow
            canvas.create_text(tx + 1, ty_main + 1, text=clean_text.upper(),
                               font=("Segoe UI Black", 10),
                               fill="#000000", anchor="w")
            # Main label
            canvas.create_text(tx, ty_main, text=clean_text.upper(),
                               font=("Segoe UI Black", 10),
                               fill="#ffffff", anchor="w")

            if subtitle:
                canvas.create_text(tx, ty_sub, text=subtitle,
                                   font=("Segoe UI", 8),
                                   fill="#8490a8", anchor="w")

        def _draw_once():
            if canvas.winfo_width() <= 1:
                canvas.after(30, _draw_once)
                return
            _redraw(False)

        _draw_once()

        if page_id:
            canvas.bind("<Button-1>", lambda e: self._show_overlay(page_id))

        canvas.bind("<Enter>", lambda e: _redraw(True))
        canvas.bind("<Leave>", lambda e: _redraw(False))

    def _create_session_bar(self, parent, label, color_start, color_end, key):
        """Create session average bar with AnimatedBar."""
        row = tk.Frame(parent, bg=THEME["bg_main"])
        row.pack(fill="x", pady=1)

        lbl = tk.Label(
            row,
            text=label,
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"],
            width=4,
            anchor="w"
        )
        lbl.pack(side="left", padx=(8, 4))

        bar = AnimatedBar(row, color_start, bg_color="#1a1d24", height=16)
        bar.bg_frame.pack(side="left", fill="x", expand=True, padx=4)

        val_lbl = tk.Label(
            row,
            text="0%",
            font=("Consolas", 8, "bold"),
            bg=THEME["bg_main"],
            fg=color_start,
            width=4,
            anchor="e"
        )
        val_lbl.pack(side="right", padx=(4, 8))

        if not hasattr(self, 'session_bars'):
            self.session_bars = {}

        self.session_bars[key] = {
            "bar": bar,
            "label": val_lbl,
            "color": color_start
        }

    def _build_yourpc_section(self, parent):
        """Build YOUR PC - Personal Data section with hardware cards - ULTRA COMPACT"""
        # Section container - minimal padding
        section = tk.Frame(parent, bg=THEME["bg_main"])
        section.pack(fill="x", pady=(6, 2))

        # NO TITLE - just cards directly

        # Cards container (3 cards side by side) - no extra spacing
        cards = tk.Frame(section, bg=THEME["bg_main"])
        cards.pack(fill="x")

        # Get hardware info
        try:
            import platform
            cpu_model = platform.processor()[:25] if platform.processor() else "Unknown CPU"
        except:
            cpu_model = "Unknown CPU"

        try:
            import psutil
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
            ram_model = f"{total_ram_gb:.1f} GB RAM"
        except:
            ram_model = "Unknown RAM"

        # Try to get GPU
        gpu_model = "Unknown GPU"
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_model = gpus[0].name[:25]
        except:
            pass

        # Create 3 hardware cards
        self._create_hardware_card(cards, "CPU", cpu_model, "#3b82f6", "cpu")
        self._create_hardware_card(cards, "RAM", ram_model, "#fbbf24", "ram")
        self._create_hardware_card(cards, "GPU", gpu_model, "#10b981", "gpu")

    def _create_hardware_card(self, parent, hw_type, model, color, key):
        """Create ULTRA COMPACT hardware card"""
        card = tk.Frame(parent, bg=THEME["bg_panel"], relief="flat", bd=0)
        card.pack(side="left", fill="both", expand=True, padx=2)

        # Minimal padding
        inner = tk.Frame(card, bg=THEME["bg_panel"])
        inner.pack(fill="both", expand=True, padx=4, pady=4)

        # Header (type + model) - smaller fonts
        header = tk.Frame(inner, bg=THEME["bg_panel"])
        header.pack(fill="x")

        tk.Label(
            header,
            text=hw_type,
            font=("Segoe UI", 7, "bold"),
            bg=THEME["bg_panel"],
            fg=color,
            anchor="w"
        ).pack(side="left")

        tk.Label(
            header,
            text=model[:20],  # Shorter model name
            font=("Segoe UI", 6),
            bg=THEME["bg_panel"],
            fg=THEME["muted"],
            anchor="w"
        ).pack(side="left", padx=(4, 0))

        # Mini chart area (sparkline) - SMALLER
        chart_frame = tk.Frame(inner, bg="#0f1117", height=22)
        chart_frame.pack(fill="x", pady=(3, 0))
        chart_frame.pack_propagate(False)

        chart_canvas = tk.Canvas(chart_frame, bg="#0f1117", highlightthickness=0)
        chart_canvas.pack(fill="both", expand=True)

        # Temperature bar - smaller
        temp_frame = tk.Frame(inner, bg=THEME["bg_panel"])
        temp_frame.pack(fill="x", pady=(3, 0))

        tk.Label(
            temp_frame,
            text="TEMP",
            font=("Segoe UI", 5),
            bg=THEME["bg_panel"],
            fg=THEME["muted"]
        ).pack(side="left")

        temp_bar_bg = tk.Frame(temp_frame, bg="#1a1d24", height=4)
        temp_bar_bg.pack(side="left", fill="x", expand=True, padx=(3, 3))
        temp_bar_bg.pack_propagate(False)

        temp_bar_fill = tk.Frame(temp_bar_bg, bg=color, height=4)
        temp_bar_fill.place(x=0, y=0, relwidth=0, relheight=1.0)

        temp_label = tk.Label(
            temp_frame,
            text="0°C",
            font=("Consolas", 6),
            bg=THEME["bg_panel"],
            fg=color,
            width=3
        )
        temp_label.pack(side="right")

        # Health status - smaller font
        health_label = tk.Label(
            inner,
            text="✓ All good",
            font=("Segoe UI", 6),
            bg=THEME["bg_panel"],
            fg="#10b981",
            anchor="w"
        )
        health_label.pack(fill="x", pady=(2, 0))

        # Load status - smaller font
        load_label = tk.Label(
            inner,
            text="No activity",
            font=("Segoe UI", 6),
            bg=THEME["bg_panel"],
            fg=THEME["muted"],
            anchor="w"
        )
        load_label.pack(fill="x", pady=(1, 0))

        # Store references for updates
        if not hasattr(self, 'hardware_cards'):
            self.hardware_cards = {}

        self.hardware_cards[key] = {
            "chart_canvas": chart_canvas,
            "chart_data": [],  # Store last 30 values for sparkline
            "temp_bar": temp_bar_fill,
            "temp_label": temp_label,
            "health_label": health_label,
            "load_label": load_label,
            "color": color
        }

    def _build_content_area(self):
        """Build main content area with chart + live metrics + TOP 5 panels"""
        content = tk.Frame(self.content_area, bg=THEME["bg_main"])
        content.pack(fill="both", expand=True, padx=20, pady=10)

        # MAIN ROW: Left panel | Chart | Right panel
        main_row = tk.Frame(content, bg=THEME["bg_main"])
        main_row.pack(fill="both", expand=True)

        # LEFT PANEL - TOP 5 User Processes
        left_panel = tk.Frame(main_row, bg=THEME["bg_panel"], width=220)
        left_panel.pack(side="left", fill="y", padx=(0, 8))
        left_panel.pack_propagate(False)

        tk.Label(
            left_panel,
            text="TOP 5 USER PROCESSES",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["muted"]
        ).pack(pady=(8, 5))

        # Container for user process rows
        self.expanded_user_container = tk.Frame(left_panel, bg=THEME["bg_panel"])
        self.expanded_user_container.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.expanded_user_widgets = []

        # Process tooltip (shared for both TOP 5 panels)
        self._process_tooltip = ProcessTooltip(self.root) if _HAS_PROC_LIB else None

        # AI Writing Panel (bottom of left panel)
        self._build_ai_writing_panel(left_panel)

        # CENTER - Chart + Live Metrics
        center = tk.Frame(main_row, bg=THEME["bg_main"])
        center.pack(side="left", fill="both", expand=True, padx=5)

        # Chart (50% height - reduced)
        chart_frame = tk.Frame(center, bg="#0f1117", height=140)
        chart_frame.pack(fill="x", pady=(0, 5))
        chart_frame.pack_propagate(False)

        # === ULTRA MODERN REAL-TIME CHART ===
        # Canvas for 3-bar chart (CPU, RAM, GPU)
        self.realtime_canvas = tk.Canvas(
            chart_frame,
            bg="#0f1117",
            highlightthickness=0,
            width=500,
            height=140
        )
        self.realtime_canvas.pack(fill="both", expand=True, padx=8, pady=5)

        # Trigger chart draw once canvas actually has dimensions
        self.realtime_canvas.bind('<Configure>', self._on_chart_configure)

        # chart_data / chart_max_samples persist from __init__ — do NOT reset here.
        # The LIVE buffer survives view switches so the chart never starts blank.
        self._chart_after_id = None   # reset so _schedule_chart_update works on new canvas

        # Start chart update loop
        self._schedule_chart_update(100)

        # Live metrics line
        metrics_frame = tk.Frame(center, bg="#1a1d24", height=28)
        metrics_frame.pack(fill="x")
        metrics_frame.pack_propagate(False)

        tk.Label(
            metrics_frame,
            text="CURRENT USAGE:",
            font=("Segoe UI", 7, "bold"),
            bg="#1a1d24",
            fg="#6b7280"
        ).pack(side="left", padx=(10, 15))

        # CPU metric
        self.live_cpu_label = tk.Label(
            metrics_frame,
            text="CPU: 0%",
            font=("Consolas", 8, "bold"),
            bg="#1a1d24",
            fg="#3b82f6"
        )
        self.live_cpu_label.pack(side="left", padx=8)

        # GPU metric
        self.live_gpu_label = tk.Label(
            metrics_frame,
            text="GPU: 0%",
            font=("Consolas", 8, "bold"),
            bg="#1a1d24",
            fg="#10b981"
        )
        self.live_gpu_label.pack(side="left", padx=8)

        # RAM metric
        self.live_ram_label = tk.Label(
            metrics_frame,
            text="RAM: 0%",
            font=("Consolas", 8, "bold"),
            bg="#1a1d24",
            fg="#fbbf24"
        )
        self.live_ram_label.pack(side="left", padx=8)

        # Time filter buttons (chart_filter persists from __init__ — not reset on view switch)

        # Separator (visual space)
        tk.Frame(metrics_frame, bg="#1a1d24", width=2).pack(side="left", padx=10)

        # Filter buttons container
        filter_btns = tk.Frame(metrics_frame, bg="#1a1d24")
        filter_btns.pack(side="right", padx=10)

        # Create filter buttons - real-time + historical from SQLite
        filter_options = ["LIVE", "1H", "4H", "1D", "1W", "1M"]
        self.filter_buttons = {}
        # Historical data cache — reset on dashboard rebuild (new canvas, reload needed)
        self._historical_chart_data = None

        for idx, filter_name in enumerate(filter_options):
            _active = (filter_name == getattr(self, 'chart_filter', 'LIVE'))
            btn = tk.Label(
                filter_btns,
                text=filter_name,
                font=("Segoe UI", 6, "bold"),
                bg="#2563eb" if _active else "#000000",
                fg="#ffffff"  if _active else "#6b7280",
                cursor="hand2",
                padx=6,
                pady=2
            )
            btn.pack(side="left", padx=1)

            # Click handler
            def make_filter_click(f_name, f_btn):
                def on_click(e):
                    # Reset all buttons to black
                    for fb in self.filter_buttons.values():
                        fb.config(bg="#000000", fg="#6b7280")
                    # Highlight selected
                    f_btn.config(bg="#2563eb", fg="#ffffff")
                    self.chart_filter = f_name
                    if hasattr(self, '_chart_last_num'):
                        self._chart_last_num = -1
                    if f_name != 'LIVE':
                        self._load_historical_chart_data(f_name)
                    else:
                        self._historical_chart_data = None
                    # Immediate redraw — don't wait for 2s timer
                    self._schedule_chart_update(50)
                return on_click

            btn.bind("<Button-1>", make_filter_click(filter_name, btn))
            self.filter_buttons[filter_name] = btn

            # Hover effect
            def make_hover(f_btn, f_name):
                def on_enter(e):
                    if self.chart_filter != f_name:
                        f_btn.config(bg="#1a1a1a")
                def on_leave(e):
                    if self.chart_filter != f_name:
                        f_btn.config(bg="#000000")
                return on_enter, on_leave

            enter_h, leave_h = make_hover(btn, filter_name)
            btn.bind("<Enter>", enter_h)
            btn.bind("<Leave>", leave_h)

        # === INNOVATIVE FEATURE BUTTONS (below chart) ===
        self._build_feature_buttons(center)

        # RIGHT PANEL - TOP 5 System Processes
        right_panel = tk.Frame(main_row, bg=THEME["bg_panel"], width=220)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        tk.Label(
            right_panel,
            text="TOP 5 SYSTEM PROCESSES",
            font=("Segoe UI", 8, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["muted"]
        ).pack(pady=(8, 5))

        # Container for system process rows
        self.expanded_sys_container = tk.Frame(right_panel, bg=THEME["bg_panel"])
        self.expanded_sys_container.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.expanded_sys_widgets = []

    def _build_feature_buttons(self, parent):
        """Build feature buttons — Turbo Boost & More Optimization Tools."""
        buttons_container = tk.Frame(parent, bg=THEME["bg_main"])
        buttons_container.pack(fill="x", pady=(8, 0))

        # Container for two buttons side by side
        buttons_row = tk.Frame(buttons_container, bg=THEME["bg_main"])
        buttons_row.pack(fill="x", padx=5)

        # Left: Turbo Boost — COMING SOON (greyed out)
        turbo_btn = tk.Frame(buttons_row, bg="#2a2d35")
        turbo_btn.pack(side="left", fill="both", expand=True, padx=(0, 3))

        turbo_content = tk.Frame(turbo_btn, bg="#1e2028")
        turbo_content.pack(fill="both", expand=True, padx=2, pady=2)

        turbo_header = tk.Frame(turbo_content, bg="#2a2d35")
        turbo_header.pack(fill="x", padx=8, pady=(6, 4))

        tk.Label(
            turbo_header,
            text="Turbo Boost:",
            font=("Segoe UI", 11, "bold"),
            bg="#2a2d35",
            fg="#6b7280",
            padx=6, pady=2
        ).pack(side="left")

        tk.Label(
            turbo_header,
            text="OFF",
            font=("Segoe UI", 11, "bold"),
            bg="#2a2d35",
            fg="#4b5563",
            padx=4, pady=2
        ).pack(side="left")

        self.turbo_active = False

        tk.Frame(turbo_content, bg="#374151", height=1).pack(fill="x", pady=(4, 4))

        turbo_actions = tk.Frame(turbo_content, bg="#1e2028")
        turbo_actions.pack(fill="x", padx=8, pady=(0, 6))

        tk.Label(
            turbo_actions,
            text="Configure",
            font=("Segoe UI", 7, "bold"),
            bg="#374151", fg="#6b7280",
            padx=8, pady=3
        ).pack(side="left")

        tk.Label(
            turbo_actions,
            text="Launch",
            font=("Segoe UI", 7, "bold"),
            bg="#374151", fg="#6b7280",
            padx=10, pady=3
        ).pack(side="right")

        # ── Coming soon tooltip ───────────────────────────────────────────────
        _tip = tk.Label(
            self.root,
            text="Coming soon…\nCheck Optimization Center for features",
            font=("Segoe UI", 9),
            bg="#1c1f27", fg="#94a3b8",
            padx=10, pady=8,
            justify="center",
            relief="flat",
            bd=0
        )

        def _show_tip(e):
            x = turbo_btn.winfo_rootx()
            y = turbo_btn.winfo_rooty() + turbo_btn.winfo_height() + 4
            _tip.place(x=x - self.root.winfo_rootx(),
                       y=y - self.root.winfo_rooty())
            _tip.lift()

        def _hide_tip(e):
            _tip.place_forget()

        for w in (turbo_btn, turbo_content, turbo_header, turbo_actions):
            w.bind("<Enter>", _show_tip, add="+")
            w.bind("<Leave>", _hide_tip, add="+")

        # === RIGHT: MORE OPTIMIZATION TOOLS ===
        optim_btn = tk.Frame(buttons_row, bg="#10b981", cursor="hand2")  # Bright green border
        optim_btn.pack(side="right", fill="both", expand=True, padx=(3, 0))

        # Main content container with glowing background
        optim_content = tk.Frame(optim_btn, bg="#047857")  # Brighter background
        optim_content.pack(fill="both", expand=True, padx=2, pady=2)

        # Header with GLOWING background
        optim_header = tk.Frame(optim_content, bg="#10b981")  # Bright glowing green header
        optim_header.pack(fill="x", padx=8, pady=(6, 4))

        tk.Label(
            optim_header,
            text="More Optimization Tools",
            font=("Segoe UI", 11, "bold"),
            bg="#10b981",  # Bright background
            fg="#ffffff",
            padx=6,
            pady=2
        ).pack(anchor="w")

        # Thin separator line (brighter) - moved up (no subtitles)
        tk.Frame(optim_content, bg="#34d399", height=2).pack(fill="x", pady=(4, 4))

        # Bottom action buttons
        optim_actions = tk.Frame(optim_content, bg="#047857")
        optim_actions.pack(fill="x", padx=8, pady=(0, 6))

        # Statystyki button (brighter)
        stats_btn = tk.Label(
            optim_actions,
            text="Performance improvement statistics",
            font=("Segoe UI", 7, "bold"),
            bg="#10b981",
            fg="#ffffff",
            cursor="hand2",
            padx=8,
            pady=3
        )
        stats_btn.pack(side="left")

        # Click handler
        def open_stats(e):
            self._show_overlay("statistics")

        stats_btn.bind("<Button-1>", open_stats)

        # Hover effect
        def on_enter_stats(e):
            stats_btn.config(bg="#34d399")  # Brighter on hover
        def on_leave_stats(e):
            stats_btn.config(bg="#10b981")
        stats_btn.bind("<Enter>", on_enter_stats)
        stats_btn.bind("<Leave>", on_leave_stats)

        # Active tools counter
        self.tools_label = tk.Label(
            optim_actions,
            text="Active tools: ",
            font=("Segoe UI", 7),
            bg="#047857",
            fg="#a7f3d0"
        )
        self.tools_label.pack(side="right", padx=(0, 2))

        self.tools_count_label = tk.Label(
            optim_actions,
            text="0/16",
            font=("Segoe UI", 7, "bold"),
            bg="#047857",
            fg="#34d399"  # Brighter green for glowing effect
        )
        self.tools_count_label.pack(side="right")

        # Start glowing animation for numbers
        self._animate_tools_glow()

    def _animate_turbo_glow(self):
        """Animate glowing effect on Turbo Boost ON/OFF status"""
        if not hasattr(self, 'turbo_status_label'):
            return

        try:
            if self.turbo_active:
                # Brighter glow between vivid green shades
                colors = ["#34d399", "#6ee7b7", "#a7f3d0", "#6ee7b7", "#34d399"]
            else:
                # Brighter glow between vivid red/pink shades
                colors = ["#f87171", "#fca5a5", "#fecaca", "#fca5a5", "#f87171"]

            if not hasattr(self, '_turbo_glow_index'):
                self._turbo_glow_index = 0

            self.turbo_status_label.config(fg=colors[self._turbo_glow_index % len(colors)])
            self._turbo_glow_index += 1

            # Continue animation
            if self._running:
                self.root.after(500, self._animate_turbo_glow)
        except:
            pass

    def _animate_tools_glow(self):
        """Animate glowing effect on tools count numbers"""
        if not hasattr(self, 'tools_count_label'):
            return

        try:
            # Brighter glow between vivid green shades
            colors = ["#34d399", "#6ee7b7", "#a7f3d0", "#6ee7b7", "#34d399"]

            if not hasattr(self, '_tools_glow_index'):
                self._tools_glow_index = 0

            self.tools_count_label.config(fg=colors[self._tools_glow_index % len(colors)])
            self._tools_glow_index += 1

            # Continue animation
            if self._running:
                self.root.after(600, self._animate_tools_glow)
        except:
            pass

    def _build_ai_writing_panel(self, parent):
        """Build compact info panel with typing animation"""
        panel = tk.Frame(parent, bg="#0a0e27", height=50)
        panel.pack(fill="x", padx=5, pady=(3, 3))
        panel.pack_propagate(False)

        # Thin accent line at top
        tk.Frame(panel, bg="#8b5cf6", height=1).pack(fill="x")

        # Text display area — fills entire panel
        text_area = tk.Frame(panel, bg="#0f1117")
        text_area.pack(fill="both", expand=True, padx=4, pady=2)

        # Text label with cursor
        self.ai_text_container = tk.Frame(text_area, bg="#0f1117")
        self.ai_text_container.pack(fill="both", expand=True)

        self.ai_text_label = tk.Label(
            self.ai_text_container,
            text="",
            font=("Consolas", 8),
            bg="#0f1117",
            fg="#a78bfa",
            wraplength=200,
            justify="left",
            anchor="nw"
        )
        self.ai_text_label.pack(side="left", fill="both", expand=True)

        # Blinking cursor
        self.ai_cursor = tk.Label(
            self.ai_text_container,
            text="|",
            font=("Consolas", 8, "bold"),
            bg="#0f1117",
            fg="#a78bfa"
        )
        self.ai_cursor.pack(side="left", anchor="n")

        # Messages — shorter, punchier
        self.ai_messages = [
            "PC Workman — by Marcin 'HCK' Firmuga",
            "16 optimization tools, one-click setup.",
            "Built with heart from the Netherlands.",
            "Your PC, Smarter. Always watching.",
        ]

        self.ai_current_message_index = 0
        self.ai_current_text = ""
        self.ai_typing = False
        self.ai_deleting = False
        self.ai_char_index = 0

        # Start animations
        self.root.after(500, self._animate_ai_cursor)
        self.root.after(500, self._animate_ai_typing)

    def _animate_ai_cursor(self):
        """Blink cursor animation"""
        if not hasattr(self, 'ai_cursor'):
            return

        try:
            if not self.ai_cursor.winfo_exists():
                return
            current_fg = self.ai_cursor.cget("fg")
            if current_fg == "#a78bfa":
                self.ai_cursor.config(fg="#0f1117")  # Hide
            else:
                self.ai_cursor.config(fg="#a78bfa")  # Show

            if self._running:
                self.root.after(600, self._animate_ai_cursor)
        except:
            pass

    def _animate_ai_typing(self):
        """Type message character by character, then delete"""
        if not hasattr(self, 'ai_text_label') or not hasattr(self, 'ai_messages'):
            return

        try:
            if not self.ai_text_label.winfo_exists():
                return

            message = self.ai_messages[self.ai_current_message_index]
            delay = 70

            if not self.ai_typing and not self.ai_deleting:
                self.ai_typing = True
                self.ai_char_index = 0
                self.ai_current_text = ""
                delay = 70

            elif self.ai_typing:
                if self.ai_char_index < len(message):
                    self.ai_current_text = message[:self.ai_char_index + 1]
                    self.ai_text_label.config(text=self.ai_current_text)
                    self.ai_char_index += 1
                    delay = 70
                else:
                    self.ai_typing = False
                    self.ai_deleting = True
                    delay = 6000  # Hold 6s

            elif self.ai_deleting:
                if len(self.ai_current_text) > 0:
                    # Delete 3 chars at a time for speed
                    self.ai_current_text = self.ai_current_text[:-3] if len(self.ai_current_text) > 3 else ""
                    self.ai_text_label.config(text=self.ai_current_text)
                    delay = 30
                else:
                    self.ai_deleting = False
                    self.ai_current_message_index = (self.ai_current_message_index + 1) % len(self.ai_messages)
                    delay = 1500

            if self._running:
                self.root.after(delay, self._animate_ai_typing)
        except Exception:
            if self._running:
                self.root.after(2000, self._animate_ai_typing)


    def _render_expanded_user_processes(self, procs):
        """Render TOP 5 user processes — 2-line rows with animated bars."""
        if not hasattr(self, 'expanded_user_container'):
            return
        try:
            if not self.expanded_user_container.winfo_exists():
                return
        except Exception:
            return

        cpu_cores = self._cached_cpu_count()
        total_ram_mb = self._cached_total_ram_mb()

        row_gradients = ["#1c1f26", "#1e2128", "#20232a", "#22252c", "#24272e"]

        if not self.expanded_user_widgets:
            for i in range(5):
                row_bg = row_gradients[i]
                row = tk.Frame(self.expanded_user_container, bg=row_bg, height=36)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                # Line 1 — process name
                top_line = tk.Frame(row, bg=row_bg)
                top_line.pack(fill="x", padx=6, pady=(4, 0))

                name_lbl = tk.Label(
                    top_line, text="", font=("Segoe UI", 7, "bold"),
                    bg=row_bg, fg=THEME["text"], anchor="w"
                )
                name_lbl.pack(side="left")

                # Line 2 — CPU + RAM bars
                bars_line = tk.Frame(row, bg=row_bg)
                bars_line.pack(fill="x", padx=6, pady=(2, 4))

                # CPU half
                cpu_half = tk.Frame(bars_line, bg=row_bg)
                cpu_half.pack(side="left", fill="x", expand=True)

                tk.Label(cpu_half, text="CPU", font=("Segoe UI", 6, "bold"),
                         bg=row_bg, fg="#3b82f6").pack(side="left")

                cpu_bar = AnimatedBar(cpu_half, "#3b82f6", bg_color="#0d1117", height=5)
                cpu_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                cpu_val = tk.Label(cpu_half, text="0%", font=("Consolas", 6),
                                   bg=row_bg, fg="#3b82f6", width=3, anchor="e")
                cpu_val.pack(side="left")

                # Divider
                tk.Frame(bars_line, bg="#2a2d34", width=1).pack(
                    side="left", fill="y", padx=3)

                # RAM half
                ram_half = tk.Frame(bars_line, bg=row_bg)
                ram_half.pack(side="left", fill="x", expand=True)

                tk.Label(ram_half, text="RAM", font=("Segoe UI", 6, "bold"),
                         bg=row_bg, fg="#fbbf24").pack(side="left")

                ram_bar = AnimatedBar(ram_half, "#fbbf24", bg_color="#0d1117", height=5)
                ram_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                ram_val = tk.Label(ram_half, text="0%", font=("Consolas", 6),
                                   bg=row_bg, fg="#fbbf24", width=3, anchor="e")
                ram_val.pack(side="left")

                widget_data = {
                    "row": row, "name": name_lbl,
                    "cpu_bar": cpu_bar, "cpu_val": cpu_val,
                    "ram_bar": ram_bar, "ram_val": ram_val,
                    "proc_name": "",
                }
                self.expanded_user_widgets.append(widget_data)

                # Tooltip bindings
                if self._process_tooltip:
                    def _enter(e, wd=widget_data):
                        pn = wd["proc_name"]
                        if pn:
                            tt = _proc_lib.format_tooltip_text(pn)
                            if tt:
                                self._process_tooltip.show(e, pn, tt)
                    def _leave(e):
                        self._process_tooltip.hide()
                    name_lbl.bind("<Enter>", _enter)
                    name_lbl.bind("<Leave>", _leave)
                    row.bind("<Enter>", _enter)
                    row.bind("<Leave>", _leave)

        for i, widget_data in enumerate(self.expanded_user_widgets):
            if i < len(procs):
                proc = procs[i]
                display_name = proc.get('name', 'unknown')
                cpu_raw = proc.get('cpu_percent', 0)
                ram_mb = proc.get('ram_MB', 0)
                cpu_pct = (cpu_raw / cpu_cores) if cpu_cores > 0 else cpu_raw
                ram_pct = (ram_mb / total_ram_mb) * 100 if total_ram_mb > 0 else 0

                widget_data["proc_name"] = display_name
                widget_data["name"].config(text=f"{i+1}. {display_name[:20]}")
                widget_data["cpu_bar"].set_target(cpu_pct)
                widget_data["cpu_val"].config(text=f"{cpu_pct:.0f}%")
                widget_data["ram_bar"].set_target(ram_pct)
                widget_data["ram_val"].config(text=f"{ram_pct:.0f}%")
                widget_data["row"].pack(fill="x", pady=1)
            else:
                widget_data["name"].config(text="")
                widget_data["cpu_bar"].set_target(0)
                widget_data["cpu_val"].config(text="")
                widget_data["ram_bar"].set_target(0)
                widget_data["ram_val"].config(text="")

    def _render_expanded_system_processes(self, procs):
        """Render TOP 5 system processes — reuse widgets instead of destroy/recreate"""
        if not hasattr(self, 'expanded_sys_container'):
            return
        try:
            if not self.expanded_sys_container.winfo_exists():
                return
        except Exception:
            return

        cpu_cores = self._cached_cpu_count()
        total_ram_mb = self._cached_total_ram_mb()

        row_gradients = ["#1c1f26", "#1e2128", "#20232a", "#22252c", "#24272e"]

        if not self.expanded_sys_widgets:
            for i in range(5):
                row_bg = row_gradients[i]
                row = tk.Frame(self.expanded_sys_container, bg=row_bg, height=36)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                # Line 1 — process name
                top_line = tk.Frame(row, bg=row_bg)
                top_line.pack(fill="x", padx=6, pady=(4, 0))

                name_lbl = tk.Label(
                    top_line, text="", font=("Segoe UI", 7, "bold"),
                    bg=row_bg, fg=THEME["text"], anchor="w"
                )
                name_lbl.pack(side="left")

                # Line 2 — CPU + RAM bars
                bars_line = tk.Frame(row, bg=row_bg)
                bars_line.pack(fill="x", padx=6, pady=(2, 4))

                # CPU half
                cpu_half = tk.Frame(bars_line, bg=row_bg)
                cpu_half.pack(side="left", fill="x", expand=True)

                tk.Label(cpu_half, text="CPU", font=("Segoe UI", 6, "bold"),
                         bg=row_bg, fg="#3b82f6").pack(side="left")

                cpu_bar = AnimatedBar(cpu_half, "#3b82f6", bg_color="#0d1117", height=5)
                cpu_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                cpu_val = tk.Label(cpu_half, text="0%", font=("Consolas", 6),
                                   bg=row_bg, fg="#3b82f6", width=3, anchor="e")
                cpu_val.pack(side="left")

                # Divider
                tk.Frame(bars_line, bg="#2a2d34", width=1).pack(
                    side="left", fill="y", padx=3)

                # RAM half
                ram_half = tk.Frame(bars_line, bg=row_bg)
                ram_half.pack(side="left", fill="x", expand=True)

                tk.Label(ram_half, text="RAM", font=("Segoe UI", 6, "bold"),
                         bg=row_bg, fg="#fbbf24").pack(side="left")

                ram_bar = AnimatedBar(ram_half, "#fbbf24", bg_color="#0d1117", height=5)
                ram_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                ram_val = tk.Label(ram_half, text="0%", font=("Consolas", 6),
                                   bg=row_bg, fg="#fbbf24", width=3, anchor="e")
                ram_val.pack(side="left")

                sys_widget_data = {
                    "row": row, "name": name_lbl,
                    "cpu_bar": cpu_bar, "cpu_val": cpu_val,
                    "ram_bar": ram_bar, "ram_val": ram_val,
                    "proc_name": "",
                }
                self.expanded_sys_widgets.append(sys_widget_data)

                # Tooltip bindings
                if self._process_tooltip:
                    def _sys_enter(e, wd=sys_widget_data):
                        pn = wd["proc_name"]
                        if pn:
                            tt = _proc_lib.format_tooltip_text(pn)
                            if tt:
                                self._process_tooltip.show(e, pn, tt)
                    def _sys_leave(e):
                        self._process_tooltip.hide()
                    name_lbl.bind("<Enter>", _sys_enter)
                    name_lbl.bind("<Leave>", _sys_leave)
                    row.bind("<Enter>", _sys_enter)
                    row.bind("<Leave>", _sys_leave)

        for i, widget_data in enumerate(self.expanded_sys_widgets):
            if i < len(procs):
                proc = procs[i]
                display_name = proc.get('name', 'unknown')
                cpu_raw = proc.get('cpu_percent', 0)
                ram_mb = proc.get('ram_MB', 0)
                cpu_pct = (cpu_raw / cpu_cores) if cpu_cores > 0 else cpu_raw
                ram_pct = (ram_mb / total_ram_mb) * 100 if total_ram_mb > 0 else 0

                widget_data["proc_name"] = display_name
                widget_data["name"].config(text=f"{i+1}. {display_name[:20]}")
                widget_data["cpu_bar"].set_target(cpu_pct)
                widget_data["cpu_val"].config(text=f"{cpu_pct:.0f}%")
                widget_data["ram_bar"].set_target(ram_pct)
                widget_data["ram_val"].config(text=f"{ram_pct:.0f}%")
                widget_data["row"].pack(fill="x", pady=1)
            else:
                widget_data["name"].config(text="")
                widget_data["cpu_bar"].set_target(0)
                widget_data["cpu_val"].config(text="")
                widget_data["ram_bar"].set_target(0)
                widget_data["ram_val"].config(text="")

    def _create_mini_bar(self, parent, value, color, text, bg):
        """Create mini inline bar for compact display"""
        # Bar background
        bar_bg = tk.Frame(parent, bg="#0f1117", width=30, height=4)
        bar_bg.pack(side="left", padx=(0, 2))
        bar_bg.pack_propagate(False)

        # Bar fill
        bar_fill = tk.Frame(bar_bg, bg=color, height=4)
        bar_fill.place(x=0, y=0, relwidth=min(value/100.0, 1.0), relheight=1.0)

        # Value text
        val_lbl = tk.Label(
            parent,
            text=text,
            font=("Consolas", 6),
            bg=bg,
            fg=color,
            width=4,
            anchor="e"
        )
        val_lbl.pack(side="left")

    def _animate_panel(self, container):
        """Quick gradient pulse animation on refresh"""
        try:
            original_bg = container.cget("bg")
            # Lighten
            container.config(bg="#252932")
            self.root.after(80, lambda: self._animate_panel_return(container, original_bg))
        except:
            pass

    def _animate_panel_return(self, container, original_bg):
        """Return to original color"""
        try:
            container.config(bg=original_bg)
        except:
            pass

    def _init_system_tray(self):
        """Initialize system tray icon"""
        if SystemTrayManager is None:
            print("[SystemTray] Not available (missing dependencies)")
            self.tray_manager = None
            return

        try:
            # Callback to show sensors page
            def show_sensors_page():
                self._restore_from_tray()
                self._show_overlay("sensors")

            self.tray_manager = SystemTrayManager(
                main_window_callback=self._restore_from_tray,
                stats_callback=lambda: self._show_overlay("statistics"),
                quit_callback=self._quit_from_tray,
                sensors_callback=show_sensors_page  # NEW: Sensors shortcut! 🌲
            )
            self.tray_manager.start()
            print("[SystemTray] Initialized")
        except Exception as e:
            print(f"[SystemTray] Failed to initialize: {e}")
            self.tray_manager = None

    def _on_closing(self):
        """Handle window close (X button) → Minimize to tray (NOT EXIT!)"""
        print("[ExpandedMode] Minimizing to tray (X clicked) - Program stays running!")

        # Show background notification
        if ToastNotification is not None:
            beautiful_message = (
                "PC_Workman still working!\n"
                "_________________________\n\n"
                "HCK_Labs\n"
                "_________________________\n\n"
                "Right-click tray icon → Exit to close"
            )
            ToastNotification.show(
                "PC_Workman Background Mode",
                beautiful_message,
                duration_ms=4000
            )

        # ONLY MINIMIZE (hide window), DON'T QUIT!
        self.root.withdraw()
        print("[ExpandedMode] Window hidden - running in background!")

    def _restore_from_tray(self):
        """Restore window from system tray → Expanded Mode"""
        print("[ExpandedMode] Restoring from tray")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _quit_from_tray(self):
        """Quit application from tray menu"""
        print("[ExpandedMode] Quitting from tray")
        self._running = False

        if self.tray_manager:
            self.tray_manager.stop()

        if self.quit_callback:
            self.quit_callback()
        else:
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass

    def _switch_to_minimal(self):
        """Switch to minimal mode (⚡ Minimal Mode button)"""
        print("[ExpandedMode] Switching to Minimal Mode...")

        # Hide Expanded window
        self.root.withdraw()

        # Switch to Minimal Mode
        if self.switch_to_minimal_callback:
            self.switch_to_minimal_callback()

    def _cached_cpu_count(self):
        """Cached CPU core count (never changes at runtime)."""
        if not hasattr(self, '_cpu_count_cache'):
            self._cpu_count_cache = psutil.cpu_count() if psutil else 1
        return self._cpu_count_cache

    def _cached_total_ram_mb(self):
        """Cached total RAM in MB (never changes at runtime)."""
        if not hasattr(self, '_total_ram_mb_cache'):
            self._total_ram_mb_cache = (psutil.virtual_memory().total / (1024 * 1024)) if psutil else 8192
        return self._total_ram_mb_cache

    def _update_loop(self):
        """Update loop — 1s cadence, lightweight label updates only."""
        if not self._running:
            return

        try:
            sample = self._get_current_sample()

            if sample:
                self.session_samples.append(sample)
                if len(self.session_samples) > self.max_session_samples:
                    self.session_samples.pop(0)

                n = len(self.session_samples)
                avg_cpu = sum(s.get("cpu_percent", 0) for s in self.session_samples) / n
                avg_gpu = sum(s.get("gpu_percent", 0) for s in self.session_samples) / n
                avg_ram = sum(s.get("ram_percent", 0) for s in self.session_samples) / n

                self._update_session_bar("cpu", avg_cpu)
                self._update_session_bar("gpu", avg_gpu)
                self._update_session_bar("ram", avg_ram)

                self._update_live_metrics(sample)

                # Hardware cards every 2nd tick (2s)
                if not hasattr(self, '_hw_card_counter'):
                    self._hw_card_counter = 0
                self._hw_card_counter += 1
                if self._hw_card_counter >= 2 and self.current_view == "dashboard":
                    self._hw_card_counter = 0
                    self._update_hardware_cards(sample)

                # Tray icon every 3rd tick (3s)
                if self.tray_manager:
                    if not hasattr(self, '_tray_counter'):
                        self._tray_counter = 0
                    self._tray_counter += 1
                    if self._tray_counter >= 3:
                        self._tray_counter = 0
                        cpu = sample.get("cpu_percent", 0)
                        ram = sample.get("ram_percent", 0)
                        gpu = sample.get("gpu_percent", 0)
                        cpu_temp = sample.get("cpu_temp", 0)
                        gpu_temp = sample.get("gpu_temp", 0)
                        self.tray_manager.update_stats(cpu, ram, gpu, cpu_temp, gpu_temp)

                # TOP 5 processes every 3rd tick (3s)
                if not hasattr(self, '_update_counter'):
                    self._update_counter = 0
                self._update_counter += 1
                if self._update_counter >= 3:
                    self._update_counter = 0
                    if self.current_view == "dashboard":
                        self._update_top5_processes()

        except Exception as e:
            print(f"[ExpandedMode] Update error: {e}")
            import traceback
            traceback.print_exc()

        # 1-second cadence (was 300ms — main lag source)
        if self._running:
            self.root.after(1000, self._update_loop)

    def _get_current_sample(self):
        """Get current system sample"""
        if self.monitor and hasattr(self.monitor, "read_snapshot"):
            return self.monitor.read_snapshot()

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

    def _update_session_bar(self, key, value):
        """Update session average bar with smooth animation."""
        if not hasattr(self, 'session_bars'):
            return
        bar_data = self.session_bars.get(key)
        if not bar_data:
            return
        try:
            bar_data["bar"].set_target(value)
            bar_data["label"].config(text=f"{value:.1f}%")
        except Exception:
            pass

    def _update_live_metrics(self, sample):
        """Update live metrics line."""
        try:
            if not hasattr(self, 'live_cpu_label') or not self.live_cpu_label.winfo_exists():
                return

            cpu = sample.get("cpu_percent", 0)
            gpu = sample.get("gpu_percent", 0)
            ram = sample.get("ram_percent", 0)

            self.live_cpu_label.config(text=f"CPU: {cpu:.0f}%")
            self.live_gpu_label.config(text=f"GPU: {gpu:.0f}%")
            self.live_ram_label.config(text=f"RAM: {ram:.0f}%")

            # Update chart data
            if hasattr(self, 'chart_data'):
                self.chart_data['cpu'].append(cpu)
                self.chart_data['gpu'].append(gpu)
                self.chart_data['ram'].append(ram)

                # Keep only last 100 samples
                if len(self.chart_data['cpu']) > self.chart_max_samples:
                    self.chart_data['cpu'].pop(0)
                    self.chart_data['gpu'].pop(0)
                    self.chart_data['ram'].pop(0)
        except:
            pass

    def _load_historical_chart_data(self, mode):
        """Load historical chart data from SQLite stats engine"""
        try:
            from hck_stats_engine.query_api import query_api
            import time as _time

            now = _time.time()
            range_map = {
                '1H': 3600,
                '4H': 4 * 3600,
                '1D': 86400,
                '1W': 7 * 86400,
                '1M': 30 * 86400,
            }
            duration = range_map.get(mode, 86400)
            start_ts = now - duration

            data = query_api.get_usage_for_range(start_ts, now, max_points=100)

            if data:
                self._historical_chart_data = {
                    'cpu': [d['cpu_avg'] for d in data],
                    'ram': [d['ram_avg'] for d in data],
                    'gpu': [d['gpu_avg'] for d in data],
                }
                print(f"[Chart] Loaded {len(data)} points for {mode} ({duration}s range)")
            else:
                self._historical_chart_data = None
                print(f"[Chart] No data available for {mode}")
        except Exception as e:
            print(f"[ExpandedMode] Historical data load error: {e}")
            self._historical_chart_data = None

    def _schedule_chart_update(self, delay_ms=2000):
        """Schedule chart update, cancelling any pending one to avoid duplicate loops."""
        if self._chart_after_id is not None:
            try:
                self.root.after_cancel(self._chart_after_id)
            except Exception:
                pass
        self._chart_after_id = self.root.after(delay_ms, self._update_realtime_chart)

    def _on_chart_configure(self, event):
        """Called when canvas gets real dimensions (first map or resize)."""
        if event.width <= 1 or event.height <= 1:
            return
        if hasattr(self, '_chart_last_num'):
            self._chart_last_num = -1
        self._schedule_chart_update(50)

    def _update_realtime_chart(self):
        """Draw 3-bar real-time chart using reusable canvas rectangles."""
        self._chart_after_id = None
        if not hasattr(self, 'realtime_canvas') or not self._running:
            return

        try:
            canvas = self.realtime_canvas
            width = canvas.winfo_width()
            height = canvas.winfo_height()

            if width <= 1 or height <= 1:
                self._schedule_chart_update(150)
                return

            margin = 10
            cw = width - margin * 2
            ch = height - margin * 2
            bottom_y = margin + ch

            # Periodically refresh historical data (~every 30s in non-LIVE mode)
            if getattr(self, 'chart_filter', 'LIVE') != 'LIVE':
                self._hist_refresh_counter = getattr(self, '_hist_refresh_counter', 0) + 1
                if self._hist_refresh_counter >= 15:
                    self._hist_refresh_counter = 0
                    self._load_historical_chart_data(self.chart_filter)

            # Select data source
            if (getattr(self, 'chart_filter', 'LIVE') != 'LIVE' and
                    getattr(self, '_historical_chart_data', None)):
                cpu_data = self._historical_chart_data.get('cpu', [])
                ram_data = self._historical_chart_data.get('ram', [])
                gpu_data = self._historical_chart_data.get('gpu', [])
            else:
                cpu_data = self.chart_data.get('cpu', [])
                ram_data = self.chart_data.get('ram', [])
                gpu_data = self.chart_data.get('gpu', [])

            num = max(len(cpu_data), len(ram_data), len(gpu_data))

            if num == 0:
                canvas.delete("all")
                canvas.create_text(
                    width // 2, height // 2,
                    text="Collecting data...",
                    fill="#2a2d34", font=("Segoe UI", 9), tags="placeholder"
                )
                self._schedule_chart_update(500)
                return

            canvas.delete("placeholder")

            bar_w = max(int(cw / num), 1)

            if not hasattr(self, '_chart_items'):
                self._chart_items = {'cpu': [], 'ram': [], 'gpu': []}
                self._chart_last_num = 0

            # Rebuild pool when bar count changes
            _prev_num = getattr(self, '_chart_last_num', 0)
            _new_bar_added = num > _prev_num
            if num != _prev_num:
                canvas.delete("chart_bar")
                self._chart_items = {'cpu': [], 'ram': [], 'gpu': []}
                for i in range(num):
                    x1 = margin + i * bar_w
                    x2 = x1 + max(bar_w - 1, 1)
                    cid = canvas.create_rectangle(x1, bottom_y, x2, bottom_y,
                                                  fill="#3b82f6", outline="", tags="chart_bar")
                    rid = canvas.create_rectangle(x1, bottom_y, x2, bottom_y,
                                                  fill="#fbbf24", outline="", tags="chart_bar")
                    gid = canvas.create_rectangle(x1, bottom_y, x2, bottom_y,
                                                  fill="#10b981", outline="", tags="chart_bar")
                    self._chart_items['cpu'].append(cid)
                    self._chart_items['ram'].append(rid)
                    self._chart_items['gpu'].append(gid)
                self._chart_last_num = num

            # Update bar positions — animate newest bar when a new sample arrived
            last = num - 1
            update_range = range(num) if not _new_bar_added else range(num - 1)
            for i in update_range:
                x1 = margin + i * bar_w
                x2 = x1 + max(bar_w - 1, 1)
                cpu_top = bottom_y - int((cpu_data[i] if i < len(cpu_data) else 0) / 100.0 * ch)
                ram_top = bottom_y - int((ram_data[i] if i < len(ram_data) else 0) / 100.0 * ch)
                gpu_top = bottom_y - int((gpu_data[i] if i < len(gpu_data) else 0) / 100.0 * ch)
                canvas.coords(self._chart_items['cpu'][i], x1, cpu_top, x2, bottom_y)
                canvas.coords(self._chart_items['ram'][i], x1, ram_top, x2, bottom_y)
                canvas.coords(self._chart_items['gpu'][i], x1, gpu_top, x2, bottom_y)

            if _new_bar_added and last >= 0:
                # Grow the newest bar from zero height (~60 fps, 600 ms ease-out)
                lx1 = margin + last * bar_w
                lx2 = lx1 + max(bar_w - 1, 1)
                cpu_t = bottom_y - int((cpu_data[last] if last < len(cpu_data) else 0) / 100.0 * ch)
                ram_t = bottom_y - int((ram_data[last] if last < len(ram_data) else 0) / 100.0 * ch)
                gpu_t = bottom_y - int((gpu_data[last] if last < len(gpu_data) else 0) / 100.0 * ch)
                self._start_bar_grow_anim(canvas, last, lx1, lx2, cpu_t, ram_t, gpu_t, bottom_y)

            self._schedule_chart_update(2000)

        except Exception as e:
            print(f"[Chart] Error: {e}")
            if self._running:
                self._schedule_chart_update(2000)

    def _start_bar_grow_anim(self, canvas, idx, x1, x2, cpu_t, ram_t, gpu_t, bottom_y):
        """Start a 600 ms ease-out grow animation for the newest chart bar."""
        import time as _time
        self._bar_anim = {
            'canvas': canvas,
            'cpu_id': self._chart_items['cpu'][idx],
            'ram_id': self._chart_items['ram'][idx],
            'gpu_id': self._chart_items['gpu'][idx],
            'x1': x1, 'x2': x2,
            'cpu_t': cpu_t, 'ram_t': ram_t, 'gpu_t': gpu_t,
            'bottom_y': bottom_y,
            't0': _time.perf_counter(),
            'dur': 0.60,
        }
        self._tick_bar_grow_anim()

    def _tick_bar_grow_anim(self):
        """Animation tick — runs at ~60 fps until the bar reaches full height."""
        import time as _time
        s = getattr(self, '_bar_anim', None)
        if not s:
            return
        try:
            if not s['canvas'].winfo_exists():
                self._bar_anim = None
                return
        except Exception:
            self._bar_anim = None
            return

        elapsed = _time.perf_counter() - s['t0']
        t = min(elapsed / s['dur'], 1.0)
        # ease-out cubic: fast start, slow finish
        ease = 1.0 - (1.0 - t) ** 3
        by = s['bottom_y']

        def _lerp(target):
            return int(by + (target - by) * ease)

        c = s['canvas']
        c.coords(s['cpu_id'], s['x1'], _lerp(s['cpu_t']), s['x2'], by)
        c.coords(s['ram_id'], s['x1'], _lerp(s['ram_t']), s['x2'], by)
        c.coords(s['gpu_id'], s['x1'], _lerp(s['gpu_t']), s['x2'], by)

        if t < 1.0:
            self.root.after(16, self._tick_bar_grow_anim)
        else:
            self._bar_anim = None

    def _update_hardware_cards(self, sample):
        """Update hardware cards with sparklines and status"""
        if not hasattr(self, 'hardware_cards'):
            return

        try:
            cpu = sample.get("cpu_percent", 0)
            ram = sample.get("ram_percent", 0)
            gpu = sample.get("gpu_percent", 0)

            # Update CPU card
            self._update_hardware_card("cpu", cpu)

            # Update RAM card
            self._update_hardware_card("ram", ram)

            # Update GPU card
            self._update_hardware_card("gpu", gpu)
        except Exception as e:
            print(f"[HardwareCards] Error: {e}")

    def _update_hardware_card(self, key, value):
        """Update individual hardware card"""
        if key not in self.hardware_cards:
            return

        card = self.hardware_cards[key]

        # Guard against destroyed widgets
        try:
            if not card["chart_canvas"].winfo_exists():
                return
        except Exception:
            return

        # Add value to chart data
        card["chart_data"].append(value)
        if len(card["chart_data"]) > 30:  # Keep last 30 values
            card["chart_data"].pop(0)

        # Draw sparkline
        self._draw_sparkline(card["chart_canvas"], card["chart_data"], card["color"])

        # Update temperature (simulated based on load)
        temp = 30 + (value * 0.6)  # 30°C base + load-based increase
        card["temp_label"].config(text=f"{temp:.0f}°C")
        card["temp_bar"].place(relwidth=min(temp / 100, 1.0))

        # Update health status - SHORTER TEXTS
        if value < 85:
            card["health_label"].config(text="✓ All good", fg="#10b981")
        else:
            card["health_label"].config(text="⚠ Inspekcja", fg="#f59e0b")

        # Update load status - SHORTER TEXTS
        if value < 10:
            card["load_label"].config(text="No activity", fg=THEME["muted"])
        elif value < 50:
            card["load_label"].config(text="Standard", fg="#3b82f6")
        elif value < 80:
            card["load_label"].config(text="Nadmierne", fg="#f59e0b")
        else:
            card["load_label"].config(text="Maksymalne", fg="#ef4444")

    def _draw_sparkline(self, canvas, data, color):
        """Draw mini sparkline chart"""
        if not data or len(data) < 2:
            return

        try:
            if not canvas.winfo_exists():
                return
            canvas.delete("all")
            width = canvas.winfo_width()
            height = canvas.winfo_height()

            if width < 10 or height < 10:
                return

            # Calculate points
            max_val = max(data) if max(data) > 0 else 100
            min_val = min(data)
            range_val = max_val - min_val if max_val != min_val else 1

            points = []
            for i, val in enumerate(data):
                x = (i / (len(data) - 1)) * width
                y = height - ((val - min_val) / range_val) * height
                points.extend([x, y])

            # Draw line
            if len(points) >= 4:
                canvas.create_line(points, fill=color, width=2, smooth=True)

                # Fill area under curve
                fill_points = points[:]
                fill_points.extend([width, height, 0, height])
                canvas.create_polygon(fill_points, fill=color, stipple="gray25", outline="")

        except Exception as e:
            print(f"[Sparkline] Error: {e}")

    def _update_top5_processes(self):
        """Update TOP 5 process panels with animation"""
        try:
            if self.data_manager and hasattr(self.data_manager, "get_latest_snapshot"):
                snapshot = self.data_manager.get_latest_snapshot()
                if snapshot:
                    user_procs = snapshot.get("user_processes", [])
                    system_procs = snapshot.get("system_processes", [])

                    self._render_expanded_user_processes(user_procs[:5])
                    self._render_expanded_system_processes(system_procs[:5])
            elif psutil is not None:
                # Fallback: get processes directly
                procs = []
                for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_info']):
                    try:
                        info = proc.info
                        mem_info = info.get("memory_info")
                        ram_mb = mem_info.rss / (1024 * 1024) if mem_info else 0
                        procs.append({
                            "name": info.get("name", "unknown"),
                            "cpu_percent": info.get("cpu_percent", 0) or 0,
                            "ram_MB": ram_mb
                        })
                    except:
                        pass

                # Sort by CPU
                procs.sort(key=lambda x: x["cpu_percent"], reverse=True)

                # Split into user/system (simple heuristic)
                user_procs = [p for p in procs if not p["name"].lower().startswith(("system", "svchost", "dwm"))]
                system_procs = [p for p in procs if p["name"].lower().startswith(("system", "svchost", "dwm"))]

                self._render_expanded_user_processes(user_procs[:5])
                self._render_expanded_system_processes(system_procs[:5])
        except Exception as e:
            print(f"[ExpandedMode] Error updating processes: {e}")

    # ========== OVERLAY MINI-MONITOR (ALWAYS-ON-TOP) ==========

    def _launch_overlay_monitor(self):
        """Launch always-on-top overlay monitor as a Toplevel (separate desktop window)"""
        try:
            from ui.overlay_mini_monitor import launch_overlay_in_main_tk
            self._overlay = launch_overlay_in_main_tk(self.root, monitor=self.monitor)
        except Exception as e:
            print(f"[OverlayMonitor] Launch error: {e}")

    # ========== SIDEBAR NAVIGATION ==========
    # Sidebar is now built in _build_ui() using SidebarNav component

    # ========== OVERLAY PANEL SYSTEM ==========

    def _show_overlay(self, page_id):
        """Show overlay panel with smooth animation - OVERLAY MODE (doesn't push content)"""
        if self.active_overlay == page_id and self.overlay_frame:
            # Already showing this page, close it
            self._close_overlay()
            return

        # Close existing overlay if any
        if self.overlay_frame:
            self._close_overlay()

        # Create overlay frame - FULL CONTENT AREA (except header)
        # Content area is 980px wide (1160 - 180 sidebar)
        self.overlay_frame = tk.Frame(self.content_area, bg="#0f1117", relief="flat", bd=0)
        self.overlay_frame.place(x=980, y=60, width=980, height=515)

        # Build page content
        self._build_overlay_content(page_id)

        # Animate slide-in from right - COVERS CONTENT AREA
        self._animate_overlay_slide(980, 0, page_id)

    def _animate_overlay_slide(self, start_x, end_x, page_id):
        """Smooth slide animation for overlay"""
        start_time = time.time()
        duration_ms = 250

        def ease_out_cubic(t):
            return 1 - pow(1 - t, 3)

        def anim():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)
            eased = ease_out_cubic(progress)
            current_x = int(start_x + (end_x - start_x) * eased)

            if self.overlay_frame:
                self.overlay_frame.place_configure(x=current_x)

            if progress >= 1.0:
                self.active_overlay = page_id
                return

            self.root.after(16, anim)

        anim()

    def _close_overlay(self):
        """Close overlay with slide-out animation - FULL SCREEN"""
        if not self.overlay_frame:
            return

        start_x = 0  # Start from left edge (full screen)
        end_x = 980  # Slide out to right
        start_time = time.time()
        duration_ms = 200

        def ease_in_cubic(t):
            return pow(t, 3)

        def anim():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)
            eased = ease_in_cubic(progress)
            current_x = int(start_x + (end_x - start_x) * eased)

            if self.overlay_frame:
                self.overlay_frame.place_configure(x=current_x)

            if progress >= 1.0:
                if self.overlay_frame:
                    self.overlay_frame.destroy()
                    self.overlay_frame = None
                self.active_overlay = None
                return

            self.root.after(16, anim)

        anim()

    def _build_overlay_content(self, page_id):
        """Build content for overlay panel"""
        # Header with close button
        header = tk.Frame(self.overlay_frame, bg="#1a1d24", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Close button (X)
        close_btn = tk.Label(
            header,
            text="✕",
            font=("Segoe UI", 18, "bold"),
            bg="#1a1d24",
            fg="#64748b",
            cursor="hand2",
            padx=15
        )
        close_btn.pack(side="right", pady=10)
        close_btn.bind("<Button-1>", lambda e: self._close_overlay())

        # Hover effect for close button
        def on_enter_close(e):
            close_btn.config(fg="#ef4444")
        def on_leave_close(e):
            close_btn.config(fg="#64748b")
        close_btn.bind("<Enter>", on_enter_close)
        close_btn.bind("<Leave>", on_leave_close)

        # Dashboard Back! button (LEFT of X)
        back_btn = tk.Label(
            header,
            text="⬅ Dashboard",
            font=("Segoe UI", 9, "bold"),
            bg="#1a1d24",
            fg="#64748b",
            cursor="hand2",
            padx=10
        )
        back_btn.pack(side="right", pady=10, padx=(0, 5))  # 5px gap from X
        back_btn.bind("<Button-1>", lambda e: self._close_overlay())

        # Hover effect for back button
        def on_enter_back(e):
            back_btn.config(fg="#8b5cf6")
        def on_leave_back(e):
            back_btn.config(fg="#64748b")
        back_btn.bind("<Enter>", on_enter_back)
        back_btn.bind("<Leave>", on_leave_back)

        # Title
        title_map = {
            "your_pc": "💻 My PC - Hardware & Health",
            "sensors": "📡 MONITORING — Centrum",
            "live_graphs": "💻 My PC - Hardware & Health",
            "optimization": "⚡ System Optimization",
            "statistics": "📊 Detailed Statistics",
            "fan_control": "🌀 Fan Dashboard",
            "fans_hardware": "❊ FANS - Hardware Info",
            "fans_usage_stats": "📊 Usage Statistics",
            "hck_labs": "🚀 HCK Labs",
            "guide": "📖 Program Guide"
        }

        title_text = title_map.get(page_id, "Page")
        title = tk.Label(
            header,
            text=title_text,
            font=("Segoe UI", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        )
        title.pack(side="left", padx=20, pady=10)

        # Content area with scrollbar
        content_frame = tk.Frame(self.overlay_frame, bg="#0f1117")
        content_frame.pack(fill="both", expand=True)

        # Build specific page content
        if page_id == "your_pc":
            build_yourpc_page(self, content_frame)  # Use helper module
        elif page_id == "sensors":
            self._build_monitoring_sensors_page(content_frame)
        elif page_id == "live_graphs":
            build_yourpc_page(self, content_frame)
            content_frame.after(180, _open_hw_table_popup, self.root)
        elif page_id == "optimization":
            self._build_optimization_page(content_frame)
        elif page_id == "statistics":
            self._build_statistics_page(content_frame)
        elif page_id == "fan_control":
            self._build_fancontrol_page(content_frame)
        elif page_id == "fans_hardware":
            create_fans_hardware_page(content_frame, self.monitor)
        elif page_id == "fans_usage_stats":
            create_fans_usage_stats_page(content_frame, self.monitor)
        elif page_id == "hck_labs":
            self._build_hcklabs_page(content_frame)
        elif page_id == "guide":
            self._build_guide_page(content_frame)

    # ========== PAGE BUILDERS ==========

    def _build_monitoring_sensors_page(self, parent):
        """MONITORING — Centrum: loads Monitoring & Alerts page"""
        try:
            from ui.pages.monitoring_alerts import build_monitoring_alerts_page
            build_monitoring_alerts_page(self, parent)
        except Exception as e:
            import traceback
            tk.Label(parent, text=f"Monitoring page error:\n{e}",
                     font=("Segoe UI", 10), bg="#0f1117", fg="#ef4444",
                     justify="left").pack(anchor="nw", padx=20, pady=20)
            traceback.print_exc()

    def _build_live_graphs_page(self, parent):
        """AllMonitor — opens My PC overlay then immediately shows HW table popup"""
        # Close current overlay, open your_pc, then trigger table popup
        self._close_overlay()
        self._show_overlay("your_pc")
        # After overlay is built, fire the table popup
        self.root.after(150, _launch_hw_table_window_root, self.root)

    def _build_optimization_page(self, parent):
        """Build Optimization page - System optimization recommendations"""
        # Scrollable container
        canvas = tk.Canvas(parent, bg="#0f1117", highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#0f1117")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Get current stats for recommendations
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1) if psutil else 0
            ram_percent = psutil.virtual_memory().percent if psutil else 0
        except:
            cpu_percent, ram_percent = 0, 0

        # Recommendations based on usage
        recommendations = []

        if cpu_percent > 80:
            recommendations.append({
                "title": "⚠️ High CPU Usage Detected",
                "severity": "warning",
                "tips": [
                    "Close unused applications and browser tabs",
                    "Check Task Manager for resource-heavy processes",
                    "Consider upgrading CPU for better performance"
                ]
            })
        else:
            recommendations.append({
                "title": "✅ CPU Performance - Good",
                "severity": "good",
                "tips": [
                    "Current CPU usage is healthy",
                    "Keep monitoring heavy applications",
                    "Regular maintenance keeps performance optimal"
                ]
            })

        if ram_percent > 85:
            recommendations.append({
                "title": "⚠️ High RAM Usage Detected",
                "severity": "warning",
                "tips": [
                    "Close unused applications to free memory",
                    "Consider adding more RAM",
                    "Restart computer to clear memory leaks"
                ]
            })
        else:
            recommendations.append({
                "title": "✅ RAM Usage - Optimal",
                "severity": "good",
                "tips": [
                    f"Using {ram_percent:.1f}% of available memory",
                    "Memory management is efficient",
                    "No immediate action needed"
                ]
            })

        # General optimization tips
        recommendations.append({
            "title": "💡 General Optimization Tips",
            "severity": "info",
            "tips": [
                "Regularly update Windows and drivers",
                "Run disk cleanup to free space",
                "Disable startup programs you don't need",
                "Keep your system cool with proper ventilation",
                "Consider SSD upgrade for faster performance"
            ]
        })

        # Render recommendations
        severity_colors = {
            "warning": "#f59e0b",
            "good": "#10b981",
            "info": "#3b82f6"
        }

        for rec in recommendations:
            # Section frame
            section_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
            section_frame.pack(fill="x", padx=10, pady=8)

            color = severity_colors.get(rec["severity"], "#64748b")

            # Header
            header = tk.Frame(section_frame, bg=color, height=40)
            header.pack(fill="x")
            header.pack_propagate(False)

            title_lbl = tk.Label(
                header,
                text=rec["title"],
                font=("Segoe UI", 12, "bold"),
                bg=color,
                fg="#ffffff"
            )
            title_lbl.pack(side="left", padx=15, pady=8)

            # Tips
            for tip in rec["tips"]:
                tip_frame = tk.Frame(section_frame, bg="#1a1d24")
                tip_frame.pack(fill="x", padx=15, pady=3)

                bullet = tk.Label(
                    tip_frame,
                    text="•",
                    font=("Segoe UI", 12, "bold"),
                    bg="#1a1d24",
                    fg=color
                )
                bullet.pack(side="left", padx=(5, 10))

                tip_lbl = tk.Label(
                    tip_frame,
                    text=tip,
                    font=("Segoe UI", 10),
                    bg="#1a1d24",
                    fg="#94a3b8",
                    anchor="w",
                    wraplength=480,
                    justify="left"
                )
                tip_lbl.pack(side="left", fill="x", expand=True)

            # Bottom padding
            tk.Frame(section_frame, bg="#1a1d24", height=10).pack()

    def _build_statistics_page(self, parent):
        """Build Statistics page"""
        tk.Label(
            parent,
            text="📊 STATISTICS\n\nDetailed stats coming soon...",
            font=("Segoe UI", 12),
            bg="#0f1117",
            fg="#64748b",
            justify="center"
        ).pack(expand=True)

    def _build_hcklabs_page(self, parent):
        """HCK Labs — minimalist blog style"""
        BG      = "#080b10"
        CARD    = "#0e1118"
        BORDER  = "#181d2e"
        TEXT    = "#e2e8f0"
        MUTED   = "#475569"
        DIM     = "#94a3b8"
        AMBER   = "#f59e0b"
        EMERALD = "#10b981"
        VIOLET  = "#8b5cf6"
        BLUE    = "#3b82f6"

        # ── scrollable container ─────────────────────────────────────────────
        cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=cv.yview,
                          bg=BG, troughcolor=BG, width=5)
        sf = tk.Frame(cv, bg=BG)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        win_id = cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>", lambda e: cv.itemconfig(win_id, width=e.width))
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        # ── HERO ─────────────────────────────────────────────────────────────
        hero = tk.Frame(sf, bg=CARD)
        hero.pack(fill="x")
        tk.Frame(hero, bg=AMBER, height=3).pack(fill="x")

        hero_inner = tk.Frame(hero, bg=CARD)
        hero_inner.pack(fill="x", padx=32, pady=(28, 24))

        tk.Label(hero_inner, text="HCK_Labs", font=("Segoe UI Light", 30),
                 bg=CARD, fg=TEXT, anchor="w").pack(anchor="w")
        tk.Label(hero_inner, text="Engineering · Monitoring · Intelligence",
                 font=("Segoe UI", 11), bg=CARD, fg=MUTED, anchor="w").pack(anchor="w", pady=(2, 14))

        # Quick action row
        btn_row = tk.Frame(hero_inner, bg=CARD)
        btn_row.pack(anchor="w")

        def _make_hero_btn(p, label, color, cmd):
            b = tk.Label(p, text=label, font=("Segoe UI Semibold", 9, "bold"),
                         bg=color, fg="#000000" if color in (AMBER, EMERALD) else "#ffffff",
                         padx=16, pady=7, cursor="hand2")
            b.pack(side="left", padx=(0, 10))
            b.bind("<Button-1>", lambda e: cmd())
            return b

        _make_hero_btn(btn_row, "🔧 Services", VIOLET,
                       lambda: self._show_services_dialog(sf))
        _make_hero_btn(btn_row, "🔄 Check Update", EMERALD,
                       lambda: self._show_update_dialog(sf))

        tk.Frame(hero, bg=BORDER, height=1).pack(fill="x")

        # ── ABOUT (2-col grid) ───────────────────────────────────────────────
        def _section(title, subtitle=None):
            wrap = tk.Frame(sf, bg=BG)
            wrap.pack(fill="x", padx=24, pady=(22, 0))
            tk.Label(wrap, text=title, font=("Segoe UI Semibold", 13, "bold"),
                     bg=BG, fg=TEXT, anchor="w").pack(anchor="w")
            if subtitle:
                tk.Label(wrap, text=subtitle, font=("Segoe UI", 9),
                         bg=BG, fg=MUTED, anchor="w").pack(anchor="w", pady=(1, 0))
            tk.Frame(wrap, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))
            return wrap

        def _card(parent, accent, title, body):
            frame = tk.Frame(parent, bg=CARD)
            frame.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
            tk.Frame(frame, bg=accent, height=3).pack(fill="x")
            inner = tk.Frame(frame, bg=CARD)
            inner.pack(fill="both", expand=True, padx=14, pady=12)
            tk.Label(inner, text=title, font=("Segoe UI Semibold", 10, "bold"),
                     bg=CARD, fg=TEXT, anchor="w").pack(anchor="w")
            tk.Label(inner, text=body, font=("Segoe UI", 9), bg=CARD, fg=DIM,
                     anchor="w", justify="left", wraplength=280).pack(anchor="w", pady=(4, 0))

        _section("About", "What PC_Workman is and why it exists")
        about_row = tk.Frame(sf, bg=BG)
        about_row.pack(fill="x", padx=24)
        _card(about_row, BLUE, "Mission",
              "Make system monitoring accessible, beautiful, and intelligent for everyone — not just power users.")
        _card(about_row, VIOLET, "Inspiration",
              "Designed with learnings from Tesla UI, Apple macOS, and MSI Afterburner. Calm, dense, and fast.")
        _card(about_row, EMERALD, "Philosophy",
              "Local-first. No cloud. No telemetry. Everything runs on your machine — configure once, runs forever.")

        # ── FEATURES GRID ───────────────────────────────────────────────────
        _section("What makes it different")
        features = [
            (AMBER,   "Dual-Mode",        "Minimal widget + full control center — switch instantly"),
            (VIOLET,  "HCK_GPT",          "Local AI insights, habit tracking, anomaly alerts — no API key"),
            (BLUE,    "Stats Engine v2",   "SQLite pipeline: minute → hourly → daily → monthly retention"),
            (EMERALD, "Auto Optimization", "RAM flush, DNS cache, temp files, process priority — automated & silent"),
            ("#ef4444","Time-Travel Stats","Click any historical point to see what was running then"),
            (DIM,     "Universal HW",      "All CPUs, all GPUs, all configs — no driver dependencies"),
        ]
        grid_outer = tk.Frame(sf, bg=BG)
        grid_outer.pack(fill="x", padx=24)
        row_frame = None
        for i, (accent, title, body) in enumerate(features):
            if i % 3 == 0:
                row_frame = tk.Frame(grid_outer, bg=BG)
                row_frame.pack(fill="x")
            _card(row_frame, accent, title, body)

        # ── COMPARE TABLE ───────────────────────────────────────────────────
        _section("vs Competition")
        comp_wrap = tk.Frame(sf, bg=BG)
        comp_wrap.pack(fill="x", padx=24, pady=(8, 0))

        rows = [
            ("vs MSI Afterburner",    "Full system, not just GPU"),
            ("vs GeForce Experience", "All GPUs · no forced login · lightweight"),
            ("vs HWMonitor",          "Actionable insights, not just read-only numbers"),
            ("vs Task Manager",       "AI suggestions · historical trends · auto-optimization"),
        ]
        for i, (vs, advantage) in enumerate(rows):
            bg_row = CARD if i % 2 == 0 else "#0a0d13"
            r = tk.Frame(comp_wrap, bg=bg_row)
            r.pack(fill="x")
            tk.Label(r, text=vs, font=("Segoe UI Semibold", 9, "bold"),
                     bg=bg_row, fg=BLUE, width=24, anchor="w").pack(side="left", padx=16, pady=8)
            tk.Label(r, text="→  " + advantage, font=("Segoe UI", 9),
                     bg=bg_row, fg=DIM).pack(side="left", padx=4, pady=8)

        # ── VERSION FOOTER ───────────────────────────────────────────────────
        _section("Build info")
        footer = tk.Frame(sf, bg=CARD)
        footer.pack(fill="x", padx=24, pady=(8, 32))
        pairs = [
            ("Version", "PC_Workman HCK 1.7.2"),
            ("Engine", "Stats Engine v2 — SQLite WAL"),
            ("Runtime", "Python 3.9+ / tkinter"),
            ("License", "MIT — HCK_Labs"),
        ]
        for label, val in pairs:
            r = tk.Frame(footer, bg=CARD)
            r.pack(fill="x", padx=16, pady=3)
            tk.Label(r, text=label, font=("Segoe UI", 9), bg=CARD,
                     fg=MUTED, width=12, anchor="w").pack(side="left")
            tk.Label(r, text=val, font=("Segoe UI Semibold", 9), bg=CARD,
                     fg=TEXT).pack(side="left", padx=8)
        tk.Frame(footer, bg=BG, height=8).pack(fill="x")

    def _build_fancontrol_page(self, parent):
        """Build fan dashboard page."""
        main = tk.Frame(parent, bg="#0f1117")
        main.pack(fill="both", expand=True)

        # No "Dashboard Back!" button - only X button in top-right corner
        # This saves space and is cleaner!

        # Fan dashboard container
        dashboard_container = tk.Frame(main, bg="#0f1117")
        dashboard_container.pack(fill="both", expand=True)

        # Create fan dashboard
        self.fan_dashboard = create_fan_dashboard(dashboard_container)

        # Store reference for updates
        if not hasattr(self, '_fan_dashboards'):
            self._fan_dashboards = []
        self._fan_dashboards.append(self.fan_dashboard)

        # Start real-time updates (every 2 seconds)
        def update_fan_dashboard():
            try:
                if hasattr(self, 'fan_dashboard'):
                    self.fan_dashboard.update_realtime()
                parent.after(2000, update_fan_dashboard)  # 2s interval
            except:
                pass  # Stop if widget destroyed

        update_fan_dashboard()

    def _build_pc2d_graphic_in_yourpc(self, parent):
        """Build 2D PC case graphic with components - for Your PC Components tab"""
        self._build_pc2d_graphic(parent)

    def _build_pc2d_graphic(self, parent):
        """Build 2D PC case graphic with components - ETAP 2"""
        # Get live hardware data
        hw_data = self._get_hardware_data()

        # Main canvas for PC graphic
        canvas = tk.Canvas(parent, bg="#0a0e27", highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=10, pady=10)

        # Wait for canvas to be visible to get dimensions
        parent.update_idletasks()
        canvas_width = canvas.winfo_width() if canvas.winfo_width() > 1 else 500
        canvas_height = canvas.winfo_height() if canvas.winfo_height() > 1 else 400

        # PC case outline (centered)
        case_x = canvas_width // 2 - 150
        case_y = 30
        case_width = 300
        case_height = 340

        # Draw PC case outline
        canvas.create_rectangle(
            case_x, case_y, case_x + case_width, case_y + case_height,
            outline="#475569", width=2, fill="#0f172a"
        )

        # Title at top
        canvas.create_text(
            canvas_width // 2, 15,
            text="🖥️ PC COMPONENTS OVERVIEW",
            font=("Segoe UI", 10, "bold"),
            fill="#64748b"
        )

        # Component positions (relative to case)
        components = [
            # CPU (top-center with cooler)
            {
                "name": "CPU",
                "model": hw_data["cpu_model"],
                "temp": hw_data["cpu_temp"],
                "x": case_x + 150,
                "y": case_y + 60,
                "width": 80,
                "height": 60,
                "color": "#3b82f6",
                "info_side": "left"
            },
            # GPU (middle-center, larger)
            {
                "name": "GPU",
                "model": hw_data["gpu_model"],
                "temp": hw_data["gpu_temp"],
                "x": case_x + 140,
                "y": case_y + 160,
                "width": 100,
                "height": 70,
                "color": "#10b981",
                "info_side": "right"
            },
            # RAM (top-left, vertical modules)
            {
                "name": "RAM",
                "model": hw_data["ram_model"],
                "temp": hw_data["ram_temp"],
                "x": case_x + 40,
                "y": case_y + 40,
                "width": 20,
                "height": 80,
                "color": "#fbbf24",
                "info_side": "left"
            },
            # Motherboard (background label)
            {
                "name": "MOBO",
                "model": hw_data["mobo_model"],
                "temp": hw_data["mobo_temp"],
                "x": case_x + 150,
                "y": case_y + 290,
                "width": 120,
                "height": 30,
                "color": "#8b5cf6",
                "info_side": "bottom"
            },
            # PSU (bottom)
            {
                "name": "PSU",
                "model": hw_data["psu_model"],
                "temp": hw_data["psu_temp"],
                "x": case_x + 100,
                "y": case_y + 280,
                "width": 80,
                "height": 40,
                "color": "#64748b",
                "info_side": "bottom"
            },
            # Storage (front bay)
            {
                "name": "DISK",
                "model": hw_data["disk_model"],
                "temp": hw_data["disk_temp"],
                "x": case_x + 250,
                "y": case_y + 90,
                "width": 30,
                "height": 50,
                "color": "#06b6d4",
                "info_side": "right"
            }
        ]

        # Draw each component with info box
        for comp in components:
            # Draw component rectangle
            canvas.create_rectangle(
                comp["x"] - comp["width"]//2,
                comp["y"] - comp["height"]//2,
                comp["x"] + comp["width"]//2,
                comp["y"] + comp["height"]//2,
                outline=comp["color"],
                width=2,
                fill="#1e293b"
            )

            # Component label
            canvas.create_text(
                comp["x"], comp["y"],
                text=comp["name"],
                font=("Segoe UI", 7, "bold"),
                fill=comp["color"]
            )

            # Create info box with connection line
            self._create_component_info_box(canvas, comp, canvas_width, case_x, case_y, case_width, case_height)

        # Draw case fans (4 positions on sides)
        fan_positions = [
            {"x": case_x + 10, "y": case_y + 100, "label": "F1"},
            {"x": case_x + 10, "y": case_y + 200, "label": "F2"},
            {"x": case_x + case_width - 10, "y": case_y + 100, "label": "F3"},
            {"x": case_x + case_width - 10, "y": case_y + 200, "label": "F4"}
        ]

        for fan in fan_positions:
            # Small fan circle
            canvas.create_oval(
                fan["x"] - 8, fan["y"] - 8,
                fan["x"] + 8, fan["y"] + 8,
                outline="#8b5cf6", width=1, fill="#0f172a"
            )
            canvas.create_text(
                fan["x"], fan["y"],
                text=fan["label"],
                font=("Consolas", 6),
                fill="#8b5cf6"
            )

    def _get_hardware_data(self):
        """Get live hardware data for 2D graphic"""
        data = {}

        # CPU
        try:
            import platform
            cpu_full = platform.processor()
            # Shorten CPU name
            cpu_parts = cpu_full.split()
            if "Intel" in cpu_full:
                # Extract core name (e.g., "i7-9700K")
                cpu_model = next((p for p in cpu_parts if p.startswith("i") or "-" in p), cpu_full[:20])
            elif "AMD" in cpu_full:
                cpu_model = next((p for p in cpu_parts if "Ryzen" in p or "-" in p), cpu_full[:20])
            else:
                cpu_model = cpu_full[:20]
            data["cpu_model"] = cpu_model
            data["cpu_temp"] = 30 + (psutil.cpu_percent(interval=0.1) * 0.6) if psutil else 40
        except:
            data["cpu_model"] = "Unknown CPU"
            data["cpu_temp"] = 40

        # RAM
        try:
            ram_gb = psutil.virtual_memory().total / (1024**3) if psutil else 0
            data["ram_model"] = f"{ram_gb:.0f}GB DDR4"
            data["ram_temp"] = 35
        except:
            data["ram_model"] = "Unknown RAM"
            data["ram_temp"] = 35

        # GPU
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_name = gpus[0].name
                # Shorten GPU name
                if "NVIDIA" in gpu_name:
                    gpu_name = gpu_name.replace("NVIDIA GeForce", "").strip()
                elif "AMD" in gpu_name:
                    gpu_name = gpu_name.replace("AMD Radeon", "").strip()
                data["gpu_model"] = gpu_name[:20]
                data["gpu_temp"] = gpus[0].temperature if hasattr(gpus[0], 'temperature') else 45
            else:
                data["gpu_model"] = "Unknown GPU"
                data["gpu_temp"] = 45
        except:
            data["gpu_model"] = "Unknown GPU"
            data["gpu_temp"] = 45

        # Motherboard
        try:
            import wmi
            w = wmi.WMI()
            mobo = w.Win32_BaseBoard()[0]
            data["mobo_model"] = f"{mobo.Manufacturer} {mobo.Product}"[:25]
            data["mobo_temp"] = 38
        except:
            data["mobo_model"] = "Unknown Motherboard"
            data["mobo_temp"] = 38

        # PSU (simulated)
        data["psu_model"] = "650W 80+ Gold"
        data["psu_temp"] = 42

        # Disk
        try:
            import psutil
            disks = psutil.disk_partitions()
            if disks:
                disk_usage = psutil.disk_usage(disks[0].mountpoint)
                total_gb = disk_usage.total / (1024**3)
                data["disk_model"] = f"{total_gb:.0f}GB SSD"
            else:
                data["disk_model"] = "Unknown Disk"
            data["disk_temp"] = 35
        except:
            data["disk_model"] = "Unknown Disk"
            data["disk_temp"] = 35

        return data

    def _create_component_info_box(self, canvas, comp, canvas_width, case_x, case_y, case_width, case_height):
        """Create info box with connection line for component"""
        # Info box dimensions
        box_width = 140
        box_height = 50

        # Position info box based on side
        if comp["info_side"] == "left":
            box_x = 20
            box_y = comp["y"] - box_height // 2
        elif comp["info_side"] == "right":
            box_x = canvas_width - box_width - 20
            box_y = comp["y"] - box_height // 2
        elif comp["info_side"] == "bottom":
            box_x = comp["x"] - box_width // 2
            box_y = case_y + case_height + 20
        else:
            box_x = 20
            box_y = comp["y"]

        # Ensure box stays within canvas bounds
        box_y = max(10, min(box_y, canvas.winfo_height() - box_height - 10))

        # Draw connection line
        line_color = comp["color"] + "80"  # Add transparency
        canvas.create_line(
            comp["x"], comp["y"],
            box_x + (box_width // 2 if comp["info_side"] == "bottom" else (0 if comp["info_side"] == "left" else box_width)),
            box_y + box_height // 2,
            fill=comp["color"],
            width=1,
            dash=(2, 2)
        )

        # Draw info box background
        canvas.create_rectangle(
            box_x, box_y,
            box_x + box_width, box_y + box_height,
            fill="#1a1d24",
            outline=comp["color"],
            width=1
        )

        # Component name header
        canvas.create_text(
            box_x + box_width // 2,
            box_y + 10,
            text=f"{comp['name']}:",
            font=("Segoe UI", 7, "bold"),
            fill=comp["color"]
        )

        # Model name
        canvas.create_text(
            box_x + box_width // 2,
            box_y + 24,
            text=comp["model"][:25],
            font=("Consolas", 6),
            fill="#e2e8f0"
        )

        # Temperature
        temp_color = "#10b981" if comp["temp"] < 50 else ("#fbbf24" if comp["temp"] < 70 else "#ef4444")
        canvas.create_text(
            box_x + box_width // 2,
            box_y + 36,
            text=f"🌡️ {comp['temp']:.1f}°C",
            font=("Consolas", 6),
            fill=temp_color
        )

        # Info button (ℹ️)
        info_btn_x = box_x + box_width - 15
        info_btn_y = box_y + 10

        info_circle = canvas.create_oval(
            info_btn_x - 6, info_btn_y - 6,
            info_btn_x + 6, info_btn_y + 6,
            fill=comp["color"],
            outline=""
        )

        info_text = canvas.create_text(
            info_btn_x, info_btn_y,
            text="i",
            font=("Segoe UI", 8, "bold"),
            fill="#ffffff"
        )

        # Make info button clickable
        def on_info_click(event):
            self._show_component_details(comp)

        canvas.tag_bind(info_circle, "<Button-1>", on_info_click)
        canvas.tag_bind(info_text, "<Button-1>", on_info_click)
        canvas.tag_bind(info_circle, "<Enter>", lambda e: canvas.config(cursor="hand2"))
        canvas.tag_bind(info_text, "<Enter>", lambda e: canvas.config(cursor="hand2"))
        canvas.tag_bind(info_circle, "<Leave>", lambda e: canvas.config(cursor=""))
        canvas.tag_bind(info_text, "<Leave>", lambda e: canvas.config(cursor=""))

    def _show_component_details(self, comp):
        """Show detailed component information in popup"""
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title(f"{comp['name']} Details")
        popup.geometry("400x300")
        popup.configure(bg="#0f1117")
        popup.resizable(False, False)

        # Center popup
        popup.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 150
        popup.geometry(f"400x300+{x}+{y}")

        # Header
        header = tk.Frame(popup, bg=comp["color"], height=50)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"{comp['name']} - Detailed Information",
            font=("Segoe UI", 12, "bold"),
            bg=comp["color"],
            fg="#ffffff"
        ).pack(pady=15)

        # Content
        content = tk.Frame(popup, bg="#0f1117")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        details = [
            ("Component Type:", comp["name"]),
            ("Model:", comp["model"]),
            ("Temperature:", f"{comp['temp']:.1f}°C"),
            ("Status:", "Operational" if comp["temp"] < 80 else "High Temperature"),
            ("Health:", "✓ Good" if comp["temp"] < 70 else "⚠ Check Cooling")
        ]

        for label, value in details:
            row = tk.Frame(content, bg="#0f1117")
            row.pack(fill="x", pady=5)

            tk.Label(
                row,
                text=label,
                font=("Segoe UI", 9, "bold"),
                bg="#0f1117",
                fg="#94a3b8",
                width=18,
                anchor="w"
            ).pack(side="left")

            tk.Label(
                row,
                text=value,
                font=("Consolas", 9),
                bg="#0f1117",
                fg="#e2e8f0",
                anchor="w"
            ).pack(side="left", padx=10)

        # Close button
        close_btn = tk.Label(
            popup,
            text="✕ Close",
            font=("Segoe UI", 10, "bold"),
            bg="#1e293b",
            fg="#94a3b8",
            cursor="hand2",
            padx=20,
            pady=8
        )
        close_btn.pack(pady=(0, 15))
        close_btn.bind("<Button-1>", lambda e: popup.destroy())

        # Hover effect
        def on_enter(e):
            close_btn.config(bg="#334155", fg="#e2e8f0")
        def on_leave(e):
            close_btn.config(bg="#1e293b", fg="#94a3b8")
        close_btn.bind("<Enter>", on_enter)
        close_btn.bind("<Leave>", on_leave)

    def _build_advanced_dashboard(self, parent):
        """Build Advanced Dashboard widget layout."""
        # Scrollable container
        canvas = tk.Canvas(parent, bg="#0a0e27", highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg="#0a0e27")

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # === REAL-TIME FAN USAGE GRAPH ===
        graph_frame = tk.Frame(scrollable, bg="#1a1d24")
        graph_frame.pack(fill="x", padx=10, pady=(5, 15))

        # Graph header
        tk.Label(
            graph_frame,
            text="REAL-TIME FAN USAGE",
            font=("Segoe UI", 9, "bold"),
            bg="#1a1d24",
            fg="#8b5cf6"
        ).pack(pady=(10, 5))

        # Graph canvas - gradient from yellow to green
        graph_canvas = tk.Canvas(graph_frame, bg="#0f1117", height=80, highlightthickness=0)
        graph_canvas.pack(fill="x", padx=15, pady=(0, 10))

        # Get real fan data
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1) if psutil else 50
        except:
            cpu_usage = 50

        # Draw gradient bar (usage percentage)
        bar_width = 400  # Fixed width for now
        bar_height = 50
        bar_x = 40
        bar_y = 15

        # Background
        graph_canvas.create_rectangle(bar_x, bar_y, bar_x + bar_width, bar_y + bar_height, fill="#1e293b", outline="")

        # Gradient fill (yellow -> green based on usage)
        usage_width = int((cpu_usage / 100) * bar_width)
        if usage_width > 0:
            # Create gradient effect with multiple rectangles
            segments = 20
            for i in range(segments):
                seg_width = usage_width / segments
                seg_x = bar_x + (i * seg_width)

                # Color interpolation yellow (#fbbf24) -> green (#10b981)
                ratio = i / segments
                r = int(251 * (1 - ratio) + 16 * ratio)
                g = int(191 * (1 - ratio) + 185 * ratio)
                b = int(36 * (1 - ratio) + 129 * ratio)
                color = f"#{r:02x}{g:02x}{b:02x}"

                graph_canvas.create_rectangle(
                    seg_x, bar_y, seg_x + seg_width + 1, bar_y + bar_height,
                    fill=color, outline=""
                )

        # Usage text overlay
        graph_canvas.create_text(
            bar_x + bar_width // 2, bar_y + bar_height // 2,
            text=f"{cpu_usage:.1f}%",
            font=("Segoe UI", 16, "bold"),
            fill="#ffffff"
        )

        # Labels
        tk.Label(
            graph_frame,
            text="Current CPU Load (Fan responds to temperature)",
            font=("Segoe UI", 7),
            bg="#1a1d24",
            fg="#94a3b8"
        ).pack(pady=(0, 10))

        # === TOP 3 OPTIONS (horizontal row) ===
        top_options_frame = tk.Frame(scrollable, bg="#0a0e27")
        top_options_frame.pack(fill="x", padx=10, pady=(0, 10))

        top_options = [
            {
                "title": "🎯 Fan Curve Profile",
                "description": "Choose speed curve",
                "choices": ["Silent", "Balanced", "Performance", "Custom"],
                "default": "Balanced"
            },
            {
                "title": "🌡️ Temperature Target",
                "description": "Target temperature",
                "choices": ["60°C", "70°C", "75°C", "80°C"],
                "default": "70°C"
            },
            {
                "title": "🚀 Max Fan Speed",
                "description": "Maximum speed limit",
                "choices": ["80%", "90%", "100%"],
                "default": "100%"
            }
        ]

        for opt in top_options:
            self._create_fan_option_card_compact(top_options_frame, opt, horizontal=True)

        # === BOTTOM OPTIONS (2 rows of 2) ===
        bottom_row1 = tk.Frame(scrollable, bg="#0a0e27")
        bottom_row1.pack(fill="x", padx=10, pady=(0, 5))

        bottom_row2 = tk.Frame(scrollable, bg="#0a0e27")
        bottom_row2.pack(fill="x", padx=10, pady=(0, 10))

        bottom_options = [
            {
                "title": "⚡ PWM Mode",
                "description": "Control method",
                "choices": ["PWM", "DC Mode", "Auto"],
                "default": "PWM",
                "parent": bottom_row1
            },
            {
                "title": "🔇 Min Fan Speed",
                "description": "Minimum speed",
                "choices": ["0%", "20%", "30%", "40%"],
                "default": "20%",
                "parent": bottom_row1
            },
            {
                "title": "⏱️ Response Time",
                "description": "Response speed",
                "choices": ["Fast", "Medium", "Slow"],
                "default": "Medium",
                "parent": bottom_row2
            }
        ]

        for opt in bottom_options:
            parent_frame = opt.pop("parent")
            self._create_fan_option_card_compact(parent_frame, opt, horizontal=True)

        # Save changes button
        save_btn = tk.Label(
            scrollable,
            text="💾 Save Changes",
            font=("Segoe UI", 11, "bold"),
            bg="#8b5cf6",
            fg="#ffffff",
            cursor="hand2",
            padx=40,
            pady=12
        )
        save_btn.pack(pady=(15, 20))

        def on_save(e):
            print("[Advanced Dashboard] Settings saved!")

        save_btn.bind("<Button-1>", on_save)

        # Hover effect
        def on_enter_save(e):
            save_btn.config(bg="#7c3aed")
        def on_leave_save(e):
            save_btn.config(bg="#8b5cf6")
        save_btn.bind("<Enter>", on_enter_save)
        save_btn.bind("<Leave>", on_leave_save)

    def _create_fan_option_card_compact(self, parent, option, horizontal=False):
        """Create compact fan control option card"""
        card = tk.Frame(parent, bg="#1a1d24")
        if horizontal:
            card.pack(side="left", fill="both", expand=True, padx=5)
        else:
            card.pack(fill="x", padx=15, pady=5)

        # Header with title (smaller)
        tk.Label(
            card,
            text=option["title"],
            font=("Segoe UI", 9, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        ).pack(fill="x", padx=10, pady=(8, 2))

        # Description (smaller)
        tk.Label(
            card,
            text=option["description"],
            font=("Segoe UI", 7),
            bg="#1a1d24",
            fg="#94a3b8",
            anchor="w"
        ).pack(fill="x", padx=10, pady=(0, 6))

        # Choices - horizontal buttons (smaller)
        choices_frame = tk.Frame(card, bg="#1a1d24")
        choices_frame.pack(fill="x", padx=10, pady=(0, 8))

        for choice in option["choices"]:
            is_default = (choice == option["default"])
            btn_bg = "#8b5cf6" if is_default else "#334155"
            btn_fg = "#ffffff" if is_default else "#94a3b8"

            choice_btn = tk.Label(
                choices_frame,
                text=choice,
                font=("Segoe UI", 7, "bold"),
                bg=btn_bg,
                fg=btn_fg,
                cursor="hand2",
                padx=8,
                pady=4
            )
            choice_btn.pack(side="left", padx=1)

            # Click handler
            def make_click_handler(btn, opt_title, ch):
                def on_click(e):
                    print(f"[Dashboard] {opt_title}: {ch}")
                    for widget in choices_frame.winfo_children():
                        widget.config(bg="#334155", fg="#94a3b8")
                    btn.config(bg="#8b5cf6", fg="#ffffff")
                return on_click

            choice_btn.bind("<Button-1>", make_click_handler(choice_btn, option["title"], choice))

            # Hover effect
            def make_hover(btn):
                def on_enter(e):
                    if btn.cget("bg") != "#8b5cf6":
                        btn.config(bg="#475569")
                def on_leave(e):
                    if btn.cget("bg") != "#8b5cf6":
                        btn.config(bg="#334155")
                return on_enter, on_leave

            on_enter, on_leave = make_hover(choice_btn)
            choice_btn.bind("<Enter>", on_enter)
            choice_btn.bind("<Leave>", on_leave)

    def _create_fan_option_card(self, parent, option):
        """Create fan control option card with dropdown"""
        card = tk.Frame(parent, bg="#1a1d24")
        card.pack(fill="x", padx=15, pady=5)

        # Header with title
        tk.Label(
            card,
            text=option["title"],
            font=("Segoe UI", 10, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        ).pack(fill="x", padx=10, pady=(10, 2))

        # Description
        tk.Label(
            card,
            text=option["description"],
            font=("Segoe UI", 8),
            bg="#1a1d24",
            fg="#94a3b8",
            anchor="w"
        ).pack(fill="x", padx=10, pady=(0, 8))

        # Choices - horizontal buttons
        choices_frame = tk.Frame(card, bg="#1a1d24")
        choices_frame.pack(fill="x", padx=10, pady=(0, 10))

        for choice in option["choices"]:
            is_default = (choice == option["default"])
            btn_bg = "#8b5cf6" if is_default else "#334155"
            btn_fg = "#ffffff" if is_default else "#94a3b8"

            choice_btn = tk.Label(
                choices_frame,
                text=choice,
                font=("Segoe UI", 8, "bold"),
                bg=btn_bg,
                fg=btn_fg,
                cursor="hand2",
                padx=12,
                pady=6
            )
            choice_btn.pack(side="left", padx=2)

            # Click handler
            def make_click_handler(btn, opt_title, ch):
                def on_click(e):
                    print(f"[FanControl] {opt_title}: {ch}")
                    # Update all buttons in this group
                    for widget in choices_frame.winfo_children():
                        widget.config(bg="#334155", fg="#94a3b8")
                    btn.config(bg="#8b5cf6", fg="#ffffff")
                return on_click

            choice_btn.bind("<Button-1>", make_click_handler(choice_btn, option["title"], choice))

            # Hover effect
            def make_hover(btn):
                def on_enter(e):
                    if btn.cget("bg") != "#8b5cf6":
                        btn.config(bg="#475569")
                def on_leave(e):
                    if btn.cget("bg") != "#8b5cf6":
                        btn.config(bg="#334155")
                return on_enter, on_leave

            on_enter, on_leave = make_hover(choice_btn)
            choice_btn.bind("<Enter>", on_enter)
            choice_btn.bind("<Leave>", on_leave)

    def _create_fan_display_compact(self, parent, label, rpm, percent, temp, connected):
        """Create COMPACT fan display - 50% height, 30% narrower"""
        # Title - smaller
        tk.Label(
            parent,
            text=label,
            font=("Segoe UI", 9, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(pady=(8, 3))

        # Fan graphic - SMALLER (60x60 instead of 120x120)
        fan_canvas = tk.Canvas(parent, bg="#1a1d24", width=60, height=60, highlightthickness=0)
        fan_canvas.pack(pady=5)

        # Draw fan blades (smaller)
        center_x, center_y = 30, 30
        radius = 25

        # Outer circle
        fan_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline="#8b5cf6", width=2
        )

        # Fan blades
        blade_angles = [0, 90, 180, 270]
        for angle in blade_angles:
            import math
            rad = math.radians(angle)
            end_x = center_x + radius * 0.8 * math.cos(rad)
            end_y = center_y + radius * 0.8 * math.sin(rad)
            fan_canvas.create_line(
                center_x, center_y, end_x, end_y,
                fill="#8b5cf6", width=2
            )

        # Center hub
        fan_canvas.create_oval(
            center_x - 5, center_y - 5,
            center_x + 5, center_y + 5,
            fill="#8b5cf6", outline=""
        )

        # Connection status
        if connected:
            status_text = "✓ Connected"
            status_color = "#10b981"
        else:
            status_text = "✕ Not Connected"
            status_color = "#ef4444"

        tk.Label(
            parent,
            text=status_text,
            font=("Segoe UI", 7),
            bg="#1a1d24",
            fg=status_color
        ).pack()

        # Current speed - compact
        speed_frame = tk.Frame(parent, bg="#fbbf24", height=1)
        speed_frame.pack(fill="x", padx=10, pady=(8, 3))

        tk.Label(
            parent,
            text=f"{rpm} RPM",
            font=("Consolas", 8, "bold"),
            bg="#1a1d24",
            fg="#fbbf24"
        ).pack()

        tk.Label(
            parent,
            text=f"{percent:.0f}%",
            font=("Consolas", 7),
            bg="#1a1d24",
            fg="#fbbf24"
        ).pack(pady=(0, 5))

        # Temperature - compact
        temp_frame = tk.Frame(parent, bg="#3b82f6", height=1)
        temp_frame.pack(fill="x", padx=10, pady=(3, 3))

        # Temperature color
        if temp < 50:
            temp_color = "#10b981"
        elif temp < 70:
            temp_color = "#fbbf24"
        else:
            temp_color = "#ef4444"

        tk.Label(
            parent,
            text=f"{temp:.1f}°C",
            font=("Consolas", 9, "bold"),
            bg="#1a1d24",
            fg=temp_color
        ).pack(pady=(0, 8))

    def _create_fan_display(self, parent, label, rpm, percent, temp, connected):
        """Create animated fan display with stats"""
        # Title
        tk.Label(
            parent,
            text=label,
            font=("Segoe UI", 10, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(pady=(10, 5))

        # Fan graphic (animated circle - simulated rotation)
        fan_canvas = tk.Canvas(parent, bg="#1a1d24", width=120, height=120, highlightthickness=0)
        fan_canvas.pack(pady=10)

        # Draw fan blades (4 blades in circle)
        center_x, center_y = 60, 60
        radius = 50

        # Outer circle
        fan_canvas.create_oval(
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius,
            outline="#8b5cf6", width=3
        )

        # Fan blades (4 lines from center)
        blade_angles = [0, 90, 180, 270]
        for angle in blade_angles:
            import math
            rad = math.radians(angle)
            end_x = center_x + radius * 0.8 * math.cos(rad)
            end_y = center_y + radius * 0.8 * math.sin(rad)
            fan_canvas.create_line(
                center_x, center_y, end_x, end_y,
                fill="#8b5cf6", width=3
            )

        # Center hub
        fan_canvas.create_oval(
            center_x - 10, center_y - 10,
            center_x + 10, center_y + 10,
            fill="#8b5cf6", outline=""
        )

        # Connection status
        if connected:
            status_text = "✓ Connected"
            status_color = "#10b981"
        else:
            status_text = "✕ Not Connected"
            status_color = "#ef4444"

        tk.Label(
            parent,
            text=status_text,
            font=("Segoe UI", 8),
            bg="#1a1d24",
            fg=status_color
        ).pack()

        # Current speed
        speed_frame = tk.Frame(parent, bg="#fbbf24", height=2)
        speed_frame.pack(fill="x", padx=15, pady=(15, 5))

        tk.Label(
            parent,
            text=f"Current Speed: {rpm} RPM / {percent:.0f}%",
            font=("Consolas", 9, "bold"),
            bg="#1a1d24",
            fg="#fbbf24"
        ).pack(pady=(0, 10))

        # Temperature
        temp_frame = tk.Frame(parent, bg="#3b82f6", height=2)
        temp_frame.pack(fill="x", padx=15, pady=(5, 5))

        # Temperature color based on value
        if temp < 50:
            temp_color = "#10b981"  # Green
        elif temp < 70:
            temp_color = "#fbbf24"  # Yellow
        else:
            temp_color = "#ef4444"  # Red

        tk.Label(
            parent,
            text=f"TEMP: {temp:.1f}°C",
            font=("Consolas", 11, "bold"),
            bg="#1a1d24",
            fg=temp_color
        ).pack()

    def _build_guide_page(self, parent):
        """Guide — full-width minimalist blog with live-guide button placeholder"""
        BG      = "#080b10"
        CARD    = "#0e1118"
        BORDER  = "#181d2e"
        TEXT    = "#e2e8f0"
        MUTED   = "#475569"
        DIM     = "#94a3b8"
        VIOLET  = "#8b5cf6"
        BLUE    = "#3b82f6"
        EMERALD = "#10b981"
        AMBER   = "#f59e0b"

        # ── scrollable ────────────────────────────────────────────────────────────
        cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=cv.yview,
                          bg=BG, troughcolor=BG, width=5)
        sf = tk.Frame(cv, bg=BG)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        win_id = cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>", lambda e: cv.itemconfig(win_id, width=e.width))
        cv.bind_all("<MouseWheel>", lambda e: cv.yview_scroll(int(-1*(e.delta/120)), "units"), add="+")
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        # ── HERO ─────────────────────────────────────────────────────────────────
        hero = tk.Frame(sf, bg=CARD)
        hero.pack(fill="x")
        tk.Frame(hero, bg=VIOLET, height=3).pack(fill="x")

        hero_inner = tk.Frame(hero, bg=CARD)
        hero_inner.pack(fill="x", padx=32, pady=(24, 20))

        left_hero = tk.Frame(hero_inner, bg=CARD)
        left_hero.pack(side="left", fill="both", expand=True)

        tk.Label(left_hero, text="Program Guide",
                 font=("Segoe UI Light", 28), bg=CARD, fg=TEXT, anchor="w").pack(anchor="w")
        tk.Label(left_hero, text="Everything you need to get the most out of PC_Workman",
                 font=("Segoe UI", 10), bg=CARD, fg=MUTED, anchor="w").pack(anchor="w", pady=(3, 0))

        # Live Guide button (right side of hero) — placeholder for future interactive tour
        live_btn = tk.Label(hero_inner,
                            text="▶  Guide on program LIVE",
                            font=("Segoe UI Semibold", 10, "bold"),
                            bg=VIOLET, fg="#ffffff",
                            padx=18, pady=10, cursor="hand2")
        live_btn.pack(side="right", padx=(0, 0), anchor="center")

        def _live_guide_click(e=None):
            # Close guide overlay so dashboard is visible, then launch
            self._close_overlay()
            self.root.after(280, self._start_live_guide)

        live_btn.bind("<Button-1>", _live_guide_click)
        live_btn.bind("<Enter>", lambda e: live_btn.config(bg="#7c3aed"))
        live_btn.bind("<Leave>", lambda e: live_btn.config(bg=VIOLET))

        tk.Frame(hero, bg=BORDER, height=1).pack(fill="x")

        # ── SECTION HELPER ────────────────────────────────────────────────────────
        def _section_hdr(icon, title, subtitle, accent):
            wrap = tk.Frame(sf, bg=BG)
            wrap.pack(fill="x", padx=0, pady=(0, 0))
            bar = tk.Frame(wrap, bg=accent, height=2)
            bar.pack(fill="x")
            inner = tk.Frame(wrap, bg=CARD)
            inner.pack(fill="x", padx=28, pady=14)
            tk.Label(inner, text=f"{icon}  {title}",
                     font=("Segoe UI Semibold", 13, "bold"),
                     bg=CARD, fg=TEXT, anchor="w").pack(anchor="w")
            if subtitle:
                tk.Label(inner, text=subtitle, font=("Segoe UI", 9),
                         bg=CARD, fg=MUTED, anchor="w").pack(anchor="w", pady=(1, 0))
            return wrap

        def _article(bullets, accent=DIM):
            body = tk.Frame(sf, bg=BG)
            body.pack(fill="x", padx=28, pady=(4, 18))
            for bullet in bullets:
                row = tk.Frame(body, bg=BG)
                row.pack(fill="x", pady=3)
                tk.Frame(row, bg=accent, width=3).pack(side="left", fill="y", padx=(0, 10))
                tk.Label(row, text=bullet, font=("Segoe UI", 10),
                         bg=BG, fg=DIM, anchor="w", justify="left", wraplength=820).pack(anchor="w", pady=4)

        # ── ARTICLES ──────────────────────────────────────────────────────────────
        _section_hdr("✨", "Core Monitoring", "What runs under the hood", BLUE)
        _article([
            "Real-time CPU, GPU, RAM tracking — updates every second, background-threaded so the UI never freezes.",
            "Session averages shown on the dashboard give you a quick health baseline without digging into charts.",
            "Stats Engine v2 stores minute-by-minute data in SQLite — browse 1D / 3D / 1W / 1M history in Monitoring.",
            "All data lives on your machine. No cloud, no telemetry, no accounts.",
        ], BLUE)

        _section_hdr("🤖", "HCK_GPT Assistant", "Your local AI companion — no internet needed", EMERALD)
        _article([
            "Type 'stats', 'alerts', 'insights', or 'teaser' in the chat to get personalized system summaries.",
            "HCK_GPT learns your usage patterns (games, dev tools, browsers) and adapts its messages over time.",
            "Today Report shows a session chart, top processes, alert status, and uptime — one click in the chat panel.",
            "Everything runs locally — no API key, no data sent anywhere.",
        ], EMERALD)

        _section_hdr("⚡", "Optimization & Automation", "Set it once, forget about it", AMBER)
        _article([
            "AUTO RAM Flush monitors memory every 10 seconds. If usage stays above threshold for 30s, it flushes automatically.",
            "TURBO BOOST runs all Quick Actions at once — power plan, DNS, temp files, process priority.",
            "Settings persist across restarts — your AUTO toggle state is saved in settings/user_prefs.json.",
            "Optimization Center shows 1/14 active features — more coming with each release.",
        ], AMBER)

        _section_hdr("📊", "AllMonitor & Graphs", "Full picture of your hardware", VIOLET)
        _article([
            "AllMonitor page shows live scrolling graphs for CPU, GPU, RAM — updated every 200ms.",
            "Hardware & Health Table (OPEN TABLE button) shows every sensor: temps, voltages, fan speeds.",
            "Monitoring — Centrum page shows time-travel statistics with spike detection and hover tooltips.",
            "Fan Dashboard controls cooling profiles and shows fan curve visualizations.",
        ], VIOLET)

        _section_hdr("🛡️", "Privacy & Safety", "Your PC, your data, your rules", "#64748b")
        _article([
            "PC_Workman is 100% offline. Nothing is transmitted, collected, or uploaded.",
            "Every feature can be disabled individually — monitoring only, optimization only, or everything.",
            "Optimization actions are safe: RAM flush uses Windows APIs, no registry edits without confirmation.",
            "Logs stored in data/logs/ — delete anytime, program recreates them on next launch.",
        ], "#64748b")

        # ── PRO TIPS ROW ─────────────────────────────────────────────────────────
        tips_hdr = tk.Frame(sf, bg=BG)
        tips_hdr.pack(fill="x", padx=28, pady=(8, 4))
        tk.Label(tips_hdr, text="💡  Quick Tips", font=("Segoe UI Semibold", 11, "bold"),
                 bg=BG, fg=AMBER).pack(anchor="w")
        tk.Frame(tips_hdr, bg=BORDER, height=1).pack(fill="x", pady=(4, 0))

        tips = [
            ("Floating Monitor", "Launch the always-on-top overlay from the dashboard — stays above all windows."),
            ("Tray Icon", "3-bar icon in system tray shows CPU/GPU/RAM at a glance — right-click for quick actions."),
            ("Minimal Mode", "Switch to compact mode for passive monitoring while you work or game."),
            ("Mouse Wheel", "Scroll anywhere inside panels — all pages support mousewheel navigation."),
        ]
        tips_row = tk.Frame(sf, bg=BG)
        tips_row.pack(fill="x", padx=28, pady=(0, 32))
        for tip_title, tip_body in tips:
            tip_card = tk.Frame(tips_row, bg=CARD)
            tip_card.pack(side="left", fill="both", expand=True, padx=(0, 8))
            tk.Frame(tip_card, bg=AMBER, height=2).pack(fill="x")
            tk.Label(tip_card, text=tip_title, font=("Segoe UI Semibold", 9, "bold"),
                     bg=CARD, fg=TEXT).pack(anchor="w", padx=12, pady=(10, 2))
            tk.Label(tip_card, text=tip_body, font=("Segoe UI", 9), bg=CARD, fg=DIM,
                     wraplength=180, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

    # ========== OVERLAY WIDGET ==========

    def _launch_overlay_widget(self):
        """Launch floating overlay widget"""
        if create_overlay_widget is None:
            from tkinter import messagebox
            messagebox.showwarning("Overlay Widget", "Overlay widget module not available!")
            return

        # Launch in separate thread to avoid blocking main window
        def launch_thread():
            try:
                create_overlay_widget()
            except Exception as e:
                print(f"[ERROR] Overlay widget failed: {e}")

        widget_thread = threading.Thread(target=launch_thread, daemon=True)
        widget_thread.start()

    # ========== SERVICES DIALOG ==========

    def _show_services_dialog(self, parent):
        """Show Services dialog - same as in hck_gpt_panel"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("🔧 Service Setup - hck_GPT")
        dialog.geometry("600x500")
        dialog.configure(bg="#0f1117")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 300
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 250
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = tk.Frame(dialog, bg="#8b5cf6")
        header.pack(fill="x")

        tk.Label(
            header,
            text="🔧 Service Setup Wizard",
            font=("Segoe UI", 14, "bold"),
            bg="#8b5cf6",
            fg="#ffffff"
        ).pack(pady=15)

        # Content frame with scrollbar
        content = tk.Frame(dialog, bg="#0f1117")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # Import chat handler
        try:
            from hck_gpt.chat_handler import ChatHandler
            chat_handler = ChatHandler()

            # Text widget for chat
            text_frame = tk.Frame(content, bg="#1a1d24")
            text_frame.pack(fill="both", expand=True)

            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side="right", fill="y")

            text_widget = tk.Text(
                text_frame,
                bg="#1a1d24",
                fg="#ffffff",
                font=("Consolas", 10),
                wrap="word",
                yscrollcommand=scrollbar.set
            )
            text_widget.pack(fill="both", expand=True)
            scrollbar.config(command=text_widget.yview)

            # Start wizard
            responses = chat_handler.wizard.start()
            for response in responses:
                text_widget.insert("end", response + "\n")
            text_widget.config(state="disabled")

            # Entry for user input
            entry_frame = tk.Frame(content, bg="#0f1117")
            entry_frame.pack(fill="x", pady=(10, 0))

            entry = tk.Entry(
                entry_frame,
                bg="#1a1d24",
                fg="#ffffff",
                font=("Consolas", 11),
                insertbackground="#8b5cf6"
            )
            entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

            def send_message():
                msg = entry.get().strip()
                if msg:
                    entry.delete(0, "end")
                    text_widget.config(state="normal")
                    text_widget.insert("end", f"\n> {msg}\n")
                    responses = chat_handler.process_message(msg)
                    for response in responses:
                        text_widget.insert("end", response + "\n")
                    text_widget.see("end")
                    text_widget.config(state="disabled")

            entry.bind("<Return>", lambda e: send_message())

            send_btn = tk.Button(
                entry_frame,
                text="Send",
                bg="#8b5cf6",
                fg="#ffffff",
                font=("Segoe UI", 10, "bold"),
                bd=0,
                padx=15,
                command=send_message
            )
            send_btn.pack(side="right")

        except ImportError:
            tk.Label(
                content,
                text="Service Setup not available\n\nChat handler module not found.",
                font=("Segoe UI", 12),
                bg="#0f1117",
                fg="#ef4444",
                justify="center"
            ).pack(expand=True)

        # Close button
        close_btn = tk.Button(
            dialog,
            text="Close",
            bg="#374151",
            fg="#ffffff",
            font=("Segoe UI", 10),
            bd=0,
            padx=20,
            pady=8,
            command=dialog.destroy
        )
        close_btn.pack(pady=15)

    # ── Live Guide ────────────────────────────────────────────────────────────

    def _start_live_guide(self) -> None:
        """
        Launch the interactive Live Guide on the dashboard.
        If we're not on the dashboard, switch first and wait for it to render.
        """
        if _LiveGuide is None:
            import tkinter.messagebox as mb
            mb.showinfo("Live Guide", "LiveGuide module not found.", parent=self.root)
            return

        if self.current_view != "dashboard":
            self._switch_to_page("dashboard")
            self.root.after(400, self._start_live_guide)
            return

        # Ensure dashboard widgets exist (realtime_canvas is a reliable sentinel)
        if not hasattr(self, "realtime_canvas"):
            self.root.after(200, self._start_live_guide)
            return

        # Kill any existing guide before starting a fresh one
        if hasattr(self, "_live_guide") and self._live_guide is not None:
            try:
                self._live_guide.close()
            except Exception:
                pass

        self._live_guide = _LiveGuide(self)
        self._live_guide.start()

    def _show_update_dialog(self, parent):
        """Show Check Update dialog"""
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("🔄 Check for Updates")
        dialog.geometry("500x350")
        dialog.configure(bg="#0f1117")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 175
        dialog.geometry(f"+{x}+{y}")

        # Header
        header = tk.Frame(dialog, bg="#10b981")
        header.pack(fill="x")

        tk.Label(
            header,
            text="🔄 Check for Updates",
            font=("Segoe UI", 14, "bold"),
            bg="#10b981",
            fg="#ffffff"
        ).pack(pady=15)

        # Content
        content = tk.Frame(dialog, bg="#0f1117")
        content.pack(fill="both", expand=True, padx=30, pady=20)

        # Message
        tk.Label(
            content,
            text="Hey!",
            font=("Segoe UI", 16, "bold"),
            bg="#0f1117",
            fg="#ffffff"
        ).pack(anchor="w", pady=(0, 15))

        # Version info
        version_frame = tk.Frame(content, bg="#0f1117")
        version_frame.pack(anchor="w", pady=5)

        tk.Label(
            version_frame,
            text="Your version: ",
            font=("Segoe UI", 12),
            bg="#0f1117",
            fg="#cbd5e1"
        ).pack(side="left")

        tk.Label(
            version_frame,
            text="v1.7.1",
            font=("Segoe UI", 12, "bold"),
            bg="#0f1117",
            fg="#10b981"
        ).pack(side="left")

        tk.Label(
            version_frame,
            text=" - 10.04.2026",
            font=("Segoe UI", 12),
            bg="#0f1117",
            fg="#64748b"
        ).pack(side="left")

        # Message text
        tk.Label(
            content,
            text="\nI would really like to tell you if there's a new update!\nBut I'm limited ;)",
            font=("Segoe UI", 11),
            bg="#0f1117",
            fg="#94a3b8",
            justify="left"
        ).pack(anchor="w", pady=(15, 10))

        tk.Label(
            content,
            text="Please check here if your version is up to date!",
            font=("Segoe UI", 11),
            bg="#0f1117",
            fg="#cbd5e1"
        ).pack(anchor="w", pady=(5, 15))

        # GitHub button
        def open_github():
            import webbrowser
            webbrowser.open("https://github.com/HCK-Labs/PC-Workman/releases")

        github_btn = tk.Button(
            content,
            text="🔗 CHECK UPDATE ON GITHUB",
            font=("Segoe UI Semibold", 11, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            bd=0,
            padx=25,
            pady=12,
            cursor="hand2",
            command=open_github
        )
        github_btn.pack(pady=15)

        # Close button
        close_btn = tk.Button(
            dialog,
            text="Close",
            bg="#374151",
            fg="#ffffff",
            font=("Segoe UI", 10),
            bd=0,
            padx=20,
            pady=8,
            command=dialog.destroy
        )
        close_btn.pack(pady=15)

    # ========== MAIN LOOP ==========

    def run(self):
        """Run the window"""
        # Auto-launch overlay monitor after UI is visible
        self.root.after(1500, self._launch_overlay_monitor)
        self.root.mainloop()

    def quit(self):
        """Quit the window"""
        self._running = False
        # Stop background monitor collection
        if self.monitor and hasattr(self.monitor, 'stop_background_collection'):
            self.monitor.stop_background_collection()
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass


# ========== MODULE-LEVEL HELPERS ==========

def _open_hw_table_popup(anchor):
    """Core: open ProInfoTable popup anchored to any tk widget or window."""
    try:
        from ui.components.pro_info_table import ProInfoTable
    except ImportError:
        ProInfoTable = None

    popup = tk.Toplevel(anchor)
    popup.title("Hardware & Health")
    popup.configure(bg="#0a0e14")
    popup.attributes("-topmost", True)
    popup.resizable(True, True)

    # Header
    hdr = tk.Frame(popup, bg="#111827")
    hdr.pack(fill="x")
    tk.Label(hdr, text="Hardware & Health Table",
             font=("Segoe UI Semibold", 11), bg="#111827",
             fg="#ffffff", pady=8).pack(side="left", padx=14)
    x_btn = tk.Label(hdr, text="✕", font=("Segoe UI", 12, "bold"),
                     bg="#111827", fg="#64748b", padx=12, cursor="hand2")
    x_btn.pack(side="right", pady=5)
    x_btn.bind("<Button-1>", lambda e: popup.destroy())
    x_btn.bind("<Enter>", lambda e: x_btn.config(fg="#ef4444"))
    x_btn.bind("<Leave>", lambda e: x_btn.config(fg="#64748b"))

    content = tk.Frame(popup, bg="#0a0e14")
    content.pack(fill="both", expand=True, padx=4, pady=4)

    if ProInfoTable:
        try:
            table = ProInfoTable(content)
            table.pack(fill="both", expand=True)
        except Exception as e:
            tk.Label(content, text=f"Error loading table: {e}",
                     font=("Segoe UI", 10), bg="#0a0e14", fg="#ef4444").pack(pady=50)
    else:
        tk.Label(content, text="Hardware table not available",
                 font=("Segoe UI", 10), bg="#0a0e14", fg="#6b7280").pack(pady=50)

    # Center on screen
    popup.update_idletasks()
    w, h = 520, 640
    sw = popup.winfo_screenwidth()
    sh = popup.winfo_screenheight()
    popup.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")


def _draw_page_icon(canvas, page_id, cx, cy, accent="#3b82f6"):
    """
    Draw a crisp vector icon centred at (cx, cy) on an existing tk.Canvas.
    All coordinates are relative to (cx, cy).  Icons fit inside ~20×24 px.
    """
    import math

    A   = accent        # primary accent colour
    BG  = "#05070d"     # icon panel background (same as icon section fill)
    W   = "#ffffff"     # white for inset details
    DK  = "#0a0e1a"     # dark for screen / details

    def R(x0, y0, x1, y1, fill=A, outline=""):
        canvas.create_rectangle(cx+x0, cy+y0, cx+x1, cy+y1, fill=fill, outline=outline)

    def O(x0, y0, x1, y1, fill=A, outline=""):
        canvas.create_oval(cx+x0, cy+y0, cx+x1, cy+y1, fill=fill, outline=outline)

    def P(*pts, fill=A, outline=""):
        flat = []
        for x, y in pts:
            flat += [cx + x, cy + y]
        canvas.create_polygon(flat, fill=fill, outline=outline, smooth=False)

    def Arc(x0, y0, x1, y1, **kw):
        canvas.create_arc(cx+x0, cy+y0, cx+x1, cy+y1, **kw)

    # ── MY PC — monitor + stand ───────────────────────────────────────────────
    if page_id == "your_pc":
        R(-11, -10,  11,  5)                    # bezel
        R( -9,  -8,   9,  3, fill=DK)           # screen glass
        R( -1,   5,   1,  9)                    # stand arm
        R( -6,   8,   6, 11)                    # base
        O(  7,   0,   9,  2, fill="#10b981")    # power LED green

    # ── MONITORING — big exclamation mark ────────────────────────────────────
    elif page_id == "sensors":
        R(-2, -12,  2,  4, fill=A)             # stem (tall)
        O(-3,   6,  3, 12, fill=A)             # dot (round)

    # ── ALLMONITOR — bar chart ────────────────────────────────────────────────
    elif page_id == "live_graphs":
        R(-11,  3, -5, 10)                      # short bar
        R( -3, -3,  3, 10)                      # medium bar
        R(  5, -9, 11, 10)                      # tall bar
        R(-13,  9, 13, 12)                      # baseline

    # ── OPTIMIZATION — lightning bolt ─────────────────────────────────────────
    elif page_id == "optimization":
        P((4,-12), (-2,-1), (3,-1), (-4,12), (-5,12),
          (1, 1), (-4,  1), (2,-12))

    # ── FAN DASHBOARD — monitor icon (same as My PC), purple tint ────────────
    elif page_id == "fan_control":
        R(-11, -10,  11,  5)                    # bezel
        R( -9,  -8,   9,  3, fill=DK)           # screen glass
        R( -1,   5,   1,  9)                    # stand arm
        R( -6,   8,   6, 11)                    # base
        O(  7,   0,   9,  2, fill="#a78bfa")    # purple LED

    # ── HCK_LABS — globe icon ─────────────────────────────────────────────────
    elif page_id == "hck_labs":
        O(-11, -11, 11, 11)                                                    # outer sphere
        O( -5, -11,  5, 11)                                                    # central meridian oval
        canvas.create_line(cx-11, cy,   cx+11, cy,   fill=accent, width=1.5)  # equator
        canvas.create_line(cx- 9, cy-5, cx+ 9, cy-5, fill=accent, width=1.0)  # N parallel
        canvas.create_line(cx- 9, cy+5, cx+ 9, cy+5, fill=accent, width=1.0)  # S parallel

    # ── GUIDE — open book ─────────────────────────────────────────────────────
    elif page_id == "guide":
        P((-1,-9), (-11,-7), (-11,8), (-1,7))          # left page
        P(( 1,-9), ( 11,-7), ( 11,8), ( 1,7))          # right page
        R(-1, -9,  1,  9, fill=DK)                     # spine
        # lines left
        for ly in (-4, -1, 2):
            R(-9, ly, -3, ly+1, fill=DK)
        # lines right
        for ly in (-4, -1, 2):
            R( 3, ly,  9, ly+1, fill=DK)


def _launch_hw_table_window(parent):
    """Alias kept for compatibility."""
    _open_hw_table_popup(parent)


def _launch_hw_table_window_root(root):
    """Called via root.after() — uses root as anchor."""
    _open_hw_table_popup(root)

    # Size and position after content loads
    popup.update_idletasks()
    w, h = 520, 640
    sw = popup.winfo_screenwidth()
    sh = popup.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    popup.geometry(f"{w}x{h}+{x}+{y}")
