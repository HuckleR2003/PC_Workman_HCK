"""tests.test_no_dead_modules
Every module in the app packages is reachable from startup.py (2026-11-14).

The audit found 21 files (330 KB) that nothing imported: old copies of the
main window left next to the live ones in ui/windows/ (one of them no longer
even parsed), plus helpers nobody called. Searching the code kept landing in
them, and a fix applied to the dead copy looks done and changes nothing.

Reachability follows import statements anywhere in a file and string literals
that name a module (startup.py loads core modules with __import__("core.x")).
A module that is only run by hand goes in ALLOWED, with the reason.
"""
import ast
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PKGS = ("core", "hck_gpt", "hck_stats_engine", "ui", "utils")

ALLOWED = {
    # Developer tool, run by hand: python -m hck_gpt.intents.train_classifier
    "hck_gpt/intents/train_classifier.py",
}


def _collect():
    files = {"startup.py": os.path.join(_ROOT, "startup.py"),
             "import_core.py": os.path.join(_ROOT, "import_core.py")}
    for pkg in _PKGS:
        for dp, dn, fn in os.walk(os.path.join(_ROOT, pkg)):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for n in fn:
                if n.endswith(".py"):
                    p = os.path.join(dp, n)
                    files[os.path.relpath(p, _ROOT).replace("\\", "/")] = p
    return files


def _modname(rel):
    m = rel[:-3].replace("/", ".")
    return m[:-9] if m.endswith(".__init__") else m


class TestNoDeadModules(unittest.TestCase):

    def test_every_module_parses(self):
        for rel, path in _collect().items():
            with open(path, encoding="utf-8") as f:
                try:
                    ast.parse(f.read())
                except SyntaxError as e:
                    self.fail(f"{rel} does not parse: {e}")

    def test_everything_is_reachable_from_startup(self):
        files = _collect()
        mods = {_modname(r): r for r in files}

        def edges(rel):
            with open(files[rel], encoding="utf-8") as f:
                tree = ast.parse(f.read())
            me, out = _modname(rel), set()
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    base = node.module or ""
                    if node.level:
                        parts = me.split(".")
                        if not rel.endswith("__init__.py"):
                            parts = parts[:-1]
                        parts = parts[:len(parts) - (node.level - 1)]
                        base = ".".join(parts + ([base] if base else []))
                    names = [base] + [f"{base}.{a.name}" for a in node.names]
                elif (isinstance(node, ast.Constant)
                      and isinstance(node.value, str)
                      and re.fullmatch(r"[A-Za-z_][\w.]*", node.value)):
                    names = [node.value]
                for n in names:
                    while n:
                        if n in mods:
                            out.add(mods[n])
                        n = n.rsplit(".", 1)[0] if "." in n else ""
            return out

        seen, todo = set(), ["startup.py"]
        while todo:
            r = todo.pop()
            if r not in seen:
                seen.add(r)
                todo.extend(edges(r))

        dead = sorted(r for r in files
                      if r.startswith(_PKGS) and r not in seen
                      and r not in ALLOWED)
        self.assertEqual(dead, [], "nothing imports these modules. Wire them "
                                   "in, delete them, or add them to ALLOWED "
                                   "with a reason")

    def test_spec_lists_no_missing_module(self):
        """A hidden import that no longer exists makes PyInstaller warn and
        hides real problems in the build log."""
        files = _collect()
        mods = {_modname(r) for r in files}
        with open(os.path.join(_ROOT, "PCWorkman.spec"), encoding="utf-8") as f:
            spec = f.read()
        block = spec[spec.index("hiddenimports = ["):spec.index("a = Analysis(")]
        listed = re.findall(r"'((?:core|hck_gpt|hck_stats_engine|ui|utils)"
                            r"(?:\.[A-Za-z_]\w*)*)'", block)
        missing = sorted(m for m in listed if m not in mods)
        self.assertEqual(missing, [], "listed in PCWorkman.spec, not on disk")


if __name__ == "__main__":
    unittest.main()
