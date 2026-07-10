"""
core/live_collector.py — THE single always-on producer for live sensor data.

Root-cause fix (2026-07-04): live_sensors used to be fed by UI pages (My PC,
Fan Dashboard) — so the In-Game Overlay showed "--", Monitoring said
"Collecting data…" forever and the learning engines got zero samples unless
the right page happened to be open. This daemon runs from startup, every
2 seconds, no UI required. Pages become consumers (their own writes remain
harmless: same fetchers, same caches, same values).

Data intake per tick:
  · psutil        — CPU load / freq / core counts, RAM, disks (every 5th tick)
  · nvidia-smi    — GPU temp/load/VRAM/power/clocks (self-cached 1.5 s)
  · OHM/LHM web   — motherboard volts + temps (ports 8085/8086, cached 4 s)
  · LHM via WMI   — CPU temperature (hardware_sensors); falls back to an
                    ESTIMATE (35 + load*0.5) flagged with cpu_temp_src="est"
                    so history/learning can stay honest and skip it.

Also maintains per-session min/max in live_sensors["session_hist"]
(canonical keys: cpu_load, cpu_temp, gpu_temp, gpu_load, cpu_power, gpu_power).
"""
from __future__ import annotations

import threading
import time

try:
    from import_core import register_component, update_status, STATUS_OK, STATUS_STARTING
    _HAS_REGISTRY = True
except Exception:
    _HAS_REGISTRY = False

TICK_S = 2.0

# ── nvidia-smi cache (moved from ui/components/yourpc_page.py) ────────────────
_GPU_SMI: dict = {}
_GPU_SMI_TS: float = 0.0


def fetch_gpu_smi() -> dict:
    """GPU stats via nvidia-smi, cached 1.5 s. {} / ok=False when unavailable."""
    global _GPU_SMI, _GPU_SMI_TS
    import subprocess as _sp
    if time.time() - _GPU_SMI_TS < 1.5:
        return _GPU_SMI
    _GPU_SMI_TS = time.time()
    try:
        r = _sp.run(
            ["nvidia-smi",
             "--query-gpu=temperature.gpu,power.draw,clocks.gr,clocks.mem,"
             "utilization.gpu,memory.used,memory.total,name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, errors="replace", timeout=3,
            creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0),
        )
        if r.returncode == 0:
            p = [x.strip() for x in r.stdout.strip().split(",")]
            _GPU_SMI = {
                "temp":      float(p[0]),
                "power":     float(p[1]),
                "clk_gr":    int(p[2]),
                "clk_mem":   int(p[3]),
                "usage":     float(p[4]),
                "mem_used":  int(p[5]),
                "mem_total": int(p[6]),
                "name":      p[7] if len(p) > 7 else "NVIDIA GPU",
                "ok":        True,
            }
    except Exception:
        _GPU_SMI.setdefault("ok", False)
    return _GPU_SMI


# ── OHM/LHM motherboard sensors (moved from ui/components/yourpc_page.py) ─────
_MB_CACHE: dict = {"volt_12v": -1.0, "volt_5v": -1.0, "volt_33v": -1.0,
                   "temp_sys": -1.0, "temp_vrm": -1.0, "source": ""}
_MB_CACHE_TS: float = 0.0


