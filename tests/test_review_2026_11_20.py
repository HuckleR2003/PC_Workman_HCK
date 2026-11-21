"""Review pass after phase 8 (2026-11-20).

  * the optimization guide's summary reads Startup again: entries the user
    turned off on step 2 are no longer named as "left";
  * Store builds: HKCU writes are virtualized unless the manifest says
    otherwise; the Startup Manager sends such users to Task Manager;
  * hck_GPT's network guide: the routing of internet questions, the verdicts
    of the quick test, the report with its yellow source band;
  * Esc: closes the hck_GPT panel, then goes to the Dashboard.
No test here goes out to the network: the measurements are replaced.
"""
import os
import tempfile
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestOptimizeSummary(unittest.TestCase):

    def test_disabled_entries_are_not_named_as_left(self):
        from hck_gpt.engine.flow_engine import FlowEngine
        import hck_gpt.responses.flows as flows
        eng = FlowEngine()
        for fid, f in __import__("hck_gpt.engine.flow_engine", fromlist=["x"]).flow_engine._flows.items():
            eng.register(f)
        four = [{"name": f"App{i}", "impact": "high"} for i in range(4)]
        two = four[2:]
        calls = iter([(four, 19), (two, 19)])
        seq = [{"ram_pct": 82.0, "cpu_pct": 30.0, "procs": 240},
               {"ram_pct": 80.0, "cpu_pct": 25.0, "procs": 238},
               {"ram_pct": 70.0, "cpu_pct": 20.0, "procs": 231}]
        fake = mock.MagicMock()
        fake.flush_now.return_value = (True, "ok", 1000, 1200)
        with mock.patch.object(flows, "_measure", side_effect=seq), \
             mock.patch.object(flows, "_startup_flagged", side_effect=lambda: next(calls)), \
             mock.patch.object(flows, "_running_unneeded", return_value=[]), \
             mock.patch.dict("sys.modules", {"core.auto_optimizer": mock.MagicMock(auto_optimizer=fake)}):
            eng.start("optimize", None, "pl")
            eng.process_input("dalej", None)      # startup: App0..App3
            eng.process_input("dalej", None)      # services
            eng.process_input("dalej", None)      # memory
            out = " ".join(eng.process_input("tak", None))
        self.assertIn("Wyłączone z autostartu: App0, App1", out)
        left = out.split("Na stałe zostało:")[1] if "Na stałe zostało:" in out else ""
        self.assertIn("App2", left)
        self.assertNotIn("App0", left)


class TestInstallKind(unittest.TestCase):

    def _manifest(self, body):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "AppxManifest.xml")
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        return p

    def test_virtualized_unless_the_manifest_turns_it_off(self):
        from utils.install_kind import registry_virtualized
        old = self._manifest("<Package><Properties></Properties></Package>")
        new = self._manifest("<Package><Properties><desktop6:RegistryWriteVirtualization>disabled"
                             "</desktop6:RegistryWriteVirtualization></Properties></Package>")
        self.assertTrue(registry_virtualized(old, store=True))
        self.assertFalse(registry_virtualized(new, store=True))
        self.assertFalse(registry_virtualized(old, store=False))

    def test_next_package_manifest_turns_it_off(self):
        p = os.path.join(ROOT, "dist", "msix", "AppxManifest.xml")
        if not os.path.exists(p):
            self.skipTest("no MSIX folder")
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("<desktop6:RegistryWriteVirtualization>disabled", txt)
        self.assertIn('Name="unvirtualizedResources"', txt)
        self.assertIn('MinVersion="10.0.18362.0"', txt)

    def test_store_users_are_sent_to_task_manager_not_to_run_as_admin(self):
        from ui.pages import startup_manager as sm
        with mock.patch("utils.install_kind.registry_virtualized", return_value=True):
            self.assertTrue(sm._store_blocked({"name": "OneDrive", "hive": "HKCU"}))
            self.assertFalse(sm._store_blocked({"name": "x", "_task": True}))
        with mock.patch("utils.install_kind.registry_virtualized", return_value=False):
            self.assertFalse(sm._store_blocked({"name": "OneDrive", "hive": "HKCU"}))


