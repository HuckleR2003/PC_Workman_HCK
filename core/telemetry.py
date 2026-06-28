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
    session_min  how long the app has been open this run

What it never touches: usernames, machine names, IPs, file paths, process names,
or any content. `build_payload()` returns the exact dict that is sent, so the
Settings consent dialog can show the user the literal payload before they agree.
"""
from __future__ import annotations

import locale
import platform
import time

# Deployed Cloudflare Worker endpoint. Fill in after you deploy the worker
# (cloudflare/telemetry-worker.js).  Until then telemetry simply no-ops.
ENDPOINT = "https://pcworkmantelemetry.firmuga-marcin-s.workers.dev"

_session_start = time.time()


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


def _resolve_version(app_version: str = "") -> str:
    """Use the caller's version, else read APP_VERSION from startup.py (tracks the
    real version in dev and frozen builds), else a safe fallback. Stops empty
    app_version="" payloads from the Settings 'send on enable' path."""
    if app_version:
        return app_version
    try:
        import os, re
        from utils.paths import BUNDLE_DIR
        with open(os.path.join(BUNDLE_DIR, "startup.py"), encoding="utf-8") as f:
            for line in f:
                m = re.match(r'\s*APP_VERSION\s*=\s*["\']([^"\']+)["\']', line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return "1.8.0"


def build_payload(app_version: str = "") -> dict:
    """The exact anonymous snapshot we would send. Safe to show the user verbatim."""
    from core import network

    payload = {
        "install_id":  network.get_install_id(),
        "app_version": _resolve_version(app_version),
        "ts":          int(time.time()),
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


def send(app_version: str = "") -> bool:
    """Send the snapshot if (and only if) the user opted in. Returns success.

    Runs a synchronous hardware scan first so the payload carries real specs even
    when the user never opened the My PC -> Components tab. Call off the UI thread
    (startup fires this from a daemon thread; Settings from 'telemetry-now')."""
    from core import network
    if not network.telemetry_enabled() or not ENDPOINT:
        return False
    try:
        from core.hardware_detector import get_hardware_detector
        get_hardware_detector().ensure_data()   # blocks here until specs are known
    except Exception:
        pass
    return network.post_json(ENDPOINT, build_payload(app_version))
