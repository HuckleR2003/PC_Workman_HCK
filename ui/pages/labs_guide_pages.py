"""ui/pages/labs_guide_pages.py - the HCK_Labs and Guide pages (2026-11-17).

Rebuilt for this release after Marcin asked for both to look much better and more
modern. They were static English blog pages, and the Guide's "What's new"
listed the previous version. Now:

HCK_Labs   gradient hero with the author and the projects, live numbers
           from this PC (learning, recorded hours, games, recordings), a
           version timeline, the projects and the principles behind them.
Guide      gradient hero with the LIVE tour, what is new in this version as
           cards, a three-step start, questions that ask hck_GPT on click,
           the feature map and the guides on pcworkman.dev.

Polish and English follow the interface language. Everything is plain Tk;
the gradients are drawn on a Canvas and redrawn when the page is resized.
"""
from __future__ import annotations

import time
import tkinter as tk

from utils.fonts import UI as _UI, HDR as _HDR, HEAVY as _HEAVY, LIGHT as _LIGHT

BG = "#070a12"
CARD = "#0d111c"
CARD_HI = "#121829"
BORDER = "#1b2236"
TEXT = "#e8edf5"
DIM = "#9aa7bd"
MUTED = "#6f7c92"
VIOLET = "#8b5cf6"
BLUE = "#3b82f6"
EMERALD = "#10b981"
AMBER = "#f59e0b"
ROSE = "#f43f5e"
CYAN = "#22d3ee"


def _pl() -> bool:
    try:
        from utils.i18n import get_lang
        return str(get_lang()).lower().startswith("pl")
    except Exception:
        return True


def L(pl: str, en: str) -> str:
    return pl if _pl() else en


def _version() -> tuple:
    try:
        from utils.app_version import APP_VERSION, RELEASE_DATE
        return APP_VERSION, RELEASE_DATE
    except Exception:
        return "?", ""


# ── building blocks ──────────────────────────────────────────────────────────
def _scroll_area(parent):
    cv = tk.Canvas(parent, bg=BG, highlightthickness=0)
    sb = tk.Scrollbar(parent, orient="vertical", command=cv.yview,
                      bg=BG, troughcolor=BG, width=6)
    sf = tk.Frame(cv, bg=BG)
    sf.bind("<Configure>", lambda e=None: cv.configure(scrollregion=cv.bbox("all")))
    wid = cv.create_window((0, 0), window=sf, anchor="nw")
    cv.configure(yscrollcommand=sb.set)
    cv.bind("<Configure>", lambda e=None: cv.itemconfig(wid, width=e.width))

    def _wheel(e):
        try:
            if cv.winfo_exists():
                cv.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass
    cv.bind_all("<MouseWheel>", _wheel)
    sb.pack(side="right", fill="y")
    cv.pack(side="left", fill="both", expand=True)
    return sf


