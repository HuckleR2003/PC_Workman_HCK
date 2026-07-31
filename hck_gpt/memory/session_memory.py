# hck_gpt/memory/session_memory.py
"""
Session Memory - in-RAM state for the current app session.

Tracks:
  - Message history (last 50 exchanges)
  - Observed system events this session (spikes, throttles, etc.)
  - Last known live PC snapshot
  - Conversation topic stack (for contextual follow-up)
  - CPU/RAM trend buffer (rising / stable / falling)
  - Auto conversation summary (every 6 messages - used by Hybrid Engine)

Not persisted to disk - cleared on every app restart.
For persistent knowledge see user_knowledge.py
"""
from __future__ import annotations

import time
import re
import threading
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Any


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Message:
    role: str          # "user" | "assistant"
    text: str
    timestamp: float = field(default_factory=time.time)

    def age_seconds(self) -> float:
        return time.time() - self.timestamp


@dataclass
class ObservedEvent:
    event_type: str    # "cpu_spike" | "throttle" | "high_ram" | "high_temp" | ...
    detail: str = ""
    timestamp: float = field(default_factory=time.time)

    def age_minutes(self) -> float:
        return (time.time() - self.timestamp) / 60


@dataclass
class ConversationFrame:
    """One bounded diagnostic thread inside the current app session.

    This is deliberately not a second memory system. It is the structured
    part of :class:`SessionMemory`: what the user is trying to do, which real
    subject is involved, what evidence exists, and whether earlier advice was
    tried and checked. Frames are never persisted and expire after inactivity.
    """

    frame_id: str
    subject_kind: str = ""
    subject_value: str = ""
    goal: str = ""
    symptom: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    missing_evidence: List[str] = field(default_factory=list)
    advice: str = ""
    advice_intent: str = ""
    advice_state: str = "none"       # none | offered | accepted | declined
    verification_state: str = "none" # none | waiting | better | same | worse | measured
    confidence: float = 0.0
    source_intent: str = ""
    last_intent: str = ""
    baseline: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    question_attempts: Dict[str, int] = field(default_factory=dict)
    last_question_key: str = ""
    revisions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def touch(self, ttl_seconds: float) -> None:
        self.updated_at = time.time()
        self.expires_at = self.updated_at + ttl_seconds

    def is_expired(self, now: Optional[float] = None) -> bool:
        return bool(self.expires_at and (now or time.time()) >= self.expires_at)


# ── Main class ────────────────────────────────────────────────────────────────

