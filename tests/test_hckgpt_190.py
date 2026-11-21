"""hck_GPT the release after 1.8.8: conclusions, follow-ups and the observation note.

From the third long test (2026-11-17) and the 63-question library:
- every library question (with variants) reaches an answer about it;
- the insight layer reads real counters and the event log without failing;
- a conversation keeps "it": the process, the game, the last action;
- the observation note records, compares and writes its note where the
  isolated test folder says, never to the user's Desktop;
- the knowledge base of the tests is not the user's.
"""
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


LIBRARY = {
    "Hej, co tam u mojego komputera?": "pc_checkup",
    "Czy mój komputer jest zdrowy?": "pc_checkup",
    "Mam wrażenie, że ostatnio działa wolniej.": "slower_lately",
    "wolno działa komputer": "slowdown_cause",
    "Co najbardziej spowalnia mojego PC?": "slowdown_cause",
    "Czy coś niepotrzebnie działa w tle?": "background_load",
    "Co mogę bezpiecznie zamknąć?": "closable_apps",
    "Czy mam za dużo programów uruchomionych?": "background_load",
    "Czy muszę coś naprawić?": "pc_checkup",
    "Czy powinienem się czymś martwić?": "pc_checkup",
    "Czy mój procesor jest jeszcze dobry?": "part_verdict",
    "Czy moja karta graficzna daje radę?": "part_verdict",
    "Czy mam wystarczająco dużo RAM-u?": "ram_enough",
    "Który podzespół jest najsłabszy?": "bottleneck",
    "Co powinienem wymienić jako pierwsze?": "bottleneck",
    "Czy moja płyta obsłuży mocniejszy procesor?": "board_cpu_upgrade",
    "Czy mam szybki dysk?": "disk_speed_check",
    "Czy mam jakieś wąskie gardło?": "bottleneck",
    "Czy procesor osiąga maksymalne taktowanie?": "cpu_boost",
    "Czy moja karta graficzna jest wykorzystywana w pełni?": "gpu_utilization",
    "Czy coś ogranicza wydajność mojego komputera?": "bottleneck",
    "Czy komputer zwalnia pod obciążeniem?": "cpu_boost",
    "Czy temperatury są bezpieczne podczas grania?": "gaming_temps",
    "Czy mój SSD jest w dobrej kondycji?": "ssd_health",
    "Czy mój RAM jest dziś bardziej obciążony niż wczoraj?": "history_compare_days",
    "Czy komputer działa gorzej niż zwykle?": "usage_vs_normal",
    "Czy moje średnie zużycie CPU jest normalne?": "usage_vs_normal",
    "Czy wydajność pogarsza się z czasem?": "usage_vs_normal",
    "Czy mój procesor osiąga temperaturę throttlingu?": "cpu_boost",
    "Czy CPU pracuje na limicie mocy?": "cpu_boost",
    "Czy GPU ma wystarczająco dużo VRAM-u?": "vram_check",
    "Czy mam aktywny profil wysokiej wydajności?": "power_plan",
    "Czy mój dysk może ograniczać ładowanie gier?": "disk_speed_check",
    "Czy mam błędy związane ze sprzętem?": "stability_check",
    "Czy mój komputer ma problemy ze stabilnością?": "stability_check",
    "Czy któryś proces zużywa więcej zasobów niż zwykle?": "process_anomaly",
    "Czy masz dostęp do moich plików?": "files_access",
    "Czy zapisujesz moje dane?": "data_stored",
    "Czy wysyłasz coś do internetu?": "privacy_data",
    "Czy mogę zobaczyć, co o mnie zapamiętałeś?": "what_remembered",
    "Czy potrafisz rozpoznać wirusa?": "virus_capability",
    "Czy Windows Defender wystarczy?": "defender_enough",
    "Czy każdy proces svchost.exe jest bezpieczny?": "svchost_safety",
    "Czy mogę ufać programom, które mają podpis cyfrowy?": "signed_trust",
    "Czy potrafisz wykryć program podszywający się pod inny?": "impostor_check",
    "Dlaczego mój komputer mnie nienawidzi?": "fun_roast",
    "Czy mój PC jest już stary?": "pc_age",
    "Czy powinienem kupić nowy komputer?": "new_pc_advice",
    "Czy mój komputer jest zmęczony?": "pc_tired",
    "Co robisz, kiedy nic nie robię?": "idle_activity",
    "Czy pilnujesz mojego komputera?": "watching",
    "Czy jesteś prawdziwym AI?": "about_assistant",
    "Czy lubisz swoją pracę?": "likes_job",
    "Czy potrafisz przewidzieć kiedy komputer zacznie zwalniać?": "predict_slowdown",
    "zacznij nagrywanie": "observe_start",
    "zakończ nagrywanie": "observe_stop",
    "Jak sprawdzić, że jest poprawa?": "observe_howto",
    "A co jeśli dalej będzie zacinać?": "still_lagging",
    "Czy to pomoże?": "will_it_help",
    "Jak to zrobić?": "how_to",
    "Chce pograć w cs2 ale mam lagi": "game_lag",
    "Co powinienem zamknąć przed grą?": "closable_apps",
}


