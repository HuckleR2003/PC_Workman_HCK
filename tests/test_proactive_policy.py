"""Scoring, modes, budget and duplicate guards for proactive hck_GPT."""
import unittest
from unittest import mock

from hck_gpt.memory.proactive_monitor import ProactiveMonitor
from hck_gpt.memory.proactive_policy import ProactivePolicy


class TestProactivePolicy(unittest.TestCase):
    def test_invalid_mode_falls_back_to_balanced(self):
        self.assertEqual(ProactivePolicy.normalize_mode("loud"), "balanced")

    def test_quiet_suppresses_idle_tip(self):
        result = ProactivePolicy.decide("idle_tip", mode="quiet")
        self.assertFalse(result.allowed)

    def test_balanced_allows_a_calm_tip_when_novel(self):
        result = ProactivePolicy.decide("idle_tip", mode="balanced")
        self.assertTrue(result.allowed)

    def test_companion_allows_game_checkin(self):
        result = ProactivePolicy.decide("game_checkin", mode="companion")
        self.assertTrue(result.allowed)

    def test_critical_alert_bypasses_disabled_master_switch(self):
        result = ProactivePolicy.decide(
            "cpu_temp_crit", mode="quiet", enabled=False)
        self.assertTrue(result.allowed)
        self.assertTrue(result.urgent)

    def test_noncritical_alert_respects_disabled_master_switch(self):
        result = ProactivePolicy.decide(
            "cpu_high", mode="companion", enabled=False)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "disabled")

    def test_active_conversation_reduces_score(self):
        calm = ProactivePolicy.decide("context_idle_tip", user_active=False)
        active = ProactivePolicy.decide("context_idle_tip", user_active=True)
        self.assertLess(active.score, calm.score)

    def test_low_novelty_reduces_score(self):
        novel = ProactivePolicy.decide("long_session", novelty=1.0)
        repeat = ProactivePolicy.decide("long_session", novelty=0.0)
        self.assertLess(repeat.score, novel.score)


class TestProactiveDispatch(unittest.TestCase):
    def setUp(self):
        self.mon = ProactiveMonitor()
        self.pushed = []
        self.mon.register_push(self.pushed.append)
        self.settings = {
            "gpt_proactive_alerts": True,
            "gpt_proactive_mode": "balanced",
            "gpt_process_spike": True,
        }
        self.settings_patch = mock.patch.object(
            self.mon, "_app_settings", side_effect=lambda: dict(self.settings))
        self.settings_patch.start()

    def tearDown(self):
        self.settings_patch.stop()

    def test_same_candidate_is_dispatched_once(self):
        first = self.mon._dispatch_candidate(
            "context_idle_tip", "hck_GPT: one useful fact")
        second = self.mon._dispatch_candidate(
            "context_idle_tip", "hck_GPT: one useful fact")
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(self.pushed), 1)

    def test_budget_caps_nonurgent_candidates(self):
        for index in range(4):
            self.mon._dispatch_candidate(
                "context_idle_tip", f"hck_GPT: useful fact {index}")
        self.assertEqual(len(self.pushed), 3)

    def test_urgent_candidate_bypasses_full_budget(self):
        self.mon._budget_log = [1e20, 1e20, 1e20]
        ok = self.mon._dispatch_candidate(
            "cpu_temp_crit", "hck_GPT: critical", urgent=True)
        self.assertTrue(ok)
        self.assertEqual(self.pushed, ["hck_GPT: critical"])

    def test_process_spike_has_its_own_switch(self):
        self.settings["gpt_process_spike"] = False
        ok = self.mon._dispatch_candidate(
            "process_spike", "hck_GPT: process spike")
        self.assertFalse(ok)
        self.assertEqual(self.pushed, [])

    def test_quiet_mode_blocks_game_recap_but_not_critical(self):
        self.settings["gpt_proactive_mode"] = "quiet"
        self.assertFalse(self.mon._dispatch_candidate(
            "game_recap", "hck_GPT: session recap"))
        self.assertTrue(self.mon._dispatch_candidate(
            "gpu_temp_crit", "hck_GPT: critical temperature", urgent=True))


if __name__ == "__main__":
    unittest.main()
