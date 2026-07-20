"""tests.test_sidebar
Guards for the 2026-07 sidebar restructure:
  - merged FANS Hardware+Usage tab, removed My PC Health/Efficiency,
    added My PC Components, removed Statistics, re-pointed Optimization
    to its three real destinations.
Uses a real Tk instance to click-simulate EVERY nav item and verifies each
emitted (page_id, subpage_id) resolves in main_window_expanded's routing
tables, and that every routing target has a builder branch. Skips cleanly
where no display is available.
"""
import os
import re
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAIN = os.path.join(_ROOT, "ui", "windows", "main_window_expanded.py")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _routing_tables():
    """Parse direct_pages + page_map dict literals from the main window."""
    src = _read(_MAIN)
    tables = {}
    for name in ("direct_pages", "page_map"):
        m = re.search(name + r"\s*=\s*\{(.*?)\}", src, re.S)
        entries = dict(re.findall(r'"([^"]+)":\s*("[^"]*"|None)', m.group(1)))
        tables[name] = {k: (v.strip('"') if v != "None" else None)
                        for k, v in entries.items()}
    return tables, src


class TestSidebarStructure(unittest.TestCase):
    """The nav tree matches the restructure spec exactly."""

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        from ui.components.sidebar_nav import SidebarNav
        cls.clicks = []
        cls.nav = SidebarNav(cls.root, on_navigate=lambda p, s: cls.clicks.append((p, s)))
        cls.structure = cls.nav._nav_structure()
        cls.by_id = {i["id"]: i for i in cls.structure}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_top_level_ids(self):
        self.assertEqual(
            [i["id"] for i in self.structure],
            ["dashboard", "monitoring_alerts", "my_pc", "first_setup",
             "fan_control", "optimization"],
            "top-level nav should have exactly these 6 entries (no Statistics)")

    def test_removed_entries_are_gone(self):
        all_subs = {s for i in self.structure if i["subitems"]
                    for s, _ in i["subitems"]}
        for gone in ("efficiency", "health", "fans_hardware",
                     "usage_statistics", "stats_today", "wizard"):
            self.assertNotIn(gone, all_subs, f"'{gone}' should be removed")

    def test_new_entries_exist(self):
        subs = {i["id"]: [s for s, _ in i["subitems"]]
                for i in self.structure if i["subitems"]}
        self.assertEqual(subs["my_pc"], ["central", "components", "sensors"])
        self.assertEqual(subs["fan_control"], ["fan_dashboard", "hw_usage"])
        self.assertEqual(subs["optimization"],
                         ["center", "startup_mgr", "services_mgr"])

    def test_every_click_routes_somewhere(self):
        """Click-simulate every item + subitem; each emitted id must resolve
        in direct_pages or page_map."""
        tables, _ = _routing_tables()
        known = set(tables["direct_pages"]) | set(tables["page_map"])
        type(self).clicks = self.clicks = []
        for item in self.structure:
            if item["subitems"]:
                for sub_id, _lbl in item["subitems"]:
                    self.nav._handle_subitem_click(f"{item['id']}.{sub_id}")
            else:
                self.nav._handle_item_click(item["id"])
        self.assertGreaterEqual(len(self.clicks), 13)
        unresolved = []
        for page_id, sub in self.clicks:
            full = f"{page_id}.{sub}" if sub else page_id
            if full not in known and page_id not in known:
                unresolved.append(full)
        self.assertEqual(unresolved, [],
                         f"nav clicks with no routing entry: {unresolved}")

    def test_labels_resolve_in_both_languages(self):
        from utils.i18n import set_lang
        for lang in ("pl", "en"):
            set_lang(lang)
            for item in self.nav._nav_structure():
                self.assertTrue(item["label"].strip(),
                                f"empty label for {item['id']} [{lang}]")
                self.assertFalse(item["label"].startswith("nav."),
                                 f"raw key leaked: {item['label']} [{lang}]")
                for _sid, lbl in (item["subitems"] or []):
                    self.assertTrue(lbl.strip())
                    self.assertFalse(lbl.startswith("nav."),
                                     f"raw key leaked: {lbl} [{lang}]")
        set_lang("en")


class TestRoutingIntegrity(unittest.TestCase):

    def test_every_direct_target_has_a_builder_branch(self):
        tables, src = _routing_tables()
        targets = {v for v in tables["direct_pages"].values() if v}
        for tgt in targets:
            self.assertTrue(
                re.search(rf'page_id == "{tgt}"', src) or tgt == "dashboard",
                f"direct page target '{tgt}' has no _switch_to_page branch")

    def test_restructure_routing_entries(self):
        tables, src = _routing_tables()
        dp, pm = tables["direct_pages"], tables["page_map"]
        # merged fans page + legacy ids kept working
        self.assertEqual(dp.get("fan_control.hw_usage"), "fans_hw_usage")
        self.assertEqual(dp.get("fan_control.fans_hardware"), "fans_hw_usage")
        self.assertEqual(dp.get("fan_control.usage_statistics"), "fans_hw_usage")
        # optimization triple
        self.assertEqual(dp.get("optimization.center"), "optimization")
        self.assertEqual(dp.get("optimization.startup_mgr"), "startup_manager")
        self.assertEqual(dp.get("optimization.services_mgr"), "services_manager")
        # my_pc: components deep-link present, removed ids gone
        self.assertEqual(pm.get("my_pc.components"), "your_pc")
        self.assertNotIn("my_pc.efficiency", pm)
        self.assertNotIn("my_pc.health", pm)
        self.assertNotIn("statistics", pm)
        self.assertIn("_yourpc_initial_tab", src,
                      "components deep-link missing")

    def test_merged_view_exists_and_uses_both_builders(self):
        src = _read(_MAIN)
        m = re.search(r"def _build_fans_hw_usage_view\(.*?\n(    def |\Z)",
                      src, re.S)
        self.assertIsNotNone(m, "_build_fans_hw_usage_view missing")
        body = m.group(0)
        self.assertIn("create_fans_hardware_page", body)
        self.assertIn("create_fans_usage_stats_page", body)


if __name__ == "__main__":
    unittest.main()
