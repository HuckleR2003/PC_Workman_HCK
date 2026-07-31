"""tests.test_feature_awareness
hck_GPT feature-awareness + intent-fix guards (2026-07-23).

Born from a real user session: "mój PC laguje" answered with a hardware
spec sheet, "zacina mi się komputer" landed in GREETING (ML guess over an
empty keyword match), and "chcę kupić nowy zasilacz" was unknown. These
tests pin the fixed routings AND verify the assistant actively points to
the app's features ([-> Overclock], [-> Optimization], [-> Upgrade
Readiness]) where the context calls for them.
"""
import os
import re
import unittest

os.environ.setdefault("PCW_DEBUG", "0")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# (phrase, expected intent) - every line was a REAL miss before the fix.
FIXED_ROUTES = [
    # whole-PC lag/stutter -> why_slow (used to hit hw_all / greeting)
    ("moj pc laguje",                 "why_slow"),
    ("mój pc laguje",                 "why_slow"),
    ("zacina mi sie komputer",        "why_slow"),
    ("komputer sie przycina",         "why_slow"),
    ("pc muli",                       "why_slow"),
    # single-app freeze -> symptom_freeze (used to hit greeting)
    ("program sie zacina",            "symptom_freeze"),
    ("aplikacja sie zacina",          "symptom_freeze"),
    ("gra sie zacina",                "symptom_freeze"),
    ("program przestal odpowiadac",   "symptom_freeze"),
    # generic part-buying -> upgrade_compat (zasilacz was flat unknown)
    ("chce kupic nowy zasilacz",      "upgrade_compat"),
    ("chce kupic nowa karte graficzna", "upgrade_compat"),
    ("chce kupic nowy ram",           "upgrade_compat"),
    ("chce kupic nowy procesor",      "upgrade_compat"),
    ("chce wymienic gpu",             "upgrade_compat"),
    ("chce wymienic procesor",        "upgrade_compat"),
    ("nowy cpu do kupienia",          "upgrade_compat"),
    ("planuje ulepszyc komputer",     "upgrade_compat"),
    ("i want a new graphics card",    "upgrade_compat"),
    ("upgrade my psu",                "upgrade_compat"),
    # 2026-07-24 wave-2 harness: natural phrasings that used to hit
    # greeting/unknown/gaming - locked in so they never regress again.
    ("wszystko mi sie tnie",          "why_slow"),
    ("kompik zamula ostatnio",        "why_slow"),
    ("my pc is so slow lately",       "why_slow"),
    ("program sie zawiesza",          "symptom_freeze"),
    ("przegladarka sie wiesza",       "symptom_freeze"),
    ("gra sie zawiesza",              "symptom_freeze"),
    ("mysle o nowej karcie graficznej", "upgrade_compat"),
    ("planuje ulepszyc kompa",        "upgrade_compat"),
    ("jaka karte graficzna mam",      "hw_gpu"),
    ("czy procesor sie dlawi",        "throttle_check"),
]


