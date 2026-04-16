import platform
import subprocess
import threading

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False


def _wmic(wmi_path: str, get_fields: list, timeout: int = 8) -> list:
    try:
        cmd = ["wmic", wmi_path, "get", ",".join(get_fields), "/format:csv"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return []
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        header = None
        items = []
        for line in lines:
            parts = line.split(",")
            if header is None:
                header = [p.strip().lower() for p in parts]
                continue
            if len(parts) < len(header):
                continue
            items.append({header[i]: parts[i].strip() for i in range(len(header))})
        return items
    except Exception:
        return []


def _fmt_driver_date(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 8 and raw[:8].isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return raw or "Unknown"


class HardwareDetector:
    def __init__(self):
        self._data: dict = {}
        self._ready = False
        self._lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._ready

    def scan_async(self, on_done=None):
        def _work():
            data = self._do_scan()
            with self._lock:
                self._data = data
                self._ready = True
            if on_done:
                on_done(data)
        threading.Thread(target=_work, daemon=True).start()

    def get_data(self) -> dict:
        with self._lock:
            return dict(self._data)

    def _do_scan(self) -> dict:
        return {
            "cpu": self._scan_cpu(),
            "gpu": self._scan_gpu(),
            "ram": self._scan_ram(),
            "storage": self._scan_storage(),
            "motherboard": self._scan_motherboard(),
        }

    def _scan_cpu(self) -> dict:
        info = {
            "name": "Unknown CPU",
            "cores_physical": 0,
            "cores_logical": 0,
            "freq_current_mhz": 0,
            "freq_max_mhz": 0,
            "manufacturer": "",
            "architecture": platform.machine(),
        }
        rows = _wmic("cpu", ["name", "numberofcores", "numberoflogicalprocessors",
                              "maxclockspeed", "currentclockspeed", "manufacturer"])
        if rows:
            r = rows[0]
            info["name"] = r.get("name", "Unknown CPU") or "Unknown CPU"
            info["cores_physical"] = int(r.get("numberofcores", 0) or 0)
            info["cores_logical"] = int(r.get("numberoflogicalprocessors", 0) or 0)
            info["freq_current_mhz"] = int(r.get("currentclockspeed", 0) or 0)
            info["freq_max_mhz"] = int(r.get("maxclockspeed", 0) or 0)
            info["manufacturer"] = r.get("manufacturer", "").strip()

        if HAS_PSUTIL:
            if not info["cores_physical"]:
                info["cores_physical"] = psutil.cpu_count(logical=False) or 0
            if not info["cores_logical"]:
                info["cores_logical"] = psutil.cpu_count(logical=True) or 0
            try:
                freq = psutil.cpu_freq()
                if freq:
                    if not info["freq_current_mhz"]:
                        info["freq_current_mhz"] = int(freq.current)
                    if not info["freq_max_mhz"] and freq.max:
                        info["freq_max_mhz"] = int(freq.max)
            except Exception:
                pass
        return info

    def _scan_gpu(self) -> dict:
        info = {
            "name": "Not detected",
            "vram_mb": 0,
            "driver_version": "",
            "driver_date": "",
            "usage_pct": 0,
            "temp_c": 0,
        }
        if HAS_GPUTIL:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    info["name"] = g.name
                    info["vram_mb"] = int(g.memoryTotal)
                    info["usage_pct"] = int(g.load * 100)
                    info["temp_c"] = int(g.temperature)
            except Exception:
                pass

        rows = _wmic("path Win32_VideoController",
                     ["name", "adapterram", "driverversion", "driverdate"])
        if rows:
            r = rows[0]
            if info["name"] == "Not detected":
                info["name"] = r.get("name", "Unknown GPU") or "Unknown GPU"
            ram_b = int(r.get("adapterram", 0) or 0)
            if ram_b > 0 and not info["vram_mb"]:
                info["vram_mb"] = ram_b // (1024 * 1024)
            info["driver_version"] = r.get("driverversion", "").strip()
            info["driver_date"] = _fmt_driver_date(r.get("driverdate", ""))
        return info

    def _scan_ram(self) -> dict:
        info = {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent": 0.0,
            "speed_mhz": 0,
            "form_factor": "",
            "slots_used": 0,
            "modules": [],
        }
        if HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                info["total_gb"] = round(mem.total / (1024 ** 3), 1)
                info["used_gb"] = round(mem.used / (1024 ** 3), 1)
                info["free_gb"] = round(mem.available / (1024 ** 3), 1)
                info["percent"] = mem.percent
            except Exception:
                pass

        rows = _wmic("memorychip", ["capacity", "speed", "formfactor", "manufacturer"])
        info["slots_used"] = len(rows)
        _ff_map = {8: "DIMM", 12: "SO-DIMM", 13: "SO-DIMM"}
        for r in rows:
            cap_gb = round(int(r.get("capacity", 0) or 0) / (1024 ** 3), 1)
            speed = int(r.get("speed", 0) or 0)
            ff_code = int(r.get("formfactor", 0) or 0)
            ff = _ff_map.get(ff_code, "DIMM")
            if speed > info["speed_mhz"]:
                info["speed_mhz"] = speed
            info["form_factor"] = ff
            info["modules"].append({
                "capacity_gb": cap_gb,
                "speed_mhz": speed,
                "form_factor": ff,
                "manufacturer": r.get("manufacturer", "").strip(),
            })
        return info

    def _scan_storage(self) -> dict:
        drives = []
        rows = _wmic("diskdrive", ["model", "size", "mediatype"])
        for r in rows:
            size_b = int(r.get("size", 0) or 0)
            drives.append({
                "model": r.get("model", "Unknown Drive").strip(),
                "size_gb": round(size_b / (1024 ** 3), 0),
                "media_type": r.get("mediatype", "").strip(),
            })

        partitions = []
        if HAS_PSUTIL:
            try:
                for p in psutil.disk_partitions():
                    try:
                        u = psutil.disk_usage(p.mountpoint)
                        partitions.append({
                            "device": p.device,
                            "mountpoint": p.mountpoint,
                            "fstype": p.fstype,
                            "total_gb": round(u.total / (1024 ** 3), 1),
                            "used_gb": round(u.used / (1024 ** 3), 1),
                            "free_gb": round(u.free / (1024 ** 3), 1),
                            "percent": u.percent,
                        })
                    except Exception:
                        pass
            except Exception:
                pass
        return {"drives": drives, "partitions": partitions}

    def _scan_motherboard(self) -> dict:
        info = {"manufacturer": "", "product": "", "version": ""}
        rows = _wmic("baseboard", ["manufacturer", "product", "version"])
        if rows:
            r = rows[0]
            info["manufacturer"] = r.get("manufacturer", "").strip()
            info["product"] = r.get("product", "").strip()
            info["version"] = r.get("version", "").strip()
        return info


_detector_instance: HardwareDetector | None = None


def get_hardware_detector() -> HardwareDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = HardwareDetector()
    return _detector_instance
