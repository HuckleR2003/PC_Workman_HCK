"""tests.test_phase1_foundations - phase 1 of the big update (2026-11-20).

  * navigation history and "← Back" (no page had a way back to where the
    user came from);
  * one process reference for every list of processes;
  * every game recorded, light ones too (only GPU >= 60 % left a trace);
  * the number of processes in the minute history;
  * one gradient banner for page headers.
"""
import datetime as dt
import os
import time
import unittest


class TestNavHistory(unittest.TestCase):

    def test_push_pop_dedupe_limit(self):
        from ui.components.nav_history import NavHistory
        h = NavHistory(limit=3)
        h.push(("page", "dashboard", None))
        h.push(("page", "dashboard", None))
        self.assertEqual(len(h), 1, "the same place twice in a row is one step")
        for p in ("a", "b", "c"):
            h.push(("page", p, None))
        self.assertEqual(len(h), 3)
        self.assertEqual(h.pop()[1], "c")
        h.push(None)
        h.push(("page", "", None))
        self.assertEqual(len(h), 2)

    def test_labels(self):
        from ui.components.nav_history import label
        self.assertEqual(label(("overlay", "your_pc", "components"), "pl"), "Mój PC")
        self.assertEqual(label(("page", "startup_manager", None), "en"), "Startup Manager")
        self.assertEqual(label(None), "")


class TestBackInTheWindow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        from _isolate import isolate_window_state; isolate_window_state()
        cls.win = mwe.ExpandedMainWindow(
            data_manager=None, monitor=None,
            switch_to_minimal_callback=lambda: None, quit_callback=lambda: None)
        cls.win.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _pump(self, s=0.6):
        end = time.time() + s
        while time.time() < end:
            self.win.root.update()

    def test_back_returns_to_my_pc_on_the_same_tab(self):
        win = self.win
        win._handle_sidebar_navigation("my_pc")
        self._pump()
        from ui.components import yourpc_page as yp
        yp._show_tab(win, "components")
        win._handle_sidebar_navigation("optimization")
        self._pump()
        win._handle_sidebar_navigation("optimization", "startup_mgr")
        self._pump()
        self.assertEqual(win._nav_last[1], "startup_manager")
        win.go_back()
        self._pump()
        self.assertEqual(win._nav_last[1], "optimization")
        win.go_back()
        self._pump()
        self.assertEqual(win.active_overlay, "your_pc")
        self.assertEqual(win.yourpc_active_tab, "components")
        win.go_back()
        self._pump()
        self.assertEqual(win.current_view, "dashboard")
        self.assertIsNone(win.active_overlay)
        self.assertEqual(len(win._nav_hist()), 0)
        self.assertFalse(win.sidebar._back_row.winfo_manager(),
                         "no back row when there is nowhere to go")


class TestProcessHistory(unittest.TestCase):

    def test_streak_and_week(self):
        from core.process_history import summarize, describe
        today = dt.date(2026, 11, 20)
        days = {(today - dt.timedelta(days=k)).isoformat() for k in range(1, 13)}
        info = summarize(days, today)
        self.assertEqual(info["streak"], 12, "a streak may end yesterday")
        self.assertEqual(info["days_7"], 6)
        self.assertFalse(info["today"])
        self.assertIn("12", describe(info, "pl"))
        some = summarize({"2026-11-20", "2026-11-17", "2026-11-14"}, today)
        self.assertEqual(some["streak"], 1)
        self.assertEqual(some["days_7"], 3, "20, 17 and 14 Nov are all in the 7 days")
        self.assertEqual(summarize(set(), today)["first_seen"], None)


class TestProcessRef(unittest.TestCase):

    def test_known_and_unknown(self):
        from ui.components.process_ref import card_lines
        title, lines = card_lines("explorer.exe")
        self.assertTrue(lines)
        self.assertNotEqual(title, "")
        _, lines = card_lines("definitely-not-a-real-process-xyz.exe")
        self.assertTrue(any("bazie" in l or "library" in l for l in lines))

    def test_rows_in_activity_memory_point_at_processes(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "ui", "pages", "activity_memory.py"), encoding="utf-8").read()
        self.assertIn("process_ref.bind(", src)


