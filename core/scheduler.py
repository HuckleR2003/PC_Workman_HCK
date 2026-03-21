# core/scheduler.py
"""
core.scheduler updated
- collects per-second snapshots
- every 60 seconds computes minute-average from last 60 samples and writes to logger.minute buffer
"""

from import_core import register_component, COMPONENTS
import threading, time, traceback, statistics

# Stats Engine v2 references (lazy-loaded)
_stats_aggregator = None
_process_aggregator = None
_event_detector = None
_stats_loaded = False

def _load_stats_engine():
    """Lazy-load stats engine components (safe if not available)"""
    global _stats_aggregator, _process_aggregator, _event_detector, _stats_loaded
    if _stats_loaded:
        return
    _stats_loaded = True
    try:
        from hck_stats_engine.aggregator import aggregator
        from hck_stats_engine.process_aggregator import process_aggregator
        from hck_stats_engine.events import event_detector
        _stats_aggregator = aggregator
        _process_aggregator = process_aggregator
        _event_detector = event_detector
    except Exception as e:
        print(f"[Scheduler] Stats engine not available: {e}")

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

        # Lazy-load stats engine on first worker tick
        _load_stats_engine()

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

                # --- Stats Engine v2: accumulate per-process data every second ---
                if _process_aggregator:
                    try:
                        proc_list = snap.get('processes', [])
                        classifier = COMPONENTS.get('core.process_classifier')
                        if proc_list:
                            _process_aggregator.accumulate_second(proc_list, classifier)
                    except Exception:
                        pass

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

                        # --- Stats Engine v2: feed minute data to aggregator ---
                        if _stats_aggregator:
                            try:
                                # Get temperature readings
                                _cpu_temp = None
                                _gpu_temp = None
                                try:
                                    snap = monitor.read_snapshot()
                                    _cpu_temp = snap.get('cpu_temp', None)
                                    _gpu_temp = snap.get('gpu_temp', None)
                                    if _cpu_temp is None:
                                        _cpu_temp = 35 + cpu_avg * 0.5
                                except Exception:
                                    pass
                                _stats_aggregator.on_minute_tick(
                                    minute_ts, cpu_avg, ram_avg, gpu_avg,
                                    cpu_vals, ram_vals, gpu_vals,
                                    cpu_temp=_cpu_temp, gpu_temp=_gpu_temp
                                )
                            except Exception:
                                pass

                        # --- Stats Engine v2: spike detection ---
                        if _event_detector:
                            try:
                                _event_detector.check_and_log_spike(cpu_avg, ram_avg, gpu_avg)
                            except Exception:
                                pass

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
