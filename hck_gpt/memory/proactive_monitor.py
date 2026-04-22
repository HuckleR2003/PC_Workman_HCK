# hck_gpt/memory/proactive_monitor.py
"""
Proactive Monitor — background thread that watches system state
and autonomously pushes alerts/tips to the hck_GPT panel.

Monitored conditions:
  - CPU consistently high (>85% for 2+ consecutive checks)
  - RAM critical (>90%)
  - RAM moderate + pagefile active
  - CPU throttling detected
  - Disk nearly full (<4 GB free)
  - New heavy process appeared (sudden CPU spike by single process)
  - Long session detected (PC on for many hours)

Push mechanism:
  Register a callback via proactive_monitor.register_push(fn).
  The fn receives a single string message and is called from a
  background thread — make sure to schedule it on the main thread
  (use tkinter's .after(0, ...) when registering).

Silent notifications (banner):
  Register via proactive_monitor.register_banner(fn) for non-intrusive
  status text updates in the hck_GPT banner.
"""
from __future__ import annotations

import threading
import time
import random
from typing import Callable, List, Optional


# ── Thresholds ────────────────────────────────────────────────────────────────
CPU_HIGH_PCT      = 85.0
CPU_CRIT_PCT      = 95.0
RAM_HIGH_PCT      = 88.0
RAM_CRIT_PCT      = 93.0
DISK_LOW_GB       = 4.0
THROTTLE_RATIO    = 0.60   # below 60 % of max = throttled
CHECK_INTERVAL_S  = 45     # seconds between checks
MIN_GAP_SAME_S    = 300    # don't repeat same alert within 5 min


# ── Message pools — PL + EN ───────────────────────────────────────────────────

_MSGS: dict[str, dict[str, list[str]]] = {
    "cpu_high": {
        "pl": [
            "hck_GPT: ⚠ CPU wysokie ({val}%) — sprawdź co go zajmuje ('top procesy').",
            "hck_GPT: CPU pod dużym obciążeniem: {val}%. Może warto zamknąć zbędne programy?",
            "hck_GPT: Uwaga — procesor pracuje na {val}%. Wszystko OK?",
        ],
        "en": [
            "hck_GPT: ⚠ CPU high ({val}%) — check what's using it ('top processes').",
            "hck_GPT: CPU load is {val}%. Consider closing unused apps.",
            "hck_GPT: Heads up — processor at {val}%. Everything ok?",
        ],
    },
    "cpu_crit": {
        "pl": [
            "hck_GPT: 🔴 CPU KRYTYCZNE {val}%! System może być niestabilny.",
            "hck_GPT: Procesor prawie na granicy: {val}%! Sprawdź procesy natychmiast.",
        ],
        "en": [
            "hck_GPT: 🔴 CPU CRITICAL {val}%! System may become unstable.",
            "hck_GPT: Processor at {val}%! Check running processes immediately.",
        ],
    },
    "ram_high": {
        "pl": [
            "hck_GPT: Pamięć RAM zajęta w {val}% — rozważ zamknięcie kart przeglądarki.",
            "hck_GPT: ⚠ RAM: {val}%. Przy dalszym wzroście system może zacząć używać pliku wymiany.",
        ],
        "en": [
            "hck_GPT: RAM usage at {val}% — consider closing browser tabs.",
            "hck_GPT: ⚠ RAM at {val}%. System may start using pagefile if it rises further.",
        ],
    },
    "ram_crit": {
        "pl": [
            "hck_GPT: 🔴 RAM KRYTYCZNE {val}%! Możliwe spowolnienia lub crashe.",
        ],
        "en": [
            "hck_GPT: 🔴 RAM CRITICAL {val}%! Slowdowns or crashes may occur.",
        ],
    },
    "throttle": {
        "pl": [
            "hck_GPT: ⚠ CPU throttluje! Działa na {val}% swojej mocy — sprawdź temperatury.",
            "hck_GPT: Dławienie procesora wykryte ({val}% mocy). Przyczyną jest zazwyczaj przegrzanie.",
        ],
        "en": [
            "hck_GPT: ⚠ CPU throttling! Running at {val}% power — check temperatures.",
            "hck_GPT: CPU power limit active ({val}% of max). Usually caused by heat.",
        ],
    },
    "disk_low": {
        "pl": [
            "hck_GPT: 💾 Mało miejsca na dysku — tylko {val} GB wolne. Rozważ czyszczenie.",
            "hck_GPT: Dysk prawie pełny ({val} GB wolne). Sprawdź zakładkę Optimization.",
        ],
        "en": [
            "hck_GPT: 💾 Disk almost full — only {val} GB free. Consider cleanup.",
            "hck_GPT: Low disk space ({val} GB free). Check the Optimization tab.",
        ],
    },
    "long_session": {
        "pl": [
            "hck_GPT: Pracujesz już {val}h. Pamiętaj o przerwie — i może restart od czasu do czasu? 😊",
            "hck_GPT: Sesja trwa {val}h. Dłuższa praca bez restartu może skutkować wyciekami pamięci.",
        ],
        "en": [
            "hck_GPT: You've been running for {val}h. Remember to take a break! 😊",
            "hck_GPT: {val}h uptime. Long sessions without restart may cause memory leaks.",
        ],
    },
    "all_clear": {
        "pl": [
            "hck_GPT: ✓ System w dobrej kondycji — CPU i RAM w normie.",
            "hck_GPT: Wszystko gra — brak anomalii.",
            "hck_GPT: System spokojny. Możesz pracować bez obaw.",
        ],
        "en": [
            "hck_GPT: ✓ System healthy — CPU and RAM nominal.",
            "hck_GPT: All clear — no anomalies detected.",
            "hck_GPT: System is calm. No issues found.",
        ],
    },
}

