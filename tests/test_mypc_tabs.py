"""tests.test_mypc_tabs
My PC internal tab guards (2026-07-16 audit). Every tab in the strip
(central / health / components / efficiency / startup / map) must BUILD on a
real Tk root without raising, and the degraded/empty states must render a
professional card instead of a blank page.

Born from a live-Tk audit that found the Health tab (and any tab using the
shared _sec_hdr) crashing on an invalid Tk option: letterSpacing=1 (a CSS
property that leaked into a tkinter Label). Skips where no display exists.
"""
import types
import unittest


class _TkTabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            cls.tk = tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.components.yourpc_page as yp
        cls.yp = yp

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def _fake(self):
        return types.SimpleNamespace(root=self.root, monitor=None,
                                     yourpc_tabs={}, yourpc_active_tab=None)

    def _count(self, w):
        return 1 + sum(self._count(c) for c in w.winfo_children())


class TestAllTabsBuild(_TkTabTest):

    TABS = ("central", "health", "components", "efficiency", "startup", "map")

    def test_every_tab_builds_without_crashing(self):
        for tab in self.TABS:
            with self.subTest(tab=tab):
                frame = self.tk.Frame(self.root)
                try:
                    getattr(self.yp, f"_build_{tab}")(self._fake(), frame)
                    self.root.update_idletasks()
                except Exception as e:
                    self.fail(f"My PC tab '{tab}' crashed on build: "
                              f"{type(e).__name__}: {e}")
                finally:
                    frame.destroy()

    def test_no_cssish_tk_options_in_module(self):
        """letterSpacing / lineHeight / fontWeight etc. are CSS, not Tk -
        they crash at render. Guard the whole module."""
        import inspect
        src = inspect.getsource(self.yp)
        for bad in ("letterSpacing", "lineHeight", "fontWeight",
                    "borderRadius", "boxShadow"):
            self.assertNotIn(bad + "=", src,
                             f"CSS-ish Tk option '{bad}' will crash at render")


class TestEmptyStates(_TkTabTest):

    def test_startup_empty_state_renders(self):
        f = self.tk.Frame(self.root)
        sf, _ = self.yp._make_scroll_frame(f)
        self.yp._render_startup(sf, self.tk.Label(sf), [], self._fake())
        self.root.update_idletasks()
        self.assertGreater(self._count(f), 6,
                           "0 startup entries must show an empty-state card")
        f.destroy()

    def test_components_empty_state_renders(self):
        f = self.tk.Frame(self.root)
        sf, _ = self.yp._make_scroll_frame(f)
        self.yp._render_components(sf, self.tk.Label(sf), {})
        self.root.update_idletasks()
        self.assertGreater(self._count(f), 6,
                           "empty scan must show an empty-state card, "
                           "not a wall of N/A")
        f.destroy()

    def test_empty_state_helper_shape(self):
        f = self.tk.Frame(self.root)
        self.yp._empty_state(f, "🧩", "Title", "subtitle text")
        self.root.update_idletasks()
        self.assertGreaterEqual(self._count(f), 4)
        f.destroy()


if __name__ == "__main__":
    unittest.main()
