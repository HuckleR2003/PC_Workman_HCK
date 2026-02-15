"""
HCK Stats Engine v2 - Database Manager
SQLite database lifecycle, schema creation, thread-safe connections
"""

import sqlite3
import threading
import os
import time

from hck_stats_engine.constants import DB_PATH, LOGS_DIR, SCHEMA_VERSION


class StatsDBManager:
    """Thread-safe SQLite database manager for long-term statistics storage"""

    def __init__(self):
        self._db_path = DB_PATH
        self._local = threading.local()
        self._initialized = False

        # Ensure directory exists
        os.makedirs(LOGS_DIR, exist_ok=True)

        # Initialize schema
        try:
            self._ensure_schema()
            self._initialized = True
            print(f"[StatsDB] Database ready at {self._db_path}")
        except Exception as e:
            print(f"[StatsDB] WARNING: Failed to initialize: {e}")

    @property
    def is_ready(self):
        return self._initialized

    def get_connection(self):
        """Get thread-local database connection"""
        if not self._initialized:
            return None

        if not hasattr(self._local, 'conn') or self._local.conn is None:
            try:
                self._local.conn = sqlite3.connect(self._db_path, timeout=10)
                self._local.conn.execute("PRAGMA journal_mode=WAL")
                self._local.conn.execute("PRAGMA busy_timeout=5000")
                self._local.conn.execute("PRAGMA synchronous=NORMAL")
                self._local.conn.row_factory = sqlite3.Row
            except Exception as e:
                print(f"[StatsDB] Connection error: {e}")
                return None

        return self._local.conn

    def close(self):
        """Close current thread's connection"""
        if hasattr(self._local, 'conn') and self._local.conn:
            try:
                self._local.conn.close()
            except:
                pass
            self._local.conn = None

    def _ensure_schema(self):
        """Create all tables if they don't exist"""
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        try:
            # Check if schema already exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if cursor.fetchone():
                # Schema exists, check version
                ver = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
                if ver and ver >= SCHEMA_VERSION:
                    conn.close()
                    return

            # Create all tables
            conn.executescript(self._get_schema_sql())

            # Record schema version
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
                (SCHEMA_VERSION,)
            )
            conn.commit()
            print(f"[StatsDB] Schema v{SCHEMA_VERSION} created successfully")

        except Exception as e:
            print(f"[StatsDB] Schema error: {e}")
            raise
        finally:
            conn.close()

    def _get_schema_sql(self):
        """Return complete schema SQL"""
        return """
        -- Schema version tracking
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER NOT NULL,
            applied_at  TEXT NOT NULL
        );

        -- Per-minute statistics (retained 7 days)
        CREATE TABLE IF NOT EXISTS minute_stats (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    REAL    NOT NULL,
            cpu_avg      REAL    NOT NULL,
            cpu_min      REAL    NOT NULL,
            cpu_max      REAL    NOT NULL,
            ram_avg      REAL    NOT NULL,
            ram_min      REAL    NOT NULL,
            ram_max      REAL    NOT NULL,
            gpu_avg      REAL    NOT NULL,
            gpu_min      REAL    NOT NULL,
            gpu_max      REAL    NOT NULL,
            cpu_temp     REAL,
            gpu_temp     REAL,
            sample_count INTEGER NOT NULL DEFAULT 60
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_minute_ts ON minute_stats(timestamp);

        -- Per-hour statistics (retained 90 days)
        CREATE TABLE IF NOT EXISTS hourly_stats (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    REAL    NOT NULL,
            cpu_avg      REAL    NOT NULL,
            cpu_min      REAL    NOT NULL,
            cpu_max      REAL    NOT NULL,
            cpu_p95      REAL,
            ram_avg      REAL    NOT NULL,
            ram_min      REAL    NOT NULL,
            ram_max      REAL    NOT NULL,
            gpu_avg      REAL    NOT NULL,
            gpu_min      REAL    NOT NULL,
            gpu_max      REAL    NOT NULL,
            cpu_temp_avg REAL,
            gpu_temp_avg REAL,
            sample_count INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_hourly_ts ON hourly_stats(timestamp);

        -- Per-day statistics (retained forever)
        CREATE TABLE IF NOT EXISTS daily_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str        TEXT    NOT NULL,
            timestamp       REAL    NOT NULL,
            cpu_avg         REAL    NOT NULL,
            cpu_min         REAL    NOT NULL,
            cpu_max         REAL    NOT NULL,
            cpu_p95         REAL,
            ram_avg         REAL    NOT NULL,
            ram_min         REAL    NOT NULL,
            ram_max         REAL    NOT NULL,
            gpu_avg         REAL    NOT NULL,
            gpu_min         REAL    NOT NULL,
            gpu_max         REAL    NOT NULL,
            cpu_temp_avg    REAL,
            gpu_temp_avg    REAL,
            uptime_minutes  INTEGER,
            sample_count    INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_date ON daily_stats(date_str);
        CREATE INDEX IF NOT EXISTS idx_daily_ts ON daily_stats(timestamp);

        -- Per-week statistics (retained forever)
        CREATE TABLE IF NOT EXISTS weekly_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_str        TEXT    NOT NULL,
            timestamp       REAL    NOT NULL,
            cpu_avg         REAL    NOT NULL,
            cpu_min         REAL    NOT NULL,
            cpu_max         REAL    NOT NULL,
            ram_avg         REAL    NOT NULL,
            ram_min         REAL    NOT NULL,
            ram_max         REAL    NOT NULL,
            gpu_avg         REAL    NOT NULL,
            gpu_min         REAL    NOT NULL,
            gpu_max         REAL    NOT NULL,
            cpu_temp_avg    REAL,
            gpu_temp_avg    REAL,
            uptime_minutes  INTEGER,
            sample_count    INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_week ON weekly_stats(week_str);

        -- Per-month statistics (retained forever)
        CREATE TABLE IF NOT EXISTS monthly_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            month_str       TEXT    NOT NULL,
            timestamp       REAL    NOT NULL,
            cpu_avg         REAL    NOT NULL,
            cpu_min         REAL    NOT NULL,
            cpu_max         REAL    NOT NULL,
            ram_avg         REAL    NOT NULL,
            ram_min         REAL    NOT NULL,
            ram_max         REAL    NOT NULL,
            gpu_avg         REAL    NOT NULL,
            gpu_min         REAL    NOT NULL,
            gpu_max         REAL    NOT NULL,
            cpu_temp_avg    REAL,
            gpu_temp_avg    REAL,
            uptime_minutes  INTEGER,
            sample_count    INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_monthly_month ON monthly_stats(month_str);

        -- Per-process per-hour statistics (retained 90 days)
        CREATE TABLE IF NOT EXISTS process_hourly_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       REAL    NOT NULL,
            process_name    TEXT    NOT NULL,
            display_name    TEXT,
            process_type    TEXT,
            category        TEXT,
            cpu_avg         REAL    NOT NULL,
            cpu_max         REAL    NOT NULL,
            ram_avg_mb      REAL    NOT NULL,
            ram_max_mb      REAL    NOT NULL,
            sample_count    INTEGER NOT NULL,
            active_seconds  INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_proc_hourly_ts ON process_hourly_stats(timestamp);
        CREATE INDEX IF NOT EXISTS idx_proc_hourly_name ON process_hourly_stats(process_name);

        -- Per-process per-day statistics (retained forever)
        CREATE TABLE IF NOT EXISTS process_daily_stats (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str             TEXT    NOT NULL,
            timestamp            REAL    NOT NULL,
            process_name         TEXT    NOT NULL,
            display_name         TEXT,
            process_type         TEXT,
            category             TEXT,
            cpu_avg              REAL    NOT NULL,
            cpu_max              REAL    NOT NULL,
            ram_avg_mb           REAL    NOT NULL,
            ram_max_mb           REAL    NOT NULL,
            total_active_seconds INTEGER NOT NULL,
            sample_count         INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_proc_daily_ts ON process_daily_stats(timestamp);
        CREATE INDEX IF NOT EXISTS idx_proc_daily_name ON process_daily_stats(process_name);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_proc_daily_date_name ON process_daily_stats(date_str, process_name);

        -- Events/alerts table (retained forever)
        CREATE TABLE IF NOT EXISTS events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    REAL    NOT NULL,
            event_type   TEXT    NOT NULL,
            severity     TEXT    NOT NULL DEFAULT 'info',
            metric       TEXT,
            value        REAL,
            baseline     REAL,
            process_name TEXT,
            description  TEXT,
            resolved_at  REAL
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        """


# Singleton instance
db_manager = StatsDBManager()
