"""
import_core.py
Central registry for PC_Workman_HCK components.

Each module registers itself here by: 
- `register_component(name, obj)` - 
This registry assigns a unique sequential ID. eg.:
  py001_hck, py002_hck, json005_hck, etc.
and keeps metadata for debugging, diagnostics, and UI overlays.
"""

import os
import time
import threading

# Main global registry
COMPONENTS = {}
REGISTER_LOG = []  # chronological history of all registrations
_ID_COUNTER = {
    "py": 0,
    "json": 0,
    "csv": 0,
    "txt": 0
}

_lock = threading.Lock()


def _get_prefix_for_name(name: str) -> str:
    """Infer prefix (py/json/csv/txt) from filename or extension-like string."""
    name = name.lower()
    if name.endswith(".json") or "json" in name:
        return "json"
    if name.endswith(".csv") or "csv" in name:
        return "csv"
    if name.endswith(".txt") or "txt" in name:
        return "txt"
    return "py"


def _assign_id(prefix: str) -> str:
    """Increment and return formatted ID for given prefix."""
    with _lock:
        _ID_COUNTER.setdefault(prefix, 0)
        _ID_COUNTER[prefix] += 1
        num = _ID_COUNTER[prefix]
    return f"{prefix}{num:03d}_hck"


def register_component(name: str, obj):
    """
    Register a component globally.
    Assigns unique HCK ID (like py001_hck) and logs the registration.
    """
    prefix = _get_prefix_for_name(name)
    comp_id = _assign_id(prefix)

    metadata = {
        "id": comp_id,
        "name": name,
        "type": prefix,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file_path": getattr(obj, "__file__", None)
    }

    COMPONENTS[name] = obj
    REGISTER_LOG.append(metadata)

    print(f"[import_core] Registered {name} as {comp_id}")

    return obj


def list_components(show_ids=True):
    """Return formatted list of all registered components."""
    lines = []
    for meta in REGISTER_LOG:
        line = f"{meta['id']} | {meta['name']} | {meta['timestamp']}"
        lines.append(line if show_ids else meta["name"])
    return "\n".join(lines)


def get_component(name: str):
    """Helper: safely get registered component."""
    return COMPONENTS.get(name)


def count_components():
    """Return number of components currently registered."""
    return len(COMPONENTS)


# Simple self-test
if __name__ == "__main__":
    class Dummy:
        pass

    register_component("core.monitor", Dummy())
    register_component("data.log.json", Dummy())
    register_component("ui.main_window", Dummy())
    print(list_components())
