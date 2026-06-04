# hck_gpt/engine/hybrid_engine.py
"""
Hybrid Engine - the brain of hck_GPT

Decision flow for every user message:
  1. intent_parser -> ParseResult with confidence score
  2. confidence >= RULE_THRESHOLD (0.65)
       -> FAST RULE ENGINE (response_builder)   - deterministic, instant
  3. confidence < RULE_THRESHOLD  AND  Ollama available
       -> LOCAL LLM (Ollama)  with rich system prompt + full PC context
  4. Ollama unavailable / timeout  AND  confidence >= LOW_THRESHOLD (0.35)
       -> RULE ENGINE FALLBACK (best effort)
  5. All else -> None (ChatHandler falls through to legacy routes)

Ollama integration:
  - Requires Ollama running locally (http://localhost:11434)
  - Default model: configurable via HybridEngine.model attribute
  - Availability is cached for 5 minutes (no constant polling)
  - Timeout: 10 seconds (graceful fallback on slow response)
  - Streaming disabled - we wait for the complete response

System prompt design:
  - Identity: who hck_GPT is and what it's for
  - Live PC state snapshot (CPU, RAM, temps, processes)
  - Hardware profile (CPU model, GPU, RAM specs)
  - Session context (summary, recent chat, alerts, trends)
  - Hard rules: short answers, no markdown headers, practical
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List, Optional
from import_core import register_component, update_status, STATUS_OK, STATUS_IDLE, STATUS_WARN

# ── Constants ──────────────────────────────────────────────────────────────────
OLLAMA_HOST        = "localhost"
OLLAMA_PORT        = 11434
DEFAULT_MODEL      = "llama3.2"          # override: hybrid_engine.model = "mistral"
RULE_THRESHOLD     = 0.65               # above -> rule engine (deterministic); raised from 0.60 so borderline queries get Ollama's natural language
LOW_THRESHOLD      = 0.20               # below -> no rule fallback at all
OLLAMA_TIMEOUT     = 10                 # seconds before giving up on Ollama
AVAILABILITY_TTL   = 300               # re-check Ollama availability every 5 min
MAX_TOKENS         = 220               # max LLM output tokens (keep responses short)
TEMPERATURE        = 0.72              # default LLM temperature

# Intent-aware temperature: factual queries need precision, small talk needs warmth
_INTENT_TEMPERATURE: Dict[str, float] = {
    # Factual / diagnostic - deterministic, low creativity
    "hw_cpu":         0.35,
    "hw_gpu":         0.35,
    "hw_ram":         0.35,
    "hw_storage":     0.35,
    "hw_all":         0.35,
    "hw_motherboard": 0.35,
    "temperature":    0.35,
    "throttle_check": 0.35,
    "stats":          0.35,
    "processes":      0.35,
    "disk_health":    0.35,
    "ram_why_high":   0.40,
    "gpu_temp_why":   0.40,
    "why_slow":       0.45,
    "turbo_boost":    0.45,
    "process_info":   0.40,
    "session_compare":0.40,
    # Performance / optimization - slight creativity OK
    "performance":    0.55,
    "optimization":   0.55,
    "power_plan":     0.50,
    "speed_up_pc":    0.55,
    # Open-ended / conversational - more creative
    "small_talk":     0.80,
    "about_program":  0.65,
    "help":           0.60,
    "health_check":   0.50,
    "unnecessary_programs": 0.50,
    "virus_check":    0.50,
    # New community intents
    "fan_noise_history":    0.40,
    "driver_status":        0.35,
    "gaming_vs_work_time":  0.45,
    "process_identity":     0.40,
    "stale_apps":           0.50,
    "fps_degradation":      0.45,
    "app_behavior_change":  0.45,
    "startup_slowdown":     0.50,
    "temp_comparison":      0.35,
    "crash_context":        0.45,
    "game_hardware_stress": 0.45,
    "battery_drain_rate":   0.40,
    "power_after_restart":  0.40,
    # Second wave community intents
    "game_can_run":         0.40,
    "gaming_ram_usage":     0.40,
    "daily_ram_usage":      0.40,
    "battery_estimate":     0.45,
    "upgrade_feasibility":  0.40,
    "top_resource_hog":     0.40,
    # Previously vocab-only (now explicitly temperature-mapped)
    "browser_cache":        0.45,
    "ram_compare":          0.40,
    "swap_analysis":        0.40,
    "usb_transfer":         0.40,
    "network_usage":        0.40,
    "startup_safety":       0.50,
}


# ── Ollama HTTP Client ─────────────────────────────────────────────────────────

class OllamaClient:
    """
    Minimal HTTP client for Ollama local API.
    Uses only stdlib http.client - no requests dependency.
    """

    def is_available(self) -> bool:
        """Ping /api/tags - returns True if Ollama is running."""
        import http.client
        conn = None
        try:
            conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=2)
            conn.request("GET", "/api/tags")
            resp = conn.getresponse()
            resp.read()   # drain buffer
            return resp.status == 200
        except Exception:
            return False
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def list_models(self) -> List[str]:
        """Return list of locally available model names."""
        import http.client
        conn = None
        try:
            conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=3)
            conn.request("GET", "/api/tags")
            resp = conn.getresponse()
            if resp.status == 200:
                body = resp.read()
                data = json.loads(body.decode("utf-8", errors="replace"))
                return [
                    m.get("name", "")
                    for m in data.get("models", [])
                    if m.get("name")
                ]
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return []

    def generate(
        self,
        model: str,
        prompt: str,
        system: str,
        timeout: int = OLLAMA_TIMEOUT,
        temperature: float = TEMPERATURE,
    ) -> Optional[str]:
        """
        POST /api/generate - non-streaming.
        Returns the raw response text, or None on failure.
        """
        payload = json.dumps({
            "model":  model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature":  temperature,
                "num_predict":  MAX_TOKENS,
                "stop": ["\n\n\n", "User:", "hck_GPT:", "==="],
            },
        }, ensure_ascii=False).encode("utf-8")

        import http.client
        conn = None
        try:
            conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=timeout)
            conn.request(
                "POST", "/api/generate",
                body=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            resp = conn.getresponse()
            if resp.status == 200:
                body = resp.read()
                raw  = json.loads(body.decode("utf-8", errors="replace"))
                return (raw.get("response") or "").strip()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        return None


# ── Hybrid Engine ─────────────────────────────────────────────────────────────

class HybridEngine:
    """
    Routes each user message to the best available responder:
    rule engine (fast) or local LLM (smart).
    """

    # Intents that should always prefer Ollama (conversational / open-ended / personality-heavy)
    _OLLAMA_PREFERRED_INTENTS = frozenset({
        "small_talk",
        "unknown",
        "fun_roast",       # needs personality, not deterministic templates
        "about_author",    # open-ended, conversational
        "ai_context",      # self-reflection, LLM handles better
    })

    # FEATURE: Context Time-Windowing
    # Maps intent into relevant history window in minutes for the LLM prompt.
    # Intents that ask about NOW get a tight 5-min window (fresh data).
    # Intents doing Time-Travel get a wide window (hours/days worth of context).
    _CONTEXT_WINDOWS: dict[str, int] = {
        # Real-time diagnostics - last 5 min is enough
        "hw_cpu":           5,
        "hw_gpu":           5,
        "hw_ram":           5,
        "temperature":      10,
        "throttle_check":   5,
        "performance":      5,
        "processes":        5,
        # Session-level - last 30 min
        "health_check":     30,
        "ram_why_high":     30,
        "gpu_temp_why":     30,
        "why_slow":         30,
        "stats":            60,
        # Time-Travel queries - need multi-hour / day context
        "temp_comparison":  10080,   # 7 days
        "fps_degradation":  10080,   # 7 days
        "app_behavior_change": 2880, # 2 days
        "crash_context":    240,     # 4 hours
        "fan_noise_history": 1440,   # 24 hours
        "game_hardware_stress": 2880,
        "session_compare":  2880,
        "perf_change":      2880,
        "pc_changes":       2880,
        # Second wave community intents
        "gaming_ram_usage": 2880,   # 2 days of gaming history
        "daily_ram_usage":  10080,  # 7 days for daily average
        "game_can_run":     5,      # live hardware snapshot
        "battery_estimate": 5,      # current battery state
        "upgrade_feasibility": 5,   # live hardware info
        "top_resource_hog": 5,      # live process snapshot
        "browser_cache":    30,     # current + recent session
        "ram_compare":      2880,
        "swap_analysis":    30,
        "usb_transfer":     5,
        "network_usage":    5,
        "startup_safety":   5,
        # Hardware info - snapshot queries
        "hw_storage":       5,
        "hw_all":           5,
        "hw_motherboard":   5,
        # System state - live
        "uptime":           5,
        "disk_speed":       5,
        "disk_health":      5,
        "process_info":     5,
        "turbo_boost":      5,
        "voltage_check":    5,
        "fan_speed":        5,
        "game_ready":       5,
        "process_kill":     5,
        "ram_flush":        5,
        "overclock_check":  5,
        "ai_context":       5,
        "startup_check":    5,
        # Short session window
        "disk_usage_why":   30,
        "optimization":     30,
        "speed_up_pc":      30,
        "process_deep_dive":30,
        "symptom_noisy":    60,
        "driver_status":    60,
        "process_identity": 30,
        # Medium history
        "battery_drain":    120,    # 2 hours of drain data
        "battery_drain_rate":120,
        "session_digest":   480,    # 8-hour session summary
        "system_risk":      480,
        "power_after_restart": 480,
        "symptom_freeze":   240,    # 4 hours pre-freeze context
        # Long history - trend analysis
        "gaming_session":   2880,   # 2 days gaming history
        "gaming_vs_work_time": 2880,
        "stale_apps":       10080,  # 7 days
        "weekly_trends":    10080,
        "thermal_prediction": 10080,
        "thermal_history":  10080,
        "compare_baseline": 10080,
        "morning_brief":    10080,
        # Other
        "fun_roast":        30,
        "startup_slowdown": 5,
        "power_plan":       5,
        "virus_check":      30,
        "unnecessary_programs": 30,
        "about_program":    5,
        "about_author":     5,
        "help":             5,
        "explain_proactive":30,
    }

    def __init__(self) -> None:
        self._ollama = OllamaClient()
        self.model   = DEFAULT_MODEL

        # Availability cache
        self._available:            Optional[bool] = None
        self._available_checked_at: float          = 0.0
        self._available_model:      str            = ""   # model confirmed present

        # Temporary unavailability after a timeout (shorter than full TTL)
        self._temp_unavail_until:   float          = 0.0

        # Stats (for diagnostics)
        self.llm_calls:       int = 0
        self.llm_successes:   int = 0
        self.rule_calls:      int = 0

        register_component('hck_gpt.engine', self, STATUS_IDLE)

    # ── Public API ────────────────────────────────────────────────────────────

    def process(
        self,
        msg: str,
        result: Any,           # ParseResult from intent_parser
        lang: str = "pl",
    ) -> Optional[List[str]]:
        """
        Main decision router.
        Returns a list of response lines, or None (caller falls through).
        """
        try:
            from hck_gpt.responses.builder import response_builder
        except Exception:
            return None

        confidence = getattr(result, "confidence", 0.0)
        intent     = getattr(result, "intent",     "unknown")

        # ── OPEN-ENDED INTENTS -> always try Ollama first ──────────────────────
        if intent in self._OLLAMA_PREFERRED_INTENTS:
            if self._check_available():
                llm_resp = self._query_llm(msg, lang, result)
                if llm_resp:
                    self.llm_successes += 1
                    return llm_resp
            # Fallback for small_talk even without Ollama
            if intent == "small_talk":
                resp = response_builder.build(result, lang)
                if resp:
                    self.rule_calls += 1
                    return resp
            return None

        # ── HIGH CONFIDENCE -> rule engine (instant, deterministic) ────────────
        if confidence >= RULE_THRESHOLD:
            resp = response_builder.build(result, lang)
            if resp:
                self.rule_calls += 1
                return resp

        # ── MEDIUM CONFIDENCE -> try Ollama, then rule fallback ────────────────
        if self._check_available():
            llm_resp = self._query_llm(msg, lang, result)
            if llm_resp:
                self.llm_successes += 1
                return llm_resp

        if confidence >= LOW_THRESHOLD:
            resp = response_builder.build(result, lang)
            if resp:
                self.rule_calls += 1
                return resp

        return None

    @property
    def ollama_online(self) -> bool:
        """Returns cached availability status (for UI display)."""
        return bool(self._available) and time.time() >= self._temp_unavail_until

    def refresh_availability(self) -> bool:
        """Force-check Ollama availability (ignores cache)."""
        self._available_checked_at = 0
        self._temp_unavail_until   = 0
        return self._check_available()

    # ── Availability check ────────────────────────────────────────────────────

    def _check_available(self) -> bool:
        now = time.time()
        # Temporarily unavailable (e.g. after timeout) - don't retry yet
        if now < self._temp_unavail_until:
            return False
        if self._available is None or (now - self._available_checked_at) > AVAILABILITY_TTL:
            self._available            = self._ollama.is_available()
            self._available_checked_at = now
            if self._available:
                self._pick_best_model()
        return bool(self._available)

    def _pick_best_model(self) -> None:
        """
        From locally available models, pick the best one for PC assistant work.
        Preference: llama3 > mistral > phi3 > gemma > anything > default.
        """
        try:
            models = self._ollama.list_models()
            if not models:
                return
            # Preference order
            preferred = [
                "llama3.2", "llama3.1", "llama3",
                "mistral", "mistral-nemo",
                "phi3", "phi3.5",
                "gemma2", "gemma",
                "qwen2.5", "qwen2",
            ]
            for pref in preferred:
                for m in models:
                    if pref in m.lower():
                        self.model = m
                        self._available_model = m
                        return
            # Take first available
            self.model = models[0]
            self._available_model = models[0]
        except Exception:
            pass

    # ── LLM query ─────────────────────────────────────────────────────────────

    def _query_llm(
        self, msg: str, lang: str, result: Any = None
    ) -> Optional[List[str]]:
        """Build full prompt + call Ollama, return formatted response lines."""
        self.llm_calls += 1
        intent = getattr(result, "intent", "unknown") if result else "unknown"
        temperature = _INTENT_TEMPERATURE.get(intent, TEMPERATURE)
        try:
            system_prompt = self._build_system_prompt(lang, result)
            raw = self._ollama.generate(
                model=self.model,
                prompt=msg,
                system=system_prompt,
                timeout=OLLAMA_TIMEOUT,
                temperature=temperature,
            )
        except Exception:
            # On exception, cool down for 60s (not 5min) - could be transient
            self._temp_unavail_until = time.time() + 60
            return None

        if not raw:
            # Empty response - may be model loading; short cool-down
            self._temp_unavail_until = time.time() + 30
            return None

        return self._format_response(raw, lang)

    def _format_response(self, raw: str, lang: str) -> List[str]:
        """
        Clean and split LLM output into displayable lines.
        - Prefix first line with 'hck_GPT:'
        - Strip markdown artifacts
        - Cap at 10 lines
        """
        # Remove markdown artifacts and normalise bullet styles
        clean = (raw
                 .replace("**", "")
                 .replace("##", "")
                 .replace("# ", "")
                 .replace("---", "")
                 .replace("\n- ", "\n• ")    # markdown dash-bullet -> unicode bullet
                 .replace("\n* ", "\n• ")    # markdown star-bullet -> unicode bullet
                 .strip())

        raw_lines = [l.strip() for l in clean.split("\n") if l.strip()]
        if not raw_lines:
            return []

        result: List[str] = []
        for i, line in enumerate(raw_lines[:10]):
            if i == 0:
                # First line gets the hck_GPT: prefix
                if not line.startswith("hck_GPT:"):
                    line = f"hck_GPT: {line}"
            else:
                # Continuation lines indented
                line = f"  {line}"
            result.append(line)

        return result

    # ── System prompt builder ─────────────────────────────────────────────────

    def _build_system_prompt(self, lang: str, result: Any = None) -> str:
        """
        Constructs a comprehensive system prompt for Ollama.
        Sections:
          [Identity]     - who hck_GPT is
          [Intent]       - detected query intent (helps LLM focus)
          [Rules]        - how to respond
          [PC Context]   - live snapshot + hardware + history
          [Language]     - which language to use
        """
        # Gather context - MEGA FEATURE: Context Time-Windowing
        # Pick relevant history window based on intent type
        intent = getattr(result, "intent", "unknown") if result else "unknown"
        window_minutes = self._CONTEXT_WINDOWS.get(intent, 30)
        try:
            from hck_gpt.context.system_context import system_context
            pc_ctx = system_context.build_llm_context_windowed(lang, window_minutes)
        except Exception:
            pc_ctx = "(PC context unavailable)"

        # Identity block
        identity = (
            "You are hck_GPT, an AI assistant deeply embedded in PC Workman HCK - "
            "a professional Windows PC monitoring and optimization application. "
            "You have direct access to the user's real-time system data: "
            "CPU and RAM usage, temperatures, running processes, hardware specs, "
            "today's usage averages, and past system alerts. "
            "You are not a generic assistant - you are a specialized PC expert "
            "who knows this specific computer intimately."
        )

        # Intent hint - guides the LLM on what kind of answer is expected
        intent_block = self._build_intent_hint(result, lang)

        # Recent conversation context (last 3 exchanges)
        conv_ctx = ""
        try:
            from hck_gpt.memory.session_memory import session_memory as _sm
            recent = _sm.recent_exchange_text(n_pairs=3)
            if recent:
                conv_ctx = f"\n\n[Recent Conversation]\n{recent}"
        except Exception:
            pass

        # Hard rules
        rules = (
            "RULES - follow these strictly:\n"
            "1. Responses must be SHORT - 1 to 6 lines maximum. No walls of text.\n"
            "2. Never use markdown headers (no # or ##), no bullet point lists with dashes.\n"
            "3. Never make up hardware data - only use what is provided in [PC Context].\n"
            "4. Start your reply with the most relevant fact, not with 'As an AI...' or similar.\n"
            "5. If the user asks something outside PC topics (weather, recipes, etc.) - "
            "politely redirect: 'I specialize in PC diagnostics - ask me about your hardware or system.'\n"
            "6. Numbers always matter - include them (%, MHz, GB, °C) when available.\n"
            "7. Be direct, warm, and practical - like a knowledgeable friend who knows this PC intimately.\n"
            "8. If something is concerning (high CPU, throttling, low RAM, high temps), say so clearly.\n"
            "9. Never start a line with 'hck_GPT:' - that prefix is added automatically.\n"
            "10. Reference the recent conversation context when it's relevant - show continuity.\n"
            "11. If the user seems frustrated, acknowledge it briefly before the answer.\n"
            "12. Personality: you're knowledgeable, slightly dry-humored, and care about this PC."
        )

        # Language instruction
        if lang == "en":
            lang_rule = "LANGUAGE: Respond in ENGLISH. The user is writing in English."
        else:
            lang_rule = (
                "JĘZYK: Odpowiadaj PO POLSKU. Użytkownik pisze po polsku. "
                "Używaj naturalnego, potocznego języka - nie formalnego."
            )

        # Combine - include intent block only when non-empty
        sections = [
            f"[Identity]\n{identity}",
            f"[Rules]\n{rules}",
        ]
        if intent_block:
            sections.append(f"[Intent]\n{intent_block}")
        sections.append(f"[PC Context]\n{pc_ctx}{conv_ctx}")
        sections.append(f"[Language]\n{lang_rule}")

        return "\n\n".join(sections)

    # ── Intent hint builder ───────────────────────────────────────────────────

    _INTENT_HINTS: Dict[str, str] = {
        "hw_cpu":         "User is asking about their CPU - give model, clock speed, cores, and current load/temp.",
        "hw_gpu":         "User is asking about their GPU - give model, VRAM, current load/temp.",
        "hw_ram":         "User is asking about their RAM - give total, used, speed, and slots.",
        "hw_storage":     "User is asking about storage - give drive sizes, used/free, and type (SSD/HDD).",
        "hw_all":         "User wants a full hardware overview - cover CPU, GPU, RAM, storage concisely.",
        "hw_motherboard": "User is asking about their motherboard - give manufacturer, model, chipset, BIOS.",
        "temperature":    "User is asking about system temperatures - be specific: CPU, GPU, and threshold warnings.",
        "throttle_check": "User is asking about CPU/GPU throttling - check current temps and clock speeds.",
        "stats":          "User wants usage statistics - give today's averages and peaks for CPU/RAM.",
        "processes":      "User is asking about running processes - list top consumers by CPU or RAM.",
        "ram_why_high":   "User is asking why RAM usage is high - name the top consumers and explain.",
        "gpu_temp_why":   "User is asking why GPU temperature is high - explain causes (load, cooling, drivers).",
        "why_slow":       "User is asking why the PC is slow - check CPU/RAM/processes and give the real culprit.",
        "turbo_boost":    "User is asking about Intel Turbo Boost or AMD Boost - explain how it works on their CPU.",
        "process_info":   "User is asking about a specific process - explain what it does and if it's safe.",
        "disk_health":    "User is asking about disk health - check usage, S.M.A.R.T. status if available.",
        "performance":    "User is asking about general system performance - give actionable assessment.",
        "optimization":   "User wants optimization advice - give 2-3 specific, actionable tips.",
        "power_plan":     "User is asking about Windows power plan - explain current plan and tradeoffs.",
        "speed_up_pc":    "User wants to speed up their PC - give the most impactful specific actions.",
        "health_check":   "User wants an overall PC health assessment - cover temps, RAM, CPU, disk.",
        "virus_check":    "User is asking about security/malware - check processes for red flags, recommend actions.",
        "unnecessary_programs": "User wants to know what programs can be safely removed or disabled.",
        "about_program":  "User is asking about PC Workman HCK itself - explain what it does.",
        "small_talk":     "User is making casual conversation - be warm and friendly, briefly mention their PC status.",
        # New community intents
        "fan_noise_history":  "User is asking if their fan is louder than usual - compare current CPU/temp load to history, explain causes.",
        "driver_status":      "User wants to know which drivers are installed and when they were updated - list key drivers with age.",
        "gaming_vs_work_time":"User wants a breakdown of time spent gaming vs working - categorize CPU usage by app type.",
        "process_identity":   "User is asking if a specific .exe is a Windows process or suspicious - check library and system path.",
        "stale_apps":         "User wants to find apps they haven't used in a while - list likely unused installed programs.",
        "fps_degradation":    "User says FPS is worse than it used to be - do Time-Travel comparison of GPU/CPU/temp over 30 days.",
        "app_behavior_change":"User says an app started behaving differently - compare current vs 7-day metric trend, suggest causes.",
        "startup_slowdown":   "User asks what slows startup the most - rank startup entries by boot impact, suggest disabling highest ones.",
        "temp_comparison":    "User asks if PC is running hotter than usual - compare current temps to 7-day and 30-day historical averages.",
        "crash_context":      "User asks what was happening before the last freeze - check session events, temps, and RAM pressure.",
        "game_hardware_stress":"User asks which game stresses hardware most - show active game processes, GPU/CPU peak from history.",
        "battery_drain_rate": "User asks how much battery is used during gaming - show current drain rate and estimates by activity type.",
        "power_after_restart":"User asks what used most power since restart - show processes with most cumulative CPU time since boot.",
        # Second wave community intents
        "game_can_run":       "User asks if their PC can run a specific game - check RAM, GPU VRAM, and disk against known game requirements. Be specific: can run / can run on low / cannot run.",
        "gaming_ram_usage":   "User asks how much RAM they use while gaming - compare gaming session RAM peaks from history vs current, give typical range.",
        "daily_ram_usage":    "User asks about typical daily RAM usage - pull 7-day average from metrics_store, show range and peak. Compare to installed RAM.",
        "battery_estimate":   "User asks how long battery will last for an activity - check current battery %, estimate hours based on activity type drain rate.",
        "upgrade_feasibility":"User asks if they can add RAM or storage - check current RAM slots, populated slots, max supported RAM via WMI. Give honest yes/no.",
        "top_resource_hog":   "User asks which process uses the most disk or RAM - show top 5 processes by RSS memory and top 5 by disk I/O bytes. Concrete names and numbers.",
        "browser_cache":      "User asks if their browser is slow because of cache/memory - check all browser processes' RAM usage, give total, name browsers running.",
        "ram_compare":        "User wants to compare RAM usage across sessions or time - show current vs today's peak vs 7-day average. Concrete numbers.",
        "swap_analysis":      "User asks which processes are using swap/pagefile - show current pagefile usage, explain RAM pressure, name top causes.",
        "usb_transfer":       "User connected an external drive and asks about CPU/IO load - show current disk I/O bytes/sec and CPU load, identify the transfer process.",
        "network_usage":      "User asks what is using their network - list processes with active network connections and estimated bandwidth by app.",
        "startup_safety":     "User wants to disable a program from startup (like Discord) - give exact step-by-step guide for Task Manager startup tab, name safe candidates.",
        # Hardware snapshot intents
        "hw_storage":         "User is asking about storage - list all drives (SSD/HDD), capacity, used/free, and health status.",
        "hw_all":             "User wants a full hardware overview - cover CPU model+speed, GPU model+VRAM, RAM total+speed, main storage. Keep it structured.",
        "hw_motherboard":     "User is asking about motherboard - give manufacturer, model, chipset, BIOS version and date.",
        # System state
        "uptime":             "User is asking how long the PC has been running - show current uptime in hours/days, and current CPU+RAM load.",
        "disk_speed":         "User is asking about disk read/write speed - show current I/O bytes/sec and peak, name the process doing most I/O.",
        "disk_health":        "User is asking about disk health - check SMART status if available, show usage %, warn if drive is near capacity or old.",
        "process_info":       "User is asking what a specific process does - name it, explain its function, confirm if it is system/safe/suspicious.",
        "turbo_boost":        "User is asking about CPU turbo/boost - explain current boost state, if it's active, and what CPU temp/load triggers throttle.",
        "voltage_check":      "User is asking about system voltages - show CPU VCore, memory voltage, 12V rail if available via sensors.",
        "fan_speed":          "User is asking about fan RPM - show all fan sensors (CPU fan, case fan), current RPM, and if any fans are stalled.",
        "game_ready":         "User asks if PC is ready for gaming right now - check current temps, RAM free, GPU load. Give go/no-go with reason.",
        "process_kill":       "User wants to stop a process - confirm the process name, warn if it's a system process, suggest safest way to close it.",
        "ram_flush":          "User wants to free up RAM - explain what's safe to close (no system processes), give current top RAM consumers with MB values.",
        "overclock_check":    "User is asking if CPU/GPU is overclocked - check clock speeds vs base specs, report if running above stock.",
        "ai_context":         "User is asking about hck_GPT itself - explain what it can do, what data it uses, and how to ask questions.",
        "startup_check":      "User is asking which programs start with Windows - list startup entries, flag heavy ones, suggest which to disable.",
        # Short session intents
        "disk_usage_why":     "User is asking why disk usage is high - name the top disk-writing processes and current I/O bytes/sec.",
        "optimization":       "User wants optimization advice - give top 3 specific actions based on current bottlenecks (CPU, RAM, disk, startup).",
        "speed_up_pc":        "User wants to speed up their PC - identify the biggest drag (high RAM, startup apps, temps) and give the most impactful fix first.",
        "process_deep_dive":  "User wants details on a specific process - give CPU%, RAM MB, disk I/O, network usage, and whether it's expected behavior.",
        "symptom_noisy":      "User is reporting fan noise - check current fan RPM and CPU/GPU temps, explain what is causing the fans to spin up.",
        "driver_status":      "User wants to know about their drivers - list GPU, audio, network driver versions and last-updated dates.",
        "process_identity":   "User is asking if a .exe is safe or suspicious - check its path (system32 = safe, temp = suspicious), size, and CPU/RAM usage pattern.",
        # Medium history
        "battery_drain":      "User is asking about battery drain - show current battery %, drain rate (W or %/hr), and which processes are biggest power consumers.",
        "battery_drain_rate": "User asks how fast battery drains - give current drain rate, estimated time remaining, and top power-consuming apps.",
        "session_digest":     "User wants a summary of this session - show session duration, CPU/RAM peak, top processes, and any alerts raised.",
        "system_risk":        "User is asking about system risks - check for high temps, low disk space, memory pressure, and suspicious processes. Rate overall risk.",
        "power_after_restart":"User asks what used the most resources since last boot - show top CPU consumers by cumulative time since uptime start.",
        "symptom_freeze":     "User is asking what caused a recent freeze - look at CPU/RAM/temp events from the past 4 hours before the freeze.",
        # Long history trend intents
        "gaming_session":     "User wants gaming session data - show last gaming session duration, average FPS metrics, peak GPU/CPU temps, and RAM peak.",
        "gaming_vs_work_time":"User wants gaming vs work usage breakdown - categorize app usage by type over last 2 days. Give hours and percentage.",
        "stale_apps":         "User wants to find unused apps - list installed programs not seen in process list for over 7 days.",
        "weekly_trends":      "User wants weekly usage trends - show CPU and RAM averages by day for the last 7 days. Highlight the heaviest day.",
        "thermal_prediction": "User wants to know if temps will be a problem - analyze the 7-day temperature trend. Warn if trend is rising.",
        "thermal_history":    "User wants temperature history - show daily CPU/GPU temperature averages for the past 7 days. Flag days above safe threshold.",
        "compare_baseline":   "User wants to know if performance changed - compare current CPU/RAM/temps to the 7-day average as baseline.",
        "morning_brief":      "User wants a morning system brief - show overnight resource usage, last session summary, temps, and if anything needs attention today.",
        # Other
        "fun_roast":          "User wants a humorous roast of their PC specs - be witty and playful, reference real specs (CPU, RAM, GPU). Keep it light.",
        "startup_slowdown":   "User asks what is slowing down boot - list startup programs by estimated boot impact, suggest which to disable.",
        "power_plan":         "User is asking about Windows power plan - show current plan (Balanced/High Performance/Power Saver), explain tradeoffs.",
        "virus_check":        "User is asking about security risks - check if any processes are running from unusual paths, flag high CPU from unknown .exe names.",
        "unnecessary_programs":"User wants to know what programs are unnecessary - list installed apps not used in recent sessions, safe to remove.",
        "about_program":      "User is asking about PC Workman HCK - explain it is a real-time system monitor with AI assistant, mention hck_GPT, key features.",
        "about_author":       "User is asking who made this app - mention HuckleR2003 / the developer, purpose of the project.",
        "help":               "User is asking for help - list what hck_GPT can answer: hardware info, temps, processes, optimization, history, diagnostics.",
        "explain_proactive":  "User is asking about the proactive alert they just received - give full context: what triggered it, current values, and recommended action.",
        "pc_changes":         "User is asking what changed recently on their PC - compare current vs 2-day-old process list and startup entries, flag new additions.",
        "perf_change":        "User is asking if performance changed over time - compare current CPU/RAM averages to the 7-day baseline and flag any degradation trend.",
        "session_compare":    "User wants to compare sessions - show today vs yesterday for CPU avg, RAM peak, and top processes. Highlight differences.",
    }

    def _build_intent_hint(self, result: Any, lang: str) -> str:
        if result is None:
            return ""
        intent    = getattr(result, "intent",   "unknown")
        conf      = getattr(result, "confidence", 0.0)
        entities  = getattr(result, "entities",  {})

        hint = self._INTENT_HINTS.get(intent, "")
        if not hint:
            return ""

        lines = [f"Detected query type: {intent} (confidence {conf:.0%})"]
        lines.append(hint)
        if entities:
            ent_str = ", ".join(f"{k}={v}" for k, v in entities.items())
            lines.append(f"Mentioned components: {ent_str}")
        return "\n".join(lines)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return current engine status (for debug / settings panel)."""
        return {
            "ollama_online":     self.ollama_online,
            "active_model":      self._available_model or self.model,
            "llm_calls":         self.llm_calls,
            "llm_successes":     self.llm_successes,
            "rule_calls":        self.rule_calls,
            "rule_threshold":    RULE_THRESHOLD,
            "ollama_host":       f"{OLLAMA_HOST}:{OLLAMA_PORT}",
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
hybrid_engine = HybridEngine()

# Background availability check on import (non-blocking)
def _bg_check():
    try:
        hybrid_engine._check_available()
    except Exception:
        pass

threading.Thread(target=_bg_check, daemon=True, name="hck_ollama_check").start()
