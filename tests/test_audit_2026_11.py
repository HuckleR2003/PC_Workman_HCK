"""tests.test_audit_2026_11
Guards for what the November 2026 audit found.

1. Process suspension froze system services. The scan suspended every idle
   process that was not on a short whitelist; turbo_engine.log (2026-07-06)
   shows MSI services, GameInput and the console host frozen in one second.
   It is an allow-list now, the foreground app's whole family is off limits,
   and frozen PIDs are written to disk so a crash cannot leave them frozen.
2. "Background" scans that ran on the UI thread (Services, Startup).
3. CIM dates in the "/Date(ms)/" shape shown raw as the GPU driver date.
"""
import inspect
import json
import os
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestSuspenderIsAnAllowList(unittest.TestCase):

    def setUp(self):
        import core.turbo_manager as tm
        self.tm = tm
        self.S = tm.TurboProcessSuspender

    def test_services_and_unknown_processes_are_never_candidates(self):
        # every name below was frozen on 2026-07-06
        for name in ("MSI_Central_Service.exe", "GameInputRedistService.exe",
                     "gamingservicesnet.exe", "OpenConsole.exe",
                     "LightKeeperService.exe", "RvControlSvc.exe",
                     "MSI.TerminalServer.exe", "some_unknown_tool.exe", ""):
            self.assertFalse(self.S._may_suspend(name), name)

    def test_known_apps_are_candidates(self):
        for name in ("chrome.exe", "Discord.exe", "Spotify.exe", "steam.exe"):
            self.assertTrue(self.S._may_suspend(name), name)

    def test_foreground_app_family_is_off_limits(self):
        self.assertFalse(self.S._may_suspend("chrome.exe", "Chrome.exe"))
        self.assertTrue(self.S._may_suspend("discord.exe", "chrome.exe"))

    def test_scan_uses_the_gate(self):
        src = inspect.getsource(self.S._scan)
        self.assertIn("_may_suspend", src,
                      "the scan no longer checks the allow-list")

    def test_candidate_list_contains_nothing_system(self):
        for name in self.tm._CANDIDATE_NAMES:
            self.assertNotIn(name, {n.lower() for n in
                                    self.tm._PROC_WHITELIST_NAMES}, name)
            self.assertNotRegex(name, r"svc|service|host")


class TestSuspenderLeavesNothingFrozen(unittest.TestCase):

    def test_recover_ignores_a_recycled_pid(self):
        """The file names a PID that now belongs to another process (ours).
        It must not be touched, and the file must be cleaned up."""
        import core.turbo_manager as tm
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({str(os.getpid()): {"name": "chrome.exe",
                                          "created": 1.0}}, f)
        woken = tm.turbo_processes._recover_orphans(path)
        self.assertEqual(woken, 0)
        self.assertFalse(os.path.exists(path))

    def test_recover_survives_a_missing_or_broken_file(self):
        import core.turbo_manager as tm
        self.assertEqual(tm.turbo_processes._recover_orphans(
            os.path.join(tempfile.gettempdir(), "pcw_no_such_file.json")), 0)
        fd, path = tempfile.mkstemp(suffix=".json")
        os.write(fd, b"{not json")
        os.close(fd)
        try:
            self.assertEqual(tm.turbo_processes._recover_orphans(path), 0)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_state_is_persisted_and_restored_on_exit(self):
        import core.turbo_manager as tm
        S = tm.TurboProcessSuspender
        self.assertIn("_persist", inspect.getsource(S._suspend))
        self.assertIn("_persist", inspect.getsource(S.resume))
        self.assertIn("atexit", inspect.getsource(S.__init__))
        self.assertIn("_recover_orphans", inspect.getsource(S.__init__))

    def test_callers_use_the_real_api(self):
        opt = _read("ui", "pages", "optimization_services.py")
        self.assertNotIn("suspended_list()", opt,
                         "suspended_list is a property, calling it raises")
        self.assertNotIn("turbo_processes._idle_seconds",
                         _read("ui", "pages", "settings_page.py"))


class TestScansRunOffTheUiThread(unittest.TestCase):
    """`Thread(target=lambda: page.after(0, lambda: done(slow())))` runs
    slow() on the UI thread. The scan must be called by the worker itself."""

    def test_services_scan(self):
        src = _read("ui", "pages", "services_manager.py")
        self.assertNotIn("_on_ready(_get_statuses_batch(names))", src)
        # the worker stores the result, the UI thread picks it up (2026-11-16)
        self.assertIn('result["statuses"] = _get_statuses_batch(names)', src)
        self.assertIn("page.after(60, _poll)", src)

    def test_startup_scan(self):
        src = _read("ui", "pages", "startup_manager.py")
        self.assertNotIn("_on_ready(_read_startup_entries())", src)
        self.assertIn("entries = _read_startup_entries()", src)


class TestCimDates(unittest.TestCase):

    def test_both_shapes_parse(self):
        from core.hardware_detector import parse_cim_date, _fmt_driver_date
        self.assertEqual(_fmt_driver_date("/Date(1784678400000)/"), "2026-07-22")
        self.assertEqual(_fmt_driver_date("\\/Date(1784678400000)\\/"),
                         "2026-07-22")
        self.assertEqual(_fmt_driver_date("20231005000000.000000-000"),
                         "2023-10-05")
        self.assertIsNone(parse_cim_date(""))
        self.assertIsNone(parse_cim_date(None))
        self.assertEqual(_fmt_driver_date("garbage"), "Unknown")


if __name__ == "__main__":
    unittest.main()
