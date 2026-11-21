"""core/pc_insight.py - what the recorded data says about this PC (2026-11-17).

hck_GPT answered many questions with one raw number ("CPU clock: 2500 MHz",
"Disk C: 80% used") or with the wrong handler. The 63-question library from
the third long test (2026-11-17) asked what a person wants to know: is
anything limiting my PC, which part is the weakest, is the disk fast, is the
PC old, should I worry. This module turns the data PC Workman already has
into those conclusions. Every function returns data (dicts / lists), never
chat text, so the chat, the guide and later the UI can share them.

    cpu_clock()          real clock from Windows performance counters:
                         base x "% Processor Performance"; "% Performance
                         Limit" below 100 means heat or power is holding it
    cpu_profile()        model, base / boost clock, generation year
    disks()              physical drives: type, bus, health (Get-PhysicalDisk)
    hardware_errors()    WHEA, disk and file-system errors, sudden restarts
    gaming_profile()     how CPU and GPU behave in the minutes PC Workman
                         recorded as gaming (GPU >= 60 %)
    vram_peak()          the highest VRAM use seen in the last 7 days
    usage_norms()        this PC's normal CPU / RAM / GPU and whether the last
                         2 days differ
    process_anomalies()  programs using clearly more than their own normal
    pc_age()             how old the main parts are
    weakest_part()       which part holds the PC back, with the reason
    findings()           everything worth a mention, most important first

Rules: real data only; what cannot be read is reported as unknown; slow
reads (PowerShell, event log) are cached and run on the chat's worker
thread, never on the UI thread.
"""
from __future__ import annotations

import datetime as _dt
import re
import threading
import time

_DAY = 86400.0
_cache: dict = {}
_lock = threading.Lock()


def _cached(key: str, ttl: float, fn):
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    val = fn()
    with _lock:
        _cache[key] = (now, val)
    return val


def _hist(comp: str, days: float) -> dict:
    try:
        from hck_stats_engine import history
        now = time.time()
        return history.stats(comp, now - days * _DAY, now) or {}
    except Exception:
        return {}


# ── CPU clock, from Windows performance counters ─────────────────────────────
def cpu_clock(window: float = 0.6) -> dict:
    """{"base", "actual", "perf_pct", "limit_pct", "util_pct"} or {} when the
    counters cannot be read. psutil reports the base clock on Windows; the
    "% Processor Performance" counter is what the cores really run at."""
    try:
        import ctypes
        from ctypes import wintypes
        pdh = ctypes.windll.pdh

        class _V(ctypes.Structure):
            _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]

        q = wintypes.HANDLE()
        if pdh.PdhOpenQueryW(None, 0, ctypes.byref(q)) != 0:
            return {}
        names = {
            "perf_pct": r"\Processor Information(_Total)\% Processor Performance",
            "limit_pct": r"\Processor Information(_Total)\% Performance Limit",
            "base": r"\Processor Information(_Total)\Processor Frequency",
            "util_pct": r"\Processor Information(_Total)\% Processor Utility",
        }
        handles = {}
        for k, n in names.items():
            h = wintypes.HANDLE()
            if pdh.PdhAddEnglishCounterW(q, n, 0, ctypes.byref(h)) == 0:
                handles[k] = h
        pdh.PdhCollectQueryData(q)
        time.sleep(window)
        pdh.PdhCollectQueryData(q)
        out = {}
        for k, h in handles.items():
            v = _V()
            if pdh.PdhGetFormattedCounterValue(h, 0x200, None, ctypes.byref(v)) == 0:
                out[k] = float(v.doubleValue)
        pdh.PdhCloseQuery(q)
        if out.get("base") and out.get("perf_pct"):
            out["actual"] = out["base"] * out["perf_pct"] / 100.0
        return out
    except Exception:
        return {}


