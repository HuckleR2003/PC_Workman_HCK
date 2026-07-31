"""Deep multi-turn guards for hck_GPT's Conversation Director."""
import unittest
from itertools import product
from types import SimpleNamespace
from unittest import mock

from hck_gpt.intents.parser import IntentParser, ParseResult
from hck_gpt.memory.session_memory import SessionMemory
from hck_gpt.responses.builder import ResponseBuilder


def _result(intent, raw, confidence=1.0):
    return ParseResult(
        intent=intent, confidence=confidence, entities={}, raw_text=raw,
    )


class TestConversationFrame(unittest.TestCase):
    def setUp(self):
        self.mem = SessionMemory()
        self.parser = IntentParser()

    def _start_slow_game(self, raw="laguje kiedy gram"):
        with mock.patch.object(
                SessionMemory, "collect_live_evidence", return_value={}):
            self.mem.remember_turn(
                _result("why_slow", raw), ["hck_GPT: sprawdzam problem"],
            )

    def test_frame_carries_goal_symptom_and_context(self):
        self._start_slow_game()
        frame = self.mem.frame_snapshot()
        self.assertEqual(frame["goal"], "diagnose")
        self.assertEqual(frame["symptom"], "slow")
        self.assertEqual(frame["evidence"]["context"], "gaming")
        self.assertIn("when_during_game", frame["missing_evidence"])
        self.assertIn("lag_type", frame["missing_evidence"])

    def test_frame_expires_instead_of_leaking_old_problem(self):
        self._start_slow_game()
        frame = self.mem.active_frame()
        self.assertIsNotNone(frame)
        self.assertIsNone(self.mem.active_frame(now=frame.expires_at + 0.1))

    def test_advice_has_before_measurement_and_state(self):
        evidence = {"cpu_pct": 70.0, "ram_pct": 80.0, "captured_at": 1}
        with mock.patch.object(
                SessionMemory, "collect_live_evidence", return_value=evidence):
            self.mem.remember_turn(
                _result("optimization", "bezpiecznie zoptymalizuj komputer"),
                ["hck_GPT: Zacznij od autostartu."],
            )
        frame = self.mem.frame_snapshot()
        self.assertEqual(frame["advice_state"], "offered")
        self.assertEqual(frame["verification_state"], "waiting")
        self.assertEqual(frame["baseline"]["ram_pct"], 80.0)

    def test_temperature_delta_requires_same_real_sensor_source(self):
        self._start_slow_game()
        frame = self.mem.active_frame()
        frame.baseline = {"cpu_temp": 70.0, "cpu_temp_source": "sensor"}
        no_source = self.mem.compare_frame_evidence({"cpu_temp": 60.0})
        self.assertNotIn("cpu_temp", no_source)
        real = self.mem.compare_frame_evidence(
            {"cpu_temp": 60.0, "cpu_temp_source": "sensor"})
        self.assertEqual(real["cpu_temp"], -10.0)

    def test_correction_changes_subject_without_losing_goal(self):
        with mock.patch.object(
                SessionMemory, "collect_live_evidence", return_value={}):
            self.mem.remember_turn(
                _result("gpu_temp_why", "dlaczego gpu jest gorące"),
                ["hck_GPT: GPU"],
            )
        goal = self.mem.frame_snapshot()["goal"]
        kind, value = self.mem.correct_subject_from_text(
            "nie chodzi o GPU, tylko CPU")
        self.assertEqual((kind, value), ("component", "cpu"))
        self.assertEqual(self.mem.frame_snapshot()["goal"], goal)

    def test_english_correction_uses_the_meant_subject_not_negated_one(self):
        kind, value = self.mem.correct_subject_from_text(
            "I meant CPU, not GPU")
        self.assertEqual((kind, value), ("component", "cpu"))

    def test_short_corrections_choose_the_asserted_subject(self):
        cases = (
            ("nie GPU tylko CPU", "cpu"),
            ("not GPU but CPU", "cpu"),
            ("not GPU, CPU", "cpu"),
            ("CPU rather than GPU", "cpu"),
            ("pomyliłem się, chodziło mi o RAM", "ram"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                kind, value = self.mem.correct_subject_from_text(raw)
                self.assertEqual((kind, value), ("component", expected))

    def test_frame_is_present_in_llm_context(self):
        self._start_slow_game()
        context = self.mem.get_context_for_llm()
        self.assertIn("Active diagnostic frame", context)
        self.assertIn("context=gaming", context)


class TestHumanFollowupSequences(unittest.TestCase):
    """More than 50 compact human replies must continue one diagnosis."""

    CONTEXT_REPLIES = (
        "w grze", "podczas gry", "kiedy gram", "przy graniu",
        "in game", "while gaming", "when i play", "during games",
        "w przeglądarce", "podczas przeglądania", "in browser",
        "while browsing", "przy starcie", "after boot", "at startup",
        "na pulpicie", "w spoczynku", "on desktop", "at idle",
    )
    TIMING_REPLIES = (
        "po 5 minutach", "po 20 minutach", "po 2 godzinach",
        "od razu", "po chwili", "z czasem", "after 10 minutes",
        "after 1 hour", "right away", "after a while", "over time",
    )
    LAG_REPLIES = (
        "bardziej ścina niż laguje", "mam spadki klatek", "spadają fps",
        "to mikroprzycięcia", "rośnie ping", "postać teleportuje",
        "it stutters", "frame drops", "fps drops", "network lag",
        "rubberbanding and latency",
    )
    GAME_REPLIES = (
        "tylko w Valorant", "w Cyberpunk 2077", "tylko Fortnite",
        "podczas Minecraft", "in Counter-Strike 2", "only in Apex Legends",
        "in Elden Ring", "while playing Warzone",
    )
    CONTROL_REPLIES = (
        ("zrobiłem to co dalej", "verify_after_action"),
        ("jest lepiej po zmianie", "verify_after_action"),
        ("bez zmian po tej poradzie", "verify_after_action"),
        ("dlaczego to radzisz", "explain_previous_advice"),
        ("czemu mam to zrobić", "explain_previous_advice"),
        ("nie chcę tego robić", "decline_advice"),
        ("porównaj teraz z wcześniej", "compare_after_change"),
        ("jak bardzo jesteś tego pewny", "explain_confidence"),
    )

    def _memory(self):
        mem = SessionMemory()
        with mock.patch.object(
                SessionMemory, "collect_live_evidence",
                return_value={"cpu_pct": 20.0, "ram_pct": 45.0}):
            mem.remember_turn(
                _result("why_slow", "laguje kiedy gram"),
                ["hck_GPT: sprawdzam i proponuję pomiar"],
            )
        return mem

    def test_49_detail_replies_continue_the_active_diagnosis(self):
        parser = IntentParser()
        replies = (self.CONTEXT_REPLIES + self.TIMING_REPLIES
                   + self.LAG_REPLIES + self.GAME_REPLIES)
        self.assertGreaterEqual(len(replies), 49)
        failures = []
        for reply in replies:
            mem = self._memory()
            parsed = parser.parse(reply)
            resolved = mem.resolve_followup(reply, parsed)
            if resolved.intent != "continue_diagnosis":
                failures.append((reply, parsed.intent, resolved.intent))
        self.assertEqual(failures, [])


class TestExpandedConversationLanguage(TestHumanFollowupSequences):
    """Natural variants, corrections and ambiguity stay inside one frame."""

    DETAIL_CASES = (
        ("w trakcie meczu", "context", "gaming"),
        ("jak odpalam gre", "context", "gaming"),
        ("when the game is running", "context", "gaming"),
        ("na chromie", "context", "browser"),
        ("on youtube", "context", "browser"),
        ("po zalogowaniu", "context", "startup"),
        ("while windows starts", "context", "startup"),
        ("sam pulpit", "context", "desktop"),
        ("with nothing open", "context", "desktop"),
        ("whatever i do", "context", "system_wide"),
        ("nie w grze, tylko na pulpicie", "context", "desktop"),
        ("not in game but in browser", "context", "browser"),
        ("po 30 sekundach", "timing", "30 sekundach"),
        ("after 45 seconds", "timing", "45 seconds"),
        ("po kilku min", "timing", "after_a_while"),
        ("once it warms up", "timing", "after_a_while"),
        ("w połowie meczu", "timing", "mid_session"),
        ("near the end of the match", "timing", "late_session"),
        ("od pierwszej minuty", "timing", "immediately"),
        ("cofa mnie i gubi pakiety", "lag_kind", "network"),
        ("klatki lecą w dół", "lag_kind", "fps"),
        ("rwie obraz", "lag_kind", "stutter"),
        ("myszka reaguje po czasie", "lag_kind", "input"),
        ("nie wiem czy ping czy fps", "lag_kind", "unclear"),
        ("czasem ping czasem fps", "lag_kind", "mixed"),
        ("pierwszy raz", "recurrence", "first_time"),
        ("za każdym razem", "frequency", "consistent"),
        ("not every match", "frequency", "intermittent"),
        ("tylko w tej grze", "scope", "one_game"),
        ("we wszystkich grach", "scope", "all_games"),
        ("po aktualizacji sterownika", "trigger", "driver_update"),
        ("after a windows update", "trigger", "windows_update"),
        ("po alt-tab", "trigger", "alt_tab"),
    )

    def _diagnosis(self):
        mem = SessionMemory()
        with mock.patch.object(
                SessionMemory, "collect_live_evidence", return_value={}):
            mem.remember_turn(
                _result("why_slow", "laguje kiedy gram"),
                ["hck_GPT: diagnosis"],
            )
        return mem

    def test_33_natural_details_are_extracted_without_guessing(self):
        mem = SessionMemory()
        self.assertEqual(len(self.DETAIL_CASES), 33)
        for raw, key, expected in self.DETAIL_CASES:
            with self.subTest(raw=raw):
                self.assertEqual(
                    mem.conversation_details(raw).get(key), expected,
                )

    def test_arbitrary_game_titles_survive_without_a_hardcoded_database(self):
        mem = SessionMemory()
        cases = (
            ("gram w Helldivers 2 po 10 minutach", "helldivers 2"),
            ("playing Baldur's Gate 3 after a while", "baldur's gate 3"),
            ("podczas gry w Starfield", "starfield"),
        )
        for raw, expected in cases:
            with self.subTest(raw=raw):
                details = mem.conversation_details(raw)
                self.assertEqual(details.get("game"), expected)
                self.assertEqual(details.get("context"), "gaming")

    def test_question_selector_asks_the_least_repeated_missing_detail(self):
        mem = self._diagnosis()
        mem.mark_frame_question("when_during_game")
        key, attempt = mem.next_frame_question(mark_asked=True)
        self.assertEqual((key, attempt), ("lag_type", 1))
        mem.record_frame_evidence({"lag_kind": "stutter"}, "diagnose")
        key, attempt = mem.next_frame_question(mark_asked=True)
        self.assertEqual((key, attempt), ("when_during_game", 2))

    def test_revised_context_is_auditable_instead_of_silently_overwritten(self):
        mem = self._diagnosis()
        mem.record_frame_evidence({"context": "desktop"}, "diagnose")
        frame = mem.frame_snapshot()
        self.assertEqual(frame["evidence"]["context"], "desktop")
        self.assertEqual(frame["revisions"][-1]["key"], "context")
        self.assertEqual(frame["revisions"][-1]["from"], "gaming")
        self.assertEqual(frame["revisions"][-1]["to"], "desktop")

    def test_short_slots_follow_the_goal_not_a_generic_diagnosis(self):
        parser = IntentParser()

        upgrade = SessionMemory()
        upgrade.remember_turn(
            _result("upgrade_advice", "chcę ulepszyć komputer"),
            ["hck_GPT: upgrade"],
        )
        resolved = upgrade.resolve_followup("2500 zł", parser.parse("2500 zł"))
        self.assertEqual(resolved.intent, "upgrade_budget")
        resolved = upgrade.resolve_followup(
            "głównie montaż video", parser.parse("głównie montaż video"))
        self.assertEqual(resolved.intent, "upgrade_workload")

        desktop = SessionMemory()
        desktop.remember_turn(
            _result("desktop_problem", "zniknęły ikony"),
            ["hck_GPT: desktop"],
        )
        resolved = desktop.resolve_followup(
            "pierwszy raz", parser.parse("pierwszy raz"))
        self.assertEqual(resolved.intent, "desktop_recurrence")

    def test_explicit_new_questions_are_not_stolen_by_old_timing_context(self):
        mem = self._diagnosis()
        parser = IntentParser()
        cases = (
            "jaka jest temperatura CPU po 20 minutach?",
            "czy Cyberpunk 2077 pójdzie na moim komputerze?",
            "czy GPU jest gorące po 10 minutach?",
        )
        for raw in cases:
            with self.subTest(raw=raw):
                parsed = parser.parse(raw)
                resolved = mem.resolve_followup(raw, parsed)
                self.assertNotEqual(resolved.intent, "continue_diagnosis")

    def test_400_varied_gaming_sequences_keep_a_complete_diagnosis(self):
        parser = IntentParser()
        contexts = (
            "w trakcie meczu", "jak odpalam gre", "gdy gram",
            "during a match", "while playing", "once i launch a game",
            "tylko w Valorant", "w grze Helldivers 2",
            "gram w Baldur's Gate 3", "podczas gry w Starfield",
        )
        timings = (
            "od pierwszej minuty", "po 30 sekundach", "po kilku min",
            "w połowie meczu", "pod koniec meczu", "after 10 minutes",
            "after a few minutes", "near the end of the match",
        )
        kinds = (
            "cofa mnie", "klatki lecą w dół", "rwie obraz",
            "myszka reaguje po czasie", "czasem ping czasem fps",
        )
        sequences = list(product(contexts, timings, kinds))
        self.assertEqual(len(sequences), 400)
        failures = []
        for context, timing, kind in sequences:
            mem = self._diagnosis()
            for reply in (context, timing, kind):
                resolved = mem.resolve_followup(reply, parser.parse(reply))
                if resolved.intent != "continue_diagnosis":
                    failures.append((reply, resolved.intent))
                    break
                mem.record_frame_evidence(
                    mem.conversation_details(reply), "diagnose",
                    resolved.intent,
                )
            else:
                frame = mem.frame_snapshot()
                if frame["missing_evidence"]:
                    failures.append((context, timing, kind, frame))
        self.assertEqual(failures, [])

    def test_control_replies_reach_their_frame_handlers(self):
        parser = IntentParser()
        failures = []
        for reply, expected in self.CONTROL_REPLIES:
            mem = self._memory()
            frame = mem.active_frame()
            frame.baseline = {"cpu_pct": 30.0}
            resolved = mem.resolve_followup(reply, parser.parse(reply))
            if resolved.intent != expected:
                failures.append((reply, expected, resolved.intent))
        self.assertEqual(failures, [])

    def test_check_again_uses_saved_baseline_instead_of_restarting_answer(self):
        mem = self._memory()
        resolved = mem.resolve_followup(
            "sprawdź ponownie", IntentParser().parse("sprawdź ponownie"))
        self.assertEqual(resolved.intent, "compare_after_change")

    def test_exact_three_turn_gaming_chain_never_forgets_game_context(self):
        mem = self._memory()
        parser = IntentParser()
        for reply, expected_key, expected_value in (
            ("w grze", "context", "gaming"),
            ("po 20 minutach", "timing", "20 minutach"),
            ("bardziej ścina niż laguje", "lag_kind", "stutter"),
        ):
            parsed = mem.resolve_followup(reply, parser.parse(reply))
            self.assertEqual(parsed.intent, "continue_diagnosis", reply)
            details = mem.conversation_details(reply)
            mem.record_frame_evidence(details, "diagnose", parsed.intent)
            evidence = mem.frame_snapshot()["evidence"]
            self.assertEqual(evidence[expected_key], expected_value)
            self.assertEqual(evidence["context"], "gaming")
        self.assertEqual(mem.frame_snapshot()["missing_evidence"], [])

    def test_60_four_turn_gaming_conversations_reach_complete_context(self):
        parser = IntentParser()
        contexts = (
            "w grze", "podczas gry", "in game", "tylko w Valorant",
            "in Counter-Strike 2",
        )
        timings = (
            "od razu", "po 5 minutach", "po 20 minutach",
            "after 10 minutes", "after a while", "over time",
        )
        kinds = ("bardziej ścina niż laguje", "spadają fps")
        sequences = list(product(contexts, timings, kinds))
        self.assertEqual(len(sequences), 60)
        failures = []
        for context, timing, kind in sequences:
            mem = self._memory()
            for reply in (context, timing, kind):
                parsed = mem.resolve_followup(reply, parser.parse(reply))
                if parsed.intent != "continue_diagnosis":
                    failures.append((context, timing, kind, reply, parsed.intent))
                    break
                mem.record_frame_evidence(
                    mem.conversation_details(reply), "diagnose", parsed.intent)
            else:
                frame = mem.frame_snapshot()
                evidence = frame["evidence"]
                if (evidence.get("context") != "gaming"
                        or "timing" not in evidence
                        or "lag_kind" not in evidence
                        or frame["missing_evidence"]):
                    failures.append((context, timing, kind, frame))
        self.assertEqual(failures, [])


class TestConversationResponses(unittest.TestCase):
    def setUp(self):
        self.mem = SessionMemory()
        self.rb = ResponseBuilder()
        self.memory_patch = mock.patch(
            "hck_gpt.memory.session_memory.session_memory", self.mem)
        self.memory_patch.start()

    def tearDown(self):
        self.memory_patch.stop()

    def test_lag_while_gaming_response_does_not_ask_game_or_desktop_again(self):
        fake_snap = {"cpu_pct": 12.0, "ram_pct": 42.0, "gpu_load": 15.0}
        with mock.patch(
                "hck_gpt.context.system_context.system_context.snapshot",
                return_value=fake_snap), mock.patch(
                "hck_gpt.memory.user_knowledge.user_knowledge.get_all_hardware",
                return_value={}), mock.patch(
                "hck_gpt.memory.user_knowledge.user_knowledge.get_all_patterns",
                return_value={}):
            out = self.rb._resp_why_slow(
                _result("why_slow", "Laguje kiedy gram"), "pl")
        joined = " ".join(out).lower()
        self.assertIn("podczas grania", joined)
        self.assertNotIn("gra? przeglądarka?", joined)
        self.assertIn("kilkunastu minutach", joined)

    def test_continue_handler_accepts_short_detail_and_asks_one_question(self):
        with mock.patch.object(
                SessionMemory, "collect_live_evidence", return_value={}):
            self.mem.remember_turn(
                _result("why_slow", "komputer laguje"),
                ["hck_GPT: diagnoza"],
            )
        out = self.rb._resp_continue_diagnosis(
            _result("continue_diagnosis", "w grze"), "pl")
        joined = " ".join(out)
        self.assertIn("tej samej diagnozy", joined)
        self.assertEqual(joined.count("?"), 1)
        self.assertEqual(
            self.mem.frame_snapshot()["evidence"]["context"], "gaming")

    def test_verify_never_claims_success_from_action_alone(self):
        with mock.patch.object(
                SessionMemory, "collect_live_evidence",
                return_value={"cpu_pct": 20.0}):
            self.mem.remember_turn(
                _result("optimization", "optymalizuj"),
                ["hck_GPT: zamknij zbędną aplikację"],
            )
        out = self.rb._resp_verify_after_action(
            _result("verify_after_action", "zrobiłem to"), "pl")
        joined = " ".join(out).lower()
        self.assertIn("nie ogłoszę sukcesu", joined)
        self.assertEqual(joined.count("?"), 1)


class TestChatEntryRouting(unittest.TestCase):
    def test_greeting_does_not_swallow_a_real_problem(self):
        import hck_gpt.chat_handler as chat_module
        handler = object.__new__(chat_module.ChatHandler)
        handler.wizard = SimpleNamespace(is_active=lambda: False)
        handler._pending_reset = False
        handler._last_lang = "pl"
        memory = SessionMemory()
        with mock.patch.object(chat_module, "session_memory", memory), \
             mock.patch(
                 "hck_gpt.memory.session_memory.session_memory", memory), \
             mock.patch.object(
                chat_module.hybrid_engine, "process",
                return_value=["hck_GPT: routed diagnosis"]) as process:
            out = handler.process_message("hej laguje kiedy gram", ui_lang="pl")
        self.assertEqual(out, ["hck_GPT: routed diagnosis"])
        self.assertEqual(process.call_args.args[1].intent, "why_slow")


if __name__ == "__main__":
    unittest.main()
