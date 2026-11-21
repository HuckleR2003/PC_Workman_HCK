"""Read-only quality audit for hck_GPT.

This is a diagnostic harness, not a production test suite. It compares the
keyword parser with the trained ML path, checks response reachability, probes
offline fallbacks, and exercises confirmation parsing without applying actions.

Run:
    python -B scripts/audit_hck_gpt.py
"""
from __future__ import annotations

import random
import os
import sys
import time
from collections import defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Windows consoles may still use cp1250. Keep the audit readable instead of
# failing when a response contains an emoji or another unsupported glyph.
try:
    sys.stdout.reconfigure(errors="backslashreplace")
except (AttributeError, ValueError):
    pass


ROUTE_CASES = [
    # Hardware and current state
    ("jaki dokładnie procesor siedzi w tym komputerze", {"hw_cpu"}),
    ("pokaż model gpu i ilość vram", {"hw_gpu"}),
    ("ile fizycznie mam pamięci operacyjnej", {"hw_ram"}),
    ("what motherboard is installed in this machine", {"hw_motherboard"}),
    ("show every drive and how much space is left", {"hw_storage"}),
    ("daj mi pełną specyfikację tego komputera", {"hw_all"}),
    ("czy z temperaturami jest teraz wszystko w porządku", {"temperature"}),
    ("is my processor thermal throttling right now", {"throttle_check"}),
    ("który podzespół jest teraz najgorętszy", {"hottest_component"}),
    ("czy napięcia zasilacza wyglądają normalnie", {"voltage_check"}),
    # Slowness and diagnosis
    ("komputer od paru dni wyraźnie zamula", {"why_slow", "speed_up_pc"}),
    ("everything started stuttering this week", {"why_slow", "symptom_freeze"}),
    ("dlaczego pamięć jest prawie pełna", {"ram_why_high"}),
    ("what is hammering my disk right now", {"disk_usage_why", "top_resource_hog"}),
    ("który program najbardziej obciąża komputer", {"top_resource_hog", "processes"}),
    ("czy plik wymiany jest teraz używany", {"swap_analysis"}),
    ("przeglądarka pożera mi całą pamięć", {"browser_cache", "ram_why_high"}),
    ("po godzinie grania zaczynają się spadki fps", {"fps_degradation", "gaming_session"}),
    ("czy wydajność pogorszyła się od zeszłego tygodnia", {"perf_change", "weekly_trends"}),
    ("co zmieniło się na komputerze od wczoraj", {"pc_changes", "session_compare"}),
    # Processes, safety, startup
    ("czym jest svchost.exe i czy jest bezpieczny", {"process_identity", "process_info"}),
    ("can I safely close explorer.exe", {"process_kill", "process_identity"}),
    ("czy mogę zakończyć ten proces bez uszkodzenia systemu", {"process_kill"}),
    ("co uruchamia się razem z windowsem", {"startup_check"}),
    ("czy discord musi startować razem z systemem", {"startup_safety"}),
    ("why did this application behave differently today", {"app_behavior_change"}),
    ("których programów praktycznie nie używam", {"stale_apps"}),
    ("czy sterowniki wyglądają na aktualne", {"driver_status"}),
    ("sprawdź czy ten proces może być wirusem", {"virus_check", "process_identity"}),
    # Gaming, power and battery
    ("czy cyberpunk pójdzie płynnie na moim sprzęcie", {"game_can_run"}),
    ("przygotuj komputer zanim uruchomię grę", {"game_ready", "gaming_session"}),
    ("która gra najmocniej obciąża kartę", {"game_hardware_stress"}),
    ("ile czasu spędzam w grach a ile w pracy", {"gaming_vs_work_time"}),
    ("ile pamięci zwykle bierze granie", {"gaming_ram_usage"}),
    ("jak szybko rozładowuje się teraz bateria", {"battery_drain_rate", "battery_estimate"}),
    ("how much battery time do I have left", {"battery_estimate"}),
    ("jaki plan zasilania jest aktywny", {"power_plan"}),
    ("czy pobór energii zmienił się po restarcie", {"power_after_restart"}),
    # Upgrade and compatibility
    ("co powinienem wymienić jako pierwsze", {"upgrade_advice"}),
    ("czy w ogóle warto rozbudowywać ten zestaw", {"upgrade_feasibility"}),
    ("mam b460 i chcę włożyć i5 11400f, czy zadziała", {"upgrade_compat"}),
    ("will an rtx 4070 work with my current pc", {"upgrade_compat"}),
    ("czy zestaw ddr5 6000 będzie pasował", {"ram_compat"}),
    ("jaki ram mogę bezpiecznie dołożyć", {"ram_compat", "upgrade_feasibility"}),
    # History, conversation and assistant identity
    ("porównaj obecną sesję z poprzednią", {"session_compare", "session_digest"}),
    ("zrób krótkie podsumowanie dzisiejszej sesji", {"session_digest", "stats"}),
    ("czy temperatury rosną z tygodnia na tydzień", {"thermal_history", "temp_comparison"}),
    ("co pamiętasz z naszej ostatniej odpowiedzi", {"recall_numbers"}),
    ("co już wiesz o sposobie w jaki używam komputera", {"ai_context", "privacy_data"}),
    ("jakie dane przechowujesz i gdzie", {"privacy_data"}),
    ("kim jest autor pc workmana", {"about_author"}),
    ("czym właściwie jest pc workman", {"about_program"}),
    ("co potrafisz i o co mogę zapytać", {"help"}),
    # Polish without diacritics, typos and mixed language
    ("dlaczego moj komp sie tak grzeje", {"temperature", "gpu_temp_why"}),
    ("czy procek sie dlawi pod obciazeniem", {"throttle_check"}),
    ("pokaz mi najciezszy proces teraz", {"top_resource_hog", "processes"}),
    ("my komputer jest wolny od wczoraj", {"why_slow", "speed_up_pc"}),
    ("sprawdz gpu temperature please", {"temperature", "gpu_temp_why"}),
    ("czy rtx 4070 fit do mojego pc", {"upgrade_compat"}),
    # Deliberately vague inputs. These should not become confident facts.
    ("coś jest nie tak", {"unknown", "health_check"}),
    ("sprawdź to", {"unknown"}),
    ("dlaczego", {"unknown"}),
]


