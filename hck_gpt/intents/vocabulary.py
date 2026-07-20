# hck_gpt/intents/vocabulary.py
"""
Vocabulary - intent trigger patterns and entity extraction maps.

Both Polish and English keywords are present in every intent so the
chatbot responds to mixed-language input without any translation step.

Pattern scoring (in parser.py):
  - Multi-word phrases:  len(words) * 1.5  (biggest bonus)
  - Exact single token:  1.0
  - Partial prefix:      0.4
  - Normalised:          min(1.0, score / 3.0)

Adding more multi-word phrases to an intent raises its confidence score,
making it more likely to be handled by the rule engine (threshold 0.60).
Ambiguous / open-ended queries remain below threshold -> Ollama LLM.
"""
from __future__ import annotations
from typing import Dict, List

# ── Intent patterns ───────────────────────────────────────────────────────────
# intent_name -> list of trigger strings (lowercase, PL + EN)

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
        "jaka mam karte", "jaka mam grafike", "jaka mam karte graficzna",
        "karta graficzna model", "ile vram", "ile ma vram",
        "what gpu", "my gpu", "gpu info", "graphics info",
        "which graphics", "what graphics card", "what gpu do i have",
        "what gpu am i running", "tell me my gpu",
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
        "płyta", "płyta główna", "plyta",
        # Multi-word
        "jaka płyta", "moja płyta", "model płyty",
        "plyta glowna", "jaka plyte", "jaka mam plyte", "jaka mam plyte glowna",
        "co to za plyta", "model plyty",
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

    # ── Proactive message follow-up - "what does that mean?" ─────────────────
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
        # Multi-word PL <- these raise confidence significantly
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
        # colloquial variants (2026-07-16 pass)
        "mocno się grzeje",
        "laptop parzy",
        "gorący laptop",
        "komp się przegrzewa",
        "wysoka temperatura",
        "pc is overheating",
        "my pc is burning up",
        "computer gets really hot",

        # warm/hot phrasings (Samanta report 2026-07-06)
        "dlaczego mój laptop jest ciepły",
        "czemu laptop jest ciepły",
        "laptop jest ciepły",
        "dlaczego komputer jest gorący",
        "czemu komputer jest gorący",
        "komputer jest gorący",
        "dlaczego jest tak gorąco",
        "czemu tak gorąco w komputerze",
        "laptop się grzeje",
        "komputer się grzeje",
        "czemu się grzeje",
        "dlaczego mój pc jest gorący",
        "why is my laptop warm",
        "why is my laptop hot",
        "why is my pc hot",
        "my computer is hot",
        "why is it so hot",
        "why is my laptop heating up",
        "my laptop is warm",
        # Natural phrasings - routing audit 2026-06
        "przegrzany", "czy przegrzany", "komputer przegrzany",
        "czy mój komputer jest przegrzany", "komputer jest przegrzany",
        "czy się przegrzewa", "przegrzewa się", "za gorący",
        "czy za gorące", "czy procesor się grzeje za mocno",
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
        # Natural phrasings - routing audit 2026-06
        "czy coś throttluje", "coś throttluje", "throttluje wydajność",
        "czy coś throttluje wydajność", "czy coś dławi wydajność",
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
        # Natural phrasings - routing audit 2026-06
        "średnie obciążenie", "dzisiejsze obciążenie", "jakie mam dzisiaj średnie",
        "średnie zużycie", "obciążenie dzisiaj", "dzisiaj średnie obciążenie",
        "moje średnie", "jakie mam dzisiaj średnie obciążenie",
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
        # Natural phrasings - routing audit 2026-06
        "najbardziej obciąża", "co najbardziej obciąża", "co obciąża teraz",
        "co najbardziej obciąża pc", "co najbardziej obciąża mój pc",
        "co żre", "co żre pamięć", "co żre ram", "co zżera", "co zjada pamięć",
        "najwięcej pamięci", "najwięcej zużywają", "programy zużywają ram",
        "jakie programy najwięcej zużywają ram", "które najwięcej żrą",
        "najwięcej żrą", "żre najwięcej", "top 5 procesów", "top 10 procesów",
        "które procesy żrą", "top 5 procesów które najwięcej żrą",
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
        "jak przyspieszyć", "jak zoptymalizować",
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
        "siemasz", "siemano", "elo", "joł", "no hej", "no siema",
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
        # Polish - multi-word (high bonus)
        "jak działa program", "o czym jest program", "czym jest pc workman",
        "co to jest ten program", "co robi program", "jakie są funkcje",
        "jak to działa", "powiedz o programie", "opisz program",
        "co to workman", "czym jest hck", "do czego służy program",
        "o czym jest aplikacja", "co potrafi program", "co umie program",
        "co robi ten program", "co ten program robi", "jak działa ta aplikacja",
        "czym jest ta aplikacja", "co to za program", "do czego to służy",
        "po co jest ten program", "opowiedz o programie", "jakie funkcje ma",
        "co oferuje program", "jakie możliwości ma",
        "jak działa pc workman", "czy program dobrze chodzi",
        "czy pc workman dobrze działa", "czy program działa dobrze",
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

    # ── Upgrade advice - what part to replace/upgrade ─────────────────────────
    "upgrade_advice": [
        # natural phrasings - routing audit 2026-07-02
        "czy mam stary sprzęt",
        "stary sprzęt",
        "czy mój sprzęt jest stary",
        "czy komputer jest przestarzały",
        "przestarzały sprzęt",
        "is my hardware old",
        "is my pc outdated",
        "do i have old hardware",
        # Polish - multi-word (high bonus)
        "co warto wymienić w komputerze", "co warto wymienic",
        "co warto wymienić", "warto wymienić w komputerze",
        "czy mam coś do wymiany", "co mam wymienić", "czy jakąś część wymienić",
        "czy jakąś część mam wymienić", "co mam rozbudować", "co rozbudować",
        "co ulepszyć w komputerze", "co kupić by komputer był lepszy",
        "co ulepszyć by komputer był lepszy", "co rozbudować by lepiej chodził",
        "co mam rozbudować by lepiej chodził komputer", "czy warto coś wymienić",
        "jaką część wymienić", "czy mój komputer wymaga wymiany",
        "co dokupić do komputera", "co wymienić by szybciej chodził",
        "czy coś wymienić w komputerze", "co poprawić w sprzęcie",
        "czy mam wąskie gardło", "co jest wąskim gardłem",
        "upgrade komputera", "rozbudowa komputera",
        # English
        "do i need to upgrade", "what should i upgrade", "what to upgrade",
        "which part should i replace", "should i replace any part",
        "what to buy to make my pc faster", "what hardware to upgrade",
        "is my cpu a bottleneck", "what's my bottleneck", "what is my bottleneck",
        "do i need a new gpu", "do i need more ram", "upgrade advice",
        "what should i replace",
    ],

    # ── Privacy / data - do you spy / what do you collect ─────────────────────
    "privacy_data": [
        # Polish - multi-word (high bonus)
        "czy mnie szpiegujesz", "czy ty mnie szpiegujesz", "czy szpiegujesz",
        "czy program mnie szpieguje", "czy mnie podsłuchujesz",
        "czy kradniesz dane", "czy kradniesz moje dane", "czy wykradasz dane",
        "co zapamiętujesz", "co zapamietujesz", "jakie informacje zbierasz",
        "jakie dane zbierasz", "czy zbierasz dane", "czy zbierasz moje dane",
        "czy wysyłasz moje dane", "czy wysylasz moje dane", "czy wysyłasz dane",
        "jakie dane przechowujesz", "czy moje dane są bezpieczne",
        "co o mnie wiesz", "czy mnie śledzisz", "czy program jest bezpieczny",
        # English
        "are you spying on me", "do you spy on me", "do you spy",
        "do you steal my data", "do you steal data", "what do you remember",
        "what information do you collect", "what data do you collect",
        "do you collect data", "do you collect my data", "do you send my data",
        "is my data safe", "what do you know about me", "do you track me",
        "what data do you store", "are you safe to use",
    ],

    # ── Security / virus check ────────────────────────────────────────────────
    "virus_check": [
        # colloquial variants (2026-07-16 pass)
        "chyba mam wirusa",
        "podejrzany proces",
        "coś podejrzanego działa",
        "something feels infected",
        "suspicious process running",

        # Natural phrasings - routing audit 2026-06
        "coś podejrzanego", "coś podejrzanego w tle", "czy coś podejrzanego chodzi",
        "czy coś podejrzanego chodzi w tle", "podejrzanego chodzi w tle",
        "czy discord jest bezpieczny", "czy discord bezpieczny",
        "czy ten program jest bezpieczny", "czy to bezpieczne",
        # Polish - with and without diacritics
        "czy jest jakis wirus", "czy jest wirus",
        "wirus na komputerze", "podejrzane oprogramowanie",
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
        "is discord safe", "is discord.exe safe", "is steam safe",
        "is this exe safe", "is this process safe",
        "is it a virus", "could this be a virus",
    ],

    # ── Background / unnecessary programs ─────────────────────────────────────
    "unnecessary_programs": [
        # Natural phrasings - routing audit 2026-06
        "co wyłączyć z tła", "wyłączyć coś z tła", "bezpiecznie wyłączyć",
        "co mogę wyłączyć", "co mogę bezpiecznie wyłączyć",
        "czy mogę bezpiecznie wyłączyć coś z tła", "co wyłączyć żeby szybszy",
        "co wyłączyć żeby przyspieszyć", "wyłączyć żeby pc był szybszy",
        "co mogę bezpiecznie wyłączyć żeby pc był szybszy",
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
        "jakie uslugi windows moge wylaczyc", "co moge bezpiecznie wylaczyc",
        "jakie uslugi wylaczyc", "uslugi do wylaczenia",
        "what windows services can i disable safely",
        "which services can i turn off",
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
        "szybkość dysku", "jak szybki jest dysk",
        "jak szybki jest moj dysk", "predkosc dysku",
        "odczyt dysku", "zapis dysku", "io dysku",
        "szybkość zapisu", "szybkość odczytu",
        # English
        "how to speed up disk", "disk is slow", "slow disk",
        "speed up disk", "disk full", "disk optimization",
        "optimize disk", "hard drive slow", "disk drive slow",
        "how to free disk space", "what is using disk space",
        "disk almost full", "clean up disk",
        "disk read speed", "disk write speed", "disk io speed",
        "how fast is my disk", "disk transfer speed",
    ],

    # ── Speed up PC / FPS ─────────────────────────────────────────────────────
    "speed_up_pc": [
        # natural phrasings - routing audit 2026-07-02
        "co zrobić by lepiej chodził",
        "co zrobic by lepiej chodzil",
        "co zrobić by komputer szybciej chodził",
        "żeby szybciej chodził",
        "by komputer szybciej działał",
        "jak usprawnić komputer",
        "co zrobić żeby przyspieszyć",
        "make it run faster",
        "make my pc run better",
        # Polish - "what can I disable to go faster"
        "co moge wylaczyc zeby pc byl szybszy",
        "co wylaczyc zeby szybszy", "co wylaczyc zeby pc szybciej dzialal",
        "jak przyspieszyc przez wylaczenie", "co wylaczyc dla wydajnosci",
        # Polish
        "jak przyspieszyć komputer", 
        "jak mieć więcej fps", "komputer działa wolno",
        "jak poprawić fps", "jak przyspieszyć gry",
        "wolny komputer co zrobić", "co zrobić żeby komputer był szybszy",
        "przyspieszenie komputera", 
        "jak przyspieszyć windows", "komputer chodzi wolno",
        "co zrobić z wolnym komputerem", "przyspiesz pc",
        "jak poprawić wydajność komputera",
        # English
        "how to speed up pc", 
        "how to get more fps", "pc is slow what to do",
        "how to make pc faster", "pc runs slow",
        "how to improve fps", "make games run faster",
        "boost pc performance", "how to make computer faster",
        "my pc is slow", "improve computer speed",
        "get more fps", "how do i speed up my pc",
    ],

    # ── Small talk / open conversation -> goes to Ollama ──────────────────────
    "small_talk": [
        # greeting-style small talk (higher score so rule fallback works)
        "jak się masz", "co słychać", "co u ciebie", "jak leci",
        "co tam stary", "co tam", "jak tam", "jak tam u ciebie", "co porabiasz",
        
        "jakie masz rady", "co mi radzisz", "co dziś polecasz",
        "how are you", "what's up", 
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
        # guidance & context variants (round 2)
        "czemu komputer tak wolno działa",
        "dlaczego wszystko tak długo trwa",
        "why does my pc take forever",
        "why is everything taking so long",

        # colloquial variants (2026-07-16 pass)
        "komp muli",
        "laptop zamula",
        "komputer zamula",
        "wszystko zamula",
        "komputer laguje",
        "pc laguje",
        "wszystko się tnie",
        "komp się przycina",
        "strasznie muli",
        "czemu tak zamula",
        "komputer strasznie wolny",
        "komp zwalnia",
        "wszystko wolno chodzi",
        "my pc is lagging",
        "computer keeps lagging",
        "everything is slow",
        "pc feels sluggish",
        "why is everything so laggy",
        "my pc is crawling",
        "computer is so laggy",

        # natural phrasings - routing audit 2026-07-02
        "laptop się zacina",
        "czemu mój laptop się zacina",
        "laptop sie zacina",
        "komputer wolno chodzi",
        "czemu mój komputer wolno chodzi",
        "wolno chodzi",
        "laptop wolno chodzi",
        "komputer muli",
        "muli mi komputer",
        "czemu tak wolno",
        "laptop is stuttering",
        "my laptop stutters",
        "pc runs slow",
        # Natural phrasings - routing audit 2026-06
        "dlaczego komputer chodzi wolno", "komputer chodzi wolno", "chodzi wolno",
        "dlaczego wolno", "dlaczego tak wolno", "czemu komputer chodzi wolno",
        "dlaczego komputer jest wolny", 
        # Polish - ASCII variants (key: "dlaczego wolno chodzi" vs "wolny komputer")
        "dlaczego komputer tak wolno chodzi", "dlaczego tak wolno chodzi",
        "dlaczego pc wolno chodzi", "co sprawia ze chodzi wolno",
        # Polish
        "dlaczego laguje", "dlaczego komputer wolno działa",
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
        # colloquial variants (2026-07-16 pass)
        "ram na maksa",
        "pamięć się kończy",
        "brakuje pamięci",
        "brakuje ramu",
        "mało ramu",
        "ram is full",
        "out of memory",
        "running out of ram",
        "memory maxed out",

        # Polish
        "dlaczego ram jest wysoki", "dlaczego ram jest pełny",
        "dlaczego ram jest na 90", "dlaczego ram jest zajęty",
        "co zre mi tyle ramu", "co zre mi ram", "co zre ram",
        "co zajmuje ram", "co zużywa ram", "co żre ram", "co zera ram",
        "co zera mi ram", "co pożera ram", "ram jest pełny dlaczego",
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
        "ile mam wolnego miejsca", "ile miejsca na dysku",
        "ile wolnego na dysku", "ile gb wolne",
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
        # colloquial variants (2026-07-16 pass)
        "za dużo programów na starcie",
        "co się włącza przy starcie",
        "what launches at boot",

        # natural phrasings - routing audit 2026-07-02
        "czy coś mam niepotrzebnego w startupie",
        "niepotrzebne w autostarcie",
        "co niepotrzebnego włącza się z windowsem",
        "włącza się z windowsem",
        "co startuje niepotrzebnie",
        "zbędne programy na starcie",
        "niepotrzebne programy na starcie",
        "useless startup programs",
        "unnecessary startup programs",
        "junk in my startup",
        # Polish
        "czy mam za dużo programów startowych", "ile mam programów startowych",
        "co odpala się przy starcie", "co uruchamia się przy starcie",
        "jakie programy startują automatycznie", "co się włącza przy logowaniu",
        "za dużo autostart", "autostart sprawdź", "co jest w autostarcie",
        "czy mój autostart jest ok", "sprawdź autostart", "autostart",
        "ile rzeczy odpala się z windows", "za dużo na starcie",
        "co się odpala z windowsem", "co odpala się z windowsem",
        "co uruchamia się z windowsem", "co startuje z windowsem",
        "co się uruchamia z windows", "jakie mam aplikacje autostartu",
        "aplikacje autostartu", "moje programy startowe", "lista autostartu",
        # English
        "too many startup programs", "check startup apps", "startup programs list",
        "what starts with windows", "startup check", "what launches on boot",
        "how many startup programs", "startup manager", "autostart check",
        "what runs at startup", "startup bloat",
    ],

    # ── High disk usage diagnosis ─────────────────────────────────────────────
    "disk_usage_why": [
        # colloquial variants (2026-07-16 pass)
        "dysk pełny",
        "brak miejsca na dysku",
        "kończy się miejsce na dysku",
        "disk is full",
        "no space left on disk",

        # Natural phrasings - routing audit 2026-06
        "co zapisuje na dysk", "co najbardziej zapisuje", "co pisze na dysk",
        "co zapisuje dysk", "co najbardziej zapisuje na dysk",
        "dlaczego dysk zajęty", "dysk cały czas zajęty",
        "dlaczego dysk jest cały czas zajęty", "czemu dysk pracuje",
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
        # colloquial variants (2026-07-16 pass)
        "bateria szybko pada",
        "bateria szybko się rozładowuje",
        "battery dies fast",
        "battery drains too quickly",

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
        # Natural phrasings - routing audit 2026-06
        "co się zmieniło w wydajności", "zmieniło w wydajności",
        "co się zmieniło w wydajności w tym tygodniu", "zmiana wydajności w tygodniu",
        "wydajność w tym tygodniu", "co zmieniło się w wydajności",
        "chodzi gorzej niż zwykle", "gorzej niż zwykle", "czy chodzi gorzej",
        "wolniej niż zwykle", "gorzej niż normalnie", "czy komputer chodzi gorzej",
        "czy działa gorzej", "czy komputer chodzi gorzej niż zwykle",
        # Polish
        "co się zmieniło od ostatniego uruchomienia",
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
        # Polish - roast / meme queries
        "zrób roast mojego pc", "zrob roast mojego pc",
        "zrób roast", "roast mój pc", "roast mojego komputera",
        "skrytykuj mój sprzęt", "zrób sobie jaja z mojego pc",
        "powiedz że mój pc jest słaby", "wyśmiej mój komputer",
        # Polish - meme questions
        "dlaczego mój komputer mnie nienawidzi", "komputer mnie nienawidzi",
        "czy mój pc jest głupi", "pc jest głupi", "komputer jest głupi",
        "czy moj pc spiewa w nocy", "co robi pc jak spie",
        "ile kalorii spala procesor", "ile kalorii spala cpu",
        "czy moge nakarmić pc zeby dzialal szybciej",
        "dlaczego komputer oddycha tak ciezko", "komputer oddycha",
        "czy pc teskni za mna gdy ide spac", "czy pc jest smutny",
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
        # English - meme questions
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
        # Frustration expressions (route to fun_roast for empathetic response)
        "ten komputer jest do niczego", "ten pc jest do niczego",
        "komputer jest beznadziejny", "ten sprzet to dramat",
        "pc nie dziala jak powinien", "komputer mnie wkurwia",
        "nienawidze tego komputera", "ten komputer to kupa",
        "my pc is useless", "this pc is garbage",
        "this computer is terrible", "i hate this pc",
        "my pc is so slow it hurts", "this machine is a disaster",
    ],

    # ── Startup safety - can I disable X from startup? ───────────────────────
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
        # Natural phrasings - routing audit 2026-06
        "co się zmieniło od wczoraj", "co się zmieniło w moim pc od wczoraj",
        "zmieniło w moim pc od wczoraj", "co nowego od wczoraj", "co się zmieniło w pc",
        # Polish
        "co nowego na pc",
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
        # natural phrasings - routing audit 2026-07-02
        "czy mój komputer jest bezpieczny",
        "czy komputer jest bezpieczny",
        "czy jestem bezpieczny",
        "czy mój pc jest bezpieczny",
        "is my computer safe",
        "is my pc secure",
        "am i safe",
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
        # Natural phrasings - routing audit 2026-06
        "ram bardziej zajęty", "bardziej zajęty niż", "ram bardziej zajęty niż zwykle",
        "czy ram jest bardziej zajęty niż w zeszłym tygodniu", "więcej ramu niż zwykle",
        "ram vs zeszły tydzień", "ram więcej niż wcześniej",
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
        "virtual memory usage", 
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

    # ── Voltage / VCore / power delivery ─────────────────────────────────────
    "voltage_check": [
        # Polish tokens
        "napięcie", "vcore", "voltage", "volt",
        # Polish multi-word
        "napięcie cpu", "napięcie procesora", "jakie jest napięcie",
        "ile ma vcore", "czy vcore jest ok", "czy napięcie jest normalne",
        "napięcie rdzenia", "napięcie gpu", "napięcie ram",
        "vcore jest za wysokie", "vcore skacze", "napięcie skacze",
        "czy moje napięcie jest bezpieczne", "jakie napięcie ma cpu",
        "pokaż napięcie", "vcore teraz", "napięcie ddr",
        # English tokens
        "vcpu", "vddr",
        # English multi-word
        "what is my cpu voltage", "what's my vcore", "show voltage",
        "is my vcore normal", "is my voltage safe", "cpu voltage check",
        "voltage too high", "vcore spiking", "check voltages",
        "gpu voltage", "ddr voltage", "memory voltage",
        "what voltage is my cpu running at", "is vcore safe",
        "my voltage is high", "voltage spike", "power delivery",
    ],

    # ── Fan speed / cooling health ────────────────────────────────────────────
    "fan_speed": [
        # Polish tokens
        "wentylator", "wentylatora", "wiatrak", "rpm", "chłodzenie",
        # Polish multi-word
        "prędkość wentylatora", "ile obrotów wentylator", "wentylator rpm",
        "czy chłodzenie działa", "czy wentylator działa",
        "wentylator na 100", "wentylator głośny", "dlaczego wentylator głośny",
        "dlaczego pc hałasuje", "dlaczego komputer hałasuje",
        "chłodzenie procesora", "wentylator cpu", "wentylator gpu",
        "obroty wentylatora", "fan speed", "sprawdź wentylatora",
        "wentylator się nie kręci", "chłodzenie nie działa",
        "ile obrotów ma mój wentylator", "obróty chłodzenia",
        # English tokens
        "fans", "cooler", "cooling",
        # English multi-word
        "what is my fan speed", "fan rpm check", "how fast are my fans",
        "is my cooling working", "why is my fan loud", "fan noise",
        "cpu fan speed", "gpu fan speed", "case fans",
        "why is pc so loud", "fans at 100 percent",
        "is my cpu cooler working", "check fan speed", "fan rpm",
        "cooling system check", "cpu cooler rpm", "are fans spinning",
        "why is computer so noisy", "fan running loud",
    ],

    # ── Gaming session / FPS context ─────────────────────────────────────────
    "gaming_session": [
        # Polish tokens
        "gra", "granie", "gaming", "fps", "klatki",
        # Polish multi-word
        "jak było podczas grania", "podczas grania cpu",
        "jak się trzymał komputer podczas grania",
        "jak grało się na tym pc", "sesja gamingowa",
        "czy pc wytrzyma granie", "czy mogę grać",
        "jak radzi sobie pc podczas gry", "jak wyglądała sesja gry",
        "podsumowanie sesji gry", "co się działo podczas gry",
        "komputer grzał podczas gry", "fps drops dlaczego",
        "dlaczego fps spada", "dlaczego gra się zacina",
        "jak poprawić fps", "więcej fps jak",
        "optymalizacja pod gry", "ustawienia pod gry",
        "czy mój pc radzi sobie z grami", "jak wydajność w grach",
        "jak mój komputer radzi sobie z grami",
        # English multi-word
        "gaming session summary", "how was my gaming session",
        "fps drops why", "why fps drops", "game session stats",
        "how did pc handle gaming", "gaming performance",
        "optimize for gaming", "is my pc good for gaming",
        "fps drop fix", "stutter during gaming", "game lags",
        "why does game lag", "game performance check",
        "how many fps can i get", "gaming optimization",
        "my pc during gaming", "pc gaming stats",
    ],

    # ── Weekly trends / historical performance ────────────────────────────────
    "weekly_trends": [
        # Polish tokens
        "tydzień", "tygodniu", "tygodnia", "tygodniowe",
        # Polish multi-word
        "jak był ten tydzień", "podsumowanie tygodnia",
        "jak wyglądał tydzień", "co się działo w tym tygodniu",
        "czy ten tydzień był gorszy", "trend tygodniowy",
        "jak wyglądał mój pc przez tydzień",
        "wydajność przez tydzień", "tydzień vs tydzień",
        "porównaj tygodnie", "czy w tym tygodniu jest gorzej",
        "jak wypadł ten tydzień", "poprzedni tydzień vs teraz",
        "przez ostatni tydzień co się działo",
        "tygodniowe podsumowanie wydajności",
        "jak tydzień wyglądał pod względem wydajności",
        # English multi-word
        "weekly summary", "this week performance",
        "how was this week", "weekly trends",
        "week performance review", "compare weeks",
        "week over week", "how did pc perform this week",
        "weekly performance report", "what happened this week",
        "weekly stats", "performance over the week",
        "this week vs last week", "weekly average",
        "performance trend this week", "cpu trend weekly",
    ],

    # ── Thermal prediction / overheat risk ────────────────────────────────────
    "thermal_prediction": [
        # deep-param / learning phrasings (2026-07-05)
        "jakie temperatury są dla mnie normalne",
        "moja normalna temperatura",
        "czego się spodziewać po temperaturach",
        "jaka temperatura jest u mnie ok",
        "what temps are normal for me",
        "my normal temperature range",
        "what temperature should i expect",
        # Polish multi-word
        "czy się przegrzeje", "czy jest ryzyko przegrzania",
        "czy mój komputer się przegrzeje", "czy mogę grać bez ryzyka przegrzania",
        "czy temperatura jest bezpieczna do gry", "czy thermal throttle grozi",
        "czy będzie throttlować", "ryzyko przegrzania",
        "czy chłodzenie wystarczy", "czy wytrzyma obciążenie",
        "czy mogę uruchomić to bez przegrzania",
        "temperatura jest bliska limitu", "czy temp jest bezpieczna",
        "czy mój cooler wystarczy do gry", "jak długo mogę grać bez przegrzania",
        "czy mam ryzyko termiczne",
        # English multi-word
        "will my pc overheat", "is there overheat risk",
        "will it thermal throttle", "is it safe to game with these temps",
        "can my cooling handle this", "thermal throttle risk",
        "will cpu overheat during gaming", "is my cooling enough",
        "overheat risk check", "can i game without overheating",
        "is temperature safe for gaming", "will it throttle",
        "thermal safety check", "how long before overheat",
        "is my cooler sufficient", "safe to run heavy workload",
        "temps are near limit is it ok",
    ],

    # ── Process deep-dive / why so heavy ─────────────────────────────────────
    "process_deep_dive": [
        # Polish multi-word
        "dlaczego chrome tyle ram", "dlaczego discord tyle ram",
        "dlaczego x używa tyle ram", "dlaczego x tyle zajmuje",
        "dlaczego ten program tyle żre", "co powoduje że x tyle używa",
        "dlaczego ten proces jest taki ciężki", "czy to normalne że x tyle ram",
        "co robił ten program tak intensywnie", "dlaczego svchost tyle cpu",
        "dlaczego x zużywa tyle cpu", "co robi ten program przez cały czas",
        "czy mogę ograniczyć x w tle", "x tyle zjada dlaczego",
        "dlaczego x jest tak ciężki", "co robi x żeby tyle zajmować",
        "czy x powinien tyle zajmować", "normalnie x tyle zajmuje",
        # English multi-word
        "why is chrome using 2gb", "why does discord use so much ram",
        "why is x using so much memory", "why does x take so much cpu",
        "is it normal for x to use that much", "why is this process so heavy",
        "what is svchost doing using 15 percent", "why is x so resource hungry",
        "can i limit x background usage", "why does x run all the time",
        "why x uses so much", "what is x doing to use so much cpu",
        "is it normal for x to use that much ram", "x memory usage high why",
        "x cpu usage high why", "deep dive into process",
        "why does x take so many resources", "x is really heavy why",
    ],
    # ── PC froze / stutter symptom ───────────────────────────────────────────
    "symptom_freeze": [
        # Polish
        "zamroziło się", "pc się zamroziło", "komputer się zawiesił",
        "komputer się zawiesza", "komputer sie zawiesza", "pc się zawiesza",
        "zawiesza się", "zawiesza mi się", "system się zawiesza",
        "zawieszenie systemu", "ekran stanął", "all froze", "screen froze",
        "na chwilę się zawiesiło", "przez chwilę nic nie reagowało",
        "pc nie reaguje", "zawiesiło na sekundę", "zawiesiło na chwilę",
        "zacięcie na sekundę", "pc stanął na chwilę",
        "błąd zamrożenia", "system się zawiesił raz", "komputer stanął",
        "na chwilę zamroziło", "kliknąłem i nic", "kursor się zatrzymał",
        "myszka się zacięła na chwilę", "pc krótko się zawiesił",
        # English
        "pc froze for a second", "everything froze", "system froze",
        "computer froze briefly", "screen froze for a moment",
        "pc became unresponsive", "it froze for a second",
        "nothing responded for a moment", "pc locked up",
        "brief freeze", "micro freeze", "stutter then freeze",
        "mouse stopped for a second", "freeze spike",
        "app froze", "game froze", "windows froze",
    ],

    # ── Loud fan / noisy PC ───────────────────────────────────────────────────
    "symptom_noisy": [
        # colloquial variants (2026-07-16 pass)
        "wentylatory szaleją",
        "głośno wieje z komputera",
        "fans going crazy",
        "pc sounds like a jet",

        # Polish
        "komputer hałasuje", "pc hałasuje", "głośny wentylator",
        "głośny komputer", "glosny komputer", "głośny pc",
        "wentylator jest głośny", "coś głośno hałasuje w pc",
        "komputer jest głośny", "pc jest głośny", "dudni komputer",
        "pc ryczy", "wentylator rzyczy", "coś głośno pracuje",
        "od czego hałasuje pc", "co powoduje hałas", "skąd ten hałas",
        "dlaczego komputer jest taki głośny", "hałas przy obciążeniu",
        "głośny pod obciążeniem", "wentylator przy starcie głośny",
        # English
        "pc is loud", "noisy pc", "loud fan", "fans are loud",
        "computer is very noisy", "what is making that noise",
        "why is pc so loud", "why is my computer noisy",
        "noisy under load", "fan running at full speed loud",
        "pc sounds like a jet engine", "loud when gaming",
        "loud at startup", "fan noise fix",
    ],

    # ── Is this normal? Baseline comparison ──────────────────────────────────
    "compare_baseline": [
        # deep-param / learning phrasings (2026-07-05)
        "czy to normalne dla mnie",
        "czy to moja norma",
        "jak wypadam względem normy",
        "czy odbiegam od normy",
        "czy jestem w normie",
        "is this normal for me",
        "am i within my normal",
        "how do i compare to my baseline",
        "is this my normal",
        # Polish
        "czy to normalne", "czy tak powinno być",
        "czy to wysoki wynik", "czy tak jest normalnie",
        "czy cpu na 70 to normalne", "czy ram na 80 to normalne",
        "czy to w normie", "czy to za dużo", "czy to za wysoko",
        "czy powinienem się martwić", "czy to niepokojące",
        "czy taka temperatura jest ok", "czy takie obciążenie jest ok",
        "czy to jest dobre czy złe", "norma czy nie",
        "czy to jest powyżej normy", "co jest normalne dla mojego pc",
        # English
        "is this normal", "is this expected", "is that too high",
        "is cpu at 70 normal", "is ram at 80 normal",
        "should i be worried", "is this a problem",
        "normal or not", "is this reading ok",
        "is that temperature okay", "is that usage okay",
        "is this within normal range", "good or bad reading",
        "is that value dangerous", "should this be lower",
        "what is normal for my pc", "is cpu load normal",
    ],

    # ── Game-ready check ─────────────────────────────────────────────────────
    "game_ready": [
        # Natural phrasings - routing audit 2026-06
        "gotowy do grania", "gotowy do gry", "czy gotowy do grania",
        "pc gotowy do grania", "czy pc gotowy do grania", "gotowy na granie",
        "czy mogę teraz grać", "czy mogę grać teraz", "czy pc jest gotowy do grania teraz",
        # Polish
        "czy mogę grać", "czy pc jest gotowy do gry",
        "czy mój komputer wytrzyma grę", "czy jest ok do grania",
        "czy powinienem zamknąć coś przed grą",
        "co zamknąć przed grą", "przygotuj pc pod gry",
        "czy warto coś wyłączyć przed graniem",
        "co wyłączyć przed grą", "przygotowanie do grania",
        "czy system jest gotowy", "optymalizuj pod grę",
        "jak przygotować pc do grania", "czy turbo przed grą",
        "szybki test przed grą", "sprawdź przed grą",
        "co zrobić przed grą", "zanim zacznę grać",
        # English
        "am i ready to game", "is my pc ready for gaming",
        "should i close anything before gaming",
        "what to close before gaming", "prepare pc for gaming",
        "optimize before game", "is it ok to start gaming now",
        "pre-game check", "pre-gaming optimization",
        "should i use turbo before gaming",
        "what should i turn off before gaming",
        "gaming prep", "get ready to game",
        "is pc in good state for gaming",
    ],

    # ── Morning brief / first-launch context ─────────────────────────────────
    "morning_brief": [
        # Polish + EN direct phrases
        "morning brief", "poranny brief", "dobry ranek pc",
        "co nowego od kiedy sie obudzilem", "co sie dzialo od rana",
        "co sie stalo kiedy spalem", "co sie dzialo bez mnie",
        "co nowego na pc od rana", "od kiedy sie obudzilem co sie stalo",
        "co sie działo przez noc", "podsumowanie nocy",
        "co się działo gdy byłem nieobecny", "raport poranny",
        "co nowego od uruchomienia", "co się zdarzyło od startu",
        "co się działo gdy spałem", "podsumowanie od uruchomienia",
        "jak szło przez noc", "raport z nocy",
        "co wybrało się dzisiaj", "co dzisiaj na start",
        "witaj nowy dzień pc", "poranny stan systemu",
        # English
        "what happened overnight", "morning briefing",
        "morning pc summary", "what happened while i was away",
        "overnight report", "what went on while i was asleep",
        "system report since boot", "since boot summary",
        "morning status", "good morning pc status",
        "what has happened today", "today so far summary",
        "system digest", "daily brief",
    ],

    # ── Session digest / end-of-day summary ──────────────────────────────────
    "session_digest": [
        # Polish - with and without diacritics
        "podsumuj dzisiejsza sesje", "podsumuj ta sesje",
        "podsumowanie tej sesji", "co sie dzisiaj dzialo",
        "podsumuj dzisiaj", "podsumowanie sesji", "co dziś się działo",
        "jak wyglądał dzień na pc", "dzisiejsze podsumowanie",
        "co się działo dzisiaj na pc", "sesja podsumowanie",
        "co pc robił dzisiaj", "raport z sesji",
        "jak minął dzień komputerowy", "pokaż co się działo",
        "co się wydarzyło podczas tej sesji",
        "jak wyglądała ta sesja", "zakończenie sesji",
        # English
        "summarize today", "session summary",
        "what happened today on my pc", "today's pc report",
        "how was today on my pc", "daily summary",
        "end of day report", "session digest",
        "what did my pc do today", "wrap up today",
        "what happened this session", "today's activity",
        "session report", "pc activity report",
    ],

    # ── Force close / kill process ────────────────────────────────────────────
    "process_kill": [
        # Polish
        "zabij proces", "zamknij na siłę", "wymuś zamknięcie",
        "zabij chrome", "zabij discorda", "zabij steam",
        "zamknij chrome na siłę", "wymuś zamknięcie procesu",
        "zakończ zadanie", "kill process", "end task",
        "force close", "force quit", "zakończ",
        "zamknij program który nie reaguje",
        "nie można zamknąć programu", "program się nie zamyka",
        "jak zamknąć zawieszony program",
        "jak zakończyć zablokowany program",
        # English
        "kill chrome", "force close chrome",
        "force quit discord", "end task for x",
        "how to force close a program", "program won't close",
        "kill unresponsive app", "force kill process",
        "terminate program", "how to end task",
        "close frozen program", "force close frozen app",
        "how to kill background process",
        "end process force", "force terminate",
    ],

    # ── Temperature history ───────────────────────────────────────────────────
    "thermal_history": [
        # Polish
        "historia temperatur", "jak wyglądały temperatury",
        "jakie były temperatury dzisiaj", "temperatura przez sesję",
        "historyczne temperatury", "czy temperatura rosła",
        "jak rosła temperatura", "temperatura w czasie",
        "trendy temperatur", "temperatura podczas grania wcześniej",
        "jak zmieniała się temperatura", "temperatura log",
        "czy były skoki temperatury", "peaki temperatur",
        "maksymalna temperatura dzisiaj",
        # English
        "show temperature history", "temperature over time",
        "how did temperatures look", "temp history",
        "did temperature spike today", "temperature trend",
        "historical temps", "thermal log", "temp over session",
        "max temperature today", "peak temperature",
        "temperature changes over time", "how hot did it get",
        "thermal history", "temp spikes today",
    ],

    # ── Free up RAM ───────────────────────────────────────────────────────────
    "ram_flush": [
        # Polish
        "zwolnij ram", "wyczyść ram", "odśwież pamięć",
        "zrób ram flush", "ram flush", "wyczyść pamięć",
        "jak zwolnić pamięć", "jak zrobić ram flush",
        "odczaruj ram", "posprzątaj ram", "usuń z pamięci",
        "zrestartuj pamięć", "możesz zwolnić ram",
        "jak zmniejszyć zajętość ramu", "optymalizuj ram",
        "uwolnij pamięć",
        # English
        "free up ram", "flush ram", "clear memory",
        "clear ram", "free memory",
        "how to free up ram", "empty standby list",
        "memory flush", "release memory",
        "how to clear ram", "optimize memory",
        "reduce ram usage", "free system memory",
        "reclaim ram", "clear cached memory",
    ],

    # ── Overclock / OC check ──────────────────────────────────────────────────
    "overclock_check": [
        # Polish
        "czy jest overclockowany", "czy cpu jest oc",
        "czy procesor jest podkręcony", "czy gpu jest oc",
        "ile wynosi podkręcenie", "oc status",
        "czy mam podkręcony procesor", "czy mam oc",
        "czy jest podkręcony sprzęt", "oc check",
        "czy powinienem podkręcić", "czy warto podkręcić cpu",
        "jak bezpiecznie podkręcić", "czy mogę podkręcić",
        "podkręcenie bezpieczne", "taktowanie powyżej normy",
        "czy moj cpu jest podkrecony", "czy jest podkrecony",
        "podkrecony procesor", "oc procesora",
        "czy mam podkrecony cpu", "czy jest oc na cpu",
        # English
        "is my cpu overclocked", "is it overclocked",
        "overclock status", "is gpu overclocked",
        "am i running overclocked", "oc detection",
        "should i overclock", "is overclocking safe",
        "how to overclock safely", "can i overclock",
        "running above base clock", "boost clock vs oc",
        "is my cpu running at stock speeds",
        "overclocking check", "xmp enabled",
    ],

    # ── What does AI know about my PC ────────────────────────────────────────
    "ai_context": [
        "co już wiesz o moim komputerze",
        "co wiesz o moim komputerze",
        "co wiesz o moim kompie",
        # deep-param / learning phrasings (2026-07-05)
        "ile się nauczyłeś",
        "ile juz sie nauczyles",
        "jak długo się uczysz",
        "od kiedy się uczysz",
        "postęp uczenia",
        "ile już wiesz o moim pc",
        "jak idzie uczenie",
        "ile godzin obserwujesz",
        "how long have you been learning",
        "learning progress",
        "how much have you learned",
        "how far along is the learning",
        "how many hours observed",
        # Polish
        "co wiesz o moim pc", "co o mnie wiesz",
        "co zapamiętałeś", "co masz w pamięci o moim sprzęcie",
        "jakie dane zebrałeś", "jakie informacje masz",
        "co zebrałeś o moim komputerze", "co ci wiadomo",
        "powiedz co wiesz o mnie", "jakie masz dane o moim pc",
        "co widzisz o moim sprzęcie", "pokaż co wiesz",
        "jaka jest twoja wiedza o moim pc",
        # English
        "what do you know about my pc", "what have you learned",
        "what do you remember about my system",
        "show me what you know", "what data have you collected",
        "what information do you have about my pc",
        "what have you observed about my hardware",
        "tell me what you know", "ai context dump",
        "what's in your memory about my pc",
        "summarize what you know about my system",
    ],

    # ── Fan noise history - is fan louder than usual? ────────────────────────
    "fan_noise_history": [
        # Natural phrasings - routing audit 2026-06 (plural / "głośno chodzą")
        "wentylatory głośno", "głośno chodzą", "wentylatory tak głośno chodzą",
        "dlaczego wentylatory tak głośno chodzą", "dlaczego wentylatory głośno chodzą",
        "wentylatory hałasują", "głośne wentylatory", "wentylatory chodzą głośno",
        # Polish
        "czy wentylator jest głośniejszy niż zwykle",
        "wentylator jest głośniejszy", "wentylator głośniej",
        "dlaczego wentylator tak hałasuje", "wentylator hałasuje bardziej",
        "czy fan jest głośniejszy", "wentylator głośny teraz",
        "fan głośniejszy niż wcześniej", "czy komputer jest głośniejszy",
        "dlaczego komputer tak huczy", "głośny wentylator",
        "wentylator warczy", "komputer huczy bardziej",
        "czy to normalne że wentylator tak hałasuje",
        "wentylator chodzi za mocno", "za głośny wentylator",
        "wentylator szumi bardziej niż zwykle",
        # English
        "is my fan louder than usual", "fan is louder than normal",
        "why is my fan so loud", "fan louder than before",
        "is the fan spinning faster", "fan making more noise",
        "computer is louder than usual", "fan noise increased",
        "why is my computer so loud", "loud fan right now",
        "fan ramping up", "fan is noisy", "louder fan than before",
        "is fan noise normal", "fan spinning hard",
        "why does my pc sound like a jet engine",
    ],

    # ── Driver status - installed drivers and update dates ───────────────────
    "driver_status": [
        # natural phrasings - routing audit 2026-07-02
        "czy moje sterowniki wymagają aktualizacji",
        "sterowniki wymagają aktualizacji",
        "czy sterowniki są aktualne",
        "stare sterowniki",
        "czy mam stare sterowniki",
        "czy mam niepotrzebne sterowniki",
        "niepotrzebne sterowniki",
        "zbędne sterowniki",
        "duchy sterowników",
        "ghost drivers",
        "are my drivers outdated",
        "do my drivers need updating",
        "unnecessary drivers",
        # Polish
        "zainstalowane sterowniki", "lista zainstalowanych sterownikow",
        "jakie sterowniki mam zainstalowane", "sterowniki na komputerze",
        "jakie mam sterowniki", "kiedy były aktualizowane sterowniki",
        "kiedy ostatnio sterowniki byly aktualizowane",
        "kiedy zaktualizowane sterowniki", "ostatnia aktualizacja sterownikow",
        "jakie sterowniki są zainstalowane", "lista sterowników",
        "sprawdź sterowniki",
        "sterowniki graficzne", "sterowniki gpu", "sterowniki nvidia",
        "sterowniki amd", "sterowniki intel", "status sterowników",
        "kiedy ostatnio zaktualizowałem sterowniki",
        "czy moje sterowniki są przestarzałe",
        "czy sterownik karty graficznej jest aktualny",
        "jak stare są moje sterowniki", "data sterownika",
        # English
        "what drivers do i have installed", "when were drivers last updated",
        "check my drivers", "driver status", "list my drivers",
        "are my drivers up to date", "gpu driver version",
        "nvidia driver version", "amd driver version",
        "intel driver version", "driver check",
        "when was my graphics driver last updated",
        "driver update date",
        "how old are my drivers", "driver info",
        "which drivers are installed",
    ],

    # ── Gaming vs work time breakdown ────────────────────────────────────────
    "gaming_vs_work_time": [
        # Polish
        "ile czasu spędzam na grach a ile na pracy",
        "ile czasu na grach", "ile gram w gry",
        "ile czasu na pracy przy komputerze",
        "gry vs praca czas", "gry vs robota",
        "ile procent czasu gram", "jaki procent to gry",
        "jak spędzam czas na komputerze",
        "podział czasu na pc", "analiza czasu na pc",
        "ile czasu w grach vs aplikacje",
        "ile grałem w tym tygodniu", "statystyki czasu gier",
        # English
        "how much time do i spend gaming vs working",
        "gaming vs work time", "how much time gaming",
        "time spent on games", "gaming vs productivity",
        "how much do i game", "work vs play breakdown",
        "gaming time stats", "time analysis on pc",
        "how much time on games vs apps",
        "gaming hours this week", "time breakdown pc",
    ],

    # ── Process identity - is this exe Windows or suspicious? ────────────────
    "process_identity": [
        # Polish
        "czy ten plik exe jest częścią windows",
        "czy ten proces jest częścią windows",
        "czy to jest wirus czy windows",
        "co to jest za plik exe", "co to jest za proces",
        "czy to bezpieczny proces", "czy ten proces jest podejrzany",
        "czy to windows czy wirus", "co robi ten plik",
        "co to jest conhost exe", "co to jest werfault",
        "co to jest msiexec", "co to jest taskhostw",
        "skąd ten plik", "czy to złośliwe oprogramowanie",
        "sprawdź ten plik", "czy mam to wyłączyć",
        # English
        "is this exe part of windows", "is this process windows or virus",
        "what is this exe file", "what does this process do",
        "is this a windows process", "is this process safe",
        "is this process suspicious", "what is this file",
        "is this malware", "check this process",
        "should i be worried about this process",
        "is it safe to kill this process", "is this file legitimate",
        "what is conhost exe", "what is werfault",
        "is msiexec safe", "what is taskhostw",
    ],

    # ── Stale / unused applications ──────────────────────────────────────────
    "stale_apps": [
        # Polish
        "które aplikacje nie były otwierane od miesiąca",
        "nieużywane aplikacje", "stare aplikacje na pc",
        "które programy nie były uruchamiane",
        "co nie jest otwierane od dawna",
        "aplikacje których nie używam",
        "które programy mogę odinstalować",
        "co od dawna nie uruchomione",
        "nieaktywne programy", "nieużywane programy",
        "które apki są zbędne", "zapomniane programy",
        "co odinstalować żeby zwolnić miejsce",
        # English
        "which apps have not been opened in a month",
        "unused applications", "stale apps on my pc",
        "apps i never use", "programs i haven't opened",
        "which programs can i uninstall", "unused programs",
        "inactive applications", "forgotten software",
        "what apps to uninstall", "apps taking up space",
        "programs not opened recently",
        "clean up unused software",
    ],

    # ── FPS degradation - time-travel debugging ──────────────────────────────
    "fps_degradation": [
        # Polish
        "dlaczego moje fps są gorsze niż miesiąc temu",
        "fps gorsze niż kiedyś", "fps spadły z czasem",
        "kiedyś miałem lepsze fps", "fps są coraz gorsze",
        "dlaczego gra chodzi gorzej niż wcześniej",
        "fps gorsze niż były", "wydajność w grach spadła",
        "gra działała lepiej wcześniej", "fps degradacja",
        "klatki gorsze niż poprzednio", "tracę fps z czasem",
        "wydajność w grach coraz niższa",
        # English
        "why is my fps worse than last month",
        "fps worse than before", "fps has dropped over time",
        "used to have better fps", "fps getting worse",
        "gaming performance dropped", "fps degradation",
        "game runs worse than it used to",
        "fps lower than they were", "performance decreased in games",
        "frames per second dropped", "why are frames lower now",
        "game feels slower than before",
    ],

    # ── App behavior change - why did X start behaving differently? ──────────
    "app_behavior_change": [
        # Polish
        "dlaczego aplikacja zaczęła się zachowywać inaczej",
        "aplikacja działa inaczej niż wcześniej",
        "program zachowuje się dziwnie od jakiegoś czasu",
        "coś się zmieniło w działaniu programu",
        "program laguje od niedawna", "aplikacja spowalnia od tygodnia",
        "dlaczego program X działa inaczej",
        "coś się zmieniło po ostatniej aktualizacji",
        "program działa gorzej od jakiegoś czasu",
        "co się zmieniło że program działa wolniej",
        # English
        "why did my app start behaving differently",
        "app is acting differently than before",
        "program started behaving strangely",
        "something changed with how this app works",
        "app is slow since last week",
        "why is this program different now",
        "app changed behavior after update",
        "program works worse since recently",
        "something changed and now my app is slow",
        "why is this app suddenly different",
    ],

    # ── Startup slowdown - what slows boot the most ──────────────────────────
    "startup_slowdown": [
        # Natural phrasings - routing audit 2026-06
        "co spowalnia start", "spowalnia start windowsa", "co spowalnia uruchamianie",
        "spowalnia uruchamianie", "co najbardziej spowalnia start",
        "wolny start windowsa", "spowalnia start", "co spowalnia start windowsa",
        "co najbardziej spowalnia start windowsa", 
        # Polish
        "co najbardziej zwalnia komputer podczas uruchamiania",
        "co spowalnia boot", "co hamuje uruchamianie",
        "dlaczego komputer wolno się uruchamia",
        "co zwalnia start systemu", "co spowalnia windows",
        "co ładuje się przy starcie i zwalnia",
        "boot jest wolny", "windows ładuje się długo",
        "który program zwalnia boot", "startup jest wolny",
        "co robić żeby szybciej bootować",
        "jak przyspieszyć uruchamianie windows",
        "co zajmuje czas przy uruchamianiu",
        # English
        "what slows down my computer during startup",
        "what slows boot time", "boot is slow",
        "what is slowing down windows startup",
        "what runs at startup and slows my pc",
        "slow boot cause", "why does windows take so long to boot",
        "what is delaying startup", "boot time is too long",
        "what causes slow startup", "fastest boot tips",
        "how to speed up windows startup",
        "what programs are slowing boot",
    ],

    # ── Temperature comparison - hotter than usual lately? ───────────────────
    "temp_comparison": [
        # Polish - ASCII fallback (bez polskich znakow)
        "czy moj pc jest goretszy niz zwykle",
        "czy pc jest goretszy", "goretszy niz zwykle",
        "czy jest cieplejszy niz normalnie", "temperatury sa wyzsze",
        "czy gorecej niz zwykle", "czy jest gorecej niz bylo",
        "czy temperatura wzrosla ostatnio",
        # Polish - accented
        "czy komputer jest ostatnio goręcej niż zwykle",
        "czy temperatury są wyższe niż wcześniej",
        "czy mój pc jest cieplejszy niż był",
        "temperatury wzrosły ostatnio", "czy goręcej niż normalnie",
        "czy cpu jest cieplejsze niż kiedyś",
        "temperatura wyższa niż powinna", "co z temperaturami ostatnio",
        "czy pc przegrzewa się bardziej niż wcześniej",
        "temperatura wzrosła w porównaniu z poprzednim tygodniem",
        "czy jest goręcej niż miesiąc temu",
        # English
        "is my pc hotter than usual lately",
        "are temperatures higher than before",
        "is my cpu running hotter than it used to",
        "temperatures seem higher recently",
        "is it hotter than normal", "temps have increased",
        "running hotter than before", "temperature comparison over time",
        "is my pc warmer than it was last week",
        "has temperature increased compared to before",
        "thermal history comparison",
    ],

    # ── Crash / freeze context - what happened before the crash? ─────────────
    "crash_context": [
        # Polish
        "co się działo na moim pc tuż przed ostatnim freezem",
        "co się działo przed ostatnim crashem",
        "co było uruchomione przed zawieszeniem",
        "co spowodowało ostatni freeze",
        "dlaczego komputer się zawiesił",
        "jaki był stan pc przed crashem",
        "co działało przed freezem systemu",
        "co zrobiłem przed ostatnim zawieszeniem",
        "analiza przed crashem", "kontekst ostatniego freezu",
        "co było aktywne przed zatrzymaniem komputera",
        # English
        "what was happening on my pc before the last freeze",
        "what was running before the crash",
        "what caused the last freeze",
        "what was the pc state before it froze",
        "what was active before the system froze",
        "crash context", "freeze analysis",
        "what happened before my pc crashed",
        "pc state before crash",
        "what processes were running before the freeze",
        "what led to the system freeze",
    ],

    # ── Game hardware stress - which game stresses hardware most ─────────────
    "game_hardware_stress": [
        # Natural phrasings - routing audit 2026-06
        "która gra najbardziej obciąża", "która gra obciąża sprzęt",
        "która gra najbardziej obciąża sprzęt", "która gra najbardziej obciąża mój sprzęt",
        "która gra męczy", "która gra najbardziej męczy", "co najbardziej męczy sprzęt",
        # Polish
        "która gra najbardziej obciąża mój hardware",
        "która gra najbardziej obciąża cpu",
        "która gra najbardziej obciąża gpu",
        "która gra najbardziej grzeje komputer",
        "które gry są najbardziej wymagające",
        "która gra powoduje największe obciążenie",
        "gra vs obciążenie sprzętu",
        "co najbardziej obciąża hardware podczas grania",
        "która gra najbardziej eksploatuje gpu",
        "wydajność gier na moim sprzęcie",
        # English
        "which game stresses my hardware the most",
        "which game pushes cpu the hardest",
        "which game pushes gpu the hardest",
        "most demanding game for my hardware",
        "which game heats up my pc the most",
        "game vs hardware stress", "most hardware intensive game",
        "which game is most demanding on my system",
        "what game stresses hardware most",
        "what game stresses my hardware most",
        "what game stresses my hardware",
        "which game stresses my gpu most",
        "game performance on my hardware",
        "most demanding games for my specs",
    ],

    # ── Battery drain rate - % lost during gaming/work ───────────────────────
    "battery_drain_rate": [
        # Natural phrasings - routing audit 2026-06
        "bateria szybko spada", "szybko spada bateria", "dlaczego bateria spada",
        "czemu bateria spada", "bateria się rozładowuje", "szybko się rozładowuje",
        "dlaczego bateria tak szybko spada", "tak szybko spada",
        # Polish
        "ile procent baterii tracę podczas grania",
        "ile procent baterii tracę podczas pracy",
        "jak szybko rozładowuje się bateria podczas grania",
        "ile bateria traci podczas gry",
        "ile czasu wystarczy bateria podczas grania",
        "bateria szybko spada podczas grania",
        "ile prądu pobiera komputer podczas grania",
        "bateria się szybko rozładowuje",
        # English
        "how much battery do i lose while gaming",
        "battery drain during gaming", "battery drain while working",
        "how fast does battery drain when gaming",
        "how long does battery last gaming",
        "battery drains fast during gaming",
        "how much power does gaming use",
        "battery percentage drop while gaming",
        "battery life during gaming session",
    ],

    # ── Power usage after restart ─────────────────────────────────────────────
    "power_after_restart": [
        # Polish
        "co od ostatniego restartu zużyło największo prądu",
        "co zużyło najwięcej prądu od startu",
        "ile prądu zużył mój komputer od restartu",
        "co pochłonęło prąd od uruchomienia",
        "który program zużył najwięcej energii",
        "co pożarło prąd od startu systemu",
        "analiza zużycia energii od startu",
        # English
        "what used the most power since last restart",
        "power usage since startup",
        "what consumed the most power after boot",
        "energy usage since restart",
        "which program used most power since start",
        "power consumption since system start",
        "what has been using the most power",
    ],

    # ── Can my PC run game X ──────────────────────────────────────────────────
    "game_can_run": [
        # colloquial variants (2026-07-16 pass)
        "czy pociągnie grę",
        "czy uciągnie tę grę",
        "will my pc handle the game",
        "can my pc handle it",

        # Natural phrasings - routing audit 2026-06
        "da radę odpalić", "czy odpali", "czy pójdzie", "karta da radę odpalić",
        "da radę odpalić cyberpunka", "czy moja karta da radę odpalić",
        "czy moja karta da radę odpalić cyberpunka", "czy uruchomię", "pociągnie grę",
        "czy pociągnie", "czy ruszy",
        # Polish - generic game capability (no specific title needed)
        "czy unreal engine 5 ujdzie na moim pc", "czy unreal engine ujdzie",
        "czy gra ujdzie na moim pc", "czy ujdzie na moim komputerze",
        "czy ta gra ujdzie", "czy pc uniesie gre",
        "czy gra zadziala na moim pc", "czy zadziala na moim sprzecie",
        "czy moj pc udwignie gre", "czy komputer dam rade uruchomic gre",
        # Polish - long specific phrases that beat hw_all generic tokens
        "czy ten komputer odpali grę", "czy odpalę tę grę",
        "czy mój komputer uniesie grę",
        "czy mój sprzęt wystarczy na grę", "czy zadziała gra na moim pc",
        "czy komputer nadaje się do gry", "minimalne wymagania sprzętowe",
        "czy zagram w fortnite", "czy zagram w csgo", "czy zagram w cs2",
        "czy zagram w cyberpunk", "czy zagram w minecraft",
        "czy zagram w hogwarts", "czy zagram w gta",
        "czy zagram w valorant", "czy zagram w elden ring",
        "czy zagram w witcher", "czy zadziała cyberpunk",
        "czy komputer odpali cyberpunka", "czy gra pójdzie na ultra",
        "czy gra pójdzie na low", "czy gra pójdzie bez lagów",
        "minimalne wymagania do gry", "sprawdź wymagania gry",
        "czy mój ram wystarczy na cyberpunk", "czy mój gpu wystarczy",
        "czy dysk wystarczy żeby włączyć grę",
        "czy hogwarts zacina bo nie mam ram", "czy ram wystarczy na grę",
        "fortnite bez lagów z muzyką", "czy odpalę fortnite",
        "czy zagram w fortnite bez lagów",
        "wymagania sprzętowe gry", "czy dam radę zagrać",
        "czy sprzęt wystarczy do grania", "czy pc poradzi sobie z grą",
        # Polish ASCII fallback (game-specific to win over hw_all)
        "czy odpale fortnite", "czy odpale cyberpunk",
        "czy odpale cs2", "czy odpale minecraft",
        "czy zagra w fortnite", "czy zagra w cyberpunk",
        "czy zagra w cs2", "czy zagra w hogwarts",
        "czy zagra w valorant", "odpale gre",
        "wymagania gry check", "spelnia wymagania gry",
        "gra pojdzie na moim pc", "gra pojdzie na niskich",
        "gra pojdzie na ultra", "czy spelnia wymagania",
        "czy udzwigne gre", "czy udzwigne cyberpunka",
        "czy udzwigne eldenringa", "czy udzwigne fortnite",
        "czy udzwigne cs2", "czy udzwigne minecraft",
        "czy udzwigne valoranta", "czy udzwigne witchera",
        # English
        "can my pc run the game", "can i run this game",
        "can my computer run fortnite", "can my pc run cs2",
        "can my pc run cyberpunk", "can my pc run hogwarts legacy",
        "can my pc run minecraft", "can my pc run gta 5",
        "can i play fortnite on this pc", "will my pc run this game",
        "is my pc good enough for this game", "can my rig handle the game",
        "minimum requirements check", "does my pc meet game requirements",
        "will cyberpunk run on my pc", "can my pc handle cyberpunk",
        "will fortnite run without lag", "can i run the game on ultra",
        "can i run the game on low settings", "game requirements check",
        "is my gpu good enough for this game", "does my ram meet requirements",
        "will hogwarts legacy run", "will elden ring run on my pc",
        "can i run elden ring", "can i run cyberpunk", "can i run fortnite",
        "can i run cs2", "can i run valorant", "can i run minecraft",
        "can i run gta", "can i run the witcher",
        "enough ram for this game", "is my disk enough for cyberpunk",
        "can this laptop run the game", "does my pc meet minimum specs",
    ],

    # ── How much RAM do I use during gaming ──────────────────────────────────
    "gaming_ram_usage": [
        # Natural phrasings - routing audit 2026-06
        "ram podczas grania", "ile ramu podczas grania", "zużywam podczas grania",
        "ram w grach", "ile ram w grach", "pamięć podczas grania",
        "ile ramu w grach", "ile ramu zazwyczaj zużywam podczas grania",
        # Polish - strong multi-word phrases that beat hw_ram single "ram" token
        "ile ramu zazwyczaj używam podczas grania",
        "ile pamięci używam kiedy gram",
        "ile ramu zajmuje granie", "zużycie ram podczas gier",
        "ile ram kiedy gram w gry", "ram podczas gaming",
        "ile ramu kiedy gram w cs", "ile ramu kiedy gram w fortnite",
        "ile ramu kiedy gram w minecraft", "ile ramu przy grach",
        "typowe zużycie ram podczas grania",
        "ile pamięci gry zajmują średnio",
        "ram w sesji gamingowej", 
        "zużycie pamięci podczas grania", "ile ram gra zużywa",
        # Polish ASCII fallback - key uniquifiers with "gram" / "grania" context
        "ile ramu uzywam podczas grania", "ile ram uzywam podczas grania",
        "ile pamieci uzywam podczas grania", "ile ram podczas grania",
        "ile ram kiedy gram", "ile ramu kiedy gram",
        "ram kiedy gram", 
        "ile pamieci kiedy gram", "ile pamieci podczas grania",
        "pamieci kiedy gram", "ram gaming session",
        # English
        "how much ram do i use when gaming",
        "how much memory do i use while gaming",
        "ram usage during gaming", "memory usage while gaming",
        "how much ram does gaming use", "gaming ram consumption",
        "typical ram usage when gaming", "how much ram for gaming",
        "ram usage in games", "how much memory does the game use",
        "ram while playing games", "gaming memory usage",
        "how much ram when i play cs2", "how much ram fortnite uses",
        "average ram during gaming session",
        "ram usage while gaming",
    ],

    # ── How much RAM do I use on a daily basis ────────────────────────────────
    "daily_ram_usage": [
        # Polish
        "ile ramu używam na codzień", "ile pamięci zazwyczaj używam",
        "typowe zużycie ram", "ile ram na co dzień",
        "ile ramu zużywam średnio", "przeciętne zużycie ram",
        "jakie jest moje zwykłe zużycie ram",
        "ile pamięci operacyjnej normalnie używam",
        "ile ram przy normalnej pracy", "ile ram przy codziennej pracy",
        "ile ram zazwyczaj", "zwykłe zużycie pamięci",
        "ile pamięci normalnie zajmuje system", "ram na codzień",
        "ile ram bez gier", "ile pamięci do pracy",
        # English
        "how much ram do i use daily", "how much ram do i normally use",
        "average ram usage", "typical ram usage",
        "how much ram do i use on average", "daily ram consumption",
        "what is my usual ram usage", "normal ram usage",
        "how much memory does my pc typically use",
        "ram usage without gaming", "daily memory usage",
        "everyday ram usage", "average daily memory",
        "what is my average memory usage", "how much ram usually",
        "typical memory load",
    ],

    # ── How long will battery last for activity X ─────────────────────────────
    "battery_estimate": [
        # Natural phrasings - routing audit 2026-06
        "wytrzyma bateria", "jak długo wytrzyma bateria", "ile wytrzyma bateria",
        "ile zostało baterii", "na ile starczy baterii", "jak długo bateria",
        "ile czasu na baterii", "jak długo jeszcze wytrzyma bateria",
        # Polish (with ł)
        "ile mi zostało baterii",
        "ile czasu wytrzyma bateria kiedy piszę",
        "jak długo wytrzyma bateria przy pisaniu projektu",
        "ile godzin zostało mi baterii", "jak długo laptop pociągnie",
        "jak długo wytrzyma bateria w pociągu",
        "jak długo bateria przy pracy biurowej",
        "ile godzin grania zostało mi na baterii",
        "jak długo bateria przy youtube", "jak długo bateria przy oglądaniu",
        "czy bateria starczy na film", "czy bateria starczy na prezentację",
        "ile zostało czasu na baterii", "na ile jeszcze wystarczy bateria",
        "ile godzin bateria przy normalnym użytkowaniu",
        "szacowany czas pracy na baterii", "prognoza baterii",
        "jak długo wytrzyma laptop bez ładowania",
        # Polish ASCII fallback (l instead of ł - for users without Polish keyboard)
        "jak dlugo wytrzyma bateria", "ile mi zostalo baterii",
        "ile czasu wytrzyma bateria kiedy pisze",
        "jak dlugo wytrzyma bateria przy pisaniu projektu",
        "ile godzin zostalo mi baterii", "jak dlugo laptop pociagnie",
        "jak dlugo bateria", 
        "jak dlugo bateria pracy", "ile godzin bateria",
        "szacowany czas bateria", "bateria ile czasu",
        # English
        "how long will my battery last", "battery life estimate",
        "how long will the battery last on the train",
        "how long will battery last while writing a project",
        "how many hours of battery do i have left",
        "how long until battery dies", "battery time estimate",
        "how long will battery last for work",
        "how long for gaming on battery", "battery hours remaining",
        "will battery last through a presentation",
        "can battery last for a movie", "estimated battery life",
        "how long will laptop last without charging",
        "battery runtime estimate", "predicted battery life",
        "how much time do i have on battery",
        # English short forms without "my" (multi-word, beat uptime "how long" token)
        "how long will battery last", "how long does battery last",
        "how long battery will last", "battery life remaining",
        "hours left on battery", "battery time left",
        "how many hours battery", "battery estimate",
    ],

    # ── Can I upgrade RAM or storage on this machine ──────────────────────────
    "upgrade_feasibility": [
        # Natural phrasings - routing audit 2026-06
        "dołożyć ramu", "dołożyć więcej ram", "dołożyć ram", "więcej ramu",
        "czy mogę dołożyć ram", "dołożyć ram do laptopa", "czy mogę dołożyć więcej ramu",
        "wymienić dysk", "wymienić dysk na większy", "większy dysk",
        "czy da się wymienić dysk", "wymiana dysku", "rozbudować komputer",
        "czy mogę rozbudować", "czy da się wymienić dysk na większy",
        # Polish (with ł/ó/ę etc.)
        "czy mogę rozbudować ram",
        "czy da się dołożyć ram do tego laptopa",
        "czy laptop ma możliwość rozbudowy ramu",
        "czy mogę zainstalować więcej ramu",
        "czy mogę wymienić ram na więcej gb",
        "czy da się wbudować większy dysk", "czy można dodać dysk",
        "czy można wymienić dysk", "czy mogę dołożyć ssd",
        "czy laptop obsługuje upgrade", "czy mam wolne sloty ram",
        "ile slotów ram jest wolnych", "ile slotów ram mam",
        "czy mogę rozbudować pamięć", "czy mogę dołożyć pamięć",
        "czy warto dokupić ram", "upgrade ramu możliwy",
        "ile gb mogę wsadzić w ram", "maksymalna ilość ram",
        "czy komputer obsługuje więcej ramu", "upgrade dysk możliwy",
        "czy warto dokupić dysk", "ile ssd mogę dodać",
        "czy laptop da się rozbudować", "możliwości rozbudowy",
        "czy sprzęt obsługuje upgrade", "co mogę dokupić do komputera",
        # Polish ASCII fallback (l instead of ł)
        "czy moge dolożyc ram", "czy moge rozbudowac ram",
        "czy da sie dolożyc ram", "dolożyc ram do laptopa",
        "czy moge dolożyc pamieci", "czy moge dolożyc ssd",
        "sloty ram wolne", "ile slotow ram",
        "wolne sloty ram", "upgrade ramu",
        "mozliwosc rozbudowy", "rozbudowa laptopa",
        "dolożyc ram", "dolożyc dysk",
        # English
        "can i add more ram", "can i upgrade my ram",
        "is ram upgradeable on this laptop", "can i add ram to my laptop",
        "can i install more ram", "can i replace ram with more gb",
        "can i add an ssd", "can i add another drive",
        "upgrade feasibility", "can this laptop be upgraded",
        "how many ram slots do i have", "are there free ram slots",
        "how much ram can i install maximum", "max supported ram",
        "is my ram upgradeable", "can i expand storage",
        "upgrade ram possible", "can i put more ram in",
        "is storage upgradeable", "can i add more storage",
        "laptop upgrade options", "hardware upgrade check",
        "how much ram can i add", "ssd upgrade possible",
        "what can i upgrade on this pc", "upgrade my laptop",
    ],

    # ── Upgrade Readiness: will a SPECIFIC part fit this machine ──────────────
    # (upgrade_advice = "what should I upgrade", upgrade_feasibility = slots;
    #  this one = "czy i5 11400F wejdzie na moją płytę" - socket/chipset check)
    "upgrade_compat": [
        # Polish - phrase CORES first: the part name sits mid-sentence
        # ("czy i5 11400f bedzie pasowac..."), so patterns must not assume
        # the question word is adjacent to the verb.
        "będzie pasować do", "bedzie pasowac do",
        "będzie pasował do", "bedzie pasowal do",
        "pasuje do mojej płyty", "pasuje do mojej plyty",
        "pasuje do płyty głównej", "pasuje do plyty glownej",
        "pasuje do mojego zestawu", "pasuje do mojego komputera",
        "wymiana procesora na", "wymiana karty na",
        "zmiana procesora na", "zmiana karty na",
        "wymiana cpu na", "wymiana gpu na",
        "czy będzie pasować", "czy bedzie pasowac", "czy będzie pasował",
        "czy pasuje do mojej płyty", "czy pasuje do plyty",
        "czy pasuje do mojego komputera", "czy zadziała na mojej płycie",
        "czy zadziala na mojej plycie", "czy zadziała w moim komputerze",
        "czy mogę włożyć procesor", "czy moge wlozyc procesor",
        # ASCII twin loses to hw_motherboard; the accented pattern also
        # matches unaccented input via the parser's fold pass.
        "czy wejdzie na moją płytę",
        "kompatybilny z moją płytą", "kompatybilny z moja plyta",
        "kompatybilność procesora", "kompatybilnosc procesora",
        "kompatybilność części", "kompatybilnosc czesci",
        "sprawdź kompatybilność", "sprawdz kompatybilnosc",
        "wymienić procesor na", "wymienic procesor na",
        "zmienić procesor na", "zmienic procesor na",
        "wymienić kartę na", "wymienic karte na",
        "wymiana procesora na nowszy", "upgrade procesora do",
        "planuję kupić procesor", "planuje kupic procesor",
        "zamierzam kupić procesor", "chcę kupić procesor",
        "nowy procesor do mojej płyty", "nowa karta do mojego zestawu",
        "jaki mam socket", "jaki socket mam", "socket mojej płyty",
        "socket mojej plyty", "jaki socket ma moja płyta",
        "czy potrzebna nowa płyta",
        "czy muszę wymienić płytę główną",
        # English - phrase cores (part name sits mid-sentence)
        "fit my board", "fit my motherboard", "fit in my pc",
        "work with my board", "work on my motherboard",
        "compatible with my board",
        "will it fit my", "will it work with my motherboard",
        "will it work on my board", "compatible with my motherboard",
        "compatible with my pc", "cpu compatibility check",
        "gpu compatibility check", "check compatibility",
        "upgrade my cpu to", "upgrade my gpu to",
        "swap my cpu for", "replace my cpu with", "replace my gpu with",
        "planning to buy a cpu", "planning to buy a gpu",
        "does it fit my board", "will this cpu fit",
        "what socket do i have", "what socket is my motherboard",
        "do i need a new motherboard for",
    ],

    # ── Upgrade Readiness: RAM type/speed vs the platform ─────────────────────
    # (upgrade_feasibility = free slots/max GB; this one = DDR gen + MHz fit)
    "ram_compat": [
        # Polish
        "jaki ram pasuje", "jaki ram pasuje do mojej płyty",
        "jaki ram do mojej płyty", "jaki ram do mojej plyty",
        "jaka pamięć pasuje", "jaka pamiec pasuje",
        "jaki typ ram mam", "jaki typ pamięci mam",
        "czy ddr5 zadziała", "czy ddr5 zadziala", "czy ddr5 pasuje",
        "czy ddr4 zadziała", "czy ddr4 zadziala", "czy ddr4 pasuje",
        "kompatybilność ram", "kompatybilnosc ram",
        "jaka prędkość ram mogę", "jaka predkosc ram",
        "jaki ram kupić do tej płyty", "jaki ram kupic do tej plyty",
        "ram do mojej płyty głównej", "ram do plyty glownej",
        "jakie kości ram pasują", "jakie kosci ram pasuja",
        # English
        "what ram fits", "which ram fits my", "what ram fits my motherboard",
        "ram compatibility", "will ddr5 work", "will ddr4 work",
        "what memory fits", "ram for my motherboard",
        "which ddr do i have", "what ddr is my pc",
        "what ram speed can i use", "which ram should i buy for this board",
    ],

    # ── Fan Dashboard consult (chart's hck_GPT [AI] button pastes this) ──────
    "fan_consult": [
        # Polish - the exact pasted question + natural variants
        "chyba będę konfigurować wentylatory", "będę konfigurować wentylatory",
        "bede konfigurowac wentylatory", "konfiguruję wentylatory",
        "zanim ustawię wentylatory", "chcę ustawić krzywą wentylatorów",
        "czy mogę podkręcić wentylatory", "sprawdź temperatury przed wentylatorami",
        # English
        "about to configure my fans", "before i tune my fans",
        "i will configure the fans", "check temps before fan tuning",
        "are my temps ok for fan tuning",
    ],

    # ── Apply the learned hck_GPT - AI fan profile from chat ─────────────────
    "fan_apply_ai": [
        # Polish
        "ustaw profil ai wentylatorów", "ustaw profil ai wentylatorow",
        "włącz profil ai wentylatorów", "wlacz profil ai wentylatorow",
        "zmień profil wentylatorów na ai", "przełącz wentylatory na ai",
        "ustaw wyuczony profil wentylatorów", "profil hck_gpt ai wentylatory",
        "zmień plan wentylatorów", "zmien plan wentylatorow",
        # English
        "apply the ai fan profile", "apply ai fan profile",
        "switch fans to the ai profile", "set the learned fan profile",
        "change my fan plan to ai", "enable the hck_gpt fan profile",
    ],

    # ── Which process eats most disk or RAM ───────────────────────────────────
    "top_resource_hog": [
        # colloquial variants (2026-07-16 pass)
        "co tak obciąża komputer",
        "co zżera zasoby",
        "co obciąża system",
        "what is hogging my pc",
        "what is using everything",
        "what is taking all my resources",

        # Polish tokens - unique verbs that DON'T appear in hw_ram/hw_storage
        "zjada", "pozera", "zeżera", "kradnie", "pochłania",
        # Polish
        "jaki proces zjada mi najwięcej ramu",
        "jaki proces zjada mi najwięcej dysku",
        "który program pożera dysk", "który program pożera ram",
        "co najbardziej obciąża dysk", "co najbardziej obciąża pamięć",
        "co zjada ram teraz", "co zjada dysk teraz",
        "kto pożera zasoby", "największy pożeracz ram",
        "który program używa najwięcej miejsca na dysku",
        "który program ma największy io dysku",
        "największy io dysku", "top io dysku",
        "co zużywa najwięcej ramu teraz", "co zżera ram",
        "co zżera dysk", "co zajmuje dysk teraz",
        "który proces kradnie ram", "który proces blokuje dysk",
        "jaki program zajmuje dysk najbardziej",
        "co tak dysk zajmuje", "co tak pamięć zajmuje",
        "pochłaniacz ramu", "pochłaniacz dysku",
        # Polish ASCII fallback
        "co zjada ram", "co zjada dysk",
        "co pozera ram", "co pozera dysk",
        "zjada mi ram", "zjada mi dysk",
        "zjada ram teraz", "zjada dysk teraz",
        "pozera zasoby", "top io ram",
        # English
        "which process uses the most ram", "which process uses the most disk",
        "what is the top ram consumer", "which app uses most memory",
        "what is eating my disk", "what is eating my ram",
        "biggest ram hog", "biggest disk hog",
        "top disk io process", "what has highest disk usage",
        "which program hogs memory", "most ram intensive process",
        "most disk intensive process", "top memory consumer",
        "what is hogging disk io", "what process uses most storage",
        "who is eating disk io", "disk hog right now",
        "ram hog right now", "top resource hog",
        "which app is using the most ram", "memory hog process",
    ],

    # ── DeepMonitor live-sensor intents (2026-07-02) ─────────────────────────
    "sensor_report": [
        # deep-param / learning phrasings (2026-07-05)
        "pokaż wszystkie parametry",
        "głębokie parametry",
        "parametry sprzętu na żywo",
        "wszystkie odczyty naraz",
        "napięcia i temperatury",
        "pełny odczyt sprzętu",
        "show me every parameter",
        "deep hardware parameters",
        "all live readings",
        "full hardware readout",
        # Polish
        "raport czujników", "raport sensorów", "wszystkie czujniki",
        "pokaż czujniki", "pokaż sensory", "odczyty czujników",
        "deep monitor", "deepmonitor", "pełne parametry",
        "wszystkie parametry", "wszystkie odczyty", "parametry na żywo",
        # English
        "sensor report", "all sensors", "show sensors",
        "sensor readings", "full sensor report", "all readings",
        "deep monitor report", "live parameters", "all parameters",
        "full telemetry report", "hardware readings now",
    ],
    "hottest_component": [
        # Polish
        "najgorętszy podzespół", "co jest najgorętsze", "najcieplejszy podzespół",
        "co się najbardziej grzeje", "co sie najbardziej grzeje",
        "który podzespół jest najgorętszy", "co jest najcieplejsze",
        "co najbardziej grzeje", "najgorętszy element",
        # English
        "hottest component", "what is hottest", "which part is hottest",
        "what runs hottest", "hottest part right now",
        "which component is the hottest", "what is the warmest part",
    ],
    "cpu_clock": [
        # Polish
        "zegar procesora", "taktowanie procesora", "taktowanie cpu",
        "ile mhz ma procesor", "częstotliwość procesora", "zegar cpu",
        "na ilu mhz chodzi procesor", "aktualne taktowanie",
        # English
        "cpu clock", "cpu frequency", "current cpu clock",
        "what clock is my cpu at", "cpu mhz now", "processor frequency",
        "how fast is my cpu clocked", "current clock speed",
    ],
    "vram_usage": [
        # Polish
        "użycie vram", "zużycie vram", "ile vram zajęte",
        "pamięć karty graficznej", "ile pamięci gpu", "vram karty",
        "zajętość vram", "ile vramu używam",
        # English
        "vram usage", "how much vram", "gpu memory usage",
        "video memory used", "how much video memory",
        "vram used right now", "gpu ram usage",
    ],
    # ── Cooling & guided tune-up (2026-07-02) ────────────────────────────────
    "cooling_advice": [
        # Polish
        "jak schłodzić komputer", "jak schłodzić procesor", "jak schłodzić laptopa",
        "jak obniżyć temperatury", "jak zmniejszyć temperatury",
        "jak poprawić chłodzenie", "komputer się grzeje co robić",
        "co zrobić z temperaturami", "jak ochłodzić komputer",
        # English
        "how to cool my pc", "how to cool down my computer",
        "lower my temperatures", "how do i reduce temperatures",
        "improve cooling", "my pc runs hot what to do",
    ],
    "optimize_guide": [
        # guidance & context variants (round 2)
        "pomóż mi przyspieszyć komputer",
        "pomóż mi zoptymalizować komputer",
        "pomóż z optymalizacją",
        "co mam zrobić krok po kroku",
        "przeprowadź mnie krok po kroku",
        "pokaż mi co zrobić po kolei",
        "help me optimize my pc",
        "help me speed up my computer",
        "what should i do step by step",
        "take me through it step by step",

        # colloquial variants (2026-07-16 pass)
        "ogarnij mi komputer",
        "ogarnij komputer",
        "zrób coś z tym komputerem",
        "zrób porządek na komputerze",
        "tune my pc",
        "fix my slow pc",

        # Polish - the master 5-step flow (FlowEngine)
        # how-to inflections (diacritic folding covers ascii input)
        "jak zoptymalizować komputer", "jak zoptymalizować mój komputer",
        "jak zoptymalizować pc", "jak zoptymalizować mój pc",
        "jak zoptymalizować laptopa", "jak zoptymalizować system",
        "zoptymalizować komputer", "zoptymalizować pc",
        "chcę zoptymalizować komputer", "poprowadź mnie przez optymalizację",
        "poprowadź przez optymalizację", "poprowadź mnie",
        "zoptymalizuj mój komputer", "zoptymalizuj komputer", "zoptymalizuj mi komputer",
        "optymalizacja komputera", "przyspiesz mój komputer", "przyspiesz komputer",
        "napraw wydajność", "popraw wydajność komputera", "zrób porządek z komputerem",
        "komputer do optymalizacji", "pełna optymalizacja", "optymalizuj wszystko",
        "przeprowadź mnie przez optymalizację", "pokaż jak przyspieszyć komputer",
        # English
        "optimize my pc", "optimize my computer", "optimize this pc",
        "speed up my pc", "speed up my computer", "make my pc faster",
        "make my computer faster", "full optimization", "fix my performance",
        "clean up my pc", "walk me through optimization",
        "how do i speed up my computer", "improve my pc performance",
        "how to optimize my computer", "how to optimize my pc",
        "how can i optimize my pc", "how do i optimize my computer",
        "guide me through optimization",
    ],
    "recall_numbers": [
        # guidance & context variants (round 2)
        "wróć do tego",
        "wróć do tematu",
        "co mówiłeś wcześniej",
        "o czym rozmawialiśmy",
        "przypomnij co pokazałeś",
        "go back to that",
        "what did we talk about",
        "what were we discussing",
        "remind me what you showed",

        # Polish - response-ledger recall
        "ile to było", "ile to wynosiło", "powtórz liczby", "powtórz wyniki",
        "przypomnij wyniki", "przypomnij te liczby", "jakie były wyniki",
        "co mi wcześniej pokazałeś", "wróć do tamtych liczb",
        # English
        "what was that number", "what were the numbers", "repeat the numbers",
        "remind me the results", "what did you show me before",
        "what were the results", "recall the numbers",
    ],
    "tuneup_guide": [
        # Polish
        "podrasuj mój komputer", "podrasować komputer", "chcę podrasować sprzęt",
        "przewodnik optymalizacji", "optymalizacja krok po kroku",
        "popraw wydajność krok po kroku", 
        "wyciśnij więcej z komputera", "plan optymalizacji", "zacznij tuning",
        # English
        "tune up my pc", "pc tune up guide", "optimize my pc step by step",
        "optimization guide",
        "make my pc faster guide", "squeeze more out of my pc",
    ],

}

# ── Entity extraction map ─────────────────────────────────────────────────────
# token -> canonical entity name
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
    # New entities
    "napięcie": "voltage", "vcore": "voltage", "voltage": "voltage",
    "wentylator": "fan", "fans": "fan", "rpm": "fan",
    "gaming": "gaming", "fps": "gaming", "granie": "gaming",
    "tydzień": "week", "weekly": "week", "tygodnia": "week",
    # New entities (symptom + action + context)
    "zamroziło": "freeze", "froze": "freeze", "freeze": "freeze",
    "hałas": "noise", "głośny": "noise", "noisy": "noise",
    "normalne": "baseline", "normal": "baseline",
    "gra": "game", "grę": "game",
    "zabij": "kill", "kill": "kill", "force": "kill",
    "oc": "overclock", "podkręcony": "overclock",
    "flush": "flush", "zwolnij": "flush",
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
