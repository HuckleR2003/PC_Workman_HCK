"""tests.test_prefs_io
Shared prefs/window helpers (2026-07 dedup guards).

utils/prefs_io.py and utils/win_active.py replaced six _load_prefs/_save_prefs
copies and three _foreground_pid copies. These tests pin the contract that
made the dedup safe: reads never raise (return the default), writes never
raise (return False), and the migrated modules actually delegate to the shared
helper instead of re-growing their own copy.
"""
import json
import os
import tempfile
import unittest

os.environ.setdefault("PCW_DEBUG", "0")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestPrefsIO(unittest.TestCase):

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "sub", "prefs.json")

    def test_roundtrip_utf8(self):
        from utils.prefs_io import load_json, save_json
        data = {"język": "polski", "n": 42, "list": [1, 2]}
        self.assertTrue(save_json(self.p, data))       # creates the sub dir
        self.assertEqual(load_json(self.p, {}), data)

    def test_load_missing_returns_default(self):
        from utils.prefs_io import load_json
        self.assertEqual(load_json(self.p, {}), {})
        self.assertEqual(load_json(self.p, {"a": 1}), {"a": 1})
        self.assertEqual(load_json(self.p), {})         # default None -> {}

    def test_load_bad_json_returns_default(self):
        from utils.prefs_io import load_json
        os.makedirs(os.path.dirname(self.p), exist_ok=True)
        with open(self.p, "w", encoding="utf-8") as f:
            f.write("{ not valid json ,,,")
        self.assertEqual(load_json(self.p, {"safe": True}), {"safe": True})

    def test_save_unwritable_returns_false_never_raises(self):
        from utils.prefs_io import save_json
        # A path whose parent cannot be created (a file used as a directory)
        blocker = os.path.join(self.d, "afile")
        with open(blocker, "w") as f:
            f.write("x")
        bad = os.path.join(blocker, "nested", "prefs.json")
        self.assertFalse(save_json(bad, {"a": 1}))      # must not raise


class TestWinActive(unittest.TestCase):

    def test_foreground_pid_returns_int(self):
        from utils.win_active import foreground_pid
        self.assertIsInstance(foreground_pid(), int)    # 0 is fine (headless)


class TestMigrationRatchet(unittest.TestCase):
    """The six/three copies must stay deleted - migrated modules delegate."""

    PREFS_FILES = [
        ("core", "auto_optimizer.py"),
        ("core", "hibernation_manager.py"),
        ("core", "process_guard.py"),
        ("ui", "pages", "optimization_services.py"),
        ("ui", "pages", "startup_manager.py"),
    ]
    PID_FILES = [
        ("core", "app_activity_tracker.py"),
        ("core", "fps_monitor.py"),
        ("core", "turbo_manager.py"),
    ]

    def test_prefs_modules_delegate_to_helper(self):
        for parts in self.PREFS_FILES:
            src = _read(*parts)
            self.assertIn("from utils.prefs_io import", src,
                          f"{parts[-1]} must use the shared prefs helper")

    def test_pid_modules_delegate_to_helper(self):
        for parts in self.PID_FILES:
            src = _read(*parts)
            self.assertIn("from utils.win_active import", src,
                          f"{parts[-1]} must use the shared foreground-pid helper")


if __name__ == "__main__":
    unittest.main()
