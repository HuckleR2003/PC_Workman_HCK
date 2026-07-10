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
    # Single source of truth: utils.paths is MSIX-aware (Store installs are
    # read-only next to the exe -> APP_DIR = %LOCALAPPDATA%\PC_Workman_HCK).
    try:
        from utils.paths import APP_DIR
        return APP_DIR
    except Exception:
        pass
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

# ── Learned metrics ───────────────────────────────────────────────────────────
# v3: learn EVERY real signal per workload bucket, not just CPU temperature.
# Why: cpu_temp needs LibreHardwareMonitor (most users don't run it) — before
# this, those machines learned nothing and the Learning Center sat at 0% forever.
# gpu_temp (nvidia-smi) and cpu_load (psutil) are real on virtually every
# machine, so learning is now visibly accumulating for everyone. The engine
# picks a "primary" metric (best real signal available) for headline display
# and chat, in priority order below.
_METRICS = {
    "cpu_temp": {"lo": TEMP_MIN, "hi": TEMP_MAX, "unit": "°C",
                 "en": "CPU temp",  "pl": "temp. CPU"},
    "gpu_temp": {"lo": TEMP_MIN, "hi": TEMP_MAX, "unit": "°C",
                 "en": "GPU temp",  "pl": "temp. GPU"},
    "cpu_load": {"lo": 0.0,      "hi": 100.0,    "unit": "%",
                 "en": "CPU load",  "pl": "obc. CPU"},
}
_METRIC_PRIORITY = ("cpu_temp", "gpu_temp", "cpu_load")

