"""
Network gate  -  PC Workman is OFFLINE by default.
==================================================
Every outbound connection in the whole app must go through `post_json()`, which
is a no-op unless the user has explicitly turned Network Access ON in Settings.
When the master switch is OFF the program makes ZERO network connections - the
user can verify that with a firewall or Wireshark.

State lives in settings/network.json (human-readable, easy to inspect):
    network_allowed   master switch (default False = full offline)
    telemetry_enabled anonymous opt-in telemetry (only meaningful if allowed)
    install_id        random anonymous UUID, generated once, no personal link
    consent_at        when the user first turned access on

No usernames, machine names, IPs or any personal data are stored here.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid

_lock = threading.Lock()

_DEFAULTS = {
    "network_allowed":   True,    # 1.8.0: telemetry on by default (INFO + TURN in Settings)
    "telemetry_enabled": True,
    "telemetry_touched": False,   # has the user flipped the switch at least once
    "install_id":        "",
    "consent_at":        "",
}


def _path() -> str:
    try:
        from utils.paths import APP_DIR
        base = APP_DIR
    except Exception:
        base = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base, "settings", "network.json")


def _load() -> dict:
    try:
        with open(_path(), encoding="utf-8") as f:
            d = json.load(f)
        return {**_DEFAULTS, **d} if isinstance(d, dict) else dict(_DEFAULTS)
    except Exception:
        return dict(_DEFAULTS)


def _save(d: dict) -> None:
    try:
        p = _path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass


# ── Public state ──────────────────────────────────────────────────────────────

def network_allowed() -> bool:
    """True only if the user turned the master Network Access switch ON."""
    return bool(_load().get("network_allowed", False))


def telemetry_enabled() -> bool:
    """True only if BOTH network access and telemetry are on."""
    d = _load()
    return bool(d.get("network_allowed") and d.get("telemetry_enabled"))


def get_state() -> dict:
    return _load()


def set_network(allowed: bool, telemetry: bool | None = None) -> None:
    """Set the master switch (and optionally telemetry). Turning access off also
    forces telemetry off."""
    with _lock:
        d = _load()
        d["network_allowed"] = bool(allowed)
        if telemetry is not None:
            d["telemetry_enabled"] = bool(telemetry)
        if not allowed:
            d["telemetry_enabled"] = False
        if allowed and not d.get("consent_at"):
            d["consent_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save(d)


def telemetry_touched() -> bool:
    """True once the user has flipped the telemetry switch at least once."""
    return bool(_load().get("telemetry_touched", False))


def set_touched() -> None:
    with _lock:
        d = _load()
        d["telemetry_touched"] = True
        _save(d)


def get_install_id() -> str:
    """Anonymous, random per-install id (created once). Not linked to anything."""
    with _lock:
        d = _load()
        if not d.get("install_id"):
            d["install_id"] = uuid.uuid4().hex
            _save(d)
        return d["install_id"]


# ── The single outbound gate ────────────────────────────────────────────────

def post_json(url: str, payload: dict, timeout: float = 6.0) -> bool:
    """POST `payload` as JSON. NO-OP (returns False) unless network is allowed.
    This is the only place in the app that opens an outbound connection."""
    if not network_allowed():
        return False
    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "PCWorkman"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False
