import os
import ctypes

_FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
)

UI   = "Segoe UI"
MONO = "Consolas"

def load():
    global UI
    loaded = 0
    candidates = [
        "InterVariable.ttf",
        "Inter-Regular.ttf",
        "Inter-Bold.ttf",
        "Inter-SemiBold.ttf",
        "Inter-Medium.ttf",
    ]
    for fname in candidates:
        path = os.path.join(_FONT_DIR, fname)
        if os.path.exists(path):
            try:
                ctypes.windll.gdi32.AddFontResourceW(path)
                loaded += 1
            except Exception:
                pass
    if loaded > 0:
        UI = "Inter"
    return loaded
