"""tests.test_000_isolation - the whole test run gets its own data folder.

Named to sort FIRST: `unittest discover` imports test modules in file-name
order, and this sets PCW_APP_DIR before any other module imports
utils.paths. From then on APP_DIR, i.e. every settings, cache and log file
the app writes, is a temporary folder.

Why (2026-11-15): with the new safe writer every write leaves a .bak file,
which made it visible that tests had been writing into the developer's real
files all along: Optimization receipts (data/cache/opt_receipts.json), the
learned voltage baseline (data/cache/voltage_baseline.json) and the TURBO
service profiles (settings/turbo_services.json). A test must never be able to
change what a user's PC Workman remembers.

Read-only assets (icons, locales, process library) come from BUNDLE_DIR and
are untouched by this.
"""
import os
import shutil
import tempfile
import unittest

_REAL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if not os.environ.get("PCW_APP_DIR"):
    _tmp = tempfile.mkdtemp(prefix="pcw_test_appdir_")
    # Data the app ships and only READS from APP_DIR in a dev checkout: copy
    # it in, so tests see the same inputs as before (never the user's state).
    for rel in (("data", "process_info"),):
        src = os.path.join(_REAL_ROOT, *rel)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(_tmp, *rel))
    os.environ["PCW_APP_DIR"] = _tmp
if not os.environ.get("PCW_LOG_DIR"):
    os.environ["PCW_LOG_DIR"] = os.path.join(os.environ["PCW_APP_DIR"],
                                             "data", "logs")


class TestIsolation(unittest.TestCase):

    def test_app_dir_is_not_the_project(self):
        from utils.paths import APP_DIR
        self.assertNotEqual(os.path.normcase(os.path.abspath(APP_DIR)),
                            os.path.normcase(_REAL_ROOT),
                            "tests would write the real settings")


if __name__ == "__main__":
    unittest.main()
