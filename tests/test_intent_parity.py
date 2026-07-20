"""tests.test_intent_parity
Guards against the "silent intent" bug class: an intent with trigger phrases
in INTENT_PATTERNS but no _resp_<intent> handler in the response builder.
The parser matches such an intent with full confidence and the user gets the
generic fallback - no crash, no log. It shipped twice (17 in v1.7.6, 16 in
v1.8.0) before this test existed.

Handlers are collected from every module in hck_gpt/responses/ (the 2026-07-15
split moved them from the builder.py monolith into r_* category mixins), so
the check survives any future re-organisation of the package.
"""
import glob
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VOCAB = os.path.join(_ROOT, "hck_gpt", "intents", "vocabulary.py")
_RESPONSES_GLOB = os.path.join(_ROOT, "hck_gpt", "responses", "*.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestIntentHandlerParity(unittest.TestCase):

    def setUp(self):
        voc = _read(_VOCAB)
        responses_src = "".join(_read(p) for p in glob.glob(_RESPONSES_GLOB))
        # top-level keys of INTENT_PATTERNS: 4-space-indented "name": [
        self.intents = re.findall(
            r'^\s{4}["\']([a-z0-9_]+)["\']\s*:\s*\[', voc, re.M)
        self.handlers = set(re.findall(r'def _resp_([a-z0-9_]+)\(',
                                       responses_src))

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

    def test_no_handler_defined_twice(self):
        """A handler defined in two mixins would silently shadow via MRO."""
        all_defs = []
        for p in glob.glob(_RESPONSES_GLOB):
            all_defs += re.findall(r'def (_resp_[a-z0-9_]+)\(', _read(p))
        dupes = {d for d in all_defs if all_defs.count(d) > 1}
        self.assertEqual(dupes, set(),
                         f"Handlers defined in more than one module: {dupes}")

    def test_monolith_guard(self):
        """The 6.5k-line builder monolith must never grow back. Every module
        in hck_gpt/responses/ stays below 1,600 lines; add a new r_* category
        module instead of piling into an existing one."""
        for p in glob.glob(_RESPONSES_GLOB):
            n = _read(p).count("\n") + 1
            self.assertLess(
                n, 1600,
                f"{os.path.basename(p)} has {n} lines - split it instead of "
                f"growing another monolith")


if __name__ == "__main__":
    unittest.main()
