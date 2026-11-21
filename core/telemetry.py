"""
Anonymous, opt-in telemetry  -  PC Workman
===========================================
Sends a minimal hardware/usage snapshot ONLY when the user has explicitly turned
on Network Access + Telemetry in Settings. Everything goes through core.network's
single gate, so with the master switch off this module sends nothing.

What it sends (and nothing else):
    install_id  random anonymous UUID
    app_version / os / country (from locale, never from IP)
    cpu / gpu / ram / disk / motherboard MODELS (hardware, not identity)
    screens      up to 4 monitors: resolution, refresh rate, Windows scaling
    session_min  how long the app has been open this run

What it never touches: usernames, machine names, IPs, file paths, process names,
or any content. `build_payload()` returns the exact dict that is sent, so the
Settings consent dialog can show the user the literal payload before they agree.
"""
from __future__ import annotations

import atexit
import locale
import platform
import threading
import time
import uuid

# Deployed Cloudflare Worker endpoint. Fill in after you deploy the worker
# (cloudflare/telemetry-worker.js).  Until then telemetry simply no-ops.
ENDPOINT = "https://pcworkmantelemetry.firmuga-marcin-s.workers.dev"

_session_start = time.time()
# One random id per run, so the start / heartbeat / end reports of one
# session can be grouped. Not stored anywhere on the machine.
_session_id = uuid.uuid4().hex[:12]

# Why session_min was always 0 (found 2026-11-15): the only report was sent
# 2 seconds after start, so "how long the app has been open" was always
# int(2 / 60) = 0. Now a session reports three times:
#   start      right after launch (hardware, version, country)
#   heartbeat  every HEARTBEAT_S while the app runs (survives a crash or a
#              Task Manager kill, which never reach the end report)
#   end        on a normal exit, with the real session length
HEARTBEAT_S = 60 * 60
END_TIMEOUT_S = 3.0          # never hold up closing the app for longer
_MIN_END_SESSION_S = 60      # a sub-minute run says nothing a start didn't

_reporter = {"thread": None, "stop": threading.Event(), "version": ""}


def _os_info() -> str:
    try:
        return f"{platform.system()} {platform.release()} (build {platform.version()})"
    except Exception:
        return ""


def _country() -> str:
    """Two-letter region from the OS locale - never from an IP address."""
    try:
        loc = (locale.getdefaultlocale()[0] or "")
        return loc.split("_")[-1] if "_" in loc else ""
    except Exception:
        return ""


MAX_SCREENS = 4


def _screens() -> list:
    """Every monitor: physical resolution, refresh rate, Windows scaling and
    which one is primary. Sizes only - never monitor names, serials or EDID.

    Added 2026-11-16 so layout work (the 125% Services loop, small laptop
    screens, ultrawides) can be judged by what users actually run.

    Resolution and refresh come from EnumDisplaySettings, which reports the
    real mode whatever the process DPI awareness is. Scaling comes from
    GetDpiForMonitor; startup.py makes the app per-monitor DPI aware, so it is
    correct in the app (a DPI-unaware test process reads 100%)."""
    out = []
    try:
        import ctypes
        from ctypes import wintypes

        # Private DLL handles: setting argtypes here must not change how the
        # rest of the app calls ctypes.windll.user32.
        user32 = ctypes.WinDLL("user32")
        try:
            shcore = ctypes.WinDLL("shcore")
        except OSError:
            shcore = None

        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                        ("szDevice", wintypes.WCHAR * 32)]

        class DEVMODEW(ctypes.Structure):
            _fields_ = [("dmDeviceName", wintypes.WCHAR * 32),
                        ("dmSpecVersion", wintypes.WORD), ("dmDriverVersion", wintypes.WORD),
                        ("dmSize", wintypes.WORD), ("dmDriverExtra", wintypes.WORD),
                        ("dmFields", wintypes.DWORD),
                        ("dmPositionX", wintypes.LONG), ("dmPositionY", wintypes.LONG),
                        ("dmDisplayOrientation", wintypes.DWORD),
                        ("dmDisplayFixedOutput", wintypes.DWORD),
                        ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
                        ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
                        ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
                        ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
                        ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
                        ("dmDisplayFlags", wintypes.DWORD),
                        ("dmDisplayFrequency", wintypes.DWORD),
                        ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD),
                        ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
                        ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
                        ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD)]

        ENUM_CURRENT_SETTINGS = -1
        MONITORINFOF_PRIMARY = 1
        MDT_EFFECTIVE_DPI = 0

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
            ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p,
                                               MonitorEnumProc, wintypes.LPARAM]
        user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR,
                                           ctypes.POINTER(MONITORINFOEXW)]
        user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                                ctypes.POINTER(DEVMODEW)]

        def _one(hmon, _hdc, _rect, _data):
            try:
                mi = MONITORINFOEXW()
                mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
                if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    return True
                r = mi.rcMonitor
                w, h, hz = r.right - r.left, r.bottom - r.top, 0
                dm = DEVMODEW()
                dm.dmSize = ctypes.sizeof(DEVMODEW)
                if user32.EnumDisplaySettingsW(mi.szDevice, ENUM_CURRENT_SETTINGS & 0xFFFFFFFF,
                                               ctypes.byref(dm)):
                    w, h, hz = int(dm.dmPelsWidth), int(dm.dmPelsHeight), int(dm.dmDisplayFrequency)
                scale = 100
                if shcore is not None:
                    dx, dy = wintypes.UINT(), wintypes.UINT()
                    if shcore.GetDpiForMonitor(hmon, MDT_EFFECTIVE_DPI,
                                               ctypes.byref(dx), ctypes.byref(dy)) == 0 and dx.value:
                        scale = round(dx.value * 100 / 96)
                out.append({"w": w, "h": h, "hz": hz if hz > 1 else 0, "scale": scale,
                            "primary": bool(mi.dwFlags & MONITORINFOF_PRIMARY)})
            except Exception:
                pass
            return True

        user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_one), 0)
    except Exception:
        return []
    out.sort(key=lambda s: not s["primary"])          # primary first
    return out[:MAX_SCREENS]


