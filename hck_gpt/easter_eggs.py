"""
hck_gpt/easter_eggs.py
======================
Hidden, opt-in meme scenes for hck_GPT.

Typing a secret trigger ("surprise 1", "sauce", "ketchup", ...) plays a scene:
  • a SILENT alien/laser animation in a small strip at the TOP of the chat
    (~30% height) - a funny top add-on,
  • the lyric "words" arriving as normal hck_GPT chat MESSAGES at the bottom,
    in sync, with dynamic background colouring,
then a confused greeting + the normal command list.

The app stays SILENT - the viral audio is added later in video editing; only the
RHYTHM of this TIMELINE has to match the track. Tune by editing the ms offsets.

Scene 1 timings tapped against `meme_pro.mp3` (14 s).
"""
import random

# Vivid colours for the laser show.
_BULLET_COLORS = ["#39ff14", "#ff1493", "#00e5ff", "#ffe600", "#ff4d00", "#bf00ff", "#ffffff"]
_FLASH_COLORS  = ["#5a0030", "#003a5a", "#3a3a00", "#3a0000", "#00103a", "#06300f"]
_GLOW_COLORS   = ["#22ff88", "#ff44cc", "#44aaff", "#ffcc22", "#ff5555", "#aa66ff"]

# ── Scene 1: "Sauce" ──────────────────────────────────────────────────────────
# (offset_ms, kind, payload)   kind: word | laser("R"/"L") | poop | end
# Every beat locked to a REAL onset detected in Meme.wav (16.5 s, numpy onset
# detection). Words ride the early hits; the three laser volleys sit on the three
# rapid-fire clusters; 💩 spam covers the loud chaotic finale.
_SURPRISE_1 = [
    (300,   "word", "SOS"),
    (900,   "word", "sauce"),
    (1500,  "word", "no ketchup"),   # ear-confirmed
    (2150,  "word", "NAH"),
    (2900,  "word", "JUST SAUCE"),    # ear-confirmed
    (3500,  "word", "SASUAGE"),
    (4100,  "word", "RAW SAUCE"),     # ear-confirmed
    (4900,  "word", "AH"),
    (5750,  "word", "YO"),            # ear-confirmed
    (6350,  "word", "HUUH"),
    (6900,  "word", "HA"),
    (7403,  "word", "OHHHH"),         # ideal (kept)
    (8461,  "word", "The"),           # ideal (kept)
    (8825,  "word", "tingles."),      # ideal (kept)
    # RIGHT x3 - real cluster 9174-9344
    (9174,  "laser", "R"), (9244, "laser", "R"), (9344, "laser", "R"),
    (9873,  "word", "AND A"),
    # LEFT x6 - real cluster 10227-10756
    (10227, "laser", "L"), (10312, "laser", "L"), (10401, "laser", "L"),
    (10561, "laser", "L"), (10656, "laser", "L"), (10756, "laser", "L"),
    (11010, "word", "HA"),
    # RIGHT x4 - real cluster 11224-11459
    (11224, "laser", "R"), (11284, "laser", "R"), (11364, "laser", "R"), (11459, "laser", "R"),
    # ── chaotic finale: lasers + 💩 alternating across 11.6-16.2s (real onsets),
    #    including the 14-16s stretch that was empty before ──
    (11639, "laser", "L"), (11733, "laser", "L"),
    (12167, "poop",  None),
    (12272, "laser", "R"), (12352, "laser", "R"), (12422, "laser", "R"),
    (12696, "poop",  None),
    (13050, "laser", "L"), (13125, "laser", "L"), (13235, "laser", "L"),
    (13405, "poop",  None),
    (14108, "laser", "R"), (14188, "laser", "R"), (14283, "laser", "R"), (14372, "laser", "R"),
    (14462, "poop",  None),
    (14816, "laser", "L"), (14891, "laser", "L"), (14991, "laser", "L"),
    (15171, "poop",  None),
    (15520, "laser", "R"), (15600, "laser", "R"), (15694, "laser", "R"),
    (15874, "poop",  None),
    (16222, "laser", "L"),
    (16450, "end",   None),
]

# Secret triggers -> scene. Exact-match only (whole input), so normal questions
# like "is ketchup a process?" never fire it.
TRIGGERS = {
    "surprise 1": _SURPRISE_1, "surprise1": _SURPRISE_1,
    "sauce": _SURPRISE_1, "no sauce": _SURPRISE_1,
    "ketchup": _SURPRISE_1, "no ketchup": _SURPRISE_1,
    "sos": _SURPRISE_1,
}


