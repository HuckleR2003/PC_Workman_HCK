# core/hibernation_manager.py
"""
HibernationManager — sleep / wake user applications to reclaim resources.

Two behaviors, per-app configurable:
  "low"    — SetPriorityClass(IDLE_PRIORITY_CLASS)
             Process still runs, gets CPU scraps. Safe for everything.
  "freeze" — psutil.Process.suspend() (NtSuspendProcess internally)
             Process stops executing entirely. User opts in per-app.
  "none"   — no action (default, fully active)

Settings persisted in:
  data/cache/hibernation_prefs.json
    {
      "ignored":         ["discord.exe", ...],          # never suggest
      "turbo_behaviors": {"spotify.exe": "low", ...}   # Turbo Mode per-app
    }

Turbo integration:
  Call apply_turbo_behaviors() when Turbo activates.
  Call restore_turbo_apps()   when Turbo deactivates.
"""
from __future__ import annotations

import ctypes
import json
import os
import threading
import time
from typing import Dict, Optional

import psutil

from import_core import register_component, update_status, STATUS_IDLE, STATUS_OK, STATUS_WARN

# ── Constants ─────────────────────────────────────────────────────────────────

IDLE_PRIORITY_CLASS   = 0x00000040   # ctypes constant (kernel32)
NORMAL_PRIORITY_CLASS = 0x00000020
PROCESS_SET_INFORMATION = 0x0200
PROCESS_SUSPEND_RESUME  = 0x0800

# ── Paths ─────────────────────────────────────────────────────────────────────

try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = (
        os.path.dirname(_sys.executable)
        if getattr(_sys, "frozen", False)
        else os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    )

_PREFS_PATH = os.path.join(_APP_DIR, "data", "cache", "hibernation_prefs.json")


# ── HibernationManager ────────────────────────────────────────────────────────