class TestLibraryRoutes(unittest.TestCase):

    def test_every_question_reaches_its_answer(self):
        """The answer chosen by the builder (parser + insight redirect)."""
        from hck_gpt.intents.parser import intent_parser
        from hck_gpt.responses.builder import ResponseBuilder
        bad = []
        for q, want in LIBRARY.items():
            got = ResponseBuilder._redirect(intent_parser.parse(q).intent, q)
            if got != want:
                bad.append((q, got, want))
        self.assertEqual(bad, [])


class TestInsightLayer(unittest.TestCase):

    def test_reads_without_failing(self):
        from core import pc_insight as p
        clk = p.cpu_clock(0.2)
        if clk:
            self.assertGreater(clk["actual"], 300)
        self.assertIsInstance(p.findings(deep=False), list)
        self.assertIn(p.weakest_part()["part"], ("ram", "gpu", "cpu", "disk", ""))
        self.assertIsInstance(p.hardware_errors(), dict)

    def test_years_and_disk_classes(self):
        from core import pc_insight as p
        self.assertEqual(p._cpu_year("12th Gen Intel(R) Core(TM) i5-12400F"), 2022)
        self.assertEqual(p._cpu_year("AMD Ryzen 5 5600X 6-Core Processor"), 2020)
        self.assertEqual(p._gpu_year("NVIDIA GeForce RTX 3050"), 2022)
        self.assertEqual(p.disk_speed_class({"media": "SSD", "bus": "NVMe"}), "nvme")
        self.assertEqual(p.disk_speed_class({"media": "SSD", "bus": "SATA"}), "sata_ssd")
        self.assertEqual(p.disk_speed_class({"media": "HDD", "bus": "SATA"}), "hdd")


class TestConversation(unittest.TestCase):

    def setUp(self):
        from hck_gpt.memory.session_memory import session_memory
        session_memory.clear_conversation_frame()
        session_memory._turn_context.clear()
        session_memory._last_references.clear()

    def test_it_means_the_program_just_named(self):
        from hck_gpt.chat_handler import ChatHandler
        from hck_gpt.memory.session_memory import session_memory
        h = ChatHandler()
        h.process_message("co najbardziej obciaza komputer", ui_lang="pl")
        session_memory.note_reference("process", "python.exe", "test")
        out = " ".join(h.process_message("A czy mogę to wyłączyć?", ui_lang="pl"))
        self.assertIn("python.exe", out)
        how = " ".join(h.process_message("Jak to zrobić?", ui_lang="pl"))
        self.assertIn("Menedżer zadań", how)
        helps = " ".join(h.process_message("Czy to pomoże?", ui_lang="pl"))
        self.assertIn("RAM", helps)

    def test_game_is_remembered(self):
        from hck_gpt.chat_handler import ChatHandler
        h = ChatHandler()
        first = " ".join(h.process_message("Chce pograć w cs2 ale mam lagi", ui_lang="pl"))
        self.assertIn("CS2", first)
        follow = " ".join(h.process_message("Czy mój komputer sobie z tym radzi?", ui_lang="pl"))
        self.assertIn("CS2", follow)


class TestObservationNote(unittest.TestCase):

    def test_record_compare_and_note_stay_in_the_test_folder(self):
        from core import observation as o
        self.assertTrue(os.environ.get("PCW_APP_DIR"))
        o.start("a"); time.sleep(3.2)
        a = o.stop()
        o.start("b"); time.sleep(3.2)
        b = o.stop()
        self.assertFalse(a.get("too_short"))
        self.assertIn("verdict", b["compare"])
        self.assertTrue(b["note_path"].startswith(os.environ["PCW_APP_DIR"]),
                        "notes of a test run must not land on the Desktop")
        text = open(b["note_path"], encoding="utf-8").read()
        self.assertIn("Porównanie z poprzednim nagraniem", text)

    def test_compare_verdict(self):
        from core.observation import compare
        a = {"cpu": {"avg": 60}, "ram": {"avg": 85}}
        b = {"cpu": {"avg": 40}, "ram": {"avg": 70}}
        self.assertEqual(compare(a, b)["verdict"], "better")
        self.assertEqual(compare(b, a)["verdict"], "worse")