def _mix(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def _gradient_hero(parent, height, stops, draw_text):
    """A Canvas band with a horizontal gradient through `stops`, darkened
    towards the bottom; draw_text(canvas, width) adds the content."""
    cv = tk.Canvas(parent, height=height, bg=BG, highlightthickness=0)
    cv.pack(fill="x")

    def _draw(_e=None):
        w = max(cv.winfo_width(), 600)
        cv.delete("all")
        # one gradient for every page header (ui/components/hero_banner)
        from ui.components.hero_banner import paint_gradient
        paint_gradient(cv, w, height, stops, BG)
        draw_text(cv, w)
    cv.bind("<Configure>", _draw)
    cv.after(30, _draw)
    return cv


def _section_title(parent, title, subtitle="", accent=VIOLET):
    wrap = tk.Frame(parent, bg=BG)
    wrap.pack(fill="x", padx=28, pady=(26, 10))
    row = tk.Frame(wrap, bg=BG)
    row.pack(fill="x")
    tk.Frame(row, bg=accent, width=4, height=18).pack(side="left", padx=(0, 10))
    tk.Label(row, text=title, font=(_HDR, 14, "bold"), bg=BG, fg=TEXT).pack(side="left")
    if subtitle:
        tk.Label(wrap, text=subtitle, font=(_UI, 9), bg=BG, fg=MUTED,
                 anchor="w").pack(anchor="w", padx=(14, 0), pady=(2, 0))


def _card(parent, accent, title, body, row, col, cols=3, foot="", on_click=None):
    outer = tk.Frame(parent, bg=BORDER)
    outer.grid(row=row, column=col, sticky="nsew",
               padx=(0, 10) if col < cols - 1 else 0, pady=(0, 10))
    inner = tk.Frame(outer, bg=CARD)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Frame(inner, bg=accent, height=3).pack(fill="x")
    body_f = tk.Frame(inner, bg=CARD)
    body_f.pack(fill="both", expand=True, padx=16, pady=(12, 14))
    head = tk.Frame(body_f, bg=CARD)
    head.pack(fill="x")
    tk.Frame(head, bg=accent, width=8, height=8).pack(side="left", padx=(0, 8))
    tk.Label(head, text=title, font=(_HDR, 11, "bold"), bg=CARD, fg=TEXT,
             anchor="w").pack(side="left")
    lab = tk.Label(body_f, text=body, font=(_UI, 9), bg=CARD, fg=DIM, anchor="w",
                   justify="left", wraplength=260)
    lab.pack(anchor="w", pady=(6, 0), fill="x")
    if foot:
        tk.Label(body_f, text=foot, font=(_UI, 8, "bold"), bg=CARD, fg=accent,
                 anchor="w").pack(anchor="w", pady=(8, 0))
    widgets = [inner, body_f, head, lab] + list(head.winfo_children())

    def _hover(on):
        col_ = CARD_HI if on else CARD
        outer.config(bg=accent if on else BORDER)
        for w in widgets:
            try:
                if w.cget("bg") in (CARD, CARD_HI):
                    w.config(bg=col_)
            except Exception:
                pass
        for w in body_f.winfo_children():
            try:
                w.config(bg=col_)
            except Exception:
                pass
    for w in widgets + list(body_f.winfo_children()):
        w.bind("<Enter>", lambda e=None: _hover(True), add="+")
        w.bind("<Leave>", lambda e=None: _hover(False), add="+")
        if on_click:
            w.bind("<Button-1>", lambda e=None: on_click(), add="+")
            try:
                w.config(cursor="hand2")
            except Exception:
                pass

    def _wrap(e):
        try:
            lab.config(wraplength=max(160, e.width - 36))
        except Exception:
            pass
    inner.bind("<Configure>", _wrap, add="+")
    return outer


def _grid(parent, cols=3, padx=28):
    g = tk.Frame(parent, bg=BG)
    g.pack(fill="x", padx=padx)
    for c in range(cols):
        g.columnconfigure(c, weight=1, uniform="cards")
    return g


def _pill_button(parent, text, bg, fg, cmd, hover=None):
    b = tk.Label(parent, text=text, font=(_HDR, 10, "bold"), bg=bg, fg=fg,
                 padx=18, pady=8, cursor="hand2")
    b.bind("<Button-1>", lambda e=None: cmd())
    if hover:
        b.bind("<Enter>", lambda e=None: b.config(bg=hover))
        b.bind("<Leave>", lambda e=None: b.config(bg=bg))
    return b


def _open(url):
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass


# ── live numbers from this PC ────────────────────────────────────────────────
def _live_numbers() -> list:
    out = []
    v, _d = _version()
    out.append((f"v{v}", L("wersja", "version"), VIOLET))
    try:
        from core.thermal_baseline import thermal_baseline as tb
        out.append((f"{tb.overall_training_pct()}%", L("nauczone o tym PC", "learned about this PC"), EMERALD))
    except Exception:
        pass
    try:
        from hck_stats_engine import history
        now = time.time()
        st = history.stats("cpu", now - 90 * 86400, now)
        if st.get("has_data"):
            out.append((f"{st['recorded_hours']:.0f} h", L("nagranej historii", "of recorded history"), BLUE))
    except Exception:
        pass
    try:
        from hck_stats_engine.load_periods import periods
        ps = [p for p in periods(time.time() - 30 * 86400, time.time()) if p.get("process_name")]
        if ps:
            out.append((f"{sum(p['minutes'] for p in ps) / 60:.1f} h",
                        L("grania w 30 dni", "of gaming in 30 days"), AMBER))
    except Exception:
        pass
    try:
        from hck_gpt.process_library import process_library
        out.append((str(len(process_library.processes)), L("znanych procesów", "known processes"), CYAN))
    except Exception:
        pass
    return out[:5]


def _stat_tiles(parent, items):
    g = _grid(parent, cols=len(items) or 1)
    for i, (big, small, col) in enumerate(items):
        outer = tk.Frame(g, bg=BORDER)
        outer.grid(row=0, column=i, sticky="nsew", padx=(0, 10) if i < len(items) - 1 else 0)
        inner = tk.Frame(outer, bg=CARD)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(inner, text=big, font=(_HEAVY, 20), bg=CARD, fg=col).pack(anchor="w", padx=16, pady=(12, 0))
        tk.Label(inner, text=small, font=(_UI, 9), bg=CARD, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 12))


