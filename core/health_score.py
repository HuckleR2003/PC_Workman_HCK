"""core.health_score - one health score from what is actually known
(2026-11-20).

My PC's "Health score 95" came from a formula on the live load. This one is
built from the findings hck_GPT already reads (core/pc_insight): six parts,
each with a score 0-100, a reason and the place where it is fixed. A part
with no data is left out of the total instead of being counted as fine.

    score(data) -> {"total": 87, "parts": [{"key", "score", "why", "go"}, ...]}

`data` is what collect() gathers (findings, gaming profile, drives); score()
is pure, so the rules are tested without touching the PC.
"""
from __future__ import annotations

WEIGHTS = {"stability": 25, "drives": 20, "temps": 20, "memory": 15,
           "drivers": 10, "startup": 10}

# where each part is fixed (page ids of the main window)
GO = {"stability": "stability", "drives": "process_center", "temps": "activity_hardware",
      "memory": "upgrade_readiness", "drivers": "first_setup", "startup": "startup_manager"}


def collect() -> dict:
    """Everything score() needs. Slow (the event log, the drives): call it
    from a background thread."""
    data = {"findings": [], "gaming": {}, "disks": []}
    try:
        from core.pc_insight import findings, gaming_profile, disks
        data["findings"] = findings(deep=True)
        data["gaming"] = gaming_profile()
        data["disks"] = disks()
    except Exception:
        pass
    return data


def _by_code(findings) -> dict:
    return {f["code"]: f.get("data") or {} for f in findings or []}


def score(data: dict) -> dict:
    f = _by_code(data.get("findings"))
    parts = []

    # stability: the Windows event log (no log, no score)
    if any(k in f for k in ("hw_errors", "disk_errors", "restarts", "no_errors")):
        if "hw_errors" in f:
            s, why = 30, "hw_errors"
        elif "disk_errors" in f:
            s, why = 40, "disk_errors"
        elif "restarts" in f:
            s, why = 70, "restarts"
        else:
            s, why = 100, "no_errors"
        parts.append({"key": "stability", "score": s, "why": why})

    # drives: SMART state and room on C:
    if data.get("disks") or "c_full" in f or "disk_health" in f:
        if "disk_health" in f:
            s, why = 20, "disk_health"
        elif "c_full" in f:
            s, why = 50, "c_full"
        elif "system_hdd" in f:
            s, why = 75, "system_hdd"
        else:
            s, why = 100, "drives_ok"
        parts.append({"key": "drives", "score": s, "why": why})

    # temperatures: the GPU in recorded gaming
    gp = data.get("gaming") or {}
    t = gp.get("gpu_temp_max")
    if t:
        s = 100 if t < 75 else 80 if t < 82 else 55 if t < 88 else 30
        parts.append({"key": "temps", "score": s, "why": "gpu_temp", "value": t})

    # memory: size against use, XMP, virtual memory
    if "ram_small" in f or "ram_ok" in f:
        s = 60 if "ram_small" in f else 100
        why = "ram_small" if "ram_small" in f else "ram_ok"
        if "xmp_off" in f:
            s -= 10
            why = why if why == "ram_small" else "xmp_off"
        if "no_pagefile" in f:
            s = min(s, 50)
            why = "no_pagefile"
        parts.append({"key": "memory", "score": max(s, 0), "why": why})

    # drivers: the graphics driver's age
    if "gpu_driver" in f:
        m = f["gpu_driver"].get("months", 0)
        s = 100 if m < 6 else 85 if m < 12 else 60 if m < 24 else 40
        parts.append({"key": "drivers", "score": s, "why": "gpu_driver", "value": m})

    # startup: programs that slow the boot
    if "startup_heavy" in f:
        n = f["startup_heavy"].get("n", 0)
        parts.append({"key": "startup", "score": max(50, 100 - n * 8), "why": "startup_heavy",
                      "value": n})
    elif data.get("findings"):
        parts.append({"key": "startup", "score": 100, "why": "startup_ok"})

    for p in parts:
        p["go"] = GO[p["key"]]
    weight = sum(WEIGHTS[p["key"]] for p in parts)
    total = round(sum(p["score"] * WEIGHTS[p["key"]] for p in parts) / weight) if weight else None
    return {"total": total, "parts": parts}
