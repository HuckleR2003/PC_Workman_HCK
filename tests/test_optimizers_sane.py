"""tests.test_optimizers_sane
The optimization engines must do what they say, and undo it (2026-11-14).

Found by reading every engine against one question: "what happens after an
hour, and what happens if PC Workman dies in the middle?"

  1. Auto RAM Flush had no pause. Above the threshold it trimmed every
     process about once a minute, forever, which slows a PC down.
  2. Turbo Power Plan could record "Turbo PC" as the plan to go back to
     (after a crash), so switching it off never left Turbo PC.
  3. App Hibernation kept its list in memory and woke nothing on exit: a
     frozen app stayed frozen until reboot.
  4. The master TURBO switch reported "1 fired" with nothing armed.
"""
import inspect
import json
import os
import subprocess
import tempfile
import time
import unittest
from unittest import mock

import psutil

BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
TURBO = "11111111-2222-3333-4444-555555555555"
MINE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


class TestRamFlushCooldown(unittest.TestCase):

    def test_useful_flush_gets_the_normal_pause(self):
        import core.auto_optimizer as ao
        self.assertEqual(ao.next_cooldown(0, 800), ao.COOLDOWN_S)
        self.assertEqual(ao.next_cooldown(1200, 800), ao.COOLDOWN_S)

    def test_useless_flush_backs_off(self):
        import core.auto_optimizer as ao
        first = ao.next_cooldown(0, 20)
        second = ao.next_cooldown(first, 20)
        self.assertGreater(first, ao.COOLDOWN_S)
        self.assertGreater(second, first)

    def test_back_off_has_a_ceiling(self):
        import core.auto_optimizer as ao
        pause = 0
        for _ in range(12):
            pause = ao.next_cooldown(pause, -50)
        self.assertEqual(pause, ao.COOLDOWN_MAX_S)

    def test_pause_is_at_least_minutes_not_seconds(self):
        import core.auto_optimizer as ao
        self.assertGreaterEqual(ao.COOLDOWN_S, 120)
        self.assertGreater(ao.COOLDOWN_S, ao.TRIGGER_S)

    def test_the_loop_honours_it(self):
        import core.auto_optimizer as ao
        src = inspect.getsource(ao.AutoOptimizer._loop)
        self.assertIn("_next_auto_ts", src)
        self.assertIn("next_cooldown", src)

    def test_loop_flushes_once_then_waits(self):
        """Drive the real loop with RAM pinned above the threshold: one
        flush, then cooldown ticks. Before the fix this flushed on every
        third tick for as long as the loop ran."""
        import core.auto_optimizer as ao
        opt = ao.AutoOptimizer.__new__(ao.AutoOptimizer)
        ao.AutoOptimizer.__init__(opt)
        opt._ram_auto = True
        opt._tpp_recovered = True
        flushes = []
        ticks = {"n": 0}

        def fake_wait(_s):
            ticks["n"] += 1
            if ticks["n"] >= 40:                    # 40 ticks = 400 s of loop
                opt._stop.set()
            return False

        opt._stop.wait = fake_wait
        vm = mock.MagicMock(percent=92.0)
        with mock.patch("psutil.virtual_memory", return_value=vm), \
                mock.patch.object(opt, "flush_now",
                                  side_effect=lambda: flushes.append(1)
                                  or (True, "Freed 300 MB", 1000, 1300)), \
                mock.patch.object(opt, "_tpp_tick"):
            opt._loop()
        self.assertEqual(len(flushes), 1,
                         f"{len(flushes)} flushes in 40 ticks of high RAM")
        self.assertGreater(opt._next_auto_ts, time.time())


