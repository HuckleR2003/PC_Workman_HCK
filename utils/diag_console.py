# utils/diag_console.py
"""
Diagnostic output without a console window (2026-11-14).

Until November 2026 the build was a console app that tried to hide its own console
once the UI was up. On Windows 11 the default terminal is Windows Terminal,
where a program cannot hide its own window: the call reports success and
nothing happens. errors.log holds 43 "console_hide_failed" events from one
machine. And when startup did fail, the console had nothing useful to say,
because errors went to errors.log, not to the screen.

The rule now: the user never sees a console unless they ask for one.

  silent    windowed build, started normally. No console exists. Everything
            the app prints goes to data/logs/startup.log.
  console   started with --console. A console is opened on request and shows
            the same output live. For us and for testers.
  terminal  started from a terminal (dev run, `py startup.py`). Output goes to
            that terminal as before.
  startup   Settings > "Show diagnostic console at startup" is ON (2026-11-15).
            A PC Workman window (ui/diag_window.py, same look as the error
            window) shows the startup log live and closes by itself 3 s after
            the main window is ready (release_startup_console). No cmd window:
            that is what --console is for.

In all three modes the output is also written to startup.log, so the error
window (ui/startup_error.py) and a bug report always have the same evidence.

Why this module must run first: in a windowed build sys.stdout and sys.stderr
are None. print() tolerates that, but any direct sys.stderr.write() raises
AttributeError and input() raises RuntimeError. setup() replaces both streams
with a writer that always works, so no later code has to care.
"""
import os
import sys
import threading
import time

CONSOLE_FLAG = "--console"
_MAX_LOG_BYTES = 512_000        # a long session must not grow the log forever

MODE = "terminal"
STARTUP_CONSOLE_KEY = "show_startup_console"     # settings/app_settings.json
STARTUP_CONSOLE_DELAY_MS = 3000
_problems: list = []
_problems_lock = threading.Lock()
_installed = False
_tees: list = []
_listeners: list = []           # extra readers of the output (diag window)


def startup_console_wanted() -> bool:
    """The Settings switch, read straight from the file: this runs before
    anything else in the app is imported."""
    try:
        import json
        from utils.paths import APP_DIR
        with open(os.path.join(APP_DIR, "settings", "app_settings.json"),
                  encoding="utf-8") as f:
            return bool(json.load(f).get(STARTUP_CONSOLE_KEY, False))
    except Exception:
        return False


def open_startup_window() -> bool:
    """MODE 'startup': open the diagnostic window with what is logged so far
    and feed it every later line. Returns False when it could not open; the
    log file keeps everything either way."""
    if MODE != "startup":
        return False
    try:
        from ui import diag_window
        ok = diag_window.start(read_log_tail(max_chars=200_000))
        if ok:
            _listeners.append(diag_window.feed)
        return ok
    except Exception:
        return False


def release_startup_console() -> bool:
    """The app is ready: start the 3 s countdown of the diagnostic window
    (MODE 'startup' only). Returns True when a window was told to close."""
    global MODE
    if MODE != "startup":
        return False
    MODE = "silent"
    try:
        from ui import diag_window
        if diag_window.is_open():
            diag_window.close_after(STARTUP_CONSOLE_DELAY_MS)
            return True
    except Exception:
        pass
    return False


def close_startup_window_now() -> None:
    """Startup failed: the error window takes over, this one goes."""
    try:
        from ui import diag_window
        diag_window.close_now()
    except Exception:
        pass


def startup_log_path() -> str:
    try:
        from utils.paths import log_dir
        base = log_dir()
    except Exception:
        base = os.path.join(os.getcwd(), "data", "logs")
    return os.path.join(base, "startup.log")


