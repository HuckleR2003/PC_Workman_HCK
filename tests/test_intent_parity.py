"""tests.test_intent_parity
Guards against the "silent intent" bug class: an intent with trigger phrases
in INTENT_PATTERNS but no _resp_<intent> handler in the response builder.
The parser matches such an intent with full confidence and the user gets the
generic fallback - no crash, no log. It shipped twice (17 in v1.7.6, 16 in
v1.8.0) before this test existed.

Static source check (no imports), so it runs on any platform in milliseconds.
"""
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VOCAB = os.path.join(_ROOT, "hck_gpt", "intents", "vocabulary.py")
_BUILDER = os.path.join(_ROOT, "hck_gpt", "responses", "builder.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestIntentHandlerParity(unittest.TestCase):

    def setUp(self):
        voc = _read(_VOCAB)
        builder = _read(_BUILDER)
        # top-level keys of INTENT_PATTERNS: 4-space-indented "name": [
        self.intents = re.findall(
            r'^\s{4}["\']([a-z0-9_]+)["\']\s*:\s*\[', voc, re.M)
        self.handlers = set(re.findall(r'def _resp_([a-z0-9_]+)\(', builder))

    def test_vocabulary_is_not_empty(self):
        self.assertGreater(len(self.intents), 80,
                           "INTENT_PATTERNS parse failed or vocabulary shrank")

    def test_every_intent_has_a_handler(self):
        missing = [i for i in self.intents if i not in self.handlers]
        self.assertEqual(
            missing, [],
            f"Intents with trigger phrases but NO _resp_ handler (silent "
            f"fallback for the user): {missing}")

    def test_no_duplicate_intent_keys(self):
        dupes = {i for i in self.intents if self.intents.count(i) > 1}
        self.assertEqual(dupes, set(),
                         f"Duplicate INTENT_PATTERNS keys: {dupes}")


if __name__ == "__main__":
    unittest.main()
