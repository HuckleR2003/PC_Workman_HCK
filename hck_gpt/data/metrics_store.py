"""
hck_gpt.data.metrics_store
===========================
Persistent storage for DeepMonitor sensor snapshots.

Extends the existing hck_stats.db (hck_stats_engine) with a new table
`deepmonitor_snapshots` that captures GPU temps, MB temps/voltages, disk
usage, swap and power estimates - data the main stats engine doesn't store.

Background thread saves a snapshot every SNAPSHOT_INTERVAL seconds.
On startup, loads historical min/max back into live_sensors.LIVE so
hck_GPT can compare "now" against real multi-day baselines.

Usage
-----
    from hck_gpt.data.metrics_store import metrics_store
    metrics_store.start()          # called once at app boot
    metrics_store.stop()           # called at app shutdown (optional)
    rows = metrics_store.get_history(hours=24)
    summary = metrics_store.daily_summary(days=7)
"""
from __future__ import annotations

import sqlite3
import threading
import time
import os
import sys
import json
import logging

log = logging.getLogger("metrics_store")

# ── Paths (mirrors hck_stats_engine.constants pattern) ───────────────────────
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
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_DATA_DIR = os.path.join(_base_dir(), "data", "logs")
_DB_PATH  = os.path.join(_DATA_DIR, "hck_stats.db")   # shared with stats engine

SNAPSHOT_INTERVAL = 300   # 5 minutes between snapshots
RETENTION_DAYS    = 183   # ~6 months of look-back history (was 90)


