"""core/data_export.py - move what PC Workman learned to another Windows.

Asked in the fourth long test (2026-11-17): "I am installing a new Windows,
how do I export the data?". export_zip() packs into one ZIP on the Desktop:

    data/logs/hck_stats.db     the history (SQLite online backup: consistent
                               while the app runs)
    data/cache/*.json          learning, receipts, notes
    data/observations/*.json   observation recordings
    settings/*.json            settings
    user_knowledge.db          what hck_GPT knows (hardware, facts)

Import: unpack the folders into the new PC Workman folder before its first
start, and user_knowledge.db into %LOCALAPPDATA%\\PC_Workman_HCK. A
README_IMPORT.txt inside the ZIP says the same. Nothing is deleted.
With PCW_APP_DIR set (tests) the ZIP goes to that folder, not the Desktop.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import zipfile


def _app_dir() -> str:
    try:
        from utils.paths import APP_DIR
        return APP_DIR
    except Exception:
        return os.getcwd()


def _sqlite_copy(src: str, dst: str) -> bool:
    try:
        a = sqlite3.connect(src, timeout=5)
        b = sqlite3.connect(dst)
        a.backup(b)
        b.close()
        a.close()
        return True
    except Exception:
        return False


_README = """PC Workman - przeniesienie danych / data transfer

PL:
1. Zainstaluj albo rozpakuj PC Workman na nowym systemie, NIE uruchamiaj go.
2. Foldery data i settings z tego ZIP skopiuj do folderu PC Workman (obok pliku .exe).
3. user_knowledge.db skopiuj do %LOCALAPPDATA%\\PC_Workman_HCK (utwórz folder, jeśli go nie ma).
4. Uruchom PC Workman: historia, nauka i ustawienia będą na miejscu.

EN:
1. Install or unpack PC Workman on the new system, do NOT start it.
2. Copy the data and settings folders from this ZIP into the PC Workman folder (next to the .exe).
3. Copy user_knowledge.db into %LOCALAPPDATA%\\PC_Workman_HCK (create it if missing).
4. Start PC Workman: history, learning and settings are back.
"""


def export_zip(dest_dir: str | None = None) -> dict:
    """{"path", "files", "mb"} of the created ZIP, or {"error"}."""
    app = _app_dir()
    if dest_dir is None:
        try:
            from core.observation import _notes_dir
            dest_dir = _notes_dir()
        except Exception:
            dest_dir = os.path.expanduser("~")
    name = time.strftime("PC Workman - dane %Y-%m-%d %H-%M.zip")
    path = os.path.join(dest_dir, name)
    count = 0
    try:
        with tempfile.TemporaryDirectory() as tmp, \
                zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("README_IMPORT.txt", _README)
            try:
                from utils.paths import log_dir
                logs = log_dir()
            except Exception:
                logs = os.path.join(app, "data", "logs")
            db = os.path.join(logs, "hck_stats.db")
            if os.path.exists(db):
                tmpdb = os.path.join(tmp, "hck_stats.db")
                if _sqlite_copy(db, tmpdb):
                    z.write(tmpdb, "data/logs/hck_stats.db")
                    count += 1
            for sub, pattern in (("data/cache", ".json"), ("data/observations", ".json"),
                                 ("settings", ".json")):
                folder = os.path.join(app, *sub.split("/"))
                if not os.path.isdir(folder):
                    continue
                for f in sorted(os.listdir(folder)):
                    if f.endswith(pattern):
                        z.write(os.path.join(folder, f), f"{sub}/{f}")
                        count += 1
            try:
                import importlib
                uk = importlib.import_module("hck_gpt.memory.user_knowledge")
                if os.path.exists(uk.DB_PATH):
                    tmpuk = os.path.join(tmp, "user_knowledge.db")
                    if _sqlite_copy(uk.DB_PATH, tmpuk):
                        z.write(tmpuk, "user_knowledge.db")
                        count += 1
            except Exception:
                pass
    except Exception as e:
        return {"error": str(e)}
    return {"path": path, "files": count,
            "mb": round(os.path.getsize(path) / 1024 ** 2, 1)}
