# hck_gpt/context/hardware_scanner.py
"""
Hardware Scanner

One-time (and periodic) scan of the system.
Populates UserKnowledge DB with: CPU model/cores/boost, GPU model/VRAM,
RAM size/speed, Motherboard, Storage summary, OS version.

Designed to run in a background thread at startup so the UI
doesn't block. Safe to call multiple times — skipped if data is fresh.

WMI is used for model names (Windows only).
psutil covers everything else.
"""
from __future__ import annotations

import os
import platform
import time


def scan_and_store(force: bool = False) -> None:
    """
    Scan hardware and persist to user_knowledge.
    Skipped if data was collected within the last 24 h (unless force=True).
    """
    from hck_gpt.memory.user_knowledge import user_knowledge

    if not force and user_knowledge.hardware_is_fresh(max_age_hours=24):
        return

    _scan_psutil(user_knowledge)
    _scan_wmi(user_knowledge)
    _scan_os(user_knowledge)


# ── psutil scan (always available) ───────────────────────────────────────────

def _scan_psutil(uk) -> None:
    try:
        import psutil

        # CPU cores / threads
        uk.set_hardware("cpu_cores",   psutil.cpu_count(logical=False))
        uk.set_hardware("cpu_threads", psutil.cpu_count(logical=True))

        freq = psutil.cpu_freq()
        if freq:
            if freq.max:
                uk.set_hardware("cpu_boost_ghz", round(freq.max / 1000, 2))
            if freq.min:
                uk.set_hardware("cpu_base_ghz",  round(freq.min / 1000, 2))

        # RAM total
        vm = psutil.virtual_memory()
        uk.set_hardware("ram_total_gb", round(vm.total / 1_073_741_824, 1))

        # Storage summary
        parts = []
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                parts.append(f"{p.device} {u.total / 1_073_741_824:.0f} GB")
            except Exception:
                pass
        if parts:
            uk.set_hardware("storage_summary", " | ".join(parts))

    except Exception:
        pass


# ── WMI scan (Windows only, richer names) ─────────────────────────────────────

def _scan_wmi(uk) -> None:
    try:
        import wmi
        w = wmi.WMI()

        # CPU model
        for cpu in w.Win32_Processor():
            name = (cpu.Name or "").strip()
            if name:
                uk.set_hardware("cpu_model", name)
            break

        # GPU model + VRAM
        for gpu in w.Win32_VideoController():
            name = (gpu.Name or "").strip()
            if name and "Microsoft" not in name and "Basic" not in name:
                uk.set_hardware("gpu_model", name)
                vram = gpu.AdapterRAM
                if vram and vram > 0:
                    uk.set_hardware("gpu_vram_gb", round(vram / 1_073_741_824, 1))
                break

        # Motherboard
        for board in w.Win32_BaseBoard():
            mfr  = (board.Manufacturer or "").strip()
            prod = (board.Product      or "").strip()
            if prod and mfr and mfr.lower() not in ("to be filled by o.e.m.",
                                                      "default string"):
                uk.set_hardware("motherboard_model", f"{mfr} {prod}")
            break

        # RAM speed + part number (first populated DIMM)
        for mem in w.Win32_PhysicalMemory():
            speed = mem.Speed
            if speed:
                uk.set_hardware("ram_speed_mhz", int(speed))
            part = (getattr(mem, "PartNumber", None) or "").strip()
            if part and part.lower() not in ("", "unknown", "to be filled by o.e.m."):
                uk.set_hardware("ram_model", part)
            break

        # Primary disk model (first non-optical physical drive)
        for disk in w.Win32_DiskDrive():
            model = (getattr(disk, "Model", None) or "").strip()
            if model and "cd" not in model.lower() and "dvd" not in model.lower():
                uk.set_hardware("disk_model", model)
                break

    except Exception:
        # WMI unavailable or failed — silently skip
        pass


# ── OS info ───────────────────────────────────────────────────────────────────

def _scan_os(uk) -> None:
    try:
        ver = f"Windows {platform.release()} (build {platform.version().split('.')[-1]})"
        uk.set_hardware("os_version", ver)
    except Exception:
        pass


# ── Usage pattern update (runs at most once per 24 h) ────────────────────────

