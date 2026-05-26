#!/usr/bin/env python3
# hck_gpt/intents/train_classifier.py
"""
Standalone ML Classifier Training Script

Run from the project root:
    python -m hck_gpt.intents.train_classifier
    python hck_gpt/intents/train_classifier.py

What it does:
  1. Builds the augmented training corpus from vocabulary.py
  2. Trains a Multinomial Naive Bayes classifier
  3. Runs 5-fold cross-validation and prints accuracy
  4. Saves the model to data/cache/ (replaces any previous version)
  5. Prints a summary report

Use this after editing vocabulary.py to pre-bake the model before shipping.
The app auto-trains on first launch anyway — this is just for convenience
and for verifying vocabulary quality before a release.
"""
from __future__ import annotations

import sys
import os
import time

# Make sure project root is on path when run as a script
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.normpath(os.path.join(_here, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def main() -> None:
    print("=" * 60)
    print("  hck_GPT — ML Intent Classifier Training")
    print("=" * 60)
    print()

    # ── Import ────────────────────────────────────────────────────
    try:
        from hck_gpt.intents.ml_classifier import (
            MLIntentClassifier, TrainingDataBuilder, NaiveBayesClassifier
        )
    except ImportError as exc:
        print(f"[ERROR] Could not import classifier: {exc}")
        sys.exit(1)

    # ── Build corpus ──────────────────────────────────────────────
    print("[~] Building training corpus...")
    t0 = time.perf_counter()
    try:
        builder = TrainingDataBuilder()
        X, y    = builder.build()
        fingerprint = builder.vocab_fingerprint()
    except Exception as exc:
        print(f"[ERROR] Failed to build corpus: {exc}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    n_intents  = len(set(y))
    n_examples = len(X)
    corpus_time = time.perf_counter() - t0
    print(f"[+] Corpus: {n_intents} intents, {n_examples} examples  ({corpus_time*1000:.0f} ms)")
    print(f"[+] Vocabulary fingerprint: {fingerprint}")
    print()

    # ── Train ─────────────────────────────────────────────────────
    print("[~] Training Naive Bayes classifier...")
    t0 = time.perf_counter()
    model = NaiveBayesClassifier(smoothing=0.5).fit(X, y)
    train_time = time.perf_counter() - t0
    print(f"[+] Training done  ({train_time*1000:.0f} ms)")
    print()

    # ── Cross-validation ──────────────────────────────────────────
    print("[~] Running 5-fold cross-validation...")
    clf = MLIntentClassifier()
    t0 = time.perf_counter()
    acc = clf.cross_validate(k=5)
    cv_time = time.perf_counter() - t0
    bar  = "█" * int(acc * 30) + "░" * (30 - int(acc * 30))
    print(f"[+] CV accuracy: {acc*100:.1f}%  [{bar}]  ({cv_time*1000:.0f} ms)")
    print()

    # ── Per-intent sample check ───────────────────────────────────
    print("[~] Sample predictions (sanity check):")
    test_queries = [
        ("jaki mam procesor",            "hw_cpu"),
        ("ile mam ramu",                 "hw_ram"),
        ("dlaczego komputer jest wolny",  "why_slow"),
        ("temperatura karty graficznej",  "temperature"),
        ("co to jest svchost",            "process_info"),
        ("włącz turbo boost",             "turbo_boost"),
        ("what cpu do i have",            "hw_cpu"),
        ("why is my ram so high",         "ram_why_high"),
        ("disk health check",             "disk_health"),
        ("how are you",                   "small_talk"),
    ]
    for query, expected in test_queries:
        pred, conf = model.predict(query)
        status = "✓" if pred == expected else "✗"
        print(f"  {status}  \"{query}\"")
        print(f"      → {pred} ({conf:.0%})  expected: {expected}")
    print()

    # ── Save ──────────────────────────────────────────────────────
    print("[~] Saving model to data/cache/...")
    clf2 = MLIntentClassifier()
    clf2._model  = model
    clf2._ready  = True
    saved = clf2._train_and_save()
    if saved:
        print("[+] Model saved successfully")
    else:
        print("[!] Save failed — model will be retrained on next app launch")
    print()

    # ── Summary ───────────────────────────────────────────────────
    print("=" * 60)
    print(f"  Intents   : {n_intents}")
    print(f"  Examples  : {n_examples}")
    print(f"  Train time: {train_time*1000:.0f} ms")
    print(f"  CV acc    : {acc*100:.1f}%")
    if acc >= 0.85:
        print("  Status    : GOOD — ready for production")
    elif acc >= 0.70:
        print("  Status    : OK — consider adding more vocabulary phrases")
    else:
        print("  Status    : LOW — review vocabulary.py for ambiguous phrases")
    print("=" * 60)


if __name__ == "__main__":
    main()
