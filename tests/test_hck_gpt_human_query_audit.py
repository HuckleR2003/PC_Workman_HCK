"""Regression floor for independent human-style hck_GPT questions."""
from __future__ import annotations

import unittest

from hck_gpt.intents.ml_classifier import ml_classifier
from hck_gpt.intents.parser import IntentParser, ParseResult
from hck_gpt.intents.vocabulary import INTENT_PATTERNS
from hck_gpt.memory.session_memory import SessionMemory
from scripts import audit_hck_gpt_human_queries as audit
from tests.hck_gpt_human_query_bank import (
    CONTEXT_QUERY_CASES,
    HUMAN_QUERY_CASES,
    OOD_QUERY_CASES,
)


class TestHumanQueryAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old_model = ml_classifier._model
        cls._old_ready = ml_classifier._ready
        cls.model, _ = audit._train_model()
        ml_classifier._model = cls.model
        ml_classifier._ready = True
        IntentParser._folded_cache = {}
        cls.parser = IntentParser()

    @classmethod
    def tearDownClass(cls):
        ml_classifier._model = cls._old_model
        ml_classifier._ready = cls._old_ready
        IntentParser._folded_cache = {}

    def test_bank_is_large_and_not_copied_into_vocabulary(self):
        self.assertGreater(len(HUMAN_QUERY_CASES), 100)
        production = {
            audit._fold(phrase)
            for phrases in INTENT_PATTERNS.values()
            for phrase in phrases
        }
        overlaps = [
            query
            for _, query, _ in HUMAN_QUERY_CASES
            if audit._fold(query) in production
        ]
        self.assertEqual([], overlaps)

    def test_production_routing_stays_above_eighty_percent(self):
        correct = sum(
            self.parser.parse(query).intent in accepted
            for _, query, accepted in HUMAN_QUERY_CASES
        )
        self.assertGreaterEqual(correct / len(HUMAN_QUERY_CASES), 0.80)

    def test_open_set_rejection_stays_above_eighty_percent(self):
        rejected = sum(
            self.parser.parse(query).intent == "unknown"
            for _, query in OOD_QUERY_CASES
        )
        self.assertGreaterEqual(rejected / len(OOD_QUERY_CASES), 0.80)

    def test_context_followups_stay_above_eighty_percent(self):
        correct = 0
        for initial, initial_intent, followup, accepted in CONTEXT_QUERY_CASES:
            memory = SessionMemory()
            memory.remember_turn(
                ParseResult(
                    intent=initial_intent,
                    confidence=1.0,
                    raw_text=initial,
                ),
                ["hck_GPT: test context"],
            )
            parsed = self.parser.parse(followup)
            resolved = memory.resolve_followup(followup, parsed)
            correct += resolved.intent in accepted
        self.assertGreaterEqual(correct / len(CONTEXT_QUERY_CASES), 0.80)

    def test_substrings_do_not_create_known_false_routes(self):
        cases = {
            "could you identify the processor?": "hw_cpu",
            "what happened just before the crash?": "crash_context",
            "napisz wiadomość do rekrutera": "unknown",
            "how do I say good morning in Japanese?": "unknown",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(expected, self.parser.parse(query).intent)


if __name__ == "__main__":
    unittest.main()
