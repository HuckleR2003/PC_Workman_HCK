"""
core/turbo_manager.py
─────────────────────
TURBO Mode Backend - three subsystems:

  TurboServiceManager   - stop non-essential Windows services by profile
  TurboProcessSuspender - freeze idle background processes, resume on demand
  TurboPowerManager     - auto-switch power plan; game/battery detection

Singletons exposed at module level:
  turbo_services  = TurboServiceManager()
  turbo_processes = TurboProcessSuspender()
  turbo_power     = TurboPowerManager()
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import threading
import time
from typing import Optional

import psutil
from import_core import register_component, update_status, STATUS_OK, STATUS_IDLE

# ─── Paths ────────────────────────────────────────────────────────────────────
try:
    from utils.paths import APP_DIR as _APP_DIR
except Exception:
    import sys as _sys
    _APP_DIR = (
        os.path.dirname(_sys.executable)
        if getattr(_sys, "frozen", False)
        else os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    )

_LOG_PATH      = os.path.join(_APP_DIR, "data", "logs", "turbo_engine.log")
_STATE_PATH    = os.path.join(_APP_DIR, "settings", "turbo_state.json")
_PROFILES_PATH = os.path.join(_APP_DIR, "settings", "turbo_services.json")  # user mode edits

os.makedirs(os.path.dirname(_LOG_PATH),   exist_ok=True)
os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)


def _log(tag: str, msg: str) -> None:
    import datetime
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] [{tag}]  {msg}\n")
    except Exception:
        pass


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  SERVICE PROFILES
# ══════════════════════════════════════════════════════════════════════════════

# These services are NEVER touched regardless of profile.
_SVC_WHITELIST: set[str] = {
    # Core Windows
    "RpcSs", "RpcEptMapper", "DcomLaunch", "LSM", "lsass",
    "services", "wininit", "winlogon", "smss",
    # Security - absolute no-touch
    "WinDefend", "MpsSvc", "SecurityHealthService", "wscsvc",
    "BITS", "CryptSvc", "EventLog", "EventSystem", "SamSs",
    # Audio
    "Audiosrv", "AudioEndpointBuilder",
    # Graphics / GPU
    "GraphicsPerfSvc", "nvlddmkm", "amdkmdag",
    # Network stack
    "Dhcp", "Dnscache", "NlaSvc", "netprofm", "Netman",
    "LanmanWorkstation", "LanmanServer", "Nsi",
    # Task infra
    "Schedule", "Power",
}

# Friendly names shown in the UI
_SVC_LABELS: dict[str, str] = {
    "DiagTrack":          "Connected User Telemetry",
    "dmwappushservice":   "WAP Push Message Routing",
    "SysMain":            "SuperFetch (Superfetch)",
    "WSearch":            "Windows Search Indexing",
    "XblAuthManager":     "Xbox Live Auth Manager",
    "XblGameSave":        "Xbox Live Game Save",
    "XboxGipSvc":         "Xbox Accessory Management",
    "XboxNetApiSvc":      "Xbox Live Networking",
    "MapsBroker":         "Downloaded Maps Manager",
    "TabletInputService": "Touch Keyboard & Handwriting",
    "Fax":                "Fax Service",
    "RemoteRegistry":     "Remote Registry",
    "TermService":        "Remote Desktop (RDP)",
    "spooler":            "Print Spooler",
    "BTAGService":        "Bluetooth Audio Gateway",
    "bthserv":            "Bluetooth Support Service",
    "WerSvc":             "Windows Error Reporting",
    "wuauserv":           "Windows Update (session)",
    "RetailDemo":         "Retail Demo Service",
    "SEMgrSvc":           "Payments & NFC/SE Manager",
    "WbioSrvc":           "Windows Biometric Service",
}

PROFILES: dict[str, dict] = {
    "gaming": {
        "label":    "Gaming",
        "color":    "#c62828",   # bordeaux
        "bg":       "#170808",
        "services": [
            "DiagTrack", "dmwappushservice",
            "SysMain", "WSearch",
            "XblAuthManager", "XblGameSave", "XboxGipSvc", "XboxNetApiSvc",
            "MapsBroker", "TabletInputService",
            "Fax", "RemoteRegistry", "TermService",
            "spooler", "BTAGService", "bthserv",
            "RetailDemo", "SEMgrSvc",
        ],
        "desc": "Max CPU headroom - stops search, telemetry, Xbox, BT, printing.",
    },
    "economy": {
        "label":    "Economy",
        "color":    "#10b981",   # emerald
        "bg":       "#061210",
        "services": [
            "DiagTrack", "dmwappushservice",
            "SysMain", "WSearch",
            "XblAuthManager", "XblGameSave", "XboxGipSvc", "XboxNetApiSvc",
            "MapsBroker", "TabletInputService",
            "Fax", "RemoteRegistry", "TermService",
            "spooler", "BTAGService", "bthserv",
            "WerSvc", "wuauserv",
            "RetailDemo", "SEMgrSvc", "WbioSrvc",
        ],
        "desc": "Deep savings - stops all non-essential including Update & BT.",
    },
    # User-composed custom profile, built in the Services Manager. White-themed,
    # starts empty — the user picks exactly which services it stops.
    "manager": {
        "label":    "Manager",
        "color":    "#e5e7eb",   # near-white
        "bg":       "#101014",
        "services": [],
        "desc":     "Your custom set — pick exactly which services stop. Edit in Services Manager.",
    },
}

# Recommended-to-disable services, each paired with a plain-language question so
# the Services Manager can guide the user ("Do you use Bluetooth?"). Answering
# "no" is a strong hint the service is safe to add to a mode's stop-list.
RECOMMENDED: list[dict] = [
    {"label": "Bluetooth",      "services": ["bthserv", "BTAGService"],
     "q_pl": "Czy używasz Bluetooth?",            "q_en": "Do you use Bluetooth?"},
    {"label": "Drukowanie",     "services": ["spooler"],
     "q_pl": "Czy drukujesz na tym komputerze?",  "q_en": "Do you print on this PC?"},
    {"label": "Xbox",           "services": ["XblAuthManager", "XblGameSave",
                                             "XboxGipSvc", "XboxNetApiSvc"],
     "q_pl": "Grasz w gry Xbox / Game Pass?",      "q_en": "Do you play Xbox / Game Pass games?"},
    {"label": "Telemetria",     "services": ["DiagTrack", "dmwappushservice"],
     "q_pl": "Wyłączyć telemetrię Microsoftu?",    "q_en": "Disable Microsoft telemetry?"},
    {"label": "Fax",            "services": ["Fax"],
     "q_pl": "Czy używasz faksu?",                 "q_en": "Do you use fax?"},
    {"label": "Pulpit zdalny",  "services": ["RemoteRegistry", "TermService"],
     "q_pl": "Używasz pulpitu/rejestru zdalnego?", "q_en": "Do you use remote desktop/registry?"},
]


# ══════════════════════════════════════════════════════════════════════════════
#  TurboServiceManager
# ══════════════════════════════════════════════════════════════════════════════

class TurboServiceManager:
    """Stop / restore Windows services by TURBO profile."""

    def __init__(self) -> None:
        self._stopped:  dict[str, str] = {}   # {svc: original_state}
        self._lock      = threading.Lock()
        self._confirmed = False               # user confirmed first-use warning
        self._overrides = self._load_overrides()   # {mode: [services]} user edits
        register_component('core.turbo_services', self, STATUS_IDLE)

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_admin(self) -> bool:
        return _is_admin()

    @property
    def active(self) -> bool:
        return bool(self._stopped)

    @property
    def stopped_count(self) -> int:
        return len(self._stopped)

    def get_service_statuses(self, services: list[str]) -> dict[str, str]:
        """Return {svc: 'running'|'stopped'|'unknown'} for given services."""
        result = {}
        try:
            r = subprocess.run(
                ["sc", "queryex", "type=", "all", "state=", "all"],
                capture_output=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            current = None
            state   = "unknown"
            for line in r.stdout.decode("utf-8", errors="replace").splitlines():
                ls = line.strip()
                if ls.startswith("SERVICE_NAME:"):
                    if current and current in services:
                        result[current] = state
                    current = ls.split(":", 1)[1].strip()
                    state   = "unknown"
                elif ls.startswith("STATE") and ":" in ls:
                    sl = ls.lower()
                    if "running" in sl:
                        state = "running"
                    elif "stopped" in sl:
                        state = "stopped"
                    elif "paused" in sl:
                        state = "paused"
            if current and current in services:
                result[current] = state
        except Exception:
            pass
        # Fill missing
        for svc in services:
            result.setdefault(svc, "unknown")
        return result

    def stop_profile(
        self,
        profile_key: str,
        progress_cb=None,       # called(svc, ok, msg) per service
    ) -> list[tuple[str, bool, str]]:
        """Stop all services in profile. Returns [(svc, ok, msg)]."""
        services = [
            s for s in self.get_profile_services(profile_key)
            if s not in _SVC_WHITELIST
        ]
        statuses = self.get_service_statuses(services)
        results  = []

        for svc in services:
            orig = statuses.get(svc, "unknown")
            if orig == "running":
                ok, msg = self._sc("stop", svc)
                with self._lock:
                    if ok:
                        self._stopped[svc] = "running"
            else:
                ok, msg = True, "already stopped"
            results.append((svc, ok, msg))
            if progress_cb:
                progress_cb(svc, ok, msg)

        _log("SVC", f"profile={profile_key}  stopped={self.stopped_count}")
        self._persist()
        return results

    def restore_all(self, progress_cb=None) -> list[tuple[str, bool, str]]:
        """Start all services we previously stopped."""
        with self._lock:
            to_restore = list(self._stopped.items())

        results = []
        for svc, orig in to_restore:
            if orig == "running":
                ok, msg = self._sc("start", svc)
                if ok:
                    with self._lock:
                        self._stopped.pop(svc, None)
                results.append((svc, ok, msg))
                if progress_cb:
                    progress_cb(svc, ok, msg)

        _log("SVC", f"restore_all  restored={len(results)}")
        self._persist()
        return results

    def load_state(self) -> None:
        """Reload stopped-service state from disk (crash recovery)."""
        try:
            with open(_STATE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._stopped = data.get("svc_stopped", {})
        except Exception:
            pass

    # ── Editable profiles (single source of truth, synced with Features) ───────

    def _load_overrides(self) -> dict:
        try:
            with open(_PROFILES_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_overrides(self) -> None:
        try:
            os.makedirs(os.path.dirname(_PROFILES_PATH), exist_ok=True)
            with open(_PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(self._overrides, f, indent=2)
        except Exception:
            pass

    def get_profile_services(self, key: str) -> list[str]:
        """Effective stop-list for a mode: user override if set, else the preset."""
        if key in self._overrides:
            return list(self._overrides[key])
        return list(PROFILES.get(key, {}).get("services", []))

    def set_profile_services(self, key: str, services: list[str]) -> None:
        self._overrides[key] = sorted(set(services))
        self._save_overrides()

    def set_membership(self, key: str, svc: str, on: bool) -> None:
        """Add/remove a single service from a mode's stop-list (persisted)."""
        cur = set(self.get_profile_services(key))
        cur.add(svc) if on else cur.discard(svc)
        self.set_profile_services(key, sorted(cur))

    def reset_profile(self, key: str) -> None:
        """Drop the user override so the mode falls back to its built-in preset."""
        self._overrides.pop(key, None)
        self._save_overrides()

    def get_active_profile(self) -> str:
        """Currently selected mode, shared by the Services Manager and Features."""
        key = self._overrides.get("__active__", "gaming")
        return key if key in PROFILES else "gaming"

    def set_active_profile(self, key: str) -> None:
        if key in PROFILES:
            self._overrides["__active__"] = key
            self._save_overrides()

    @staticmethod
    def friendly(svc: str) -> str:
        return _SVC_LABELS.get(svc, svc)

    def list_all_services(self) -> list[dict]:
        """Every Windows service: [{name, display, state}], sorted by display name.
        Whitelisted core services are flagged 'locked' so the UI can protect them."""
        out = []
        try:
            r = subprocess.run(
                ["sc", "query", "type=", "service", "state=", "all"],
                capture_output=True, timeout=12,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            name = disp = None
            state = "unknown"
            for line in r.stdout.decode("utf-8", errors="replace").splitlines():
                ls = line.strip()
                if ls.startswith("SERVICE_NAME:"):
                    if name:
                        out.append({"name": name, "display": disp or name,
                                    "state": state, "locked": name in _SVC_WHITELIST})
                    name = ls.split(":", 1)[1].strip()
                    disp, state = None, "unknown"
                elif ls.startswith("DISPLAY_NAME:"):
                    disp = ls.split(":", 1)[1].strip()
                elif ls.startswith("STATE") and ":" in ls:
                    sl = ls.lower()
                    state = ("running" if "running" in sl else
                             "stopped" if "stopped" in sl else "unknown")
            if name:
                out.append({"name": name, "display": disp or name,
                            "state": state, "locked": name in _SVC_WHITELIST})
        except Exception:
            pass
        out.sort(key=lambda s: s["display"].lower())
        return out

    # ── Internal ──────────────────────────────────────────────────────────────

    def _sc(self, action: str, svc: str) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                ["sc", action, svc],
                capture_output=True, timeout=12,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            ok  = r.returncode == 0
            err = r.stderr.decode("utf-8", errors="replace").strip()
            out = r.stdout.decode("utf-8", errors="replace").strip()
            msg = "OK" if ok else (err or out)[:60]
            _log("SVC", f"{action.upper()} {svc}  ->  {'OK' if ok else msg}")
            return ok, msg
        except Exception as ex:
            return False, str(ex)[:50]

    def _persist(self) -> None:
        try:
            with self._lock:
                snap = dict(self._stopped)
            existing = {}
            try:
                with open(_STATE_PATH, encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
            existing["svc_stopped"] = snap
            with open(_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  PROCESS SUSPENSION - blacklists
# ══════════════════════════════════════════════════════════════════════════════

_PROC_WHITELIST_NAMES: set[str] = {
    # System core
    "System", "Registry", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe", "svchost.exe",
    "dwm.exe", "fontdrvhost.exe", "spoolsv.exe", "explorer.exe",
    "conhost.exe", "taskhostw.exe", "sihost.exe", "ctfmon.exe",
    "SearchIndexer.exe", "SearchHost.exe",
    # Security
    "MsMpEng.exe", "MpCmdRun.exe", "SecurityHealthSystray.exe",
    "SecurityHealthHost.exe", "avp.exe", "avgnt.exe", "mbam.exe",
    "ccSvcHst.exe", "NortonSecurity.exe",
    # Display / GPU
    "nvcontainer.exe", "nvdisplay.container.exe", "NVDisplay.Container.exe",
    "RtkAudioService64.exe",
    # PC Workman itself
    "startup.py", "python.exe", "pythonw.exe",
}

_PROC_WHITELIST_KEYWORDS = (
    "antivirus", "antimalware", "firewall", "defender",
    "nvidia", "amd", "intel", "display", "audio",
    "windows\\system32", "windows\\syswow64",
)

# Known safe paths (partial) - process running elsewhere = suspicious
_KNOWN_EXE_PATHS: dict[str, str] = {
    "chrome.exe":   r"program files\google\chrome",
    "msedge.exe":   r"program files (x86)\microsoft\edge",
    "firefox.exe":  r"program files\mozilla firefox",
    "discord.exe":  r"appdata",
    "spotify.exe":  r"appdata",
    "onedrive.exe": r"appdata\local\microsoft\onedrive",
    "slack.exe":    r"appdata",
    "teams.exe":    r"appdata",
    "steam.exe":    r"program files (x86)\steam",
}

# Candidates we actively look for - well-known idle-able apps
SUSPEND_CANDIDATES = (
    "chrome.exe", "msedge.exe", "firefox.exe",
    "discord.exe", "slack.exe", "teams.exe",
    "spotify.exe", "onedrive.exe", "dropbox.exe",
    "googledrivefs.exe", "OneDrive.exe",
    "EpicGamesLauncher.exe", "steam.exe",
)

IDLE_SECONDS_DEFAULT = 5 * 60    # 5 minutes
AUTO_RESUME_SECONDS  = 30 * 60   # 30 minutes


# ══════════════════════════════════════════════════════════════════════════════
#  TurboProcessSuspender
# ══════════════════════════════════════════════════════════════════════════════

class TurboProcessSuspender:
    """
    Detect idle background processes and freeze them.
    Uses psutil.suspend() / resume().
    Checks for process name spoofing before suspending.
    Auto-resumes after AUTO_RESUME_SECONDS or when TURBO off.
    """

    def __init__(self) -> None:
        self._suspended: dict[int, dict] = {}   # pid -> info dict
        self._cpu_samples: dict[int, list] = {} # pid -> [float, ...]
        self._lock        = threading.Lock()
        self._running     = False
        self.idle_threshold = IDLE_SECONDS_DEFAULT
        self._sample_interval = 30              # scan every 30 s
        register_component('core.turbo_processes', self, STATUS_IDLE)

    # ── Control ───────────────────────────────────────────────────────────────

    def start(self, idle_seconds: int = IDLE_SECONDS_DEFAULT) -> None:
        self.idle_threshold = idle_seconds
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._loop, daemon=True, name="turbo-proc").start()
        _log("PROC", f"monitor started  idle_threshold={idle_seconds}s")

    def stop(self) -> None:
        self._running = False
        self.resume_all()
        _log("PROC", "monitor stopped - all resumed")

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def active(self) -> bool:
        return self._running

    @property
    def suspended_count(self) -> int:
        return len(self._suspended)

    @property
    def suspended_list(self) -> list[dict]:
        now = time.time()
        with self._lock:
            return [
                {
                    "pid":          info["pid"],
                    "name":         info["name"],
                    "idle_seconds": int(now - info["suspended_at"]),
                    "suspicious":   info.get("suspicious", False),
                }
                for info in self._suspended.values()
            ]

    def resume(self, pid: int) -> bool:
        with self._lock:
            info = self._suspended.pop(pid, None)
        if info is None:
            return False
        try:
            psutil.Process(pid).resume()
            _log("PROC", f"resumed  pid={pid}  name={info['name']}")
            return True
        except Exception:
            return False

    def resume_all(self) -> int:
        with self._lock:
            pids = list(self._suspended.keys())
        count = sum(1 for p in pids if self.resume(p))
        if count:
            _log("PROC", f"resume_all  count={count}")
        return count

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._scan()
                self._expire_old()
            except Exception:
                pass
            time.sleep(self._sample_interval)

    def _scan(self) -> None:
        fg_pid  = self._foreground_pid()
        our_pid = os.getpid()
        needed_samples = max(2, self.idle_threshold // self._sample_interval)

        for proc in psutil.process_iter(["pid", "name", "exe", "status"]):
            try:
                pid  = proc.pid
                name = proc.info.get("name") or ""
                exe  = proc.info.get("exe")  or ""

                # Hard skips
                if (pid <= 8
                        or pid == our_pid
                        or pid == fg_pid
                        or pid in self._suspended
                        or proc.info.get("status") == psutil.STATUS_ZOMBIE):
                    continue

                if self._is_whitelisted(name, exe):
                    continue

                # CPU sample
                cpu = proc.cpu_percent(interval=None)
                samples = self._cpu_samples.setdefault(pid, [])
                samples.append(cpu)
                if len(samples) > needed_samples + 2:
                    samples.pop(0)

                # Suspend when idle for threshold
                if (len(samples) >= needed_samples
                        and all(s < 0.8 for s in samples[-needed_samples:])):
                    suspicious = self._is_suspicious(name, exe)
                    self._suspend(proc, suspicious)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._cpu_samples.pop(proc.pid, None)
            except Exception:
                pass

    def _suspend(self, proc: psutil.Process, suspicious: bool = False) -> None:
        pid  = proc.pid
        name = proc.name()
        try:
            proc.suspend()
            with self._lock:
                self._suspended[pid] = {
                    "pid":          pid,
                    "name":         name,
                    "suspended_at": time.time(),
                    "suspicious":   suspicious,
                }
            self._cpu_samples.pop(pid, None)
            flag = "  ⚠ suspicious path" if suspicious else ""
            _log("PROC", f"suspended  pid={pid}  name={name}{flag}")
        except Exception:
            pass

    def _expire_old(self) -> None:
        now = time.time()
        with self._lock:
            expired = [
                pid for pid, info in self._suspended.items()
                if now - info["suspended_at"] > AUTO_RESUME_SECONDS
            ]
        for pid in expired:
            self.resume(pid)

    def _is_whitelisted(self, name: str, exe: str) -> bool:
        # Anti-cheat first — the one category we must never suspend.
        try:
            from core.protected_processes import is_protected
            if is_protected(name, exe):
                return True
        except Exception:
            pass
        if name in _PROC_WHITELIST_NAMES:
            return True
        nl = name.lower()
        el = exe.lower()
        return any(kw in nl or kw in el for kw in _PROC_WHITELIST_KEYWORDS)

    def _is_suspicious(self, name: str, exe: str) -> bool:
        """Name doesn't match exe, or known app running from unexpected path."""
        if not exe:
            return False
        exe_basename = os.path.basename(exe).lower()
        if exe_basename != name.lower():
            return True
        expected = _KNOWN_EXE_PATHS.get(name.lower())
        if expected and expected not in exe.lower():
            return True
        return False

    @staticmethod
    def _foreground_pid() -> int:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid  = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value
        except Exception:
            return 0


# ══════════════════════════════════════════════════════════════════════════════
#  TurboPowerManager
# ══════════════════════════════════════════════════════════════════════════════

_PLAN_GUIDS = {
    "balanced":    "381b4222-f694-41f0-9685-ff5bb260df2e",
    "high_perf":   "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
    "ultimate":    "e9a42b02-d5df-448d-aa00-03f14749eb61",
    "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
}


class TurboPowerManager:
    """
    Stable power-plan switcher with:
    - Language-agnostic GUID parsing
    - Admin check
    - Game / fullscreen detection
    - Battery-mode override
    - atexit restore guarantee
    """

    def __init__(self) -> None:
        self._original: Optional[str] = None
        self._turbo_guid: Optional[str] = None
        self.active   = False
        self._lock    = threading.Lock()
        self._monitor = False
        register_component('core.turbo_power', self, STATUS_IDLE)

    # ── Power plan helpers ────────────────────────────────────────────────────

    def list_plans(self) -> dict[str, str]:
        """Return {name: guid} from powercfg /list - language-agnostic.
        Uses binary mode + safe UTF-8 decode to handle any OEM codepage."""
        plans = {}
        try:
            r = subprocess.run(
                ["powercfg", "/list"],
                capture_output=True, timeout=6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout = r.stdout.decode("utf-8", errors="replace")
            for line in stdout.splitlines():
                parts = line.strip().split()
                for i, p in enumerate(parts):
                    if len(p) == 36 and p.count("-") == 4:
                        name = " ".join(parts[i + 1:]).strip("*()\t ").strip()
                        if name:
                            plans[name] = p
                        break
        except Exception:
            pass
        return plans

    def active_guid(self) -> Optional[str]:
        try:
            r = subprocess.run(
                ["powercfg", "/getactivescheme"],
                capture_output=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout = r.stdout.decode("utf-8", errors="replace")
            for tok in stdout.split():
                if len(tok) == 36 and tok.count("-") == 4:
                    return tok
        except Exception:
            pass
        return None

    def set_plan(self, guid: str) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                ["powercfg", "/setactive", guid],
                capture_output=True, timeout=6,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            ok = r.returncode == 0
            err = r.stderr.decode("utf-8", errors="replace").strip()[:40]
            _log("PWR", f"setactive {guid}  ->  {'OK' if ok else err}")
            return ok, ("OK" if ok else err[:50])
        except Exception as ex:
            return False, str(ex)[:50]

    def create_turbo_plan(self, name: str = "Turbo PC") -> Optional[str]:
        """Duplicate HP or Ultimate Performance and rename.  Needs admin."""
        plans = self.list_plans()
        if name in plans:
            return plans[name]
        for src in (_PLAN_GUIDS["high_perf"], _PLAN_GUIDS["ultimate"]):
            r = subprocess.run(
                ["powercfg", "/duplicatescheme", src],
                capture_output=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout_dup = r.stdout.decode("utf-8", errors="replace")
            new_guid = next(
                (t for t in stdout_dup.split()
                 if len(t) == 36 and t.count("-") == 4 and t.lower() != src.lower()),
                None,
            )
            if new_guid:
                subprocess.run(
                    ["powercfg", "/changename", new_guid, name,
                     "PC Workman - Turbo PC custom high-performance profile"],
                    capture_output=True, timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                _log("PWR", f"created Turbo plan  guid={new_guid}")
                return new_guid
        return None

    # ── Activate / restore ────────────────────────────────────────────────────

    def activate(self) -> tuple[bool, str]:
        if not _is_admin():
            return False, "Needs admin - restart as Administrator"
        if self.is_on_battery():
            return False, "On battery - not switching to high perf"
        with self._lock:
            if not self._original:
                self._original = self.active_guid()
            if not self._turbo_guid:
                self._turbo_guid = self.create_turbo_plan()
            if not self._turbo_guid:
                return False, "Failed to create Turbo PC plan"
        ok, msg = self.set_plan(self._turbo_guid)
        if ok:
            self.active = True
        return ok, "Turbo PC  active ✓" if ok else msg

    def restore(self) -> tuple[bool, str]:
        guid = self._original or _PLAN_GUIDS["balanced"]
        ok, msg = self.set_plan(guid)
        if ok:
            self.active = False
        return ok, "Balanced restored ✓" if ok else msg

    # ── Detection helpers ─────────────────────────────────────────────────────

    @staticmethod
    def is_fullscreen_game() -> bool:
        """True if the foreground window fills the primary screen."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            sw = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            sh = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
            w  = rect.right - rect.left
            h  = rect.bottom - rect.top
            return w >= sw * 0.95 and h >= sh * 0.95
        except Exception:
            return False

    @staticmethod
    def is_on_battery() -> bool:
        try:
            bat = psutil.sensors_battery()
            if bat:
                return not bat.power_plugged
        except Exception:
            pass
        return False

    def start_auto_monitor(self, interval: int = 15) -> None:
        """Poll for fullscreen game; activate/restore automatically."""
        if self._monitor:
            return
        self._monitor = True
        def _loop():
            while self._monitor:
                try:
                    game_on = self.is_fullscreen_game()
                    if game_on and not self.active:
                        self.activate()
                    elif not game_on and self.active:
                        self.restore()
                except Exception:
                    pass
                time.sleep(interval)
        threading.Thread(target=_loop, daemon=True, name="turbo-pwr").start()

    def stop_auto_monitor(self) -> None:
        self._monitor = False


# ── Module-level singletons ───────────────────────────────────────────────────

turbo_services  = TurboServiceManager()
turbo_processes = TurboProcessSuspender()
turbo_power     = TurboPowerManager()

# Load persisted state on import (crash recovery for service restore)
turbo_services.load_state()
