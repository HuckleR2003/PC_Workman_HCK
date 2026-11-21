"""tests.test_phase4_navigation - phase 4 of the big update (2026-11-20).

  * the sidebar: My PC first; items with subitems are "split" (the name
    opens the page, the arrow opens the list); Monitoring has "All
    statistics";
  * the Optimization Center: a banner, features in groups with one colour
    each, action chips in the interface language, no typed-in counter;
  * the sidebar hides itself on the Optimization Center (a setting).
"""
import time
import unittest


class _WindowCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        from _isolate import isolate_window_state
        cls.settings_path = isolate_window_state()
        cls.win = mwe.ExpandedMainWindow(
            data_manager=None, monitor=None,
            switch_to_minimal_callback=lambda: None, quit_callback=lambda: None)
        cls.win.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _pump(self, s=0.5):
        end = time.time() + s
        while time.time() < end:
            self.win.root.update()


class TestSplitItems(_WindowCase):

    def test_name_opens_the_page_arrow_only_toggles(self):
        sb = self.win.sidebar
        calls = []
        old = sb.on_navigate
        sb.on_navigate = lambda p, s: calls.append((p, s))
        try:
            sb._handle_item_click("monitoring_alerts")
            self.assertEqual(calls, [("monitoring_alerts", None)])
            self.assertIn("monitoring_alerts", sb.expanded_categories)
            calls.clear()
            sb._toggle_category("monitoring_alerts")
            self.assertNotIn("monitoring_alerts", sb.expanded_categories)
            self.assertEqual(calls, [], "the arrow does not navigate")
        finally:
            sb.on_navigate = old

    def test_my_pc_is_the_main_button(self):
        sb = self.win.sidebar
        first = sb._nav_structure()[0]
        self.assertEqual(first["id"], "my_pc")
        self.assertTrue(first.get("primary"))
        self.assertTrue(sb.item_widgets["my_pc"]["split"])

    def test_all_statistics_opens_the_hardware_history(self):
        self.win._handle_sidebar_navigation("monitoring_alerts", "all_stats")
        self._pump(1.0)
        self.assertEqual(self.win.current_view, "activity_hardware")

    def test_rail_shows_only_the_arrow(self):
        sb = self.win.sidebar
        sb.set_back("Wróć: Mój PC", lambda: None)
        sb._auto_hide = True
        sb._collapse_sidebar()
        self.assertEqual(sb._back_lbl.cget("text"), "←")
        sb._expand_sidebar()
        self.assertIn("Mój PC", sb._back_lbl.cget("text"))
        sb._auto_hide = False


class TestOptimizationCenter(_WindowCase):

    def test_banner_groups_and_labels(self):
        import tkinter as tk
        from utils import i18n
        old = i18n.get_lang()
        i18n.set_lang("pl")
        try:
            self.win.current_view = None
            self.win._switch_to_page("optimization")
            self._pump(1.5)
            texts = []

            def walk(w):
                for c in w.winfo_children():
                    if isinstance(c, tk.Label):
                        texts.append(str(c.cget("text")))
                    walk(c)
            walk(self.win.content_area)
            for group in ("PAMIĘĆ", "PROCESOR I ZASILANIE", "USŁUGI I START", "DOWODY I PORADY"):
                self.assertIn(group, texts)
            self.assertIn("OCZYŚĆ RAM", texts)
            self.assertNotIn("ACTIVATE", texts)
            self.assertFalse(any("active" == t.split()[-1] for t in texts if t.strip()),
                             "the typed-in '2 / 16 active' counter is gone")
            self.assertIn("Przewodnik krok po kroku", texts)
        finally:
            i18n.set_lang(old)

    def test_sidebar_hides_on_this_page_only(self):
        win = self.win
        win.current_view = None
        win._switch_to_page("optimization")
        self._pump(0.3)
        self.assertTrue(win.sidebar._auto_hide)
        win.current_view = None
        win._switch_to_page("dashboard")
        self._pump(0.3)
        self.assertFalse(win.sidebar._auto_hide)

    def test_the_setting_turns_it_off(self):
        from utils.prefs_io import update_json
        win = self.win
        update_json(self.settings_path, optimization_hide_sidebar=False)
        try:
            win.current_view = None
            win._switch_to_page("optimization")
            self._pump(0.3)
            self.assertFalse(win.sidebar._auto_hide)
        finally:
            update_json(self.settings_path, optimization_hide_sidebar=True)
            win.current_view = None
            win._switch_to_page("dashboard")


class TestBannerCrumbs(_WindowCase):

    def test_crumbs_lead_to_my_pc_and_siblings(self):
        from ui.components.hero_banner import nav_crumbs
        win = self.win
        crumbs = nav_crumbs(win, "Centrum optymalizacji", [("Autostart", "startup_manager")])
        labels = [c[0] if c else None for c in crumbs]
        self.assertEqual(labels[2], None, "a divider before where you are")
        self.assertTrue(crumbs[3][2], "the current page is marked")
        self.assertIsNone(crumbs[3][1], "and not clickable")
        crumbs[-1][1]()
        self._pump(0.8)
        self.assertEqual(win.current_view, "startup_manager")
        crumbs[0][1]()
        self._pump(0.8)
        self.assertEqual(win.active_overlay or win.current_view, "your_pc")


class TestNoUnreadyFeatureInAnswers(unittest.TestCase):

    def test_slow_internet_answer(self):
        # 2026-11-20: the answer is the network guide; it tests first, and on
        # a DNS fault offers the flush (measurement replaced, no network)
        from unittest import mock
        from core import net_check
        from hck_gpt.engine.flow_engine import flow_engine
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        fault = {"ts": 0, "target": "google.com", "adapter": {"kind": None}, "gateway": "192.168.1.1",
                 "gw": {"sent": 3, "lost": 0, "avg": 2.0, "min": 1.0, "max": 3.0, "jitter": 1.0},
                 "dns_ip": None, "dns_ms": None, "web": None, "tcp_ms": None,
                 "raw": {"sent": 2, "lost": 0, "avg": 18.0, "min": 17.0, "max": 19.0, "jitter": 1.0}}
        try:
            with mock.patch.object(net_check, "check", return_value=fault), \
                 mock.patch("hck_gpt.responses.r_network._traffic_mbps", return_value=(0.1, 0.1)):
                out = "\n".join(response_builder.build(
                    ParseResult("network_slow", 1.0, raw_text="mam wolny internet"), "pl"))
        finally:
            flow_engine.abort()
        self.assertNotIn("Network Adapter Reset", out)
        self.assertIn("ipconfig /flushdns", out)


if __name__ == "__main__":
    unittest.main()
