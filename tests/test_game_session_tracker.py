"""Gaming observer and evidence tracker regression tests."""
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from hck_gpt.memory.game_session import GameSessionTracker
from ui.components.gaming_toast import GamingToastWatcher


class TestGameSessionTracker(unittest.TestCase):
    def test_fps_is_rejected_without_explicit_rtss_source(self):
        tracker = GameSessionTracker()
        tracker.start("game.exe", now=0)
        tracker.sample("game.exe", {"fps": 144, "cpu_pct": 20}, now=50)
        summary = tracker.end("game.exe", now=100)
        self.assertNotIn("fps", summary["averages"])
        self.assertFalse(summary["fps_available"])

    def test_rtss_fps_is_kept_with_source(self):
        tracker = GameSessionTracker()
        tracker.start("game.exe", now=0)
        tracker.sample(
            "game.exe", {"fps": 120, "fps_source": "rtss"}, now=50)
        tracker.sample(
            "game.exe", {"fps": 100, "fps_source": "rtss"}, now=100)
        summary = tracker.end("game.exe", now=150)
        self.assertEqual(summary["averages"]["fps"], 110.0)
        self.assertEqual(summary["fps_source"], "rtss")

    def test_checkin_is_companion_only_and_once(self):
        tracker = GameSessionTracker()
        tracker.start("game.exe", now=0)
        tracker.sample("game.exe", {"gpu_pct": 70}, now=50)
        tracker.sample("game.exe", {"gpu_pct": 80}, now=100)
        self.assertFalse(tracker.should_check_in("game.exe", "balanced", now=700))
        self.assertTrue(tracker.should_check_in("game.exe", "companion", now=700))
        tracker.mark_checkin("game.exe")
        self.assertFalse(tracker.should_check_in("game.exe", "companion", now=800))

    def test_short_session_summary_stays_measurement_only(self):
        tracker = GameSessionTracker()
        tracker.start("game.exe", "Game", {"cpu_pct": 10}, now=0)
        tracker.sample("game.exe", {"cpu_pct": 30, "ram_pct": 50}, now=50)
        summary = tracker.end("game.exe", now=200)
        self.assertEqual(summary["duration_s"], 200)
        self.assertEqual(summary["averages"]["cpu_pct"], 30.0)
        self.assertEqual(summary["label"], "Game")

    def test_samples_are_bounded(self):
        tracker = GameSessionTracker()
        tracker.MAX_SAMPLES = 5
        tracker.SAMPLE_GAP_S = 0
        tracker.start("game.exe", now=0)
        for index in range(12):
            tracker.sample("game.exe", {"cpu_pct": index}, now=index + 1)
        summary = tracker.end("game.exe", now=20)
        self.assertEqual(summary["sample_count"], 5)


class TestSingleGamingWatcher(unittest.TestCase):
    @staticmethod
    def _proc(name):
        return SimpleNamespace(info={"name": name})

    def test_watcher_emits_one_start_and_one_end(self):
        watcher = GamingToastWatcher()
        events = []
        watcher.register_game_observer(
            lambda event, exe, label: events.append((event, exe, label)))
        fake_psutil = SimpleNamespace(
            process_iter=mock.Mock(side_effect=[
                [self._proc("valorant.exe")],
                [self._proc("valorant.exe")],
                [],
            ])
        )
        with mock.patch.dict(sys.modules, {"psutil": fake_psutil}), \
             mock.patch.object(watcher, "_is_enabled", return_value=False):
            watcher._check()
            watcher._check()
            watcher._check()
        self.assertEqual([row[0] for row in events], ["start", "end"])
        self.assertEqual(events[0][1], "valorant.exe")

    def test_duplicate_observer_registration_is_ignored(self):
        watcher = GamingToastWatcher()
        callback = mock.Mock()
        watcher.register_game_observer(callback)
        watcher.register_game_observer(callback)
        self.assertEqual(len(watcher._observers), 1)


if __name__ == "__main__":
    unittest.main()
