"""
core/opt_receipts.py - Optimization Receipts (2026-07).

Every optimizer on the market says "your PC is faster now". PC Workman
shows the receipt: a BEFORE snapshot at the moment an action fires and an
AFTER snapshot ~20 seconds later, side by side, kept in a small local log.

    record("RAM Flush")   <- called by the action itself (one line)
    get_receipts()        -> newest-first list of receipt dicts

Design constraints (why this is safe):
  - read-only consumers: live_sensors snapshot + psutil fallback
  - the AFTER capture runs on a daemon threading.Timer - if the app closes
    first, the receipt simply stays marked as still measuring
  - JSON persistence in APP_DIR/data/cache (writable in frozen/MSIX builds),
    capped at the newest 20 entries
  - every path is defensive: a failed receipt must NEVER break the action
    that triggered it
"""

import json
import os
import threading
import time

_AFTER_DELAY_S = 20.0
_MAX_ENTRIES   = 20

_lock = threading.Lock()


def _store_path() -> str:
    try:
        from utils.paths import APP_DIR
        base = APP_DIR
    except Exception:
        base = os.path.abspath(".")
    d = os.path.join(base, "data", "cache")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "opt_receipts.json")


def _metrics() -> dict:
    """Small comparable snapshot: RAM %, CPU %, CPU temp (when real)."""
    out = {"ram_pct": -1.0, "cpu_load": -1.0, "cpu_temp": -1.0}
    try:
        from hck_gpt.data import live_sensors
        s = live_sensors.snapshot() or {}
        out["cpu_load"] = float(s.get("cpu_load", -1) or -1)
        out["cpu_temp"] = float(s.get("cpu_temp", -1) or -1)
    except Exception:
        pass
    try:
        import psutil
        out["ram_pct"] = float(psutil.virtual_memory().percent)
        if out["cpu_load"] < 0:
            out["cpu_load"] = float(psutil.cpu_percent(interval=None))
    except Exception:
        pass
    return out


def _load() -> list:
    try:
        with open(_store_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(entries: list) -> None:
    try:
        with open(_store_path(), "w", encoding="utf-8") as f:
            json.dump(entries[-_MAX_ENTRIES:], f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def record(action: str) -> None:
    """Open a receipt for `action`: BEFORE now, AFTER in ~20 s. Never raises."""
    try:
        entry = {
            "ts":     time.time(),
            "action": str(action)[:48],
            "before": _metrics(),
            "after":  None,
        }
        with _lock:
            entries = _load()
            entries.append(entry)
            _save(entries)
        ts = entry["ts"]

        def _capture_after():
            try:
                after = _metrics()
                with _lock:
                    items = _load()
                    for e in reversed(items):
                        if abs(float(e.get("ts", 0)) - ts) < 0.5 and e.get("after") is None:
                            e["after"] = after
                            break
                    _save(items)
            except Exception:
                pass

        t = threading.Timer(_AFTER_DELAY_S, _capture_after)
        t.daemon = True
        t.start()
    except Exception:
        pass


def get_receipts() -> list:
    """Newest-first receipts (list of dicts). Never raises."""
    try:
        with _lock:
            return list(reversed(_load()))
    except Exception:
        return []
