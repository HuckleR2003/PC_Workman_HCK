"""Phase 7 (2026-11-20): the PC map, rebuilt.

The old map drew the back faces of its boxes in list order, so parts showed
through each other. These tests measure, off-screen, that every part with a
name can be seen, that nothing shares a place, and the pure pieces of the
view (colours, details, layout from the hardware).
"""
import os
import unittest

from ui.components import pc_map_scene as S


def _footprints_overlap(a, b):
    e = 1e-6
    return (a.x < b.x + b.w - e and b.x < a.x + a.w - e and
            a.y < b.y + b.d - e and b.y < a.y + a.d - e and
            a.z < b.z + b.h - e and b.z < a.z + a.h - e)


# parts the user points at; slots and the PCIe connector may hide under
# what sits in them
_MUST_SEE = {"cpu": 0.85, "gpu": 0.9, "ram": 0.9, "nvme": 0.9, "psu": 0.9, "drive": 0.9,
             "vrm": 0.45, "mobo": 0.4, "chipset": 0.9,
             "battery": 0.9, "screen": 0.9, "fan": 0.9}


class TestScene(unittest.TestCase):

    def _scenes(self):
        for ram in (1, 2, 3, 4):
            for gpu in (True, False):
                for nvme in (True, False):
                    for sata in (0, 1, 3):
                        yield f"desktop ram={ram} gpu={gpu} nvme={nvme} sata={sata}", \
                            S.desktop(ram, gpu, nvme, sata)
        for gpu in (True, False):
            yield f"laptop gpu={gpu}", S.laptop(gpu)

    def test_no_two_parts_share_a_place(self):
        for name, parts in self._scenes():
            for i, a in enumerate(parts):
                for b in parts[i + 1:]:
                    self.assertFalse(_footprints_overlap(a, b), f"{name}: {a} / {b}")

    def test_every_named_part_can_be_seen(self):
        for name, parts in self._scenes():
            vis = S.visibility(parts, 480, 360)
            for key, need in _MUST_SEE.items():
                if key in vis:
                    self.assertGreaterEqual(vis[key], need, f"{name}: {key} {vis[key]:.2f}")

    def test_order_puts_what_sits_on_top_after_its_base(self):
        parts = S.desktop()
        order = S.order(parts)
        board = next(p for p in order if p.key == "mobo" and p.role == "board")
        for p in order:
            if p is not board:
                self.assertLess(order.index(board), order.index(p))
        cooler = [p for p in order if p.key == "cpu"]
        self.assertEqual([p.z for p in cooler], sorted(p.z for p in cooler))

    def test_sticks_go_in_the_second_and_fourth_slot_first(self):
        idx = sorted(p.idx for p in S.desktop(ram_sticks=2) if p.key == "ram")
        self.assertEqual(idx, [1, 3])
        self.assertEqual(sum(1 for p in S.desktop(ram_sticks=2) if p.key == "ram_slot"), 4)

    def test_hit_finds_the_front_part(self):
        parts = S.desktop()
        f = S.fit(parts, 700, 500)
        x, y = S.to_screen([S.top_center(next(p for p in parts if p.key == "psu"))], f)[0]
        self.assertEqual(S.hit(parts, f, x, y + 3), "psu")
        self.assertIsNone(S.hit(parts, f, 2, 2))

    def test_scene_fills_the_canvas(self):
        for parts in (S.desktop(), S.laptop()):
            f = S.fit(parts, 700, 500, margin=24)
            x0, y0, x1, y1 = S.bounds(parts)
            sc = f[0]
            self.assertTrue((x1 - x0) * sc >= 0.9 * 652 or (y1 - y0) * sc >= 0.9 * 452)
        # the laptop takes at least 60% of the height (plan 7.8)
        parts = S.laptop()
        f = S.fit(parts, 700, 500)
        _x0, y0, _x1, y1 = S.bounds(parts)
        self.assertGreaterEqual((y1 - y0) * f[0], 0.6 * 500)

    def test_labels_do_not_sit_on_the_same_spot(self):
        for parts in (S.desktop(2, True, True, 2), S.laptop()):
            pts = list(S.label_points(parts, S.fit(parts, 700, 500)).values())
            for i, a in enumerate(pts):
                for b in pts[i + 1:]:
                    self.assertGreater(abs(a[0] - b[0]) + abs(a[1] - b[1]), 25)

    def test_heat_colours(self):
        self.assertEqual(S.heat_color(0), S.COOL)
        self.assertEqual(S.heat_color(1), S.HOT)
        self.assertEqual(S.heat_color(None), S.NEUTRAL)
        img, _f = S.render(S.desktop(), 200, 150, {"cpu": 0.1}, hovered="cpu")
        self.assertEqual(img.size, (200, 150))


class TestViewPieces(unittest.TestCase):

    def test_heat_temperature_first_then_load(self):
        from ui.components.pc_map import heat_values
        h = heat_values({"cpu_temp": 85, "cpu_pct": 5, "gpu_temp": None, "gpu_pct": 50,
                         "ram_pct": 40}, {})
        self.assertEqual(h["cpu"], 1.0)
        self.assertAlmostEqual(h["gpu"], 0.5)
        self.assertEqual(h["ram"], 0.0)
        w = heat_values({}, {"cpu": {"avg": 20, "temp_avg": None}}, "week")
        self.assertAlmostEqual(w["cpu"], 0.2)
        self.assertIsNone(w["gpu"])

    def test_layout_from_the_hardware(self):
        from ui.components.pc_map import layout_args
        hw = {"ram": {"modules": [{"capacity_gb": 8}]}, "gpu": {"name": "RTX 3050"},
              "disks": [{"bus": "NVMe"}, {"bus": "SATA"}, {"bus": "SATA"}, {"bus": "USB"}]}
        self.assertEqual(layout_args(hw), {"ram_sticks": 1, "has_gpu": True, "nvme": True, "sata": 2})
        self.assertFalse(layout_args({"gpu": {"name": "Not detected"}, "disks": [{"bus": "SATA"}]})["nvme"])

    def test_details_name_the_model_and_say_what_is_unknown(self):
        from ui.components.pc_map import details
        hw = {"cpu": {"name": "i5-12400F", "cores_physical": 6, "cores_logical": 12},
              "disks": [{"name": "Samsung SSD 980 1TB", "bus": "NVMe", "media": "SSD", "size": 1e12}]}
        t, rows, note = details("cpu", {"cpu_pct": 10, "cpu_temp": None}, {}, hw, "pl")
        self.assertEqual(t, "Procesor (CPU)")
        self.assertIn(("", "i5-12400F"), rows)
        self.assertIn("LibreHardwareMonitor", note)
        t, rows, _n = details("nvme", {}, {}, hw, "en")
        self.assertIn(("", "Samsung SSD 980 1TB"), rows)
        t, rows, note = details("psu", {}, {}, hw, "pl")
        self.assertIn("nieznany", note)

    def test_the_map_has_no_scroll_and_pauses_when_hidden(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "ui", "components", "pc_map.py"), encoding="utf-8").read()
        self.assertNotIn("Scrollbar", src)          # opens at the top, always
        self.assertIn("winfo_ismapped", src)        # nothing drawn while hidden
        self.assertNotIn("after(120", src)          # no 120 ms redraw loop


if __name__ == "__main__":
    unittest.main()