def cpu_profile() -> dict:
    """{"name", "base", "boost", "year", "cores"}; unknown fields are 0 / ''."""
    name = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            name = str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
    except Exception:
        pass
    prof = {"name": name, "base": 0, "boost": 0, "year": 0, "cores": 0}
    try:
        from ui.components.yourpc_page import _CPU_KB
        for model, data in _CPU_KB.items():
            if model.lower() in name.lower():
                prof.update(base=data.get("base", 0), boost=data.get("boost", 0),
                            cores=data.get("cores", 0))
                break
    except Exception:
        pass
    prof["year"] = _cpu_year(name)
    return prof


_INTEL_GEN_YEAR = {6: 2015, 7: 2017, 8: 2017, 9: 2018, 10: 2020, 11: 2021,
                   12: 2022, 13: 2022, 14: 2023}


def _cpu_year(name: str) -> int:
    n = name.lower()
    m = re.search(r"(\d{1,2})th gen", n)
    if m:
        return _INTEL_GEN_YEAR.get(int(m.group(1)), 0)
    m = re.search(r"i[3579]-(\d{4,5})", n)
    if m:
        num = m.group(1)
        gen = int(num[:2]) if len(num) == 5 else int(num[0])
        return _INTEL_GEN_YEAR.get(gen, 0)
    if "core ultra" in n:
        return 2024
    m = re.search(r"ryzen \d (\d)\d{3}", n)
    if m:
        return {1: 2017, 2: 2018, 3: 2019, 5: 2020, 7: 2023, 8: 2024, 9: 2024}.get(int(m.group(1)), 0)
    return 0


_GPU_EXACT_YEAR = {"3050": 2022, "3090 ti": 2022, "4060": 2023, "4060 ti": 2023,
                   "4070": 2023, "1630": 2022, "1650": 2019, "1660": 2019,
                   "2060": 2019, "2070": 2018, "2080": 2018}


def _gpu_year(name: str) -> int:
    n = name.lower()
    for model, yr in _GPU_EXACT_YEAR.items():
        if re.search(r"(rtx|gtx)\s?" + re.escape(model) + r"\b", n):
            return yr
    m = re.search(r"(rtx|gtx)\s?(\d{2})(\d{2})", n)
    if m:
        series = int(m.group(2))
        return {9: 2014, 10: 2016, 16: 2019, 20: 2018, 30: 2020, 40: 2022, 50: 2025}.get(series, 0)
    m = re.search(r"rx\s?(\d)(\d{3})", n)
    if m:
        return {4: 2016, 5: 2017, 6: 2020, 7: 2022, 9: 2025}.get(int(m.group(1)), 0)
    if re.search(r"rx\s?5\d{2}\b", n):
        return 2017
    return 0


# ── drives ───────────────────────────────────────────────────────────────────
def disks() -> list:
    """[{"name", "media", "bus", "health", "size_gb"}] from Get-PhysicalDisk,
    cached 30 minutes (the call takes 1-2 s)."""
    def _read():
        import json
        import subprocess
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,"
                 "HealthStatus,Size | ConvertTo-Json"],
                capture_output=True, timeout=12,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            data = json.loads(out.decode("utf-8", errors="replace") or "[]")
        except Exception:
            return []
        if isinstance(data, dict):
            data = [data]
        res = []
        for d in data or []:
            res.append({"name": str(d.get("FriendlyName") or "").strip(),
                        "media": str(d.get("MediaType") or ""),
                        "bus": str(d.get("BusType") or ""),
                        "health": str(d.get("HealthStatus") or ""),
                        "size_gb": round((d.get("Size") or 0) / 1e9)})
        return res
    return _cached("disks", 1800, _read)


def system_disk() -> dict:
    """The physical drive Windows runs from, best effort: the hck_GPT
    hardware scan names it; otherwise the fastest drive."""
    ds = disks()
    if not ds:
        return {}
    try:
        from hck_gpt.memory.user_knowledge import user_knowledge
        model = str((user_knowledge.get_all_hardware() or {}).get("disk_model") or "")
        for d in ds:
            if model and d["name"] and d["name"].lower() in model.lower():
                return d
    except Exception:
        pass
    rank = {"nvme": 0, "sata": 1}
    return sorted(ds, key=lambda d: (rank.get(d["bus"].lower(), 2),
                                     0 if d["media"].upper() == "SSD" else 1))[0]


