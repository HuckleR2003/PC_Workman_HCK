"""tests.test_mypc_perf
My PC responsiveness guards (2026-07-18).

Two fixes this locks in:
  1. Phase 1 - a full-cover overlay must NOT build the dashboard underneath
     just to cover it (was ~26% of entry cost).
  2. No blocking `wmic` on the UI thread inside the My PC build path - two
     3 s-timeout `wmic` calls (cpu name, disk models) were the main cause of
     "My PC loads forever" on Win11 24H2, where wmic is slow/deprecated. The
     names come from the warmed hardware_detector instead.
"""
import inspect
import unittest


class TestNoBlockingWmicInBuild(unittest.TestCase):

    def test_build_hey_user_table_has_no_wmic(self):
        import ui.components.yourpc_page as yp
        src = inspect.getsource(yp._build_hey_user_table)
        # strip comments so our explanatory notes about the OLD wmic don't
        # trip the guard - we only care about executable code
        code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
        self.assertNotIn('"wmic"', code,
                         "blocking wmic back in the My PC build path")
        self.assertNotIn("_sp.run", code,
                         "subprocess.run back in the My PC build path")

    def test_cpu_name_reads_warmed_identity(self):
        import ui.components.yourpc_page as yp
        src = inspect.getsource(yp._build_hey_user_table)
        self.assertIn("hardware_detector", src)
        self.assertIn("live_sensors", src)


class TestPhase1SkipsDashboard(unittest.TestCase):

    def test_full_cover_helper(self):
        from ui.windows.main_window_expanded import ExpandedMainWindow as E
        self.assertTrue(E._overlay_full_cover("your_pc"))
        self.assertTrue(E._overlay_full_cover("sensors"))
        self.assertFalse(E._overlay_full_cover("settings"))

    def test_sidebar_overlay_path_skips_build_when_no_dashboard(self):
        from ui.windows.main_window_expanded import ExpandedMainWindow as E
        src = inspect.getsource(E._handle_sidebar_navigation)
        # the old unconditional _switch_to_page("dashboard") must be gone
        self.assertNotIn('_switch_to_page("dashboard")\n\n            self._show_overlay',
                         src)
        self.assertIn("_dashboard_present", src)


class TestPhase2KeepAlive(unittest.TestCase):
    """Phase 2 (2026-07-18): My PC is built ONCE and kept alive - re-entry
    re-places the same frame (measured 346 ms build -> 1-17 ms cached)."""

    @classmethod
    def setUpClass(cls):
        import os
        import tkinter as tk
        os.environ.setdefault("PCW_DEBUG", "0")
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        cls.win = mwe.ExpandedMainWindow(
            data_manager=None, monitor=None,
            switch_to_minimal_callback=lambda: None,
            quit_callback=lambda: None)
        cls.win.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _pump(self, ms=350):
        import time
        end = time.time() + ms / 1000
        while time.time() < end:
            self.win.root.update()

    def test_cached_reentry_reuses_the_same_frame(self):
        win = self.win
        win._handle_sidebar_navigation("optimization", "center")
        win._handle_sidebar_navigation("my_pc", "central")
        self._pump()
        f1 = win.overlay_frame
        self.assertIs(win._overlay_cache.get("your_pc"), f1)
        # leave via a direct page: the kept frame must SURVIVE the content wipe
        win._handle_sidebar_navigation("monitoring_alerts", "temperature")
        self.assertTrue(f1.winfo_exists(),
                        "keep-alive frame destroyed by the content wipe")
        win._handle_sidebar_navigation("my_pc", "central")
        self._pump()
        self.assertIs(win.overlay_frame, f1, "cached frame was not reused")

    def test_invalidate_drops_cache_and_rebuild_works(self):
        win = self.win
        win._handle_sidebar_navigation("my_pc", "central")
        self._pump()
        win._handle_sidebar_navigation("dashboard")
        win._invalidate_keepalive()
        self.assertEqual(len(win._overlay_cache), 0)
        win._handle_sidebar_navigation("my_pc", "central")
        self._pump()
        self.assertIsNotNone(win.overlay_frame)
        self.assertTrue(win.overlay_frame.winfo_exists())

    def test_deep_link_honored_on_cached_reentry(self):
        win = self.win
        win._handle_sidebar_navigation("my_pc", "central")
        self._pump()
        win._handle_sidebar_navigation("dashboard")
        win._handle_sidebar_navigation("my_pc", "components")
        self._pump()
        self.assertEqual(win.yourpc_active_tab, "components")

    def test_refresh_loops_are_visibility_aware(self):
        import ui.components.yourpc_page as yp
        src = inspect.getsource(yp)
        self.assertGreaterEqual(src.count("winfo_viewable()"), 3,
                                "keep-alive loops must idle while hidden")

    def test_tab_cache_keeps_only_audited_tabs(self):
        import ui.components.yourpc_page as yp
        self.assertEqual(yp._KEEPALIVE_TABS,
                         frozenset({"central", "components", "map"}))


if __name__ == "__main__":
    unittest.main()
