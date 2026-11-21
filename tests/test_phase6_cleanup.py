"""Phase 6 (2026-11-20): Cleanup, Health report, Your profile.

The cleanup engine is tested only on files these tests create in their own
temporary folders. Nothing here touches the user's TEMP, browsers, the
Recycle Bin or the DNS cache: the shell calls are replaced.
"""
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from core import cleanup

DAY = 86400


def _file(folder, name, size=1000, age_s=3 * DAY):
    os.makedirs(folder, exist_ok=True)
    p = os.path.join(folder, name)
    with open(p, "wb") as f:
        f.write(b"x" * size)
    t = time.time() - age_s
    os.utime(p, (t, t))
    return p


class _Sandbox(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        # never the real Recycle Bin, never the real scan file
        for name, value in (("_recycle_bin", mock.Mock(side_effect=RuntimeError)),
                            ("empty_recycle_bin", mock.Mock(side_effect=AssertionError("bin"))),
                            ("_scan_path", lambda: os.path.join(self.dir, "scan.json")),
                            ("_log", lambda result: None),
                            ("is_admin", lambda: False),
                            ("_running", lambda names: set())):
            p = mock.patch.object(cleanup, name, value)
            p.start()
            self.addCleanup(p.stop)

    def spec(self, *items):
        return [(k, f, {**o, "group": o.get("group", "windows")}) for k, f, o in items]


class TestEngine(_Sandbox):

    def test_young_files_are_skipped(self):
        d = os.path.join(self.dir, "t")
        old = _file(d, "old.tmp")
        _file(d, "new.tmp", age_s=60)
        c, = cleanup.scan(spec=self.spec(("user_temp", [d], {})))
        self.assertEqual([p for p, _s in c.files], [old])
        self.assertEqual(c.size, 1000)
        self.assertTrue(c.selected)

    def test_pattern_and_top_only(self):
        d = os.path.join(self.dir, "Explorer")
        keep = _file(d, "iconcache_16.db")
        hit = _file(d, "thumbcache_256.db")
        _file(os.path.join(d, "sub"), "thumbcache_32.db")
        c, = cleanup.scan(spec=self.spec(("thumb_cache", [d],
                                          {"pattern": "thumbcache_*.db", "top_only": True, "min_age": 0})))
        self.assertEqual([p for p, _s in c.files], [hit])
        self.assertNotIn(keep, [p for p, _s in c.files])

    def test_star_expands_to_every_profile(self):
        base = os.path.join(self.dir, "User Data")
        a = _file(os.path.join(base, "Default", "Cache"), "f_000001")
        b = _file(os.path.join(base, "Profile 1", "Cache"), "f_000002")
        _file(os.path.join(base, "Default", "Login Data"), "secret")   # not a cache
        c, = cleanup.scan(spec=self.spec(("br_chrome", [os.path.join(base, "*", "Cache")],
                                          {"group": "browsers", "exe": ["chrome.exe"]})))
        self.assertEqual(sorted(p for p, _s in c.files), sorted([a, b]))
        self.assertEqual(c.group, "browsers")

    def test_open_program_blocks_its_item(self):
        d = os.path.join(self.dir, "discord", "Cache")
        _file(d, "data_1")
        with mock.patch.object(cleanup, "_running", lambda names: {"discord.exe"}):
            c, = cleanup.scan(spec=self.spec(("app_discord", [d], {"exe": ["discord.exe"]})))
        self.assertTrue(c.blocked)
        self.assertFalse(c.selected)
        self.assertEqual(c.files, [])
        self.assertTrue(c.note.startswith("running:"))

    def test_admin_items_blocked_without_rights(self):
        d = os.path.join(self.dir, "WinTemp")
        _file(d, "a.tmp")
        c, = cleanup.scan(spec=self.spec(("windows_temp", [d], {"admin": True})))
        self.assertTrue(c.blocked)
        self.assertEqual(c.note, "admin")
        self.assertFalse(c.selected)

    def test_missing_folders_are_dropped(self):
        c, = cleanup.scan(spec=self.spec(("app_spotify", [os.path.join(self.dir, "nope")], {})))
        self.assertEqual(c.folders, [])
        from ui.pages.cleanup_page import visible
        self.assertFalse(visible(c))

    def test_downloads_are_manual_and_go_to_the_recycle_bin(self):
        d = os.path.join(self.dir, "Downloads")
        _file(d, "big.iso", size=cleanup.BIG_FILE + 1, age_s=200 * DAY)
        _file(d, "small.zip", size=10, age_s=200 * DAY)
        c, = cleanup.scan(spec=self.spec(("big_downloads", [d],
                                          {"big_only": True, "manual": True, "top_only": True,
                                           "recycle": True, "group": "files"})))
        self.assertFalse(c.selected)
        self.assertEqual(len(c.files), 1)
        c.selected = True
        with mock.patch.object(cleanup, "to_recycle_bin", return_value=1) as trb:
            cleanup.clean([c])
        self.assertTrue(trb.call_args.kwargs["undo"])

    def test_clean_removes_only_scanned_files(self):
        d = os.path.join(self.dir, "t")
        old = _file(d, "old.tmp")
        young = _file(d, "young.tmp", age_s=60)
        cats = cleanup.scan(spec=self.spec(("user_temp", [d], {})))
        r = cleanup.clean(cats)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(young))
        self.assertEqual(r["freed"], 1000)
        self.assertEqual(r["files"], 1)

    def test_unselected_and_blocked_are_left_alone(self):
        d = os.path.join(self.dir, "t")
        p = _file(d, "old.tmp")
        c, = cleanup.scan(spec=self.spec(("user_temp", [d], {})))
        c.selected = False
        cleanup.clean([c])
        self.assertTrue(os.path.exists(p))
        c.selected, c.blocked = True, True
        cleanup.clean([c])
        self.assertTrue(os.path.exists(p))

    def test_scan_summary_is_remembered_without_file_names(self):
        d = os.path.join(self.dir, "t")
        _file(d, "secret_name.tmp", size=5000)
        cleanup.scan(spec=self.spec(("user_temp", [d], {})))
        s = cleanup.last_scan()
        self.assertEqual(s["items"]["user_temp"]["size"], 5000)
        self.assertEqual(s["total"], 5000)
        with open(cleanup._scan_path(), encoding="utf-8") as f:
            self.assertNotIn("secret_name", f.read())

    def test_every_real_item_is_known_and_grouped(self):
        from ui.pages.cleanup_page import _CAT, _GROUP
        keys = [k for k, _f, _o in cleanup.categories_spec()]
        self.assertEqual(len(keys), len(set(keys)))
        for k, _f, o in cleanup.categories_spec():
            self.assertIn(k, _CAT, k)
            self.assertIn(o["group"], _GROUP)
            self.assertIn(o["group"], cleanup.GROUPS)
        self.assertIn("recycle_bin", _CAT)

    def test_browser_items_never_reach_passwords_or_history(self):
        for k, folders, _o in cleanup.categories_spec():
            if not k.startswith("br_"):
                continue
            for f in folders:
                tail = os.path.basename(f).lower()
                self.assertIn(tail, ("cache", "code cache", "gpucache", "cache2"), f)

    def test_flush_dns_runs_ipconfig_only(self):
        with mock.patch("subprocess.run") as run:
            run.return_value = mock.Mock(returncode=0)
            self.assertTrue(cleanup.flush_dns())
        self.assertEqual(run.call_args.args[0], ["ipconfig", "/flushdns"])