class TestFixedRoutings(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from hck_gpt.intents.parser import IntentParser
        cls.parser = IntentParser()

    def test_real_user_misses_now_route_home(self):
        bad = []
        for phrase, want in FIXED_ROUTES:
            got = self.parser.parse(phrase).intent
            if got != want:
                bad.append((phrase, got, want))
        self.assertEqual(bad, [], f"regressed routings: {bad}")

    def test_specialized_intents_reach_their_own_handlers(self):
        """New handlers must not be shadowed by obsolete broad aliases."""
        from hck_gpt.responses.builder import ResponseBuilder
        for intent in (
            "symptom_freeze", "game_ready", "gaming_session",
            "process_deep_dive", "process_kill", "ram_flush",
            "overclock_check", "ai_context", "thermal_prediction",
        ):
            self.assertNotIn(intent, ResponseBuilder._INTENT_ALIASES)
            self.assertTrue(hasattr(ResponseBuilder, f"_resp_{intent}"))


class TestFeatureAwareness(unittest.TestCase):
    """The assistant must point at app features when context matches."""

    @classmethod
    def setUpClass(cls):
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import IntentParser
        cls.rb = response_builder
        cls.parser = IntentParser()

    def _answer(self, intent, text="x", lang="pl"):
        r = self.parser.parse(text)
        r.intent = intent
        handler = getattr(self.rb, f"_resp_{intent}")
        out = handler(r, lang) or []
        return "\n".join(str(l) for l in out)

    def test_throttle_answer_links_overclock(self):
        txt = self._answer("throttle_check", "czy cpu throttluje")
        self.assertIn("[-> Overclock]", txt,
                      "throttle answer must point at the OVERCLOCK tab")

    def test_why_slow_answer_links_optimization_and_guide(self):
        txt = self._answer("why_slow", "moj pc laguje")
        self.assertIn("[-> Optimization]", txt)
        self.assertTrue("5 krok" in txt or "zoptymalizuj komputer" in txt,
                        "why_slow should offer the 5-step guided fix")

    def test_upgrade_answer_links_upgrade_readiness(self):
        txt = self._answer("upgrade_compat", "chce kupic nowy procesor")
        self.assertIn("[-> Upgrade Readiness]", txt)

    def test_nav_callbacks_registered_for_all_markers(self):
        src = _read("ui", "windows", "main_window_expanded.py")
        for name in ("Optimization", "Startup Manager", "Services Manager",
                     "Upgrade Readiness", "Stability Tests", "Overclock",
                     "Dashboard", "My PC", "Components", "Monitoring",
                     "Fan Control", "Settings", "Statistics"):
            self.assertTrue(
                re.search(r'register_nav_callback\(\s*"%s"' % re.escape(name), src),
                f"nav callback {name!r} not registered")

    def test_five_step_guide_flow_exists(self):
        src = _read("hck_gpt", "responses", "flows.py")
        self.assertTrue("5 krok" in src or "5 steps" in src,
                        "the 5-step optimization guide must exist in flows")


class TestOptimizationTilesResearchPass(unittest.TestCase):
    """2026-07 research pass: leader-inspired tiles, snake oil removed."""

    def setUp(self):
        self.src = _read("ui", "pages", "optimization_services.py")

    def test_new_tiles_present(self):
        for title in ("Thermal Throttle Investigator", "Safe Storage Advisor",
                      "Responsiveness Guard", "App Leftover Scanner",
                      "What Changed?", "Optimization Receipts"):
            self.assertIn(title, self.src, f"missing tile: {title}")

    def test_soon_tiles_render_slim(self):
        """2026-07 redesign: SOON rows are quiet full-width strips."""
        self.assertIn('"slim": not ready', self.src)
        self.assertIn("COMING NEXT", self.src)

    def test_registry_junk_cleaner_removed(self):
        self.assertNotIn('"title": "Registry Junk Cleaner"', self.src,
                         "registry snake oil must stay removed")

    def test_throttle_tile_opens_overclock(self):
        self.assertIn('_NAV["cb"]("overclock")', self.src,
                      "Thermal Throttle Investigator tile must open OVERCLOCK")


class TestOptimizationReceipts(unittest.TestCase):
    """core/opt_receipts.py - the before/after proof engine."""

    def test_receipt_lifecycle(self):
        import time
        import core.opt_receipts as orc
        orig_delay = orc._AFTER_DELAY_S
        orc._AFTER_DELAY_S = 0.05        # fast AFTER capture for the test
        try:
            orc.record("Unit Test")
            items = orc.get_receipts()
            self.assertTrue(items, "receipt must exist immediately")
            newest = items[0]
            self.assertEqual(newest["action"], "Unit Test")
            self.assertIn("ram_pct", newest["before"])
            time.sleep(0.6)
            newest = orc.get_receipts()[0]
            self.assertIsNotNone(newest["after"],
                                 "AFTER snapshot must land once the timer fires")
        finally:
            orc._AFTER_DELAY_S = orig_delay

    def test_record_never_raises(self):
        from core.opt_receipts import record
        record("")          # weird input - must stay silent
        record("X" * 500)   # oversize - clamped, not crashed

    def test_flush_now_carries_a_receipt_hook(self):
        src = _read("core", "auto_optimizer.py")
        self.assertIn("opt_receipts", src,
                      "flush_now must open an Optimization Receipt")


class TestOverclockLabUnits(unittest.TestCase):
    """Pure-function sanity of the Headroom Lab internals."""

    def test_bucket_classification_matches_learning(self):
        from ui.pages.overclock_lab import _bucket
        self.assertEqual(_bucket(5,  0),  "idle")
        self.assertEqual(_bucket(30, 0),  "light")
        self.assertEqual(_bucket(50, 0),  "medium")
        self.assertEqual(_bucket(90, 10), "heavy")
        self.assertEqual(_bucket(20, 75), "gaming")

    def test_seg_color_gradient_endpoints(self):
        from ui.pages.overclock_lab import _seg_color
        for frac in (0.0, 0.3, 0.55, 0.8, 1.0):
            c = _seg_color(frac)
            self.assertTrue(re.fullmatch(r"#[0-9a-f]{6}", c), c)
        self.assertEqual(_seg_color(0.0), "#a3e635")   # lime at low fill
        self.assertEqual(_seg_color(1.0), "#c0182a")   # brand bordeaux at limit

    def test_bucket_stats_never_raises(self):
        from ui.pages.overclock_lab import _bucket_stats
        out = _bucket_stats()
        self.assertIsInstance(out, dict)


if __name__ == "__main__":
    unittest.main()
