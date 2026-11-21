"""tests.test_paths
Tests for utils.paths - APP_DIR resolution across dev / frozen / MSIX modes.
The MSIX case is the critical one: Store installs live in WindowsApps, which
is read-only, so every write (stats DB, learning baselines, prefs) silently
failed there until APP_DIR learned to redirect to LOCALAPPDATA (1.8.1).
"""
import importlib
import os
import sys
import unittest

import utils.paths as paths


class TestAppDirResolution(unittest.TestCase):

    def tearDown(self):
        # undo any frozen simulation and restore the real module state
        if hasattr(sys, "frozen"):
            del sys.frozen
        sys.executable = self._real_executable
        if self._saved_app_dir is not None:
            os.environ["PCW_APP_DIR"] = self._saved_app_dir
        importlib.reload(paths)

    def setUp(self):
        self._real_executable = sys.executable
        # these tests check the real resolution rules, not the suite sandbox
        self._saved_app_dir = os.environ.pop("PCW_APP_DIR", None)

    def test_dev_mode_points_to_project_root(self):
        saved = os.environ.pop("PCW_APP_DIR", None)   # the suite's sandbox
        try:
            importlib.reload(paths)
            self.assertTrue(os.path.isfile(
                os.path.join(paths.APP_DIR, "startup.py")),
                f"dev APP_DIR should be the project root, got {paths.APP_DIR}")
        finally:
            if saved is not None:
                os.environ["PCW_APP_DIR"] = saved

    def test_override_moves_app_dir(self):
        saved = os.environ.get("PCW_APP_DIR")
        target = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "build", "pcw_override_probe")
        try:
            os.environ["PCW_APP_DIR"] = target
            importlib.reload(paths)
            self.assertEqual(paths.APP_DIR, target)
        finally:
            if saved is None:
                os.environ.pop("PCW_APP_DIR", None)
            else:
                os.environ["PCW_APP_DIR"] = saved
            try:
                os.rmdir(target)
            except OSError:
                pass

    def test_msix_install_redirects_to_localappdata(self):
        sys.frozen = True
        sys.executable = (r"C:\Program Files\WindowsApps"
                          r"\Vendor.App_1.0.0.0_x64__abc123\App.exe")
        importlib.reload(paths)
        self.assertNotIn("WindowsApps", paths.APP_DIR,
                         "MSIX APP_DIR must never stay inside WindowsApps")
        self.assertIn("PC_Workman_HCK", paths.APP_DIR)

    def test_msix_dir_is_actually_writable(self):
        sys.frozen = True
        sys.executable = (r"C:\Program Files\WindowsApps"
                          r"\Vendor.App_1.0.0.0_x64__abc123\App.exe")
        importlib.reload(paths)
        probe = os.path.join(paths.APP_DIR, ".test_probe")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)

    def test_bundle_dir_exists(self):
        importlib.reload(paths)
        self.assertTrue(os.path.isdir(paths.BUNDLE_DIR))


class TestWritablePathsUseAppDir(unittest.TestCase):
    """Settings and data must be found next to the exe (APP_DIR).
    Found 2026-11-15 in the built exe: the main window read the language from
    _internal (__file__), so a language chosen in Settings never survived a
    restart; Export / Reset data touched nothing; the fan dashboard wrote to
    the CURRENT folder, which is System32 when Windows autostarts the app."""

    FILES = ("ui/windows/main_window_expanded.py", "ui/pages/settings_page.py",
             "ui/components/yourpc_page.py", "ui/components/fan_dashboard.py")

    def test_no_cwd_relative_settings_or_data(self):
        import re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bad = []
        for rel in self.FILES:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    code = line.split("#", 1)[0]
                    if re.search(r'os\.path\.join\(\s*["\'](settings|data)["\']',
                                 code):
                        bad.append(f"{rel}:{n}")
        self.assertEqual(bad, [], "path relative to the current folder")

    def test_settings_json_is_not_read_through_file_dir(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "ui", "windows", "main_window_expanded.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn(
            '_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__)))',
            src)


class TestLogDir(unittest.TestCase):
    """errors.log and freeze_dump.txt follow PCW_LOG_DIR, so a test run can
    never again append to the logs of real use (found 2026-11-14)."""

    def setUp(self):
        self._saved = os.environ.get("PCW_LOG_DIR")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("PCW_LOG_DIR", None)
        else:
            os.environ["PCW_LOG_DIR"] = self._saved

    def test_default_is_app_data_logs(self):
        os.environ.pop("PCW_LOG_DIR", None)
        self.assertEqual(paths.log_dir(),
                         os.path.join(paths.APP_DIR, "data", "logs"))

    def test_override_moves_both_logs(self):
        import utils.crash_log as crash_log
        import utils.freeze_watchdog as freeze_watchdog
        os.environ["PCW_LOG_DIR"] = r"C:\somewhere\else"
        self.assertEqual(crash_log._path(), r"C:\somewhere\else\errors.log")
        self.assertEqual(freeze_watchdog._dump_path(),
                         r"C:\somewhere\else\freeze_dump.txt")


if __name__ == "__main__":
    unittest.main()