OOD_CASES = [
    "jaka będzie jutro pogoda",
    "napisz mi przepis na naleśniki",
    "opowiedz historię o smoku",
    "my cat is sleeping on the keyboard",
    "banana telescope purple",
    "who won the football match",
    "pomóż mi napisać list motywacyjny",
    "ile kilometrów jest do berlina",
    "translate this sentence into spanish",
    "what is the capital of france",
]


LANG_CASES = [
    ("jaki mam procesor", "pl"),
    ("jaki mam procesor?", "pl"),
    ("what cpu do I have", "en"),
    ("show gpu temperature", "en"),
    ("hej, check my ram", "pl"),
    ("please sprawdź temperaturę", "pl"),
    ("cpu", "pl"),
    ("gpu?", "pl"),
    ("thanks", "en"),
    ("dzieki", "pl"),
]


def _set_ml(model) -> None:
    from hck_gpt.intents.ml_classifier import ml_classifier
    ml_classifier._model = model
    ml_classifier._ready = model is not None


def _fresh_parser():
    from hck_gpt.intents.parser import IntentParser
    IntentParser._folded_cache = {}
    return IntentParser()


def _run_routes(label: str, model) -> list[tuple[str, str, set[str], float]]:
    _set_ml(model)
    parser = _fresh_parser()
    misses = []
    for text, accepted in ROUTE_CASES:
        result = parser.parse(text)
        if result.intent not in accepted:
            misses.append((text, result.intent, accepted, result.confidence))
    print(f"{label}: {len(ROUTE_CASES) - len(misses)}/{len(ROUTE_CASES)} accepted")
    for text, got, accepted, confidence in misses:
        print(f"  MISS {text!r} -> {got} ({confidence:.3f}), expected {sorted(accepted)}")
    return misses


def _grouped_phrase_cv(k: int = 5) -> float:
    """Phrase-group CV without leaking augmentations across train/test folds."""
    from hck_gpt.intents.ml_classifier import (
        NaiveBayesClassifier,
        _ascii_fold,
    )
    from hck_gpt.intents.vocabulary import INTENT_PATTERNS

    groups = []
    excluded = {
        "jest", "moje", "moja", "mamy", "maja",
        "what", "does", "this", "that", "have", "with",
    }
    for intent, phrases in INTENT_PATTERNS.items():
        for phrase in phrases:
            augmented = [phrase]
            folded = _ascii_fold(phrase)
            if folded != phrase:
                augmented.append(folded)
            words = phrase.split()
            if len(words) >= 3:
                for word in words:
                    if len(word) >= 4 and _ascii_fold(word) not in excluded:
                        augmented.append(word)
                        folded_word = _ascii_fold(word)
                        if folded_word != word:
                            augmented.append(folded_word)
            groups.append((intent, phrase, augmented))

    rng = random.Random(42)
    rng.shuffle(groups)
    correct = total = 0
    for fold_index in range(k):
        train_x, train_y, valid = [], [], []
        for index, (intent, phrase, augmented) in enumerate(groups):
            if index % k == fold_index:
                valid.append((phrase, intent))
            else:
                train_x.extend(augmented)
                train_y.extend([intent] * len(augmented))
        model = NaiveBayesClassifier().fit(train_x, train_y)
        for phrase, intent in valid:
            correct += model.predict(phrase)[0] == intent
            total += 1
    return correct / total if total else 0.0