def fetch_mb_sensors() -> dict:
    """Probe OHM (8085) then LHM (8086) web servers for MB volts/temps.
    Returns floats, -1.0 when missing; 'source' is ''/'ohm'/'lhm'. Cached 4 s."""
    global _MB_CACHE, _MB_CACHE_TS
    if time.time() - _MB_CACHE_TS < 4.0:
        return _MB_CACHE
    _MB_CACHE_TS = time.time()

    result = {"volt_12v": -1.0, "volt_5v": -1.0, "volt_33v": -1.0,
              "temp_sys": -1.0, "temp_vrm": -1.0, "source": ""}

    def _walk(node: dict, acc: dict):
        text  = node.get("Text", "")
        value = node.get("Value", "")
        try:
            num = float(value.split()[0])
        except Exception:
            num = None
        if num is not None:
            tl = text.lower()
            if "+12" in tl:
                acc["volt_12v"] = num
            elif "+5" in tl and "12" not in tl:
                acc["volt_5v"] = num
            elif "+3.3" in tl or "3.3v" in tl:
                acc["volt_33v"] = num
            elif "vrm" in tl and "temp" not in tl:
                acc["temp_vrm"] = num
            elif ("motherboard" in tl or "system" in tl or "systin" in tl
                  or "temp1" in tl):
                acc["temp_sys"] = num
        for child in node.get("Children", []):
            _walk(child, acc)

    try:
        import urllib.request, json
        for port, src in [(8085, "ohm"), (8086, "lhm")]:
            try:
                with urllib.request.urlopen(
                        f"http://localhost:{port}/data.json", timeout=0.8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                acc: dict = {}
                _walk(data, acc)
                if any(v > 0 for v in acc.values() if isinstance(v, float)):
                    result.update(acc)
                    result["source"] = src
                    break
            except Exception:
                continue
    except Exception:
        pass

    _MB_CACHE = result
    return result


def _cpu_temp(cpu_load: float) -> tuple:
    """(temp_c, src) — real sensor via LHM when available, else flagged estimate."""
    try:
        from core.hardware_sensors import get_hardware_sensors
        cpu = get_hardware_sensors()._get_cpu_sensors()
        est = None
        for name, v in cpu.get("sensors", {}).items():
            if v.get("type") == "temperature":
                if "estimat" in name.lower():
                    est = float(v["raw"])
                else:
                    return float(v["raw"]), "sensor"
        if est is not None:
            return est, "est"
    except Exception:
        pass
    # last-resort estimate so the UI can still show *something*, clearly flagged
    if cpu_load >= 0:
        return 35.0 + cpu_load * 0.5, "est"
    return -1.0, ""


class LiveCollector:
    """Background daemon: fills hck_gpt.data.live_sensors every TICK_S seconds."""

    _SESSION_KEYS = ("cpu_load", "cpu_temp", "gpu_temp", "gpu_load",
                     "cpu_power", "gpu_power")

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None
        self._tick = 0
        if _HAS_REGISTRY:
            try:
                register_component("core.live_collector", self, STATUS_STARTING)
            except Exception:
                pass

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="live_collector")
        self._thread.start()
        if _HAS_REGISTRY:
            try:
                update_status("core.live_collector", STATUS_OK, "collecting")
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()

    # ── main loop ─────────────────────────────────────────────────────────────
    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._collect_once()
            except Exception:
                pass
            self._stop.wait(TICK_S)

    def _collect_once(self) -> None:
        from hck_gpt.data import live_sensors as ls
        self._tick += 1
        patch: dict = {}

        # CPU basics (psutil)
        try:
            import psutil
            patch["cpu_load"] = float(psutil.cpu_percent(interval=None))
            f = psutil.cpu_freq()
            if f:
                patch["cpu_mhz"] = float(f.current)
                if f.max:
                    patch["cpu_boost"] = float(f.max)
            if self._tick == 1:
                patch["cpu_cores_p"] = psutil.cpu_count(logical=False) or -1
                patch["cpu_cores_l"] = psutil.cpu_count(logical=True) or -1
        except Exception:
            pass

        # CPU temperature (LHM or flagged estimate)
        temp, src = _cpu_temp(patch.get("cpu_load", -1.0))
        patch["cpu_temp"] = temp
        patch["cpu_temp_src"] = src

        # GPU (nvidia-smi, self-cached)
        smi = fetch_gpu_smi()
        ok = bool(smi.get("ok"))
        patch["gpu_ok"] = ok
        if ok:
            patch["gpu_temp"]     = smi.get("temp", -1.0)
            patch["gpu_load"]     = smi.get("usage", -1.0)
            patch["gpu_power"]    = smi.get("power", -1.0)
            patch["gpu_clk_gr"]   = float(smi.get("clk_gr", -1))
            patch["gpu_clk_mem"]  = float(smi.get("clk_mem", -1))
            patch["gpu_vram_mb"]  = float(smi.get("mem_used", -1))
            total = max(smi.get("mem_total", 0), 1)
            patch["gpu_vram_pct"] = smi.get("mem_used", 0) / total * 100.0
            if smi.get("name"):
                patch["gpu_name"] = smi["name"]

        # Motherboard volts/temps (OHM/LHM web, self-cached)
        mb = fetch_mb_sensors()
        patch["mb_volt_12v"] = mb.get("volt_12v", -1.0)
        patch["mb_volt_5v"]  = mb.get("volt_5v", -1.0)
        patch["mb_volt_33v"] = mb.get("volt_33v", -1.0)
        patch["mb_temp_sys"] = mb.get("temp_sys", -1.0)
        patch["mb_temp_vrm"] = mb.get("temp_vrm", -1.0)
        patch["mb_source"]   = mb.get("source", "")

        # Disks — cheap but not free; every 5th tick (10 s)
        if self._tick % 5 == 1:
            try:
                import psutil
                disks = {}
                for p in psutil.disk_partitions():
                    try:
                        u = psutil.disk_usage(p.mountpoint)
                        disks[p.mountpoint] = {
                            "used_gb":  round(u.used / 1e9, 1),
                            "free_gb":  round(u.free / 1e9, 1),
                            "total_gb": round(u.total / 1e9, 1),
                            "pct":      round(u.percent, 1),
                        }
                    except Exception:
                        continue
                patch["disks"] = disks
            except Exception:
                pass

        # Session min/max fold (canonical keys; merge, never clobber others)
        try:
            hist = ls.get("session_hist") or {}
            for k in self._SESSION_KEYS:
                v = patch.get(k, -1.0)
                if v is None or v < 0:
                    continue
                lo, hi = hist.get(k, [v, v])
                hist[k] = [min(lo, v), max(hi, v)]
            patch["session_hist"] = hist
        except Exception:
            pass

        ls.update(patch)


# ── Singleton ──────────────────────────────────────────────────────────────────
live_collector = LiveCollector()
