"""tests.test_one_language
One interface language at a time (2026-11-14).

With the interface set to English, Startup Manager, Services Manager and
parts of Drivers still drew Polish, because the text was typed into the
code instead of going through utils.i18n.t(). 75 strings in six files.
These tests keep it from coming back:

  1. no Polish text typed into the UI packages outside a t() call,
  2. every key passed to t() exists in BOTH locale files,
  3. the two locale files have exactly the same keys,
  4. a name used in a file is defined there (the fix itself once shipped a
     page that called _t() without importing it).
"""
import ast
import builtins
import json
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DIACRITICS = re.compile(r"[ąćęłńóśżźĄĆĘŁŃÓŚŻŹ]")

# Polish text that is allowed to stay in ui/ code, with the reason.
ALLOWED_LITERALS = {
    # Value stored in prefs files (startup_prefs.json, service_prefs.json).
    # Shown to the user through common.user_tag, never directly.
    "UŻYTKOWNIK",
    # Keys of ui/pages/services_manager._REC_SLUG: they match the labels in
    # core.turbo_manager.RECOMMENDED, under which quick-setup answers are saved.
    "Drukowanie", "Telemetria", "Pulpit zdalny",
}


def _ui_files():
    for dp, dn, fn in os.walk(os.path.join(_ROOT, "ui")):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for n in fn:
            if n.endswith(".py"):
                p = os.path.join(dp, n)
                yield os.path.relpath(p, _ROOT).replace("\\", "/"), p


def _flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, prefix + k + "."))
        else:
            out[prefix + k] = v
    return out


def _locale(lang):
    with open(os.path.join(_ROOT, "locales", f"{lang}.json"),
              encoding="utf-8") as f:
        return _flat(json.load(f))


