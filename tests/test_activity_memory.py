"""tests.test_activity_memory - history of CPU / RAM / GPU (2026-11-16).

Guards the Activity Memory feature and the two recording bugs found while
building it:

  1. hours and days were never rolled up when the app was closed before the
     boundary (5 hours and 11 days were missing in a real database), so the
     history had holes; aggregator.catch_up() fills them;
  2. without a sensor the scheduler stored `35 + cpu * 0.5` as the CPU
     temperature; now only measured values are stored, and old placeholder
     rows are recognised and hidden when read.

All data goes to synthetic dates in 2021 inside the test database
(PCW_APP_DIR from test_000_isolation) and is deleted afterwards.
"""
import os
import time
import unittest
from datetime import datetime

from hck_stats_engine.db_manager import db_manager
from hck_stats_engine.aggregator import aggregator
from hck_stats_engine import history as h

DAY = 86400
T0 = 1614556800.0                 # 2021-03-01 00:00 UTC
NOW = T0 + 16 * DAY               # "now" for the synthetic history


def _minute(conn, ts, cpu, ram=50.0, gpu=5.0, temp=None):
    conn.execute("""
        INSERT OR REPLACE INTO minute_stats
            (timestamp, cpu_avg, cpu_min, cpu_max, ram_avg, ram_min, ram_max,
             gpu_avg, gpu_min, gpu_max, cpu_temp, gpu_temp, sample_count)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,60)
    """, (ts, cpu, max(cpu - 5, 0), min(cpu + 10, 100), ram, ram - 2, ram + 2,
          gpu, gpu, gpu + 1, temp, None))


def _wipe(conn):
    a, b = T0 - DAY, NOW + DAY
    for tbl in ("minute_stats", "hourly_stats", "daily_stats",
                "process_hourly_stats", "process_daily_stats"):
        conn.execute(f"DELETE FROM {tbl} WHERE timestamp >= ? AND timestamp < ?", (a, b))
    for tbl in ("weekly_stats", "monthly_stats"):
        try:
            conn.execute(f"DELETE FROM {tbl} WHERE timestamp >= ? AND timestamp < ?", (a, b))
        except Exception:
            pass
    conn.commit()


class _HistoryCase(unittest.TestCase):
    """14 quiet days at 10 % CPU, then 2 busy days at 45 %.
    One minute row every 10 minutes."""

    @classmethod
    def setUpClass(cls):
        cls.conn = db_manager.get_connection()
        _wipe(cls.conn)
        ts = T0
        while ts < NOW:
            busy = ts >= NOW - 2 * DAY
            _minute(cls.conn, ts, 45.0 if busy else 10.0)
            ts += 600
        cls.conn.commit()
        cls.caught = aggregator.catch_up(now=NOW)

    @classmethod
    def tearDownClass(cls):
        _wipe(cls.conn)


class TestCatchUp(_HistoryCase):

    def test_every_complete_hour_and_day_is_rolled_up(self):
        hours, days = self.caught
        self.assertEqual(hours, 16 * 24)
        self.assertEqual(days, 16)
        n = self.conn.execute("SELECT COUNT(*) FROM hourly_stats WHERE timestamp >= ? "
                              "AND timestamp < ?", (T0, NOW)).fetchone()[0]
        self.assertEqual(n, 16 * 24)

    def test_second_run_finds_nothing(self):
        self.assertEqual(aggregator.catch_up(now=NOW), (0, 0))

    def test_day_uptime_is_recorded_time(self):
        # 144 rows x 60 samples = 2.4 h recorded per day, not 24 h
        up = self.conn.execute("SELECT uptime_minutes FROM daily_stats WHERE "
                               "timestamp = ?", (T0,)).fetchone()[0]
        self.assertEqual(up, 144)


