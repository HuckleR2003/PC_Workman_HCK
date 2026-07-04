"""tests.test_protected_processes
Tests for core.protected_processes - the anti-cheat guard that every
suspend / kill / priority / memory-trim primitive must consult.
A false negative here can crash a player's game or trip an anti-cheat ban,
so this list is regression-tested exhaustively.
"""
import unittest

from core.protected_processes import is_protected


class TestAntiCheatProtected(unittest.TestCase):
    """Every major anti-cheat engine must be refused by the primitives."""

    ANTI_CHEATS = [
        # Riot Vanguard (Valorant / League of Legends)
        "vgc.exe", "vgtray.exe", "vgk.sys", "RiotClientServices.exe",
        # EasyAntiCheat
        "EasyAntiCheat.exe", "EasyAntiCheat_EOS.exe", "easyanticheat_x64.exe",
        # BattlEye
        "BEService.exe", "BEService_x64.exe", "bedaisy.sys",
        # FACEIT
        "faceitclient.exe", "faceitservice.exe",
        # Others
        "PnkBstrA.exe", "PnkBstrB.exe", "mhyprot2.sys", "mhyprot3.sys",
    ]

    def test_known_anticheat_exes_are_protected(self):
        for name in self.ANTI_CHEATS:
            with self.subTest(name=name):
                self.assertTrue(is_protected(name),
                                f"{name} must be protected")

    def test_case_insensitive(self):
        self.assertTrue(is_protected("VGC.EXE"))
        self.assertTrue(is_protected("beservice.exe"))

    def test_full_path_as_name(self):
        self.assertTrue(is_protected(r"C:\Riot Games\VALORANT\vgc.exe"))
        self.assertTrue(is_protected("C:/Riot Games/VALORANT/vgc.exe"))

    def test_keyword_match_on_exe_path(self):
        self.assertTrue(
            is_protected("helper.exe", r"C:\Program Files\EasyAntiCheat\x.exe"))
        self.assertTrue(is_protected("SomeAntiCheatHelper.exe"))


class TestNormalProcessesNotProtected(unittest.TestCase):
    """Games and everyday apps must stay optimizable - no false positives."""

    NORMAL = [
        "chrome.exe", "discord.exe", "steam.exe", "spotify.exe",
        "notepad.exe", "python.exe", "svchost.exe", "explorer.exe",
        # the GAMES themselves are not anti-cheats - they may be optimized
        "LeagueClient.exe", "VALORANT.exe", "cs2.exe", "FortniteClient.exe",
    ]

    def test_normal_apps_not_protected(self):
        for name in self.NORMAL:
            with self.subTest(name=name):
                self.assertFalse(is_protected(name),
                                 f"{name} must NOT be protected")

    def test_empty_and_garbage_input(self):
        self.assertFalse(is_protected(""))
        self.assertFalse(is_protected("", ""))
        self.assertFalse(is_protected(None))


if __name__ == "__main__":
    unittest.main()
