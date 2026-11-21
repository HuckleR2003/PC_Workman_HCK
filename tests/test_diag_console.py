"""tests.test_diag_console
No console window, and nothing that needs one (2026-11-14).

The build used to be a console app that hid its console after the UI came
up. On Windows 11 (Windows Terminal) that hide is a silent no-op: one machine
logged 43 "console_hide_failed" events. The build is windowed now, which has
one sharp edge: sys.stdout and sys.stderr are None there. These tests lock
in the three things that keep a windowed build alive:

  1. the spec really is console=False and bundles the new modules,
  2. startup.py installs the streams before its first print() and never
     calls input() (RuntimeError without a console),
  3. the stream writer works with no real stream behind it.
"""
import io
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _code_only(src: str) -> str:
    """Source without comments, so notes about the old behaviour are fine."""
    return "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())


class TestWindowedBuild(unittest.TestCase):

    def test_spec_builds_without_console(self):
        spec = _code_only(_read("PCWorkman.spec"))
        self.assertRegex(spec, r"console\s*=\s*False")
        self.assertNotRegex(spec, r"console\s*=\s*True")

    def test_spec_never_bundles_personal_settings(self):
        """network.json carries an install id and the telemetry choice;
        user_prefs.json, fan curves and TURBO state are one person's."""
        spec = _code_only(_read("PCWorkman.spec"))
        self.assertNotIn("(os.path.join(project_root, 'settings'), 'settings')",
                         spec)
        for personal in ("network.json", "user_prefs.json", "turbo_state.json",
                         "fan_dashboard.json", "app_settings.json"):
            self.assertNotIn(personal, spec)

    def test_spec_bundles_the_new_modules(self):
        spec = _read("PCWorkman.spec")
        self.assertIn("'utils.diag_console',", spec)
        self.assertIn("'ui.startup_error',", spec)

    def test_startup_sets_streams_before_first_print(self):
        src = _code_only(_read("startup.py"))
        setup_at = src.find("diag_console.setup()")
        first_print = re.search(r"^\s*print\(", src, re.M)
        self.assertGreater(setup_at, 0, "startup.py never calls setup()")
        self.assertLess(setup_at, first_print.start(),
                        "a print() runs before the streams are installed")

    def test_startup_never_waits_for_console_input(self):
        src = _code_only(_read("startup.py"))
        self.assertNotRegex(src, r"(?<![\w.])input\(",
                            "input() raises RuntimeError in a windowed build")

    def test_startup_no_longer_hides_a_console(self):
        src = _code_only(_read("startup.py"))
        self.assertNotIn("hide_console", src)
        self.assertNotIn("ShowWindow(hwnd, 0)", src)

    def test_no_direct_writes_to_possibly_missing_streams(self):
        """sys.stderr.write() and friends are safe only after setup(). Any
        module imported before that, or run outside startup.py, must not
        rely on them. Scans the app packages."""
        pattern = re.compile(
            r"sys\.(?:__stdout__|__stderr__)\b|"
            r"sys\.std(?:out|err)\.buffer\b")
        offenders = []
        for pkg in ("core", "hck_gpt", "hck_stats_engine", "ui", "utils"):
            for dirpath, _dirs, files in os.walk(os.path.join(_ROOT, pkg)):
                for name in files:
                    if not name.endswith(".py"):
                        continue
                    path = os.path.join(dirpath, name)
                    with open(path, encoding="utf-8", errors="replace") as f:
                        if pattern.search(_code_only(f.read())):
                            offenders.append(os.path.relpath(path, _ROOT))
        self.assertEqual(offenders, [],
                         "these touch streams that are None in the exe")


class TestTee(unittest.TestCase):

    def test_writes_with_no_real_stream(self):
        from utils.diag_console import _Tee
        log = io.StringIO()
        tee = _Tee(None, log)
        self.assertEqual(tee.write("hello\n"), 6)
        tee.flush()
        self.assertFalse(tee.isatty())
        self.assertEqual(log.getvalue(), "hello\n")

    def test_writes_to_both(self):
        from utils.diag_console import _Tee
        real, log = io.StringIO(), io.StringIO()
        _Tee(real, log).write("x")
        self.assertEqual((real.getvalue(), log.getvalue()), ("x", "x"))

    def test_a_broken_stream_never_raises(self):
        from utils.diag_console import _Tee

        class Broken:
            def write(self, _t):
                raise OSError("gone")

            def flush(self):
                raise OSError("gone")

        tee = _Tee(Broken(), Broken())
        tee.write("still fine")
        tee.flush()

    def test_log_stops_growing_at_the_limit(self):
        import utils.diag_console as dc
        log = io.StringIO()
        tee = dc._Tee(None, log)
        chunk = "x" * 100_000
        for _ in range(10):
            tee.write(chunk)
        self.assertLess(len(log.getvalue()), dc._MAX_LOG_BYTES + 200_000)
        self.assertIn("log size limit reached", log.getvalue())

    def test_print_works_through_it(self):
        from utils.diag_console import _Tee
        log = io.StringIO()
        print("zażółć", file=_Tee(None, log))
        self.assertEqual(log.getvalue(), "zażółć\n")


