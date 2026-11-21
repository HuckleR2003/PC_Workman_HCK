"""tests.test_gpt_chat_journal - every hck_GPT exchange is written down
locally (2026-11-16).

Questions and answers lived only in the chat window. To find what hck_GPT
misses, or answers about the wrong component, each exchange now goes to
data/logs/hck_gpt_chat.jsonl with what the parser understood.
"""
import json
import os
import tempfile
import unittest


class TestChatJournal(unittest.TestCase):

    def setUp(self):
        self._old = os.environ.get("PCW_LOG_DIR")
        self.dir = tempfile.mkdtemp(prefix="pcw_chat_")
        os.environ["PCW_LOG_DIR"] = self.dir
        from hck_gpt.chat_handler import ChatHandler
        self.h = ChatHandler()

    def tearDown(self):
        if self._old is None:
            os.environ.pop("PCW_LOG_DIR", None)
        else:
            os.environ["PCW_LOG_DIR"] = self._old

    def _rows(self):
        with open(os.path.join(self.dir, "hck_gpt_chat.jsonl"), encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def test_question_answer_and_parse_are_recorded(self):
        answer = self.h.process_message("jaka jest temperatura gpu?", ui_lang="pl")
        row = self._rows()[-1]
        self.assertEqual(row["question"], "jaka jest temperatura gpu?")
        self.assertEqual(row["answer"], [str(x) for x in answer])
        self.assertEqual(row["lang"], "pl")
        self.assertIn("intent", row["parsed"])
        self.assertIn("confidence", row["parsed"])
        self.assertGreaterEqual(row["ms"], 0)

    def test_gibberish_is_marked_as_fallback(self):
        self.h.process_message("qwzx plorkt vvbn", ui_lang="en")
        self.assertTrue(self._rows()[-1]["fallback"])

    def test_empty_message_is_not_recorded(self):
        self.h.process_message("   ", ui_lang="en")
        self.assertFalse(os.path.exists(os.path.join(self.dir, "hck_gpt_chat.jsonl")))


if __name__ == "__main__":
    unittest.main()
