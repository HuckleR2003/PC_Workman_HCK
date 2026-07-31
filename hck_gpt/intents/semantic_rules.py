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


def route_semantic(raw_text: str) -> Optional[str]:
    """Return a high-confidence semantic intent or ``None``."""
    text = _fold(raw_text)
    if not text:
        return None
    if _looks_out_of_domain(text):
        return "unknown"
    for resolver in (
        _route_conversation_control,
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
