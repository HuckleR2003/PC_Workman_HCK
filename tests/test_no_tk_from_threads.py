"""No worker thread calls Tk (2026-11-21).

Tk called from a worker raises "main thread is not in main loop" when the main
loop is not the one pumping (the error was swallowed and the Startup Manager
stayed on "Scanning…"). A worker holding the last reference to a widget
frees the Tk interpreter from the wrong thread: the process aborts with
Tcl_AsyncDelete. The pattern to use is ui/bg.py: run(), Mailbox/watch(),
post().

The check reads the source: for every threading.Thread(target=...), it walks
the target and the functions of the same module it calls (by name or as
self.<method>), and looks for Tk calls. Functions handed to ui.bg.run() are
on a worker too and are checked the same way.
"""
import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TK_CALLS = {
    "after", "after_idle", "after_cancel", "winfo_exists", "winfo_children", "winfo_width",
    "winfo_height", "winfo_toplevel", "itemconfig", "itemconfigure", "config", "configure",
    "update_idletasks", "deiconify", "withdraw", "geometry", "pack", "grid", "place",
    "pack_forget", "destroy", "create_text", "create_line", "create_rectangle", "coords",
    "tag_configure", "tag_add", "see", "focus_set", "lift", "attributes", "itemcget", "cget",
}
# names that are Tk-looking but not Tk here: (file, function) -> why
ALLOWED = {
    # its own Tk interpreter on its own thread, created and polled there:
    # it must show before the main window exists (like the splash screen)
    ("ui/diag_window.py", "_run"),
}


def _defs(tree):
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(node)
    return out


def _target_nodes(call, defs):
    """The function bodies a Thread(target=...) or bg.run(w, work, ...) starts."""
    tgt = None
    for kw in call.keywords:
        if kw.arg == "target":
            tgt = kw.value
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
    if tgt is None and name == "run" and isinstance(f, ast.Attribute) and \
            getattr(f.value, "id", "") in ("_bg_ui", "bg") and len(call.args) >= 2:
        tgt = call.args[1]
    if tgt is None:
        return []
    if isinstance(tgt, ast.Lambda):
        return [tgt]
    if isinstance(tgt, ast.Name):
        return defs.get(tgt.id, [])
    if isinstance(tgt, ast.Attribute):
        return defs.get(tgt.attr, [])
    return []


def _is_thread_call(call):
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
    if name == "Thread":
        return True
    return name == "run" and isinstance(f, ast.Attribute) and getattr(f.value, "id", "") in ("_bg_ui", "bg")


def _tk_calls_in(node, defs, seen, depth=0):
    found = []
    if id(node) in seen or depth > 4:
        return found
    seen.add(id(node))
    body = node.body if isinstance(node.body, list) else [node.body]
    for stmt in body:
        for sub in ast.walk(stmt):
            if not isinstance(sub, ast.Call):
                continue
            f = sub.func
            if isinstance(f, ast.Attribute):
                if f.attr in TK_CALLS:
                    found.append((sub.lineno, f.attr))
                # self.method() / obj.method(): follow functions of this module
                elif isinstance(f.value, ast.Name) and f.value.id == "self":
                    for d in defs.get(f.attr, []):
                        found += _tk_calls_in(d, defs, seen, depth + 1)
            elif isinstance(f, ast.Name):
                for d in defs.get(f.id, []):
                    found += _tk_calls_in(d, defs, seen, depth + 1)
    return found


def violations():
    out = []
    for top in ("ui", "hck_gpt", "core", "hck_stats_engine", "utils"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, top)):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for n in fn:
                if not n.endswith(".py"):
                    continue
                path = os.path.join(dp, n)
                rel = os.path.relpath(path, ROOT).replace("\\", "/")
                if rel == "ui/bg.py":
                    continue                 # the helper itself polls on the UI thread
                with open(path, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                defs = _defs(tree)
                for call in ast.walk(tree):
                    if isinstance(call, ast.Call) and _is_thread_call(call):
                        for t in _target_nodes(call, defs):
                            tname = getattr(t, "name", "<lambda>")
                            if (rel, tname) in ALLOWED:
                                continue
                            for line, attr in _tk_calls_in(t, defs, set()):
                                out.append(f"{rel}:{line} .{attr}() reached from thread target {tname} (line {call.lineno})")
    return sorted(set(out))


class TestNoTkFromThreads(unittest.TestCase):

    def test_no_worker_thread_calls_tk(self):
        self.assertEqual(violations(), [], "use ui/bg.py: run(), Mailbox + watch(), post()")


class TestBgHelper(unittest.TestCase):
    """ui/bg.py itself, on a real (hidden) Tk root."""

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            cls.root = tk.Tk()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def _pump(self, cond, timeout=5.0):
        import time
        end = time.time() + timeout
        while time.time() < end and not cond():
            self.root.update()
            time.sleep(0.01)

    def test_run_delivers_on_the_ui_thread(self):
        import threading
        from ui import bg
        seen = {}

        def work():
            seen["work_thread"] = threading.current_thread() is threading.main_thread()
            return 42
        bg.run(self.root, work, lambda v: seen.update(v=v, done_main=threading.current_thread() is threading.main_thread()),
               poll_ms=10)
        self._pump(lambda: "v" in seen)
        self.assertEqual(seen["v"], 42)
        self.assertFalse(seen["work_thread"])
        self.assertTrue(seen["done_main"])

    def test_nothing_runs_when_the_widget_is_gone(self):
        import time
        import tkinter as tk
        from ui import bg
        w = tk.Frame(self.root)
        called = []
        bg.run(w, lambda: time.sleep(0.1), lambda v: called.append(v), poll_ms=10)
        w.destroy()
        self._pump(lambda: False, timeout=0.4)
        self.assertEqual(called, [])

    def test_errors_go_to_fail(self):
        from ui import bg
        got = []
        bg.run(self.root, lambda: 1 / 0, lambda v: got.append("done"), fail=lambda e: got.append(type(e).__name__),
               poll_ms=10)
        self._pump(lambda: got)
        self.assertEqual(got, ["ZeroDivisionError"])

    def test_mailbox_keeps_order_and_unhooks(self):
        import threading
        import tkinter as tk
        from ui import bg
        w = tk.Frame(self.root)
        box = bg.Mailbox()
        got, closed = [], []
        bg.watch(w, box, got.append, every_ms=10, on_close=lambda: closed.append(True))
        cb = bg.listener(box)
        t = threading.Thread(target=lambda: [cb(i) for i in range(5)])
        t.start()
        t.join()
        self._pump(lambda: len(got) == 5)
        self.assertEqual(got, [0, 1, 2, 3, 4])
        w.destroy()
        self._pump(lambda: closed, timeout=1)
        self.assertEqual(closed, [True])
        self.assertTrue(box.closed)

    def test_post_from_a_thread_runs_on_drain(self):
        import threading
        from ui import bg
        ran = []
        t = threading.Thread(target=lambda: bg.post(lambda: ran.append(threading.current_thread() is threading.main_thread())))
        t.start()
        t.join()
        bg.drain()
        self.assertEqual(ran, [True])


if __name__ == "__main__":
    for v in violations():
        print(v)
