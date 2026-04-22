# hck_gpt/intents/parser.py
"""
Intent Parser

Converts a free-form user message into a structured ParseResult containing:
  - intent   : best matching intent name (str)
  - confidence: 0.0–1.0
  - entities : extracted component/metric names
  - tokens   : cleaned token list

Algorithm:
  1. Lowercase + strip punctuation
  2. Remove stopwords
  3. Score every intent against the token list and full text
     (multi-word phrases score higher)
  4. Return the highest-scoring intent + all entities found
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List

from hck_gpt.intents.vocabulary import ENTITY_MAP, INTENT_PATTERNS, STOPWORDS


# ── Result data class ─────────────────────────────────────────────────────────

@dataclass
class ParseResult:
    intent:     str
    confidence: float
    entities:   Dict[str, str]        = field(default_factory=dict)
    tokens:     List[str]             = field(default_factory=list)
    raw_text:   str                   = ""

    def has_entity(self, entity: str) -> bool:
        return entity in self.entities

    def is_confident(self, threshold: float = 0.5) -> bool:
        return self.confidence >= threshold

    def __repr__(self) -> str:
        return (f"ParseResult(intent={self.intent!r}, "
                f"conf={self.confidence:.2f}, "
                f"entities={self.entities})")


# ── Parser ────────────────────────────────────────────────────────────────────

class IntentParser:
    """
    Lightweight keyword-scoring intent classifier.
    No external dependencies. Supports PL + EN simultaneously.
    """

    def parse(self, text: str) -> ParseResult:
        if not text or not text.strip():
            return ParseResult("unknown", 0.0, raw_text=text)

        clean_text = text.lower().strip()
        # Normalize accent-stripped Polish words before scoring
        clean_text = self._normalize_accents(clean_text)
        # Also score against ASCII-folded version for full fuzzy coverage
        folded_text = self._ascii_fold(clean_text)
        tokens      = self._tokenize(clean_text)
        # Add ASCII-folded tokens so "dzieki"→"dzięki" works via token match
        folded_tokens = self._tokenize(folded_text)
        scores: Dict[str, float] = {}

        # Build ASCII-folded versions of all patterns once
        folded_patterns_cache: Dict[str, List[str]] = {
            intent: [self._ascii_fold(p) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }

        for intent, patterns in INTENT_PATTERNS.items():
            # Score against original (accented) text
            score = self._score_intent(tokens, clean_text, patterns)
            # Score against ASCII-folded text (catches input without diacritics)
            folded_score = self._score_intent(
                folded_tokens, folded_text, folded_patterns_cache[intent]
            )
            combined = max(score, folded_score)
            if combined > 0:
                scores[intent] = combined

        if not scores:
            return ParseResult("unknown", 0.0, tokens=tokens, raw_text=text)

        best_intent = max(scores, key=lambda k: scores[k])
        # Rough normalisation: a score of 3 → confidence ≈ 1.0
        confidence  = min(1.0, scores[best_intent] / 3.0)
        entities    = self._extract_entities(tokens, clean_text)

        return ParseResult(
            intent=best_intent,
            confidence=confidence,
            entities=entities,
            tokens=tokens,
            raw_text=text,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    # Polish accent normalization map (typed without diacritics → with)
    _PL_ACCENT = str.maketrans(
        "aeosnzcl",
        "aeosnzcl",   # identity — real mapping done via replace below
    )

    _ACCENT_MAP = [
        # without → with (most common user typos)
        ("specyfikacje", "specyfikacja"),
        ("wydajnosc",    "wydajność"),
        ("pamieci",      "pamięci"),
        ("pamicc",       "pamięci"),
        ("procesora",    "procesora"),  # already fine
        ("plyte",        "płytę"),
        ("plyta",        "płyta"),
    ]

    def _normalize_accents(self, text: str) -> str:
        """
        Best-effort Polish accent restoration.
        Maps common accent-stripped words to their accented form.
        This lets 'dzieki', 'specyfikacja', 'wydajnosc' etc. score correctly.
        """
        import unicodedata
        # Build full normalization: strip diacritics from BOTH text and patterns
        # → compare in ASCII-folded space
        # (Implemented by also accent-folding vocabulary patterns in scoring)
        for stripped, accented in self._ACCENT_MAP:
            text = text.replace(stripped, accented)
        return text

    def _ascii_fold(self, text: str) -> str:
        """Remove diacritics for fuzzy matching (ą→a, ę→e, etc.)."""
        import unicodedata
        return "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        )

    def _tokenize(self, text: str) -> List[str]:
        text = re.sub(r"[^\w\s]", " ", text)
        return [
            t for t in text.split()
            if t not in STOPWORDS and len(t) > 1
        ]

    def _score_intent(self, tokens: List[str], full_text: str,
                      patterns: List[str]) -> float:
        score = 0.0
        for pattern in patterns:
            if " " in pattern:
                # Multi-word phrase → higher reward, check in full text
                if pattern in full_text:
                    score += len(pattern.split()) * 1.5
            else:
                if pattern in tokens:
                    score += 1.0
                elif any(
                    t.startswith(pattern) or pattern.startswith(t)
                    for t in tokens
                    if len(t) >= 3 and len(pattern) >= 3
                ):
                    score += 0.4
        return score

    def _extract_entities(self, tokens: List[str],
                          full_text: str) -> Dict[str, str]:
        entities: Dict[str, str] = {}
        # Multi-word entities first
        for phrase, entity in ENTITY_MAP.items():
            if " " in phrase and phrase in full_text:
                entities[entity] = phrase
        # Single-word entities
        for token in tokens:
            if token in ENTITY_MAP:
                ent = ENTITY_MAP[token]
                if ent not in entities:
                    entities[ent] = token
        return entities


# ── Singleton ─────────────────────────────────────────────────────────────────
intent_parser = IntentParser()
