"""tests.test_flow_engine
Wave-1 hck_GPT expansion guards: the FlowEngine (guided multi-step flows),
the master "optimize" flow with verify-after-action, and the response
ledger recall. All headless; system-touching actions are mocked.
"""
import unittest
from unittest import mock

from hck_gpt.engine import flow_engine as fe_mod
from hck_gpt.engine.flow_engine import FlowEngine, Flow, FlowStep
import hck_gpt.responses.flows as flows  # registers "optimize" on the singleton


class _FakeRB:
    PREFIX = "hck_GPT:"


def _engine_with_optimize():
    """Fresh engine wired with the real optimize flow definition."""
    eng = FlowEngine()
    eng.register(fe_mod.flow_engine._flows["optimize"])
    return eng


class TestFlowEngineCore(unittest.TestCase):

    def _mini(self):
        eng = FlowEngine()
        log = []
        eng.register(Flow("mini", [
            FlowStep(lambda rb, st, lg: ["s0"]),
            FlowStep(lambda rb, st, lg: ["ask"],
                     act=lambda rb, st, lg: log.append("ACT") or ["done"]),
            FlowStep(lambda rb, st, lg: ["end"]),
        ]))
        return eng, log

    def test_walkthrough_confirm(self):
        eng, log = self._mini()
        self.assertEqual(eng.start("mini", None, "en"), ["s0"])
        self.assertTrue(eng.is_active())
        self.assertEqual(eng.process_input("next", None), ["ask"])
        out = eng.process_input("yes", None)
        self.assertEqual(out, ["done", "end"])
        self.assertEqual(log, ["ACT"])
        self.assertFalse(eng.is_active(), "flow must end after last step")

    def test_skip_action(self):
        eng, log = self._mini()
        eng.start("mini", None, "pl")
        eng.process_input("dalej", None)
        out = eng.process_input("pomiń", None)
        self.assertEqual(out, ["end"])
        self.assertEqual(log, [], "skip must NOT run the action")

    def test_interjection_pauses_not_kills(self):
        eng, _ = self._mini()
        eng.start("mini", None, "pl")
        self.assertIsNone(eng.process_input("jaki mam procesor?", None),
                          "non-navigation must fall through to normal routing")
        self.assertTrue(eng.is_active(), "flow must stay paused, not die")
        self.assertEqual(eng.process_input("dalej", None), ["ask"])

    def test_abort_words(self):
        eng, _ = self._mini()
        eng.start("mini", None, "en")
        out = eng.process_input("stop", None)
        self.assertTrue(out and "stopped" in out[0].lower())
        self.assertFalse(eng.is_active())

    def test_ttl_expiry(self):
        eng, _ = self._mini()
        eng.start("mini", None, "pl")
        eng._ts -= (fe_mod.FLOW_TTL_S + 1)
        self.assertFalse(eng.is_active(), "abandoned flow must expire")

    def test_action_failure_still_advances(self):
        eng = FlowEngine()
        eng.register(Flow("boom", [
            FlowStep(lambda rb, st, lg: ["ask"],
                     act=lambda rb, st, lg: 1 / 0),
            FlowStep(lambda rb, st, lg: ["end"]),
        ]))
        eng.start("boom", None, "pl")
        out = eng.process_input("tak", None)
        self.assertTrue(any("end" in x for x in out))
        self.assertTrue(any("⚠" in x for x in out))