class TestKnowledgeBaseIsolated(unittest.TestCase):

    def test_tests_never_touch_the_users_knowledge_base(self):
        import importlib
        uk = importlib.import_module("hck_gpt.memory.user_knowledge")
        real = os.path.join(os.path.expanduser("~"), "AppData", "Local",
                            "PC_Workman_HCK", "user_knowledge.db")
        self.assertNotEqual(os.path.normcase(uk.DB_PATH), os.path.normcase(real))



# 34 questions of the fourth long test that ended in "I did not understand"
FOURTH_TEST = {
    "ile sie bedziesz uczyc jeszcze?": "learning_eta",
    "gdzie zainstalowac ten libreoffice?": "lhm_help",
    "librehardwaremonitor": "lhm_help",
    "gdzie pobrac by napiecie dzialalo?": "lhm_help",
    "czy mam wirusy?": "virus_check",
    "jak sprawdzic czy mam wirusa?": "virus_check",
    "czy cos dolega mojemu pc?": "pc_checkup",
    "a gta 6?": "game_can_run",
    "czy tworcy cos jeszcze tworza?": "project_status",
    "czy prace nad pc workmanem nadal trwaja?": "project_status",
    "czy program sie rozwija?": "project_status",
    "cos nowego?": "whats_new",
    "znalazles cos nowego?": "whats_new",
    "jest cos na co zwrocic uwage?": "whats_new",
    "czy cos wymienic?": "bottleneck",
    "nie rozpoznajesz pytan": "meta_feedback",
    "jestes?": "presence",
    "halo": "presence",
    "cos nie dziala?": "error_help",
    "mam blad": "error_help",
    "gdzie znajde nową wersje?": "version_check",
    "jak stan twojej pamieci?": "what_remembered",
    "czy jestes claude": "about_assistant",
    "fajny ziomek jestes": "compliment",
    "jak przeniesc dane pc workmana na nowy system?": "data_export",
    "instaluje nowego windowsa, jak zrobic export": "data_export",
    "zrób export": "data_export_run",
    "Jak usunac dane?": "data_reset",
    "zacznij dane od nowa": "data_reset",
    "czy da sie usunac nauczanie?": "data_reset",
}


class TestFourthLongTest(unittest.TestCase):

    def test_routes(self):
        from hck_gpt.intents.parser import intent_parser
        from hck_gpt.responses.builder import ResponseBuilder
        bad = [(q, ResponseBuilder._redirect(intent_parser.parse(q).intent, q), w)
               for q, w in FOURTH_TEST.items()
               if ResponseBuilder._redirect(intent_parser.parse(q).intent, q) != w]
        self.assertEqual(bad, [])

    def test_export_zip_has_the_data_and_stays_in_the_test_folder(self):
        import zipfile
        from core.data_export import export_zip
        res = export_zip()
        self.assertNotIn("error", res)
        self.assertTrue(res["path"].startswith(os.environ["PCW_APP_DIR"]))
        names = zipfile.ZipFile(res["path"]).namelist()
        self.assertIn("README_IMPORT.txt", names)

    def test_version_in_settings_text_follows_the_source(self):
        import json
        from utils.app_version import APP_VERSION
        for f in ("en.json", "pl.json"):
            txt = open(os.path.join(ROOT, "locales", f), encoding="utf-8").read()
            self.assertNotIn("1.7.4", txt)
            self.assertIn("{version}", txt)
        # the number itself is pinned once, in test_version.py (2026-11-21)
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")


# fifth long test (2026-11-17): questions from the 1.9.0 run
FIFTH_TEST = {
    "czy komputer ma wirusa": "virus_check",
    "jak sprawdzic czy mam wirusa?": "virus_check",
    "mam wolny internet": "network_slow",
    "net mi tnie": "network_slow",
    "co moge robic w programie?": "app_capabilities",
    "jakie funkcje ma pc workman": "app_capabilities",
    "czym jest deepmonitor": "feature_info",
    "deepmonitor?": "feature_info",
    "czym jest nagranie": "feature_info",
    "fan dashboard": "feature_info",
    "monitoring learning": "feature_info",
    "co to recent events w monitoring learning": "feature_info",
    "co to jest turbo": "feature_info",
    "mam dużo recent events": "recent_events",
    "nagrywaj": "observe_start",
    "co to librehardware?": "lhm_help",
    "czy librehardwaremonitor jest konieczny?": "lhm_help",
    "a da się podkręcić kartę graficzna?": "gpu_overclock",
    "czy mam jakies bledy?": "error_help",
    "co odinstalowac?": "stale_apps",
    "co usunac?": "free_space",
    "kto ty jesteś": "about_assistant",
    "czy dobrze dzialasz?": "presence",
    "opowiedz zart": "joke",
    "wyłącz teams": "startup_check",
    # must keep their answers
    "co to teams": "process_identity",
    "czym jest unity": "process_identity",
    "czy jest nakladka?": "overlay_where",
    "czy mam wirusa": "virus_check",
}


