"""hck_gpt.responses.r_features - hck_GPT knows the program it lives in
(fifth long test, 2026-11-17).

"czym jest deepmonitor" got "which process do you want to check", "co mogę
robić w programie" got the list of background programs, "mam wolny
internet" got the lag check. These answers come from here:

    feature_info      one feature of PC Workman: what it does, where it is
    app_capabilities  a tour of the program, every feature with a link
    network_slow      slow internet: what the PC itself can show, then a guide
    gpu_overclock     overclocking the graphics card (the CPU answer said
                      "locked multiplier" to a GPU question)
    recent_events     what the Recent Events list counts
    joke              "opowiedz żart"

FEATURES is the single list both answers use. Each entry: the folded
patterns that name it, the PL/EN name, what it does, where it is, and the
chat link that opens it (a name registered with register_nav_callback).
"""
from __future__ import annotations

import random
import re
import time

from hck_gpt.responses.common import List, ParseResult, _t

FEATURES = [
    {"id": "deepmonitor", "rx": r"deep ?monitor\w*|all ?monitor",
     "name": ("DeepMonitor", "DeepMonitor"),
     "what": ("Pełna tabela parametrów na żywo: każdy czujnik CPU, GPU, RAM, dysków i sieci w jednym oknie, z wartościami min i max od uruchomienia. "
              "W tle co kilka minut zapisuje też migawki do bazy, z nich uczę się normy temperatur i napięć.",
              "A full live table of every sensor: CPU, GPU, RAM, drives and network in one window, with min and max since start. "
              "In the background it also saves snapshots every few minutes; I learn the normal temperatures and voltages from them."),
     "where": ("Dashboard → 📊 DeepMonitor (Zerknij na parametry).", "Dashboard → 📊 DeepMonitor."),
     "nav": "DeepMonitor"},
    {"id": "observation", "rx": r"nagrani\w*|nagrywani\w*|notatk\w* obserwac\w*|obserwacj\w*|recording|observation note",
     "name": ("Nagranie (notatka obserwacji)", "Recording (observation note)"),
     "what": ("Co sekundę zapisuję CPU, RAM, GPU, temperaturę GPU, zegar procesora i najcięższy proces. Po zakończeniu porównuję nagranie z poprzednim: "
              "widać, czy zmiana (sterownik, wyłączony autostart, nowe ustawienia gry) naprawdę pomogła.",
              "Every second I save CPU, RAM, GPU, GPU temperature, CPU clock and the heaviest process. When it ends I compare it with the previous "
              "recording, so you see whether a change (a driver, a disabled startup entry, new game settings) really helped."),
     "where": ("W czacie: 'zacznij nagrywanie' i 'zakończ nagrywanie'. Nagrania zostają w data\\observations.",
               "In the chat: 'start recording' and 'stop recording'. Recordings stay in data\\observations."),
     "offer": "record"},
    {"id": "process_center", "rx": r"centrum (informacji o )?proces\w*|process (information )?cent(er|re)|tabel\w* procesow",
     "name": ("Centrum informacji o procesach", "Process Information Center"),
     "what": ("Wszystkie procesy w jednej tabeli: ile biorą teraz i średnio przez 7 dni, czy działają codziennie, czy są zaufane i co z nimi zrobić. "
              "Do tego wykres liczby procesów w czasie. Dwuklik na procesie w dowolnym miejscu programu otwiera tu jego kartę.",
              "Every process in one table: what it takes now and on average over 7 days, whether it runs every day, whether it is trusted and what to do with it. "
              "Plus a chart of the number of processes over time. A double click on a process anywhere in the program opens its card here."),
     "where": ("Menu po lewej → Centrum procesów.", "Left menu → Process Center."),
     "nav": "Process Center"},
    {"id": "cleanup", "rx": r"oczyszczani\w*|cleanup|sprzatani\w*",
     "name": ("Oczyszczanie", "Cleanup"),
     "what": ("Lista w grupach: Windows (pliki tymczasowe, miniatury, raporty błędów, shadery, pobrane aktualizacje), "
              "każda przeglądarka osobno (tylko pamięć podręczna, bez haseł i historii), Discord, Steam, Spotify oraz Twoje pliki (Kosz, duże stare w Pobranych). "
              "Obok wynik analizy z rozmiarami i plikami, pod nim porady przyspieszania, plus szybkie czyszczenie pamięci DNS. "
              "Usuwa tylko to, co zaznaczysz, po potwierdzeniu z kwotą; otwarte programy pomija.",
              "A list in groups: Windows (temporary files, thumbnails, error reports, shaders, downloaded updates), "
              "each browser on its own (only the cache, no passwords or history), Discord, Steam, Spotify and your files (Recycle Bin, big old ones in Downloads). "
              "Next to it what the scan found with sizes and files, below it speed-up tips, plus a quick DNS cache flush. "
              "It removes only what you tick, after a confirmation with the amount; open programs are skipped."),
     "where": ("My PC → Oczyszczanie.", "My PC → Cleanup."),
     "nav": "Cleanup"},
    {"id": "health_report", "rx": r"raport\w* zdrowia|health report",
     "name": ("Raport zdrowia", "Health report"),
     "what": ("Wynik zdrowia komputera z częściami, co się zmieniło od ostatniego raportu i trzy rzeczy do zrobienia najpierw. Zapiszesz go jako plik HTML.",
              "The PC's health score with its parts, what changed since the last report and three things to do first. Saved as an HTML file."),
     "where": ("My PC → Raport zdrowia.", "My PC → Health report."),
     "nav": "Health Report"},
    {"id": "profile", "rx": r"twoj\w* profil|profil\w* (uzytkownika|pc workman)|your profile",
     "name": ("Twój profil", "Your profile"),
     "what": ("Ten komputer, statystyki od początku (godziny, gry, nagrania, czyszczenia), kamienie milowe i prywatność w jednym miejscu. Bez konta, wszystko lokalnie.",
              "This PC, stats since the beginning (hours, games, recordings, cleanups), milestones and privacy in one place. No account, all local."),
     "where": ("My PC → Twój profil.", "My PC → Your profile."),
     "nav": "Your Profile"},
    {"id": "fan_dashboard", "rx": r"fan ?dashboard|fan ?control|centrum ac|wentylator\w* .{0,10}(panel|zakladk|strona)|krzyw\w* wentylator",
     "name": ("Fan Dashboard (Centrum AC)", "Fan Dashboard"),
     "what": ("Temperatury, obroty wentylatorów i krzywe w jednym miejscu, z historią. Obroty i temperaturę CPU czyta z LibreHardwareMonitor; "
              "bez niego pokazuje to, co podaje Windows i karta graficzna, i uczciwie oznacza oszacowania.",
              "Temperatures, fan speeds and curves in one place, with history. Fan speeds and the CPU temperature come from LibreHardwareMonitor; "
              "without it, it shows what Windows and the graphics card report and marks estimates as such."),
     "where": ("Menu po lewej → Fan Dashboard.", "Left menu → Fan Dashboard."),
     "nav": "Fan Control"},
    {"id": "learning", "rx": r"monitoring (i |and |& )?learning|learning center|centrum nauki|nauk\w* (normy|programu)",
     "name": ("Monitoring & Learning", "Monitoring & Learning"),
     "what": ("Tu widać, czego program nauczył się o Twoim komputerze: normę temperatur dla bezczynności, pracy i grania, postęp nauki, "
              "okresy dużego obciążenia (z nazwą gry) i listę ostatnich zdarzeń.",
              "This shows what the program learned about your PC: the normal temperatures for idle, work and gaming, the learning progress, "
              "busy stretches (with the game's name) and the recent events list."),
     "where": ("Menu po lewej → Monitoring & Learning.", "Left menu → Monitoring & Learning."),
     "nav": "Learning Center"},
    {"id": "overlay", "rx": r"nakladk\w*|overlay|mini ?monitor",
     "name": ("In-Game Overlay", "In-Game Overlay"),
     "what": ("Licznik na wierzchu gry: FPS, CPU, GPU, temperatury, RAM. Wybierasz, co widać, i styl. Obok jest MiniOverlay, mały monitor, który działa cały czas.",
              "A counter on top of the game: FPS, CPU, GPU, temperatures, RAM. You pick what shows and the style. Next to it is MiniOverlay, a small always-on monitor."),
     "where": ("Mój PC → kafelek GAMING / In-Game.", "My PC → the GAMING / In-Game tile."),
     "nav": "In-Game Overlay"},
    {"id": "activity_memory", "rx": r"activity ?memory|pamiec\w* aktywnosci|histori\w* (cpu|ram|gpu|procesow)",
     "name": ("Activity Memory", "Activity Memory"),
     "what": ("Historia obciążenia CPU, RAM i GPU minuta po minucie, z procesami, które wtedy pracowały. Odpowiada na pytanie „co się działo wczoraj o 20:00”.",
              "CPU, RAM and GPU load minute by minute, with the processes that ran at the time. It answers \"what happened yesterday at 8 pm\"."),
     "where": ("Dashboard → wykres → Activity Memory.", "Dashboard → the chart → Activity Memory."),
     "nav": "Activity Memory"},
    {"id": "turbo", "rx": r"\bturbo\b|silnik turbo",
     "name": ("Silnik TURBO", "TURBO engine"),
     "what": ("Zestaw przełączników na czas grania lub ciężkiej pracy: własny plan zasilania 'Turbo PC', zatrzymanie zbędnych usług, automatyczne czyszczenie RAM. "
              "Po zamknięciu PC Workman wszystko wraca do stanu sprzed włączenia.",
              "A set of switches for gaming or heavy work: a 'Turbo PC' power plan, stopping unneeded services, automatic RAM flush. "
              "When PC Workman closes, everything returns to how it was."),
     "where": ("Optymalizacja → TURBO.", "Optimization → TURBO."),
     "nav": "Optimization"},
    {"id": "process_guard", "rx": r"process ?guard|responsiveness ?guard|throttle ?guard",
     "name": ("Process Guard", "Process Guard"),
     "what": ("Przy prawdziwej presji na CPU obniża na chwilę priorytet procesów w tle. Nie rusza systemu, anti-cheatów ani aplikacji, której używasz; każda decyzja trafia do logu.",
              "Under real CPU pressure it lowers the priority of background processes for a while. It never touches the system, anti-cheats or the app you use; every decision is logged."),
     "where": ("Optymalizacja → Process Guard.", "Optimization → Process Guard."),
     "nav": "Optimization"},
    {"id": "hibernation", "rx": r"hibernac\w*|hibernation|usypia\w* aplikac",
     "name": ("App Hibernation", "App Hibernation"),
     "what": ("Usypia aplikacje, których nie używasz od ustalonej liczby minut, żeby oddały procesor i pamięć. Budzą się, gdy do nich wrócisz.",
              "Puts apps you have not used for a set number of minutes to sleep, so they give back CPU and memory. They wake up when you return."),
     "where": ("Optymalizacja → App Hibernation.", "Optimization → App Hibernation."),
     "nav": "Optimization"},
    {"id": "ram_flush", "rx": r"ram ?flush|flush ram|czyszczeni\w* (ram|pamieci)|paragon\w*",
     "name": ("RAM Flush", "RAM Flush"),
     "what": ("Oddaje systemowi pamięć, której programy nie używają (przycięcie working set). Po każdym czyszczeniu zostaje paragon: ile oddało i komu.",
              "Gives the system back memory programs are not using (working set trim). Each flush leaves a receipt: how much and from whom."),
     "where": ("Dashboard → FLUSH RAM, automatycznie: Optymalizacja → Auto RAM Flush.", "Dashboard → FLUSH RAM; automatic: Optimization → Auto RAM Flush."),
     "nav": "Optimization"},
    {"id": "upgrade_readiness", "rx": r"upgrade ?readiness|gotowosc\w* (do )?(rozbudowy|ulepszen)",
     "name": ("Upgrade Readiness", "Upgrade Readiness"),
     "what": ("Sprawdza, co pasuje do Twojej płyty: procesory, RAM, dyski, zasilacz, i co z tego da najwięcej przy Twoim sposobie używania.",
              "Checks what fits your board: CPUs, RAM, drives, power supply, and which of them helps most for the way you use the PC."),
     "where": ("Menu po lewej → Upgrade Readiness.", "Left menu → Upgrade Readiness."),
     "nav": "Upgrade Readiness"},
    {"id": "pc_map", "rx": r"map\w* (pc|komputera|podzespolow|komponentow)|\bmapa\b",
     "name": ("Mapa PC", "PC Map"),
     "what": ("Płyta główna z podzespołami na swoich miejscach (gniazdo CPU, sloty RAM, PCIe, M.2), zasilacz i dyski obok; osobny widok laptopa. "
              "Kolory od zieleni do czerwieni według temperatury, teraz albo średnio z 7 dni. Najedź na część: model i liczby; "
              "kliknięcie CPU, GPU albo RAM otwiera ich historię.",
              "The motherboard with its parts in their places (CPU socket, RAM slots, PCIe, M.2), the PSU and drives beside it; a separate laptop view. "
              "Colours from green to red by temperature, now or as a 7-day average. Point at a part: its model and numbers; "
              "a click on the CPU, GPU or RAM opens its history."),
     "where": ("Mój PC → MAPA.", "My PC → MAP."),
     "nav": "My PC"},
    {"id": "stability", "rx": r"test\w* stabilnosc\w*|stability test\w*|stres ?test\w*|stress ?test\w*",
     "name": ("Testy stabilności", "Stability Tests"),
     "what": ("Krótkie testy obciążenia CPU, RAM i dysku, z pomiarem temperatur i zegarów w trakcie.",
              "Short CPU, RAM and drive load tests, with temperatures and clocks measured during the run."),
     "where": ("Mój PC → Centrum → Testy stabilności.", "My PC → Central → Stability Tests."),
     "nav": "Stability Tests"},
    {"id": "startup_manager", "rx": r"startup ?manager|menedzer\w* autostartu|zakladk\w* autostart",
     "name": ("Autostart", "Startup Manager"),
     "what": ("Lista wszystkiego, co uruchamia się z Windows, z wpływem na start. Wpis wyłączasz jednym kliknięciem i możesz go przywrócić.",
              "Everything that starts with Windows, with its impact on boot. One click disables an entry and you can bring it back."),
     "where": ("Optymalizacja → Autostart.", "Optimization → Startup."),
     "nav": "Startup Manager"},
    {"id": "services_manager", "rx": r"services ?manager|menedzer\w* uslug|zakladk\w* uslug",
     "name": ("Usługi", "Services Manager"),
     "what": ("Usługi Windows z opisem po ludzku i oceną, które można bezpiecznie przełączyć na ręczne.",
              "Windows services with a plain description and which ones can safely be set to manual."),
     "where": ("Optymalizacja → Usługi.", "Optimization → Services."),
     "nav": "Services Manager"},
    {"id": "recent_events", "rx": r"recent ?events?|ostatnie zdarzeni\w*",
     "name": ("Recent Events", "Recent Events"),
     "what": ("Lista ostatnich zdarzeń: nagłe skoki obciążenia i okresy dużego obciążenia z nazwą gry.",
              "The latest events: sudden load spikes and busy stretches with the game's name."),
     "where": ("Monitoring & Learning → RECENT EVENTS.", "Monitoring & Learning → RECENT EVENTS."),
     "nav": "Learning Center"},
    {"id": "hck_labs", "rx": r"hck ?labs",
     "name": ("HCK_Labs", "HCK_Labs"),
     "what": ("Strona o projekcie: wersja, co nowego, statystyki Twojego używania i link do sprawdzenia aktualizacji.",
              "The project page: version, what is new, your usage statistics and a link to check for updates."),
     "where": ("Menu po lewej → HCK_Labs.", "Left menu → HCK_Labs."),
     "nav": None},
]

