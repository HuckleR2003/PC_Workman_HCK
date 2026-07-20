# utils/crash_log.py
"""
Global error capture (2026-07-18, "there is never anything in the console").

Three classes of errors used to vanish silently:
  1. Tkinter CALLBACK exceptions - Tk swallows them into stderr, and the
     diagnostic console auto-hides on successful launch, so nobody ever saw
     them. This was the big one.
  2. Uncaught exceptions on worker threads.
  3. Uncaught exceptions anywhere else.

install(root) hooks all three and appends full tracebacks to
APP_DIR/data/logs/errors.log (plus stderr, for dev runs from a terminal).
One rotation rule: the file is trimmed to its last ~200 KB on startup.
"""
import os
import sys
import threading
import time
import traceback

_MAX_BYTES = 200_000


def _path() -> str:
    try:
        from utils.paths import APP_DIR
        base = APP_DIR
    except Exception:
        base = os.getcwd()
    return os.path.join(base, "data", "logs", "errors.log")


def _write(kind: str, text: str) -> None:
    line = (f"\n{'-' * 64}\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{kind}\n{text}")
    try:
        p = _path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    try:
        print(line, file=sys.stderr)
    except Exception:
        pass


def _trim() -> None:
    try:
        p = _path()
        if os.path.getsize(p) > _MAX_BYTES:
            with open(p, "rb") as f:
                f.seek(-_MAX_BYTES, os.SEEK_END)
                tail = f.read()
            with open(p, "wb") as f:
                f.write(tail)
    except Exception:
        pass


def install(root) -> None:
    """Hook Tk callback errors + thread errors + global excepthook."""
    _trim()

    def _tk_hook(exc, val, tb):
        _write("TK CALLBACK EXCEPTION",
               "".join(traceback.format_exception(exc, val, tb)))
    try:
        root.report_callback_exception = _tk_hook
    except Exception:
        pass

    def _thread_hook(args):
        _write(f"THREAD EXCEPTION ({args.thread.name if args.thread else '?'})",
               "".join(traceback.format_exception(
                   args.exc_type, args.exc_value, args.exc_traceback)))
    try:
        threading.excepthook = _thread_hook
    except Exception:
        pass

    _prev = sys.excepthook

    def _sys_hook(exc, val, tb):
        _write("UNCAUGHT EXCEPTION",
               "".join(traceback.format_exception(exc, val, tb)))
        try:
            _prev(exc, val, tb)
        except Exception:
            pass
    sys.excepthook = _sys_hook
