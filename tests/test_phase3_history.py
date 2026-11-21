"""tests.test_phase3_history - phase 3 of the big update (2026-11-20).

  * the mouse wheel in Activity Memory: smaller steps, and zooming out past
    "everything" resets the view; the window never starts before the
    first record;
  * the Hardware tab: CPU, RAM and GPU on one time axis;
  * a click on the Dashboard chart opens that history (the pin is gone);
  * Monitoring's section headers lead there too;
  * the Learning Center's ring follows the signal its card shows.
"""
import time
import unittest


class _WindowCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        from _isolate import isolate_window_state; isolate_window_state()
        cls.win = mwe.ExpandedMainWindow(
            data_manager=None, monitor=None,
            switch_to_minimal_callback=lambda: None, quit_callback=lambda: None)
        cls.win.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _pump(self, s=0.5):
        end = time.time() + s
        while time.time() < end:
            self.win.root.update()


class TestZoom(_WindowCase):

    def test_wheel_steps_and_reset(self):
        from ui.pages import activity_memory as am
        self.assertEqual(am.WHEEL_ORDER[0], "1H")
        self.assertEqual(am.WHEEL_ORDER[-1], "ALL")
        for lab in am.ZOOM_ORDER:
            self.assertIn(lab, am.WHEEL_ORDER, "every button range is a wheel step")
        win = self.win
        win.open_activity_memory("cpu")
        self._pump()
        p = win._activity_page
        p._set_span("24H")
        p._zoom(time.time() - 3600, -1)
        self.assertEqual(p.span_label, "12H", "one notch in from 24H is 12H, not 1H")
        p._set_span("ALL")
        p.end = time.time() - 86400          # looking somewhere in the past
        p._zoom(time.time(), +1)
        self.assertEqual(p.span_label, "ALL")
        self.assertIsNone(p.end, "out past everything: back to the whole history")

    def test_the_window_never_starts_before_the_first_record(self):
        win = self.win
        win.open_activity_memory("cpu")
        self._pump()
        p = win._activity_page
        p._first_ts = time.time() - 10 * 86400
        p._set_span("24H")
        p._set_end(p._first_ts + 3600)        # asks for a day ending 1 h after the start
        a, b = p._window()
        self.assertGreaterEqual(a, p._first_ts - 1)


class TestHardwareTab(_WindowCase):

    def test_three_charts_one_axis(self):
        win = self.win
        win.open_activity_memory("hardware")
        self._pump(1.5)
        p = win._activity_page
        self.assertTrue(p.hw)
        self.assertEqual(list(p.charts), ["cpu", "ram", "gpu"])
        self.assertTrue(all(c.fixed_pr == 48 for c in p.charts.values()))
        self.assertIn("cpu", p.tiles)
        self.assertIn("gpu_t", p.tiles)

    def test_dashboard_chart_click_opens_it_on_the_same_range(self):
        win = self.win
        win.current_view = None
        win._switch_to_page("dashboard")
        self._pump()
        win.chart_filter = "1W"
        win._chart_on_click(None)
        self._pump(1.0)
        self.assertEqual(win.current_view, "activity_hardware")
        self.assertEqual(win._activity_page.span_label, "7D")
        self.assertEqual(win._FILTER_TO_HISTORY["LIVE"], "1H")


class TestMonitoringLinks(_WindowCase):

    def test_temperature_header_opens_hardware(self):
        import tkinter as tk
        win = self.win
        win._handle_sidebar_navigation("monitoring_alerts")
        self._pump(1.5)
        found = []

        def walk(w):
            for c in w.winfo_children():
                if isinstance(c, tk.Label) and "TEMPERATURE MONITOR" in str(c.cget("text")):
                    found.append(c)
                walk(c)
        walk(win.content_area)
        self.assertTrue(found)
        self.assertEqual(str(found[0].cget("cursor")), "hand2")
        found[0].event_generate("<Button-1>")
        self._pump(1.0)
        self.assertEqual(win.current_view, "activity_hardware")


class TestLearningRing(unittest.TestCase):

    def test_cpu_temperature_waits_three_hours_to_lead(self):
        import core.thermal_baseline as tbm
        tb = tbm.ThermalBaseline.__new__(tbm.ThermalBaseline)
        totals = {"cpu_temp": 40, "gpu_temp": 3000, "cpu_load": 3000}
        tb._metric_total = lambda m: totals[m]
        self.assertEqual(tb.primary_metric(), "gpu_temp")
        totals["cpu_temp"] = tbm.T_TRAINED
        self.assertEqual(tb.primary_metric(), "cpu_temp")


if __name__ == "__main__":
    unittest.main()
