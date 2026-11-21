# core/fan_sensors.py
"""
The one source of fan readings (2026-11-14).

Until now the fan pages had no source at all. "FANS - Hardware Info" drew
random numbers under the title "Real-time fan monitoring" and listed cooler
models nobody owns; the usage charts were random walks; My PC printed two
hard-coded RPM values. Windows does not report fan speed to applications, so
the only honest reading is one a sensor driver gives us.

The rule this module exists to enforce:

    A fan speed on screen is a measurement, or it is not there.

`core.live_collector` reads fan RPM from the OpenHardwareMonitor /
LibreHardwareMonitor web server (the same request that already brings the
voltages) and hands every tick to `record()`. UI pages call `measured()` and
`history()`. When no sensor answers, both return nothing and the pages show
an empty state that says so.
"""
import threading
import time
from collections import deque

SAMPLE_INTERVAL_S = 5                 # history resolution
_HISTORY_SECONDS = 12 * 3600          # longest range the usage page offers
_MAXLEN = _HISTORY_SECONDS // SAMPLE_INTERVAL_S

_lock = threading.Lock()
_current: list = []                   # [{"name": str, "rpm": int}, ...]
_current_ts: float = 0.0
_source: str = ""                     # "" | "ohm" | "lhm"
_history: dict = {}                   # name -> deque[(ts, rpm)]
_last_sample: float = 0.0


def clean(raw) -> list:
    """Normalise a list of fan dicts: named, numeric, non-negative."""
    out = []
    for f in raw or []:
        try:
            name = str(f.get("name", "")).strip()
            rpm = int(float(f.get("rpm", -1)))
        except Exception:
            continue
        if name and rpm >= 0:
            out.append({"name": name, "rpm": rpm})
    return out


def record(fans, source: str = "", now: float = None) -> None:
    """Store one reading. Called by the live collector on every tick."""
    global _current, _current_ts, _source, _last_sample
    now = time.time() if now is None else now
    fans = clean(fans)
    with _lock:
        _current = fans
        _current_ts = now
        _source = source if fans else ""
        if fans and now - _last_sample >= SAMPLE_INTERVAL_S:
            _last_sample = now
            for f in fans:
                _history.setdefault(
                    f["name"], deque(maxlen=_MAXLEN)).append((now, f["rpm"]))


def measured(max_age: float = 15.0) -> list:
    """Fans measured right now. Empty when no sensor is answering, or when
    the last reading is older than *max_age* seconds (sensor went away)."""
    with _lock:
        if not _current or time.time() - _current_ts > max_age:
            return []
        return [dict(f) for f in _current]


def source() -> str:
    """Which daemon the readings come from: '', 'ohm' or 'lhm'."""
    with _lock:
        return _source


def source_label() -> str:
    return {"ohm": "OpenHardwareMonitor",
            "lhm": "LibreHardwareMonitor"}.get(source(), "")


def history(seconds: int) -> dict:
    """name -> [rpm, ...] for the last *seconds*, oldest first. Measured
    samples only; a fan with fewer than two samples is left out."""
    cutoff = time.time() - seconds
    with _lock:
        out = {}
        for name, dq in _history.items():
            pts = [rpm for ts, rpm in dq if ts >= cutoff]
            if len(pts) >= 2:
                out[name] = pts
        return out


def history_xy(seconds: int) -> dict:
    """Like history(), with time: name -> [(seconds_ago, rpm), ...]. Fans
    that appeared at different moments stay aligned on one time axis."""
    now = time.time()
    cutoff = now - seconds
    with _lock:
        out = {}
        for name, dq in _history.items():
            pts = [(now - ts, rpm) for ts, rpm in dq if ts >= cutoff]
            if len(pts) >= 2:
                out[name] = pts
        return out


def _reset_for_tests() -> None:
    global _current, _current_ts, _source, _last_sample
    with _lock:
        _current, _current_ts, _source, _last_sample = [], 0.0, "", 0.0
        _history.clear()
