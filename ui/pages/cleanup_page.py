"""ui.pages.cleanup_page - Cleanup (2026-11-20).

My PC's "Cleanup" button had no page behind it. Two columns, like the
cleaners people know:
  * left: what to clean, in groups (Windows, Browsers, Apps, Your files),
    a box per item and per group; the choice is remembered, except for the
    user's own files and the Recycle Bin, which always start unticked;
  * right: what the scan found, biggest first, with a bar and the files one
    click away; below it, tips from hck_GPT that follow from this scan.
core/cleanup.py has the rules (which folders, what is skipped, what goes to
the Recycle Bin). Nothing is removed before a confirmation with the amount.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox

from utils.fonts import UI as _BODY, HDR as _HDR, MONO as _MONO

BG = "#0a0e14"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
DIM = "#64748b"
GREEN = "#34d399"
AMBER = "#fbbf24"
VIOLET = "#a78bfa"
BAR_BG = "#1b2330"

LEFT_W = 300

_TX = {
    "title": {"pl": "Oczyszczanie", "en": "Cleanup"},
    "sub": {"pl": "Pliki tymczasowe i pamięć podręczną Windows i programy odtwarzają same. Twoje pliki idą najwyżej do Kosza.",
            "en": "Windows and the programs rebuild their temporary files and caches. Your own files go to the Recycle Bin at most."},
    "clean": {"pl": "Wyczyść zaznaczone", "en": "Clean the selected"},
    "opt": {"pl": "Centrum optymalizacji", "en": "Optimization Center"},
    "rescan": {"pl": "Skanuj ponownie", "en": "Scan again"},
    "scanning": {"pl": "Skanuję foldery…", "en": "Scanning the folders…"},
    "what": {"pl": "CO WYCZYŚCIĆ", "en": "WHAT TO CLEAN"},
    "found": {"pl": "WYNIK ANALIZY", "en": "WHAT THE SCAN FOUND"},
    "can": {"pl": "MOŻESZ ODZYSKAĆ", "en": "YOU CAN FREE"},
    "sel": {"pl": "ZAZNACZONE", "en": "SELECTED"},
    "sel_v": {"pl": "{n} pozycji", "en": "{n} items"},
    "last": {"pl": "OSTATNIE CZYSZCZENIE", "en": "LAST CLEANUP"},
    "last_v": {"pl": "{n} plików", "en": "{n} files"},
    "never": {"pl": "jeszcze nie było", "en": "none yet"},
    "show": {"pl": "Pokaż pliki", "en": "Show files"},
    "hide": {"pl": "Ukryj pliki", "en": "Hide files"},
    "files": {"pl": "{n} plików", "en": "{n} files"},
    "admin": {"pl": "Wymaga uruchomienia jako administrator.", "en": "Needs run as administrator."},
    "running": {"pl": "Pominięte, program jest otwarty: {b}.", "en": "Skipped, the program is open: {b}."},
    "nothing": {"pl": "Skan nie znalazł nic do usunięcia.", "en": "The scan found nothing to remove."},
    "quick": {"pl": "SZYBKIE AKCJE", "en": "QUICK ACTIONS"},
    "dns": {"pl": "Wyczyść pamięć DNS", "en": "Flush the DNS cache"},
    "dns_d": {"pl": "Pomaga, gdy strona nie chce się otworzyć po zmianie sieci. Nic nie usuwa z dysku.",
              "en": "Helps when a site will not open after a network change. Removes nothing from the disk."},
    "dns_ok": {"pl": "✓ Pamięć DNS wyczyszczona.", "en": "✓ DNS cache flushed."},
    "dns_err": {"pl": "Nie udało się wyczyścić pamięci DNS.", "en": "Could not flush the DNS cache."},
    "confirm_t": {"pl": "Wyczyścić?", "en": "Clean up?"},
    "confirm": {"pl": "Usunę {s} z: {c}.\n\nPliki tymczasowe i pamięć podręczna znikną na stałe (Windows i programy odtworzą je, gdy będą potrzebne).{bin}{dl}\n\nKontynuować?",
                "en": "I will remove {s} from: {c}.\n\nTemporary files and caches are deleted for good (Windows and the programs rebuild them when needed).{bin}{dl}\n\nContinue?"},
    "confirm_bin": {"pl": "\nOpróżnienia Kosza nie da się cofnąć.", "en": "\nEmptying the Recycle Bin cannot be undone."},
    "confirm_dl": {"pl": "\nDuże pliki z Pobranych trafią do Kosza.", "en": "\nBig files from Downloads go to the Recycle Bin."},
    "working": {"pl": "Czyszczę…", "en": "Cleaning…"},
    "done": {"pl": "✓ Zwolniono {s}: {n} plików. Pominięte (w użyciu): {k}.",
             "en": "✓ Freed {s}: {n} files. Skipped (in use): {k}."},
    "tips": {"pl": "hck_GPT: CO JESZCZE PRZYSPIESZY KOMPUTER", "en": "hck_GPT: WHAT ELSE SPEEDS THE PC UP"},
    "ask": {"pl": "Zapytaj hck_GPT", "en": "Ask hck_GPT"},
    "ask_q": {"pl": "jak przyspieszyć komputer", "en": "how to speed up my pc"},
}

_GROUP = {
    "windows": {"pl": "Windows", "en": "Windows"},
    "browsers": {"pl": "Przeglądarki", "en": "Browsers"},
    "apps": {"pl": "Aplikacje", "en": "Apps"},
    "files": {"pl": "Twoje pliki", "en": "Your files"},
}

# key: (name, one line of what it is)
_CAT = {
    "user_temp": ({"pl": "Pliki tymczasowe", "en": "Temporary files"},
                  {"pl": "Folder TEMP Twojego konta: resztki instalatorów i programów. Bez plików z ostatniej doby.",
                   "en": "Your account's TEMP folder: leftovers of installers and programs. Not the last day's files."}),
    "windows_temp": ({"pl": "Pliki tymczasowe Windows", "en": "Windows temporary files"},
                     {"pl": "Folder Windows\\Temp.", "en": "The Windows\\Temp folder."}),
    "thumb_cache": ({"pl": "Miniatury Eksploratora", "en": "Explorer thumbnails"},
                    {"pl": "Podglądy zdjęć i filmów w folderach. Eksplorator zrobi je od nowa; te w użyciu pominę.",
                     "en": "Previews of photos and videos in folders. Explorer makes them again; those in use are skipped."}),
    "error_reports": ({"pl": "Raporty błędów i zrzuty awarii", "en": "Error reports and crash dumps"},
                      {"pl": "Raporty, które Windows zebrał po awariach programów, i ich zrzuty pamięci.",
                       "en": "Reports Windows collected after programs crashed, and their memory dumps."}),
    "system_reports": ({"pl": "Raporty systemowe i minidumpy", "en": "System reports and minidumps"},
                       {"pl": "Raporty błędów całego systemu i zrzuty po niebieskich ekranach.",
                        "en": "System-wide error reports and dumps after blue screens."}),
    "shader_cache": ({"pl": "Pamięć podręczna shaderów", "en": "Shader cache"},
                     {"pl": "Skompilowane shadery NVIDIA, AMD i DirectX. Gra odbuduje je przy pierwszym starcie.",
                      "en": "Compiled NVIDIA, AMD and DirectX shaders. A game rebuilds them on its first start."}),
    "update_cache": ({"pl": "Pobrane aktualizacje Windows", "en": "Downloaded Windows updates"},
                     {"pl": "Pliki instalacyjne aktualizacji, które już są zainstalowane.",
                      "en": "Setup files of updates already installed."}),
    "delivery_opt": ({"pl": "Optymalizacja dostarczania", "en": "Delivery Optimization"},
                     {"pl": "Kopie aktualizacji, które Windows trzyma dla innych komputerów.",
                      "en": "Copies of updates Windows keeps to share with other PCs."}),
    "br_chrome": ({"pl": "Chrome", "en": "Chrome"},
                  {"pl": "Pamięć podręczna stron. Bez haseł, historii i ciasteczek.",
                   "en": "The page cache. No passwords, history or cookies."}),
    "br_edge": ({"pl": "Edge", "en": "Edge"},
                {"pl": "Pamięć podręczna stron. Bez haseł, historii i ciasteczek.",
                 "en": "The page cache. No passwords, history or cookies."}),
    "br_brave": ({"pl": "Brave", "en": "Brave"},
                 {"pl": "Pamięć podręczna stron. Bez haseł, historii i ciasteczek.",
                  "en": "The page cache. No passwords, history or cookies."}),
    "br_opera": ({"pl": "Opera", "en": "Opera"},
                 {"pl": "Pamięć podręczna stron. Bez haseł, historii i ciasteczek.",
                  "en": "The page cache. No passwords, history or cookies."}),
    "br_operagx": ({"pl": "Opera GX", "en": "Opera GX"},
                   {"pl": "Pamięć podręczna stron. Bez haseł, historii i ciasteczek.",
                    "en": "The page cache. No passwords, history or cookies."}),
    "br_firefox": ({"pl": "Firefox", "en": "Firefox"},
                   {"pl": "Pamięć podręczna stron. Bez haseł, historii i ciasteczek.",
                    "en": "The page cache. No passwords, history or cookies."}),
    "app_discord": ({"pl": "Discord", "en": "Discord"},
                    {"pl": "Obrazki, filmy i kod, które Discord trzyma, żeby nie pobierać ich drugi raz.",
                     "en": "Images, videos and code Discord keeps so it does not download them again."}),
    "app_steam": ({"pl": "Steam (przeglądarka sklepu)", "en": "Steam (store browser)"},
                  {"pl": "Pamięć podręczna stron sklepu i biblioteki. Gry i zapisy zostają.",
                   "en": "The cache of the store and library pages. Games and saves stay."}),
    "app_spotify": ({"pl": "Spotify", "en": "Spotify"},
                    {"pl": "Utwory odtworzone online. Pobrane do słuchania offline zostają.",
                     "en": "Songs streamed online. Those downloaded for offline stay."}),
    "big_downloads": ({"pl": "Duże pliki w Pobranych", "en": "Big files in Downloads"},
                      {"pl": "Ponad 100 MB i starsze niż 90 dni. Twoje pliki: nie zaznaczam ich sam, trafią do Kosza.",
                       "en": "Over 100 MB, older than 90 days. Your files: never ticked by me, they go to the Recycle Bin."}),
    "recycle_bin": ({"pl": "Kosz", "en": "Recycle Bin"},
                    {"pl": "Opróżnienia nie da się cofnąć, dlatego nie zaznaczam go sam.",
                     "en": "Emptying it cannot be undone, so I never tick it myself."}),
}

# never remembered as ticked: the user's own files and the permanent one
_ALWAYS_MANUAL = ("big_downloads", "recycle_bin")

_TIP = {
    "temp": {"pl": "Pliki tymczasowe zajmują {s}. To miejsce na dysku, nie szybkość: komputer nie przyspieszy od samego usunięcia, ale aktualizacje i instalatory przestaną się dusić.",
             "en": "Temporary files take {s}. That is disk space, not speed: the PC will not get faster from this alone, but updates and installers stop running short."},
    "disk": {"pl": "Na dysku {d} zostało {p}% wolnego. Poniżej około 10% Windows zwalnia przy aktualizacjach i pliku stronicowania, więc tu czyszczenie naprawdę pomaga.",
             "en": "Drive {d} has {p}% free. Below about 10% Windows slows down on updates and the page file, so here cleaning really helps."},
    "shader": {"pl": "Pamięć shaderów ({s}) czyść raczej po zmianie sterownika karty albo gdy gra ma błędy grafiki. Na co dzień przyspiesza ładowanie gier.",
               "en": "Clear the shader cache ({s}) after a graphics driver change or when a game shows glitches. Day to day it makes games load faster."},
    "running": {"pl": "Zamknij {b}, a przy następnym skanie wyczyszczę też ich pamięć podręczną.",
                "en": "Close {b} and the next scan will clear their cache too."},
    "admin": {"pl": "Część pozycji (raporty systemowe, pobrane aktualizacje) wymaga uruchomienia PC Workman jako administrator.",
              "en": "Some items (system reports, downloaded updates) need PC Workman run as administrator."},
    "startup": {"pl": "Największą różnicę przy starcie robi Autostart: programy, które ruszają z Windows, a których nie używasz.",
                "en": "The biggest difference at boot is Startup: programs that start with Windows that you do not use."},
    "services": {"pl": "Usługi pokażą, co działa w tle bez Twojej wiedzy; wyłączysz tylko to, co jest bezpieczne.",
                 "en": "Services show what runs in the background; you turn off only what is safe."},
    "opt": {"pl": "Centrum optymalizacji: plan zasilania, RAM Flush i reszta narzędzi w jednym miejscu.",
            "en": "Optimization Center: the power plan, RAM Flush and the other tools in one place."},
    "go_startup": {"pl": "Autostart", "en": "Startup"},
    "go_services": {"pl": "Usługi", "en": "Services"},
    "go_opt": {"pl": "Otwórz", "en": "Open"},
}


def _lang():
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(k, **kw):
    s = _TX[k][_lang()]
    return s.format(**kw) if kw else s


def _size(n):
    from core.cleanup import fmt_size
    return fmt_size(n, _lang())


def _name(key, lang):
    return _CAT.get(key, ({"pl": key, "en": key},))[0][lang]


def visible(c) -> bool:
    """Items whose folders do not exist on this PC are not shown at all."""
    return bool(c.folders) or c.key == "recycle_bin"


def _drive_free():
    try:
        import os
        import shutil
        d = (os.environ.get("SystemDrive") or "C:") + "\\"
        u = shutil.disk_usage(d)
        return d.rstrip("\\"), round(100 * u.free / u.total)
    except Exception:
        return None, None


def speed_tips(cats, lang="pl", drive=None, free_pct=None):
    """[(text, (button text, action) or None)] from this scan; action is a
    page id. Pure: no Tk, the free space comes in from the caller."""
    lang = "en" if lang == "en" else "pl"
    by = {c.key: c for c in cats}

    def t(k, **kw):
        return _TIP[k][lang].format(**kw) if kw else _TIP[k][lang]
    from core.cleanup import fmt_size
    out = []
    if free_pct is not None and free_pct < 15:
        out.append((t("disk", d=drive or "C:", p=free_pct), None))
    tmp = by.get("user_temp")
    if tmp and tmp.size >= 1024 ** 3:
        out.append((t("temp", s=fmt_size(tmp.size, lang)), None))
    sh = by.get("shader_cache")
    if sh and sh.size >= 500 * 1024 ** 2:
        out.append((t("shader", s=fmt_size(sh.size, lang)), None))
    running = sorted({_name(c.key, lang) for c in cats
                      if c.note.startswith("running:") and visible(c)})
    if running:
        out.append((t("running", b=", ".join(running)), None))
    if any(c.note == "admin" and visible(c) for c in cats):
        out.append((t("admin"), None))
    out.append((t("startup"), (t("go_startup"), "startup_manager")))
    out.append((t("services"), (t("go_services"), "services_manager")))
    out.append((t("opt"), (t("go_opt"), "optimization")))
    return out


class _Shared:
    """Plain data for the worker threads (no Tk objects)."""
    def __init__(self):
        self.cats = None
        self.result = None
        self.dns = None


def _scan_worker(sh):
    try:
        from core.cleanup import scan
        sh.cats = scan()
    except Exception as e:
        print(f"[Cleanup] scan: {e}")
        sh.cats = []


def _clean_worker(sh, cats):
    try:
        from core.cleanup import clean
        sh.result = clean(cats)
    except Exception as e:
        sh.result = {"freed": 0, "files": 0, "skipped": 0, "per": {}, "error": str(e)}


def _dns_worker(sh):
    from core.cleanup import flush_dns
    sh.dns = flush_dns()


class CleanupPage:

    def __init__(self, app, parent):
        self.app = app
        self.sh = _Shared()
        self.cats = []
        self.open_preview = set()
        self.saved = self._load_choice()
        self.root = tk.Frame(parent, bg=BG)
        self.root.pack(fill="both", expand=True)
        from ui.components.hero_banner import hero_banner, nav_crumbs
        crumbs = nav_crumbs(app, _tx("title"), [(_tx("opt"), "optimization")])
        hero_banner(self.root, _tx("title"), _tx("sub"), stops=["#0ea5e9", "#22c55e", "#84cc16"],
                    height=112, crumbs=crumbs,
                    buttons=[(_tx("clean"), self._clean, True), (_tx("rescan"), self._scan, False)])

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=(10, 12))
        cv = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
        body = tk.Frame(cv, bg=BG)
        win = cv.create_window((0, 0), window=body, anchor="nw")
        cv.bind("<Configure>", lambda e=None: cv.itemconfigure(win, width=e.width))
        body.bind("<Configure>", lambda e=None: cv.configure(scrollregion=cv.bbox("all")))
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        cv.bind_all("<MouseWheel>", lambda e=None: cv.yview_scroll(int(-e.delta / 120), "units")
                    if e is not None and cv.winfo_exists() else None)

        self.left = tk.Frame(body, bg=PANEL, width=LEFT_W, highlightthickness=1, highlightbackground=LINE)
        self.left.pack(side="left", fill="y", anchor="n")
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0), anchor="n")

        tiles = tk.Frame(right, bg=BG)
        tiles.pack(fill="x")
        self.t_can = self._tile(tiles, _tx("can"), GREEN)
        self.t_sel = self._tile(tiles, _tx("sel"), TEXT)
        self.t_last = self._tile(tiles, _tx("last"), TEXT, last=True)
        self.status = tk.Label(right, text="", font=(_BODY, 9, "bold"), bg=BG, fg=GREEN, anchor="w",
                               justify="left", wraplength=640)
        self.status.pack(fill="x", pady=(6, 0))
        self.found = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        self.found.pack(fill="x", pady=(6, 0))
        self.tips = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground="#3b2f63")
        self.tips.pack(fill="x", pady=(10, 0))
        self._show_last()
        self._scan()

    # ── pieces ───────────────────────────────────────────────────────────
    def _tile(self, parent, cap, col, last=False):
        f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        f.pack(side="left", fill="x", expand=True, padx=(0, 0 if last else 8))
        tk.Label(f, text=cap, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", padx=12, pady=(6, 0))
        v = tk.Label(f, text="…", font=(_HDR, 15, "bold"), bg=PANEL, fg=col, anchor="w")
        v.pack(fill="x", padx=12)
        s = tk.Label(f, text="", font=(_BODY, 7), bg=PANEL, fg=DIM, anchor="w")
        s.pack(fill="x", padx=12, pady=(0, 6))
        return v, s

    def _caption(self, parent, text, bg=PANEL, fg=MUTED):
        tk.Label(parent, text=text, font=(_BODY, 8, "bold"), bg=bg, fg=fg, anchor="w").pack(
            fill="x", padx=12, pady=(10, 4))

    def _alive(self):
        try:
            return bool(self.root.winfo_exists())
        except Exception:
            return False

    def _show_last(self):
        from core.cleanup import last_cleanup
        last = last_cleanup()
        v, s = self.t_last
        if last:
            v.config(text=_size(last.get("freed", 0)))
            s.config(text=time.strftime("%d.%m.%Y %H:%M", time.localtime(last["ts"])) + "  ·  "
                     + _tx("last_v", n=last.get("files", 0)))
        else:
            v.config(text="--")
            s.config(text=_tx("never"))

    # ── the remembered choice ────────────────────────────────────────────
    def _settings_file(self):
        try:
            return self.app._app_settings_file()
        except Exception:
            return None

    def _load_choice(self):
        try:
            from utils.prefs_io import load_json
            p = self._settings_file()
            return dict((load_json(p, {}) or {}).get("cleanup_selection", {})) if p else {}
        except Exception:
            return {}

    def _save_choice(self):
        try:
            from utils.prefs_io import update_json
            p = self._settings_file()
            if p:
                self.saved.update({c.key: bool(c.selected) for c in self.cats
                                   if not c.blocked and c.key not in _ALWAYS_MANUAL})
                update_json(p, cleanup_selection=self.saved)
        except Exception:
            pass

    # ── scan ─────────────────────────────────────────────────────────────
    def _scan(self):
        self.sh.cats = None
        for fr in (self.left, self.found, self.tips):
            for w in fr.winfo_children():
                w.destroy()
        tk.Label(self.found, text=_tx("scanning"), font=(_BODY, 9), bg=PANEL, fg=MUTED).pack(
            anchor="w", padx=12, pady=12)
        # the left column too: a scan of a big TEMP takes 10+ s, and an empty
        # box looked broken in the test build (2026-11-21)
        self._caption(self.left, _tx("what"))
        tk.Label(self.left, text=_tx("scanning"), font=(_BODY, 9), bg=PANEL, fg=MUTED,
                 width=34, anchor="w").pack(anchor="w", padx=12, pady=(0, 12))
        self.t_can[0].config(text="…")
        self.t_sel[0].config(text="…")
        threading.Thread(target=_scan_worker, args=(self.sh,), daemon=True, name="cleanup-scan").start()
        self._wait_scan()

    def _wait_scan(self):
        if not self._alive():
            return
        if self.sh.cats is None:
            self.root.after(150, self._wait_scan)
            return
        self.cats = [c for c in self.sh.cats if visible(c)]
        for c in self.cats:
            if c.blocked or not c.size:
                c.selected = False
            elif c.key in _ALWAYS_MANUAL:
                c.selected = False
            elif c.key in self.saved:
                c.selected = bool(self.saved[c.key])
        self._draw()

    def _chosen(self):
        return [c for c in self.cats if c.selected and not c.blocked and c.size]

    def _draw(self):
        self._draw_left()
        self._draw_found()
        self._draw_tips()

    def _box(self, parent, state, bg, enabled=True):
        txt = {True: "☑", False: "☐", None: "▣"}[state]
        return tk.Label(parent, text=txt, font=(_BODY, 12), bg=bg,
                        fg=(GREEN if state is not False else MUTED) if enabled else "#374151",
                        cursor="hand2" if enabled else "arrow")

    def _draw_left(self):
        for w in self.left.winfo_children():
            w.destroy()
        lang = _lang()
        self._caption(self.left, _tx("what"))
        from core.cleanup import GROUPS
        for g in GROUPS:
            items = [c for c in self.cats if c.group == g]
            if not items:
                continue
            usable = [c for c in items if not c.blocked and c.size]
            sel = [c for c in usable if c.selected]
            state = (True if usable and len(sel) == len(usable) else (False if not sel else None))
            head = tk.Frame(self.left, bg=PANEL2)
            head.pack(fill="x", padx=8, pady=(6, 2))
            b = self._box(head, state, PANEL2, enabled=bool(usable))
            b.pack(side="left", padx=(4, 0))
            tk.Label(head, text=_GROUP[g][lang], font=(_BODY, 9, "bold"), bg=PANEL2, fg=TEXT).pack(
                side="left", padx=(4, 0), pady=3)
            tk.Label(head, text=_size(sum(c.size for c in items if not c.blocked)), font=(_BODY, 8),
                     bg=PANEL2, fg=MUTED).pack(side="right", padx=8)
            if usable:
                b.bind("<Button-1>", lambda e=None, u=usable, s=state: self._toggle_group(u, s))
            for c in items:
                row = tk.Frame(self.left, bg=PANEL)
                row.pack(fill="x", padx=(20, 8))
                ok = not c.blocked and bool(c.size)
                cb = self._box(row, bool(c.selected), PANEL, enabled=ok)
                cb.pack(side="left")
                tk.Label(row, text=_name(c.key, lang), font=(_BODY, 9), bg=PANEL,
                         fg=TEXT if ok else DIM, anchor="w").pack(side="left", padx=(4, 0))
                if c.blocked:
                    side = "⚠"
                    fg = AMBER
                else:
                    side = _size(c.size) if c.size else "0"
                    fg = AMBER if c.size >= 1024 ** 3 else (MUTED if c.size else DIM)
                tk.Label(row, text=side, font=(_BODY, 8), bg=PANEL, fg=fg).pack(side="right")
                if ok:
                    cb.bind("<Button-1>", lambda e=None, cat=c: self._toggle(cat))

        self._caption(self.left, _tx("quick"))
        q = tk.Frame(self.left, bg=PANEL)
        q.pack(fill="x", padx=12, pady=(0, 12))
        btn = tk.Label(q, text=_tx("dns"), font=(_BODY, 9, "bold"), bg="#1e293b", fg=TEXT,
                       padx=10, pady=4, cursor="hand2")
        btn.pack(anchor="w")
        btn.bind("<Button-1>", lambda e=None: self._dns())
        tk.Label(q, text=_tx("dns_d"), font=(_BODY, 7), bg=PANEL, fg=DIM, anchor="w", justify="left",
                 wraplength=LEFT_W - 30).pack(fill="x", pady=(4, 0))

    def _draw_found(self):
        for w in self.found.winfo_children():
            w.destroy()
        lang = _lang()
        total = sum(c.size for c in self.cats if not c.blocked)
        chosen = self._chosen()
        v, s = self.t_can
        v.config(text=_size(total))
        s.config(text="")
        v, s = self.t_sel
        v.config(text=_size(sum(c.size for c in chosen)))
        s.config(text=_tx("sel_v", n=len(chosen)))

        self._caption(self.found, _tx("found"))
        rows = sorted([c for c in self.cats if c.size or c.blocked],
                      key=lambda c: (c.blocked, -c.size))
        if not any(c.size for c in rows):
            tk.Label(self.found, text=_tx("nothing"), font=(_BODY, 9), bg=PANEL, fg=MUTED).pack(
                anchor="w", padx=12, pady=(0, 12))
        top = max([c.size for c in rows] + [1])
        for c in rows:
            r = tk.Frame(self.found, bg=PANEL)
            r.pack(fill="x", padx=12, pady=(4, 0))
            line = tk.Frame(r, bg=PANEL)
            line.pack(fill="x")
            tk.Label(line, text=_name(c.key, lang), font=(_BODY, 9, "bold"), bg=PANEL,
                     fg=TEXT if c.selected else MUTED, anchor="w").pack(side="left")
            tk.Label(line, text=_size(c.size) if not c.blocked else "", font=(_HDR, 10, "bold"),
                     bg=PANEL, fg=AMBER if c.size >= 1024 ** 3 else TEXT).pack(side="right")
            if c.blocked:
                note = _tx("admin") if c.note == "admin" else _tx("running", b=c.note.split(":", 1)[1])
                tk.Label(r, text=note, font=(_BODY, 8), bg=PANEL, fg=AMBER, anchor="w").pack(fill="x")
                continue
            bar = tk.Canvas(r, height=6, bg=BAR_BG, highlightthickness=0)
            bar.pack(fill="x", pady=(2, 0))
            frac = c.size / top
            col = GREEN if c.selected else "#475569"
            bar.bind("<Configure>", lambda e=None, f=frac, k=col, b=bar: (
                b.delete("all"),
                b.create_rectangle(0, 0, max(2, int(b.winfo_width() * f)), 6, fill=k, width=0)))
            info = tk.Frame(r, bg=PANEL)
            info.pack(fill="x", pady=(1, 0))
            tk.Label(info, text=_CAT.get(c.key, (None, {lang: ""}))[1][lang], font=(_BODY, 7), bg=PANEL,
                     fg=DIM, anchor="w").pack(side="left")
            if c.key != "recycle_bin" and c.files:
                lnk = tk.Label(info, text=(_tx("hide") if c.key in self.open_preview else _tx("show"))
                               + "  ·  " + _tx("files", n=len(c.files)),
                               font=(_BODY, 7, "bold"), bg=PANEL, fg=VIOLET, cursor="hand2")
                lnk.pack(side="right")
                lnk.bind("<Button-1>", lambda e=None, k=c.key: self._toggle_preview(k))
            if c.key in self.open_preview:
                pv = tk.Frame(r, bg=PANEL2)
                pv.pack(fill="x", pady=(2, 2))
                for path, size in c.preview():
                    pr = tk.Frame(pv, bg=PANEL2)
                    pr.pack(fill="x", padx=6)
                    tk.Label(pr, text=_size(size), font=(_MONO, 7), bg=PANEL2, fg=TEXT, width=9,
                             anchor="e").pack(side="right")
                    tk.Label(pr, text=path, font=(_MONO, 7), bg=PANEL2, fg=MUTED, anchor="w").pack(
                        side="left", fill="x", expand=True)
        tk.Frame(self.found, bg=PANEL, height=10).pack(fill="x")

    def _draw_tips(self):
        for w in self.tips.winfo_children():
            w.destroy()
        lang = _lang()
        self._caption(self.tips, _tx("tips"), fg=VIOLET)
        d, p = _drive_free()
        for text, act in speed_tips(self.cats, lang, d, p):
            row = tk.Frame(self.tips, bg=PANEL)
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text="•", font=(_BODY, 9), bg=PANEL, fg=VIOLET).pack(side="left", anchor="n")
            if act:
                b = tk.Label(row, text=act[0] + " →", font=(_BODY, 8, "bold"), bg="#2a2244", fg="#ffffff",
                             padx=8, pady=2, cursor="hand2")
                b.pack(side="right", anchor="n", padx=(8, 0))
                b.bind("<Button-1>", lambda e=None, pg=act[1]: self._go(pg))
            tk.Label(row, text=text, font=(_BODY, 8), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                     wraplength=520).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ask = tk.Label(self.tips, text="💬 " + _tx("ask"), font=(_BODY, 9, "bold"), bg="#6d28d9", fg="#ffffff",
                       padx=12, pady=4, cursor="hand2")
        ask.pack(anchor="w", padx=12, pady=(8, 12))
        ask.bind("<Button-1>", lambda e=None: self._ask())

    # ── actions ──────────────────────────────────────────────────────────
    def _toggle(self, c):
        c.selected = not c.selected
        self._save_choice()
        self._draw()

    def _toggle_group(self, usable, state):
        on = state is not True
        for c in usable:
            c.selected = on
        self._save_choice()
        self._draw()

    def _toggle_preview(self, key):
        self.open_preview ^= {key}
        self._draw_found()

    def _go(self, page_id):
        try:
            self.app.current_view = None
            self.app._switch_to_page(page_id)
        except Exception:
            pass

    def _ask(self):
        panel = getattr(self.app, "gpt_panel", None)
        if panel is not None and hasattr(panel, "ask"):
            panel.ask(_tx("ask_q"))

    def _dns(self):
        self.sh.dns = None
        threading.Thread(target=_dns_worker, args=(self.sh,), daemon=True, name="cleanup-dns").start()
        self._wait_dns()

    def _wait_dns(self):
        if not self._alive():
            return
        if self.sh.dns is None:
            self.root.after(150, self._wait_dns)
            return
        self.status.config(text=_tx("dns_ok") if self.sh.dns else _tx("dns_err"),
                           fg=GREEN if self.sh.dns else AMBER)

    def _clean(self):
        chosen = self._chosen()
        if not chosen:
            return
        lang = _lang()
        names = ", ".join(_name(c.key, lang) for c in chosen)
        msg = _tx("confirm", s=_size(sum(c.size for c in chosen)), c=names,
                  bin=_tx("confirm_bin") if any(c.key == "recycle_bin" for c in chosen) else "",
                  dl=_tx("confirm_dl") if any(c.key == "big_downloads" for c in chosen) else "")
        if not messagebox.askyesno(_tx("confirm_t"), msg, parent=self.root):
            return
        self.status.config(text=_tx("working"), fg=MUTED)
        self.sh.result = None
        threading.Thread(target=_clean_worker, args=(self.sh, self.cats), daemon=True,
                         name="cleanup-run").start()
        self._wait_clean()

    def _wait_clean(self):
        if not self._alive():
            return
        if self.sh.result is None:
            self.root.after(200, self._wait_clean)
            return
        r = self.sh.result
        self.status.config(text=_tx("done", s=_size(r.get("freed", 0)), n=r.get("files", 0),
                                    k=r.get("skipped", 0)), fg=GREEN)
        self._show_last()
        self._scan()


def build_cleanup_page(app, parent) -> CleanupPage:
    return CleanupPage(app, parent)
