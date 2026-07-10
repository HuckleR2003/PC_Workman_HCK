"""tests.test_auto_optimizer
Regression tests for the Turbo Power Plan migration (2026-07-10).

The old page-bound `_tpp_monitor_loop` spawned a NEW infinite thread on every
Optimization-page visit, each polling a destroyed widget's winfo_exists() from
a background thread every 5 s. N leaked threads hammering Tcl deadlocked the
interpreter: process alive in Task Manager, UI frozen - the tester's exact
report. TPP now lives in core.auto_optimizer (ONE daemon, no widgets).

powercfg primitives are mocked - these tests must never switch a real
power plan on the machine running them.
"""
import threading
import unittest
from unittest import mock

import core.auto_optimizer as ao


def _fresh_optimizer():
    """A private AutoOptimizer instance (not the singleton)."""
    return ao.AutoOptimizer()


class TestTppReconcile(unittest.TestCase):
    """The daemon-side reconcile must mirror the old monitor's behavior."""

    def setUp(self):
        self.opt = _fresh_optimizer()
        self.opt._tpp_auto = True
        self.opt._tpp_on_turbo = True
        self.calls = []
        # fake powercfg layer - record calls, never touch the system
        self.p_admin  = mock.patch.object(ao, "_is_admin", lambda: True)
        self.p_active = mock.patch.object(ao, "_pp_active_guid",
                                          lambda: "ORIG-GUID")
        self.p_list   = mock.patch.object(ao, "_pp_list",
                                          lambda: {"Turbo PC": "TURBO-GUID"})
        self.p_set    = mock.patch.object(ao, "_pp_set",
                                          lambda g: self.calls.append(g) or True)
        for p in (self.p_admin, self.p_active, self.p_list, self.p_set):
            p.start()
            self.addCleanup(p.stop)

    def test_turbo_on_activates_plan(self):
        with mock.patch.object(ao, "_load_prefs_full",
                               lambda: {"turbo_active": True}):
            self.opt._tpp_tick()
        self.assertTrue(self.opt.tpp_is_active())
        self.assertEqual(self.calls, ["TURBO-GUID"])

    def test_turbo_off_restores_original(self):
        with mock.patch.object(ao, "_load_prefs_full",
                               lambda: {"turbo_active": True}):
            self.opt._tpp_tick()
        with mock.patch.object(ao, "_load_prefs_full",
                               lambda: {"turbo_active": False}):
            self.opt._tpp_tick()
        self.assertFalse(self.opt.tpp_is_active())
        self.assertEqual(self.calls, ["TURBO-GUID", "ORIG-GUID"])

    def test_tick_idempotent_no_flapping(self):
        """Repeated ticks with an unchanged flag must not re-run powercfg."""
        with mock.patch.object(ao, "_load_prefs_full",
                               lambda: {"turbo_active": True}):
            for _ in range(5):
                self.opt._tpp_tick()
        self.assertEqual(self.calls, ["TURBO-GUID"])

    def test_gating_requires_auto_and_on_turbo(self):
        """No reconcile when either pill is off (old monitor semantics)."""
        self.opt._tpp_auto = False
        with mock.patch.object(ao, "_load_prefs_full",
                               lambda: {"turbo_active": True}):
            self.opt._tpp_tick()
        self.assertEqual(self.calls, [])

    def test_no_admin_no_switch(self):
        with mock.patch.object(ao, "_is_admin", lambda: False), \
             mock.patch.object(ao, "_load_prefs_full",
                               lambda: {"turbo_active": True}):
            self.opt._tpp_tick()
        self.assertFalse(self.opt.tpp_is_active())
        self.assertEqual(self.calls, [])


class TestSingleDaemonNoAccumulation(unittest.TestCase):
    """The freeze class: N page visits must NOT mean N monitor threads."""

    def test_start_is_idempotent(self):
        opt = _fresh_optimizer()
        before = threading.active_count()
        for _ in range(5):          # 5 "visits"
            opt.start()
        after = threading.active_count()
        self.assertLessEqual(after - before, 1,
                             "start() spawned more than one daemon thread")
        opt.stop()

    def test_ui_module_has_no_monitor_loop(self):
        """The page must never again own a TPP polling loop."""
        import inspect
        import ui.pages.optimization_services as opt_page
        src = inspect.getsource(opt_page)
        self.assertNotIn("_tpp_monitor_loop", src)
        self.assertNotIn('_TPP["stop_flag"]', src)


class TestStatusListenerRouting(unittest.TestCase):
    """RAM and TPP cards must not receive each other's status messages."""

    def test_kind_routing(self):
        opt = _fresh_optimizer()
        ram_msgs, tpp_msgs = [], []
        opt.register_status_listener(ram_msgs.append, kind="ram")
        opt.register_status_listener(tpp_msgs.append, kind="tpp")
        opt._emit("freed 500 MB", kind="ram")
        opt._emit("Turbo PC  active", kind="tpp")
        self.assertEqual(ram_msgs, ["freed 500 MB"])
        self.assertEqual(tpp_msgs, ["Turbo PC  active"])

    def test_unregister(self):
        opt = _fresh_optimizer()
        msgs = []
        opt.register_status_listener(msgs.append, kind="tpp")
        opt.unregister_status_listener(msgs.append)
        opt._emit("x", kind="tpp")
        self.assertEqual(msgs, [])


if __name__ == "__main__":
    unittest.main()
