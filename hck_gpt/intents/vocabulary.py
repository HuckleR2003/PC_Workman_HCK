# hck_gpt/intents/vocabulary.py
"""
Vocabulary — intent trigger patterns and entity extraction maps.

Both Polish and English keywords are present in every intent so the
chatbot responds to mixed-language input without any translation step.

Pattern scoring (in parser.py):
  - Multi-word phrases:  len(words) * 1.5  (biggest bonus)
  - Exact single token:  1.0
  - Partial prefix:      0.4
  - Normalised:          min(1.0, score / 3.0)

Adding more multi-word phrases to an intent raises its confidence score,
making it more likely to be handled by the rule engine (threshold 0.60).
Ambiguous / open-ended queries remain below threshold → Ollama LLM.
"""
from __future__ import annotations
from typing import Dict, List

# ── Intent patterns ───────────────────────────────────────────────────────────
# intent_name → list of trigger strings (lowercase, PL + EN)

INTENT_PATTERNS: Dict[str, List[str]] = {

    # ── Hardware queries ──────────────────────────────────────────────────────
    "hw_cpu": [
        # Tokens
        "procesor", "cpu", "processor", "rdzeń", "rdzenie", "rdzeni",
        "taktowanie", "taktowania", "ghz", "mhz", "boost",
        "intel", "amd", "ryzen",
        # Multi-word (high bonus)
        "core i5", "core i7", "core i9",
        "jaki procesor", "jaki mam procesor", "mój procesor",
        "pokaż procesor", "dane procesora", "info o procesorze",
        "ile rdzeni", "ile ghz", "ile mhz",
        "what cpu", "my cpu", "show cpu", "cpu info",
        "which cpu", "what processor", "my processor",
        "cpu details", "processor details",
    ],
    "hw_gpu": [
        # Tokens
        "karta graficzna", "gpu", "graphics card", "grafika",
        "vram", "nvidia", "geforce", "rtx", "gtx",
        "radeon", "arc",
        # Multi-word
        "amd gpu", "rx 6", "rx 7",
        "jaka karta", "jaka grafika", "moja karta", "mój gpu",
        "karta graficzna model", "ile vram", "ile ma vram",
        "what gpu", "my gpu", "gpu info", "graphics info",
        "which graphics", "what graphics card",
    ],
    "hw_ram": [
        # Tokens
        "ram", "memory", "ddr", "ddr4", "ddr5",
        # Multi-word
        "pamięć ram", "pamięć operacyjna",
        "ile ram", "ile pamięci", "mój ram", "ile mam ram",
        "ile gb ram", "ile mb ram",
        "how much ram", "my ram", "ram info",
        "ram usage", "memory info", "memory usage",
        "how much memory",
    ],
    "hw_motherboard": [
        # Tokens
        "motherboard", "mainboard", "socket", "chipset", "bios", "uefi",
        # Multi-word
        "płyta główna", "jaka płyta", "moja płyta", "model płyty",
        "what motherboard", "my motherboard", "motherboard model",
        "which motherboard",
    ],
    "hw_storage": [
        # Tokens
        "dysk", "ssd", "hdd", "nvme", "storage",
        # Multi-word
        "dyski", "dysk twardy", "przestrzeń dyskowa", "pojemność dysku",
        "ile miejsca", "wolne miejsce", "ile gb dysk", "wolne na dysku",
        "disk space", "my disk", "storage space", "free space",
        "how much space", "disk usage",
    ],
    "hw_all": [
        # Tokens
        "spec", "specs", "podzespoły", "komponenty",
        # Multi-word
        "specyfikacja", "co mam", "mój komputer", "mój pc",
        "moje podzespoły", "jakie mam podzespoły", "jaki mam sprzęt",
        "pokaż sprzęt", "pokaż specyfikację", "pokaż podzespoły",
        "pełna specyfikacja", "parametry komputera",
        "my specs", "my computer", "show specs", "full specs",
        "what hardware", "hardware info", "pc info", "system info",
        "show hardware", "all specs",
    ],

    # ── System health & diagnostics ───────────────────────────────────────────
    "health_check": [
        # Tokens
        "zdrowie", "health", "kondycja", "diagnostyka", "diagnostics",
        # Multi-word  ← these raise confidence significantly
        "stan systemu", "czy ok", "czy działa ok", "czy wszystko ok",
        "sprawdź komputer", "oceń komputer",
        "health check", "system health", "is my pc ok",
        "check health", "pc health", "system check",
        "czy komputer jest zdrowy", "jak działa mój komputer",
        "jak mój pc", "czy jest ok", "czy mam problem",
        "jak system", "check system", "run diagnostics",
        "is everything ok", "is it ok",
    ],
    "temperature": [
        # Tokens
        "temperatura", "temp", "temperature", "gorąco", "overheat", "hot",
        # Multi-word
        "temperatury", "grzeje się", "przegrzanie komputera",
        "ile stopni", "jak gorący", "cpu temp", "gpu temp",
        "jakie temperatury", "temperatura procesora", "temperatura cpu",
        "cooling system", "chłodzenie", "sprawdź temperatury",
        "how hot", "is it hot", "pc temperature", "thermal",
        "temp check", "too hot", "running hot",
    ],
    "throttle_check": [
        # Tokens
        "throttling", "throttle", "dławienie", "spowalnia", "spowolnienie",
        # Multi-word
        "wolniej działa", "wolno działa",
        "cpu throttle", "power limit", "cpu throttling",
        "czy throttluje", "czy cpu throttluje", "czy procesor throttluje",
        "is cpu throttling", "power limiting",
    ],

    # ── Performance & usage ───────────────────────────────────────────────────
    "performance": [
        # Tokens
        "wydajność", "performance", "szybkość", "speed",
        "fps", "lag", "laguje", "lagi", "wolno",
        # Multi-word
        "zacina się", "zacięcia ma", "działa wolno", "powolny komputer",
        "jak szybki", "aktualna wydajność", "obciążenie systemu",
        "how fast", "is it fast", "slow pc", "runs slow",
        "current performance", "performance check",
    ],
    "stats": [
        # Tokens
        "statystyki", "stats", "statistics", "dane", "averages",
        # Multi-word
        "dzisiejsze średnie", "show stats", "usage stats",
        "today stats", "daily stats", "dzisiejsze dane",
        "średnie cpu", "średnie ram",
    ],
    "uptime": [
        # Tokens
        "uptime", "sesja",
        # Multi-word
        "czas pracy", "jak długo", "od kiedy działa", "ile czasu",
        "od ilu godzin", "session time", "how long running",
        "jak długo działa", "czas sesji",
        "how long", "session uptime",
    ],
    "processes": [
        # Tokens
        "procesy", "process", "processes", "aplikacje", "programy",
        # Multi-word
        "co zajmuje cpu", "co używa cpu", "co zużywa ram",
        "top procesy", "który program",
        "jaki program obciąża", "jakie aplikacje działają",
        "top apps", "top processes", "what is using cpu",
        "what's using", "most cpu", "cpu hog",
    ],

    # ── Optimisation & power ──────────────────────────────────────────────────
    "optimization": [
        # Tokens
        "optymalizacja", "optimization", "optimize",
        # Multi-word
        "optymalizuj komputer", "jak przyspieszyć", "jak zoptymalizować",
        "wyczyść komputer", "speed up pc",
        "make it faster", "improve performance",
        "jak poprawić wydajność",
    ],
    "power_plan": [
        # Tokens
        "zasilanie", "power", "energia",
        # Multi-word
        "plan zasilania", "tryb oszczędzania", "power saving",
        "zużycie prądu", "battery saver", "high performance plan",
        "aktywny plan zasilania", "current power plan",
        "what power plan", "power mode",
    ],

    # ── Conversational ────────────────────────────────────────────────────────
    "greeting": [
        "cześć", "hej", "hi", "hello", "siema", "yo",
        "dzień dobry", "dobry wieczór", "dobry ranek",
        "hejka", "hejki", "siemka", "witaj",
        "good morning", "good evening", "hey there",
    ],
    "thanks": [
        "dziękuję", "dzięki", "dzięki wielkie", "dziękuję bardzo",
        "thanks", "thank you", "thx", "spoko", "ok dzięki",
        "wielkie dzięki", "super dzięki", "thanks a lot",
    ],
    "help": [
        # Tokens
        "pomoc", "help", "komendy", "commands",
        # Multi-word
        "co potrafisz", "co umiesz", "co możesz",
        "jak używać", "lista komend", "jak ci pisać",
        "what can you do", "how to use", "show commands",
        "what do you know", "help me",
    ],

    # ── Small talk / open conversation → goes to Ollama ──────────────────────
    "small_talk": [
        # deliberately low-scoring single tokens (Ollama handles these better)
        "powiedz", "opowiedz", "zastanów", "jak myślisz",
        "co sądzisz", "twoja opinia", "porozmawiajmy",
        "tell me", "what do you think", "your opinion",
        "co o tym", "ciekawostka", "wiesz że",
    ],
}

