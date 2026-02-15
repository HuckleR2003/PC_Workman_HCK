"""
HCK Stats Engine v2 - Events & Spike Detection
Detects anomalous usage spikes and logs them to the events table.
"""

import time

from hck_stats_engine.constants import (
    SPIKE_THRESHOLD_CPU, SPIKE_THRESHOLD_RAM, SPIKE_THRESHOLD_GPU,
    SPIKE_THRESHOLD_TEMP, SPIKE_COOLDOWN, SPIKE_BASELINE_WINDOW
)
from hck_stats_engine.db_manager import db_manager


class EventDetector:
    """Detects usage spikes by comparing current values against recent baselines"""

    def __init__(self):
        # Rate limiting: {metric_name: last_event_timestamp}
        self._last_event_time = {}
        self._baseline_cache = {}
        self._baseline_cache_time = 0
        print("[EventDetector] Initialized")

    def check_and_log_spike(self, cpu_avg, ram_avg, gpu_avg,
                            cpu_temp=None, gpu_temp=None):
        """Check current values against baselines and log spikes.

        Called every minute tick. Rate-limited to max 1 event per metric
        per SPIKE_COOLDOWN seconds.

        Args:
            cpu_avg: Current CPU usage %
            ram_avg: Current RAM usage %
            gpu_avg: Current GPU usage %
            cpu_temp: Optional CPU temperature
            gpu_temp: Optional GPU temperature
        """
        if not db_manager.is_ready:
            return

        now = time.time()
        baseline = self._get_baseline(now)

        if not baseline:
            return  # Not enough data for comparison

        # Check each metric
        self._check_metric(now, 'cpu', cpu_avg, baseline.get('cpu_avg', 0),
                          SPIKE_THRESHOLD_CPU, 'CPU usage')
        self._check_metric(now, 'ram', ram_avg, baseline.get('ram_avg', 0),
                          SPIKE_THRESHOLD_RAM, 'RAM usage')
        self._check_metric(now, 'gpu', gpu_avg, baseline.get('gpu_avg', 0),
                          SPIKE_THRESHOLD_GPU, 'GPU usage')

        if cpu_temp is not None and baseline.get('cpu_temp') is not None:
            self._check_metric(now, 'cpu_temp', cpu_temp, baseline['cpu_temp'],
                              SPIKE_THRESHOLD_TEMP, 'CPU temperature')
        if gpu_temp is not None and baseline.get('gpu_temp') is not None:
            self._check_metric(now, 'gpu_temp', gpu_temp, baseline['gpu_temp'],
                              SPIKE_THRESHOLD_TEMP, 'GPU temperature')

    def _check_metric(self, now, metric_name, current_val, baseline_val,
                      threshold, description):
        """Check if a metric exceeds its threshold above baseline"""
        delta = current_val - baseline_val

        if delta < threshold:
            return  # No spike

        # Rate limiting
        last_time = self._last_event_time.get(metric_name, 0)
        if now - last_time < SPIKE_COOLDOWN:
            return  # Too soon since last event for this metric

        # Determine severity
        if delta >= threshold * 2:
            severity = 'critical'
        elif delta >= threshold * 1.5:
            severity = 'warning'
        else:
            severity = 'info'

        # Log the event
        self._log_event(
            timestamp=now,
            event_type='spike',
            severity=severity,
            metric=metric_name,
            value=round(current_val, 2),
            baseline=round(baseline_val, 2),
            description=f"{description} spike: {current_val:.1f} (baseline: {baseline_val:.1f}, delta: +{delta:.1f})"
        )

        self._last_event_time[metric_name] = now

    def _get_baseline(self, now):
        """Get recent baseline averages from minute_stats.
        Cached for 60 seconds to avoid excessive queries.
        """
        if now - self._baseline_cache_time < 60 and self._baseline_cache:
            return self._baseline_cache

        conn = db_manager.get_connection()
        if not conn:
            return None

        cutoff = now - SPIKE_BASELINE_WINDOW

        try:
            rows = conn.execute("""
                SELECT AVG(cpu_avg) as cpu_avg, AVG(ram_avg) as ram_avg,
                       AVG(gpu_avg) as gpu_avg,
                       AVG(cpu_temp) as cpu_temp, AVG(gpu_temp) as gpu_temp
                FROM minute_stats
                WHERE timestamp >= ?
            """, (cutoff,)).fetchone()

            if not rows or rows['cpu_avg'] is None:
                return None

            self._baseline_cache = {
                'cpu_avg': rows['cpu_avg'],
                'ram_avg': rows['ram_avg'],
                'gpu_avg': rows['gpu_avg'],
                'cpu_temp': rows['cpu_temp'],
                'gpu_temp': rows['gpu_temp'],
            }
            self._baseline_cache_time = now
            return self._baseline_cache

        except Exception as e:
            print(f"[EventDetector] Baseline query error: {e}")
            return None

    def _log_event(self, timestamp, event_type, severity, metric,
                   value, baseline, description, process_name=None):
        """Write an event to the database"""
        conn = db_manager.get_connection()
        if not conn:
            return

        try:
            conn.execute("""
                INSERT INTO events
                (timestamp, event_type, severity, metric, value, baseline,
                 process_name, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, event_type, severity, metric, value, baseline,
                  process_name, description))
            conn.commit()
            print(f"[EventDetector] {severity.upper()}: {description}")
        except Exception as e:
            print(f"[EventDetector] Log event error: {e}")

    def log_custom_event(self, event_type, severity, description,
                         metric=None, value=None, process_name=None):
        """Log a custom event (for external use).

        Args:
            event_type: 'spike', 'anomaly', 'shutdown', 'startup', etc.
            severity: 'info', 'warning', 'critical'
            description: Human-readable description
        """
        self._log_event(
            timestamp=time.time(),
            event_type=event_type,
            severity=severity,
            metric=metric,
            value=value,
            baseline=None,
            description=description,
            process_name=process_name
        )

    def get_active_alerts_count(self):
        """Get count of unresolved events in last 24 hours.

        Returns:
            dict: {total, critical, warning, info}
        """
        if not db_manager.is_ready:
            return {'total': 0, 'critical': 0, 'warning': 0, 'info': 0}

        conn = db_manager.get_connection()
        if not conn:
            return {'total': 0, 'critical': 0, 'warning': 0, 'info': 0}

        cutoff = time.time() - 86400  # last 24h

        try:
            rows = conn.execute("""
                SELECT severity, COUNT(*) as cnt
                FROM events
                WHERE timestamp >= ? AND resolved_at IS NULL
                GROUP BY severity
            """, (cutoff,)).fetchall()

            counts = {'total': 0, 'critical': 0, 'warning': 0, 'info': 0}
            for r in rows:
                sev = r['severity']
                cnt = r['cnt']
                if sev in counts:
                    counts[sev] = cnt
                counts['total'] += cnt

            return counts

        except Exception as e:
            print(f"[EventDetector] Alert count error: {e}")
            return {'total': 0, 'critical': 0, 'warning': 0, 'info': 0}


# Singleton instance
event_detector = EventDetector()
