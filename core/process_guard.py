# core/process_guard.py
"""
Process Suspect Guard - PC Workman's intelligent mini-antivirus engine.

Goes well beyond a static name blacklist. For every running process it asks
three questions a real analyst would ask:

  1. IS IT WHO IT CLAIMS TO BE?  (author / Authenticode signature)
       A process named "svchost.exe" should be signed by Microsoft and live in
       System32. If the publisher is missing/mismatched, that is a red flag.

  2. IS THE NAME A DECOY?  (typosquatting / homoglyphs)
       Malware loves names one keystroke away from a trusted one:
       svhost.exe, shch0st.exe, ciaude.exe, chr0me.exe, rundlI32.exe.
       We homoglyph-normalise (0->o, 1->l, rn->m ...) and measure edit distance
       against critical + popular process names.

  3. IS IT WEARING A SYSTEM PROCESS'S CLOTHES?  (masquerade)
       A *real* system name (svchost/lsass/csrss...) running from %TEMP% or
       AppData instead of System32 is a classic injection trick.

Verdicts: trusted / unknown / caution / suspicious / danger  (+ 0-100 risk score)
Reasons are returned bilingually (PL/EN) so chat and UI can render either.

Signature verification uses Windows Authenticode via PowerShell, cached by
(path, size, mtime) so the slow check runs at most once per binary version.
Heuristic checks (name/path/typosquat) are instant and need no signature.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from import_core import register_component
except Exception:  # pragma: no cover - allow standalone import in tests
    def register_component(*_a, **_k):  # type: ignore
        return None

try:
    from utils.paths import APP_DIR, BUNDLE_DIR
except Exception:  # pragma: no cover
    APP_DIR = BUNDLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── Critical Windows processes: must live in a system dir AND be MS-signed ─────
# Running from anywhere else is a strong masquerade signal.
_CRITICAL_SYSTEM = {
    "svchost.exe", "lsass.exe", "csrss.exe", "services.exe", "winlogon.exe",
    "smss.exe", "wininit.exe", "dwm.exe", "conhost.exe", "taskhostw.exe",
    "spoolsv.exe", "ctfmon.exe", "runtimebroker.exe", "sihost.exe",
    "fontdrvhost.exe", "dllhost.exe", "searchindexer.exe", "audiodg.exe",
    "lsm.exe", "explorer.exe", "ntoskrnl.exe",
}

# Kernel pseudo-processes: no on-disk binary, cannot be path-checked or signed.
# They are trusted by definition (an impersonator would need a real .exe file,
# which would then fail the typosquat/path checks instead).
_KERNEL_PSEUDO = {
    "system", "registry", "memory compression", "secure system",
    "system idle process", "idle",
}

# High-value impersonation targets for typosquat detection (kept tight to avoid
# false positives on short generic names). Critical system names are added too.
_POPULAR_TARGETS = {
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe",
    "discord.exe", "steam.exe", "spotify.exe", "teams.exe", "slack.exe",
    "zoom.exe", "claude.exe", "notepad.exe", "cmd.exe", "powershell.exe",
    "rundll32.exe", "regsvr32.exe", "taskmgr.exe", "msiexec.exe",
    "onedrive.exe", "outlook.exe", "winword.exe", "excel.exe",
}

# Known malware / unwanted name fragments (coin miners, classic droppers).
_MALWARE_FRAGMENTS = {
    "xmrig", "cpuminer", "nicehash", "minerd", "claymore", "cgminer",
    "bfgminer", "ethminer", "gminer", "phoenixminer", "nbminer", "lolminer",
    "trojan", "keylog", "ransom", "cryptolock",
}

# Folders a legitimate process almost never runs a persistent binary from.
_RISKY_PATH_HINTS = ("\\temp\\", "\\tmp\\", "\\appdata\\local\\temp\\",
                     "\\downloads\\", "\\$recycle.bin\\", "\\windows\\temp\\")

# Homoglyph / leet normalisation: makes svhost, shch0st, ciaude comparable to
# their real counterparts before measuring edit distance.
_HOMOGLYPH = str.maketrans({
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s",
    "6": "g", "7": "t", "8": "b", "9": "g",
    "$": "s", "@": "a", "|": "l", "!": "i",
})


def _homoglyph_norm(name: str) -> str:
    """Lowercase, drop .exe, fold common look-alike substitutions."""
    s = (name or "").lower().strip()
    if s.endswith(".exe"):
        s = s[:-4]
    s = s.translate(_HOMOGLYPH)
    s = s.replace("rn", "m").replace("vv", "w")
    return s


def _lev(a: str, b: str, cap: int = 3) -> int:
    """Levenshtein distance with early-exit once it clearly exceeds `cap`."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > cap:
        return cap + 1
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        best = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if cur[j] < best:
                best = cur[j]
        if best > cap:
            return cap + 1
        prev = cur
    return prev[lb]


