"""
HCK Stats Engine v2 - Query API
Read interface for UI charts and data display.
Automatically selects optimal data granularity based on requested time range.
"""

import time
from datetime import datetime, timezone

from hck_stats_engine.constants import (
    SECONDS_PER_HOUR, SECONDS_PER_DAY, SECONDS_PER_WEEK
)
from hck_stats_engine.db_manager import db_manager


class StatsQueryAPI:
    """Read-only query interface for historical statistics"""

    def __init__(self):
        print("[StatsQueryAPI] Initialized")

    def get_usage_for_range(self, start_ts, end_ts, max_points=500):
        """Get system usage data for a time range with automatic granularity.

        Auto-selects the best table based on range duration:
          - <=2 hours: minute_stats (~120 points)
          - <=2 days: minute_stats (downsampled if needed)
          - <=14 days: hourly_stats (~336 points)
          - <=120 days: daily_stats (~120 points)
          - >120 days: monthly_stats

        Args:
            start_ts: Start Unix timestamp
            end_ts: End Unix timestamp
            max_points: Maximum data points to return (for UI performance)

        Returns:
            list of dicts: [{timestamp, cpu_avg, cpu_min, cpu_max, ram_avg, ram_min,
                            ram_max, gpu_avg, gpu_min, gpu_max}, ...]
            Empty list if no data or database unavailable.
        """
        if not db_manager.is_ready:
            return []

        conn = db_manager.get_connection()
        if not conn:
            return []

        duration = end_ts - start_ts

        try:
            if duration <= 2 * SECONDS_PER_DAY:
                return self._query_minute_range(conn, start_ts, end_ts, max_points)
            elif duration <= 14 * SECONDS_PER_DAY:
                return self._query_hourly_range(conn, start_ts, end_ts, max_points)
            elif duration <= 120 * SECONDS_PER_DAY:
                return self._query_daily_range(conn, start_ts, end_ts, max_points)
            else:
                return self._query_monthly_range(conn, start_ts, end_ts, max_points)
        except Exception as e:
            print(f"[StatsQueryAPI] Query error: {e}")
            return []

    def _query_minute_range(self, conn, start_ts, end_ts, max_points):
        """Query minute_stats table"""
        rows = conn.execute("""
            SELECT timestamp, cpu_avg, cpu_min, cpu_max,
                   ram_avg, ram_min, ram_max,
                   gpu_avg, gpu_min, gpu_max,
                   cpu_temp, gpu_temp, sample_count
            FROM minute_stats
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (start_ts, end_ts)).fetchall()

        results = [self._row_to_dict(r) for r in rows]
        return self._downsample(results, max_points)

    def _query_hourly_range(self, conn, start_ts, end_ts, max_points):
        """Query hourly_stats table"""
        rows = conn.execute("""
            SELECT timestamp, cpu_avg, cpu_min, cpu_max,
                   ram_avg, ram_min, ram_max,
                   gpu_avg, gpu_min, gpu_max,
                   cpu_temp_avg as cpu_temp, gpu_temp_avg as gpu_temp, sample_count
            FROM hourly_stats
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (start_ts, end_ts)).fetchall()

        results = [self._row_to_dict(r) for r in rows]
        return self._downsample(results, max_points)

    def _query_daily_range(self, conn, start_ts, end_ts, max_points):
        """Query daily_stats table"""
        rows = conn.execute("""
            SELECT timestamp, cpu_avg, cpu_min, cpu_max,
                   ram_avg, ram_min, ram_max,
                   gpu_avg, gpu_min, gpu_max,
                   cpu_temp_avg as cpu_temp, gpu_temp_avg as gpu_temp,
                   sample_count, uptime_minutes
            FROM daily_stats
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (start_ts, end_ts)).fetchall()

        results = []
        for r in rows:
            d = self._row_to_dict(r)
            d['uptime_minutes'] = r['uptime_minutes']
            results.append(d)
        return self._downsample(results, max_points)

    def _query_monthly_range(self, conn, start_ts, end_ts, max_points):
        """Query monthly_stats table"""
        rows = conn.execute("""
            SELECT timestamp, cpu_avg, cpu_min, cpu_max,
                   ram_avg, ram_min, ram_max,
                   gpu_avg, gpu_min, gpu_max,
                   cpu_temp_avg as cpu_temp, gpu_temp_avg as gpu_temp,
                   sample_count, uptime_minutes
            FROM monthly_stats
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
        """, (start_ts, end_ts)).fetchall()

        results = []
        for r in rows:
            d = self._row_to_dict(r)
            d['uptime_minutes'] = r['uptime_minutes']
            results.append(d)
        return results

    def _row_to_dict(self, row):
        """Convert sqlite3.Row to standard dict"""
        return {
            'timestamp': row['timestamp'],
            'cpu_avg': row['cpu_avg'],
            'cpu_min': row['cpu_min'],
            'cpu_max': row['cpu_max'],
            'ram_avg': row['ram_avg'],
            'ram_min': row['ram_min'],
            'ram_max': row['ram_max'],
            'gpu_avg': row['gpu_avg'],
            'gpu_min': row['gpu_min'],
            'gpu_max': row['gpu_max'],
            'cpu_temp': row['cpu_temp'] if 'cpu_temp' in row.keys() else None,
            'gpu_temp': row['gpu_temp'] if 'gpu_temp' in row.keys() else None,
            'sample_count': row['sample_count'],
        }

    def _downsample(self, data, max_points):
        """Reduce number of data points if exceeding max_points.
        Uses simple nth-element selection to preserve data shape.
        """
        if len(data) <= max_points:
            return data

        step = len(data) / max_points
        result = []
        idx = 0.0
        while idx < len(data):
            result.append(data[int(idx)])
            idx += step

        # Always include last point
        if result and result[-1] != data[-1]:
            result.append(data[-1])

        return result

    # =========================================================
    # Process queries
    # =========================================================

    def get_process_breakdown(self, hour_ts=None, top_n=10):
        """Get top processes for a specific hour.

        Args:
            hour_ts: Hour timestamp (default: current hour from in-memory data)
            top_n: Number of top processes

        Returns:
            list of dicts: [{process_name, display_name, cpu_avg, cpu_max,
                            ram_avg_mb, ram_max_mb, active_seconds, category}, ...]
        """
        if not db_manager.is_ready:
            return []

        conn = db_manager.get_connection()
        if not conn:
            return []

        if hour_ts is None:
            hour_ts = int(time.time() // SECONDS_PER_HOUR) * SECONDS_PER_HOUR

        try:
            rows = conn.execute("""
                SELECT process_name, display_name, process_type, category,
                       cpu_avg, cpu_max, ram_avg_mb, ram_max_mb,
                       sample_count, active_seconds
                FROM process_hourly_stats
                WHERE timestamp = ?
                ORDER BY cpu_avg DESC
                LIMIT ?
            """, (hour_ts, top_n)).fetchall()

            return [{
                'process_name': r['process_name'],
                'display_name': r['display_name'] or r['process_name'],
                'process_type': r['process_type'],
                'category': r['category'],
                'cpu_avg': r['cpu_avg'],
                'cpu_max': r['cpu_max'],
                'ram_avg_mb': r['ram_avg_mb'],
                'ram_max_mb': r['ram_max_mb'],
                'active_seconds': r['active_seconds'],
                'sample_count': r['sample_count'],
            } for r in rows]

        except Exception as e:
            print(f"[StatsQueryAPI] Process breakdown error: {e}")
            return []

    def get_process_daily_breakdown(self, date_str=None, top_n=10):
        """Get top processes for a specific day.

        Args:
            date_str: Date string like '2025-01-15' (default: today)
            top_n: Number of top processes

        Returns:
            list of dicts
        """
        if not db_manager.is_ready:
            return []

        conn = db_manager.get_connection()
        if not conn:
            return []

        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        try:
            rows = conn.execute("""
                SELECT process_name, display_name, process_type, category,
                       cpu_avg, cpu_max, ram_avg_mb, ram_max_mb,
                       total_active_seconds, sample_count
                FROM process_daily_stats
                WHERE date_str = ?
                ORDER BY cpu_avg DESC
                LIMIT ?
            """, (date_str, top_n)).fetchall()

            return [{
                'process_name': r['process_name'],
                'display_name': r['display_name'] or r['process_name'],
                'process_type': r['process_type'],
                'category': r['category'],
                'cpu_avg': r['cpu_avg'],
                'cpu_max': r['cpu_max'],
                'ram_avg_mb': r['ram_avg_mb'],
                'ram_max_mb': r['ram_max_mb'],
                'total_active_seconds': r['total_active_seconds'],
                'sample_count': r['sample_count'],
            } for r in rows]

        except Exception as e:
            print(f"[StatsQueryAPI] Process daily error: {e}")
            return []

    def get_process_timeline(self, process_name, start_ts, end_ts):
        """Get usage timeline for a specific process.

        Args:
            process_name: Process name to track
            start_ts: Start timestamp
            end_ts: End timestamp

        Returns:
            list of dicts: [{timestamp, cpu_avg, cpu_max, ram_avg_mb, ram_max_mb}, ...]
        """
        if not db_manager.is_ready:
            return []

        conn = db_manager.get_connection()
        if not conn:
            return []

        duration = end_ts - start_ts

        try:
            if duration <= 3 * SECONDS_PER_DAY:
                # Use hourly data
                rows = conn.execute("""
                    SELECT timestamp, cpu_avg, cpu_max, ram_avg_mb, ram_max_mb,
                           active_seconds
                    FROM process_hourly_stats
                    WHERE process_name = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                """, (process_name.lower(), start_ts, end_ts)).fetchall()
            else:
                # Use daily data
                rows = conn.execute("""
                    SELECT timestamp, cpu_avg, cpu_max, ram_avg_mb, ram_max_mb,
                           total_active_seconds as active_seconds
                    FROM process_daily_stats
                    WHERE process_name = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC
                """, (process_name.lower(), start_ts, end_ts)).fetchall()

            return [{
                'timestamp': r['timestamp'],
                'cpu_avg': r['cpu_avg'],
                'cpu_max': r['cpu_max'],
                'ram_avg_mb': r['ram_avg_mb'],
                'ram_max_mb': r['ram_max_mb'],
                'active_seconds': r['active_seconds'],
            } for r in rows]

        except Exception as e:
            print(f"[StatsQueryAPI] Process timeline error: {e}")
            return []

    # =========================================================
    # Metadata / Info queries
    # =========================================================

    def get_available_date_range(self):
        """Get the earliest and latest timestamps in the database.

        Returns:
            dict: {earliest_ts, latest_ts, earliest_date, latest_date, total_days}
            None if no data
        """
        if not db_manager.is_ready:
            return None

        conn = db_manager.get_connection()
        if not conn:
            return None

        try:
            # Check across all time-series tables
            earliest = None
            latest = None

            for table in ['minute_stats', 'hourly_stats', 'daily_stats']:
                row = conn.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table}").fetchone()
                if row and row[0] is not None:
                    if earliest is None or row[0] < earliest:
                        earliest = row[0]
                    if latest is None or row[1] > latest:
                        latest = row[1]

            if earliest is None:
                return None

            return {
                'earliest_ts': earliest,
                'latest_ts': latest,
                'earliest_date': datetime.fromtimestamp(earliest).strftime('%Y-%m-%d'),
                'latest_date': datetime.fromtimestamp(latest).strftime('%Y-%m-%d'),
                'total_days': int((latest - earliest) / SECONDS_PER_DAY) + 1,
            }

        except Exception as e:
            print(f"[StatsQueryAPI] Date range error: {e}")
            return None

    def get_events(self, start_ts=None, end_ts=None, event_type=None,
                   severity=None, limit=50):
        """Get events/alerts from the events table.

        Args:
            start_ts: Optional start filter
            end_ts: Optional end filter
            event_type: Optional type filter ('spike', 'anomaly', etc.)
            severity: Optional severity filter ('info', 'warning', 'critical')
            limit: Max events to return

        Returns:
            list of dicts
        """
        if not db_manager.is_ready:
            return []

        conn = db_manager.get_connection()
        if not conn:
            return []

        try:
            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if start_ts is not None:
                query += " AND timestamp >= ?"
                params.append(start_ts)
            if end_ts is not None:
                query += " AND timestamp <= ?"
                params.append(end_ts)
            if event_type is not None:
                query += " AND event_type = ?"
                params.append(event_type)
            if severity is not None:
                query += " AND severity = ?"
                params.append(severity)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

            return [{
                'id': r['id'],
                'timestamp': r['timestamp'],
                'event_type': r['event_type'],
                'severity': r['severity'],
                'metric': r['metric'],
                'value': r['value'],
                'baseline': r['baseline'],
                'process_name': r['process_name'],
                'description': r['description'],
                'resolved_at': r['resolved_at'],
            } for r in rows]

        except Exception as e:
            print(f"[StatsQueryAPI] Events query error: {e}")
            return []

    def get_summary_stats(self, days=7):
        """Get summary statistics for the last N days.

        Uses daily_stats when available, falls back to hourly_stats and
        minute_stats so that lifetime uptime is computed even before
        the first day-boundary aggregation.

        Args:
            days: Number of days to summarize

        Returns:
            dict: {cpu_avg, ram_avg, gpu_avg, cpu_max, ram_max, gpu_max,
                   total_uptime_hours, data_points, days_with_data}
        """
        if not db_manager.is_ready:
            return {}

        conn = db_manager.get_connection()
        if not conn:
            return {}

        cutoff = time.time() - days * SECONDS_PER_DAY

        try:
            # --- Primary: daily_stats ---
            rows = conn.execute("""
                SELECT cpu_avg, cpu_max, ram_avg, ram_max, gpu_avg, gpu_max,
                       uptime_minutes, sample_count
                FROM daily_stats
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (cutoff,)).fetchall()

            daily_uptime_min = 0
            daily_samples = 0
            daily_days = 0

            if rows:
                daily_uptime_min = sum(r['uptime_minutes'] or 0 for r in rows)
                daily_samples = sum(r['sample_count'] for r in rows)
                daily_days = len(rows)

            # --- Supplement: hourly_stats (hours not yet rolled into daily) ---
            # Find the latest daily_stats timestamp so we only count
            # hourly data that hasn't been aggregated yet.
            latest_daily_ts = 0
            if rows:
                latest_daily_ts = max(r['uptime_minutes'] for r in rows) if False else 0
            try:
                ld_row = conn.execute(
                    "SELECT MAX(timestamp) as t FROM daily_stats WHERE timestamp >= ?",
                    (cutoff,)).fetchone()
                if ld_row and ld_row['t']:
                    latest_daily_ts = ld_row['t'] + SECONDS_PER_DAY
            except Exception:
                pass

            hourly_uptime_min = 0
            hourly_rows = []
            try:
                hourly_cutoff = max(cutoff, latest_daily_ts)
                hourly_rows = conn.execute("""
                    SELECT cpu_avg, cpu_max, ram_avg, ram_max, gpu_avg, gpu_max,
                           sample_count
                    FROM hourly_stats
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (hourly_cutoff,)).fetchall()
                if hourly_rows:
                    # Each hourly row's sample_count = minutes of data
                    hourly_uptime_min = sum(r['sample_count'] for r in hourly_rows)
            except Exception:
                pass

            # --- Supplement: minute_stats (current hour, not yet in hourly) ---
            minute_uptime_min = 0
            minute_rows = []
            try:
                latest_hourly_ts = 0
                lh_row = conn.execute(
                    "SELECT MAX(timestamp) as t FROM hourly_stats WHERE timestamp >= ?",
                    (cutoff,)).fetchone()
                if lh_row and lh_row['t']:
                    latest_hourly_ts = lh_row['t'] + SECONDS_PER_HOUR

                minute_cutoff = max(cutoff, latest_daily_ts, latest_hourly_ts)
                minute_rows = conn.execute("""
                    SELECT cpu_avg, cpu_max, ram_avg, ram_max, gpu_avg, gpu_max,
                           sample_count
                    FROM minute_stats
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (minute_cutoff,)).fetchall()
                if minute_rows:
                    # Each minute_stats row = ~1 minute of uptime
                    minute_uptime_min = len(minute_rows)
            except Exception:
                pass

            # Combine all rows for averages/peaks
            all_rows = list(rows) + list(hourly_rows) + list(minute_rows)
            if not all_rows:
                return {}

            total_uptime_min = daily_uptime_min + hourly_uptime_min + minute_uptime_min
            total_samples = sum(r['sample_count'] for r in all_rows)

            return {
                'cpu_avg': round(sum(r['cpu_avg'] for r in all_rows) / len(all_rows), 2),
                'ram_avg': round(sum(r['ram_avg'] for r in all_rows) / len(all_rows), 2),
                'gpu_avg': round(sum(r['gpu_avg'] for r in all_rows) / len(all_rows), 2),
                'cpu_max': round(max(r['cpu_max'] for r in all_rows), 2),
                'ram_max': round(max(r['ram_max'] for r in all_rows), 2),
                'gpu_max': round(max(r['gpu_max'] for r in all_rows), 2),
                'total_uptime_hours': round(total_uptime_min / 60, 1),
                'data_points': total_samples,
                'days_with_data': max(daily_days, 1),
            }

        except Exception as e:
            print(f"[StatsQueryAPI] Summary error: {e}")
            return {}


# Singleton instance
query_api = StatsQueryAPI()
