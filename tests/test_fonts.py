"""tests.test_fonts - one typeface that really loads (2026-11-16).

The app asked Tk for "Inter", but the bundled variable font registers as
"Inter Variable Text". Tk silently drew Arial; other modules asked for Segoe
UI by name. Three typefaces on every page, none of them the intended one.
And the smallest texts (4-6 pt) were close to unreadable.
"""
import ast
import os
import re
import tkinter as tk
import unittest

from utils import fonts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _py_files(*bases):
    for base in bases:
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in fn:
                if f.endswith(".py"):
                    yield os.path.join(dp, f)


class TestFamiliesResolve(unittest.TestCase):

    def test_tk_draws_the_family_we_ask_for(self):
        import tkinter.font as tkfont
        fonts.load()
        try:
            root = tk.Tk()
        except tk.TclError:
            raise unittest.SkipTest("no display")
        try:
            for fam in (fonts.UI, fonts.HDR, fonts.HEAVY, fonts.LIGHT, fonts.MONO):
                got = tkfont.Font(root=root, family=fam, size=9).actual()["family"]
                self.assertEqual(got, fam, f"asked for {fam!r}, Tk drew {got!r}")
        finally:
            root.destroy()

    def test_inter_is_the_ui_font_when_shipped(self):
        if os.path.exists(os.path.join(ROOT, "data", "fonts", "InterVariable.ttf")):
            self.assertEqual(fonts.UI, "Inter Variable Text")


class TestOneTypeface(unittest.TestCase):

    def test_no_family_names_typed_into_the_code(self):
        bad = []
        for p in _py_files("ui", "hck_gpt", "core"):
            for node in ast.walk(ast.parse(open(p, encoding="utf-8").read())):
                if isinstance(node, ast.Constant) and node.value in (
                        "Segoe UI", "Segoe UI Semibold", "Segoe UI Black",
                        "Segoe UI Light", "Inter", "Arial"):
                    bad.append(f"{os.path.relpath(p, ROOT)}:{node.lineno} {node.value}")
        self.assertEqual(bad, [], "use utils.fonts.UI / HDR / HEAVY / LIGHT")

    def test_nothing_smaller_than_7_pt(self):
        rx = re.compile(r'\(\s*(?:_MONO|_BODY|_HDR|_F|_M|_UIF|_MONOF|_BLACK|'
                        r'_FONT_UI|_FONT_HDR|_FONT_HEAVY|_FONT_LIGHT|"Consolas")'
                        r'\s*,\s*([1-6])\s*[,)]')
        small = []
        for p in _py_files("ui", "hck_gpt"):
            for i, line in enumerate(open(p, encoding="utf-8"), 1):
                if rx.search(line):
                    small.append(f"{os.path.relpath(p, ROOT)}:{i}")
        self.assertEqual(small, [], "text below 7 pt is not readable")

    def test_symbols_in_semibold_have_a_weight(self):
        """HDR / HEAVY at normal weight draw a box for symbols Inter lacks
        (⤢, ▾, emoji); with "bold" Windows takes them from another font."""
        try:
            from fontTools.ttLib import TTFont
        except ImportError:
            raise unittest.SkipTest("fontTools not installed")
        path = os.path.join(ROOT, "data", "fonts", "InterVariable.ttf")
        if not os.path.exists(path):
            raise unittest.SkipTest("Inter not shipped")
        cmap = TTFont(path).getBestCmap()
        rx = re.compile(r'\((?:_HDR|_FONT_HDR|_FONT_HEAVY|_BLACK)\s*,\s*\d+\s*\)')
        bad = []
        for p in _py_files("ui", "hck_gpt"):
            for i, line in enumerate(open(p, encoding="utf-8"), 1):
                if not rx.search(line):
                    continue
                code = line.split("#", 1)[0]
                if any(ord(c) > 127 and not c.isalpha() and ord(c) not in cmap
                       for c in code):
                    bad.append(f"{os.path.relpath(p, ROOT)}:{i}")
        self.assertEqual(bad, [])


class TestWindowAndBoost(unittest.TestCase):

    def test_default_window_grew_and_fonts_follow(self):
        from utils import ui_scale
        self.assertGreaterEqual(ui_scale._BASE_W, 1276)     # 1160 + 10 %
        self.assertGreaterEqual(ui_scale._BASE_H, 632)      # 575 + 10 %
        self.assertGreater(ui_scale.FONT_BOOST, 1.0)


if __name__ == "__main__":
    unittest.main()
