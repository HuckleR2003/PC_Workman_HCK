"""
core/auto_optimizer.py - the always-on engine behind AUTO optimizations.

Root-cause fix (2026-07-05): the Auto RAM Flush watcher lived inside the
Optimization *page* (`ui/pages/optimization_services.py`) and was only started
when the user clicked the AUTO pill. So a user who enabled AUTO, closed the app
and reopened it had the pill lit but the watcher DEAD - it only ran while the
page was open and toggled. Same class of bug as the page-bound sensor pipeline.

Now ONE daemon owns it, started from startup.py, driven by saved prefs, running
whether or not any page is open. The page becomes a configurator + status view.

Currently drives:
  · Auto RAM Flush - waits for sustained pressure, then trims working sets
    (SetSystemFileCacheSize + EmptyWorkingSet), skipping user-excluded AND
    anti-cheat processes (core.protected_processes).
  · TURBO coupling - when TURBO is on and the user ticked "run on TURBO",
    the flush watcher activates for the duration of TURBO.
  · Turbo Power Plan (TPP) - creates/activates the "Turbo PC" power plan and
    reconciles it with the master TURBO flag. Migrated from the Optimization
    page (2026-07-10): the old page-bound monitor spawned a NEW infinite
    thread on every page visit, each polling a destroyed widget's
    winfo_exists() from a background thread every 5 s - N leaked threads
    hammering Tcl deadlocked the interpreter (UI frozen, process alive).

Design mirrors core.live_collector: single producer, prefs-driven, UI is a
consumer that registers a status listener (guarded, never the source of truth).
"""
from __future__ import annotations

import atexit
import json
import os
import subprocess
import threading
import time

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    _APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from import_core import register_component, update_status, STATUS_OK, STATUS_STARTING
    _HAS_REGISTRY = True
except Exception:
    _HAS_REGISTRY = False

try:
    from core.protected_processes import is_protected as _is_protected
except Exception:
    def _is_protected(name, exe=""):   # noqa: E704
        return False

_PREFS_PATH = os.path.join(_APP_DIR, "settings", "user_prefs.json")

TICK_S       = 10          # RAM sampled every 10 s
TRIGGER_S    = 30          # sustained-pressure window before a flush fires
_DEFAULT_THR = 75          # % RAM


