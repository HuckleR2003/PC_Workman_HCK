# core/startup_watcher.py
"""
StartupWatcher - background thread that polls the Windows registry for:
  1. New autostart entries  (HKCU/HKLM Run keys)
  2. New installed applications  (Uninstall keys)

Thread-safe; fires callbacks on the calling thread (wrap with root.after(0,…)
when used from tkinter).

Usage
-----
    from core.startup_watcher import get_watcher

    w = get_watcher()
    w.register_startup_cb(lambda name, exe, hive: ...)
    w.register_app_cb(lambda name, exe: ...)
    w.start()          # starts background daemon thread
    # later:
    w.stop()
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable, List, Optional

from import_core import register_component, update_status, STATUS_OK, STATUS_STARTING

try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False


# ── Config ────────────────────────────────────────────────────────────────────

_POLL_INTERVAL   = 45      # seconds between registry scans
_FIRST_SCAN_WAIT = 30      # seconds after start() before first scan (let app load)
_OWN_APP_KEY     = "PC_Workman_HCK"   # ignore our own registry entry

_APP_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..")
)
_CACHE_FILE = os.path.join(_APP_DIR, "data", "cache", "system_watchers.json")

# Registry paths for startup entries
_STARTUP_PATHS = [
    ("HKCU", winreg.HKEY_CURRENT_USER  if _HAS_WINREG else None,
     r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM32", winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
] if _HAS_WINREG else []

# Registry paths for installed apps
_UNINSTALL_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE if _HAS_WINREG else None,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER  if _HAS_WINREG else None,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
] if _HAS_WINREG else []


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ── Registry readers ──────────────────────────────────────────────────────────

def _read_startup_ids() -> dict[str, dict]:
    """Return {uid: {name, exe, hive}} for every current startup entry."""
    if not _HAS_WINREG:
        return {}
    result: dict[str, dict] = {}
    for hive_label, hive_const, path in _STARTUP_PATHS:
        if hive_const is None:
            continue
        try:
            key = winreg.OpenKey(hive_const, path, 0, winreg.KEY_READ)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                i += 1
            except OSError:
                break
            if name.lower() == _OWN_APP_KEY.lower():
                continue
            exe = os.path.basename(value.strip('"').split()[0]).lower() if value else ""
            uid = f"{hive_label}:{name.lower()}"
            result[uid] = {"name": name, "exe": exe, "value": value, "hive": hive_label}
        winreg.CloseKey(key)
    return result


def _read_installed_apps() -> dict[str, dict]:
    """Return {display_name_lower: {name, exe}} for installed apps."""
    if not _HAS_WINREG:
        return {}
    result: dict[str, dict] = {}
    for hive_const, path in _UNINSTALL_PATHS:
        if hive_const is None:
            continue
        try:
            root_key = winreg.OpenKey(hive_const, path, 0, winreg.KEY_READ)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub_name = winreg.EnumKey(root_key, i)
                i += 1
            except OSError:
                break
            try:
                sub_key = winreg.OpenKey(root_key, sub_name, 0, winreg.KEY_READ)
                try:
                    display_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                except FileNotFoundError:
                    winreg.CloseKey(sub_key)
                    continue
                try:
                    display_icon, _ = winreg.QueryValueEx(sub_key, "DisplayIcon")
                    # Strip index suffix ",0"
                    exe = display_icon.split(",")[0].strip().strip('"')
                except FileNotFoundError:
                    exe = ""
                winreg.CloseKey(sub_key)
                key_lower = display_name.strip().lower()
                if key_lower and key_lower not in result:
                    result[key_lower] = {"name": display_name.strip(), "exe": exe}
            except OSError:
                continue
        winreg.CloseKey(root_key)
    return result


# ── Watcher class ─────────────────────────────────────────────────────────────

class StartupWatcher:
    """
    Background daemon that detects new startup entries and newly installed apps.

    Callbacks receive plain Python values and are invoked from the watcher
    thread - wrap with  root.after(0, lambda: cb(...))  for tkinter safety.
    """

    def __init__(self) -> None:
        self._startup_cbs: List[Callable] = []
        register_component("core.startup_watcher", self, STATUS_OK)
        self._app_cbs:     List[Callable] = []
        self._thread:      Optional[threading.Thread] = None
        self._stop_evt     = threading.Event()

        # Known sets - populated on first scan (baseline), never fired first time
        self._known_startup: Optional[set] = None
        self._known_apps:    Optional[set] = None

    # ── Registration ──────────────────────────────────────────────────────────

    def register_startup_cb(self, fn: Callable[[str, str, str], None]) -> None:
        """fn(name: str, exe: str, hive: str)"""
        self._startup_cbs.append(fn)

    def register_app_cb(self, fn: Callable[[str, str], None]) -> None:
        """fn(display_name: str, exe_path: str)"""
        self._app_cbs.append(fn)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._run, name="StartupWatcher", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        # Delay first scan so the app can finish loading
        if self._stop_evt.wait(timeout=_FIRST_SCAN_WAIT):
            return

        # Try to restore baseline from cache
        cache = _load_cache()
        if "startup_known" in cache:
            self._known_startup = set(cache["startup_known"])
        if "apps_known" in cache:
            self._known_apps = set(cache["apps_known"])

        while not self._stop_evt.is_set():
            try:
                self._scan()
            except Exception as exc:
                print(f"[StartupWatcher] scan error: {exc}")
            self._stop_evt.wait(timeout=_POLL_INTERVAL)

    def _scan(self) -> None:
        # ── Startup entries ────────────────────────────────────────────────────
        current_startup = _read_startup_ids()
        current_ids     = set(current_startup.keys())

        if self._known_startup is None:
            # First scan - establish baseline, no notifications
            self._known_startup = current_ids
            _save_cache(self._build_cache(current_ids, self._known_apps))
        else:
            new_entries = current_ids - self._known_startup
            for uid in new_entries:
                info = current_startup[uid]
                for cb in self._startup_cbs:
                    try:
                        cb(info["name"], info["exe"], info["hive"])
                    except Exception as exc:
                        print(f"[StartupWatcher] startup_cb error: {exc}")
            if new_entries:
                self._known_startup = current_ids
                _save_cache(self._build_cache(current_ids, self._known_apps))

        # ── Installed apps ─────────────────────────────────────────────────────
        current_apps    = _read_installed_apps()
        current_app_ids = set(current_apps.keys())

        if self._known_apps is None:
            self._known_apps = current_app_ids
            _save_cache(self._build_cache(self._known_startup, current_app_ids))
        else:
            new_apps = current_app_ids - self._known_apps
            for app_id in new_apps:
                info = current_apps[app_id]
                for cb in self._app_cbs:
                    try:
                        cb(info["name"], info["exe"])
                    except Exception as exc:
                        print(f"[StartupWatcher] app_cb error: {exc}")
            if new_apps:
                self._known_apps = current_app_ids
                _save_cache(self._build_cache(self._known_startup, current_app_ids))

    def _build_cache(self, startup_ids, app_ids) -> dict:
        return {
            "startup_known": sorted(startup_ids or []),
            "apps_known":    sorted(app_ids    or []),
            "last_scan":     time.time(),
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_instance: Optional[StartupWatcher] = None


def get_watcher() -> StartupWatcher:
    global _instance
    if _instance is None:
        _instance = StartupWatcher()
    return _instance
