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

_NEXT    = ("dalej", "next", "ok", "oki", "go", "kontynuuj", "continue", "gotowe", "ready",
            "zaczynajmy", "zaczynamy", "start", "lecimy", "let's go")
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

    def __init__(self, say: Callable, act: Optional[Callable] = None,
                 ask: Optional[Callable] = None, chips: tuple = (),
                 yes: Optional[tuple] = None):
        self.say = say
        self.act = act
        # ask(rb, state, lang, msg) -> lines | None: a question asked while
        # this step is open ("nie ma nic do wylaczenia?" on the startup step
        # used to get "I did not understand"; 2026-11-16)
        self.ask = ask
        # quick replies offered under this step: "start", "next",
        # "nav:<link name>"; yes / skip / stop are added automatically
        self.chips = tuple(chips)
        # label of the confirm button for this action step, (pl, en);
        # default "TAK, WYKONAJ" (2026-11-17: "TAK, SPRAWDŹ" for checks).
        # May be a callable(state) -> (pl, en) when the step offers
        # different things (2026-11-20: the network guide)
        self.yes = yes


class Flow:
    def __init__(self, flow_id: str, steps: List[FlowStep],
                 finish: Optional[Callable] = None):
        self.id = flow_id
        self.steps = steps
        # finish(rb, state, lang) -> lines said when the user moves past the
        # last step (an action step ends the flow whether run or skipped)
        self.finish = finish


