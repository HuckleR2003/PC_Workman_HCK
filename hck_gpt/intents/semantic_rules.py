"""Conservative semantic routing rules for natural PL/EN questions.

The vocabulary parser is good at known phrases and the small ML classifier is
good at paraphrases. This layer covers relationships that bag-of-words models
often lose, for example:

    process + close + safe       -> process_kill
    temperature + compared time -> temp_comparison
    drive + 100% + background   -> disk_usage_why

Rules require multiple independent cues wherever possible. They never perform
an action and never fabricate an answer. ``None`` means "leave the decision to
the keyword/ML parser"; ``unknown`` is an explicit open-set rejection.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


_PART_MODEL = re.compile(
    r"\b(?:i[3579][ -]?\d{4,5}[a-z]{0,2}"
    r"|ryzen\s*[3579]\s*\d{4}[a-z0-9]{0,4}"
    r"|(?:core\s*)?ultra\s*[579]\s*\d{3}[a-z]{0,3}(?:\s+plus)?"
    r"|rtx\s*\d{4}|gtx\s*\d{3,4}|rx\s*\d{3,4}"
    r"|arc\s*[ab]\d{3}|ddr[2345])\b"
)
_EXE_NAME = re.compile(r"\b[\w.-]+\.exe\b")


def _fold(text: str) -> str:
    value = "".join(
        char
        for char in unicodedata.normalize("NFD", (text or "").lower())
        if unicodedata.category(char) != "Mn"
    )
    value = value.translate(str.maketrans({
        "ł": "l", "ø": "o", "đ": "d",
    }))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s.-]", " ", value)).strip()


def _has(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _all(text: str, *groups: tuple[str, ...]) -> bool:
    return all(_has(text, *group) for group in groups)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w.-]+\b", text))


_PC_ANCHORS = (
    "pc", "pecet", "komputer", "komp", "windows", "pulpit", "taskbar",
    "cpu", "procek", "procesor", "gpu", "grafik", "karta", "ram", "pamiec",
    "dysk", "drive", "storage", "ssd", "hdd", "plyt", "motherboard",
    "proces", "process", ".exe", "aplikac", "program", "system", "sprzet",
    "hardware", "wentyl", "fan", "temperatur", "ciepl", "gorac", "heat", "hot",
    "bateri", "battery", "zasil", "power", "fps", "gaming", "gra", "game",
    "vram", "sensor", "czujnik", "sterownik", "driver", "boot", "startup",
    "autostart", "siec", "network", "usb", "pendrive",
)

_OOD_CUES = (
    "pogod", "weather forecast", "bedzie padac", "weekend weather",
    "ugotow", "przepis", "makaron", "piec chleb", "bake a sourdough",
    "lot do", "tani lot", "trip around", "wycieczk", "wakacj",
    "politycz", "wiadomosci ze swiata", "today s political news",
    "na swiecie", "world news",
    "wynik meczu", "formula 1 race", "football match", "mecz legii",
    "fotosyntez", "quadratic equation", "rozwiaz rownanie",
    "rozwiaz to rownanie", "sprawdzian",
    "przetlumacz", "translate this", "say good morning in japanese",
    "wiersz", "fantasy character", "dragon", "smok",
    "akcje", "mortgage", "kredyt", "nvidii",
    "boli mnie", "this rash", "skin rash", "boli gardlo",
    "sore throat", "require a doctor",
    "mandat", "rental contract", "clause legal", "odwolanie",
    "ekspres do kawy", "office chair", "polec mi",
    "zachod slonca", "niebo", "moon", "ksiezyc",
    "przypomnij mi jutro", "book a meeting", "spotkanie z",
    "wiadomosc do mojego szefa", "email from", "received an email",
    "fioletowy banan", "quantum potato", "teleskop",
)


def _looks_out_of_domain(text: str) -> bool:
    if not _has(text, *_OOD_CUES):
        return False
    strong_pc = (
        "pc", "pecet", "komputer", "windows", "cpu", "gpu", "ram", "dysk",
        "ssd", "hdd", "procesor", "procek", ".exe", "taskbar", "pulpit",
        "sprzet", "hardware", "wentyl", "temperatur", "bateri", "fps",
    )
    return not _has(text, *strong_pc)


def is_explicit_out_of_domain(raw_text: str) -> bool:
    """Whether the message contains a concrete non-PC task marker."""
    return _looks_out_of_domain(_fold(raw_text))


def _route_process(text: str) -> Optional[str]:
    process_context = _EXE_NAME.search(text) or re.search(
        r"\b(?:proces(?:y|u|em|ie|ach|ow)?|process(?:es)?|executable"
        r"|aplikac\w*|program\w*)\b",
        text,
    )
    if not process_context:
        return None
    if _has(
        text,
        "zamkn", "zakoncz", "wylacz", "ubic", "zabic",
        "close", "closing", "stop it", "kill", "task manager",
    ):
        return "process_kill"
    if _has(
        text,
        "wirus", "podejrz", "podszywa", "dziwn", "syf",
        "suspicious", "legitimate", "malware", "virus",
    ):
        return "virus_check"
    if _has(
        text,
        "co robi", "czym jest", "systemow", "nalezy do",
        "what is", "what does", "responsible for", "identify",
        "belongs to", "safe",
    ):
        return "process_identity"
    if _has(text, "wylistuj", "dzialajace", "running", "what is running"):
        return "processes"
    return None


def _route_thermal(text: str) -> Optional[str]:
    thermal = _has(
        text,
        "temperatur", "stopni", "ciepl", "gorac", "grzej", "grzew",
        "przegrz", "gotuje",
        "temperature", "heat", " hot", "hot ", "thermal",
    )
    if _all(
        text,
        ("czujnik", "sensor", "odczyt"),
        ("wszyst", "surow", "real", "estimated", "dostepn"),
    ):
        return "sensor_report"
    if _all(
        text,
        ("cpu", "procek", "procesor"),
        ("zegar", "taktow", "czestotliw", "frequency", "clock"),
    ):
        if _has(
            text,
            "zbija", "spada", "dlaw", "gorac", "heat forcing",
            "clocks down", "throttl",
        ):
            return "throttle_check"
        return "cpu_clock"
    if _all(
        text,
        ("pamiec karty", "pamieci karty", "vram", "graphics memory",
         "video memory"),
        ("ile", "zajet", "uzy", "use", "used"),
    ):
        return "vram_usage"
    if _all(
        text,
        ("wentyl", "fan"),
        ("krzyw", "curve", "konfigur", "configure", "ustaw"),
    ):
        return "fan_consult"
    if _all(
        text,
        ("wentyl", "fan"),
        ("halas", "glos", "wyj", "noise", "loud"),
    ):
        if _has(text, "ostatnio", "z czasem", "history", "over time", "getting worse"):
            return "fan_noise_history"
        return "symptom_noisy"
    if _all(
        text,
        ("wentyl", "fan"),
        ("rpm", "predk", "szybk", "speed", "krec"),
    ):
        return "fan_speed"
    if _has(
        text,
        "najciepl", "najgorets", "hottest", "najwiekszy odczyt",
    ):
        return "hottest_component"
    if not thermal:
        return None
    if _has(
        text,
        "zbija takt", "dlawienie", "throttl",
        "clocks down", "forcing the cpu clock",
    ):
        return "throttle_check"
    if _has(
        text,
        "przewid", "jesli sie utrzyma", "wkrotce",
        "become unsafe soon", "will become", "prediction",
    ):
        return "thermal_prediction"
    if _all(
        text,
        ("porown", "cieplej", "wyzsz", "compare", "against"),
        ("dzis", "wczoraj", "poprzed", "earlier", "today", "sesj"),
    ):
        return "temp_comparison"
    if _has(
        text,
        "z tygodnia", "kazdym tygodni", "dlugotermin", "long-term",
        "temperature history", "historia temperatur",
    ):
        return "thermal_history"
    if _all(
        text,
        ("przeprowadz", "porad", "guide", "reducing", "reduce"),
        ("chlodz", "temperatur", "heat"),
    ):
        return "cooling_advice"
    if _has(text, "gpu", "grafik", "karta") and _has(
        text, "dlaczego", "why", "hot", "grze", "gorac"
    ):
        return "gpu_temp_why"
    return "temperature"


def _route_hardware(text: str) -> Optional[str]:
    if _has(text, "napie", "voltage", "12v", "5v", "3.3v"):
        return "voltage_check"
    if _all(
        text,
        ("windows", "system"),
        ("jak dlugo", "how long", "uptime"),
    ) and _has(text, "dziala", "running", "restart", "reboot"):
        return "uptime"
    if _all(
        text,
        ("sesj", "session"),
        ("liczb", "statyst", "numbers", "stats"),
    ):
        return "stats"
    if _all(
        text,
        ("komputer", "computer", "pc", "machine"),
        ("wydajnos", "performance"),
    ) and _has(
        text, "teraz", "obecnie", "w tej chwili", "right now", "at the moment"
    ):
        return "performance"
    if _all(
        text,
        ("peln", "wszyst", "complete", "all"),
        ("spec", "sprzet", "hardware", "component", "zestawien"),
    ) or _has(text, "bebe"):
        return "hw_all"
    if _all(
        text,
        ("cpu", "procesor", "procek"),
        ("jaki", "nazw", "model", "doklad", "identify", "exact", "what",
         "mam za"),
    ):
        return "hw_cpu"
    if _all(
        text,
        ("gpu", "grafik", "karta", "graphics adapter"),
        ("jaka", "nazw", "model", "identify", "which", "wykryl"),
    ):
        return "hw_gpu"
    if _all(
        text,
        ("ram", "pamiec", "memory"),
        ("fizycz", "zainstal", "installed", "kosci", "modul", "ile"),
    ) and not _has(text, "uzy", "usage", "zajet", "gry", "gaming", "dzien"):
        return "hw_ram"
    if _all(
        text,
        ("plyt", "motherboard", "board"),
        ("jaka", "model", "manufacturer", "producent", "what", "read",
         "co to za"),
    ):
        return "hw_motherboard"
    if _all(
        text,
        ("dysk", "drive", "storage", "nosnik"),
        ("pojem", "wolne", "miejsc", "connected", "urzadzen", "device"),
    ):
        return "hw_storage"
    return None


def _route_diagnosis(text: str) -> Optional[str]:
    if _all(
        text,
        ("siec", "network", "connection", "danych"),
        ("program", "aplikac", "wysyla", "consuming", "zuzy"),
    ):
        return "network_usage"
    if _all(
        text,
        ("ram", "pamiec", "memory"),
        ("pelna", "prawie", "wysok", "znik", "brak", "high", "nothing open"),
    ):
        return "ram_why_high"
    if _all(
        text,
        ("dysk", "drive", "storage"),
        ("100", "sto procent", "mieli", "meczy", "hammer", "background"),
    ):
        return "disk_usage_why"
    if _all(
        text,
        ("najwiecej", "najwieksz", "pozeracz", "worst", "most"),
        ("zasob", "cpu", "ram", "resource", "offender", "aplikac", "program"),
    ):
        return "top_resource_hog"
    if _all(
        text,
        ("program", "proces", "aplikac", "running"),
        ("wylist", "dzialajace", "teraz", "currently", "what is running"),
    ):
        return "processes"
    if _all(
        text,
        ("windows", "system"),
        ("desktop", "pulpit"),
    ) and _has(text, "slower", "wolniej", "wolniejsz", "than before"):
        return "startup_slowdown"
    startup = bool(re.search(
        r"\b(?:autostart|startup|boot|sign-in|startuje)\b",
        text,
    ))
    startup = startup or _has(
        text,
        "wstawac z systemem", "launch at sign-in", "launch with windows",
    )
    if startup and _has(
        text, "woln", "dluz", "slower", "longer", "wydluz", "od tygodnia"
    ):
        return "startup_slowdown"
    if startup and _has(
        text, "wylacz", "disable", "powinien", "sensible", "bezpiecz"
    ):
        return "startup_safety"
    if startup:
        return "startup_check"
    if _all(
        text,
        ("aplikac", "program"),
        ("nigdy", "dawno", "nie uzy", "not used", "long time", "stale"),
    ):
        return "stale_apps"
    if _all(
        text,
        ("aplikac", "program", "background apps"),
        ("zbedn", "unnecessary", "niepotrzeb"),
    ):
        return "unnecessary_programs"
    if _has(text, "sterownik", "driver") and _has(
        text, "stare", "aktual", "zaniedb", "outdated", "update"
    ):
        return "driver_status"
    if _has(
        text,
        "pasek zadan", "taskbar", "czarny pulpit", "ikony",
        "desktop stopped", "pulpit kaput",
    ):
        return "desktop_problem"
    if _has(
        text,
        "przed ostatnim zwis", "przed freez", "przed awari",
        "before the crash", "just before", "reconstruct",
    ):
        return "crash_context"
    if _has(
        text,
        "zamar", "zawies", "sie wiesza", "lock up", "locks up", "freeze",
        "freezes", "stutter", "zwis",
    ):
        return "symptom_freeze"
    if _all(
        text,
        ("przegladark", "browser", "tabs", "cache"),
        ("ram", "pamiec", "memory", "puch", "nie oddaje"),
    ):
        return "browser_cache"
    if _all(
        text,
        ("working sets", "ram", "pamiec"),
        ("trim", "oprozn", "flush", "zwoln"),
    ):
        return "ram_flush"
    if _has(text, "plik stronic", "pliku stronic", "pagefile", "paging", "swap"):
        return "swap_analysis"
    if _has(text, "pendrive", "usb transfer", "kopiowanie na usb"):
        return "usb_transfer"
    if _all(
        text,
        ("siec", "network", "connection", "danych"),
        ("program", "aplikac", "wysyla", "consuming", "zuzy"),
    ):
        return "network_usage"
    if _all(
        text,
        ("dysk", "drive", "storage"),
        ("zdrow", "zuzy", "bled", "failing", "health"),
    ):
        return "disk_health"
    if _all(
        text,
        ("dysk", "drive", "storage"),
        ("predk", "szybk", "wolny", "how fast", "speed"),
    ):
        return "disk_speed"
    slow = _has(
        text,
        "muli", "zamula", "zadyszk", "opozn", "sluggish",
        "laguje", "wolny", "spowoln", "stutter",
    ) or bool(re.search(r"\btnie\b", text))
    if slow and _has(
        text,
        "co moge zrobic", "odzyskal", "plan", "make windows less",
        "przyspiesz", "speed up",
    ):
        return "speed_up_pc"
    if slow:
        return "why_slow"
    if _all(
        text,
        ("komputer", "pc", "windows", "pecet"),
        ("odzysk", "szybkosc", "less sluggish", "przyspiesz"),
    ):
        return "speed_up_pc"
    if _all(
        text,
        ("komputer", "computer", "pc", "machine"),
        ("loud", "glosn", "wyje"),
    ) and _has(text, "idle", "pulpit", "nic nie robi"):
        return "symptom_noisy"
    return None


def _route_history(text: str) -> Optional[str]:
    if _all(
        text,
        ("wydajn", "performance", "dziala gorzej"),
        ("zmien", "zeszl", "last week", "since"),
    ):
        return "perf_change"
    if _has(text, "normalnego poziomu", "moja norma", "usual baseline",
            "normal baseline", "unusual for"):
        if _has(text, "ram", "memory"):
            return "ram_compare"
        return "compare_baseline"
    if _all(
        text,
        ("zmien", "change"),
        ("wczoraj", "dzis", "today", "od wczoraj"),
    ):
        return "pc_changes"
    if _all(
        text,
        ("sesj", "session"),
        ("porown", "poprzed", "compare", "previous", "against"),
    ):
        return "session_compare"
    if _all(
        text,
        ("sesj", "session", "dzisiejsz"),
        ("podsum", "digest", "kilku punkt", "concise"),
    ):
        return "session_digest"
    if _has(text, "poranny przeglad", "this morning", "rano") and _has(
        text, "pc", "komputer", "morning", "przeglad"
    ):
        return "morning_brief"
    if _has(text, "trend", "tendenc") and not _has(
        text, "temperatur", "heat", "fan", "wentyl"
    ):
        return "weekly_trends"
    if _all(
        text,
        ("ram", "pamiec", "memory"),
        ("dzien", "daily", "przeciet", "typical"),
    ):
        return "daily_ram_usage"
    if _all(
        text,
        ("program", "aplikac", "app"),
        ("inaczej", "wiecej zasob", "more resources", "than usual"),
    ):
        return "app_behavior_change"
    if _has(
        text,
        "przypomnij liczby", "jakie liczby", "exact values",
        "previous answer", "podales przed chwila",
    ):
        return "recall_numbers"
    if _has(
        text,
        "czemu sam", "dlaczego sam", "sam wyskakujesz",
        "proactively notified", "proactive message",
    ):
        return "explain_proactive"
    if _all(
        text,
        ("learned", "zapamiet", "wiesz"),
        ("locally", "lokal", "usage", "uzyw"),
    ):
        return "ai_context"
    return None


def _route_gaming_power(text: str) -> Optional[str]:
    game = bool(re.search(
        r"\b(?:gra|gry|grze|grach|grania|granie|gaming|game|games|fps"
        r"|cyberpunk)\b",
        text,
    ))
    if game and _has(text, "pojdzie", "grywal", "run on", "how well"):
        return "game_can_run"
    if game and _has(text, "gotow", "przed odpal", "ready before", "make sure"):
        return "game_ready"
    if game and _has(
        text, "najmocniej", "dociska", "stressed", "stress", "most demanding"
    ):
        return "game_hardware_stress"
    if game and _has(
        text,
        "fps", "klat", "spada", "worse after", "po godzin", "dluzszej",
    ):
        return "fps_degradation"
    if game and _has(
        text, "ram", "pamiec", "pamieci", "memory footprint", "memory use"
    ):
        return "gaming_ram_usage"
    if game and _all(text, ("czas", "time"), ("prac", "work")):
        return "gaming_vs_work_time"
    if game and _has(text, "ostatnia sesj", "last time", "summarize"):
        return "gaming_session"
    battery = _has(text, "bateri", "akumulator", "battery")
    if battery and _has(
        text,
        "na ile", "wystarczy", "ile zostalo", "time remain", "how much time",
        "roughly",
    ):
        return "battery_estimate"
    if battery and _has(text, "tempie", "rate", "procent", "discharge rate"):
        return "battery_drain_rate"
    if battery and _has(text, "szybciej", "znika", "drain", "ubywa", "krotko"):
        return "battery_drain"
    if _has(text, "profil zasil", "plan zasil", "power mode", "power plan"):
        return "power_plan"
    if _all(text, ("restart", "reboot"), ("energi", "power consumption", "pobiera")):
        return "power_after_restart"
    if _has(text, "podkrec", "overclock"):
        return "overclock_check"
    return None


def _route_upgrade(text: str) -> Optional[str]:
    if _all(
        text,
        ("ram", "pamiec", "memory"),
        ("doloz", "dokup", "modul", "taktow", "jaki typ", "kit"),
    ):
        return "ram_compat"
    if _has(text, "ddr2", "ddr3", "ddr4", "ddr5") and _has(
        text,
        "doloz", "dokup", "modul", "gryz", "pas", "work with",
        "compatible", "z tym co mam", "zadzia", "u mnie", "work on",
    ):
        return "ram_compat"
    if _PART_MODEL.search(text) and _has(
        text,
        "pas", "wejd", "zadzia", "fit", "work", "compatible",
        "zgodn", "obecn", "wymian",
    ):
        return "upgrade_compat"
    if _has(text, "upgrad", "wymian", "wymien", "rozbudow", "zakup", "dokup"):
        if _has(text, "kolejnosc", "roadmap", "plan", "budzet", "evidence-based"):
            return "upgrade_plan"
        if _has(
            text,
            "czy warto", "ma sens", "droge rozbudowy", "dead end",
            "worth upgrading", "platform",
        ):
            return "upgrade_feasibility"
        if _has(
            text,
            "co da", "najpierw", "najwieksz", "odczuwal", "single",
            "improve", "pierwsze",
        ):
            return "upgrade_advice"
    if _all(
        text,
        ("ram", "pamiec", "working sets"),
        ("oprozn", "flush", "trim", "zwoln"),
    ):
        return "ram_flush"
    if _has(text, "turbo") and _has(
        text, "tryb", "mode", "popraw", "change", "realnie"
    ):
        return "turbo_boost"
    if _has(text, "tune-up", "dopieszc", "pelny przeglad") and _has(
        text, "system", "guided", "plan", "przeglad"
    ):
        return "tuneup_guide"
    if _has(text, "optymal", "optimization", "porzadki wydajn") and _has(
        text, "krok", "guide", "przeprowadz", "od czego", "walk me"
    ):
        return "optimize_guide"
    if _has(text, "optymal", "optimization", "poprawic") and _has(
        text, "bezpiecz", "safe", "nie wylacz", "analyze", "sprawdz"
    ):
        return "optimization"
    return None


def _route_conversation_control(text: str) -> Optional[str]:
    """Route explicit controls for the active diagnostic frame.

    The handlers remain useful without a frame and explain what detail is
    missing, so the parser does not need to import session memory.
    """
    if _has(
        text,
        "nie chodzi o", "mialem na mysli", "poprawka chodzi",
        "chodzilo mi o", "pomylilem sie", "pomylilam sie",
        "i meant", "correction i meant", "not that process", "my mistake",
    ):
        return "correct_subject"
    if _has(
        text,
        "dlaczego to radzisz", "czemu mam to zrobic",
        "wyjasnij poprzednia porade", "na czym opierasz te porade",
        "skad taki krok", "why do you recommend", "why this step",
        "explain your previous advice", "what is that advice based on",
    ):
        return "explain_previous_advice"
    if _has(
        text,
        "porownaj stan po", "sprawdz efekt tej zmiany",
        "porownaj teraz z wczesniej", "compare after the change",
        "check the result of that change", "compare now with before",
    ):
        return "compare_after_change"
    if _has(
        text,
        "zrobilem to", "zrobilam to", "juz zrobione", "wykonalem ten krok",
        "wykonalam ten krok", "gotowe", "sprobowalem", "sprobowalam",
        "jest lepiej po", "bez zmian po", "jest gorzej po", "nie pomoglo",
        "i did it", "done now", "finished it", "i tried it",
        "better after the change", "no change after that",
        "worse after the change", "did not help",
    ):
        return "verify_after_action"
    if _has(
        text,
        "nie chce tego robic", "odpuscmy ten krok", "pomin te porade",
        "wole tego nie ruszac", "tego nie zrobie", "inny sposob",
        "i do not want to do that", "skip that step", "skip that advice",
        "i would rather not", "another way",
    ):
        return "decline_advice"
    if _has(
        text,
        "jak bardzo jestes", "skad ta pewnosc", "fakt czy hipoteza",
        "to pewne czy zgadujesz", "how confident", "how sure",
        "fact or a hypothesis", "certain or a guess",
    ):
        return "explain_confidence"
    if _all(
        text,
        ("kompatybil", "compatibility", "zestaw", "build"),
        ("brakuje", "potrzebujesz", "podac", "missing", "need", "provide"),
    ):
        return "compat_missing_details"
    if _has(text, "budzet", "budget", "mogę wydac", "moge wydac", "can spend"):
        if _has(text, "upgrad", "moderniz", "sprzet", "hardware", "wydac", "spend"):
            return "upgrade_budget"
    if _has(
        text,
        "glownie do gier", "sprzet do montazu", "do programowania",
        "mainly for gaming", "hardware for video editing",
        "computer for development", "workload for the upgrade",
    ):
        return "upgrade_workload"
    if _all(
        text,
        ("pulpit", "explorer", "ikony", "taskbar", "desktop"),
        ("znow", "wrocil", "kolejny raz", "again", "came back"),
    ):
        return "desktop_recurrence"
    if _has(
        text,
        "kontynuuj diagnoze", "idziemy dalej z diagnoza",
        "kolejny szczegol", "continue the diagnosis", "keep troubleshooting",
        "another detail", "bardziej scina niz laguje",
        "stutters more than it lags",
    ):
        return "continue_diagnosis"
    return None


def _route_conversation(text: str) -> Optional[str]:
    if _has(text, "roast", "zjedz moj", "wysmiej"):
        return "fun_roast"
    if _has(text, "pc workman") and _has(
        text, "czym", "co to", "explain what", "what is"
    ):
        return "about_program"
    if _has(text, "kto cie stworzyl", "kto rozwija", "person behind", "who created"):
        return "about_author"
    if _has(
        text,
        "co moge zapytac", "mozliwosci", "kinds of computer questions",
        "nie wiem od czego",
    ):
        return "help"
    if _has(
        text,
        "gdzie zapisujesz", "dane przechow", "dane opuszcz", "data leave",
        "monitoring data leave", "prywatn", "privacy",
    ):
        return "privacy_data"
    if _has(
        text,
        "jak tam u ciebie", "co myslisz", "what do you think",
        "something casual", "cos luzno", "mechaniku",
    ):
        return "small_talk"
    if _has(text, "dziek", "thank you", "thanks", "cleared things up"):
        return "thanks"
    greeting = _has(text, "dzien dobry") or bool(re.search(
        r"\b(?:hej|hejka|czesc|hello|yo)\b",
        text,
    ))
    if greeting and (
        _word_count(text) <= 10 or _has(text, "zaczynam", "ready")
    ):
        return "greeting"
    if _has(
        text,
        "czym dokladnie jestes", "kim jestes", "what exactly are you",
        "what are you",
    ):
        return "about_program"
    if _all(
        text,
        ("system", "komputer", "machine"),
        ("zdrow", "health", "safety check"),
    ):
        return "health_check"
    if _has(
        text,
        "powazny powod do niepokoju", "real risk", "system risk",
        "zagrozenie dla systemu",
    ):
        return "system_risk"
    return None



# ── Everyday questions (2026-11-16) ──────────────────────────────────────────
# From the first long test: 28 of 71 questions ended in "I did not
# understand". Most were short and everyday ("wszystko dziala?", "czemu
# zacina?", "gdzie jest overlay?"), and short questions without a hardware
# word were rejected outright. These routes run before that rejection.
# Text here is accent-folded and lowercase.

_RX_EVERYDAY = [
    # where is the in-game overlay
    ("overlay_where", re.compile(
        r"(in.?game (overlay|stats|statystyk|monitor)|\bingame\b|nakladk|overlay|zakladk\w* w grze|w grze zakladk|"
        r"statystyki w grze|fps w grze|mini ?monitor|stats in game|show fps)")),
    # is my PC fine
    ("pc_status", re.compile(
        r"^(czy )?(wszystko|wszytko|wszysko|all|everything)\b.{0,25}"
        r"(dziala|gra|ok|okej|w porzadku|dobrze|fine|good|working|alright)|"
        r"(czy|jak) (komputer|kompu?t?|pc|pecet|sprzet)\w* (jest )?"
        r"(ok|okej|w porzadku|dobrze chodzi|zdrow|dziala)|"
        r"czy (cos|coś) (jest )?(nie tak|zle|źle)|cos (jest )?nie tak|"
        r"czy (jest )?jakis problem|stan (kompa|komputera|pc)|jak sie czuje (pc|komp)|"
        r"(is|does) (everything|my pc|the pc|my computer) .{0,12}(ok|fine|good|working)|"
        r"anything wrong|sprawdz (komputer|kompa|pc)$|co z kompem")),
    # RAM pressure stated as a complaint: "mam duze obciazenie ramu" went to
    # the upgrade fit check and offered the CPU-motherboard guide
    ("ram_why_high", re.compile(
        r"(duz\w*|wysok\w*|ogromn\w*|ciagle|caly czas|za duzo).{0,20}"
        r"(obciazen\w*|zuzyc\w*|uzyc\w*|zajet\w*)?.{0,12}\bram\w*|"
        r"\bram\w* (jest |mam )?(caly czas |ciagle )?(pelny|zapchany|zajety|na (9|8)\d)|"
        r"brakuje (mi )?(ram|pamieci)|(high|full) (ram|memory) usage|ram (is )?(always )?full")),
    # why does it lag / stutter
    ("why_slow", re.compile(
        r"(skad|czemu|dlaczego|why|what causes).{0,25}"
        r"(lag|zacina|tnie|przycina|klatkuj|muli|wolno|freez|stutter|fps|spowalnia)|"
        r"(spadki|drops?) fps|przycina mi|freezy w|co spowalnia|fps drops")),
    # what uses a lot
    ("top_resource_hog", re.compile(
        r"co (tak |najwiecej |duzo |mi )?(zuzywa|zjada|zre|bierze|obciaza)|"
        r"(czy )?cos (mi )?(tak )?(przeciaza|obciaza|zamula) (komputer|kompa|pc|system)|"
        r"kto (zjada|zuzywa)|co najwiecej (bierze|zuzywa|zjada)|"
        r"what (is )?(using|eating|hogging)")),
    # what could I upgrade, is my part good
    ("upgrade_advice", re.compile(
        r"co (bym |moglbym |moge |warto )?(ulepszyc|wymienic|dokupic|poprawic w kompie)|"
        r"czy (mam )?(dobr\w+|mocn\w+|slab\w+) (gpu|cpu|procesor|karte|grafike|sprzet|komputer)|"
        r"czy (moja karta|moj procesor|ten sprzet|to dobry sprzet)|"
        r"jak mocny jest|jaki upgrade|what should i upgrade|is my (gpu|cpu) good")),
    # do I have the latest version
    ("version_check", re.compile(
        r"(najnowsz\w*|aktualn\w*|latest|newest) (wersj\w*|version)|"
        r"(jaka|ktora) (mam )?wersj\w*|czy jest (aktualizacj|nowsza)|"
        r"jak (zaktualizowac|aktualizowac|update) (pc ?workman|program)|"
        r"czy program jest aktualny|am i (on|using) the latest|how (do i|to) update")),
    # website, articles, guides
    ("website", re.compile(
        r"strona (programu|pc ?workman|internetowa)|stron\w* programu|"
        r"gdzie (pobrac|sciagnac)|link do (strony|programu)|"
        r"gdzie (sa |znajde )?(artykul|poradnik|blog)|(website|download page|where to download)")),
    # what can I delete / uninstall / free space
    ("free_space", re.compile(
        r"co (moge|mozna|warto) (usunac|wywalic|skasowac)|"
        r"jak zwolnic (miejsce|dysk)|co (mi )?zajmuje (tyle )?(miejsca|miejsce|dysk)|czym zapchan\w* dysk|"
        r"free up (space|disk)|what can i delete")),
    ("stale_apps", re.compile(
        r"co (moge|mozna|warto) (odinstalowac|wyrzucic z programow)|"
        r"czego nie uzywam|what can i uninstall")),
    # where do I update drivers
    ("driver_update_where", re.compile(
        r"(gdzie|jak|skad).{0,20}(zaktualizuj\w*|aktualizowac|aktualizuje|update|pobrac).{0,20}"
        r"(sterownik|driver|je\b|go\b)|aktualizacja sterownikow|where (do i|to) update drivers|"
        r"gdzie (je|go) z?aktualizuj")),
    # has PC Workman learned
    ("ai_context", re.compile(
        r"(czy )?(program|pc ?workman|ty)?.{0,10}(juz )?(sie )?(nauczyl|nauczyles|uczysz|nauczyla)|"
        r"ile sie (nauczyl|nauczyles)|co o mnie wiesz|czego sie nauczyl|znasz juz moj|"
        r"(have|has) (you|it) learned|what have you learned")),
    # are you an AI
    ("about_assistant", re.compile(
        r"^(czy )?(jestes|you are|are you) (ai|bot|chatgpt|gpt|sztuczn|czlowiek|robot)|"
        r"^(ai|bot)\??$|kim (ty )?jestes|jak dzialasz\??$|who are you|what are you")),
    # who makes it (also: the author's name typed on its own)
    ("about_author", re.compile(
        r"(marcin|firmuga|hck labs|kto (cie|ciebie|to|program|pc ?workman)\w* "
        r"(zrobil|stworzyl|tworzy|robi|napisal)|kto (jest )?(autorem|tworca)|"
        r"kto (tworzy|zrobil|stworzyl|robi|napisal|rozwija)|"
        r"who (made|built|created|makes) (you|this|pc ?workman)|who is the (author|developer))")),
    # Ollama / local LLM
    ("ollama_info", re.compile(r"(ollam|lokaln\w* (ai|llm|model)|\bllm\b|local (ai|llm|model))")),
    # short reactions
    ("reaction", re.compile(
        r"^(nice|super|spoko|lol|xd+|wow|cool|great|fajnie|git|haha+|hah|mega|extra|"
        r"ekstra|okej|ok|co powiesz|co to bylo( xd)?|niezle|brawo)[ !?.]*$")),
]


def _route_everyday(text: str) -> Optional[str]:
    t = text.strip()
    for intent, rx in _RX_EVERYDAY:
        if rx.search(t):
            return intent
    return None


# ── Second long test + 122-question sweep (2026-11-17) ──────────────────────
# Checked before _RX_EVERYDAY: these are narrower, and some of them used to be
# caught there by a broader rule ("fps drops in games" read as the overlay,
# "co to pamiec wirtualna" as the last TIP, "czy komputer spal" as a game).
_RX_EVERYDAY2 = [
    ("restart_check", re.compile(
        r"niebieski ekran|blue ?screen|\bbsod\b|sam (sie )?(restartuje|wylacza|resetuje)|"
        r"(restartuje|wylacza|resetuje) sie sam|keeps (restarting|shutting down)|"
        r"restarts (by )?itself|kernel.?power|nagle sie wylacz")),
    ("optimize_guide", re.compile(
        r"zrob (mi )?optymalizacj|zoptymalizuj (mi )?(kompa|komputer|pc|system|laptopa)|"
        r"przeprowadz (mnie )?przez optymalizacj|przewodnik optymalizacji|"
        r"(start|run) the (optimization )?guide")),
    ("where_page", re.compile(
        r"^gdzie (jest|sa|znajde|mam) .{0,25}(optymalizacj|autostart|uslug|wentylator|"
        r"ustawieni|histori|pamiec aktywnosci|sterownik|overclock)|"
        r"^where (is|are|do i find) .{0,25}(optimization|startup|services|fans?|settings|"
        r"history|drivers|overclock)")),
    ("virtual_memory", re.compile(
        r"pamiec\w* wirtualn|plik\w* (stronicowania|wymiany)|pagefile|virtual memory|swap file")),
    ("history_peak", re.compile(
        r"kiedy .{0,40}(najbardziej obciazon|najwieksze obciazenie|najciezej|najwiecej pracowal|"
        r"szczyt|najgorecej)|najciezszy moment|najwieksze obciazenie (dzis|wczoraj|w tym tygodniu)|"
        r"when was .{0,25}(busiest|most loaded|highest load)|peak (load|usage) (today|yesterday)")),
    ("history_sleep", re.compile(
        r"czy (komputer|kompu?t?e?r?|pc|laptop|sprzet) (spal|byl uspiony|byl w uspieniu|zasnal|"
        r"przechodzil w uspienie)|kiedy (komputer |pc )?(spal|byl uspiony)|"
        r"(did|was) (my )?(pc|computer|it) (sleep|asleep)")),
    ("history_games", re.compile(
        r"w co (najwiecej |najdluzej |dzis |dzisiaj )?gral|ile (czasu |godzin )?(dzis |dzisiaj )?"
        r"(gralem|gralam|gram|spedzilem w grach)|czas (grania|w grach)|"
        r"how (long|much) did i play|what (games )?did i play")),
    ("history_today", re.compile(
        r"ile (godzin|czasu) .{0,15}(pracowal|dzialal|chodzil|byl wlaczony)|"
        r"jak dlugo .{0,12}(dziala|chodzi|pracuje|jest wlaczony) (komputer|komp|pc|laptop)|"
        r"how long (has|was) (my |the )?(pc|computer) (been )?(on|running)")),
    ("history_compare_days", re.compile(
        r"porownaj (dzis|dzisiaj|dzien).{0,15}wczoraj|dzis (vs|a) wczoraj|"
        r"today (vs|versus|compared to) yesterday|compare today")),
    ("perf_change", re.compile(
        r"od (wczoraj|kilku dni|tygodnia|niedawna) .{0,12}(wolniej|gorzej|muli|zamula|laguje)|"
        r"(wolniej|gorzej) .{0,10}od (wczoraj|kilku dni|tygodnia)|ostatnio (wolniej|gorzej) dziala|"
        r"kiedys (byl )?szybsz|po aktualizacji .{0,25}(zwolnil|wolniej|gorzej|muli)|"
        r"slower (since|than before|lately)")),
    ("closable_apps", re.compile(
        r"(co|ktore programy|jakie programy|ktore aplikacje|jakie aplikacje) (moge |mozna |warto )?"
        r"(zamknac|wylaczyc teraz)|co zamknac|what (apps )?can i close")),
    ("services_advice", re.compile(
        r"(jakie|ktore|co za) uslug\w* (wylaczyc|moge wylaczyc|sa zbedne|niepotrzebne)|"
        r"zbedne uslugi|which services (to|can i) (disable|turn off)")),
    ("startup_check", re.compile(
        r"(wolno|dlugo|powoli) (sie )?(uruchamia|wlacza|odpala|startuje|laduje|bootuje)|"
        r"dlugo startuje|wolny start|co mam w autostarcie|programy (przy|na) starcie|"
        r"wylaczyc programy (przy|na|z) start|autostart|slow (boot|startup)|takes long to (boot|start)")),
    ("symptom_noisy", re.compile(
        r"(wiatrak|wentylator|chlodzeni|cooler)\w* .{0,15}(szumi|glosn|halasuj|wyj|buczy|warcz)|"
        r"(komputer|komp|pc|laptop) (glosno chodzi|halasuje|jest glosny|buczy|szumi)|"
        r"(fan|fans) (is |are )?(so )?(loud|noisy)")),
    ("ram_why_high", re.compile(
        r"(chrome|opera|edge|firefox|brave|przegladark)\w* .{0,20}(zjada|zuzywa|zre|bierze|trzyma)"
        r".{0,15}(ram|pamiec|duzo)|(chrome|opera|browser) (eats|uses) (so much )?(ram|memory)")),
    ("top_resource_hog", re.compile(
        r"(duz|wysok)\w* (zuzyc|obciazen|uzyc)\w* .{0,10}(procesor|cpu)|"
        r"(procesor|cpu) .{0,10}(na 100|caly czas|ciagle|wysoko)|"
        r"what s (using|eating) my (cpu|ram|memory)|whats using")),
    ("free_space", re.compile(
        r"pliki? (tymczasow|temp)|folder temp|wyczysc\w* (dysk|c)\b|dysk c (jest )?(pelny|zapchany)|"
        r"zapchany dysk|brak miejsca|malo miejsca|delete temp files|disk (is )?full")),
    ("throttle_check", re.compile(r"co to (jest )?throttl|what is throttl")),
    ("power_plan", re.compile(
        r"tryb\w* (wysokiej )?wydajnosci|wysoka wydajnosc|plan\w* zasilania|high performance (mode|plan)")),
    ("xmp_check", re.compile(
        r"\bxmp\b|\bexpo\b|\bd o c p\b|docp|predkosc\w* ram|taktowani\w* ram|ram (chodzi|dziala|pracuje) na|"
        r"ram speed|dual channel")),
    ("refresh_rate", re.compile(
        r"\b\d{2,3} ?hz\b|odswiezani|czestotliwosc\w* (ekranu|monitora)|refresh rate")),
    ("audio_crackle", re.compile(
        r"(dzwiek|audio|glosnik|sluchawk)\w* .{0,15}(trzeszcz|charcz|przerywa|zacina|skrzypi|chrypi)|"
        r"crackl|audio (stutter|crackle|pops)")),
    ("backup_where", re.compile(r"backup|kopi\w* zapasow|kopie plikow")),
    ("dust_cleaning", re.compile(
        r"\bkurz|wyczyscic (komputer|kompa|pc|obudowe|wentylator|laptopa) z|czyszczenie (komputera|kompa|pc)|"
        r"past\w* termo|wymienic paste|zmienic paste|clean (the )?dust|thermal paste")),
    ("windows_update_off", re.compile(
        r"wylacz\w* (windows )?update|wylacz\w* aktualizacj\w* (windows|systemu)|"
        r"disable windows update|turn off windows update")),
    ("language_change", re.compile(
        r"zmien\w* jezyk|zmiana jezyka|(po|na) angielsk\w*$|(po|na) polsk\w*$|change (the )?language")),
    ("self_usage", re.compile(
        r"(pc ?workman|ten program|ta aplikacja) .{0,20}(spowalnia|zuzywa|zjada|obciaza|bierze|zamula)|"
        r"ile (ramu|pamieci|cpu|procesora) (zuzywa|bierze|zjada) (pc ?workman|ten program|program)|"
        r"does pc ?workman (slow|use)")),
    ("network_drop", re.compile(
        r"(wifi|wi fi|internet|siec|net)\w* .{0,15}(rozlacza|zrywa|gubi|znika|przerywa|wywala)|"
        r"(wifi|internet) (keeps )?(disconnect|dropping)")),
    ("network_usage", re.compile(r"internet .{0,10}(wolno|wolny|slabo|muli)|slow internet")),
    ("why_slow", re.compile(
        r"(przegladark|chrome|opera|youtube|film)\w* .{0,10}(sie )?(zacina|tnie|przycina|laguje|muli)")),
    ("game_can_run", re.compile(
        r"czy (uruchomie|odpale|pojdzie|pociagnie|zagram|dam rade|ruszy)|"
        r"(can|will) (my pc|i) run")),
    ("fps_degradation", re.compile(
        r"fps (drops?|spada|spadaja|leci)|(malo|niskie) fps|fps drops|low fps")),
    ("privacy_data", re.compile(
        r"telemetri|(wysyla|zbiera|wysylasz|zbierasz|przesyla) .{0,12}dan|prywatnosc|"
        r"(send|collect)s? (my )?data|privacy")),
    ("process_kill", re.compile(
        r"czy (moge|mozna|da sie) (zamknac|wylaczyc|ubic|zabic) [a-z0-9]{3,}|"
        r"can i (close|kill|end) [a-z0-9]{3,}")),
    ("process_identity", re.compile(
        r"^co to (jest |za )?(proces |program )?(?!pamiec|ram|throttl|xmp|cpu|gpu|swap|"
        r"bsod|tdp|fps|overlay|turbo|dysk|ssd|hdd)[a-z0-9_.-]{4,}( exe)?$|"
        r"^what is [a-z0-9_.-]{4,} exe$")),
    # "czy mam lagi" fell to "nie zrozumiałem" in the second long test
    ("why_slow", re.compile(
        r"^(czy )?(mam|miewam) (lag\w*|przyciecia|zaciecia)|(skad|czemu|dlaczego) (sa |mam )?lag|"
        r"\blag(i|a|uje|ow)\b.{0,15}(w grze|na pulpicie|w grach)|^do i have lag")),
    ("vague_problem", re.compile(
        r"^(nie dziala|nic nie dziala|pomocy|pomoz|pomoz mi|ratunku|help me|nothing works|"
        r"it doesn t work|it does not work)$")),
]


def _route_everyday2(text: str) -> Optional[str]:
    t = text.strip()
    for intent, rx in _RX_EVERYDAY2:
        if rx.search(t):
            return intent
    return None


def _route_insight(text: str) -> Optional[str]:
    """Questions that want a conclusion (2026-11-17): hck_gpt.intents.insight_rules."""
    try:
        from hck_gpt.intents.insight_rules import route_insight
        return route_insight(text, folded=True)
    except Exception:
        return None


def route_semantic(raw_text: str) -> Optional[str]:
    """Return a high-confidence semantic intent or ``None``."""
    text = _fold(raw_text)
    if not text:
        return None
    if _looks_out_of_domain(text):
        return "unknown"
    for resolver in (
        _route_conversation_control,
        _route_insight,
        _route_everyday2,
        _route_everyday,
        _route_process,
        _route_thermal,
        _route_upgrade,
        _route_gaming_power,
        _route_diagnosis,
        _route_history,
        _route_hardware,
        _route_conversation,
    ):
        intent = resolver(text)
        if intent:
            return intent
    if _word_count(text) <= 5 and not _has(text, *_PC_ANCHORS):
        return "unknown"
    return None


__all__ = ["is_explicit_out_of_domain", "route_semantic"]
