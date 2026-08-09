"""tests.test_window_scaling
Resizable-window rework guards (2026-07).

Three behaviors must never regress:
  1. ui_scale: small screens get a BIGGER window (the old formula shrank it),
     FHD/2K/4K tiers stay exactly as designed.
  2. The root window is freely resizable with a minsize floor at the designed
     compact geometry - growing is safe, shrinking below it clips widgets.
  3. Manual resize morphs the maximize button into "RESET size", and the
     reset snaps back to the centered compact geometry. Maximize (zoomed)
     still round-trips and never re-locks the window.
"""
import os
import unittest

os.environ.setdefault("PCW_DEBUG", "0")

from utils.ui_scale import _compute_scale, _BASE_W, _BASE_H


class TestScaleFormula(unittest.TestCase):

    def test_fhd_and_up_tiers_unchanged(self):
        self.assertEqual(_compute_scale(1920, 1080), 1.0)
        self.assertEqual(_compute_scale(2560, 1440), 1.35)
        self.assertEqual(_compute_scale(3840, 2160), 2.0)

    def test_1366x768_gets_full_size_window(self):
        """The classic small laptop: old formula gave 0.85 (a shrunken
        986x489 window). New formula fills the screen -> full 1.0."""
        s = _compute_scale(1366, 768)
        self.assertEqual(s, 1.0)
        self.assertLessEqual(_BASE_W * s, 1366 * 0.9)

    def test_1280x720_window_fits_screen(self):
        s = _compute_scale(1280, 720)
        self.assertGreater(s, 0.9)          # old formula: 0.85
        self.assertLessEqual(_BASE_W * s, 1280 * 0.92)
        self.assertLessEqual(_BASE_H * s, 720 * 0.90)

    def test_1024x768_floor_holds(self):
        s = _compute_scale(1024, 768)
        self.assertGreaterEqual(s, 0.75)
        self.assertLessEqual(_BASE_W * s, 1024)

    def test_never_above_fhd_baseline_below_1920(self):
        for sw, sh in ((1600, 900), (1440, 900), (1366, 768), (1280, 800)):
            self.assertLessEqual(_compute_scale(sw, sh), 1.0)

    def test_window_fits_on_every_common_screen(self):
        """
        Ratchet. The tiers above 1920 used to read width only, so a 3840x1080
        super-ultrawide picked the 4K scale and produced a 1150px-tall window
        on a 1080px screen: the bottom of the app was off-screen and nothing
        reported it. No screen may ever get a window it cannot show.
        """
        TASKBAR = 48
        screens = (
            (1024, 768), (1280, 720), (1366, 768), (1440, 900), (1600, 900),
            (1920, 1080), (1920, 1200),
            (2560, 1080), (2560, 1440), (3440, 1440),
            (3840, 1080), (3840, 1600), (3840, 2160), (5120, 1440),
        )
        for sw, sh in screens:
            s = _compute_scale(sw, sh)
            w, h = _BASE_W * s, _BASE_H * s
            self.assertLessEqual(w, sw, f"window wider than {sw}x{sh}")
            self.assertLessEqual(h + TASKBAR, sh, f"window taller than {sw}x{sh}")

    def test_standard_tiers_did_not_move(self):
        """The ultrawide clamp must not touch normal screens: 1080p stays 1:1."""
        self.assertEqual(_compute_scale(1920, 1080), 1.0)
        self.assertEqual(_compute_scale(2560, 1440), 1.35)
        self.assertEqual(_compute_scale(3840, 2160), 2.0)


class TestResizableWindow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        import utils.ui_scale as uis
        cls.uis = uis
        try:
            cls.win = mwe.ExpandedMainWindow(
                data_manager=None, monitor=None,
                switch_to_minimal_callback=lambda: None,
                quit_callback=lambda: None)
        except Exception as e:  # pragma: no cover
            raise unittest.SkipTest(f"window build unavailable: {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.win.root.destroy()
        except Exception:
            pass

    def _pump(self):
        self.win.root.update_idletasks()
        self.win.root.update()

    def test_1_window_is_resizable_with_minsize_floor(self):
        r = self.win.root
        w_ok, h_ok = r.resizable()
        self.assertTrue(bool(w_ok) and bool(h_ok), "window must be user-resizable")
        self.assertEqual(r.minsize(), (self.uis.compact_w(), self.uis.compact_h()),
                         "minsize floor must equal the designed compact size")

    def test_2_default_size_shows_maximize_glyph(self):
        self._pump()
        self.assertTrue(self.win._is_default_size())
        self.win._update_max_btns()
        btn = getattr(self.win, "_max_btn", None)
        if btn is not None and btn.winfo_exists():
            self.assertEqual(btn.cget("text"), "⤢")

    def test_3_manual_resize_morphs_button_to_reset(self):
        r = self.win.root
        r.geometry(f"{self.uis.compact_w() + 160}x{self.uis.compact_h() + 90}")
        self._pump()
        self.assertFalse(self.win._is_default_size())
        self.win._update_max_btns()          # call directly - no debounce wait
        btn = getattr(self.win, "_max_btn", None)
        if btn is not None and btn.winfo_exists():
            self.assertIn("RESET", btn.cget("text"))

    def test_4_reset_returns_to_compact_centered(self):
        r = self.win.root
        r.geometry(f"{self.uis.compact_w() + 160}x{self.uis.compact_h() + 90}")
        self._pump()
        self.win._on_max_btn_click()         # resized state -> must route to reset
        self._pump()
        self.assertTrue(self.win._is_default_size(),
                        f"RESET left geometry at {r.geometry()}")
        self.assertFalse(self.win._is_maximized)

    def test_5_maximize_roundtrip_keeps_window_resizable(self):
        win = self.win
        win._toggle_maximize()
        self._pump()
        self.assertTrue(win._is_maximized)
        win._toggle_maximize()
        self._pump()
        self.assertFalse(win._is_maximized)
        w_ok, h_ok = win.root.resizable()
        self.assertTrue(bool(w_ok) and bool(h_ok),
                        "restore from zoomed must NOT re-lock resizing")

    def test_6_page_switch_after_resize_is_stable(self):
        """Resize, then walk through direct pages + an overlay page - nothing
        may raise (crash_log would swallow it in prod; here it fails loud)."""
        win = self.win
        win.root.geometry(f"{self.uis.compact_w() + 200}x{self.uis.compact_h() + 120}")
        self._pump()
        for page, sub in (("monitoring_alerts", "temperature"),
                          ("optimization", "center"),
                          ("my_pc", "central"),
                          ("settings", None),
                          ("dashboard", None)):
            win.current_view = None
            win.active_overlay = None
            win.overlay_frame = None
            win._handle_sidebar_navigation(page, sub)
            self._pump()
        win._reset_size()
        self._pump()
        self.assertTrue(win._is_default_size())


if __name__ == "__main__":
    unittest.main()
