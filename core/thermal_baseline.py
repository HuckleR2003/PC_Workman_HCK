"""
Thermal Baseline Engine — PC Workman HCK
========================================
Learns CPU temperature natural ranges per workload context using Welford's
online algorithm (numerically stable incremental mean + variance).

WHY an online accumulator (and not a windowed re-scan)
------------------------------------------------------
Each rebuild folds ONLY the snapshots recorded since the last one into a
per-bucket running accumulator (count + mean + M2). Learning therefore
ACCUMULATES over the whole life of the install — the running stats persist
in JSON and survive even after the raw snapshots are pruned at 90 days. A
fixed "last N days" window can never know your long-term normal; this can.

WHY bucket by workload
----------------------
A plain mean±σ over "last 24 h" is broken if that day was heavy gaming: the
baseline shifts toward the hot values and real anomalies disappear. Bucketing
by workload keeps the "idle normal" stable even after 8 hours of gaming.

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
    data/cache/thermal_baseline.json  — per-bucket {n, mean, M2} + last_ts;
    auto-created, version-checked (a version bump discards the old format).
    sigma and the p5/p95 band are derived live from mean + M2.

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
    .training_status()             → dict for UI display
    .overall_training_pct()        → 0-100 int
    .rebuild(force=False)          → int new samples folded in
    .maybe_rebuild(min_interval_s) → async incremental fold if stale
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
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

# z-multiplier for the displayed normal band (≈ central 90%: p5 / p95)
_P_Z          = 1.645

# Valid temperature range (rejects sensor errors / cold-boot noise)
TEMP_MIN      = 10.0
TEMP_MAX      = 110.0

# v2: per-bucket Welford accumulator {n, mean, M2} + last_ts (was windowed batch)
VERSION       = 2


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
        self._rebuild_lock = threading.Lock()
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
        """Return the learned range for a workload bucket. Always returns safely.
        sigma and the p5/p95 band are derived live from the running mean + M2."""
        with self._lock:
            bd = dict(self._raw.get("buckets", {}).get(bucket, {}))
        n    = int(bd.get("n", 0))
        mean = float(bd.get("mean", 50.0))
        if n >= 2:
            var   = bd.get("M2", 0.0) / (n - 1)          # Bessel's correction
            sigma = math.sqrt(var) if var > 0 else 1.0
        else:
            sigma = 5.0
        return BaselineRange(
            bucket = bucket,
            n      = n,
            mean   = mean,
            sigma  = sigma,
            p5     = mean - _P_Z * sigma,
            p95    = mean + _P_Z * sigma,
        )

    def overall_training_pct(self) -> int:
        """0–100 % — rough overall training completeness across all buckets."""
        # Single lock acquisition for all buckets (avoids 5 separate lock/unlock cycles)
        with self._lock:
            raw_buckets = self._raw.get("buckets", {})
        total  = sum(raw_buckets.get(b, {}).get("n", 0) for b in BUCKETS)
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

    def format_for_chat(self, cpu_temp: float = 0.0,
                        cpu_load: float = 0.0,
                        gpu_load: float = 0.0,
                        lang: str = "en") -> str:
        """
        Return a chat-ready string with workload-aware temperature context.
        Used by hck_gpt/responses/builder.py.

        Parameters
        ----------
        cpu_temp : current CPU temperature in °C (0 = unknown)
        cpu_load : current CPU utilisation % (for bucket classification)
        gpu_load : current GPU utilisation % (for gaming detection)
        lang     : "en" | "pl"
        """
        bucket = self.classify(cpu_load, gpu_load)
        br     = self.get_range(bucket)

        # ── Not yet trained ──────────────────────────────────────────────────
        if not br.is_usable:
            if lang == "pl":
                return (
                    f"🌡 Uczę się Twojego systemu "
                    f"({br.training_level}: {br.n}/{T_CALIBRATED} próbek).\n"
                    "  Potrzebuję więcej danych by ocenić temperaturę w kontekście."
                )
            return (
                f"🌡 Still learning your system "
                f"({br.training_level}: {br.n}/{T_CALIBRATED} samples).\n"
                "  Need more data to evaluate temperature in workload context."
            )

        # ── Classification ───────────────────────────────────────────────────
        if cpu_temp > 0:
            classification = br.classify_temp(cpu_temp)
            context        = br.context_label(cpu_temp)
        else:
            classification = "unknown"
            context        = ""

        _icons = {"normal": "✓", "elevated": "⚠", "high": "🔴",
                  "critical": "🔴", "unknown": "·"}
        icon = _icons.get(classification, "·")

        if lang == "pl":
            _bucket_pl = {
                "idle": "bezczynność", "light": "lekki", "medium": "średni",
                "heavy": "intensywny", "gaming": "gaming",
            }
            bn = _bucket_pl.get(bucket, bucket)
            lines = [
                f"🌡 TEMPERATURA CPU  (tryb: {bn})",
                f"  {icon} {cpu_temp:.1f}°C — {classification}" if cpu_temp else
                "  Brak odczytu temperatury",
                f"  Zakres normalny: {br.p5:.0f}–{br.p95:.0f}°C "
                f"(σ={br.sigma:.1f}°C)",
            ]
            if context:
                lines.append(f"  {context}")
            lines.append(
                f"\n  Kalibracja: {br.training_level} "
                f"({br.n}/{T_CALIBRATED} próbek)"
            )
        else:
            lines = [
                f"🌡 CPU TEMPERATURE  (workload: {bucket})",
                f"  {icon} {cpu_temp:.1f}°C — {classification}" if cpu_temp else
                "  No temperature reading",
                f"  Normal range: {br.p5:.0f}–{br.p95:.0f}°C "
                f"(σ={br.sigma:.1f}°C)",
            ]
            if context:
                lines.append(f"  {context}")
            lines.append(
                f"\n  Calibration: {br.training_level} "
                f"({br.n}/{T_CALIBRATED} samples)"
            )

        return "\n".join(lines)

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

    @staticmethod
    def _welford_add(acc: dict, x: float) -> None:
        """Fold one sample into a running accumulator (Welford 1962)."""
        n     = acc["n"] + 1
        delta = x - acc["mean"]
        mean  = acc["mean"] + delta / n
        acc["n"]    = n
        acc["mean"] = mean
        acc["M2"]   = acc["M2"] + delta * (x - mean)

    def rebuild(self, force: bool = False) -> int:
        """
        Fold any new DeepMonitor snapshots into the per-bucket Welford
        accumulators (running n + mean + M2). Only rows newer than the last
        processed timestamp are read, so learning ACCUMULATES across the whole
        life of the install — never recomputed from a fixed window, and it
        survives even after the raw rows are pruned at 90 days.

        Returns the number of new valid samples folded in this pass. Throttled
        to once per 5 min unless force=True. Concurrent calls are skipped (the
        first wins) so the accumulators are never double-counted.
        """
        if not force and (time.time() - self._last_rebuild < 300):
            return 0
        if not self._rebuild_lock.acquire(blocking=False):
            return 0
        try:
            with self._lock:
                last_ts = float(self._raw.get("last_ts", 0.0) or 0.0)
                buckets = {
                    b: dict(self._raw.get("buckets", {}).get(
                        b, {"n": 0, "mean": 0.0, "M2": 0.0}))
                    for b in BUCKETS
                }

            rows = self._query_db_since(last_ts)
            if not rows:
                self._last_rebuild = time.time()
                return 0

            max_ts    = last_ts
            processed = 0
            for row in rows:
                ts = float(row.get("ts", 0.0) or 0.0)
                if ts > max_ts:
                    max_ts = ts
                cpu_t = float(row.get("cpu_temp", -1.0) or -1.0)
                if cpu_t < TEMP_MIN or cpu_t > TEMP_MAX:
                    continue   # reject invalid / estimated-before-data readings
                cpu_l = float(row.get("cpu_load", 0.0) or 0.0)
                gpu_l = float(row.get("gpu_load", 0.0) or 0.0)
                self._welford_add(buckets[self.classify(cpu_l, gpu_l)], cpu_t)
                processed += 1

            with self._lock:
                self._raw["buckets"]     = buckets
                self._raw["last_ts"]     = max_ts
                self._raw["last_update"] = time.time()
                self._raw["version"]     = VERSION
                self._last_rebuild       = time.time()

            self._save_json()
            return processed
        finally:
            self._rebuild_lock.release()

    def maybe_rebuild(self, min_interval_s: float = 300.0) -> None:
        """Trigger an async incremental fold only if older than min_interval_s."""
        if time.time() - self._last_rebuild > min_interval_s:
            threading.Thread(
                target=self.rebuild,
                daemon=True,
                name="ThermalBaselineRebuild",
            ).start()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _query_db_since(self, last_ts: float) -> list[dict]:
        """Load ts/cpu_temp/cpu_load/gpu_load for snapshots newer than last_ts."""
        try:
            con = sqlite3.connect(_DB_PATH, timeout=5)
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT ts, cpu_temp, cpu_load, gpu_load "
                "FROM deepmonitor_snapshots "
                "WHERE ts > ? AND cpu_temp > 0 "
                "ORDER BY ts",
                (last_ts,),
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
            "last_ts":     0.0,
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