class TestGameSessions(unittest.TestCase):

    def setUp(self):
        from hck_stats_engine.game_sessions import GameSessionRecorder
        self.rec = GameSessionRecorder()
        self.t0 = time.time() - 3600

    def tearDown(self):
        from hck_stats_engine.db_manager import db_manager
        conn = db_manager.get_connection()
        conn.execute("DELETE FROM events WHERE event_type='game_session' AND timestamp >= ?",
                     (self.t0 - 10,))
        conn.commit()

    def test_a_light_game_is_recorded_once(self):
        from hck_stats_engine.game_sessions import sessions
        r, t0 = self.rec, self.t0
        r.on_game_event("start", "beamng.drive.exe", now=t0)
        r.on_game_event("start", "BeamNG.drive.x64.exe", now=t0 + 5)
        r.on_game_event("tick", "beamng.drive.exe", now=t0 + 120)
        r.on_game_event("end", "beamng.drive.x64.exe", now=t0 + 600)
        self.assertEqual(len(sessions(t0 - 1, t0 + 3600)), 1, "one game, one session")
        r.on_game_event("end", "beamng.drive.exe", now=t0 + 1500)
        s = sessions(t0 - 1, t0 + 3600)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["minutes"], 25)
        self.assertIn("beamng", s[0]["process_name"].lower())

    def test_tick_moves_the_end_so_a_crash_leaves_the_row(self):
        from hck_stats_engine.game_sessions import sessions
        r, t0 = self.rec, self.t0
        r.on_game_event("start", "StardewValley.exe", now=t0)
        r.on_game_event("tick", "StardewValley.exe", now=t0 + 30)     # too soon
        r.on_game_event("tick", "StardewValley.exe", now=t0 + 300)
        s = sessions(t0 - 1, t0 + 3600)[0]
        self.assertEqual(s["minutes"], 5)

    def test_recent_events_name_the_game(self):
        from ui.pages.monitoring_alerts import _event_message
        msg = _event_message({"event_type": "game_session", "process_name": "PlateUp",
                              "description": "42 min"})
        self.assertIn("PlateUp", msg)
        self.assertIn("42 min", msg)


class TestProcessCount(unittest.TestCase):

    def test_columns_exist_and_a_minute_records_it(self):
        from hck_stats_engine.db_manager import db_manager
        from hck_stats_engine.aggregator import aggregator as stats_aggregator
        conn = db_manager.get_connection()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(minute_stats)")}
        self.assertIn("proc_count", cols)
        hcols = {r[1] for r in conn.execute("PRAGMA table_info(hourly_stats)")}
        self.assertTrue({"proc_avg", "proc_max"} <= hcols)
        ts = int(time.time() // 60) * 60 - 7 * 86400 + 13      # far from real minutes
        try:
            stats_aggregator._insert_minute_stats(ts, 10, 50, 5, [10], [50], [5])
            n = conn.execute("SELECT proc_count FROM minute_stats WHERE timestamp = ?",
                             (ts,)).fetchone()[0]
            self.assertGreater(n, 10)
        finally:
            conn.execute("DELETE FROM minute_stats WHERE timestamp = ?", (ts,))
            conn.commit()


class TestHeroBanner(unittest.TestCase):

    def test_builds_with_two_buttons(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        try:
            root.withdraw()
            from ui.components.hero_banner import hero_banner
            clicked = []
            cv = hero_banner(root, "Gaming", "subtitle",
                             buttons=[("Start", lambda: clicked.append(1), True),
                                      ("Mini", lambda: None, False),
                                      ("third is dropped", lambda: None, False)])
            root.update()
            holder = [w for w in cv.winfo_children()][0]
            self.assertEqual(len(holder.winfo_children()), 2)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
