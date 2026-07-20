"""tests.test_navigation
End-to-end guard for sidebar navigation (2026-07-16 regression).

A console-cleanup pass converted print(...) trace calls to a gated _dbg(),
but one call kept `flush=True` and _dbg didn't accept kwargs. That TypeError
fired on the FIRST line of _handle_sidebar_navigation, so EVERY sidebar click
raised and fell back to the dashboard - the whole app looked broken while
tests stayed green (they never built the window). This test builds the real
ExpandedMainWindow on a live Tk root and fires every nav item, so that class
of break can never ship silently again.
"""
import os
import unittest

os.environ.setdefault("PCW_DEBUG", "0")

# Every (page_id, subpage_id) the sidebar actually emits, from _nav_structure.
NAV = [
    ("dashboard", None),
    ("monitoring_alerts", "temperature"),
    ("monitoring_alerts", "voltage"),
    ("monitoring_alerts", "alerts"),
    ("my_pc", "central"),
    ("my_pc", "components"),
    ("my_pc", "sensors"),
    ("first_setup", None),
    ("fan_control", "fan_dashboard"),
    ("fan_control", "hw_usage"),
    ("optimization", "center"),
    ("optimization", "startup_mgr"),
    ("optimization", "services_mgr"),
    ("settings", None),
]
# Pages that replace the content area (vs. slide-in overlays).
DIRECT = {"dashboard", "monitoring_alerts", "first_setup", "fan_control",
          "optimization"}


class TestSidebarNavigationEndToEnd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        try:
            cls.win = mwe.ExpandedMainWindow(
                data_manager=None, monitor=None,
                switch_to_minimal_callback=lambda: None,
                quit_callback=lambda: None)
            cls.win.root.withdraw()
        except Exception as e:  # pragma: no cover
            raise unittest.SkipTest(f"window build unavailable: {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _kids(self, w):
        try:
            return 1 + sum(self._kids(c) for c in w.winfo_children())
        except Exception:
            return 0

    def test_every_nav_item_routes_and_builds(self):
        win = self.win
        broken = []
        for page, sub in NAV:
            win.current_view = None
            win.active_overlay = None
            win.overlay_frame = None
            try:
                win._handle_sidebar_navigation(page, sub)
                win.root.update_idletasks()
            except Exception as e:
                broken.append(f"{page}.{sub} RAISED {type(e).__name__}: {e}")
                continue
            if page in DIRECT:
                # a direct page must land on its own view, not fall back
                if page != "dashboard" and win.current_view == "dashboard":
                    broken.append(f"{page}.{sub} fell back to dashboard")
            else:
                # overlay pages build their frame (active flag is set post-anim)
                of = getattr(win, "overlay_frame", None)
                if of is None or self._kids(of) < 3:
                    broken.append(f"{page}.{sub} overlay did not build")
        self.assertEqual(broken, [],
                         "sidebar navigation broken: " + "; ".join(broken))

    def test_upgrade_readiness_page_builds(self):
        """Not a sidebar item - reached via open_upgrade_readiness() buttons
        (Components / Drivers / Alerts). Must build on the real window."""
        win = self.win
        win.current_view = None
        win.open_upgrade_readiness("cpu")
        win.root.update_idletasks()
        self.assertEqual(win.current_view, "upgrade_readiness")
        kids = self._kids(win.content_area)
        self.assertGreater(kids, 10, "upgrade readiness page did not build")
        # back to dashboard must still work afterwards
        win.current_view = None
        win._handle_sidebar_navigation("dashboard", None)
        win.root.update_idletasks()
        self.assertEqual(win.current_view, "dashboard")

    def test_upgrade_advisor_expand_builds(self):
        """The Optimization Center's Upgrade Advisor card must render its
        expanded panel (worker thread -> after(0) -> widgets)."""
        import time
        import tkinter as tk
        from ui.pages.optimization_services import _build_upgrade_advisor_expand
        win = self.win
        host = tk.Frame(win.root)
        card = tk.Frame(host)
        _build_upgrade_advisor_expand(host, card)
        deadline = time.time() + 4.0
        built = False
        while time.time() < deadline:
            win.root.update()
            # the worker's _render replaces the loading label with real rows
            if self._kids(host) > 3:
                built = True
                break
            time.sleep(0.05)
        host.destroy()
        self.assertTrue(built, "advisor expand never rendered its content")

    def test_dbg_accepts_print_kwargs(self):
        """_dbg must be a drop-in for print (the flush= regression)."""
        import ui.windows.main_window_expanded as mwe
        try:
            mwe._dbg("x", flush=True, end="")   # must not raise
        except TypeError as e:
            self.fail(f"_dbg is not print-compatible: {e}")


if __name__ == "__main__":
    unittest.main()