def _train_in_memory():
    from hck_gpt.intents.ml_classifier import (
        NaiveBayesClassifier,
        TrainingDataBuilder,
    )
    x_values, y_values = TrainingDataBuilder().build()
    model = NaiveBayesClassifier().fit(x_values, y_values)
    return model, len(x_values)


def _inventory() -> None:
    from hck_gpt.intents.vocabulary import INTENT_PATTERNS
    from hck_gpt.responses.builder import ResponseBuilder

    builder = ResponseBuilder()
    phrases = [
        (intent, phrase)
        for intent, intent_phrases in INTENT_PATTERNS.items()
        for phrase in intent_phrases
    ]
    handlers = {
        name[6:]
        for name in dir(builder)
        if name.startswith("_resp_") and callable(getattr(builder, name))
    }
    duplicates = defaultdict(set)
    for intent, phrase in phrases:
        duplicates[phrase].add(intent)
    cross_duplicates = {
        phrase: intents
        for phrase, intents in duplicates.items()
        if len(intents) > 1
    }
    print(
        f"inventory: intents={len(INTENT_PATTERNS)}, handlers={len(handlers)}, "
        f"phrases={len(phrases)}, multiword={sum(' ' in p for _, p in phrases)}, "
        f"cross_intent_exact_duplicates={len(cross_duplicates)}, "
        f"aliases={len(builder._INTENT_ALIASES)}"
    )
    print("missing handlers:", sorted(set(INTENT_PATTERNS) - handlers))
    print("orphan handlers:", sorted(handlers - set(INTENT_PATTERNS)))
    print("production aliases with dedicated source handlers:")
    for source, target in builder._INTENT_ALIASES.items():
        print(f"  {source} -> {target} (source_handler={source in handlers})")


def _handler_harness() -> None:
    from hck_gpt.engine.flow_engine import flow_engine
    from hck_gpt.intents.parser import ParseResult
    from hck_gpt.intents.vocabulary import INTENT_PATTERNS
    from hck_gpt.responses.builder import ResponseBuilder

    builder = ResponseBuilder()
    direct_failures = []
    build_failures = []
    for intent in INTENT_PATTERNS:
        for lang in ("pl", "en"):
            result = ParseResult(
                intent=intent,
                confidence=1.0,
                entities={},
                raw_text="audit",
            )
            try:
                direct = getattr(builder, f"_resp_{intent}")(result, lang)
                if not isinstance(direct, list) or not direct:
                    direct_failures.append((intent, lang, "empty"))
            except Exception as exc:
                direct_failures.append((intent, lang, repr(exc)))
            finally:
                flow_engine.abort()
            try:
                built = builder.build(result, lang)
                if not isinstance(built, list) or not built:
                    build_failures.append((intent, lang, "empty"))
            except Exception as exc:
                build_failures.append((intent, lang, repr(exc)))
            finally:
                flow_engine.abort()
    print(
        f"handler direct calls: {len(INTENT_PATTERNS) * 2 - len(direct_failures)}"
        f"/{len(INTENT_PATTERNS) * 2}"
    )
    print(
        f"handler production build: {len(INTENT_PATTERNS) * 2 - len(build_failures)}"
        f"/{len(INTENT_PATTERNS) * 2}"
    )
    for item in direct_failures[:20]:
        print("  DIRECT_FAIL", item)
    for item in build_failures[:20]:
        print("  BUILD_FAIL", item)


