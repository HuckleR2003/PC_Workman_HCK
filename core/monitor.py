### HCK_Labs
# core/monitor.py
"""
core.monitor
Real monitor using psutil (CPU, RAM, per-process) and optional GPUtil for GPU.
Provides:
 - Monitor.read_snapshot() -> dict
 - Monitor.top_processes(n=6) -> list of dicts
 - In-memory buffer (managed by scheduler/logger) lives outside here.
"""

from import_core import register_component
import time
import threading
import psutil
import platform

# Try to import GPUtil. If not = GPU usage = 0
try:
    import GPUtil
    _GPUS_AVAILABLE = True
except Exception:
    _GPUS_AVAILABLE = False

class Monitor:
    def __init__(self):
        self.name = "core.monitor"
        self._cached_snapshot = None
        self._snapshot_lock = threading.Lock()
        self._bg_running = False
        register_component(self.name, self)

    def start_background_collection(self, interval=1.0):
        """Start background thread that collects snapshots every N seconds.
        This keeps process_iter() off the GUI thread."""
        if self._bg_running:
            return
        self._bg_running = True
        self._bg_interval = interval
        t = threading.Thread(target=self._bg_collect_loop, daemon=True)
        t.start()
        print("[Monitor] Background collection started")

    def stop_background_collection(self):
        self._bg_running = False

    def _bg_collect_loop(self):
        """Background thread: collect snapshots continuously."""
        while self._bg_running:
            try:
                snap = self._collect_snapshot()
                with self._snapshot_lock:
                    self._cached_snapshot = snap
            except Exception as e:
                print(f"[Monitor] BG collection error: {e}")
            time.sleep(self._bg_interval)

    def _get_gpu_percent(self):
        if not _GPUS_AVAILABLE:
            return 0.0
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return 0.0
            # return avg usage percentage across GPUs
            vals = [g.load * 100.0 for g in gpus]
            return round(sum(vals) / len(vals), 2)
        except Exception:
            return 0.0

    def _collect_snapshot(self):
        """Internal: actually collect system data (may be slow ~100-300ms)."""
        ts = time.time()
        cpu = psutil.cpu_percent(interval=None)  # non-blocking
        ram = psutil.virtual_memory().percent
        gpu = self._get_gpu_percent()

        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                info = p.info
                cpu_p = info.get('cpu_percent') or 0.0
                mem_info = info.get('memory_info')
                ram_mb = (mem_info.rss / (1024*1024)) if mem_info else 0.0
                procs.append({
                    'pid': info.get('pid'),
                    'name': (info.get('name') or '').strip(),
                    'cpu_percent': round(cpu_p, 2),
                    'ram_MB': round(ram_mb, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'timestamp': ts,
            'cpu_percent': round(cpu, 2),
            'ram_percent': round(ram, 2),
            'gpu_percent': round(gpu, 2),
            'processes': procs
        }

    def read_snapshot(self):
        """Returns cached snapshot (non-blocking for GUI thread).
        Falls back to direct collection if background thread not started."""
        with self._snapshot_lock:
            if self._cached_snapshot is not None:
                return self._cached_snapshot
        # Fallback: direct collection (blocks caller)
        return self._collect_snapshot()

    def top_processes(self, n=6, by='cpu'):
        """
        Return top n processes sorted by 'cpu' or 'ram' or 'cpu+ram'.
        'ram' sorts by ram_MB, 'cpu' sorts by cpu_percent.
        """
        snap = self.read_snapshot()
        procs = snap.get('processes', [])
        if by == 'ram':
            key = lambda p: p.get('ram_MB', 0.0)
        elif by == 'cpu+ram':
            key = lambda p: (p.get('cpu_percent', 0.0) + (p.get('ram_MB', 0.0) / 1024.0))
        else:
            key = lambda p: p.get('cpu_percent', 0.0)

        procs_sorted = sorted(procs, key=key, reverse=True)
        return procs_sorted[:n]

# register instance
monitor = Monitor()
