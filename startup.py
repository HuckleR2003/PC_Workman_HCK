"""
startup.py
Entry point for PC Workman HCK.
Includes Diagnostic Console Helper that auto-hides on successful UI launch.
"""

# ONE version source (utils/app_version.py) - bump it there, never here.
from utils.app_version import APP_VERSION, MAIN_WINDOW_TITLE

HELPER_VERSION = "1.6.3"

# ============================================
# IMMEDIATE CONSOLE OUTPUT - Shows before any imports
# ============================================
print("=" * 70)
print(f"  PC Workman v{APP_VERSION} - This console will close if program runs correctly")
print("  Attach this information when reporting errors/issues")
print("=" * 70)
print()
print("=" * 37)
print(f"  DIAGNOSTIC CONSOLE HELPER v{HELPER_VERSION}  ")
print("=" * 37)
print()
print("[~] Initializing Python environment...")

import sys
import io
import os
import ctypes
from typing import Optional, Any

# ── High-DPI awareness - MUST run before any tk.Tk() is created ────────────────
# Without this, Windows bitmap-stretches the whole UI on displays scaled above
# 100% (125% / 150% - standard on laptops), making every label blurry and hard
# to read. Per-Monitor-Aware-V2 gives crisp native rendering; the app then sees
# the REAL screen resolution, so utils.ui_scale picks the correct SCALE tier
# instead of a stretched-down one. This is THE fix for "blurry / unreadable text".
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()    # legacy fallback (Win 7/8)
        except Exception:
            pass

print("[+] Python environment ready")


# ============================================
# OPTIONAL ADMIN ELEVATION (opt-in, Settings -> "Run as administrator")
# ============================================
# Some actions (HKLM startup entries, certain services, power plans) need
# Administrator. Rather than fail silently, the user can tick one Settings box
# and PC Workman re-launches itself elevated at startup (a single UAC prompt).
# Must run BEFORE the single-instance mutex and any tk.Tk(). Declining UAC is
# fine - the app just continues without admin. Never loops: an elevated process
# passes the IsUserAnAdmin() check and returns immediately.
def _maybe_elevate() -> None:
    if sys.platform != "win32":
        return
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return                                   # already elevated
    except Exception:
        return
    # read the opt-in pref
    try:
        import json
        from utils.paths import APP_DIR
        _sf = os.path.join(APP_DIR, "settings", "app_settings.json")
        with open(_sf, encoding="utf-8") as _f:
            if not json.load(_f).get("run_as_admin", False):
                return
    except Exception:
        return
    exe = sys.executable
    # Microsoft Store / MSIX: the exe is a virtualized WindowsApps path; a
    # "runas" relaunch of it is unreliable and against Store guidance. Skip -
    # the app works fine without elevation there.
    if "windowsapps" in exe.lower():
        return
    try:
        if getattr(sys, "frozen", False):
            target, params = exe, " ".join(f'"{a}"' for a in sys.argv[1:])
        else:
            target = exe
            params = " ".join(f'"{a}"' for a in
                              [os.path.abspath(sys.argv[0])] + sys.argv[1:])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", target,
                                                 params, None, 1)
        if rc > 32:                                  # elevated instance launched
            sys.exit(0)                              # quit the non-elevated one
    except Exception:
        pass                                         # UAC declined -> run as-is


_maybe_elevate()

print("[~] Loading core systems...")

# ============================================
# DIAGNOSTIC CONSOLE HELPER
# ============================================
def get_console_window():
    """Get handle to console window"""
    if sys.platform == 'win32':
        return ctypes.windll.kernel32.GetConsoleWindow()
    return None

def hide_console():
    """Hide the console window"""
    if sys.platform == 'win32':
        hwnd = get_console_window()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0

def show_console():
    """Show the console window"""
    if sys.platform == 'win32':
        hwnd = get_console_window()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW = 5

def log(msg: str, level: str = "INFO"):
    """Print log message with level prefix"""
    prefix = {
        "INFO": "[*]",
        "OK": "[+]",
        "WARN": "[!]",
        "ERROR": "[-]",
        "LOAD": "[~]"
    }.get(level, "[*]")
    print(f"{prefix} {msg}")

# Fix console encoding issues on Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("[+] Core systems loaded")

try:
    from utils.fonts import load
    _n = load()
    if _n:
        print(f"[+] Inter font loaded ({_n} files)")
    else:
        print("[~] Inter not found - using Segoe UI  (place Inter*.ttf in data/fonts/ to upgrade)")
except Exception:
    pass

