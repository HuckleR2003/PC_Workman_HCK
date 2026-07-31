"""Regression tests for the 2026-07 hck_GPT context and guidance upgrade."""
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from hck_gpt.engine.flow_engine import FlowEngine
from hck_gpt.intents.parser import IntentParser, ParseResult
from hck_gpt.memory.session_memory import SessionMemory
from hck_gpt.responses.builder import ResponseBuilder
import hck_gpt.responses.flows as flows


class TestConversationalReferences(unittest.TestCase):

    def setUp(self):
        self.mem = SessionMemory()
        self.parser = IntentParser()

    @staticmethod
    def _result(intent, raw):
        return ParseResult(intent=intent, confidence=1.0,
                           entities={}, raw_text=raw)

    def test_gpu_pronoun_temperature_followup(self):
        self.mem.remember_turn(
            self._result("hw_gpu", "jaki mam gpu"),
            ["hck_GPT: GPU: test"],
        )
        resolved = self.mem.resolve_followup(
            "a jego temperatura?", self.parser.parse("a jego temperatura?"))
        self.assertEqual(resolved.intent, "gpu_temp_why")

    def test_process_pronoun_keeps_exact_executable(self):
        self.mem.remember_turn(
            self._result("process_identity", "co to discord.exe"),
            ["hck_GPT: Discord"],
        )
        resolved = self.mem.resolve_followup(
            "czy mogę go zamknąć?",
            self.parser.parse("czy mogę go zamknąć?"),
        )
        self.assertEqual(resolved.intent, "process_kill")
        self.assertIn("discord.exe", resolved.raw_text)

    def test_part_pronoun_keeps_full_variant(self):
        self.mem.remember_turn(
            self._result(
                "upgrade_compat",
                "sprawdź Intel Core Ultra 5 250KF Plus",
            ),
            ["hck_GPT: część"],
        )
        resolved = self.mem.resolve_followup(
            "czy będzie pasować?",
            self.parser.parse("czy będzie pasować?"),
        )
        self.assertEqual(resolved.intent, "upgrade_compat")
        self.assertIn("ultra 5 250kf plus", resolved.raw_text.lower())

    def test_ambiguous_tech_word_keeps_conversation_language(self):
        from hck_gpt.intents.lang_detect import detect_language
        self.assertEqual(detect_language("cpu", fallback="en"), "en")
        self.assertEqual(detect_language("cpu", fallback="pl"), "pl")
        self.assertEqual(detect_language("hej, check my RAM"), "pl")


class TestGuidedFlows(unittest.TestCase):

    def _engine(self, flow_id):
        eng = FlowEngine()
        eng.register(flows.flow_engine._flows[flow_id])
        return eng

    def test_cooling_flow_marks_estimate_and_does_not_fake_delta(self):
        estimate = {
            "cpu_temp": 72.0, "cpu_temp_src": "est", "gpu_temp": 60.0,
            "cpu_load": 20.0, "gpu_load": 5.0, "ram_pct": 50.0,
            "top_name": "chrome.exe", "top_cpu": 2.0, "top_ram_mb": 600.0,
        }
        eng = self._engine("cooling")
        with mock.patch.object(flows, "_thermal_measure",
                               side_effect=[estimate, estimate, estimate]):
            first = eng.start("cooling", None, "en")
            self.assertTrue(any("estimated" in line.lower()
                                for line in first))
            eng.process_input("next", None)
            eng.process_input("next", None)
            last = eng.process_input("next", None)
        self.assertTrue(any("not invent" in line.lower() for line in last))
        self.assertFalse(eng.is_active())

    def test_desktop_flow_uses_initial_symptom_and_never_runs_action(self):
        eng = self._engine("desktop_repair")
        with mock.patch.object(
                flows, "_desktop_state",
                return_value={"explorer": True, "dwm": True,
                              "top_name": "", "top_cpu": 0.0}):
            first = eng.start(
                "desktop_repair", None, "en",
                initial_state={"raw_text": "black screen with cursor"},
            )
            second = eng.process_input("next", None)
        self.assertTrue(any("black screen" in line.lower() for line in first))
        self.assertTrue(any("windows explorer" in line.lower()
                            and "restart" in line.lower() for line in second))

    def test_upgrade_plan_marks_unknowns_instead_of_guessing(self):
        data = {
            "platform": {
                "cpu_name": "Ryzen 5 5600X", "gpu_name": "RTX 3060",
                "socket": "AM4", "chipset": "B550", "ram_type": "DDR4",
                "ram_actual": "DDR4", "board": "B550 TEST",
            },
            "summary": {}, "temps": {},
        }
        eng = self._engine("upgrade_plan")
        with mock.patch.object(flows, "_upgrade_snapshot",
                               return_value=data):
            eng.start("upgrade_plan", None, "en")
            evidence = eng.process_input("next", None)
            compat = eng.process_input("next", None)
        self.assertTrue(any("history is still too short" in x.lower()
                            for x in evidence))
        self.assertTrue(any("psu and case" in x.lower() for x in compat))


