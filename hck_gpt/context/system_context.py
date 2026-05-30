# hck_gpt/context/system_context.py
"""
System Context Builder

Assembles a unified snapshot of the current PC state by pulling from:
  - psutil           (live CPU %, RAM %, freq, disk, temps, top processes)
  - hck_stats_engine (today's averages from the DB)
  - user_knowledge   (stored hardware profile)
  - session_memory   (events, trends, conversation context)

Provides:
  snapshot()            -> structured dict of current PC state
  build_prompt_context()-> compact string (legacy, used by ResponseBuilder)
  build_llm_context()   -> rich multi-section string for Ollama system prompt
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple


class SystemContext:
    """
    Single source of truth for current PC state.
    snapshot()         - fresh metrics dict
    build_llm_context()- rich narrative string for LLM system prompt
    """

    # Internal trend push interval (seconds) - push to session_memory no more than once per 30s
    _TREND_PUSH_INTERVAL  = 30.0
    # LLM context cache - rebuild at most every 5 s to avoid hammering psutil + SQLite
    # on rapid Ollama calls (e.g. user sends multiple messages quickly)
    _LLM_CONTEXT_CACHE_TTL = 5.0

    def __init__(self) -> None:
        self._last_trend_push: float = 0.0
        self._llm_context_cache: str   = ""
        self._llm_context_ts:    float = 0.0
        self._llm_context_lang:  str   = ""    # invalidate cache on language switch

    # ── Main snapshot ──────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a dict with current PC metrics + stored hardware profile.
        Keys present depend on what's available - always check before using.
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

            # Disk - Windows-safe: prefer SystemDrive env var
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

            # Top 3 processes by CPU - capped iteration, skip zombies safely
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

        # ── Hardware-sensor temperatures (LibreHardwareMonitor via core) ───────
        # psutil.sensors_temperatures() is usually empty on Windows.
        # core.hardware_sensors has a proper driver-backed implementation.
        try:
            from core.hardware_sensors import get_cpu_temp, get_gpu_temp
            cpu_t = get_cpu_temp()
            gpu_t = get_gpu_temp()
            if cpu_t:
                ctx["cpu_temp"] = round(float(cpu_t), 1)
                # Enrich or replace the psutil temperatures list so the
                # LLM context always shows at least CPU/GPU readings.
                existing = ctx.get("temperatures", [])
                has_cpu_entry = any("cpu" in lbl.lower() or "package" in lbl.lower()
                                    for lbl, _ in existing)
                if not has_cpu_entry:
                    ctx.setdefault("temperatures", []).insert(
                        0, ("CPU Package", round(float(cpu_t), 1))
                    )
            if gpu_t:
                ctx["gpu_temp"] = round(float(gpu_t), 1)
                existing = ctx.get("temperatures", [])
                has_gpu_entry = any("gpu" in lbl.lower() for lbl, _ in existing)
                if not has_gpu_entry:
                    ctx.setdefault("temperatures", []).append(
                        ("GPU Core", round(float(gpu_t), 1))
                    )
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
            mhz  = f" @ {snap['cpu_mhz']} MHz" if snap.get("cpu_mhz") else ""
            thr  = "  ⚠ throttled"              if snap.get("cpu_throttled") else ""
            temp = f"  {snap['cpu_temp']}°C"    if snap.get("cpu_temp") else ""
            lines.append(f"CPU: {snap['cpu_pct']:.0f}%{mhz}{temp}{thr}")

        if "ram_pct" in snap:
            lines.append(
                f"RAM: {snap['ram_pct']:.0f}%"
                f"  ({snap.get('ram_used_gb','?')}"
                f" / {snap.get('ram_total_gb','?')} GB)"
            )

        if snap.get("gpu_temp") is not None:
            lines.append(f"GPU temp: {snap['gpu_temp']}°C")

        if snap.get("cpu_avg_today") is not None:
            lines.append(
                f"Today avg - CPU: {snap['cpu_avg_today']}%"
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

    # ── Rich LLM context (used by Hybrid Engine -> Ollama) ─────────────────────

    def build_llm_context(self, lang: str = "pl") -> str:
        """
        Generates a detailed multi-section context string for Ollama system prompt.
        Includes: live metrics, hardware, top processes, temps, today averages,
                  recent events from session_memory, conversation summary, trends.

        Result is cached for _LLM_CONTEXT_CACHE_TTL seconds to avoid rebuilding
        the full context (psutil + SQLite + session_memory) on every rapid message.
        Cache is invalidated on language change.
        """
        now = time.time()
        if (self._llm_context_cache
                and self._llm_context_lang == lang
                and (now - self._llm_context_ts) < self._LLM_CONTEXT_CACHE_TTL):
            return self._llm_context_cache

        ctx = self._build_llm_context_impl(lang)
        self._llm_context_cache = ctx
        self._llm_context_ts    = now
        self._llm_context_lang  = lang
        return ctx

    def build_llm_context_windowed(self, lang: str = "pl",
                                    window_minutes: int = 30) -> str:
        """
        MEGA FEATURE: Context Time-Windowing.
        Builds context constrained to the last `window_minutes` of data.
        For wide windows (> 60 min) appends historical trend section from
        metrics_store so the LLM gets time-travel context for degradation queries.

        Falls back to build_llm_context() on any error.
        """
        try:
            # Base context is always live (unchanged)
            base = self._build_llm_context_impl(lang)

            # For narrow windows (<= 30 min) - strip old "Today's Averages" section
            # to avoid noise; the live snapshot is sufficient.
            if window_minutes <= 30:
                # Already fresh enough - return base minus heavy history sections
                lines = base.split("\n\n")
                filtered = [
                    sec for sec in lines
                    if not sec.startswith("=== Learned Usage Patterns")
                    and not sec.startswith("=== Recent Patterns")
                ]
                return "\n\n".join(filtered)

            # For wide windows - append historical trend from metrics_store
            parts = [base]
            try:
                from hck_gpt.data.metrics_store import metrics_store
                days = max(1, window_minutes // (60 * 24))
                history = metrics_store.daily_summary(days=min(days, 30))
                if history:
                    trend_lines = [f"=== Historical Metrics ({days}-day trend) ==="]
                    for row in history[:7]:
                        d      = row.get("date_str") or "?"
                        c_avg  = row.get("cpu_avg")       # cpu_load AVG
                        c_max  = row.get("cpu_max")       # cpu_load MAX
                        ct_avg = row.get("cpu_temp_avg")  # cpu_temp AVG
                        g_avg  = row.get("gpu_avg")       # gpu_load AVG
                        gt_avg = row.get("gpu_temp_avg")  # gpu_temp AVG
                        r_avg  = row.get("ram_avg")       # ram_pct AVG
                        parts_line = [d]
                        if c_avg  is not None: parts_line.append(f"CPU {c_avg:.0f}%")
                        if c_max  is not None: parts_line.append(f"peak {c_max:.0f}%")
                        if ct_avg is not None: parts_line.append(f"temp {ct_avg:.0f}°C")
                        if g_avg  is not None: parts_line.append(f"GPU {g_avg:.0f}%")
                        if gt_avg is not None: parts_line.append(f"GPU_temp {gt_avg:.0f}°C")
                        if r_avg  is not None: parts_line.append(f"RAM {r_avg:.0f}%")
                        trend_lines.append("  " + "  |  ".join(parts_line))
                    parts.append("\n".join(trend_lines))
            except Exception:
                pass

            return "\n\n".join(parts)
        except Exception:
            return self.build_llm_context(lang)

    def _build_llm_context_impl(self, lang: str = "pl") -> str:
        """Internal - builds the full context string. Called by build_llm_context()."""
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
                throttle = f"  [THROTTLED - {ratio:.0f}% power]"
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

        # ── Section 7: Learned usage patterns (from usage_patterns table) ────
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            patterns = user_knowledge.get_all_patterns()
            pat_lines: List[str] = []
            if patterns.get("typical_cpu_avg") is not None:
                pat_lines.append(
                    f"Typical CPU avg (7-day baseline): {patterns['typical_cpu_avg']}%")
            if patterns.get("typical_ram_avg") is not None:
                pat_lines.append(
                    f"Typical RAM avg (7-day baseline): {patterns['typical_ram_avg']}%")
            if patterns.get("top_app_week"):
                pat_lines.append(
                    f"Heaviest app this week: {patterns['top_app_week']}")
            if pat_lines:
                parts.append("=== Learned Usage Patterns ===\n" + "\n".join(pat_lines))
        except Exception:
            pass

        # ── Section 8: Recent AI-discovered insights (from insights_log) ─────
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            insights = user_knowledge.get_recent_insights(n=3)
            if insights:
                ins_lines: List[str] = []
                for cat, insight, _ in insights:
                    # Strip key prefix ("high_cpu_pattern: ") to keep it concise
                    display = insight.split(": ", 1)[-1] if ": " in insight else insight
                    ins_lines.append(f"  [{cat}] {display}")
                parts.append(
                    "=== Recent Patterns (AI-discovered) ===\n" + "\n".join(ins_lines))
        except Exception:
            pass

        # ── Section 9: Today vs typical baseline (session delta) ─────────────
        try:
            from hck_gpt.memory.user_knowledge import user_knowledge
            patterns = user_knowledge.get_all_patterns()
            typ_cpu = patterns.get("typical_cpu_avg")
            typ_ram = patterns.get("typical_ram_avg")
            today_cpu = snap.get("cpu_avg_today")
            today_ram = snap.get("ram_avg_today")
            delta_lines: List[str] = []
            if today_cpu is not None and typ_cpu is not None:
                diff = float(today_cpu) - float(typ_cpu)
                arrow = "↑" if diff > 5 else ("↓" if diff < -5 else "->")
                sign  = "+" if diff >= 0 else ""
                delta_lines.append(
                    f"CPU today {today_cpu}% vs typical {typ_cpu}%  {arrow} ({sign}{diff:.0f}%)")
            if today_ram is not None and typ_ram is not None:
                diff = float(today_ram) - float(typ_ram)
                arrow = "↑" if diff > 5 else ("↓" if diff < -5 else "->")
                sign  = "+" if diff >= 0 else ""
                delta_lines.append(
                    f"RAM today {today_ram}% vs typical {typ_ram}%  {arrow} ({sign}{diff:.0f}%)")
            if delta_lines:
                parts.append("=== Today vs Typical ===\n" + "\n".join(delta_lines))
        except Exception:
            pass

        return "\n\n".join(parts)


# ── Singleton ─────────────────────────────────────────────────────────────────
system_context = SystemContext()