_COMPILED = [(f, re.compile(f["rx"])) for f in FEATURES]


def find_feature(folded: str):
    for f, rx in _COMPILED:
        if rx.search(folded):
            return f
    return None


_JOKES_PL = [
    "Mój komputer ma tyle otwartych kart w przeglądarce, że RAM poprosił o urlop.",
    "Dlaczego procesor nigdy się nie spóźnia? Bo zawsze trzyma się zegara.",
    "Wentylator powiedział procesorowi: „spokojnie, ochłoń”. Procesor: „łatwo ci mówić, ty się tylko kręcisz”.",
    "Restart naprawia 90% problemów. Pozostałe 10% naprawia drugi restart.",
    "Karta graficzna i zasilacz poszły na randkę. Skończyło się na tym, że zasilacz płacił za wszystko.",
]
_JOKES_EN = [
    "My browser has so many tabs open that the RAM asked for a holiday.",
    "Why is the CPU never late? It always keeps to the clock.",
    "The fan told the CPU: \"chill out\". The CPU: \"easy for you to say, you just go round in circles\".",
    "A restart fixes 90% of problems. A second restart fixes the other 10%.",
]


class FeatureResponses:

    def _resp_feature_info(self, r: ParseResult, lang: str = "pl") -> List[str]:
        from hck_gpt.intents.insight_rules import fold
        f = find_feature(fold(getattr(r, "raw_text", "") or ""))
        if f is None:
            return self._resp_app_capabilities(r, lang)
        i = 1 if lang == "en" else 0
        lines = [f"{self.PREFIX} {f['name'][i]}: {f['what'][i]}",
                 _t(lang, f"  Gdzie: {f['where'][0]}", f"  Where: {f['where'][1]}")]
        if f["id"] == "recent_events":
            lines += self._events_summary(lang)
        if f.get("nav"):
            lines.append(f"  [-> {f['nav']}]")
        if f.get("offer"):
            lines.append(f"§OFFER {f['offer']}")
        try:
            from hck_gpt.memory.session_memory import session_memory
            session_memory.note_reference("feature", f["id"], "feature_info")
        except Exception:
            pass
        return lines

    def _resp_app_capabilities(self, r: ParseResult, lang: str = "pl") -> List[str]:
        en = lang == "en"
        groups = [
            (("Na żywo", "Live"), ("process_center", "deepmonitor", "fan_dashboard", "overlay")),
            (("Historia i nauka", "History and learning"), ("activity_memory", "learning", "observation")),
            (("Przyspieszanie", "Speeding up"), ("turbo", "ram_flush", "cleanup", "startup_manager", "process_guard")),
            (("Sprzęt", "Hardware"), ("health_report", "pc_map", "upgrade_readiness", "stability")),
        ]
        by_id = {f["id"]: f for f in FEATURES}
        lines = [_t(lang, f"{self.PREFIX} Co możesz robić w PC Workman:", f"{self.PREFIX} What you can do in PC Workman:")]
        for (title, ids) in groups:
            lines.append(f"§STEP {title[1 if en else 0]}")
            for fid in ids:
                f = by_id[fid]
                short = f["what"][1 if en else 0].split(". ")[0].rstrip(".")
                lines.append(f"  · {f['name'][1 if en else 0]}: {short}." + (f" [-> {f['nav']}]" if f.get("nav") else ""))
        lines.append(_t(lang, "  Mnie możesz pytać o wszystko z tej listy, np. „czym jest DeepMonitor” albo „zoptymalizuj komputer”.",
                        "  You can ask me about anything on this list, e.g. \"what is DeepMonitor\" or \"optimize my pc\"."))
        return lines

    def _events_summary(self, lang: str) -> List[str]:
        try:
            from hck_stats_engine.query_api import query_api
            ev = query_api.get_events(start_ts=time.time() - 86400, limit=200) or []
        except Exception:
            ev = []
        if not ev:
            return []
        n = {}
        for e in ev:
            if e.get("event_type") == "shutdown":
                continue        # bookkeeping, hidden from the list as well
            n[e.get("event_type")] = n.get(e.get("event_type"), 0) + 1
        if not n:
            return [_t(lang, "  Z ostatnich 24 h: nic poza zwykłą pracą.", "  Last 24 h: nothing beyond normal work.")]
        names = {"shutdown": ("zamknięcia programu", "program shutdowns"),
                 "load_period": ("okresy dużego obciążenia", "busy stretches"),
                 "spike": ("nagłe skoki", "sudden spikes"),
                 "anomaly": ("odchylenia od normy", "anomalies")}
        i = 1 if lang == "en" else 0
        parts = [f"{names.get(k, (k, k))[i]} {v}" for k, v in sorted(n.items(), key=lambda kv: -kv[1])]
        out = [_t(lang, "  Z ostatnich 24 h: " + ", ".join(parts) + ".", "  Last 24 h: " + ", ".join(parts) + ".")]
        if n.get("load_period"):
            out.append(_t(lang, "  Okres dużego obciążenia to zwykle granie albo render: to zapis, nie alarm.",
                          "  A busy stretch is usually gaming or rendering: a record, not an alarm."))
        return out

    def _resp_recent_events(self, r: ParseResult, lang: str = "pl") -> List[str]:
        r.raw_text = "recent events"
        return self._resp_feature_info(r, lang)

    # _resp_network_slow: the network guide answers it now, tested first (r_network.py, 2026-11-20)

    def _resp_gpu_overclock(self, r: ParseResult, lang: str = "pl") -> List[str]:
        gpu = ""
        try:
            from hck_gpt.data.live_sensors import get as _ls_get
            gpu = str(_ls_get("gpu_name", "") or "")
        except Exception:
            gpu = ""
        lines = [_t(lang, f"{self.PREFIX} Kartę graficzną" + (f" ({gpu})" if gpu else "") + " da się podkręcić, bez BIOS-u, z poziomu Windows.",
                    f"{self.PREFIX} The graphics card" + (f" ({gpu})" if gpu else "") + " can be overclocked from Windows, no BIOS needed.")]
        lines += [
            _t(lang, "  · Narzędzie: MSI Afterburner (darmowe, działa z każdą marką karty). NVIDIA App ma też automatyczne strojenie.",
               "  · Tool: MSI Afterburner (free, works with any card brand). The NVIDIA App also has automatic tuning."),
            _t(lang, "  · Zacznij od +50 do +100 MHz rdzenia, sprawdź w grze 15 minut, potem dokładaj po 25 MHz. Pamięć osobno, krokami po 100 MHz.",
               "  · Start with +50 to +100 MHz on the core, test 15 minutes in a game, then add 25 MHz at a time. Memory separately, 100 MHz steps."),
            _t(lang, "  · Typowy zysk to kilka procent FPS. Artefakty, zawieszenia albo wyjście gry do pulpitu oznaczają, że trzeba cofnąć krok.",
               "  · The usual gain is a few percent FPS. Artifacts, freezes or the game crashing to desktop mean one step back."),
            _t(lang, "  · Pilnuj temperatury: w nakładce PC Workman widać GPU °C w trakcie gry.",
               "  · Watch the temperature: the PC Workman overlay shows GPU °C while you play."),
            _t(lang, "  Przed i po możesz zrobić nagranie ('zacznij nagrywanie'), porównam wyniki.",
               "  You can record before and after ('start recording'), I will compare the results."),
            "  [-> In-Game Overlay]",
        ]
        return lines

    def _resp_joke(self, r: ParseResult, lang: str = "pl") -> List[str]:
        pool = _JOKES_EN if lang == "en" else _JOKES_PL
        return [f"{self.PREFIX} {random.choice(pool)} 🙂"]