class TestTipsAndGpt(_Sandbox):

    def _cat(self, key, size=0, note="", blocked=False):
        c = cleanup.Category(key, [self.dir], {})
        c.size, c.note, c.blocked = size, note, blocked
        return c

    def test_tips_follow_the_scan(self):
        from ui.pages.cleanup_page import speed_tips
        cats = [self._cat("user_temp", 9 * 1024 ** 3),
                self._cat("br_edge", note="running:msedge.exe", blocked=True)]
        tips = speed_tips(cats, "pl", "C:", 8)
        text = " ".join(t for t, _a in tips)
        self.assertIn("8% wolnego", text)
        self.assertIn("Pliki tymczasowe zajmują 9,0 GB", text)
        self.assertIn("Zamknij Edge", text)
        pages = [a[1] for _t, a in tips if a]
        self.assertEqual(pages, ["startup_manager", "services_manager", "optimization"])

    def test_tips_stay_quiet_on_a_clean_pc(self):
        from ui.pages.cleanup_page import speed_tips
        tips = speed_tips([self._cat("user_temp", 10)], "en", "C:", 60)
        self.assertEqual(len(tips), 3)          # only the three general ones

    def test_gpt_free_space_mentions_the_last_scan(self):
        from hck_gpt.responses.r_everyday import EverydayResponses
        fake = {"ts": time.time() - 3600, "total": 3 * 1024 ** 3,
                "items": {"user_temp": {"size": 2 * 1024 ** 3, "blocked": ""},
                          "br_operagx": {"size": 300 * 1024 ** 2, "blocked": ""},
                          "br_edge": {"size": 999 * 1024 ** 3, "blocked": "running:msedge.exe"}}}
        with mock.patch.object(cleanup, "last_scan", return_value=fake):
            line, = EverydayResponses._last_cleanup_scan(EverydayResponses, "pl")
        self.assertIn("3,0 GB", line)
        self.assertIn("pliki tymczasowe 2,0 GB", line)
        self.assertIn("Opera GX", line)
        self.assertNotIn("Edge", line)

    def test_gpt_ignores_an_old_scan(self):
        from hck_gpt.responses.r_everyday import EverydayResponses
        fake = {"ts": time.time() - 30 * DAY, "total": 1, "items": {"user_temp": {"size": 1}}}
        with mock.patch.object(cleanup, "last_scan", return_value=fake):
            self.assertEqual(EverydayResponses._last_cleanup_scan(EverydayResponses, "pl"), [])


