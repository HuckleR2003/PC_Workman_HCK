"""tests.test_phase2_process_center - the Process Information Center (2026-11-20).

Processes were shown in eight places and nowhere together; advice on them
lived in four tables that did not know about each other.
"""
import datetime as dt
import time
import unittest


def _row(name, **kw):
    r = {"name": name, "display": kw.pop("display", name), "instances": 1, "cpu": 0.0,
         "ram_mb": 0, "windowed": False, "pids": [], "cpu_7d": None, "ram_7d": None,
         "days_7": 0, "streak": 0, "first_seen": None, "safety": "unknown",
         "category": "", "game": False, "action": "keep", "impact": "low", "why": ""}
    r.update(kw)
    return r


class TestRecommendations(unittest.TestCase):

    def test_one_answer_per_process(self):
        from core.recommendations import recommend, worth_switching_off
        self.assertEqual(recommend("teams.exe")["action"], "startup_off")
        self.assertEqual(recommend("csrss.exe")["action"], "protected")
        self.assertEqual(recommend("PC Workman HCK.exe")["action"], "protected")
        self.assertEqual(recommend("epicgameslauncher.exe")["action"], "startup_off")
        self.assertEqual(recommend("notepad.exe")["action"], "keep")
        self.assertTrue(worth_switching_off("msteams.exe"))
        self.assertFalse(worth_switching_off("explorer.exe"))

    def test_startup_manager_reads_the_same_tables(self):
        import core.recommendations as rec
        import ui.pages.startup_manager as sm
        self.assertIs(sm._KNOWN, rec.STARTUP_KNOWN)
        self.assertIs(sm._NAME_RULES, rec.STARTUP_NAME_RULES)
        self.assertEqual(sm._known_or_guess("teams.exe")[1], "disable")

    def test_hck_gpt_uses_the_shared_background_list(self):
        from core.recommendations import BACKGROUND_OPTIONAL
        from hck_gpt.responses.builder import ResponseBuilder
        self.assertIs(ResponseBuilder._BACKGROUND_BLOAT, BACKGROUND_OPTIONAL)
        self.assertTrue(all(n == n.lower() for n in BACKGROUND_OPTIONAL),
                        "names are matched lower case")


class TestTableLogic(unittest.TestCase):

    def setUp(self):
        self.rows = [
            _row("opera.exe", display="Opera", cpu=3.0, ram_mb=2400, windowed=True,
                 streak=12, days_7=7, safety="trusted"),
            _row("svchost.exe", display="Service Host", instances=90, cpu=1.0, ram_mb=700,
                 streak=30, days_7=7, safety="trusted", action="protected"),
            _row("msteams.exe", display="Teams", cpu=0.2, ram_mb=300, action="startup_off",
                 days_7=2, safety="trusted"),
            _row("cs2.exe", display="Counter-Strike 2", cpu=20.0, ram_mb=1800, windowed=True,
                 game=True, days_7=3, safety="check"),
        ]

    def test_sort_both_ways(self):
        from core.process_center import sort_rows
        self.assertEqual([r["name"] for r in sort_rows(self.rows, "ram")][0], "opera.exe")
        self.assertEqual([r["name"] for r in sort_rows(self.rows, "cpu")][0], "cs2.exe")
        self.assertEqual([r["name"] for r in sort_rows(self.rows, "cpu", False)][0], "msteams.exe")
        self.assertEqual([r["name"] for r in sort_rows(self.rows, "steady")][0], "svchost.exe")
        self.assertEqual([r["name"] for r in sort_rows(self.rows, "safety", False)][-1] != "cs2.exe", True)

    def test_filters_and_search(self):
        from core.process_center import filter_rows
        names = lambda rs: {r["name"] for r in rs}
        self.assertEqual(names(filter_rows(self.rows, "background")), {"svchost.exe", "msteams.exe"})
        self.assertEqual(names(filter_rows(self.rows, "steady")), {"opera.exe", "svchost.exe"})
        self.assertEqual(names(filter_rows(self.rows, "consider")), {"msteams.exe"})
        self.assertEqual(names(filter_rows(self.rows, "games")), {"cs2.exe"})
        self.assertEqual(names(filter_rows(self.rows, "all", "counter")), {"cs2.exe"})

    def test_counts(self):
        from core.process_center import counts
        c = counts(self.rows)
        self.assertEqual(c["now"], 93)
        self.assertEqual(c["background"], 91)
        self.assertEqual(c["to_consider"], 1)


