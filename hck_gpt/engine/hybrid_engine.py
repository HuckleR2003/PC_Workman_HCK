# hck_gpt/engine/hybrid_engine.py
"""
Hybrid Engine — the brain of hck_GPT

Decision flow for every user message:
  1. intent_parser → ParseResult with confidence score
  2. confidence >= RULE_THRESHOLD (0.75)
       → FAST RULE ENGINE (response_builder)   — deterministic, instant
  3. confidence < RULE_THRESHOLD  AND  Ollama available
       → LOCAL LLM (Ollama)  with rich system prompt + full PC context
  4. Ollama unavailable / timeout  AND  confidence >= LOW_THRESHOLD (0.35)
       → RULE ENGINE FALLBACK (best effort)
  5. All else → None (ChatHandler falls through to legacy routes)

Ollama integration:
  - Requires Ollama running locally (http://localhost:11434)
  - Default model: configurable via HybridEngine.model attribute
  - Availability is cached for 5 minutes (no constant polling)
  - Timeout: 10 seconds (graceful fallback on slow response)
  - Streaming disabled — we wait for the complete response

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
RULE_THRESHOLD     = 0.65               # above → rule engine (deterministic); raised from 0.60 so borderline queries get Ollama's natural language
LOW_THRESHOLD      = 0.20               # below → no rule fallback at all
OLLAMA_TIMEOUT     = 10                 # seconds before giving up on Ollama
AVAILABILITY_TTL   = 300               # re-check Ollama availability every 5 min
MAX_TOKENS         = 220               # max LLM output tokens (keep responses short)
TEMPERATURE        = 0.72              # default LLM temperature

# Intent-aware temperature: factual queries need precision, small talk needs warmth
_INTENT_TEMPERATURE: Dict[str, float] = {
    # Factual / diagnostic — deterministic, low creativity
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
    # Performance / optimization — slight creativity OK
    "performance":    0.55,
    "optimization":   0.55,
    "power_plan":     0.50,
    "speed_up_pc":    0.55,
    # Open-ended / conversational — more creative
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
}


# ── Ollama HTTP Client ─────────────────────────────────────────────────────────

class OllamaClient:
    """
    Minimal HTTP client for Ollama local API.
    Uses only stdlib http.client — no requests dependency.
    """

    def is_available(self) -> bool:
        """Ping /api/tags — returns True if Ollama is running."""
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
        POST /api/generate — non-streaming.
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

    # Intents that should always prefer Ollama (conversational / open-ended)
    _OLLAMA_PREFERRED_INTENTS = frozenset({"small_talk", "unknown"})

    # MEGA FEATURE: Context Time-Windowing
    # Maps intent → relevant history window in minutes for the LLM prompt.
    # Intents that ask about NOW get a tight 5-min window (fresh data).
    # Intents doing Time-Travel get a wide window (hours/days worth of context).
    _CONTEXT_WINDOWS: dict[str, int] = {
        # Real-time diagnostics — last 5 min is enough
        "hw_cpu":           5,
        "hw_gpu":           5,
        "hw_ram":           5,
        "temperature":      10,
        "throttle_check":   5,
        "performance":      5,
        "processes":        5,
        # Session-level — last 30 min
        "health_check":     30,
        "ram_why_high":     30,
        "gpu_temp_why":     30,
        "why_slow":         30,
        "stats":            60,
        # Time-Travel queries — need multi-hour / day context
        "temp_comparison":  10080,   # 7 days
        "fps_degradation":  10080,   # 7 days
        "app_behavior_change": 2880, # 2 days
        "crash_context":    240,     # 4 hours
        "fan_noise_history": 1440,   # 24 hours
        "game_hardware_stress": 2880,
        "session_compare":  2880,
        "perf_change":      2880,
        "pc_changes":       2880,
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

        # ── OPEN-ENDED INTENTS → always try Ollama first ──────────────────────
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

        # ── HIGH CONFIDENCE → rule engine (instant, deterministic) ────────────
        if confidence >= RULE_THRESHOLD:
            resp = response_builder.build(result, lang)
            if resp:
                self.rule_calls += 1
                return resp

        # ── MEDIUM CONFIDENCE → try Ollama, then rule fallback ────────────────
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
        # Temporarily unavailable (e.g. after timeout) — don't retry yet
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
            # On exception, cool down for 60s (not 5min) — could be transient
            self._temp_unavail_until = time.time() + 60
            return None

        if not raw:
            # Empty response — may be model loading; short cool-down
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
                 .replace("\n- ", "\n• ")    # markdown dash-bullet → unicode bullet
                 .replace("\n* ", "\n• ")    # markdown star-bullet → unicode bullet
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
          [Identity]     — who hck_GPT is
          [Intent]       — detected query intent (helps LLM focus)
          [Rules]        — how to respond
          [PC Context]   — live snapshot + hardware + history
          [Language]     — which language to use
        """
        # Gather context — MEGA FEATURE: Context Time-Windowing
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
            "You are hck_GPT, an AI assistant deeply embedded in PC Workman HCK — "
            "a professional Windows PC monitoring and optimization application. "
            "You have direct access to the user's real-time system data: "
            "CPU and RAM usage, temperatures, running processes, hardware specs, "
            "today's usage averages, and past system alerts. "
            "You are not a generic assistant — you are a specialized PC expert "
            "who knows this specific computer intimately."
        )

        # Intent hint — guides the LLM on what kind of answer is expected
        intent_block = self._build_intent_hint(result, lang)

        # Hard rules
        rules = (
            "RULES — follow these strictly:\n"
            "1. Responses must be SHORT — 1 to 5 lines maximum. No walls of text.\n"
            "2. Never use markdown headers (no # or ##), no bullet point lists with dashes.\n"
            "3. Never make up hardware data — only use what is provided in [PC Context].\n"
            "4. Start your reply with the most relevant fact, not with 'As an AI...' or similar.\n"
            "5. If the user asks something outside PC topics (weather, recipes, etc.) — "
            "politely redirect: 'I specialize in PC diagnostics — ask me about your hardware or system.'\n"
            "6. Numbers always matter — include them (%, MHz, GB) when available.\n"
            "7. Be direct, warm, and practical — like a knowledgeable friend who knows this PC.\n"
            "8. If something is concerning (high CPU, throttling, low RAM), say so clearly.\n"
            "9. Never start a line with 'hck_GPT:' — that prefix is added automatically."
        )

        # Language instruction
        if lang == "en":
            lang_rule = "LANGUAGE: Respond in ENGLISH. The user is writing in English."
        else:
            lang_rule = (
                "JĘZYK: Odpowiadaj PO POLSKU. Użytkownik pisze po polsku. "
                "Używaj naturalnego, potocznego języka — nie formalnego."
            )

        # Combine — include intent block only when non-empty
        sections = [
            f"[Identity]\n{identity}",
            f"[Rules]\n{rules}",
        ]
        if intent_block:
            sections.append(f"[Intent]\n{intent_block}")
        sections.append(f"[PC Context]\n{pc_ctx}")
        sections.append(f"[Language]\n{lang_rule}")

        return "\n\n".join(sections)

    # ── Intent hint builder ───────────────────────────────────────────────────

    _INTENT_HINTS: Dict[str, str] = {
        "hw_cpu":         "User is asking about their CPU — give model, clock speed, cores, and current load/temp.",
        "hw_gpu":         "User is asking about their GPU — give model, VRAM, current load/temp.",
        "hw_ram":         "User is asking about their RAM — give total, used, speed, and slots.",
        "hw_storage":     "User is asking about storage — give drive sizes, used/free, and type (SSD/HDD).",
        "hw_all":         "User wants a full hardware overview — cover CPU, GPU, RAM, storage concisely.",
        "hw_motherboard": "User is asking about their motherboard — give manufacturer, model, chipset, BIOS.",
        "temperature":    "User is asking about system temperatures — be specific: CPU, GPU, and threshold warnings.",
        "throttle_check": "User is asking about CPU/GPU throttling — check current temps and clock speeds.",
        "stats":          "User wants usage statistics — give today's averages and peaks for CPU/RAM.",
        "processes":      "User is asking about running processes — list top consumers by CPU or RAM.",
        "ram_why_high":   "User is asking why RAM usage is high — name the top consumers and explain.",
        "gpu_temp_why":   "User is asking why GPU temperature is high — explain causes (load, cooling, drivers).",
        "why_slow":       "User is asking why the PC is slow — check CPU/RAM/processes and give the real culprit.",
        "turbo_boost":    "User is asking about Intel Turbo Boost or AMD Boost — explain how it works on their CPU.",
        "process_info":   "User is asking about a specific process — explain what it does and if it's safe.",
        "disk_health":    "User is asking about disk health — check usage, S.M.A.R.T. status if available.",
        "session_compare":"User wants to compare today's metrics with yesterday's session.",
        "performance":    "User is asking about general system performance — give actionable assessment.",
        "optimization":   "User wants optimization advice — give 2-3 specific, actionable tips.",
        "power_plan":     "User is asking about Windows power plan — explain current plan and tradeoffs.",
        "speed_up_pc":    "User wants to speed up their PC — give the most impactful specific actions.",
        "health_check":   "User wants an overall PC health assessment — cover temps, RAM, CPU, disk.",
        "virus_check":    "User is asking about security/malware — check processes for red flags, recommend actions.",
        "unnecessary_programs": "User wants to know what programs can be safely removed or disabled.",
        "about_program":  "User is asking about PC Workman HCK itself — explain what it does.",
        "small_talk":     "User is making casual conversation — be warm and friendly, briefly mention their PC status.",
        # New community intents
        "fan_noise_history":  "User is asking if their fan is louder than usual — compare current CPU/temp load to history, explain causes.",
        "driver_status":      "User wants to know which drivers are installed and when they were updated — list key drivers with age.",
        "gaming_vs_work_time":"User wants a breakdown of time spent gaming vs working — categorize CPU usage by app type.",
        "process_identity":   "User is asking if a specific .exe is a Windows process or suspicious — check library and system path.",
        "stale_apps":         "User wants to find apps they haven't used in a while — list likely unused installed programs.",
        "fps_degradation":    "User says FPS is worse than it used to be — do Time-Travel comparison of GPU/CPU/temp over 30 days.",
        "app_behavior_change":"User says an app started behaving differently — compare current vs 7-day metric trend, suggest causes.",
        "startup_slowdown":   "User asks what slows startup the most — rank startup entries by boot impact, suggest disabling highest ones.",
        "temp_comparison":    "User asks if PC is running hotter than usual — compare current temps to 7-day and 30-day historical averages.",
        "crash_context":      "User asks what was happening before the last freeze — check session events, temps, and RAM pressure.",
        "game_hardware_stress":"User asks which game stresses hardware most — show active game processes, GPU/CPU peak from history.",
        "battery_drain_rate": "User asks how much battery is used during gaming — show current drain rate and estimates by activity type.",
        "power_after_restart":"User asks what used most power since restart — show processes with most cumulative CPU time since boot.",
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
