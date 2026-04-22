# hck_gpt/memory/session_memory.py
"""
Session Memory — in-RAM state for the current app session.

Tracks:
  - Message history (last 50 exchanges)
  - Observed system events this session (spikes, throttles, etc.)
  - Last known live PC snapshot
  - Conversation topic stack (for contextual follow-up)
  - CPU/RAM trend buffer (rising / stable / falling)
  - Auto conversation summary (every 6 messages — used by Hybrid Engine)

Not persisted to disk — cleared on every app restart.
For persistent knowledge see user_knowledge.py
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Any, Tuple


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

    def __init__(self) -> None:
        self.session_id: str   = f"s_{int(time.time())}"
        self.started_at: float = time.time()

        self._messages: Deque[Message]       = deque(maxlen=self.MAX_MESSAGES)
        self._events:   Deque[ObservedEvent] = deque(maxlen=self.MAX_EVENTS)

        # Last snapshot from SystemContext.snapshot()
        self.live_snapshot: Dict[str, Any] = {}

        # Conversation topic stack — top = current subject
        self._topic_stack: List[str] = []

        # Flags / counters used by the response builder
        self.greeted_this_session: bool = False
        self.hardware_scanned:     bool = False

        # ── Trend tracking ────────────────────────────────────────────────────
        # Circular buffers of recent metric readings
        self._cpu_trend: Deque[float] = deque(maxlen=self.TREND_WINDOW)
        self._ram_trend: Deque[float] = deque(maxlen=self.TREND_WINDOW)
        self._trend_last_at: float    = 0.0

        # ── Conversation summary ──────────────────────────────────────────────
        self.conversation_summary: str = ""
        self._summary_at_count: int    = 0   # message count when last summarized

    # ── Messages ──────────────────────────────────────────────────────────────

    def add_message(self, role: str, text: str) -> None:
        # Sanitize text — strip null bytes that could cause downstream issues
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

    # ── Context snapshot ──────────────────────────────────────────────────────

    def update_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.live_snapshot = snapshot

    # ── Topic tracking ────────────────────────────────────────────────────────

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
        Simple extractive summarizer — no LLM needed.
        Collects user messages + known topics, writes a short summary sentence.
        Always safe to call — all exceptions are swallowed.
        """
        try:
            self._auto_summarize_impl()
        except Exception:
            pass

    def _auto_summarize_impl(self) -> None:
        """Internal summarizer logic — called inside try/except."""
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
            # fallback — take first 120 chars of combined messages
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
