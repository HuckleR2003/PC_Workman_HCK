"""
HCK Stats Engine v2 - Process Aggregator
Per-process usage accumulation and aggregation to SQLite
"""

import time
from collections import defaultdict
from datetime import datetime, timezone

from hck_stats_engine.constants import SECONDS_PER_HOUR, SECONDS_PER_DAY
from hck_stats_engine.db_manager import db_manager


class ProcessAggregator:
    """Accumulates per-process usage data and flushes to SQLite on hour/day boundaries"""

    def __init__(self):
        # In-memory accumulator: {(hour_ts, process_name): stats_dict}
        self._hourly_accum = defaultdict(lambda: {
            'cpu_sum': 0.0,
            'cpu_max': 0.0,
            'ram_sum_mb': 0.0,
            'ram_max_mb': 0.0,
            'sample_count': 0,
            'active_seconds': 0,
            'display_name': None,
            'process_type': None,
            'category': None,
        })
        self._current_hour = int(time.time() // SECONDS_PER_HOUR) * SECONDS_PER_HOUR
        print("[ProcessAggregator] Initialized")

    def accumulate_second(self, processes_list, classifier=None):
        """Called every second with current process snapshot.

        Args:
            processes_list: List of dicts [{name, cpu_percent, ram_MB, ...}, ...]
            classifier: Optional ProcessClassifier for metadata
        """
        now = time.time()
        hour_ts = int(now // SECONDS_PER_HOUR) * SECONDS_PER_HOUR

        # Check if we crossed an hour boundary
        if hour_ts > self._current_hour:
            # Flush the completed hour before accumulating new data
            try:
                self.flush_hourly_processes(self._current_hour)
            except Exception as e:
                print(f"[ProcessAggregator] Auto-flush error: {e}")
            self._current_hour = hour_ts

        for proc in processes_list:
            proc_name = proc.get('name', 'unknown').lower()
            cpu = proc.get('cpu_percent', 0.0)
            ram = proc.get('ram_MB', 0.0)

            # Skip idle processes (saves memory)
            if cpu < 0.1 and ram < 1.0:
                continue

            key = (hour_ts, proc_name)
            acc = self._hourly_accum[key]
            acc['cpu_sum'] += cpu
            acc['cpu_max'] = max(acc['cpu_max'], cpu)
            acc['ram_sum_mb'] += ram
            acc['ram_max_mb'] = max(acc['ram_max_mb'], ram)
            acc['sample_count'] += 1
            acc['active_seconds'] += 1

            # Store classification metadata (first time or update)
            if acc['display_name'] is None and classifier:
                try:
                    info = classifier.classify_process(proc_name)
                    acc['display_name'] = info.get('display_name', proc_name)
                    acc['process_type'] = info.get('type', 'unknown')
                    acc['category'] = info.get('category', 'Unknown')
                except Exception:
                    acc['display_name'] = proc_name

    def flush_hourly_processes(self, hour_ts):
        """Write accumulated process data for given hour to SQLite.

        Args:
            hour_ts: Hour boundary timestamp to flush
        """
        if not db_manager.is_ready:
            return

        conn = db_manager.get_connection()
        if not conn:
            return

        # Collect all entries for this hour
        entries_to_flush = []
        keys_to_remove = []

        for key, acc in self._hourly_accum.items():
            if key[0] == hour_ts:
                entries_to_flush.append((key[1], acc))
                keys_to_remove.append(key)

        if not entries_to_flush:
            return

        try:
            for proc_name, acc in entries_to_flush:
                if acc['sample_count'] == 0:
                    continue

                cpu_avg = round(acc['cpu_sum'] / acc['sample_count'], 2)
                ram_avg = round(acc['ram_sum_mb'] / acc['sample_count'], 2)

                conn.execute("""
                    INSERT INTO process_hourly_stats
                    (timestamp, process_name, display_name, process_type, category,
                     cpu_avg, cpu_max, ram_avg_mb, ram_max_mb, sample_count, active_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (hour_ts, proc_name,
                      acc['display_name'] or proc_name,
                      acc['process_type'],
                      acc['category'],
                      cpu_avg,
                      round(acc['cpu_max'], 2),
                      ram_avg,
                      round(acc['ram_max_mb'], 2),
                      acc['sample_count'],
                      acc['active_seconds']))

            conn.commit()

            # Remove flushed entries from memory
            for key in keys_to_remove:
                del self._hourly_accum[key]

            print(f"[ProcessAggregator] Flushed {len(entries_to_flush)} processes for "
                  f"{datetime.fromtimestamp(hour_ts).strftime('%Y-%m-%d %H:00')}")

        except Exception as e:
            print(f"[ProcessAggregator] Hourly flush error: {e}")

    def aggregate_daily_processes(self, day_ts, date_str):
        """Aggregate process_hourly_stats for a day into process_daily_stats.

        Args:
            day_ts: Day boundary timestamp
            date_str: Date string like '2025-01-15'
        """
        if not db_manager.is_ready:
            return

        conn = db_manager.get_connection()
        if not conn:
            return

        day_end = day_ts + SECONDS_PER_DAY

        try:
            rows = conn.execute("""
                SELECT process_name, display_name, process_type, category,
                       SUM(cpu_avg * sample_count) as cpu_weighted_sum,
                       MAX(cpu_max) as cpu_max,
                       SUM(ram_avg_mb * sample_count) as ram_weighted_sum,
                       MAX(ram_max_mb) as ram_max_mb,
                       SUM(active_seconds) as total_active,
                       SUM(sample_count) as total_samples
                FROM process_hourly_stats
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY process_name
            """, (day_ts, day_end)).fetchall()

            if not rows:
                return

            for row in rows:
                total_samples = row['total_samples']
                if total_samples == 0:
                    continue

                cpu_avg = round(row['cpu_weighted_sum'] / total_samples, 2)
                ram_avg = round(row['ram_weighted_sum'] / total_samples, 2)

                conn.execute("""
                    INSERT OR REPLACE INTO process_daily_stats
                    (date_str, timestamp, process_name, display_name, process_type,
                     category, cpu_avg, cpu_max, ram_avg_mb, ram_max_mb,
                     total_active_seconds, sample_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (date_str, day_ts,
                      row['process_name'],
                      row['display_name'],
                      row['process_type'],
                      row['category'],
                      cpu_avg,
                      round(row['cpu_max'], 2),
                      ram_avg,
                      round(row['ram_max_mb'], 2),
                      row['total_active'],
                      total_samples))

            conn.commit()
            print(f"[ProcessAggregator] Daily process aggregation done for {date_str}")

        except Exception as e:
            print(f"[ProcessAggregator] Daily aggregation error: {e}")

    def flush_all(self):
        """Flush all accumulated data (called on shutdown)"""
        try:
            # Flush current hour's data
            self.flush_hourly_processes(self._current_hour)

            # Flush any remaining hours (shouldn't happen but safety)
            remaining_hours = set(key[0] for key in self._hourly_accum.keys())
            for hour_ts in remaining_hours:
                self.flush_hourly_processes(hour_ts)

            print("[ProcessAggregator] Shutdown flush completed")
        except Exception as e:
            print(f"[ProcessAggregator] Shutdown flush error: {e}")

    def get_current_hour_top(self, n=10):
        """Get top N processes for the current hour (from in-memory accumulator).

        Returns:
            list: [{name, display_name, cpu_avg, ram_avg_mb, active_seconds}, ...]
        """
        results = []
        for key, acc in self._hourly_accum.items():
            if key[0] == self._current_hour and acc['sample_count'] > 0:
                results.append({
                    'name': key[1],
                    'display_name': acc['display_name'] or key[1],
                    'process_type': acc['process_type'],
                    'category': acc['category'],
                    'cpu_avg': round(acc['cpu_sum'] / acc['sample_count'], 2),
                    'cpu_max': round(acc['cpu_max'], 2),
                    'ram_avg_mb': round(acc['ram_sum_mb'] / acc['sample_count'], 2),
                    'ram_max_mb': round(acc['ram_max_mb'], 2),
                    'active_seconds': acc['active_seconds'],
                })

        results.sort(key=lambda x: x['cpu_avg'], reverse=True)
        return results[:n]


# Singleton instance
process_aggregator = ProcessAggregator()