class TestHistoryQueries(_HistoryCase):

    def test_resolution_follows_the_span(self):
        self.assertEqual(h.resolution_for(3600), "minute")
        self.assertEqual(h.resolution_for(7 * DAY), "hour")
        self.assertEqual(h.resolution_for(365 * DAY), "day")

    def test_series_and_stats(self):
        s = h.series("cpu", NOW - DAY, NOW)
        self.assertEqual(s["resolution"], "minute")
        self.assertEqual(len(s["points"]), 144)
        st = h.stats("cpu", NOW - DAY, NOW)
        self.assertAlmostEqual(st["avg"], 45.0, places=1)
        self.assertEqual(st["max"], 55.0)
        self.assertAlmostEqual(st["recorded_hours"], 2.4, places=1)

    def test_long_range_uses_hours_then_days(self):
        week = h.series("cpu", NOW - 7 * DAY, NOW)
        self.assertEqual(week["resolution"], "hour")
        self.assertEqual(len(week["points"]), 7 * 24)
        year = h.series("cpu", NOW - 365 * DAY, NOW)
        self.assertEqual(year["resolution"], "day")
        self.assertEqual(len(year["points"]), 16)

    def test_compare_previous(self):
        c = h.compare_previous("cpu", NOW - 2 * DAY, NOW)
        self.assertTrue(c["has_data"])
        self.assertAlmostEqual(c["delta"], 35.0, places=1)

    def test_recent_vs_usual_is_notable(self):
        r = h.recent_vs_usual("cpu", recent_days=2, usual_days=14, now=NOW)
        self.assertTrue(r["notable"], r)
        self.assertAlmostEqual(r["usual_avg"], 10.0, places=1)
        self.assertAlmostEqual(r["recent_avg"], 45.0, places=1)

    def test_steady_load_is_not_notable(self):
        r = h.recent_vs_usual("ram", recent_days=2, usual_days=14, now=NOW)
        self.assertFalse(r["notable"])

    def test_downsample_keeps_the_spike(self):
        pts = [{"ts": i, "avg": 5, "min": 0, "max": 10, "temp": None,
                "samples": 60} for i in range(1000)]
        pts[537]["max"] = 99
        out = h._downsample(pts, 50)
        self.assertLessEqual(len(out), 51)
        self.assertIn(99, [p["max"] for p in out])


class TestTemperatures(unittest.TestCase):

    def test_placeholder_formula_is_recognised(self):
        self.assertTrue(h._is_fake_cpu_temp(35 + 0.5 * 42.0, 42.0))
        self.assertTrue(h._is_fake_cpu_temp(round(35 + 0.5 * 17.3, 1), 17.3))
        self.assertFalse(h._is_fake_cpu_temp(63.0, 42.0))

    def test_fake_rows_are_hidden_real_rows_kept(self):
        conn = db_manager.get_connection()
        a = T0 - 3 * 3600
        try:
            _minute(conn, a, 40.0, temp=55.0)          # placeholder value
            _minute(conn, a + 60, 40.0, temp=71.0)     # measured
            conn.commit()
            pts = h.series("cpu", a, a + 120)["points"]
            self.assertEqual([p["temp"] for p in pts], [None, 71.0])
        finally:
            conn.execute("DELETE FROM minute_stats WHERE timestamp IN (?,?)", (a, a + 60))
            conn.commit()

    def test_scheduler_stores_only_measured_temps(self):
        import hck_gpt.data.live_sensors as ls
        from core.scheduler import _measured_temps
        orig = ls.snapshot
        try:
            ls.snapshot = lambda: {"cpu_temp": 52.0, "cpu_temp_src": "est",
                                   "gpu_temp": 61.0, "gpu_ok": True}
            self.assertEqual(_measured_temps(), (None, 61.0))
            ls.snapshot = lambda: {"cpu_temp": 66.0, "cpu_temp_src": "sensor",
                                   "gpu_temp": -1, "gpu_ok": False}
            self.assertEqual(_measured_temps(), (66.0, None))
        finally:
            ls.snapshot = orig

    def test_scheduler_has_no_placeholder_left(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "core", "scheduler.py"), encoding="utf-8") as f:
            code = "\n".join(l.split("#", 1)[0] for l in f)
        self.assertNotIn("35 + cpu_avg", code)