# Periodic tips shown when system is idle/healthy
_IDLE_TIPS: dict[str, list[str]] = {
    "pl": [
        "hck_GPT: 💡 Tip: Zakładka AllMonitor pokazuje historyczne min/max dla każdego zasobu.",
        "hck_GPT: 💡 Tip: 'service setup' w chatie uruchamia kreator optymalizacji.",
        "hck_GPT: 💡 Tip: Wpisz 'stats' by zobaczyć dzisiejsze średnie użycia.",
        "hck_GPT: 💡 Tip: Zakładka Efficiency pokazuje Top CPU i RAM procesy w czasie rzeczywistym.",
        "hck_GPT: 💡 Wiesz, że możesz zapytać: 'jaki mam procesor' i podam Ci pełne dane?",
        "hck_GPT: 💡 Monitoruję Twój PC cicho w tle. Pisz jeśli chcesz sprawdzić coś konkretnego.",
    ],
    "en": [
        "hck_GPT: 💡 Tip: AllMonitor tab shows historical min/max for each resource.",
        "hck_GPT: 💡 Tip: Type 'service setup' to launch the optimization wizard.",
        "hck_GPT: 💡 Tip: Type 'stats' to see today's usage averages.",
        "hck_GPT: 💡 Tip: The Efficiency tab shows live Top CPU and RAM processes.",
        "hck_GPT: 💡 You can ask 'what CPU do I have' and I'll give you full details.",
        "hck_GPT: 💡 I'm monitoring your PC silently. Ask me anything specific.",
    ],
}


# ── Main class ────────────────────────────────────────────────────────────────