def update_usage_patterns(force: bool = False) -> None:
    """
    Compute 7-day usage averages and top app, persist to usage_patterns table.
    Runs at most once per 24 h (unless force=True).
    Stores: typical_cpu_avg, typical_ram_avg, top_app_week, patterns_updated_at.
    """
    from hck_gpt.memory.user_knowledge import user_knowledge

    last_run = user_knowledge.get_pattern("patterns_updated_at", 0)
    if not force and (time.time() - float(last_run)) < 86400:
        return

    try:
        from hck_stats_engine.query_api import query_api

        # 7-day averages
        summary = query_api.get_summary_stats(days=7)
        if summary:
            if summary.get("cpu_avg") is not None:
                user_knowledge.set_pattern("typical_cpu_avg",
                                           round(float(summary["cpu_avg"]), 1))
            if summary.get("ram_avg") is not None:
                user_knowledge.set_pattern("typical_ram_avg",
                                           round(float(summary["ram_avg"]), 1))

        # Top app this week (heaviest by CPU × duration score)
        try:
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")
            procs = query_api.get_process_daily_breakdown(today_str, top_n=10)
            if procs:
                def _score(r):
                    return (r.get("cpu_avg") or 0) * (r.get("total_active_seconds") or 0)
                best = max(procs, key=_score)
                raw = best.get("display_name") or best.get("process_name") or ""
                top = raw.replace(".exe", "").strip()
                if top:
                    user_knowledge.set_pattern("top_app_week", top)
        except Exception:
            pass

        user_knowledge.set_pattern("patterns_updated_at", time.time())

    except Exception:
        pass


# ── Pattern detection → insights_log (runs at most once per 24 h) ─────────────

def detect_and_log_patterns() -> None:
    """
    Analyse stored usage data, detect significant trends, and persist them to
    insights_log so the LLM context always has an up-to-date picture.
    Each insight type is written at most once every 48 h to avoid spam.
    """
    from hck_gpt.memory.user_knowledge import user_knowledge

    try:
        from hck_stats_engine.query_api import query_api

        # ── 7-day summary ─────────────────────────────────────────────────────
        summary = query_api.get_summary_stats(days=7)
        if not summary:
            return

        cpu7 = float(summary.get("cpu_avg") or 0)
        ram7 = float(summary.get("ram_avg") or 0)

        # Pattern A — chronically high CPU
        if cpu7 > 70 and not user_knowledge.insight_seen_recently("high_cpu_pattern", hours=48):
            user_knowledge.log_insight(
                "performance",
                f"high_cpu_pattern: 7-day CPU avg {cpu7:.0f}% — system under sustained high load",
                {"cpu_avg_7d": round(cpu7, 1)},
            )

        # Pattern B — chronically high RAM
        if ram7 > 78 and not user_knowledge.insight_seen_recently("high_ram_pattern", hours=48):
            user_knowledge.log_insight(
                "memory",
                f"high_ram_pattern: 7-day RAM avg {ram7:.0f}% — RAM under sustained pressure",
                {"ram_avg_7d": round(ram7, 1)},
            )

        # Pattern C — top app this week
        top_app = user_knowledge.get_pattern("top_app_week")
        if top_app:
            key = f"top_app_{top_app[:20]}"
            if not user_knowledge.insight_seen_recently(key, hours=72):
                user_knowledge.log_insight(
                    "usage",
                    f"{key}: '{top_app}' is consistently the heaviest resource user this week",
                    {"app": top_app},
                )

        # Pattern D — week-over-week CPU trend
        try:
            prev = query_api.get_summary_stats(days=14)
            if prev and summary:
                cpu_prev = float(prev.get("cpu_avg") or 0)
                if cpu_prev > 0:
                    delta = cpu7 - cpu_prev
                    if abs(delta) > 10 and not user_knowledge.insight_seen_recently("week_trend", hours=72):
                        direction = "increased" if delta > 0 else "decreased"
                        user_knowledge.log_insight(
                            "trend",
                            f"week_trend: CPU avg {direction} by {abs(delta):.0f}% "
                            f"vs previous week ({cpu_prev:.0f}% → {cpu7:.0f}%)",
                            {"delta": round(delta, 1),
                             "this_week": round(cpu7, 1),
                             "prev_week": round(cpu_prev, 1)},
                        )
        except Exception:
            pass

        # Prune stale insights (keep 90 days)
        try:
            user_knowledge.prune_old_insights(keep_days=90)
        except Exception:
            pass

    except Exception:
        pass
