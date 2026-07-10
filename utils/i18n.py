# utils/i18n.py
"""
Centralized internationalization (i18n) module for PC Workman.

Supported languages: English ("en"), Polish ("pl")
Locale files:  locales/en.json, locales/pl.json

Public API
----------
    from utils.i18n import t, get_lang, set_lang, register_on_change, unregister_on_change

    t("nav.dashboard")                  -> "Dashboard"   (en) / "Panel główny" (pl)
    t("settings.general.startup_label") -> localized string
    t("dashboard.hello", name="Alice")  -> "Hello, Alice" / "Witaj, Alice"

    get_lang()              -> "en" or "pl"
    set_lang("pl")          -> changes global language, fires all registered callbacks
    register_on_change(fn)  -> fn() called whenever the language changes
    unregister_on_change(fn)

Keys use dot-separated paths that match the nested structure in the JSON files.
Missing keys fall back to the English catalog, then to the bare key string.

Thread safety
-------------
`set_lang` should only be called from the tkinter main thread (same as any
UI state change). The callbacks are invoked synchronously in the same call.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

# ── Paths ──────────────────────────────────────────────────────────────────────

_HERE    = os.path.dirname(__file__)
_LOCALES = os.path.normpath(os.path.join(_HERE, "..", "locales"))

# ── Supported languages ────────────────────────────────────────────────────────

SUPPORTED: Dict[str, str] = {
    "en": "English",
    "pl": "Polski",
}

_DEFAULT_LANG = "en"

# ── Module state ───────────────────────────────────────────────────────────────

_LANG:     str  = _DEFAULT_LANG
_CATALOGS: Dict[str, Dict] = {}          # lang -> parsed JSON dict
_CALLBACKS: List[Callable[[], None]] = []


# ── Catalog loader ─────────────────────────────────────────────────────────────

def _load_catalog(lang: str) -> Dict:
    """Load and cache a locale JSON file. Returns {} on error."""
    if lang in _CATALOGS:
        return _CATALOGS[lang]

    path = os.path.join(_LOCALES, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _CATALOGS[lang] = data
        return data
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"[i18n] Could not load '{lang}': {exc}")
        _CATALOGS[lang] = {}
        return {}


def _get_nested(data: Dict, key_path: str) -> Optional[str]:
    """
    Walk `data` via dot-separated `key_path` and return the string value,
    or None if any segment is missing or the leaf is not a string.
    """
    parts  = key_path.split(".")
    node: Any = data
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
        if node is None:
            return None
    return node if isinstance(node, str) else None


# ── Public API ─────────────────────────────────────────────────────────────────

def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """
    Translate *key* (dotted path) in the current language.

    Falls back to English catalog, then returns the bare key string so the
    UI never crashes on a missing translation.

    kwargs are passed to str.format_map() for interpolation, e.g.
        t("dashboard.hello", name="Alice")  ->  "Hello, Alice"
    """
    catalog = _load_catalog(_LANG)
    value   = _get_nested(catalog, key)

    # Fall back to English
    if value is None and _LANG != _DEFAULT_LANG:
        en_catalog = _load_catalog(_DEFAULT_LANG)
        value = _get_nested(en_catalog, key)

    # Last resort - the caller's default, or the bare key (never crash the UI)
    if value is None:
        return default if default is not None else key

    if kwargs:
        try:
            value = value.format_map(kwargs)
        except (KeyError, ValueError):
            pass  # return unformatted rather than crash

    return value


def get_lang() -> str:
    """Return the active language code ("en" / "pl")."""
    return _LANG


def set_lang(lang: str) -> None:
    """
    Set the active language and fire all registered on-change callbacks.

    Silently ignores unknown language codes (logs a warning).
    """
    global _LANG
    if lang not in SUPPORTED:
        print(f"[i18n] Unsupported language: '{lang}'. Supported: {list(SUPPORTED)}")
        return
    if lang == _LANG:
        return
    _LANG = lang
    # Pre-load the new catalog so the first `t()` call is instant
    _load_catalog(lang)
    for fn in list(_CALLBACKS):
        try:
            fn()
        except Exception as exc:
            print(f"[i18n] on_change callback error: {exc}")


def register_on_change(fn: Callable[[], None]) -> None:
    """Register a zero-argument callback to be called after `set_lang()`."""
    if fn not in _CALLBACKS:
        _CALLBACKS.append(fn)


def unregister_on_change(fn: Callable[[], None]) -> None:
    """Remove a previously registered callback (no-op if not registered)."""
    try:
        _CALLBACKS.remove(fn)
    except ValueError:
        pass


# ── Warm up the default catalog at import time ─────────────────────────────────

_load_catalog(_DEFAULT_LANG)
