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

# ── Constants ──────────────────────────────────────────────────────────────────
OLLAMA_HOST        = "localhost"
OLLAMA_PORT        = 11434
DEFAULT_MODEL      = "llama3.2"          # override: hybrid_engine.model = "mistral"
RULE_THRESHOLD     = 0.60               # above → rule engine (deterministic)
LOW_THRESHOLD      = 0.20               # below → no rule fallback at all
OLLAMA_TIMEOUT     = 10                 # seconds before giving up on Ollama
AVAILABILITY_TTL   = 300               # re-check Ollama availability every 5 min
MAX_TOKENS         = 220               # max LLM output tokens (keep responses short)
TEMPERATURE        = 0.72              # LLM temperature (slight creativity)


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
                "temperature":  TEMPERATURE,
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
                llm_resp = self._query_llm(msg, lang)
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
            llm_resp = self._query_llm(msg, lang)
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

    def _query_llm(self, msg: str, lang: str) -> Optional[List[str]]:
        """Build full prompt + call Ollama, return formatted response lines."""
        self.llm_calls += 1
        try:
            system_prompt = self._build_system_prompt(lang)
            raw = self._ollama.generate(
                model=self.model,
                prompt=msg,
                system=system_prompt,
                timeout=OLLAMA_TIMEOUT,
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
        # Remove markdown artifacts
        clean = (raw
                 .replace("**", "")
                 .replace("##", "")
                 .replace("# ", "")
                 .replace("---", "")
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

    def _build_system_prompt(self, lang: str) -> str:
        """
        Constructs a comprehensive system prompt for Ollama.
        Sections:
          [Identity]     — who hck_GPT is
          [Rules]        — how to respond
          [PC Context]   — live snapshot + hardware + history
          [Language]     — which language to use
        """
        # Gather context
        try:
            from hck_gpt.context.system_context import system_context
            pc_ctx = system_context.build_llm_context(lang)
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

        # Combine
        prompt = "\n\n".join([
            f"[Identity]\n{identity}",
            f"[Rules]\n{rules}",
            f"[PC Context]\n{pc_ctx}",
            f"[Language]\n{lang_rule}",
        ])

        return prompt

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
