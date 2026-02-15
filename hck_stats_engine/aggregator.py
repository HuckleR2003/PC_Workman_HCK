"""
HCK Stats Engine v2 - Aggregation Pipeline
minute → hour → day → week → month with automatic boundary detection and pruning
"""

import time
import os
import csv
import tempfile
from datetime import datetime, timezone

from hck_stats_engine.constants import (
    RETENTION_MINUTES, RETENTION_HOURLY, RETENTION_PROCESS_HOURLY,
    RETENTION_RAW_CSV, PRUNING_INTERVAL, SECONDS_PER_HOUR, SECONDS_PER_DAY,
    LOGS_DIR
)
from hck_stats_engine.db_manager import db_manager


class StatsAggregator:
    """Central aggregation pipeline for system statistics"""

    def __init__(self):
        self._last_hour_boundary = 0
        self._last_day_boundary = 0
        self._last_pruning = 0
        self._process_aggregator = None

        # Initialize boundaries from database
        self._init_boundaries()
        print("[StatsAggregator] Initialized")

    def _init_boundaries(self):
        """Initialize boundary timestamps from database"""
        conn = db_manager.get_connection()
        if not conn:
            now = time.time()
            self._last_hour_boundary = int(now // SECONDS_PER_HOUR) * SECONDS_PER_HOUR
            self._last_day_boundary = int(now // SECONDS_PER_DAY) * SECONDS_PER_DAY
            return

        try:
            # Get last hour boundary from hourly_stats
            row = conn.execute("SELECT MAX(timestamp) FROM hourly_stats").fetchone()
            if row and row[0]:
                self._last_hour_boundary = row[0]
            else:
                self._last_hour_boundary = int(time.time() // SECONDS_PER_HOUR) * SECONDS_PER_HOUR

            # Get last day boundary from daily_stats
            row = conn.execute("SELECT MAX(timestamp) FROM daily_stats").fetchone()
            if row and row[0]:
                self._last_day_boundary = row[0]
            else:
                self._last_day_boundary = int(time.time() // SECONDS_PER_DAY) * SECONDS_PER_DAY

        except Exception as e:
            print(f"[StatsAggregator] Boundary init error: {e}")
            now = time.time()
            self._last_hour_boundary = int(now // SECONDS_PER_HOUR) * SECONDS_PER_HOUR
            self._last_day_boundary = int(now // SECONDS_PER_DAY) * SECONDS_PER_DAY

    def set_process_aggregator(self, proc_agg):
        """Link process aggregator"""
        self._process_aggregator = proc_agg

    def on_minute_tick(self, timestamp, cpu_avg, ram_avg, gpu_avg,
                       cpu_vals=None, ram_vals=None, gpu_vals=None,
                       cpu_temp=None, gpu_temp=None):
        """Called by scheduler every 60 seconds with aggregated minute data.

        Args:
            timestamp: Unix epoch for the minute
            cpu_avg, ram_avg, gpu_avg: Pre-computed averages
            cpu_vals, ram_vals, gpu_vals: Raw 60-second value lists for min/max
            cpu_temp, gpu_temp: Optional temperature readings
        """
        if not db_manager.is_ready:
            return

        try:
            # Insert minute stats
            self._insert_minute_stats(timestamp, cpu_avg, ram_avg, gpu_avg,
                                      cpu_vals, ram_vals, gpu_vals,
                                      cpu_temp, gpu_temp)

            # Check hour boundary
            current_hour = int(timestamp // SECONDS_PER_HOUR) * SECONDS_PER_HOUR
            if current_hour > self._last_hour_boundary:
                self._aggregate_hour(self._last_hour_boundary)
                self._last_hour_boundary = current_hour

            # Check day boundary
            current_day = int(timestamp // SECONDS_PER_DAY) * SECONDS_PER_DAY
            if current_day > self._last_day_boundary:
                self._aggregate_day(self._last_day_boundary)
                self._check_weekly_monthly(self._last_day_boundary)
                self._last_day_boundary = current_day

            # Pruning check (once per hour)
            now = time.time()
            if now - self._last_pruning > PRUNING_INTERVAL:
                self._run_pruning()
                self._last_pruning = now

        except Exception as e:
            print(f"[StatsAggregator] on_minute_tick error: {e}")

    def _insert_minute_stats(self, timestamp, cpu_avg, ram_avg, gpu_avg,
                             cpu_vals, ram_vals, gpu_vals,
                             cpu_temp=None, gpu_temp=None):
        """Insert a minute stats row into SQLite"""
        conn = db_manager.get_connection()
        if not conn:
            return

        # Compute min/max from raw values if available
        if cpu_vals and len(cpu_vals) > 0:
            cpu_min, cpu_max = min(cpu_vals), max(cpu_vals)
        else:
            cpu_min = cpu_max = cpu_avg

        if ram_vals and len(ram_vals) > 0:
            ram_min, ram_max = min(ram_vals), max(ram_vals)
        else:
            ram_min = ram_max = ram_avg

        if gpu_vals and len(gpu_vals) > 0:
            gpu_min, gpu_max = min(gpu_vals), max(gpu_vals)
        else:
            gpu_min = gpu_max = gpu_avg

        sample_count = len(cpu_vals) if cpu_vals else 60

        try:
            conn.execute("""
                INSERT OR REPLACE INTO minute_stats
                (timestamp, cpu_avg, cpu_min, cpu_max, ram_avg, ram_min, ram_max,
                 gpu_avg, gpu_min, gpu_max, cpu_temp, gpu_temp, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, round(cpu_avg, 2), round(cpu_min, 2), round(cpu_max, 2),
                  round(ram_avg, 2), round(ram_min, 2), round(ram_max, 2),
                  round(gpu_avg, 2), round(gpu_min, 2), round(gpu_max, 2),
                  round(cpu_temp, 1) if cpu_temp else None,
                  round(gpu_temp, 1) if gpu_temp else None,
                  sample_count))
            conn.commit()
        except Exception as e:
            print(f"[StatsAggregator] Insert minute error: {e}")

    def _aggregate_hour(self, hour_ts):
        """Aggregate minute_stats for a given hour into hourly_stats"""
        conn = db_manager.get_connection()
        if not conn:
            return

        hour_end = hour_ts + SECONDS_PER_HOUR

        try:
            rows = conn.execute("""
                SELECT cpu_avg, cpu_min, cpu_max, ram_avg, ram_min, ram_max,
                       gpu_avg, gpu_min, gpu_max, cpu_temp, gpu_temp, sample_count
                FROM minute_stats
                WHERE timestamp >= ? AND timestamp < ?
            """, (hour_ts, hour_end)).fetchall()

            if not rows:
                return

            # Compute aggregates
            cpu_avgs = [r['cpu_avg'] for r in rows]
            cpu_mins = [r['cpu_min'] for r in rows]
            cpu_maxs = [r['cpu_max'] for r in rows]
            ram_avgs = [r['ram_avg'] for r in rows]
            ram_mins = [r['ram_min'] for r in rows]
            ram_maxs = [r['ram_max'] for r in rows]
            gpu_avgs = [r['gpu_avg'] for r in rows]
            gpu_mins = [r['gpu_min'] for r in rows]
            gpu_maxs = [r['gpu_max'] for r in rows]
            total_samples = sum(r['sample_count'] for r in rows)

            # P95 for CPU
            sorted_cpu = sorted(cpu_avgs)
            p95_idx = int(len(sorted_cpu) * 0.95)
            cpu_p95 = sorted_cpu[min(p95_idx, len(sorted_cpu) - 1)]

            # Temp averages (may be NULL)
            cpu_temps = [r['cpu_temp'] for r in rows if r['cpu_temp'] is not None]
            gpu_temps = [r['gpu_temp'] for r in rows if r['gpu_temp'] is not None]
            cpu_temp_avg = sum(cpu_temps) / len(cpu_temps) if cpu_temps else None
            gpu_temp_avg = sum(gpu_temps) / len(gpu_temps) if gpu_temps else None

            conn.execute("""
                INSERT OR REPLACE INTO hourly_stats
                (timestamp, cpu_avg, cpu_min, cpu_max, cpu_p95,
                 ram_avg, ram_min, ram_max, gpu_avg, gpu_min, gpu_max,
                 cpu_temp_avg, gpu_temp_avg, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (hour_ts,
                  round(sum(cpu_avgs) / len(cpu_avgs), 2),
                  round(min(cpu_mins), 2), round(max(cpu_maxs), 2), round(cpu_p95, 2),
                  round(sum(ram_avgs) / len(ram_avgs), 2),
                  round(min(ram_mins), 2), round(max(ram_maxs), 2),
                  round(sum(gpu_avgs) / len(gpu_avgs), 2),
                  round(min(gpu_mins), 2), round(max(gpu_maxs), 2),
                  round(cpu_temp_avg, 1) if cpu_temp_avg else None,
                  round(gpu_temp_avg, 1) if gpu_temp_avg else None,
                  total_samples))
            conn.commit()

            # Also aggregate processes for this hour
            if self._process_aggregator:
                try:
                    self._process_aggregator.flush_hourly_processes(hour_ts)
                except Exception as e:
                    print(f"[StatsAggregator] Process hourly flush error: {e}")

            print(f"[StatsAggregator] Hourly aggregation done for {datetime.fromtimestamp(hour_ts).strftime('%Y-%m-%d %H:00')}")

        except Exception as e:
            print(f"[StatsAggregator] Hourly aggregation error: {e}")

    def _aggregate_day(self, day_ts):
        """Aggregate hourly_stats for a given day into daily_stats"""
        conn = db_manager.get_connection()
        if not conn:
            return

        day_end = day_ts + SECONDS_PER_DAY
        date_str = datetime.fromtimestamp(day_ts, tz=timezone.utc).strftime('%Y-%m-%d')

        try:
            rows = conn.execute("""
                SELECT cpu_avg, cpu_min, cpu_max, cpu_p95,
                       ram_avg, ram_min, ram_max, gpu_avg, gpu_min, gpu_max,
                       cpu_temp_avg, gpu_temp_avg, sample_count
                FROM hourly_stats
                WHERE timestamp >= ? AND timestamp < ?
            """, (day_ts, day_end)).fetchall()

            if not rows:
                return

            cpu_avgs = [r['cpu_avg'] for r in rows]
            ram_avgs = [r['ram_avg'] for r in rows]
            gpu_avgs = [r['gpu_avg'] for r in rows]
            total_samples = sum(r['sample_count'] for r in rows)
            uptime_minutes = len(rows) * 60  # Each hourly row = 60 min

            cpu_temps = [r['cpu_temp_avg'] for r in rows if r['cpu_temp_avg'] is not None]
            gpu_temps = [r['gpu_temp_avg'] for r in rows if r['gpu_temp_avg'] is not None]

            sorted_cpu = sorted(cpu_avgs)
            cpu_p95 = sorted_cpu[int(len(sorted_cpu) * 0.95)] if sorted_cpu else 0

            conn.execute("""
                INSERT OR REPLACE INTO daily_stats
                (date_str, timestamp, cpu_avg, cpu_min, cpu_max, cpu_p95,
                 ram_avg, ram_min, ram_max, gpu_avg, gpu_min, gpu_max,
                 cpu_temp_avg, gpu_temp_avg, uptime_minutes, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_str, day_ts,
                  round(sum(cpu_avgs) / len(cpu_avgs), 2),
                  round(min(r['cpu_min'] for r in rows), 2),
                  round(max(r['cpu_max'] for r in rows), 2),
                  round(cpu_p95, 2),
                  round(sum(ram_avgs) / len(ram_avgs), 2),
                  round(min(r['ram_min'] for r in rows), 2),
                  round(max(r['ram_max'] for r in rows), 2),
                  round(sum(gpu_avgs) / len(gpu_avgs), 2),
                  round(min(r['gpu_min'] for r in rows), 2),
                  round(max(r['gpu_max'] for r in rows), 2),
                  round(sum(cpu_temps) / len(cpu_temps), 1) if cpu_temps else None,
                  round(sum(gpu_temps) / len(gpu_temps), 1) if gpu_temps else None,
                  uptime_minutes, total_samples))
            conn.commit()

            # Also aggregate daily processes
            if self._process_aggregator:
                try:
                    self._process_aggregator.aggregate_daily_processes(day_ts, date_str)
                except Exception as e:
                    print(f"[StatsAggregator] Process daily agg error: {e}")

            print(f"[StatsAggregator] Daily aggregation done for {date_str}")

        except Exception as e:
            print(f"[StatsAggregator] Daily aggregation error: {e}")

    def _check_weekly_monthly(self, day_ts):
        """Check if we need weekly/monthly aggregation"""
        conn = db_manager.get_connection()
        if not conn:
            return

        dt = datetime.fromtimestamp(day_ts, tz=timezone.utc)

        # Weekly: aggregate if Monday
        if dt.weekday() == 0:  # Monday
            self._aggregate_weekly(day_ts, dt)

        # Monthly: aggregate if 1st of month
        if dt.day == 1:
            self._aggregate_monthly(day_ts, dt)

    def _aggregate_weekly(self, week_start_ts, dt):
        """Aggregate daily_stats for the previous week"""
        conn = db_manager.get_connection()
        if not conn:
            return

        week_end_ts = week_start_ts
        prev_week_start = week_start_ts - 7 * SECONDS_PER_DAY
        week_str = datetime.fromtimestamp(prev_week_start, tz=timezone.utc).strftime('%Y-W%W')

        try:
            rows = conn.execute("""
                SELECT cpu_avg, cpu_min, cpu_max, ram_avg, ram_min, ram_max,
                       gpu_avg, gpu_min, gpu_max, cpu_temp_avg, gpu_temp_avg,
                       uptime_minutes, sample_count
                FROM daily_stats
                WHERE timestamp >= ? AND timestamp < ?
            """, (prev_week_start, week_end_ts)).fetchall()

            if not rows:
                return

            total_samples = sum(r['sample_count'] for r in rows)
            total_uptime = sum(r['uptime_minutes'] or 0 for r in rows)

            conn.execute("""
                INSERT OR REPLACE INTO weekly_stats
                (week_str, timestamp, cpu_avg, cpu_min, cpu_max,
                 ram_avg, ram_min, ram_max, gpu_avg, gpu_min, gpu_max,
                 cpu_temp_avg, gpu_temp_avg, uptime_minutes, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (week_str, prev_week_start,
                  round(sum(r['cpu_avg'] for r in rows) / len(rows), 2),
                  round(min(r['cpu_min'] for r in rows), 2),
                  round(max(r['cpu_max'] for r in rows), 2),
                  round(sum(r['ram_avg'] for r in rows) / len(rows), 2),
                  round(min(r['ram_min'] for r in rows), 2),
                  round(max(r['ram_max'] for r in rows), 2),
                  round(sum(r['gpu_avg'] for r in rows) / len(rows), 2),
                  round(min(r['gpu_min'] for r in rows), 2),
                  round(max(r['gpu_max'] for r in rows), 2),
                  None, None, total_uptime, total_samples))
            conn.commit()
            print(f"[StatsAggregator] Weekly aggregation done for {week_str}")

        except Exception as e:
            print(f"[StatsAggregator] Weekly aggregation error: {e}")

    def _aggregate_monthly(self, month_start_ts, dt):
        """Aggregate daily_stats for the previous month"""
        conn = db_manager.get_connection()
        if not conn:
            return

        # Previous month
        if dt.month == 1:
            prev_month = 12
            prev_year = dt.year - 1
        else:
            prev_month = dt.month - 1
            prev_year = dt.year

        month_str = f"{prev_year}-{prev_month:02d}"
        prev_start = datetime(prev_year, prev_month, 1, tzinfo=timezone.utc).timestamp()

        try:
            rows = conn.execute("""
                SELECT cpu_avg, cpu_min, cpu_max, ram_avg, ram_min, ram_max,
                       gpu_avg, gpu_min, gpu_max, uptime_minutes, sample_count
                FROM daily_stats
                WHERE timestamp >= ? AND timestamp < ?
            """, (prev_start, month_start_ts)).fetchall()

            if not rows:
                return

            total_samples = sum(r['sample_count'] for r in rows)
            total_uptime = sum(r['uptime_minutes'] or 0 for r in rows)

            conn.execute("""
                INSERT OR REPLACE INTO monthly_stats
                (month_str, timestamp, cpu_avg, cpu_min, cpu_max,
                 ram_avg, ram_min, ram_max, gpu_avg, gpu_min, gpu_max,
                 cpu_temp_avg, gpu_temp_avg, uptime_minutes, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (month_str, prev_start,
                  round(sum(r['cpu_avg'] for r in rows) / len(rows), 2),
                  round(min(r['cpu_min'] for r in rows), 2),
                  round(max(r['cpu_max'] for r in rows), 2),
                  round(sum(r['ram_avg'] for r in rows) / len(rows), 2),
                  round(min(r['ram_min'] for r in rows), 2),
                  round(max(r['ram_max'] for r in rows), 2),
                  round(sum(r['gpu_avg'] for r in rows) / len(rows), 2),
                  round(min(r['gpu_min'] for r in rows), 2),
                  round(max(r['gpu_max'] for r in rows), 2),
                  None, None, total_uptime, total_samples))
            conn.commit()
            print(f"[StatsAggregator] Monthly aggregation done for {month_str}")

        except Exception as e:
            print(f"[StatsAggregator] Monthly aggregation error: {e}")

    def _run_pruning(self):
        """Delete old data per retention policy"""
        conn = db_manager.get_connection()
        if not conn:
            return

        now = time.time()

        try:
            # Prune minute_stats (7 days)
            conn.execute("DELETE FROM minute_stats WHERE timestamp < ?",
                        (now - RETENTION_MINUTES,))

            # Prune hourly_stats (90 days)
            conn.execute("DELETE FROM hourly_stats WHERE timestamp < ?",
                        (now - RETENTION_HOURLY,))

            # Prune process_hourly_stats (90 days)
            conn.execute("DELETE FROM process_hourly_stats WHERE timestamp < ?",
                        (now - RETENTION_PROCESS_HOURLY,))

            conn.commit()

            # Prune raw CSV
            self._prune_raw_csv()

            print(f"[StatsAggregator] Pruning completed")

        except Exception as e:
            print(f"[StatsAggregator] Pruning error: {e}")

    def _prune_raw_csv(self):
        """Truncate raw_usage.csv to last 24 hours"""
        csv_path = os.path.join(LOGS_DIR, "raw_usage.csv")
        if not os.path.exists(csv_path):
            return

        try:
            cutoff = time.time() - RETENTION_RAW_CSV
            kept_lines = []
            header = None

            with open(csv_path, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    kept_lines.append(header)

                for row in reader:
                    try:
                        ts = float(row[0])
                        if ts >= cutoff:
                            kept_lines.append(row)
                    except (ValueError, IndexError):
                        continue

            # Write back atomically
            tmp_path = csv_path + ".tmp"
            with open(tmp_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(kept_lines)

            os.replace(tmp_path, csv_path)

        except Exception as e:
            print(f"[StatsAggregator] CSV pruning error: {e}")

    def flush_on_shutdown(self):
        """Flush any pending data before app exit"""
        try:
            if self._process_aggregator:
                self._process_aggregator.flush_all()
            print("[StatsAggregator] Shutdown flush completed")
        except Exception as e:
            print(f"[StatsAggregator] Shutdown flush error: {e}")


# Singleton instance
aggregator = StatsAggregator()
