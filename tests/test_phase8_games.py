"""Phase 8 (2026-11-20): the game library (data/games.json).

About 230 games with a genre and messages, genre pools for the rest, a
different line the first time a game is seen, Steam games found by their
folder. Nothing here reads the user's Steam library: manifests are written
to a temporary folder.
"""
import json
import os
import random
import shutil
import tempfile
import unittest
from unittest import mock

from core import game_library as GL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "data", "games.json"), encoding="utf-8") as f:
            cls.db = json.load(f)

    def test_size_and_shape(self):
        games = self.db["games"]
        self.assertGreaterEqual(len(games), 150)
        genres = self.db["genres"]
        for g in games:
            self.assertTrue(g["exe"] and g["name"], g)
            self.assertIn(g["genre"], genres, g["name"])
            for lang in ("pl", "en"):
                msgs = g["msg"][lang]
                self.assertTrue(1 <= len(msgs) <= 3, g["name"])
                for t, _s in msgs:
                    self.assertTrue(t.strip())
        for k, v in genres.items():
            self.assertTrue(v["pl"] and v["en"] and v["accent"].startswith("#"), k)
        self.assertTrue(self.db["first"]["pl"] and self.db["first"]["en"])

    def test_titles_are_short(self):
        """The toast grows to fit, up to 460 px at 100 %: titles stay short
        enough for one line there (2026-11-20: a fixed 300 px cut them)."""
        pools = [g["msg"][l] for g in self.db["games"] for l in ("pl", "en")]
        pools += [v[l] for v in self.db["genres"].values() for l in ("pl", "en")]
        pools += [self.db["first"][l] for l in ("pl", "en")]
        for pool in pools:
            for t, _s in pool:
                self.assertLessEqual(len(t), 45, t)

    def test_no_exe_belongs_to_two_games(self):
        seen = {}
        for g in self.db["games"]:
            for e in g["exe"]:
                self.assertEqual(e, e.lower())
                self.assertNotIn(e, seen, f"{e}: {seen.get(e)} / {g['name']}")
                seen[e] = g["name"]

    def test_appids_are_unique(self):
        ids = [g["appid"] for g in self.db["games"] if g.get("appid")]
        self.assertEqual(len(ids), len(set(ids)))

    def test_games_from_the_plan_are_there(self):
        names = {g["name"] for g in self.db["games"]}
        for n in ("Democracy 4", "PlateUp!", "Don't Starve Together", "Infection Free Zone",
                  "Supermarket Together", "Unturned", "Minecraft", "Stardew Valley"):
            self.assertIn(n, names)

    def test_no_marketing_words(self):
        txt = json.dumps(self.db["games"], ensure_ascii=False).lower()
        for w in ("najlepsz", "rewolucyj", "niesamowit", "ultimate experience", "best ever", "—"):
            self.assertNotIn(w, txt)


class TestLibrary(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        p = mock.patch.object(GL, "_seen_path", lambda: os.path.join(self.dir, "seen.json"))
        p.start()
        self.addCleanup(p.stop)
        GL._MANIFEST_CACHE.clear()

    def test_lookup_by_name_family_and_old_alias(self):
        self.assertEqual(GL.by_exe("PlateUp.exe")["name"], "PlateUp!")
        self.assertEqual(GL.by_exe("beamng.drive.x64.exe")["name"], "BeamNG.drive")
        self.assertEqual(GL.by_exe("seaofthieves.exe")["name"], "Sea of Thieves")
        self.assertIsNone(GL.by_exe("notepad.exe"))

    def test_generic_names_need_a_game_folder(self):
        strict = GL.known_exes(strict=True)
        self.assertNotIn("discovery.exe", strict)
        self.assertNotIn("fm.exe", strict)
        self.assertIn("discovery.exe", GL.known_exes(strict=False))
        self.assertIn("cs2.exe", strict)
        from core import game_detect
        game_detect._KNOWN = None
        game_detect._cache.clear()
        self.assertFalse(game_detect.is_game("discovery.exe", exe_path=r"C:\Tools\discovery.exe"))
        game_detect._cache.clear()          # the answer is cached per name
        self.assertTrue(game_detect.is_game("discovery.exe",
                                            exe_path=r"D:\SteamLibrary\steamapps\common\THE FINALS\discovery.exe"))

    def _steam(self, appid, name, installdir, exe):
        lib = os.path.join(self.dir, "SteamLibrary", "steamapps")
        os.makedirs(os.path.join(lib, "common", installdir), exist_ok=True)
        with open(os.path.join(lib, f"appmanifest_{appid}.acf"), "w", encoding="utf-8") as f:
            f.write(f'"AppState"\n{{\n\t"appid"\t\t"{appid}"\n\t"name"\t\t"{name}"\n'
                    f'\t"installdir"\t\t"{installdir}"\n}}\n')
        return os.path.join(lib, "common", installdir, exe)

    def test_steam_folder_finds_the_game_when_the_exe_name_is_new(self):
        path = self._steam(1599600, "PlateUp!", "PlateUp", "PlateUp_v2.exe")
        info = GL.resolve("plateup_v2.exe", path)
        self.assertEqual(info["name"], "PlateUp!")
        self.assertEqual(info["genre"], "cozy")

    def test_unknown_steam_game_gets_its_real_name_and_the_default_pool(self):
        path = self._steam(999999, "Some Small Game", "SSG", "ssg.exe")
        info = GL.resolve("ssg.exe", path)
        self.assertEqual(info["name"], "Some Small Game")
        self.assertEqual(info["genre"], "default")
        t, s, _a = GL.message("ssg.exe", "pl", path, first=False, rng=random.Random(1))
        self.assertEqual(s, "Some Small Game")

    def test_first_time_then_own_message(self):
        self.assertTrue(GL.is_first_time("plateup.exe"))
        t1, s1, a1 = GL.message("plateup.exe", "pl", rng=random.Random(0))
        self.assertIn(t1, [x[0] for x in GL.load()["first"]["pl"]])
        self.assertEqual(s1, "PlateUp!")
        GL.mark_seen("plateup.exe")
        self.assertFalse(GL.is_first_time("plateup.exe"))
        t2, s2, _a = GL.message("plateup.exe", "en", rng=random.Random(0))
        self.assertEqual(s2, "PlateUp!")
        self.assertEqual((t2, s2), tuple(GL.by_exe("plateup.exe")["msg"]["en"][0]))
        self.assertTrue(a1.startswith("#"))

    def test_seen_file_holds_names_only(self):
        GL.mark_seen("beamng.drive.x64.exe")
        with open(os.path.join(self.dir, "seen.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"games": ["beamng.drive"]})

    def test_display_names(self):
        from core.game_detect import display_name
        self.assertEqual(display_name("cs2.exe"), "Counter-Strike 2")
        self.assertEqual(display_name("BeamNG.drive.x64.exe"), "BeamNG.drive")
        self.assertEqual(display_name("someunknown.exe"), "someunknown")

    def test_toast_uses_the_library(self):
        from ui.components import gaming_toast as T
        title, sub, accent = T._pick("stardewvalley.exe", "en", first=False)
        self.assertEqual(sub, "Stardew Valley")
        self.assertTrue(T._is_known("cs2.exe"))
        self.assertEqual(T._canon("seaofthieves.exe"), "sotgame.exe")

    def test_spec_ships_the_library(self):
        with open(os.path.join(ROOT, "PCWorkman.spec"), encoding="utf-8") as f:
            self.assertIn("'games.json'", f.read())


if __name__ == "__main__":
    unittest.main()
