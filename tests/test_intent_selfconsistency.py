"""tests.test_intent_selfconsistency
THE strongest hck_GPT stability guard (2026-07-16): every multi-word phrase
in the vocabulary, parsed by the REAL parser, must route back to the intent
that declares it - except a reviewed ALLOWED set of semantic near-synonym
overlaps (both sides answer sensibly). Any NEW collision fails the build.
Born from a 3,118-phrase sweep that caught the guided-flow offer phrase
("zoptymalizuj komputer") being stolen by the legacy `optimization` intent.
"""
import unittest


# Reviewed overlaps: (phrase, declared_intent, actual_winner) - both answers
# are sensible for the phrasing; do NOT grow this list without a review.
ALLOWED = {
    ("co najbardziej obciąża dysk", "top_resource_hog"),
    ("co najbardziej obciąża pamięć", "top_resource_hog"),
    ("co o mnie wiesz", "ai_context"),
    ("co pożera ram", "ram_why_high"),
    ("co się zmieniło od wczoraj", "pc_changes"),
    ("co to za program", "process_info"),
    ("co zajmuje dysk", "disk_usage_why"),
    ("co zużywa ram", "ram_why_high"),
    ("co żre ram", "processes"),
    # template phrase with a literal X placeholder (ML corpus fodder)
    ("czy X w autostarcie jest potrzebny", "startup_safety"),
    ("czy mogę grać", "game_ready"),
    ("dlaczego program X działa inaczej", "app_behavior_change"),
    ("głośny wentylator", "fan_noise_history"),
    ("is this process safe", "process_identity"),
    ("jak poprawić fps", "speed_up_pc"),
    ("komputer chodzi wolno", "speed_up_pc"),
    # ł-fold fix (2026-07-21) folds wyłączyć->wylaczyc, so these "what can I
    # disable to be faster" phrases now tie to unnecessary_programs (the
    # what-to-disable list) - a precise, sensible answer for that phrasing.
    ("co moge wylaczyc zeby pc byl szybszy", "speed_up_pc"),
    ("co wylaczyc zeby szybszy", "speed_up_pc"),
    ("pc runs slow", "why_slow"),
    ("pre-gaming optimization", "game_ready"),
    ("problemy z dyskiem", "disk_health"),
    # scorer matches substrings without word boundaries: "ram usage" in
    # "vram usage" - future refinement candidate, harmless answer meanwhile
    ("vram usage", "vram_usage"),
    ("what does this process do", "process_identity"),
    ("what is eating my ram", "top_resource_hog"),
    ("what is this program", "process_info"),
    ("what's my ram usage", "performance"),
    ("why is pc so loud", "symptom_noisy"),
}


class TestPhraseSelfConsistency(unittest.TestCase):

    def test_every_multiword_phrase_routes_home(self):
        from hck_gpt.intents.vocabulary import INTENT_PATTERNS
        from hck_gpt.intents.parser import IntentParser
        p = IntentParser()
        new_collisions = []
        for intent, phrases in INTENT_PATTERNS.items():
            for ph in phrases:
                if " " not in ph:
                    continue
                got = p.parse(ph).intent
                if got != intent and (ph, intent) not in ALLOWED:
                    new_collisions.append((ph, intent, got))
        self.assertEqual(
            new_collisions, [],
            "NEW phrase collisions (phrase, declared, winner) - either fix "
            "the vocabulary or consciously review into ALLOWED: "
            + repr(new_collisions[:12]))

    def test_no_phrase_duplicated_inside_one_intent(self):
        from hck_gpt.intents.vocabulary import INTENT_PATTERNS
        dupes = []
        for intent, phrases in INTENT_PATTERNS.items():
            seen = set()
            for ph in phrases:
                if ph in seen:
                    dupes.append((intent, ph))
                seen.add(ph)
        self.assertEqual(dupes, [], f"self-duplicated phrases: {dupes}")

    def test_flow_offer_phrase_reaches_the_flow(self):
        """The speed_up_pc offer says 'napisz: zoptymalizuj komputer' -
        that exact phrase MUST start the guided flow."""
        from hck_gpt.intents.parser import IntentParser
        self.assertEqual(IntentParser().parse("zoptymalizuj komputer").intent,
                         "optimize_guide")


if __name__ == "__main__":
    unittest.main()

class TestNoSlopInResponses(unittest.TestCase):
    """Public-text style rule (CLAUDE.md): chat responses are public-facing -
    no em-dashes. A 2026-07-16 sweep found 100 of them; never again."""

    # Built from the codepoint ON PURPOSE: a 2026-07-17 repo-wide "replace
    # every em-dash" sweep rewrote the literal inside this very test,
    # silently turning it into "does the answer contain a hyphen" (always
    # true). chr(0x2014) is plain ASCII - no text sweep can ever eat it.
    EM_DASH = chr(0x2014)

    def test_no_emdash_in_any_response(self):
        from hck_gpt.intents.vocabulary import INTENT_PATTERNS
        from hck_gpt.responses.builder import ResponseBuilder
        from hck_gpt.intents.parser import ParseResult
        rb = ResponseBuilder()
        offenders = []
        for intent in INTENT_PATTERNS:
            for lang in ("pl", "en"):
                out = getattr(rb, f"_resp_{intent}")(ParseResult(
                    intent=intent, confidence=1.0, entities={},
                    raw_text="t"), lang)
                if self.EM_DASH in "\n".join(str(x) for x in out):
                    offenders.append((intent, lang))
        self.assertEqual(offenders, [],
                         f"em-dash slop in responses: {offenders}")
