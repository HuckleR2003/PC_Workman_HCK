# hck_gpt/context/system_context.py
"""
System Context Builder

Assembles a unified snapshot of the current PC state by pulling from:
  - psutil           (live CPU %, RAM %, freq, disk, temps, top processes)
  - hck_stats_engine (today's averages from the DB)
  - user_knowledge   (stored hardware profile)
  - session_memory   (events, trends, conversation context)

Provides:
  snapshot()            → structured dict of current PC state
  build_prompt_context()→ compact string (legacy, used by ResponseBuilder)
  build_llm_context()   → rich multi-section string for Ollama system prompt
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple


class SystemContext:
    """
    Single source of truth for current PC state.
    snapshot()         — fresh metrics dict
    build_llm_context()— rich narrative string for LLM system prompt
    """

    # Internal trend push interval (seconds) — push to session_memory no more than once per 30s
    _TREND_PUSH_INTERVAL = 30.0

    def __init__(self) -> None:
        self._last_trend_push: float = 0.0

    # ── Main snapshot ──────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a dict with current PC metrics + stored hardware profile.
        Keys present depend on what's available — always check before using.
        """
        ctx: Dict[str, Any] = {}

        # ── Live psutil ────────────────────────────────────────────────────────
        try:
            import psutil
            ctx["cpu_pct"]             = psutil.cpu_percent(interval=None)
            vm                         = psutil.virtual_memory()
            ctx["ram_pct"]             = vm.percent
            ctx["ram_total_gb"]        = round(vm.total   / 1_073_741_824, 1)
            ctx["ram_used_gb"]         = round(vm.used    / 1_073_741_824, 1)
            ctx["ram_free_gb"]         = round(vm.available / 1_073_741_824, 1)

            freq = psutil.cpu_freq()
            if freq:
                ctx["cpu_mhz"]         = round(freq.current)
                ctx["cpu_max_mhz"]     = round(freq.max) if freq.max else None
                ctx["cpu_min_mhz"]     = round(freq.min) if freq.min else None

            ctx["cpu_cores_physical"]  = psutil.cpu_count(logical=False)
            ctx["cpu_cores_logical"]   = psutil.cpu_count(logical=True)

            # Disk — Windows-safe: prefer SystemDrive env var
            try:
                import os as _os
                _sysdrive = _os.environ.get("SystemDrive", "C:") + "\\"
                disk = psutil.disk_usage(_sysdrive)
                ctx["disk_pct"]        = disk.percent
                ctx["disk_free_gb"]    = round(disk.free  / 1_073_741_824, 1)
                ctx["disk_total_gb"]   = round(disk.total / 1_073_741_824, 1)
            except Exception:
                pass

            # Throttle detection: current < 60 % of max
            if ctx.get("cpu_mhz") and ctx.get("cpu_max_mhz"):
                ratio = ctx["cpu_mhz"] / ctx["cpu_max_mhz"]
                ctx["cpu_throttle_ratio"] = round(ratio, 2)
                ctx["cpu_throttled"]      = ratio < 0.60

            # Top 3 processes by CPU — capped iteration, skip zombies safely
            try:
                raw_procs = []
                for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
                    try:
                        raw_procs.append(p)
                        if len(raw_procs) >= 128:   # cap at 128 to avoid hangs
                            break
                    except Exception:
                        continue
                procs = sorted(
                    raw_procs,
                    key=lambda p: p.info.get("cpu_percent", 0) or 0,
                    reverse=True
                )[:3]
                ctx["top_procs"] = [
                    {
                        "name": (p.info.get("name") or "?")[:30],
                        "cpu":  round(p.info.get("cpu_percent", 0) or 0, 1),
                        "ram_mb": round(
                            (p.info.get("memory_info").rss
                             if p.info.get("memory_info") else 0) / 1_048_576, 0
                        ),
                    }
                    for p in procs
                    if (p.info.get("cpu_percent") or 0) > 0
                ]
            except Exception:
                ctx["top_procs"] = []

            # Temperatures (Windows: not always available via psutil)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    flat: List[Tuple[str, float]] = []
                    for name, entries in temps.items():
                        for e in entries[:2]:
                            label = (e.label or name)[:20]
                            flat.append((label, round(e.current, 1)))
                    ctx["temperatures"] = flat[:6]  # max 6 readings
            except Exception:
                ctx["temperatures"] = []

        except Exception:
            pass

        # ── Today's averages from stats engine ─────────────────────────────────
        try:
            from hck_stats_engine.query_api import query_api
            from datetime import datetime
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp()
            usage = query_api.get_usage_for_range(
                today_start, time.time(), max_points=30
            )
            if usage:
                cpu_v = [d.get("cpu_avg") or 0 for d in usage]
                ram_v = [d.get("ram_avg") or 0 for d in usage]
                gpu_v = [d.get("gpu_avg") or 0 for d in usage if d.get("gpu_avg")]
                if cpu_v:
                    ctx["cpu_avg_today"] = round(sum(cpu_v) / len(cpu_v), 1)
                    ctx["cpu_max_today"] = round(max(cpu_v), 1)
                if ram_v:
                    ctx["ram_avg_today"] = round(sum(ram_v) / len(ram_v), 1)
                if gpu_v:
                    ctx["gpu_avg_today"] = round(sum(gpu_v) / len(gpu_v), 1)
        except Exception:
            pass

        # ── Stored hardware profile ────────────────────────────────────────────
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            ctx["hw"] = user_knowledge.get_all_hardware()
        except Exception:
            ctx["hw"] = {}

        # ── Push to session_memory trend buffer (rate-limited) ─────────────────
        try:
            import math as _math
            now = time.time()
            if now - self._last_trend_push >= self._TREND_PUSH_INTERVAL:
                cpu_pct = ctx.get("cpu_pct")
                ram_pct = ctx.get("ram_pct")
                if (cpu_pct is not None and ram_pct is not None
                        and not _math.isnan(float(cpu_pct))
                        and not _math.isnan(float(ram_pct))):
                    from hck_gpt.memory.session_memory import session_memory
                    session_memory.push_metric(float(cpu_pct), float(ram_pct))
                    self._last_trend_push = now
        except Exception:
            pass

        return ctx

    # ── Legacy compact context (used by ResponseBuilder) ──────────────────────

    def build_prompt_context(self) -> str:
        """
        Returns a compact multi-line string summarising the PC state.
        Used as context header when the chatbot builds a response.
        """
        snap  = self.snapshot()
        lines = ["[PC State]"]

        if "cpu_pct" in snap:
            mhz = f" @ {snap['cpu_mhz']} MHz" if snap.get("cpu_mhz") else ""
            thr = "  ⚠ throttled" if snap.get("cpu_throttled") else ""
            lines.append(f"CPU: {snap['cpu_pct']:.0f}%{mhz}{thr}")

        if "ram_pct" in snap:
            lines.append(
                f"RAM: {snap['ram_pct']:.0f}%"
                f"  ({snap.get('ram_used_gb','?')}"
                f" / {snap.get('ram_total_gb','?')} GB)"
            )

        if snap.get("cpu_avg_today") is not None:
            lines.append(
                f"Today avg — CPU: {snap['cpu_avg_today']}%"
                + (f"  RAM: {snap['ram_avg_today']}%"
                   if snap.get("ram_avg_today") else "")
            )

        hw = snap.get("hw", {})
        if hw.get("cpu_model"):
            lines.append(f"CPU model: {hw['cpu_model']}")
        if hw.get("gpu_model"):
            lines.append(f"GPU model: {hw['gpu_model']}")
        if hw.get("ram_total_gb"):
            spd = f" @ {hw['ram_speed_mhz']} MHz" if hw.get("ram_speed_mhz") else ""
            lines.append(f"RAM: {hw['ram_total_gb']} GB{spd}")
        if hw.get("motherboard_model"):
            lines.append(f"Motherboard: {hw['motherboard_model']}")

        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            facts = user_knowledge.get_all_facts()
            if facts:
                lines.append("Facts: " + ", ".join(
                    f"{k}={v}" for k, v in list(facts.items())[:4]
                ))
        except Exception:
            pass

        return "\n".join(lines)

    # ── Rich LLM context (used by Hybrid Engine → Ollama) ─────────────────────

    def build_llm_context(self, lang: str = "pl") -> str:
        """
        Generates a detailed multi-section context string for Ollama system prompt.
        Includes: live metrics, hardware, top processes, temps, today averages,
                  recent events from session_memory, conversation summary, trends.
        """
        snap   = self.snapshot()
        parts: List[str] = []

        # ── Section 1: Live system state ──────────────────────────────────────
        live_lines: List[str] = []

        cpu_pct = snap.get("cpu_pct")
        ram_pct = snap.get("ram_pct")
        cpu_mhz = snap.get("cpu_mhz")
        cpu_max = snap.get("cpu_max_mhz")

        if cpu_pct is not None:
            throttle = ""
            if snap.get("cpu_throttled"):
                ratio = snap.get("cpu_throttle_ratio", 0) * 100
                throttle = f"  [THROTTLED — {ratio:.0f}% power]"
            mhz_str = f" @ {cpu_mhz} MHz" if cpu_mhz else ""
            max_str = f" / max {cpu_max} MHz" if cpu_max else ""
            live_lines.append(f"CPU: {cpu_pct:.0f}%{mhz_str}{max_str}{throttle}")

        if ram_pct is not None:
            used  = snap.get("ram_used_gb", "?")
            total = snap.get("ram_total_gb", "?")
            free  = snap.get("ram_free_gb",  "?")
            live_lines.append(f"RAM: {ram_pct:.0f}%  ({used}/{total} GB used,  {free} GB free)")

        disk_free = snap.get("disk_free_gb")
        disk_tot  = snap.get("disk_total_gb")
        if disk_free is not None:
            live_lines.append(f"Disk C: {disk_free} GB free / {disk_tot} GB total")

        if live_lines:
            parts.append("=== Live System State ===\n" + "\n".join(live_lines))

        # ── Section 2: Today averages ─────────────────────────────────────────
        avg_lines: List[str] = []
        if snap.get("cpu_avg_today") is not None:
            avg_lines.append(
                f"CPU avg: {snap['cpu_avg_today']}%  peak: {snap.get('cpu_max_today', '?')}%"
            )
        if snap.get("ram_avg_today") is not None:
            avg_lines.append(f"RAM avg: {snap['ram_avg_today']}%")
        if snap.get("gpu_avg_today") is not None:
            avg_lines.append(f"GPU avg: {snap['gpu_avg_today']}%")
        if avg_lines:
            parts.append("=== Today's Averages ===\n" + "\n".join(avg_lines))

        # ── Section 3: Top processes ──────────────────────────────────────────
        procs = snap.get("top_procs", [])
        if procs:
            proc_lines = [
                f"  {p['name']:<30} CPU {p['cpu']:.1f}%  RAM {p['ram_mb']:.0f} MB"
                for p in procs
            ]
            parts.append("=== Top Processes (by CPU) ===\n" + "\n".join(proc_lines))

        # ── Section 4: Temperatures ───────────────────────────────────────────
        temps = snap.get("temperatures", [])
        if temps:
            temp_lines = [f"  {label:<22} {val}°C" for label, val in temps]
            parts.append("=== Temperatures ===\n" + "\n".join(temp_lines))

        # ── Section 5: Hardware profile ───────────────────────────────────────
        hw = snap.get("hw", {})
        hw_lines: List[str] = []
        if hw.get("cpu_model"):
            cores = hw.get("cpu_cores", "?")
            boost = hw.get("cpu_boost_ghz", "?")
            hw_lines.append(f"CPU: {hw['cpu_model']}  ({cores} cores, boost {boost} GHz)")
        if hw.get("gpu_model"):
            vram = f"  VRAM: {hw['gpu_vram_gb']} GB" if hw.get("gpu_vram_gb") else ""
            hw_lines.append(f"GPU: {hw['gpu_model']}{vram}")
        if hw.get("ram_total_gb"):
            spd = f" @ {hw['ram_speed_mhz']} MHz" if hw.get("ram_speed_mhz") else ""
            hw_lines.append(f"RAM: {hw['ram_total_gb']} GB{spd}")
        if hw.get("motherboard_model"):
            hw_lines.append(f"Motherboard: {hw['motherboard_model']}")
        if hw.get("os_version"):
            hw_lines.append(f"OS: {hw['os_version']}")
        if hw.get("storage_summary"):
            hw_lines.append(f"Storage: {hw['storage_summary']}")
        if hw_lines:
            parts.append("=== Hardware Profile ===\n" + "\n".join(hw_lines))

        # ── Section 6: Session events + trends ───────────────────────────────
        try:
            from hck_gpt.memory.session_memory import session_memory
            events_str = session_memory.recent_events_summary(within_minutes=30)
            if events_str:
                parts.append(f"=== Recent Session Alerts ===\n{events_str}")

            trend_str = session_memory.trend_summary()
            if trend_str and trend_str != "stable":
                parts.append(f"=== Metric Trends ===\n{trend_str}")

            conv_ctx = session_memory.get_context_for_llm()
            if conv_ctx:
                parts.append("=== Conversation Context ===\n" + conv_ctx)
        except Exception:
            pass

        return "\n\n".join(parts)


# ── Singleton ─────────────────────────────────────────────────────────────────
system_context = SystemContext()