# ── Schema migration (adds table if absent; never drops existing tables) ──────
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS deepmonitor_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL    NOT NULL,            -- epoch
    date_str      TEXT    NOT NULL,            -- YYYY-MM-DD (for daily grouping)
    cpu_load      REAL,                        -- %
    cpu_temp      REAL,                        -- °C estimated
    cpu_mhz       REAL,                        -- current MHz
    cpu_power     REAL,                        -- W estimated
    gpu_temp      REAL,                        -- °C via nvidia-smi
    gpu_load      REAL,                        -- %
    gpu_vram_pct  REAL,                        -- %
    gpu_power     REAL,                        -- W
    ram_pct       REAL,                        -- %
    ram_used_gb   REAL,
    swap_pct      REAL,                        -- % pagefile used
    mb_temp_sys   REAL,                        -- °C from LHM/OHM (or -1)
    mb_temp_vrm   REAL,
    mb_volt_12v   REAL,
    mb_volt_5v    REAL,
    mb_volt_33v   REAL,
    mb_volt_vcore REAL,                        -- CPU core V (2026-07-17)
    mb_volt_gpu   REAL,                        -- GPU core V (2026-07-17)
    disk_json     TEXT,                        -- JSON: {mountpoint: {used_gb,free_gb,pct}}
    mb_source     TEXT DEFAULT ''             -- '' | 'ohm' | 'lhm'
);
CREATE INDEX IF NOT EXISTS idx_dm_ts ON deepmonitor_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_dm_date ON deepmonitor_snapshots(date_str);
"""


class MetricsStore:
    """Thread-safe persistent store for DeepMonitor sensor snapshots."""

    def __init__(self) -> None:
        self._lock   = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop   = threading.Event()
        self._ready  = False
        self._db_path = _DB_PATH

    # ── Init ──────────────────────────────────────────────────────────────────

    def _ensure_table(self) -> bool:
        """Migrate / create deepmonitor_snapshots in the shared DB."""
        os.makedirs(_DATA_DIR, exist_ok=True)
        try:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.executescript(_SCHEMA_SQL)
            # CREATE IF NOT EXISTS does not add columns to an EXISTING table -
            # older installs need the 2026-07-17 rails added explicitly.
            have = {r[1] for r in conn.execute(
                "PRAGMA table_info(deepmonitor_snapshots)")}
            for col in ("mb_volt_vcore", "mb_volt_gpu"):
                if col not in have:
                    conn.execute(f"ALTER TABLE deepmonitor_snapshots "
                                 f"ADD COLUMN {col} REAL")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log.warning("metrics_store: schema init failed: %s", e)
            return False

    def start(self) -> None:
        """Start the background snapshot writer + load historical baselines."""
        self._ready = self._ensure_table()
        if not self._ready:
            log.warning("metrics_store: DB not ready, persistence disabled.")
            return
        self._load_historical_baselines()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._writer_loop,
            name="DeepMonitorWriter",
            daemon=True,
        )
        self._thread.start()
        log.info("metrics_store: background writer started (interval=%ds)", SNAPSHOT_INTERVAL)

    def stop(self) -> None:
        self._stop.set()

    # ── Background writer ─────────────────────────────────────────────────────

    def _writer_loop(self) -> None:
        # Stagger first write by 60 s so the UI finishes loading first
        self._stop.wait(60)
        while not self._stop.is_set():
            try:
                self._save_snapshot()
                self._prune_old_rows()
            except Exception as e:
                log.debug("metrics_store writer error: %s", e)
            self._stop.wait(SNAPSHOT_INTERVAL)

    def _save_snapshot(self) -> None:
        """Read live_sensors.LIVE + psutil and persist one row."""
        try:
            from hck_gpt.data.live_sensors import snapshot as _ls_snap
            ls = _ls_snap()
        except Exception:
            ls = {}

        # RAM / swap from psutil (more reliable than estimates)
        try:
            import psutil
            vm   = psutil.virtual_memory()
            sw   = psutil.swap_memory()
            ram_pct    = vm.percent
            ram_gb     = vm.used / 1e9
            swap_pct   = sw.percent
        except Exception:
            ram_pct = ls.get("cpu_load", -1.0)   # fallback
            ram_gb  = -1.0
            swap_pct = -1.0

        now      = time.time()
        date_str = time.strftime("%Y-%m-%d", time.localtime(now))

        row = (
            now,
            date_str,
            ls.get("cpu_load",    -1.0),
            # estimated temps never enter history/learning - real sensors only
            (ls.get("cpu_temp", -1.0)
             if ls.get("cpu_temp_src") == "sensor" else -1.0),
            ls.get("cpu_mhz",     -1.0),
            ls.get("cpu_power",   -1.0),
            ls.get("gpu_temp",    -1.0),
            ls.get("gpu_load",    -1.0),
            ls.get("gpu_vram_pct",-1.0),
            ls.get("gpu_power",   -1.0),
            ram_pct,
            ram_gb,
            swap_pct,
            ls.get("mb_temp_sys", -1.0),
            ls.get("mb_temp_vrm", -1.0),
            ls.get("mb_volt_12v", -1.0),
            ls.get("mb_volt_5v",  -1.0),
            ls.get("mb_volt_33v", -1.0),
            ls.get("mb_volt_vcore", -1.0),
            ls.get("mb_volt_gpu",   -1.0),
            json.dumps(ls.get("disks", {})),
            ls.get("mb_source",   ""),
        )
        sql = """
            INSERT INTO deepmonitor_snapshots
            (ts, date_str, cpu_load, cpu_temp, cpu_mhz, cpu_power,
             gpu_temp, gpu_load, gpu_vram_pct, gpu_power,
             ram_pct, ram_used_gb, swap_pct,
             mb_temp_sys, mb_temp_vrm, mb_volt_12v, mb_volt_5v, mb_volt_33v,
             mb_volt_vcore, mb_volt_gpu,
             disk_json, mb_source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        with self._get_conn() as conn:
            conn.execute(sql, row)
            conn.commit()
        log.debug("metrics_store: snapshot saved (cpu=%.0f%% gpu=%.0f°C)",
                  row[2], row[6])

    def _prune_old_rows(self) -> None:
        cutoff = time.time() - RETENTION_DAYS * 86400
        with self._get_conn() as conn:
            conn.execute("DELETE FROM deepmonitor_snapshots WHERE ts < ?", (cutoff,))
            conn.commit()

    # ── Historical baseline loader ─────────────────────────────────────────────

    def _load_historical_baselines(self) -> None:
        """
        On startup: query DB for the last 7 days of data.
        Populate live_sensors session_hist with real historical min/max so
        hck_GPT comparisons work on first query, not just current session.
        """
        try:
            since = time.time() - 7 * 86400
            sql = """
                SELECT
                  MIN(CASE WHEN cpu_load  >= 0 THEN cpu_load  END) AS cpu_lo,
                  MAX(CASE WHEN cpu_load  >= 0 THEN cpu_load  END) AS cpu_hi,
                  AVG(CASE WHEN cpu_load  >= 0 THEN cpu_load  END) AS cpu_av,
                  MIN(CASE WHEN cpu_temp  >= 0 THEN cpu_temp  END) AS temp_lo,
                  MAX(CASE WHEN cpu_temp  >= 0 THEN cpu_temp  END) AS temp_hi,
                  MIN(CASE WHEN gpu_temp  >= 0 THEN gpu_temp  END) AS gtemp_lo,
                  MAX(CASE WHEN gpu_temp  >= 0 THEN gpu_temp  END) AS gtemp_hi,
                  MIN(CASE WHEN ram_pct   >= 0 THEN ram_pct   END) AS ram_lo,
                  MAX(CASE WHEN ram_pct   >= 0 THEN ram_pct   END) AS ram_hi,
                  AVG(CASE WHEN ram_pct   >= 0 THEN ram_pct   END) AS ram_av,
                  MIN(CASE WHEN gpu_load  >= 0 THEN gpu_load  END) AS gpu_lo,
                  MAX(CASE WHEN gpu_load  >= 0 THEN gpu_load  END) AS gpu_hi,
                  COUNT(*) AS n
                FROM deepmonitor_snapshots
                WHERE ts >= ?
            """
            with self._get_conn() as conn:
                row = conn.execute(sql, (since,)).fetchone()

            if not row or (row["n"] or 0) < 2:
                log.info("metrics_store: not enough history yet (%d rows)", row["n"] if row else 0)
                return

            # Push into live_sensors session_hist so the panel + AI can use it
            from hck_gpt.data import live_sensors as _ls
            hist = {
                "cpu_pct":  [row["cpu_lo"] or 0, row["cpu_hi"] or 100],
                "cpu_pkg":  [row["temp_lo"] or 0, row["temp_hi"] or 100],
                "gpu_temp": [row["gtemp_lo"] or 0, row["gtemp_hi"] or 100],
                "gpu_load": [row["gpu_lo"] or 0, row["gpu_hi"] or 100],
                "ram_pct":  [row["ram_lo"] or 0, row["ram_hi"] or 100],
            }
            _ls.update({
                # merge - the live_collector daemon owns per-session extremes
                "session_hist": {**(_ls.get("session_hist") or {}), **hist},
                "_hist_cpu_avg_7d": round(row["cpu_av"] or 0, 1),
                "_hist_ram_avg_7d": round(row["ram_av"] or 0, 1),
                "_hist_rows_7d":    row["n"],
            })
            log.info(
                "metrics_store: loaded 7-day baselines (%d rows) - "
                "CPU avg=%.0f%% RAM avg=%.0f%%",
                row["n"], row["cpu_av"] or 0, row["ram_av"] or 0,
            )
        except Exception as e:
            log.warning("metrics_store: baseline load failed: %s", e)

    # ── Public query API (used by hck_GPT response handlers) ──────────────────

    def get_history(self, hours: int = 24) -> list[dict]:
        """
        Return deepmonitor snapshots for the last N hours.
        Each row is a plain dict with all sensor columns.
        """
        if not self._ready:
            return []
        try:
            since = time.time() - hours * 3600
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM deepmonitor_snapshots WHERE ts >= ? ORDER BY ts DESC",
                    (since,),
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            log.debug("metrics_store.get_history error: %s", e)
            return []

    def daily_summary(self, days: int = 7) -> list[dict]:
        """
        Return per-day aggregated stats for the last N days.
        Useful for hck_GPT multi-day comparison responses.
        """
        if not self._ready:
            return []
        try:
            since = time.time() - days * 86400
            sql = """
                SELECT
                    date_str,
                    AVG(CASE WHEN cpu_load >= 0 THEN cpu_load END)   AS cpu_avg,
                    MAX(CASE WHEN cpu_load >= 0 THEN cpu_load END)   AS cpu_max,
                    AVG(CASE WHEN cpu_temp >= 0 THEN cpu_temp END)   AS cpu_temp_avg,
                    MAX(CASE WHEN cpu_temp >= 0 THEN cpu_temp END)   AS cpu_temp_max,
                    AVG(CASE WHEN gpu_temp >= 0 THEN gpu_temp END)   AS gpu_temp_avg,
                    MAX(CASE WHEN gpu_temp >= 0 THEN gpu_temp END)   AS gpu_temp_max,
                    AVG(CASE WHEN gpu_load >= 0 THEN gpu_load END)   AS gpu_avg,
                    MAX(CASE WHEN gpu_load >= 0 THEN gpu_load END)   AS gpu_max,
                    AVG(CASE WHEN ram_pct  >= 0 THEN ram_pct  END)   AS ram_avg,
                    MAX(CASE WHEN ram_pct  >= 0 THEN ram_pct  END)   AS ram_max,
                    MAX(CASE WHEN swap_pct >= 0 THEN swap_pct END)   AS swap_max,
                    COUNT(*) AS snapshots
                FROM deepmonitor_snapshots
                WHERE ts >= ?
                GROUP BY date_str
                ORDER BY date_str DESC
            """
            with self._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, (since,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            log.debug("metrics_store.daily_summary error: %s", e)
            return []

    def last_session_extremes(self) -> dict:
        """
        Return min/max/avg for the last 24 h - useful for 'compare with yesterday' logic.
        Returns empty dict if no data.
        """
        rows = self.daily_summary(days=2)
        if not rows:
            return {}
        today = rows[0]
        yesterday = rows[1] if len(rows) > 1 else {}
        return {"today": today, "yesterday": yesterday}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn


# ── Singleton ─────────────────────────────────────────────────────────────────
metrics_store = MetricsStore()
