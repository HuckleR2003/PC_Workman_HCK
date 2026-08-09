# tests/test_deep_link.py
"""
Pins the pcworkman:// contract.

A deep link arrives from a web page, so the parser is a trust boundary. It may
name a page or hand text to the chat. It may never reach an unknown page, build
an arbitrary URL, or cause an action to run. These tests fail the build if that
stops being true.
"""
import os
import re
import unittest

from utils.deep_link import parse, from_argv, SCHEME, _PAGES


class DeepLinkParsing(unittest.TestCase):

    def test_open_known_page(self):
        self.assertEqual(parse("pcworkman://open/startup_manager"),
                         {"action": "open", "page": "startup_manager"})

    def test_unknown_page_is_refused(self):
        for u in ("pcworkman://open/does_not_exist",
                  "pcworkman://open/",
                  "pcworkman://open/../settings",
                  "pcworkman://open/%2e%2e%2fsettings"):
            self.assertIsNone(parse(u), u)

    def test_guide_slug(self):
        self.assertEqual(parse("pcworkman://guide/why-is-my-disk-at-100-percent"),
                         {"action": "guide", "slug": "why-is-my-disk-at-100-percent"})

    def test_guide_rejects_anything_that_is_not_a_slug(self):
        for u in ("pcworkman://guide/../../etc/passwd",
                  "pcworkman://guide/a b",
                  "pcworkman://guide/x?y=1#z",
                  "pcworkman://guide/"):
            got = parse(u)
            if got is not None:
                self.assertTrue(all(c.isalnum() or c == "-" for c in got["slug"]), u)

    def test_ask_returns_text_only(self):
        got = parse("pcworkman://ask?q=why%20is%20my%20disk%20at%20100%25")
        self.assertEqual(got, {"action": "ask", "text": "why is my disk at 100%"})

    def test_ask_text_is_capped(self):
        got = parse("pcworkman://ask?q=" + "a" * 900)
        self.assertLessEqual(len(got["text"]), 300)

    def test_foreign_schemes_are_ignored(self):
        for u in ("https://evil.example/x", "file:///C:/Windows/system32",
                  "javascript:alert(1)", "", None, 123):
            self.assertIsNone(parse(u))

    def test_no_action_verbs_exist(self):
        """The scheme must not be able to trigger an optimisation."""
        for verb in ("flush", "turbo", "kill", "suspend", "optimize", "run"):
            self.assertIsNone(parse(f"pcworkman://{verb}/anything"))

    def test_from_argv_picks_only_our_links(self):
        argv = ["--debug", "https://x.test", "pcworkman://open/settings", "junk"]
        self.assertEqual(from_argv(argv), [{"action": "open", "page": "settings"}])

    def test_pages_match_the_real_router(self):
        """A renamed page must not leave a dead deep link behind."""
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "ui", "windows", "main_window_expanded.py")
        if not os.path.exists(src):
            self.skipTest("router not present")
        with open(src, encoding="utf-8") as fh:
            real = set(re.findall(r'page_id == "([a-z_]+)"', fh.read()))
        unknown = _PAGES - real
        self.assertFalse(unknown, f"deep-link pages not in the router: {unknown}")

    def test_scheme_name(self):
        self.assertEqual(SCHEME, "pcworkman")


if __name__ == "__main__":
    unittest.main()
