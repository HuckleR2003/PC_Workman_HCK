"""
core/machine_type.py - laptop or desktop (2026-11-16).

hck_GPT told a desktop owner "Most laptops have 1-2 M.2/SATA slots", and
"thanks, I have a PC" was not remembered. Now:
  - what the user says ("mam PC", "I have a laptop") is stored as a fact
    and always wins;
  - otherwise Windows is asked whether the machine has a system battery
    (GetSystemPowerStatus): a battery means a laptop. A desktop on a UPS
    reports no system battery, so it stays a desktop.
"""
from __future__ import annotations

import re

FACT_KEY = "machine_type"

_LAPTOP_RX = re.compile(r"\b(laptop\w*|notebook\w*|lapka|lapek)\b", re.I)
_DESKTOP_RX = re.compile(
    r"\b(pc|peceta?|stacjonark\w*|stacjonarn\w*|desktop\w*|tower|blaszak\w*|"
    r"komputer stacjonarny)\b", re.I)
_OWN_RX = re.compile(r"\b(mam|to jest|to|i have|it'?s|it is|my)\b", re.I)


def detect() -> str | None:
    """'laptop' | 'desktop' | None from the power status."""
    try:
        import ctypes

        class _SPS(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_ubyte),
                        ("BatteryFlag", ctypes.c_ubyte),
                        ("BatteryLifePercent", ctypes.c_ubyte),
                        ("SystemStatusFlag", ctypes.c_ubyte),
                        ("BatteryLifeTime", ctypes.c_ulong),
                        ("BatteryFullLifeTime", ctypes.c_ulong)]
        st = _SPS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
            return None
        if st.BatteryFlag == 255:          # unknown
            return None
        return "desktop" if st.BatteryFlag & 128 else "laptop"
    except Exception:
        return None


def get() -> str | None:
    """What the user said, else what Windows reports."""
    try:
        from hck_gpt.memory.user_knowledge import user_knowledge
        said = user_knowledge.get_fact(FACT_KEY, "")
        if said in ("laptop", "desktop"):
            return said
    except Exception:
        pass
    return detect()


# "mam PC", "to laptop", "I have a desktop": the owning word right before
# the machine word. 2026-11-17: "my" and a lone "pc" anywhere were enough
# before, so "my pc is slow" and "is my pc fine" got "Noted - this is a
# desktop" instead of an answer.
_STATE_RX = re.compile(
    r"\b(?:mam|posiadam|u[zż]ywam|i have|i own|i use|i'?m on|it'?s|it is|this is|"
    r"to jest|to)\s+(?:a\s+|an\s+|taki\s+|zwyk[lł]y\s+|zwyk[lł]ego\s+)?"
    r"(laptop\w*|notebook\w*|lapk\w*|lapek|pc|peceta?|stacjonark\w*|stacjonarn\w*|"
    r"desktop\w*|tower|blaszak\w*)\b", re.I)


def from_message(text: str) -> str | None:
    """'laptop' / 'desktop' when the message states what the machine is
    ("mam PC", "jak cos mam pc", "I have a laptop"), else None."""
    t = (text or "").lower().replace("pc workman", " ")
    kinds = {"laptop" if _LAPTOP_RX.search(m.group(1)) else "desktop"
             for m in _STATE_RX.finditer(t)}
    if len(kinds) != 1:
        return None
    return kinds.pop()


def statement_only(text: str) -> bool:
    """True when the message is just that statement ("dzięki, jak coś mam
    PC"), so a short acknowledgement is the whole answer; a message with
    more in it ("mam laptopa i strasznie się grzeje") is answered normally."""
    t = (text or "").lower()
    rest = _STATE_RX.sub(" ", t)
    rest = re.sub(r"[^\w\s]", " ", rest)
    filler = {"dzieki", "dzięki", "jak", "cos", "coś", "co", "ok", "okej", "spoko",
              "thanks", "btw", "a", "i", "no", "tak", "yes", "just", "fyi", "and",
              "ale", "przy", "okazji", "by", "the", "way"}
    return len([w for w in rest.split() if w not in filler]) <= 1


def remember(kind: str) -> None:
    try:
        from hck_gpt.memory.user_knowledge import user_knowledge
        user_knowledge.set_fact(FACT_KEY, kind, source="user")
    except Exception:
        pass
