# core/analyzer.py
from import_core import register_component, COMPONENTS
import statistics
import time

class Analyzer:
    def __init__(self):
        register_component('core.analyzer', self)

    def _get_buffer(self):
        logger = COMPONENTS.get('core.logger')
        if not logger:
            return []
        # prefer last 4h buffer (logger holds it)
        return logger.get_last_seconds(4 * 3600)

    def average_over_seconds(self, seconds=30):
        buf = self._get_buffer()
        if not buf:
            return {'cpu': 0.0, 'ram': 0.0, 'gpu': 0.0}
        cutoff = time.time() - seconds
        vals = [r for r in buf if r['timestamp'] >= cutoff]
        if not vals:
            return {'cpu': 0.0, 'ram': 0.0, 'gpu': 0.0}
        cpu = round(statistics.mean([float(r['cpu_percent']) for r in vals]), 2)
        ram = round(statistics.mean([float(r['ram_percent']) for r in vals]), 2)
        gpu = round(statistics.mean([float(r['gpu_percent']) for r in vals]), 2)
        return {'cpu': cpu, 'ram': ram, 'gpu': gpu}

    def averages_now_1h_4h(self):
        return {
            'now': self.average_over_seconds(30),
            '1h': self.average_over_seconds(3600),
            '4h': self.average_over_seconds(4*3600)
        }

    def detect_spike_last(self, seconds=60, threshold_percent=30.0):
        buf = self._get_buffer()
        if not buf:
            return False, 0.0
        cutoff = time.time() - seconds
        vals = [float(r['cpu_percent']) for r in buf if r['timestamp'] >= cutoff]
        if len(vals) < 2:
            return False, 0.0
        last = vals[-1]
        prev_mean = statistics.mean(vals[:-1]) if len(vals) > 1 else vals[0]
        if prev_mean == 0:
            return False, 0.0
        diff = ((last - prev_mean) / prev_mean) * 100.0
        return abs(diff) >= threshold_percent, round(diff, 2)

analyzer = Analyzer()