# ── prefs (shared file with the Optimization page) ───────────────────────────
def _load_prefs_full() -> dict:
    try:
        with open(_PREFS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_opt() -> dict:
    return _load_prefs_full().get("optimization", {})


# ── Turbo Power Plan primitives (powercfg) ────────────────────────────────────
_TURBO_PC_NAME = "Turbo PC"
_NO_WINDOW     = getattr(subprocess, "CREATE_NO_WINDOW", 0)


from utils.admin import is_admin as _is_admin  # single source of truth

def _pp_active_guid() -> str | None:
    try:
        r = subprocess.run(["powercfg", "/getactivescheme"],
                           capture_output=True, timeout=5,
                           creationflags=_NO_WINDOW)
        for p in r.stdout.decode("utf-8", errors="replace").split():
            if len(p) == 36 and p.count("-") == 4:
                return p
    except Exception:
        pass
    return None


def _pp_set(guid: str) -> bool:
    try:
        r = subprocess.run(["powercfg", "/setactive", guid],
                           capture_output=True, timeout=5,
                           creationflags=_NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


def _pp_list() -> dict:
    """Return {name: guid} of all power plans (language-agnostic; binary mode
    + safe UTF-8 decode avoids Polish OEM codepage issues)."""
    plans = {}
    try:
        r = subprocess.run(["powercfg", "/list"],
                           capture_output=True, timeout=5,
                           creationflags=_NO_WINDOW)
        for line in r.stdout.decode("utf-8", errors="replace").splitlines():
            parts = line.strip().split()
            for i, p in enumerate(parts):
                if len(p) == 36 and p.count("-") == 4:
                    name_part = " ".join(parts[i + 1:]).strip("()*").strip()
                    if name_part:
                        plans[name_part] = p
                    break   # one GUID per line
    except Exception:
        pass
    return plans


def _pp_create_turbo() -> str | None:
    """Duplicate High Performance (or Ultimate Performance) and rename it to
    'Turbo PC'. Returns the new GUID or None. Requires admin."""
    CANDIDATE_GUIDS = [
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",   # High Performance
        "e9a42b02-d5df-448d-aa00-03f14749eb61",   # Ultimate Performance
    ]
    try:
        plans = _pp_list()
        if _TURBO_PC_NAME in plans:
            return plans[_TURBO_PC_NAME]
        new_guid = None
        for src_guid in CANDIDATE_GUIDS:
            r = subprocess.run(["powercfg", "/duplicatescheme", src_guid],
                               capture_output=True, timeout=8,
                               creationflags=_NO_WINDOW)
            for tok in r.stdout.decode("utf-8", errors="replace").split():
                if (len(tok) == 36 and tok.count("-") == 4
                        and tok.lower() != src_guid.lower()):
                    new_guid = tok
                    break
            if new_guid:
                break
        if not new_guid:
            return None
        subprocess.run(["powercfg", "/changename", new_guid, _TURBO_PC_NAME,
                        "PC Workman - custom high-performance profile"],
                       capture_output=True, timeout=5,
                       creationflags=_NO_WINDOW)
        return new_guid
    except Exception:
        return None


# ── the flush primitive (moved out of the UI so the daemon owns it) ──────────
def ram_flush(exclude: set | None = None) -> tuple:
    """Trim working sets system-wide. Returns (ok, msg, before_mb, after_mb).
    Skips PID<=4, user-excluded exe names, and any anti-cheat process."""
    import psutil
    import ctypes
    exclude = exclude or set()
    before = int(psutil.virtual_memory().available / 1048576)
    try:
        cmd = ctypes.c_int(4)
        ctypes.windll.ntdll.NtSetSystemInformation(80, ctypes.byref(cmd),
                                                   ctypes.sizeof(cmd))
    except Exception:
        pass
    try:
        ctypes.windll.kernel32.SetSystemFileCacheSize(
            ctypes.c_size_t(0xFFFFFFFF), ctypes.c_size_t(0xFFFFFFFF), 0)
    except Exception:
        pass
    count = skipped = 0
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            pid  = proc.pid
            name = (proc.info.get("name") or "").lower()
            if pid <= 4:
                continue
            if name and (name in exclude or _is_protected(name)):
                skipped += 1
                continue
            try:
                h = ctypes.windll.kernel32.OpenProcess(0x0100 | 0x0400, False, pid)
                if h:
                    ctypes.windll.psapi.EmptyWorkingSet(h)
                    ctypes.windll.kernel32.CloseHandle(h)
                    count += 1
            except Exception:
                pass
    except Exception:
        pass
    time.sleep(0.8)
    after = int(psutil.virtual_memory().available / 1048576)
    freed = after - before
    skip_note = f"  ·  {skipped} protected" if skipped else ""
    if freed > 0:
        return True, f"Freed {freed} MB  ({count} procs{skip_note})", before, after
    if count > 0:
        return True, f"Flushed {count} procs (limited perms{skip_note})", before, after
    return False, "No effect - admin rights needed", before, after


class AutoOptimizer:
    """Always-on daemon: runs AUTO optimizations from saved prefs, no UI needed."""

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        # live state (seeded from prefs at start)
        self._ram_auto     = False
        self._ram_on_turbo = False
        self._threshold    = _DEFAULT_THR
        self._exclude: set = set()
        self._turbo_on     = False
        self._high_secs     = 0
        self._last_status   = ""
        self._listeners: list = []          # (callback, kind) pairs
        # Turbo Power Plan state
        self._tpp_auto          = False     # background reconcile enabled
        self._tpp_on_turbo      = False     # couple plan to master TURBO
        self._tpp_active        = False     # Turbo PC plan currently set
        self._tpp_original_guid = None
        self._tpp_turbo_guid    = None
        if _HAS_REGISTRY:
            try:
                register_component("core.auto_optimizer", self, STATUS_STARTING)
            except Exception:
                pass

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.reload_prefs()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="auto_optimizer")
        self._thread.start()
        if _HAS_REGISTRY:
            try:
                update_status("core.auto_optimizer", STATUS_OK,
                              "ram_auto" if self._ram_auto else "idle")
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()

    def reload_prefs(self) -> None:
        o = _load_opt()
        with self._lock:
            self._ram_auto     = bool(o.get("ram_auto", False))
            self._ram_on_turbo = bool(o.get("ram_on_turbo", False))
            self._threshold    = int(o.get("ram_threshold", _DEFAULT_THR))
            self._exclude      = {str(n).lower() for n in o.get("ram_flush_exclude", [])}
            self._tpp_auto     = bool(o.get("tpp_auto", False))
            self._tpp_on_turbo = bool(o.get("tpp_on_turbo", False))

    # ── live setters (called by the Optimization page; keep UI and daemon in sync)
    def set_ram_auto(self, on: bool) -> None:
        with self._lock:
            self._ram_auto = bool(on)
            if not on:
                self._high_secs = 0
        self._emit("AUTO on" if on else "AUTO off")

    def set_threshold(self, pct: int) -> None:
        with self._lock:
            self._threshold = max(50, min(95, int(pct)))

    def set_exclude(self, names) -> None:
        with self._lock:
            self._exclude = {str(n).lower() for n in names}

    def set_turbo(self, on: bool) -> None:
        """Called when the master TURBO switch flips."""
        with self._lock:
            self._turbo_on = bool(on)
            if not on:
                self._high_secs = 0

    def set_ram_on_turbo(self, on: bool) -> None:
        """Arm/disarm RAM flushing on the master TURBO switch (the page pill
        delegates here, mirroring set_tpp_on_turbo)."""
        with self._lock:
            self._ram_on_turbo = bool(on)

    def _ram_watch_active(self) -> bool:
        return self._ram_auto or (self._ram_on_turbo and self._turbo_on)

    # ── Turbo Power Plan API (page delegates here; daemon reconciles) ─────────
    def set_tpp_auto(self, on: bool) -> None:
        with self._lock:
            self._tpp_auto = bool(on)

    def set_tpp_on_turbo(self, on: bool) -> None:
        with self._lock:
            self._tpp_on_turbo = bool(on)

    def tpp_is_active(self) -> bool:
        return self._tpp_active

    def tpp_activate(self) -> tuple:
        """Activate the Turbo PC plan (creates it on first use). (ok, msg)."""
        if not _is_admin():
            return False, "Needs admin - restart as Administrator"
        if not self._tpp_original_guid:
            self._tpp_original_guid = _pp_active_guid()
        if not self._tpp_turbo_guid:
            plans = _pp_list()
            if _TURBO_PC_NAME in plans:
                self._tpp_turbo_guid = plans[_TURBO_PC_NAME]
            else:
                guid = _pp_create_turbo()
                if not guid:
                    return False, "Plan creation failed"
                self._tpp_turbo_guid = guid
        if _pp_set(self._tpp_turbo_guid):
            self._tpp_active = True
            try:
                from import_core import COMPONENTS
                hibm = COMPONENTS.get("core.hibernation_manager")
                if hibm:
                    hibm.apply_turbo_behaviors()
            except Exception:
                pass
            msg = "Turbo PC  active ✓"
            self._emit(msg, kind="tpp")
            return True, msg
        return False, "Activation failed"

    def tpp_restore(self) -> tuple:
        """Restore the original power plan. (ok, msg)."""
        guid = self._tpp_original_guid or "381b4222-f694-41f0-9685-ff5bb260df2e"
        if _pp_set(guid):
            self._tpp_active = False
            try:
                from import_core import COMPONENTS
                hibm = COMPONENTS.get("core.hibernation_manager")
                if hibm:
                    hibm.restore_turbo_apps()
            except Exception:
                pass
            msg = "Balanced restored ✓"
            self._emit(msg, kind="tpp")
            return True, msg
        return False, "Restore failed"

    def _tpp_tick(self) -> None:
        """Reconcile the power plan with the master TURBO flag (daemon-side).
        Replaces the page-bound monitor loop that accumulated one thread per
        page visit and polled destroyed widgets from background threads."""
        if not (self._tpp_auto and self._tpp_on_turbo):
            return
        turbo_on = self._turbo_on or bool(
            _load_prefs_full().get("turbo_active", False))
        if turbo_on and not self._tpp_active:
            self.tpp_activate()
        elif not turbo_on and self._tpp_active:
            self.tpp_restore()

    # ── status plumbing for the UI (optional, guarded) ────────────────────────
    def register_status_listener(self, cb, kind: str = "ram") -> None:
        with self._lock:
            # equality, not identity: bound methods compare equal across
            # accesses while each access is a distinct object
            if not any(c == cb for c, _ in self._listeners):
                self._listeners.append((cb, kind))

    def unregister_status_listener(self, cb) -> None:
        with self._lock:
            self._listeners = [(c, k) for c, k in self._listeners if c != cb]

    def get_status(self) -> str:
        return self._last_status

    def _emit(self, text: str, kind: str = "ram") -> None:
        self._last_status = text
        for cb, k in list(self._listeners):
            if k != kind:
                continue
            try:
                cb(text)
            except Exception:
                pass

    # ── manual flush (the "FLUSH RAM" button routes here too) ─────────────────
    def flush_now(self) -> tuple:
        with self._lock:
            exclude = set(self._exclude)
        res = ram_flush(exclude)
        self._emit(res[1])
        return res

    # ── main loop ─────────────────────────────────────────────────────────────
    def _loop(self) -> None:
        import psutil
        while not self._stop.is_set():
            try:
                if self._ram_watch_active():
                    pct = psutil.virtual_memory().percent
                    with self._lock:
                        thr = self._threshold
                    if pct > thr:
                        self._high_secs = min(self._high_secs + TICK_S, TRIGGER_S)
                        self._emit(f"high  {self._high_secs}s/{TRIGGER_S}s")
                        if self._high_secs >= TRIGGER_S:
                            self._high_secs = 0
                            ok, msg, before, after = self.flush_now()
                    else:
                        if self._high_secs:
                            self._high_secs = 0
                            self._emit("")
                else:
                    self._high_secs = 0
            except Exception:
                pass
            try:
                self._tpp_tick()
            except Exception:
                pass
            self._stop.wait(TICK_S)


# ── Singleton ──────────────────────────────────────────────────────────────────
auto_optimizer = AutoOptimizer()


def _tpp_atexit():
    """Never leave the machine stuck on the Turbo PC plan after exit."""
    try:
        if auto_optimizer._tpp_active:
            auto_optimizer.tpp_restore()
    except Exception:
        pass


atexit.register(_tpp_atexit)
