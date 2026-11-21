"""tests.test_learning_and_periods - group B after the long test (2026-11-16).

  - load periods: 40 min of GPU at 95-99 % in BeamNG left no event, because
    the spike check compares a minute with the 5 minutes before it;
  - games: BeamNG was on no list ("Expected?" about a game);
  - learning: one sample per 5 minutes, so the "about 6 hours" card was
    wrong; now one sample per recorded minute;
  - RAM: "RAM at 90%" nine times in two hours on a PC where that is normal;
  - sleep: holes in the history with no explanation;
  - laptop or desktop: neither detected nor remembered.
"""
import os
import sqlite3
import tempfile
import time
import unittest

from hck_stats_engine.db_manager import db_manager

T0 = 1609459200.0          # 2021-01-01, far from any real data


def _wipe_events():
    c = db_manager.get_connection()
    c.execute("DELETE FROM events WHERE timestamp >= ? AND timestamp < ?",
              (T0 - 86400, T0 + 86400))
    c.commit()


class TestLoadPeriods(unittest.TestCase):

    def setUp(self):
        _wipe_events()

    def tearDown(self):
        _wipe_events()

    def _feed(self, tracker, gpu_values, start=T0, game="BeamNG.drive"):
        for i, g in enumerate(gpu_values):
            tracker.on_minute(start + i * 60, {"cpu": 40.0, "gpu": g},
                              {"gpu": 60.0 + g / 10}, top_process="opera.exe",
                              game=game if g > 60 else None)

    def test_slow_ramp_is_one_period_with_the_game(self):
        from hck_stats_engine.load_periods import LoadPeriodTracker, periods
        tr = LoadPeriodTracker()
        ramp = [5, 15, 30, 45, 60, 75, 85, 90, 95, 97, 98, 99, 97, 96, 98, 97,
                95, 30, 20, 10, 5]
        self._feed(tr, ramp)
        found = periods(T0 - 3600, T0 + 7200, "gpu")
        self.assertEqual(len(found), 1, found)
        p = found[0]
        self.assertEqual(p["process_name"], "BeamNG.drive")
        self.assertGreaterEqual(p["peak"], 99)
        self.assertGreaterEqual(p["minutes"], 10)
        self.assertIn("max", p["description"])          # measured GPU temperature
        self.assertEqual(periods(T0 - 3600, T0 + 7200, "cpu"), [])

    def test_sleep_gap_closes_the_period(self):
        from hck_stats_engine.load_periods import LoadPeriodTracker, periods
        tr = LoadPeriodTracker()
        self._feed(tr, [95] * 6)
        self._feed(tr, [95] * 6, start=T0 + 3 * 3600)    # after a 3 h gap
        self.assertEqual(len(periods(T0 - 3600, T0 + 6 * 3600, "gpu")), 2)

    def test_spike_list_does_not_show_periods(self):
        from hck_stats_engine.load_periods import LoadPeriodTracker
        from hck_stats_engine import history
        tr = LoadPeriodTracker()
        self._feed(tr, [95] * 6)
        self.assertEqual(history.events("gpu", T0 - 3600, T0 + 3600), [])

    def test_wired_into_the_minute_tick(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "core", "scheduler.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("load_period_tracker.on_minute(", src)


class TestGameDetect(unittest.TestCase):

    def test_store_library_paths(self):
        from core.game_detect import is_game, display_name
        self.assertTrue(is_game(
            "beamng.test.exe",
            exe_path=r"D:\SteamLibrary\steamapps\common\BeamNG.drive\Bin64\beamng.test.exe"))
        self.assertTrue(is_game(
            "somegame.exe", exe_path=r"C:\Program Files\Epic Games\X\somegame.exe"))
        self.assertFalse(is_game("steam.exe", exe_path=r"C:\Program Files (x86)\Steam\steam.exe"))
        self.assertFalse(is_game("notepad_x.exe", exe_path=r"C:\Windows\notepad_x.exe"))
        self.assertEqual(display_name("BeamNG.drive.x64.exe"), "BeamNG.drive")

    def test_game_is_not_a_process_spike(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "hck_gpt", "memory", "proactive_monitor.py"),
                  encoding="utf-8") as f:
            src = f.read()
        block = src[src.index("if pcpu < PROC_SPIKE_PCT:"):]
        block = block[:block.index('self._alert("process_spike", pname)')]
        self.assertIn("is_game(pname, pid=pid)", block)


class TestLearningFromMinutes(unittest.TestCase):

    def setUp(self):
        import core.thermal_baseline as tbm
        self.tbm = tbm
        self.d = tempfile.mkdtemp()
        db = os.path.join(self.d, "s.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE minute_stats (timestamp REAL, cpu_avg REAL, "
                    "gpu_avg REAL, cpu_temp REAL, gpu_temp REAL)")
        for i in range(240):                       # 4 hours idle
            cpu = 6.0
            con.execute("INSERT INTO minute_stats VALUES (?,?,?,?,?)",
                        (T0 + i * 60, cpu, 3.0, 35 + cpu * 0.5, 42.0))
        con.commit()
        con.close()
        self._old = (tbm._DB_PATH, tbm._PREFS_PATH)
        tbm._DB_PATH = db
        tbm._PREFS_PATH = os.path.join(self.d, "tb.json")
        self.tb = tbm.ThermalBaseline()
        self.tb.rebuild(force=True)

    def tearDown(self):
        self.tbm._DB_PATH, self.tbm._PREFS_PATH = self._old

    def test_one_sample_per_minute(self):
        self.assertAlmostEqual(self.tb.total_observed_hours(), 4.0, places=1)
        idle = self.tb.get_range("idle", "gpu_temp")
        self.assertEqual(idle.n, 240)
        self.assertEqual(idle.training_level, "trained")     # 3 h of idle

    def test_placeholder_cpu_temperature_is_not_learned(self):
        self.assertEqual(self.tb._metric_total("cpu_temp"), 0)

    def test_percent_is_about_the_workloads_that_occur(self):
        # only idle occurred, and it is past "trained": fully learned so far
        self.assertEqual(self.tb.overall_training_pct(), 100)


class TestRamNorm(unittest.TestCase):

    def _monitor(self, norm):
        from hck_gpt.memory.proactive_monitor import ProactiveMonitor
        m = ProactiveMonitor()
        m._lang = "pl"
        m._ram_norm = lambda: norm
        self.alerts, self.notes = [], []
        m._alert = lambda ev, val, urgent=False: self.alerts.append(ev)
        m._maybe_ram_norm_note = lambda n: self.notes.append(n)
        return m

    def _check(self, m, ram):
        """Run only the RAM-high branch of _check_system."""
        from hck_gpt.memory import proactive_monitor as pm
        if ram >= pm.RAM_HIGH_PCT and ram < pm.RAM_CRIT_PCT:
            norm = m._ram_norm()
            if norm is None or ram > norm["p95"] + 3:
                m._alert("ram_high", f"{ram:.0f}")
            else:
                m._maybe_ram_norm_note(norm)

    def test_within_this_pcs_normal_gives_one_note(self):
        m = self._monitor({"avg": 86.0, "p95": 91.0, "hours": 20})
        self._check(m, 90.0)
        self.assertEqual(self.alerts, [])
        self.assertEqual(len(self.notes), 1)

    def test_above_normal_still_alerts(self):
        m = self._monitor({"avg": 70.0, "p95": 80.0, "hours": 20})
        self._check(m, 90.0)
        self.assertEqual(self.alerts, ["ram_high"])

    def test_branch_in_the_monitor_matches(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               "hck_gpt", "memory", "proactive_monitor.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn('if norm is None or ram > norm["p95"] + 3:', src)

    def test_note_names_the_norm_and_links(self):
        from hck_gpt.memory.proactive_monitor import ProactiveMonitor
        m = ProactiveMonitor()
        m._lang = "pl"
        msg = m.ram_norm_message({"avg": 86.0, "p95": 91.0, "hours": 20})
        self.assertIn("86%", msg)
        self.assertIn("91%", msg)
        self.assertIn("[-> Upgrade Readiness]", msg)


class TestSleep(unittest.TestCase):

    def tearDown(self):
        _wipe_events()

    def test_sleep_is_recorded_and_found(self):
        from core.scheduler import _record_sleep
        from hck_stats_engine.load_periods import sleeps
        _record_sleep(T0, T0 + 3 * 3600 + 13 * 60)
        found = sleeps(T0 - 60, T0 + 4 * 3600)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["end"] - found[0]["start"], 11580, delta=1)


class TestMachineType(unittest.TestCase):

    def test_phrases(self):
        from core.machine_type import from_message
        self.assertEqual(from_message("Dzieki, jak cos mam PC"), "desktop")
        self.assertEqual(from_message("mam laptopa"), "laptop")
        self.assertEqual(from_message("to jest stacjonarka"), "desktop")
        self.assertEqual(from_message("I have a laptop"), "laptop")
        self.assertIsNone(from_message("czy mam dobre gpu?"))
        self.assertIsNone(from_message("mam pc workmana od wczoraj"))

    def test_chat_remembers_it(self):
        from hck_gpt.chat_handler import ChatHandler
        from core import machine_type
        h = ChatHandler()
        out = h.process_message("Dzieki, jak cos mam PC", ui_lang="pl")
        self.assertIn("stacjonarny", out[0])
        self.assertEqual(machine_type.get(), "desktop")
        h.process_message("mam laptopa", ui_lang="pl")
        self.assertEqual(machine_type.get(), "laptop")


if __name__ == "__main__":
    unittest.main()
