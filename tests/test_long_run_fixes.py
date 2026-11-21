"""tests.test_long_run_fixes - what the first long test run found (2026-11-16).

Six hours of real use with hck_GPT journals switched on showed:
  - the chat froze the window (18 s security scan, 4 s Ollama probe on every
    question it did not recognise);
  - [-> links] on the first line of a message were never clickable;
  - the summary averaged hour rows and minute rows as equals (40 minutes of
    gaming outweighed four hours) and counted seconds as minutes;
  - temperature summaries still used the old 35 + load/2 CPU placeholder;
  - answers claimed nothing leaves the PC while telemetry is on by default;
  - "CPU back to normal - now 75%", "boost 2500 MHz" on an i5-12400F,
    "nice" answered with the temperatures again.
"""
import os
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestChatDoesNotFreezeTheWindow(unittest.TestCase):

    def test_answer_is_worked_out_on_a_thread(self):
        src = _read("hck_gpt", "panel.py")
        send = src[src.index("    def _send(self):"):src.index("    def _deliver(")]
        self.assertIn('name="hck_gpt-answer"', send)
        # the only process_message call in _send is inside the worker
        self.assertEqual(send.count("process_message("), 1)
        # 2026-11-21: the worker takes the handler and plain values, not the panel
        self.assertIn("def _work(h=self.chat_handler", send)

    def test_ollama_probe_never_blocks_an_answer(self):
        import importlib
        he = importlib.import_module("hck_gpt.engine.hybrid_engine")
        self.assertEqual(he.OLLAMA_HOST, "127.0.0.1")
        self.assertLessEqual(he.PROBE_TIMEOUT, 0.5)
        eng = he.HybridEngine()

        class Slow:
            def is_available(self):
                time.sleep(2)
                return False
        eng._ollama = Slow()
        eng._available = None
        t = time.time()
        self.assertFalse(eng._check_available())
        self.assertLess(time.time() - t, 0.2, "the answer waited for the probe")