class HibernationManager:
    """
    Manages sleep / wake for idle user applications.
    Persists ignore list and per-app Turbo behaviors.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

        # {pid: {"name", "exe", "behavior", "slept_at", "original_priority"}}
        self._sleeping: Dict[int, dict] = {}

        # Loaded from / saved to disk
        self._ignored:         set  = set()       # exe names (lowercase)
        self._turbo_behaviors: dict = {}           # exe_lower -> "low"|"freeze"|"none"

        self._load_prefs()
        register_component("core.hibernation_manager", self, STATUS_IDLE)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def ignored(self) -> set:
        with self._lock:
            return set(self._ignored)

    @property
    def turbo_behaviors(self) -> dict:
        with self._lock:
            return dict(self._turbo_behaviors)

    def sleep_app(self, pid: int, name: str, exe: str,
                  behavior: str = "low") -> bool:
        """
        Put a process to sleep.
        behavior: "low" (priority) | "freeze" (suspend)
        Returns True on success.
        """
        behavior = behavior.lower()
        if behavior not in ("low", "freeze"):
            behavior = "low"

        # HARD SAFETY: never sleep ourselves, an OS-critical process, or an
        # anti-cheat. Freezing dwm.exe/explorer.exe white-screens the desktop;
        # freezing our own process hangs the whole app. (This was the cause of
        # the "total freeze after 5-15 min" report.)
        try:
            from core.protected_processes import is_protected, is_self
            if is_self(pid) or is_protected(name, exe):
                return False
        except Exception:
            pass

        try:
            proc = psutil.Process(pid)
            original_nice = proc.nice()
        except Exception:
            return False

        try:
            if behavior == "freeze":
                proc.suspend()
            else:
                # Low priority via kernel32
                _set_priority(pid, IDLE_PRIORITY_CLASS)

            with self._lock:
                self._sleeping[pid] = {
                    "pid":              pid,
                    "name":             name,
                    "exe":              exe,
                    "behavior":         behavior,
                    "slept_at":         time.time(),
                    "original_nice":    original_nice,
                }
            update_status("core.hibernation_manager", STATUS_OK,
                          f"{len(self._sleeping)} sleeping")
            return True

        except Exception:
            return False

    def wake_app(self, pid: int) -> bool:
        """Restore a sleeping process to normal operation."""
        with self._lock:
            info = self._sleeping.pop(pid, None)
        if info is None:
            return False
        try:
            proc = psutil.Process(pid)
            if info["behavior"] == "freeze":
                proc.resume()
            else:
                _set_priority(pid, NORMAL_PRIORITY_CLASS)
            return True
        except psutil.NoSuchProcess:
            # Process already exited — consider it successfully "woken"
            return True
        except Exception:
            return False
        finally:
            remaining = len(self._sleeping)
            update_status("core.hibernation_manager",
                          STATUS_OK if remaining == 0 else STATUS_WARN,
                          f"{remaining} sleeping")

    def wake_all(self) -> int:
        with self._lock:
            pids = list(self._sleeping.keys())
        return sum(1 for pid in pids if self.wake_app(pid))

    @property
    def sleeping_count(self) -> int:
        with self._lock:
            return len(self._sleeping)

    def get_sleeping(self) -> list:
        now = time.time()
        with self._lock:
            return [
                {**info, "sleep_min": int((now - info["slept_at"]) / 60)}
                for info in self._sleeping.values()
            ]

    def is_sleeping(self, pid: int) -> bool:
        with self._lock:
            return pid in self._sleeping

    def cleanup_dead_pids(self) -> int:
        """
        Remove entries for processes that have already exited naturally.
        Call periodically (e.g. every 60s) to prevent stale PID accumulation.
        Returns the number of entries removed.
        """
        with self._lock:
            dead = [pid for pid in self._sleeping
                    if not psutil.pid_exists(pid)]
            for pid in dead:
                self._sleeping.pop(pid, None)
        if dead:
            remaining = len(self._sleeping)
            update_status("core.hibernation_manager",
                          STATUS_OK if remaining == 0 else STATUS_WARN,
                          f"{remaining} sleeping")
        return len(dead)

    def get_savings_estimate(self) -> dict:
        """
        Estimate resource impact of currently hibernated processes.

        Returns
        -------
        dict with:
          processes       : total sleeping process count
          total_sleep_min : combined CPU-minutes offline across all sleeping apps
          frozen_count    : processes fully suspended (NtSuspendProcess)
          low_count       : processes on idle priority (SetPriorityClass)
        """
        now = time.time()
        with self._lock:
            sleeping = list(self._sleeping.values())
        return {
            "processes":       len(sleeping),
            "total_sleep_min": int(sum(
                (now - s["slept_at"]) / 60 for s in sleeping)),
            "frozen_count":    sum(1 for s in sleeping
                                   if s["behavior"] == "freeze"),
            "low_count":       sum(1 for s in sleeping
                                   if s["behavior"] == "low"),
        }

    # ── Ignored list ──────────────────────────────────────────────────────────

    def add_ignored(self, exe: str) -> None:
        key = os.path.basename(exe).lower()
        with self._lock:
            self._ignored.add(key)
        self._save_prefs()

    def remove_ignored(self, exe: str) -> None:
        key = os.path.basename(exe).lower()
        with self._lock:
            self._ignored.discard(key)
        self._save_prefs()

    def is_ignored(self, exe: str) -> bool:
        key = os.path.basename(exe).lower()
        with self._lock:
            return key in self._ignored

    # ── Turbo behaviors ───────────────────────────────────────────────────────

    def set_turbo_behavior(self, exe: str, behavior: str) -> None:
        """behavior: 'none' | 'low' | 'freeze'"""
        key = os.path.basename(exe).lower()
        with self._lock:
            if behavior == "none":
                self._turbo_behaviors.pop(key, None)
            else:
                self._turbo_behaviors[key] = behavior
        self._save_prefs()

    def get_turbo_behavior(self, exe: str) -> str:
        key = os.path.basename(exe).lower()
        with self._lock:
            return self._turbo_behaviors.get(key, "none")

    def apply_turbo_behaviors(self) -> int:
        """
        Called when Turbo mode activates.
        Applies configured behaviors to all matching running processes.
        Returns count of processes affected.
        """
        with self._lock:
            behaviors = dict(self._turbo_behaviors)

        count = 0
        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name     = proc.info.get("name") or ""
                    exe      = proc.info.get("exe")  or ""
                    exe_key  = os.path.basename(exe).lower() if exe else name.lower()
                    behavior = behaviors.get(exe_key, "none")
                    if behavior == "none":
                        continue
                    if self.is_sleeping(proc.pid):
                        continue
                    if self.sleep_app(proc.pid, name, exe, behavior):
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        return count

    def restore_turbo_apps(self) -> int:
        """Called when Turbo mode deactivates. Wakes all Turbo-slept apps."""
        with self._lock:
            turbo_pids = [
                pid for pid, info in self._sleeping.items()
                if info.get("behavior") in ("low", "freeze")
            ]
        return sum(1 for pid in turbo_pids if self.wake_app(pid))

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_prefs(self) -> None:
        try:
            with open(_PREFS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._ignored         = set(data.get("ignored", []))
                self._turbo_behaviors = dict(data.get("turbo_behaviors", {}))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        except Exception:
            pass

    def _save_prefs(self) -> None:
        try:
            os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
            with self._lock:
                data = {
                    "ignored":         sorted(self._ignored),
                    "turbo_behaviors": dict(self._turbo_behaviors),
                }
            with open(_PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


# ── Low-level priority helper ─────────────────────────────────────────────────

def _set_priority(pid: int, priority_class: int) -> bool:
    try:
        h = ctypes.windll.kernel32.OpenProcess(
            PROCESS_SET_INFORMATION, False, pid
        )
        if not h:
            return False
        try:
            return bool(ctypes.windll.kernel32.SetPriorityClass(h, priority_class))
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return False


# ── Singleton ─────────────────────────────────────────────────────────────────

hibernation_manager = HibernationManager()
