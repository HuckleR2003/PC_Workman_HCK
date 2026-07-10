# core/app_activity_tracker.py
"""
AppActivityTracker — tracks which user-visible applications have keyboard/mouse
focus (foreground window) and surfaces idle candidates for hibernation.

Detection logic (multi-signal, avoids false positives):
  1. Process has been in the foreground at least once this session
     → confirms it's a user app, not a background service
  2. Has NOT been in the foreground for >= idle_threshold_min minutes
  3. Average CPU over last 3 samples < CPU_IDLE_PCT
     → confirms it's not doing heavy background work (compiling, downloading…)
  4. Not in the protected process list (system / security / drivers)

Background thread samples every SAMPLE_INTERVAL seconds.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import threading
import time
from typing import Dict, List, Optional

import psutil

from import_core import register_component, STATUS_IDLE, STATUS_OK

# ── Constants ──────────────────────────────────────────────────────────────────

SAMPLE_INTERVAL   = 15     # seconds between foreground polls
CPU_IDLE_PCT      = 3.0    # max avg CPU% to consider "idle" (not actively working)
CPU_SAMPLES_NEED  = 3      # number of samples required before declaring idle
MIN_RUNTIME_MIN   = 5      # ignore processes running < 5 min (just launched)

# ── Protected processes — never surfaced as hibernation candidates ─────────────

_PROTECTED_NAMES: frozenset[str] = frozenset({
    # Windows kernel / core
    "System", "Registry", "Idle", "smss.exe", "csrss.exe",
    "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "svchost.exe", "dwm.exe", "fontdrvhost.exe", "conhost.exe",
    "taskhostw.exe", "sihost.exe", "ctfmon.exe",
    "explorer.exe", "spoolsv.exe",
    "SearchIndexer.exe", "SearchHost.exe",
    "dllhost.exe", "RuntimeBroker.exe", "ShellExperienceHost.exe",
    "StartMenuExperienceHost.exe", "TextInputHost.exe",
    # Security / antivirus
    "MsMpEng.exe", "MpCmdRun.exe", "SecurityHealthSystray.exe",
    "SecurityHealthHost.exe", "avp.exe", "avgnt.exe", "mbam.exe",
    "ccSvcHst.exe", "NortonSecurity.exe", "eset_service.exe",
    # Drivers / GPU / Audio
    "nvcontainer.exe", "nvdisplay.container.exe", "NVDisplay.Container.exe",
    "RtkAudioService64.exe", "audiodg.exe",
    # PC Workman itself
    "startup.py", "python.exe", "pythonw.exe", "PC_Workman_HCK.exe",
})

_PROTECTED_KEYWORDS: tuple[str, ...] = (
    "antivirus", "antimalware", "firewall", "defender",
    "windows\\system32", "windows\\syswow64",
)


# ── AppActivityTracker ────────────────────────────────────────────────────────

class AppActivityTracker:
    """
    Continuously polls the foreground window and builds a picture of which
    user-launched applications are actively used vs idle.
    """

    def __init__(self) -> None:
        # pid -> timestamp of last time this PID was the foreground window
        self._last_fg:     Dict[int, float] = {}
        # pid -> timestamp when we first observed this PID in the foreground
        self._first_seen:  Dict[int, float] = {}
        # pid -> list of recent cpu% samples (capped at CPU_SAMPLES_NEED + 2)
        self._cpu_samples: Dict[int, list]  = {}
        # pid -> process name (cached to survive process death lookup)
        self._pid_names:   Dict[int, str]   = {}

        self._lock    = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        register_component("core.app_activity_tracker", self, STATUS_IDLE)

    # ── Control ───────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="app-activity-tracker"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    # ── Public API ────────────────────────────────────────────────────────────

    def get_idle_apps(self, idle_threshold_min: int = 15) -> List[dict]:
        """
        Return list of apps that are:
          - known user apps (seen in foreground at least once)
          - idle for >= idle_threshold_min minutes
          - CPU < CPU_IDLE_PCT (not doing active background work)
          - not in protected list

        Each entry: {pid, name, exe, idle_min, ram_mb, cpu_avg, first_seen_min}
        """
        now         = time.time()
        threshold_s = idle_threshold_min * 60
        result      = []

        try:
            live_procs = {p.pid: p for p in psutil.process_iter(
                ["pid", "name", "exe", "memory_info", "status", "create_time"]
            )}
        except Exception:
            return []

        with self._lock:
            known_fg_pids = set(self._last_fg.keys())

        for pid, proc in live_procs.items():
            try:
                # Only surface apps that were ever in the foreground this session
                if pid not in known_fg_pids:
                    continue

                info   = proc.info
                name   = info.get("name") or ""
                exe    = info.get("exe")  or ""
                status = info.get("status") or ""

                if status == psutil.STATUS_ZOMBIE:
                    continue

                if self._is_protected(name, exe):
                    continue

                with self._lock:
                    last_fg   = self._last_fg.get(pid, 0)
                    first_seen = self._first_seen.get(pid, now)
                    samples   = list(self._cpu_samples.get(pid, []))

                idle_s = now - last_fg
                if idle_s < threshold_s:
                    continue

                # Min runtime guard — skip apps launched less than MIN_RUNTIME_MIN ago
                runtime_s = now - (info.get("create_time") or now)
                if runtime_s < MIN_RUNTIME_MIN * 60:
                    continue

                # CPU guard — need enough samples and must be below threshold
                if len(samples) < CPU_SAMPLES_NEED:
                    continue
                cpu_avg = sum(samples[-CPU_SAMPLES_NEED:]) / CPU_SAMPLES_NEED
                if cpu_avg >= CPU_IDLE_PCT:
                    continue

                # RAM
                mem_info = info.get("memory_info")
                ram_mb   = int((mem_info.rss if mem_info else 0) / 1_048_576)

                result.append({
                    "pid":          pid,
                    "name":         name,
                    "exe":          exe,
                    "idle_min":     int(idle_s / 60),
                    "ram_mb":       ram_mb,
                    "cpu_avg":      round(cpu_avg, 1),
                    "first_seen_min": int((now - first_seen) / 60),
                })

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

        # Sort by idle time descending (longest idle first)
        result.sort(key=lambda x: x["idle_min"], reverse=True)
        return result

    def mark_active(self, pid: int) -> None:
        """Manually mark a PID as just-active (e.g. after user wakes an app)."""
        now = time.time()
        with self._lock:
            self._last_fg[pid] = now

    def forget_pid(self, pid: int) -> None:
        """Remove all tracking for a PID (e.g. process was killed)."""
        with self._lock:
            self._last_fg.pop(pid, None)
            self._first_seen.pop(pid, None)
            self._cpu_samples.pop(pid, None)
            self._pid_names.pop(pid, None)

    # ── Background loop ───────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._sample()
                self._prune_dead()
            except Exception:
                pass
            time.sleep(SAMPLE_INTERVAL)

    def _sample(self) -> None:
        now    = time.time()
        fg_pid = self._foreground_pid()

        try:
            procs = {p.pid: p for p in psutil.process_iter(
                ["pid", "name", "exe", "status"]
            )}
        except Exception:
            return

        with self._lock:
            # Record foreground PID
            if fg_pid and fg_pid in procs:
                proc_info = procs[fg_pid].info
                name      = proc_info.get("name") or ""
                if not self._is_protected(name, proc_info.get("exe") or ""):
                    self._last_fg[fg_pid] = now
                    if fg_pid not in self._first_seen:
                        self._first_seen[fg_pid] = now
                    self._pid_names[fg_pid] = name

            # CPU samples for all known-fg processes still alive
            for pid in list(self._last_fg.keys()):
                if pid not in procs:
                    continue
                try:
                    cpu = procs[pid].cpu_percent(interval=None)
                    samples = self._cpu_samples.setdefault(pid, [])
                    samples.append(cpu)
                    if len(samples) > CPU_SAMPLES_NEED + 2:
                        samples.pop(0)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

    def _prune_dead(self) -> None:
        """Remove tracking for processes that no longer exist."""
        try:
            live = {p.pid for p in psutil.process_iter(["pid"])}
        except Exception:
            return
        with self._lock:
            dead = [pid for pid in self._last_fg if pid not in live]
            for pid in dead:
                self._last_fg.pop(pid, None)
                self._first_seen.pop(pid, None)
                self._cpu_samples.pop(pid, None)
                self._pid_names.pop(pid, None)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _foreground_pid() -> int:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid  = ctypes.c_ulong(0)
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value
        except Exception:
            return 0

    @staticmethod
    def _is_protected(name: str, exe: str) -> bool:
        # Central guard first (anti-cheat + OS-critical + PC Workman itself) so
        # the "Unused Apps" list never even offers to sleep a critical process.
        try:
            from core.protected_processes import is_protected as _central
            if _central(name, exe):
                return True
        except Exception:
            pass
        if name in _PROTECTED_NAMES:
            return True
        nl = name.lower()
        el = exe.lower()
        return any(kw in nl or kw in el for kw in _PROTECTED_KEYWORDS)


# ── Singleton ─────────────────────────────────────────────────────────────────

app_activity_tracker = AppActivityTracker()
