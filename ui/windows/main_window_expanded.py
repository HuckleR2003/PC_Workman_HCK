# ui/main_window_expanded.py
"""
PC Workman - EXPANDED MODE (Main Window) v1.7.1
980x500 resolution, centered, full-featured interface
Full-featured interface with modern dark theme
"""

import tkinter as tk
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
from ui.components.led_bars import AnimatedBar
from ui.components.sidebar_nav import SidebarNav
from ui.pages.fan_control import create_fans_hardware_page, create_fans_usage_stats_page

# Centralized i18n - initialize active language from saved settings at import time
try:
    from utils.i18n import t as _t, set_lang as _i18n_set_lang, register_on_change as _i18n_register
    _HAS_I18N_MW = True
except ImportError:
    _HAS_I18N_MW = False
    def _t(key: str, **kwargs) -> str:
        return key.split(".")[-1].replace("_", " ").title()
    def _i18n_set_lang(code: str) -> None: pass
    def _i18n_register(fn) -> None: pass

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

# ── Font system ────────────────────────────────────────────────────────────────
try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR  = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

# InteractiveChart (replaces old canvas chart)
try:
    from ui.components.interactive_chart import InteractiveChart as _InteractiveChart
except ImportError:
    _InteractiveChart = None

# ── Dynamic scaling ────────────────────────────────────────────────────────────
try:
    import utils.ui_scale as _uis
except ImportError:
    class _uis:  # fallback stub
        SCALE = 1.0
        @staticmethod
        def init(_root): pass
        @staticmethod
        def compact_w(): return 1160
        @staticmethod
        def compact_h(): return 575
        @staticmethod
        def sidebar_width(): return 180


