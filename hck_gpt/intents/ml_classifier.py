# hck_gpt/intents/ml_classifier.py
"""
ML Intent Classifier - Pure-Python Multinomial Naive Bayes

Zero external dependencies (only stdlib).
Trained on phrases from vocabulary.py with data augmentation.
Saves/loads model to data/cache/ (pickle).
Auto-retrains when vocabulary fingerprint changes.

Performance target:
  - Training time   : < 1 second
  - Inference time  : < 1 ms
  - Accuracy (5-CV) : ~85–92% on vocabulary phrases
  - Model size      : ~200–400 KB on disk

Architecture:
  word unigrams + bigrams  ->  Multinomial NB  ->  softmax probabilities

Integration with parser.py:
  - ML conf >= 0.70  ->  use ML result directly
  - ML conf 0.35–0.69 ->  blend 65% ML + 35% keyword score
  - ML conf < 0.35   ->  pure keyword scoring (current behaviour)
"""
from __future__ import annotations

import math
import os
import pickle
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Optional, Tuple


# ── Text utilities ─────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Lowercase word unigrams + bigrams, strip punctuation, min length 2."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    words = [w for w in text.split() if len(w) >= 2]
    tokens = words[:]
    tokens += [f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)]
    return tokens


def _ascii_fold(text: str) -> str:
    """Strip diacritics: ą->a, ę->e, ó->o, ś->s, ź/ż->z, ć->c, ń->n, ł->l."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


# ── Naive Bayes Classifier ─────────────────────────────────────────────────────

# Laplace smoothing — single source of truth used by NB and cross-validation
NB_SMOOTHING: float = 0.5


class NaiveBayesClassifier:
    """
    Multinomial Naive Bayes with Laplace smoothing and softmax output.

    Uses log-space arithmetic to avoid floating-point underflow on long texts.
    Softmax converts raw log-scores to a proper probability distribution so
    confidence values are comparable across different query lengths.
    """

    def __init__(self, smoothing: float = NB_SMOOTHING) -> None:
        self.smoothing   = smoothing
        self.classes:     List[str]             = []
        self.log_priors:  Dict[str, float]      = {}
        self.word_counts: Dict[str, Counter]    = {}
        self.totals:      Dict[str, int]        = {}
        self.vocab_size:  int                   = 0
        self.trained:     bool                  = False

    def fit(self, X: List[str], y: List[str]) -> "NaiveBayesClassifier":
        n = len(X)
        class_doc_counts = Counter(y)
        self.classes = sorted(set(y))

        self.log_priors = {
            cls: math.log(class_doc_counts[cls] / n)
            for cls in self.classes
        }

        self.word_counts = {cls: Counter() for cls in self.classes}
        vocab: set = set()
        for text, label in zip(X, y):
            tokens = _tokenize(text)
            self.word_counts[label].update(tokens)
            vocab.update(tokens)

        self.vocab_size = len(vocab)
        self.totals = {
            cls: sum(self.word_counts[cls].values())
            for cls in self.classes
        }
        self.trained = True
        return self

    def predict_proba(self, text: str) -> Dict[str, float]:
        if not self.trained:
            return {}
        tokens  = _tokenize(text)
        log_scores: Dict[str, float] = {}

        for cls in self.classes:
            score  = self.log_priors[cls]
            total  = self.totals[cls]
            counts = self.word_counts[cls]
            denom  = total + self.smoothing * self.vocab_size
            for tok in tokens:
                score += math.log((counts.get(tok, 0) + self.smoothing) / denom)
            log_scores[cls] = score

        if not log_scores:
            return {}
        # Numerically stable softmax
        max_s   = max(log_scores.values())
        exp_s   = {cls: math.exp(s - max_s) for cls, s in log_scores.items()}
        total_e = sum(exp_s.values()) or 1.0
        return {cls: v / total_e for cls, v in exp_s.items()}

    def predict(self, text: str) -> Tuple[str, float]:
        probs = self.predict_proba(text)
        if not probs:
            return "unknown", 0.0
        best = max(probs, key=probs.__getitem__)
        return best, probs[best]


# ── Training Data Builder ──────────────────────────────────────────────────────

class TrainingDataBuilder:
    """
    Generates augmented training corpus from vocabulary.py INTENT_PATTERNS.

    Augmentation strategy (per phrase):
      1. Original phrase                         (always)
      2. ASCII-folded variant (no diacritics)    (if different from original)
      3. Individual content words from long phrases (len >= 3 words, word len >= 4)

    This gives ~3000–6000 training examples from ~1500 vocabulary phrases.
    """

    def build(self) -> Tuple[List[str], List[str]]:
        from hck_gpt.intents.vocabulary import INTENT_PATTERNS
        X: List[str] = []
        y: List[str] = []

        for intent, phrases in INTENT_PATTERNS.items():
            for phrase in phrases:
                # 1. Original
                X.append(phrase); y.append(intent)

                # 2. Accent-stripped variant
                folded = _ascii_fold(phrase)
                if folded != phrase:
                    X.append(folded); y.append(intent)

                # 3. Individual content words from long phrases
                words = phrase.split()
                if len(words) >= 3:
                    for w in words:
                        if len(w) >= 4 and _ascii_fold(w) not in {
                            "jest", "moje", "moja", "mamy", "maja",
                            "what", "does", "this", "that", "have", "with",
                        }:
                            X.append(w); y.append(intent)
                            folded_w = _ascii_fold(w)
                            if folded_w != w:
                                X.append(folded_w); y.append(intent)

        return X, y

    def vocab_fingerprint(self) -> str:
        """MD5 hash of current INTENT_PATTERNS - detects vocabulary changes."""
        import hashlib
        from hck_gpt.intents.vocabulary import INTENT_PATTERNS
        content = str(sorted(
            (k, sorted(v)) for k, v in INTENT_PATTERNS.items()
        ))
        return hashlib.md5(content.encode("utf-8")).hexdigest()[:16]


# ── ML Intent Classifier ───────────────────────────────────────────────────────

class MLIntentClassifier:
    """
    Production wrapper: persistence + auto-retrain + cross-validation.

    Usage (singleton):
        from hck_gpt.intents.ml_classifier import ml_classifier

        # On app start (non-blocking):
        ml_classifier.load_or_train(background=True)

        # In parser:
        intent, conf = ml_classifier.predict("jaki mam procesor")
    """

    _MODEL_FILE = "intent_nb_classifier.pkl"
    _HASH_FILE  = "intent_nb_classifier.hash"

    def __init__(self) -> None:
        self._model:     Optional[NaiveBayesClassifier] = None
        self._ready:     bool = False
        self._cache_dir: str  = self._resolve_cache_dir()

    # ── Public ────────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready and self._model is not None

    def load_or_train(self, background: bool = False) -> bool:
        """
        Load cached model (if vocabulary unchanged) or retrain from scratch.
        Set background=True for non-blocking startup (daemon thread).
        """
        if background:
            import threading
            threading.Thread(
                target=self._load_or_train_impl,
                daemon=True,
                name="hck_ml_train"
            ).start()
            return True
        return self._load_or_train_impl()

    def predict(self, text: str) -> Tuple[str, float]:
        """Returns (intent, confidence 0–1). Thread-safe after training."""
        if not self.is_ready:
            return "unknown", 0.0
        return self._model.predict(text)

    def predict_proba(self, text: str) -> Dict[str, float]:
        """Full probability distribution over all intents."""
        if not self.is_ready:
            return {}
        return self._model.predict_proba(text)

    def retrain(self) -> bool:
        """Force full retrain even if cached model exists."""
        return self._train_and_save()

    def cross_validate(self, k: int = 5) -> float:
        """
        K-fold cross-validation accuracy estimate.
        Useful for vocabulary quality checks.
        Returns accuracy as 0.0–1.0.
        """
        try:
            import random
            X, y = TrainingDataBuilder().build()
            if len(X) < k * 20:
                return 0.0

            rng = random.Random(42)
            combined = list(zip(X, y))
            rng.shuffle(combined)
            X, y = [a for a, _ in combined], [b for _, b in combined]

            n = len(X)
            fold = n // k
            correct = total = 0
            for i in range(k):
                vs, ve = i * fold, (i + 1) * fold
                Xtr = X[:vs] + X[ve:]
                ytr = y[:vs] + y[ve:]
                m = NaiveBayesClassifier(smoothing=NB_SMOOTHING).fit(Xtr, ytr)
                for xt, yt in zip(X[vs:ve], y[vs:ve]):
                    correct += (m.predict(xt)[0] == yt)
                    total   += 1
            return round(correct / total, 4) if total else 0.0
        except Exception:
            return 0.0

    def get_top_k(self, text: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Return top-k (intent, confidence) pairs sorted by confidence descending.
        Useful for debugging intent routing — shows what the model is "thinking".
        Returns empty list if model is not ready.
        """
        probs = self.predict_proba(text)
        if not probs:
            return []
        return sorted(probs.items(), key=lambda x: x[1], reverse=True)[:k]

    def accuracy_report(self) -> str:
        """Human-readable accuracy + training set size report."""
        try:
            X, y = TrainingDataBuilder().build()
            n_examples = len(X)
            n_intents  = len(set(y))
            acc = self.cross_validate()
            return (
                f"ML classifier: {n_intents} intents, "
                f"{n_examples} training examples, "
                f"{acc*100:.1f}% CV accuracy"
            )
        except Exception as e:
            return f"ML classifier: report failed ({e})"

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_or_train_impl(self) -> bool:
        if self._load_if_fresh():
            return True
        return self._train_and_save()

    def _load_if_fresh(self) -> bool:
        """Load only if saved vocabulary hash matches current vocabulary."""
        try:
            mpath = os.path.join(self._cache_dir, self._MODEL_FILE)
            hpath = os.path.join(self._cache_dir, self._HASH_FILE)
            if not os.path.exists(mpath) or not os.path.exists(hpath):
                return False
            with open(hpath, "r", encoding="utf-8") as f:
                saved_hash = f.read().strip()
            if saved_hash != TrainingDataBuilder().vocab_fingerprint():
                return False  # vocabulary changed -> must retrain
            with open(mpath, "rb") as f:
                self._model = pickle.load(f)
            self._ready = True
            return True
        except Exception:
            return False

    def _train_and_save(self) -> bool:
        try:
            builder  = TrainingDataBuilder()
            X, y     = builder.build()
            self._model = NaiveBayesClassifier(smoothing=0.5).fit(X, y)
            self._ready = True
            os.makedirs(self._cache_dir, exist_ok=True)
            with open(os.path.join(self._cache_dir, self._MODEL_FILE), "wb") as f:
                pickle.dump(self._model, f)
            with open(os.path.join(self._cache_dir, self._HASH_FILE), "w", encoding="utf-8") as f:
                f.write(builder.vocab_fingerprint())
            return True
        except Exception:
            return False

    @staticmethod
    def _resolve_cache_dir() -> str:
        try:
            from utils.paths import APP_DIR
            return os.path.join(APP_DIR, "data", "cache")
        except Exception:
            import sys
            base = (
                os.path.dirname(sys.executable)
                if getattr(sys, "frozen", False)
                else os.path.normpath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "..")
                )
            )
            return os.path.join(base, "data", "cache")


# ── Singleton ──────────────────────────────────────────────────────────────────
ml_classifier = MLIntentClassifier()