class _Tee:
    """Writes to the real stream (when there is one) and to the log file.
    Never raises: diagnostics must not be able to take the app down."""

    def __init__(self, primary, logfile):
        self._primary = primary
        self._log = logfile
        self._written = 0
        self._lock = threading.Lock()
        self.encoding = "utf-8"
        self.errors = "replace"

    def write(self, text):
        if not isinstance(text, str):
            text = str(text)
        if self._primary is not None:
            try:
                self._primary.write(text)
            except Exception:
                pass
        for listener in list(_listeners):
            try:
                listener(text)
            except Exception:
                pass
        log = self._log
        if log is not None:
            with self._lock:
                try:
                    if self._written < _MAX_LOG_BYTES:
                        log.write(text)
                        self._written += len(text)
                        if self._written >= _MAX_LOG_BYTES:
                            log.write("\n[log size limit reached, "
                                      "further output not recorded]\n")
                        log.flush()
                except Exception:
                    pass
        return len(text)

    def detach_primary(self):
        """Keep writing to the log only (the console is about to go)."""
        primary, self._primary = self._primary, None
        try:
            if primary is not None:
                primary.flush()
        except Exception:
            pass

    def flush(self):
        for stream in (self._primary, self._log):
            if stream is not None:
                try:
                    stream.flush()
                except Exception:
                    pass

    def isatty(self):
        try:
            return bool(self._primary is not None and self._primary.isatty())
        except Exception:
            return False

    def writable(self):
        return True

    def __getattr__(self, name):
        # fileno(), buffer, reconfigure()... exist only with a real stream.
        primary = self.__dict__.get("_primary")
        if primary is None:
            raise AttributeError(name)
        return getattr(primary, name)


def _open_log():
    """startup.log is rewritten on every run. The previous run is kept as
    startup.prev.log, because people restart the app before they report."""
    try:
        path = startup_log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            try:
                os.replace(path, path[:-4] + ".prev.log")
            except Exception:
                pass
        return open(path, "w", encoding="utf-8", errors="replace")
    except Exception:
        return None


def _has_console() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:
        return False


def _open_console() -> bool:
    """Give a windowed process a console of its own (--console)."""
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        if not k32.GetConsoleWindow() and not k32.AllocConsole():
            return False
        try:
            k32.SetConsoleTitleW("PC Workman - diagnostic console")
            k32.SetConsoleOutputCP(65001)
        except Exception:
            pass
        sys.stdout = open("CONOUT$", "w", encoding="utf-8",
                          errors="replace", buffering=1)
        sys.stderr = sys.stdout
        try:
            sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
        except Exception:
            pass
        return True
    except Exception:
        return False


def setup(argv=None) -> str:
    """Install the output streams. Call once, before the first print()."""
    global MODE, _installed
    if _installed:
        return MODE
    _installed = True
    argv = list(sys.argv[1:] if argv is None else argv)
    wants_console = CONSOLE_FLAG in argv

    if sys.platform == "win32" and wants_console and sys.stdout is None:
        MODE = "console" if _open_console() else "silent"
    elif (sys.platform == "win32" and sys.stdout is None
          and startup_console_wanted()):
        # Settings switch: the diagnostic WINDOW for the startup only (see
        # module doc). Opened by startup.py right after setup().
        MODE = "startup"
    elif sys.stdout is None:
        MODE = "silent"
    else:
        MODE = "console" if wants_console else "terminal"

    # A real stream: make it UTF-8 so Polish text and box characters never
    # raise UnicodeEncodeError on a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    logfile = _open_log()
    out = _Tee(sys.stdout, logfile)
    err = out if sys.stderr is sys.stdout else _Tee(sys.stderr, logfile)
    sys.stdout, sys.stderr = out, err
    _tees[:] = [out] if err is out else [out, err]

    try:
        import platform
        print(f"[startup.log] {time.strftime('%Y-%m-%d %H:%M:%S')}  "
              f"mode={MODE}  frozen={bool(getattr(sys, 'frozen', False))}  "
              f"Windows {platform.version()}  Python {platform.python_version()}")
    except Exception:
        pass
    return MODE


def note_problem(text: str) -> None:
    """Remember something that went wrong during startup. If the UI still
    comes up, these are shown once in a small notice instead of vanishing."""
    with _problems_lock:
        _problems.append(str(text))


def problems() -> list:
    with _problems_lock:
        return list(_problems)


def read_log_tail(max_chars: int = 6000) -> str:
    """Last part of startup.log, for the error window and 'Copy details'."""
    try:
        sys.stdout.flush()
    except Exception:
        pass
    try:
        with open(startup_log_path(), "r", encoding="utf-8",
                  errors="replace") as f:
            data = f.read()
        return data[-max_chars:]
    except Exception:
        return ""
