# tests/test_shortcuts.py
"""
Pins the shortcut contract.

The Store AUMID was wrong once (it named an Application Id that does not exist
in the published manifest), so the desktop shortcut opened nothing. That is the
kind of bug nobody reports, they just stop using the shortcut.
"""
import os
import re
import unittest

from utils import shortcuts


class ShortcutContract(unittest.TestCase):

    def test_aumid_matches_the_published_manifest(self):
        self.assertTrue(shortcuts._AUMID.endswith("!App"),
                        "Application Id must stay 'App': changing it breaks "
                        "every pinned tile of existing Store users")
        self.assertIn("MarcinHCKFirmuga.PCWorkman_4hekbcs2ddfbc", shortcuts._AUMID)

    def test_desktop_dir_is_a_path(self):
        d = shortcuts.desktop_dir()
        self.assertTrue(isinstance(d, str) and d)

    def test_admin_shortcut_is_refused_on_store_installs(self):
        real = shortcuts.is_store_install
        try:
            shortcuts.is_store_install = lambda: True
            ok, note = shortcuts.create_admin_shortcut()
            self.assertFalse(ok)
            self.assertEqual(note, "store")
        finally:
            shortcuts.is_store_install = real

    def test_run_as_admin_bit_is_the_documented_one(self):
        src = open(shortcuts.__file__, encoding="utf-8").read()
        self.assertIn("0x20", src)
        self.assertIn("21", src)


if __name__ == "__main__":
    unittest.main()
