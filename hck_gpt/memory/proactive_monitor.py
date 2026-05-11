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
            "hck_GPT: ⚠ CPU na {val}% od dłuższego czasu. Wpisz 'top procesy' żeby zobaczyć winowajcę.",
            "hck_GPT: CPU {val}% — coś go zjada. Jeśli to nie Ty, to kto? Wpisz 'top'.",
            "hck_GPT: Uwaga — procesor na {val}%. Normalne? Czy może ktoś góruje w tle?",
        ],
        "en": [
            "hck_GPT: ⚠ CPU sustained at {val}%. Type 'top processes' to see who's responsible.",
            "hck_GPT: CPU {val}% — something's eating it. Type 'top' to find out what.",
            "hck_GPT: Heads up — CPU at {val}%. Expected load, or something sneaky in the background?",
        ],
    },
    "cpu_crit": {
        "pl": [
            "hck_GPT: 🔴 CPU KRYTYCZNE {val}%! System może zacząć się dławić lub zawieszać.",
            "hck_GPT: Procesor na {val}%! To nie jest normalne. Sprawdź 'top procesy' natychmiast.",
        ],
        "en": [
            "hck_GPT: 🔴 CPU CRITICAL {val}%! System may start throttling or freezing.",
            "hck_GPT: CPU at {val}%! That's not normal. Run 'top processes' right now.",
        ],
    },
    "ram_high": {
        "pl": [
            "hck_GPT: ⚠ RAM na {val}% — system może zaraz sięgnąć po plik wymiany. Wpisz 'dlaczego ram wysoki'.",
            "hck_GPT: RAM zajęty w {val}%. Jeśli spowalnia — wpisz 'optymalizacja' albo zamknij przeglądarkę.",
        ],
        "en": [
            "hck_GPT: ⚠ RAM at {val}% — system may hit the pagefile soon. Ask me 'why is ram high'.",
            "hck_GPT: RAM at {val}%. If things feel sluggish — type 'optimization' or close the browser.",
        ],
    },
    "ram_crit": {
        "pl": [
            "hck_GPT: 🔴 RAM KRYTYCZNE {val}%! Możliwe spowolnienia lub crashe. Uruchom Flush RAM w Optimization.",
            "hck_GPT: 🔴 RAM na {val}%! Zamknij zbędne programy TERAZ albo skorzystaj z TURBO → RAM Flush.",
        ],
        "en": [
            "hck_GPT: 🔴 RAM CRITICAL {val}%! Expect slowdowns or crashes. Run RAM Flush in Optimization.",
            "hck_GPT: 🔴 RAM at {val}%! Close unused apps NOW, or use TURBO → RAM Flush.",
        ],
    },
    "throttle": {
        "pl": [
            "hck_GPT: ⚠ CPU throttluje — działa na {val}% mocy. Sprawdź temperatury ('temperatury').",
            "hck_GPT: Dławienie CPU wykryte ({val}% mocy). Zwykle to przegrzanie. Wpisz 'temperatura'.",
        ],
        "en": [
            "hck_GPT: ⚠ CPU throttling — running at {val}% of max power. Check temps ('temperatures').",
            "hck_GPT: CPU power limit hit ({val}% of max). Heat is usually the cause. Type 'temperature'.",
        ],
    },
    "disk_low": {
        "pl": [
            "hck_GPT: 💾 Dysk prawie pełny — tylko {val} GB wolne. Zakładka Optimization → wyczyść TEMP.",
            "hck_GPT: Mało miejsca na dysku: {val} GB. Wpisz 'disk speed' żeby zobaczyć pełny stan.",
        ],
        "en": [
            "hck_GPT: 💾 Disk almost full — only {val} GB free. Optimization tab → clear TEMP folder.",
            "hck_GPT: Low disk space: {val} GB left. Type 'disk speed' for full disk status.",
        ],
    },
    "long_session": {
        "pl": [
            "hck_GPT: Pracujesz już {val}h bez restartu. Wycieki pamięci mogą się zbierać — rozważ restart tej nocy.",
            "hck_GPT: Sesja trwa {val}h. RAM Flush może pomóc jeśli coś spowalnia. Zakładka Optimization.",
        ],
        "en": [
            "hck_GPT: {val}h uptime. Memory leaks may be building — consider a restart tonight.",
            "hck_GPT: Running for {val}h. RAM Flush can help if things feel sluggish. Check Optimization tab.",
        ],
    },
    "all_clear": {
        "pl": [
            "hck_GPT: ✓ System w normie — CPU i RAM OK.",
            "hck_GPT: Spokojnie. Brak anomalii.",
            "hck_GPT: Wszystko gra.",
        ],
        "en": [
            "hck_GPT: ✓ System healthy — CPU and RAM nominal.",
            "hck_GPT: All clear. No issues.",
            "hck_GPT: Looking good.",
        ],
    },
    # New: GPU temperature spike alert
    "gpu_temp_spike": {
        "pl": [
            "hck_GPT: ⚠ Spike temperatury GPU do {val}°C. Sprawdź chłodzenie lub obniż ustawienia graficzne.",
            "hck_GPT: GPU {val}°C — wysoko. Wpisz 'czy gpu się przegrzewa' po analizę.",
        ],
        "en": [
            "hck_GPT: ⚠ GPU temperature spike to {val}°C. Check cooling or lower graphics settings.",
            "hck_GPT: GPU at {val}°C — that's hot. Ask me 'is my gpu overheating' for analysis.",
        ],
    },
}

