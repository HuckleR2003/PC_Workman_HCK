# utils/freeze_watchdog.py
"""
Main-thread freeze watchdog (born 2026-07-18, after a hard "(brak
odpowiedzi)" freeze on the main dashboard that left no evidence).

A 2 s after() heartbeat stamps a timestamp from the Tk main thread. A tiny
daemon thread checks it: if the main thread has not beaten for STALL_S
seconds, the watchdog dumps the stack of EVERY thread to
APP_DIR/data/logs/freeze_dump.txt - so the NEXT freeze hands us the exact
line the UI thread is stuck on, instead of a guessing game.

One dump per stall (re-armed after recovery). Zero cost when healthy.
"""
import os
import sys
import threading
import time
import traceback

STALL_S = 15
_CHECK_S = 5


def _dump_path() -> str:
    try:
        from utils.paths import APP_DIR
        base = APP_DIR
    except Exception:
        base = os.getcwd()
    return os.path.join(base, "data", "logs", "freeze_dump.txt")


def start(root) -> None:
    """Attach the watchdog to the Tk root. Safe to call once at startup."""
    beat = {"t": time.time(), "dumped": False}

    def _pump():
        beat["t"] = time.time()
        beat["dumped"] = False          # healthy again -> re-arm
        try:
            root.after(2000, _pump)
        except Exception:
            pass                        # app is closing

    def _watch():
        while True:
            time.sleep(_CHECK_S)
            stalled = time.time() - beat["t"]
            if stalled <= STALL_S or beat["dumped"]:
                continue
            beat["dumped"] = True       # one dump per incident
            try:
                path = _dump_path()
                os.makedirs(os.path.dirname(path), exist_ok=True)
                names = {t.ident: t.name for t in threading.enumerate()}
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 72}\n")
                    f.write(f"MAIN THREAD STALLED for {stalled:.0f}s at "
                            f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    for tid, frame in sys._current_frames().items():
                        f.write(f"\n-- thread {names.get(tid, tid)}\n")
                        f.write("".join(traceback.format_stack(frame)))
            except Exception:
                pass

    try:
        root.after(2000, _pump)
        threading.Thread(target=_watch, daemon=True,
                         name="freeze-watchdog").start()
    except Exception:
        pass