class TestReportAndProfile(unittest.TestCase):

    def test_report_todo_is_the_three_weakest(self):
        from ui.pages.health_report import build_report, to_html
        scored = {"total": 70, "parts": [
            {"key": "stability", "score": 40, "why": ""}, {"key": "drives", "score": 90, "why": ""},
            {"key": "temps", "score": 60, "why": ""}, {"key": "memory", "score": 100, "why": ""},
            {"key": "drivers", "score": 75, "why": ""}]}
        r = build_report(scored, [(1, "<b>x</b>")], None, "pl", now=1_800_000_000)
        self.assertEqual([t["score"] for t in r["todo"]], [40, 60, 75])
        html = to_html(r, "pl")
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertIn(">70<", html)

    def test_report_names_what_moved(self):
        from ui.pages.health_report import build_report
        scored = {"total": 80, "parts": [{"key": "temps", "score": 80, "why": ""}]}
        prev = {"ts": 1_700_000_000, "total": 60, "parts": {"temps": 50}}
        r = build_report(scored, [], prev, "en")
        self.assertEqual(len(r["changes"]), 2)

    def test_milestones_are_earned_not_clicked(self):
        from ui.pages.profile_page import milestones
        zero = {"learning_days": 0, "hours": 0, "learn_pct": 0, "games": 0, "recordings": 0, "cleanups": 0}
        self.assertFalse(any(e for _k, e in milestones(zero)))
        full = {"learning_days": 9, "hours": 120, "learn_pct": 90, "games": 2, "recordings": 1, "cleanups": 1}
        self.assertTrue(all(e for _k, e in milestones(full)))


if __name__ == "__main__":
    unittest.main()