def match(text: str):
    """Return the scene timeline for an exact secret trigger, else None."""
    if not text:
        return None
    return TRIGGERS.get(text.strip().lower())


def play(canvas, timeline, *, on_word, on_poop, on_end, width, height) -> None:
    """Run *timeline*. Lasers/aliens draw on *canvas* (the small TOP strip); word
    and poop beats fire the on_word / on_poop callbacks (the panel turns those
    into chat messages). on_end fires once, on the "end" beat. Every callback
    guards against the canvas being destroyed mid-scene.
    """
    W = max(int(width or 0), 200)
    H = max(int(height or 0), 48)
    cy = H // 2
    base_bg = canvas.cget("bg")
    state = {"tick": 0}
    aliens = []   # [{glow, em, x}]

    def alive() -> bool:
        try:
            return bool(canvas.winfo_exists())
        except Exception:
            return False

    def make_alien(x):
        glow = canvas.create_oval(x - 17, cy - 17, x + 17, cy + 17,
                                  fill=random.choice(_GLOW_COLORS), outline="")
        em = canvas.create_text(x, cy, text="👾", font=("Segoe UI Emoji", 22))
        aliens.append({"glow": glow, "em": em, "x": x})

    def bob():
        # gentle up/down bob + glow recolour, so the aliens look alive the whole time
        if not alive():
            return
        state["tick"] += 1
        dy = 2 if (state["tick"] // 3) % 2 == 0 else -2   # nets 0 every 6 ticks
        for a in aliens:
            try:
                canvas.move(a["glow"], 0, dy)
                canvas.move(a["em"], 0, dy)
                if state["tick"] % 4 == 0:
                    canvas.itemconfig(a["glow"], fill=random.choice(_GLOW_COLORS))
            except Exception:
                pass
        canvas.after(110, bob)

    def flash():
        if not alive():
            return
        try:
            canvas.config(bg=random.choice(_FLASH_COLORS))
            canvas.after(70, lambda: alive() and canvas.config(bg=base_bg))
        except Exception:
            pass

    def impact(x, y, color):
        if not alive():
            return
        sid = canvas.create_text(x, y, text="✸", fill=color, font=("Segoe UI", 24, "bold"))
        canvas.after(200, lambda: alive() and canvas.delete(sid))

    def _fly(bid, step, target_x, color, y):
        if not alive():
            return
        try:
            canvas.move(bid, step, 0)
            x = canvas.coords(bid)[0]
        except Exception:
            return
        if (step > 0 and x < target_x) or (step < 0 and x > target_x):
            canvas.after(16, lambda: _fly(bid, step, target_x, color, y))
        else:
            try:
                canvas.delete(bid)
            except Exception:
                pass
            impact(target_x, y, color)

    def laser(direction):
        if not alive():
            return
        flash()
        color = random.choice(_BULLET_COLORS)
        speed = max(42, W // 8)          # a touch slower -> the shot lasts longer
        y = cy
        if direction == "R":
            x0 = (aliens[0]["x"] + 18) if aliens else 40
            mz = canvas.create_text(x0, y, text="✦", fill=color, font=("Segoe UI", 19, "bold"))
            canvas.after(120, lambda: alive() and canvas.delete(mz))
            bid = canvas.create_text(x0 + 14, y, text="▰▰▰▰►", fill=color,
                                     font=("Consolas", 15, "bold"))
            _fly(bid, speed, W - 8, color, y)
        else:
            x0 = (aliens[1]["x"] - 18) if len(aliens) > 1 else (W - 40)
            mz = canvas.create_text(x0, y, text="✦", fill=color, font=("Segoe UI", 19, "bold"))
            canvas.after(120, lambda: alive() and canvas.delete(mz))
            bid = canvas.create_text(x0 - 14, y, text="◄▰▰▰▰", fill=color,
                                     font=("Consolas", 15, "bold"))
            _fly(bid, -speed, 8, color, y)

    def run(kind, payload):
        if kind == "word":
            if on_word:
                on_word(payload)
        elif kind == "poop":
            if on_poop:
                on_poop()
        elif kind == "laser":
            laser(payload)
        elif kind == "end":
            if on_end:
                on_end()

    # init: two idle aliens at the top, bobbing
    if alive():
        make_alien(34)
        make_alien(W - 34)
        bob()

    for ms, kind, payload in timeline:
        try:
            canvas.after(int(ms), lambda k=kind, p=payload: run(k, p))
        except Exception:
            pass
