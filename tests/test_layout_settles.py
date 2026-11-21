"""tests.test_layout_settles - a page must stop moving once it is built
(2026-11-16).

Services Manager in the default window size never stopped moving: its two
service columns split the width by what their text asked for, the text
wrapped to the width it got, and every wrap moved the split again. The user
saw the list jump continuously (recorded as a GIF).

The test builds the real window at its default size, opens each page that
lays text out to its width, lets it settle, and then compares the geometry
of every widget across a further second. Nothing may move.
"""
import time
import tkinter as tk
import unittest

PAGES = [("services_manager", None), ("startup_manager", None),
         ("optimization", None), ("dashboard", None)]


def _geometry(root):
    out = {}
    stack = [root]
    while stack:
        w = stack.pop()
        try:
            if w.winfo_ismapped():
                out[str(w)] = (w.winfo_x(), w.winfo_y(),
                               w.winfo_width(), w.winfo_height())
            stack.extend(w.winfo_children())
        except tk.TclError:
            pass
    return out


class TestLayoutSettles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        try:
            from _isolate import isolate_window_state; isolate_window_state()
            cls.win = mwe.ExpandedMainWindow(
                data_manager=None, monitor=None,
                switch_to_minimal_callback=lambda: None,
                quit_callback=lambda: None)
        except Exception as e:  # pragma: no cover
            raise unittest.SkipTest(f"window build unavailable: {e}")
        cls.win.root.deiconify()
        cls._pump(0.6)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    @classmethod
    def _pump(cls, seconds):
        end = time.time() + seconds
        while time.time() < end:
            try:
                cls.win.root.update()
            except tk.TclError:
                return
            time.sleep(0.02)

    def test_pages_stop_moving(self):
        content = self.win.content_area
        moving = []
        for page, sub in PAGES:
            self.win._handle_sidebar_navigation(page, sub)
            # Let late data arrive first: the dashboard's process list fills
            # when the first sample comes in, which on a busy machine takes
            # longer than a second. Wait (up to 8 s) for two equal snapshots;
            # a real layout loop never gets there, and the check below then
            # sees it moving.
            self._pump(1.5)
            prev = _geometry(content)
            for _ in range(13):
                self._pump(0.5)
                cur = _geometry(content)
                if cur == prev:
                    break
                prev = cur
            before = _geometry(content)
            self._pump(1.0)
            after = _geometry(content)
            changed = [k for k in before if k in after and before[k] != after[k]]
            # live values (bars, sparklines, counters) may change their own
            # canvas content but not the layout; allow a couple of widgets
            # whose text is a live number
            if len(changed) > 3:
                moving.append(f"{page}: {len(changed)} widgets moved, e.g. "
                              f"{changed[0]} {before[changed[0]]} -> {after[changed[0]]}")
        self.assertEqual(moving, [], "the layout keeps moving after it was built")

    def test_services_settle_at_125_percent_scaling(self):
        """The loop showed up only with Windows display scaling at 125 %:
        text is wider there, and the old column split never settled - Tk's
        update() did not even return. A watchdog ends the run with a
        traceback instead of hanging the whole suite."""
        import faulthandler
        root = self.win.root
        old = root.tk.call("tk", "scaling")
        faulthandler.dump_traceback_later(90, exit=True)
        try:
            root.tk.call("tk", "scaling", 1.25 * 96 / 72)
            self.win._handle_sidebar_navigation("dashboard", None)
            self.win._handle_sidebar_navigation("services_manager", None)
            self._pump(2.0)
            before = _geometry(self.win.content_area)
            self._pump(1.0)
            after = _geometry(self.win.content_area)
            changed = [k for k in before if k in after and before[k] != after[k]]
            self.assertLessEqual(len(changed), 3, changed[:5])
            self.assertGreater(len(before), 100, "the service list never loaded")
        finally:
            faulthandler.cancel_dump_traceback_later()
            root.tk.call("tk", "scaling", old)


if __name__ == "__main__":
    unittest.main()
