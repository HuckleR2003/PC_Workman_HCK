# tests/test_guide_links.py
"""
Pins the intent -> guide contract.

The whole point of the offer is that it lands on a page that exists, in the
language the user is speaking. A wrong slug or a flipped language would send
someone to a 404 from inside a paid-for Store app, so both are tested against
the real docs/guides folder rather than against the map's own opinion.
"""
import os
import re
import unittest

from hck_gpt import guide_links as gl

_DOCS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "guides",
)


class GuideLinkMapTests(unittest.TestCase):

    def setUp(self):
        gl.reset_offers()

    def test_every_mapped_intent_points_at_a_known_guide(self):
        for intent, slug in gl.INTENT_GUIDE.items():
            self.assertIn(slug, gl.GUIDES,
                          f"intent {intent} maps to unknown guide {slug}")

    def test_every_guide_has_both_languages(self):
        for slug, names in gl.GUIDES.items():
            self.assertTrue(names.get("pl"), f"{slug} missing PL label")
            self.assertTrue(names.get("en"), f"{slug} missing EN label")

    def test_intents_exist_in_the_vocabulary(self):
        """A renamed intent must not leave a dead entry behind."""
        voc = os.path.join(
            os.path.dirname(_DOCS), "..", "hck_gpt", "intents", "vocabulary.py")
        voc = os.path.normpath(voc)
        if not os.path.exists(voc):
            self.skipTest("vocabulary.py not found")
        with open(voc, encoding="utf-8") as fh:
            src = fh.read()
        known = set(re.findall(r"^\s{4}[\"']([a-z0-9_]+)[\"']\s*:", src, re.M))
        for intent in gl.INTENT_GUIDE:
            self.assertIn(intent, known,
                          f"{intent} is mapped to a guide but is not an intent")

    def test_target_files_exist_for_both_languages(self):
        if not os.path.isdir(_DOCS):
            self.skipTest("docs/guides not present in this checkout")
        for slug in gl.GUIDES:
            folder = os.path.join(_DOCS, slug)
            self.assertTrue(os.path.isdir(folder), f"missing guide folder {slug}")
            for lang in ("pl", "en"):
                rel = gl.url_for(slug, lang)[len(gl.SITE):]      # slug/...
                tail = rel[len(slug) + 1:] or "index.html"
                self.assertTrue(
                    os.path.exists(os.path.join(folder, tail)),
                    f"{slug} has no {lang} page at {tail}")

    def test_polish_native_guides_are_not_flipped(self):
        """index.html is Polish for the two PL-first guides, English elsewhere."""
        self.assertTrue(
            gl.url_for("jak-przyspieszyc-komputer", "pl").endswith("komputer/"))
        self.assertTrue(
            gl.url_for("jak-przyspieszyc-komputer", "en").endswith("index_en.html"))
        self.assertTrue(
            gl.url_for("why-is-my-ram-usage-so-high", "en").endswith("high/"))
        self.assertTrue(
            gl.url_for("why-is-my-ram-usage-so-high", "pl").endswith("index_pl.html"))

    def test_marker_round_trips_back_to_its_slug(self):
        for slug in gl.GUIDES:
            for lang in ("pl", "en"):
                marker = gl.marker_for(slug, lang)
                label = marker[len("[-> "):-1]
                got = gl.slug_for_marker(label)
                self.assertIsNotNone(got, f"marker for {slug}/{lang} not parsed")
                self.assertEqual(got[0], slug)

    def test_unmapped_intent_offers_nothing(self):
        for intent in ("greeting", "thanks", "small_talk", "cpu", "ram"):
            self.assertIsNone(gl.offer_lines(intent, "pl"),
                              f"{intent} should not carry a guide offer")

    def test_offer_is_made_once_per_session(self):
        first = gl.take_offer("ram_why_high", "pl")
        self.assertIsNotNone(first)
        self.assertIsNone(gl.take_offer("ram_why_high", "pl"))
        # a different intent sharing the same guide stays quiet too
        self.assertIsNone(gl.take_offer("daily_ram_usage", "pl"))
        # an unrelated guide is still available
        self.assertIsNotNone(gl.take_offer("disk_health", "pl"))

    def test_offer_lines_are_a_lead_plus_a_marker(self):
        lines = gl.offer_lines("why_slow", "en")
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].startswith("[-> Guide: "))
        self.assertTrue(lines[1].endswith("]"))

    def test_no_em_dashes_in_user_facing_labels(self):
        for names in gl.GUIDES.values():
            for text in names.values():
                self.assertNotIn("—", text)


if __name__ == "__main__":
    unittest.main()
