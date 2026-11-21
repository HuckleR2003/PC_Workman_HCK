"""tests.test_telemetry_session
Telemetry reports the real session length (2026-11-15).

The only report used to go out 2 seconds after launch, so every session_min
on the server was 0. A session now reports "start", an hourly "heartbeat"
and an "end" on exit. These tests run the real client against a local HTTP
server and read what actually arrives. Nothing leaves the machine, and the
real settings/network.json is never touched.
"""
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock


class _Sink(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        _Sink.received.append(json.loads(self.rfile.read(n)))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):            # keep the test output clean
        pass


class _FakeDetector:
    def ensure_data(self):
        pass

    def get_data(self):
        return {"cpu": {"name": "Test CPU", "cores_physical": 6},
                "gpu": {"name": "Test GPU"},
                "ram": {"total_gb": 8, "speed_mhz": 2133},
                "motherboard": {"manufacturer": "Board", "product": "X"},
                "storage": {"drives": []}}


class TestTelemetrySession(unittest.TestCase):

    def setUp(self):
        import core.network as network
        import core.telemetry as telemetry
        self.net, self.tel = network, telemetry

        self.server = HTTPServer(("127.0.0.1", 0), _Sink)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        _Sink.received = []

        tmp = tempfile.mkdtemp(prefix="pcw_test_net_")
        cfg = os.path.join(tmp, "network.json")
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"network_allowed": True, "telemetry_enabled": True,
                       "install_id": "test-install"}, f)
        self.patches = [
            mock.patch.object(network, "_path", lambda: cfg),
            mock.patch.object(telemetry, "ENDPOINT",
                              f"http://127.0.0.1:{self.server.server_port}"),
            mock.patch("core.hardware_detector.get_hardware_detector",
                       lambda: _FakeDetector()),
            mock.patch.object(telemetry, "_reporter",
                              {"thread": None, "stop": threading.Event(),
                               "version": ""}),
            mock.patch("atexit.register"),     # no real exit hook in tests
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        self.tel._reporter["stop"].set()
        for p in reversed(self.patches):
            p.stop()
        self.server.shutdown()
        self.server.server_close()

    def _wait_for(self, n, timeout=5.0):
        end = time.time() + timeout
        while time.time() < end and len(_Sink.received) < n:
            time.sleep(0.02)
        return list(_Sink.received)

    def test_start_then_heartbeats_with_growing_session(self):
        # pretend the app has been open for 90 minutes already
        with mock.patch.object(self.tel, "_session_start", time.time() - 5400):
            self.tel.start_reporting("9.9.9", first_delay_s=0.0,
                                     heartbeat_s=0.2)
            got = self._wait_for(3)
        self.assertGreaterEqual(len(got), 3)
        self.assertEqual(got[0]["kind"], "start")
        self.assertEqual(got[1]["kind"], "heartbeat")
        self.assertGreaterEqual(got[1]["session_min"], 90,
                                "session length is not the real one")
        self.assertEqual(len({g["session_id"] for g in got}), 1,
                         "one session must keep one session_id")
        self.assertEqual(got[0]["app_version"], "9.9.9")
        self.assertEqual(got[0]["cpu"], "Test CPU")

    def test_end_report_carries_the_real_length(self):
        with mock.patch.object(self.tel, "_session_start", time.time() - 1500):
            self.tel._reporter["version"] = "9.9.9"
            t0 = time.time()
            self.tel._send_end()
            took = time.time() - t0
        got = self._wait_for(1)
        self.assertEqual([g["kind"] for g in got], ["end"])
        self.assertEqual(got[0]["session_min"], 25)
        self.assertLess(took, self.tel.END_TIMEOUT_S + 1,
                        "closing the app waited on the network")

    def test_a_few_seconds_run_sends_no_end(self):
        with mock.patch.object(self.tel, "_session_start", time.time() - 5):
            self.tel._send_end()
        time.sleep(0.3)
        self.assertEqual(_Sink.received, [])

    def test_nothing_is_sent_when_telemetry_is_off(self):
        with mock.patch.object(self.net, "telemetry_enabled", lambda: False):
            self.assertFalse(self.tel.send("9.9.9", "start"))
        time.sleep(0.3)
        self.assertEqual(_Sink.received, [])

    def test_unreachable_server_never_blocks_long(self):
        with mock.patch.object(self.tel, "ENDPOINT", "http://127.0.0.1:9"):
            t0 = time.time()
            ok = self.tel.send("9.9.9", "end", timeout=1.0)
        self.assertFalse(ok)
        self.assertLess(time.time() - t0, 3)

    def test_payload_has_only_the_documented_fields(self):
        p = self.tel.build_payload("9.9.9", "start")
        self.assertEqual(set(p), {
            "install_id", "app_version", "ts", "kind", "session_id",
            "session_min", "os", "country", "cpu", "cpu_cores", "gpu",
            "ram_gb", "ram_mhz", "disks", "motherboard", "screens"})

    def test_screens_are_sizes_only(self):
        """Real call on this machine: at least one monitor, primary first,
        and nothing but the five documented keys (no names, no serials)."""
        screens = self.tel._screens()
        self.assertGreaterEqual(len(screens), 1)
        self.assertLessEqual(len(screens), self.tel.MAX_SCREENS)
        self.assertTrue(screens[0]["primary"])
        for s in screens:
            self.assertEqual(set(s), {"w", "h", "hz", "scale", "primary"})
            self.assertGreater(s["w"], 0)
            self.assertGreater(s["h"], 0)
            self.assertGreaterEqual(s["scale"], 100)

    def test_screens_failure_sends_an_empty_list(self):
        import ctypes
        with mock.patch.object(ctypes, "WinDLL", side_effect=OSError("no user32")):
            self.assertEqual(self.tel._screens(), [])

    def test_worker_keeps_the_new_fields(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "cloudflare", "telemetry-worker.js"),
                  encoding="utf-8") as f:
            worker = f.read()
        allowed = worker[worker.index("const ALLOWED"):worker.index("];")]
        for field in self.tel.build_payload("9.9.9"):
            self.assertIn(f'"{field}"', allowed,
                          f"the Worker would drop {field}")


class TestStartupUsesSessionReporting(unittest.TestCase):

    def test_startup_no_longer_sends_once_after_two_seconds(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "startup.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("start_reporting", src)
        self.assertNotIn("_telemetry_once", src)


if __name__ == "__main__":
    unittest.main()