class TestTopProcesses(unittest.TestCase):

    def test_time_is_capped_by_recorded_time(self):
        """A browser has many processes: their seconds add up to more than
        the hour. The time shown never exceeds what was recorded."""
        conn = db_manager.get_connection()
        hr = time.time() - 3 * DAY
        hr = int(hr // 3600) * 3600
        try:
            conn.execute("""INSERT OR REPLACE INTO hourly_stats
                (timestamp, cpu_avg, cpu_min, cpu_max, cpu_p95, ram_avg, ram_min,
                 ram_max, gpu_avg, gpu_min, gpu_max, sample_count)
                VALUES (?,20,5,60,50,50,40,60,5,0,10,1800)""", (hr,))
            conn.execute("""INSERT INTO process_hourly_stats
                (timestamp, process_name, display_name, process_type, category,
                 cpu_avg, cpu_max, ram_avg_mb, ram_max_mb, sample_count, active_seconds)
                VALUES (?, 'zz_browser.exe', 'ZZ Browser', 'user', 'Browser',
                        4, 30, 900, 1200, 1800, 21600)""", (hr,))
            conn.commit()
            top = h.top_processes("cpu", hr, hr + 3600, 5, recorded_seconds=1800)
            zz = [p for p in top if p["process"] == "zz_browser.exe"][0]
            self.assertLessEqual(zz["active_hours"], 0.5)
            # 4 % per instance x 21600 s over 1800 s recorded = 48 %
            self.assertAlmostEqual(zz["value"], 48.0, places=1)
            self.assertEqual(h.top_processes("gpu", hr, hr + 3600), [])
        finally:
            conn.execute("DELETE FROM process_hourly_stats WHERE process_name='zz_browser.exe'")
            conn.execute("DELETE FROM hourly_stats WHERE timestamp=?", (hr,))
            conn.commit()


class TestHckGptTrend(unittest.TestCase):

    def test_message_links_to_activity_memory(self):
        from hck_gpt.memory.proactive_monitor import ProactiveMonitor
        m = ProactiveMonitor.__new__(ProactiveMonitor)
        r = {"recent_days": 2, "recent_avg": 45.0, "usual_avg": 10.0, "delta": 35.0}
        m._lang = "en"
        self.assertIn("[-> CPU History]", m.history_trend_message("cpu", r))
        m._lang = "pl"
        msg = m.history_trend_message("cpu", r)
        self.assertIn("[-> Historia CPU]", msg)
        self.assertIn("45%", msg)
        self.assertIn("10%", msg)

    def test_policy_lets_it_through_in_balanced_mode(self):
        from hck_gpt.memory.proactive_policy import ProactivePolicy
        self.assertTrue(ProactivePolicy.decide("history_trend", "balanced").allowed)

    def test_links_are_registered_in_the_main_window(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "ui", "windows", "main_window_expanded.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn('f"{_c.upper()} History", f"Historia {_c.upper()}"', src)
        self.assertIn("self._make_card_clickable(card, key)", src)
        self.assertIn('page_id.startswith("activity_")', src)


class TestPageHelpers(unittest.TestCase):

    def test_ticks_stay_inside_and_are_ordered(self):
        from ui.pages.activity_memory import time_ticks
        now = time.time()
        for span in (3600, DAY, 7 * DAY, 30 * DAY, 90 * DAY, 365 * DAY, 4 * 365 * DAY):
            ticks = time_ticks(now - span, now, 8)
            self.assertTrue(ticks, span)
            self.assertLessEqual(len(ticks), 12, span)
            ts = [t for t, _ in ticks]
            self.assertEqual(ts, sorted(ts))
            self.assertTrue(all(now - span <= t <= now for t in ts))

    def test_gaps_split_the_line(self):
        from ui.pages.activity_memory import segments
        pts = [{"ts": t} for t in (0, 60, 120, 3600, 3660)]
        self.assertEqual([len(s) for s in segments(pts, "minute")], [3, 2])


class TestPageBuilds(_HistoryCase):

    def test_page_shows_the_busy_days(self):
        import tkinter as tk
        from utils import i18n
        from ui.pages import activity_memory as am
        lang = i18n.get_lang()
        i18n.set_lang("en")
        root = tk.Tk()
        root.geometry("980x545")
        try:
            settings = os.path.join(os.environ.get("PCW_APP_DIR", "."), "settings",
                                    "app_settings.json")

            class App:
                _activity_state = {"span": "24H", "end": NOW, "temp": True}

                @staticmethod
                def _app_settings_file():
                    return settings

                def _cpu_marketing_name(self):
                    return "Test CPU"

                def _gpu_name_nonblocking(self):
                    return "Test GPU"

                def _switch_to_page(self, pid):
                    self.switched = pid

            app = App()
            page = am.build_activity_memory_page(app, root, "cpu")
            deadline = time.time() + 20
            while page._result is None and time.time() < deadline:
                root.update()
                time.sleep(0.02)
            self.assertIsNotNone(page._result, "history never loaded")
            root.update()
            self.assertEqual(page.tiles["avg"][1].cget("text"), "45.0%")
            self.assertEqual(len(page.chart.points), 144)
            # two periods back (the busy stretch is 2 days) are the quiet days
            for target in (NOW - DAY, NOW - 2 * DAY):
                page._step(-1)
                deadline = time.time() + 20
                while abs(page._result["end"] - target) > 1 and time.time() < deadline:
                    root.update()
                    time.sleep(0.02)
                self.assertAlmostEqual(page._result["end"], target, delta=1)
            self.assertEqual(page.tiles["avg"][1].cget("text"), "10.0%")
            a = datetime.fromtimestamp(NOW - 3 * DAY)
            self.assertIn(f"{a.day} Mar", page.period_lbl.cget("text"))
            # component switch goes through the router
            page._switch_comp("ram")
            self.assertEqual(app.switched, "activity_ram")
        finally:
            root.destroy()
            i18n.set_lang(lang)


if __name__ == "__main__":
    unittest.main()
