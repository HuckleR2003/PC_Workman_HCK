"""
utils/fonts.py - the app's typefaces, in one place (2026-11-16).

The app ships Inter (data/fonts/InterVariable.ttf). It asked Tk for the
family "Inter", but a variable font registers itself on Windows as
"Inter Variable Text" (plus one family per named weight: "... SemiBold",
"... Black"). Tk found no "Inter" and silently drew that text in Arial.
Modules that read UI before load() ran got "Segoe UI" instead, and headers
asked for "Segoe UI Semibold" by name: three typefaces mixed on every page.

Every module takes its family names from here:
    UI     body text
    HDR    headings (semibold)
    HEAVY  big numbers and titles (black)
    LIGHT  light display text
    MONO   numbers in tables and logs
The names are decided at import time from the font file that exists, so a
module that imports UI before load() has run still gets the right name;
load() only registers the file before the first window opens. Without the
file the app uses Segoe UI, which every Windows has.
"""
import os
import ctypes

_FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "fonts")
)
_INTER_FILE = os.path.join(_FONT_DIR, "InterVariable.ttf")
_HAS_INTER = os.path.exists(_INTER_FILE)

if _HAS_INTER:
    UI    = "Inter Variable Text"
    HDR   = "Inter Variable Text SemiBold"
    HEAVY = "Inter Variable Text Black"
    LIGHT = "Inter Variable Text Light"
else:
    UI    = "Segoe UI"
    HDR   = "Segoe UI Semibold"
    HEAVY = "Segoe UI Black"
    LIGHT = "Segoe UI Light"
MONO = "Consolas"
# For a label that is one symbol (⤢ ⊡ ▾): a font that has it, instead of
# relying on Windows to find one (it does not always, see below)
SYMBOL = "Segoe UI Symbol"

# Symbols Inter does not have (arrows like ⤢, ▾, emoji) are drawn from
# another font by Windows - except in the HDR / HEAVY families at normal
# weight, which show an empty box instead. Text with such a symbol in those
# families adds "bold" (checked by tests/test_fonts.py).
SCALE = 1.0  # set by ui_scale.init() when window is maximized

_loaded = False


def load():
    """Register the bundled font for this process. Returns files loaded."""
    global _loaded
    if _loaded or not _HAS_INTER:
        return 1 if _loaded else 0
    try:
        # FR_PRIVATE (0x10): visible to this process only, gone on exit
        if ctypes.windll.gdi32.AddFontResourceExW(_INTER_FILE, 0x10, 0):
            _loaded = True
    except Exception:
        pass
    return 1 if _loaded else 0