def _resolve_version(app_version: str = "") -> str:
    """Use the caller's version, else the ONE version source
    (utils/app_version.py). The old approach read startup.py as a FILE, which
    does not exist inside a frozen dist - the Settings 'send on enable' path
    silently reported the stale fallback there."""
    if app_version:
        return app_version
    try:
        from utils.app_version import APP_VERSION
        return APP_VERSION
    except Exception:
        return "unknown"


def build_payload(app_version: str = "", kind: str = "start") -> dict:
    """The exact anonymous snapshot we would send. Safe to show the user verbatim."""
    from core import network

    payload = {
        "install_id":  network.get_install_id(),
        "app_version": _resolve_version(app_version),
        "ts":          int(time.time()),
        "kind":        kind,
        "session_id":  _session_id,
        "session_min": int((time.time() - _session_start) / 60),
        "os":          _os_info(),
        "country":     _country(),
        "cpu":         "",
        "cpu_cores":   0,
        "gpu":         "",
        "ram_gb":      0,
        "ram_mhz":     0,
        "disks":       [],
        "motherboard": "",
        "screens":     _screens(),
    }
    try:
        from core.hardware_detector import get_hardware_detector
        hw  = get_hardware_detector().get_data()
        cpu = hw.get("cpu") or {}
        gpu = hw.get("gpu") or {}
        ram = hw.get("ram") or {}
        mb  = hw.get("motherboard") or {}
        payload["cpu"]       = cpu.get("name", "") or ""
        payload["cpu_cores"] = int(cpu.get("cores_physical", 0) or 0)
        payload["gpu"]       = gpu.get("name", "") or ""
        payload["ram_gb"]    = round(ram.get("total_gb", 0) or 0)
        payload["ram_mhz"]   = int(ram.get("speed_mhz", 0) or 0)
        payload["motherboard"] = " ".join(
            x for x in (mb.get("manufacturer", ""), mb.get("product", "")) if x
        ).strip()
        for d in (hw.get("storage") or {}).get("drives", [])[:4]:
            payload["disks"].append({
                "model": d.get("model", ""),
                "size_gb": d.get("size_gb", 0),
                "type": d.get("media_type", ""),
            })
    except Exception:
        pass
    return payload


def send(app_version: str = "", kind: str = "start",
         timeout: float = 6.0) -> bool:
    """Send the snapshot if (and only if) the user opted in. Returns success.

    Runs a synchronous hardware scan first so the payload carries real specs even
    when the user never opened the My PC -> Components tab. Call off the UI thread
    (startup fires this from a daemon thread; Settings from 'telemetry-now')."""
    from core import network
    if not network.telemetry_enabled() or not ENDPOINT:
        return False
    if kind == "start":
        try:
            from core.hardware_detector import get_hardware_detector
            get_hardware_detector().ensure_data()   # blocks until specs are known
        except Exception:
            pass
    return network.post_json(ENDPOINT, build_payload(app_version, kind),
                             timeout=timeout)


def start_reporting(app_version: str = "", first_delay_s: float = 2.0,
                    heartbeat_s: float = None) -> None:
    """Start the session reports (start, hourly heartbeat, end on exit).
    Safe to call more than once; only the first call does anything."""
    if _reporter["thread"] is not None:
        return
    _reporter["version"] = app_version
    every = HEARTBEAT_S if heartbeat_s is None else heartbeat_s
    stop = _reporter["stop"]

    def _loop():
        if stop.wait(first_delay_s):
            return
        try:
            send(app_version, "start")
        except Exception:
            pass
        while not stop.wait(every):
            try:
                send(app_version, "heartbeat")
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="telemetry")
    _reporter["thread"] = t
    t.start()
    atexit.register(_send_end)


def _send_end() -> None:
    """Final report with the real session length. Short timeout: closing the
    app must never wait on the network."""
    _reporter["stop"].set()
    if time.time() - _session_start < _MIN_END_SESSION_S:
        return
    try:
        send(_reporter["version"], "end", timeout=END_TIMEOUT_S)
    except Exception:
        pass
