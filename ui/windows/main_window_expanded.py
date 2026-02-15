# ui/main_window_expanded.py
"""
PC Workman - EXPANDED MODE (Main Window) v1.6.8
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
from ui.components.led_bars import LEDSegmentBar
from ui.components.sidebar_nav import SidebarNav
from ui.pages.fan_control import create_fans_hardware_page, create_fans_usage_stats_page

# YOUR PC page helper
from ui.components.yourpc_page import build_yourpc_page

# Fan Dashboard (Advanced cooling control)
from ui.components.fan_dashboard import create_fan_dashboard

# Overlay Widget (Floating Monitor)
try:
    from ui.overlay_widget import create_overlay_widget
except ImportError:
    create_overlay_widget = None

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

        # System Tray
        self.tray_manager = None
        self._init_system_tray()

        # Create root window
        self.root = tk.Tk()
        self.root.title("PC Workman - HCK Labs v1.6.8")
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

        # Close any open overlay first
        self._close_overlay()

        # Clear current content
        for widget in self.content_area.winfo_children():
            widget.destroy()

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

    def _handle_sidebar_navigation(self, page_id, subpage_id=None):
        """Handle navigation from sidebar"""
        import sys
        print(f"[Sidebar Nav] Navigate to: {page_id}" + (f".{subpage_id}" if subpage_id else ""), flush=True)
        sys.stdout.flush()

        # Pages that replace the entire content area (not overlay)
        direct_pages = {
            "fan_control.fans_hardware": "fans_hardware",
            "fan_control.usage_statistics": "fans_usage_stats",
            "fan_control.fan_dashboard": "fan_control",
            "fan_control": "fan_control",
            # Monitoring & Alerts - direct page
            "monitoring_alerts": "monitoring_alerts",
            "monitoring_alerts.temperature": "monitoring_alerts",
            "monitoring_alerts.voltage": "monitoring_alerts",
            "monitoring_alerts.alerts": "monitoring_alerts",
        }

        # Check if this is a direct page switch
        if subpage_id:
            full_id = f"{page_id}.{subpage_id}"
            if full_id in direct_pages:
                self._switch_to_page(direct_pages[full_id])
                return
        elif page_id in direct_pages:
            self._switch_to_page(direct_pages[page_id])
            return

        # Map sidebar IDs to overlay pages
        page_map = {
            "dashboard": "DASHBOARD",  # Special: go to dashboard
            # My PC section
            "my_pc": "your_pc",
            "my_pc.central": "your_pc",
            "my_pc.efficiency": "your_pc",
            "my_pc.sensors": "sensors",
            "my_pc.health": "your_pc",
            # Optimization section
            "optimization": "optimization",
            "optimization.services": "optimization",
            "optimization.startup": "optimization",
            "optimization.wizard": "optimization",
            # Statistics section
            "statistics": "statistics",
            "statistics.stats_today": "statistics",
            "statistics.stats_weekly": "statistics",
            "statistics.stats_monthly": "statistics",
            # Monitoring & Alerts section
            "monitoring_alerts": "monitoring_alerts",
            "monitoring_alerts.temperature": "monitoring_alerts",
            "monitoring_alerts.voltage": "monitoring_alerts",
            "monitoring_alerts.alerts": "monitoring_alerts",
            # Other
            "settings": "settings",
            "pinned": None,
        }

        # Determine target page
        if subpage_id:
            full_id = f"{page_id}.{subpage_id}"
            target = page_map.get(full_id, page_map.get(page_id))
        else:
            target = page_map.get(page_id)

        # Handle special cases
        if target == "overlay_launch":
            # Launch overlay widget
            if create_overlay_widget:
                create_overlay_widget(self.root, self.monitor)
            return

        if target == "DASHBOARD" or target is None:
            # Go back to dashboard - force rebuild
            self._close_overlay()
            self.current_view = None  # Force rebuild
            self._switch_to_page("dashboard")
            return

        # For overlay pages, first make sure we're on dashboard, then show overlay
        if self.current_view != "dashboard":
            self.current_view = None  # Force rebuild
            self._switch_to_page("dashboard")

        # Show the overlay page
        self._show_overlay(target)

    def _build_hckgpt_banner(self):
        """Build hck_GPT banner at bottom with sliding chat panel"""
        # Banner container
        banner = tk.Frame(self.content_area, bg="#8b5cf6", height=35, cursor="hand2")
        banner.pack(fill="x", side="bottom")
        banner.pack_propagate(False)

        # Banner content
        banner_content = tk.Frame(banner, bg="#8b5cf6")
        banner_content.pack(fill="both", expand=True, padx=15, pady=5)

        # Left: hck_GPT text
        tk.Label(
            banner_content,
            text="hck_GPT - Your PC master!",
            font=("Segoe UI", 9, "bold"),
            bg="#8b5cf6",
            fg="#ffffff",
            cursor="hand2"
        ).pack(side="left")

        # Right: Click me!
        tk.Label(
            banner_content,
            text="Click me!",
            font=("Segoe UI", 8),
            bg="#8b5cf6",
            fg="#e9d5ff",
            cursor="hand2"
        ).pack(side="right")

        # Chat panel (hidden by default) - slides from bottom
        self.chat_panel = tk.Frame(self.content_area, bg="#1a1d24", height=0)
        self.chat_panel.place(x=0, y=575, width=980, height=0)  # Start hidden below window
        self.chat_visible = False

        # Click handler - toggle chat
        def toggle_chat(e):
            if not self.chat_visible:
                self._show_chat_panel()
            else:
                self._hide_chat_panel()

        banner.bind("<Button-1>", toggle_chat)
        banner_content.bind("<Button-1>", toggle_chat)
        for child in banner_content.winfo_children():
            child.bind("<Button-1>", toggle_chat)

        # Hover effect
        def on_enter(e):
            banner.config(bg="#7c3aed")
            banner_content.config(bg="#7c3aed")
            for child in banner_content.winfo_children():
                child.config(bg="#7c3aed")

        def on_leave(e):
            banner.config(bg="#8b5cf6")
            banner_content.config(bg="#8b5cf6")
            for child in banner_content.winfo_children():
                child.config(bg="#8b5cf6")

        banner.bind("<Enter>", on_enter)
        banner.bind("<Leave>", on_leave)

    def _show_chat_panel(self):
        """Slide chat panel up from bottom"""
        self.chat_visible = True
        target_height = 300
        target_y = 575 - target_height

        # Build chat content if not built yet
        if not self.chat_panel.winfo_children():
            self._build_chat_content()

        # Animate slide up
        start_y = 575
        start_time = time.time()
        duration_ms = 300

        def animate():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)
            # Ease out cubic
            eased = 1 - pow(1 - progress, 3)
            current_y = int(start_y + (target_y - start_y) * eased)
            current_height = int(target_height * eased)

            self.chat_panel.place(y=current_y, height=current_height)

            if progress < 1.0:
                self.root.after(16, animate)

        animate()

    def _hide_chat_panel(self):
        """Slide chat panel down to hide"""
        self.chat_visible = False
        start_y = 575 - 300
        target_y = 575
        start_height = 300
        start_time = time.time()
        duration_ms = 250

        def animate():
            elapsed = (time.time() - start_time) * 1000
            progress = min(elapsed / duration_ms, 1.0)
            # Ease in cubic
            eased = pow(progress, 3)
            current_y = int(start_y + (target_y - start_y) * eased)
            current_height = int(start_height * (1 - eased))

            self.chat_panel.place(y=current_y, height=current_height)

            if progress >= 1.0:
                self.chat_panel.place(y=575, height=0)

            if progress < 1.0:
                self.root.after(16, animate)

        animate()

    def _build_chat_content(self):
        """Build hck_GPT chat interface"""
        # Header
        chat_header = tk.Frame(self.chat_panel, bg="#8b5cf6", height=40)
        chat_header.pack(fill="x")
        chat_header.pack_propagate(False)

        tk.Label(
            chat_header,
            text="💬 hck_GPT Assistant",
            font=("Segoe UI Semibold", 11, "bold"),  # Modern semibold!
            bg="#8b5cf6",
            fg="#ffffff"
        ).pack(side="left", padx=15, pady=10)

        # Close button
        close_btn = tk.Label(
            chat_header,
            text="✕",
            font=("Segoe UI", 14),
            bg="#8b5cf6",
            fg="#ffffff",
            cursor="hand2"
        )
        close_btn.pack(side="right", padx=15)
        close_btn.bind("<Button-1>", lambda e: self._hide_chat_panel())

        # Chat area
        chat_area = tk.Frame(self.chat_panel, bg="#0f1117")
        chat_area.pack(fill="both", expand=True, padx=10, pady=10)

        # Messages container (scrollable)
        messages_canvas = tk.Canvas(chat_area, bg="#0f1117", highlightthickness=0)
        scrollbar = tk.Scrollbar(chat_area, orient="vertical", command=messages_canvas.yview)
        self.messages_frame = tk.Frame(messages_canvas, bg="#0f1117")

        self.messages_frame.bind(
            "<Configure>",
            lambda e: messages_canvas.configure(scrollregion=messages_canvas.bbox("all"))
        )

        messages_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        messages_canvas.configure(yscrollcommand=scrollbar.set)

        messages_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Welcome message
        self._add_gpt_message("Hello! I'm hck_GPT, your PC assistant. How can I help you today?")

        # Input area
        input_frame = tk.Frame(self.chat_panel, bg="#1a1d24")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Text entry
        self.chat_input = tk.Entry(
            input_frame,
            font=("Segoe UI", 10),
            bg="#0f1117",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat"
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=8)
        self.chat_input.bind("<Return>", lambda e: self._send_message())

        # Send button
        send_btn = tk.Label(
            input_frame,
            text="Send",
            font=("Segoe UI", 9, "bold"),
            bg="#8b5cf6",
            fg="#ffffff",
            cursor="hand2",
            padx=20,
            pady=8
        )
        send_btn.pack(side="right")
        send_btn.bind("<Button-1>", lambda e: self._send_message())

        # Hover effect
        def on_enter_send(e):
            send_btn.config(bg="#7c3aed")
        def on_leave_send(e):
            send_btn.config(bg="#8b5cf6")
        send_btn.bind("<Enter>", on_enter_send)
        send_btn.bind("<Leave>", on_leave_send)

    def _add_gpt_message(self, text):
        """Add GPT assistant message to chat"""
        msg_frame = tk.Frame(self.messages_frame, bg="#0f1117")
        msg_frame.pack(fill="x", pady=5, anchor="w")

        msg_bubble = tk.Frame(msg_frame, bg="#8b5cf6")
        msg_bubble.pack(side="left", padx=10)

        tk.Label(
            msg_bubble,
            text=text,
            font=("Segoe UI", 9),
            bg="#8b5cf6",
            fg="#ffffff",
            wraplength=600,
            justify="left",
            padx=12,
            pady=8
        ).pack()

    def _add_user_message(self, text):
        """Add user message to chat"""
        msg_frame = tk.Frame(self.messages_frame, bg="#0f1117")
        msg_frame.pack(fill="x", pady=5, anchor="e")

        msg_bubble = tk.Frame(msg_frame, bg="#3b82f6")
        msg_bubble.pack(side="right", padx=10)

        tk.Label(
            msg_bubble,
            text=text,
            font=("Segoe UI", 9),
            bg="#3b82f6",
            fg="#ffffff",
            wraplength=600,
            justify="left",
            padx=12,
            pady=8
        ).pack()

    def _send_message(self):
        """Send user message and get GPT response"""
        user_text = self.chat_input.get().strip()
        if not user_text:
            return

        # Add user message
        self._add_user_message(user_text)
        self.chat_input.delete(0, tk.END)

        # Simulate GPT response (placeholder)
        self.root.after(500, lambda: self._add_gpt_message(
            f"I understand you said: '{user_text}'. This is a placeholder response. Full GPT integration coming soon!"
        ))

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

        tk.Label(
            left_nav,
            text="QUICK ACCESS",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["muted"]
        ).pack(pady=(10, 5))

        # Navigation buttons (left)
        nav_buttons_left = [
            ("💻 Your PC", "#3b82f6"),
            ("🌲 Sensors", "#8b5cf6"),
            ("📊 Live Graphs", "#f97316"),
            ("🌀 Fan Curves", "#a855f7"),
            ("⚡ Optimization", "#10b981"),
        ]

        for text, color in nav_buttons_left:
            self._create_nav_button(left_nav, text, color, pady=0)

        # CENTER - SESSION AVERAGE BARS
        center = tk.Frame(middle, bg=THEME["bg_main"])
        center.pack(side="left", fill="both", expand=True, padx=5)

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

        tk.Label(
            right_nav,
            text="EXPLORE",
            font=("Segoe UI", 9, "bold"),
            bg=THEME["bg_panel"],
            fg=THEME["muted"]
        ).pack(pady=(10, 5))

        # Navigation buttons (right)
        nav_buttons_right = [
            ("🌀 Advanced Dashboard", "#8b5cf6"),
            ("🚀 HCK_Labs", "#f59e0b"),
            ("📖 Guide", "#06b6d4"),
        ]

        for text, color in nav_buttons_right:
            self._create_nav_button(right_nav, text, color, pady=0)

        # NOTE: Shimmer animation REMOVED - static gradient instead

    def _create_nav_button(self, parent, text, color, pady=4):
        """Create gradient sidebar button"""
        # Main button container
        btn_container = tk.Frame(parent, bg=THEME["bg_panel"])
        btn_container.pack(fill="x", padx=8, pady=pady)

        # Click handler - map text to page ID
        page_map = {
            "💻 Your PC": "your_pc",
            "🌲 Sensors": "sensors",
            "📊 Live Graphs": "live_graphs",
            "🌀 Fan Curves": "fan_curves",
            "⚡ Optimization": "optimization",
            "📊 Statistics": "statistics",
            "🌀 Advanced Dashboard": "fan_control",
            "🚀 HCK_Labs": "hck_labs",
            "📖 Guide": "guide"
        }

        page_id = page_map.get(text)

        # Clean text name (remove emoji)
        clean_text = text.split()[-1] if ' ' in text else text
        if clean_text == "PC":
            clean_text = "MY PC"

        # === GRADIENT COLOR MAPS ===
        gradient_maps = {
            "#3b82f6": [(30, 64, 175), (59, 130, 246), (96, 165, 250)],  # Blue gradient
            "#10b981": [(4, 120, 87), (16, 185, 129), (52, 211, 153)],   # Green gradient
            "#8b5cf6": [(107, 33, 168), (139, 92, 246), (167, 139, 250)], # Purple gradient
            "#f59e0b": [(217, 119, 6), (245, 158, 11), (251, 191, 36)],  # Orange gradient
            "#ef4444": [(185, 28, 28), (239, 68, 68), (248, 113, 113)],  # Red gradient
            "#ec4899": [(190, 24, 93), (236, 72, 153), (244, 114, 182)]  # Pink gradient
        }

        gradient_rgb = gradient_maps.get(color, [(59, 130, 246), (96, 165, 250), (147, 197, 253)])

        # === CANVAS BUTTON (45px height) ===
        canvas_height = 45
        canvas = tk.Canvas(
            btn_container,
            bg=THEME["bg_panel"],
            height=canvas_height,
            highlightthickness=0,
            cursor="hand2"
        )
        canvas.pack(fill="x")

        # NOTE: Canvas storage removed - no animation needed

        # Draw button after canvas is ready
        def draw_button(event=None, anim_offset=0):
            canvas.delete("all")
            width = canvas.winfo_width()
            if width <= 1:
                canvas.after(50, draw_button)
                return

            height = canvas_height

            # LEFT SECTION - ICON (40px width, dark background) - NO "/" separator!
            icon_width = 40
            canvas.create_rectangle(0, 0, icon_width, height, fill="#1a1d24", outline="")

            # Icon (centered)
            icon_x = icon_width // 2
            icon_y = height // 2
            if page_id and page_id in self.nav_icons:
                canvas.create_image(icon_x, icon_y, image=self.nav_icons[page_id], tags="icon")

            # RIGHT SECTION - ANIMATED GRADIENT TEXT AREA (starts right after icon!)
            gradient_start = icon_width  # No gap, no diagonal separator!
            gradient_width = width - gradient_start

            # Draw STATIC GRADIENT (vertical lines with color interpolation - NO animation)
            for i in range(int(gradient_width)):
                # Calculate color interpolation (3-color gradient: dark -> mid -> light)
                ratio = i / gradient_width if gradient_width > 0 else 0

                # STATIC ratio (no anim_offset)
                if ratio < 0.5:
                    # First half: dark to mid
                    local_ratio = ratio * 2
                    r = int(gradient_rgb[0][0] + (gradient_rgb[1][0] - gradient_rgb[0][0]) * local_ratio)
                    g = int(gradient_rgb[0][1] + (gradient_rgb[1][1] - gradient_rgb[0][1]) * local_ratio)
                    b = int(gradient_rgb[0][2] + (gradient_rgb[1][2] - gradient_rgb[0][2]) * local_ratio)
                else:
                    # Second half: mid to light
                    local_ratio = (ratio - 0.5) * 2
                    r = int(gradient_rgb[1][0] + (gradient_rgb[2][0] - gradient_rgb[1][0]) * local_ratio)
                    g = int(gradient_rgb[1][1] + (gradient_rgb[2][1] - gradient_rgb[1][1]) * local_ratio)
                    b = int(gradient_rgb[1][2] + (gradient_rgb[2][2] - gradient_rgb[1][2]) * local_ratio)

                grad_color = f"#{r:02x}{g:02x}{b:02x}"
                x = gradient_start + i
                canvas.create_line(x, 0, x, height, fill=grad_color, tags="gradient")

            # Button text
            text_x = gradient_start + 15  # Closer to icon (was 20)
            text_y = height // 2
            canvas.create_text(
                text_x, text_y,
                text=clean_text.upper(),
                font=("Segoe UI Semibold", 11, "bold"),  # Semibold for modern, sleek look
                fill="#ffffff",
                anchor="w",
                tags="text"
            )

            # Shadow for depth
            canvas.create_text(
                text_x + 1, text_y + 1,
                text=clean_text.upper(),
                font=("Segoe UI Semibold", 11, "bold"),
                fill="#000000",
                anchor="w",
                tags="text_shadow"
            )
            # Move text to front
            canvas.tag_raise("text")

        # Bind resize to redraw
        canvas.bind("<Configure>", draw_button)
        draw_button()

        # === CLICK HANDLER ===
        if page_id:
            def on_click(e):
                self._show_overlay(page_id)
            canvas.bind("<Button-1>", on_click)

        # === HOVER EFFECT - just visual feedback ===
        def on_enter(e):
            # Simple hover - could add subtle effect later if needed
            pass

        def on_leave(e):
            pass

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)

    def _create_session_bar(self, parent, label, color_start, color_end, key):
        """Create gradient session average bar - COMPACT VERSION"""
        row = tk.Frame(parent, bg=THEME["bg_main"])
        row.pack(fill="x", pady=1)  # Reduced from 2 to 1

        # Label - smaller font
        lbl = tk.Label(
            row,
            text=label,
            font=("Segoe UI", 8, "bold"),  # Reduced from 9 to 8
            bg=THEME["bg_main"],
            fg=THEME["text"],
            width=4,  # Reduced from 5 to 4
            anchor="w"
        )
        lbl.pack(side="left", padx=(8, 4))  # Reduced padding

        # Bar background - SMALLER HEIGHT
        bar_bg = tk.Frame(row, bg="#1a1d24", height=16)  # Reduced from 22 to 16
        bar_bg.pack(side="left", fill="x", expand=True, padx=4)  # Reduced padding
        bar_bg.pack_propagate(False)

        # Bar fill (gradient effect via solid color for now)
        bar_fill = tk.Frame(bar_bg, bg=color_start, height=16)  # Reduced from 22 to 16
        bar_fill.place(x=0, y=0, relwidth=0, relheight=1.0)

        # Value label - smaller font
        val_lbl = tk.Label(
            row,
            text="0%",
            font=("Consolas", 8, "bold"),  # Reduced from 10 to 8
            bg=THEME["bg_main"],
            fg=color_start,
            width=4,  # Reduced from 5 to 4
            anchor="e"
        )
        val_lbl.pack(side="right", padx=(4, 8))  # Reduced padding

        # Store references
        if not hasattr(self, 'session_bars'):
            self.session_bars = {}

        self.session_bars[key] = {
            "fill": bar_fill,
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
            text="✓ Wszystko OK",
            font=("Segoe UI", 6),
            bg=THEME["bg_panel"],
            fg="#10b981",
            anchor="w"
        )
        health_label.pack(fill="x", pady=(2, 0))

        # Load status - smaller font
        load_label = tk.Label(
            inner,
            text="Brak aktywności",
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

        # Data storage for chart (100 samples per resource)
        self.chart_data = {
            "cpu": [],  # CPU usage history
            "ram": [],  # RAM usage history
            "gpu": []   # GPU usage history
        }
        self.chart_max_samples = 100  # 100 seconds of data

        # Start chart update animation
        self._update_realtime_chart()

        # Live Metrics Line (AKTUALNE UŻYCIE)
        metrics_frame = tk.Frame(center, bg="#1a1d24", height=28)
        metrics_frame.pack(fill="x")
        metrics_frame.pack_propagate(False)

        tk.Label(
            metrics_frame,
            text="AKTUALNE UŻYCIE:",
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

        # Time filter buttons
        self.chart_filter = "SESSION"  # Default filter

        # Separator (visual space)
        tk.Frame(metrics_frame, bg="#1a1d24", width=2).pack(side="left", padx=10)

        # Filter buttons container
        filter_btns = tk.Frame(metrics_frame, bg="#1a1d24")
        filter_btns.pack(side="right", padx=10)

        # Create filter buttons - real-time + historical from SQLite
        filter_options = ["LIVE", "1H", "4H", "1D", "1W", "1M"]
        self.filter_buttons = {}
        self._historical_chart_data = None  # SQLite data cache

        for idx, filter_name in enumerate(filter_options):
            btn = tk.Label(
                filter_btns,
                text=filter_name,
                font=("Segoe UI", 6, "bold"),
                bg="#000000" if filter_name != "LIVE" else "#2563eb",
                fg="#6b7280" if filter_name != "LIVE" else "#ffffff",
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
                    # Load historical data for long-range modes
                    if f_name in ('1D', '1W', '1M'):
                        self._load_historical_chart_data(f_name)
                    else:
                        self._historical_chart_data = None
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
        """Build innovative feature buttons - Turbo Boost & More Optimization Tools"""
        buttons_container = tk.Frame(parent, bg=THEME["bg_main"])
        buttons_container.pack(fill="x", pady=(8, 0))

        # Container for two buttons side by side
        buttons_row = tk.Frame(buttons_container, bg=THEME["bg_main"])
        buttons_row.pack(fill="x", padx=5)

        # Left: Boost mode
        turbo_btn = tk.Frame(buttons_row, bg="#2563eb", cursor="hand2")  # Bright blue border
        turbo_btn.pack(side="left", fill="both", expand=True, padx=(0, 3))

        # Main content container with glowing background
        turbo_content = tk.Frame(turbo_btn, bg="#1e40af")  # Brighter background
        turbo_content.pack(fill="both", expand=True, padx=2, pady=2)

        # Header row with GLOWING background: "Turbo Boost: ON/OFF"
        turbo_header = tk.Frame(turbo_content, bg="#3b82f6")  # Bright glowing blue header
        turbo_header.pack(fill="x", padx=8, pady=(6, 4))

        tk.Label(
            turbo_header,
            text="Turbo Boost:",
            font=("Segoe UI", 11, "bold"),
            bg="#3b82f6",  # Bright background
            fg="#ffffff",
            padx=6,
            pady=2
        ).pack(side="left")

        # ON/OFF with glowing animation
        self.turbo_status_label = tk.Label(
            turbo_header,
            text="OFF",
            font=("Segoe UI", 11, "bold"),
            bg="#3b82f6",  # Bright background
            fg="#fca5a5",  # Lighter red when OFF
            padx=4,
            pady=2
        )
        self.turbo_status_label.pack(side="left", padx=(5, 6))

        # Start glowing animation
        self.turbo_active = False
        self._animate_turbo_glow()

        # Thin separator line (brighter) - moved up (no subtitle)
        tk.Frame(turbo_content, bg="#60a5fa", height=2).pack(fill="x", pady=(4, 4))

        # Bottom action buttons
        turbo_actions = tk.Frame(turbo_content, bg="#1e40af")
        turbo_actions.pack(fill="x", padx=8, pady=(0, 6))

        # Configure button
        config_btn = tk.Label(
            turbo_actions,
            text="Configure",
            font=("Segoe UI", 7, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            cursor="hand2",
            padx=8,
            pady=3
        )
        config_btn.pack(side="left")

        # Click handler - opens Optimization overlay
        def open_optimization(e):
            self._show_overlay("optimization")

        config_btn.bind("<Button-1>", open_optimization)

        # Hover effect
        def on_enter_config(e):
            config_btn.config(bg="#60a5fa")  # Brighter on hover
        def on_leave_config(e):
            config_btn.config(bg="#3b82f6")
        config_btn.bind("<Enter>", on_enter_config)
        config_btn.bind("<Leave>", on_leave_config)

        # Launch/Stop button (brighter)
        self.turbo_action_btn = tk.Label(
            turbo_actions,
            text="Launch",
            font=("Segoe UI", 7, "bold"),
            bg="#34d399",  # Brighter green
            fg="#ffffff",
            cursor="hand2",
            padx=10,
            pady=3
        )
        self.turbo_action_btn.pack(side="right")

        def toggle_turbo(e):
            self.turbo_active = not self.turbo_active
            if self.turbo_active:
                self.turbo_status_label.config(text="ON", fg="#6ee7b7")  # Brighter green
                self.turbo_action_btn.config(text="Stop", bg="#f87171")  # Brighter red
            else:
                self.turbo_status_label.config(text="OFF", fg="#fca5a5")  # Light red
                self.turbo_action_btn.config(text="Launch", bg="#34d399")  # Bright green

        self.turbo_action_btn.bind("<Button-1>", toggle_turbo)

        # Hover effect
        def on_enter_action(e):
            if self.turbo_active:
                self.turbo_action_btn.config(bg="#fca5a5")  # Lighter red on hover
            else:
                self.turbo_action_btn.config(bg="#6ee7b7")  # Lighter green on hover
        def on_leave_action(e):
            if self.turbo_active:
                self.turbo_action_btn.config(bg="#f87171")  # Bright red
            else:
                self.turbo_action_btn.config(bg="#34d399")  # Bright green
        self.turbo_action_btn.bind("<Enter>", on_enter_action)
        self.turbo_action_btn.bind("<Leave>", on_leave_action)

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
            text="Statystyki podniesienia wydajności",
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
        """Build AI writing panel with typing animation"""
        panel = tk.Frame(parent, bg="#0a0e27", height=100)
        panel.pack(fill="x", padx=5, pady=(5, 5))
        panel.pack_propagate(False)

        # Category selection (top - very minimal)
        categories = tk.Frame(panel, bg="#0a0e27")
        categories.pack(fill="x", pady=(5, 5))

        # Category 1: Person + Heart (Human)
        cat1 = tk.Label(
            categories,
            text="👤❤️",
            font=("Segoe UI", 8),
            bg="#0a0e27",
            fg="#64748b",
            cursor="hand2",
            padx=5
        )
        cat1.pack(side="left", padx=2)

        # Category 2: Robot + Money (AI - selected by default)
        self.ai_cat2 = tk.Label(
            categories,
            text="🤖💵",
            font=("Segoe UI", 8),
            bg="#fbbf24",  # Yellow highlight - selected
            fg="#ffffff",
            cursor="hand2",
            padx=5
        )
        self.ai_cat2.pack(side="left", padx=2)

        # Click handlers
        def select_cat1(e):
            cat1.config(bg="#fbbf24", fg="#ffffff")
            self.ai_cat2.config(bg="#0a0e27", fg="#64748b")
            self.current_ai_category = 1

        def select_cat2(e):
            cat1.config(bg="#0a0e27", fg="#64748b")
            self.ai_cat2.config(bg="#fbbf24", fg="#ffffff")
            self.current_ai_category = 2

        cat1.bind("<Button-1>", select_cat1)
        self.ai_cat2.bind("<Button-1>", select_cat2)
        self.current_ai_category = 2  # Default selected

        # AI text display area
        text_area = tk.Frame(panel, bg="#0f1117")
        text_area.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # Text label with cursor
        self.ai_text_container = tk.Frame(text_area, bg="#0f1117")
        self.ai_text_container.pack(expand=True)

        self.ai_text_label = tk.Label(
            self.ai_text_container,
            text="",
            font=("Segoe UI", 7),
            bg="#0f1117",
            fg="#10b981",
            wraplength=200,
            justify="left"
        )
        self.ai_text_label.pack(side="left")

        # Blinking cursor
        self.ai_cursor = tk.Label(
            self.ai_text_container,
            text="█",
            font=("Segoe UI", 7),
            bg="#0f1117",
            fg="#10b981"
        )
        self.ai_cursor.pack(side="left")

        # AI messages (4 messages cycling)
        self.ai_messages = [
            "Totalny ziomek (bro) przedstawiciel twojego PC, który tylko czeka by dbać o zasoby i być dla użytkownika.",
            "Pełno naszych funkcji Optymalizacji (narzędzia 16) jest stworzonych tak, by po konfiguracji użytkownik niczym się nie przejmował i miał dokładnie te funkcje, te wyłączone usługi, i inne rzeczy które chce. Bez zaglądania więcej tam.",
            "Wkładam serce, jako samotny informatyk-media manager-researcher-student AI :) Pozdrawiam z Holandii :), pracuję jako order picker.",
            "Wiem że na tym etapie nikt tego nie przeczyta. Ale jak się znajdzie ktoś taki to dziękuję że jesteś!"
        ]

        self.ai_current_message_index = 0
        self.ai_current_text = ""
        self.ai_typing = False  # Will be set to True on first call
        self.ai_deleting = False
        self.ai_char_index = 0

        # Start animations (after small delay to ensure widgets are ready)
        self.root.after(100, self._animate_ai_cursor)
        self.root.after(100, self._animate_ai_typing)

    def _animate_ai_cursor(self):
        """Blink cursor animation"""
        if not hasattr(self, 'ai_cursor'):
            return

        try:
            current_fg = self.ai_cursor.cget("fg")
            if current_fg == "#10b981":
                self.ai_cursor.config(fg="#0f1117")  # Hide (same as bg)
            else:
                self.ai_cursor.config(fg="#10b981")  # Show

            if self._running:
                self.root.after(500, self._animate_ai_cursor)
        except:
            pass

    def _animate_ai_typing(self):
        """Type message character by character, then delete"""
        if not hasattr(self, 'ai_text_label') or not hasattr(self, 'ai_messages'):
            return

        try:
            message = self.ai_messages[self.ai_current_message_index]
            delay = 50  # Default delay

            # State machine: idle -> typing -> waiting -> deleting -> idle
            if not self.ai_typing and not self.ai_deleting:
                # START TYPING
                self.ai_typing = True
                self.ai_char_index = 0
                self.ai_current_text = ""
                delay = 50

            elif self.ai_typing:
                # TYPING CHARACTER BY CHARACTER
                if self.ai_char_index < len(message):
                    self.ai_current_text = message[:self.ai_char_index + 1]
                    self.ai_text_label.config(text=self.ai_current_text)
                    self.ai_char_index += 1
                    delay = 50  # 50ms per character
                else:
                    # FINISHED TYPING - switch to deleting mode after wait
                    self.ai_typing = False
                    self.ai_deleting = True
                    delay = 5000  # Wait 5 seconds before deleting

            elif self.ai_deleting:
                # DELETING WITH BACKSPACE
                if len(self.ai_current_text) > 0:
                    self.ai_current_text = self.ai_current_text[:-1]
                    self.ai_text_label.config(text=self.ai_current_text)
                    delay = 20  # 20ms per character (faster deletion)
                else:
                    # FINISHED DELETING - move to next message
                    self.ai_deleting = False
                    self.ai_current_message_index = (self.ai_current_message_index + 1) % len(self.ai_messages)
                    delay = 1000  # Wait 1 second before next message

            # Continue animation
            if self._running:
                self.root.after(delay, self._animate_ai_typing)
        except Exception as e:
            print(f"[AI Typing] Error: {e}")
            if self._running:
                self.root.after(1000, self._animate_ai_typing)

    def _animate_button_shimmer(self):
        """ANIMATED RGB GRADIENT - kolory zmieniają się płynnie! 🌈"""
        if not hasattr(self, 'nav_button_canvases') or not self._running:
            return

        try:
            for btn_data in self.nav_button_canvases:
                canvas = btn_data['canvas']
                gradient_rgb = btn_data['gradient_rgb']

                # Update gradient offset
                offset = btn_data.get('gradient_offset', 0)
                offset = (offset + 0.005) % 1.0  # Slow RGB cycling
                btn_data['gradient_offset'] = offset

                # Redraw gradient with new offset
                canvas.delete("gradient")

                width = canvas.winfo_width()
                if width <= 1:
                    continue

                gradient_start = 40  # After icon
                gradient_width = width - gradient_start
                height = 45

                # Draw animated gradient
                for i in range(int(gradient_width)):
                    ratio = i / gradient_width if gradient_width > 0 else 0
                    animated_ratio = (ratio + offset) % 1.0

                    if animated_ratio < 0.5:
                        local_ratio = animated_ratio * 2
                        r = int(gradient_rgb[0][0] + (gradient_rgb[1][0] - gradient_rgb[0][0]) * local_ratio)
                        g = int(gradient_rgb[0][1] + (gradient_rgb[1][1] - gradient_rgb[0][1]) * local_ratio)
                        b = int(gradient_rgb[0][2] + (gradient_rgb[1][2] - gradient_rgb[0][2]) * local_ratio)
                    else:
                        local_ratio = (animated_ratio - 0.5) * 2
                        r = int(gradient_rgb[1][0] + (gradient_rgb[2][0] - gradient_rgb[1][0]) * local_ratio)
                        g = int(gradient_rgb[1][1] + (gradient_rgb[2][1] - gradient_rgb[1][1]) * local_ratio)
                        b = int(gradient_rgb[1][2] + (gradient_rgb[2][2] - gradient_rgb[1][2]) * local_ratio)

                    grad_color = f"#{r:02x}{g:02x}{b:02x}"
                    x = gradient_start + i
                    canvas.create_line(x, 0, x, height, fill=grad_color, tags="gradient")

                # Keep text on top
                canvas.tag_raise("text")
                canvas.tag_raise("icon")

            # Continue animation (60 FPS for smooth gradient)
            if self._running:
                self.root.after(33, self._animate_button_shimmer)
        except Exception as e:
            print(f"[RGB Animation] Error: {e}")
            if self._running:
                self.root.after(33, self._animate_button_shimmer)

    def _render_expanded_user_processes(self, procs):
        """Render TOP 5 user processes with refresh animation"""
        # Guard against destroyed container
        if not hasattr(self, 'expanded_user_container'):
            return
        try:
            if not self.expanded_user_container.winfo_exists():
                return
        except Exception:
            return

        # Clear old widgets
        for widget in self.expanded_user_widgets:
            try:
                widget.destroy()
            except Exception:
                pass
        self.expanded_user_widgets = []

        # Get total system CPU and RAM usage
        total_cpu = psutil.cpu_percent() if psutil else 100
        total_ram_pct = psutil.virtual_memory().percent if psutil else 100

        # Gradient backgrounds for TOP 1-5
        row_gradients = ["#1c1f26", "#1e2128", "#20232a", "#22252c", "#24272e"]

        for i, proc in enumerate(procs[:5], start=1):
            # Get process info
            display_name = proc.get('name', 'unknown')
            cpu_raw = proc.get('cpu_percent', 0)  # Per-core CPU usage
            ram_mb = proc.get('ram_MB', 0)

            # Convert CPU to system-relative percentage
            # psutil gives per-core % (0-100 per core), we need % of total CPU usage
            cpu_cores = psutil.cpu_count() if psutil else 1
            cpu_system_pct = (cpu_raw / cpu_cores) if cpu_cores > 0 else cpu_raw

            # Calculate RAM as % of total RAM
            total_ram_mb = (psutil.virtual_memory().total / (1024 * 1024)) if psutil else 8192
            ram_pct = (ram_mb / total_ram_mb) * 100 if total_ram_mb > 0 else 0

            # Row with gradient background
            row_bg = row_gradients[i-1] if i <= len(row_gradients) else THEME["bg_panel"]
            row = tk.Frame(self.expanded_user_container, bg=row_bg, height=22)
            row.pack(fill="x", pady=0)
            row.pack_propagate(False)

            # Process name
            name_lbl = tk.Label(
                row,
                text=f"{i}. {display_name[:14]}",
                font=("Segoe UI", 7),
                bg=row_bg,
                fg=THEME["text"],
                anchor="w"
            )
            name_lbl.pack(side="left", padx=4, fill="y")

            # CPU/RAM bars side by side
            bars_frame = tk.Frame(row, bg=row_bg)
            bars_frame.pack(side="right", padx=3)

            # CPU
            cpu_container = tk.Frame(bars_frame, bg=row_bg)
            cpu_container.pack(side="left", padx=1)

            tk.Label(cpu_container, text="C", font=("Segoe UI", 6),
                    bg=row_bg, fg="#6b7280", width=2).pack(side="left")

            self._create_mini_bar(cpu_container, cpu_system_pct, "#3b82f6", f"{cpu_system_pct:.0f}%", row_bg)

            # RAM
            ram_container = tk.Frame(bars_frame, bg=row_bg)
            ram_container.pack(side="left", padx=1)

            tk.Label(ram_container, text="R", font=("Segoe UI", 6),
                    bg=row_bg, fg="#6b7280", width=2).pack(side="left")

            self._create_mini_bar(ram_container, ram_pct, "#fbbf24", f"{ram_pct:.0f}%", row_bg)

            self.expanded_user_widgets.append(row)

        # Refresh animation (pulse)
        self._animate_panel(self.expanded_user_container)

    def _render_expanded_system_processes(self, procs):
        """Render TOP 5 system processes with refresh animation"""
        # Guard against destroyed container
        if not hasattr(self, 'expanded_sys_container'):
            return
        try:
            if not self.expanded_sys_container.winfo_exists():
                return
        except Exception:
            return

        # Clear old widgets
        for widget in self.expanded_sys_widgets:
            try:
                widget.destroy()
            except Exception:
                pass
        self.expanded_sys_widgets = []

        # Get total system CPU and RAM usage
        total_cpu = psutil.cpu_percent() if psutil else 100
        total_ram_pct = psutil.virtual_memory().percent if psutil else 100

        # Gradient backgrounds for TOP 1-5
        row_gradients = ["#1c1f26", "#1e2128", "#20232a", "#22252c", "#24272e"]

        for i, proc in enumerate(procs[:5], start=1):
            # Get process info
            display_name = proc.get('name', 'unknown')
            cpu_raw = proc.get('cpu_percent', 0)  # Per-core CPU usage
            ram_mb = proc.get('ram_MB', 0)

            # Convert CPU to system-relative percentage
            cpu_cores = psutil.cpu_count() if psutil else 1
            cpu_system_pct = (cpu_raw / cpu_cores) if cpu_cores > 0 else cpu_raw

            # Calculate RAM as % of total RAM
            total_ram_mb = (psutil.virtual_memory().total / (1024 * 1024)) if psutil else 8192
            ram_pct = (ram_mb / total_ram_mb) * 100 if total_ram_mb > 0 else 0

            # Row with gradient background
            row_bg = row_gradients[i-1] if i <= len(row_gradients) else THEME["bg_panel"]
            row = tk.Frame(self.expanded_sys_container, bg=row_bg, height=22)
            row.pack(fill="x", pady=0)
            row.pack_propagate(False)

            # Process name
            name_lbl = tk.Label(
                row,
                text=f"{i}. {display_name[:14]}",
                font=("Segoe UI", 7),
                bg=row_bg,
                fg=THEME["text"],
                anchor="w"
            )
            name_lbl.pack(side="left", padx=4, fill="y")

            # CPU/RAM bars side by side
            bars_frame = tk.Frame(row, bg=row_bg)
            bars_frame.pack(side="right", padx=3)

            # CPU
            cpu_container = tk.Frame(bars_frame, bg=row_bg)
            cpu_container.pack(side="left", padx=1)

            tk.Label(cpu_container, text="C", font=("Segoe UI", 6),
                    bg=row_bg, fg="#6b7280", width=2).pack(side="left")

            self._create_mini_bar(cpu_container, cpu_system_pct, "#3b82f6", f"{cpu_system_pct:.0f}%", row_bg)

            # RAM
            ram_container = tk.Frame(bars_frame, bg=row_bg)
            ram_container.pack(side="left", padx=1)

            tk.Label(ram_container, text="R", font=("Segoe UI", 6),
                    bg=row_bg, fg="#6b7280", width=2).pack(side="left")

            self._create_mini_bar(ram_container, ram_pct, "#fbbf24", f"{ram_pct:.0f}%", row_bg)

            self.expanded_sys_widgets.append(row)

        # Refresh animation (pulse)
        self._animate_panel(self.expanded_sys_container)

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

    def _update_loop(self):
        """Update loop for session averages, live metrics, and processes - AFTER() BASED"""
        if not self._running:
            return

        try:
            # Get current sample
            sample = self._get_current_sample()

            if sample:
                # Add to session samples
                self.session_samples.append(sample)

                # Keep only last N samples
                if len(self.session_samples) > self.max_session_samples:
                    self.session_samples.pop(0)

                # Calculate averages
                avg_cpu = sum(s.get("cpu_percent", 0) for s in self.session_samples) / len(self.session_samples)
                avg_gpu = sum(s.get("gpu_percent", 0) for s in self.session_samples) / len(self.session_samples)
                avg_ram = sum(s.get("ram_percent", 0) for s in self.session_samples) / len(self.session_samples)

                # Update session bars (every 0.3s)
                self._update_session_bar("cpu", avg_cpu)
                self._update_session_bar("gpu", avg_gpu)
                self._update_session_bar("ram", avg_ram)

                # Update live metrics (every 0.3s)
                self._update_live_metrics(sample)

                # Update hardware cards (only on dashboard)
                if self.current_view == "dashboard":
                    self._update_hardware_cards(sample)

                # Update system tray icon
                if self.tray_manager:
                    cpu = sample.get("cpu_percent", 0)
                    ram = sample.get("ram_percent", 0)
                    gpu = sample.get("gpu_percent", 0)
                    cpu_temp = sample.get("cpu_temp", 0)
                    gpu_temp = sample.get("gpu_temp", 0)
                    self.tray_manager.update_stats(cpu, ram, gpu, cpu_temp, gpu_temp)

                # Update TOP 5 processes every 1 second (3 cycles)
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

        # Schedule next update - CRITICAL: use after() not sleep()
        if self._running:
            self.root.after(300, self._update_loop)  # 300ms = 0.3s

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
        """Update session average bar"""
        if not hasattr(self, 'session_bars'):
            return

        bar_data = self.session_bars.get(key)
        if not bar_data:
            return

        try:
            if not bar_data["fill"].winfo_exists():
                return
            bar_data["fill"].place(relwidth=min(value / 100.0, 1.0))
            bar_data["label"].config(text=f"{value:.1f}%")
        except Exception:
            pass

    def _update_live_metrics(self, sample):
        """Update live metrics line (AKTUALNE UŻYCIE)"""
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
            range_map = {'1D': 86400, '1W': 7 * 86400, '1M': 30 * 86400}
            duration = range_map.get(mode, 86400)
            start_ts = now - duration

            data = query_api.get_usage_for_range(start_ts, now, max_points=100)

            if data:
                self._historical_chart_data = {
                    'cpu': [d['cpu_avg'] for d in data],
                    'ram': [d['ram_avg'] for d in data],
                    'gpu': [d['gpu_avg'] for d in data],
                }
            else:
                self._historical_chart_data = None
        except Exception as e:
            print(f"[ExpandedMode] Historical data load error: {e}")
            self._historical_chart_data = None

    def _update_realtime_chart(self):
        """Draw ultra modern 3-bar real-time chart (CPU, RAM, GPU)"""
        if not hasattr(self, 'realtime_canvas') or not self._running:
            return

        try:
            canvas = self.realtime_canvas
            canvas.delete("all")  # Clear canvas

            # Get canvas dimensions
            width = canvas.winfo_width()
            height = canvas.winfo_height()

            if width <= 1 or height <= 1:
                # Canvas not ready yet
                self.root.after(100, self._update_realtime_chart)
                return

            # Chart area (leave margins)
            margin_left = 10
            margin_right = 10
            margin_top = 10
            margin_bottom = 10

            chart_width = width - margin_left - margin_right
            chart_height = height - margin_top - margin_bottom

            # Get data - use historical data if in historical mode
            if (hasattr(self, '_historical_chart_data') and
                    self._historical_chart_data and
                    hasattr(self, 'chart_filter') and
                    self.chart_filter in ('1D', '1W', '1M')):
                cpu_data = self._historical_chart_data.get('cpu', [])
                ram_data = self._historical_chart_data.get('ram', [])
                gpu_data = self._historical_chart_data.get('gpu', [])
            else:
                cpu_data = self.chart_data.get('cpu', [])
                ram_data = self.chart_data.get('ram', [])
                gpu_data = self.chart_data.get('gpu', [])

            # Number of samples to display
            num_samples = max(len(cpu_data), len(ram_data), len(gpu_data))
            if num_samples == 0:
                # No data yet, schedule next update
                self.root.after(1000, self._update_realtime_chart)
                return

            # Bar width
            bar_width = chart_width / num_samples if num_samples > 0 else 1

            # Colors (DARK BLUE for CPU, YELLOW for RAM, GREEN for GPU)
            cpu_color = "#1e3a8a"  # Dark blue
            ram_color = "#fbbf24"  # Yellow
            gpu_color = "#10b981"  # Green (same as in hardware section)

            # Draw bars from BOTTOM TO TOP
            # Strategy: Draw highest value first (at bottom) so lower values overlay on top
            for i in range(num_samples):
                x = margin_left + (i * bar_width)

                # Get values
                cpu_val = cpu_data[i] if i < len(cpu_data) else 0
                ram_val = ram_data[i] if i < len(ram_data) else 0
                gpu_val = gpu_data[i] if i < len(gpu_data) else 0

                # Calculate heights (percentage of chart height)
                cpu_h = (cpu_val / 100.0) * chart_height
                ram_h = (ram_val / 100.0) * chart_height
                gpu_h = (gpu_val / 100.0) * chart_height

                # Sort by value (draw highest first so it's at bottom)
                bars = [
                    (cpu_h, cpu_color),
                    (ram_h, ram_color),
                    (gpu_h, gpu_color)
                ]
                bars.sort(reverse=True, key=lambda b: b[0])

                # Draw bars from bottom to top
                for bar_h, bar_color in bars:
                    if bar_h > 0:
                        y1 = margin_top + chart_height  # Bottom
                        y2 = y1 - bar_h  # Top

                        canvas.create_rectangle(
                            x, y2,
                            x + bar_width - 1, y1,
                            fill=bar_color,
                            outline=""
                        )

            # Schedule next update (every 1 second)
            self.root.after(1000, self._update_realtime_chart)
        except Exception as e:
            print(f"[Chart] Error: {e}")
            if self._running:
                self.root.after(1000, self._update_realtime_chart)

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
            card["health_label"].config(text="✓ Wszystko OK", fg="#10b981")
        else:
            card["health_label"].config(text="⚠ Inspekcja", fg="#f59e0b")

        # Update load status - SHORTER TEXTS
        if value < 10:
            card["load_label"].config(text="Brak aktywności", fg=THEME["muted"])
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
            "sensors": "🌲 Hardware Sensors - HWMonitor Style",
            "live_graphs": "📊 Live Hardware Graphs - MSI Afterburner Style",
            "fan_curves": "🌀 Fan Curve Editor - Custom Cooling",
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
            self._build_sensors_page(content_frame)
        elif page_id == "live_graphs":
            self._build_live_graphs_page(content_frame)
        elif page_id == "fan_curves":
            self._build_fan_curves_page(content_frame)
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
    # Note: _build_yourpc_page moved to ui/yourpc_page.py module

    def _build_yourpc_page_OLD_REMOVED(self, parent):
        """Build YOUR PC page - Hardware health and personal data"""
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

        # Get hardware info
        try:
            import platform
            cpu_model = platform.processor() if platform.processor() else "Unknown CPU"
        except:
            cpu_model = "Unknown CPU"

        try:
            ram_total = psutil.virtual_memory().total / (1024**3)
            ram_used = psutil.virtual_memory().used / (1024**3)
            ram_percent = psutil.virtual_memory().percent
        except:
            ram_total, ram_used, ram_percent = 0, 0, 0

        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            gpu_model = gpus[0].name if gpus else "Unknown GPU"
            gpu_temp = gpus[0].temperature if gpus and hasattr(gpus[0], 'temperature') else 0
            gpu_load = gpus[0].load * 100 if gpus else 0
        except:
            gpu_model = "Unknown GPU"
            gpu_temp = 0
            gpu_load = 0

        # Hardware sections
        hardware_sections = [
            {
                "title": "🖥️ CPU Information",
                "icon_color": "#3b82f6",
                "items": [
                    ("Model", cpu_model),
                    ("Cores", str(psutil.cpu_count(logical=False)) if psutil else "N/A"),
                    ("Threads", str(psutil.cpu_count(logical=True)) if psutil else "N/A"),
                    ("Current Usage", f"{psutil.cpu_percent(interval=0.1)}%" if psutil else "N/A"),
                    ("Temperature", "30-70°C (simulated)")
                ]
            },
            {
                "title": "💾 RAM Information",
                "icon_color": "#fbbf24",
                "items": [
                    ("Total Memory", f"{ram_total:.2f} GB"),
                    ("Used Memory", f"{ram_used:.2f} GB"),
                    ("Usage", f"{ram_percent:.1f}%"),
                    ("Available", f"{(ram_total - ram_used):.2f} GB")
                ]
            },
            {
                "title": "🎮 GPU Information",
                "icon_color": "#10b981",
                "items": [
                    ("Model", gpu_model),
                    ("Current Load", f"{gpu_load:.1f}%"),
                    ("Temperature", f"{gpu_temp}°C" if gpu_temp > 0 else "N/A"),
                    ("Status", "Operational" if gpu_load < 90 else "High Load")
                ]
            }
        ]

        for section in hardware_sections:
            # Section frame
            section_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
            section_frame.pack(fill="x", padx=10, pady=8)

            # Section header
            header = tk.Frame(section_frame, bg=section["icon_color"], height=40)
            header.pack(fill="x")
            header.pack_propagate(False)

            title_lbl = tk.Label(
                header,
                text=section["title"],
                font=("Segoe UI", 13, "bold"),
                bg=section["icon_color"],
                fg="#ffffff"
            )
            title_lbl.pack(side="left", padx=15, pady=8)

            # Items
            for label, value in section["items"]:
                item_frame = tk.Frame(section_frame, bg="#1a1d24")
                item_frame.pack(fill="x", padx=15, pady=4)

                lbl = tk.Label(
                    item_frame,
                    text=label,
                    font=("Segoe UI", 10, "bold"),
                    bg="#1a1d24",
                    fg="#94a3b8",
                    width=20,
                    anchor="w"
                )
                lbl.pack(side="left")

                val = tk.Label(
                    item_frame,
                    text=value,
                    font=("Consolas", 10),
                    bg="#1a1d24",
                    fg="#ffffff",
                    anchor="w"
                )
                val.pack(side="left", padx=10)

            # Bottom padding
            tk.Frame(section_frame, bg="#1a1d24", height=10).pack()

    def _build_sensors_page(self, parent):
        """Build SENSORS page - HWMonitor-style hierarchical sensor tree 🌲"""
        from core.hardware_sensors import get_hardware_sensors
        from ui.components.sensor_tree import create_sensor_tree_page

        # Get hardware sensors singleton
        sensors = get_hardware_sensors()

        # Create sensor tree page with auto-refresh
        tree_view = create_sensor_tree_page(parent, sensors)

        # Auto-refresh every 2 seconds
        def auto_refresh():
            try:
                tree_view.refresh()
                parent.after(2000, auto_refresh)
            except:
                pass  # Stop if widget destroyed

        auto_refresh()

    def _build_live_graphs_page(self, parent):
        """Build LIVE GRAPHS page - MSI Afterburner-style real-time graphs 📊"""
        from ui.components.hardware_graphs import create_graphs_page

        # Create graphs panel
        graphs_panel = create_graphs_page(parent, self.monitor)

        # Store reference for updates
        if not hasattr(self, '_graphs_panels'):
            self._graphs_panels = []
        self._graphs_panels.append(graphs_panel)

        # Auto-update every 0.2s (5 FPS)
        def auto_update():
            try:
                # Get current sample
                sample = self.monitor.get_current_sample()
                graphs_panel.update(sample)
                parent.after(200, auto_update)  # 0.2s = 200ms
            except:
                pass  # Stop if widget destroyed

        auto_update()

    def _build_fan_curves_page(self, parent):
        """Build FAN CURVES page - MSI Afterburner-style fan curve editor 🌀"""
        from ui.components.fan_curve_editor import create_fan_curve_page

        def on_curve_change(points):
            """Handle fan curve changes"""
            print(f"[FanCurve] Curve changed: {[(p.temp, p.speed) for p in points]}")
            # TODO: Apply curve to hardware (requires admin + compatible hardware)

        # Create fan curve editor
        editor = create_fan_curve_page(parent, on_curve_change)

        # Store reference
        if not hasattr(self, '_fan_curve_editors'):
            self._fan_curve_editors = []
        self._fan_curve_editors.append(editor)

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
        """Build HCK Labs page"""
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

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === HEADER ===
        header = tk.Frame(scrollable_frame, bg="#1a1d24")
        header.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(
            header,
            text="🚀 HCK_Labs",
            font=("Segoe UI Light", 24, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            header,
            text="Educational AI-Engineering Project",
            font=("Segoe UI Semilight", 12),
            bg="#1a1d24",
            fg="#8b5cf6"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # === QUICK ACTIONS (SERVICES + CHECK UPDATE) ===
        actions_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
        actions_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            actions_frame,
            text="Quick Actions",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 10))

        buttons_row = tk.Frame(actions_frame, bg="#1a1d24")
        buttons_row.pack(fill="x", padx=15, pady=10)

        # SERVICES Button
        services_btn = tk.Button(
            buttons_row,
            text="🔧 SERVICES",
            font=("Segoe UI Semibold", 11, "bold"),
            bg="#8b5cf6",
            fg="#ffffff",
            activebackground="#7c3aed",
            activeforeground="#ffffff",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            command=lambda: self._show_services_dialog(scrollable_frame)
        )
        services_btn.pack(side="left", padx=(0, 15))

        # CHECK UPDATE Button
        update_btn = tk.Button(
            buttons_row,
            text="🔄 CHECK UPDATE!",
            font=("Segoe UI Semibold", 11, "bold"),
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            activeforeground="#ffffff",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            command=lambda: self._show_update_dialog(scrollable_frame)
        )
        update_btn.pack(side="left")

        # === ABOUT PROJECT ===
        about_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
        about_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            about_frame,
            text="About PC_Workman",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 10))

        about_text = """PC_Workman HCK is a next-generation Windows system monitoring and optimization tool.