class TestPowerPlanGoesBack(unittest.TestCase):

    def test_normal_case_keeps_the_users_plan(self):
        from core.auto_optimizer import pick_original_plan
        self.assertEqual(pick_original_plan(MINE, TURBO, None), MINE)

    def test_turbo_is_never_the_plan_to_return_to(self):
        """After a crash the machine is still on Turbo PC."""
        from core.auto_optimizer import pick_original_plan
        self.assertEqual(pick_original_plan(TURBO, TURBO, MINE), MINE)
        self.assertEqual(pick_original_plan(TURBO.upper(), TURBO, None),
                         BALANCED)
        self.assertEqual(pick_original_plan(TURBO, TURBO, TURBO), BALANCED)

    def test_nothing_known_falls_back_to_balanced(self):
        from core.auto_optimizer import pick_original_plan
        self.assertEqual(pick_original_plan(None, None, None), BALANCED)

    def test_original_plan_is_written_to_disk_and_recovered(self):
        import core.auto_optimizer as ao
        self.assertIn("_state_update(tpp_original=",
                      inspect.getsource(ao.AutoOptimizer.tpp_activate))
        self.assertIn("_tpp_recover",
                      inspect.getsource(ao.AutoOptimizer._loop))

    def test_state_file_merge_keeps_other_keys(self):
        """turbo_state.json is shared with the service manager."""
        import core.auto_optimizer as ao
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"svc_stopped": {"WSearch": "running"}}, f)
            with mock.patch.object(ao, "_STATE_PATH", path):
                ao._state_update(tpp_original=MINE)
                self.assertEqual(ao._state_read(),
                                 {"svc_stopped": {"WSearch": "running"},
                                  "tpp_original": MINE})
                ao._state_update(tpp_original=None)
                self.assertEqual(ao._state_read(),
                                 {"svc_stopped": {"WSearch": "running"}})
        finally:
            os.remove(path)


class TestTurboFlagSurvivesRestart(unittest.TestCase):

    def test_daemon_reads_the_master_flag_at_start(self):
        import core.auto_optimizer as ao
        opt = ao.AutoOptimizer.__new__(ao.AutoOptimizer)
        import threading
        opt._lock = threading.Lock()
        with mock.patch.object(ao, "_load_prefs_full",
                               return_value={"turbo_active": True,
                                             "optimization": {
                                                 "ram_on_turbo": True}}):
            opt.reload_prefs()
        self.assertTrue(opt._turbo_on)
        self.assertTrue(opt._ram_watch_active(),
                        "RAM-on-TURBO was dead after every restart")


class TestMasterSwitchIsHonest(unittest.TestCase):

    def test_no_fixed_success_entry(self):
        from ui.pages import optimization_services as osvc
        src = inspect.getsource(osvc.set_turbo_active)
        self.assertNotIn('("App Hibernation + Services", True)', src)
        self.assertIn('("Service Stop", admin)', src)

    def test_power_plan_is_not_switched_on_the_ui_thread(self):
        from ui.pages import optimization_services as osvc
        src = inspect.getsource(osvc.set_turbo_active)
        worker = src[src.index("def _turbo_workers"):]
        before = src[:src.index("def _turbo_workers")]
        self.assertIn("_tpp_run()", worker)
        self.assertNotIn("_tpp_run()", before)
        self.assertNotIn("_tpp_restore()", before)

    def test_nothing_armed_reports_nothing_fired(self):
        from ui.pages import optimization_services as osvc
        fake_hib = mock.MagicMock(turbo_behaviors={})
        fake_svc = mock.MagicMock()
        fake_svc.get_active_profile.return_value = "manager"
        fake_svc.get_profile_services.return_value = []
        with mock.patch.object(osvc, "_set_turbo_flag"), \
                mock.patch.object(osvc, "_load_prefs", return_value={}), \
                mock.patch.dict("import_core.COMPONENTS",
                                {"core.hibernation_manager": fake_hib}), \
                mock.patch("core.turbo_manager.turbo_services", fake_svc):
            res = osvc.set_turbo_active(True)
            time.sleep(0.3)
        self.assertEqual(res["applied"], [])
        fake_svc.stop_profile.assert_not_called()
        fake_hib.apply_turbo_behaviors.assert_not_called()