class TestOptimizeFlow(unittest.TestCase):
    """The real master flow, with psutil/flush mocked to fixed numbers."""

    def test_full_run_reports_measured_delta(self):
        eng = _engine_with_optimize()
        rb = _FakeRB()
        seq = [{"ram_pct": 82.0, "cpu_pct": 30.0, "procs": 240},   # baseline
               {"ram_pct": 80.0, "cpu_pct": 25.0, "procs": 238},   # pre-flush
               {"ram_pct": 61.0, "cpu_pct": 20.0, "procs": 231}]   # verify
        with mock.patch.object(flows, "_measure", side_effect=seq), \
             mock.patch.object(flows, "_startup_flagged",
                               return_value=(4, 19)):
            s0 = eng.start("optimize", rb, "pl")
            self.assertTrue(any("82" in x for x in s0), "baseline in step 1")
            s1 = eng.process_input("dalej", rb)
            self.assertTrue(any("4" in x and "19" in x for x in s1),
                            "startup numbers must be real")
            s2 = eng.process_input("dalej", rb)
            self.assertTrue(any("Services Manager" in x for x in s2))
            s3 = eng.process_input("dalej", rb)
            self.assertTrue(any("tak" in x or "yes" in x for x in s3))
            fake = mock.MagicMock()
            fake.flush_now.return_value = (True, "Freed 500 MB", 1000, 1500)
            with mock.patch.dict("sys.modules",
                                 {"core.auto_optimizer":
                                  mock.MagicMock(auto_optimizer=fake)}):
                s4 = eng.process_input("tak", rb)
        joined = " ".join(s4)
        self.assertIn("82", joined)
        self.assertIn("61", joined)
        self.assertIn("-21", joined, "verify must show the MEASURED delta")
        self.assertIn("500", joined, "freed MB must be reported")
        self.assertTrue(fake.flush_now.called)
        self.assertFalse(eng.is_active())

    def test_ledger_records_and_recall_answers(self):
        from hck_gpt.memory.session_memory import session_memory
        session_memory.record_response_data("optimize_guide",
                                            {"ram_before": 82, "ram_after": 61})
        recent = session_memory.last_recorded(3)
        self.assertTrue(any(i == "optimize_guide" for i, _ in recent))
        from hck_gpt.responses.builder import ResponseBuilder
        from hck_gpt.intents.parser import ParseResult
        out = ResponseBuilder()._resp_recall_numbers(
            ParseResult(intent="recall_numbers", confidence=1.0,
                        entities={}, raw_text="ile to było"), "pl")
        self.assertTrue(any("ram_before=82" in x for x in out))



class TestAILayerAlive(unittest.TestCase):
    """The responses-package split once dropped the module-level singleton -
    chat_handler swallowed the ImportError and the WHOLE AI layer was
    silently OFF (HAS_AI_LAYER=False). Never again."""

    def test_singleton_and_ai_layer(self):
        from hck_gpt.responses import response_builder  # noqa: F401
        import hck_gpt.chat_handler as ch
        self.assertTrue(ch.HAS_AI_LAYER,
                        "AI layer must be ON (singleton import failed?)")


class TestContextChain(unittest.TestCase):
    """Conversation memory (2026-07-16): every data answer auto-records its
    headline; 'wroc do tego' recalls it even after unrelated small talk."""

    def test_recall_after_smalltalk(self):
        from hck_gpt.intents.parser import IntentParser
        from hck_gpt.responses.builder import response_builder as rb
        p = IntentParser()
        self.assertTrue(rb.build(p.parse("jaka mam temperaturę"), "pl"))
        rb.build(p.parse("dzięki wielkie"), "pl")       # chit-chat between
        r = p.parse("wróć do tego")
        self.assertEqual(r.intent, "recall_numbers")
        out = " ".join(rb.build(r, "pl"))
        self.assertIn("temperature", out,
                      "earlier answer must be recallable after small talk")

    def test_smalltalk_never_pollutes_ledger(self):
        from hck_gpt.responses.builder import ResponseBuilder
        self.assertIn("small_talk", ResponseBuilder._NO_LEDGER)
        self.assertIn("greeting", ResponseBuilder._NO_LEDGER)

    def test_guidance_phrasings_reach_the_guide(self):
        from hck_gpt.intents.parser import IntentParser
        p = IntentParser()
        for msg in ("pomóż mi przyspieszyć komputer",
                    "help me optimize my pc",
                    "co mam zrobić krok po kroku"):
            self.assertEqual(p.parse(msg).intent, "optimize_guide", msg)


if __name__ == "__main__":
    unittest.main()
