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
        register_component(self.name, self)

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

    def read_snapshot(self):
        """
        Returns a snapshot dict:
        {
            "timestamp": float (unix),
            "cpu_percent": float,
            "ram_percent": float,
            "gpu_percent": float,
            "processes": [ {"pid": int, "name": str, "cpu_percent": float, "ram_MB": float}, ... ]
        }
        """
        ts = time.time()
        cpu = psutil.cpu_percent(interval=None)  # non-blocking
        ram = psutil.virtual_memory().percent
        gpu = self._get_gpu_percent()

        procs = []
        # iterate processes and collect simple metrics - robust to AccessDenied
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

        snapshot = {
            'timestamp': ts,
            'cpu_percent': round(cpu, 2),
            'ram_percent': round(ram, 2),
            'gpu_percent': round(gpu, 2),
            'processes': procs
        }
        return snapshot

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