class TestHibernationWakesWhatItSleeps(unittest.TestCase):
    """Runs against a real, harmless child process (ping to localhost)."""

    def setUp(self):
        import core.hibernation_manager as hm
        self.hm = hm
        self.H = hm.hibernation_manager
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self._patch = mock.patch.object(hm, "_SLEEPING_PATH", self.path)
        self._patch.start()
        try:
            self.child = subprocess.Popen(
                ["ping", "-n", "60", "127.0.0.1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as e:                      # pragma: no cover
            self._patch.stop()
            raise unittest.SkipTest(f"cannot start a child process: {e}")
        self.proc = psutil.Process(self.child.pid)
        self.name = self.proc.name()

    def tearDown(self):
        try:
            self.H.wake_app(self.child.pid)
        except Exception:
            pass
        try:
            self.proc.resume()
        except Exception:
            pass
        self.child.kill()
        self.child.wait(timeout=5)
        self._patch.stop()
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_low_priority_round_trip_restores_the_original(self):
        self.proc.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        self.assertTrue(self.H.sleep_app(self.child.pid, self.name, "", "low"))
        self.assertEqual(self.proc.nice(), psutil.IDLE_PRIORITY_CLASS)
        self.assertTrue(os.path.exists(self.path), "nothing written to disk")
        self.assertTrue(self.H.wake_app(self.child.pid))
        self.assertEqual(self.proc.nice(), psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                         "wake forced 'normal' instead of the old priority")
        self.assertFalse(os.path.exists(self.path))

    def test_frozen_app_is_recovered_after_a_crash(self):
        self.assertTrue(self.H.sleep_app(self.child.pid, self.name, "",
                                         "freeze"))
        self.assertEqual(self.proc.status(), psutil.STATUS_STOPPED)
        # the app "crashes": memory is gone, the file is all that is left
        with self.H._lock:
            self.H._sleeping.pop(self.child.pid, None)
        self.assertEqual(self.H.recover_orphans(), 1)
        self.assertNotEqual(self.proc.status(), psutil.STATUS_STOPPED,
                            "still frozen after recovery")
        self.assertFalse(os.path.exists(self.path))

    def test_recovery_never_touches_a_recycled_pid(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({str(self.child.pid): {"name": self.name, "created": 1.0,
                                             "behavior": "freeze",
                                             "original_nice": 32}}, f)
        self.proc.suspend()
        self.assertEqual(self.H.recover_orphans(), 0)
        self.assertEqual(self.proc.status(), psutil.STATUS_STOPPED,
                         "a process we never slept was resumed")

    def test_exit_hook_wakes_everything(self):
        self.assertTrue(self.H.sleep_app(self.child.pid, self.name, "",
                                         "freeze"))
        self.H._on_exit()
        self.assertNotEqual(self.proc.status(), psutil.STATUS_STOPPED)
        self.assertIn("atexit", inspect.getsource(type(self.H).__init__))


class TestSuspenderOnARealProcess(unittest.TestCase):
    """The Process Guard recovery path, on a real child process."""

    def test_frozen_process_is_recovered_from_the_file(self):
        import core.turbo_manager as tm
        try:
            child = subprocess.Popen(
                ["ping", "-n", "60", "127.0.0.1"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as e:                      # pragma: no cover
            raise unittest.SkipTest(f"cannot start a child process: {e}")
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            proc = psutil.Process(child.pid)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({str(child.pid): {"name": proc.name(),
                                            "created": proc.create_time()}}, f)
            proc.suspend()
            self.assertEqual(proc.status(), psutil.STATUS_STOPPED)
            self.assertEqual(tm.turbo_processes._recover_orphans(path), 1)
            self.assertNotEqual(proc.status(), psutil.STATUS_STOPPED)
        finally:
            child.kill()
            child.wait(timeout=5)
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
