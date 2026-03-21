"""hck_stats_engine.avg_calculator
Utilities to compute hourly -> daily -> weekly aggregations.
"""
from import_core import register_component
import csv, os, statistics
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'logs')
HOURLY = os.path.join(DATA_DIR, 'hourly_usage.csv')

class AvgCalculator:
    def __init__(self):
        register_component('hck_stats_engine.avg_calculator', self)

    def hourly_to_daily(self):
        # naive implementation: group by date
        if not os.path.exists(HOURLY):
            return []
        rows = []
        with open(HOURLY, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            day_buckets = {}
            for r in reader:
                date = r['iso_time'][:10]
                day_buckets.setdefault(date, []).append(float(r['cpu_percent']))
            for date, vals in day_buckets.items():
                rows.append({'date': date, 'cpu_avg': round(statistics.mean(vals),2)})
        return rows

avg_calc = AvgCalculator()