class TestNetworkRouting(unittest.TestCase):

    CASES = {
        "network_check": ["sprawdź internet", "czy mam internet?", "jaki mam ping", "check my internet",
                          "is my wifi ok", "test połączenia", "czy mój internet jest stabilny",
                          "laguje mi w grach online", "gubi pakiety", "sprawdź wifi", "jakość internetu",
                          "zdiagnozuj sieć", "what's my ping", "sprawdź mi połączenie z internetem"],
        "network_down": ["nie mam internetu", "internet mi nie działa", "strony się nie ładują",
                         "youtube długo się ładuje", "no internet", "brak dostępu do internetu",
                         "ograniczona łączność", "pages won't load", "router nie działa"],
        "network_speed": ["zmierz prędkość internetu", "jak szybki jest mój internet", "speed test",
                          "ile mam mega", "internet speed", "test prędkości"],
        "network_dns": ["wyczyść dns", "flush dns", "dns nie działa"],
        "network_slow": ["wolny internet", "internet muli"],
    }

    def test_internet_questions_reach_the_guide(self):
        from hck_gpt.intents.insight_rules import route_insight
        for intent, qs in self.CASES.items():
            for q in qs:
                self.assertEqual(route_insight(q), intent, q)

    def test_other_questions_stay_where_they_were(self):
        from hck_gpt.intents.insight_rules import route_insight
        for q in ("ile ramu mam", "sprawdź temperaturę", "test stabilności", "netflix się tnie"):
            self.assertNotIn(str(route_insight(q)), self.CASES, q)

    def test_builder_answers_every_network_intent(self):
        from hck_gpt.responses.builder import ResponseBuilder
        for intent in self.CASES:
            self.assertTrue(hasattr(ResponseBuilder, f"_resp_{intent}"), intent)
        # the old checklist answers are overridden by the guide
        from hck_gpt.responses.r_network import NetworkResponses
        self.assertIs(ResponseBuilder._resp_network_slow, NetworkResponses._resp_network_slow)
        self.assertIs(ResponseBuilder._resp_network_drop, NetworkResponses._resp_network_drop)


def _res(**kw):
    r = {"ts": time.time(), "target": "google.com", "adapter": {"kind": "wifi", "name": "Wi-Fi", "speed_mbps": 300},
         "gateway": "192.168.1.1",
         "gw": {"sent": 3, "lost": 0, "avg": 2.0, "min": 1.0, "max": 3.0, "jitter": 1.0},
         "dns_ip": "142.250.0.1", "dns_ms": 30.0,
         "web": {"sent": 4, "lost": 0, "avg": 20.0, "min": 15.0, "max": 25.0, "jitter": 3.0},
         "raw": {"sent": 2, "lost": 0, "avg": 18.0, "min": 17.0, "max": 19.0, "jitter": 1.0},
         "tcp_ms": 25.0}
    r.update(kw)
    return r


_DEAD = {"sent": 4, "lost": 4, "avg": None, "min": None, "max": None, "jitter": None}


