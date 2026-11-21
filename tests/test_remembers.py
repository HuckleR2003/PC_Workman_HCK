"""tests.test_remembers
PC Workman remembers what the user set (2026-11-15).

Every settings write used to be open(path, "w") + json.dump: the file is
emptied first and written afterwards, so a close, a crash or a second writer
in that moment left a broken file, the next read returned {} and everything
in it was "forgotten". Some values were never saved at all (window size and
position, the chart range, two thresholds on the Optimization page).
"""
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tmp(name="x.json"):
    return os.path.join(tempfile.mkdtemp(prefix="pcw_test_rem_"), name)


class TestSafeWrites(unittest.TestCase):

    def test_round_trip_and_backup(self):
        from utils.prefs_io import load_json, save_json
        p = _tmp()
        self.assertTrue(save_json(p, {"language": "pl"}))
        self.assertTrue(save_json(p, {"language": "en"}))
        self.assertEqual(load_json(p), {"language": "en"})
        with open(p + ".bak", encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"language": "pl"})

    def test_damaged_file_falls_back_to_the_backup(self):
        """What a crash in the middle of the old write left behind."""
        from utils.prefs_io import load_json, save_json
        p = _tmp()
        save_json(p, {"a": 1})
        save_json(p, {"a": 2})
        with open(p, "w", encoding="utf-8") as f:
            f.write('{"a": ')                      # half-written
        self.assertEqual(load_json(p), {"a": 1})
        self.assertEqual(load_json(p), {"a": 1}, "backup was not put back")

    def test_empty_file_is_damaged_too(self):
        from utils.prefs_io import load_json, save_json
        p = _tmp()
        save_json(p, {"kept": True})
        save_json(p, {"kept": True, "n": 2})
        open(p, "w").close()                       # emptied, never written
        self.assertEqual(load_json(p), {"kept": True})

    def test_a_bad_file_never_becomes_the_backup(self):
        from utils.prefs_io import save_json
        p = _tmp()
        save_json(p, {"good": 1})
        save_json(p, {"good": 2})
        with open(p, "w") as f:
            f.write("garbage")
        save_json(p, {"good": 3})
        # the broken file is dropped, the last GOOD version stays the backup
        with open(p + ".bak", encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"good": 1})

    def test_no_temp_files_left(self):
        from utils.prefs_io import save_json
        p = _tmp()
        for i in range(5):
            save_json(p, {"i": i})
        leftovers = [n for n in os.listdir(os.path.dirname(p)) if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_concurrent_writers_lose_nothing(self):
        """Two threads, 200 increments each, through update/edit_json."""
        from utils.prefs_io import edit_json, load_json
        p = _tmp()

        def bump(key):
            for _ in range(200):
                edit_json(p, lambda d: d.__setitem__(key, d.get(key, 0) + 1))
        ts = [threading.Thread(target=bump, args=(k,)) for k in ("a", "b")]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(load_json(p), {"a": 200, "b": 200})

    def test_update_json_removes_with_none(self):
        from utils.prefs_io import update_json, load_json
        p = _tmp()
        update_json(p, keep=1, drop=2)
        update_json(p, drop=None)
        self.assertEqual(load_json(p), {"keep": 1})

    def test_no_plain_settings_writes_left(self):
        """Every json.dump to a file goes through utils/prefs_io."""
        offenders = []
        for top in ("core", "ui", "hck_gpt", "utils", "hck_stats_engine"):
            for dp, dn, fn in os.walk(os.path.join(_ROOT, top)):
                dn[:] = [d for d in dn if d != "__pycache__"]
                for n in fn:
                    if not n.endswith(".py"):
                        continue
                    rel = os.path.relpath(os.path.join(dp, n), _ROOT).replace("\\", "/")
                    if rel == "utils/prefs_io.py":
                        continue
                    with open(os.path.join(dp, n), encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            code = line.split("#", 1)[0]
                            if "json.dump(" in code:
                                offenders.append(f"{rel}:{i}")
        self.assertEqual(offenders, [], "write JSON with utils.prefs_io")


class TestSettingsPageMerges(unittest.TestCase):

    def test_saving_the_page_keeps_keys_saved_elsewhere(self):
        import ui.pages.settings_page as sp
        p = _tmp("app_settings.json")
        with mock.patch.object(sp, "_SETTINGS_FILE", p):
            page_copy = sp._load_settings()                 # page opens: {}
            from utils.prefs_io import update_json
            update_json(p, window={"w": 1200}, chart_filter="1D")   # main window
            page_copy["language"] = "pl"
            sp._save_settings(page_copy)                    # page saves later
            got = sp._load_settings()
        self.assertEqual(got.get("language"), "pl")
        self.assertEqual(got.get("chart_filter"), "1D", "page wiped the chart range")
        self.assertEqual(got.get("window"), {"w": 1200}, "page wiped the window size")


class TestQuickSetupRemembered(unittest.TestCase):

    def test_answers_survive_a_new_page(self):
        import ui.pages.services_manager as sm
        p = _tmp("quick_setup.json")
        with mock.patch.object(sm, "_QUICK_PATH", p):
            sm._save_quick({"Fax": "no", "Drukowanie": "yes"})
            self.assertEqual(sm._load_quick(), {"Fax": "no", "Drukowanie": "yes"})


class TestOptimizationThresholdsRemembered(unittest.TestCase):

    def test_process_guard_threshold_is_the_settings_value(self):
        from ui.pages import optimization_services as osvc
        p = _tmp("app_settings.json")
        with mock.patch.object(osvc, "_APP_SETTINGS_PATH", p):
            osvc._set_app_setting(turbo_idle_seconds=600)
            self.assertEqual(osvc._app_setting("turbo_idle_seconds"), 600)
        import inspect
        src = inspect.getsource(osvc._build_guard_expand)
        self.assertIn('_app_setting("turbo_idle_seconds"', src)
        self.assertNotIn("_sel_thr(300)  # default", src)

    def test_hibernation_threshold_is_saved(self):
        import inspect
        from ui.pages import optimization_services as osvc
        src = inspect.getsource(osvc)
        self.assertIn("hib_idle_min", src)

    def test_save_opt_merges_under_the_lock(self):
        from ui.pages import optimization_services as osvc
        p = _tmp("user_prefs.json")
        with mock.patch.object(osvc, "_PREFS_PATH", p):
            osvc._save_opt(ram_auto=True)
            osvc._set_turbo_flag(True)
            osvc._save_opt(hib_idle_min=30)
            d = osvc._load_prefs()
        self.assertEqual(d["optimization"], {"ram_auto": True, "hib_idle_min": 30})
        self.assertTrue(d["turbo_active"])


class TestWindowRemembered(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        from _isolate import isolate_window_state
        cls.path = isolate_window_state()
        import ui.windows.main_window_expanded as mwe
        cls.mwe = mwe

    @classmethod
    def tearDownClass(cls):
        # the next window test must start from defaults, not from our sizes
        from utils.prefs_io import remove_json
        remove_json(cls.path)

    def _build(self):
        win = self.mwe.ExpandedMainWindow(
            data_manager=None, monitor=None,
            switch_to_minimal_callback=lambda: None, quit_callback=lambda: None)
        win.root.update()
        return win

    def test_size_position_and_chart_range_come_back(self):
        from utils.prefs_io import save_json, load_json
        from utils import ui_scale as uis
        save_json(self.path, {"window": {"x": 120, "y": 90,
                                         "w": uis.compact_w() + 80,
                                         "h": uis.compact_h() + 40,
                                         "maximized": False},
                              "chart_filter": "1D"})
        win = self._build()
        try:
            self.assertEqual(win.chart_filter, "1D")
            self.assertEqual(win.root.winfo_width(), uis.compact_w() + 80)
            self.assertEqual((win.root.winfo_x(), win.root.winfo_y()), (120, 90))
            win._remember_chart_filter("1W")
            win._save_window_placement()
            saved = load_json(self.path)
            self.assertEqual(saved["chart_filter"], "1W")
            self.assertEqual(saved["window"]["x"], 120)
        finally:
            win.root.destroy()

    def test_off_screen_placement_is_ignored(self):
        """Saved on a second monitor that is no longer connected."""
        from utils.prefs_io import save_json
        save_json(self.path, {"window": {"x": 40000, "y": 40000,
                                         "w": 1200, "h": 700}})
        win = self._build()
        try:
            self.assertLess(win.root.winfo_x(), win.root.winfo_screenwidth())
        finally:
            win.root.destroy()

    def test_garbage_settings_do_not_break_the_window(self):
        from utils.prefs_io import save_json
        save_json(self.path, {"window": "nonsense", "chart_filter": "42H"})
        win = self._build()
        try:
            self.assertEqual(win.chart_filter, "LIVE")
        finally:
            win.root.destroy()


class TestServicesButtonsAreHonest(unittest.TestCase):

    def test_stop_is_called_stop(self):
        for lang, word in (("en", "Stop"), ("pl", "Zatrzymaj")):
            with open(os.path.join(_ROOT, "locales", f"{lang}.json"),
                      encoding="utf-8") as f:
                self.assertEqual(json.load(f)["services_manager"]["disable"], word)

    def test_failures_are_shown(self):
        with open(os.path.join(_ROOT, "ui", "pages", "services_manager.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn("services_manager.failed_title", src)
        self.assertIn("services_manager.until_restart", src)


if __name__ == "__main__":
    unittest.main()
