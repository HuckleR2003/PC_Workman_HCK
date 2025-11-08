# core/scheduler.py
"""
core.scheduler updated
- collects per-second snapshots
- every 60 seconds computes minute-average from last 60 samples and writes to logger.minute buffer
"""

from import_core import register_component, COMPONENTS
import threading, time, traceback, statistics

class Scheduler:
    def __init__(self, sample_interval=1.0):
        self.sample_interval = float(sample_interval)
        self._stop = threading.Event()
        self._thread = None
        self._counter = 0
        register_component('core.scheduler', self)

    def _worker(self):
        monitor = COMPONENTS.get('core.monitor')
        logger = COMPONENTS.get('core.logger')
        analyzer = COMPONENTS.get('core.analyzer')

        if not monitor or not logger:
            return

        while not self._stop.is_set():
            try:
                snap = monitor.read_snapshot()
                # record per second
                row = {
                    'timestamp': snap['timestamp'],
                    'cpu_percent': snap.get('cpu_percent', 0.0),
                    'ram_percent': snap.get('ram_percent', 0.0),
                    'gpu_percent': snap.get('gpu_percent', 0.0)
                }
                logger.record_snapshot(row)

                # simple per-60s aggregation
                self._counter += 1
                if self._counter >= 60:
                    # compute average of last 60 samples
                    samples = logger.get_last_n_samples(60)
                    if samples:
                        cpu_vals = [float(s['cpu_percent']) for s in samples]
                        ram_vals = [float(s['ram_percent']) for s in samples]
                        gpu_vals = [float(s['gpu_percent']) for s in samples]
                        cpu_avg = statistics.mean(cpu_vals)
                        ram_avg = statistics.mean(ram_vals)
                        gpu_avg = statistics.mean(gpu_vals)
                        # minute timestamp = start of minute window (rounded)
                        minute_ts = int(time.time())
                        logger.record_minute_avg(minute_ts, cpu_avg, ram_avg, gpu_avg)
                    self._counter = 0

                # optional light analysis
                if analyzer:
                    try:
                        analyzer.detect_spike_last(seconds=30, threshold_percent=50.0)
                    except Exception:
                        pass

                time.sleep(self.sample_interval)
            except Exception:
                traceback.print_exc()
                time.sleep(self.sample_interval)

    def start_loop(self):
        if self._thread and self._thread.is_alive():
            return self._thread
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        return self._thread

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

# register instance
scheduler = Scheduler(sample_interval=1.0)