# ═════════════════════════════════════════════════════════════════════════════
# HCK_Labs
# ═════════════════════════════════════════════════════════════════════════════
def build_hcklabs_page(win, parent):
    sf = _scroll_area(parent)
    v, rel = _version()

    def _hero_text(cv, w):
        cv.create_text(36, 40, anchor="nw", text="HCK_Labs", font=(_LIGHT, 34), fill=TEXT)
        cv.create_text(38, 96, anchor="nw",
                       text=L("Marcin „HCK” Firmuga · Polska · jedna osoba, bez studia",
                              "Marcin \"HCK\" Firmuga · Poland · one person, no studio"),
                       font=(_UI, 11), fill=DIM)
        cv.create_text(38, 122, anchor="nw",
                       text=L("Narzędzia, które mierzą zamiast zgadywać. Tworzone nocami, testowane na prawdziwym komputerze.",
                              "Tools that measure instead of guessing. Built at night, tested on a real PC."),
                       font=(_UI, 10), fill=MUTED, width=max(300, w - 380))
        cv.create_text(w - 36, 44, anchor="ne", text=f"v{v}", font=(_HEAVY, 22), fill=_mix(TEXT, VIOLET, 0.35))
        if rel:
            cv.create_text(w - 36, 80, anchor="ne", text=rel, font=(_UI, 9), fill=MUTED)

    _gradient_hero(sf, 180, ["#f59e0b", "#a855f7", "#3b82f6", "#0ea5e9"], _hero_text)

    btns = tk.Frame(sf, bg=BG)
    btns.pack(fill="x", padx=28, pady=(14, 0))
    _pill_button(btns, "pcworkman.dev", VIOLET, "#ffffff",
                 lambda: _open("https://pcworkman.dev"), hover="#7c3aed").pack(side="left", padx=(0, 10))
    _pill_button(btns, "GitHub", "#1f2937", TEXT,
                 lambda: _open("https://github.com/HuckleR2003/PC_Workman_HCK"), hover="#374151").pack(side="left", padx=(0, 10))
    _pill_button(btns, L("Sprawdź aktualizację", "Check for update"), EMERALD, "#04130d",
                 lambda: win._show_update_dialog(sf), hover="#34d399").pack(side="left", padx=(0, 10))
    _pill_button(btns, L("Usługi", "Services"), "#1f2937", TEXT,
                 lambda: win._show_services_dialog(sf), hover="#374151").pack(side="left")

    _section_title(sf, L("Ten komputer w liczbach", "This PC in numbers"),
                   L("Liczone na żywo z tego, co PC Workman tu zapisał.", "Counted live from what PC Workman recorded here."),
                   accent=EMERALD)
    _stat_tiles(sf, _live_numbers())

    _section_title(sf, L("Projekty", "Projects"), accent=AMBER)
    g = _grid(sf)
    _card(g, VIOLET, "PC Workman",
          L("Monitor i asystent komputera: historia obciążenia, nauka normy tego PC, hck_GPT, optymalizacja z pomiarem przed i po.",
            "A PC monitor and assistant: load history, learning this PC's normal, hck_GPT, optimization measured before and after."),
          0, 0, foot=f"v{v}")
    _card(g, AMBER, "Scaling Laws",
          L("Gra o prowadzeniu laboratorium AI. Budżet, badania, konkurencja i decyzje, które mają koszt.",
            "A game about running an AI lab. Budget, research, rivals and decisions that cost something."),
          0, 1, foot=L("w drodze na Steam", "on its way to Steam"),
          on_click=lambda: _open("https://pcworkman.dev"))
    _card(g, EMERALD, L("Poradniki", "Guides"),
          L("Ponad 20 poradników o realnych problemach z komputerem, po polsku i angielsku, bez logowania.",
            "20+ guides on real PC problems, in Polish and English, no signup."),
          0, 2, foot="pcworkman.dev", on_click=lambda: _open("https://pcworkman.dev"))

    _section_title(sf, L("Droga do tej wersji", "How we got here"), accent=BLUE)
    timeline = [
        ("1.7", L("Centrum optymalizacji, Live Guide, DeepMonitor", "Optimization center, Live Guide, DeepMonitor")),  # past release
        ("1.8.0", L("Nauka normy tego komputera, nakładka w grach", "Learning this PC's normal, in-game overlay")),  # past release
        ("1.8.5", L("Sprawdzanie zgodności części przed zakupem", "Part compatibility before you buy")),  # past release
        ("1.8.7", L("Przewodniki krok po kroku w hck_GPT", "Step-by-step guides in hck_GPT")),  # past release
        ("1.8.8", L("Stabilność, Pamięć aktywności, nauka z każdej minuty", "Stability, Activity Memory, learning from every minute")),  # past release
        (v, L("hck_GPT wyciąga wnioski, rozmowy, notatka obserwacyjna", "hck_GPT draws conclusions, conversations, observation note")),
    ]
    tl = tk.Frame(sf, bg=BG)
    tl.pack(fill="x", padx=36)
    for i, (ver, what) in enumerate(timeline):
        last = i == len(timeline) - 1
        row = tk.Frame(tl, bg=BG)
        row.pack(fill="x")
        rail = tk.Canvas(row, width=24, height=34, bg=BG, highlightthickness=0)
        rail.pack(side="left")
        col = VIOLET if last else _mix(BLUE, MUTED, 0.4)
        if i > 0:
            rail.create_line(12, 0, 12, 17, fill=BORDER, width=2)
        if not last:
            rail.create_line(12, 17, 12, 34, fill=BORDER, width=2)
        rail.create_oval(6, 11, 18, 23, fill=col, outline=col)
        tk.Label(row, text=ver, font=(_HDR, 10, "bold"), bg=BG, fg=TEXT if last else DIM,
                 width=7, anchor="w").pack(side="left", padx=(6, 0))
        tk.Label(row, text=what, font=(_UI, 10 if last else 9), bg=BG,
                 fg=TEXT if last else MUTED, anchor="w").pack(side="left")

    _section_title(sf, L("Zasady", "Principles"), accent=ROSE)
    g = _grid(sf)
    _card(g, BLUE, L("Mierzone, nie zgadywane", "Measured, not guessed"),
          L("Każda liczba na ekranie pochodzi z czujnika albo z historii. Czego Windows nie podaje, tego nie zmyślamy.",
            "Every number on screen comes from a sensor or the history. What Windows does not report, we do not invent."), 0, 0)
    _card(g, EMERALD, L("Twoje dane zostają u Ciebie", "Your data stays with you"),
          L("Historia, nauka i rozmowy są lokalnie. Anonimowa telemetria jest opisana i wyłączasz ją jednym kliknięciem.",
            "History, learning and chats stay local. Anonymous telemetry is described and off with one click."), 0, 1)
    _card(g, AMBER, L("Bez zmian bez zgody", "No changes without consent"),
          L("Optymalizacja pokazuje, co zrobi, i mierzy efekt. Nic nie wyłącza się samo w tle.",
            "Optimization shows what it will do and measures the effect. Nothing turns off by itself."), 0, 2)

    foot = tk.Frame(sf, bg=BG)
    foot.pack(fill="x", padx=28, pady=(26, 30))
    tk.Frame(foot, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
    tk.Label(foot, text=f"PC Workman HCK {v}" + (f" · {rel}" if rel else "") + " · Python / Tk · HCK_Labs",
             font=(_UI, 8), bg=BG, fg=MUTED).pack(anchor="w")


# ═════════════════════════════════════════════════════════════════════════════
# Guide
# ═════════════════════════════════════════════════════════════════════════════
_ASK = {"pl": ["Wszystko działa?", "Co spowalnia komputer?", "Czy mam wąskie gardło?",
           "Czy procesor osiąga boost?", "W co najwięcej grałem?", "Co o mnie pamiętasz?",
           "Zacznij nagrywanie", "Zoptymalizuj komputer"],
        "en": ["Is everything OK?", "What slows my PC?", "Do I have a bottleneck?",
           "Does my CPU reach its boost?", "What did I play the most?", "What do you remember about me?",
           "Start recording", "Optimize my PC"]}


def build_guide_page(win, parent):
    sf = _scroll_area(parent)
    v, rel = _version()

    def _hero_text(cv, w):
        cv.create_text(36, 34, anchor="nw", text=L("PRZEWODNIK", "GUIDE"), font=(_HDR, 9, "bold"),
                       fill=_mix(TEXT, CYAN, 0.5))
        cv.create_text(36, 54, anchor="nw", text=L("Poznaj PC Workman", "Get to know PC Workman"),
                       font=(_LIGHT, 30), fill=TEXT)
        cv.create_text(38, 104, anchor="nw",
                       text=L("Od wykresów na żywo po rozmowę z hck_GPT. Kliknij pytanie poniżej, a hck_GPT od razu odpowie.",
                              "From live charts to talking with hck_GPT. Click a question below and hck_GPT answers right away."),
                       font=(_UI, 10), fill=DIM, width=max(300, w - 420))
    _gradient_hero(sf, 160, ["#7c3aed", "#4f46e5", "#0891b2", "#10b981"], _hero_text)

    top = tk.Frame(sf, bg=BG)
    top.pack(fill="x", padx=28, pady=(14, 0))

    def _live():
        win._close_overlay()
        win.root.after(280, win._start_live_guide)
    _pill_button(top, L("Przewodnik LIVE po programie", "LIVE tour of the program"), VIOLET, "#ffffff",
                 _live, hover="#7c3aed").pack(side="left", padx=(0, 10))
    tk.Label(top, text=L("interaktywnie, krok po kroku, Esc kończy", "interactive, step by step, Esc ends it"),
             font=(_UI, 9), bg=BG, fg=MUTED).pack(side="left")

    # what is new in this version
    _section_title(sf, L(f"Nowości w {v}", f"New in {v}"),
                   L("Pełna lista: CHANGELOG.md", "The full list: CHANGELOG.md"), accent=EMERALD)
    g = _grid(sf, cols=4)
    news = [
        # 1.9.2 (2026-11-21)
        (EMERALD, L("Oczyszczanie", "Cleanup"),
         L("Pliki tymczasowe, pamięć przeglądarek i aplikacji, Kosz. Wynik analizy z paskami, usuwa tylko to, co zaznaczysz.",
           "Temporary files, browser and app caches, the Recycle Bin. A scan with bars; it removes only what you tick.")),
        (BLUE, L("Centrum procesów", "Process Center"),
         L("Każdy proces: co to jest, ile kosztuje teraz i przez 7 dni, czy można go zamknąć.",
           "Every process: what it is, what it costs now and over 7 days, whether it can be closed.")),
        (VIOLET, L("Test internetu", "Internet test"),
         L("„Sprawdź internet”, „jaki mam ping”: test połączenia, ocena i kroki, na życzenie pomiar prędkości.",
           "\"Check my internet\", \"what's my ping\": a connection test, a verdict and steps, a speed test on request.")),
        (AMBER, L("Mapa PC i gry", "PC map and games"),
         L("Nowa mapa podzespołów z temperaturami. Baza 228 gier z gatunkami i powitaniami.",
           "A new parts map with temperatures. A library of 228 games with genres and greetings.")),
    ]
    for i, (col, t, b) in enumerate(news):
        _card(g, col, t, b, 0, i, cols=4)

    # three steps
    _section_title(sf, L("Start w 3 krokach", "Start in 3 steps"), accent=BLUE)
    g = _grid(sf)
    steps = [
        ("1", L("Panel główny", "Dashboard"),
         L("Średnie sesji i karty CPU, RAM, GPU. Kliknij kartę, żeby zobaczyć jej historię.",
           "Session averages and the CPU, RAM, GPU cards. Click a card for its history.")),
        ("2", "hck_GPT",
         L("Pasek na dole. Pytaj zwykłymi słowami, odpowiedzi są z danych tego komputera.",
           "The bar at the bottom. Ask in plain words; answers come from this PC's data.")),
        ("3", L("Optymalizacja", "Optimization"),
         L("⚡ Optymalizacja w czacie prowadzi przez 6 kroków z pomiarem przed i po.",
           "⚡ Optimize in the chat walks through 6 steps measured before and after.")),
    ]
    for i, (n, t, b) in enumerate(steps):
        _card(g, [VIOLET, CYAN, EMERALD][i], f"{n}.  {t}", b, 0, i)

    # questions that ask hck_GPT
    _section_title(sf, L("Zapytaj hck_GPT", "Ask hck_GPT"),
                   L("Kliknięcie zamyka przewodnik i zadaje pytanie w czacie.", "A click closes the guide and asks in the chat."),
                   accent=CYAN)
    chips = tk.Frame(sf, bg=BG)
    chips.pack(fill="x", padx=28)
    qs = _ASK["pl"] if _pl() else _ASK["en"]

    def _ask(q):
        win._close_overlay()

        def _go():
            panel = getattr(win, "gpt_panel", None)
            if panel is not None:
                try:
                    panel.ask(q)
                except Exception:
                    pass
        win.root.after(320, _go)
    row = None
    for i, q in enumerate(qs):
        if i % 4 == 0:
            row = tk.Frame(chips, bg=BG)
            row.pack(fill="x", pady=(0, 8))
        c = tk.Label(row, text=q, font=(_UI, 10), bg=CARD, fg=TEXT, padx=14, pady=8,
                     cursor="hand2", highlightthickness=1, highlightbackground=BORDER)
        c.pack(side="left", padx=(0, 8))
        c.bind("<Button-1>", lambda e=None, q=q: _ask(q))
        c.bind("<Enter>", lambda e=None, c=c: c.config(highlightbackground=CYAN, bg=CARD_HI))
        c.bind("<Leave>", lambda e=None, c=c: c.config(highlightbackground=BORDER, bg=CARD))

    # feature map
    _section_title(sf, L("Co jest w programie", "What is in the program"), accent=VIOLET)
    g = _grid(sf)
    tiles = [
        (BLUE, L("Monitoring", "Monitoring"),
         L("CPU, GPU i RAM co sekundę, historia minutowa w bazie, wykresy od godziny do roku.",
           "CPU, GPU and RAM every second, minute history in a database, charts from an hour to a year.")),
        (EMERALD, L("Pamięć aktywności", "Activity Memory"),
         L("Okresy obciążenia z nazwą gry, uśpienia, najcięższe procesy każdego okresu.",
           "Busy stretches with the game's name, sleeps, the heaviest processes of any period.")),
        (ROSE, L("Nauka", "Learning"),
         L("Norma temperatur i obciążenia osobno dla bezczynności, pracy i grania.",
           "Normal temperatures and load, separately for idle, work and gaming.")),
        (AMBER, L("Optymalizacja", "Optimization"),
         L("TURBO, RAM Flush, autostart i usługi; każda zmiana z pokwitowaniem przed i po.",
           "TURBO, RAM Flush, startup and services; every change with a before-and-after receipt.")),
        (VIOLET, L("Mój PC", "My PC"),
         L("Podzespoły, sterowniki, zgodność części przed zakupem, testy stabilności.",
           "Components, drivers, part compatibility before buying, stability tests.")),
        (CYAN, L("W grze", "In game"),
         L("Nakładka z FPS, CPU, GPU i temperaturami; podsumowanie każdej sesji gry.",
           "An overlay with FPS, CPU, GPU and temperatures; a summary of every gaming session.")),
    ]
    for i, (col, t, b) in enumerate(tiles):
        _card(g, col, t, b, i // 3, i % 3)

    # guides on the site
    gb = tk.Frame(sf, bg=BORDER, cursor="hand2")
    gb.pack(fill="x", padx=28, pady=(22, 30))
    gi = tk.Frame(gb, bg=CARD, cursor="hand2")
    gi.pack(fill="both", expand=True, padx=1, pady=1)
    tk.Frame(gi, bg=AMBER, height=3).pack(fill="x")
    inner = tk.Frame(gi, bg=CARD)
    inner.pack(fill="x", padx=18, pady=14)
    tk.Label(inner, text=L("PORADNIKI NA PCWORKMAN.DEV", "GUIDES ON PCWORKMAN.DEV"), font=(_HDR, 9, "bold"),
             bg=CARD, fg=AMBER).pack(anchor="w")
    tk.Label(inner, text=L("Głośne wentylatory, dysk na 100%, nieznany proces, wymiana podzespołów: ponad 20 poradników, za darmo i bez logowania.",
                           "Loud fans, disk at 100%, an unknown process, planning an upgrade: 20+ guides, free and with no signup."),
             font=(_UI, 10), bg=CARD, fg=TEXT, justify="left", wraplength=900).pack(anchor="w", pady=(4, 0))
    tk.Label(inner, text=L("Otwórz w przeglądarce  →", "Open in your browser  →"), font=(_UI, 9, "bold"),
             bg=CARD, fg=DIM).pack(anchor="w", pady=(6, 0))
    url = "https://pcworkman.dev/index_pl.html" if _pl() else "https://pcworkman.dev/"
    for w in (gb, gi, inner, *inner.winfo_children()):
        w.bind("<Button-1>", lambda e=None: _open(url))