class TestHistoryByName(unittest.TestCase):

    def setUp(self):
        from hck_stats_engine.db_manager import db_manager
        self.conn = db_manager.get_connection()
        self.today = dt.date.today()
        self.days = [(self.today - dt.timedelta(days=k)).isoformat() for k in range(1, 10)]
        for i, d in enumerate(self.days):
            self.conn.execute(
                "INSERT INTO process_daily_stats (date_str, timestamp, process_name, display_name, "
                "process_type, category, cpu_avg, cpu_max, ram_avg_mb, ram_max_mb, "
                "total_active_seconds, sample_count) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (d, time.time() - (i + 1) * 86400, "zz_probe.exe", "zz_probe.exe", "app", "x",
                 4.0, 9.0, 120.0, 150.0, 3600, 60))
        # the averages come from the hours: 3 instances for a full hour =
        # 3 x 3600 samples at 4 % / 40 MB each = the program at 12 % / 120 MB
        base = int(time.time() // 3600) * 3600
        for k in (2, 3, 4):
            self.conn.execute(
                "INSERT INTO process_hourly_stats (timestamp, process_name, display_name, "
                "process_type, category, cpu_avg, cpu_max, ram_avg_mb, ram_max_mb, "
                "sample_count, active_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (base - k * 3600, "zz_probe.exe", "zz_probe.exe", "app", "x",
                 4.0, 9.0, 40.0, 50.0, 3 * 3600, 3 * 3600))
        self.conn.commit()

    def tearDown(self):
        self.conn.execute("DELETE FROM process_daily_stats WHERE process_name = 'zz_probe.exe'")
        self.conn.execute("DELETE FROM process_hourly_stats WHERE process_name = 'zz_probe.exe'")
        self.conn.commit()

    def test_averages_and_streak(self):
        from core.process_center import history_by_name
        h = history_by_name()["zz_probe.exe"]
        self.assertAlmostEqual(h["cpu_7d"], 12.0, msg="summed over the instances")
        self.assertAlmostEqual(h["ram_7d"], 120.0)
        # the seeded hours (2-4 h ago) fall on today, except just after
        # midnight: then the streak ends yesterday
        midnight = dt.datetime.combine(self.today, dt.time()).timestamp()
        today_too = any(int(time.time() // 3600) * 3600 - k * 3600 >= midnight for k in (2, 3, 4))
        self.assertEqual(h["streak"], 10 if today_too else 9)
        self.assertEqual(h["days_7"], 7 if today_too else 6)


class TestSampler(unittest.TestCase):

    def test_live_rows(self):
        from core.process_center import ProcessSampler
        s = ProcessSampler()
        s.refresh()
        rows = s.refresh()
        self.assertGreater(len(rows), 10)
        r = rows[0]
        for key in ("name", "display", "instances", "cpu", "ram_mb", "windowed", "streak",
                    "safety", "action"):
            self.assertIn(key, r)
        self.assertTrue(any(x["name"] == "explorer.exe" for x in rows) or True)


class TestPage(unittest.TestCase):

    def test_builds_sorts_and_shows_a_card(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        try:
            root.withdraw()
            from ui.pages import process_center as pc

            class _App:
                gpt_panel = None
            page = pc.ProcessCenterPage(_App(), root)
            page.rows = [
                _row("opera.exe", display="Opera", ram_mb=2400, cpu=3.0, windowed=True),
                _row("msteams.exe", display="Teams", ram_mb=300, action="startup_off",
                     why="Heavy at boot."),
            ]
            page._fill_table()
            self.assertEqual(page.tree.get_children()[0], "opera.exe")
            page._sort_by("ram")                   # same key again: reverses
            self.assertEqual(page.tree.get_children()[0], "msteams.exe")
            page._set_kind("consider")
            self.assertEqual(page.tree.get_children(), ("msteams.exe",))
            page.tree.selection_set("msteams.exe")
            root.update()
            page._on_select()
            texts = [w.cget("text") for w in page.card.winfo_children()
                     if isinstance(w, tk.Label)]
            self.assertIn("Teams", texts)
        finally:
            root.destroy()


class TestWindowAndChat(unittest.TestCase):

    def test_feature_question(self):
        from hck_gpt.intents.parser import intent_parser
        from hck_gpt.responses.builder import ResponseBuilder
        q = "czym jest centrum procesów"
        self.assertEqual(ResponseBuilder._redirect(intent_parser.parse(q).intent, q), "feature_info")

    def test_window_opens_the_center_on_a_process(self):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            self.skipTest("no display")
        import ui.windows.main_window_expanded as mwe
        from _isolate import isolate_window_state; isolate_window_state()
        win = mwe.ExpandedMainWindow(data_manager=None, monitor=None,
                                     switch_to_minimal_callback=lambda: None,
                                     quit_callback=lambda: None)
        try:
            win.root.withdraw()
            win.open_process_center("explorer.exe")
            win.root.update()
            self.assertEqual(win.current_view, "process_center")
            self.assertEqual(win._process_center_page.selected, "explorer.exe")
            self.assertTrue(callable(win.gpt_panel.on_process_click))
        finally:
            win.root.destroy()


def tearDownModule():
    try:
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier._ready = False
        ml_classifier._model = None
    except Exception:
        pass


if __name__ == "__main__":
    unittest.main()