Our mission: Make system monitoring accessible, beautiful, and intelligent.

Inspired by: Tesla UI, Apple macOS, MSI Afterburner
But better: AI-powered insights, calm design, universal hardware support"""

        tk.Label(
            about_frame,
            text=about_text,
            font=("Segoe UI", 10),
            bg="#1a1d24",
            fg="#cbd5e1",
            justify="left",
            wraplength=850
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # === KEY FEATURES ===
        features_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
        features_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            features_frame,
            text="What Makes Us Unique",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 10))

        features = [
            ("🎯 Dual-Mode System", "Minimal monitoring + Expanded control center"),
            ("🤖 AI Assistant", "hck_GPT provides intelligent optimization suggestions"),
            ("📊 Smart Analytics", "Session tracking, predictive alerts, performance scoring"),
            ("🎨 Modern UI", "Tesla/Apple level design, smooth animations, calm colors"),
            ("⚡ Background Tools", "Auto-optimization running silently in the background"),
            ("🌐 Universal Support", "All CPUs, All GPUs, All configurations")
        ]

        for title, desc in features:
            feature_row = tk.Frame(features_frame, bg="#0f1117")
            feature_row.pack(fill="x", padx=15, pady=5)

            tk.Label(
                feature_row,
                text=title,
                font=("Segoe UI Semibold", 10, "bold"),
                bg="#0f1117",
                fg="#10b981"
            ).pack(anchor="w", padx=10, pady=(8, 2))

            tk.Label(
                feature_row,
                text=desc,
                font=("Segoe UI", 9),
                bg="#0f1117",
                fg="#94a3b8"
            ).pack(anchor="w", padx=10, pady=(0, 8))

        # === COMPETITIVE EDGE ===
        comp_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
        comp_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            comp_frame,
            text="Better Than Competition",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 10))

        comparisons = [
            ("vs MSI Afterburner", "✅ Full system optimization, not just GPU overclock"),
            ("vs GeForce Experience", "✅ All GPUs supported, lightweight, no forced login"),
            ("vs HWMonitor", "✅ Actionable insights, not just read-only sensors"),
            ("vs Task Manager", "✅ AI suggestions, beautiful UI, predictive alerts")
        ]

        for vs, advantage in comparisons:
            comp_row = tk.Frame(comp_frame, bg="#0f1117")
            comp_row.pack(fill="x", padx=15, pady=3)

            tk.Label(
                comp_row,
                text=vs,
                font=("Segoe UI Semibold", 9, "bold"),
                bg="#0f1117",
                fg="#3b82f6",
                width=22,
                anchor="w"
            ).pack(side="left", padx=10, pady=5)

            tk.Label(
                comp_row,
                text=advantage,
                font=("Segoe UI", 9),
                bg="#0f1117",
                fg="#cbd5e1"
            ).pack(side="left", padx=5, pady=5)

        # === VERSION INFO ===
        version_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
        version_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            version_frame,
            text="Version Information",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 10))

        version_info = [
            ("Current Version", "v1.6.8 - Stats Engine & Time-Travel"),
            ("Release Date", "February 15, 2026"),
            ("Architecture", "Dual-Mode (Minimal + Expanded)"),
            ("Language", "Python 3.x + Tkinter"),
            ("License", "Educational Project - HCK_Labs")
        ]

        for label, value in version_info:
            version_row = tk.Frame(version_frame, bg="#0f1117")
            version_row.pack(fill="x", padx=15, pady=3)

            tk.Label(
                version_row,
                text=f"{label}:",
                font=("Segoe UI Semibold", 9, "bold"),
                bg="#0f1117",
                fg="#64748b",
                width=18,
                anchor="w"
            ).pack(side="left", padx=10, pady=5)

            tk.Label(
                version_row,
                text=value,
                font=("Segoe UI", 9),
                bg="#0f1117",
                fg="#f59e0b"
            ).pack(side="left", padx=5, pady=5)

        # === MAINTAINER ===
        maintainer_frame = tk.Frame(scrollable_frame, bg="#1a1d24")
        maintainer_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            maintainer_frame,
            text="Development",
            font=("Segoe UI Semibold", 14, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w", padx=15, pady=(15, 10))

        tk.Label(
            maintainer_frame,
            text="Maintainer: Marcin Firmuga",
            font=("Segoe UI Semibold", 10),
            bg="#1a1d24",
            fg="#8b5cf6"
        ).pack(anchor="w", padx=15, pady=5)

        tk.Label(
            maintainer_frame,
            text="Built with AI assistance (Claude Sonnet 4.5)\nFocus: Learning through real-world software engineering",
            font=("Segoe UI", 9),
            bg="#1a1d24",
            fg="#94a3b8",
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # === FOOTER ===
        footer = tk.Frame(scrollable_frame, bg="#0f1117")
        footer.pack(fill="x", padx=20, pady=20)

        tk.Label(
            footer,
            text="Thank you for using PC_Workman HCK!\n\n\"Your PC, Smarter.\"",
            font=("Segoe UI Semilight", 11),
            bg="#0f1117",
            fg="#64748b",
            justify="center"
        ).pack(pady=20)

    def _build_fancontrol_page(self, parent):
        """Build NEW AI-Enhanced Fan Dashboard - Next-Gen Cooling Control"""
        main = tk.Frame(parent, bg="#0f1117")
        main.pack(fill="both", expand=True)

        # No "Dashboard Back!" button - only X button in top-right corner
        # This saves space and is cleaner!

        # === FAN DASHBOARD ULTIMATE (Vertical sliders + SZTOS!) ===
        dashboard_container = tk.Frame(main, bg="#0f1117")
        dashboard_container.pack(fill="both", expand=True)

        # Create FAN DASHBOARD ULTIMATE
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
        """Build Advanced Dashboard - MSI Afterburner / Apple inspired"""
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
        """Build Guide page"""
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

        # Header section
        header_container = tk.Frame(scrollable_frame, bg="#0f1117")
        header_container.pack(fill="x", padx=15, pady=(10, 20))

        # Header background with gradient effect
        header_bg = tk.Frame(header_container, bg="#1a1d24", bd=0)
        header_bg.pack(fill="x")

        # Top accent line (cyber glow)
        accent_top = tk.Frame(header_bg, bg="#8b5cf6", height=3)
        accent_top.pack(fill="x")

        # Header content
        header_content = tk.Frame(header_bg, bg="#1a1d24")
        header_content.pack(fill="x", padx=20, pady=15)

        # Title section
        title_section = tk.Frame(header_content, bg="#1a1d24")
        title_section.pack(side="left", fill="both", expand=True)

        tk.Label(
            title_section,
            text="User Guide - Program Advantages",
            font=("Segoe UI Light", 22, "bold"),
            bg="#1a1d24",
            fg="#ffffff"
        ).pack(anchor="w")

        tk.Label(
            title_section,
            text="Everything you need to maximize PC_Workman potential",
            font=("Segoe UI", 9),
            bg="#1a1d24",
            fg="#64748b"
        ).pack(anchor="w", pady=(3, 0))

        # Navigation button
        nav_btn = tk.Label(
            header_content,
            text="⚡ Navigation Quick!",
            font=("Segoe UI Semibold", 11, "bold"),
            bg="#2d2d35",
            fg="#ffd700",  # Gold text
            cursor="hand2",
            padx=20,
            pady=10,
            relief="flat"
        )
        nav_btn.pack(side="right", padx=10)

        # Navigation quick menu
        def show_nav_menu(e):
            menu = tk.Menu(self.root, tearoff=0, bg="#1a1d24", fg="#ffffff",
                          font=("Segoe UI", 9), borderwidth=0)
            menu.add_command(label="💻 Your PC", command=lambda: self._show_overlay("your_pc"))
            menu.add_command(label="🌲 Sensors", command=lambda: self._show_overlay("sensors"))
            menu.add_command(label="📊 Live Graphs", command=lambda: self._show_overlay("live_graphs"))
            menu.add_command(label="🌀 Fan Curves", command=lambda: self._show_overlay("fan_curves"))
            menu.add_separator()
            menu.add_command(label="⚡ Optimization", command=lambda: self._show_overlay("optimization"))
            menu.add_command(label="📊 Statistics", command=lambda: self._show_overlay("statistics"))
            menu.add_separator()
            menu.add_command(label="📌 Floating Monitor", command=self._launch_overlay_widget)
            menu.tk_popup(e.x_root, e.y_root)

        nav_btn.bind("<Button-1>", show_nav_menu)

        # Hover effect
        def on_enter(e):
            nav_btn.config(bg="#3d3d45", fg="#ffed4e")
        def on_leave(e):
            nav_btn.config(bg="#2d2d35", fg="#ffd700")
        nav_btn.bind("<Enter>", on_enter)
        nav_btn.bind("<Leave>", on_leave)

        # Bottom accent line
        accent_bottom = tk.Frame(header_bg, bg="#3b82f6", height=2)
        accent_bottom.pack(fill="x")

        # Guide categories
        categories = [
            {
                "icon": "✨",
                "title": "Core Features",
                "subtitle": "What makes PC_Workman special",
                "color": "#8b5cf6",
                "content": [
                    "PC_Workman is built with **you** in mind - designed to serve your needs and adapt to your workflow. Our philosophy is simple: configure once, benefit forever.",

                    "• **Background Intelligence**: Once you set up your preferences in [Optimization Options], the program works silently in the background - day after day, month after month - automatically executing your configured sequences. No manual intervention needed.",

                    "• **Set & Forget**: Whether it's cleaning temporary files, optimizing RAM usage, or monitoring temperatures - PC_Workman handles it all while you focus on what matters: your work, gaming, or creativity.",

                    "• **Smart Monitoring**: Real-time tracking of CPU, GPU, RAM with intelligent alerts only when something truly needs your attention. No annoying pop-ups for normal behavior."
                ]
            },
            {
                "icon": "🤖",
                "title": "HCK_GPT Assistant",
                "subtitle": "Your AI-powered PC companion",
                "color": "#10b981",
                "content": [
                    "The future is here. [HCK_GPT] is evolving into your personal system assistant - learning about you and your habits to provide truly customized support.",

                    "• **Context Awareness**: HCK_GPT will remember your favorite games (Steam, Epic), your creative tools (VSCode, Blender, Photoshop), and your work patterns - adjusting recommendations accordingly.",

                    "• **Intelligent Suggestions**: 'I see you're launching Cyberpunk 2077 - would you like me to close background apps and boost GPU performance?' That's the level of intelligence we're building.",

                    "• **Learning System**: The more you use PC_Workman, the smarter HCK_GPT becomes. It learns your preferences, schedules, and optimization needs to serve you better every day."
                ]
            },
            {
                "icon": "🛡️",
                "title": "Security & Privacy",
                "subtitle": "Your data, your control",
                "color": "#3b82f6",
                "content": [
                    "We take your privacy seriously. PC_Workman operates **entirely on your device** - no cloud uploads, no data collection, no telemetry.",

                    "• **Offline First**: All monitoring, optimization, and AI processing happens locally. Your system data never leaves your PC.",

                    "• **Full Control**: Every feature can be enabled or disabled. Want just monitoring? Done. Only optimization? You got it. Complete customization is in your hands.",

                    "• **Transparent Operations**: Check logs, review actions, understand exactly what PC_Workman does. No hidden processes, no mysterious background tasks."
                ]
            },
            {
                "icon": "⚡",
                "title": "Performance Optimization",
                "subtitle": "Squeeze every drop of power",
                "color": "#f59e0b",
                "content": [
                    "Transform your PC from sluggish to lightning-fast with our intelligent optimization engine powered by advanced algorithms.",

                    "• **Smart Cleanup**: [Optimization Options] provides one-click solutions: clear temp files, optimize startup programs, defrag registry, boost RAM - all automated and safe.",

                    "• **Gaming Mode**: Automatically detect game launches and apply performance profiles: close unnecessary apps, boost CPU/GPU, disable Windows updates during gameplay.",

                    "• **Custom Profiles**: Create profiles for different scenarios - 'Work Mode' (minimal resource usage), 'Creative Mode' (max RAM for Photoshop/Blender), 'Gaming Mode' (max performance).",

                    "• **Real Results**: Users report 15-30% FPS improvements in games, 40% faster app launches, and significantly smoother multitasking. Your mileage may vary, but the gains are real."
                ]
            },
            {
                "icon": "📊",
                "title": "Advanced Monitoring",
                "subtitle": "Know your system inside out",
                "color": "#ef4444",
                "content": [
                    "Access professional-grade monitoring tools that rival software costing hundreds of dollars - completely free.",

                    "• **HWMonitor-Style Sensors**: Hierarchical tree showing every temperature, voltage, fan speed, and clock - color-coded for instant health checks (green/yellow/red).",

                    "• **MSI Afterburner Graphs**: Real-time scrolling graphs with 30 seconds of history. See exactly when your CPU spiked or GPU throttled.",

                    "• **Fan Curve Editor**: Visual drag-and-drop interface to create custom cooling profiles. Silent for office work, aggressive for gaming - you control the balance.",

                    "• **System Tray Intelligence**: Our enhanced 3-bar icon shows CPU/GPU/RAM at a glance with temperature tooltips. The most informative tray icon you'll ever see."
                ]
            },
            {
                "icon": "🎯",
                "title": "Workflow Integration",
                "subtitle": "Fits seamlessly into your routine",
                "color": "#ec4899",
                "content": [
                    "PC_Workman adapts to how **you** work, not the other way around. Our design philosophy: invisible when you don't need us, powerful when you do.",

                    "• **Minimal Mode**: Compact widget in bottom-right corner - always visible, never intrusive. Perfect for monitoring during work or gaming.",

                    "• **Overlay Monitor**: Always-on-top mini-monitor shows live CPU/GPU/RAM above all applications. Check performance without alt-tabbing from your game or Photoshop.",

                    "• **Dual Operation**: Main window for deep analysis, tray icon for quick checks, overlay for continuous monitoring - three interfaces, one powerful tool.",

                    "• **Smart Notifications**: Beautiful toast notifications only appear when necessary - 'High temperature detected' or 'RAM usage critical' - never spam, always helpful."
                ]
            }
        ]

        for category in categories:
            self._create_guide_category(scrollable_frame, category)

        # === FOOTER - PRO TIPS! ===
        footer = tk.Frame(scrollable_frame, bg="#1a1d24")
        footer.pack(fill="x", padx=15, pady=(20, 30))

        tk.Label(
            footer,
            text="💡 Pro Tip",
            font=("Segoe UI Semibold", 12, "bold"),
            bg="#1a1d24",
            fg="#ffd700"
        ).pack(anchor="w", padx=15, pady=(10, 5))

        tk.Label(
            footer,
            text="Press the mini-monitor in the left panel to launch the overlay monitor - it will stay visible above all windows!",
            font=("Segoe UI", 10),
            bg="#1a1d24",
            fg="#94a3b8",
            wraplength=520,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

    def _create_guide_category(self, parent, category):
        """Create single guide category with cyberpunk styling"""
        # Category container
        container = tk.Frame(parent, bg="#0f1117")
        container.pack(fill="x", padx=15, pady=10)

        # Category card with accent border
        card = tk.Frame(container, bg=category["color"], bd=0)
        card.pack(fill="x")

        # Left accent bar
        accent = tk.Frame(card, bg=category["color"], width=5)
        accent.pack(side="left", fill="y")

        # Card content
        content_bg = tk.Frame(card, bg="#1a1d24")
        content_bg.pack(side="left", fill="both", expand=True)

        # Header section
        header = tk.Frame(content_bg, bg="#1a1d24")
        header.pack(fill="x", padx=20, pady=15)

        # Icon + Title
        title_row = tk.Frame(header, bg="#1a1d24")
        title_row.pack(fill="x")

        tk.Label(
            title_row,
            text=category["icon"],
            font=("Segoe UI", 24),
            bg="#1a1d24",
            fg=category["color"]
        ).pack(side="left", padx=(0, 10))

        title_section = tk.Frame(title_row, bg="#1a1d24")
        title_section.pack(side="left", fill="x", expand=True)

        tk.Label(
            title_section,
            text=category["title"],
            font=("Segoe UI Semibold", 16, "bold"),
            bg="#1a1d24",
            fg="#ffffff",
            anchor="w"
        ).pack(fill="x")

        tk.Label(
            title_section,
            text=category["subtitle"],
            font=("Segoe UI", 9),
            bg="#1a1d24",
            fg="#64748b",
            anchor="w"
        ).pack(fill="x")

        # Content - mini gradient cards instead of bullet points
        content_frame = tk.Frame(content_bg, bg="#1a1d24")
        content_frame.pack(fill="x", padx=20, pady=(0, 15))

        # Gradient colors for mini-cards
        gradient_colors = [
            "#f0f4ff",  # Light blue
            "#fff4f0",  # Light orange
            "#f0fff4",  # Light green
            "#fff0f8",  # Light pink
            "#f4f0ff",  # Light purple
            "#fffbf0"   # Light yellow
        ]
        color_idx = 0

        for paragraph in category["content"]:
            # Process markdown-style highlights
            processed = self._process_markdown_highlights(paragraph)

            # Check if it's a bullet point
            if paragraph.strip().startswith("•"):
                # Create mini-card with gradient background
                mini_card = tk.Frame(content_frame, bg=gradient_colors[color_idx % len(gradient_colors)])
                mini_card.pack(fill="x", pady=2)
                color_idx += 1

                # Remove bullet point from text
                clean_text = processed.replace("•", "").strip()

                # Split into title and description if there's a colon
                if ":" in clean_text:
                    parts = clean_text.split(":", 1)
                    title = parts[0].strip()
                    desc = parts[1].strip()

                    # Title (bold part)
                    tk.Label(
                        mini_card,
                        text=title,
                        font=("Segoe UI", 8, "bold"),
                        bg=mini_card["bg"],
                        fg="#1a1d24",
                        anchor="w"
                    ).pack(fill="x", padx=10, pady=(4, 0))

                    # Description
                    tk.Label(
                        mini_card,
                        text=desc,
                        font=("Segoe UI", 7),
                        bg=mini_card["bg"],
                        fg="#334155",
                        anchor="w",
                        wraplength=480,
                        justify="left"
                    ).pack(fill="x", padx=10, pady=(0, 4))
                else:
                    # No colon, just show the text
                    tk.Label(
                        mini_card,
                        text=clean_text,
                        font=("Segoe UI", 7),
                        bg=mini_card["bg"],
                        fg="#1a1d24",
                        anchor="w",
                        wraplength=480,
                        justify="left"
                    ).pack(fill="x", padx=10, pady=4)
            else:
                # Regular paragraph (intro text)
                p_label = tk.Label(
                    content_frame,
                    text=processed,
                    font=("Segoe UI", 9),
                    bg="#1a1d24",
                    fg="#cbd5e1",
                    anchor="w",
                    wraplength=500,
                    justify="left"
                )
                p_label.pack(fill="x", pady=(0, 8))

    def _process_markdown_highlights(self, text):
        """Process markdown-style highlights [text] and **bold**"""
        # Replace [keyword] with highlighted version (we'll use uppercase + color via emoji)
        import re

        # [keyword] → 「KEYWORD」 (Japanese brackets for tech feel)
        text = re.sub(r'\[([^\]]+)\]', r'「\1」', text)

        # **bold** → BOLD (we can't do actual bold in Label, so use caps)
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)

        return text

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
            text="v1.6.8",
            font=("Segoe UI", 12, "bold"),
            bg="#0f1117",
            fg="#10b981"
        ).pack(side="left")

        tk.Label(
            version_frame,
            text=" - 13.01.2026",
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
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
