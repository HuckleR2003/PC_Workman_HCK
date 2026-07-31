"""utils/prefs_io.py - one guarded JSON read/write path (2026-07 dedup).

Six near-identical _load_prefs/_save_prefs copies (auto_optimizer,
hibernation_manager, process_guard, optimization_services, startup_manager)
each re-implemented `json.load` + `os.makedirs` + `try/except`. This is the
single helper they now share.

Contract (matches every old copy): reading NEVER raises (returns the default),
writing NEVER raises (returns False on failure). Settings persistence must not
be able to crash the app.
"""
import json
import os


def load_json(path: str, default=None):
    """Read a JSON file. Returns `default` (or {} when default is None) on any
    error - missing file, bad JSON, permissions. Never raises."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def save_json(path: str, data, indent: int = 2) -> bool:
    """Write `data` as JSON, creating parent dirs first. Returns True on
    success, False on any failure. Never raises. `ensure_ascii=False` keeps
    Polish characters human-readable (still valid JSON)."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception:
        return False
