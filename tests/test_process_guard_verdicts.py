# tests/test_process_guard_verdicts.py
"""
Ratchet for the verdict boundary in the mini-AV.

The bug this pins: a process library note saying "heavy or bloatware-class"
(`lib_caution`) was escalating the SECURITY verdict, so spoolsv.exe (Print
Spooler) and dllhost.exe (COM Surrogate) came back as "caution" even with a
valid Microsoft signature and the correct System32 path. Promotion to trusted
only ran while the verdict was still "unknown", so the signature could never
undo it. A scanner that flags the Print Spooler is a scanner people mute.

Advisory codes must never be the sole cause of a security verdict, and none of
this may weaken masquerade, typosquat or miner detection.
"""
import unittest

from core.process_guard import ProcessGuard, _SECURITY_NEGATIVE


class VerdictBoundaryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.g = ProcessGuard()

    def _verdict(self, name, exe, deep=False):
        return self.g.analyze(name, exe=exe, deep=deep)

    def test_advisory_codes_are_not_security_negative(self):
        for code in ("lib_caution", "lib_safe", "system_ok", "signed_ms",
                     "signed_ok", "whitelist", "unknown", "kernel"):
            self.assertNotIn(code, _SECURITY_NEGATIVE,
                             f"{code} is advisory and must not drive a verdict")

    def test_real_security_codes_are_listed(self):
        for code in ("masquerade", "typosquat", "malware_name", "risky_path",
                     "bad_signature", "expected_signed", "publisher_mismatch"):
            self.assertIn(code, _SECURITY_NEGATIVE)

    def test_masquerade_still_caught(self):
        f = self._verdict("svchost.exe", r"C:\Users\x\AppData\Local\Temp\svchost.exe")
        self.assertEqual(f.verdict, "danger")
        self.assertGreaterEqual(f.score, 85)

    def test_homoglyph_still_caught(self):
        f = self._verdict("svch0st.exe", r"C:\Windows\System32\svch0st.exe")
        self.assertIn(f.verdict, ("suspicious", "danger"))

    def test_miner_name_still_caught(self):
        f = self._verdict("xmrig.exe", r"C:\Users\x\Downloads\xmrig.exe")
        self.assertEqual(f.verdict, "danger")

    def test_risky_path_still_caught(self):
        f = self._verdict("someapp.exe", r"C:\Users\x\AppData\Local\Temp\someapp.exe")
        self.assertNotEqual(f.verdict, "trusted")


if __name__ == "__main__":
    unittest.main()