def disk_speed_class(d: dict) -> str:
    """'nvme' | 'sata_ssd' | 'hdd' | 'unknown'."""
    if not d:
        return "unknown"
    if d.get("media", "").upper() == "HDD":
        return "hdd"
    if d.get("bus", "").lower() == "nvme":
        return "nvme"
    if d.get("media", "").upper() == "SSD":
        return "sata_ssd"
    return "unknown"


# ── hardware errors from the Windows event log ───────────────────────────────
# warnings, errors and critical only: Ntfs also logs "volume is healthy"
_ERR_QUERY = ("*[System[(Level=1 or Level=2 or Level=3) and "
              "(Provider[@Name='Microsoft-Windows-WHEA-Logger'] or "
              "Provider[@Name='disk'] or Provider[@Name='Ntfs'] or "
              "Provider[@Name='stornvme'] or Provider[@Name='storahci'] or "
              "EventID=41 or EventID=1001 or EventID=6008)]]")


def hardware_errors(days: int = 30) -> dict:
    """{"whea": n, "disk": n, "ntfs": n, "restart": n, "bsod": n, "last": dt}
    over `days`, cached 10 minutes."""
    def _read():
        import subprocess
        out = {"whea": 0, "disk": 0, "ntfs": 0, "restart": 0, "bsod": 0,
               "unexpected": 0, "last": None, "ok": False}
        try:
            raw = subprocess.run(
                ["wevtutil", "qe", "System", f"/q:{_ERR_QUERY}", "/c:200", "/rd:true", "/f:text"],
                capture_output=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            return out
        out["ok"] = True
        since = _dt.datetime.now() - _dt.timedelta(days=days)
        src, date = "", None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Source:"):
                src = line.split(":", 1)[1].strip().lower()
            elif line.startswith("Date:"):
                try:
                    utc = _dt.datetime.strptime(line.split(":", 1)[1].strip()[:19],
                                                "%Y-%m-%dT%H:%M:%S")
                    date = utc.replace(tzinfo=_dt.timezone.utc).astimezone().replace(tzinfo=None)
                except Exception:
                    date = None
            elif line.startswith("Event ID:") and date is not None:
                if date < since:
                    continue
                try:
                    eid = int(line.split(":", 1)[1].strip())
                except ValueError:
                    continue
                if "whea" in src:
                    out["whea"] += 1
                elif src in ("disk", "stornvme", "storahci"):
                    out["disk"] += 1
                elif src == "ntfs":
                    # file-system damage only; 137 (transaction log after an
                    # unclean shutdown) and friends are not a failing drive
                    if eid not in (55, 98, 130, 140):
                        continue
                    out["ntfs"] += 1
                elif eid == 41:
                    out["restart"] += 1
                elif eid == 1001:
                    out["bsod"] += 1
                elif eid == 6008:
                    out["unexpected"] += 1
                else:
                    continue
                if out["last"] is None or date > out["last"]:
                    out["last"] = date
        return out
    return _cached(f"hwerr{days}", 600, _read)


# ── how the PC behaves while gaming ──────────────────────────────────────────
def gaming_profile(days: int = 7) -> dict:
    """CPU and GPU in the minutes recorded as gaming (GPU >= 60 %):
    {"minutes", "gpu_avg", "gpu_p95", "cpu_avg", "cpu_max", "gpu_temp_max",
    "limited_by": "gpu" | "cpu" | "cap" | ""}."""
    try:
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection()
        rows = conn.execute(
            "SELECT cpu_avg, cpu_max, gpu_avg, gpu_temp FROM minute_stats "
            "WHERE timestamp >= ? AND gpu_avg >= 60", (time.time() - days * _DAY,)).fetchall()
    except Exception:
        return {}
    if not rows:
        return {"minutes": 0}
    gpu = sorted(r[2] for r in rows)
    cpu = [r[0] for r in rows]
    out = {"minutes": len(rows),
           "gpu_avg": sum(gpu) / len(gpu),
           "gpu_p95": gpu[min(len(gpu) - 1, int(len(gpu) * 0.95))],
           "cpu_avg": sum(cpu) / len(cpu),
           "cpu_max": max(r[1] or 0 for r in rows),
           "gpu_temp_max": max((r[3] or 0) for r in rows) or None}
    if out["gpu_avg"] >= 90:
        out["limited_by"] = "gpu"          # the card is the limit: normal for games
    elif out["cpu_avg"] >= 80:
        out["limited_by"] = "cpu"
    else:
        out["limited_by"] = "cap"          # neither maxed: frame cap, V-Sync or one busy core
    return out


def vram_peak(days: int = 7) -> dict:
    """{"peak_pct", "total_gb", "now_pct"}: VRAM from DeepMonitor snapshots and
    the live sensors."""
    out = {"peak_pct": None, "total_gb": None, "now_pct": None}
    try:
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection()
        r = conn.execute("SELECT MAX(gpu_vram_pct) FROM deepmonitor_snapshots WHERE ts >= ?",
                         (time.time() - days * _DAY,)).fetchone()
        if r and r[0]:
            out["peak_pct"] = float(r[0])
    except Exception:
        pass
    try:
        from hck_gpt.data.live_sensors import snapshot
        s = snapshot() or {}
        if (s.get("gpu_vram_pct") or -1) >= 0:
            out["now_pct"] = float(s["gpu_vram_pct"])
    except Exception:
        pass
    try:
        from hck_gpt.memory.user_knowledge import user_knowledge
        v = (user_knowledge.get_all_hardware() or {}).get("gpu_vram_gb")
        out["total_gb"] = float(str(v).replace("GB", "").strip()) if v else None
    except Exception:
        pass
    if out["now_pct"] is not None:
        out["peak_pct"] = max(out["peak_pct"] or 0, out["now_pct"])
    return out


# ── normal levels and what changed ───────────────────────────────────────────
def usage_norms() -> dict:
    """{comp: {"avg", "p95", "hours", "recent": recent_vs_usual(...)}}."""
    out = {}
    try:
        from hck_stats_engine import history
    except Exception:
        return out
    for comp in ("cpu", "ram", "gpu"):
        st = _hist(comp, 14)
        if not st.get("has_data"):
            continue
        try:
            rv = history.recent_vs_usual(comp)
        except Exception:
            rv = {}
        out[comp] = {"avg": st["avg"], "p95": st["p95"], "max": st["max"],
                     "hours": st["recorded_hours"], "recent": rv}
    return out


def process_anomalies(min_ratio: float = 2.0) -> list:
    """Programs whose CPU or RAM over the last 24 h is clearly above their own
    average of the 6 days before: [{"name", "comp", "now", "usual"}]."""
    try:
        from hck_stats_engine import history
        now = time.time()
        out = []
        # averages over the time actually recorded, not the calendar: 6 days
        # with 5 h recorded made every program look 20x above "usual"
        # (fourth long test, 2026-11-17)
        rec_recent = (history.stats("cpu", now - _DAY, now).get("recorded_hours") or 0) * 3600
        rec_usual = (history.stats("cpu", now - 7 * _DAY, now - _DAY).get("recorded_hours") or 0) * 3600
        if rec_recent < 2 * 3600 or rec_usual < 12 * 3600:
            return []
        for comp in ("cpu", "ram"):
            recent = {p["process"]: p for p in history.top_processes(
                comp, now - _DAY, now, n=40, recorded_seconds=rec_recent)}
            usual = {p["process"]: p for p in history.top_processes(
                comp, now - 7 * _DAY, now - _DAY, n=80, recorded_seconds=rec_usual)}
            floor = 1.0 if comp == "cpu" else 150.0
            for proc, p in recent.items():
                u = usual.get(proc)
                if proc.lower() in ("memcompression", "system", "registry", "idle",
                                    "system idle process"):
                    continue
                if not u or (p.get("value") or 0) < floor:
                    continue
                if (u.get("value") or 0) > 0 and p["value"] >= u["value"] * min_ratio:
                    out.append({"name": p.get("name") or proc, "comp": comp,
                                "now": p["value"], "usual": u["value"]})
        return sorted(out, key=lambda x: -(x["now"] / max(x["usual"], 0.1)))[:5]
    except Exception:
        return []


# ── age and the weakest part ─────────────────────────────────────────────────
def _hw() -> dict:
    try:
        from hck_gpt.memory.user_knowledge import user_knowledge
        return user_knowledge.get_all_hardware() or {}
    except Exception:
        return {}


def pc_age() -> dict:
    hw = _hw()
    cpu = cpu_profile()
    gpu_name = str(hw.get("gpu_model") or "")
    bios_year = 0
    try:
        from core.component_check import _bios
        b = _bios()
        bios_year = b["date"].year if b.get("date") else 0
    except Exception:
        pass
    year = _dt.date.today().year
    parts = {"cpu": cpu["year"], "gpu": _gpu_year(gpu_name), "board": bios_year}
    known = [v for v in parts.values() if v]
    return {"parts": parts, "cpu_name": cpu["name"], "gpu_name": gpu_name,
            "oldest": min(known) if known else 0,
            "age": (year - min(known)) if known else None}


def weakest_part() -> dict:
    """{"part": "ram" | "gpu" | "cpu" | "disk" | "", "why": code, "data": {...}}.
    Order of evidence: too little RAM for what it does, a slow system drive,
    a part that sits at its limit in the history while the others do not."""
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / 1024 ** 3
    except Exception:
        ram_gb = 0
    ram = _hist("ram", 7)
    if ram_gb and ram_gb < 12 and ram.get("has_data") and ram["avg"] >= 70:
        return {"part": "ram", "why": "small_and_full",
                "data": {"gb": ram_gb, "avg": ram["avg"], "p95": ram["p95"]}}
    if disk_speed_class(system_disk()) == "hdd":
        return {"part": "disk", "why": "hdd", "data": {}}
    gp = gaming_profile()
    if gp.get("minutes", 0) >= 30:
        if gp["limited_by"] == "cpu":
            return {"part": "cpu", "why": "cpu_in_games", "data": gp}
        if gp["limited_by"] == "gpu":
            return {"part": "gpu", "why": "gpu_in_games", "data": gp}
    cpu = _hist("cpu", 7)
    if cpu.get("has_data") and cpu["avg"] >= 60:
        return {"part": "cpu", "why": "cpu_busy", "data": {"avg": cpu["avg"]}}
    if ram_gb and ram_gb < 16 and ram.get("has_data") and ram["avg"] >= 60:
        return {"part": "ram", "why": "ram_tight", "data": {"gb": ram_gb, "avg": ram["avg"]}}
    if not ram.get("has_data") or ram.get("recorded_hours", 0) < 2:
        # no verdict without history: "no bottleneck" would be a guess
        return {"part": "", "why": "no_data", "data": {}}
    return {"part": "", "why": "balanced", "data": {"gaming": gp}}


# ── findings: everything worth a mention ─────────────────────────────────────
def findings(deep: bool = True) -> list:
    """[{"sev": 2 | 1 | 0, "code", "data"}] sorted by severity. sev 2 = fix it,
    1 = worth knowing, 0 = fine (kept so an answer can say what was checked).
    deep=False skips the slow reads (drives, event log)."""
    out = []
    try:
        import psutil
        vm = psutil.virtual_memory()
        ram_gb = vm.total / 1024 ** 3
    except Exception:
        vm, ram_gb = None, 0
    ram = _hist("ram", 7)
    if ram_gb and ram.get("has_data"):
        # the same line as weakest_part(): small and mostly full
        if (ram_gb < 12 and ram["avg"] >= 70) or (ram_gb < 16 and ram["avg"] >= 80):
            out.append({"sev": 1, "code": "ram_small", "data": {"gb": ram_gb, "avg": ram["avg"]}})
        else:
            out.append({"sev": 0, "code": "ram_ok", "data": {"gb": ram_gb, "avg": ram["avg"]}})
    try:
        spd = int(_hw().get("ram_speed_mhz") or 0)
        if spd in (2133, 2400, 4800):
            out.append({"sev": 1, "code": "xmp_off", "data": {"mhz": spd}})
    except Exception:
        pass
    try:
        for part in psutil.disk_partitions(all=False):
            if "fixed" not in (part.opts or "") and part.fstype == "":
                continue
            try:
                u = psutil.disk_usage(part.mountpoint)
            except Exception:
                continue
            if part.mountpoint.upper().startswith("C") and u.free / 1024 ** 3 < 15:
                out.append({"sev": 2, "code": "c_full", "data": {"free_gb": u.free / 1024 ** 3}})
    except Exception:
        pass
    try:
        from core.pagefile import info as _pf
        pf = _pf()
        if pf.get("mode") == "none":
            out.append({"sev": 2 if ram_gb and ram_gb <= 16 else 1, "code": "no_pagefile", "data": pf})
    except Exception:
        pass
    try:
        from core.component_check import _class_drivers, _GPU_CLASS, _age_months
        g = next((d for d in _class_drivers(_GPU_CLASS) if d["date"]
                  and "basic display" not in d["name"].lower()), None)
        if g:
            m = _age_months(g["date"])
            out.append({"sev": 1 if m >= 12 else 0, "code": "gpu_driver",
                        "data": {"months": m, "name": g["name"]}})
    except Exception:
        pass
    gp = gaming_profile()
    if gp.get("gpu_temp_max") and gp["gpu_temp_max"] >= 84:
        out.append({"sev": 1, "code": "gpu_hot", "data": gp})
    clk = cpu_clock(0.4)
    if clk.get("limit_pct") is not None and clk["limit_pct"] < 95 and (clk.get("util_pct") or 0) > 30:
        out.append({"sev": 1, "code": "cpu_limited", "data": clk})
    if deep:
        err = hardware_errors()
        if err.get("ok"):
            if err["whea"] or err["bsod"]:
                out.append({"sev": 2, "code": "hw_errors", "data": err})
            elif err["disk"] or err["ntfs"]:
                out.append({"sev": 2, "code": "disk_errors", "data": err})
            elif err["restart"] >= 2:
                out.append({"sev": 1, "code": "restarts", "data": err})
            else:
                out.append({"sev": 0, "code": "no_errors", "data": err})
        for d in disks():
            if d["health"] and d["health"].lower() != "healthy":
                out.append({"sev": 2, "code": "disk_health", "data": d})
        if disk_speed_class(system_disk()) == "hdd":
            out.append({"sev": 1, "code": "system_hdd", "data": {}})
    for a in process_anomalies():
        out.append({"sev": 1, "code": "process_up", "data": a})
    for comp, n in usage_norms().items():
        if (n.get("recent") or {}).get("notable"):
            out.append({"sev": 1, "code": "usage_up", "data": {"comp": comp, **n["recent"]}})
    try:
        from hck_gpt.responses.flows import _startup_flagged
        flagged, total = _startup_flagged()
        if len(flagged) >= 4:
            out.append({"sev": 1, "code": "startup_heavy",
                        "data": {"n": len(flagged), "total": total}})
    except Exception:
        pass
    return sorted(out, key=lambda f: -f["sev"])
