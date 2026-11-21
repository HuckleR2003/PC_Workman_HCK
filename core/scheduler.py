# core/scheduler.py
from import_core import register_component, COMPONENTS
import threading, time, traceback, statistics

# Stats Engine
_stats_aggregator = None
_process_aggregator = None
_event_detector = None
_stats_loaded = False

def _load_stats_engine():
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

def _measured_temps():
    """(cpu_temp, gpu_temp) as measured right now, None where nothing
    measures it. The CPU estimate the live collector keeps for the UI is
    flagged cpu_temp_src='est' and never enters the history."""
    cpu = gpu = None
    try:
        from hck_gpt.data.live_sensors import snapshot
        s = snapshot()
        v = s.get("cpu_temp", -1)
        if s.get("cpu_temp_src") == "sensor" and v and v > 0:
            cpu = float(v)
        v = s.get("gpu_temp", -1)
        if s.get("gpu_ok") and v and v > 0:
            gpu = float(v)
    except Exception:
        pass
    return cpu, gpu


# The loop samples every second. A gap longer than this while the app keeps
# running means the PC slept (the long test: 16:19-19:32 and 19:54-20:18).
SLEEP_GAP_S = 120


def _record_sleep(start, end):
    """Store a sleep as an event, so the history can say "the PC slept"
    instead of leaving an unexplained hole (2026-11-16)."""
    try:
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection()
        if not conn:
            return
        conn.execute(
            "INSERT INTO events (timestamp, event_type, severity, description, "
            "resolved_at) VALUES (?, 'sleep', 'info', ?, ?)",
            (start, f"{int((end - start) / 60)} min", end))
        conn.commit()
    except Exception:
        pass


def _top_and_game(procs):
    """(name of the busiest process, display name of a running game or None)."""
    top, game = None, None
    try:
        from core.game_detect import is_game, display_name
        best = -1.0
        for p in procs or []:
            name = p.get('name') or ''
            cpu = float(p.get('cpu_percent') or 0)
            if cpu > best and name.lower() not in ('system', 'registry'):
                best, top = cpu, name
            if game is None and is_game(name, pid=p.get('pid')):
                game = display_name(name)
    except Exception:
        pass
    return top, game


class Scheduler:
    def __init__(self, sample_interval=1.0):
        self.sample_interval = float(sample_interval)
        self._stop = threading.Event()
        self._thread = None
        self._counter = 0
        self._last_sample_ts = 0.0
        register_component('core.scheduler', self)

    def _worker(self):
        monitor = COMPONENTS.get('core.monitor')
        logger = COMPONENTS.get('core.logger')
        analyzer = COMPONENTS.get('core.analyzer')

        if not monitor or not logger:
            return

        _load_stats_engine()

        while not self._stop.is_set():
            try:
                snap = monitor.read_snapshot()
                _now = float(snap.get('timestamp') or time.time())
                if self._last_sample_ts and _now - self._last_sample_ts > SLEEP_GAP_S:
                    _record_sleep(self._last_sample_ts, _now)
                self._last_sample_ts = _now
                row = {
                    'timestamp': snap['timestamp'],
                    'cpu_percent': snap.get('cpu_percent', 0.0),
                    'ram_percent': snap.get('ram_percent', 0.0),
                    'gpu_percent': snap.get('gpu_percent', 0.0)
                }
                logger.record_snapshot(row)

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
                        minute_ts = int(time.time())
                        logger.record_minute_avg(minute_ts, cpu_avg, ram_avg, gpu_avg)

                        if _stats_aggregator:
                            try:
                                # Temperatures: MEASURED values only
                                # (2026-11-16). Without a sensor this wrote
                                # `35 + cpu_avg * 0.5` into the history as
                                # if it had been measured.
                                _cpu_temp, _gpu_temp = _measured_temps()
                                _stats_aggregator.on_minute_tick(
                                    minute_ts, cpu_avg, ram_avg, gpu_avg,
                                    cpu_vals, ram_vals, gpu_vals,
                                    cpu_temp=_cpu_temp, gpu_temp=_gpu_temp
                                )
                            except Exception:
                                pass

                        if _event_detector:
                            try:
                                _event_detector.check_and_log_spike(cpu_avg, ram_avg, gpu_avg)
                            except Exception:
                                pass

                        # Stretches of high load, with the game or process
                        # behind them (2026-11-16): a slow ramp-up never
                        # trips the spike check above.
                        try:
                            from hck_stats_engine.load_periods import load_period_tracker
                            _ct, _gt = _measured_temps()
                            top, game = _top_and_game(snap.get('processes', []))
                            load_period_tracker.on_minute(
                                minute_ts, {"cpu": cpu_avg, "gpu": gpu_avg},
                                {"cpu": _ct, "gpu": _gt},
                                top_process=top, game=game)
                        except Exception:
                            pass

                    self._counter = 0

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
        # periods from the minutes recorded before they were tracked
        # (2026-11-17), once, in the background
        def _rebuild():
            try:
                time.sleep(20)
                from hck_stats_engine.load_periods import rebuild_from_minutes
                n = rebuild_from_minutes()
                if n:
                    print(f"[LoadPeriods] rebuilt {n} period(s) from the minute history")
            except Exception:
                pass
        threading.Thread(target=_rebuild, daemon=True, name="LoadPeriodRebuild").start()
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        return self._thread

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)

scheduler = Scheduler(sample_interval=1.0)