# v3: per-bucket, PER-METRIC Welford accumulators {n, mean, M2} + last_ts.
# A version bump discards the old single-metric JSON; rebuild() re-folds the
# whole DeepMonitor history (rows survive up to the retention window), so no
# learning is permanently lost - it re-accumulates on the next rebuild.
VERSION       = 3


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

    def get_range(self, bucket: str, metric: str = "cpu_temp") -> BaselineRange:
        """Learned range for one (bucket, metric). Always returns safely.
        sigma and the p5/p95 band are derived live from the running mean + M2.
        Default metric = cpu_temp keeps every existing caller working."""
        with self._lock:
            bd = dict(self._raw.get("buckets", {}).get(bucket, {}).get(metric, {}))
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

    def _metric_total(self, metric: str) -> int:
        with self._lock:
            bkts = self._raw.get("buckets", {})
            return sum(int(bkts.get(b, {}).get(metric, {}).get("n", 0))
                       for b in BUCKETS)

    def primary_metric(self) -> str:
        """The best real signal this machine actually produces, in priority
        order cpu_temp -> gpu_temp -> cpu_load. cpu_load is the guaranteed
        fallback (always real), so the Learning Center is never empty."""
        for m in _METRIC_PRIORITY:
            if self._metric_total(m) >= T_INIT:
                return m
        return "cpu_load"

    def metric_unit(self, metric: str) -> str:
        return _METRICS.get(metric, {}).get("unit", "")

    def metric_label(self, metric: str, lang: str = "en") -> str:
        cfg = _METRICS.get(metric, {})
        return cfg.get(lang, cfg.get("en", metric))

    def available_metrics(self) -> list:
        """Metrics that have any learned data (for honest UI hints)."""
        return [m for m in _METRIC_PRIORITY if self._metric_total(m) > 0]

    def classify_temp(self, temp: float, metric: str = None,
                      cpu_load: float = None, gpu_load: float = None) -> str:
        """Engine-level 'normal|elevated|high|critical' for a live reading,
        judged against the learned range. Picks the workload bucket from load
        when given, else the best-learned bucket for the metric. (The heavy
        lifting lives on BaselineRange; this is the convenience entry point
        callers like the hck_GPT 'hottest component' handler expect.)"""
        metric = metric or self.primary_metric()
        if cpu_load is not None:
            bucket = self.classify(cpu_load, gpu_load or 0.0)
        else:
            bucket = max(BUCKETS, key=lambda b: self.get_range(b, metric).n)
        br = self.get_range(bucket, metric)
        return br.classify_temp(temp) if br.is_usable else "unknown"

    def overall_training_pct(self, metric: str = None) -> int:
        """0–100 % overall training completeness for the primary (or given)
        metric across all buckets. Uses the primary metric so it reflects
        whatever this machine can actually learn."""
        metric = metric or self.primary_metric()
        total  = self._metric_total(metric)
        target = len(BUCKETS) * T_CALIBRATED
        return min(100, int(total / target * 100)) if target else 0

    def training_status(self, metric: str = None) -> dict[str, dict]:
        """
        Per-bucket training summary for the primary (or given) metric:
            { "idle": {"level": "trained", "n": 72, "mean": 36.4, …}, … }
        Defaults to the primary metric so the Learning Center is populated on
        every machine (cpu_load always has data, gpu_temp on NVIDIA, etc.).
        """
        metric = metric or self.primary_metric()
        result = {}
        for b in BUCKETS:
            r = self.get_range(b, metric)
            result[b] = {
                "level":        r.training_level,
                "training_pct": r.training_pct,
                "n":            r.n,
                "mean":         r.mean,
                "sigma":        r.sigma,
                "p5":           r.p5,
                "p95":          r.p95,
            }
        return result

    def format_for_chat(self, cpu_temp: float = 0.0,
                        cpu_load: float = 0.0,
                        gpu_load: float = 0.0,
                        lang: str = "en",
                        gpu_temp: float = -1.0) -> str:
        """
        Chat-ready, workload-aware verdict. Reports the best REAL signal this
        machine produces right now: CPU temp when a sensor exists, otherwise
        GPU temp (nvidia-smi), so the answer is grounded on every machine
        instead of stalling when LibreHardwareMonitor isn't running.
        Used by hck_gpt/responses/builder.py.
        """
        _PL = lang == "pl"
        bucket = self.classify(cpu_load, gpu_load)
        _bucket_pl = {"idle": "bezczynność", "light": "lekki", "medium": "średni",
                      "heavy": "intensywny", "gaming": "gaming"}
        bn = _bucket_pl.get(bucket, bucket) if _PL else bucket

        # pick the reported metric: a real current reading, priority CPU->GPU
        reading = None
        for m, v in (("cpu_temp", cpu_temp), ("gpu_temp", gpu_temp)):
            if v is not None and v > 0:
                reading = (m, float(v))
                break

        if reading is None:
            # No live temperature at all - report progress on the primary metric
            pm = self.primary_metric()
            br = self.get_range(bucket, pm)
            lbl = self.metric_label(pm, lang)
            if _PL:
                return (f"🌡 Uczę się Twojego systemu przez {lbl} "
                        f"({br.training_level}: {br.n}/{T_CALIBRATED} próbek, tryb: {bn}).\n"
                        "  Brak żywego odczytu temperatury (uruchom LibreHardwareMonitor, "
                        "by odblokować temperaturę CPU).")
            return (f"🌡 Learning your system via {lbl} "
                    f"({br.training_level}: {br.n}/{T_CALIBRATED} samples, workload: {bn}).\n"
                    "  No live temperature reading (run LibreHardwareMonitor to unlock CPU temp).")

        metric, value = reading
        br   = self.get_range(bucket, metric)
        unit = self.metric_unit(metric)
        head = self.metric_label(metric, lang).upper()

        if not br.is_usable:
            if _PL:
                return (f"🌡 {value:.0f}{unit} ({head}, tryb: {bn}) - jeszcze się uczę "
                        f"Twojej normy ({br.training_level}: {br.n}/{T_CALIBRATED} próbek).")
            return (f"🌡 {value:.0f}{unit} ({head}, workload: {bn}) - still learning "
                    f"your normal ({br.training_level}: {br.n}/{T_CALIBRATED} samples).")

        classification = br.classify_temp(value)
        _icons = {"normal": "✓", "elevated": "⚠", "high": "🔴", "critical": "🔴"}
        icon = _icons.get(classification, "·")
        context = br.context_label(value)

        if _PL:
            lines = [f"🌡 {head}  (tryb: {bn})",
                     f"  {icon} {value:.1f}{unit} — {classification}",
                     f"  Zakres normalny: {br.p5:.0f}–{br.p95:.0f}{unit} (σ={br.sigma:.1f}{unit})"]
            if context:
                lines.append(f"  {context}")
            lines.append(f"\n  Kalibracja: {br.training_level} "
                         f"({br.n}/{T_CALIBRATED} próbek, nauczone z Twoich danych)")
        else:
            lines = [f"🌡 {head}  (workload: {bn})",
                     f"  {icon} {value:.1f}{unit} — {classification}",
                     f"  Normal range: {br.p5:.0f}–{br.p95:.0f}{unit} (σ={br.sigma:.1f}{unit})"]
            if context:
                lines.append(f"  {context}")
            lines.append(f"\n  Calibration: {br.training_level} "
                         f"({br.n}/{T_CALIBRATED} samples, learned from your own data)")
        return "\n".join(lines)

    # Each DeepMonitor snapshot = one sample; metrics_store writes one every
    # 5 minutes, so N samples ≈ N × 5 min of your machine actually observed.
    SAMPLE_INTERVAL_MIN = 5.0

    def total_observed_hours(self, metric: str = None) -> float:
        """Rough hours of real machine time behind the learning (primary metric)."""
        metric = metric or self.primary_metric()
        return self._metric_total(metric) * self.SAMPLE_INTERVAL_MIN / 60.0

    def observed_hours(self, bucket: str, metric: str = None) -> float:
        metric = metric or self.primary_metric()
        return self.get_range(bucket, metric).n * self.SAMPLE_INTERVAL_MIN / 60.0

    def learning_since_str(self, lang: str = "en") -> str:
        """How long PC Workman has been observing this machine, e.g. '3 days'."""
        ts = float(self._raw.get("started_ts", 0.0) or 0.0)
        if not ts:
            # reads cleanly after "Uczę się od {x}" / "Learning for {x}"
            return "niedawna" if lang == "pl" else "a short while"
        delta = time.time() - ts
        if delta < 3600:
            v = max(1, int(delta / 60));  return f"{v} min"
        if delta < 86400:
            v = int(delta / 3600);        return f"{v} h"
        v = int(delta / 86400)
        if lang == "pl":
            return f"{v} {'dzień' if v == 1 else 'dni'}"
        return f"{v} {'day' if v == 1 else 'days'}"

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
                # buckets[bucket][metric] = {n, mean, M2}
                buckets = {}
                for b in BUCKETS:
                    src = self._raw.get("buckets", {}).get(b, {})
                    buckets[b] = {
                        m: dict(src.get(m, {"n": 0, "mean": 0.0, "M2": 0.0}))
                        for m in _METRICS
                    }

            rows = self._query_db_since(last_ts)
            if not rows:
                self._last_rebuild = time.time()
                return 0

            max_ts    = last_ts
            min_ts    = 0.0
            processed = 0
            for row in rows:
                ts = float(row.get("ts", 0.0) or 0.0)
                if ts > max_ts:
                    max_ts = ts
                if ts > 0 and (min_ts == 0.0 or ts < min_ts):
                    min_ts = ts
                cpu_l  = float(row.get("cpu_load", -1.0) or -1.0)
                gpu_l  = float(row.get("gpu_load", -1.0) or -1.0)
                bucket = self.classify(max(cpu_l, 0.0), max(gpu_l, 0.0))
                folded = False
                for m, cfg in _METRICS.items():
                    v = float(row.get(m, -1.0) or -1.0)
                    if v < cfg["lo"] or v > cfg["hi"]:
                        continue   # metric absent/invalid this row - skip it only
                    self._welford_add(buckets[bucket][m], v)
                    folded = True
                if folded:
                    processed += 1

            with self._lock:
                self._raw["buckets"]     = buckets
                self._raw["last_ts"]     = max_ts
                self._raw["last_update"] = time.time()
                self._raw["version"]     = VERSION
                # when did we first start observing this machine? (earliest
                # snapshot ever folded — powers the "learning for X days" counter)
                if processed and not self._raw.get("started_ts") and min_ts:
                    self._raw["started_ts"] = min_ts
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
        """Load every learnable signal for snapshots newer than last_ts.
        No cpu_temp filter: we fold whatever is real per row (gpu_temp/cpu_load
        exist even when cpu_temp is absent), each metric gated on its own."""
        try:
            con = sqlite3.connect(_DB_PATH, timeout=5)
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT ts, cpu_temp, gpu_temp, cpu_load, gpu_load "
                "FROM deepmonitor_snapshots "
                "WHERE ts > ? "
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
