"""
Live sensor data bridge
=======================
Updated by the Hey-USER refresh loop every 2 s.
Consumed by hck_GPT response builder, proactive monitor, etc.

Values are -1.0 / -1 / "" when data is unavailable (driver not present,
nvidia-smi not found, etc.).  Always check before using.
"""
import threading
import time as _time

_lock = threading.Lock()

# ── Canonical live sensor state ──────────────────────────────────────────────
LIVE: dict = {
    # CPU
    "cpu_load":    -1.0,   # %
    "cpu_temp":    -1.0,   # °C (estimated when no driver)
    "cpu_mhz":     -1.0,   # current clock MHz
    "cpu_boost":   -1.0,   # boost / max clock MHz (from profile)
    "cpu_power":   -1.0,   # W (estimated)
    "cpu_tdp":     -1.0,   # W TDP (from profile)
    "cpu_pl2":     -1.0,   # W PL2 (from profile)
    "cpu_cores_p": -1,     # physical cores
    "cpu_cores_l": -1,     # logical threads
    "cpu_name":    "",     # e.g. "Intel Core i7-12700K"
    # GPU
    "gpu_temp":    -1.0,   # °C
    "gpu_load":    -1.0,   # %
    "gpu_vram_pct":-1.0,   # %
    "gpu_vram_mb": -1.0,   # MB used
    "gpu_power":   -1.0,   # W
    "gpu_tdp":     -1.0,   # W
    "gpu_clk_gr":  -1.0,   # MHz core clock
    "gpu_clk_mem": -1.0,   # MHz memory clock
    "gpu_name":    "",
    "gpu_ok":      False,  # True when nvidia-smi returned valid data
    # Motherboard (real values available only with LHM/OHM running)
    "mb_volt_12v": -1.0,
    "mb_volt_5v":  -1.0,
    "mb_volt_33v": -1.0,
    "mb_temp_sys": -1.0,
    "mb_temp_vrm": -1.0,
    "mb_source":   "",     # "" | "ohm" | "lhm" - which daemon provided the data
    # Disk - keyed by mount point (e.g. "C:\\")
    # Each value: {"used_gb": float, "free_gb": float, "total_gb": float, "pct": float}
    "disks": {},
    # Session extremes (populated externally by _track_sensor in Hey-USER)
    "session_hist": {},    # key -> [min, max]
    # Meta
    "ts": 0.0,             # epoch timestamp of last full update
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def update(patch: dict) -> None:
    """Bulk-update LIVE from a dict.  Called from Tkinter main thread."""
    with _lock:
        for k, v in patch.items():
            LIVE[k] = v
        LIVE["ts"] = _time.time()


def snapshot() -> dict:
    """Return a shallow copy of LIVE.  Safe from any thread."""
    with _lock:
        d = dict(LIVE)
        d["disks"]        = {k: dict(v) for k, v in LIVE.get("disks", {}).items()}
        d["session_hist"] = {k: list(v) for k, v in LIVE.get("session_hist", {}).items()}
        return d


def get(key: str, default=None):
    """Read one key safely from any thread."""
    with _lock:
        return LIVE.get(key, default)


def is_fresh(max_age: float = 10.0) -> bool:
    """True if live data was updated within the last max_age seconds."""
    with _lock:
        return (_time.time() - LIVE["ts"]) < max_age


# ── Convenience accessors for hck_GPT ────────────────────────────────────────

def cpu_summary() -> dict:
    """Dict with the most relevant CPU fields (safe copy)."""
    keys = ("cpu_load", "cpu_temp", "cpu_mhz", "cpu_boost",
            "cpu_power", "cpu_pl2", "cpu_tdp", "cpu_name",
            "cpu_cores_p", "cpu_cores_l")
    with _lock:
        return {k: LIVE[k] for k in keys}


def gpu_summary() -> dict:
    keys = ("gpu_temp", "gpu_load", "gpu_vram_pct", "gpu_vram_mb",
            "gpu_power", "gpu_tdp", "gpu_clk_gr", "gpu_clk_mem",
            "gpu_name", "gpu_ok")
    with _lock:
        return {k: LIVE[k] for k in keys}


def disk_summary() -> dict:
    with _lock:
        return {k: dict(v) for k, v in LIVE.get("disks", {}).items()}


def mb_summary() -> dict:
    keys = ("mb_volt_12v", "mb_volt_5v", "mb_volt_33v",
            "mb_temp_sys", "mb_temp_vrm", "mb_source")
    with _lock:
        return {k: LIVE[k] for k in keys}
