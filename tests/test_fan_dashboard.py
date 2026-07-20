"""tests.test_fan_dashboard
Fan Dashboard 2026-07-18 redesign guards: curve interpolation, monotonic
point constraint, the locked-by-default chart, and the learned AI profile.
Pure-logic tests - the real-window build is covered by test_navigation.
"""
import unittest

from ui.components.fan_dashboard import (
    CompactFanCurveGraph, FanAIEngine,
)
from ui.components.fan_curve_editor import FanCurvePoint


class _Graph(CompactFanCurveGraph):
    """Logic-only instance: skip tk.Canvas init, keep the math."""
    def __init__(self):
        self.width, self.height = 550, 170
        self.points = [FanCurvePoint(t, s) for t, s in
                       [(0, 25), (40, 40), (80, 75), (100, 90)]]
        self.locked = True
        self._hover = False
        self._live_temp = None
        self._ai_btn = None
        self.dragging_point = None
        self.get_max_rpm = lambda: 2400
        self.get_min_pct = lambda: 0
        self.get_set_rpm = lambda: 0
        self.on_curve_change = None
        self.on_ai_consult = None

    def _draw(self):
        pass

    def _show_ai_button(self):
        self._ai_btn = "shown"


class _Ev:
    def __init__(self, x, y):
        self.x, self.y = x, y


class TestCurveMath(unittest.TestCase):

    def test_speed_at_interpolates(self):
        g = _Graph()
        self.assertEqual(g.speed_at(0), 25)
        self.assertEqual(g.speed_at(100), 90)
        self.assertAlmostEqual(g.speed_at(20), 32.5)   # halfway 25..40
        self.assertEqual(g.speed_at(-10), 25)          # clamps below
        self.assertEqual(g.speed_at(150), 90)          # clamps above

    def test_drag_cannot_pass_neighbours(self):
        """The monotonic guard: a middle point dragged far right must stop
        MIN_GAP short of its right neighbour, never overlap or pass it."""
        g = _Graph()
        g.locked = False
        g.dragging_point = 1                           # point at temp=40
        far_right = _Ev(x=10_000, y=60)
        g._on_drag(far_right)
        self.assertEqual(g.points[1].temp, 80 - g.MIN_GAP)
        far_left = _Ev(x=-10_000, y=60)
        g._on_drag(far_left)
        self.assertEqual(g.points[1].temp, 0 + g.MIN_GAP)

    def test_min_slider_lifts_the_floor(self):
        """MIN FAN SPEED clamps speed_at from below - the visible chart
        floor and the card percents can never dip under it."""
        g = _Graph()
        g.get_min_pct = lambda: 40
        self.assertEqual(g.speed_at(0), 40)     # curve says 25 -> floor wins
        self.assertEqual(g.speed_at(100), 90)   # above the floor untouched

    def test_drag_clamps_speed(self):
        g = _Graph()
        g.locked = False
        g.dragging_point = 1
        g._on_drag(_Ev(x=200, y=-500))
        self.assertEqual(g.points[1].speed, 100)
        g._on_drag(_Ev(x=200, y=5000))
        self.assertEqual(g.points[1].speed, 0)

    def test_locked_chart_ignores_drag_and_first_click_unlocks(self):
        g = _Graph()
        before = [(p.temp, p.speed) for p in g.points]
        g.dragging_point = 1
        g._on_drag(_Ev(x=300, y=30))                   # locked -> no change
        self.assertEqual(before, [(p.temp, p.speed) for p in g.points])
        g.dragging_point = None
        g._on_click(_Ev(x=300, y=30))                  # first click unlocks
        self.assertFalse(g.locked)
        self.assertEqual(g._ai_btn, "shown")


class TestAIProfile(unittest.TestCase):

    def test_ai_curve_is_monotonic_and_bounded(self):
        pts = FanAIEngine.generate_curve("ai")
        self.assertGreaterEqual(len(pts), 5)
        temps = [p.temp for p in pts]
        speeds = [p.speed for p in pts]
        self.assertEqual(temps, sorted(temps))
        self.assertTrue(all(t2 - t1 >= 3 for t1, t2 in zip(temps, temps[1:])),
                        f"points closer than MIN_GAP: {temps}")
        self.assertTrue(all(0 <= s <= 100 for s in speeds))
        self.assertEqual(pts[-1].speed, 100)           # always full at 100C

    def test_named_profiles_still_generate(self):
        for name in ("silent", "balanced", "performance"):
            pts = FanAIEngine.generate_curve(name)
            self.assertEqual(len(pts), 5)


class TestChatWiring(unittest.TestCase):

    def test_fan_intents_have_handlers(self):
        from hck_gpt.responses.builder import ResponseBuilder
        rb = ResponseBuilder()
        self.assertTrue(hasattr(rb, "_resp_fan_consult"))
        self.assertTrue(hasattr(rb, "_resp_fan_apply_ai"))

    def test_apply_ai_without_dashboard_is_honest(self):
        """No dashboard open -> the answer must say 'open it first', never
        claim success."""
        from hck_gpt.responses.builder import ResponseBuilder
        from hck_gpt.intents.parser import ParseResult
        out = ResponseBuilder()._resp_fan_apply_ai(
            ParseResult(intent="fan_apply_ai", confidence=1.0,
                        entities={}, raw_text="t"), "en")
        joined = " ".join(out)
        self.assertNotIn("Done", joined)
        self.assertIn("Fan Dashboard", joined)

    def test_panel_has_public_ask(self):
        import inspect
        from hck_gpt import panel as panel_mod
        src = inspect.getsource(panel_mod)
        self.assertIn("def ask(self, text", src)


if __name__ == "__main__":
    unittest.main()