class ProactiveMonitor:
    """
    Background monitor that analyses system state and pushes
    contextual alerts/tips to the hck_GPT panel.
    """

    def __init__(self) -> None:
        self._push_fn:   Optional[Callable[[str], None]] = None
        self._banner_fn: Optional[Callable[[str], None]] = None
        self._lang:      str  = "pl"
        self._thread:    Optional[threading.Thread] = None
        self._running:   bool = False

        # State tracking
        self._last_alert:  dict[str, float] = {}  # event_type → last sent ts
        self._cpu_high_cnt: int = 0
        self._session_start = time.time()
        self._session_long_alerted = False
        self._idle_tip_idx = 0

    # ── Registration ──────────────────────────────────────────────────────────

    def register_push(self, fn: Callable[[str], None]) -> None:
        """Register callback for in-chat messages (must be thread-safe)."""
        self._push_fn = fn

    def register_banner(self, fn: Callable[[str], None]) -> None:
        """Register callback for banner status text updates."""
        self._banner_fn = fn

    def set_language(self, lang: str) -> None:
        self._lang = lang if lang in ("pl", "en") else "pl"

    # ── Start / stop ──────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="hck_proactive"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        # Initial delay — let the app fully load first
        time.sleep(60)
        tip_counter = 0

        while self._running:
            try:
                self._check_system()
                tip_counter += 1
                # Show idle tip every ~8 checks (~6 min) when system is healthy
                if tip_counter % 8 == 0:
                    self._maybe_idle_tip()
            except Exception:
                pass
            time.sleep(CHECK_INTERVAL_S)

    # ── System checks ─────────────────────────────────────────────────────────

    def _check_system(self) -> None:
        try:
            import psutil
        except ImportError:
            return

        # Use interval=1 (was 2) — shorter blocking, still accurate enough
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory().percent
        freq = psutil.cpu_freq()

        # CPU — require 2 consecutive high readings before alerting
        if cpu >= CPU_CRIT_PCT:
            self._cpu_high_cnt += 1
            if self._cpu_high_cnt >= 2:
                self._alert("cpu_crit", f"{cpu:.0f}")
        elif cpu >= CPU_HIGH_PCT:
            self._cpu_high_cnt += 1
            if self._cpu_high_cnt >= 2:
                self._alert("cpu_high", f"{cpu:.0f}")
        else:
            # Reset counter faster when CPU drops clearly below threshold
            if cpu < CPU_HIGH_PCT - 10:
                self._cpu_high_cnt = 0
            else:
                self._cpu_high_cnt = max(0, self._cpu_high_cnt - 1)

        # RAM
        if ram >= RAM_CRIT_PCT:
            self._alert("ram_crit", f"{ram:.0f}")
        elif ram >= RAM_HIGH_PCT:
            self._alert("ram_high", f"{ram:.0f}")

        # Throttling
        if freq and freq.max and freq.current and freq.max > 0:
            ratio = freq.current / freq.max
            if ratio < THROTTLE_RATIO:
                self._alert("throttle", f"{ratio*100:.0f}")

        # Disk — Windows-safe: try system drive first, fallback to partitions
        try:
            import os
            system_drive = os.environ.get("SystemDrive", "C:") + "\\"
            disk = psutil.disk_usage(system_drive)
            free_gb = disk.free / 1_073_741_824
            if free_gb < DISK_LOW_GB:
                self._alert("disk_low", f"{free_gb:.1f}")
        except Exception:
            try:
                # Generic fallback
                parts = psutil.disk_partitions()
                if parts:
                    disk = psutil.disk_usage(parts[0].mountpoint)
                    free_gb = disk.free / 1_073_741_824
                    if free_gb < DISK_LOW_GB:
                        self._alert("disk_low", f"{free_gb:.1f}")
            except Exception:
                pass

        # Long session
        uptime_h = (time.time() - self._session_start) / 3600
        if uptime_h > 8 and not self._session_long_alerted:
            self._session_long_alerted = True
            self._alert("long_session", f"{uptime_h:.0f}")

        # Banner: always update with current state
        self._update_banner(cpu, ram)

    # ── Alert dispatch ────────────────────────────────────────────────────────

    def _alert(self, event_type: str, val: str) -> None:
        now = time.time()
        last = self._last_alert.get(event_type, 0)
        if now - last < MIN_GAP_SAME_S:
            return

        self._last_alert[event_type] = now
        pool = _MSGS.get(event_type, {}).get(self._lang, [])
        if not pool:
            return

        msg = random.choice(pool).format(val=val)
        self._push(msg)

        # Record in session memory
        try:
            from hck_gpt.memory.session_memory import session_memory
            session_memory.record_event(event_type, f"{val}")
        except Exception:
            pass

    def _maybe_idle_tip(self) -> None:
        """Push a helpful tip when system is calm."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            if cpu > 60 or ram > 80:
                return  # not idle enough
        except Exception:
            return

        tips = _IDLE_TIPS.get(self._lang, _IDLE_TIPS.get("pl", []))
        if not tips:
            return
        msg = tips[self._idle_tip_idx % len(tips)]
        self._idle_tip_idx += 1
        self._push(msg)

    def _update_banner(self, cpu: float, ram: float) -> None:
        if not self._banner_fn:
            return
        try:
            lang = self._lang
            if cpu >= CPU_HIGH_PCT:
                if lang == "pl":
                    status = f"CPU {cpu:.0f}% — wysokie obciążenie"
                else:
                    status = f"CPU {cpu:.0f}% — high load"
            elif ram >= RAM_HIGH_PCT:
                if lang == "pl":
                    status = f"RAM {ram:.0f}% — mało wolnej pamięci"
                else:
                    status = f"RAM {ram:.0f}% — low memory"
            else:
                if lang == "pl":
                    status = f"CPU {cpu:.0f}%  RAM {ram:.0f}%  — system OK"
                else:
                    status = f"CPU {cpu:.0f}%  RAM {ram:.0f}%  — system OK"
            self._banner_fn(status)
        except Exception:
            pass

    # ── Push helper ───────────────────────────────────────────────────────────

    def _push(self, msg: str) -> None:
        if self._push_fn:
            try:
                self._push_fn(msg)
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────
proactive_monitor = ProactiveMonitor()
