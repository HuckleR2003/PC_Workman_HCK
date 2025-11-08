# core/logger.py
"""
core.logger (v1.0.6 -> v1.0.6+)
- save raw per-second to raw_usage.csv 
- buffor (4h) per-second
- collect average usage and info, and updates minute_avg.csv (1H MODE)
- sharing get_last_seconds(), get_last_n_samples(), get_last_minutes()
"""

from import_core import register_component
import os, csv, time
from collections import deque
from datetime import datetime

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'logs')
os.makedirs(BASE_DIR, exist_ok=True)

RAW_CSV = os.path.join(BASE_DIR, 'raw_usage.csv')       # per-second raw
MINUTE_CSV = os.path.join(BASE_DIR, 'minute_avg.csv')  # per-minute averages (for 1H)

# config
_MAX_SECONDS_BUFFER = 4 * 3600  # keep up to 4 hours per-second
_MINUTES_BUFFER = 24 * 60       # keep up to 24 hours of minute averages (1440)

# in-memory buffers
_seconds_buffer = deque(maxlen=_MAX_SECONDS_BUFFER)  # dict rows: timestamp, iso_time, cpu_percent, ram_percent, gpu_percent
_minutes_buffer = deque(maxlen=_MINUTES_BUFFER)     # dict rows: minute_ts (start), iso_time, cpu_avg, ram_avg, gpu_avg

CSV_HEADER = ['timestamp', 'iso_time', 'cpu_percent', 'ram_percent', 'gpu_percent']
MINUTE_HEADER = ['minute_ts', 'iso_time', 'cpu_avg', 'ram_avg', 'gpu_avg']

class Logger:
    def __init__(self):
        register_component('core.logger', self)
        # ensure CSV files and headers
        if not os.path.exists(RAW_CSV):
            with open(RAW_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
        if not os.path.exists(MINUTE_CSV):
            with open(MINUTE_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(MINUTE_HEADER)

    def record_snapshot(self, snapshot: dict):
        """Record per-second snapshot (both memory and raw csv)."""
        ts = snapshot.get('timestamp', time.time())
        iso = datetime.utcfromtimestamp(ts).isoformat()
        row = {
            'timestamp': ts,
            'iso_time': iso,
            'cpu_percent': float(snapshot.get('cpu_percent', 0.0)),
            'ram_percent': float(snapshot.get('ram_percent', 0.0)),
            'gpu_percent': float(snapshot.get('gpu_percent', 0.0))
        }
        _seconds_buffer.append(row)
        try:
            with open(RAW_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([row['timestamp'], row['iso_time'], row['cpu_percent'], row['ram_percent'], row['gpu_percent']])
        except Exception:
            pass

    def record_minute_avg(self, minute_ts: float, cpu_avg: float, ram_avg: float, gpu_avg: float):
        """Append a minute-average row to minute buffer and CSV."""
        iso = datetime.utcfromtimestamp(minute_ts).isoformat()
        row = {
            'minute_ts': minute_ts,
            'iso_time': iso,
            'cpu_avg': round(cpu_avg, 3),
            'ram_avg': round(ram_avg, 3),
            'gpu_avg': round(gpu_avg, 3)
        }
        _minutes_buffer.append(row)
        try:
            with open(MINUTE_CSV, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([row['minute_ts'], row['iso_time'], row['cpu_avg'], row['ram_avg'], row['gpu_avg']])
        except Exception:
            pass

    # getters for UI / analyzer
    def get_last_seconds(self, seconds=30):
        if seconds <= 0:
            return []
        if not _seconds_buffer:
            return []
        cutoff = time.time() - seconds
        out = [r for r in list(_seconds_buffer) if r['timestamp'] >= cutoff]
        return out

    def get_last_n_samples(self, n=30):
        return list(_seconds_buffer)[-n:]

    def get_last_minutes(self, n=60):
        """Return last n minute-averages (newest last)."""
        if n <= 0:
            return []
        return list(_minutes_buffer)[-n:]

logger = Logger()
