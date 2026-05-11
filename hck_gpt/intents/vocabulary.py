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
        "co mam za procesor", "jaki to procesor", "powiedz mi o procesorze",
        "what cpu", "my cpu", "show cpu", "cpu info",
        "which cpu", "what processor", "my processor",
        "cpu details", "processor details",
        "tell me about my cpu", "show me my processor",
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
        "jaki mam dysk", "jaki dysk", "jaki dysk mam", "model dysku",
        "disk space", "my disk", "storage space", "free space",
        "how much space", "disk usage",
        "what disk", "what disk do i have", "which disk", "what drive",
        "what drives", "what hard drive", "disk model", "drive model",
        "what storage", "my storage", "storage info",
    ],
    "hw_all": [
        # Tokens
        "spec", "specs", "podzespoły", "komponenty", "components",
        # Multi-word
        "specyfikacja", "co mam", "mój komputer", "mój pc",
        "moje podzespoły", "jakie mam podzespoły", "jaki mam sprzęt",
        "pokaż sprzęt", "pokaż specyfikację", "pokaż podzespoły",
        "pełna specyfikacja", "parametry komputera",
        "my specs", "my computer", "show specs", "full specs",
        "what hardware", "hardware info", "pc info", "system info",
        "show hardware", "all specs",
        "what components", "what components i have", "which components",
        "my components", "all components", "show components",
        "what do i have", "show me my specs",
    ],

    # ── Proactive message follow-up — "what does that mean?" ─────────────────
    "explain_proactive": [
        # Polish tokens
        "wyjaśnij", "wytłumacz", "objaśnij",
        # Polish multi-word
        "co to znaczy", "co oznacza", "co miałeś na myśli",
        "wyjaśnij ostatnią wiadomość", "co to był za komunikat",
        "o co chodzi z tym", "wytłumacz mi to",
        "co chciałeś powiedzieć", "co to za wiadomość",
        "co znaczy taka wiadomość", "o co chodzi z tym komunikatem",
        "co oznacza ta wiadomość", "co to znaczy 3/7",
        "co to znaczy 4/7", "co to znaczy 5/7", "co to znaczy 6/7",
        "co to znaczy 7/7", "co to znaczy 2/7",
        "co oznacza x/7", "co to jest x/7",
        # English tokens
        "explain", "clarify",
        # English multi-word
        "what does that mean", "what did you mean",
        "explain that", "explain the message",
        "what was that message", "clarify that",
        "what does 3/7 mean", "what is 3/7",
        "what 3/7", "explain 3/7",
        "what does 2/7 mean", "what does 4/7 mean",
        "what does 5/7 mean", "what does 6/7 mean",
        "what does 7/7 mean",
        "what does it mean", "i don't understand that",
        "explain that notification", "what was that notification",
        "what was that alert", "what did that mean",
        "what does that notification mean", "explain the alert",
        "what were you saying", "what do you mean by that",
    ],

    # ── System health & diagnostics ───────────────────────────────────────────
    "health_check": [
        # Tokens
        "zdrowie", "health", "kondycja", "diagnostyka", "diagnostics",
        # Multi-word PL ← these raise confidence significantly
        "stan systemu", "czy ok", "czy działa ok", "czy wszystko ok",
        "sprawdź komputer", "oceń komputer",
        "czy komputer jest zdrowy", "jak działa mój komputer",
        "jak mój pc", "czy jest ok", "czy mam problem",
        "jak system", "jak sobie radzi komputer", "jak sobie radzi pc",
        "oceń stan pc", "pokaż stan systemu", "co słychać z pc",
        "czy pc jest w porządku", "jak wygląda zdrowie systemu",
        # Multi-word EN
        "health check", "system health", "is my pc ok",
        "check health", "pc health", "system check",
        "check system", "run diagnostics",
        "is everything ok", "is it ok",
        "how is my pc doing", "how is my computer doing",
        "how's my pc doing", "how's my computer",
        "how's my system", "how is my system",
        "is my pc healthy", "is my pc fine",
        "is everything running fine", "how's everything running",
        "pc status", "system status", "status check",
        "is my computer ok", "give me a status report",
        "quick health check", "how's the pc",
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
        # Multi-word PL
        "zacina się", "zacięcia ma", "działa wolno", "powolny komputer",
        "jak szybki", "aktualna wydajność", "obciążenie systemu",
        "ile cpu używam", "ile ram używam", "jak bardzo obciążony",
        "pokaż wydajność", "pokaż obciążenie", "co obciąża pc",
        # Multi-word EN
        "how fast", "is it fast", "slow pc", "runs slow",
        "current performance", "performance check",
        "how much cpu am i using", "what's my cpu usage",
        "cpu usage right now", "current cpu load",
        "how loaded is my pc", "show me performance",
        "what's my ram usage", "ram usage now",
        "how hard is my pc working", "how busy is my pc",
        "what's the current load", "show system load",
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

    # ── Program info / meta ───────────────────────────────────────────────────
    "about_program": [
        # Polish — multi-word (high bonus)
        "jak działa program", "o czym jest program", "czym jest pc workman",
        "co to jest ten program", "co robi program", "jakie są funkcje",
        "jak to działa", "powiedz o programie", "opisz program",
        "co to workman", "czym jest hck", "do czego służy program",
        "o czym jest aplikacja", "co potrafi program", "co umie program",
        "co robi ten program", "co ten program robi", "jak działa ta aplikacja",
        "czym jest ta aplikacja", "co to za program", "do czego to służy",
        "po co jest ten program", "opowiedz o programie", "jakie funkcje ma",
        "co oferuje program", "jakie możliwości ma",
        # Single tokens
        "workman", "aplikacja", "hck_gpt",
        # English
        "how does it work", "what is this program", "what is pc workman",
        "what does this do", "what is this software", "about this app",
        "tell me about this program", "what is this app",
        "what does pc workman do", "what does the program do",
        "program features", "what can this do", "about the program",
        "describe this software", "what does this program do",
        "what is hck", "what is workman", "explain this app",
    ],
    "about_author": [
        # Polish
        "kto stworzył", "kto jest autorem", "kto to zrobił",
        "kto napisał program", "kto zbudował", "kto opracował",
        "autor programu", "twórca programu", "kto cię stworzył",
        "kto cię zrobił", "przez kogo",
        # English
        "who made this", "who is the author", "who created this",
        "who built this", "who wrote this", "who developed this",
        "author of this program", "creator of pc workman",
        "who made you", "who are you made by",
    ],

    # ── Security / virus check ────────────────────────────────────────────────
    "virus_check": [
        # Polish
        "czy mam wirusa", "sprawdź wirusy", "czy jest malware",
        "czy jest zagrożenie", "czy mam złośliwe oprogramowanie",
        "sprawdź bezpieczeństwo", "czy coś podejrzanego działa",
        "podejrzane procesy", "analiza bezpieczeństwa",
        "czy coś złego działa", "czy mój komputer jest zainfekowany",
        "skanowanie wirusów", "przeskanuj komputer",
        # English
        "do i have a virus", "virus check", "check for malware",
        "any malware running", "security check", "suspicious processes",
        "check security", "is there malware", "am i infected",
        "check for threats", "malware scan", "any threats",
        "is something suspicious running", "virus scan",
        "check for viruses", "any dangerous processes",
    ],

    # ── Background / unnecessary programs ─────────────────────────────────────
    "unnecessary_programs": [
        # Polish
        "niepotrzebne programy", "czy są niepotrzebne programy",
        "czy chodzą w tle niepotrzebne programy",
        "czy chodzą jakieś niepotrzebne programy",
        "czy mam niepotrzebne programy", "co chodzi w tle",
        "co działa w tle", "jakie programy działają w tle",
        "zbędne programy", "niepotrzebne aplikacje w tle",
        "co zużywa zasoby w tle", "wyłącz niepotrzebne",
        "jakie aplikacje pożerają ram",
        # English
        "unnecessary programs", "useless background apps",
        "any unnecessary programs running", "what is running in background",
        "unnecessary apps", "bloatware check",
        "background apps using resources",
        "what programs are running unnecessarily",
        "any background bloat",
    ],

    # ── Disk speed / optimization ─────────────────────────────────────────────
    "disk_speed": [
        # Polish
        "jak przyspieszyć dysk", "dysk wolno chodzi",
        "przyspieszenie dysku", "dysk jest wolny",
        "jak wyczyścić dysk", "dysk c pełny",
        "wolny dysk", "problemy z dyskiem",
        "jak zwolnić miejsce na dysku", "co zajmuje dysk",
        "co zajmuje miejsce", "dysk prawie pełny",
        # English
        "how to speed up disk", "disk is slow", "slow disk",
        "speed up disk", "disk full", "disk optimization",
        "optimize disk", "hard drive slow", "disk drive slow",
        "how to free disk space", "what is using disk space",
        "disk almost full", "clean up disk",
    ],

    # ── Speed up PC / FPS ─────────────────────────────────────────────────────
    "speed_up_pc": [
        # Polish
        "jak przyspieszyć komputer", "przyspiesz komputer",
        "jak mieć więcej fps", "komputer działa wolno",
        "jak poprawić fps", "jak przyspieszyć gry",
        "wolny komputer co zrobić", "co zrobić żeby komputer był szybszy",
        "przyspieszenie komputera", "jak zoptymalizować komputer",
        "jak przyspieszyć windows", "komputer chodzi wolno",
        "co zrobić z wolnym komputerem", "przyspiesz pc",
        "jak poprawić wydajność komputera",
        # English
        "how to speed up pc", "speed up my computer",
        "how to get more fps", "pc is slow what to do",
        "how to make pc faster", "pc runs slow",
        "how to improve fps", "make games run faster",
        "boost pc performance", "how to make computer faster",
        "my pc is slow", "improve computer speed",
        "get more fps", "how do i speed up my pc",
    ],

    # ── Small talk / open conversation → goes to Ollama ──────────────────────
    "small_talk": [
        # greeting-style small talk (higher score so rule fallback works)
        "jak się masz", "co słychać", "co u ciebie", "jak leci",
        "dobry wieczór", "dobry ranek", "dzień dobry",
        "jakie masz rady", "co mi radzisz", "co dziś polecasz",
        "how are you", "what's up", "good evening", "good morning",
        "any tips for today", "what do you recommend",
        # deliberate open-ended (Ollama handles better)
        "powiedz", "opowiedz", "zastanów", "jak myślisz",
        "co sądzisz", "twoja opinia", "porozmawiajmy",
        "tell me", "what do you think", "your opinion",
        "co o tym", "ciekawostka", "wiesz że",
    ],

    # ── TURBO Boost ───────────────────────────────────────────────────────────
    "turbo_boost": [
        # Polish
        "turbo", "turbo boost", "włącz turbo", "uruchom turbo",
        "co robi turbo", "jak działa turbo", "czy warto turbo",
        "co to turbo", "czym jest turbo boost", "turbo mode",
        "tryb turbo", "włącz tryb turbo", "aktywuj turbo",
        "co daje turbo", "czy turbo pomaga", "kiedy włączyć turbo",
        "turbo boost co to", "turbo boost jak włączyć",
        # English
        "enable turbo", "turn on turbo", "what is turbo boost",
        "what does turbo do", "turbo boost mode", "how does turbo work",
        "activate turbo", "is turbo worth it", "turbo boost help",
    ],

    # ── Why slow / lag ────────────────────────────────────────────────────────
    "why_slow": [
        # Polish
        "dlaczego laguje", "dlaczego wolno", "dlaczego komputer wolno działa",
        "co spowalnia", "co spowalnia komputer", "co spowalnia pc",
        "komputer się zacina", "lagi na pc", "lagi w grze",
        "dlaczego jest lag", "co powoduje lagi", "co powoduje spowolnienie",
        "dlaczego gra laguje", "dlaczego działa tak wolno",
        "co obciąża komputer", "co tak zwalnia", "skąd te lagi",
        "co powoduje że jest wolno", "pc jest wolny dlaczego",
        "dlaczego mój komputer laguje",
        # English
        "why is my pc slow", "why is it lagging", "what causes lag",
        "what is slowing down my pc", "why does my computer lag",
        "what's causing the slowdown", "why is everything slow",
        "why does it stutter", "why am i getting lag",
        "my pc is slow why", "what's making my pc slow",
    ],

    # ── Process info ──────────────────────────────────────────────────────────
    "process_info": [
        # Polish
        "co to jest", "co to za proces", "co robi ten proces",
        "czym jest svchost", "co to svchost.exe", "co to explorer.exe",
        "co to chrome.exe", "co to discord.exe",
        "czy mogę wyłączyć", "czy bezpiecznie wyłączyć",
        "czy ten proces jest bezpieczny", "czy to wirus",
        "co to za program", "czym jest ten program",
        "do czego służy ten proces", "ten proces co robi",
        "czy mogę zabić ten proces", "czy warto wyłączyć",
        # English
        "what is this process", "what does this process do",
        "what is svchost", "can i disable this", "is this safe to kill",
        "can i end this process", "what is chrome.exe",
        "is this a virus", "what does svchost do",
        "should i close this process", "what is this program",
        "is it safe to end this task",
    ],

    # ── RAM why high ──────────────────────────────────────────────────────────
    "ram_why_high": [
        # Polish
        "dlaczego ram jest wysoki", "dlaczego ram jest pełny",
        "dlaczego ram jest na 90", "dlaczego ram jest zajęty",
        "co zajmuje ram", "co zużywa ram", "ram jest pełny dlaczego",
        "czy ram jest dobry", "czy mój ram wystarczy",
        "dlaczego pamięć jest zajęta", "co zajmuje pamięć",
        "ram skacze", "ram rośnie", "dlaczego ram rośnie",
        "czy to normalne że ram jest na 94", "czy ram na 90 to normalne",
        "ram przekroczył", "ram za wysoki", "za mało ramu",
        # English
        "why is ram so high", "why is ram full", "what's using ram",
        "what is eating my ram", "ram is at 90 percent why",
        "why is memory so high", "what uses so much ram",
        "is ram at 94 percent normal", "why is ram jumping",
        "what's consuming my memory",
    ],

    # ── GPU temperature why ───────────────────────────────────────────────────
    "gpu_temp_why": [
        # Polish
        "czy gpu się przegrzewa", "dlaczego gpu jest gorące",
        "gpu temperatura za wysoka", "karta graficzna się grzeje",
        "dlaczego karta graficzna jest gorąca", "gpu nagrzewa się",
        "gpu 80 stopni", "gpu 85 stopni", "gpu 90 stopni",
        "czy gpu temp jest normalna", "ile powinna mieć gpu temperatura",
        "gpu przegrzanie", "jak schłodzić gpu", "gpu za gorące",
        # English
        "is my gpu overheating", "why is gpu so hot",
        "gpu temperature too high", "gpu running hot",
        "is 80 degrees gpu normal", "is gpu 85c ok",
        "gpu thermal throttling", "how to cool down gpu",
        "why is my graphics card hot",
    ],

    # ── Disk health ───────────────────────────────────────────────────────────
    "disk_health": [
        # Polish
        "czy dysk jest zdrowy", "stan dysku", "zdrowie dysku",
        "czy ssd jest ok", "czy hdd jest ok", "sprawdź dysk",
        "czy dysk może paść", "czy dysk nie umiera",
        "smart dysk", "badania dysku", "diagnoza dysku",
        "ile zostało dyskowi", "czy dysk jest dobry",
        "dysk robi dziwne dźwięki", "problemy z dyskiem",
        "czy dysk się starzeje",
        # English
        "is my disk healthy", "disk health check", "check disk health",
        "is my ssd ok", "is my hdd ok", "disk smart status",
        "how long will my disk last", "is my drive failing",
        "check drive health", "disk diagnostics",
    ],

    # ── Startup programs check ───────────────────────────────────────────────
    "startup_check": [
        # Polish
        "czy mam za dużo programów startowych", "ile mam programów startowych",
        "co odpala się przy starcie", "co uruchamia się przy starcie",
        "jakie programy startują automatycznie", "co się włącza przy logowaniu",
        "za dużo autostart", "autostart sprawdź", "co jest w autostarcie",
        "czy mój autostart jest ok", "sprawdź autostart",
        "ile rzeczy odpala się z windows", "za dużo na starcie",
        # English
        "too many startup programs", "check startup apps", "startup programs list",
        "what starts with windows", "startup check", "what launches on boot",
        "how many startup programs", "startup manager", "autostart check",
        "what runs at startup", "startup bloat",
    ],

    # ── High disk usage diagnosis ─────────────────────────────────────────────
    "disk_usage_why": [
        # Polish
        "dlaczego dysk jest obciążony", "co zajmuje dysk", "dysk usage wysoki",
        "dlaczego dysk pracuje na 100", "dysk na 100 procent dlaczego",
        "co obciąża dysk", "skąd takie obciążenie dysku", "dysk szaleje",
        "dysk muli dlaczego", "co tak bardzo korzysta z dysku",
        "dlaczego led dysku cały czas miga", "aktywność dysku wysoka",
        "disk activity 100", "wysoka aktywność dysku",
        # English
        "why is disk at 100", "disk usage high why", "what's causing disk activity",
        "disk is at 100 percent", "why disk so active", "high disk usage",
        "disk thrashing", "why is my disk so busy", "disk io why",
        "what is reading my disk", "disk activity cause",
    ],

    # ── Battery / power drain ─────────────────────────────────────────────────
    "battery_drain": [
        # Polish
        "który proces zużywa baterię", "co niszczy baterię",
        "co rozładowuje baterię", "bateria szybko się rozładowuje dlaczego",
        "co drenauje baterię", "co zabiera baterię", "brak baterii dlaczego",
        "który program jest najgorszy dla baterii", "co zużywa prąd",
        "jak oszczędzić baterię", "bateria szybko siada",
        "który proces rozładowuje baterię teraz", "co teraz zjada baterię",
        "co zużywa baterię w tej chwili", "który program zabija baterię",
        "co teraz drenuje baterię", "bateria się rozładowuje co to",
        # English
        "what drains battery", "battery drain cause", "which app drains battery",
        "why does battery drain so fast", "battery life bad why",
        "what uses most battery", "battery drain fix",
        "which process kills battery", "save battery", "battery saving",
        "which process is draining my battery right now",
        "what is draining my battery right now",
        "what's eating my battery", "which app is killing my battery",
        "what process uses most battery", "battery draining fast what to do",
    ],

    # ── Performance change / delta ────────────────────────────────────────────
    "perf_change": [
        # Polish
        "co się zmieniło w wydajności", "co się zmieniło od ostatniego uruchomienia",
        "czy jest gorzej niż ostatnio", "od kiedy jest wolniej",
        "kiedy zaczęło być wolniej", "co się zmieniło od startu",
        "dlaczego dziś jest wolniej niż wczoraj", "co nowego obciąża komputer",
        "co się pojawiło nowego", "które procesy są nowe",
        "od kiedy komputer spowalnia", "kiedy zaczęło lagować",
        # English
        "what changed in performance", "what changed since last boot",
        "why is it slower than yesterday", "when did it get slow",
        "what's new that's slowing things", "performance got worse when",
        "new processes slowing pc", "what recently started using cpu",
        "performance degraded why", "what changed recently",
    ],

    # ── Fun / roast / personality ─────────────────────────────────────────────
    "fun_roast": [
        # Polish — meme questions
        "dlaczego mój komputer mnie nienawidzi", "komputer mnie nienawidzi",
        "czy mój pc jest głupi", "pc jest głupi", "komputer jest głupi",
        "który proces jest największym leniem", "który program jest leniem",
        "czy mogę powiedzieć chrome żeby się zamknął", "chrome się zamknij",
        "dlaczego discord działa w tle jak stalker", "discord stalker",
        "czy svchost to szpieg", "svchost szpieg", "czy to szpieg",
        "czy mogę zrobić mojemu pc timeout", "pc timeout",
        "dlaczego wszystko ładuje się jakby miało kaca",
        "komputer ma kaca", "kac komputerowy",
        "który program jest największym złodziejem ram",
        "mój komputer dzisiaj leniwy", "pc jest leniwy dzisiaj",
        "komputer sobie nie radzi", "komputer jest zmęczony",
        # English — meme questions
        "why does my computer hate me", "my pc hates me",
        "is my pc dumb", "is my computer stupid",
        "which process is the laziest", "who is the laziest program",
        "can i tell chrome to close itself", "chrome please close",
        "why does discord run in background like a stalker",
        "is svchost a spy", "svchost spy",
        "can i give my pc a timeout",
        "why does everything load like it has a hangover",
        "my computer is lazy today", "pc is tired today",
        "which program steals the most ram",
    ],

    # ── Startup safety — can I disable X from startup? ───────────────────────
    "startup_safety": [
        # Polish
        "czy mogę wyłączyć ze startu", "czy bezpiecznie wyłączyć ze startu",
        "czy warto wyłączyć ze startu", "czy X w autostarcie jest potrzebny",
        "czy powinienem wyłączyć ze startu", "co mogę wyłączyć ze startu",
        "które programy startowe wyłączyć", "jakie programy startowe są zbędne",
        "czy chrome może startować z windows", "czy discord musi startować",
        "czy spotify potrzebuje autostart", "czy steam musi startować z windows",
        "czy mogę usunąć z autostartu", "co usunąć z autostartu",
        "które wpisy startowe są bezpieczne", "czy ten program musi startować",
        "wyłączyć chrome ze startu", "wyłączyć discord ze startu",
        "wyłączyć spotify ze startu", "wyłączyć steam ze startu",
        # English
        "is it safe to disable from startup", "can i disable from startup",
        "should i disable from startup", "which startup programs to disable",
        "can i remove from startup", "safe to remove from startup",
        "is it safe to disable chrome from startup",
        "is it safe to disable discord from startup",
        "should i disable spotify from startup",
        "can i turn off steam from startup", "what startup programs can i disable",
        "which startup entries are safe to remove",
        "is x safe to disable at startup", "disable from autostart",
    ],

    # ── What changed on my PC since yesterday ────────────────────────────────
    "pc_changes": [
        # Polish
        "co się zmieniło od wczoraj", "co nowego na pc",
        "co zmieniło się w systemie", "jakie zmiany od wczoraj",
        "co jest inne niż wczoraj", "co nowego od ostatniego razu",
        "zmiany systemowe", "co się pojawiło nowego w systemie",
        "co się zmieniło na komputerze", "jakie są zmiany na pc",
        "co nowego na komputerze", "co nowego w systemie",
        "co się zmieniło od ostatniego uruchomienia systemu",
        "jakie zmiany zaszły", "co się różni od wczoraj",
        # English
        "what changed since yesterday", "what's new on my pc",
        "what changed on my pc", "what changed in the system",
        "what's different today", "any changes since yesterday",
        "what system changes happened", "what changed on my computer",
        "what's new since last time", "what has changed",
        "what changed on pc since yesterday", "system changes today",
    ],

    # ── System risk assessment ────────────────────────────────────────────────
    "system_risk": [
        # Polish
        "co zagraża mojemu pc", "analiza ryzyka systemu", "ryzyko systemu",
        "które zmiany są ryzykowne", "co stwarza ryzyko",
        "co zagraża wydajności", "co zagraża stabilności",
        "co może się zepsuć", "co powoduje największe ryzyko",
        "jakie są ryzyka systemu", "które zmiany powodują problemy",
        "co jest niebezpieczne w systemie", "co zagraża bezpieczeństwu",
        "analiza zagrożeń", "stabilność systemu",
        "co zagraża wydajności bezpieczeństwu stabilności",
        "które zmiany tworzą ryzyko",
        # English
        "what risks does my pc have", "system risk assessment",
        "which changes create risk", "what poses the highest risk",
        "what is risky on my pc", "performance security stability risk",
        "what threatens my system", "risk analysis",
        "what could break", "what causes the most problems",
        "which recent changes are risky", "system stability risk",
        "what is creating stability risk", "what creates performance risk",
        "recent changes highest risk", "system threat analysis",
    ],

    # ── Browser cache / slow browser ─────────────────────────────────────────
    "browser_cache": [
        # Polish
        "czy przeglądarka jest wolna przez cache", "przeglądarka wolna przez cache",
        "czy chrome ma za duży cache", "czy firefox ma za duży cache",
        "cache przeglądarki jest za duży", "wyczyść cache przeglądarki",
        "przeglądarka zwalnia przez cache", "przeglądarka jest powolna przez cache",
        "co zajmuje pamięć w chrome", "chrome zajmuje za dużo ram",
        "chrome jest wolny dlaczego", "firefox jest wolny dlaczego",
        "edge jest wolny dlaczego", "przeglądarka pożera ram",
        "chrome pożera ram", "chrome żre ram", "cache przeglądarki",
        "czy warto wyczyścić cache", "kiedy wyczyścić cache",
        "co to cache przeglądarki", "jak zmniejszyć zużycie ram przez chrome",
        "dlaczego przeglądarka zajmuje tyle ram",
        # English
        "browser slow because of cache", "is browser slow because of caching",
        "can you tell me if my browser is getting slow because of huge caching",
        "browser cache too big", "clear browser cache", "chrome cache issue",
        "why is chrome using so much ram", "why is browser using so much memory",
        "chrome eating memory", "browser memory hog", "firefox memory issue",
        "is my browser cache too large", "browser slow memory",
        "chrome slow why", "edge slow why", "firefox slow why",
        "browser ram usage high", "how to fix browser slowness",
        "browser consuming too much memory", "chrome tab memory",
    ],

    # ── RAM usage comparison between sessions / experiments ──────────────────
    "ram_compare": [
        # Polish
        "porównaj użycie ram", "porównaj ram z poprzedniej sesji",
        "ile ram było wcześniej", "ram był wyższy wcześniej",
        "porównaj exp1 i exp2 ram", "porównaj eksperymenty ram",
        "jak ram wyglądał wcześniej", "ram w sesji poprzedniej",
        "porównaj ram teraz i wcześniej", "porównaj zużycie pamięci",
        "ile ram zajmował wcześniej program", "zmiana zużycia ram",
        "ram rósł od startu", "jak ram rósł przez sesję",
        "sesja vs sesja ram", "compare ram usage",
        "było więcej ram zajęte wcześniej", "ram wcześniej vs teraz",
        # English
        "compare my exp1 and exp2 ram usage", "compare ram usage between experiments",
        "compare ram sessions", "ram usage comparison",
        "how does ram compare now vs before", "ram was higher earlier",
        "ram increased over session", "compare ram between runs",
        "session ram comparison", "how much ram was used before",
        "ram usage then vs now", "did ram grow over time",
        "compare memory usage", "ram usage over time",
        "how much ram did it use earlier",
    ],

    # ── Swap / pagefile / virtual memory analysis ─────────────────────────────
    "swap_analysis": [
        # Polish
        "plik wymiany", "pagefile", "swap", "wirtualna pamięć",
        "co zajmuje swap", "co korzysta ze swap", "swap jest pełny",
        "za mało ram swap używany", "procesy na swapie",
        "które procesy używają swap", "swap usage wysoki",
        "plik stronicowania pełny", "pagefile overflow",
        "dlaczego jest swap", "swap spowalnia komputer",
        "co siedzi na pagefile", "ram skończony swap używany",
        "procesy korzystające ze swap", "swap wysoki co zrobić",
        "jak zmniejszyć swap", "jak wyłączyć swap",
        "czy swap spowalnia", "czy plik wymiany jest za mały",
        # English
        "which processes are taking up a lot of swap space and slowing me down",
        "what is using swap space", "swap usage high", "pagefile full",
        "what processes use swap", "swap space analysis",
        "virtual memory usage", "pagefile overflow",
        "too much swap being used", "swap is slow",
        "processes using pagefile", "why is swap full",
        "how to reduce swap usage", "ram out pagefile used",
        "swap is eating performance", "pagefile performance impact",
        "what's in my pagefile", "is swap slowing me down",
        "virtual memory full", "swap file too small",
    ],

    # ── USB / external drive transfer monitoring ──────────────────────────────
    "usb_transfer": [
        # Polish
        "zewnętrzny dysk transfer", "usb transfer", "kopiuję pliki ile cpu",
        "transfer zdjęć ile cpu", "podłączyłem zewnętrzny dysk",
        "zewnętrzny ssd podłączyłem", "usb kopiowanie ile zasobów",
        "ile cpu zajmuje transfer", "transfer plików cpu",
        "kopiowanie plików obciążenie", "usb dysk aktywność",
        "transfer danych cpu", "zewnętrzny dysk aktywność",
        "ile io dysku przy kopiowaniu", "usb transfer obciążenie",
        "czy transfer spowalnia komputer", "kopiuję przez usb",
        "transfer z dysku zewnętrznego", "skopiować pliki obciążenie",
        "ile zajmuje kopiowanie", "prędkość transferu usb",
        # English
        "i connected my external ssd and am transferring photos how much cpu is it taking up",
        "external ssd transfer cpu usage", "usb transfer cpu load",
        "copying files how much cpu", "file transfer cpu usage",
        "external drive transfer speed", "usb activity cpu",
        "how much cpu does file transfer use", "disk io during transfer",
        "transfer speed external drive", "copying photos cpu usage",
        "external drive connected cpu load", "usb copy performance",
        "how much resources does transfer use", "file copy cpu cost",
        "disk transfer activity", "is file transfer slowing my pc",
        "usb drive cpu overhead", "external disk io",
    ],

    # ── Network usage by process ──────────────────────────────────────────────
    "network_usage": [
        # Polish
        "co używa internetu", "co korzysta z sieci", "co pobiera",
        "który program pobiera dane", "który program wysyła dane",
        "co zajmuje sieć", "sieć jest obciążona", "internet jest wolny dlaczego",
        "które procesy używają sieci", "co drenuje sieć",
        "co zużywa bandwidth", "co używa wifi", "co korzysta z wifi",
        "który program używa internetu", "co pobiera w tle",
        "co wysyła dane w tle", "aktywność sieciowa", "ruch sieciowy",
        "ile danych pobiera mój komputer", "co niszczy internet",
        "aktywność sieci", "który program żre internet",
        "internet zajęty kto", "sieć 100 procent kto",
        # English
        "which process is using the network", "what is using my internet",
        "what's eating my bandwidth", "network usage by process",
        "which app is downloading in background", "what is using wifi",
        "who is using my network", "network activity monitor",
        "what process is sending data", "what process is receiving data",
        "background downloads", "what is using my connection",
        "which app uses most bandwidth", "network hog",
        "why is my internet slow which process", "who is eating my bandwidth",
        "internet usage by app", "network traffic by process",
        "what is downloading", "what is uploading",
    ],

    # ── Session compare ───────────────────────────────────────────────────────
    "session_compare": [
        # Polish
        "co się zmieniło", "co się zmieniło od ostatniego razu",
        "jak było wczoraj", "dlaczego wczoraj było lepiej",
        "porównaj sesje", "porównaj z wczorajszym",
        "jaka była wczoraj", "ile wczoraj zużywał cpu",
        "jak wyglądała poprzednia sesja", "co się zmieniło od wczoraj",
        "czy jest gorzej niż wczoraj", "czy jest lepiej niż wczoraj",
        "wczorajsze statystyki", "porównanie z wczorajem",
        # English
        "what changed since last time", "compare with yesterday",
        "was it better yesterday", "how does today compare",
        "session comparison", "yesterday vs today",
        "was cpu lower yesterday", "what changed",
        "compare sessions", "is today worse than yesterday",
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
    # Actions
    "turbo": "turbo", "lag": "lag", "lagi": "lag",
    "wczoraj": "yesterday", "yesterday": "yesterday",
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
