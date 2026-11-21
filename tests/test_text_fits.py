"""tests.test_text_fits
No button or label is cut off (2026-11-15).

The audit found text sliced mid-letter all over the app: "FLUSH RA", "OPE",
"Disab", "Learı", "l5.0%". One cause behind nearly all of it: Tk's pack()
gives space in packing order, so a long text packed first leaves the button
after it with a fraction of what it needs. Worse than ugly, it hid things:
the third Proactivity option, the "Run as administrator" switch, three of
the six chart ranges and the whole MODES bar were not on screen at all.

This test builds the real window, opens the pages and measures every visible
Label / Button: the width Tk gave it against the width its text needs.
"""
import os
import tempfile
import time
import tkinter as tk
import unittest

os.environ.setdefault("PCW_DEBUG", "0")
if not os.environ.get("PCW_LOG_DIR"):
    os.environ["PCW_LOG_DIR"] = tempfile.mkdtemp(prefix="pcw_test_logs_")

# Pages whose content is built synchronously (no background scan needed).
PAGES = [
    ("dashboard", None),
    ("optimization", "center"),
    ("settings", None),
    ("first_setup", None),
    ("fan_control", "fan_dashboard"),
    ("monitoring_alerts", "temperature"),
    ("overclock", None),
]
TOLERANCE_PX = 2


def _clipped(root):
    """[(text, needs, has)] for visible labels narrower than their text."""
    out, stack = [], [root]
    while stack:
        w = stack.pop()
        try:
            stack.extend(w.winfo_children())
            if not isinstance(w, (tk.Label, tk.Button)) or not w.winfo_viewable():
                continue
            text = str(w.cget("text")).strip()
            if not text or w.cget("image"):
                continue
            try:
                if int(float(w.cget("wraplength") or 0)):
                    continue                    # wraps: narrower is fine
            except Exception:
                pass
            need, has = w.winfo_reqwidth(), w.winfo_width()
            if need - has > TOLERANCE_PX:
                out.append((text.replace("\n", " ")[:40], need, has))
        except tk.TclError:
            continue
    return out


class TestTextFits(unittest.TestCase):

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
        # Every Tk callback error while the pages are open is collected:
        # a handler that raises is a button that does nothing.
        cls.callback_errors = []
        cls.win.root.report_callback_exception = (
            lambda exc, val, tb: cls.callback_errors.append(
                f"{exc.__name__}: {val}"))
        # Geometry exists only for a mapped window.
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

    def test_nothing_is_narrower_than_its_text(self):
        problems = []
        for page, sub in PAGES:
            self.win._handle_sidebar_navigation("dashboard", None)
            self.win._handle_sidebar_navigation(page, sub)
            self._pump(0.9)
            for text, need, has in _clipped(self.win.root):
                problems.append(f"{page}/{sub}: {text!r} needs {need}px, has {has}px")
        self.assertEqual(sorted(set(problems)), [],
                         "text is cut off. Pack the control before the text "
                         "that may give way (see ui/components/fit.py)")
        # "lambda missing argument 'e'" was 11 entries in errors.log in July
        # and still came back on Overclock and Drivers until 2026-11-15.
        self.assertEqual(sorted(set(self.callback_errors)), [],
                         "a Tk callback raised while the pages were open")


class TestFitHelpers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        cls.root.geometry("400x200+0+0")

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def _row(self, width):
        row = tk.Frame(self.root, width=width, height=40)
        row.pack_propagate(False)
        row.pack()
        return row

    def test_wrap_to_width_follows_the_container(self):
        from ui.components.fit import wrap_to_width
        row = self._row(120)
        lbl = tk.Label(row, text="a long description that cannot fit in 120 px")
        lbl.pack(fill="x")
        wrap_to_width(lbl, row)
        self.root.update()
        self.assertEqual(int(lbl.cget("wraplength")), 120)
        row.configure(width=300)
        self.root.update()
        self.assertEqual(int(lbl.cget("wraplength")), 300)
        row.destroy()

    def test_optional_text_leaves_whole_and_comes_back(self):
        from ui.components.fit import show_only_if_fits
        row = self._row(300)
        must = tk.Label(row, text="REQUIRED BUTTON")
        must.pack(side="left")
        extra = tk.Label(row, text="a decorative tagline, nice to have")
        extra.pack(side="left")
        show_only_if_fits(extra, row, [must], margin=4)
        self.root.update()
        self.assertTrue(extra.winfo_manager(), "there was room, it was hidden")
        row.configure(width=130)
        self.root.update()
        self.assertFalse(extra.winfo_manager(), "no room, still half shown")
        self.assertGreaterEqual(must.winfo_width(), must.winfo_reqwidth())
        row.configure(width=300)
        self.root.update()
        self.assertTrue(extra.winfo_manager(), "room is back, text is not")
        row.destroy()

    def test_fixed_width_column_keeps_its_content_height(self):
        from ui.components.fit import fixed_width_natural_height
        row = tk.Frame(self.root)
        row.pack()
        col = tk.Frame(row, width=96)
        col.pack(side="left", fill="y")
        for txt in ("icon", "CATEGORY", "sub category"):
            tk.Label(col, text=txt).pack()
        short = tk.Label(row, text="one line")       # the neighbour is shorter
        short.pack(side="left")
        fixed_width_natural_height(col, 96)
        self.root.update()
        self.assertEqual(col.winfo_width(), 96)
        last = col.winfo_children()[-1]
        self.assertGreaterEqual(last.winfo_height(), last.winfo_reqheight(),
                                "the last line of the column is sliced")
        row.destroy()


