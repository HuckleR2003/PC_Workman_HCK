"""tests.test_conversations - hck_GPT after the long test, group C (2026-11-16).

28 of 71 questions in the first long test ended in "I did not understand".
Every group below holds the question Marcin asked first, then variants: no
Polish letters, typos, short forms, English. Each variant must reach the
intent that answers it. ACCEPT lists the other intents that answer the same
thing well (an existing health report for "is everything ok", the guide list
for "where are the guides").
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = {
 "overlay_where": ["Gdzie znajde zakladke w grze?", "jest zakladka w grze?", "Gdzie jest in-game overlay?",
                   "jak wlaczyc nakladke w grze", "gdzie overlay", "pokaz fps w grze",
                   "jak miec statystyki w grze", "gdzie jest mini monitor", "where is the in-game overlay"],
 "pc_status": ["Wszystko dziala?", "wszystko gra?", "czy wszystko dobrze chodzi?", "czy cos zle chodzi?",
               "wszystko dziala dobrze?", "czy komputer jest ok", "czy cos jest nie tak", "stan kompa",
               "jak sie czuje pc", "is everything ok", "is my pc fine", "anything wrong?", "co z kompem"],
 "why_slow": ["skad sa lagi?", "czemu zacina?", "dlaczego tnie", "czemu klatkuje", "spadki fps",
              "przycina mi gra", "czemu komputer muli", "co spowalnia komputer", "why is it lagging",
              "why does my game stutter"],
 "top_resource_hog": ["co duzo zuzywa?", "co zjada ram", "co obciaza procesor", "co mi zre zasoby",
                      "co najwiecej bierze", "kto zjada cpu", "what is using my ram"],
 "upgrade_advice": ["co moglbym ulepszyc?", "co wymienic w kompie", "co dokupic", "co warto ulepszyc",
                    "czy mam dobre gpu?", "czy mam dobry cpu?", "czy moja karta jest dobra",
                    "jak mocny jest moj procesor", "what should I upgrade"],
 "version_check": ["Czy mam najnowsza wersje?", "jaka mam wersje", "czy jest aktualizacja",
                   "jak zaktualizowac pc workman", "czy program jest aktualny", "am I on the latest version"],
 "website": ["Czy znajde gdzies strone programu?", "jaka jest strona programu", "gdzie pobrac",
             "link do strony", "gdzie znajde artykuly?", "gdzie sa poradniki", "website"],
 "ram_why_high": ["mam duze obciazenie ramu", "ram ciagle pelny", "brakuje mi ramu"],
 "about_author": ["Kto tworzy pc workman?", "Marcin hck firmuga", "kto cie zrobil", "who made you"],
 "free_space": ["co moge usunac?", "jak zwolnic miejsce", "co zajmuje miejsce", "czym zapchany dysk",
                "free up space"],
 "stale_apps": ["co moge odinstalowac?", "what can I uninstall"],
 "driver_update_where": ["Gdzie je zaktualizuje?", "gdzie zaktualizuje sterowniki?",
                         "jak zaktualizowac sterowniki", "skad pobrac sterownik", "aktualizacja sterownikow"],
 "ai_context": ["czy program juz sie nauczyl?", "ile sie nauczyles", "co o mnie wiesz",
                     "czego sie nauczyles", "znasz juz moj komputer"],
 "about_assistant": ["czy jestes ai?", "ai", "jestes chatgpt?", "jestes botem?", "kim jestes"],
 "ollama_info": ["Czy moge sie przelaczyc na ollama?", "ollama", "jak podlaczyc ollame", "czy obslugujesz lokalne ai"],
 "reaction": ["nice", "co powiesz?", "co to bylo xD", "super", "lol"],
}

# part_verdict (2026-11-17): "is my card good" now gets a verdict on that
# card from the gaming history, the 63-question library asked for it
ACCEPT = {"pc_status": {"health_check"}, "website": {"guides_available"},
          "ai_context": {"privacy_data"}, "upgrade_advice": {"part_verdict"}}


class TestEveryVariantIsUnderstood(unittest.TestCase):

    def test_routes(self):
        from hck_gpt.intents.parser import intent_parser
        wrong = []
        for want, questions in CASES.items():
            for q in questions:
                got = intent_parser.parse(q).intent
                if got != want and got not in ACCEPT.get(want, set()):
                    wrong.append(f"{q!r}: wanted {want}, got {got}")
        self.assertEqual(wrong, [])

    def test_every_new_intent_has_an_answer(self):
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        for intent in ("overlay_where", "pc_status", "version_check", "website",
                       "free_space", "driver_update_where", "about_assistant",
                       "ollama_info", "reaction", "about_author"):
            out = response_builder.build(ParseResult(intent, 1.0, raw_text="x"), "pl")
            self.assertTrue(out, intent)
            self.assertTrue(out[0].startswith("hck_GPT:"), intent)


class TestAnswers(unittest.TestCase):

    def _build(self, intent, lang="pl", text="x"):
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        return "\n".join(response_builder.build(ParseResult(intent, 1.0, raw_text=text), lang))

    def test_links_point_somewhere_real(self):
        self.assertIn("[-> In-Game Overlay]", self._build("overlay_where"))
        self.assertIn("[-> pcworkman.dev]", self._build("version_check"))
        self.assertIn("[-> Setup & Drivers]", self._build("driver_update_where"))
        import re
        src = open(os.path.join(ROOT, "ui", "windows", "main_window_expanded.py"),
                   encoding="utf-8").read()
        for name in ("In-Game Overlay", "Learning Center", "Setup & Drivers", "pcworkman.dev"):
            self.assertRegex(src, r'register_nav_callback\(\s*"' + re.escape(name) + '"', name)

    def test_version_age_uses_the_release_date(self):
        from utils.app_version import RELEASE_DATE
        import datetime
        datetime.date.fromisoformat(RELEASE_DATE)
        from utils.app_version import APP_VERSION
        self.assertIn(APP_VERSION, self._build("version_check"))

    def test_author_is_marcin(self):
        txt = self._build("about_author")
        self.assertIn("Marcin", txt)
        self.assertIn("Scaling Laws", txt)

    def test_not_chatgpt(self):
        self.assertIn("Nie jestem ChatGPT", self._build("about_assistant"))


class TestOptimizationGuide(unittest.TestCase):
    """Never confirms step 4: that would flush the RAM of the machine
    running the tests."""

    def setUp(self):
        from hck_gpt.engine.flow_engine import flow_engine
        flow_engine.abort()
        from hck_gpt.chat_handler import ChatHandler
        self.h = ChatHandler()

    def tearDown(self):
        from hck_gpt.engine.flow_engine import flow_engine
        flow_engine.abort()

    def test_cards_questions_and_buttons(self):
        h = self.h
        first = h.process_message("Zoptymalizuj komputer", ui_lang="pl")
        self.assertTrue(any(x.startswith("§STEP ") and "1/6" in x for x in first))
        self.assertFalse(any(x.startswith("↪") for x in first), "no 'waiting' on the start")
        self.assertEqual([c[0] for c in h.suggestions()], ["ZACZYNAJMY", "PRZERWIJ"])

        step2 = h.process_message("zaczynajmy", ui_lang="pl")
        self.assertTrue(any(x.startswith("§STEP ") and "2/6" in x for x in step2))
        self.assertTrue(any(x.startswith(("§OK ", "§WARN ")) for x in step2))
        labels = [c[0] for c in h.suggestions()]
        self.assertIn("DALEJ", labels)
        self.assertIn("Zobacz Autostart", labels)

        asked = h.process_message("nie ma nic do wylaczenia?", ui_lang="pl")
        self.assertFalse(h._trace.get("fallback"))
        self.assertTrue(asked[-1].startswith("↪"), asked)

        other = h.process_message("jaka mam karte graficzna?", ui_lang="pl")
        self.assertNotIn("Do wyłączenia", other[0], "a clear other question gets its own answer")
        self.assertTrue(other[-1].startswith("↪"))

        stop = h.process_message("przerwij", ui_lang="pl")
        self.assertIn("bez wprowadzania zmian", stop[0])
        self.assertIn("Co potrafisz?", [c[0] for c in h.suggestions()])

    def test_next_without_a_guide(self):
        out = self.h.process_message("dalej", ui_lang="pl")
        self.assertIn("przewodnika", out[0])


class TestChatPanel(unittest.TestCase):

    def _src(self):
        return open(os.path.join(ROOT, "hck_gpt", "panel.py"), encoding="utf-8").read()

    def test_cards_and_quick_replies(self):
        src = self._src()
        for marker in ('"§STEP "', '"§OK "', '"§WARN "'):
            self.assertIn(marker, src)
        self.assertIn("def _refresh_chips(self):", src)
        self.assertIn("self._chips_strip", src)

    def test_links_fold_the_chat_and_pages_keep_it(self):
        self.assertIn("self._nav_and_fold(c)", self._src())
        import ui.windows.main_window_expanded as mwe
        w = mwe.ExpandedMainWindow.__new__(mwe.ExpandedMainWindow)
        for pid in ("services_manager", "startup_manager", "activity_cpu", "dashboard"):
            self.assertTrue(w._page_has_chat(pid), pid)


class TestDiagnosisFrameDoesNotSwallowQuestions(unittest.TestCase):
    """2026-11-17 replay: after a RAM question opened a diagnosis, "Laguje mi
    CS2, co moge wylaczyc w tle?" got "Dopisuje ten szczegol do tej samej
    diagnozy" instead of an answer. The question mark was read from folded
    text, which has no punctuation, so it never counted."""

    def test_full_question_is_answered_short_detail_joins(self):
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier.load_or_train()
        from hck_gpt.chat_handler import ChatHandler
        h = ChatHandler()
        h.process_message("mam duze obciazenie ramu", ui_lang="pl")
        out = h.process_message("Laguje mi CS2, co moge wylaczyc w tle?", ui_lang="pl")
        self.assertNotIn("Dopisuję ten szczegół", out[0])
        detail = h.process_message("w grze", ui_lang="pl")
        self.assertIn("Dopisuję ten szczegół", detail[0])

    def test_overload_question_lists_the_heaviest(self):
        from hck_gpt.intents.parser import intent_parser
        self.assertEqual(intent_parser.parse("czy cos przeciaza komputer?").intent,
                         "top_resource_hog")


class TestQuickRepliesLanguage(unittest.TestCase):

    def test_interface_language_before_the_first_message(self):
        from utils import i18n
        from hck_gpt.chat_handler import ChatHandler
        old = i18n.get_lang()
        try:
            i18n.set_lang("en")
            self.assertEqual(ChatHandler().suggestions()[0][0], "What can you do?")
            i18n.set_lang("pl")
            self.assertEqual(ChatHandler().suggestions()[0][0], "Co potrafisz?")
        finally:
            i18n.set_lang(old)



def tearDownModule():
    # this module loads the ML classifier; later modules (the vocabulary
    # self-consistency check) expect the phrase tables alone (2026-11-17)
    try:
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier._ready = False
        ml_classifier._model = None
    except Exception:
        pass

if __name__ == "__main__":
    unittest.main()
