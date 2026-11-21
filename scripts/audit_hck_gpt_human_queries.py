"""Independent, human-style routing audit for hck_GPT.

The prompts live outside the production vocabulary and are never used for
training. The script measures deterministic keyword routing, the production
parser with an in-memory ML model, open-set rejection and short follow-ups.

Run:
    python -B scripts/audit_hck_gpt_human_queries.py
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(errors="backslashreplace")
except (AttributeError, ValueError):
    pass

from tests.hck_gpt_human_query_bank import (  # noqa: E402
    CONTEXT_QUERY_CASES,
    HUMAN_QUERY_CASES,
    OOD_QUERY_CASES,
)


MIN_HUMAN_CASES = 101
MIN_PRODUCTION_ACCURACY = 0.80
MIN_OOD_REJECTION = 0.80
MIN_CONTEXT_ACCURACY = 0.80


def _fold(text: str) -> str:
    value = "".join(
        char
        for char in unicodedata.normalize("NFD", (text or "").lower())
        if unicodedata.category(char) != "Mn"
    )
    value = value.translate(str.maketrans({
        "ł": "l", "ø": "o", "đ": "d",
    }))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", value)).strip()


def _fresh_parser(model):
    from hck_gpt.intents.ml_classifier import ml_classifier
    from hck_gpt.intents.parser import IntentParser

    IntentParser._folded_cache = {}
    ml_classifier._model = model
    ml_classifier._ready = model is not None
    return IntentParser()


def _train_model():
    from hck_gpt.intents.ml_classifier import (
        NaiveBayesClassifier,
        TrainingDataBuilder,
    )

    texts, labels = TrainingDataBuilder().build()
    return NaiveBayesClassifier().fit(texts, labels), len(texts)


def _vocabulary_overlap() -> list[tuple[str, str]]:
    from hck_gpt.intents.vocabulary import INTENT_PATTERNS

    production = {
        _fold(phrase): intent
        for intent, phrases in INTENT_PATTERNS.items()
        for phrase in phrases
    }
    return [
        (query, production[_fold(query)])
        for _, query, _ in HUMAN_QUERY_CASES
        if _fold(query) in production
    ]


def _route_cases(label: str, model):
    parser = _fresh_parser(model)
    misses = []
    by_group = defaultdict(lambda: [0, 0])
    confusion = Counter()

    for group, query, accepted in HUMAN_QUERY_CASES:
        result = parser.parse(query)
        correct = result.intent in accepted
        by_group[group][1] += 1
        by_group[group][0] += int(correct)
        if not correct:
            misses.append((
                group,
                query,
                result.intent,
                tuple(sorted(accepted)),
                result.confidence,
            ))
            confusion[(next(iter(sorted(accepted))), result.intent)] += 1

    correct = len(HUMAN_QUERY_CASES) - len(misses)
    accuracy = correct / len(HUMAN_QUERY_CASES)
    print(f"{label}: {correct}/{len(HUMAN_QUERY_CASES)} ({accuracy:.2%})")
    print("  groups: " + ", ".join(
        f"{group}={values[0]}/{values[1]}"
        for group, values in sorted(by_group.items())
    ))
    if confusion:
        print("  largest confusions:")
        for (expected, got), count in confusion.most_common(12):
            print(f"    {expected} -> {got}: {count}")
    for group, query, got, accepted, confidence in misses:
        print(
            f"  MISS [{group}] {query!r} -> {got} ({confidence:.3f}), "
            f"expected={list(accepted)}"
        )
    return accuracy, misses


def _ood(model):
    parser = _fresh_parser(model)
    misses = []
    for group, query in OOD_QUERY_CASES:
        result = parser.parse(query)
        if result.intent != "unknown":
            misses.append((group, query, result.intent, result.confidence))

    correct = len(OOD_QUERY_CASES) - len(misses)
    accuracy = correct / len(OOD_QUERY_CASES)
    print(f"open-set rejection: {correct}/{len(OOD_QUERY_CASES)} ({accuracy:.2%})")
    for group, query, got, confidence in misses:
        print(f"  FALSE HIT [{group}] {query!r} -> {got} ({confidence:.3f})")
    return accuracy, misses


def _context(model):
    from hck_gpt.intents.parser import ParseResult
    from hck_gpt.memory.session_memory import SessionMemory

    parser = _fresh_parser(model)
    misses = []
    for initial, initial_intent, followup, accepted in CONTEXT_QUERY_CASES:
        memory = SessionMemory()
        memory.remember_turn(
            ParseResult(
                intent=initial_intent,
                confidence=1.0,
                raw_text=initial,
            ),
            ["hck_GPT: audit context"],
        )
        parsed = parser.parse(followup)
        resolved = memory.resolve_followup(followup, parsed)
        if resolved.intent not in accepted:
            misses.append((
                initial,
                followup,
                resolved.intent,
                tuple(sorted(accepted)),
            ))

    correct = len(CONTEXT_QUERY_CASES) - len(misses)
    accuracy = correct / len(CONTEXT_QUERY_CASES)
    print(f"context follow-ups: {correct}/{len(CONTEXT_QUERY_CASES)} ({accuracy:.2%})")
    for initial, followup, got, accepted in misses:
        print(
            f"  MISS after {initial!r}: {followup!r} -> {got}, "
            f"expected={list(accepted)}"
        )
    return accuracy, misses


def _response_smoke(model):
    """Build every routed human query through its real deterministic handler."""
    from hck_gpt.engine.flow_engine import flow_engine
    from hck_gpt.intents.lang_detect import detect_language
    from hck_gpt.responses.builder import ResponseBuilder

    parser = _fresh_parser(model)
    builder = ResponseBuilder()
    failures = []
    for group, query, _ in HUMAN_QUERY_CASES:
        flow_engine.abort()
        try:
            result = parser.parse(query)
            lang = detect_language(query, fallback="pl")
            response = builder.build(result, lang=lang)
            useful_lines = [
                str(line).strip()
                for line in (response or [])
                if str(line).strip()
            ]
            if result.intent == "unknown" or not useful_lines:
                failures.append((group, query, result.intent, "empty response"))
        except Exception as exc:
            failures.append((
                group,
                query,
                "exception",
                f"{type(exc).__name__}: {exc}",
            ))
        finally:
            flow_engine.abort()

    correct = len(HUMAN_QUERY_CASES) - len(failures)
    accuracy = correct / len(HUMAN_QUERY_CASES)
    print(
        f"deterministic response execution: "
        f"{correct}/{len(HUMAN_QUERY_CASES)} ({accuracy:.2%})"
    )
    for group, query, intent, detail in failures:
        print(f"  RESPONSE FAIL [{group}] {query!r} -> {intent}: {detail}")
    return accuracy, failures


def main() -> int:
    print("== hck_GPT independent human-query audit ==")
    print(
        f"bank: in_domain={len(HUMAN_QUERY_CASES)}, "
        f"out_of_domain={len(OOD_QUERY_CASES)}, "
        f"context={len(CONTEXT_QUERY_CASES)}, "
        f"total={len(HUMAN_QUERY_CASES) + len(OOD_QUERY_CASES) + len(CONTEXT_QUERY_CASES)}"
    )

    overlap = _vocabulary_overlap()
    print(f"exact normalized overlap with production vocabulary: {len(overlap)}")
    for query, intent in overlap:
        print(f"  LEAK {query!r} duplicates {intent}")

    print()
    keyword_accuracy, _ = _route_cases("keyword-only routing", None)
    print()

    model, training_count = _train_model()
    print(f"in-memory training examples: {training_count}")
    production_accuracy, _ = _route_cases("production parser + ML", model)
    print()
    ood_accuracy, _ = _ood(model)
    print()
    context_accuracy, _ = _context(model)
    print()
    response_accuracy, _ = _response_smoke(model)

    passed = (
        len(HUMAN_QUERY_CASES) >= MIN_HUMAN_CASES
        and not overlap
        and production_accuracy >= MIN_PRODUCTION_ACCURACY
        and ood_accuracy >= MIN_OOD_REJECTION
        and context_accuracy >= MIN_CONTEXT_ACCURACY
        and response_accuracy >= MIN_PRODUCTION_ACCURACY
    )
    print()
    print(
        "thresholds: "
        f"human>={MIN_PRODUCTION_ACCURACY:.0%}, "
        f"OOD>={MIN_OOD_REJECTION:.0%}, "
        f"context>={MIN_CONTEXT_ACCURACY:.0%}, "
        f"bank>={MIN_HUMAN_CASES}"
    )
    print(
        f"result: {'PASS' if passed else 'FAIL'} "
        f"(keyword baseline {keyword_accuracy:.2%})"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