def _offline_fallbacks() -> None:
    from hck_gpt.engine.hybrid_engine import HybridEngine
    from hck_gpt.intents.parser import ParseResult

    engine = HybridEngine()
    engine._available = False
    engine._available_checked_at = time.time()
    print("offline preferred-intent fallbacks:")
    for intent in sorted(engine._OLLAMA_PREFERRED_INTENTS):
        result = ParseResult(intent=intent, confidence=1.0, raw_text="audit")
        output = engine.process("audit", result, lang="pl")
        print(f"  {intent}: {'response' if output else 'NONE'}")


def _ood(model) -> None:
    _set_ml(model)
    parser = _fresh_parser()
    print("out-of-domain probes with production ML enabled:")
    high = 0
    for text in OOD_CASES:
        result = parser.parse(text)
        high += result.confidence >= 0.70
        print(f"  {text!r} -> {result.intent} ({result.confidence:.3f})")
    print(f"OOD at ML hard-win confidence >=0.70: {high}/{len(OOD_CASES)}")


def _language() -> None:
    from hck_gpt.intents.lang_detect import detect_language
    misses = []
    for text, expected in LANG_CASES:
        got = detect_language(text)
        if got != expected:
            misses.append((text, got, expected))
    print(f"language detection: {len(LANG_CASES) - len(misses)}/{len(LANG_CASES)}")
    for item in misses:
        print("  LANG_MISS", item)


def _confirmation_safety() -> None:
    from hck_gpt.service_setup_wizard import ServiceSetupWizard

    wizard = ServiceSetupWizard()
    wizard._apply_optimization = lambda: ["APPLIED"]
    print("service wizard confirmation probes:")
    for text in ("yes", "tak", "no", "nie", "no thanks", "not now", "nie teraz"):
        wizard.state = "confirmation"
        output = wizard.process_input(text)
        applied = output == ["APPLIED"]
        print(f"  {text!r}: {'APPLY' if applied else 'cancel/no-apply'}")


def _end_to_end_samples(model) -> None:
    """Run safe chat entry-point probes without starting scans or writing logs."""
    from hck_gpt import chat_handler as chat_module
    from hck_gpt.engine.flow_engine import flow_engine
    from hck_gpt.memory.session_memory import session_memory

    class _IdleWizard:
        @staticmethod
        def is_active():
            return False

    handler = object.__new__(chat_module.ChatHandler)
    handler.wizard = _IdleWizard()
    handler.services_manager = None
    handler.insights = None
    handler._last_lang = "pl"
    handler._pending_reset = False

    _set_ml(model)
    chat_module.hybrid_engine._available = False
    chat_module.hybrid_engine._available_checked_at = time.time()
    original_log = chat_module.user_knowledge.log_message
    chat_module.user_knowledge.log_message = lambda *args, **kwargs: None

    samples = [
        "cpu",
        "dlaczego pamięć jest prawie pełna",
        "dlaczego mój komp się tak grzeje",
        "komputer od paru dni wyraźnie zamula",
        "co zmieniło się na komputerze od wczoraj",
        "can I safely close explorer.exe",
        "przygotuj komputer zanim uruchomię grę",
        "co już wiesz o sposobie w jaki używam komputera",
        "kim jest autor pc workmana",
        "pomóż mi napisać list motywacyjny",
    ]
    print("safe end-to-end offline samples:")
    try:
        for text in samples:
            flow_engine.abort()
            session_memory._messages.clear()
            session_memory._topic_stack.clear()
            session_memory._session_data.clear()
            output = handler.process_message(text, ui_lang="auto")
            first = str(output[0])[:120] if output else "NONE"
            print(
                f"  {text!r} -> topic={session_memory.current_topic()!r}, "
                f"first={first!r}"
            )
    finally:
        chat_module.user_knowledge.log_message = original_log
        flow_engine.abort()


def main() -> None:
    print("== hck_GPT quality audit ==")
    _inventory()
    print()

    print("== routing without ML ==")
    _run_routes("keyword parser", None)
    print()

    print("== in-memory ML ==")
    model, sample_count = _train_in_memory()
    print(f"training samples: {sample_count}")
    print(f"grouped original-phrase CV: {_grouped_phrase_cv() * 100:.2f}%")
    _run_routes("production parser + ML", model)
    print()

    print("== OOD behavior ==")
    _ood(model)
    print()

    print("== language ==")
    _language()
    print()

    print("== response execution ==")
    _handler_harness()
    print()

    print("== offline behavior ==")
    _offline_fallbacks()
    print()

    print("== confirmation safety ==")
    _confirmation_safety()
    print()

    print("== safe end-to-end samples ==")
    _end_to_end_samples(model)


if __name__ == "__main__":
    main()
