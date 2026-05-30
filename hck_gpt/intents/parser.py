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
  4. ML classifier blending:
       ML conf >= 0.70  -> ML result wins outright
       ML conf 0.35–0.69 -> 65% ML + 35% keyword blend
       ML conf < 0.35   -> pure keyword scoring (unchanged behaviour)
  5. Return the highest-scoring intent + all entities found
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    Hybrid intent classifier: keyword scoring + ML Naive Bayes blend.
    No heavy external dependencies. Supports PL + EN simultaneously.
    """

    def parse(self, text: str) -> ParseResult:
        if not text or not text.strip():
            return ParseResult("unknown", 0.0, raw_text=text)

        clean_text = text.lower().strip()
        clean_text = self._normalize_accents(clean_text)
        folded_text   = self._ascii_fold(clean_text)
        tokens        = self._tokenize(clean_text)
        folded_tokens = self._tokenize(folded_text)
        scores: Dict[str, float] = {}

        folded_patterns_cache: Dict[str, List[str]] = {
            intent: [self._ascii_fold(p) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }

        for intent, patterns in INTENT_PATTERNS.items():
            score        = self._score_intent(tokens, clean_text, patterns)
            folded_score = self._score_intent(
                folded_tokens, folded_text, folded_patterns_cache[intent]
            )
            combined = max(score, folded_score)
            if combined > 0:
                scores[intent] = combined

        # ── Keyword result ────────────────────────────────────────────────────
        if scores:
            kw_intent = max(scores, key=lambda k: scores[k])
            kw_conf   = min(1.0, scores[kw_intent] / 3.0)
        else:
            kw_intent, kw_conf = "unknown", 0.0

        # ── ML blend ──────────────────────────────────────────────────────────
        final_intent, final_conf = self._blend_with_ml(
            text, kw_intent, kw_conf
        )

        entities = self._extract_entities(tokens, clean_text)

        return ParseResult(
            intent=final_intent,
            confidence=final_conf,
            entities=entities,
            tokens=tokens,
            raw_text=text,
        )

    # ── ML integration ────────────────────────────────────────────────────────

    def _blend_with_ml(
        self, text: str, kw_intent: str, kw_conf: float
    ) -> Tuple[str, float]:
        """
        Blends keyword score with ML classifier output.

        Returns (intent, confidence) pair using the tiered strategy:
          ML conf >= 0.70  -> ML wins outright
          ML conf 0.35–0.69 -> weighted blend
          ML conf < 0.35   -> keyword-only (unchanged)
        """
        try:
            from hck_gpt.intents.ml_classifier import ml_classifier
            if not ml_classifier.is_ready:
                return kw_intent, kw_conf

            ml_intent, ml_conf = ml_classifier.predict(text)

            if ml_conf >= 0.70:
                # ML is very confident - trust it outright
                return ml_intent, ml_conf

            if ml_conf >= 0.35:
                # Blend zone: 65% ML + 35% keyword
                if ml_intent == kw_intent:
                    # Agreement -> boost
                    blended = 0.65 * ml_conf + 0.35 * kw_conf
                    return ml_intent, min(1.0, blended)
                else:
                    # Disagreement -> compare weighted scores, pick winner
                    ml_score  = 0.65 * ml_conf
                    kw_score  = 0.35 * kw_conf
                    if ml_score >= kw_score:
                        return ml_intent, min(1.0, ml_score + 0.15 * kw_score)
                    else:
                        return kw_intent, min(1.0, kw_score + 0.15 * ml_score)

        except Exception:
            pass  # ML unavailable -> fall through to keyword

        return kw_intent, kw_conf

    # ── Internal ──────────────────────────────────────────────────────────────

    # Polish accent normalization map (typed without diacritics -> with)
    _PL_ACCENT = str.maketrans(
        "aeosnzcl",
        "aeosnzcl",   # identity - real mapping done via replace below
    )

    _ACCENT_MAP = [
        # without -> with (most common user typos / accent-stripped input)
        ("specyfikacje", "specyfikacja"),
        ("wydajnosc",    "wydajność"),
        ("pamieci",      "pamięci"),
        ("pamicc",       "pamięci"),
        ("procesora",    "procesora"),  # already fine
        ("plyte",        "płytę"),
        ("plyta",        "płyta"),
        ("diagnostike",  "diagnostykę"),
        ("diagnostika",  "diagnostyka"),
        ("temperaturze", "temperaturze"),
        ("temperatur",   "temperatura"),
        ("zdrowia",      "zdrowie"),
        ("procesy",      "procesy"),    # already fine
        ("wydajnosci",   "wydajności"),
        ("specyfokacja", "specyfikacja"),
        ("specyf",       "specyfikacja"),
    ]

    def _normalize_accents(self, text: str) -> str:
        """
        Best-effort Polish accent restoration.
        Maps common accent-stripped words to their accented form.
        This lets 'dzieki', 'specyfikacja', 'wydajnosc' etc. score correctly.
        """
        import unicodedata
        # Build full normalization: strip diacritics from BOTH text and patterns
        # -> compare in ASCII-folded space
        # (Implemented by also accent-folding vocabulary patterns in scoring)
        for stripped, accented in self._ACCENT_MAP:
            text = text.replace(stripped, accented)
        return text

    def _ascii_fold(self, text: str) -> str:
        """Remove diacritics for fuzzy matching (ą->a, ę->e, etc.)."""
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
                # Multi-word phrase -> higher reward, check in full text
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
                elif len(pattern) >= 5 and any(
                    self._edit_distance(t, pattern) <= 1
                    for t in tokens
                    if abs(len(t) - len(pattern)) <= 2 and len(t) >= 4
                ):
                    # Typo tolerance: 1-character edit distance for longer words
                    score += 0.6
        return score

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Levenshtein distance - fast 1-row DP, early exit if delta > 2."""
        if abs(len(s1) - len(s2)) > 2:
            return 99
        m, n = len(s1), len(s2)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                dp[j] = prev if s1[i-1] == s2[j-1] else 1 + min(prev, dp[j], dp[j-1])
                prev = temp
        return dp[n]

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
