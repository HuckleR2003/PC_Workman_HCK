"""
Voltage Rail Analyzer — PC Workman HCK  v1.7.8
===============================================
Applies Statistical Process Control (SPC) to motherboard voltage rails
to distinguish natural noise from genuine anomalies.

WHY Median + MAD instead of Mean + σ
--------------------------------------
A voltage spike shifts the mean toward itself, causing the calculated
"normal band" to widen.  Future spikes then fall inside the (now-wider)
band and are silently missed.  Median is completely unaffected by a
small number of extreme values, and MAD (Median Absolute Deviation)
inherits that robustness.

    Modified z-score  (Iglewicz & Hoaglin, 1993):
        M_i  =  0.6745 × (x_i − median) / MAD
    → |M| > 3.5  :  anomaly   (< 0.03 % probability under Gaussian noise)
    → |M| > 2.5  :  warning   (worth watching)

Context suppression — 12 V rail:
    During GPU load transitions (|Δgpu_load| > 25 % in one 5-min step)
    a 12 V transient is physically expected and is downgraded to "info"
    rather than "warning/critical".

Anomaly decay:
    If a spike of the same magnitude (±30 % tolerance) recurs ≥ 5 times
    in the tracked window it is treated as "your hardware's normal" and
    its severity is reduced by one tier.

Rails monitored:
    12 V  — ATX spec ±5 %  → [11.40 V, 12.60 V]
     5 V  — ATX spec ±5 %  → [ 4.75 V,  5.25 V]
     3.3V — ATX spec ±5 %  → [ 3.14 V,  3.47 V]

Data availability:
    Requires LibreHardwareMonitor (LHM) or OpenHardwareMonitor (OHM).
    All mb_volt_* columns are −1.0 when neither is running.
    `is_data_available()` returns False in that case.

Public singleton:  voltage_analyzer
    .is_data_available()            → bool
    .get_rail_stats()               → dict[str, RailStats]
    .analyze_history(hours)         → (timeline, events)
    .rebuild(force=False)           → bool
    .maybe_rebuild(min_interval_s)  → async rebuild if stale
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
import threading
import time
from dataclasses import dataclass, field

# ── Paths ─────────────────────────────────────────────────────────────────────

def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
    )

_DB_PATH    = os.path.join(_base_dir(), "data", "logs",  "hck_stats.db")
_PREFS_PATH = os.path.join(_base_dir(), "data", "cache", "voltage_baseline.json")

VERSION = 2

# ── Rail metadata ─────────────────────────────────────────────────────────────

RAILS: dict[str, dict] = {
    "mb_volt_12v": {
        "label":   "12V",
        "nominal": 12.000,
        "atx_lo":  11.400,   # −5 %
        "atx_hi":  12.600,   # +5 %
        "color":   "#f59e0b",
        "unit":    "V",
    },
    "mb_volt_5v": {
        "label":   "5V",
        "nominal": 5.000,
        "atx_lo":  4.750,
        "atx_hi":  5.250,
        "color":   "#3b82f6",
        "unit":    "V",
    },
    "mb_volt_33v": {
        "label":   "3.3V",
        "nominal": 3.300,
        "atx_lo":  3.135,
        "atx_hi":  3.465,
        "color":   "#10b981",
        "unit":    "V",
    },
}

# Iglewicz-Hoaglin consistency factor
_K = 1.4826

# Modified z-score anomaly thresholds
Z_ANOMALY = 3.5
Z_WARNING = 2.5
Z_WATCH   = 1.5

# Anomaly decay: spike recurs this many times → it is "your normal"
DECAY_REPEAT_THRESH = 5


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RailStats:
    """Learned statistical baseline for one voltage rail."""
    rail:          str
    n:             int   = 0
    median:        float = 0.0
    mad:           float = 0.0
    # Control limits (Shewhart-style, but MAD-based)
    ucl:           float = 0.0   # median + Z_ANOMALY × K × MAD  (upper control limit)
    lcl:           float = 0.0   # median − Z_ANOMALY × K × MAD
    warn_hi:       float = 0.0   # median + Z_WARNING × K × MAD
    warn_lo:       float = 0.0
    nominal:       float = 0.0
    atx_lo:        float = 0.0
    atx_hi:        float = 0.0
    anomaly_count: int   = 0
    has_data:      bool  = False

    @property
    def is_usable(self) -> bool:
        return self.has_data and self.n >= 10 and self.mad > 1e-6

    @property
    def normal_band(self) -> tuple[float, float]:
        """±Z_WATCH × K × MAD — tight "expected" operating band."""
        w = Z_WATCH * _K * self.mad
        return (self.median - w, self.median + w)

    def modified_z(self, value: float) -> float:
        """
        Modified z-score: M = 0.6745 × (x − median) / MAD.
        Returns 0.0 if MAD is effectively zero (constant signal).
        """
        if self.mad < 1e-6:
            return 0.0
        return 0.6745 * (value - self.median) / self.mad

    def health_label(self) -> tuple[str, str]:
        """
        Returns (label_text, severity_key) for UI badge.
        severity_key: 'ok' | 'watch' | 'warn' | 'crit'
        """
        if not self.is_usable:
            return ("No data", "none")
        if self.anomaly_count == 0:
            return ("Healthy", "ok")
        if self.anomaly_count <= 2:
            return (f"{self.anomaly_count} anomaly",  "watch")
        if self.anomaly_count <= 6:
            return (f"{self.anomaly_count} anomalies", "warn")
        return (f"{self.anomaly_count} anomalies", "crit")


@dataclass
class VoltageEvent:
    """
    A single detected voltage anomaly or pattern violation.

    event_type codes
    ----------------
    isolated_spike      One point beyond Z_ANOMALY (Rule 1)
    cluster             2-of-3 consecutive points beyond Z_WARNING (Rule 5)
    sustained_high      9+ consecutive points above median  (Rule 2)
    sustained_low       9+ consecutive points below median  (Rule 2)
    trend_up            6+ consecutive rising points         (Rule 3)
    trend_down          6+ consecutive falling points        (Rule 3)
    transient           Load-correlated spike (suppressed)
    """
    ts:          float
    rail:        str
    value:       float
    z_score:     float
    severity:    str              # "info" | "warning" | "critical"
    event_type:  str   = "isolated_spike"
    suppressed:  bool  = False
    decayed:     bool  = False
    reason:      str   = ""       # human-readable context

    def reason_for_chat(self, lang: str = "en") -> str:
        """Short, chat-friendly reason string."""
        meta  = RAILS.get(self.rail, {})
        label = meta.get("label", self.rail)
        v_str = f"{self.value:.3f}V"
        if lang == "pl":
            _map = {
                "isolated_spike":   f"Izolowany skok na szynie {label}: {v_str}",
                "cluster":          f"Skupisko nieprawidłowych wartości ({label})",
                "sustained_high":   f"Szyna {label} utrzymuje wartości powyżej normy",
                "sustained_low":    f"Szyna {label} utrzymuje wartości poniżej normy",
                "trend_up":         f"Szyna {label} wykazuje trend wzrostowy",
                "trend_down":       f"Szyna {label} wykazuje trend spadkowy",
                "transient":        f"Przejściowy skok {label} (ładowanie GPU)",
            }
        else:
            _map = {
                "isolated_spike":   f"Isolated spike on {label} rail: {v_str}",
                "cluster":          f"Abnormal value cluster on {label} rail",
                "sustained_high":   f"{label} rail sustained above normal band",
                "sustained_low":    f"{label} rail sustained below normal band",
                "trend_up":         f"{label} rail shows rising trend",
                "trend_down":       f"{label} rail shows falling trend",
                "transient":        f"Transient {label} spike (GPU load change)",
            }
        base = _map.get(self.event_type, self.reason or f"Anomaly on {label}")
        if self.reason and self.event_type not in ("transient",):
            return f"{base}  ·  {self.reason}"
        return base


# ── VoltageAnalyzer ───────────────────────────────────────────────────────────

class VoltageAnalyzer:
    """
    Thread-safe voltage intelligence engine.
    Use via the module-level singleton ``voltage_analyzer``.
    """

    def __init__(self) -> None:
        self._lock         = threading.Lock()
        self._cache: dict  = {}
        self._last_rebuild = 0.0
        self._load_cache()

    # ── Availability check ────────────────────────────────────────────────────

    def is_data_available(self) -> bool:
        """
        Returns True if at least a few snapshots with real voltage readings
        exist in the last 7 days.  Fast path: cached rail stats.
        """
        with self._lock:
            for key in RAILS:
                rd = self._cache.get("rails", {}).get(key, {})
                if rd.get("has_data") and rd.get("n", 0) >= 3:
                    return True
        # Fallback: direct DB probe
        try:
            since = time.time() - 7 * 86400
            con   = sqlite3.connect(_DB_PATH, timeout=3)
            n = con.execute(
                "SELECT COUNT(*) FROM deepmonitor_snapshots "
                "WHERE ts >= ? AND mb_volt_12v > 0",
                (since,),
            ).fetchone()[0]
            con.close()
            return n >= 3
        except Exception:
            return False

    def snapshot_count(self) -> int:
        """Total number of DeepMonitor voltage snapshots available."""
        try:
            con = sqlite3.connect(_DB_PATH, timeout=3)
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=5000")
            n   = con.execute(
                "SELECT COUNT(*) FROM deepmonitor_snapshots "
                "WHERE mb_volt_12v > 0"
            ).fetchone()[0]
            con.close()
            return n
        except Exception:
            return 0

    # ── Rail statistics ───────────────────────────────────────────────────────

    def get_rail_stats(self) -> dict[str, RailStats]:
        """Return current learned stats for all three rails (always safe)."""
        with self._lock:
            result = {}
            for key, meta in RAILS.items():
                rd = self._cache.get("rails", {}).get(key, {})
                rs = RailStats(
                    rail          = key,
                    n             = rd.get("n",             0),
                    median        = rd.get("median",        meta["nominal"]),
                    mad           = rd.get("mad",           0.0),
                    ucl           = rd.get("ucl",           meta["atx_hi"]),
                    lcl           = rd.get("lcl",           meta["atx_lo"]),
                    warn_hi       = rd.get("warn_hi",       meta["atx_hi"]),
                    warn_lo       = rd.get("warn_lo",       meta["atx_lo"]),
                    nominal       = meta["nominal"],
                    atx_lo        = meta["atx_lo"],
                    atx_hi        = meta["atx_hi"],
                    anomaly_count = rd.get("anomaly_count", 0),
                    has_data      = rd.get("has_data",      False),
                )
                result[key] = rs
        return result

    # ── History analysis ──────────────────────────────────────────────────────

    def analyze_history(self, hours: int = 24) -> tuple[list[dict], list[VoltageEvent]]:
        """
        Analyse the last `hours` of voltage snapshots.

        Returns
        -------
        timeline : list[dict]
            Raw snapshot rows (ts, mb_volt_12v, mb_volt_5v, mb_volt_33v, gpu_load).
        events : list[VoltageEvent]
            Anomalies and warnings found in this window, context-annotated.
        """
        rows = self._query_history(hours)
        if not rows:
            return [], []

        stats     = self.get_rail_stats()
        events:   list[VoltageEvent] = []
        spike_mag: dict[str, list[float]] = {k: [] for k in RAILS}

        # ── Per-rail per-row z-scores (needed by Nelson rules) ────────────────
        rail_mz: dict[str, list[float | None]] = {k: [] for k in RAILS}
        rail_v:  dict[str, list[float]] = {k: [] for k in RAILS}
        gpu_deltas: list[float] = []

        for i, row in enumerate(rows):
            gd = 0.0
            if i > 0:
                g1 = float(rows[i-1].get("gpu_load", 0.0) or 0.0)
                g2 = float(row.get("gpu_load",       0.0) or 0.0)
                gd = abs(g2 - g1)
            gpu_deltas.append(gd)

            for rail_key, rs in stats.items():
                v = float(row.get(rail_key, -1.0) or -1.0)
                if v <= 0 or not rs.is_usable:
                    rail_mz[rail_key].append(None)
                    rail_v[rail_key].append(-1.0)
                else:
                    rail_mz[rail_key].append(rs.modified_z(v))
                    rail_v[rail_key].append(v)

        # ── Rule 1 + 5: single-spike and 2-of-3 cluster detection ─────────────
        for i, row in enumerate(rows):
            gd = gpu_deltas[i]
            for rail_key, rs in stats.items():
                mz = rail_mz[rail_key][i]
                v  = rail_v[rail_key][i]
                if mz is None or v < 0:
                    continue

                # Rule 1: single point beyond Z_ANOMALY
                if abs(mz) >= Z_ANOMALY:
                    sev  = "critical"
                    etype = "isolated_spike"
                    suppressed, reason = self._gpu_context(
                        rail_key, gd, v, rs)
                    if suppressed:
                        sev   = "info"
                        etype = "transient"
                    spike_mag[rail_key].append(abs(v - rs.median))
                    events.append(VoltageEvent(
                        ts=float(row.get("ts", 0.0)), rail=rail_key,
                        value=v, z_score=mz, severity=sev,
                        event_type=etype, suppressed=suppressed, reason=reason,
                    ))

                # Rule 5: 2-of-3 consecutive beyond Z_WARNING
                elif abs(mz) >= Z_WARNING and i >= 2:
                    window = [
                        rail_mz[rail_key][j]
                        for j in range(i - 2, i + 1)
                        if rail_mz[rail_key][j] is not None
                    ]
                    n_above = sum(1 for m in window
                                  if abs(m) >= Z_WARNING
                                  and m * mz > 0)   # same sign
                    if n_above >= 2:
                        suppressed, reason = self._gpu_context(
                            rail_key, gd, v, rs)
                        sev = "warning" if not suppressed else "info"
                        spike_mag[rail_key].append(abs(v - rs.median))
                        events.append(VoltageEvent(
                            ts=float(row.get("ts", 0.0)), rail=rail_key,
                            value=v, z_score=mz, severity=sev,
                            event_type="cluster" if not suppressed else "transient",
                            suppressed=suppressed, reason=reason,
                        ))

        # ── Rule 2: 9 consecutive same side (sustained deviation) ─────────────
        for rail_key, rs in stats.items():
            mzs = rail_mz[rail_key]
            n   = len(mzs)
            run_sign = 0
            run_len  = 0
            run_start = 0
            for i, mz in enumerate(mzs):
                if mz is None:
                    run_len = 0
                    run_sign = 0
                    continue
                sign = 1 if mz > 0 else -1
                if sign == run_sign:
                    run_len += 1
                else:
                    run_sign  = sign
                    run_len   = 1
                    run_start = i
                if run_len == 9:
                    ts9 = float(rows[i].get("ts", 0.0))
                    v9  = rail_v[rail_key][i]
                    etype = "sustained_high" if run_sign > 0 else "sustained_low"
                    reason = (f"9 consecutive {'above' if run_sign>0 else 'below'}"
                              f" median ({v9:.4f}V)")
                    events.append(VoltageEvent(
                        ts=ts9, rail=rail_key,
                        value=v9, z_score=mzs[i] or 0.0,
                        severity="warning", event_type=etype,
                        suppressed=False, reason=reason,
                    ))

        # ── Rule 3: 6 consecutive monotonically changing (trend) ──────────────
        for rail_key, rs in stats.items():
            vals = rail_v[rail_key]
            n    = len(vals)
            up_run = dn_run = 1
            for i in range(1, n):
                v1 = vals[i - 1]
                v2 = vals[i]
                if v1 < 0 or v2 < 0:
                    up_run = dn_run = 1
                    continue
                if v2 > v1:
                    up_run += 1;  dn_run = 1
                elif v2 < v1:
                    dn_run += 1;  up_run = 1
                else:
                    up_run = dn_run = 1
                if up_run == 6:
                    ts_t   = float(rows[i].get("ts", 0.0))
                    delta  = vals[i] - vals[max(0, i - 5)]
                    events.append(VoltageEvent(
                        ts=ts_t, rail=rail_key,
                        value=vals[i], z_score=rail_mz[rail_key][i] or 0.0,
                        severity="warning", event_type="trend_up",
                        reason=f"{rail_key} rising Δ {delta:+.4f}V over 30 min",
                    ))
                if dn_run == 6:
                    ts_t   = float(rows[i].get("ts", 0.0))
                    delta  = vals[i] - vals[max(0, i - 5)]
                    events.append(VoltageEvent(
                        ts=ts_t, rail=rail_key,
                        value=vals[i], z_score=rail_mz[rail_key][i] or 0.0,
                        severity="warning", event_type="trend_down",
                        reason=f"{rail_key} falling Δ {delta:+.4f}V over 30 min",
                    ))

        # ── Anomaly decay ─────────────────────────────────────────────────────
        for evt in events:
            if evt.suppressed or evt.event_type in (
                    "sustained_high", "sustained_low", "trend_up", "trend_down"):
                continue
            mag     = abs(evt.value - stats[evt.rail].median)
            similar = sum(
                1 for m in spike_mag.get(evt.rail, [])
                if abs(m - mag) / max(mag, 1e-6) < 0.30
            )
            if similar >= DECAY_REPEAT_THRESH:
                evt.decayed = True
                if evt.severity == "critical":
                    evt.severity = "warning"
                elif evt.severity == "warning":
                    evt.severity = "info"
                note = f"Repeats {similar}× — may be your hardware's normal"
                evt.reason = (evt.reason + "  ·  " + note
                              if evt.reason else note)

        events.sort(key=lambda e: e.ts)
        return rows, events

    # ── Rebuild ───────────────────────────────────────────────────────────────

    def rebuild(self, force: bool = False) -> bool:
        """
        Recompute MAD-based baselines from the last 7 days of history.
        Returns True on success.  Skips if <5 min since last rebuild
        unless force=True.
        """
        if not force and (time.time() - self._last_rebuild < 300):
            return False

        rows = self._query_history(hours=7 * 24)
        if not rows:
            self._last_rebuild = time.time()
            return False

        new_rails: dict[str, dict] = {}

        for rail_key, meta in RAILS.items():
            vals = [
                float(r[rail_key])
                for r in rows
                if (r.get(rail_key) or -1.0) > 0
            ]

            if len(vals) < 5:
                new_rails[rail_key] = {
                    "n":             len(vals),
                    "has_data":      bool(vals),
                    "median":        meta["nominal"],
                    "mad":           0.0,
                    "ucl":           meta["atx_hi"],
                    "lcl":           meta["atx_lo"],
                    "warn_hi":       meta["atx_hi"],
                    "warn_lo":       meta["atx_lo"],
                    "anomaly_count": 0,
                }
                continue

            med = _median(vals)
            mad = _mad(vals, med)

            ucl     = med + Z_ANOMALY * _K * mad
            lcl     = med - Z_ANOMALY * _K * mad
            warn_hi = med + Z_WARNING * _K * mad
            warn_lo = med - Z_WARNING * _K * mad

            n_anom  = sum(1 for v in vals
                          if abs(_modified_z(v, med, mad)) > Z_WARNING)

            new_rails[rail_key] = {
                "n":             len(vals),
                "has_data":      True,
                "median":        round(med,     4),
                "mad":           round(mad,     4),
                "ucl":           round(ucl,     4),
                "lcl":           round(lcl,     4),
                "warn_hi":       round(warn_hi, 4),
                "warn_lo":       round(warn_lo, 4),
                "anomaly_count": n_anom,
            }

        with self._lock:
            self._cache.setdefault("rails", {}).update(new_rails)
            self._cache["last_update"] = time.time()
            self._cache["version"]     = VERSION
            self._last_rebuild         = time.time()

        self._save_cache()
        return True

    def maybe_rebuild(self, min_interval_s: float = 300.0) -> None:
        """Async rebuild if baseline is older than min_interval_s."""
        if time.time() - self._last_rebuild > min_interval_s:
            threading.Thread(
                target=self.rebuild,
                daemon=True,
                name="VoltageAnalyzerRebuild",
            ).start()

    @staticmethod
    def _gpu_context(rail_key: str, gpu_delta: float,
                     v: float, rs: "RailStats") -> tuple[bool, str]:
        """
        Returns (suppressed, reason).
        12V spikes are physically expected during GPU transients.
        """
        if rail_key == "mb_volt_12v" and gpu_delta > 25.0:
            return True, f"GPU load Δ {gpu_delta:.0f}% (expected transient)"
        return False, ""

    # ── hck_GPT-facing API ────────────────────────────────────────────────────

    def get_anomaly_summary(self, hours: int = 24) -> dict:
        """
        Structured summary for hck_GPT response builder.
        Returns a dict with per-rail health + latest events.
        """
        _, events = self.analyze_history(hours=hours)
        stats_all = self.get_rail_stats()

        real_events = [e for e in events
                       if not e.suppressed and e.severity != "info"]

        per_rail = {}
        for key, meta in RAILS.items():
            rs = stats_all.get(key)
            crit_for_rail = [e for e in real_events
                             if e.rail == key and e.severity == "critical"]
            warn_for_rail = [e for e in real_events
                             if e.rail == key and e.severity == "warning"]
            rail_events   = [e for e in real_events if e.rail == key]
            per_rail[key] = {
                "label":     meta["label"],
                "has_data":  rs.has_data if rs else False,
                "median":    rs.median if rs else 0,
                "mad":       rs.mad    if rs else 0,
                "nominal":   meta["nominal"],
                "n_crit":    len(crit_for_rail),
                "n_warn":    len(warn_for_rail),
                "latest":    (rail_events[-1].reason_for_chat()
                              if rail_events else ""),
                "health":    ("critical" if crit_for_rail else
                              "warning"  if warn_for_rail else "ok"),
            }
        return {
            "data_available": self.is_data_available(),
            "snapshot_count": self.snapshot_count(),
            "rails":          per_rail,
            "total_events":   len(real_events),
            "has_critical":   any(e.severity == "critical"
                                  for e in real_events),
        }

    def format_for_chat(self, lang: str = "en") -> str:
        """
        Return a chat-ready multi-line string with voltage rail status.
        Used by hck_gpt/responses/builder.py.
        """
        if not self.is_data_available():
            if lang == "pl":
                return ("⚡ Brak danych napięć — wymagany LibreHardwareMonitor.\n"
                        "Po uruchomieniu LHM program zacznie zbierać dane szyn 12V/5V/3.3V.")
            return ("⚡ No voltage data — LibreHardwareMonitor required.\n"
                    "Once LHM is running, PC Workman will start learning your rail patterns.")

        summary = self.get_anomaly_summary()
        lines   = []

        if lang == "pl":
            header = f"⚡ NAPIĘCIA SZYN  ({summary['snapshot_count']:,} próbek · SPC)"
        else:
            header = f"⚡ VOLTAGE RAILS  ({summary['snapshot_count']:,} snapshots · SPC)"
        lines.append(header)

        health_icon = {"ok": "✓", "warning": "⚠", "critical": "🔴"}
        for key, info in summary["rails"].items():
            if not info["has_data"]:
                status = "no data"
            else:
                dev = (info["median"] - info["nominal"])
                dev_str = f"{dev:+.3f}V" if abs(dev) > 0.001 else "±0 nominal"
                icon = health_icon.get(info["health"], "·")
                if lang == "pl":
                    nc = info["n_crit"]
                    nw = info["n_warn"]
                    ev_str = (f"  {nc} krytycznych" if nc else
                              f"  {nw} ostrzeżeń" if nw else "  brak anomalii")
                    status = f"{icon} {info['label']:4s}  {info['median']:.3f}V  ({dev_str}){ev_str}"
                else:
                    nc = info["n_crit"]
                    nw = info["n_warn"]
                    ev_str = (f"  {nc} critical" if nc else
                              f"  {nw} warnings" if nw else "  no anomalies")
                    status = f"{icon} {info['label']:4s}  {info['median']:.3f}V  ({dev_str}){ev_str}"
            lines.append("  " + status)

        if summary["has_critical"]:
            _, evts = self.analyze_history(hours=24)
            crits = [e for e in evts if e.severity == "critical" and not e.suppressed]
            if crits:
                latest = crits[-1]
                if lang == "pl":
                    lines.append(f"\n⚠ Ostatnie zdarzenie krytyczne:")
                else:
                    lines.append(f"\n⚠ Latest critical event:")
                lines.append(f"  [{latest.event_type}] {latest.reason_for_chat(lang)}")

        if lang == "pl":
            lines.append("\n💬 Wpisz 'monitorowanie' by zobaczyć pełne wykresy napięć.")
        else:
            lines.append("\n💬 Type 'monitoring' to see full voltage charts.")

        return "\n".join(lines)

    def overall_health_score(self) -> int:
        """
        Returns a 0-100 PSU health score for the last 24 h.

        Scoring (starts at 100):
          - Rail with no data          : −5
          - Sustained deviation        : −15 per rail
          - Warning event (not decayed): −10 each (capped −20 per rail)
          - Critical event (not decayed): −20 each (capped −40 per rail)

        A score of 100 means all rails nominal, zero real anomalies.
        A score ≤ 40 means serious voltage instability.
        """
        _, events = self.analyze_history(hours=24)
        stats     = self.get_rail_stats()

        score = 100
        for key, rs in stats.items():
            if not rs.has_data:
                score -= 5
                continue
            rail_evts = [e for e in events
                         if e.rail == key and not e.suppressed]
            crits = sum(1 for e in rail_evts
                        if e.severity == "critical" and not e.decayed)
            warns = sum(1 for e in rail_evts
                        if e.severity == "warning"  and not e.decayed)
            sustained = any(e.event_type in ("sustained_high", "sustained_low")
                            for e in rail_evts)

            score -= min(40, crits * 20)
            score -= min(20, warns * 10)
            if sustained:
                score -= 15

        return max(0, min(100, score))

    def last_update_str(self) -> str:
        ts = self._cache.get("last_update", 0.0)
        if not ts:
            return "Never"
        delta = time.time() - ts
        if delta < 120:    return "Just now"
        if delta < 3600:   return f"{int(delta / 60)} min ago"
        return f"{int(delta / 3600)}h ago"

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _query_history(self, hours: int) -> list[dict]:
        try:
            since = time.time() - hours * 3600
            con   = sqlite3.connect(_DB_PATH, timeout=5)
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=5000")
            con.row_factory = sqlite3.Row
            rows  = con.execute(
                "SELECT ts, mb_volt_12v, mb_volt_5v, mb_volt_33v, gpu_load "
                "FROM deepmonitor_snapshots "
                "WHERE ts >= ? "
                "ORDER BY ts",
                (since,),
            ).fetchall()
            con.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _load_cache(self) -> None:
        try:
            with open(_PREFS_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            if raw.get("version") == VERSION:
                self._cache = raw
                return
        except Exception:
            pass
        self._cache = {"version": VERSION, "rails": {}, "last_update": 0.0}

    def _save_cache(self) -> None:
        try:
            os.makedirs(os.path.dirname(_PREFS_PATH), exist_ok=True)
            with open(_PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception:
            pass


# ── Math helpers ──────────────────────────────────────────────────────────────

def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _mad(vals: list[float], med: float) -> float:
    """Median Absolute Deviation."""
    devs = sorted(abs(v - med) for v in vals)
    n    = len(devs)
    mid  = n // 2
    return devs[mid] if n % 2 else (devs[mid - 1] + devs[mid]) / 2.0


def _modified_z(v: float, med: float, mad: float) -> float:
    if mad < 1e-9:
        return 0.0
    return 0.6745 * (v - med) / mad


# ── Singleton ─────────────────────────────────────────────────────────────────
voltage_analyzer = VoltageAnalyzer()
