"""
startup.py
Entry point for PC Workman HCK v1.4.0
Initializes all core components, starts the scheduler, and launches the main UI if available.
Enhanced with System Tray, Process Classification, and Data Management.
"""

import sys
import io
from typing import Optional, Any

# Fix console encoding issues on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import time
import threading
from import_core import COMPONENTS, list_components, count_components

# --- Import all major modules (Core / AI / Stats) ---
import core.monitor, core.logger, core.analyzer, core.scheduler
import core.process_classifier, core.process_data_manager  # NEW: Enhanced process tracking
#import ai.hck_gpt, ai.ai_logic, ai.detector
import hck_stats_engine.avg_calculator, hck_stats_engine.trend_analysis

# --- Try importing the UI modules safely ---
main_window_module: Optional[Any] = None
main_window_expanded_module: Optional[Any] = None
HAS_UI = False

try:
    import ui.main_window as main_window_module  # type: ignore
    import ui.main_window_expanded as main_window_expanded_module  # type: ignore
    HAS_UI = True
except ImportError:
    pass

def run_demo():
    print("╔══════════════════════════════════════════════╗")
    print("║   🧠 PC Workman – HCK_Labs  v1.5.0           ║")
    print("║   Enhanced System Tray & Process Tracking    ║")
    print("╚══════════════════════════════════════════════╝\n")

    print("🔧 Registered Components:")
    print(list_components(), "\n")
    print(f"Total components active: {count_components()}\n")

    # Get all core components
    scheduler = COMPONENTS.get('core.scheduler')
    logger = COMPONENTS.get('core.logger')
    monitor = COMPONENTS.get('core.monitor')
    data_manager = COMPONENTS.get('core.process_data_manager')

    # --- Start scheduler loop ---
    if scheduler:
        try:
            scheduler.start_loop()
            print("[Scheduler] Data collection started (1-second interval).")
        except Exception as e:
            print(f"[Scheduler] Failed to start: {e}")
            import traceback
            traceback.print_exc()
            scheduler = None
    else:
        print("[Scheduler] Scheduler component not available.")

    # --- UI Handling - DUAL MODE SYSTEM ---
    if HAS_UI and main_window_module is not None and main_window_expanded_module is not None:
        print("[UI] Launching DUAL MODE system...")

        # Mode manager to handle switching
        class ModeManager:
            def __init__(self):
                self.expanded_window: Optional[Any] = None  # Will be ExpandedMainWindow or None
                self.minimal_window: Optional[Any] = None  # Will be MainWindow or None
                self.current_mode: Optional[str] = None  # str or None
                self.quit_flag = False

            def switch_to_minimal(self):
                """Switch from Expanded to Minimal Mode"""
                print("[ModeManager] Switching to Minimal Mode...")

                # Hide Expanded if visible
                if self.expanded_window:
                    try:
                        self.expanded_window.root.withdraw()
                    except:
                        pass

                # Create or show Minimal window
                if self.minimal_window is None:
                    self.minimal_window = main_window_module.MainWindow(
                        switch_to_expanded_callback=self.switch_to_expanded
                    )
                    self.current_mode = "minimal"
                    # Note: MainWindow already has its own mainloop
                else:
                    try:
                        self.minimal_window.root.deiconify()
                        self.minimal_window.root.lift()
                        # Restart update loop if needed
                        if not self.minimal_window._running:
                            self.minimal_window._running = True
                            self.minimal_window._update_loop()  # Restart after() loop
                            # Restart tray thread
                            self.minimal_window._tray_thread = threading.Thread(target=self.minimal_window._tray_update_loop, daemon=True)
                            self.minimal_window._tray_thread.start()
                    except Exception as e:
                        print(f"[ModeManager] Error restoring minimal: {e}")

            def switch_to_expanded(self):
                """Switch from Minimal to Expanded Mode"""
                print("[ModeManager] Switching to Expanded Mode...")

                # Hide Minimal if visible
                if self.minimal_window:
                    try:
                        self.minimal_window.root.withdraw()
                    except:
                        pass

                # Show Expanded window
                if self.expanded_window:
                    try:
                        self.expanded_window.root.deiconify()
                        self.expanded_window.root.lift()
                        self.expanded_window.root.focus_force()
                    except:
                        pass

            def quit_application(self):
                """Quit both windows"""
                print("[ModeManager] Quitting application...")
                self.quit_flag = True

                if self.expanded_window:
                    try:
                        self.expanded_window._running = False
                        if self.expanded_window.tray_manager:
                            self.expanded_window.tray_manager.stop()
                        self.expanded_window.root.quit()
                    except:
                        pass

                if self.minimal_window:
                    try:
                        self.minimal_window._running = False
                        if hasattr(self.minimal_window, 'tray_manager') and self.minimal_window.tray_manager:
                            self.minimal_window.tray_manager.stop()
                        self.minimal_window.root.quit()
                    except:
                        pass

        # Create mode manager
        mode_mgr = ModeManager()

        try:
            # Start in Expanded Mode (980x500, centered, full-featured)
            mode_mgr.expanded_window = main_window_expanded_module.ExpandedMainWindow(
                data_manager=data_manager,
                monitor=monitor,
                switch_to_minimal_callback=mode_mgr.switch_to_minimal,
                quit_callback=mode_mgr.quit_application
            )
            mode_mgr.current_mode = "expanded"

            print("[UI] Expanded Mode initialized, starting mainloop...")
            mode_mgr.expanded_window.run()

        except Exception as e:
            print(f"[UI] Failed to start properly: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[UI] No UI module detected — running in headless mode.")
        print("Collecting system data for 5 seconds...\n")
        time.sleep(5)
        if logger:
            samples = logger.get_last_n_samples(5)
            for s in samples:
                print(f"CPU: {s['cpu_percent']}%  RAM: {s['ram_percent']}%  GPU: {s['gpu_percent']}%")
        print("\n✅ Headless data collection finished.\n")

    # --- Graceful stop ---
    if scheduler:
        try:
            scheduler.stop()
            print("[Scheduler] Stopped gracefully.")
        except Exception:
            pass


if __name__ == "__main__":
    run_demo()
