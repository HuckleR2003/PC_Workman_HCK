"""tests.test_gpt_journal - every unsolicited hck_GPT message is written
down, sent or held back (2026-11-16).

Before this the chat window was the only record: messages held back by the
policy, the budget or as duplicates were invisible, and everything was gone
after a restart. A long test run could not show whether hck_GPT talks too
much or about the wrong things.
"""
import json
import os
import tempfile
import unittest


class TestProactiveJournal(unittest.TestCase):

    def setUp(self):
        self._old = os.environ.get("PCW_LOG_DIR")
        self.dir = tempfile.mkdtemp(prefix="pcw_journal_")
        os.environ["PCW_LOG_DIR"] = self.dir
        from hck_gpt.memory.proactive_monitor import ProactiveMonitor
        self.m = ProactiveMonitor()
        self.sent = []
        self.m._push_fn = self.sent.append
        self.m._app_settings = lambda: {}
        self.m._is_user_active = lambda: False
        self.m.proactive_mode = lambda: "balanced"

    def tearDown(self):
        if self._old is None:
            os.environ.pop("PCW_LOG_DIR", None)
        else:
            os.environ["PCW_LOG_DIR"] = self._old

    def _rows(self):
        path = os.path.join(self.dir, "hck_gpt_proactive.jsonl")
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def test_sent_and_duplicate_are_both_recorded(self):
        msg = "Your CPU has averaged 45% for 2 days [-> CPU History]"
        self.assertTrue(self.m._dispatch_candidate("history_trend", msg))
        self.assertFalse(self.m._dispatch_candidate("history_trend", msg))
        rows = self._rows()
        self.assertEqual([r["outcome"] for r in rows], ["sent", "held:duplicate"])
        self.assertEqual(rows[0]["msg"], msg)
        self.assertEqual(self.sent, [msg])
        self.assertIsNotNone(rows[0]["score"])

    def test_budget_hold_is_recorded(self):
        for i in range(12):
            self.m._dispatch_candidate("history_trend", f"note {i}")
        outcomes = [r["outcome"] for r in self._rows()]
        self.assertIn("held:budget", outcomes)
        self.assertEqual(outcomes.count("sent"), len(self.sent))

    def test_setting_off_is_recorded(self):
        self.m._app_settings = lambda: {"gpt_digest": False}
        self.assertFalse(self.m._dispatch_candidate("digest_suggestion", "digest"))
        self.assertEqual(self._rows()[0]["outcome"], "held:setting_off")


if __name__ == "__main__":
    unittest.main()