# ── Entity extraction map ─────────────────────────────────────────────────────
# token → canonical entity name
ENTITY_MAP: Dict[str, str] = {
    # Components
    "cpu": "cpu", "procesor": "cpu", "processor": "cpu",
    "gpu": "gpu", "grafika": "gpu", "karta": "gpu",
    "ram": "ram", "pamięć": "ram", "memory": "ram",
    "dysk": "storage", "ssd": "storage", "hdd": "storage",
    "nvme": "storage", "storage": "storage",
    "płyta": "motherboard", "motherboard": "motherboard",

    # Metrics
    "temperatura": "temperature", "temp": "temperature", "temperature": "temperature",
    "użycie": "usage", "obciążenie": "usage", "usage": "usage",
    "taktowanie": "clock", "ghz": "clock", "mhz": "clock",
    "wydajność": "performance", "performance": "performance",
    "zdrowie": "health", "health": "health",
    "procesy": "processes", "processes": "processes",
}

# ── Stopwords (ignored during tokenisation) ───────────────────────────────────
STOPWORDS = frozenset({
    # Polish
    "a", "i", "w", "z", "do", "na", "to", "że", "jak", "czy",
    "jest", "są", "ma", "mi", "się", "co", "o", "po", "dla",
    "ten", "ta", "te", "tego", "tej", "nie", "tak", "już",
    "by", "się", "tu", "tam", "mój", "moja", "moje", "tego",
    # English
    "the", "a", "an", "is", "are", "my", "me", "be", "of",
    "in", "on", "at", "to", "for", "it", "its", "and", "or",
    "can", "you", "i", "do", "this", "that",
})