# ============================================
# STARTUP SEQUENCE
# ============================================
def run_demo():
    print()
    log("Starting PC Workman HCK...", "LOAD")
    print()

    # --- Step 1: Load core imports ---
    log("Loading import_core...", "LOAD")
    try:
        from import_core import COMPONENTS, list_components, count_components
        log("import_core loaded", "OK")
    except Exception as e:
        log(f"FAILED to load import_core: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        return

    # --- Step 2: Load core modules (compact output) ---
    log("Loading core modules...", "LOAD")
    core_ok = True
    for module_name in ['core.monitor', 'core.logger', 'core.analyzer', 'core.scheduler']:
        try:
            __import__(module_name)
        except Exception as e:
            log(f"  {module_name} FAILED: {e}", "ERROR")
            core_ok = False
    if core_ok:
        log("Core modules loaded", "OK")

    # Load additional core silently
    try:
        import core.process_classifier
        import core.process_data_manager
    except Exception:
        pass

    try:
        import core.app_activity_tracker
        import core.hibernation_manager
        log("App Activity Tracker + Hibernation Manager loaded", "OK")
    except Exception as e:
        log(f"Hibernation modules skipped: {e}", "WARN")

    # --- Step 3: Load stats engine ---
    try:
        import hck_stats_engine.avg_calculator
        log("Stats engine (legacy) loaded", "OK")
    except Exception as e:
        log(f"Stats engine legacy FAILED: {e}", "ERROR")

    # --- Step 3b: Load Stats Engine v2 (SQLite long-term storage) ---
    stats_engine_v2_ready = False
    try:
        import hck_stats_engine
        from hck_stats_engine import db_manager, aggregator, process_aggregator, query_api, event_detector
        if db_manager.is_ready:
            stats_engine_v2_ready = True
            log("Stats Engine v2 (SQLite) loaded - DB ready", "OK")
        else:
            log("Stats Engine v2 loaded - DB NOT ready (will retry)", "WARN")
    except Exception as e:
        log(f"Stats Engine v2 FAILED: {e}", "ERROR")

    # --- Step 3c: ML Intent Classifier - background train / load ---
    try:
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier.load_or_train(background=True)
        log("ML intent classifier: background train/load started", "OK")
    except Exception as e:
        log(f"ML classifier skipped: {e}", "WARN")

    # --- Step 3d: DeepMonitor persistent metrics store ---
    try:
        # Single always-on sensor producer - feeds live_sensors app-wide so the
        # overlay, Monitoring, hck_GPT and the snapshots below work without any
        # UI page being open (root-cause fix for "--" / "Collecting data…").
        from core.live_collector import live_collector as _collector
        _collector.start()
        log("Live sensor collector started (2s tick)", "OK")

        from hck_gpt.data.metrics_store import metrics_store as _dm_store
        _dm_store.start()
        log("DeepMonitor metrics store started (snapshot every 5 min)", "OK")

        # Always-on AUTO optimizations (RAM Flush watcher etc.) - driven by saved
        # prefs, runs whether or not the Optimization page is ever opened.
        from core.auto_optimizer import auto_optimizer as _auto_opt
        _auto_opt.start()
        log("Auto-optimizer started (AUTO features run in background)", "OK")

        # Warm the hardware-identity cache while the splash is on screen:
        # the CIM scan takes seconds, so doing it now means the first
        # My PC -> Components open and hck_GPT hardware answers are instant.
        # (Data warm-up only - never pre-build widgets during the splash.)
        try:
            import threading as _warm_thr
            from import_core import COMPONENTS as _C

            def _warm_all():
                # Hardware identity (CIM scan, seconds).
                _det = _C.get("core.hardware_detector")
                if _det is not None:
                    try:
                        _det.ensure_data()
                    except Exception:
                        pass
                # Services/startup metrics (sc query is slow) so the first
                # Optimization / My PC open is instant, not a stall.
                try:
                    from ui.components.yourpc_page import warm_metrics_cache
                    warm_metrics_cache()
                except Exception:
                    pass

            _warm_thr.Thread(target=_warm_all, daemon=True,
                             name="splash-warmup").start()
            log("Splash warm-up started (hardware + service/startup metrics)", "OK")
        except Exception:
            pass
    except Exception as e:
        log(f"DeepMonitor metrics store skipped: {e}", "WARN")

    # --- Step 4: Load UI modules ---
    log("Loading UI...", "LOAD")
    main_window_module: Optional[Any] = None
    main_window_expanded_module: Optional[Any] = None
    HAS_UI = False

    try:
        import ui
        import ui.windows.main_window as main_window_module
        import ui.windows.main_window_expanded as main_window_expanded_module
        HAS_UI = True
        log("UI modules loaded", "OK")
    except Exception as e:
        log(f"UI modules FAILED: {e}", "ERROR")
        import traceback
        traceback.print_exc()

    print()
    log(f"Components: {count_components()} registered", "INFO")

    # --- Step 5: Get components ---
    scheduler = COMPONENTS.get('core.scheduler')
    logger = COMPONENTS.get('core.logger')
    monitor = COMPONENTS.get('core.monitor')
    data_manager = COMPONENTS.get('core.process_data_manager')

    # Start background data collection (keeps process_iter off GUI thread)
    if monitor and hasattr(monitor, 'start_background_collection'):
        monitor.start_background_collection(interval=1.0)
        log("Monitor background collection started", "OK")

    # Start App Activity Tracker (foreground window polling for hibernation)
    try:
        tracker = COMPONENTS.get("core.app_activity_tracker")
        if tracker:
            tracker.start()
            log("App Activity Tracker started", "OK")
    except Exception as e:
        log(f"App Activity Tracker start failed: {e}", "WARN")

    # --- Step 6: Start scheduler ---   
    if scheduler:
        try:
            scheduler.start_loop()
            log("Scheduler started", "OK")
        except Exception as e:
            log(f"Scheduler FAILED: {e}", "ERROR")
            scheduler = None

    # --- Step 7: Launch UI ---
    if HAS_UI and main_window_module is not None and main_window_expanded_module is not None:
        log("Launching UI...", "LOAD")

        import threading

        # Mode manager
        class ModeManager:
            def __init__(self):
                self.expanded_window: Optional[Any] = None
                self.minimal_window: Optional[Any] = None
                self.current_mode: Optional[str] = None
                self.quit_flag = False

            def switch_to_minimal(self):
                if self.expanded_window:
                    try:
                        self.expanded_window.root.withdraw()
                    except Exception:
                        pass
                if self.minimal_window is None:
                    # Pass the Expanded root as master so Minimal is a Toplevel of
                    # the single app root - never a second tk.Tk() (that crashed
                    # Expanded <-> Minimal switching).
                    self.minimal_window = main_window_module.MainWindow(
                        switch_to_expanded_callback=self.switch_to_expanded,
                        master=(self.expanded_window.root if self.expanded_window else None),
                    )
                else:
                    try:
                        self.minimal_window.root.deiconify()
                        self.minimal_window.root.lift()
                        if not self.minimal_window._running:
                            self.minimal_window._running = True
                            self.minimal_window._update_loop()
                            self.minimal_window._tray_thread = threading.Thread(
                                target=self.minimal_window._tray_update_loop, daemon=True
                            )
                            self.minimal_window._tray_thread.start()
                    except Exception as e:
                        log(f"switch_to_minimal re-show failed: {e}", "WARN")
                self.current_mode = "minimal"

            def switch_to_expanded(self):
                if self.minimal_window:
                    try:
                        self.minimal_window.root.withdraw()
                    except Exception as e:
                        log(f"switch_to_expanded: minimal withdraw failed: {e}", "WARN")
                if self.expanded_window:
                    try:
                        # restore_window() re-applies the tracked window state -
                        # plain deiconify() can come back 'zoomed' on Windows
                        # after a maximize round-trip.
                        if hasattr(self.expanded_window, "restore_window"):
                            self.expanded_window.restore_window()
                        else:
                            self.expanded_window.root.deiconify()
                            self.expanded_window.root.lift()
                            self.expanded_window.root.focus_force()
                    except Exception as e:
                        log(f"switch_to_expanded failed: {e}", "ERROR")

            def quit_application(self):
                self.quit_flag = True
                if self.expanded_window:
                    try:
                        self.expanded_window._running = False
                        if self.expanded_window.tray_manager:
                            self.expanded_window.tray_manager.stop()
                        self.expanded_window.root.quit()
                    except Exception:
                        pass
                if self.minimal_window:
                    try:
                        self.minimal_window._running = False
                        if hasattr(self.minimal_window, 'tray_manager') and self.minimal_window.tray_manager:
                            self.minimal_window.tray_manager.stop()
                        self.minimal_window.root.quit()
                    except Exception:
                        pass

        # Splash screen
        try:
            from ui.splash_screen import show_splash

            splash_done = threading.Event()
            def on_splash_complete():
                splash_done.set()

            splash_thread = threading.Thread(
                target=lambda: show_splash(duration=2.5, on_complete=on_splash_complete)
            )
            splash_thread.daemon = True
            splash_thread.start()
            splash_done.wait()
            log("Splash screen done", "OK")
        except Exception as e:
            log(f"Splash screen skipped: {e}", "WARN")

        # Create mode manager and start UI
        mode_mgr = ModeManager()

        try:
            mode_mgr.expanded_window = main_window_expanded_module.ExpandedMainWindow(
                data_manager=data_manager,
                monitor=monitor,
                switch_to_minimal_callback=mode_mgr.switch_to_minimal,
                quit_callback=mode_mgr.quit_application
            )
            mode_mgr.current_mode = "expanded"

            # Welcome toast (shows 1.8 s after UI is ready)
            try:
                from ui.components.system_toast import show_welcome_toast
                show_welcome_toast(mode_mgr.expanded_window.root, delay_ms=1800)
            except Exception:
                pass

            # Gaming launch watcher (subtle 2s notifications per game)
            try:
                from ui.components.gaming_toast import gaming_watcher
                from utils.i18n import get_lang as _gl
                gaming_watcher.start(mode_mgr.expanded_window.root, lang=_gl())
            except Exception:
                pass

            # Opt-in telemetry: a no-op unless the user turned Network Access +
            # Telemetry ON in Settings AND a Worker endpoint is configured. Runs
            # off-thread so it never touches startup.
            try:
                import threading as _th

                def _telemetry_once():
                    try:
                        import time as _time
                        _time.sleep(2)   # let network init settle; send right after
                        from core.telemetry import send as _tsend
                        _tsend(APP_VERSION)   # ensure_data() scans HW inside send()
                    except Exception:
                        pass

                _th.Thread(target=_telemetry_once, daemon=True,
                           name="telemetry").start()
            except Exception:
                pass

            log("UI ready - hiding console", "OK")
            print()
            print("-" * 40)
            print("  All systems GO - Starting PC Workman")
            print("-" * 40)

            # === HIDE CONSOLE ONCE THE UI IS ACTUALLY ON SCREEN ===
            # Schedule the hide INSIDE the event loop (after the window is mapped),
            # not before mainloop starts. This way a startup that fails before the
            # UI is up leaves the diagnostic console visible (with the error), the
            # user never sees a blank "nothing on screen" gap, and the console only
            # vanishes once PC Workman is genuinely running and painted.
            try:
                _root = mode_mgr.expanded_window.root
                _root.update_idletasks()                 # force a first paint
                _root.after(500, hide_console)           # hide from inside the loop
            except Exception:
                hide_console()                           # fallback: hide immediately

            # Run the UI mainloop
            mode_mgr.expanded_window.run()

        except Exception as e:
            log(f"UI FAILED: {e}", "ERROR")
            import traceback
            traceback.print_exc()
            print()
            print("=" * 50)
            print("  UI FAILED - Check error above")
            print("=" * 50)
            input("\nPress Enter to exit...")
    else:
        log("UI not available - headless mode", "WARN")
        print()
        import time
        log("Collecting data for 5 seconds...", "INFO")
        time.sleep(5)
        if logger:
            samples = logger.get_last_n_samples(5)
            for s in samples:
                print(f"  CPU: {s['cpu_percent']}%  RAM: {s['ram_percent']}%  GPU: {s['gpu_percent']}%")
        log("Headless finished", "OK")
        input("\nPress Enter to exit...")

    # Graceful stop
    if scheduler:
        try:
            scheduler.stop()
        except Exception:
            pass

    # Flush Stats Engine v2 on shutdown
    try:
        from hck_stats_engine.aggregator import aggregator as _agg
        _agg.flush_on_shutdown()
    except Exception:
        pass 

    try:
        from hck_stats_engine.events import event_detector as _evt
        _evt.log_custom_event('shutdown', 'info', 'PC Workman shutdown')
    except Exception:
        pass

    try:
        from hck_stats_engine.db_manager import db_manager as _db
        _db.close()
    except Exception:
        pass


def _acquire_single_instance_lock():
    """
    Prevent duplicate instances on Windows using a named mutex.
    Returns the mutex handle (must be kept alive) or None if already running.
    """
    if sys.platform != "win32":
        return True   # skip on non-Windows
    try:
        import ctypes
        _MUTEX_NAME = "Global\\PC_Workman_HCK_SingleInstance"
        handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        err    = ctypes.windll.kernel32.GetLastError()
        if err == 183:   # ERROR_ALREADY_EXISTS
            # Bring existing window to front. MAIN_WINDOW_TITLE is the SAME
            # constant the window sets (utils/app_version.py) - hardcoding it
            # here once drifted (v1.8.1 vs v1.8.2) and this lookup went dead.
            try:
                hwnd = ctypes.windll.user32.FindWindowW(None, MAIN_WINDOW_TITLE)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            return None   # signal: abort launch
        return handle     # keep alive for the duration of the process
    except Exception:
        return True       # if mutex check fails, allow launch


if __name__ == "__main__":
    _mutex = _acquire_single_instance_lock()
    if _mutex is None:
        print("[!] PC Workman is already running - bringing existing window to front.")
        sys.exit(0)
    run_demo()
