"""utils/prefs_io.py - the one way settings and state files are read and written.

History: six near-identical _load_prefs/_save_prefs copies were merged here
(2026-07). On 2026-11-15 the write path was rebuilt, because it was the most
likely reason PC Workman "forgot" settings:

  - open(path, "w") EMPTIES the file first and writes it afterwards. Closing
    the app, a crash, Windows shutting down, or a second thread writing the
    same file in that moment left an empty or half-written file. The next
    read failed, returned {} and every setting in that file was gone.
  - Two threads did write the same files (turbo_state.json from the TURBO
    service manager and the power-plan daemon; user_prefs.json from the
    Optimization page and the master TURBO switch).

Now:
  - save_json writes a temporary file next to the target and swaps it in with
    os.replace, which is atomic on NTFS: a reader sees the old file or the new
    one, never half of one.
  - One lock per file: two writers wait for each other.
  - The previous good version is kept as <file>.bak. load_json falls back to
    it when the main file cannot be parsed, so even an outside corruption
    loses at most the very last change.
  - update_json(path, **changes) reads, changes and writes under the lock, for
    files several places write (no lost update from a stale copy).

Contract (unchanged): reading NEVER raises (returns the default), writing
NEVER raises (returns False on failure). Settings must not crash the app.
"""
import json
import os
import threading

_locks: dict = {}
_locks_guard = threading.Lock()


def _lock_for(path: str) -> threading.RLock:
    key = os.path.normcase(os.path.abspath(path))
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = _locks[key] = threading.RLock()
        return lock


def _read(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_json(path: str, default=None):
    """Read a JSON file. Falls back to <file>.bak when the file is damaged.
    Returns `default` (or {} when default is None) when neither can be read.
    Never raises."""
    fallback = {} if default is None else default
    with _lock_for(path):
        try:
            return _read(path)
        except FileNotFoundError:
            return fallback
        except Exception:
            pass
        try:
            data = _read(path + ".bak")
        except Exception:
            return fallback
    # Damaged main file, good backup: put the backup back so the next read is
    # clean too. Outside the read path's lock is fine: save_json locks again.
    save_json(path, data)
    return data


def save_json(path: str, data, indent: int = 2) -> bool:
    """Write `data` as JSON atomically (temp file + os.replace), keeping the
    previous version as <file>.bak. Returns True on success. Never raises.
    `ensure_ascii=False` keeps Polish characters human-readable."""
    try:
        text = json.dumps(data, indent=indent, ensure_ascii=False)
    except Exception:
        return False
    with _lock_for(path):
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(path):
                try:
                    _read(path)                    # only a GOOD file becomes .bak
                    os.replace(path, path + ".bak")
                except Exception:
                    pass
            os.replace(tmp, path)
            return True
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            return False


def remove_json(path: str) -> None:
    """Delete a state file and its backup (an empty state is no file)."""
    with _lock_for(path):
        for p in (path, path + ".bak"):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def edit_json(path: str, fn, default=None):
    """Read, let `fn(data)` change it in place, write back - all under the
    file's lock. For nested changes update_json cannot express."""
    with _lock_for(path):
        data = load_json(path, {} if default is None else dict(default))
        if not isinstance(data, dict):
            data = {}
        fn(data)
        save_json(path, data)
        return data


def update_json(path: str, default=None, **changes) -> dict:
    """Read, apply `changes` (a value of None removes the key) and write back,
    all under the file's lock. Returns the new content. For files that more
    than one place writes, so no writer overwrites another with a stale copy."""
    with _lock_for(path):
        data = load_json(path, {} if default is None else dict(default))
        if not isinstance(data, dict):
            data = {}
        for key, value in changes.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        save_json(path, data)
        return data
