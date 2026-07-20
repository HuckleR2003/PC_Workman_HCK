# hck_gpt/engine/flow_engine.py
"""
FlowEngine - stateful multi-step guided flows for hck_GPT.

Generalizes the pattern proven by `tuneup_guide` (the first stateful
coaching handler): a flow is a LIST OF STEPS, each step a callable that
returns chat lines and may read/write shared flow state. The engine owns
navigation, so every guide gets these for free:

    dalej / next / ok / go            -> advance to the next step
    tak / yes / zrób / do it          -> confirm an action step (runs it)
    pomiń / skip                      -> skip an action without running it
    stop / koniec / anuluj / cancel   -> abort the flow

Design rules (ARCHITECTURE.md - extend, never duplicate):
  * ONE active flow at a time; starting a new one replaces the old.
  * TTL: an abandoned flow expires silently after FLOW_TTL_S.
  * Interjections: a message that is NOT flow navigation returns None so
    the normal intent pipeline answers it - the flow stays paused and the
    user can come back with "dalej". No hijacking.
  * Verify-after-action: steps share `state` (a dict); measure steps store
    before-numbers, verify steps report the MEASURED delta. An optimizer
    that proves its work with numbers beats one that claims.
  * Headless: no Tk imports; fully unit-testable.

Flow definitions live in hck_gpt/responses/flows.py (data + step callables).
"""
from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

FLOW_TTL_S = 600   # 10 min of silence = flow forgotten

_NEXT    = ("dalej", "next", "ok", "oki", "go", "kontynuuj", "continue", "gotowe", "ready")
_CONFIRM = ("tak", "yes", "zrób", "zrob", "do it", "run", "wykonaj", "jedziemy", "yep")
_SKIP    = ("pomiń", "pomin", "skip", "nie", "no", "później", "later")
_ABORT   = ("stop", "koniec", "anuluj", "cancel", "przerwij", "end", "quit", "wyjdź")


class FlowStep:
    """One step of a flow.

    say(rb, state, lang) -> List[str]   - always called when the step opens.
    act(rb, state, lang) -> List[str]   - optional; runs only after the user
                                          CONFIRMS (tak/yes). Steps with an
                                          act are "action steps": the engine
                                          waits for tak / pomiń instead of
                                          plain dalej.
    """

    def __init__(self, say: Callable, act: Optional[Callable] = None):
        self.say = say
        self.act = act


class Flow:
    def __init__(self, flow_id: str, steps: List[FlowStep]):
        self.id = flow_id
        self.steps = steps


class FlowEngine:
    def __init__(self):
        self._flows: Dict[str, Flow] = {}
        self._active: Optional[str] = None
        self._step = 0
        self._acted = False          # current action step already executed?
        self._state: dict = {}
        self._lang = "pl"
        self._ts = 0.0

    # ── registration ─────────────────────────────────────────────────────────
    def register(self, flow: Flow) -> None:
        self._flows[flow.id] = flow

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def start(self, flow_id: str, rb, lang: str = "pl") -> List[str]:
        """Begin a flow at step 0 (replaces any active flow)."""
        flow = self._flows.get(flow_id)
        if flow is None:
            return []
        self._active = flow_id
        self._step = 0
        self._acted = False
        self._state = {}
        self._lang = lang
        self._ts = time.time()
        return self._open_step(rb)

    def abort(self) -> None:
        self._active = None
        self._state = {}

    def is_active(self) -> bool:
        if self._active and (time.time() - self._ts) > FLOW_TTL_S:
            self.abort()                      # expired silently
        return self._active is not None

    @property
    def active_flow_id(self) -> Optional[str]:
        return self._active if self.is_active() else None

    # ── input handling (called from chat_handler BEFORE normal routing) ──────
    def process_input(self, msg: str, rb) -> Optional[List[str]]:
        """Handle a user message while a flow is active.
        Returns chat lines, or None when the message is NOT flow navigation
        (the caller then routes it normally and the flow stays paused)."""
        if not self.is_active():
            return None
        word = (msg or "").strip().lower()
        flow = self._flows[self._active]
        step = flow.steps[self._step]
        lang = self._lang

        if word in _ABORT:
            self.abort()
            return [("Przerwałem przewodnik. Wróć kiedy chcesz, "
                     "zaczniemy od nowa.") if lang == "pl" else
                    ("Guide stopped. Come back any time - "
                     "we'll start fresh.")]

        is_action = step.act is not None and not self._acted

        if is_action and word in _CONFIRM:
            self._ts = time.time()
            self._acted = True
            out = []
            try:
                out = step.act(rb, self._state, lang) or []
            except Exception:
                out = ["⚠ " + ("Akcja nie powiodła się - lecimy dalej."
                               if lang == "pl" else
                               "That action failed - moving on.")]
            return out + self._advance(rb)

        if word in _NEXT or (is_action and word in _SKIP):
            self._ts = time.time()
            return self._advance(rb)

        if word in _CONFIRM and not is_action:
            # "tak" on a plain step just advances
            self._ts = time.time()
            return self._advance(rb)

        return None   # not navigation -> let normal routing answer, stay paused

    # ── internals ─────────────────────────────────────────────────────────────
    def _advance(self, rb) -> List[str]:
        flow = self._flows[self._active]
        self._step += 1
        self._acted = False
        if self._step >= len(flow.steps):
            self.abort()
            return []
        return self._open_step(rb)

    def _open_step(self, rb) -> List[str]:
        flow = self._flows[self._active]
        step = flow.steps[self._step]
        self._ts = time.time()
        try:
            lines = step.say(rb, self._state, self._lang) or []
        except Exception:
            lines = []
        if self._step >= len(flow.steps) - 1 and step.act is None:
            # last plain step ends the flow after speaking
            self.abort()
        return lines


# ── Singleton ──────────────────────────────────────────────────────────────────
flow_engine = FlowEngine()
