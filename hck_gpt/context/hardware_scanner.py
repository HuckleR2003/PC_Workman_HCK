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

        # RAM speed (first populated DIMM)
        for mem in w.Win32_PhysicalMemory():
            speed = mem.Speed
            if speed:
                uk.set_hardware("ram_speed_mhz", int(speed))
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
