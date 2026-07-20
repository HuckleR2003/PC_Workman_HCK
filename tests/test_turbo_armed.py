"""tests.test_turbo_armed
Quick Actions TURBO panel (2026-07-18): the X/N display and the master
switch must agree on which features fire on TURBO.

Audit findings this guards against coming back:
  - the RAM card's ON TURBO pill was drawn but never bound (clicking did
    nothing, ram_on_turbo could never be set from the UI)
  - hibernation turbo behaviors fired only inside tpp_activate, so with
    TPP-on-TURBO off they were dead on the master switch
  - the master switch never touched the TURBO Services profile at all
"""
import inspect
import unittest


class TestTurboArmed(unittest.TestCase):

    def test_summary_shape(self):
        from ui.pages.optimization_services import turbo_armed_summary
        s = turbo_armed_summary()
        self.assertGreaterEqual(len(s), 4)
        for name, armed in s:
            self.assertIsInstance(name, str)
            self.assertIsInstance(armed, bool)
        names = [n for n, _ in s]
        for expected in ("Turbo Power Plan", "RAM Flush",
                         "Service Stop", "App Hibernation"):
            self.assertIn(expected, names)

    def test_master_switch_covers_all_armed_features(self):
        """set_turbo_active must reference every feature the summary counts -
        a counter that promises more than the switch delivers is a lie."""
        from ui.pages import optimization_services as osvc
        src = inspect.getsource(osvc.set_turbo_active)
        self.assertIn("tpp_on_turbo", src)
        self.assertIn("apply_turbo_behaviors", src)
        self.assertIn("stop_profile", src)
        # RAM-on-TURBO reaches the daemon via _set_turbo_flag -> set_turbo
        flag_src = inspect.getsource(osvc._set_turbo_flag)
        self.assertIn("set_turbo", flag_src)

    def test_daemon_has_ram_on_turbo_setter(self):
        from core.auto_optimizer import auto_optimizer
        self.assertTrue(hasattr(auto_optimizer, "set_ram_on_turbo"))
        auto_optimizer.set_ram_on_turbo(True)
        self.assertTrue(auto_optimizer._ram_on_turbo)
        auto_optimizer.set_ram_on_turbo(False)
        self.assertFalse(auto_optimizer._ram_on_turbo)

    def test_ram_turbo_pill_is_bound(self):
        """The pill must be wired: source check that _wire_ram_flush binds it."""
        from ui.pages import optimization_services as osvc
        src = inspect.getsource(osvc._wire_ram_flush)
        self.assertIn("turbo_pill.bind", src)
        self.assertIn("ram_on_turbo", src)


if __name__ == "__main__":
    unittest.main()
