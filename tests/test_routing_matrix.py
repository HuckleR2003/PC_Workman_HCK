"""tests.test_routing_matrix
Real-phrasing routing guards. Born 2026-07-16 after a user click-test found
"jak zoptymalizowac moj komputer" landing on hw_all (its "moj komputer"
substring outscored the guide, which lacked how-to inflections). Every entry
here is a REAL user phrasing; keep this matrix growing with every misroute.
"""
import unittest


class TestRoutingMatrix(unittest.TestCase):
    MATRIX = [
        ("Jak zoptymalizowac moj komputer",  "optimize_guide"),
        ("Jak zoptymalizowac moj pc?",       "optimize_guide"),
        ("jak zoptymalizować mój komputer?", "optimize_guide"),
        ("JAK ZOPTYMALIZOWAĆ MÓJ KOMPUTER",  "optimize_guide"),
        ("chcę zoptymalizować komputer",     "optimize_guide"),
        ("poprowadź mnie",                   "optimize_guide"),
        ("zoptymalizuj mój komputer",        "optimize_guide"),
        ("optimize my pc",                   "optimize_guide"),
        ("how to optimize my pc",            "optimize_guide"),
        ("how do i optimize my computer",    "optimize_guide"),
        ("jak przyspieszyć komputer?",       "speed_up_pc"),
        ("jak przyspieszyc komputer",        "speed_up_pc"),
        ("co zrobić żeby przyspieszyć",      "speed_up_pc"),
        ("mój komputer",                     "hw_all"),
        ("jaki mam sprzęt",                  "hw_all"),
        ("pokaż podzespoły",                 "hw_all"),
        ("podrasuj mój komputer",            "tuneup_guide"),
        ("ile to było",                      "recall_numbers"),
        ("dlaczego mój laptop jest ciepły",  "temperature"),
        # Upgrade Readiness (2026-07-17): part model + fit/swap wording wins
        ("czy i5 11400f bedzie pasowac do mojej plyty",   "upgrade_compat"),
        ("czy rtx 4070 wejdzie na moja plyte",            "upgrade_compat"),
        ("czy musze wymienic plyte glowna pod i7 14700k", "upgrade_compat"),
        ("chce kupic ryzen 7 9800x3d czy zadziala",       "upgrade_compat"),
        ("wymiana karty na rtx 4070",                     "upgrade_compat"),
        ("will an i5 13600k fit my board",                "upgrade_compat"),
        ("is a ryzen 5 7600 compatible with my pc",       "upgrade_compat"),
        ("jaki mam socket",                               "upgrade_compat"),
        ("jaki ram pasuje do mojej plyty",                "upgrade_compat"),
        ("czy ddr5 6000 zadziala u mnie",                 "ram_compat"),
        ("will ddr5 work on my pc",                       "ram_compat"),
        # ...and the part regex must NOT steal neighbouring intents
        ("jaka temperatura ma rtx 4070",     "temperature"),
        ("czy pojdzie cyberpunk na rtx 4070", "game_can_run"),
        ("czy moge dolozyc ram",             "upgrade_feasibility"),
        ("ile mam ram",                      "hw_ram"),
        ("jaka mam plyte glowna",            "hw_motherboard"),
    ]

    def test_real_phrasings_route_correctly(self):
        from hck_gpt.intents.parser import IntentParser
        p = IntentParser()
        bad = [(m, p.parse(m).intent, want) for m, want in self.MATRIX
               if p.parse(m).intent != want]
        self.assertEqual(bad, [],
                         "misroutes (msg, got, want): " + repr(bad))

    def test_speed_up_offers_the_guide(self):
        import hck_gpt.responses.r_performance as rp
        import inspect
        src = inspect.getsource(rp.PerformanceResponses._resp_speed_up_pc)
        self.assertIn("zoptymalizuj komputer", src,
                      "speed_up_pc must offer the guided flow")


if __name__ == "__main__":
    unittest.main()