class FlowEngine:
    def __init__(self):
        self._flows: Dict[str, Flow] = {}
        self._active: Optional[str] = None
        self._step = 0
        self._acted = False          # current action step already executed?
        self._state: dict = {}
        self._lang = "pl"
        self._ts = 0.0
        self._last_transition: dict = {}
        self._completed_state: dict = {}

    # ── registration ─────────────────────────────────────────────────────────
    def register(self, flow: Flow) -> None:
        self._flows[flow.id] = flow

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def start(self, flow_id: str, rb, lang: str = "pl",
              initial_state: Optional[dict] = None) -> List[str]:
        """Begin a flow at step 0 (replaces any active flow)."""
        flow = self._flows.get(flow_id)
        if flow is None:
            return []
        self._active = flow_id
        self._step = 0
        self._acted = False
        self._state = dict(initial_state or {})
        self._lang = lang
        self._ts = time.time()
        out = self._open_step(rb)
        self._last_transition = {
            "flow_id": flow_id, "event": "started",
            "state": dict(self._state), "completed": not self.is_active(),
        }
        return out

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

    @property
    def last_transition(self) -> dict:
        return dict(self._last_transition)

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
            flow_id = self._active
            state = dict(self._state)
            self.abort()
            self._last_transition = {
                "flow_id": flow_id, "event": "aborted",
                "state": state, "completed": True,
            }
            if state.get("flush"):
                return [("Przerwałem przewodnik. Zmieniliśmy tylko jedno: zwolniłem "
                         "pamięć (RAM Flush). Wiesz, gdzie mnie szukać :)")
                        if lang == "pl" else
                        ("Guide stopped. The only change was the RAM Flush. "
                         "You know where to find me :)")]
            return [("Skończyliśmy bez wprowadzania zmian, wiesz gdzie mnie szukać :)")
                    if lang == "pl" else
                    ("We stopped without changing anything. You know where to find me :)")]

        is_action = step.act is not None and not self._acted

        if is_action and word in _CONFIRM:
            flow_id = self._active
            self._ts = time.time()
            self._acted = True
            out = []
            try:
                out = step.act(rb, self._state, lang) or []
            except Exception:
                out = ["⚠ " + ("Akcja nie powiodła się - lecimy dalej."
                               if lang == "pl" else
                               "That action failed - moving on.")]
            advanced = self._advance(rb)
            state = (dict(self._completed_state) if not self.is_active()
                     else dict(self._state))
            self._last_transition = {
                "flow_id": flow_id, "event": "confirmed",
                "state": state, "completed": not self.is_active(),
            }
            return out + advanced

        if word in _NEXT or (is_action and word in _SKIP):
            flow_id = self._active
            self._ts = time.time()
            event = "skipped" if is_action and word in _SKIP else "advanced"
            out = self._advance(rb)
            state = (dict(self._completed_state) if not self.is_active()
                     else dict(self._state))
            self._last_transition = {
                "flow_id": flow_id, "event": event,
                "state": state, "completed": not self.is_active(),
            }
            return out

        if word in _CONFIRM and not is_action:
            # "tak" on a plain step just advances
            flow_id = self._active
            self._ts = time.time()
            out = self._advance(rb)
            state = (dict(self._completed_state) if not self.is_active()
                     else dict(self._state))
            self._last_transition = {
                "flow_id": flow_id, "event": "advanced",
                "state": state, "completed": not self.is_active(),
            }
            return out

        return None   # not navigation -> let normal routing answer, stay paused

    def answer_in_context(self, msg: str, rb) -> Optional[List[str]]:
        """A question while a step is open: the step's own answer plus where
        the guide stands, or None when the step has nothing to say."""
        if not self.is_active():
            return None
        flow = self._flows[self._active]
        step = flow.steps[self._step]
        if step.ask is None:
            return None
        try:
            lines = step.ask(rb, self._state, self._lang, msg)
        except Exception:
            lines = None
        if not lines:
            return None
        self._ts = time.time()
        return list(lines) + [self.waiting_line()]

    def waiting_line(self) -> str:
        n = len(self._flows[self._active].steps) if self._active else 0
        cur = self._step + 1
        if self._lang == "pl":
            return f"↪ Przewodnik czeka na kroku {cur}/{n}: 'dalej' albo 'przerwij'."
        return f"↪ The guide is waiting on step {cur}/{n}: 'next' or 'stop'."

    def current_chips(self) -> List[tuple]:
        """Quick replies for the open step: [(label, kind, payload)], kind
        'send' (types payload) or 'nav' (opens a link by name)."""
        if not self.is_active():
            return []
        pl = self._lang == "pl"
        step = self._flows[self._active].steps[self._step]
        out = []
        if step.act is not None and not self._acted:
            yes = step.yes(self._state) if callable(step.yes) else step.yes
            yes = yes or ("TAK, WYKONAJ", "YES, RUN IT")
            out += [(yes[0] if pl else yes[1], "send", "tak" if pl else "yes"),
                     ("POMIŃ" if pl else "SKIP", "send", "pomiń" if pl else "skip")]
        elif "start" in step.chips:
            out.append(("ZACZYNAJMY" if pl else "LET'S START", "send", "zaczynajmy" if pl else "start"))
        else:
            out.append(("DALEJ" if pl else "NEXT", "send", "dalej" if pl else "next"))
        for c in step.chips:
            if c.startswith("nav:"):
                name = c[4:]
                label = {"Startup Manager": ("Zobacz Autostart", "See Startup"),
                         "Services Manager": ("Zobacz Usługi", "See Services")}.get(
                             name, (name, name))
                out.append((label[0] if pl else label[1], "nav", name))
        out.append(("PRZERWIJ" if pl else "STOP", "send", "przerwij" if pl else "stop"))
        return out

    # ── internals ─────────────────────────────────────────────────────────────
    def _advance(self, rb) -> List[str]:
        flow = self._flows[self._active]
        self._step += 1
        self._acted = False
        if self._step >= len(flow.steps):
            self._completed_state = dict(self._state)
            lines = []
            if flow.finish is not None:
                try:
                    lines = flow.finish(None, self._state, self._lang) or []
                except Exception:
                    lines = []
            self.abort()
            return lines
        return self._open_step(rb)

    def _open_step(self, rb) -> List[str]:
        flow = self._flows[self._active]
        step = flow.steps[self._step]
        self._ts = time.time()
        try:
            lines = step.say(rb, self._state, self._lang) or []
        except Exception:
            lines = []
        if not lines:
            # a step with nothing to say is passed over (2026-11-17: the
            # drivers step exists only after the components were checked)
            return self._advance(rb)
        if self._step >= len(flow.steps) - 1 and step.act is None:
            # last plain step ends the flow after speaking
            self._completed_state = dict(self._state)
            self.abort()
        return lines


# ── Singleton ──────────────────────────────────────────────────────────────────
flow_engine = FlowEngine()