class _Finder(ast.NodeVisitor):
    """String literals with Polish letters that are shown as they are:
    not a t() default, not a 'pl' branch of an inline bilingual pair."""

    def __init__(self):
        self.skip, self.hits = set(), []

    def _skip(self, node):
        for sub in ast.walk(node):
            self.skip.add(id(sub))

    def visit_Call(self, node):
        fn = node.func
        name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
        # _txt(pl, en) and L(en, pl) are the two inline bilingual helpers
        # (fan_dashboard, settings_page): both languages sit side by side.
        if name in ("t", "_t", "_t_i18n", "print", "_dbg", "log", "_log",
                    "_txt", "L"):
            for a in list(node.args) + [k.value for k in node.keywords]:
                self._skip(a)
        self.generic_visit(node)

    def visit_IfExp(self, node):
        # "polski" if _pl else "english" - an inline bilingual pair
        if "pl" in ast.unparse(node.test).lower():
            self._skip(node.body)
            self._skip(node.orelse)
        self.generic_visit(node)

    def visit_If(self, node):
        if "pl" in ast.unparse(node.test).lower():
            for part in node.body + node.orelse:
                self._skip(part)
        self.generic_visit(node)

    def visit_Dict(self, node):
        for k, v in zip(node.keys, node.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str) and (
                    k.value in ("pl", "PL") or k.value.endswith("_pl")):
                self._skip(v)
        self.generic_visit(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(
                node.value.value, str):
            self.skip.add(id(node.value))                # docstring
        self.generic_visit(node)

    def visit_Constant(self, node):
        if (isinstance(node.value, str) and id(node) not in self.skip
                and _DIACRITICS.search(node.value)
                and node.value.strip() not in ALLOWED_LITERALS):
            self.hits.append((node.lineno, node.value))


class TestNoHardcodedPolish(unittest.TestCase):

    def test_ui_text_goes_through_t(self):
        offenders = []
        for rel, path in _ui_files():
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
            first = _Finder()
            first.visit(tree)                 # collects what to skip
            second = _Finder()
            second.skip = first.skip
            second.visit(tree)
            # Calls that pick a language by argument: _tr("polski", "english")
            for ln, text in second.hits:
                offenders.append(f"{rel}:{ln}  {text[:70]!r}")
        # Known inline bilingual helpers (pl, en) passed positionally.
        offenders = [o for o in offenders if not _is_bilingual_call(o)]
        self.assertEqual(
            offenders, [],
            "Polish text typed into the UI. Use t('section.key', 'English "
            "default') and add the key to locales/en.json and locales/pl.json")


def _is_bilingual_call(offender: str) -> bool:
    """True when the literal sits on a line that also carries its English
    twin for a (pl, en) helper. Checked against the source line."""
    rel, rest = offender.split(":", 1)
    ln = int(rest.split()[0])
    with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
        lines = f.read().splitlines()
    window = "\n".join(lines[max(0, ln - 14):ln + 12])
    return bool(re.search(r"_pl\b|\bplt\b|\bpl\s*=|== ?[\"']pl[\"']|_L\(|_tr\(|_bi\(",
                          window))


class TestLocaleKeys(unittest.TestCase):

    def test_both_languages_have_the_same_keys(self):
        en, pl = _locale("en"), _locale("pl")
        self.assertEqual(sorted(set(en) - set(pl)), [], "missing in pl.json")
        self.assertEqual(sorted(set(pl) - set(en)), [], "missing in en.json")

    def test_every_key_used_in_code_exists(self):
        """t() returns its default UNFORMATTED when the key is missing, so a
        missing key with a {placeholder} shows the braces to the user."""
        en = _locale("en")
        pattern = re.compile(
            r"\b_?t(?:_i18n)?\(\s*[\"']([a-z_0-9]+(?:\.[a-z_0-9]+)+)[\"']")
        missing = set()
        for top in ("ui", "hck_gpt", "core", "utils"):
            for dp, dn, fn in os.walk(os.path.join(_ROOT, top)):
                dn[:] = [d for d in dn if d != "__pycache__"]
                for n in fn:
                    if not n.endswith(".py"):
                        continue
                    with open(os.path.join(dp, n), encoding="utf-8",
                              errors="replace") as f:
                        for m in pattern.finditer(f.read()):
                            k = m.group(1)
                            # "section.prefix_" + name is completed at run
                            # time; test_built_keys_exist covers those
                            if k not in en and not k.endswith("_"):
                                missing.add(k)
        self.assertEqual(sorted(missing), [], "used in code, not in locales")

    def test_built_keys_exist(self):
        """Keys assembled at run time: startup_manager.src_<hive> etc."""
        en = _locale("en")
        for hive in ("hkcu", "hklm", "hklm32", "startup_user", "startup_sys",
                     "task", "uwp"):
            self.assertIn(f"startup_manager.src_{hive}", en)
            self.assertIn(f"startup_manager.hint_{hive}", en)
        from ui.pages.services_manager import _REC_SLUG
        from core.turbo_manager import RECOMMENDED
        for item in RECOMMENDED:
            self.assertIn(item["label"], _REC_SLUG,
                          "a quick-setup tile without a translation slug")
            self.assertIn("services_manager.rec_" + _REC_SLUG[item["label"]], en)

    def test_placeholders_match_between_languages(self):
        en, pl = _locale("en"), _locale("pl")
        ph = re.compile(r"\{([a-z_]+)\}")
        bad = [k for k in en
               if sorted(ph.findall(str(en[k]))) != sorted(ph.findall(str(pl.get(k, ""))))]
        self.assertEqual(bad, [], "placeholders differ between en and pl")


class TestTranslatedAtDrawTime(unittest.TestCase):

    def test_startup_source_labels_follow_the_language(self):
        from utils import i18n
        from ui.pages import startup_manager as sm
        before = i18n.get_lang()
        try:
            i18n.set_lang("en")
            self.assertEqual(sm._src_label("HKCU"), "👤 Your account")
            self.assertIn("all users", sm._src_hint("HKLM"))
            self.assertEqual(sm._who_label("UŻYTKOWNIK"), "USER")
            i18n.set_lang("pl")
            self.assertEqual(sm._src_label("HKCU"), "👤 Twoje konto")
            self.assertEqual(sm._who_label("UŻYTKOWNIK"), "UŻYTKOWNIK")
            self.assertEqual(sm._src_label("???", "x"), "x")
            self.assertIsNone(sm._src_hint("???"))
        finally:
            i18n.set_lang(before)

    def test_quick_setup_question_follows_the_language(self):
        from utils import i18n
        from ui.pages import services_manager as sv
        item = {"label": "Drukowanie", "q_pl": "Czy drukujesz?",
                "q_en": "Do you print?"}
        before = i18n.get_lang()
        try:
            i18n.set_lang("en")
            self.assertEqual(sv._rec_question(item), "Do you print?")
            self.assertEqual(sv._rec_title("Drukowanie"), "Printing")
            i18n.set_lang("pl")
            self.assertEqual(sv._rec_question(item), "Czy drukujesz?")
            self.assertEqual(sv._rec_title("Drukowanie"), "Drukowanie")
        finally:
            i18n.set_lang(before)

    def test_welcome_toast_uses_the_app_language_and_real_version(self):
        with open(os.path.join(_ROOT, "ui", "components", "system_toast.py"),
                  encoding="utf-8") as f:
            src = f.read()
        body = src[src.index("def show_welcome_toast"):]
        body = body[:body.index("def _place_icon")]
        self.assertNotIn("_detect_system_lang()", body)
        self.assertIn("APP_VERSION", body)
        self.assertNotRegex(body, r"v\d+\.\d+\.\d+")


class TestTranslatorIsImported(unittest.TestCase):
    """A file that calls _t() or t() must define it."""

    def test_every_caller_defines_its_translator(self):
        missing = []
        for rel, path in _ui_files():
            with open(path, encoding="utf-8") as f:
                src = f.read()
            tree = ast.parse(src)
            defined = set(dir(builtins))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    defined.add(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for a in node.names:
                        defined.add((a.asname or a.name).split(".")[0])
                elif isinstance(node, ast.Name) and isinstance(
                        node.ctx, ast.Store):
                    defined.add(node.id)
                elif isinstance(node, ast.arg):
                    defined.add(node.arg)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id in ("_t", "t", "_t_i18n")
                        and node.func.id not in defined):
                    missing.append(f"{rel}:{node.lineno} calls "
                                   f"{node.func.id}() which is not defined")
                    break
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
