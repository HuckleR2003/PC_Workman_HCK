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
        importlib.reload(paths)

    def setUp(self):
        self._real_executable = sys.executable

    def test_dev_mode_points_to_project_root(self):
        importlib.reload(paths)
        self.assertTrue(os.path.isfile(
            os.path.join(paths.APP_DIR, "startup.py")),
            f"dev APP_DIR should be the project root, got {paths.APP_DIR}")

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


if __name__ == "__main__":
    unittest.main()
