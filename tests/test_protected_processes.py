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
        "notepad.exe", "teams.exe", "slack.exe", "obs64.exe",
        # the GAMES themselves are not anti-cheats - they may be optimized
        "LeagueClient.exe", "VALORANT.exe", "cs2.exe", "FortniteClient.exe",
    ]
    # NB: python.exe / svchost.exe / explorer.exe are intentionally NOT here -
    # they are OS-critical / self and must be protected (see the freeze fix).

    def test_normal_apps_not_protected(self):
        for name in self.NORMAL:
            with self.subTest(name=name):
                self.assertFalse(is_protected(name),
                                 f"{name} must NOT be protected")

    def test_empty_and_garbage_input(self):
        self.assertFalse(is_protected(""))
        self.assertFalse(is_protected("", ""))
        self.assertFalse(is_protected(None))


class TestSystemCriticalAndSelfProtected(unittest.TestCase):
    """Regression for the 'total system freeze after 5-15 min' bug: App
    Hibernation could suspend an OS-critical process or PC Workman itself.
    Freezing dwm.exe/explorer.exe white-screens the desktop."""

    CRITICAL = [
        "explorer.exe", "dwm.exe", "System", "csrss.exe", "winlogon.exe",
        "services.exe", "lsass.exe", "svchost.exe", "wininit.exe",
        "RuntimeBroker.exe", "MsMpEng.exe", "audiodg.exe",
    ]
    SELF = ["PC Workman HCK.exe", "python.exe", "pythonw.exe"]

    def test_os_critical_are_protected(self):
        from core.protected_processes import is_protected
        for name in self.CRITICAL + self.SELF:
            with self.subTest(name=name):
                self.assertTrue(is_protected(name), f"{name} must be protected")

    def test_critical_full_path(self):
        from core.protected_processes import is_protected
        self.assertTrue(is_protected(r"C:\Windows\explorer.exe"))
        self.assertTrue(is_protected(r"C:\Windows\System32\dwm.exe"))

    def test_is_self_pid(self):
        import os
        from core.protected_processes import is_self
        self.assertTrue(is_self(os.getpid()))
        self.assertFalse(is_self(999999))

    def test_hibernation_refuses_self_and_critical(self):
        import os
        from core.hibernation_manager import hibernation_manager as H
        self.assertFalse(H.sleep_app(os.getpid(), "python.exe", "", "freeze"),
                         "sleep_app suspended ITSELF")
        self.assertFalse(H.sleep_app(999901, "explorer.exe",
                                     r"C:\Windows\explorer.exe", "freeze"),
                         "sleep_app suspended explorer")
        self.assertFalse(H.sleep_app(999902, "dwm.exe", "", "low"),
                         "sleep_app idle-prioritised dwm")


if __name__ == "__main__":
    unittest.main()
