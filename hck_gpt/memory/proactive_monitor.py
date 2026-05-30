# hck_gpt/memory/proactive_monitor.py
"""
Proactive Monitor - background thread that watches system state
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
  background thread - make sure to schedule it on the main thread
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
from import_core import register_component, update_status, STATUS_OK, STATUS_STARTING


# ── Thresholds ────────────────────────────────────────────────────────────────
CPU_HIGH_PCT      = 85.0
CPU_CRIT_PCT      = 95.0
RAM_HIGH_PCT      = 88.0
RAM_CRIT_PCT      = 93.0
DISK_LOW_GB       = 4.0
THROTTLE_RATIO    = 0.60   # below 60 % of max = throttled
CHECK_INTERVAL_S  = 45     # seconds between checks
MIN_GAP_SAME_S    = 300    # don't repeat same alert within 5 min

# Session budget - CHI 2025: max 3 unsolicited suggestions per 30-min window
SESSION_BUDGET      = 3
SESSION_WINDOW_S    = 1800   # 30-minute window

# Process anomaly - new heavy process threshold
PROC_SPIKE_PCT      = 30.0   # single process using >30% CPU -> spike alert
PROC_SPIKE_MIN_GAP  = 600    # 10 min cooldown per process name

# DeepMonitor thresholds
DM_CPU_TEMP_WARN    = 80.0   # CPU temp warning threshold (°C)
DM_CPU_TEMP_CRIT    = 90.0   # CPU temp critical threshold (°C)
DM_GPU_TEMP_WARN    = 82.0   # GPU temp warning threshold (°C)
DM_GPU_TEMP_CRIT    = 92.0   # GPU temp critical threshold (°C)
DM_CPU_FREQ_DROP    = 0.55   # CPU freq below 55% of max = severe throttle
DM_MULTI_DISK_LOW   = 8.0    # GB free - check ALL drives, not just C:
DM_CHECK_INTERVAL   = 3      # run DeepMonitor check every N main checks (~2 min)


# ── Message pools - PL + EN ───────────────────────────────────────────────────

_MSGS: dict[str, dict[str, list[str]]] = {
    "cpu_high": {
        "pl": [
            "hck_GPT: ⚠ CPU na {val}% od dłuższego czasu. Wpisz 'top procesy' żeby zobaczyć winowajcę.",
            "hck_GPT: CPU {val}% - coś go zjada. Jeśli to nie Ty, to kto? Wpisz 'top'.",
            "hck_GPT: Uwaga - procesor na {val}%. Normalne? Czy może ktoś góruje w tle?",
        ],
        "en": [
            "hck_GPT: ⚠ CPU sustained at {val}%. Type 'top processes' to see who's responsible.",
            "hck_GPT: CPU {val}% - something's eating it. Type 'top' to find out what.",
            "hck_GPT: Heads up - CPU at {val}%. Expected load, or something sneaky in the background?",
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
            "hck_GPT: ⚠ RAM na {val}% - system może zaraz sięgnąć po plik wymiany. Wpisz 'dlaczego ram wysoki'.",
            "hck_GPT: RAM zajęty w {val}%. Jeśli spowalnia - wpisz 'optymalizacja' albo zamknij przeglądarkę.",
        ],
        "en": [
            "hck_GPT: ⚠ RAM at {val}% - system may hit the pagefile soon. Ask me 'why is ram high'.",
            "hck_GPT: RAM at {val}%. If things feel sluggish - type 'optimization' or close the browser.",
        ],
    },
    "ram_crit": {
        "pl": [
            "hck_GPT: 🔴 RAM KRYTYCZNE {val}%! Możliwe spowolnienia lub crashe. Uruchom Flush RAM w Optimization.",
            "hck_GPT: 🔴 RAM na {val}%! Zamknij zbędne programy TERAZ albo skorzystaj z TURBO -> RAM Flush.",
        ],
        "en": [
            "hck_GPT: 🔴 RAM CRITICAL {val}%! Expect slowdowns or crashes. Run RAM Flush in Optimization.",
            "hck_GPT: 🔴 RAM at {val}%! Close unused apps NOW, or use TURBO -> RAM Flush.",
        ],
    },
    "throttle": {
        "pl": [
            "hck_GPT: ⚠ CPU throttluje - działa na {val}% mocy. Sprawdź temperatury ('temperatury').",
            "hck_GPT: Dławienie CPU wykryte ({val}% mocy). Zwykle to przegrzanie. Wpisz 'temperatura'.",
        ],
        "en": [
            "hck_GPT: ⚠ CPU throttling - running at {val}% of max power. Check temps ('temperatures').",
            "hck_GPT: CPU power limit hit ({val}% of max). Heat is usually the cause. Type 'temperature'.",
        ],
    },
    "disk_low": {
        "pl": [
            "hck_GPT: 💾 Dysk prawie pełny - tylko {val} GB wolne. Zakładka Optimization -> wyczyść TEMP.",
            "hck_GPT: Mało miejsca na dysku: {val} GB. Wpisz 'disk speed' żeby zobaczyć pełny stan.",
        ],
        "en": [
            "hck_GPT: 💾 Disk almost full - only {val} GB free. Optimization tab -> clear TEMP folder.",
            "hck_GPT: Low disk space: {val} GB left. Type 'disk speed' for full disk status.",
        ],
    },
    "long_session": {
        "pl": [
            "hck_GPT: Pracujesz już {val}h bez restartu. Wycieki pamięci mogą się zbierać - rozważ restart tej nocy.",
            "hck_GPT: Sesja trwa {val}h. RAM Flush może pomóc jeśli coś spowalnia. Zakładka Optimization.",
        ],
        "en": [
            "hck_GPT: {val}h uptime. Memory leaks may be building - consider a restart tonight.",
            "hck_GPT: Running for {val}h. RAM Flush can help if things feel sluggish. Check Optimization tab.",
        ],
    },
    "all_clear": {
        "pl": [
            "hck_GPT: ✓ System w normie - CPU i RAM OK.",
            "hck_GPT: Spokojnie. Brak anomalii.",
            "hck_GPT: Wszystko gra.",
        ],
        "en": [
            "hck_GPT: ✓ System healthy - CPU and RAM nominal.",
            "hck_GPT: All clear. No issues.",
            "hck_GPT: Looking good.",
        ],
    },
    # New heavy process appeared
    "process_spike": {
        "pl": [
            "hck_GPT: 🔍 Nowy proces: {val} zużywa dużo CPU. Wpisz 'co to {val}' jeśli nie wiesz co to.",
            "hck_GPT: ⚠ {val} wskoczył na listę top obciążeń. Normalnie go tu nie ma. Wpisz 'top procesy'.",
            "hck_GPT: Wykryłem {val} - zużywa znaczną część CPU. Przypadkowe uruchomienie czy zaplanowane?",
        ],
        "en": [
            "hck_GPT: 🔍 New heavy process: {val} appeared and is consuming a lot of CPU.",
            "hck_GPT: ⚠ {val} just jumped onto the top load list - it doesn't usually show up here.",
            "hck_GPT: Spotted {val} using significant CPU. Normal activity, or something unexpected?",
        ],
    },
    # Morning brief - first launch of the day
    "morning_brief": {
        "pl": [
            "hck_GPT: 🌅 Dzień dobry. System uruchomiony. Wpisz 'podsumowanie' by zobaczyć wczorajsze dane.",
            "hck_GPT: 🌅 Nowa sesja. Ostatnio było: {val}. Wpisz 'raport poranny' po pełny przegląd.",
            "hck_GPT: Dzień dobry! Monitoruję od startu. Wpisz 'zdrowie systemu' jeśli chcesz szybki check.",
        ],
        "en": [
            "hck_GPT: 🌅 Good morning. System is up. Type 'morning brief' to see yesterday's highlights.",
            "hck_GPT: 🌅 New session started. Last time: {val}. Ask me 'session digest' for a full review.",
            "hck_GPT: Good morning! Monitoring since boot. Ask 'health check' for a quick status report.",
        ],
    },
    # Sustained high temperature (not a spike - 15+ min)
    "temp_sustained": {
        "pl": [
            "hck_GPT: ⚠ CPU utrzymuje {val}°C od dłuższego czasu. Sprawdź czy chłodzenie działa poprawnie.",
            "hck_GPT: Temperatura CPU od kilkunastu minut: {val}°C. Wpisz 'temperatura' po analizę.",
        ],
        "en": [
            "hck_GPT: ⚠ CPU has been at {val}°C for a while now. Check if your cooling is working properly.",
            "hck_GPT: CPU temp sustained at {val}°C. Ask me 'temperature' for a detailed analysis.",
        ],
    },
    # Digest suggestion after long session
    "digest_suggestion": {
        "pl": [
            "hck_GPT: 💡 Jesteś aktywny od {val}h. Wpisz 'podsumowanie sesji' by zobaczyć jak szedł dzień.",
            "hck_GPT: {val}h sesji za Tobą. Wpisz 'co się działo dzisiaj' - mam ciekawe dane do pokazania.",
        ],
        "en": [
            "hck_GPT: 💡 You've been active for {val}h. Type 'session digest' to see how the day went.",
            "hck_GPT: {val}h session. Ask me 'what happened today' - I have some interesting data for you.",
        ],
    },
    # GPU temperature spike alert
    "gpu_temp_spike": {
        "pl": [
            "hck_GPT: ⚠ Spike temperatury GPU do {val}°C. Sprawdź chłodzenie lub obniż ustawienia graficzne.",
            "hck_GPT: GPU {val}°C - wysoko. Wpisz 'czy gpu się przegrzewa' po analizę.",
        ],
        "en": [
            "hck_GPT: ⚠ GPU temperature spike to {val}°C. Check cooling or lower graphics settings.",
            "hck_GPT: GPU at {val}°C - that's hot. Ask me 'is my gpu overheating' for analysis.",
        ],
    },
    # ── DeepMonitor-sourced alerts ────────────────────────────────────────────
    "cpu_temp_warn": {
        "pl": [
            "hck_GPT: 🌡 CPU {val}°C - podwyższona temperatura. Sprawdź czy pasta termoprzewodząca jest świeża.",
            "hck_GPT: Temperatura CPU: {val}°C. Jeśli to normalna praca, rozważ czyszczenie chłodzenia.",
        ],
        "en": [
            "hck_GPT: 🌡 CPU at {val}°C - elevated temperature. Check if thermal paste needs replacing.",
            "hck_GPT: CPU temp: {val}°C. If under normal load, consider cleaning your cooler.",
        ],
    },
    "cpu_temp_crit": {
        "pl": [
            "hck_GPT: 🔴 CPU KRYTYCZNE {val}°C! Ryzyko throttlowania lub uszkodzenia. Sprawdź chłodzenie TERAZ.",
            "hck_GPT: 🔴 CPU przegrzany: {val}°C! Wyłącz ciężkie zadania i sprawdź wentylator / pastę.",
        ],
        "en": [
            "hck_GPT: 🔴 CPU CRITICAL {val}°C! Risk of throttling or hardware damage. Check cooling NOW.",
            "hck_GPT: 🔴 CPU overheating at {val}°C! Stop heavy tasks and inspect fan/thermal paste.",
        ],
    },
    "gpu_temp_warn": {
        "pl": [
            "hck_GPT: 🌡 GPU {val}°C - przekroczono próg ostrzegawczy. Sprawdź wentylator karty graficznej.",
            "hck_GPT: GPU {val}°C - wyższa temperatura niż typowe. Czy kratka obudowy jest odkurzona?",
        ],
        "en": [
            "hck_GPT: 🌡 GPU at {val}°C - warning threshold exceeded. Check GPU fan curve.",
            "hck_GPT: GPU {val}°C - higher than typical. Is your case intake clear of dust?",
        ],
    },
    "gpu_temp_crit": {
        "pl": [
            "hck_GPT: 🔴 GPU KRYTYCZNE {val}°C! Karta graficzna może się throttlować lub wyłączyć.",
            "hck_GPT: 🔴 GPU przegrzany: {val}°C! Obniż oprawę graficzną lub sprawdź przepływ powietrza.",
        ],
        "en": [
            "hck_GPT: 🔴 GPU CRITICAL {val}°C! Card may throttle or emergency shutdown.",
            "hck_GPT: 🔴 GPU overheating at {val}°C! Lower graphics settings or improve airflow.",
        ],
    },
    "multi_disk_low": {
        "pl": [
            "hck_GPT: 💾 Dysk {val} ma mało miejsca. Sprawdź zakładkę Optymalizacja -> wyczyść tymczasowe.",
            "hck_GPT: Uwaga: {val} jest prawie pełny. Przenieś duże pliki lub usuń nieużywane aplikacje.",
        ],
        "en": [
            "hck_GPT: 💾 Drive {val} is running low on space. Check Optimization -> clear temp files.",
            "hck_GPT: Warning: {val} is nearly full. Move large files or uninstall unused apps.",
        ],
    },
    "cpu_freq_severe": {
        "pl": [
            "hck_GPT: ⚠ CPU działa tylko na {val}% mocy! Silne throttlowanie - sprawdź temperatury i plan zasilania.",
            "hck_GPT: Procesor dławiony do {val}% mocy. Przyczyną może być przegrzanie lub limit zasilania.",
        ],
        "en": [
            "hck_GPT: ⚠ CPU running at only {val}% of max power! Severe throttling - check temps and power plan.",
            "hck_GPT: CPU throttled to {val}% power. Likely cause: overheating or power limit.",
        ],
    },
    "sensor_health_insight": {
        "pl": [
            "hck_GPT: ✓ DeepMonitor: CPU {val}. Wszystkie sensory w normie.",
            "hck_GPT: 📊 Raport sensorów: {val}. System pod kontrolą.",
        ],
        "en": [
            "hck_GPT: ✓ DeepMonitor: CPU {val}. All sensors nominal.",
            "hck_GPT: 📊 Sensor report: {val}. System under control.",
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
        "hck_GPT: 💡 Zapytaj 'co zmieniło się od wczoraj' - powiem Ci co nowego w systemie.",
        "hck_GPT: 💡 Startup Manager w zakładkach pokazuje co włącza się z Windowsem.",
        "hck_GPT: 💡 Zapytaj 'zdrowie systemu' - odpowiem jedną, zwartą oceną.",
        "hck_GPT: 💡 Uczę się Twoich wzorców. Im dłużej działa app, tym lepiej znam Twój PC.",
        # Nowe wskazówki 2025 PL
        "hck_GPT: 💡 Przed graniem: wpisz 'gotowy do gry' - sprawdzę system i podpowiem co zamknąć.",
        "hck_GPT: 💡 Zapytaj 'to normalne?' po każdym wyniku który wygląda dziwnie - porównam z Twoją normą.",
        "hck_GPT: 💡 TURBO ma 3 tryby: Gaming, Work, Economy. Wpisz 'turbo boost' by wybrać właściwy.",
        "hck_GPT: 💡 Zapytaj 'historia temperatur' by zobaczyć jak się zachowywało ciepło w tej sesji.",
        "hck_GPT: 💡 Mogę wymusić zamknięcie niereagującego programu. Napisz 'kill [nazwa]'.",
        "hck_GPT: 💡 Zapytaj 'podsumowanie sesji' na koniec dnia - zestawię CPU, RAM i temperatury.",
        "hck_GPT: 💡 Ciekawi Cię co zjada internet? Wpisz 'co używa sieci'.",
        "hck_GPT: 💡 RAM na 90%? Wpisz 'zwolnij pamięć' - przeprowadzę Cię przez czyszczenie.",
        "hck_GPT: 💡 Zakładka MAP OF COMPONENTS pokazuje Twój PC jako schemat 2.5D z danymi na żywo.",
        "hck_GPT: 💡 Wpisz 'raport zdrowia' - podam ocenę liczbową każdego podzespołu.",
        "hck_GPT: 💡 Zapytaj 'kiedy ostatni restart' - sprawdzę uptime i ocenię czy warto zrestartować.",
        "hck_GPT: 💡 Wpisz 'co wiesz o moim PC' - pokażę wszystko co zebrałem o Twoim sprzęcie.",
        "hck_GPT: 💡 Temperatura CPU przekracza 80°C? Zapytaj 'czy CPU jest zbyt gorące' - ocenię sytuację.",
    ],
    "en": [
        "hck_GPT: 💡 AllMonitor tab shows historical min/max for each resource.",
        "hck_GPT: 💡 Type 'service setup' to launch the optimization wizard.",
        "hck_GPT: 💡 Type 'stats' to see today's usage averages.",
        "hck_GPT: 💡 The Efficiency tab shows live Top CPU and RAM processes.",
        "hck_GPT: 💡 You can ask 'what CPU do I have' and I'll give you full details.",
        "hck_GPT: 💡 I'm watching your PC silently. Ask me anything specific.",
        "hck_GPT: 💡 Type 'top processes' to see what's eating resources right now.",
        "hck_GPT: 💡 Ask 'what changed since yesterday' - I track daily deltas.",
        "hck_GPT: 💡 Startup Manager tab shows everything that boots with Windows.",
        "hck_GPT: 💡 Ask 'health check' - I'll give you a single, clean verdict.",
        "hck_GPT: 💡 I learn your usage patterns over time. The longer I run, the smarter I get.",
        "hck_GPT: 💡 If I push a message and you're confused - just ask 'what does that mean'.",
        # New 2025 tips
        "hck_GPT: 💡 Before gaming: type 'game ready' - I'll check your system and suggest what to close.",
        "hck_GPT: 💡 Ask 'is this normal?' after any reading that looks off - I'll compare it to your baseline.",
        "hck_GPT: 💡 TURBO has three modes: Gaming, Work, Economy. Ask 'turbo boost' to learn which fits you.",
        "hck_GPT: 💡 Ask 'thermal history' to see how temperatures behaved this session.",
        "hck_GPT: 💡 I can force-close unresponsive apps. Just ask 'kill [app name]'.",
        "hck_GPT: 💡 Ask 'session digest' at the end of the day - I'll summarize CPU, RAM, and temps.",
        "hck_GPT: 💡 Wondering what's using your internet? Ask 'what is using my network'.",
        "hck_GPT: 💡 Ask 'overclock check' - I'll tell you if your CPU or RAM is running above stock.",
        "hck_GPT: 💡 RAM at 90%? Ask 'free up RAM' - I'll walk you through flushing standby memory.",
        "hck_GPT: 💡 Ask 'what do you know about my PC' - I'll show you everything I've learned.",
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
        register_component("hck_gpt.proactive_monitor", self, STATUS_OK)
        self._banner_fn: Optional[Callable[[str], None]] = None
        self._lang:      str  = "en"   # matches panel default; updated on first user message
        self._thread:    Optional[threading.Thread] = None
        self._running:   bool = False

        # State tracking
        self._last_alert:  dict[str, float] = {}  # event_type -> last sent ts
        self._cpu_high_cnt: int = 0
        self._ram_crit_cnt: int = 0   # consecutive RAM-critical readings
        self._cpu_temp_high_cnt: int = 0  # consecutive high-temp readings
        self._session_start = time.time()
        self._session_long_alerted = False
        self._digest_suggested = False
        self._morning_brief_sent = False
        self._idle_tip_idx = 0

        # Problem anchor - tracks problems that were active so we can notify when resolved
        self._was_cpu_high:  bool = False
        self._was_ram_crit:  bool = False
        self._recovery_notified: dict[str, bool] = {}

        # Process spike tracking - {proc_name: last_alert_ts}
        self._proc_spike_last: dict[str, float] = {}

        # Session budget - CHI 2025: cap unsolicited alerts to avoid annoyance
        # Tracks timestamps of each push in a rolling 30-min window
        self._budget_log: List[float] = []

        # User-active flag - set True when panel receives user input recently
        # Allows softer alert tone when user is already in conversation
        self._user_active: bool = False
        self._user_active_until: float = 0.0

        # DeepMonitor state
        self._dm_check_tick: int = 0         # counter: run DM check every DM_CHECK_INTERVAL main cycles
        self._dm_cpu_temp_crit_cnt: int = 0  # consecutive CPU critical temp readings
        self._dm_gpu_temp_crit_cnt: int = 0  # consecutive GPU critical temp readings
        self._dm_healthy_report_due: bool = True  # send one "all clear" after issues resolve

    def set_user_active(self) -> None:
        """Call when user sends a message - suppresses redundant alerts for 5 min."""
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
        # Initial delay - let the app fully load first
        time.sleep(60)
        tip_counter = 0

        # Morning brief: send once at first check if it's a fresh daily session
        self._maybe_morning_brief()

        while self._running:
            try:
                self._check_system()
                tip_counter += 1
                self._dm_check_tick += 1
                # DeepMonitor sensor check every 3 main cycles (~2 min 15 sec)
                if self._dm_check_tick % DM_CHECK_INTERVAL == 0:
                    self._check_deepmonitor()
                # Show idle tip every ~8 checks (~6 min) when system is healthy
                if tip_counter % 8 == 0:
                    self._maybe_idle_tip()
                # Suggest session digest every ~26 checks (~20 min) for long sessions
                if tip_counter % 26 == 0:
                    self._maybe_digest_suggestion()
            except Exception:
                pass
            time.sleep(CHECK_INTERVAL_S)

    # ── System checks ─────────────────────────────────────────────────────────

    def _check_system(self) -> None:
        try:
            import psutil
        except ImportError:
            return

        # ── Prune _proc_spike_last to prevent unbounded memory growth ─────────
        # Over hours, short-lived processes (update helpers, installers, etc.)
        # accumulate in this dict indefinitely. Prune entries older than 1 h.
        now_prune = time.time()
        if self._proc_spike_last:
            self._proc_spike_last = {
                k: v for k, v in self._proc_spike_last.items()
                if now_prune - v < 3600
            }

        # Use interval=1 (was 2) - shorter blocking, still accurate enough
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory().percent
        freq = psutil.cpu_freq()

        # CPU - require 2 consecutive high readings before alerting
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

        # RAM - normal high (immediate, single reading)
        if ram >= RAM_HIGH_PCT and ram < RAM_CRIT_PCT:
            self._alert("ram_high", f"{ram:.0f}")

        # Throttling
        if freq and freq.max and freq.current and freq.max > 0:
            ratio = freq.current / freq.max
            if ratio < THROTTLE_RATIO:
                self._alert("throttle", f"{ratio*100:.0f}")

        # Disk - Windows-safe: try system drive first, fallback to partitions
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

        # RAM - sustained critical (2+ readings) gets stronger alert
        if ram >= RAM_CRIT_PCT:
            self._ram_crit_cnt += 1
            if self._ram_crit_cnt >= 2:
                self._alert("ram_crit", f"{ram:.0f}", urgent=True)
        else:
            self._ram_crit_cnt = max(0, self._ram_crit_cnt - 1)

        # GPU temperature spike + sustained CPU temp
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
            gpu_temp = snap.get("gpu_temp", None)
            if gpu_temp and gpu_temp > 87:
                self._alert("gpu_temp_spike", f"{gpu_temp:.0f}")

            cpu_temp = snap.get("cpu_temp", None)
            if cpu_temp and cpu_temp > 82:
                self._cpu_temp_high_cnt += 1
                # Only alert after 3 consecutive high readings (~2+ min sustained)
                if self._cpu_temp_high_cnt >= 3:
                    self._alert("temp_sustained", f"{cpu_temp:.0f}")
            else:
                self._cpu_temp_high_cnt = max(0, self._cpu_temp_high_cnt - 1)
        except Exception:
            pass

        # Process anomaly - new heavy process detection
        try:
            import psutil as _ps
            now = time.time()
            for proc in _ps.process_iter(["name", "cpu_percent"]):
                try:
                    pname = proc.info["name"] or ""
                    pcpu  = proc.info["cpu_percent"] or 0.0
                    if pcpu < PROC_SPIKE_PCT:
                        continue
                    last_spike = self._proc_spike_last.get(pname, 0)
                    if now - last_spike < PROC_SPIKE_MIN_GAP:
                        continue
                    self._proc_spike_last[pname] = now
                    self._alert("process_spike", pname)
                    break   # only one per check cycle
                except Exception:
                    continue
        except Exception:
            pass

        # Long session
        uptime_h = (time.time() - self._session_start) / 3600
        if uptime_h > 8 and not self._session_long_alerted:
            self._session_long_alerted = True
            self._alert("long_session", f"{uptime_h:.0f}")

        # ── Problem anchor - notify when issue resolves ───────────────────────
        if self._was_cpu_high and cpu < CPU_HIGH_PCT - 10:
            if not self._recovery_notified.get("cpu"):
                self._recovery_notified["cpu"] = True
                self._was_cpu_high = False
                if lang := self._lang:
                    msg = (f"hck_GPT: ✓ CPU wróciło do normy - teraz {cpu:.0f}%. Problem minął."
                           if lang == "pl" else
                           f"hck_GPT: ✓ CPU back to normal - now {cpu:.0f}%. Problem resolved.")
                    self._push(msg)
        elif cpu >= CPU_HIGH_PCT:
            self._was_cpu_high = True
            self._recovery_notified["cpu"] = False

        if self._was_ram_crit and ram < RAM_HIGH_PCT - 5:
            if not self._recovery_notified.get("ram"):
                self._recovery_notified["ram"] = True
                self._was_ram_crit = False
                if lang := self._lang:
                    msg = (f"hck_GPT: ✓ RAM wróciło do normy - {ram:.0f}%. Świeżo po kryzysie."
                           if lang == "pl" else
                           f"hck_GPT: ✓ RAM back to normal - {ram:.0f}%. Crisis over.")
                    self._push(msg)
        elif ram >= RAM_CRIT_PCT:
            self._was_ram_crit = True
            self._recovery_notified["ram"] = False

        # Banner: always update with current state
        self._update_banner(cpu, ram)

    # ── Alert dispatch ────────────────────────────────────────────────────────

    def _budget_ok(self, urgent: bool = False) -> bool:
        """Session budget check - CHI 2025: max 3 unsolicited alerts per 30-min window."""
        if urgent:
            return True   # critical alerts always bypass budget
        now = time.time()
        # prune entries older than SESSION_WINDOW_S
        self._budget_log = [t for t in self._budget_log
                            if now - t < SESSION_WINDOW_S]
        return len(self._budget_log) < SESSION_BUDGET

    def _alert(self, event_type: str, val: str, urgent: bool = False) -> None:
        now = time.time()
        last = self._last_alert.get(event_type, 0)
        gap = MIN_GAP_SAME_S // 2 if urgent else MIN_GAP_SAME_S
        if now - last < gap:
            return

        # Session budget gate (non-urgent only)
        if not self._budget_ok(urgent):
            return

        # Context-aware: if user is actively chatting, skip non-urgent low alerts
        if self._is_user_active() and not urgent:
            if event_type in ("cpu_high", "ram_high", "long_session",
                              "process_spike", "temp_sustained"):
                return  # don't interrupt active conversation with minor alerts

        self._last_alert[event_type] = now
        pool = _MSGS.get(event_type, {}).get(self._lang, [])
        if not pool:
            return

        msg = random.choice(pool).format(val=val)
        self._push(msg)
        if not urgent:
            self._budget_log.append(now)   # count against session budget

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

        # Respect session budget - tips count toward the 30-min limit
        if not self._budget_ok(urgent=False):
            return

        tips = _IDLE_TIPS.get(self._lang, _IDLE_TIPS.get("pl", []))
        if not tips:
            return
        msg = tips[self._idle_tip_idx % len(tips)]
        self._idle_tip_idx += 1
        self._push(msg)
        self._budget_log.append(time.time())

        # Allow user to ask "what does that mean?" about the tip
        try:
            from hck_gpt.memory.session_memory import session_memory
            session_memory.set_last_proactive(msg, {"type": "idle_tip"})
        except Exception:
            pass

    def _update_banner(self, cpu: float, ram: float) -> None:
        if not self._banner_fn:
            return
        try:
            lang = self._lang

            # Collect temperatures for banner (best-effort, non-blocking)
            temp_str = ""
            try:
                from core.hardware_sensors import get_cpu_temp, get_gpu_temp
                ct = get_cpu_temp()
                gt = get_gpu_temp()
                parts = []
                if ct:
                    parts.append(f"CPU {ct:.0f}°C")
                if gt:
                    parts.append(f"GPU {gt:.0f}°C")
                if parts:
                    temp_str = "  " + "  ".join(parts)
            except Exception:
                pass

            if cpu >= CPU_CRIT_PCT:
                status = (f"⚠ CPU KRYTYCZNE {cpu:.0f}%{temp_str}"
                          if lang == "pl" else
                          f"⚠ CPU CRITICAL {cpu:.0f}%{temp_str}")
            elif cpu >= CPU_HIGH_PCT:
                status = (f"CPU {cpu:.0f}% - wysokie{temp_str}"
                          if lang == "pl" else
                          f"CPU {cpu:.0f}% - high load{temp_str}")
            elif ram >= RAM_CRIT_PCT:
                status = (f"⚠ RAM KRYTYCZNE {ram:.0f}%{temp_str}"
                          if lang == "pl" else
                          f"⚠ RAM CRITICAL {ram:.0f}%{temp_str}")
            elif ram >= RAM_HIGH_PCT:
                status = (f"RAM {ram:.0f}% - mało pamięci{temp_str}"
                          if lang == "pl" else
                          f"RAM {ram:.0f}% - low memory{temp_str}")
            else:
                status = f"CPU {cpu:.0f}%  RAM {ram:.0f}%{temp_str}  - OK"

            self._banner_fn(status)
        except Exception:
            pass

    def _maybe_morning_brief(self) -> None:
        """Send a greeting on the first daily session (once per calendar day)."""
        if self._morning_brief_sent:
            return
        import datetime
        hour = datetime.datetime.now().hour
        # Only surface a morning brief between 06:00 and 12:00
        if not (6 <= hour < 12):
            self._morning_brief_sent = True   # mark sent so we don't retry later today
            return
        self._morning_brief_sent = True

        # Try to include yesterday's peak CPU as context
        try:
            from hck_stats_engine import query_api
            peak = query_api.get_yesterday_peak_cpu()
            val = f"CPU peak {peak:.0f}%" if peak else "all quiet"
        except Exception:
            val = "all quiet"

        pool = _MSGS.get("morning_brief", {}).get(self._lang, [])
        if pool:
            msg = random.choice(pool).format(val=val)
            self._push(msg)

    def _maybe_digest_suggestion(self) -> None:
        """Suggest a session digest after 2+ hours of active use."""
        if self._digest_suggested:
            return
        uptime_h = (time.time() - self._session_start) / 3600
        if uptime_h < 2.0:
            return
        # Only when system is calm (not already alerting about issues)
        try:
            import psutil
            if psutil.cpu_percent(interval=None) > 70:
                return
        except Exception:
            pass
        self._digest_suggested = True
        pool = _MSGS.get("digest_suggestion", {}).get(self._lang, [])
        if pool:
            msg = random.choice(pool).format(val=f"{uptime_h:.0f}")
            self._push(msg)

    # ── DeepMonitor deep-sensor check ─────────────────────────────────────────

    def _check_deepmonitor(self) -> None:
        """
        Rich hardware check powered by LibreHardwareMonitor sensor data
        (the same data source as DeepMonitor / pro_info_table).
        Monitors: CPU/GPU temperature trends, severe throttling, multi-drive
        disk space, and fires contextual bilingual alerts.
        """
        try:
            from core.hardware_sensors import get_cpu_temp, get_gpu_temp
        except ImportError:
            return

        cpu_temp = gpu_temp = cpu_mhz = cpu_max_mhz = None

        # ── CPU + GPU temperatures ─────────────────────────────────────────
        try:
            t = get_cpu_temp()
            if t:
                cpu_temp = float(t)
        except Exception:
            pass

        try:
            g = get_gpu_temp()
            if g:
                gpu_temp = float(g)
        except Exception:
            pass

        # CPU temperature tiers (warn / critical with consecutive-reading hysteresis)
        if cpu_temp is not None:
            if cpu_temp >= DM_CPU_TEMP_CRIT:
                self._dm_cpu_temp_crit_cnt += 1
                if self._dm_cpu_temp_crit_cnt >= 2:
                    self._alert("cpu_temp_crit", f"{cpu_temp:.0f}", urgent=True)
                    self._dm_healthy_report_due = True
            elif cpu_temp >= DM_CPU_TEMP_WARN:
                self._dm_cpu_temp_crit_cnt = max(0, self._dm_cpu_temp_crit_cnt - 1)
                self._alert("cpu_temp_warn", f"{cpu_temp:.0f}")
                self._dm_healthy_report_due = True
            else:
                self._dm_cpu_temp_crit_cnt = max(0, self._dm_cpu_temp_crit_cnt - 1)

        # GPU temperature tiers
        if gpu_temp is not None:
            if gpu_temp >= DM_GPU_TEMP_CRIT:
                self._dm_gpu_temp_crit_cnt += 1
                if self._dm_gpu_temp_crit_cnt >= 2:
                    self._alert("gpu_temp_crit", f"{gpu_temp:.0f}", urgent=True)
                    self._dm_healthy_report_due = True
            elif gpu_temp >= DM_GPU_TEMP_WARN:
                self._dm_gpu_temp_crit_cnt = max(0, self._dm_gpu_temp_crit_cnt - 1)
                self._alert("gpu_temp_warn", f"{gpu_temp:.0f}")
                self._dm_healthy_report_due = True
            else:
                self._dm_gpu_temp_crit_cnt = max(0, self._dm_gpu_temp_crit_cnt - 1)

        # ── Severe CPU frequency throttle ─────────────────────────────────
        try:
            import psutil as _ps
            freq = _ps.cpu_freq()
            if freq and freq.max and freq.current:
                ratio = freq.current / freq.max
                if ratio < DM_CPU_FREQ_DROP:
                    self._alert("cpu_freq_severe", f"{ratio*100:.0f}")
        except Exception:
            pass

        # ── Multi-drive disk space check ──────────────────────────────────
        try:
            import psutil as _ps
            for part in _ps.disk_partitions(all=False):
                if not part.mountpoint:
                    continue
                # Skip virtual drives (cd-rom, network)
                if part.fstype in ("cdfs", "udf", "") or "cdrom" in part.opts:
                    continue
                try:
                    usage = _ps.disk_usage(part.mountpoint)
                    free_gb = usage.free / 1_073_741_824
                    if free_gb < DM_MULTI_DISK_LOW:
                        drive_label = part.mountpoint.rstrip("\\").rstrip("/") or part.device
                        event_key = f"disk_low_{drive_label}"
                        self._alert("multi_disk_low", drive_label)
                except Exception:
                    continue
        except Exception:
            pass

        # ── Sensor health insight (positive feedback when all is well) ────
        # Send a brief positive status at most once per session, only after
        # a previous issue was resolved and the system has been calm.
        try:
            import psutil as _ps
            cpu_pct = _ps.cpu_percent(interval=None)
            ram_pct = _ps.virtual_memory().percent
            temps_ok = (
                (cpu_temp is None or cpu_temp < DM_CPU_TEMP_WARN) and
                (gpu_temp is None or gpu_temp < DM_GPU_TEMP_WARN)
            )
            if (self._dm_healthy_report_due and temps_ok
                    and cpu_pct < 60 and ram_pct < 75):
                self._dm_healthy_report_due = False
                t_str = ""
                parts = []
                if cpu_temp:
                    parts.append(f"{cpu_temp:.0f} C")
                if gpu_temp:
                    parts.append(f"GPU {gpu_temp:.0f} C")
                if parts:
                    t_str = "  |  ".join(parts)
                else:
                    t_str = f"{cpu_pct:.0f}%"
                pool = _MSGS.get("sensor_health_insight", {}).get(self._lang, [])
                if pool:
                    msg = random.choice(pool).format(val=t_str)
                    self._push(msg)
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