class ExpandedMainWindow:
    """
    Expanded Mode - Full-featured 980x500 window
    - Modern header with mode switcher
    - Session average bars (CPU/GPU/RAM)
    - Advanced chart
    - Category navigation
    - Dark theme with gradient accents
    """

    # Pages where the hck_GPT banner stays visible (chat available on top).
    # "your_pc" and "fan_control" ride the overlay system — _show_overlay
    # lifts the banner above the overlay frame for them.
    _GPT_BANNER_PAGES = {"dashboard", "fan_control", "your_pc"}

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

        # ── Animation after() IDs — tracked so they can be cancelled on page switch ──
        self._anim_ai_cursor_id   = None
        self._anim_ai_typing_id   = None
        self._bar_anim_id         = None

        # ── Persistent LIVE chart buffer - survives view switches ─────────────
        # DO NOT reset in _build_dashboard_view(); data accumulates here forever.
        self.chart_data = {"cpu": [], "ram": [], "gpu": []}
        self.chart_max_samples = 100
        self.chart_filter = "LIVE"
        self._historical_chart_data = None
        self._chart_after_id = None

        # Maximize state
        self._is_maximized = False

        # System Tray
        self.tray_manager = None
        self._init_system_tray()

        # Create root window
        self.root = tk.Tk()
        _uis.init(self.root)  # detect screen size → set SCALE
        self.root.title("PC Workman HCK  v1.8.1")
        self.root.geometry(f"{_uis.compact_w()}x{_uis.compact_h()}")
        self.root.configure(bg=THEME["bg_main"])
        self.root.resizable(False, False)

        # Window / taskbar icon — new HCK brand icon (BUNDLE_DIR-aware for frozen EXE)
        try:
            from utils.paths import BUNDLE_DIR as _BUNDLE_DIR
            _win_ico_path = os.path.join(_BUNDLE_DIR, "data", "icons", "app_icon.png")
        except Exception:
            _win_ico_path = os.path.join("data", "icons", "app_icon.png")
        try:
            if Image and ImageTk and os.path.exists(_win_ico_path):
                self._win_icon = ImageTk.PhotoImage(Image.open(_win_ico_path))
                self.root.iconphoto(True, self._win_icon)
        except Exception:
            pass

        # Load navigation icons (AFTER root window creation)
        self.nav_icons = {}
        self.nav_icons_hover = {}
        self._load_navigation_icons()

        # Handle window close (X button) -> minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Center window on screen
        self._center_window()

        # Build UI
        self._build_ui()

        # Start update loop - AFTER() BASED, NO THREADING
        self._running = True
        self._update_counter = 0
        self.root.after(100, self._update_loop)  # Start after 100ms

        # ── Startup + App-install watcher ─────────────────────────────────────
        self._start_system_watchers()

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

        # BUNDLE_DIR-aware path: relative "data/icons" breaks in frozen EXE
        # when the process CWD differs from the install dir.
        try:
            from utils.paths import BUNDLE_DIR
            icons_dir = os.path.join(BUNDLE_DIR, "data", "icons")
        except ImportError:
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
        width  = _uis.compact_w()
        height = _uis.compact_h()
        screen_width  = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width  // 2) - (width  // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        """Build complete UI"""
        # MAIN CONTAINER (sidebar + content)
        self.main_container = tk.Frame(self.root, bg=THEME["bg_main"])
        self.main_container.pack(fill="both", expand=True)

        # LEFT SIDEBAR (Snyk Evo style)
        self.sidebar = SidebarNav(
            self.main_container,
            width=_uis.sidebar_width(),
            on_navigate=self._handle_sidebar_navigation
        )
        self.sidebar.pack(side="left", fill="y")

        # Apply saved settings immediately (language + auto-hide)
        try:
            import json, os as _os
            _sf = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
                                "settings", "app_settings.json")
            with open(_sf, "r", encoding="utf-8") as _f:
                _s = json.load(_f)
            # Initialize i18n language BEFORE sidebar is fully built
            _saved_lang = _s.get("language", "en")
            if _saved_lang != "en":
                _i18n_set_lang(_saved_lang)
            if _s.get("sidebar_auto_hide", False):
                self.sidebar.set_auto_hide(True)
        except Exception:
            pass

        # RIGHT CONTENT AREA
        self.content_area = tk.Frame(self.main_container, bg=THEME["bg_main"])
        self.content_area.pack(side="left", fill="both", expand=True)

        # Track current view
        self.current_view = "dashboard"
        self.dashboard_widgets = []  # Store dashboard widgets for show/hide

        # Build dashboard view (default)
        self._build_dashboard_view()

        # Register live-refresh callback for language changes
        _i18n_register(self._on_lang_changed)

    def _build_dashboard_view(self):
        """Build the main dashboard view"""
        self._build_header()
        self._build_middle_section()

        if self._is_maximized:
            self._build_content_area_maximized()
        else:
            self._build_content_area()

        self._build_hckgpt_banner()

    def _switch_to_page(self, page_id):
        """Switch content area to a specific page (replaces dashboard)"""
        print(f"[Switch] Switching to page: {page_id} (current: {self.current_view})")

        if self.current_view == page_id and page_id != "dashboard":
            return

        # Cancel all dashboard after() timers before destroying widgets
        # (prevents "bad window path" errors and stops accumulation on repeated switches)
        _cancel_ids = [
            '_chart_after_id', '_bar_anim_id',
            '_anim_ai_cursor_id', '_anim_ai_typing_id',
        ]
        for _attr in _cancel_ids:
            _aid = getattr(self, _attr, None)
            if _aid is not None:
                try:
                    self.root.after_cancel(_aid)
                except Exception:
                    pass
                setattr(self, _attr, None)

        # Chart pin does not survive a section change
        self._chart_pin_idx = None
        self._chart_hide_tip()

        # Kill overlay immediately (no animation) to prevent race conditions
        if self.overlay_frame:
            try:
                self.overlay_frame.destroy()
            except Exception:
                pass
            self.overlay_frame = None
            self.active_overlay = None

        # Preserve gpt_panel.frame — chat history must survive all page switches.
        # The frame uses place() geometry; hide it on pages without the banner,
        # re-shown by _build_hckgpt_banner on pages that carry it.
        _gpt_frame = getattr(getattr(self, "gpt_panel", None), "frame", None)
        if _gpt_frame is not None and page_id not in self._GPT_BANNER_PAGES:
            try:
                if _gpt_frame.winfo_exists():
                    _gpt_frame.place_forget()
            except Exception:
                pass

        for widget in self.content_area.winfo_children():
            if _gpt_frame is not None and widget is _gpt_frame:
                continue   # never destroy the chat panel
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

        # Direct pages that carry the hck_GPT banner (dashboard adds its own,
        # overlay pages are handled inside _show_overlay)
        if page_id == "fan_control":
            self._build_hckgpt_banner()

    def _build_page_header(self, title: str, subtitle: str = "",
                            accent: str = "#8b5cf6") -> tk.Frame:
        """
        Modern gradient canvas header for direct-navigation pages.
        64 px · vertical gradient · left accent bar · title + subtitle.
        Bottom-right: ‹ Dashboard back link.
        Top-right:    ⤢ / ⊡ maximize toggle (same as dashboard header).
        """
        container = tk.Frame(self.content_area, bg="#080b10")
        container.pack(fill="x")

        cv = tk.Canvas(container, bg="#080b10", height=64, highlightthickness=0)
        cv.pack(fill="both", expand=True)

        def _draw(e=None):
            cv.delete("all")
            W = cv.winfo_width()
            if W < 10:
                return
            H = 64
            for y in range(H):
                t = y / H
                r = int(8  + 10 * t)
                g = int(11 + 11 * t)
                b = int(16 + 22 * t)
                cv.create_line(0, y, W, y, fill=f"#{r:02x}{g:02x}{b:02x}")
            cv.create_line(0, H - 1, W, H - 1, fill="#1e2840")
            cv.create_rectangle(0, 0, 3, H, fill=accent, outline="")
            cv.create_text(18, 19, text=title, anchor="w",
                           font=(_HDR, 12), fill="#c4cfdf")
            if subtitle:
                cv.create_text(18, 44, text=subtitle, anchor="w",
                               font=(_BODY, 8), fill="#3d4a60")
            # Back link — bottom-right
            cv.create_text(W - 10, 54, text=f"‹ {_t('nav.back_dashboard')}",
                           anchor="e", font=(_BODY, 7), fill="#273448",
                           tags="back_tag")

        cv.bind("<Configure>", _draw)

        # Back navigation
        def _go_back(e=None):
            self._switch_to_page("dashboard")
            if hasattr(self, "sidebar") and self.sidebar:
                self.sidebar.set_active_page("dashboard")

        cv.tag_bind("back_tag", "<Button-1>", _go_back)
        cv.tag_bind("back_tag", "<Enter>",
                    lambda e: cv.itemconfig("back_tag", fill="#8b5cf6"))
        cv.tag_bind("back_tag", "<Leave>",
                    lambda e: cv.itemconfig("back_tag", fill="#273448"))

        # ── Maximize toggle button (top-right, overlaid on canvas) ────────────
        _max_sym = "⊡" if self._is_maximized else "⤢"
        max_btn = tk.Label(
            container,
            text=_max_sym,
            font=(_HDR, 10),
            bg="#090c14",      # matches gradient at y≈8
            fg="#6f86a3",
            cursor="hand2",
            padx=10,
        )
        max_btn.place(relx=1.0, y=8, anchor="ne", x=-8)
        max_btn.bind("<Button-1>", lambda e: self._toggle_maximize())
        max_btn.bind("<Enter>",    lambda e: max_btn.config(fg="#8b5cf6"))
        max_btn.bind("<Leave>",    lambda e: max_btn.config(fg="#6f86a3"))

        return container

    def _build_fans_hardware_view(self):
        """Build FANS - Hardware Info as main view"""
        self._build_page_header("FANS — HARDWARE", "Real-time fan monitoring & sensors", "#f59e0b")

        # Content
        content = tk.Frame(self.content_area, bg="#0a0e14")
        content.pack(fill="both", expand=True)

        create_fans_hardware_page(content, self.monitor)

    def _build_fans_usage_stats_view(self):
        """Build Usage Statistics as main view"""
        self._build_page_header("FAN STATISTICS", "Fan intensity over time", "#f59e0b")

        # Content
        content = tk.Frame(self.content_area, bg="#0a0e14")
        content.pack(fill="both", expand=True)

        create_fans_usage_stats_page(content, self.monitor)

    def _build_fan_dashboard_view(self):
        """Build Fan Dashboard as main view"""
        self._build_page_header("FAN DASHBOARD", "Cooling control center & profiles", "#f59e0b")

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
                font=(_BODY, 12),
                bg="#0f1117",
                fg="#6b7280"
            ).pack(pady=50)

    def _build_monitoring_alerts_view(self):
        """Build Monitoring & Alerts page with Time-Travel charts"""
        self._build_page_header("MONITORING & ALERTS",
                                "Temperatures · Voltages · System health", "#f59e0b")
        from ui.pages.monitoring_alerts import build_monitoring_alerts_page
        build_monitoring_alerts_page(self, self.content_area)

    def _build_first_setup_view(self):
        """Build First Setup & Drivers page - driver health, startup, checklist."""
        from ui.pages.first_setup_drivers import build_first_setup_page
        build_first_setup_page(self, self.content_area)

    def _build_optimization_view(self):
        # No _build_page_header here — optimization_services has its own gradient header
        # with back navigation integrated.
        try:
            from ui.pages.optimization_services import build_optimization_page
            build_optimization_page(self, self.content_area)
        except Exception as e:
            import traceback
            err = tk.Label(self.content_area, text=f"Failed to load page:\n{e}",
                           font=(_BODY, 10), bg="#0a0e14", fg="#ef4444",
                           justify="left", padx=20, pady=20)
            err.pack(anchor="nw")
            traceback.print_exc()

    def _build_startup_manager_view(self):
        """Build Startup Manager page."""
        # No _build_page_header here — startup_manager has its own title header
        # with back navigation integrated.
        try:
            from ui.pages.startup_manager import build_startup_manager_page
            build_startup_manager_page(self, self.content_area)
        except Exception as e:
            import traceback
            tk.Label(self.content_area, text=f"Failed to load Startup Manager:\n{e}",
                     font=(_BODY, 10), bg="#0a0e14", fg="#ef4444",
                     justify="left", padx=20, pady=20).pack(anchor="nw")
            traceback.print_exc()

    def _build_services_manager_view(self):
        """Build Services Manager page."""
        self._build_page_header("SERVICES MANAGER",
                                "Windows services & TURBO profiles", "#3b82f6")
        try:
            from ui.pages.services_manager import build_services_manager_page
            build_services_manager_page(self, self.content_area)
        except Exception as e:
            import traceback
            tk.Label(self.content_area, text=f"Failed to load Services Manager:\n{e}",
                     font=(_BODY, 10), bg="#0a0e14", fg="#ef4444",
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

    def _apply_gpt_height_scale(self, panel) -> None:
        """Maximized window → taller chat: +12% default open height,
        +35% in the chat's own Maximize mode. Compact → base heights."""
        try:
            if self._is_maximized:
                panel.set_height_scale(1.12, 1.35)
            else:
                panel.set_height_scale(1.0, 1.0)
        except Exception:
            pass

    def _build_hckgpt_banner(self):
        """
        Build (or re-pack) hck_GPT panel at bottom of dashboard.

        First call  →  creates a new HCKGPTPanel.
        Subsequent  →  re-packs the SAME frame so chat history is preserved
                        across all page switches.
        """
        # ── Re-show existing panel if alive (uses place(), not pack()) ──────────
        existing = getattr(self, "gpt_panel", None)
        if existing is not None:
            try:
                if existing.frame.winfo_exists():
                    existing.set_visibility_gate(
                        lambda: self.current_view in self._GPT_BANNER_PAGES)
                    self._apply_gpt_height_scale(existing)
                    # Defer by 10 ms so all dashboard widgets are laid out first,
                    # giving content_area its final height before _on_resize reads it.
                    # Second pass at 150 ms covers the maximized↔compact transition,
                    # where the WM is still settling the final geometry.
                    existing.frame.after(10, existing._on_resize)
                    existing.frame.after(150, existing._on_resize)
                    return
            except Exception:
                pass
            # frame was destroyed somehow — fall through and recreate
            self.gpt_panel = None

        # ── First-time creation ───────────────────────────────────────────────
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
            self.gpt_panel.set_visibility_gate(
                lambda: self.current_view in self._GPT_BANNER_PAGES)
            self._apply_gpt_height_scale(self.gpt_panel)
            # Wire clickable nav links - [-> Optimization] / [-> Startup Manager]
            try:
                self.gpt_panel.register_nav_callback(
                    "Optimization",
                    lambda: self._switch_to_page("optimization")
                )
                self.gpt_panel.register_nav_callback(
                    "Startup Manager",
                    lambda: self._switch_to_page("startup_manager")
                )
                self.gpt_panel.register_nav_callback(
                    "Services Manager",
                    lambda: self._switch_to_page("services_manager")
                )

                def _open_stability_from_chat():
                    # Stability Tests lives inside the "My PC" page -> show it, then
                    # swap its content area to the stability tests view.
                    try:
                        self._show_overlay("your_pc")
                        from ui.components.yourpc_page import _open_stability_tests
                        self.root.after(220, lambda: _open_stability_tests(self))
                    except Exception:
                        pass

                self.gpt_panel.register_nav_callback(
                    "Stability Tests", _open_stability_from_chat
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
                     font=(_BODY, 9, "bold"), bg="#8b5cf6", fg="#ffffff"
                     ).pack(side="left", padx=15, pady=5)

    def _build_header(self):
        """Build dashboard header: branding + version badge + mode switcher."""
        _BG = "#080b14"
        header = tk.Frame(self.content_area, bg=_BG, height=58)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # ── Thin accent gradient bar at very top ──────────────────────────────
        accent_bar = tk.Canvas(header, bg=_BG, height=2, highlightthickness=0)
        accent_bar.pack(fill="x")
        def _draw_accent(e=None, cv=accent_bar):
            cv.delete("all")
            W = cv.winfo_width()
            if W < 4:
                return
            step = max(1, W // 4)
            for i, col in enumerate(("#7c3aed", "#6d28d9", "#4f46e5", "#3b82f6")):
                cv.create_rectangle(i * step, 0, (i + 1) * step, 2,
                                    fill=col, outline="")
        accent_bar.bind("<Configure>", _draw_accent)

        # ── Left — wordmark ───────────────────────────────────────────────────
        left_frame = tk.Frame(header, bg=_BG)
        left_frame.pack(side="left", padx=20, fill="y")

        tk.Label(
            left_frame,
            text="PC Workman",
            font=(_HDR, 16),
            bg=_BG,
            fg="#e2e8f0"
        ).pack(side="left", pady=16)

        # Version badge (small pill)
        try:
            from startup import APP_VERSION as _AV
        except ImportError:
            _AV = "1.8.1"

        badge = tk.Label(
            left_frame,
            text=f" v{_AV} ",
            font=(_MONO, 7),
            bg="#1e1b4b",
            fg="#818cf8",
            padx=4, pady=2,
        )
        badge.pack(side="left", padx=(8, 0), pady=19)

        # Subtitle (edition tag) — live i18n
        subtitle = tk.Label(
            left_frame,
            text=_t("dashboard.subtitle"),
            font=(_BODY, 9),
            bg=_BG,
            fg="#74839a",
        )
        subtitle.pack(side="left", padx=(8, 0), pady=16)
        self._header_subtitle_lbl = subtitle

        # Right side - Mini Monitor + Mode switcher
        right_frame = tk.Frame(header, bg="#0a0e27")
        right_frame.pack(side="right", padx=20, fill="y")

        # Minimal mode button
        mode_btn = tk.Label(
            right_frame,
            text=_t("dashboard.minimal_mode"),
            font=(_HDR, 10, "bold"),
            bg="#1e293b",
            fg="#94a3b8",
            cursor="hand2",
            padx=15,
            pady=8
        )
        mode_btn.pack(side="right", pady=12)
        mode_btn.bind("<Button-1>", lambda e: self._switch_to_minimal())
        self._mode_btn = mode_btn  # kept for live i18n refresh

        def on_enter(e):
            mode_btn.config(bg="#334155", fg="#e2e8f0")
        def on_leave(e):
            mode_btn.config(bg="#1e293b", fg="#94a3b8")

        mode_btn.bind("<Enter>", on_enter)
        mode_btn.bind("<Leave>", on_leave)

        # Maximize / restore button
        _max_text = "⊡" if self._is_maximized else "⤢"
        max_btn = tk.Label(
            right_frame,
            text=_max_text,
            font=(_HDR, 12),
            bg="#1e293b",
            fg="#94a3b8",
            cursor="hand2",
            padx=12,
            pady=8
        )
        max_btn.pack(side="right", pady=12, padx=(0, 6))
        max_btn.bind("<Button-1>", lambda e: self._toggle_maximize())
        self._max_btn = max_btn

        def on_max_enter(e):
            max_btn.config(bg="#334155", fg="#e2e8f0")
        def on_max_leave(e):
            max_btn.config(bg="#1e293b", fg="#94a3b8")

        max_btn.bind("<Enter>", on_max_enter)
        max_btn.bind("<Leave>", on_max_leave)

    def _toggle_maximize(self):
        """Switch between compact and maximized (zoomed) window state."""
        if not self._is_maximized:
            self._pre_max_geometry = self.root.geometry()  # save position for restore
            self.root.resizable(True, True)
            self.root.state("zoomed")
            self._is_maximized = True
        else:
            self.root.state("normal")
            # Restore saved geometry (size + position) so window lands back where it was
            geo = getattr(self, '_pre_max_geometry', None)
            if geo:
                self.root.geometry(geo)
            else:
                self.root.geometry(f"{_uis.compact_w()}x{_uis.compact_h()}")
            self.root.resizable(False, False)
            self._is_maximized = False
        # Rebuild current view with the correct layout variant
        self._switch_to_page(self.current_view)

    def _build_content_area_maximized(self):
        """Maximized dashboard: symmetric 3-column content area.
        LEFT:  scrollable user process panel (TOP 8).
        CENTER: live metrics strip + chart, feature buttons docked at bottom.
        RIGHT: scrollable system process panel (TOP 8).
        """
        _BG    = THEME["bg_main"]
        _PANEL = THEME["bg_panel"]

        body = tk.Frame(self.content_area, bg=_BG)
        body.pack(fill="both", expand=True, padx=14, pady=(6, 0))

        # Row count adapts to the real screen height: FHD+ still fits 15, but
        # small laptops (720/768p) get ~8 — the hardcoded 15 used to cram rows
        # and clip the usage bars there. ~44 px per 2-line row, ~380 px chrome.
        _scr_h = self.root.winfo_screenheight() or 1080
        self._proc_limit = max(6, min(15, (_scr_h - 380) // 44))

        # ── LEFT COLUMN: user processes ───────────────────────────────────────
        left_col = tk.Frame(body, bg=_PANEL, width=280)
        left_col.pack(side="left", fill="y", padx=(0, 8))
        left_col.pack_propagate(False)

        _u_title = _t("dashboard.top5_user_proc").replace("5", "8")
        tk.Label(
            left_col, text=_u_title,
            font=(_BODY, 8, "bold"), bg=_PANEL, fg=THEME["muted"],
        ).pack(pady=(8, 2))
        self._build_scrollable_proc_panel(left_col, _PANEL, "user")

        # ── RIGHT COLUMN: system processes ────────────────────────────────────
        right_col = tk.Frame(body, bg=_PANEL, width=280)
        right_col.pack(side="right", fill="y", padx=(8, 0))
        right_col.pack_propagate(False)

        _s_title = _t("dashboard.top5_sys_proc").replace("5", "8")
        tk.Label(
            right_col, text=_s_title,
            font=(_BODY, 8, "bold"), bg=_PANEL, fg=THEME["muted"],
        ).pack(pady=(8, 2))
        self._build_scrollable_proc_panel(right_col, _PANEL, "sys")

        self._process_tooltip = ProcessTooltip(self.root) if _HAS_PROC_LIB else None

        # ── CENTER COLUMN: metrics strip + chart + bottom feature buttons ────
        center_col = tk.Frame(body, bg=_BG)
        center_col.pack(side="left", fill="both", expand=True)

        # Feature buttons pinned to the bottom edge, above the hck_GPT banner
        # (34 px collapsed banner + breathing room).
        self._build_feature_buttons(center_col, dock_bottom=True)

        # Live metrics strip
        metrics_frame = tk.Frame(center_col, bg="#1a1d24", height=28)
        metrics_frame.pack(side="top", fill="x")
        metrics_frame.pack_propagate(False)

        _cur_lbl = tk.Label(
            metrics_frame, text=_t("dashboard.current_usage_label"),
            font=(_BODY, 7, "bold"), bg="#1a1d24", fg="#6b7280",
        )
        _cur_lbl.pack(side="left", padx=(10, 15))
        self._current_usage_lbl = _cur_lbl

        self.live_cpu_label = tk.Label(
            metrics_frame, text="CPU: 0%",
            font=(_MONO, 8, "bold"), bg="#1a1d24", fg="#3b82f6",
        )
        self.live_cpu_label.pack(side="left", padx=8)

        self.live_gpu_label = tk.Label(
            metrics_frame, text="GPU: 0%",
            font=(_MONO, 8, "bold"), bg="#1a1d24", fg="#10b981",
        )
        self.live_gpu_label.pack(side="left", padx=8)

        self.live_ram_label = tk.Label(
            metrics_frame, text="RAM: 0%",
            font=(_MONO, 8, "bold"), bg="#1a1d24", fg="#fbbf24",
        )
        self.live_ram_label.pack(side="left", padx=8)

        tk.Frame(metrics_frame, bg="#1a1d24", width=2).pack(side="left", padx=10)

        filter_btns_max = tk.Frame(metrics_frame, bg="#1a1d24")
        filter_btns_max.pack(side="right", padx=10)

        filter_options = ["LIVE", "1H", "4H", "1D", "1W", "1M"]
        self.filter_buttons = {}
        self._historical_chart_data = None

        for _fname in filter_options:
            _active = (_fname == getattr(self, "chart_filter", "LIVE"))
            _fbtn = tk.Label(
                filter_btns_max, text=_fname,
                font=(_BODY, 6, "bold"),
                bg="#2563eb" if _active else "#000000",
                fg="#ffffff" if _active else "#6b7280",
                cursor="hand2", padx=6, pady=2,
            )
            _fbtn.pack(side="left", padx=1)

            def _make_click(fn, fb):
                def _on_click(e):
                    for fb2 in self.filter_buttons.values():
                        fb2.config(bg="#000000", fg="#6b7280")
                    fb.config(bg="#2563eb", fg="#ffffff")
                    self.chart_filter = fn
                    self._chart_needs_view_reset = True
                    if fn != "LIVE":
                        self._load_historical_chart_data(fn)
                    else:
                        self._historical_chart_data = None
                    self._schedule_chart_update(50)
                return _on_click

            _fbtn.bind("<Button-1>", _make_click(_fname, _fbtn))
            self.filter_buttons[_fname] = _fbtn

            def _make_hover(fb2, fn2):
                def _enter(e):
                    if self.chart_filter != fn2:
                        fb2.config(bg="#1a1a1a")
                def _leave(e):
                    if self.chart_filter != fn2:
                        fb2.config(bg="#000000")
                return _enter, _leave
            _ent, _lev = _make_hover(_fbtn, _fname)
            _fbtn.bind("<Enter>", _ent)
            _fbtn.bind("<Leave>", _lev)

        # Canvas bar chart (maximized): fixed at ~35% of window height —
        # a full fill-both chart dominated the column, so it gave back 25%.
        # The redraw reads live canvas size, so any height works.
        try:
            _win_h = self.root.winfo_height()
        except Exception:
            _win_h = 0
        _chart_h = int(_win_h * 0.35) if _win_h > 400 else _uis.wide_chart_h()
        self.realtime_canvas = tk.Canvas(
            center_col, bg="#080b14", bd=0, highlightthickness=1,
            highlightbackground="#0d1825", height=_chart_h,
        )
        self.realtime_canvas.pack(fill="x", pady=(4, 0))
        self.realtime_canvas.bind("<Motion>",   self._chart_on_motion)
        self.realtime_canvas.bind("<Button-1>", self._chart_on_click)
        self.realtime_canvas.bind("<Leave>",    self._chart_on_leave)
        self._chart_pin_idx   = None
        self._main_chart      = None
        self._chart_after_id  = None
        self._schedule_chart_update(100)

    def _build_scrollable_proc_panel(self, parent, bg, kind):
        """Scrollable process list — 8 rows visible, mousewheel to scroll more."""
        _ROW_H   = 42   # 40px row + 2px pady
        _VISIBLE = 8
        viewport_h = _ROW_H * _VISIBLE + 4

        outer = tk.Frame(parent, bg=bg)
        outer.pack(fill="both", expand=True, padx=5, pady=(0, 4))

        scroll_cv = tk.Canvas(outer, bg=bg, highlightthickness=0, height=viewport_h)
        scroll_cv.pack(side="left", fill="both", expand=True)

        sb = tk.Scrollbar(outer, orient="vertical", command=scroll_cv.yview,
                          width=8, bd=0, highlightthickness=0,
                          bg="#111418", troughcolor="#0b0d10",
                          activebackground="#2a3040")
        sb.pack(side="right", fill="y")
        scroll_cv.configure(yscrollcommand=sb.set)

        inner = tk.Frame(scroll_cv, bg=bg)
        win_id = scroll_cv.create_window(0, 0, anchor="nw", window=inner)

        def _content_fits():
            bbox = scroll_cv.bbox("all")
            return (not bbox) or (bbox[3] - bbox[1] <= scroll_cv.winfo_height())

        def _on_inner_resize(e):
            try:
                scroll_cv.configure(scrollregion=scroll_cv.bbox("all"))
                # Content fits the viewport — reset any stale scroll offset,
                # otherwise a blank gap sticks at the top and the wheel is dead.
                if _content_fits():
                    scroll_cv.yview_moveto(0)
            except Exception:
                pass
        inner.bind("<Configure>", _on_inner_resize)

        def _on_cv_resize(e):
            try:
                scroll_cv.itemconfigure(win_id, width=e.width)
                if _content_fits():
                    scroll_cv.yview_moveto(0)
            except Exception:
                pass
        scroll_cv.bind("<Configure>", _on_cv_resize)

        def _on_wheel(e):
            try:
                if not _content_fits():
                    scroll_cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass

        # Direct bindings (no bind_all): the old Enter/Leave global binding
        # died the moment the cursor touched a child row (<Leave> fires with
        # NotifyInferior), so the wheel never worked over the rows themselves.
        # Rows bind this same handler on creation in _render_expanded_*.
        scroll_cv.bind("<MouseWheel>", _on_wheel)
        inner.bind("<MouseWheel>", _on_wheel)

        if kind == "user":
            self.expanded_user_container = inner
            self.expanded_user_widgets = []
            self._user_wheel_handler = _on_wheel
        else:
            self.expanded_sys_container = inner
            self.expanded_sys_widgets = []
            self._sys_wheel_handler = _on_wheel

    @staticmethod
    def _bind_wheel_recursive(widget, handler):
        """Bind a mousewheel handler on a widget and every descendant."""
        try:
            widget.bind("<MouseWheel>", handler)
            for child in widget.winfo_children():
                ExpandedMainWindow._bind_wheel_recursive(child, handler)
        except Exception:
            pass

    def _build_middle_section(self):
        """Build session average bars + category navigation"""
        _mid_padx = 20
        # Maximized: taller so the session-averages block breathes AND the
        # 4th left-nav button fits — nav needs 3×62 + 50 = 236 px, so 180 px
        # (compact) clips OPTYMALIZACJA entirely and 216 px cuts it in half.
        # 274 = 238 +15% (v1.7.8 polish: taller hardware cards w/ corner names)
        _mid_h = 274 if self._is_maximized else 180
        middle = tk.Frame(self.content_area, bg=THEME["bg_main"], height=_mid_h)
        middle.pack(fill="x", side="top", padx=_mid_padx, pady=(10, 0))
        middle.pack_propagate(False)

        # LEFT NAVIGATION
        left_nav = tk.Frame(middle, bg=THEME["bg_panel"], width=_uis.scale(200))
        left_nav.pack(side="left", fill="y", padx=(0, 10))
        left_nav.pack_propagate(False)
        self.guide_left_nav = left_nav   # used by LiveGuide spotlight

        # Navigation buttons (left) - no section label, max space for buttons
        nav_buttons_left = [
            (_t("dashboard.nav_my_pc"),        "#3b82f6", _t("dashboard.nav_sub_central"),    "your_pc"),
            (_t("dashboard.nav_monitoring"),   "#8b5cf6", _t("dashboard.nav_sub_monitoring"), "sensors"),
            (_t("dashboard.nav_allmonitor"),   "#f97316", _t("dashboard.nav_sub_allmonitor"), "live_graphs"),
            (_t("dashboard.nav_optimization"), "#10b981", "",                                 "optimization"),
        ]

        for text, color, subtitle, pid in nav_buttons_left:
            self._create_nav_button(left_nav, text, color, subtitle, pady=2, page_id=pid)

        # CENTER - SESSION AVERAGE BARS
        # Maximized: inset so the block's edges line up with the chart column
        # below (proc panels are 280 px vs 200 px navs) — no visual overlap
        # with the TOP 8 process panels.
        _center_padx = 72 if self._is_maximized else 5
        center = tk.Frame(middle, bg=THEME["bg_main"])
        center.pack(side="left", fill="both", expand=True, padx=_center_padx)
        self.guide_middle_center = center   # used by LiveGuide spotlight

        # Title - MINIMAL SPACING
        tk.Label(
            center,
            text=_t("dashboard.session_averages"),
            font=(_BODY, 9, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"]
        ).pack(pady=(6, 8) if self._is_maximized else (2, 5))

        # CPU Bar
        self._create_session_bar(center, "CPU", "#3b82f6", "#ef4444", "cpu")

        # GPU Bar
        self._create_session_bar(center, "GPU", "#10b981", "#64748b", "gpu")

        # RAM Bar
        self._create_session_bar(center, "RAM", "#fbbf24", "#1e40af", "ram")

        # YOUR PC - PERSONAL DATA section
        self._build_yourpc_section(center)

        # RIGHT NAVIGATION
        right_nav = tk.Frame(middle, bg=THEME["bg_panel"], width=_uis.scale(200))
        right_nav.pack(side="right", fill="y", padx=(10, 0))
        right_nav.pack_propagate(False)
        self.guide_right_nav = right_nav   # used by LiveGuide spotlight

        # Navigation buttons (right) - no section label
        nav_buttons_right = [
            (_t("dashboard.nav_fan_dashboard"), "#8b5cf6", _t("dashboard.nav_sub_fan"),     "fan_control"),
            (_t("dashboard.nav_hck_labs"),      "#f59e0b", "",                              "hck_labs"),
            (_t("dashboard.nav_guide"),         "#06b6d4", "",                              "guide"),
        ]

        for text, color, subtitle, pid in nav_buttons_right:
            self._create_nav_button(right_nav, text, color, subtitle, pady=2, page_id=pid)

    def _create_nav_button(self, parent, text, color, subtitle="", pady=4, page_id=None):
        """Dark gradient nav button: deep navy bg, bordeaux L-corner brackets, bold text."""
        btn_container = tk.Frame(parent, bg=THEME["bg_panel"])
        btn_container.pack(fill="x", padx=6, pady=pady)

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
            # base dark colours (left -> right endpoints)
            base0 = (0x08, 0x0b, 0x18)
            base1 = (0x10, 0x16, 0x26)
            # target hover colours: darkened accent (≈30% of accent, rest black)
            hov0  = (ac_r // 5, ac_g // 5, ac_b // 5)
            hov1  = (ac_r // 3, ac_g // 3, ac_b // 3)
            blend = 0.72 if hovered else 0.0   # 0=base only, 1=hover only

            for x in range(0, w, STRIP):
                t  = x / w
                # interpolate base left->right
                br = int(base0[0] + (base1[0] - base0[0]) * t)
                bg_ = int(base0[1] + (base1[1] - base0[1]) * t)
                bb = int(base0[2] + (base1[2] - base0[2]) * t)
                # interpolate hover left->right
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

            # ── Bottom accent line: bordeaux->crimson, right 55% of button ────
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

            # ── Text - vertically centred with room to breathe ────────────────
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
                                   font=(_BODY, 8),
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
        _bar_h, _row_pady = (20, 3) if self._is_maximized else (16, 1)
        row = tk.Frame(parent, bg=THEME["bg_main"])
        row.pack(fill="x", pady=_row_pady)

        lbl = tk.Label(
            row,
            text=label,
            font=(_BODY, 8, "bold"),
            bg=THEME["bg_main"],
            fg=THEME["text"],
            width=4,
            anchor="w"
        )
        lbl.pack(side="left", padx=(8, 4))

        bar = AnimatedBar(row, color_start, bg_color="#1a1d24", height=_bar_h)
        bar.bg_frame.pack(side="left", fill="x", expand=True, padx=4)

        val_lbl = tk.Label(
            row,
            text="0%",
            font=(_MONO, 8, "bold"),
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
        """Hardware card: sparkline with the component name overlaid in its
        corner — same principle in compact and maximized, so the name never
        collides with the layout (the chart owns the whole card width)."""
        card = tk.Frame(parent, bg=THEME["bg_panel"], relief="flat", bd=0)
        card.pack(side="left", fill="both", expand=True, padx=2)

        inner = tk.Frame(card, bg=THEME["bg_panel"])
        inner.pack(fill="both", expand=True, padx=4, pady=4)

        # Sparkline area — taller in both modes so the corner name has room.
        _chart_h = 50 if self._is_maximized else 44
        chart_frame = tk.Frame(inner, bg="#0f1117", height=_chart_h)
        chart_frame.pack(fill="x", pady=(0, 0))
        chart_frame.pack_propagate(False)

        chart_canvas = tk.Canvas(chart_frame, bg="#0f1117", highlightthickness=0)
        chart_canvas.pack(fill="both", expand=True)

        # Component name + model drawn IN the chart corner (no header row → no collision)
        chart_canvas._corner_title = hw_type
        chart_canvas._corner_sub   = model[:24]
        chart_canvas._corner_color = color
        chart_canvas.after(50, lambda cv=chart_canvas: self._draw_card_corner(cv)
                           if cv.winfo_exists() else None)

        # Temperature bar - smaller
        temp_frame = tk.Frame(inner, bg=THEME["bg_panel"])
        temp_frame.pack(fill="x", pady=(3, 0))

        tk.Label(
            temp_frame,
            text="TEMP",
            font=(_BODY, 5),
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
            font=(_MONO, 6),
            bg=THEME["bg_panel"],
            fg=color,
            width=3
        )
        temp_label.pack(side="right")

        # Health status - smaller font
        health_label = tk.Label(
            inner,
            text=_t("dashboard.status_all_good"),
            font=(_BODY, 6),
            bg=THEME["bg_panel"],
            fg="#10b981",
            anchor="w"
        )
        health_label.pack(fill="x", pady=(2, 0))

        # Load status - smaller font
        load_label = tk.Label(
            inner,
            text=_t("dashboard.no_activity"),
            font=(_BODY, 6),
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
        """Build compact dashboard content: scrollable proc panels + InteractiveChart."""
        _PANEL = THEME["bg_panel"]
        _BG    = THEME["bg_main"]
        _PROC_W = _uis.scale(220)

        content = tk.Frame(self.content_area, bg=_BG)
        content.pack(fill="both", expand=True, padx=20, pady=10)

        main_row = tk.Frame(content, bg=_BG)
        main_row.pack(fill="both", expand=True)

        # ── LEFT PANEL: user processes (scrollable) ───────────────────────────
        self._proc_limit = 8
        left_panel = tk.Frame(main_row, bg=_PANEL, width=_PROC_W)
        left_panel.pack(side="left", fill="y", padx=(0, 8))
        left_panel.pack_propagate(False)

        tk.Label(
            left_panel, text=_t("dashboard.top5_user_proc"),
            font=(_BODY, 8, "bold"), bg=_PANEL, fg=THEME["muted"],
        ).pack(pady=(8, 2))

        self._build_scrollable_proc_panel(left_panel, _PANEL, "user")

        self._process_tooltip = ProcessTooltip(self.root) if _HAS_PROC_LIB else None
        self._build_ai_writing_panel(left_panel)

        # ── RIGHT PANEL: system processes (scrollable) ────────────────────────
        right_panel = tk.Frame(main_row, bg=_PANEL, width=_PROC_W)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        tk.Label(
            right_panel, text=_t("dashboard.top5_sys_proc"),
            font=(_BODY, 8, "bold"), bg=_PANEL, fg=THEME["muted"],
        ).pack(pady=(8, 2))

        self._build_scrollable_proc_panel(right_panel, _PANEL, "sys")

        # ── CENTER: InteractiveChart + metrics + feature buttons ──────────────
        center = tk.Frame(main_row, bg=_BG)
        center.pack(side="left", fill="both", expand=True, padx=5)

        # Canvas bar chart (compact)
        self.realtime_canvas = tk.Canvas(
            center, bg="#080b14", bd=0, highlightthickness=1,
            highlightbackground="#0d1825", height=150,
        )
        self.realtime_canvas.pack(fill="x", pady=(0, 0))
        self.realtime_canvas.bind("<Motion>",   self._chart_on_motion)
        self.realtime_canvas.bind("<Button-1>", self._chart_on_click)
        self.realtime_canvas.bind("<Leave>",    self._chart_on_leave)
        self._chart_pin_idx   = None
        self._main_chart      = None
        self._chart_after_id  = None
        self._schedule_chart_update(100)

        # Chart legend footer — visually part of the chart (same bg, flush above):
        # CURRENT USAGE + coloured CPU/RAM/GPU values left, time-range filters right.
        _LEG_BG = "#080b14"
        metrics_frame = tk.Frame(center, bg=_LEG_BG, height=31)
        metrics_frame.pack(fill="x")
        metrics_frame.pack_propagate(False)

        _cur_lbl = tk.Label(
            metrics_frame, text=_t("dashboard.current_usage_label"),
            font=(_BODY, 7, "bold"), bg=_LEG_BG, fg="#6b7280",
        )
        _cur_lbl.pack(side="left", padx=(10, 10))
        self._current_usage_lbl = _cur_lbl

        self.live_cpu_label = tk.Label(
            metrics_frame, text="■ CPU 0%",
            font=(_MONO, 9, "bold"), bg=_LEG_BG, fg="#3b82f6",
        )
        self.live_cpu_label.pack(side="left", padx=7)

        self.live_ram_label = tk.Label(
            metrics_frame, text="■ RAM 0%",
            font=(_MONO, 9, "bold"), bg=_LEG_BG, fg="#fbbf24",
        )
        self.live_ram_label.pack(side="left", padx=7)

        self.live_gpu_label = tk.Label(
            metrics_frame, text="■ GPU 0%",
            font=(_MONO, 9, "bold"), bg=_LEG_BG, fg="#10b981",
        )
        self.live_gpu_label.pack(side="left", padx=7)

        tk.Frame(metrics_frame, bg=_LEG_BG, width=2).pack(side="left", padx=10)

        filter_btns = tk.Frame(metrics_frame, bg=_LEG_BG)
        filter_btns.pack(side="right", padx=10)

        filter_options = ["LIVE", "1H", "4H", "1D", "1W", "1M"]
        self.filter_buttons = {}
        self._historical_chart_data = None

        for filter_name in filter_options:
            _active = (filter_name == getattr(self, 'chart_filter', 'LIVE'))
            btn = tk.Label(
                filter_btns, text=filter_name,
                font=(_BODY, 6, "bold"),
                bg="#2563eb" if _active else "#000000",
                fg="#ffffff" if _active else "#6b7280",
                cursor="hand2", padx=6, pady=2,
            )
            btn.pack(side="left", padx=1)

            def make_filter_click(f_name, f_btn):
                def on_click(e):
                    for fb in self.filter_buttons.values():
                        fb.config(bg="#000000", fg="#6b7280")
                    f_btn.config(bg="#2563eb", fg="#ffffff")
                    self.chart_filter = f_name
                    self._chart_needs_view_reset = True
                    if f_name != 'LIVE':
                        self._load_historical_chart_data(f_name)
                    else:
                        self._historical_chart_data = None
                    self._schedule_chart_update(50)
                return on_click

            btn.bind("<Button-1>", make_filter_click(filter_name, btn))
            self.filter_buttons[filter_name] = btn

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

        self._build_feature_buttons(center)

    def _build_feature_buttons(self, parent, dock_bottom=False):
        """Build feature buttons - Turbo Boost & More Optimization Tools.

        dock_bottom=True (maximized dashboard) pins the row to the bottom of
        the parent, leaving clearance for the 34 px collapsed hck_GPT banner.
        """
        buttons_container = tk.Frame(parent, bg=THEME["bg_main"])
        if dock_bottom:
            buttons_container.pack(side="bottom", fill="x", pady=(8, 48))
        else:
            buttons_container.pack(fill="x", pady=(8, 0))

        # Container for two buttons side by side
        buttons_row = tk.Frame(buttons_container, bg=THEME["bg_main"])
        buttons_row.pack(fill="x", padx=5)

        # Left: Turbo Boost — master switch for every feature set to fire on TURBO
        try:
            from ui.pages import optimization_services as _opt_mod
        except Exception:
            _opt_mod = None
        self.turbo_active = bool(_opt_mod.is_turbo_active()) if _opt_mod else False

        _T_ON, _T_OFF = "#7f1d1d", "#2a2d35"   # bordeaux (on) / grey (off)

        turbo_btn = tk.Frame(buttons_row, bg=_T_ON if self.turbo_active else _T_OFF,
                             cursor="hand2")
        turbo_btn.pack(side="left", fill="both", expand=True, padx=(0, 3))

        turbo_content = tk.Frame(turbo_btn, bg="#1e2028")
        turbo_content.pack(fill="x", padx=2, pady=2)

        turbo_header = tk.Frame(turbo_content, bg="#1e2028")
        turbo_header.pack(fill="x", padx=8, pady=(6, 4))

        tk.Label(turbo_header, text="Turbo Boost:", font=(_BODY, 11, "bold"),
                 bg="#1e2028", fg="#e5e7eb", padx=2, pady=2).pack(side="left")
        self._turbo_state_lbl = tk.Label(
            turbo_header, text="ON" if self.turbo_active else "OFF",
            font=(_BODY, 11, "bold"), bg="#1e2028",
            fg="#f87171" if self.turbo_active else "#6b7280", padx=4, pady=2)
        self._turbo_state_lbl.pack(side="left")

        tk.Frame(turbo_content, bg="#374151", height=1).pack(fill="x", pady=(4, 4))

        turbo_actions = tk.Frame(turbo_content, bg="#1e2028")
        turbo_actions.pack(fill="x", padx=8, pady=(0, 6))

        _cfg = tk.Label(turbo_actions, text="Configure", font=(_BODY, 7, "bold"),
                        bg="#374151", fg="#9ca3af", padx=8, pady=3, cursor="hand2")
        _cfg.pack(side="left")
        _cfg.bind("<Button-1>", lambda e: self._switch_to_page("optimization"))
        _cfg.bind("<Enter>", lambda e: _cfg.config(fg="#cbd5e1"))
        _cfg.bind("<Leave>", lambda e: _cfg.config(fg="#9ca3af"))

        _launch = tk.Label(turbo_actions, text="Launch", font=(_BODY, 7, "bold"),
                           bg="#7f1d1d", fg="#fecaca", padx=10, pady=3, cursor="hand2")
        _launch.pack(side="right")

        def _toggle_turbo(e=None):
            if _opt_mod is None:
                return
            res = _opt_mod.set_turbo_active(not self.turbo_active)
            self.turbo_active = res["on"]
            n = sum(1 for _, ok in res["applied"] if ok)
            base = "ON" if self.turbo_active else "OFF"
            if self.turbo_active:
                extra = (f" · {n} fired" if n
                         else (" · needs admin" if not res["admin"] else " · configure"))
            else:
                extra = ""
            self._turbo_state_lbl.config(
                text=base + extra,
                fg="#f87171" if self.turbo_active else "#6b7280")
            turbo_btn.config(bg=_T_ON if self.turbo_active else _T_OFF)
            self.root.after(2600, lambda: self._turbo_state_lbl.config(text=base)
                            if self._turbo_state_lbl.winfo_exists() else None)

        for w in (turbo_btn, turbo_content, turbo_header, self._turbo_state_lbl, _launch):
            w.bind("<Button-1>", _toggle_turbo, add="+")

        # === RIGHT: OPTIMIZATION CENTER ===
        _OC_BG    = "#0c1018"
        _OC_BD    = "#1c2840"    # slightly richer border
        _OC_BD_H  = "#2e4878"    # hover border (brighter blue)
        _OC_TEXT  = "#4a7ab5"    # visible but subtle blue
        _OC_HOV   = "#7ab0e8"    # nice hover blue
        _OC_ICON  = "#2d5080"    # icon color
        _OC_SUB   = "#8fa6c4"    # subtitle color (was #2a4a6a — barely visible)
        _OC_PATH  = "#6f86a3"    # path color (was #1e3550 — barely visible)

        optim_btn = tk.Frame(buttons_row, bg=_OC_BD, cursor="hand2")
        optim_btn.pack(side="right", fill="both", expand=True, padx=(3, 0))

        optim_content = tk.Frame(optim_btn, bg=_OC_BG)
        optim_content.pack(fill="x", padx=1, pady=1)

        # Top accent bar - medium violet-blue
        tk.Frame(optim_content, bg="#2e4878", height=2).pack(fill="x")

        optim_inner = tk.Frame(optim_content, bg=_OC_BG)
        optim_inner.pack(fill="x", padx=10, pady=(6, 8))

        # Icon + label row (20% bigger font: 9 -> 11)
        hdr_row = tk.Frame(optim_inner, bg=_OC_BG)
        hdr_row.pack(anchor="w")
        tk.Label(hdr_row, text="⚡", font=(_BODY, 11),
                 bg=_OC_BG, fg=_OC_ICON).pack(side="left", padx=(0, 5))
        optim_title = tk.Label(
            hdr_row,
            text=_t("dashboard.opt_center_label"),
            font=(_HDR, 11),   # 22% bigger than original 9
            bg=_OC_BG, fg=_OC_TEXT, cursor="hand2",
        )
        optim_title.pack(side="left")

        # Path subtitle
        tk.Label(
            optim_inner,
            text=f"Hardware & Health  ->  {_t('nav.my_pc')}",
            font=(_BODY, 7),
            bg=_OC_BG, fg=_OC_PATH,
        ).pack(anchor="w", pady=(1, 0))

        # "Everything about optimizing" tagline
        tk.Label(
            optim_inner,
            text=_t("dashboard.opt_center_sub"),
            font=(_BODY, 7, "italic"),
            bg=_OC_BG, fg=_OC_SUB,
        ).pack(anchor="w", pady=(2, 0))

        # Thin bottom separator
        tk.Frame(optim_content, bg=_OC_BD, height=1).pack(fill="x")

        # Keep attribute refs for compatibility (zero-size)
        self.tools_label       = tk.Label(optim_inner, text="", height=0,
                                          font=(_BODY, 1), bg=_OC_BG, fg=_OC_BG)
        self.tools_count_label = tk.Label(optim_inner, text="", height=0,
                                          font=(_BODY, 1), bg=_OC_BG, fg=_OC_BG)

        # Navigation -> My PC (Hardware & Health)
        def _go_hardware(e=None):
            self._switch_to_page("your_pc")

        def _oc_enter(e):
            optim_title.config(fg=_OC_HOV)
            optim_btn.config(bg=_OC_BD_H)
            optim_content.config(bg="#0f1825")
        def _oc_leave(e):
            optim_title.config(fg=_OC_TEXT)
            optim_btn.config(bg=_OC_BD)
            optim_content.config(bg=_OC_BG)

        for w in (optim_btn, optim_content, optim_inner, hdr_row, optim_title):
            w.bind("<Button-1>", _go_hardware, add="+")
            w.bind("<Enter>",   _oc_enter,    add="+")
            w.bind("<Leave>",   _oc_leave,    add="+")

    def _build_ai_writing_panel(self, parent):
        """Build compact info panel with typing animation"""
        panel = tk.Frame(parent, bg="#0a0e27", height=50)
        panel.pack(fill="x", padx=5, pady=(3, 3))
        panel.pack_propagate(False)

        # Thin accent line at top
        tk.Frame(panel, bg="#8b5cf6", height=1).pack(fill="x")

        # Text display area - fills entire panel
        text_area = tk.Frame(panel, bg="#0f1117")
        text_area.pack(fill="both", expand=True, padx=4, pady=2)

        # Text label with cursor
        self.ai_text_container = tk.Frame(text_area, bg="#0f1117")
        self.ai_text_container.pack(fill="both", expand=True)

        self.ai_text_label = tk.Label(
            self.ai_text_container,
            text="",
            font=(_MONO, 8),
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
            font=(_MONO, 8, "bold"),
            bg="#0f1117",
            fg="#a78bfa"
        )
        self.ai_cursor.pack(side="left", anchor="n")

        # Messages - shorter, punchier
        self.ai_messages = [
            "PC Workman - by Marcin 'HCK' Firmuga",
            "16 optimization tools, one-click setup.",
            "Built with heart from the Netherlands.",
            "Your PC, Smarter. Always watching.",
        ]

        self.ai_current_message_index = 0
        self.ai_current_text = ""
        self.ai_typing = False
        self.ai_deleting = False
        self.ai_char_index = 0

        # Start animations — IDs tracked so _switch_to_page can cancel them
        self._anim_ai_cursor_id = self.root.after(500, self._animate_ai_cursor)
        self._anim_ai_typing_id = self.root.after(500, self._animate_ai_typing)

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
                self._anim_ai_cursor_id = self.root.after(600, self._animate_ai_cursor)
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
                self._anim_ai_typing_id = self.root.after(delay, self._animate_ai_typing)
        except Exception:
            if self._running:
                self._anim_ai_typing_id = self.root.after(2000, self._animate_ai_typing)


    def _render_expanded_user_processes(self, procs):
        """Render TOP 5 user processes - 2-line rows with animated bars."""
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
        _n_rows = getattr(self, '_proc_limit', 5)

        if not self.expanded_user_widgets:
            for i in range(_n_rows):
                row_bg = row_gradients[i % len(row_gradients)]
                row = tk.Frame(self.expanded_user_container, bg=row_bg, height=40)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                # Line 1 - process name
                top_line = tk.Frame(row, bg=row_bg)
                top_line.pack(fill="x", padx=6, pady=(4, 0))

                name_lbl = tk.Label(
                    top_line, text="", font=(_HDR, 8),
                    bg=row_bg, fg=THEME["text"], anchor="w"
                )
                name_lbl.pack(side="left")

                # Line 2 - CPU + RAM bars
                bars_line = tk.Frame(row, bg=row_bg)
                bars_line.pack(fill="x", padx=6, pady=(2, 4))

                # CPU half
                cpu_half = tk.Frame(bars_line, bg=row_bg)
                cpu_half.pack(side="left", fill="x", expand=True)

                tk.Label(cpu_half, text="CPU", font=(_BODY, 7, "bold"),
                         bg=row_bg, fg="#3b82f6").pack(side="left")

                cpu_bar = AnimatedBar(cpu_half, "#3b82f6", bg_color="#0d1117", height=6)
                cpu_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                cpu_val = tk.Label(cpu_half, text="0%", font=(_MONO, 7, "bold"),
                                   bg=row_bg, fg="#3b82f6", width=4, anchor="e")
                cpu_val.pack(side="left")

                # Divider
                tk.Frame(bars_line, bg="#2a2d34", width=1).pack(
                    side="left", fill="y", padx=3)

                # RAM half
                ram_half = tk.Frame(bars_line, bg=row_bg)
                ram_half.pack(side="left", fill="x", expand=True)

                tk.Label(ram_half, text="RAM", font=(_BODY, 7, "bold"),
                         bg=row_bg, fg="#fbbf24").pack(side="left")

                ram_bar = AnimatedBar(ram_half, "#fbbf24", bg_color="#0d1117", height=6)
                ram_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                ram_val = tk.Label(ram_half, text="0%", font=(_MONO, 7, "bold"),
                                   bg=row_bg, fg="#fbbf24", width=4, anchor="e")
                ram_val.pack(side="left")

                widget_data = {
                    "row": row, "name": name_lbl,
                    "cpu_bar": cpu_bar, "cpu_val": cpu_val,
                    "ram_bar": ram_bar, "ram_val": ram_val,
                    "proc_name": "",
                }
                self.expanded_user_widgets.append(widget_data)

                # Wheel scroll must work with the cursor over the row content
                _wh = getattr(self, '_user_wheel_handler', None)
                if _wh:
                    self._bind_wheel_recursive(row, _wh)

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
                widget_data["cpu_val"].config(text=self._fmt_proc_pct(cpu_pct))
                widget_data["ram_bar"].set_target(ram_pct)
                widget_data["ram_val"].config(text=self._fmt_proc_pct(ram_pct))
                widget_data["row"].pack(fill="x", pady=1)
            else:
                widget_data["name"].config(text="")
                widget_data["cpu_bar"].set_target(0)
                widget_data["cpu_val"].config(text="")
                widget_data["ram_bar"].set_target(0)
                widget_data["ram_val"].config(text="")

    @staticmethod
    def _fmt_proc_pct(v: float) -> str:
        """Honest percent label: an active process never shows a flat '0%'."""
        if v <= 0:
            return "0%"
        if v < 1:
            return "<1%"
        return f"{v:.0f}%"

    def _render_expanded_system_processes(self, procs):
        """Render TOP 5 system processes - reuse widgets instead of destroy/recreate"""
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
        _n_rows = getattr(self, '_proc_limit', 5)

        if not self.expanded_sys_widgets:
            for i in range(_n_rows):
                row_bg = row_gradients[i % len(row_gradients)]
                row = tk.Frame(self.expanded_sys_container, bg=row_bg, height=40)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)

                # Line 1 - process name
                top_line = tk.Frame(row, bg=row_bg)
                top_line.pack(fill="x", padx=6, pady=(4, 0))

                name_lbl = tk.Label(
                    top_line, text="", font=(_HDR, 8),
                    bg=row_bg, fg=THEME["text"], anchor="w"
                )
                name_lbl.pack(side="left")

                # Line 2 - CPU + RAM bars
                bars_line = tk.Frame(row, bg=row_bg)
                bars_line.pack(fill="x", padx=6, pady=(2, 4))

                # CPU half
                cpu_half = tk.Frame(bars_line, bg=row_bg)
                cpu_half.pack(side="left", fill="x", expand=True)

                tk.Label(cpu_half, text="CPU", font=(_BODY, 7, "bold"),
                         bg=row_bg, fg="#3b82f6").pack(side="left")

                cpu_bar = AnimatedBar(cpu_half, "#3b82f6", bg_color="#0d1117", height=6)
                cpu_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                cpu_val = tk.Label(cpu_half, text="0%", font=(_MONO, 7, "bold"),
                                   bg=row_bg, fg="#3b82f6", width=4, anchor="e")
                cpu_val.pack(side="left")

                # Divider
                tk.Frame(bars_line, bg="#2a2d34", width=1).pack(
                    side="left", fill="y", padx=3)

                # RAM half
                ram_half = tk.Frame(bars_line, bg=row_bg)
                ram_half.pack(side="left", fill="x", expand=True)

                tk.Label(ram_half, text="RAM", font=(_BODY, 7, "bold"),
                         bg=row_bg, fg="#fbbf24").pack(side="left")

                ram_bar = AnimatedBar(ram_half, "#fbbf24", bg_color="#0d1117", height=6)
                ram_bar.bg_frame.pack(side="left", fill="x", expand=True, padx=(3, 2))

                ram_val = tk.Label(ram_half, text="0%", font=(_MONO, 7, "bold"),
                                   bg=row_bg, fg="#fbbf24", width=4, anchor="e")
                ram_val.pack(side="left")

                sys_widget_data = {
                    "row": row, "name": name_lbl,
                    "cpu_bar": cpu_bar, "cpu_val": cpu_val,
                    "ram_bar": ram_bar, "ram_val": ram_val,
                    "proc_name": "",
                }
                self.expanded_sys_widgets.append(sys_widget_data)

                # Wheel scroll must work with the cursor over the row content
                _wh = getattr(self, '_sys_wheel_handler', None)
                if _wh:
                    self._bind_wheel_recursive(row, _wh)

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
                widget_data["cpu_val"].config(text=self._fmt_proc_pct(cpu_pct))
                widget_data["ram_bar"].set_target(ram_pct)
                widget_data["ram_val"].config(text=self._fmt_proc_pct(ram_pct))
                widget_data["row"].pack(fill="x", pady=1)
            else:
                widget_data["name"].config(text="")
                widget_data["cpu_bar"].set_target(0)
                widget_data["cpu_val"].config(text="")
                widget_data["ram_bar"].set_target(0)
                widget_data["ram_val"].config(text="")

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
        """Handle window close (X button) -> Minimize to tray (NOT EXIT!)"""
        print("[ExpandedMode] Minimizing to tray (X clicked) - Program stays running!")

        # Show background notification
        if ToastNotification is not None:
            beautiful_message = (
                "PC_Workman still working!\n"
                "_________________________\n\n"
                "HCK_Labs\n"
                "_________________________\n\n"
                "Right-click tray icon -> Exit to close"
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
        """Restore window from system tray -> Expanded Mode"""
        print("[ExpandedMode] Restoring from tray")
        self.restore_window()

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

    def _on_lang_changed(self) -> None:
        """Called by i18n.set_lang() - refresh live dashboard labels immediately."""
        _safe = lambda w, **kw: (w.config(**kw) if w.winfo_exists() else None)
        try:
            if hasattr(self, "_mode_btn"):
                _safe(self._mode_btn, text=_t("dashboard.minimal_mode"))
            if hasattr(self, "_header_subtitle_lbl"):
                _safe(self._header_subtitle_lbl, text=_t("dashboard.subtitle"))
            if hasattr(self, "_current_usage_lbl"):
                _safe(self._current_usage_lbl, text=_t("dashboard.current_usage_label"))
        except Exception as exc:
            print(f"[i18n] dashboard live-refresh error: {exc}")

    def _switch_to_minimal(self):
        """Switch to minimal mode (⚡ Minimal Mode button)"""
        print("[ExpandedMode] Switching to Minimal Mode...")

        # Remember geometry so restore_window() can reapply it precisely
        if not self._is_maximized:
            try:
                self._last_normal_geometry = self.root.geometry()
            except Exception:
                pass

        # Hide Expanded window
        self.root.withdraw()

        # Switch to Minimal Mode
        if self.switch_to_minimal_callback:
            self.switch_to_minimal_callback()

    def restore_window(self):
        """Re-show the Expanded window after withdraw() (minimal mode / tray).

        On Windows, deiconify() can bring a window back in 'zoomed' state if it
        was ever maximized during the session — force the state we actually
        track in self._is_maximized instead of trusting the WM.
        """
        self.root.deiconify()
        try:
            if self._is_maximized:
                self.root.resizable(True, True)
                self.root.state("zoomed")
            else:
                if self.root.state() != "normal":
                    self.root.state("normal")
                geo = getattr(self, "_last_normal_geometry", None)
                if geo:
                    self.root.geometry(geo)
                else:
                    self.root.geometry(f"{_uis.compact_w()}x{_uis.compact_h()}")
                self.root.resizable(False, False)
        except Exception as e:
            print(f"[ExpandedMode] restore_window state error: {e}")
        self.root.lift()
        self.root.focus_force()

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
        """Update loop - 1s cadence, lightweight label updates only."""
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

                if self.current_view == "dashboard":
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
            err = str(e)
            if "bad window path" not in err and "invalid command name" not in err:
                print(f"[ExpandedMode] Update error: {e}")

        # 1-second cadence (was 300ms - main lag source)
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

            self.live_cpu_label.config(text=f"■ CPU {cpu:.0f}%")
            self.live_gpu_label.config(text=f"■ GPU {gpu:.0f}%")
            self.live_ram_label.config(text=f"■ RAM {ram:.0f}%")

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
                    # Buffer shifted left — a pinned LIVE bar tracks its
                    # sample, so the pin index moves with it (unpin at edge)
                    pin = getattr(self, '_chart_pin_idx', None)
                    if pin is not None and getattr(self, 'chart_filter', 'LIVE') == 'LIVE':
                        if pin <= 0:
                            self._chart_pin_idx = None
                            self._chart_hide_tip()
                        else:
                            self._chart_pin_idx = pin - 1
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

    # ── Dashboard chart (InteractiveChart) ───────────────────────────────────

    def _schedule_chart_update(self, delay_ms: int = 2000) -> None:
        """Schedule chart update, cancelling any pending one to avoid duplicates."""
        if self._chart_after_id is not None:
            try:
                self.root.after_cancel(self._chart_after_id)
            except Exception:
                pass
        self._chart_after_id = self.root.after(delay_ms, self._update_main_chart_data)

    def _update_main_chart_data(self, _from_anim: bool = False) -> None:
        """Animated bar chart for the main dashboard.
        Called every 2 s normally; called at ~60 fps during the grow animation."""
        self._chart_after_id = None
        if not hasattr(self, 'realtime_canvas') or not self._running:
            return

        try:
            canvas = self.realtime_canvas
            try:
                if not canvas.winfo_exists():
                    return
            except Exception:
                return

            W = canvas.winfo_width()
            H = canvas.winfo_height()
            if W <= 1 or H <= 1:
                if not _from_anim:
                    self._schedule_chart_update(150)
                return

            # Margins: left=28 (Y labels) right=8 top=8 bottom=10
            # (legend now lives in the footer strip below the canvas)
            ML, MR, MT, MB = 28, 8, 8, 10
            cw = W - ML - MR
            ch = H - MT - MB
            bottom_y = MT + ch

            # Occasional historical data refresh
            if not _from_anim and getattr(self, 'chart_filter', 'LIVE') != 'LIVE':
                self._hist_refresh_counter = getattr(self, '_hist_refresh_counter', 0) + 1
                if self._hist_refresh_counter >= 15:
                    self._hist_refresh_counter = 0
                    self._load_historical_chart_data(self.chart_filter)

            # Select data source
            if (getattr(self, 'chart_filter', 'LIVE') != 'LIVE' and
                    getattr(self, '_historical_chart_data', None)):
                cpu_data = list(self._historical_chart_data.get('cpu', []))
                ram_data = list(self._historical_chart_data.get('ram', []))
                gpu_data = list(self._historical_chart_data.get('gpu', []))
            else:
                cpu_data = list(self.chart_data.get('cpu', []))
                ram_data = list(self.chart_data.get('ram', []))
                gpu_data = list(self.chart_data.get('gpu', []))

            num = max(len(cpu_data), len(ram_data), len(gpu_data))

            # Detect new sample (only on non-animation passes to avoid false triggers)
            _prev_num = getattr(self, '_chart_last_num', 0)
            _new_bar  = (num > _prev_num) and (getattr(self, 'chart_filter', 'LIVE') == 'LIVE')
            if not _from_anim:
                self._chart_last_num = num

            ease = getattr(self, '_bar_anim_ease', 1.0)
            last = num - 1

            # ── Full redraw ──────────────────────────────────────────────────
            canvas.delete("all")

            # Grid lines at 25 / 50 / 75 / 100 %
            for pct in (25, 50, 75, 100):
                gy = bottom_y - int(pct / 100.0 * ch)
                canvas.create_line(ML, gy, W - MR, gy,
                                   fill="#0d1825", width=1, dash=(3, 5))
                canvas.create_text(ML - 3, gy, text=str(pct),
                                   fill="#2a3860", font=(_MONO, 5), anchor="e")

            if num == 0:
                canvas.create_text(
                    W // 2, MT + ch // 2,
                    text="Collecting data...",
                    fill="#1e2a3a", font=(_BODY, 8),
                )
                if not _from_anim:
                    self._schedule_chart_update(500)
                return

            bar_w = max(int(cw / num), 1)

            # ── Draw bars ────────────────────────────────────────────────────
            for i in range(num):
                x1 = ML + i * bar_w
                x2 = x1 + max(bar_w - 1, 1)
                cpu_v = float((cpu_data[i] if i < len(cpu_data) else 0) or 0)
                ram_v = float((ram_data[i] if i < len(ram_data) else 0) or 0)
                gpu_v = float((gpu_data[i] if i < len(gpu_data) else 0) or 0)

                # Apply ease-out growth to newest bar during animation
                if i == last and ease < 1.0:
                    cpu_v *= ease
                    ram_v *= ease
                    gpu_v *= ease

                cpu_top = bottom_y - int(cpu_v / 100.0 * ch)
                ram_top = bottom_y - int(ram_v / 100.0 * ch)
                gpu_top = bottom_y - int(gpu_v / 100.0 * ch)

                # CPU layer (bottom)
                if cpu_top < bottom_y:
                    canvas.create_rectangle(x1, cpu_top, x2, bottom_y,
                                            fill="#3b82f6", outline="")
                # RAM layer (middle)
                if ram_top < bottom_y:
                    canvas.create_rectangle(x1, ram_top, x2, bottom_y,
                                            fill="#fbbf24", outline="")
                # GPU layer (top / front)
                if gpu_top < bottom_y:
                    canvas.create_rectangle(x1, gpu_top, x2, bottom_y,
                                            fill="#10b981", outline="")

                # Bright 2 px top-edge highlight on the tallest series
                if bar_w >= 4:
                    tops = [
                        (cpu_top, "#60a5fa"),
                        (ram_top, "#fcd34d"),
                        (gpu_top, "#34d399"),
                    ]
                    valid = [(y, c) for y, c in tops if y < bottom_y]
                    if valid:
                        top_y, hl_col = min(valid, key=lambda t: t[0])
                        if top_y < bottom_y - 2:
                            canvas.create_rectangle(x1, top_y, x2, top_y + 2,
                                                    fill=hl_col, outline="")

            # ── Pin / hover guide line ────────────────────────────────────────
            pin = getattr(self, '_chart_pin_idx', None)
            if pin is not None and 0 <= pin < num:
                px = ML + pin * bar_w + bar_w // 2
                canvas.create_line(px, MT, px, bottom_y,
                                   fill="#334155", width=1, dash=(2, 3))
                # Keep the pinned tooltip glued to its bar with a live age
                if not _from_anim:
                    self._chart_refresh_pinned_tip(cpu_data, ram_data, gpu_data,
                                                   num, bar_w, ML, MT)

            # ── Schedule next update ─────────────────────────────────────────
            if _new_bar and not _from_anim:
                self._start_bar_grow_anim()
            elif not _from_anim:
                self._schedule_chart_update(2000)

        except Exception as e:
            err = str(e)
            if "bad window path" not in err and "invalid command name" not in err:
                print(f"[Chart] Error: {e}")
            if self._running and not _from_anim:
                self._schedule_chart_update(2000)

    def _start_bar_grow_anim(self) -> None:
        """Start a 600 ms ease-out grow animation for the newest bar."""
        import time as _time
        # Cancel any pending regular schedule
        if self._chart_after_id is not None:
            try:
                self.root.after_cancel(self._chart_after_id)
            except Exception:
                pass
            self._chart_after_id = None
        # Cancel any existing animation
        _old = getattr(self, '_bar_anim_id', None)
        if _old is not None:
            try:
                self.root.after_cancel(_old)
            except Exception:
                pass
        self._bar_anim_ease = 0.0
        self._bar_anim_t0   = _time.perf_counter()
        self._bar_anim_id   = self.root.after(16, self._tick_bar_grow_anim)

    def _tick_bar_grow_anim(self) -> None:
        """Animation tick — runs at ~60 fps until the bar reaches full height."""
        import time as _time
        self._bar_anim_id = None
        if not hasattr(self, 'realtime_canvas') or not self._running:
            self._schedule_chart_update(2000)
            return
        try:
            if not self.realtime_canvas.winfo_exists():
                self._schedule_chart_update(2000)
                return
        except Exception:
            self._schedule_chart_update(2000)
            return

        elapsed = _time.perf_counter() - self._bar_anim_t0
        t = min(elapsed / 0.60, 1.0)
        self._bar_anim_ease = 1.0 - (1.0 - t) ** 3   # ease-out cubic

        self._update_main_chart_data(_from_anim=True)

        if t < 1.0:
            self._bar_anim_id = self.root.after(16, self._tick_bar_grow_anim)
        else:
            self._bar_anim_ease = 1.0
            self._schedule_chart_update(2000)  # resume normal 2 s cycle

    def _chart_on_click(self, event: "tk.Event") -> None:
        """Pin / unpin detail tooltip on clicked bar."""
        try:
            canvas = self.realtime_canvas
            if not canvas.winfo_exists():
                return
            W = canvas.winfo_width()
            ML, MR = 28, 8
            cw = W - ML - MR

            if (getattr(self, 'chart_filter', 'LIVE') != 'LIVE' and
                    getattr(self, '_historical_chart_data', None)):
                cpu_d = list(self._historical_chart_data.get('cpu', []))
                ram_d = list(self._historical_chart_data.get('ram', []))
                gpu_d = list(self._historical_chart_data.get('gpu', []))
            else:
                cpu_d = list(self.chart_data.get('cpu', []))
                ram_d = list(self.chart_data.get('ram', []))
                gpu_d = list(self.chart_data.get('gpu', []))

            num = max(len(cpu_d), len(ram_d), len(gpu_d))
            if num < 1:
                return

            bar_w = max(int(cw / num), 1)
            idx   = max(0, min(num - 1, (event.x - ML) // max(bar_w, 1)))

            # Any click while pinned = unpin. In LIVE mode the pinned bar
            # drifts left every second, so "click the exact same bar" is
            # untargetable — this keeps the toggle predictable.
            if getattr(self, '_chart_pin_idx', None) is not None:
                self._chart_pin_idx = None
                self._chart_hide_tip()
            else:
                self._chart_pin_idx = idx
                self._chart_show_tip(idx, event.x, event.y,
                                     cpu_d, ram_d, gpu_d, num,
                                     canvas.winfo_width(), canvas.winfo_height())
        except Exception:
            pass

    def _chart_on_motion(self, event: "tk.Event") -> None:
        """Hover tooltip — suppressed when a bar is pinned."""
        if getattr(self, '_chart_pin_idx', None) is not None:
            return
        try:
            canvas = self.realtime_canvas
            if not canvas.winfo_exists():
                return
            W = canvas.winfo_width()
            ML, MR = 28, 8
            cw = W - ML - MR

            if (getattr(self, 'chart_filter', 'LIVE') != 'LIVE' and
                    getattr(self, '_historical_chart_data', None)):
                cpu_d = list(self._historical_chart_data.get('cpu', []))
                ram_d = list(self._historical_chart_data.get('ram', []))
                gpu_d = list(self._historical_chart_data.get('gpu', []))
            else:
                cpu_d = list(self.chart_data.get('cpu', []))
                ram_d = list(self.chart_data.get('ram', []))
                gpu_d = list(self.chart_data.get('gpu', []))

            num = max(len(cpu_d), len(ram_d), len(gpu_d))
            if num < 1:
                return

            bar_w = max(int(cw / num), 1)
            idx   = max(0, min(num - 1, (event.x - ML) // max(bar_w, 1)))
            self._chart_show_tip(idx, event.x, event.y,
                                 cpu_d, ram_d, gpu_d, num,
                                 canvas.winfo_width(), canvas.winfo_height())
        except Exception:
            pass

    def _chart_on_leave(self, event: "tk.Event") -> None:
        if getattr(self, '_chart_pin_idx', None) is None:
            self._chart_hide_tip()

    # Seconds covered by one bar per chart filter (LIVE appends 1 sample/s)
    _FILTER_SPAN_S = {"1H": 3600, "4H": 14400, "1D": 86400,
                      "1W": 604800, "1M": 2592000}

    def _ensure_chart_tip(self) -> "tk.Toplevel":
        """Build (once) the floating chart tooltip — borderless Toplevel at
        ~70% opacity with gaming typography and an hck_GPT-style PIN strip."""
        tw = getattr(self, '_chart_tip_win', None)
        try:
            if tw is not None and tw.winfo_exists():
                return tw
        except Exception:
            pass

        _BG = "#0a0e1a"
        tw = tk.Toplevel(self.root)
        tw.overrideredirect(True)
        try:
            tw.attributes("-alpha", 0.72)
        except Exception:
            pass
        tw.configure(bg=_BG, highlightthickness=1, highlightbackground="#22406b")

        inner = tk.Frame(tw, bg=_BG)
        inner.pack(padx=8, pady=6)

        rows = {}
        for key, label, col in (("cpu", "CPU", "#3b82f6"),
                                ("ram", "RAM", "#fbbf24"),
                                ("gpu", "GPU", "#10b981")):
            r = tk.Frame(inner, bg=_BG)
            r.pack(fill="x")
            tk.Label(r, text=label, font=("Segoe UI Black", 8),
                     bg=_BG, fg=col, width=4, anchor="w").pack(side="left")
            v = tk.Label(r, text="", font=(_MONO, 9, "bold"),
                         bg=_BG, fg="#e8eefc", anchor="e")
            v.pack(side="right", padx=(14, 0))
            rows[key] = v

        age = tk.Label(inner, text="", font=(_MONO, 7),
                       bg=_BG, fg="#5a719a", anchor="w")
        age.pack(fill="x", pady=(3, 0))

        # PIN strip — same construction as the hck_GPT TIP/HOT strips
        # (badge canvas + bordered frame), TIP colour family.
        pin_strip = tk.Frame(inner, bg="#1c1900",
                             highlightbackground="#3a3100", highlightthickness=1)
        _pb = tk.Canvas(pin_strip, width=30, height=14,
                        bg="#2e2800", highlightthickness=0)
        _pb.create_text(15, 7, text="PIN", fill="#d4a900",
                        font=("Consolas", 6, "bold"), anchor="center")
        _pb.pack(side="left", padx=(4, 0), pady=2)
        tk.Label(pin_strip,
                 text=_t("dashboard.chart_unpin", default="click bar to unpin"),
                 bg="#1c1900", fg="#d4a900", font=("Consolas", 7),
                 padx=5, pady=1, anchor="w").pack(side="left", fill="x")

        tw._rows = rows
        tw._age = age
        tw._pin_strip = pin_strip
        tw.withdraw()
        self._chart_tip_win = tw
        return tw

    def _chart_show_tip(self, idx, mx, my, cpu_d, ram_d, gpu_d, num, W, H) -> None:
        """Update + position the floating detail tooltip near the cursor/bar."""
        cpu_v = float((cpu_d[idx] if idx < len(cpu_d) else 0) or 0)
        ram_v = float((ram_d[idx] if idx < len(ram_d) else 0) or 0)
        gpu_v = float((gpu_d[idx] if idx < len(gpu_d) else 0) or 0)

        pinned = getattr(self, '_chart_pin_idx', None) is not None

        # Age of the hovered sample. LIVE collects 1 sample/s; historical
        # filters span a fixed window divided across the visible bars.
        _filter = getattr(self, 'chart_filter', 'LIVE')
        if _filter == 'LIVE':
            sec_per_bar = 1.0
        else:
            sec_per_bar = self._FILTER_SPAN_S.get(_filter, 3600) / max(num, 1)
        age_s = int((num - 1 - idx) * sec_per_bar)
        if age_s <= 0:
            age_str = "now"
        elif age_s < 60:
            age_str = f"{age_s}s ago"
        elif age_s < 3600:
            age_str = f"{age_s // 60}m {age_s % 60}s ago"
        else:
            age_str = f"{age_s // 3600}h {(age_s % 3600) // 60}m ago"

        try:
            canvas = self.realtime_canvas
            if not canvas.winfo_exists():
                return
        except Exception:
            return

        tw = self._ensure_chart_tip()
        tw._rows["cpu"].config(text=f"{cpu_v:.0f}%")
        tw._rows["ram"].config(text=f"{ram_v:.0f}%")
        tw._rows["gpu"].config(text=f"{gpu_v:.0f}%")
        tw._age.config(text=age_str)
        if pinned:
            tw._pin_strip.pack(fill="x", pady=(4, 0))
        else:
            tw._pin_strip.pack_forget()

        # Screen position next to the cursor (or pinned bar), kept on-screen
        tw.update_idletasks()
        tip_w = max(tw.winfo_reqwidth(), 110)
        tip_h = tw.winfo_reqheight()
        px = canvas.winfo_rootx() + mx + 16
        py = canvas.winfo_rooty() + my - tip_h - 12
        scr_w = self.root.winfo_screenwidth()
        if px + tip_w > scr_w - 4:
            px = canvas.winfo_rootx() + mx - tip_w - 16
        if py < 4:
            py = canvas.winfo_rooty() + my + 18
        tw.geometry(f"+{px}+{py}")
        try:
            tw.deiconify()
            tw.lift()
        except Exception:
            pass

    def _chart_refresh_pinned_tip(self, cpu_d, ram_d, gpu_d, num,
                                  bar_w, ML, MT) -> None:
        """Re-anchor + refresh the pinned tooltip on every chart redraw so the
        age keeps ticking and the box follows its bar."""
        pin = getattr(self, '_chart_pin_idx', None)
        if pin is None or not (0 <= pin < num):
            return
        try:
            canvas = self.realtime_canvas
            if not canvas.winfo_exists():
                return
            px = ML + pin * bar_w + bar_w // 2
            self._chart_show_tip(pin, px, MT + 14,
                                 cpu_d, ram_d, gpu_d, num,
                                 canvas.winfo_width(), canvas.winfo_height())
        except Exception:
            pass

    def _chart_hide_tip(self) -> None:
        tw = getattr(self, '_chart_tip_win', None)
        if tw is not None:
            try:
                tw.withdraw()
            except Exception:
                pass

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
            err = str(e)
            if "bad window path" not in err and "invalid command name" not in err:
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

        # Update health status
        if value < 85:
            card["health_label"].config(text=_t("dashboard.status_all_good"),    fg="#10b981")
        else:
            card["health_label"].config(text=_t("dashboard.status_needs_check"), fg="#f59e0b")

        # Update load status
        if value < 10:
            card["load_label"].config(text=_t("dashboard.no_activity"),    fg=THEME["muted"])
        elif value < 50:
            card["load_label"].config(text=_t("dashboard.status_standard"), fg="#3b82f6")
        elif value < 80:
            card["load_label"].config(text=_t("dashboard.status_heavy"),    fg="#f59e0b")
        else:
            card["load_label"].config(text=_t("dashboard.status_max"),      fg="#ef4444")

    @staticmethod
    def _draw_card_corner(canvas) -> None:
        """Overlay the component name in the sparkline's top-left corner
        (maximized hardware cards). Re-drawn after every sparkline pass."""
        _title = getattr(canvas, "_corner_title", None)
        if not _title:
            return
        t_id = canvas.create_text(7, 6, text=_title, anchor="nw",
                                  font=("Segoe UI Black", 8),
                                  fill=getattr(canvas, "_corner_color", "#e2e8f0"))
        _sub = getattr(canvas, "_corner_sub", "")
        if _sub:
            bbox = canvas.bbox(t_id)
            canvas.create_text((bbox[2] if bbox else 34) + 6, 8, text=_sub,
                               anchor="nw", font=(_BODY, 6), fill="#7a96b2")

    def _draw_sparkline(self, canvas, data, color):
        """Draw mini sparkline chart"""
        if not data or len(data) < 2:
            # No data yet — still show the corner label on the empty canvas
            try:
                if canvas.winfo_exists():
                    canvas.delete("all")
                    self._draw_card_corner(canvas)
            except Exception:
                pass
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

            # Component name overlaid in the chart corner (maximized cards)
            self._draw_card_corner(canvas)

        except Exception as e:
            err = str(e)
            if "bad window path" not in err and "invalid command name" not in err:
                print(f"[Sparkline] Error: {e}")

    def _update_top5_processes(self):
        """Update TOP process panels with animation.

        Note: the old primary branch called data_manager.get_latest_snapshot(),
        a method that exists nowhere in the codebase — psutil has always been
        the real path, so the dead branch was removed.
        """
        try:
            if psutil is not None:
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

                # Filter: remove System Idle Process (PID 0, not a real process)
                procs = [p for p in procs
                         if p["name"].lower() not in ("system idle process", "idle")]

                # Sort by CPU descending
                procs.sort(key=lambda x: x["cpu_percent"], reverse=True)

                # Comprehensive Windows system process set
                _SYS_NAMES = {
                    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
                    "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
                    "dwm.exe", "ntoskrnl.exe", "hal.dll", "spoolsv.exe",
                    "searchindexer.exe", "taskhostw.exe", "taskhost.exe",
                    "audiodg.exe", "conhost.exe", "fontdrvhost.exe", "sihost.exe",
                    "dllhost.exe", "wermgr.exe", "msdtc.exe", "lsm.exe",
                    "memory compression", "secure system", "cryptographic services",
                }
                def _is_sys(name: str) -> bool:
                    n = name.lower()
                    return n in _SYS_NAMES or n.startswith("svchost")

                user_procs   = [p for p in procs if not _is_sys(p["name"])]
                system_procs = [p for p in procs if     _is_sys(p["name"])]

                _lim = getattr(self, '_proc_limit', 5)
                self._render_expanded_user_processes(user_procs[:_lim])
                self._render_expanded_system_processes(system_procs[:_lim])
        except Exception as e:
            err = str(e)
            if "bad window path" not in err and "invalid command name" not in err:
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

        # Create overlay frame.
        # Settings: starts below main header (header stays visible as per spec).
        # All other pages: covers full content area including header.
        # Slide starts at the actual content width — the hardcoded 980 left the
        # overlay already half-visible in maximized mode.
        try:
            _slide_x = max(self.content_area.winfo_width(), 980)
        except Exception:
            _slide_x = 980
        self.overlay_frame = tk.Frame(self.content_area, bg="#0f1117", relief="flat", bd=0)
        if page_id == "settings":
            self.overlay_frame.place(x=_slide_x, y=60, width=980, height=515)
        else:
            self.overlay_frame.place(x=_slide_x, y=0, relwidth=1.0, relheight=1.0)

        # Build page content
        self._build_overlay_content(page_id)

        # Animate slide-in from right - COVERS CONTENT AREA
        self._animate_overlay_slide(_slide_x, 0, page_id)

        # hck_GPT banner stays available on top of these overlay pages;
        # everywhere else the overlay (created later = higher) covers it.
        if page_id in ("your_pc", "fan_control"):
            try:
                _f = getattr(getattr(self, "gpt_panel", None), "frame", None)
                if _f is not None and _f.winfo_exists():
                    _f.lift()
            except Exception:
                pass

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
        try:
            end_x = max(self.content_area.winfo_width(), 980)  # fully off-screen
        except Exception:
            end_x = 980
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
        # ── Per-page header metadata (accent colour · title · subtitle) ──────
        _META = {
            "your_pc":          ("#3b82f6", "MÓJ PC",           "Overview · Performance · Health"),
            "sensors":          ("#f59e0b", "MONITORING",        "Temperatures · Voltages · Alerts"),
            "live_graphs":      ("#3b82f6", "MÓJ PC",           "Live data & hardware overview"),
            "optimization":     ("#8b5cf6", "OPTIMIZATION",     "Features, automation & power management"),
            "statistics":       ("#3b82f6", "STATISTICS",        "Usage trends & session history"),
            "fan_control":      ("#f59e0b", "FAN CONTROL",      "Cooling profiles & temperature curves"),
            "fans_hardware":    ("#f59e0b", "FANS — HARDWARE",  "Real-time fan monitoring"),
            "fans_usage_stats": ("#f59e0b", "FAN STATISTICS",   "Fan intensity over time"),
            "hck_labs":         ("#f59e0b", "HCK LABS",         "Engineering · Monitoring · Intelligence"),
            "guide":            ("#8b5cf6", "PROGRAM GUIDE",    "Master PC Workman — commands & features"),
            "settings":         ("#3b82f6", "SETTINGS",         "Language, appearance & behavior"),
        }
        accent, ov_title, ov_sub = _META.get(
            page_id, ("#8b5cf6", page_id.upper().replace("_", " "), ""))

        # ── Gradient canvas header ────────────────────────────────────────────
        hdr_frame = tk.Frame(self.overlay_frame, bg="#080b10")
        hdr_frame.pack(fill="x")

        hdr_cv = tk.Canvas(hdr_frame, bg="#080b10", height=64, highlightthickness=0)
        hdr_cv.pack(fill="both", expand=True)

        def _draw_hdr(e=None,
                      _cv=hdr_cv, _a=accent, _tl=ov_title, _sb=ov_sub):
            _cv.delete("all")
            W = _cv.winfo_width()
            if W < 10:
                return
            H = 64
            for y in range(H):
                t = y / H
                r = int(8 + 10 * t)
                g = int(11 + 11 * t)
                b = int(16 + 22 * t)
                _cv.create_line(0, y, W, y, fill=f"#{r:02x}{g:02x}{b:02x}")
            _cv.create_line(0, H - 1, W, H - 1, fill="#1e2840")
            _cv.create_rectangle(0, 0, 3, H, fill=_a, outline="")
            _cv.create_text(18, 19, text=_tl, anchor="w",
                            font=(_HDR, 12), fill="#c4cfdf")
            if _sb:
                _cv.create_text(18, 44, text=_sb, anchor="w",
                                font=(_BODY, 8), fill="#3d4a60")

        hdr_cv.bind("<Configure>", _draw_hdr)

        # ── Close + Maximize buttons (overlaid, top-right of header) ──────────
        close_btn = tk.Label(
            hdr_frame,
            text="✕",
            font=(_BODY, 10),
            bg="#080b10",
            fg="#6f86a3",
            cursor="hand2",
            padx=12,
        )
        close_btn.place(relx=1.0, y=8, anchor="ne", x=-4)
        close_btn.bind("<Button-1>", lambda e: self._close_overlay())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#ef4444"))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#6f86a3"))

        _ov_max_sym = "⊡" if self._is_maximized else "⤢"
        ov_max_btn = tk.Label(
            hdr_frame,
            text=_ov_max_sym,
            font=(_HDR, 10),
            bg="#090c14",
            fg="#6f86a3",
            cursor="hand2",
            padx=10,
        )
        ov_max_btn.place(relx=1.0, y=8, anchor="ne", x=-38)
        ov_max_btn.bind("<Button-1>", lambda e: self._toggle_maximize())
        ov_max_btn.bind("<Enter>",    lambda e: ov_max_btn.config(fg="#8b5cf6"))
        ov_max_btn.bind("<Leave>",    lambda e: ov_max_btn.config(fg="#6f86a3"))

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
        elif page_id == "settings":
            try:
                from ui.pages.settings_page import SettingsPage
                # show_header=False: overlay already shows "⚙ Settings" in its own header
                sp = SettingsPage(content_frame, show_header=False, app=self)
                sp.frame.pack(fill="both", expand=True)
            except Exception as _se:
                import traceback
                tk.Label(content_frame,
                         text=f"Settings error:\n{_se}",
                         font=(_BODY, 10), bg="#0f1117", fg="#ef4444",
                         justify="left", padx=20, pady=20).pack(anchor="nw")
                traceback.print_exc()

    # ========== PAGE BUILDERS ==========

    def _build_monitoring_sensors_page(self, parent):
        """MONITORING - Centrum: loads Monitoring & Alerts page"""
        try:
            from ui.pages.monitoring_alerts import build_monitoring_alerts_page
            build_monitoring_alerts_page(self, parent)
        except Exception as e:
            import traceback
            tk.Label(parent, text=f"Monitoring page error:\n{e}",
                     font=(_BODY, 10), bg="#0f1117", fg="#ef4444",
                     justify="left").pack(anchor="nw", padx=20, pady=20)
            traceback.print_exc()

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
                font=(_BODY, 12, "bold"),
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
                    font=(_BODY, 12, "bold"),
                    bg="#1a1d24",
                    fg=color
                )
                bullet.pack(side="left", padx=(5, 10))

                tip_lbl = tk.Label(
                    tip_frame,
                    text=tip,
                    font=(_BODY, 10),
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
            font=(_BODY, 12),
            bg="#0f1117",
            fg="#64748b",
            justify="center"
        ).pack(expand=True)

    def _build_hcklabs_page(self, parent):
        """HCK Labs - minimalist blog style"""
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
        def _hl_wheel(e):
            try:
                if cv.winfo_exists():
                    cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass
        # No add="+": overwrite the previous page's global wheel handler
        # instead of stacking a dead one per page visit.
        cv.bind_all("<MouseWheel>", _hl_wheel)
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
                 font=(_BODY, 11), bg=CARD, fg=MUTED, anchor="w").pack(anchor="w", pady=(2, 14))

        # Quick action row
        btn_row = tk.Frame(hero_inner, bg=CARD)
        btn_row.pack(anchor="w")

        def _make_hero_btn(p, label, color, cmd):
            b = tk.Label(p, text=label, font=(_HDR, 9, "bold"),
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
            tk.Label(wrap, text=title, font=(_HDR, 13, "bold"),
                     bg=BG, fg=TEXT, anchor="w").pack(anchor="w")
            if subtitle:
                tk.Label(wrap, text=subtitle, font=(_BODY, 9),
                         bg=BG, fg=MUTED, anchor="w").pack(anchor="w", pady=(1, 0))
            tk.Frame(wrap, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))
            return wrap

        def _card(parent, accent, title, body):
            frame = tk.Frame(parent, bg=CARD)
            frame.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
            tk.Frame(frame, bg=accent, height=3).pack(fill="x")
            inner = tk.Frame(frame, bg=CARD)
            inner.pack(fill="both", expand=True, padx=14, pady=12)
            tk.Label(inner, text=title, font=(_HDR, 10, "bold"),
                     bg=CARD, fg=TEXT, anchor="w").pack(anchor="w")
            tk.Label(inner, text=body, font=(_BODY, 9), bg=CARD, fg=DIM,
                     anchor="w", justify="left", wraplength=280).pack(anchor="w", pady=(4, 0))

        _section("About", "What PC_Workman is and why it exists")
        about_row = tk.Frame(sf, bg=BG)
        about_row.pack(fill="x", padx=24)
        _card(about_row, BLUE, "Mission",
              "Make system monitoring accessible, beautiful, and intelligent for everyone - not just power users.")
        _card(about_row, VIOLET, "Inspiration",
              "Designed with learnings from Tesla UI, Apple macOS, and MSI Afterburner. Calm, dense, and fast.")
        _card(about_row, EMERALD, "Philosophy",
              "Local-first. No cloud, no account - monitoring and AI run on your machine. Optional anonymous telemetry, off in one click in Settings.")

        # ── FEATURES GRID ───────────────────────────────────────────────────
        _section("What makes it different")
        features = [
            (AMBER,   "Dual-Mode",        "Minimal widget + full control center - switch instantly"),
            (VIOLET,  "HCK_GPT",          "Local AI insights, habit tracking, anomaly alerts - no API key"),
            (BLUE,    "Stats Engine v2",   "SQLite pipeline: minute -> hourly -> daily -> monthly retention"),
            (EMERALD, "Auto Optimization", "RAM flush, DNS cache, temp files, process priority - automated & silent"),
            ("#ef4444","Time-Travel Stats","Click any historical point to see what was running then"),
            (DIM,     "Universal HW",      "All CPUs, all GPUs, all configs - no driver dependencies"),
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
            tk.Label(r, text=vs, font=(_HDR, 9, "bold"),
                     bg=bg_row, fg=BLUE, width=24, anchor="w").pack(side="left", padx=16, pady=8)
            tk.Label(r, text="->  " + advantage, font=(_BODY, 9),
                     bg=bg_row, fg=DIM).pack(side="left", padx=4, pady=8)

        # ── VERSION FOOTER ───────────────────────────────────────────────────
        _section("Build info")
        footer = tk.Frame(sf, bg=CARD)
        footer.pack(fill="x", padx=24, pady=(8, 32))
        pairs = [
            ("Version", "PC_Workman HCK 1.7.2"),
            ("Engine", "Stats Engine v2 - SQLite WAL"),
            ("Runtime", "Python 3.9+ / tkinter"),
            ("License", "MIT - HCK_Labs"),
        ]
        for label, val in pairs:
            r = tk.Frame(footer, bg=CARD)
            r.pack(fill="x", padx=16, pady=3)
            tk.Label(r, text=label, font=(_BODY, 9), bg=CARD,
                     fg=MUTED, width=12, anchor="w").pack(side="left")
            tk.Label(r, text=val, font=(_HDR, 9), bg=CARD,
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

    def _build_guide_page(self, parent):
        """Guide - modern dark blog layout with command chips and changelog strip."""
        BG      = "#060911"
        CARD    = "#0c0f1a"
        CARD2   = "#0f1320"
        BORDER  = "#161c2e"
        TEXT    = "#e2e8f0"
        MUTED   = "#475569"
        DIM     = "#8b9ab5"
        VIOLET  = "#8b5cf6"
        BLUE    = "#3b82f6"
        EMERALD = "#10b981"
        AMBER   = "#f59e0b"
        ROSE    = "#f43f5e"
        SLATE   = "#64748b"

        # ── scrollable canvas ─────────────────────────────────────────────────────
        cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=cv.yview,
                          bg=BG, troughcolor=BG, width=5)
        sf = tk.Frame(cv, bg=BG)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        win_id = cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.bind("<Configure>", lambda e: cv.itemconfig(win_id, width=e.width))
        def _gd_wheel(e):
            try:
                if cv.winfo_exists():
                    cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass
        # No add="+": overwrite the previous page's global wheel handler
        # instead of stacking a dead one per page visit.
        cv.bind_all("<MouseWheel>", _gd_wheel)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        # ── HERO ──────────────────────────────────────────────────────────────────
        hero = tk.Frame(sf, bg=CARD)
        hero.pack(fill="x")

        # 3-colour gradient bar (violet -> blue)
        grad_bar = tk.Frame(hero, bg=CARD)
        grad_bar.pack(fill="x")
        for col in ("#7c3aed", "#6d28d9", "#4f46e5", "#3b82f6"):
            tk.Frame(grad_bar, bg=col, height=3, width=1).pack(
                side="left", fill="y", expand=True)

        hero_body = tk.Frame(hero, bg=CARD)
        hero_body.pack(fill="x", padx=36, pady=(22, 20))

        left_h = tk.Frame(hero_body, bg=CARD)
        left_h.pack(side="left", fill="both", expand=True)

        # Version badge
        badge_row = tk.Frame(left_h, bg=CARD)
        badge_row.pack(anchor="w")
        tk.Label(badge_row, text=" v1.7 ", font=(_BODY, 8, "bold"),
                 bg="#1e1b4b", fg="#818cf8", padx=6, pady=2).pack(side="left")
        tk.Label(badge_row, text="  HCK_Labs",
                 font=(_BODY, 8), bg=CARD, fg=MUTED).pack(side="left")

        tk.Label(left_h, text="Program Guide",
                 font=(_BODY, 28), bg=CARD, fg=TEXT, anchor="w").pack(anchor="w", pady=(6, 0))
        tk.Label(left_h,
                 text="Everything you need to master PC_Workman - from live charts to AI commands.",
                 font=(_BODY, 10), bg=CARD, fg=MUTED, anchor="w").pack(anchor="w", pady=(4, 0))

        # Live Guide button (right, prominent)
        right_h = tk.Frame(hero_body, bg=CARD)
        right_h.pack(side="right", anchor="center")

        live_btn = tk.Label(right_h,
                            text="▶  Guide on program LIVE",
                            font=(_BODY, 11, "bold"),
                            bg=VIOLET, fg="#ffffff",
                            padx=22, pady=12, cursor="hand2")
        live_btn.pack()
        tk.Label(right_h, text="Interaktywny przewodnik krok po kroku",
                 font=(_BODY, 8), bg=CARD, fg=MUTED).pack(pady=(4, 0))

        def _live_guide_click(e=None):
            self._close_overlay()
            self.root.after(280, self._start_live_guide)

        live_btn.bind("<Button-1>", _live_guide_click)
        live_btn.bind("<Enter>",    lambda e: live_btn.config(bg="#7c3aed"))
        live_btn.bind("<Leave>",    lambda e: live_btn.config(bg=VIOLET))

        tk.Frame(hero, bg=BORDER, height=1).pack(fill="x")

        # ── What's new strip ──────────────────────────────────────────────────────
        news_strip = tk.Frame(sf, bg="#0a0e1a")
        news_strip.pack(fill="x")
        tk.Frame(news_strip, bg=EMERALD, height=2).pack(fill="x")
        news_inner = tk.Frame(news_strip, bg="#0a0e1a")
        news_inner.pack(fill="x", padx=36, pady=10)

        tk.Label(news_inner, text="✦  What's new in v1.7",
                 font=(_BODY, 9, "bold"), bg="#0a0e1a", fg=EMERALD).pack(side="left")

        changes = [
            ("hck_GPT proactive alerts", VIOLET),
            ("12 new AI intents", BLUE),
            ("Session budget (3/30 min)", EMERALD),
            ("Paper-plane send button", AMBER),
        ]
        for txt, col in changes:
            tk.Label(news_inner, text=f"  ·  {txt}",
                     font=(_BODY, 9), bg="#0a0e1a", fg=col).pack(side="left")

        tk.Frame(news_strip, bg=BORDER, height=1).pack(fill="x")

        # ── Local helpers ─────────────────────────────────────────────────────────
        def _gap(h=32):
            tk.Frame(sf, bg=BG, height=h).pack()

        def _section_hdr(icon, title, subtitle, accent, tag=None):
            """Full-width section header card."""
            _gap(0)
            wrap = tk.Frame(sf, bg=BG)
            wrap.pack(fill="x")
            tk.Frame(wrap, bg=accent, height=2).pack(fill="x")
            inner = tk.Frame(wrap, bg=CARD)
            inner.pack(fill="x", padx=0)

            row = tk.Frame(inner, bg=CARD)
            row.pack(fill="x", padx=32, pady=16)

            left_s = tk.Frame(row, bg=CARD)
            left_s.pack(side="left", fill="both", expand=True)

            title_row = tk.Frame(left_s, bg=CARD)
            title_row.pack(anchor="w")
            tk.Label(title_row, text=f"{icon}  {title}",
                     font=(_BODY, 15, "bold"),
                     bg=CARD, fg=TEXT, anchor="w").pack(side="left")
            if tag:
                tk.Label(title_row, text=f"  {tag}",
                         font=(_BODY, 8, "bold"),
                         bg=accent, fg="#ffffff",
                         padx=6, pady=2).pack(side="left", padx=(10, 0), anchor="center")

            if subtitle:
                tk.Label(left_s, text=subtitle,
                         font=(_BODY, 10), bg=CARD, fg=MUTED, anchor="w").pack(anchor="w", pady=(2, 0))
            return wrap

        def _article(bullets, accent=DIM):
            """Bulleted article block."""
            body = tk.Frame(sf, bg=BG)
            body.pack(fill="x", padx=32, pady=(8, 0))
            for bullet in bullets:
                row = tk.Frame(body, bg=BG)
                row.pack(fill="x", pady=4)
                tk.Frame(row, bg=accent, width=3).pack(side="left", fill="y", padx=(0, 12))
                tk.Label(row, text=bullet,
                         font=(_BODY, 11), bg=BG, fg=DIM,
                         anchor="w", justify="left", wraplength=800).pack(anchor="w", pady=5)

        def _chip_row(label, chips, bg_chips, fg_chips="#ffffff"):
            """Row of command example chips."""
            row = tk.Frame(sf, bg=BG)
            row.pack(fill="x", padx=32, pady=(6, 0))
            tk.Label(row, text=label,
                     font=(_BODY, 9), bg=BG, fg=MUTED).pack(side="left", padx=(0, 12))
            for chip_text in chips:
                tk.Label(row, text=chip_text,
                         font=(_BODY, 9, "bold"),
                         bg=bg_chips, fg=fg_chips,
                         padx=10, pady=3).pack(side="left", padx=(0, 6))

        # ── SECTION 1 - Core Monitoring ───────────────────────────────────────────
        _section_hdr("📊", "Core Monitoring", "What runs under the hood, 24/7", BLUE)
        _article([
            "Real-time CPU, GPU, RAM tracking - updates every second in a background thread so the UI stays buttery smooth.",
            "Session averages on the dashboard give an instant health baseline - no digging into charts needed.",
            "Stats Engine v2 stores minute-by-minute data in SQLite - browse 1H / 4H / 1D / 1W / 1M history in Monitoring.",
            "All your data lives on your machine - no cloud, no accounts. The optional anonymous telemetry can be switched off in Settings.",
        ], BLUE)
        _gap(32)

        # ── SECTION 2 - hck_GPT ───────────────────────────────────────────────────
        _section_hdr("🤖", "HCK_GPT Assistant",
                     "Local AI companion - no internet, no API key", EMERALD, tag="AI")
        _article([
            "Understands natural language - ask about CPU temps, RAM, gaming mode, or overnight performance in plain Polish or English.",
            "Proactive alerts: up to 3 unsolicited tips per 30 minutes - idle tips, process spikes, morning briefings.",
            "Today Report: one command gives you a session chart, top processes, alert status, and uptime.",
            "Everything runs locally - nothing is sent to any server, ever.",
        ], EMERALD)
        _chip_row("Example commands:",
                  ["stats", "temperatura", "podaj wyniki", "game ready", "flush RAM",
                   "morning brief", "zabij chrome"],
                  "#0d2e1f", "#34d399")
        _gap(32)

        # ── SECTION 3 - Optimization ──────────────────────────────────────────────
        _section_hdr("⚡", "Optimization & Automation",
                     "Set it once, let it run", AMBER)
        _article([
            "AUTO RAM Flush watches memory every 10 s - if usage stays above threshold for 30 s it flushes without interrupting you.",
            "TURBO BOOST fires all Quick Actions at once: High Performance power plan, DNS flush, temp files, process priority.",
            "Settings persist across restarts - your toggle states live in settings/app_settings.json.",
            "Process Guard suspends background hogs when idle threshold is reached, restores them on close.",
        ], AMBER)
        _gap(32)

        # ── SECTION 4 - DeepMonitor ───────────────────────────────────────────────
        _section_hdr("🗠", "DeepMonitor & Graphs",
                     "Full picture of your hardware at a glance", VIOLET)
        _article([
            "DeepMonitor page shows live scrolling waveforms for CPU, GPU, RAM - refreshed every 200 ms.",
            "Hardware & Health Table (OPEN TABLE button) exposes every sensor: temps, voltages, fan speeds.",
            "Monitoring - Centrum page shows time-travel statistics with spike detection and hover tooltips.",
            "Fan Dashboard controls cooling profiles and visualises fan curves in real time.",
        ], VIOLET)
        _gap(32)

        # ── SECTION 5 - Privacy ───────────────────────────────────────────────────
        _section_hdr("🛡️", "Privacy & Safety",
                     "Your PC, your data, your rules", SLATE)
        _article([
            "PC_Workman is 100 % offline. Nothing is transmitted, collected, or uploaded - ever.",
            "Every feature can be disabled individually: monitoring-only, optimisation-only, or everything.",
            "Optimisation actions are safe - RAM flush uses Windows APIs; no registry edits without confirmation.",
            "Logs in data/logs/ can be deleted any time; the app recreates them on next launch.",
        ], SLATE)

        _gap(32)

        # ── QUICK TIPS - 3-column grid ────────────────────────────────────────────
        tips_hdr = tk.Frame(sf, bg=BG)
        tips_hdr.pack(fill="x", padx=32, pady=(0, 10))
        tk.Label(tips_hdr, text="💡  Quick Tips",
                 font=(_BODY, 13, "bold"), bg=BG, fg=AMBER).pack(side="left")
        tk.Frame(tips_hdr, bg=BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(14, 0), pady=3)

        tips = [
            (VIOLET, "Floating Monitor",
             "Launch the always-on-top overlay from the dashboard - it floats above every window."),
            (BLUE, "Tray Icon",
             "The 3-bar system-tray icon shows CPU/GPU/RAM instantly - right-click for quick actions."),
            (EMERALD, "Chat Shortcuts",
             "Type 'stats', 'temp', or 'game ready' in hck_GPT for instant system snapshots."),
            (AMBER, "Mouse Wheel",
             "Scroll anywhere in any panel - all pages support mousewheel navigation."),
            (ROSE, "Keyboard Esc",
             "Press Esc in any overlay (Live Guide, pop-ups) to dismiss it instantly."),
            (SLATE, "Minimal Mode",
             "Compact sidebar collapses to an icon rail after 3 s of inactivity - maximises screen space."),
        ]

        tips_grid = tk.Frame(sf, bg=BG)
        tips_grid.pack(fill="x", padx=32, pady=(0, 8))
        tips_grid.columnconfigure(0, weight=1, uniform="tip")
        tips_grid.columnconfigure(1, weight=1, uniform="tip")
        tips_grid.columnconfigure(2, weight=1, uniform="tip")

        for idx, (accent, tip_title, tip_body) in enumerate(tips):
            col = idx % 3
            row_idx = idx // 3

            tip_outer = tk.Frame(tips_grid, bg=BORDER)
            tip_outer.grid(row=row_idx, column=col, sticky="nsew",
                           padx=(0, 6) if col < 2 else 0,
                           pady=(0, 8))
            tip_inner = tk.Frame(tip_outer, bg=CARD2)
            tip_inner.pack(fill="both", expand=True, padx=1, pady=1)

            tk.Frame(tip_inner, bg=accent, height=2).pack(fill="x")
            tk.Label(tip_inner, text=tip_title,
                     font=(_BODY, 10, "bold"),
                     bg=CARD2, fg=TEXT).pack(anchor="w", padx=14, pady=(10, 3))
            tk.Label(tip_inner, text=tip_body,
                     font=(_BODY, 9), bg=CARD2, fg=DIM,
                     wraplength=220, justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        _gap(40)

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
            font=(_BODY, 14, "bold"),
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
                font=(_MONO, 10),
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
                font=(_MONO, 11),
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
                font=(_BODY, 10, "bold"),
                bd=0,
                padx=15,
                command=send_message
            )
            send_btn.pack(side="right")

        except ImportError:
            tk.Label(
                content,
                text="Service Setup not available\n\nChat handler module not found.",
                font=(_BODY, 12),
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
            font=(_BODY, 10),
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
            font=(_BODY, 14, "bold"),
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
            font=(_BODY, 16, "bold"),
            bg="#0f1117",
            fg="#ffffff"
        ).pack(anchor="w", pady=(0, 15))

        # Version info
        version_frame = tk.Frame(content, bg="#0f1117")
        version_frame.pack(anchor="w", pady=5)

        tk.Label(
            version_frame,
            text="Your version: ",
            font=(_BODY, 12),
            bg="#0f1117",
            fg="#cbd5e1"
        ).pack(side="left")

        tk.Label(
            version_frame,
            text="v1.7.1",
            font=(_BODY, 12, "bold"),
            bg="#0f1117",
            fg="#10b981"
        ).pack(side="left")

        tk.Label(
            version_frame,
            text=" - 10.04.2026",
            font=(_BODY, 12),
            bg="#0f1117",
            fg="#64748b"
        ).pack(side="left")

        # Message text
        tk.Label(
            content,
            text="\nI would really like to tell you if there's a new update!\nBut I'm limited ;)",
            font=(_BODY, 11),
            bg="#0f1117",
            fg="#94a3b8",
            justify="left"
        ).pack(anchor="w", pady=(15, 10))

        tk.Label(
            content,
            text="Please check here if your version is up to date!",
            font=(_BODY, 11),
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
            font=(_HDR, 11, "bold"),
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
            font=(_BODY, 10),
            bd=0,
            padx=20,
            pady=8,
            command=dialog.destroy
        )
        close_btn.pack(pady=15)

    # ========== STARTUP / APP-INSTALL WATCHER ==========

    def _start_system_watchers(self) -> None:
        """
        Launch the StartupWatcher background thread.
        Callbacks are marshalled onto the main tkinter thread via root.after(0,…).
        """
        try:
            from core.startup_watcher import get_watcher
            watcher = get_watcher()
            watcher.register_startup_cb(self._on_new_startup_entry)
            watcher.register_app_cb(self._on_new_app_installed)
            watcher.start()
            print("[SystemWatcher] Startup + app-install watcher started.")
        except Exception as exc:
            print(f"[SystemWatcher] Failed to start: {exc}")

    def _on_new_startup_entry(self, name: str, exe: str, hive: str) -> None:
        """Called from watcher thread - marshal to main thread."""
        def _show():
            try:
                import json, os as _os
                _sf = _os.path.join(
                    _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
                    "settings", "app_settings.json",
                )
                with open(_sf, encoding="utf-8") as _f:
                    lang = json.load(_f).get("language", "en")
            except Exception:
                lang = "en"
            from ui.components.system_toast import show_startup_toast

            def _go_startup():
                self.current_view = None
                self._switch_to_page("startup_manager")
                if hasattr(self, "sidebar"):
                    self.sidebar.set_active_page("startup_manager")

            show_startup_toast(
                self.root, name, exe, hive,
                on_manage=_go_startup, lang=lang,
            )
        self.root.after(0, _show)

    def _on_new_app_installed(self, display_name: str, exe_path: str) -> None:
        """Called from watcher thread - marshal to main thread."""
        def _show():
            try:
                import json, os as _os
                _sf = _os.path.join(
                    _os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))),
                    "settings", "app_settings.json",
                )
                with open(_sf, encoding="utf-8") as _f:
                    lang = json.load(_f).get("language", "en")
            except Exception:
                lang = "en"
            from ui.components.system_toast import show_app_install_toast
            show_app_install_toast(self.root, display_name, exe_path, lang=lang)
        self.root.after(0, _show)

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
    popup.title("DeepMonitor - PC Workman")
    popup.configure(bg="#07090f")
    popup.resizable(True, True)

    content = tk.Frame(popup, bg="#07090f")
    content.pack(fill="both", expand=True)

    if ProInfoTable:
        try:
            table = ProInfoTable(content)
            table.pack(fill="both", expand=True)
        except Exception as e:
            tk.Label(content, text=f"Error loading table: {e}",
                     font=(_BODY, 10), bg="#07090f", fg="#ef4444").pack(pady=50)
    else:
        tk.Label(content, text="Hardware table not available",
                 font=(_BODY, 10), bg="#07090f", fg="#6b7280").pack(pady=50)

    # Center on screen - wider for 4 columns
    popup.update_idletasks()
    w, h = 660, 760
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

    # ── MY PC - monitor + stand ───────────────────────────────────────────────
    if page_id == "your_pc":
        R(-11, -10,  11,  5)                    # bezel
        R( -9,  -8,   9,  3, fill=DK)           # screen glass
        R( -1,   5,   1,  9)                    # stand arm
        R( -6,   8,   6, 11)                    # base
        O(  7,   0,   9,  2, fill="#10b981")    # power LED green

    # ── MONITORING - big exclamation mark ────────────────────────────────────
    elif page_id == "sensors":
        R(-2, -12,  2,  4, fill=A)             # stem (tall)
        O(-3,   6,  3, 12, fill=A)             # dot (round)

    # ── DEEPMONITOR - bar chart ───────────────────────────────────────────────
    elif page_id == "live_graphs":
        R(-11,  3, -5, 10)                      # short bar
        R( -3, -3,  3, 10)                      # medium bar
        R(  5, -9, 11, 10)                      # tall bar
        R(-13,  9, 13, 12)                      # baseline

    # ── OPTIMIZATION - lightning bolt ─────────────────────────────────────────
    elif page_id == "optimization":
        P((4,-12), (-2,-1), (3,-1), (-4,12), (-5,12),
          (1, 1), (-4,  1), (2,-12))

    # ── FAN DASHBOARD - monitor icon (same as My PC), purple tint ────────────
    elif page_id == "fan_control":
        R(-11, -10,  11,  5)                    # bezel
        R( -9,  -8,   9,  3, fill=DK)           # screen glass
        R( -1,   5,   1,  9)                    # stand arm
        R( -6,   8,   6, 11)                    # base
        O(  7,   0,   9,  2, fill="#a78bfa")    # purple LED

    # ── HCK_LABS - globe icon ─────────────────────────────────────────────────
    elif page_id == "hck_labs":
        O(-11, -11, 11, 11)                                                    # outer sphere
        O( -5, -11,  5, 11)                                                    # central meridian oval
        canvas.create_line(cx-11, cy,   cx+11, cy,   fill=accent, width=1.5)  # equator
        canvas.create_line(cx- 9, cy-5, cx+ 9, cy-5, fill=accent, width=1.0)  # N parallel
        canvas.create_line(cx- 9, cy+5, cx+ 9, cy+5, fill=accent, width=1.0)  # S parallel

    # ── GUIDE - open book ─────────────────────────────────────────────────────
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
    """Called via root.after() - uses root as anchor."""
    _open_hw_table_popup(root)