class TestSafetyAndProactivity(unittest.TestCase):

    def test_explorer_is_described_as_windows_not_anticheat(self):
        out = ResponseBuilder()._resp_process_kill(
            ParseResult("process_kill", 1.0, raw_text="close explorer.exe"),
            "en",
        )
        joined = " ".join(out).lower()
        self.assertIn("windows", joined)
        self.assertNotIn("anti-cheat", joined)

    def test_contextual_tip_aggregates_browser_processes(self):
        mem1 = SimpleNamespace(rss=300 * 1_048_576)
        mem2 = SimpleNamespace(rss=250 * 1_048_576)
        procs = [
            SimpleNamespace(info={
                "name": "chrome.exe", "cpu_percent": 4.0,
                "memory_info": mem1,
            }),
            SimpleNamespace(info={
                "name": "chrome.exe", "cpu_percent": 2.0,
                "memory_info": mem2,
            }),
        ]
        from hck_gpt.memory.proactive_monitor import ProactiveMonitor
        mon = ProactiveMonitor()
        mon.set_language("en")
        fake_psutil = SimpleNamespace(
            process_iter=lambda *a, **k: procs,
            cpu_count=lambda **k: 8,
        )
        with mock.patch.dict(sys.modules, {"psutil": fake_psutil}):
            msg, meta = mon._contextual_idle_tip(12.0, 48.0)
        self.assertIn("550 MB", msg)
        self.assertEqual(meta["process"], "chrome.exe")
        self.assertEqual(meta["process_ram_mb"], 550)


class TestReversibleServiceState(unittest.TestCase):

    def test_restore_uses_original_start_type(self):
        from hck_gpt.services_manager import ServicesManager
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "services.json")
            mgr = ServicesManager(path)
            mgr.is_windows = True
            with mock.patch.object(
                    mgr, "get_service_start_type", return_value="auto"), \
                 mock.patch.object(
                    mgr, "get_service_status", return_value="Running"), \
                 mock.patch.object(
                    mgr, "disable_service",
                    return_value=(True, "disabled")):
                ok, _ = mgr.apply_optimization("printer", True)
            self.assertTrue(ok)
            self.assertEqual(
                mgr.disabled_services["original_start_types"]["Spooler"],
                "auto",
            )
            with mock.patch.object(
                    mgr, "enable_service",
                    return_value=(True, "restored")) as enable, \
                 mock.patch.object(
                    mgr, "start_service",
                    return_value=(True, "started")) as start:
                mgr.restore_all_services()
            enable.assert_called_once_with("Spooler", "auto")
            start.assert_called_once_with("Spooler")
            self.assertEqual(mgr.disabled_services["disabled"], [])

    def test_partial_service_failure_is_not_reported_as_success(self):
        from hck_gpt.services_manager import ServicesManager
        with tempfile.TemporaryDirectory() as td:
            mgr = ServicesManager(os.path.join(td, "services.json"))
            mgr.is_windows = True
            with mock.patch.object(
                    mgr, "get_service_start_type", return_value="demand"), \
                 mock.patch.object(
                    mgr, "get_service_status", return_value="Stopped"), \
                 mock.patch.object(
                    mgr, "disable_service",
                    side_effect=[(True, "ok"), (False, "fail")]):
                ok, results = mgr.apply_optimization("bluetooth", True)
            self.assertFalse(ok)
            self.assertEqual([row[1] for row in results], [True, False])


class TestCurrentHardwareLibrary(unittest.TestCase):

    def test_2026_intel_desktop_parts_and_chipsets(self):
        from core import hardware_compat as hc
        self.assertEqual(
            hc.identify_cpu("Core Ultra 7 270K Plus")["key"],
            "ultra 7 270k plus",
        )
        self.assertEqual(
            hc.identify_cpu("Core Ultra 5 225F")["igpu"], False)
        self.assertEqual(hc.chipset_from_board("PRO WS W880-ACE"), "W880")
        self.assertGreaterEqual(hc.db_stats()["total"], 349)


if __name__ == "__main__":
    unittest.main()