class TestNetVerdicts(unittest.TestCase):

    def test_verdicts(self):
        from core.net_check import verdict
        self.assertEqual(verdict(_res()), ("ok", "good"))
        self.assertEqual(verdict(_res(gateway=None, gw=None, web=None, raw=_DEAD, tcp_ms=None, dns_ip=None))[1],
                         "no_network")
        self.assertEqual(verdict(_res(gw=_DEAD, web=None, raw=_DEAD, tcp_ms=None, dns_ip=None))[1], "no_router")
        self.assertEqual(verdict(_res(web=_DEAD, raw=_DEAD, tcp_ms=None))[1], "no_internet")
        self.assertEqual(verdict(_res(dns_ip=None, web=None, tcp_ms=None))[1], "dns")
        self.assertEqual(verdict(_res(web=dict(_res()["web"], avg=140.0)))[1], "high_ping")
        self.assertEqual(verdict(_res(web=dict(_res()["web"], lost=1)))[1], "loss")
        self.assertEqual(verdict(_res(gw=dict(_res()["gw"], avg=45.0)))[1], "slow_local")
        self.assertEqual(verdict(_res(web=dict(_res()["web"], jitter=40.0)))[1], "jitter")

    def test_report_names_its_source_on_a_yellow_band(self):
        from hck_gpt.responses.r_network import report
        out = report(_res(), "pl")
        self.assertTrue(out[0].startswith("§SRC Ocena według testu połączenia z google.com"))
        self.assertTrue(any(x.startswith("§OK ") for x in out))
        bad = report(_res(web=_DEAD, raw=_DEAD, tcp_ms=None), "en")
        self.assertTrue(any("past the router" in x for x in bad))

    def test_panel_draws_the_yellow_band(self):
        with open(os.path.join(ROOT, "hck_gpt", "panel.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('("§SRC ", "source_note")', src)
        self.assertIn('"source_note", background="#facc15"', src)


class TestNetworkGuide(unittest.TestCase):

    def _engine(self):
        from hck_gpt.engine.flow_engine import FlowEngine, flow_engine
        import hck_gpt.responses.r_network  # noqa: F401  (registers the flow)
        eng = FlowEngine()
        eng.register(flow_engine._flows["network"])
        return eng

    def test_speed_test_runs_only_after_yes(self):
        from core import net_check
        eng = self._engine()
        st = mock.MagicMock(return_value={"ok": True, "mbps": 87.0, "bytes": 25e6, "secs": 2.3})
        with mock.patch.object(net_check, "check", return_value=_res()), \
             mock.patch.object(net_check, "speed_test", st), \
             mock.patch("hck_gpt.responses.r_network._traffic_mbps", return_value=(0.1, 0.1)):
            first = eng.start("network", None, "pl", {"mode": "check"})
            self.assertFalse(st.called)
            self.assertEqual(eng.current_chips()[0][0], "TAK, ZMIERZ")
            out = eng.process_input("tak", None)
        self.assertTrue(st.called)
        self.assertTrue(any("87 Mb/s" in x for x in out))
        self.assertTrue(any("§SRC" in x for x in first))

    def test_no_internet_offers_a_retest_not_a_speed_test(self):
        from core import net_check
        eng = self._engine()
        dead = _res(web=_DEAD, raw=_DEAD, tcp_ms=None)
        st = mock.MagicMock()
        with mock.patch.object(net_check, "check", side_effect=[dead, _res()]), \
             mock.patch.object(net_check, "speed_test", st):
            eng.start("network", None, "pl", {"mode": "down"})
            self.assertEqual(eng.current_chips()[0][0], "TAK, SPRAWDŹ PONOWNIE")
            out = eng.process_input("tak", None)
        self.assertFalse(st.called)
        self.assertTrue(any("Przed → po" in x for x in out) or any("§OK" in x for x in out))
        self.assertFalse(eng.is_active())

    def test_dns_fault_offers_the_flush_and_runs_it_only_on_yes(self):
        from core import net_check
        eng = self._engine()
        flush = mock.MagicMock(return_value=True)
        with mock.patch.object(net_check, "check", return_value=_res(dns_ip=None, web=None, tcp_ms=None)), \
             mock.patch("core.cleanup.flush_dns", flush):
            eng.start("network", None, "pl", {"mode": "dns"})
            out = eng.process_input("pomiń", None)          # no speed test
            self.assertTrue(any("Wyczyścić teraz pamięć DNS" in x for x in out))
            self.assertFalse(flush.called)
            eng.process_input("tak", None)
        self.assertTrue(flush.called)


class TestEscape(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            tk.Tk().destroy()
        except tk.TclError:
            raise unittest.SkipTest("no display available")
        import ui.windows.main_window_expanded as mwe
        from _isolate import isolate_window_state
        isolate_window_state()
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

    def _pump(self, s=0.6):
        end = time.time() + s
        while time.time() < end:
            self.win.root.update()

    def test_esc_closes_the_panel_first_then_goes_home(self):
        w = self.win
        w.current_view = None
        w._switch_to_page("cleanup")
        self._pump()
        panel = getattr(w, "gpt_panel", None)
        if panel is not None:
            panel.is_open = True
            panel.animating = False
            with mock.patch.object(panel, "close") as close:
                w._on_escape()
                close.assert_called_once()
            self.assertEqual(w.current_view, "cleanup", "the first Esc only closes the panel")
            panel.is_open = False
        w.root.focus_set()
        w._on_escape()
        self._pump()
        self.assertEqual(w.current_view, "dashboard")
        self.assertEqual(w._on_escape(), "break")   # on the Dashboard: nothing

    def test_links_open_the_right_page_and_mark_the_sidebar(self):
        w = self.win
        w.open_page_from_link("my_pc")
        self._pump()
        self.assertEqual(w.current_view, "your_pc", "my_pc is the sidebar's id")
        w.open_page_from_link("statistics")
        self._pump()
        self.assertEqual(w.current_view, "monitoring_alerts", "no empty statistics page")
        w.open_page_from_link("cleanup")
        self._pump()
        self.assertEqual(w.current_view, "cleanup")
        self.assertEqual(w.sidebar.active_item, "cleanup")
        w.open_page_from_link("my_pc")
        self._pump()
        self.assertEqual(w.sidebar.active_item, "my_pc")

    def test_esc_in_a_field_only_leaves_the_field(self):
        import tkinter as tk
        w = self.win
        w.current_view = None
        w._switch_to_page("profile")
        self._pump()
        ent = tk.Entry(w.root)
        ent.pack()
        with mock.patch.object(w.root, "focus_get", return_value=ent):
            w._on_escape()
        self.assertEqual(w.current_view, "profile")
        ent.destroy()


if __name__ == "__main__":
    unittest.main()


class TestPageTitles(unittest.TestCase):
    """Older pages' headers follow the interface language (2026-11-21)."""

    def test_every_title_has_both_languages(self):
        from ui.components.page_titles import _TITLES
        for key, entry in _TITLES.items():
            self.assertEqual(set(entry), {"pl", "en"}, key)
            for lang in ("pl", "en"):
                self.assertEqual(len(entry[lang]), 2, key)
                # *_sub entries carry only a subtitle for a header named elsewhere
                self.assertTrue(entry[lang][1] if key.endswith("_sub") else entry[lang][0], key)

    def test_polish_names_match_the_sidebar(self):
        from unittest import mock
        from ui.components import page_titles as pt
        with mock.patch.object(pt, "_lang", return_value="pl"):
            self.assertEqual(pt.text("startup_manager"), "Menedżer Autostartu")
            self.assertEqual(pt.text("services_inner"), "Menedżer Usług")
            self.assertEqual(pt.text("fan_control"), "KONTROLA WENTYLATORÓW")
            self.assertEqual(pt.title("first_setup")[0], "KONFIGURACJA I STEROWNIKI")
        with mock.patch.object(pt, "_lang", return_value="en"):
            self.assertEqual(pt.text("startup_manager"), "Startup Manager")

    def test_no_english_only_headers_left(self):
        src = {}
        for rel in ("ui/windows/main_window_expanded.py", "ui/pages/startup_manager.py",
                    "ui/pages/services_manager.py", "ui/pages/first_setup_drivers.py"):
            with open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8") as f:
                src[rel] = f.read()
        for rel, needle in (("ui/windows/main_window_expanded.py", '_build_page_header("SERVICES MANAGER"'),
                            ("ui/windows/main_window_expanded.py", '"FAN DASHBOARD", "Cooling'),
                            ("ui/pages/startup_manager.py", 'text="Startup Manager"'),
                            ("ui/pages/services_manager.py", 'text="Services Manager"'),
                            ("ui/pages/first_setup_drivers.py", 'text="  FIRST SETUP & DRIVERS"')):
            self.assertNotIn(needle, src[rel], rel)