@dataclass
class Finding:
    name: str
    verdict: str = "unknown"          # trusted/unknown/caution/suspicious/danger
    score: int = 0                    # 0 (clean) .. 100 (certain threat)
    pid: Optional[int] = None
    exe: str = ""
    publisher: str = ""               # actual Authenticode signer (if checked)
    expected_vendor: str = ""         # from process library
    sig_status: str = ""              # Valid / NotSigned / NotTrusted / ...
    reasons: List[dict] = field(default_factory=list)   # [{code, pl, en, sev}]

    def add(self, code: str, pl: str, en: str, sev: int = 1) -> None:
        self.reasons.append({"code": code, "pl": pl, "en": en, "sev": sev})

    def reason_lines(self, lang: str = "pl") -> List[str]:
        return [r["pl"] if lang == "pl" else r["en"] for r in self.reasons]

    @property
    def is_threat(self) -> bool:
        return self.verdict in ("suspicious", "danger")


# Verdict ranking so we never downgrade a finding once escalated.
_RANK = {"trusted": 0, "unknown": 1, "caution": 2, "suspicious": 3, "danger": 4}


class ProcessGuard:
    """Stateful guard: process-library baseline + signature cache + heuristics."""

    def __init__(self) -> None:
        self.name = "core.process_guard"
        self._known: Dict[str, dict] = {}          # name -> library entry
        self._sig_cache: Dict[str, dict] = {}      # exe path -> {key, status, publisher}
        self._whitelist: set = set()               # user-trusted names
        self._sys_dirs: Tuple[str, ...] = self._system_dirs()
        self._load_library()
        self._load_prefs()
        self._targets = self._build_typosquat_targets()
        register_component(self.name, self)

    # ── Setup ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _system_dirs() -> Tuple[str, ...]:
        win = os.environ.get("SystemRoot", r"C:\Windows")
        return tuple(p.lower() for p in (
            os.path.join(win, "System32"),
            os.path.join(win, "SysWOW64"),
            os.path.join(win, "WinSxS"),
            win,                       # explorer.exe lives directly in C:\Windows
        ))

    def _load_library(self) -> None:
        for base in (BUNDLE_DIR, APP_DIR):
            path = os.path.join(base, "data", "process_library.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._known = {k.lower(): v for k, v in json.load(f).items()}
                    return
                except Exception:
                    continue

    def _build_typosquat_targets(self) -> List[Tuple[str, str]]:
        """List of (raw_name, homoglyph_normalised) impersonation targets."""
        names = set(_CRITICAL_SYSTEM) | set(_POPULAR_TARGETS) | set(self._known.keys())
        out = []
        for n in names:
            norm = _homoglyph_norm(n)
            if len(norm) >= 4:          # skip ultra-short names (too noisy)
                out.append((n, norm))
        return out

    @property
    def _prefs_path(self) -> str:
        return os.path.join(APP_DIR, "data", "cache", "process_guard.json")

    def _load_prefs(self) -> None:
        try:
            with open(self._prefs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._whitelist = set(data.get("whitelist", []))
            self._sig_cache = data.get("sig_cache", {})
        except Exception:
            pass

    def _save_prefs(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._prefs_path), exist_ok=True)
            with open(self._prefs_path, "w", encoding="utf-8") as f:
                json.dump({
                    "whitelist": sorted(self._whitelist),
                    "sig_cache": self._sig_cache,
                }, f, indent=2)
        except Exception:
            pass

    # ── Whitelist ────────────────────────────────────────────────────────────

    def is_whitelisted(self, name: str) -> bool:
        return (name or "").lower() in self._whitelist

    def whitelist_add(self, name: str) -> None:
        self._whitelist.add((name or "").lower())
        self._save_prefs()

    def whitelist_remove(self, name: str) -> None:
        self._whitelist.discard((name or "").lower())
        self._save_prefs()

    # ── Signature (Authenticode) ───────────────────────────────────────────────

    def verify_signature(self, exe_path: str) -> Tuple[str, str]:
        """
        Returns (status, publisher). status is one of:
          Valid / NotSigned / NotTrusted / HashMismatch / Unknown / Error.
        Cached by (path, size, mtime) so each binary version is checked once.
        Windows-only; returns ("Unknown", "") elsewhere.
        """
        if not exe_path or not os.path.exists(exe_path):
            return "Unknown", ""
        if not sys.platform.startswith("win"):
            return "Unknown", ""
        try:
            st = os.stat(exe_path)
            key = f"{st.st_size}:{int(st.st_mtime)}"
        except Exception:
            key = "0:0"
        cached = self._sig_cache.get(exe_path.lower())
        if cached and cached.get("key") == key:
            return cached.get("status", "Unknown"), cached.get("publisher", "")

        status, publisher = self._powershell_authenticode(exe_path)
        self._sig_cache[exe_path.lower()] = {
            "key": key, "status": status, "publisher": publisher,
        }
        # Persist lazily; cache can grow but we prune on save elsewhere if needed.
        self._save_prefs()
        return status, publisher

    @staticmethod
    def _powershell_authenticode(exe_path: str) -> Tuple[str, str]:
        try:
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                "$s = Get-AuthenticodeSignature -LiteralPath "
                f"'{exe_path}'; "
                "$subj = ''; if ($s.SignerCertificate) "
                "{ $subj = $s.SignerCertificate.Subject }; "
                "Write-Output (\"{0}|{1}\" -f $s.Status, $subj)",
            ]
            out = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace", timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            raw = (out.stdout or "").strip()
            if not raw or "|" not in raw:
                return "Unknown", ""
            status, subj = raw.split("|", 1)
            publisher = ""
            # Subject looks like: CN="Microsoft Corporation", O=..., L=...
            for part in subj.split(","):
                part = part.strip()
                if part.upper().startswith("CN="):
                    publisher = part[3:].strip().strip('"')
                    break
            return status.strip() or "Unknown", publisher
        except Exception:
            return "Error", ""

    # ── Core analysis ──────────────────────────────────────────────────────────

    def analyze(self, name: str, exe: str = "", pid: Optional[int] = None,
                deep: bool = False) -> Finding:
        """Analyse one process. `deep=True` runs Authenticode verification."""
        nm = (name or "").lower().strip()
        f = Finding(name=nm, pid=pid, exe=exe or "")
        lib = self._known.get(nm)
        if lib:
            f.expected_vendor = lib.get("vendor", "") or ""

        trusted_hint = {"v": False}   # positive trust signal seen (system/lib/signed)

        def esc(verdict: str, score: int) -> None:
            # Escalates negative severity only (caution/suspicious/danger).
            if _RANK[verdict] > _RANK[f.verdict]:
                f.verdict = verdict
            f.score = max(f.score, score)

        # Kernel pseudo-processes have no on-disk binary -> trusted by definition
        # (an impersonator would need a real .exe, caught by typosquat/path checks).
        if not nm or nm in _KERNEL_PSEUDO:
            f.verdict, f.score = "trusted", 0
            f.add("kernel", "✓ Proces jądra Windows (bez pliku na dysku).",
                  "✓ Windows kernel process (no on-disk file).", 0)
            return f

        if self.is_whitelisted(nm):
            f.verdict, f.score = "trusted", 0
            f.add("whitelist", "✓ Na Twojej liście zaufanych.",
                  "✓ On your trusted whitelist.", 0)
            return f

        exe_l = (exe or "").lower()
        on_risky_path = bool(exe_l) and any(h in exe_l for h in _RISKY_PATH_HINTS)

        # 1. Malware name fragments (miners, classic droppers)
        base = nm[:-4] if nm.endswith(".exe") else nm
        for frag in _MALWARE_FRAGMENTS:
            if frag in base:
                esc("danger", 95)
                f.add("malware_name",
                      f"🔴 Nazwa zawiera wzorzec znanego malware: '{frag}'.",
                      f"🔴 Name contains a known-malware pattern: '{frag}'.", 3)
                break

        # 2. Masquerade: critical system name from a non-system path
        if nm in _CRITICAL_SYSTEM:
            if exe_l and not self._in_system_dir(exe_l):
                esc("danger", 90)
                f.add("masquerade",
                      f"🔴 '{nm}' to proces systemowy, ale działa spoza System32 "
                      f"({exe or '?'}) - klasyczne podszywanie.",
                      f"🔴 '{nm}' is a system process but runs outside System32 "
                      f"({exe or '?'}) - classic masquerade.", 3)
            else:
                trusted_hint["v"] = True
                f.add("system_ok",
                      "✓ Proces systemowy Windows z prawidłowej lokalizacji.",
                      "✓ Windows system process from its correct location.", 0)

        # 3. Typosquat / homoglyph of a known critical/popular name
        if nm not in self._known and nm not in _CRITICAL_SYSTEM:
            hit = self._typosquat_hit(nm)
            if hit:
                target, dist = hit
                if dist == 0:
                    esc("danger", 85)          # homoglyph twin -> deliberate decoy
                elif on_risky_path:
                    esc("suspicious", 72)       # lookalike + risky location
                else:
                    esc("caution", 45)          # lookalike alone -> worth a look
                f.add("typosquat",
                      f"⚠ Nazwa łudząco podobna do zaufanego '{target}' "
                      f"(różnica: {dist}) - możliwe podszywanie pod nazwę.",
                      f"⚠ Name deceptively close to trusted '{target}' "
                      f"(edit distance {dist}) - possible name impersonation.", 3)

        # 4. Risky path (temp/downloads/recycle) - on its own only a caution
        if on_risky_path:
            esc("caution", max(f.score, 40))
            f.add("risky_path",
                  f"⚠ Uruchamiany z podejrzanej lokalizacji: {exe}.",
                  f"⚠ Running from a suspicious location: {exe}.", 2)

        # 5. Library safety flag
        if lib:
            safety = (lib.get("safety") or "").lower()
            if safety in ("suspicious", "unsafe"):
                esc("suspicious", max(f.score, 65))
                f.add("lib_flag",
                      f"⚠ Baza oznacza '{nm}' jako {safety}.",
                      f"⚠ Library flags '{nm}' as {safety}.", 2)
            elif safety == "caution":
                esc("caution", max(f.score, 30))
                f.add("lib_caution",
                      "ℹ Wymaga uwagi (np. dużo zasobów lub bloatware).",
                      "ℹ Worth watching (heavy or bloatware-class).", 1)
            elif safety == "safe":
                trusted_hint["v"] = True
                # Only show the reassuring note when nothing negative has fired,
                # so a masquerading "svchost.exe" isn't also called "known good".
                if f.verdict == "unknown":
                    f.add("lib_safe",
                          f"✓ Znany, bezpieczny program: {lib.get('name', nm)} "
                          f"({lib.get('vendor', '?')}).",
                          f"✓ Known good program: {lib.get('name', nm)} "
                          f"({lib.get('vendor', '?')}).", 0)

        # 6. Deep: Authenticode author verification
        if deep and exe and os.path.exists(exe):
            status, publisher = self.verify_signature(exe)
            f.sig_status, f.publisher = status, publisher
            self._apply_signature(f, esc, trusted_hint)

        # 7. Finalise: promote to trusted when a positive signal was seen and no
        #    negative escalation happened; otherwise leave a gentle 'unknown' note.
        if f.verdict == "unknown":
            if trusted_hint["v"]:
                f.verdict = "trusted"
            elif not lib:
                f.add("unknown",
                      "ℹ Nieznany programowi - to nie znaczy groźny (np. własne narzędzie).",
                      "ℹ Unrecognised - not necessarily harmful (e.g. your own tool).", 1)

        return f

    def _apply_signature(self, f: Finding, esc, trusted_hint: dict) -> None:
        status = (f.sig_status or "").lower()
        pub = f.publisher or ""
        pub_l = pub.lower()
        if status == "valid" and pub:
            if "microsoft" in pub_l:
                # Microsoft signs/attests a huge range of system AND OEM binaries
                # (e.g. "Microsoft Windows Hardware Compatibility Publisher" for
                # vendor drivers/services). A valid MS signature is always trusted.
                trusted_hint["v"] = True
                f.add("signed_ms",
                      f"✓ Podpis Microsoft (zaufany): {pub}.",
                      f"✓ Microsoft signature (trusted): {pub}.", 0)
            elif f.expected_vendor and not self._vendor_matches(pub, f.expected_vendor):
                # Not necessarily bad - signing entity often differs from the
                # product's brand (parent company, code-signing arm). Flag softly.
                esc("caution", max(f.score, 40))
                f.add("publisher_mismatch",
                      f"ℹ Podpisany przez '{pub}', oczekiwano '{f.expected_vendor}' "
                      f"- zwykle inny podmiot podpisujący, warto rzucić okiem.",
                      f"ℹ Signed by '{pub}', expected '{f.expected_vendor}' "
                      f"- usually just a different signing entity, worth a glance.", 1)
            else:
                trusted_hint["v"] = True
                f.add("signed_ok",
                      f"✓ Podpis cyfrowy ważny - autor: {pub}.",
                      f"✓ Valid digital signature - author: {pub}.", 0)
        elif status in ("nottrusted", "hashmismatch"):
            esc("suspicious", max(f.score, 75))
            f.add("bad_signature",
                  f"⚠ Podpis nieprawidłowy ({f.sig_status}) - plik mógł być zmodyfikowany.",
                  f"⚠ Invalid signature ({f.sig_status}) - file may be tampered.", 3)
        else:  # NotSigned / Unknown / empty
            if f.name in _CRITICAL_SYSTEM:
                # A real system process is always Microsoft-signed - unsigned is a flag.
                esc("suspicious", max(f.score, 68))
                f.add("expected_signed",
                      "⚠ Proces systemowy powinien być podpisany, a nie jest.",
                      "⚠ A system process should be signed but isn't.", 2)
            else:
                # Unsigned is common and benign for smaller / open-source tools.
                f.add("unsigned",
                      "ℹ Plik bez podpisu cyfrowego (częste dla mniejszych/otwartych narzędzi).",
                      "ℹ Not digitally signed (common for smaller/open-source tools).", 1)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _in_system_dir(self, exe_lower: str) -> bool:
        return any(exe_lower.startswith(d) for d in self._sys_dirs)

    @staticmethod
    def _vendor_matches(publisher: str, expected: str) -> bool:
        """Loose vendor comparison (ignores suffixes like Inc./LLC/Corporation)."""
        def norm(s: str) -> str:
            s = (s or "").lower()
            for junk in ("corporation", "incorporated", "inc.", "inc", "llc",
                         "ltd.", "ltd", "gmbh", "co.", "company", "foundation",
                         ",", ".", "  "):
                s = s.replace(junk, " ")
            return " ".join(s.split())
        p, e = norm(publisher), norm(expected)
        if not p or not e:
            return False
        return p == e or p in e or e in p or p.split()[0] == e.split()[0]

    def _typosquat_hit(self, name: str) -> Optional[Tuple[str, int]]:
        """Closest impersonation target within edit distance 1 (0 = homoglyph twin)."""
        nm_norm = _homoglyph_norm(name)
        if len(nm_norm) < 4:
            return None
        best: Optional[Tuple[str, int]] = None
        for raw, target_norm in self._targets:
            if _homoglyph_norm(raw) == _homoglyph_norm(name) and raw.lower() != name.lower():
                # Same after homoglyph fold but spelled differently -> deliberate decoy
                return raw, 0
            d = _lev(nm_norm, target_norm, cap=1)
            if d <= 1 and raw.lower() != name.lower():
                if best is None or d < best[1]:
                    best = (raw, d)
        return best

    # ── Whole-system scan ──────────────────────────────────────────────────────

    def scan(self, deep: bool = False, limit: int = 600) -> List[Finding]:
        """
        Enumerate running processes and return non-trusted findings, worst first.
        `deep=True` adds Authenticode checks for unknown/flagged processes only
        (so a deep scan stays responsive instead of signing every process).
        """
        out: List[Finding] = []
        try:
            import psutil
        except Exception:
            return out
        seen: set = set()
        for proc in psutil.process_iter(["name", "pid", "exe"]):
            try:
                nm = (proc.info.get("name") or "").lower().strip()
                if not nm or nm in seen:
                    continue
                seen.add(nm)
                if len(seen) > limit:
                    break
                exe = proc.info.get("exe") or ""
                # Cheap pass first
                f = self.analyze(nm, exe=exe, pid=proc.info.get("pid"), deep=False)
                # Escalate to a signature check ONLY where the publisher can change
                # the verdict: already-flagged processes, critical system names, or
                # ones with a known expected vendor. Plain unknowns are skipped so a
                # deep scan stays fast (no PowerShell call per random tool).
                if deep and exe and not self.is_whitelisted(nm) and (
                    f.verdict in ("suspicious", "danger")
                    or nm in _CRITICAL_SYSTEM
                    or f.expected_vendor
                ):
                    f = self.analyze(nm, exe=exe, pid=proc.info.get("pid"), deep=True)
                if f.verdict != "trusted":
                    out.append(f)
            except Exception:
                continue
        out.sort(key=lambda x: (_RANK[x.verdict], x.score), reverse=True)
        return out

    def scan_summary(self, deep: bool = False) -> dict:
        """Compact dict for UI/proactive: counts by verdict + top threats."""
        findings = self.scan(deep=deep)
        counts = {"danger": 0, "suspicious": 0, "caution": 0, "unknown": 0}
        for f in findings:
            counts[f.verdict] = counts.get(f.verdict, 0) + 1
        threats = [f for f in findings if f.is_threat]
        return {
            "counts": counts,
            "threats": threats,
            "has_threat": bool(threats),
            "scanned_at": time.time(),
        }


# ── Singleton ───────────────────────────────────────────────────────────────
process_guard = ProcessGuard()
