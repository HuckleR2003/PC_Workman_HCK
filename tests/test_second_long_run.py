"""Fixes after the second long test and the 122-question sweep (2026-11-17).

- the chat input never leaves the panel, whatever strips are shown
- answers in parts (§PAUSE), highlighted lines (§NOTE), the guide offer
- the optimization guide: 6 steps, components and drivers at the end
- virtual memory: read, described, directions only when asked
- learning: one refold from minute rows, rare workloads do not drag the %
- laptop / desktop statements no longer eat "my pc is slow"
- everyday questions that ended in "I did not understand"
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class TestMachineTypeStatement(unittest.TestCase):

    def test_only_real_statements(self):
        from core.machine_type import from_message, statement_only
        for q in ("my pc is slow", "is my pc fine", "what did you learn about my pc",
                  "co mam w pc", "pc workman to fajny program"):
            self.assertIsNone(from_message(q), q)
        self.assertEqual(from_message("Dzieki, jak cos mam PC"), "desktop")
        self.assertEqual(from_message("I have a laptop"), "laptop")
        self.assertTrue(statement_only("Dzieki, jak cos mam PC"))
        self.assertFalse(statement_only("mam laptopa i strasznie sie grzeje"))


class TestPagefile(unittest.TestCase):

    def test_parse_modes(self):
        from core.pagefile import _parse
        self.assertEqual(_parse(["?:\\pagefile.sys"])[0], "auto")
        self.assertEqual(_parse([])[0], "none")
        self.assertEqual(_parse(["c:\\pagefile.sys 0 0"])[0], "system")
        mode, drives = _parse(["c:\\pagefile.sys 3072 4096", "d:\\pagefile.sys 0 0"])
        self.assertEqual(mode, "custom")
        self.assertEqual([d["drive"] for d in drives], ["C:", "D:"])

    def test_describe(self):
        from core.pagefile import describe
        self.assertIn("wyłączona", describe("pl", {"mode": "none", "size_gb": 0, "drives": []}))
        self.assertIn("Windows", describe("pl", {"mode": "auto", "size_gb": 4.0, "drives": []}))


class TestComponentCheck(unittest.TestCase):

    def test_placeholder_driver_dates_are_ignored(self):
        from core.component_check import _parse_date, _nvidia_version
        self.assertIsNone(_parse_date("7-18-1968"), "Intel INF placeholder date")
        self.assertEqual(_parse_date("7-22-2026").year, 2026)
        self.assertEqual(_nvidia_version("32.0.16.1088"), "610.88")

    def test_load_verdicts(self):
        from core.component_check import load_verdict
        self.assertIn("dużo wolnej mocy", load_verdict(
            {"has_data": True, "avg": 10, "p95": 30, "recorded_hours": 5,
             "high_load_minutes": 0}, "pl", "cpu"))
        self.assertIn("ciężko", load_verdict(
            {"has_data": True, "avg": 80, "p95": 99, "recorded_hours": 5,
             "high_load_minutes": 200}, "pl", "cpu"))
        self.assertIn("zbiera", load_verdict({"has_data": False}, "pl", "cpu"))


class TestGuideEnd(unittest.TestCase):
    """Never confirms step 4 (RAM flush on the machine running the tests)."""

    def setUp(self):
        from hck_gpt.engine.flow_engine import flow_engine
        flow_engine.abort()
        from hck_gpt.chat_handler import ChatHandler
        self.h = ChatHandler()

    def tearDown(self):
        from hck_gpt.engine.flow_engine import flow_engine
        flow_engine.abort()

    def test_skip_components_ends_the_guide(self):
        h = self.h
        h.process_message("zoptymalizuj komputer", ui_lang="pl")
        h.process_message("zaczynajmy", ui_lang="pl")
        h.process_message("dalej", ui_lang="pl")
        h.process_message("dalej", ui_lang="pl")
        step5 = h.process_message("pomiń", ui_lang="pl")
        self.assertTrue(any("5/6" in x for x in step5), step5)
        self.assertTrue(any(x.startswith("§NOTE ") and "komponenty" in x for x in step5))
        self.assertEqual([c[0] for c in h.suggestions()][:2], ["TAK, SPRAWDŹ", "POMIŃ"])
        end = h.process_message("pomiń", ui_lang="pl")
        self.assertTrue(any("Przewodnik zakończony" in x for x in end), end)
        from hck_gpt.engine.flow_engine import flow_engine
        self.assertFalse(flow_engine.is_active())

    def test_pointing_question_on_a_step_is_answered_there(self):
        h = self.h
        h.process_message("zoptymalizuj komputer", ui_lang="pl")
        h.process_message("zaczynajmy", ui_lang="pl")
        out = h.process_message("co to za aplikacje", ui_lang="pl")
        self.assertTrue(out[-1].startswith("↪"), out)
        self.assertNotIn("proaktywny", " ".join(out))


class TestOfferAndVirtualMemoryHelp(unittest.TestCase):

    def test_offer_moves_to_the_end_with_a_button(self):
        from hck_gpt.chat_handler import ChatHandler
        h = ChatHandler()
        out = h._place_offer(["a", "§OFFER optimize", "b", "[-> Poradnik: x]"], "pl")
        self.assertEqual(out[-1][:6], "§NOTE ")
        self.assertEqual(out[-2], "")
        self.assertNotIn("§OFFER optimize", out)
        self.assertEqual(h.suggestions()[0][0], "ZACZNIJ PRZEWODNIK")

    def test_directions_only_right_after_the_window_opened(self):
        from hck_gpt.chat_handler import ChatHandler
        h = ChatHandler()
        h.offer_vm_help()
        self.assertEqual(h.suggestions()[0][0], "Gdzie to znajdę?")
        out = h.process_message("gdzie to znajdę?", ui_lang="pl")
        self.assertIn("Wydajność", " ".join(out))
        again = h.process_message("gdzie to znajdę?", ui_lang="pl")
        self.assertNotIn("Wydajność kliknij", " ".join(again))


class TestLearningPercent(unittest.TestCase):

    def test_rare_workloads_do_not_drag_it_down(self):
        from core.thermal_baseline import ThermalBaseline
        tb = ThermalBaseline.__new__(ThermalBaseline)
        import threading
        tb._lock = threading.Lock()
        acc = lambda n: {"gpu_temp": {"n": n, "mean": 45.0, "M2": 10.0}}
        tb._raw = {"buckets": {"idle": acc(135), "light": acc(159), "medium": acc(1),
                               "heavy": acc(1), "gaming": acc(68)}}
        self.assertGreaterEqual(tb.overall_training_pct("gpu_temp"), 60)


class TestEverydayRouting(unittest.TestCase):
    CASES = {
        "czy mam lagi": "why_slow",
        "pamięć wirtualna": "virtual_memory",
        "jak zwiększyć pamięć wirtualną": "virtual_memory",
        "kiedy komputer był najbardziej obciążony": "history_peak",
        "czy komputer spał": "history_sleep",
        "w co najwięcej grałem": "history_games",
        "porównaj dzisiaj z wczoraj": "history_compare_days",
        "co mogę zamknąć": "closable_apps",
        "niebieski ekran": "restart_check",
        "komputer sam się restartuje": "restart_check",
        "monitor 144hz pokazuje 60": "refresh_rate",
        "czy xmp jest włączony": "xmp_check",
        "dźwięk trzeszczy": "audio_crackle",
        "jak wyłączyć telemetrie": "privacy_data",
        "zrób mi optymalizację": "optimize_guide",
        "gdzie jest optymalizacja": "where_page",
        "nic nie działa": "vague_problem",
        "fps drops in games": "fps_degradation",
        "co to msmpeng": "process_identity",
    }

    def test_routes(self):
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier.load_or_train()
        from hck_gpt.intents.parser import intent_parser
        bad = [(q, intent_parser.parse(q).intent, want) for q, want in self.CASES.items()
               if intent_parser.parse(q).intent != want]
        self.assertEqual(bad, [])

    def test_gta6_is_not_gta5(self):
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        out = response_builder.build(ParseResult("game_can_run", 0.9,
                                                 raw_text="czy pociągnie gta 6"), "pl")
        self.assertIn("GTA 6", out[0])


class TestChatInputStaysInThePanel(unittest.TestCase):
    """Second long test: with a TIP shown the input row and SEND were pushed
    out of the panel (the log was packed first and took the height)."""

    def test_input_row_survives_tip_and_hot(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        try:
            root.geometry("1100x420")
            from hck_gpt.panel import HCKGPTPanel
            p = HCKGPTPanel(root, 1100, collapsed_h=34, expanded_h=230)
            p.open()
            for _ in range(60):
                root.update()
            p._insert_tip("hck_GPT: 💡 Opera trzyma teraz 1205 MB RAM. To obserwacja, nie alarm.")
            p._set_hot("RAM 95% - system pod presją")
            for _ in range(30):
                root.update()
            fy, fh = p.frame.winfo_rooty(), p.frame.winfo_height()
            ey, eh = p._entry_container.winfo_rooty(), p._entry_container.winfo_height()
            self.assertTrue(p._entry_container.winfo_ismapped())
            self.assertGreater(eh, 20)
            self.assertLessEqual(ey + eh, fy + fh + 1, "input row below the panel's edge")
            # the strips hang under the banner, above the control bar
            self.assertLess(p._tip_strip.winfo_rooty(), p._control_bar.winfo_rooty())
        finally:
            root.destroy()



def tearDownModule():
    # this module loads the ML classifier; later modules (the vocabulary
    # self-consistency check) expect the phrase tables alone (2026-11-17)
    try:
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier._ready = False
        ml_classifier._model = None
    except Exception:
        pass

if __name__ == "__main__":
    unittest.main()