class SessionMemory:
    """
    Lightweight in-RAM store for everything that happened this session.
    Instantiated once at import time (singleton pattern via module-level variable).
    """

    MAX_MESSAGES   = 50
    MAX_EVENTS     = 100
    TREND_WINDOW   = 8     # number of readings for trend analysis
    SUMMARY_EVERY  = 6     # auto-summarize every N messages
    FRAME_TTL_S    = 1200  # 20 min without a related turn = fresh diagnosis

    _CONTROL_INTENTS = frozenset({
        "correct_subject", "explain_previous_advice", "verify_after_action",
        "compare_after_change", "continue_diagnosis", "decline_advice",
        "explain_confidence", "compat_missing_details", "upgrade_budget",
        "upgrade_workload", "desktop_recurrence",
    })
    _GOAL_CONTROL_INTENTS = frozenset({
        "compat_missing_details", "upgrade_budget", "upgrade_workload",
        "desktop_recurrence",
    })
    _GOAL_BY_INTENT = {
        "why_slow": "diagnose", "health_check": "diagnose",
        "performance": "diagnose", "symptom_freeze": "diagnose",
        "crash_context": "diagnose", "app_behavior_change": "diagnose",
        "process_deep_dive": "diagnose", "process_kill": "diagnose",
        "ram_why_high": "diagnose", "disk_usage_why": "diagnose",
        "gpu_temp_why": "cool", "temperature": "inspect",
        "cooling_advice": "cool", "fan_noise_history": "cool",
        "symptom_noisy": "cool", "throttle_check": "diagnose",
        "optimization": "optimize", "speed_up_pc": "optimize",
        "optimize_guide": "optimize", "tuneup_guide": "optimize",
        "ram_flush": "optimize", "startup_slowdown": "optimize",
        "desktop_problem": "repair_desktop",
        "desktop_recurrence": "repair_desktop",
        "upgrade_advice": "upgrade", "upgrade_feasibility": "upgrade",
        "upgrade_compat": "upgrade", "ram_compat": "upgrade",
        "upgrade_plan": "upgrade", "upgrade_budget": "upgrade",
        "upgrade_workload": "upgrade", "compat_missing_details": "upgrade",
        "game_ready": "game", "gaming_session": "game",
        "fps_degradation": "game", "game_hardware_stress": "game",
        "game_can_run": "game",
    }
    _SYMPTOM_BY_INTENT = {
        "why_slow": "slow", "symptom_freeze": "freeze",
        "crash_context": "crash", "ram_why_high": "high_ram",
        "disk_usage_why": "busy_disk", "gpu_temp_why": "hot_gpu",
        "symptom_noisy": "noise", "fan_noise_history": "noise",
        "desktop_problem": "desktop", "desktop_recurrence": "desktop_recurrent",
        "fps_degradation": "fps_drop", "startup_slowdown": "slow_startup",
    }
    _ADVICE_INTENTS = frozenset({
        "why_slow", "health_check", "symptom_freeze", "process_kill",
        "ram_why_high", "disk_usage_why", "gpu_temp_why", "cooling_advice",
        "symptom_noisy", "optimization", "speed_up_pc", "optimize_guide",
        "tuneup_guide", "ram_flush", "desktop_problem", "upgrade_advice",
        "upgrade_feasibility", "upgrade_compat", "ram_compat", "upgrade_plan",
        "game_ready", "fps_degradation", "startup_slowdown",
    })

    def __init__(self) -> None:
        self.session_id: str   = f"s_{int(time.time())}"
        self.started_at: float = time.time()

        self._messages: Deque[Message]       = deque(maxlen=self.MAX_MESSAGES)
        self._events:   Deque[ObservedEvent] = deque(maxlen=self.MAX_EVENTS)

        # Last snapshot from SystemContext.snapshot()
        self.live_snapshot: Dict[str, Any] = {}

        # Conversation topic stack - top = current subject
        self._topic_stack: List[str] = []

        # Flags / counters used by the response builder
        self.greeted_this_session: bool = False
        self.hardware_scanned:     bool = False

        # ── Trend tracking ────────────────────────────────────────────────────
        # Circular buffers of recent metric readings
        self._cpu_trend: Deque[float] = deque(maxlen=self.TREND_WINDOW)
        self._ram_trend: Deque[float] = deque(maxlen=self.TREND_WINDOW)
        self._trend_last_at: float    = 0.0

        # ── Session data store ────────────────────────────────────────────────
        # Stores key values actually reported in responses this session.
        # Allows later responses to reference what was shown earlier.
        # Structure:  intent_name -> {recorded_at: float, key: value, ...}
        self._session_data: Dict[str, Any] = {}

        # Short-lived conversational references. This is the difference between
        # remembering a topic name and understanding "it", "that process" or
        # "will it fit?" in the next turn. Nothing here is persisted.
        self._turn_context: Deque[Dict[str, Any]] = deque(maxlen=12)
        self._last_references: Dict[str, Dict[str, Any]] = {}

        # Structured continuation of the current diagnostic conversation.
        # It lives here, beside the existing references and response ledger,
        # so there is still one source of truth for session context.
        self._conversation_frame: Optional[ConversationFrame] = None
        self._frame_seq: int = 0
        self._frame_lock = threading.RLock()

        # ── Last proactive message store ──────────────────────────────────────
        # Tracks the most recent autonomously pushed message so users can
        # ask "what does that mean?" / "co to znaczy?" and get an explanation.
        # Structure: {"text": str, "context": dict, "ts": float}
        self._last_proactive: Dict[str, Any] = {}

        # ── Conversation summary ──────────────────────────────────────────────
        self.conversation_summary: str = ""
        self._summary_at_count: int    = 0   # message count when last summarized

    # ── Messages ──────────────────────────────────────────────────────────────

    def add_message(self, role: str, text: str) -> None:
        # Sanitize text - strip null bytes that could cause downstream issues
        safe_text = (text or "").replace("\x00", "").strip()
        self._messages.append(Message(role=role, text=safe_text))
        # Auto-summarize every SUMMARY_EVERY user messages
        try:
            user_count = sum(1 for m in self._messages if m.role == "user")
            if user_count > 0 and user_count % self.SUMMARY_EVERY == 0:
                if user_count != self._summary_at_count:
                    self._summary_at_count = user_count
                    self._auto_summarize()
        except Exception:
            pass

    def recent_messages(self, n: int = 10) -> List[Message]:
        return list(self._messages)[-n:]

    def last_user_message(self) -> Optional[str]:
        for m in reversed(self._messages):
            if m.role == "user":
                return m.text
        return None

    def recent_exchange_text(self, n_pairs: int = 4) -> str:
        """Return last N exchanges as a compact text block for LLM context."""
        msgs = list(self._messages)
        if not msgs:
            return ""
        recent = msgs[-(n_pairs * 2):]
        lines = []
        for m in recent:
            prefix = "User" if m.role == "user" else "hck_GPT"
            # Strip 'hck_GPT:' prefix from stored assistant messages
            text = m.text.strip()
            if text.startswith("hck_GPT:"):
                text = text[8:].strip()
            if text:
                lines.append(f"{prefix}: {text}")
        return "\n".join(lines)

    # ── Events ────────────────────────────────────────────────────────────────

    def record_event(self, event_type: str, detail: str = "") -> None:
        self._events.append(ObservedEvent(event_type=event_type, detail=detail))

    def recent_events(self, n: int = 10) -> List[ObservedEvent]:
        return list(self._events)[-n:]

    def has_recent_event(self, event_type: str, within_minutes: float = 10) -> bool:
        return any(
            e.event_type == event_type and e.age_minutes() <= within_minutes
            for e in self._events
        )

    def recent_events_summary(self, within_minutes: float = 30) -> str:
        """One-line summary of events from last N minutes."""
        events = [
            e for e in self._events
            if e.age_minutes() <= within_minutes
        ]
        if not events:
            return ""
        counts: Dict[str, int] = {}
        for e in events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return ", ".join(f"{k}×{v}" for k, v in counts.items())

    # ── Last proactive message ────────────────────────────────────────────────

    def set_last_proactive(self, text: str,
                           context: Optional[Dict[str, Any]] = None) -> None:
        """Store the most recent autonomously pushed message with its context.
        Call this every time proactive_monitor or insights pushes a message so
        the user can later ask 'what does that mean?' and get an explanation.
        """
        self._last_proactive = {
            "text":    text,
            "context": context or {},
            "ts":      time.time(),
        }

    def get_last_proactive(self) -> Dict[str, Any]:
        """Return the last stored proactive message (empty dict if none)."""
        return dict(self._last_proactive)

    # ── Conversational references ─────────────────────────────────────────────

    _PROCESS_RE = re.compile(r"(?<![\w.-])([\w.-]+\.exe)(?![\w.-])", re.I)
    _PART_RE = re.compile(
        r"\b(i[3579][ -]?\d{4,5}[a-z]{0,2}|"
        r"ryzen\s*[3579]\s*\d{4}[a-z0-9]{0,3}|"
        r"ultra\s*[579]\s*\d{3}[a-z]{0,2}(?:\s*plus)?|"
        r"rtx\s*\d{4}(?:\s*ti\s*super|\s*ti|\s*super)?|"
        r"gtx\s*\d{3,4}(?:\s*ti|\s*super)?|"
        r"rx\s*\d{3,4}(?:\s*xtx|\s*xt|\s*gre)?|"
        r"ddr[2345](?:\s*\d{3,5})?)\b", re.I)
    _KNOWN_GAMES = (
        "cyberpunk 2077", "cyberpunk", "counter-strike 2", "cs2",
        "fortnite", "minecraft", "valorant", "elden ring", "witcher 3",
        "wiedźmin 3", "gta v", "gta 5", "apex legends", "warzone",
        "overwatch 2", "hogwarts legacy",
    )
    _INTENT_COMPONENT = {
        "hw_cpu": "cpu", "hw_gpu": "gpu", "hw_ram": "ram",
        "hw_storage": "storage", "hw_motherboard": "motherboard",
        "gpu_temp_why": "gpu", "temperature": "temperature",
        "ram_why_high": "ram", "ram_compare": "ram",
        "disk_health": "storage", "disk_speed": "storage",
        "disk_usage_why": "storage",
    }

    @staticmethod
    def _fold_text(text: str) -> str:
        stripped = "".join(
            c for c in unicodedata.normalize("NFD", (text or "").lower())
            if unicodedata.category(c) != "Mn"
        )
        folded = stripped.translate(str.maketrans({
            "ł": "l", "ø": "o", "đ": "d",
        }))
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s.\-']", " ", folded)).strip()

    def _new_frame(self, goal: str = "", intent: str = "") -> ConversationFrame:
        self._frame_seq += 1
        frame = ConversationFrame(
            frame_id=f"{self.session_id}_f{self._frame_seq}",
            goal=goal,
            source_intent=intent,
            last_intent=intent,
        )
        frame.touch(self.FRAME_TTL_S)
        self._conversation_frame = frame
        return frame

    def active_frame(self, now: Optional[float] = None) -> Optional[ConversationFrame]:
        """Return the live diagnostic frame, expiring stale context silently."""
        with self._frame_lock:
            frame = self._conversation_frame
            if frame is not None and frame.is_expired(now):
                self._conversation_frame = None
                return None
            return frame

    def clear_conversation_frame(self) -> None:
        with self._frame_lock:
            self._conversation_frame = None

    def ensure_frame(self, goal: str = "", intent: str = "") -> ConversationFrame:
        with self._frame_lock:
            frame = self.active_frame()
            if frame is None:
                frame = self._new_frame(goal, intent)
            elif (goal and frame.goal and goal != frame.goal
                  and intent in self._GOAL_CONTROL_INTENTS):
                frame = self._new_frame(goal, intent)
            elif goal and not frame.goal:
                frame.goal = goal
            if intent:
                frame.last_intent = intent
                frame.source_intent = frame.source_intent or intent
            frame.touch(self.FRAME_TTL_S)
            return frame

    @staticmethod
    def _subject_from_refs(refs: Dict[str, str]) -> tuple[str, str]:
        for kind in ("process", "part", "game", "component"):
            value = refs.get(kind, "")
            if value:
                return kind, value
        return "", ""

    def _detail_evidence(self, raw: str) -> Dict[str, Any]:
        """Extract details that are usually supplied as short follow-ups."""
        folded = self._fold_text(raw)
        out: Dict[str, Any] = {}

        # In corrections such as "not in game, only on desktop", inspect the
        # asserted clause instead of accidentally storing the negated one.
        asserted = folded
        contrast = re.search(
            r"\b(?:tylko|ale|but|instead(?:\s+of)?|rather(?:\s+than)?|only)\b",
            folded,
        )
        if contrast and contrast.end() < len(folded):
            asserted = folded[contrast.end():].strip()

        context_groups = (
            ("gaming", (
                "w grze", "podczas gry", "kiedy gram", "przy graniu",
                "w czasie gry", "w trakcie gry", "w trakcie meczu",
                "podczas meczu", "jak gram", "gdy gram", "kiedy odpalam gre",
                "jak odpalam gre", "przy odpalonej grze", "na grach",
                "in game", "while gaming", "when i play", "during games",
                "while playing", "during a match", "in a match",
                "once i launch a game", "when the game is running",
            )),
            ("browser", (
                "w przegladarce", "podczas przegladania", "przy przegladaniu",
                "na chromie", "w chrome", "w firefox", "w edge",
                "na youtube", "podczas ogladania filmu", "przy filmach",
                "in browser", "while browsing", "in chrome", "in firefox",
                "on youtube", "while watching video",
            )),
            ("startup", (
                "przy starcie", "podczas startu", "po uruchomieniu windows",
                "po wlaczeniu komputera", "zaraz po wlaczeniu", "po zalogowaniu",
                "przy logowaniu", "przy ladowaniu systemu", "during startup",
                "after boot", "at startup", "right after login", "on login",
                "while windows starts", "when windows loads",
            )),
            ("desktop", (
                "na pulpicie", "sam pulpit", "w spoczynku", "nic nie robie",
                "bez uruchomionych programow", "nawet gdy nic nie robie",
                "bez obciazenia", "on desktop", "at idle", "doing nothing",
                "with nothing open", "even when idle", "no apps open",
            )),
            ("system_wide", (
                "w calym systemie", "na calym komputerze", "wszędzie",
                "wszedzie", "niezaleznie co robie", "system wide",
                "across the whole pc", "whatever i do",
            )),
        )
        for context, cues in context_groups:
            if any(cue in asserted for cue in cues):
                out["context"] = context
                break

        timing = re.search(
            r"\b(?:po|after)\s+(\d{1,3})\s*(sekund\w*|sec(?:onds?)?\b|"
            r"minut\w*|min\b|minutes?\b|godzin\w*|hours?\b)",
            folded,
        )
        if timing:
            out["timing"] = f"{timing.group(1)} {timing.group(2)}"
        elif any(x in folded for x in (
                "od razu", "natychmiast", "od startu", "od pierwszej minuty",
                "zaraz po odpaleniu", "right away", "immediately",
                "from the start", "from the first minute")):
            out["timing"] = "immediately"
        elif any(x in folded for x in (
                "po chwili", "z czasem", "po paru minutach", "po paru min",
                "po kilku minutach", "po kilku min", "po kilkunastu minutach",
                "dopiero jak sie rozgrzeje", "po rozgrzaniu", "after a while",
                "over time", "after a few minutes", "once it warms up")):
            out["timing"] = "after_a_while"
        elif any(x in folded for x in (
                "w polowie meczu", "w srodku meczu", "mid match",
                "halfway through the match")):
            out["timing"] = "mid_session"
        elif any(x in folded for x in (
                "pod koniec meczu", "pod koniec gry", "po jednej rundzie",
                "near the end of the match", "after one round")):
            out["timing"] = "late_session"

        network = any(x in asserted for x in (
            "ping", "internet", "rubberband", "teleportuje", "teleport",
            "latency", "network lag", "cofa mnie", "gubi pakiety",
            "packet loss", "connection delay", "postać przeskakuje",
            "postac przeskakuje",
        ))
        fps = any(x in asserted for x in (
            "fps", "klatk", "spadki klatek", "frame drop", "frames drop",
            "malo klatek", "klatki leca w dol", "pokaz slajdow",
        ))
        stutter = any(x in asserted for x in (
            "scina", "przycina", "stutter", "mikroprzyc", "freeze",
            "zamarza", "klatkuje", "rwie obraz", "szarpie obraz",
            "chrupie", "przywiesza", "hitching",
        ))
        input_lag = any(x in asserted for x in (
            "input lag", "mysz reaguje po czasie", "myszka reaguje po czasie",
            "klawiatura ma opoznienie", "sterowanie ma opoznienie",
            "delayed mouse", "delayed keyboard", "controls respond late",
        ))
        kinds = [name for name, present in (
            ("network", network), ("fps", fps), ("stutter", stutter),
            ("input", input_lag),
        ) if present]
        uncertain = any(x in folded for x in (
            "nie wiem czy", "trudno powiedziec", "chyba", "not sure whether",
            "hard to tell", "maybe",
        ))
        if len(kinds) > 1:
            out["lag_kind"] = "unclear" if uncertain else "mixed"
        elif kinds:
            out["lag_kind"] = kinds[0]

        if any(x in folded for x in (
                "znow", "znowu", "wraca", "powtarza", "co jakis czas",
                "again", "keeps coming back", "recurring", "every time")):
            out["recurrence"] = "recurring"
        elif any(x in folded for x in (
                "pierwszy raz", "nigdy wczesniej", "first time",
                "never happened before")):
            out["recurrence"] = "first_time"

        if any(x in folded for x in (
                "czasami", "czasem", "losowo", "raz na jakis czas",
                "nie w kazdym meczu", "sometimes", "randomly", "occasionally",
                "not every match")):
            out["frequency"] = "intermittent"
        elif any(x in folded for x in (
                "za kazdym razem", "w kazdym meczu", "ciagle", "caly czas",
                "every time", "every match", "constantly", "all the time")):
            out["frequency"] = "consistent"

        if any(x in folded for x in (
                "tylko w tej grze", "tylko jedna gra", "w jednej grze",
                "only this game", "only one game")):
            out["scope"] = "one_game"
        elif any(x in folded for x in (
                "we wszystkich grach", "w kazdej grze", "kazda gra",
                "all games", "every game")):
            out["scope"] = "all_games"
        elif any(x in folded for x in (
                "caly komputer", "caly system", "wszystko wtedy laguje",
                "whole pc", "whole system", "everything lags")):
            out["scope"] = "system_wide"

        trigger_groups = (
            ("driver_update", ("po aktualizacji sterownika", "po update sterownika",
                               "after a driver update", "after updating drivers")),
            ("windows_update", ("po aktualizacji windows", "po windows update",
                                "after a windows update", "since windows updated")),
            ("game_update", ("po aktualizacji gry", "po patchu gry",
                             "after the game update", "after a game patch")),
            ("new_install", ("po instalacji programu", "odkad zainstalowalem",
                             "after installing an app", "since i installed")),
            ("settings_change", ("po zmianie ustawien", "po zmianie grafiki",
                                 "after changing settings", "after changing graphics")),
            ("alt_tab", ("po alt tab", "po alt-tab", "after alt tab",
                         "after alt-tabbing")),
        )
        for trigger, cues in trigger_groups:
            if any(cue in folded for cue in cues):
                out["trigger"] = trigger
                break

        for game in self._KNOWN_GAMES:
            if self._fold_text(game) in folded:
                out["game"] = game
                out.setdefault("context", "gaming")
                break

        if not out.get("game"):
            generic_game = re.search(
                r"\b(?:gram w|w grze|podczas gry w|playing|the game is)\s+"
                r"([\w][\w .:'-]{1,38})",
                folded,
            )
            if generic_game:
                candidate = re.split(
                    r"\b(?:po|after|kiedy|when|gdy|because|bo|i wtedy|and then)\b",
                    generic_game.group(1), maxsplit=1,
                )[0].strip(" .:-")
                blocked = {
                    "grze", "gre", "meczu", "przegladarce", "tle", "ogole",
                    "game", "games", "browser", "background", "general",
                }
                if candidate and candidate not in blocked:
                    out["game"] = candidate
                    out.setdefault("context", "gaming")

        budget = re.search(
            r"\b(\d{2,6})\s*(zl|pln|eur|euro|usd|dolar\w*)\b", folded)
        if budget:
            out["budget"] = f"{budget.group(1)} {budget.group(2)}"

        workload_map = {
            "gaming": ("gry", "grania", "gaming", "game", "fps"),
            "office": ("biuro", "office", "word", "excel"),
            "creation": ("montaz", "render", "premiere", "blender", "video"),
            "development": ("programow", "coding", "compile", "virtual machine"),
        }
        for label, cues in workload_map.items():
            if any(cue in folded for cue in cues):
                out["workload"] = label
                break
        return out

    @staticmethod
    def _missing_for(goal: str, symptom: str,
                     evidence: Dict[str, Any], refs: Dict[str, str]) -> List[str]:
        missing: List[str] = []
        if goal == "diagnose" and symptom in ("slow", "freeze", ""):
            if not evidence.get("context"):
                missing.append("where_it_happens")
            elif evidence.get("context") == "gaming":
                if not evidence.get("timing"):
                    missing.append("when_during_game")
                if evidence.get("lag_kind") in (None, "", "unclear"):
                    missing.append("lag_type")
        elif goal == "upgrade":
            if not refs.get("part") and not evidence.get("target_part"):
                missing.append("target_part")
            if not evidence.get("workload"):
                missing.append("workload")
            if not evidence.get("budget"):
                missing.append("budget")
        elif goal == "repair_desktop" and not evidence.get("recurrence"):
            missing.append("recurrence")
        return missing

    @staticmethod
    def _advice_excerpt(response: List[str]) -> str:
        useful = []
        for line in response:
            clean = str(line or "").replace("hck_GPT:", "", 1).strip()
            if not clean or clean.startswith("💬"):
                continue
            useful.append(clean)
            if len(useful) >= 4:
                break
        return " | ".join(useful)[:560]

    @staticmethod
    def collect_live_evidence() -> Dict[str, Any]:
        """Small honest snapshot used for before/after reasoning."""
        try:
            from hck_gpt.context.system_context import system_context
            snap = system_context.snapshot()
        except Exception:
            return {}
        out: Dict[str, Any] = {}
        for source, target in (
            ("cpu_pct", "cpu_pct"), ("ram_pct", "ram_pct"),
            ("gpu_load", "gpu_pct"), ("gpu_temp", "gpu_temp"),
        ):
            value = snap.get(source)
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if value >= 0:
                out[target] = round(value, 1)
        cpu_temp = snap.get("cpu_temp")
        if snap.get("cpu_temp_src") == "sensor":
            try:
                if float(cpu_temp) > 0:
                    out["cpu_temp"] = round(float(cpu_temp), 1)
                    out["cpu_temp_source"] = "sensor"
            except (TypeError, ValueError):
                pass
        out["captured_at"] = time.time()
        return out

    def frame_snapshot(self) -> Dict[str, Any]:
        frame = self.active_frame()
        if frame is None:
            return {}
        with self._frame_lock:
            return {
                "frame_id": frame.frame_id,
                "subject_kind": frame.subject_kind,
                "subject_value": frame.subject_value,
                "goal": frame.goal,
                "symptom": frame.symptom,
                "evidence": dict(frame.evidence),
                "missing_evidence": list(frame.missing_evidence),
                "advice": frame.advice,
                "advice_intent": frame.advice_intent,
                "advice_state": frame.advice_state,
                "verification_state": frame.verification_state,
                "confidence": frame.confidence,
                "source_intent": frame.source_intent,
                "last_intent": frame.last_intent,
                "baseline": dict(frame.baseline),
                "verification": dict(frame.verification),
                "question_attempts": dict(frame.question_attempts),
                "last_question_key": frame.last_question_key,
                "revisions": [dict(item) for item in frame.revisions],
                "expires_at": frame.expires_at,
            }

    def record_frame_evidence(self, values: Dict[str, Any], goal: str = "",
                              intent: str = "") -> ConversationFrame:
        with self._frame_lock:
            frame = self.ensure_frame(goal, intent)
            for key, value in values.items():
                if value in (None, ""):
                    continue
                previous = frame.evidence.get(key)
                if previous not in (None, "") and previous != value:
                    frame.revisions.append({
                        "key": key,
                        "from": previous,
                        "to": value,
                        "recorded_at": time.time(),
                    })
                    frame.revisions = frame.revisions[-8:]
                frame.evidence[key] = value
            refs = ({frame.subject_kind: frame.subject_value}
                    if frame.subject_kind and frame.subject_value else {})
            frame.missing_evidence = self._missing_for(
                frame.goal, frame.symptom, frame.evidence, refs,
            )
            frame.touch(self.FRAME_TTL_S)
            return frame

    def next_frame_question(self, mark_asked: bool = True) -> tuple[str, int]:
        """Return the least-repeated missing slot for the active diagnosis.

        A user can answer questions out of order. Choosing by the number of
        earlier attempts prevents hck_GPT from repeating one broad question
        while another useful detail is still missing. The count also lets the
        response layer use a tighter rephrasing on a second attempt.
        """
        with self._frame_lock:
            frame = self.active_frame()
            if frame is None or not frame.missing_evidence:
                return "", 0
            key = min(
                frame.missing_evidence,
                key=lambda item: (
                    frame.question_attempts.get(item, 0),
                    frame.missing_evidence.index(item),
                ),
            )
            if mark_asked:
                frame.question_attempts[key] = (
                    frame.question_attempts.get(key, 0) + 1
                )
                frame.last_question_key = key
                frame.touch(self.FRAME_TTL_S)
            return key, frame.question_attempts.get(key, 0)

    def mark_frame_question(self, key: str, goal: str = "",
                            intent: str = "") -> int:
        """Record that a handler asked for one concrete evidence slot."""
        if not key:
            return 0
        with self._frame_lock:
            frame = self.ensure_frame(goal, intent)
            frame.question_attempts[key] = frame.question_attempts.get(key, 0) + 1
            frame.last_question_key = key
            frame.touch(self.FRAME_TTL_S)
            return frame.question_attempts[key]

    def conversation_details(self, raw: str) -> Dict[str, Any]:
        """Public, copy-returning view of short conversational details."""
        return dict(self._detail_evidence(raw))

    def correct_subject_from_text(self, raw: str) -> tuple[str, str]:
        """Apply an explicit 'not X, Y' correction to the current frame."""
        folded = self._fold_text(raw)
        if re.search(r"\b(?:i meant|i mean|correction)\b", folded):
            tail = re.split(
                r"\b(?:i meant|i mean|correction)\b", folded, maxsplit=1,
            )[-1]
            tail = re.split(r"\b(?:not|rather than)\b", tail, maxsplit=1)[0]
        elif re.search(
                r"\b(?:chodzi o|chodzi mi o|chodzilo o|chodzilo mi o)\b",
                folded):
            tail = re.split(
                r"\b(?:chodzi o|chodzi mi o|chodzilo o|chodzilo mi o)\b",
                folded, maxsplit=1,
            )[-1]
        elif (re.search(r"\b(?:nie|not)\b", folded)
              and re.search(r"\b(?:tylko|but|instead|rather)\b", folded)):
            tail = re.split(
                r"\b(?:tylko|but|instead(?: of)?|rather)\b", folded, maxsplit=1,
            )[-1]
        elif re.search(r"\brather than\b", folded):
            tail = re.split(r"\brather than\b", folded, maxsplit=1)[0]
        elif re.search(r"\b(?:tylko|but|instead)\b", folded):
            tail = re.split(
                r"\b(?:tylko|but|instead(?: of)?)\b", folded, maxsplit=1,
            )[-1]
        elif re.search(r"\b(?:nie|not)\b[^,;]{1,35}[,;]", folded):
            tail = re.split(r"[,;]", folded, maxsplit=1)[-1]
        else:
            tail = folded
        refs: Dict[str, str] = {}
        proc = self._PROCESS_RE.search(tail)
        part = self._PART_RE.search(tail)
        if proc:
            refs["process"] = proc.group(1).lower()
        if part:
            refs["part"] = re.sub(r"\s+", " ", part.group(1).lower())
        for game in self._KNOWN_GAMES:
            if self._fold_text(game) in tail:
                refs["game"] = game
                break
        component_cues = {
            "cpu": ("cpu", "procesor", "procek"),
            "gpu": ("gpu", "karta graficzna", "grafika"),
            "ram": ("ram", "pamiec"),
            "storage": ("dysk", "ssd", "hdd", "storage"),
            "motherboard": ("plyta", "motherboard"),
        }
        component_hits = []
        for component, cues in component_cues.items():
            for cue in cues:
                match = re.search(rf"\b{re.escape(cue)}\b", tail)
                if match:
                    component_hits.append((match.start(), component))
        if component_hits:
            refs["component"] = max(component_hits)[1]
        kind, value = self._subject_from_refs(refs)
        if not value:
            return "", ""
        with self._frame_lock:
            frame = self.ensure_frame()
            frame.subject_kind, frame.subject_value = kind, value
            frame.evidence["subject_corrected"] = True
            frame.touch(self.FRAME_TTL_S)
            self._last_references[kind] = {
                "value": value, "intent": "correct_subject",
                "recorded_at": time.time(),
            }
        return kind, value

    def set_frame_subject(self, kind: str, value: str,
                          corrected: bool = False) -> bool:
        if not kind or not value:
            return False
        with self._frame_lock:
            frame = self.ensure_frame()
            frame.subject_kind, frame.subject_value = kind, value
            if corrected:
                frame.evidence["subject_corrected"] = True
            frame.touch(self.FRAME_TTL_S)
            self._last_references[kind] = {
                "value": value, "intent": frame.last_intent,
                "recorded_at": time.time(),
            }
            return True

    def set_advice_state(self, state: str, verification: str = "") -> bool:
        with self._frame_lock:
            frame = self.active_frame()
            if frame is None:
                return False
            if state in ("offered", "accepted", "declined"):
                frame.advice_state = state
            if verification:
                frame.verification_state = verification
            frame.touch(self.FRAME_TTL_S)
            return True

    def record_verification(self, outcome: str,
                            current: Optional[Dict[str, Any]] = None) -> bool:
        with self._frame_lock:
            frame = self.active_frame()
            if frame is None:
                return False
            if outcome in ("better", "same", "worse", "measured"):
                frame.verification_state = outcome
            frame.advice_state = "accepted"
            frame.verification = dict(current or self.collect_live_evidence())
            frame.touch(self.FRAME_TTL_S)
            return True

    def compare_frame_evidence(self,
                               current: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        frame = self.active_frame()
        if frame is None or not frame.baseline:
            return {}
        after = dict(current or self.collect_live_evidence())
        deltas: Dict[str, float] = {}
        for key in ("cpu_pct", "ram_pct", "gpu_pct", "gpu_temp"):
            if key in frame.baseline and key in after:
                deltas[key] = round(float(after[key]) - float(frame.baseline[key]), 1)
        if (frame.baseline.get("cpu_temp_source") == "sensor"
                and after.get("cpu_temp_source") == "sensor"
                and "cpu_temp" in frame.baseline and "cpu_temp" in after):
            deltas["cpu_temp"] = round(
                float(after["cpu_temp"]) - float(frame.baseline["cpu_temp"]), 1)
        return deltas

    def frame_summary(self) -> str:
        frame = self.active_frame()
        if frame is None:
            return ""
        subject = (f"{frame.subject_kind}={frame.subject_value}"
                   if frame.subject_value else "unspecified")
        evidence = ", ".join(
            f"{k}={v}" for k, v in list(frame.evidence.items())[:6]
        ) or "none"
        missing = ",".join(frame.missing_evidence[:4]) or "none"
        return (
            f"goal={frame.goal or 'unspecified'}; subject={subject}; "
            f"symptom={frame.symptom or 'unspecified'}; evidence={evidence}; "
            f"missing={missing}; advice={frame.advice_state}; "
            f"verification={frame.verification_state}; "
            f"next_question={frame.last_question_key or 'none'}; "
            f"confidence={frame.confidence:.2f}"
        )

    def remember_turn(self, result: Any, response: List[str]) -> None:
        """Remember concrete subjects from one answered turn.

        Stores only short identifiers needed by immediate follow-ups: component,
        process, game and candidate part. It intentionally does not create a
        long-term personal profile.
        """
        raw = str(getattr(result, "raw_text", "") or "")
        intent = str(getattr(result, "intent", "") or "")
        confidence = float(getattr(result, "confidence", 0.0) or 0.0)
        entities = dict(getattr(result, "entities", {}) or {})
        refs: Dict[str, str] = {}

        # Control handlers update the existing frame themselves. Re-extracting
        # both sides of "not GPU, CPU" here could undo the correction.
        if intent not in self._CONTROL_INTENTS:
            for kind in ("cpu", "gpu", "ram", "storage", "motherboard",
                         "temperature", "process", "game"):
                if kind in entities:
                    refs["component" if kind in {
                        "cpu", "gpu", "ram", "storage", "motherboard"
                    } else kind] = kind

            component = self._INTENT_COMPONENT.get(intent)
            if component and component != "temperature":
                refs.setdefault("component", component)

            proc_match = self._PROCESS_RE.search(raw)
            if proc_match:
                refs["process"] = proc_match.group(1).lower()

            part_match = self._PART_RE.search(raw)
            if part_match:
                refs["part"] = re.sub(r"\s+", " ", part_match.group(1).lower())

            folded = self._fold_text(raw)
            for game in self._KNOWN_GAMES:
                if self._fold_text(game) in folded:
                    refs["game"] = game
                    break

        now = time.time()
        for kind, value in refs.items():
            self._last_references[kind] = {
                "value": value, "intent": intent, "recorded_at": now,
            }

        headline = str(response[0])[:180] if response else ""
        self._turn_context.append({
            "intent": intent,
            "raw_text": raw[:300],
            "entities": entities,
            "references": refs,
            "headline": headline,
            "recorded_at": now,
        })

        with self._frame_lock:
            frame = self.active_frame()
            if intent in self._CONTROL_INTENTS:
                if frame is not None:
                    frame.last_intent = intent
                    frame.confidence = max(frame.confidence, confidence)
                    frame.touch(self.FRAME_TTL_S)
                return

            goal = self._GOAL_BY_INTENT.get(intent, "inspect" if refs else "")
            if not goal:
                return
            symptom = self._SYMPTOM_BY_INTENT.get(intent, "")
            details = self._detail_evidence(raw)
            if details.get("game"):
                refs.setdefault("game", str(details["game"]))
            subject_kind, subject_value = self._subject_from_refs(refs)

            replace = frame is None
            if frame is not None and subject_value and frame.subject_value:
                replace = (subject_kind != frame.subject_kind
                           or subject_value != frame.subject_value)
            if (frame is not None and not replace and goal != frame.goal
                    and not (subject_value and subject_value == frame.subject_value)
                    and frame.last_intent not in self._CONTROL_INTENTS):
                replace = True
            if replace:
                frame = self._new_frame(goal, intent)
            assert frame is not None

            frame.goal = goal or frame.goal
            frame.symptom = symptom or frame.symptom
            frame.source_intent = frame.source_intent or intent
            frame.last_intent = intent
            frame.confidence = max(frame.confidence, confidence)
            if subject_value:
                frame.subject_kind = subject_kind
                frame.subject_value = subject_value
            frame.evidence.update(details)
            frame.missing_evidence = self._missing_for(
                frame.goal, frame.symptom, frame.evidence, refs,
            )

            if intent in self._ADVICE_INTENTS and response:
                frame.advice = self._advice_excerpt(response)
                frame.advice_intent = intent
                frame.advice_state = "offered"
                frame.verification_state = "waiting"
                frame.baseline = self.collect_live_evidence()
            frame.touch(self.FRAME_TTL_S)

    def last_reference(self, kind: str, max_age_seconds: float = 900) -> str:
        item = self._last_references.get(kind, {})
        if not item or time.time() - item.get("recorded_at", 0) > max_age_seconds:
            return ""
        return str(item.get("value", ""))

    def recent_turn_context(self, n: int = 4) -> List[Dict[str, Any]]:
        return [dict(item) for item in list(self._turn_context)[-n:]]

    def reference_summary(self) -> str:
        fresh = []
        for kind in ("component", "process", "game", "part"):
            value = self.last_reference(kind)
            if value:
                fresh.append(f"{kind}={value}")
        return ", ".join(fresh)

    def resolve_followup(self, text: str, parsed: Any) -> Any:
        """Resolve compact PL/EN follow-ups into a concrete ParseResult.

        Explicit, confidently parsed questions are left untouched. The method
        only intervenes when a pronoun or a short continuation clearly depends
        on the previous turn.
        """
        folded = self._fold_text(text)
        words = folded.split()
        if not words or not self._turn_context:
            return parsed

        current_intent = str(getattr(parsed, "intent", "unknown") or "unknown")
        confidence = float(getattr(parsed, "confidence", 0.0) or 0.0)
        entities = dict(getattr(parsed, "entities", {}) or {})
        last_intent = str(self._turn_context[-1].get("intent", "") or "")

        temp_followup = any(p in folded for p in (
            "a temperatura", "jego temperatura", "jej temperatura",
            "ile ma stopni", "czy sie grzeje", "czy jest goracy",
            "what about the temperature", "its temperature",
            "how hot is it", "is it running hot",
        )) or ("ile ma" in folded and "stopni" in folded)
        process_close = any(p in folded for p in (
            "czy moge go zamknac", "czy moge go wylaczyc",
            "czy moge go zabic", "zamknac go", "wylaczyc go",
            "can i close it", "can i stop it", "can i kill it",
            "is it safe to close",
        ))
        process_more = folded in {
            "co z nim", "co on robi", "wiecej o nim", "a ten proces",
            "what about it", "what does it do", "more about it",
        }
        fit_followup = any(p in folded for p in (
            "czy bedzie pasowac", "czy to bedzie pasowac", "czy zadziala",
            "a kompatybilnosc", "will it fit", "will that fit",
            "is it compatible", "will it work",
        ))
        frame = self.active_frame()
        details = self._detail_evidence(text)
        correction = (
            any(p in folded for p in (
                "nie chodzi o", "mialem na mysli", "chodzi mi o",
                "chodziło mi o", "chodzilo mi o", "pomylilem sie",
                "pomylilam sie", "poprawka", "not the", "i meant",
                "i mean", "rather than", "my mistake", "correction",
            ))
            or bool(re.search(r"\b(?:nie|not)\b.{1,35}\b(?:tylko|but|instead|rather)\b", folded))
        )
        advice_explain = any(p in folded for p in (
            "dlaczego to radzisz", "czemu to radzisz", "po co mam to robic",
            "skad taki krok", "na czym opierasz porade", "why do you recommend",
            "why should i do", "explain that advice", "why this step",
        ))
        verify = any(p in folded for p in (
            "zrobilem to", "zrobilam to", "juz zrobione", "wykonalem",
            "wykonalam", "gotowe", "sprobowalem", "sprobowalam",
            "jest lepiej", "bez zmian", "jest gorzej", "nie pomoglo",
            "i did it", "done now", "finished it", "i tried it",
            "it is better", "no change", "it got worse", "did not help",
        ))
        decline = any(p in folded for p in (
            "nie chce tego robic", "odpuscmy to", "pominmy to",
            "wole tego nie ruszac", "tego nie zrobie", "inny sposob",
            "i do not want to do that", "skip that advice", "not doing that",
            "i would rather not", "another way",
        ))
        compare = any(p in folded for p in (
            "porownaj teraz", "co sie zmienilo po", "sprawdz efekt",
            "sprawdz ponownie", "zmierz jeszcze raz", "odczytaj jeszcze raz",
            "compare it now", "what changed after", "check the result",
            "check again", "measure again", "read it again",
        ))
        confidence_q = any(p in folded for p in (
            "jak bardzo jestes pewny", "skad ta pewnosc", "na ile to pewne",
            "to pewne czy zgadujesz", "fakt czy hipoteza",
            "how confident are you", "how sure are you", "why so confident",
            "is that certain or a guess", "fact or hypothesis",
        ))
        explicit_new_cues = {
            "czy", "jaki", "jaka", "jakie", "co", "pokaz", "sprawdz",
            "what", "which", "show", "check", "list", "apps", "app",
            "programy", "aplikacje", "temperatura", "temperature", "temp",
            "cpu", "gpu", "ram", "procesor",
        }
        compact_detail_answer = (
            len(words) <= 6
            and not explicit_new_cues.intersection(words)
            and not folded.endswith("?")
        )

        intent = None
        raw_text = text
        if correction:
            intent = "correct_subject"
        elif advice_explain and frame and frame.advice:
            intent = "explain_previous_advice"
        elif verify and frame and frame.advice:
            intent = "verify_after_action"
        elif decline and frame and frame.advice:
            intent = "decline_advice"
        elif compare and frame and frame.baseline:
            intent = "compare_after_change"
        elif confidence_q and frame:
            intent = "explain_confidence"
        elif (frame and frame.goal == "upgrade" and details.get("budget")
              and (current_intent in (
                  "unknown", "upgrade_budget", "small_talk",
                  "continue_diagnosis",
              ) or confidence < 0.65)):
            intent = "upgrade_budget"
        elif (frame and frame.goal == "upgrade" and details.get("workload")
              and (current_intent in (
                  "unknown", "upgrade_workload", "small_talk",
                  "continue_diagnosis",
              ) or confidence < 0.65)):
            intent = "upgrade_workload"
        elif (frame and frame.goal == "repair_desktop"
              and details.get("recurrence")
              and (current_intent in (
                  "unknown", "desktop_recurrence", "small_talk",
                  "continue_diagnosis",
              ) or confidence < 0.65)):
            intent = "desktop_recurrence"
        elif (frame and frame.goal in ("diagnose", "game", "cool", "inspect")
              and details and len(words) <= 24
              and (current_intent in (
                  "unknown", "why_slow", "fps_degradation",
                  "symptom_freeze", "small_talk", "continue_diagnosis",
              ) or confidence < 0.65 or compact_detail_answer)):
            # Human answers are often just "in game", "after 20 minutes" or
            # "more like stutter". They complete the pending diagnosis rather
            # than opening an unrelated intent.
            intent = "continue_diagnosis"
            entities.update({f"context_{k}": str(v)
                             for k, v in details.items()})
        elif process_close and self.last_reference("process"):
            intent = "process_kill"
            proc = self.last_reference("process")
            entities["process"] = proc
            raw_text = f"{text} {proc}"
        elif process_more and self.last_reference("process"):
            intent = "process_deep_dive"
            proc = self.last_reference("process")
            entities["process"] = proc
            raw_text = f"{text} {proc}"
        elif fit_followup and self.last_reference("part"):
            part = self.last_reference("part")
            intent = "ram_compat" if part.startswith("ddr") else "upgrade_compat"
            entities["part"] = part
            raw_text = f"{text} {part}"
        elif temp_followup:
            component = self.last_reference("component")
            intent = "gpu_temp_why" if component == "gpu" else "temperature"
            if component:
                entities[component] = component
        elif folded in {
            "a teraz", "i teraz", "co teraz pokazuje", "sprawdz ponownie",
            "what about now", "and now", "check again",
        } and last_intent:
            intent = last_intent
        elif folded in {
            "wroc do tego", "wracamy do tego", "kontynuuj temat",
            "go back to that", "continue that topic",
        } and last_intent:
            intent = last_intent

        if not intent:
            return parsed

        try:
            from hck_gpt.intents.parser import ParseResult
            return ParseResult(
                intent=intent,
                confidence=max(confidence, 0.92),
                entities=entities,
                tokens=list(getattr(parsed, "tokens", []) or []),
                raw_text=raw_text,
            )
        except Exception:
            return parsed

    # ── Context snapshot ──────────────────────────────────────────────────────

    def update_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.live_snapshot = snapshot

    # ── Topic tracking ────────────────────────────────────────────────────────

    # ── Session data store ────────────────────────────────────────────────────

    def record_response_data(self, intent: str, data: dict) -> None:
        """
        Store the key values that were reported in a response for *intent*.
        Called by ResponseBuilder handlers after they compute their output,
        so later handlers can reference what was shown earlier in the session.

        Example:
            session_memory.record_response_data("hw_ram", {
                "total_gb": 16, "speed": 3200, "current_pct": 51
            })
        """
        self._session_data[intent] = {"recorded_at": time.time(), **data}
        # Keep session store bounded - evict oldest when over 40 intents
        if len(self._session_data) > 40:
            oldest = min(self._session_data, key=lambda k: self._session_data[k].get("recorded_at", 0))
            del self._session_data[oldest]

    def last_recorded(self, n: int = 3) -> list:
        """Most recent (intent, data) pairs from the response ledger,
        newest first. Powers 'what was that number?' recall."""
        items = sorted(self._session_data.items(),
                       key=lambda kv: kv[1].get("recorded_at", 0),
                       reverse=True)
        return items[:n]

    def get_response_data(self, intent: str) -> dict:
        """
        Retrieve values previously recorded for a given intent.
        Returns an empty dict when the intent has not been reported yet.
        """
        return dict(self._session_data.get(intent, {}))

    def discussed_this_session(self) -> List[str]:
        """Return list of intents that have session data stored (= were reported)."""
        return list(self._session_data.keys())

    def push_topic(self, topic: str) -> None:
        """Push a new conversation topic (e.g. 'cpu', 'gpu', 'health')."""
        if not self._topic_stack or self._topic_stack[-1] != topic:
            self._topic_stack.append(topic)
        if len(self._topic_stack) > 6:
            self._topic_stack.pop(0)

    def current_topic(self) -> Optional[str]:
        return self._topic_stack[-1] if self._topic_stack else None

    def previous_topic(self) -> Optional[str]:
        return self._topic_stack[-2] if len(self._topic_stack) >= 2 else None

    def topic_history(self) -> List[str]:
        return list(self._topic_stack)

    # ── Metric trends ─────────────────────────────────────────────────────────

    def push_metric(self, cpu: float, ram: float) -> None:
        """Record a new CPU/RAM reading. Call from system polling loop or snapshot."""
        self._cpu_trend.append(cpu)
        self._ram_trend.append(ram)
        self._trend_last_at = time.time()

    def get_trend(self, metric: str = "cpu") -> str:
        """
        Returns 'rising', 'falling', or 'stable'.
        Requires at least 4 readings.
        """
        buf = self._cpu_trend if metric == "cpu" else self._ram_trend
        readings = list(buf)
        if len(readings) < 4:
            return "stable"
        # Compare first half average vs second half average
        mid = len(readings) // 2
        first_avg  = sum(readings[:mid]) / mid
        second_avg = sum(readings[mid:]) / (len(readings) - mid)
        delta = second_avg - first_avg
        if delta > 5:
            return "rising"
        if delta < -5:
            return "falling"
        return "stable"

    def trend_summary(self) -> str:
        """Short human-readable trend line for LLM context."""
        cpu_t = self.get_trend("cpu")
        ram_t = self.get_trend("ram")
        parts = []
        if cpu_t != "stable":
            parts.append(f"CPU {cpu_t}")
        if ram_t != "stable":
            parts.append(f"RAM {ram_t}")
        return ", ".join(parts) if parts else "stable"

    # ── Conversation summary ──────────────────────────────────────────────────

    def _auto_summarize(self) -> None:
        """
        Simple extractive summarizer - no LLM needed.
        Collects user messages + known topics, writes a short summary sentence.
        Always safe to call - all exceptions are swallowed.
        """
        try:
            self._auto_summarize_impl()
        except Exception:
            pass

    def _auto_summarize_impl(self) -> None:
        """Internal summarizer logic - called inside try/except."""
        recent = [m for m in list(self._messages)[-12:] if m.role == "user"]
        if not recent:
            return

        # Extract keywords from user messages
        topic_labels = {
            "hw_cpu": "processor", "hw_gpu": "GPU", "hw_ram": "RAM",
            "hw_all": "full specs", "health_check": "system health",
            "temperature": "temperatures", "throttle_check": "throttling",
            "performance": "performance", "stats": "statistics",
            "processes": "processes", "optimization": "optimization",
            "power_plan": "power plan", "uptime": "session uptime",
            "hw_storage": "storage", "hw_motherboard": "motherboard",
            # New intents
            "turbo_boost": "TURBO Boost", "why_slow": "PC slowdown/lag",
            "process_info": "process identification", "ram_why_high": "RAM usage",
            "gpu_temp_why": "GPU temperature", "disk_health": "disk health",
            "session_compare": "session comparison", "virus_check": "security scan",
            "unnecessary_programs": "background programs", "speed_up_pc": "speed optimization",
            # Community feedback intents
            "fan_noise_history":    "fan noise analysis",
            "driver_status":        "driver status",
            "gaming_vs_work_time":  "gaming vs work time",
            "process_identity":     "process identity check",
            "stale_apps":           "unused applications",
            "fps_degradation":      "FPS degradation (time-travel)",
            "app_behavior_change":  "app behavior change",
            "startup_slowdown":     "startup slowdown analysis",
            "temp_comparison":      "temperature trend comparison",
            "crash_context":        "crash/freeze context",
            "game_hardware_stress": "game hardware stress",
            "battery_drain_rate":   "battery drain rate",
            "power_after_restart":  "power usage since restart",
            # Wave 2 community intents
            "game_can_run":         "game requirements check",
            "gaming_ram_usage":     "gaming RAM usage",
            "daily_ram_usage":      "daily RAM usage",
            "battery_estimate":     "battery life estimate",
            "upgrade_feasibility":  "hardware upgrade feasibility",
            "top_resource_hog":     "top resource consumer",
            "browser_cache":        "browser cache / memory",
            "ram_compare":          "RAM usage comparison",
            "swap_analysis":        "swap / pagefile analysis",
            "usb_transfer":         "USB / external drive transfer",
            "network_usage":        "network usage by process",
            "startup_safety":       "startup program management",
        }
        topics_seen = []
        for t in self._topic_stack:
            label = topic_labels.get(t, t.replace("_", " "))
            if label not in topics_seen:
                topics_seen.append(label)

        texts = " ".join(m.text for m in recent[-6:])

        if topics_seen:
            self.conversation_summary = (
                f"User has been asking about: {', '.join(topics_seen[:4])}."
            )
        else:
            # fallback - take first 120 chars of combined messages
            excerpt = texts[:120].strip()
            self.conversation_summary = f"Recent questions: {excerpt}..."

    def get_conversation_summary(self) -> str:
        """Returns conversation summary, generating one if empty."""
        if not self.conversation_summary and self._topic_stack:
            self._auto_summarize()
        return self.conversation_summary

    # ── LLM context builder ───────────────────────────────────────────────────

    def get_context_for_llm(self) -> str:
        """
        Returns a compact formatted context block to inject into the LLM prompt.
        Covers: current topic, summary, recent exchange, events, trends.
        """
        parts: List[str] = []

        topic = self.current_topic()
        if topic:
            parts.append(f"Current topic: {topic.replace('_', ' ')}")

        summary = self.get_conversation_summary()
        if summary:
            parts.append(f"Context: {summary}")

        refs = self.reference_summary()
        if refs:
            parts.append(f"Current references: {refs}")

        frame = self.frame_summary()
        if frame:
            parts.append(f"Active diagnostic frame: {frame}")

        recent = self.recent_exchange_text(n_pairs=3)
        if recent:
            parts.append("Recent chat:\n" + recent)

        events = self.recent_events_summary(within_minutes=20)
        if events:
            parts.append(f"Recent system alerts this session: {events}")

        trends = self.trend_summary()
        if trends and trends != "stable":
            parts.append(f"Metric trends: {trends}")

        return "\n".join(parts)

    # ── Time-windowed event context (MEGA FEATURE: Time-Travel Debugging) ────

    def get_events_for_window(self, within_minutes: float) -> List[ObservedEvent]:
        """Return events that occurred within the given time window."""
        return [e for e in self._events if e.age_minutes() <= within_minutes]

    def get_spike_context(self, within_minutes: float = 120) -> Optional[str]:
        """
        Returns a structured summary of spikes/anomalies within the time window.
        Used by crash_context and app_behavior_change handlers for Time-Travel.
        """
        events = self.get_events_for_window(within_minutes)
        if not events:
            return None

        lines: List[str] = []
        for evt in events:
            age_m = evt.age_minutes()
            lines.append(
                f"  [{age_m:.0f}m ago] {evt.event_type}"
                + (f": {evt.detail}" if evt.detail else "")
            )
        return "\n".join(lines) if lines else None

    def get_time_windowed_context(self, intent: str, lang: str = "pl") -> str:
        """
        MEGA FEATURE: Context Time-Windowing for session data.
        Returns compact context relevant to the given intent.
        Crash/freeze intents get all events + trend context.
        """
        parts: List[str] = []

        # Topic + summary always useful
        topic = self.current_topic()
        if topic:
            parts.append(f"Current topic: {topic.replace('_', ' ')}")

        summary = self.get_conversation_summary()
        if summary:
            parts.append(f"Context: {summary}")

        frame = self.frame_summary()
        if frame:
            parts.append(f"Active diagnostic frame: {frame}")

        # Intent-specific event window
        _time_windows_min = {
            "crash_context":        240.0,
            "app_behavior_change":  120.0,
            "fan_noise_history":    60.0,
            "fps_degradation":      60.0,
            "temp_comparison":      60.0,
            "why_slow":             30.0,
            "health_check":         30.0,
        }
        window = _time_windows_min.get(intent, 20.0)
        spike_ctx = self.get_spike_context(within_minutes=window)
        if spike_ctx:
            parts.append(f"System events (last {window:.0f}min):\n{spike_ctx}")

        # Metric trends
        trends = self.trend_summary()
        if trends and trends != "stable":
            parts.append(f"Metric trends: {trends}")

        # Recent exchange
        recent = self.recent_exchange_text(n_pairs=3)
        if recent:
            parts.append("Recent chat:\n" + recent)

        return "\n".join(parts)

    # ── Utilities ─────────────────────────────────────────────────────────────

    def session_duration_str(self) -> str:
        elapsed = time.time() - self.started_at
        h, r  = divmod(int(elapsed), 3600)
        m, s  = divmod(r, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    def message_count(self) -> int:
        return len(self._messages)


# ── Singleton ─────────────────────────────────────────────────────────────────
session_memory = SessionMemory()
