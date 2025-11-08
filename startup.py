"""
startup.py
Entry point for PC Workman HCK v1.0.6
Initializes all core components, starts the scheduler, and launches the main UI if available.
"""

import time
from import_core import COMPONENTS, list_components, count_components

# --- Import all major modules (Core / AI / Stats) ---
import core.monitor, core.logger, core.analyzer, core.scheduler
import ai.hck_gpt, ai.ai_logic, ai.detector
import hck_stats_engine.avg_calculator, hck_stats_engine.trend_analysis

# --- Try importing the UI module safely ---
try:
    import ui.main_window as main_window
    HAS_UI = True
except ImportError:
    HAS_UI = False


def run_demo():
    print("╔══════════════════════════════════════════════╗")
    print("║   🧠 PC Workman – HCK_Labs  v1.0.6            ║")
    print("╚══════════════════════════════════════════════╝\n")

    print("🔧 Registered Components:")
    print(list_components(), "\n")
    print(f"Total components active: {count_components()}\n")

    scheduler = COMPONENTS.get('core.scheduler')
    logger = COMPONENTS.get('core.logger')

    # --- Start scheduler loop ---
    try:
        scheduler.start_loop()
        print("[Scheduler] Data collection started (1-second interval).")
    except Exception as e:
        print(f"[Scheduler] Failed to start: {e}")
        scheduler = None

    # --- UI Handling ---
    if HAS_UI:
        print("[UI] Launching main interface...")
        try:
            ui_window = main_window.MainWindow()
            ui_window.run()
        except Exception as e:
            print(f"[UI] Failed to start properly: {e}")
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