class TestPackOrderAtTheSource(unittest.TestCase):
    """Pages that fill in from a background scan are checked in the source:
    the control must be packed before the text column."""

    def _src(self, *parts):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, *parts), encoding="utf-8") as f:
            return f.read()

    def test_service_row_packs_controls_first(self):
        src = self._src("ui", "pages", "services_manager.py")
        row = src[src.index("def _service_row"):src.index("def _quick_card")]
        self.assertLess(row.index('right.pack(side="right"'),
                        row.index('body.pack(side="left"'))

    def test_services_bottom_bars_are_ahead_of_the_list(self):
        src = self._src("ui", "pages", "services_manager.py")
        self.assertIn("drawer.outer.pack_configure(before=content_wrap)", src)
        self.assertIn("before=content_wrap)", src.split("modes = _modes_panel(")[1][:120])

    def test_setting_row_packs_the_control_first(self):
        src = self._src("ui", "pages", "settings_page.py")
        row = src[src.index("def _setting_row"):]
        row = row[:row.index("\ndef ", 10) if "\ndef " in row[10:] else len(row)]
        self.assertLess(row.index("right_widget_factory(row)"),
                        row.index('left.pack(side="left"'))

    def test_event_lambdas_tolerate_a_missing_event(self):
        """Tk sometimes calls a bound handler with no event. `lambda e:` then
        raises TypeError and the click does nothing (errors.log: 'lambda
        missing argument e', found again on 4 pages on 2026-11-15)."""
        import re
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bad = []
        for top in ("ui", "hck_gpt"):
            for dp, dn, fn in os.walk(os.path.join(root, top)):
                dn[:] = [d for d in dn if d != "__pycache__"]
                for n in fn:
                    if n.endswith(".py"):
                        with open(os.path.join(dp, n), encoding="utf-8") as f:
                            for i, line in enumerate(f, 1):
                                if re.search(r"\blambda e(:|, )", line):
                                    bad.append(f"{n}:{i}")
        self.assertEqual(bad, [], "use `lambda e=None:`")

    def test_dashboard_card_temperature_is_not_a_formula(self):
        src = self._src("ui", "windows", "main_window_expanded.py")
        self.assertNotIn("30 + (value * 0.6)", src)
        self.assertNotIn("GPUtil.getGPUs()",
                         src[src.index("def _build_yourpc_section"):
                             src.index("def _create_hardware_card")])


class TestCardReading(unittest.TestCase):

    def test_ram_shows_usage_not_a_temperature(self):
        from ui.windows.main_window_expanded import ExpandedMainWindow as E
        r = E._card_reading("ram", 93.4)
        self.assertEqual((r["caption"], r["text"]), ("USED", "93%"))
        self.assertNotIn("°C", r["text"])

    def test_no_sensor_means_no_number(self):
        from unittest import mock
        from ui.windows.main_window_expanded import ExpandedMainWindow as E
        with mock.patch("hck_gpt.data.live_sensors.snapshot",
                        return_value={"gpu_ok": False, "gpu_temp": -1,
                                      "cpu_temp": -1}):
            self.assertEqual(E._card_reading("gpu", 80)["text"], "--")
            self.assertEqual(E._card_reading("cpu", 80)["text"], "--")

    def test_estimate_is_marked(self):
        from unittest import mock
        from ui.windows.main_window_expanded import ExpandedMainWindow as E
        with mock.patch("hck_gpt.data.live_sensors.snapshot",
                        return_value={"cpu_temp": 54.6, "cpu_temp_src": "est",
                                      "gpu_ok": True, "gpu_temp": 61.0}):
            cpu = E._card_reading("cpu", 10)
            gpu = E._card_reading("gpu", 10)
        self.assertEqual((cpu["text"], cpu["caption"]), ("~55°C", "TEMP est."))
        self.assertEqual((gpu["text"], gpu["caption"]), ("61°C", "TEMP"))

    def test_cpu_name_is_the_marketing_name(self):
        from ui.windows.main_window_expanded import ExpandedMainWindow as E
        self.assertEqual(
            E._short_hw_name("12th Gen Intel(R) Core(TM) i5-12400F"),
            "Intel Core i5-12400F")
        self.assertEqual(
            E._short_hw_name("AMD Ryzen 5 5600X 6-Core Processor"),
            "AMD Ryzen 5 5600X 6-Core")


if __name__ == "__main__":
    unittest.main()