class TestStartupConsoleSetting(unittest.TestCase):
    """Settings > "Show diagnostic console at startup" (2026-11-15)."""

    def test_setting_is_read_from_app_settings(self):
        import json
        import tempfile
        from unittest import mock
        import utils.diag_console as dc
        tmp = tempfile.mkdtemp(prefix="pcw_test_cfg_")
        os.makedirs(os.path.join(tmp, "settings"))
        path = os.path.join(tmp, "settings", "app_settings.json")
        with mock.patch("utils.paths.APP_DIR", tmp):
            self.assertFalse(dc.startup_console_wanted(), "no file -> off")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({dc.STARTUP_CONSOLE_KEY: True}, f)
            self.assertTrue(dc.startup_console_wanted())
            with open(path, "w", encoding="utf-8") as f:
                f.write("{broken")
            self.assertFalse(dc.startup_console_wanted(), "broken -> off")

    def test_release_only_in_startup_mode(self):
        import utils.diag_console as dc
        saved = dc.MODE
        try:
            dc.MODE = "console"                 # --console stays open
            self.assertFalse(dc.release_startup_console())
            self.assertEqual(dc.MODE, "console")
        finally:
            dc.MODE = saved

    def test_release_starts_the_window_countdown(self):
        from unittest import mock
        import utils.diag_console as dc
        from ui import diag_window
        saved = dc.MODE
        try:
            dc.MODE = "startup"
            with mock.patch.object(diag_window, "is_open", return_value=True), \
                    mock.patch.object(diag_window, "close_after") as close:
                self.assertTrue(dc.release_startup_console())
            close.assert_called_once_with(3000)
            self.assertEqual(dc.MODE, "silent")
        finally:
            dc.MODE = saved

    def test_output_reaches_the_window_and_the_log(self):
        import utils.diag_console as dc
        log, seen = io.StringIO(), []
        tee = dc._Tee(None, log)
        dc._listeners.append(seen.append)
        try:
            tee.write("[+] Core modules loaded\n")
        finally:
            dc._listeners.remove(seen.append)
        self.assertEqual(seen, ["[+] Core modules loaded\n"])
        self.assertIn("Core modules loaded", log.getvalue())

    def test_window_opens_live_and_counts_down(self):
        """The real window, on its own thread: lines arrive, the countdown
        closes it, a closed window stops queueing."""
        import time
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            self.skipTest("no display available")
        from ui import diag_window as dw
        self.assertTrue(dw.start("[~] Loading core systems...\n"))
        self.assertTrue(dw.is_open())
        self.assertIsNone(getattr(tk, "_default_root", None),
                          "the diagnostic window became tkinter's default "
                          "root: later images would land in its interpreter")
        dw.feed("[+] Core modules loaded\n")
        dw.close_after(300)
        end = time.time() + 5
        while dw.is_open() and time.time() < end:
            time.sleep(0.05)
        self.assertFalse(dw.is_open(), "the countdown did not close it")
        dw.feed("after close\n")
        self.assertTrue(dw._state["queue"].empty(),
                        "a closed window keeps collecting output")

    def test_spec_bundles_the_window(self):
        self.assertIn("'ui.diag_window',", _read("PCWorkman.spec"))

    def test_startup_schedules_the_release_and_settings_has_the_switch(self):
        src = _code_only(_read("startup.py"))
        self.assertIn("release_startup_console", src)
        self.assertIn("open_startup_window", src)
        settings = _read("ui", "pages", "settings_page.py")
        self.assertIn('"show_startup_console"', settings)
        import utils.diag_console as dc
        self.assertEqual(dc.STARTUP_CONSOLE_KEY, "show_startup_console")
        self.assertEqual(dc.STARTUP_CONSOLE_DELAY_MS, 3000)


class TestProblems(unittest.TestCase):

    def test_problems_are_remembered(self):
        import utils.diag_console as dc
        before = len(dc.problems())
        dc.note_problem("core.monitor FAILED: boom")
        self.assertEqual(len(dc.problems()), before + 1)
        self.assertIn("core.monitor FAILED: boom", dc.problems())
        with dc._problems_lock:
            dc._problems.remove("core.monitor FAILED: boom")


class TestErrorReport(unittest.TestCase):

    def test_report_has_what_a_bug_report_needs(self):
        from ui.startup_error import build_report
        from utils.app_version import APP_VERSION
        text = build_report("The interface could not be loaded.",
                            "Traceback (most recent call last):\n  boom")
        self.assertIn(f"PC Workman {APP_VERSION}", text)
        self.assertIn("System: Windows", text)
        self.assertIn("Problem: The interface could not be loaded.", text)
        self.assertIn("boom", text)

    def test_both_languages_have_the_same_strings(self):
        from ui.startup_error import _TEXT
        self.assertEqual(set(_TEXT["en"]), set(_TEXT["pl"]))


class TestSplashRelease(unittest.TestCase):

    def test_splash_accepts_a_release_event(self):
        import inspect
        import ui.splash_screen as sp
        self.assertIn("release", inspect.signature(sp.show_splash).parameters)
        self.assertIn("release",
                      inspect.signature(sp.SplashScreen.__init__).parameters)
        self.assertGreater(sp.SplashScreen.MAX_HOLD_S, 0)


if __name__ == "__main__":
    unittest.main()
