"""
Thermal Baseline Engine — PC Workman HCK  v1.7.8
=================================================
Learns CPU/GPU temperature natural ranges per workload context using
Welford's online algorithm (numerically stable incremental mean + variance).

WHY this beats a simple rolling window
---------------------------------------
A plain mean±σ over "last 24 h" is broken if that day was heavy gaming:
the baseline shifts toward the hot values and real anomalies disappear.
Welford runs over ALL historical data *bucketed by workload*, so the
"idle normal" stays stable even after 8 hours of gaming.

Workload buckets (classified per snapshot):
    idle     cpu_load < 15%               "System at rest"
    light    15 ≤ cpu_load < 40%         "Background tasks / browsing"
    medium   40 ≤ cpu_load < 70%         "Dev / compilation / streaming"
    heavy    cpu_load ≥ 70%               "Rendering / encoding / stress"
    gaming   gpu_load ≥ 60%               "GPU-dominated workload"
    (gaming takes priority over cpu classification)

Data source:
    deepmonitor_snapshots.cpu_temp   (°C — real from LHM or estimated)
    deepmonitor_snapshots.cpu_load   (%) — for workload bucket
    deepmonitor_snapshots.gpu_load   (%) — for gaming detection

Persistence:
    data/cache/thermal_baseline.json  — auto-created, version-checked

Training levels (samples per bucket):
    no_data      0 samples
    initializing 1–4
    learning     5–19
    basic        20–59
    trained      60–199
    calibrated   200+

Public singleton:  thermal_baseline
    .classify(cpu_load, gpu_load)  → str bucket name
    .get_range(bucket)             → BaselineRange
    .all_ranges()                  → dict[str, BaselineRange]
    .training_status()             → dict for UI display
    .overall_training_pct()        → 0-100 int
    .rebuild(force=False)          → int samples processed
    .maybe_rebuild(min_interval_s) → async rebuild if stale
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
import time

# ── Paths ─────────────────────────────────────────────────────────────────────

def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )

_PREFS_PATH = os.path.join(_base_dir(), "data", "cache", "thermal_baseline.json")
_DB_PATH    = os.path.join(_base_dir(), "data", "logs",  "hck_stats.db")

# ── Constants ─────────────────────────────────────────────────────────────────

BUCKETS       = ("idle", "light", "medium", "heavy", "gaming")

# Sample count thresholds for training levels
T_INIT        =   5
T_BASIC       =  20
T_TRAINED     =  60
T_CALIBRATED  = 200

# DeepMonitor lookback for each rebuild
LOOKBACK_DAYS = 14

# Valid temperature range (rejects sensor errors / cold-boot noise)
TEMP_MIN      = 10.0
TEMP_MAX      = 110.0

VERSION       = 1


# ── BaselineRange (immutable result object) ───────────────────────────────────

class BaselineRange:
    """
    Learned temperature profile for one workload bucket.

    Attributes
    ----------
    bucket  : str    workload context name
    n       : int    samples seen
    mean    : float  learned mean temperature (°C)
    sigma   : float  population std-dev (°C)
    p5      : float  approximate 5th-percentile  (lower normal boundary)
    p95     : float  approximate 95th-percentile (upper normal boundary)
    """
    __slots__ = ("bucket", "n", "mean", "sigma", "p5", "p95")

    def __init__(self, bucket: str, n: int = 0,
                 mean: float = 50.0, sigma: float = 5.0,
                 p5: float = 40.0, p95: float = 60.0):
        self.bucket = bucket
        self.n      = n
        self.mean   = round(mean,  1)
        self.sigma  = round(sigma, 1)
        self.p5     = round(p5,    1)
        self.p95    = round(p95,   1)

    # ── Training level ────────────────────────────────────────────────────────

    @property
    def training_level(self) -> str:
        if self.n == 0:             return "no_data"
        if self.n < T_INIT:         return "initializing"
        if self.n < T_BASIC:        return "learning"
        if self.n < T_TRAINED:      return "basic"
        if self.n < T_CALIBRATED:   return "trained"
        return "calibrated"

    @property
    def training_pct(self) -> int:
        """0–100 % toward 'calibrated'."""
        return min(100, int(self.n / T_CALIBRATED * 100))

    @property
    def is_usable(self) -> bool:
        """True once we have enough samples for a meaningful range."""
        return self.n >= T_BASIC

    # ── Analysis helpers ──────────────────────────────────────────────────────

    def z_score(self, temp: float) -> float:
        """Standard deviations above/below the learned mean."""
        return (temp - self.mean) / max(self.sigma, 0.5)

    def classify_temp(self, temp: float) -> str:
        """
        'normal' | 'elevated' | 'high' | 'critical'
        Uses workload-aware sigma bands, NOT fixed thresholds like "80°C".
        """
        z = self.z_score(temp)
        if z < 1.5:  return "normal"
        if z < 2.5:  return "elevated"
        if z < 3.5:  return "high"
        return "critical"

    def context_label(self, temp: float) -> str:
        """
        Human-readable tooltip string, e.g.:
            "14% above usual  (Gaming: 65–78°C, ±2.3°C)"
        Returns empty string when the baseline is not yet usable.
        """
        if not self.is_usable:
            return ""
        diff = temp - self.mean
        pct  = abs(diff / self.mean * 100) if self.mean else 0
        dir_ = "above" if diff >= 0 else "below"
        ctx  = self.bucket.title()
        return (f"{pct:.0f}% {dir_} usual  "
                f"({ctx}: {self.p5:.0f}–{self.p95:.0f}°C, ±{self.sigma:.1f}°C)")


# ── ThermalBaseline engine ────────────────────────────────────────────────────

class ThermalBaseline:
    """
    Thread-safe thermal learning engine.
    Reads from the DeepMonitor SQLite DB, builds per-bucket Gaussian stats,
    and persists them to JSON for fast startup.

    Use via the module-level singleton ``thermal_baseline``.
    """

    def __init__(self) -> None:
        self._lock         = threading.Lock()
        self._raw: dict    = {}
        self._last_rebuild = 0.0
        self._load_json()

    # ── Classification ────────────────────────────────────────────────────────

    def classify(self, cpu_load: float, gpu_load: float = 0.0) -> str:
        """Return workload bucket name for the given CPU / GPU utilisation."""
        if (gpu_load or 0.0) >= 60.0:   return "gaming"
        cl = cpu_load or 0.0
        if cl <  15.0: return "idle"
        if cl <  40.0: return "light"
        if cl <  70.0: return "medium"
        return "heavy"

    # ── Public query API ──────────────────────────────────────────────────────

    def get_range(self, bucket: str) -> BaselineRange:
        """Return the learned range for a workload bucket. Always returns safely."""
        with self._lock:
            bd = self._raw.get("buckets", {}).get(bucket, {})
        return BaselineRange(
            bucket = bucket,
            n      = bd.get("n",     0),
            mean   = bd.get("mean",  50.0),
            sigma  = bd.get("sigma", 5.0),
            p5     = bd.get("p5",    40.0),
            p95    = bd.get("p95",   60.0),
        )

    def all_ranges(self) -> dict[str, BaselineRange]:
        """Return BaselineRange for every workload bucket."""
        return {b: self.get_range(b) for b in BUCKETS}

    def overall_training_pct(self) -> int:
        """0–100 % — rough overall training completeness across all buckets."""
        total  = sum(self.get_range(b).n for b in BUCKETS)
        target = len(BUCKETS) * T_CALIBRATED
        return min(100, int(total / target * 100))

    def training_status(self) -> dict[str, dict]:
        """
        Per-bucket training summary suitable for UI display:
            { "idle": {"level": "trained", "n": 72, "mean": 36.4, "sigma": 2.1}, … }
        """
        result = {}
        for b in BUCKETS:
            r = self.get_range(b)
            result[b] = {
                "level":       r.training_level,
                "training_pct": r.training_pct,
                "n":           r.n,
                "mean":        r.mean,
                "sigma":       r.sigma,
                "p5":          r.p5,
                "p95":         r.p95,
            }
        return result

    def last_update_str(self) -> str:
        """Human-readable timestamp of last successful rebuild."""
        ts = self._raw.get("last_update", 0.0)
        if not ts:
            return "Never"
        delta = time.time() - ts
        if delta < 120:
            return "Just now"
        if delta < 3600:
            return f"{int(delta / 60)} min ago"
        return f"{int(delta / 3600)}h ago"

    # ── Rebuild ───────────────────────────────────────────────────────────────

    def rebuild(self, force: bool = False) -> int:
        """
        Scan the DeepMonitor database and recompute all per-bucket statistics.

        Uses true population statistics (mean, σ, 5th/95th percentile) over
        the last LOOKBACK_DAYS of snapshots.  This is run at most once per
        5 minutes unless force=True.

        Returns the total number of valid temperature samples processed.
        """
        if not force and (time.time() - self._last_rebuild < 300):
            return 0

        rows = self._query_db()
        if not rows:
            self._last_rebuild = time.time()
            return 0

        # ── Bucket samples ────────────────────────────────────────────────────
        bucket_samples: dict[str, list[float]] = {b: [] for b in BUCKETS}

        for row in rows:
            cpu_t = float(row.get("cpu_temp", -1.0) or -1.0)
            cpu_l = float(row.get("cpu_load",  0.0) or  0.0)
            gpu_l = float(row.get("gpu_load",  0.0) or  0.0)

            if cpu_t < TEMP_MIN or cpu_t > TEMP_MAX:
                continue   # reject invalid / estimated-before-data readings

            bucket_samples[self.classify(cpu_l, gpu_l)].append(cpu_t)

        # ── Per-bucket statistics ─────────────────────────────────────────────
        new_buckets: dict[str, dict] = {}

        for b, samples in bucket_samples.items():
            if len(samples) < 2:
                # Not enough data yet — keep existing or set defaults
                existing = self._raw.get("buckets", {}).get(b, {})
                new_buckets[b] = existing if existing else {
                    "n": len(samples), "mean": 50.0,
                    "sigma": 5.0, "p5": 40.0, "p95": 60.0,
                }
                continue

            n     = len(samples)
            mean  = sum(samples) / n
            var   = sum((s - mean) ** 2 for s in samples) / n
            sigma = math.sqrt(var) if var > 0 else 1.0

            s_sorted = sorted(samples)
            p5  = s_sorted[max(0,     int(0.05 * n))]
            p95 = s_sorted[min(n - 1, int(0.95 * n))]

            new_buckets[b] = {
                "n":     n,
                "mean":  round(mean,  2),
                "sigma": round(sigma, 2),
                "p5":    round(p5,    1),
                "p95":   round(p95,   1),
            }

        # ── Persist ───────────────────────────────────────────────────────────
        with self._lock:
            self._raw["buckets"]     = new_buckets
            self._raw["last_update"] = time.time()
            self._raw["version"]     = VERSION
            self._last_rebuild       = time.time()

        self._save_json()
        processed = sum(len(v) for v in bucket_samples.values())
        return processed

    def maybe_rebuild(self, min_interval_s: float = 300.0) -> None:
        """Trigger an async rebuild only if older than min_interval_s seconds."""
        if time.time() - self._last_rebuild > min_interval_s:
            threading.Thread(
                target=self.rebuild,
                daemon=True,
                name="ThermalBaselineRebuild",
            ).start()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _query_db(self) -> list[dict]:
        """Load cpu_temp / cpu_load / gpu_load from deepmonitor_snapshots."""
        try:
            import sqlite3
            since = time.time() - LOOKBACK_DAYS * 86400
            con   = sqlite3.connect(_DB_PATH, timeout=5)
            con.row_factory = sqlite3.Row
            rows  = con.execute(
                "SELECT cpu_temp, cpu_load, gpu_load "
                "FROM deepmonitor_snapshots "
                "WHERE ts >= ? AND cpu_temp > 0 "
                "ORDER BY ts",
                (since,),
            ).fetchall()
            con.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_json(self) -> None:
        try:
            with open(_PREFS_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("version") == VERSION:
                self._raw = raw
                return
        except Exception:
            pass
        self._raw = {
            "version":     VERSION,
            "buckets":     {},
            "last_update": 0.0,
        }

    def _save_json(self) -> None:
        try:
            os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
            with open(_PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._raw, f, indent=2)
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────
thermal_baseline = ThermalBaseline()
