"""tests.test_phase5_mypc - phase 5 of the big update (2026-11-20).

My PC: no "i" buttons, the summary card instead of "SESJA", the GAMING
page, "What slows this PC down", the health centre, Stability Tests with
OTHERS and TEST, the startup summary.
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


class TestHealthScore(unittest.TestCase):

    def test_parts_and_total(self):
        from core.health_score import score
        data = {"findings": [
            {"sev": 1, "code": "restarts", "data": {"restart": 4}},
            {"sev": 1, "code": "ram_small", "data": {"gb": 8, "avg": 75}},
            {"sev": 1, "code": "xmp_off", "data": {"mhz": 2133}},
            {"sev": 0, "code": "gpu_driver", "data": {"months": 4}},
        ], "gaming": {"gpu_temp_max": 70}, "disks": [{"name": "C", "health": "Healthy"}]}
        r = score(data)
        by = {p["key"]: p for p in r["parts"]}
        self.assertEqual(by["stability"]["score"], 70)
        self.assertEqual(by["memory"]["score"], 50)
        self.assertEqual(by["temps"]["score"], 100)
        self.assertEqual(by["drivers"]["score"], 100)
        self.assertEqual(by["drives"]["score"], 100)
        self.assertEqual(by["startup"]["score"], 100)
        self.assertEqual(r["total"], 85)
        for p in r["parts"]:
            self.assertTrue(p["go"])

    def test_nothing_known_is_not_counted_as_fine(self):
        from core.health_score import score
        r = score({"findings": [], "gaming": {}, "disks": []})
        self.assertIsNone(r["total"])
        self.assertEqual(r["parts"], [])

    def test_errors_weigh_most(self):
        from core.health_score import score
        r = score({"findings": [{"sev": 2, "code": "hw_errors", "data": {"whea": 3, "bsod": 1}}],
                   "gaming": {}, "disks": []})
        self.assertEqual(r["parts"][0]["score"], 30)


class TestGamingVerdicts(unittest.TestCase):

    def test_states_and_thermal(self):
        from ui.pages.gaming_home import verdicts
        v = verdicts({"state": {"cpu": 40, "ram": 95, "gpu": 70}, "gpu_t": (66, 72)})
        self.assertEqual(v["cpu"], "ok")
        self.assertEqual(v["ram"], "tight")
        self.assertEqual(v["gpu"], "ok")
        self.assertEqual(v["thermal"], "t_ok")
        v = verdicts({"state": {}, "gpu_t": (80, 88)})
        self.assertEqual(v["gpu"], "hot")
        self.assertEqual(v["thermal"], "t_hot")
        self.assertEqual(verdicts({"state": {}})["thermal"], "t_none")


class TestSummaryFacts(unittest.TestCase):

    def test_shape(self):
        from ui.components.pc_summary import compute_facts
        d = compute_facts("pl")
        self.assertIn("pct", d)
        self.assertIn("hours", d)
        self.assertTrue(d["facts"], "always at least one line")


class TestStabilityIntegrity(unittest.TestCase):

    def test_program_and_others(self):
        from ui.pages import stability_tests as st
        rows = st.check_all()
        groups = {g for g, *_ in rows}
        self.assertEqual(groups, {"PROGRAM", "OTHERS"})
        found = {rel: ok for _g, rel, ok, _s in rows}
        self.assertTrue(found["data/process_library.json"])
        self.assertTrue(found["locales/pl.json"])
        self.assertFalse(st.other_status("data/not_there.json")[0])


class TestSources(unittest.TestCase):

    def test_no_i_buttons_left_in_my_pc(self):
        src = _src("ui", "components", "yourpc_page.py")
        self.assertNotIn('text="i", font=(_BODY, 7, "bold")', src)

    def test_session_bar_replaced(self):
        src = _src("ui", "components", "yourpc_page.py")
        self.assertIn("build_summary_card", src)
        self.assertNotIn('my_pc.session_label', src)

    def test_hover_is_stronger(self):
        from ui.components import process_ref
        self.assertEqual(process_ref.HOVER_BG, "#31265a")


class TestPagesBuild(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        from _isolate import isolate_window_state; isolate_window_state()
        cls.win = mwe.ExpandedMainWindow(data_manager=None, monitor=None,
                                         switch_to_minimal_callback=lambda: None,
                                         quit_callback=lambda: None)
        cls.win.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _pump(self, s):
        import time
        end = time.time() + s
        while time.time() < end:
            self.win.root.update()

    def test_gaming_page_opens_from_the_tile_and_the_chat(self):
        import tkinter as tk
        from ui.components import yourpc_page as yp
        win = self.win
        win._handle_sidebar_navigation("my_pc")
        self._pump(1.0)
        yp._open_gaming_home(win)
        self._pump(1.5)
        texts = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, (tk.Label,)):
                    texts.append(str(c.cget("text")))
                walk(c)
        walk(win.yourpc_content_frame)
        self.assertTrue(any("CPU:" in t for t in texts), texts[:20])
        src = _src("ui", "windows", "main_window_expanded.py")
        self.assertIn("_yp._open_gaming_home(self)", src)

    def test_health_and_performance_tabs_build(self):
        from ui.components import yourpc_page as yp
        win = self.win
        win._handle_sidebar_navigation("my_pc")
        self._pump(0.8)
        for tab in ("health", "efficiency", "startup"):
            yp._show_tab(win, tab)
            self._pump(0.6)
            self.assertEqual(win.yourpc_active_tab, tab)


if __name__ == "__main__":
    unittest.main()