# Periodic tips shown when system is idle/healthy
_IDLE_TIPS: dict[str, list[str]] = {
    "pl": [
        "hck_GPT: 💡 Zakładka AllMonitor pokazuje historyczne min/max dla każdego zasobu.",
        "hck_GPT: 💡 'service setup' w chatie uruchamia kreator optymalizacji.",
        "hck_GPT: 💡 Wpisz 'stats' by zobaczyć dzisiejsze średnie użycia.",
        "hck_GPT: 💡 Zakładka Efficiency pokazuje Top CPU i RAM procesy na żywo.",
        "hck_GPT: 💡 Wiesz, że możesz zapytać 'jaki mam procesor' i podam Ci pełne dane?",
        "hck_GPT: 💡 Monitoruję Twój PC cicho w tle. Pisz jeśli chcesz coś sprawdzić.",
        "hck_GPT: 💡 Wpisz 'top procesy' by zobaczyć co teraz najbardziej obciąża system.",
        "hck_GPT: 💡 Zapytaj 'co zmieniło się od wczoraj' — powiem Ci co nowego w systemie.",
        "hck_GPT: 💡 Startup Manager w zakładkach pokazuje co włącza się z Windowsem.",
        "hck_GPT: 💡 Zapytaj 'zdrowie systemu' — odpowiem jedną, zwartą oceną.",
        "hck_GPT: 💡 Uczę się Twoich wzorców. Im dłużej działa app, tym lepiej znam Twój PC.",
    ],
    "en": [
        "hck_GPT: 💡 AllMonitor tab shows historical min/max for each resource.",
        "hck_GPT: 💡 Type 'service setup' to launch the optimization wizard.",
        "hck_GPT: 💡 Type 'stats' to see today's usage averages.",
        "hck_GPT: 💡 The Efficiency tab shows live Top CPU and RAM processes.",
        "hck_GPT: 💡 You can ask 'what CPU do I have' and I'll give you full details.",
        "hck_GPT: 💡 I'm watching your PC silently. Ask me anything specific.",
        "hck_GPT: 💡 Type 'top processes' to see what's eating resources right now.",
        "hck_GPT: 💡 Ask 'what changed since yesterday' — I track daily deltas.",
        "hck_GPT: 💡 Startup Manager tab shows everything that boots with Windows.",
        "hck_GPT: 💡 Ask 'health check' — I'll give you a single, clean verdict.",
        "hck_GPT: 💡 I learn your usage patterns over time. The longer I run, the smarter I get.",
        "hck_GPT: 💡 If I push a message and you're confused — just ask 'what does that mean'.",
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
        self._lang:      str  = "en"   # matches panel default; updated on first user message
        self._thread:    Optional[threading.Thread] = None
        self._running:   bool = False

        # State tracking
        self._last_alert:  dict[str, float] = {}  # event_type → last sent ts
        self._cpu_high_cnt: int = 0
        self._ram_crit_cnt: int = 0   # consecutive RAM-critical readings
        self._session_start = time.time()
        self._session_long_alerted = False
        self._idle_tip_idx = 0

        # Problem anchor — tracks problems that were active so we can notify when resolved
        self._was_cpu_high:  bool = False
        self._was_ram_crit:  bool = False
        self._recovery_notified: dict[str, bool] = {}

        # User-active flag — set True when panel receives user input recently
        # Allows softer alert tone when user is already in conversation
        self._user_active: bool = False
        self._user_active_until: float = 0.0

    def set_user_active(self) -> None:
        """Call when user sends a message — suppresses redundant alerts for 5 min."""
        self._user_active = True
        self._user_active_until = time.time() + 300

    def _is_user_active(self) -> bool:
        if self._user_active and time.time() < self._user_active_until:
            return True
        self._user_active = False
        return False

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

        # RAM — normal high (immediate, single reading)
        if ram >= RAM_HIGH_PCT and ram < RAM_CRIT_PCT:
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

        # RAM — sustained critical (2+ readings) gets stronger alert
        if ram >= RAM_CRIT_PCT:
            self._ram_crit_cnt += 1
            if self._ram_crit_cnt >= 2:
                self._alert("ram_crit", f"{ram:.0f}", urgent=True)
        else:
            self._ram_crit_cnt = max(0, self._ram_crit_cnt - 1)

        # GPU temperature spike (via psutil on Linux; scheduler snapshot on Windows)
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
            gpu_temp = snap.get("gpu_temp", None)
            if gpu_temp and gpu_temp > 87:
                self._alert("gpu_temp_spike", f"{gpu_temp:.0f}")
        except Exception:
            pass

        # Long session
        uptime_h = (time.time() - self._session_start) / 3600
        if uptime_h > 8 and not self._session_long_alerted:
            self._session_long_alerted = True
            self._alert("long_session", f"{uptime_h:.0f}")

        # ── Problem anchor — notify when issue resolves ───────────────────────
        if self._was_cpu_high and cpu < CPU_HIGH_PCT - 10:
            if not self._recovery_notified.get("cpu"):
                self._recovery_notified["cpu"] = True
                self._was_cpu_high = False
                if lang := self._lang:
                    msg = (f"hck_GPT: ✓ CPU wróciło do normy — teraz {cpu:.0f}%. Problem minął."
                           if lang == "pl" else
                           f"hck_GPT: ✓ CPU back to normal — now {cpu:.0f}%. Problem resolved.")
                    self._push(msg)
        elif cpu >= CPU_HIGH_PCT:
            self._was_cpu_high = True
            self._recovery_notified["cpu"] = False

        if self._was_ram_crit and ram < RAM_HIGH_PCT - 5:
            if not self._recovery_notified.get("ram"):
                self._recovery_notified["ram"] = True
                self._was_ram_crit = False
                if lang := self._lang:
                    msg = (f"hck_GPT: ✓ RAM wróciło do normy — {ram:.0f}%. Świeżo po kryzysie."
                           if lang == "pl" else
                           f"hck_GPT: ✓ RAM back to normal — {ram:.0f}%. Crisis over.")
                    self._push(msg)
        elif ram >= RAM_CRIT_PCT:
            self._was_ram_crit = True
            self._recovery_notified["ram"] = False

        # Banner: always update with current state
        self._update_banner(cpu, ram)

    # ── Alert dispatch ────────────────────────────────────────────────────────

    def _alert(self, event_type: str, val: str, urgent: bool = False) -> None:
        now = time.time()
        last = self._last_alert.get(event_type, 0)
        gap = MIN_GAP_SAME_S // 2 if urgent else MIN_GAP_SAME_S
        if now - last < gap:
            return

        # Context-aware: if user is actively chatting, skip non-urgent low alerts
        if self._is_user_active() and not urgent:
            if event_type in ("cpu_high", "ram_high", "long_session"):
                return  # don't interrupt active conversation with minor alerts

        self._last_alert[event_type] = now
        pool = _MSGS.get(event_type, {}).get(self._lang, [])
        if not pool:
            return

        msg = random.choice(pool).format(val=val)
        self._push(msg)

        # Record in session memory + store for follow-up "explain that" queries
        try:
            from hck_gpt.memory.session_memory import session_memory
            session_memory.record_event(event_type, f"{val}")
            session_memory.set_last_proactive(
                msg, {"type": event_type, "val": val}
            )
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