class TestLinksOnTheFirstLine(unittest.TestCase):

    def test_scan_starts_where_the_text_lands(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError:
            raise unittest.SkipTest("no display")
        try:
            t = tk.Text(root)
            t.insert("end", "earlier message\n")
            start = t.index("end - 1c")       # what add_message uses now
            t.insert("end", "KROK 3/5 [-> Services Manager]\n")
            self.assertTrue(t.search("[-> ", start, stopindex="end"))
        finally:
            root.destroy()
        src = _read("hck_gpt", "panel.py")
        self.assertNotIn('start_pos = self.log.index("end")\n', src)


class TestSummaryIsWeighted(unittest.TestCase):
    """Three quiet hours at 10 % and 40 busy minutes at 90 %."""

    def setUp(self):
        from hck_stats_engine.db_manager import db_manager
        self.conn = db_manager.get_connection()
        now = time.time()
        self.hours = [int((now - k * 3600) // 3600) * 3600 for k in (5, 4, 3)]
        for h in self.hours:
            self.conn.execute("""INSERT OR REPLACE INTO hourly_stats
                (timestamp, cpu_avg, cpu_min, cpu_max, cpu_p95, ram_avg, ram_min,
                 ram_max, gpu_avg, gpu_min, gpu_max, cpu_temp_avg, sample_count)
                VALUES (?,10,5,20,15,50,45,55,5,0,10,40,3600)""", (h,))
        self.mins = [int(now // 60) * 60 - k * 60 for k in range(1, 41)]
        for m in self.mins:
            self.conn.execute("""INSERT OR REPLACE INTO minute_stats
                (timestamp, cpu_avg, cpu_min, cpu_max, ram_avg, ram_min, ram_max,
                 gpu_avg, gpu_min, gpu_max, cpu_temp, gpu_temp, sample_count)
                VALUES (?,90,85,95,50,45,55,5,0,10,80,NULL,60)""", (m,))
        self.conn.commit()

    def tearDown(self):
        self.conn.execute("DELETE FROM hourly_stats WHERE timestamp IN (%s)"
                          % ",".join("?" * len(self.hours)), self.hours)
        self.conn.execute("DELETE FROM minute_stats WHERE timestamp IN (%s)"
                          % ",".join("?" * len(self.mins)), self.mins)
        self.conn.commit()

    def test_average_and_recorded_time(self):
        from hck_stats_engine.query_api import query_api
        # 14 days reads hourly rows plus the newest minutes (1 day would
        # read minutes only, and real hours always have their minutes)
        s = query_api.get_summary_stats(days=14)
        # 3 h at 10 % + 40 min at 90 %  ->  (180*10 + 40*90) / 220 = 24.5 %
        # (the old row-count average said (3*10 + 40*90) / 43 = 84 %)
        self.assertAlmostEqual(s["cpu_avg"], 24.5, delta=1.0)
        self.assertAlmostEqual(s["total_uptime_hours"], 3.7, delta=0.1)
        # one calendar day, or two when the test runs between midnight and
        # about 5 am: the hours are 3-5 h old (failed at 01:27, 2026-11-20)
        import datetime as _dt
        days = {_dt.date.fromtimestamp(ts) for ts in self.hours + self.mins}
        self.assertEqual(s["days_with_data"], len(days))

    def test_placeholder_cpu_temperature_is_not_reported(self):
        """40 + 0.5*10 = 45 is not the hourly value (40 is), so the hours
        stay; minute rows hold 80 = 35 + 90/2, the placeholder, and go."""
        from hck_stats_engine.query_api import query_api
        t = query_api.get_temperature_history(minutes=60)
        self.assertIsNone(t.get("cpu_current"))


class TestHonestAnswers(unittest.TestCase):

    def test_no_claim_that_nothing_leaves_the_pc(self):
        src = _read("hck_gpt", "responses", "r_assistant.py")
        for claim in ("nic nie idzie do chmury", "nothing in the cloud",
                      "Nigdy nie wysyłam Twoich danych bez zgody",
                      "never send your data anywhere without consent",
                      "Zero chmury"):
            self.assertNotIn(claim, src)
        self.assertNotIn("100% offline - nothing is transmitted",
                         _read("ui", "windows", "main_window_expanded.py"))

    def test_privacy_answer_states_the_real_telemetry_setting(self):
        from hck_gpt.responses.r_assistant import AssistantResponses  # noqa
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        out = "\n".join(response_builder.build(
            ParseResult(intent="privacy_data", confidence=1.0), "pl"))
        self.assertIn("telemetria", out)
        self.assertIn("[-> Settings]", out)

    def test_recovery_note_needs_a_real_drop(self):
        from hck_gpt.memory import proactive_monitor as pm
        self.assertEqual(pm.CPU_CALM_PCT, 50.0)
        src = _read("hck_gpt", "memory", "proactive_monitor.py")
        block = src[src.index("if self._was_cpu_high and cpu < CPU_CALM_PCT"):]
        block = block[:block.index("elif cpu >= CPU_HIGH_PCT")]
        self.assertNotIn("count_budget=False", block)

    def test_locked_multiplier(self):
        from hck_gpt.responses.r_hardware import HardwareResponses as H
        self.assertTrue(H._multiplier_locked("12th Gen Intel(R) Core(TM) i5-12400F"))
        self.assertFalse(H._multiplier_locked("Intel Core i5-12600K"))
        self.assertFalse(H._multiplier_locked("AMD Ryzen 7 5800X3D"))
        self.assertIsNone(H._multiplier_locked("Unknown CPU"))

    def test_proactive_language_is_not_set_by_one_message(self):
        src = _read("hck_gpt", "chat_handler.py")
        self.assertNotIn("proactive_monitor.set_language(lang)", src)


class TestReactionsDoNotRepeatTheTopic(unittest.TestCase):

    def test_nice_after_temperatures(self):
        from hck_gpt.chat_handler import ChatHandler
        h = ChatHandler()
        first = h.process_message("jak moje temperatury?", ui_lang="pl")
        again = h.process_message("nice", ui_lang="pl")
        self.assertNotEqual(first[0][:40], again[0][:40])


if __name__ == "__main__":
    unittest.main()
