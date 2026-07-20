"""tests.test_version
ONE version source (utils/app_version.py) - stability guards.

Born 2026-07-17 after the audit found the version scattered across 8 files
and already drifted: the main window titled itself v1.8.1 while startup's
FindWindowW searched for v1.8.2 (second-instance focus dead), and telemetry /
hck_GPT read startup.py as a FILE, which does not exist inside a frozen dist
(both silently reported the stale "1.8.0" fallback in shipped builds).

These tests make that class of bug impossible to reintroduce:
  - the source module stays import-free and well-formed
  - every consumer agrees with the source at runtime
  - NO source file may hardcode an app-version literal again
  - the spec derives the dist name from the source
  - the CHANGELOG carries a section for the current version
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from utils.app_version import APP_VERSION, MAIN_WINDOW_TITLE, version_tuple


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestVersionSource(unittest.TestCase):

    def test_format_and_tuple(self):
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")
        vt = version_tuple()
        self.assertEqual(len(vt), 3)
        self.assertTrue(all(isinstance(p, int) for p in vt))
        self.assertEqual(".".join(str(p) for p in vt), APP_VERSION)

    def test_current_version_is_1_8_4(self):
        """Explicit pin for THIS release - bump consciously, with the file."""
        self.assertEqual(APP_VERSION, "1.8.4")

    def test_source_module_imports_nothing(self):
        """utils/app_version.py must stay dependency-free: it is imported at
        line 1 of startup.py (pre-Tk, pre-psutil) and parsed by the spec."""
        src = _read("utils", "app_version.py")
        for line in src.splitlines():
            code = line.split("#", 1)[0].strip()
            self.assertFalse(
                code.startswith(("import ", "from ")),
                f"app_version.py must not import anything: {line!r}")

    def test_window_title_contains_version(self):
        self.assertIn(APP_VERSION, MAIN_WINDOW_TITLE)
        self.assertTrue(MAIN_WINDOW_TITLE.startswith("PC Workman HCK"))


class TestConsumersAgree(unittest.TestCase):

    def test_hck_gpt_about_version(self):
        from hck_gpt.responses.builder import ResponseBuilder
        self.assertEqual(ResponseBuilder._app_version(), APP_VERSION)

    def test_telemetry_resolved_version(self):
        from core.telemetry import _resolve_version
        self.assertEqual(_resolve_version(), APP_VERSION)
        # explicit caller version still wins (Settings passes it through)
        self.assertEqual(_resolve_version("9.9.9"), "9.9.9")

    def test_startup_imports_the_source(self):
        """startup.py must import the constant, never define a literal."""
        src = _read("startup.py")
        self.assertIn("from utils.app_version import APP_VERSION", src)
        self.assertNotRegex(
            src, r'APP_VERSION\s*=\s*["\']',
            "startup.py defines a version literal - use utils/app_version.py")

    def test_startup_findwindow_uses_shared_title(self):
        """The single-instance lookup and the window title must be the SAME
        constant - a rebuilt f-string is exactly how they drifted apart."""
        src = _read("startup.py")
        self.assertIn("FindWindowW(None, MAIN_WINDOW_TITLE)", src)
        mw = _read("ui", "windows", "main_window_expanded.py")
        self.assertIn("self.root.title(_WIN_TITLE)", mw)
        self.assertIn("MAIN_WINDOW_TITLE as _WIN_TITLE", mw)

    def test_spec_derives_dist_name(self):
        spec = _read("PCWorkman.spec")
        self.assertIn("utils', 'app_version.py", spec)
        self.assertIn("name=f'PC_Workman_HCK_{APP_VERSION}'", spec)
        self.assertIn("'utils.app_version',", spec)

    def test_changelog_has_current_version_section(self):
        """Bumping the version without writing its changelog section fails."""
        self.assertIn(f"## [{APP_VERSION}]", _read("CHANGELOG.md"))


class TestNoStrayVersionLiterals(unittest.TestCase):
    """THE ratchet: no source file may hardcode an app version again.

    Scans every .py under the app packages plus the spec, strips comments
    (history annotations like '(1.8.1)' in import_core are fine), and fails
    on any remaining 1.x.y-looking literal that is not the source module.
    """

    SCAN_DIRS = ("core", "ui", "hck_gpt", "hck_stats_engine", "utils")
    SCAN_FILES = ("startup.py", "import_core.py", "PCWorkman.spec")
    RX = re.compile(r"\b1\.[0-9]+\.[0-9]+\b")
    # utils/app_version.py IS the source; HELPER_VERSION (diagnostic console
    # banner, frozen at 1.6.3) is a different, intentionally static number.
    ALLOWED_LINE = re.compile(r"HELPER_VERSION|hck_GPT v2\.1|python_requires")

    def _iter_files(self):
        for base in self.SCAN_DIRS:
            for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
                dirnames[:] = [d for d in dirnames if d != "__pycache__"]
                for fn in filenames:
                    if fn.endswith(".py"):
                        yield os.path.join(dirpath, fn)
        for fn in self.SCAN_FILES:
            p = os.path.join(ROOT, fn)
            if os.path.isfile(p):
                yield p

    def test_no_hardcoded_versions_outside_source(self):
        src_file = os.path.join(ROOT, "utils", "app_version.py")
        offenders = []
        for path in self._iter_files():
            if os.path.abspath(path) == os.path.abspath(src_file):
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                for no, line in enumerate(f, 1):
                    code = line.split("#", 1)[0]
                    if not self.RX.search(code):
                        continue
                    if self.ALLOWED_LINE.search(line):
                        continue
                    rel = os.path.relpath(path, ROOT)
                    offenders.append(f"{rel}:{no}: {line.strip()[:90]}")
        self.assertEqual(offenders, [],
                         "hardcoded version literals (use utils/app_version.py):\n"
                         + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