class TestFifthLongTest(unittest.TestCase):

    def test_routes(self):
        from hck_gpt.intents.parser import intent_parser
        from hck_gpt.responses.builder import ResponseBuilder
        bad = []
        for q, want in FIFTH_TEST.items():
            got = ResponseBuilder._redirect(intent_parser.parse(q).intent, q)
            if got != want:
                bad.append((q, got, want))
        self.assertEqual(bad, [])

    def _build(self, intent, text, lang="pl"):
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        return response_builder.build(ParseResult(intent, 1.0, raw_text=text), lang)

    def test_feature_answers_carry_a_link(self):
        out = "\n".join(self._build("feature_info", "czym jest deepmonitor"))
        self.assertIn("DeepMonitor", out)
        self.assertIn("[-> DeepMonitor]", out)
        tour = "\n".join(self._build("app_capabilities", "co moge robic w programie"))
        self.assertIn("§STEP", tour)
        src = open(os.path.join(ROOT, "ui", "windows", "main_window_expanded.py"), encoding="utf-8").read()
        from hck_gpt.responses.r_features import FEATURES
        for f in FEATURES:
            if f.get("nav") and f["nav"] not in ("Activity Memory",):
                self.assertRegex(src, r'register_nav_callback\(\s*"' + f["nav"] + '"', f["nav"])

    def test_lhm_answer_says_optional_and_offers_the_official_page(self):
        from hck_gpt.chat_handler import ChatHandler
        h = ChatHandler()
        out = "\n".join(h.process_message("czy librehardwaremonitor jest konieczny?", ui_lang="pl"))
        self.assertIn("Czy jest konieczny? Nie.", out)
        chips = h.suggestions()
        self.assertEqual(chips[0], ("ZOBACZ SAM", "nav", "LibreHardwareMonitor"))
        from hck_gpt.panel import HCKGPTPanel
        self.assertTrue(HCKGPTPanel.LHM_URL.startswith("https://github.com/LibreHardwareMonitor/"))

    def test_game_check_uses_the_roomiest_drive_and_card_power(self):
        from hck_gpt.responses import r_gaming
        self.assertGreater(r_gaming._gpu_score("NVIDIA GeForce RTX 3050"), 90)
        name, free = r_gaming._roomiest_drive()
        import psutil
        self.assertGreaterEqual(free + 0.01, psutil.disk_usage("C:\\").free / 1024 ** 3)
        out = self._build("game_can_run", "czy pójdzie mi gta 5")
        self.assertTrue(any(l.startswith("§STEP ") for l in out))
        self.assertFalse(any("niskich/średnich" in l for l in out))

    def test_update_dialog_shows_the_real_version(self):
        src = open(os.path.join(ROOT, "ui", "windows", "main_window_expanded.py"), encoding="utf-8").read()
        body = src[src.index("def _show_update_dialog"):src.index("# ========== STARTUP")]
        self.assertNotIn("1.7.1", body)
        self.assertIn("APP_VERSION", body)
        self.assertIn("ms-windows-store://pdp/?ProductId=", body)

    def test_one_game_two_processes_is_one_session(self):
        from hck_gpt.memory.proactive_monitor import ProactiveMonitor
        fam = ProactiveMonitor._game_family
        self.assertEqual(fam("beamng.drive.exe"), fam("BeamNG.drive.x64.exe"))
        self.assertEqual(fam("AutomationGame-Win64-Shipping.exe"), "automationgame")
        self.assertNotEqual(fam("cs2.exe"), fam("steam.exe"))


class TestPages(unittest.TestCase):

    def test_settings_covers_the_whole_content_area(self):
        import ui.windows.main_window_expanded as mwe
        self.assertTrue(mwe.ExpandedMainWindow._overlay_full_cover("settings"))
        src = open(os.path.join(ROOT, "ui", "windows", "main_window_expanded.py"), encoding="utf-8").read()
        self.assertNotIn("width=980, height=515", src)

    def test_labs_and_guide_build(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        try:
            from ui.pages.labs_guide_pages import build_hcklabs_page, build_guide_page

            class _W:
                root = None
                def _close_overlay(self): pass
                def _start_live_guide(self): pass
                def _show_update_dialog(self, p): pass
                def _show_services_dialog(self, p): pass
            w = _W(); w.root = root
            for build in (build_hcklabs_page, build_guide_page):
                f = tk.Frame(root)
                f.pack(fill="both", expand=True)
                build(w, f)
                root.update()
                self.assertTrue(f.winfo_children())
                f.destroy()
        finally:
            root.destroy()

def tearDownModule():
    try:
        from hck_gpt.intents.ml_classifier import ml_classifier
        ml_classifier._ready = False
        ml_classifier._model = None
    except Exception:
        pass


if __name__ == "__main__":
    unittest.main()
