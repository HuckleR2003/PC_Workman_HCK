# tests/test_opt_receipts.py
"""
Pins the receipt contract.

The bug this ratchets: the AFTER callback used to find its own entry by
"timestamp within 0.5 s", so two receipts opened in the same instant could be
matched to each other and one action's numbers were written onto another
action's receipt. Receipts exist to be trustworthy proof; one that reports
someone else's result is worse than none.
"""
import time
import unittest

from core import opt_receipts as r


class ReceiptTests(unittest.TestCase):

    def setUp(self):
        with open(r._store_path(), "w", encoding="utf-8") as f:
            f.write("[]")

    def test_each_receipt_keeps_its_own_detail(self):
        r.record("A", delay=1, detail="7 services stopped")
        r.record("B", delay=1, detail=lambda: "12 processes suspended")
        time.sleep(2.5)
        got = {e["action"]: e.get("detail") for e in r.get_receipts()}
        self.assertEqual(got.get("A"), "7 services stopped")
        self.assertEqual(got.get("B"), "12 processes suspended")

    def test_every_receipt_has_a_unique_id(self):
        for i in range(5):
            r.record(f"act{i}", delay=60)
        ids = [e.get("id") for e in r.get_receipts()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(ids))

    def test_before_is_captured_immediately(self):
        r.record("now", delay=60)
        e = r.get_receipts()[0]
        self.assertIsNotNone(e.get("before"))
        self.assertIsNone(e.get("after"))

    def test_callable_detail_is_evaluated_at_after_time(self):
        box = {"n": 0}

        def counter():
            box["n"] += 1
            return f"{box['n']} things"

        r.record("late", delay=1, detail=counter)
        self.assertIsNone(r.get_receipts()[0].get("detail"))   # not yet run
        time.sleep(2.0)
        self.assertEqual(r.get_receipts()[0].get("detail"), "1 things")

    def test_a_broken_detail_callable_never_breaks_the_receipt(self):
        r.record("boom", delay=1, detail=lambda: 1 / 0)
        time.sleep(2.0)
        e = r.get_receipts()[0]
        self.assertIsNotNone(e.get("after"))

    def test_record_never_raises(self):
        r.record(None)              # type: ignore[arg-type]
        r.record("x", delay="bad")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
