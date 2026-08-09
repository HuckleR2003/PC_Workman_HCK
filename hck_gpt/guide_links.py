# hck_gpt/guide_links.py
"""
THE one map from intent -> published guide on pcworkman.dev.

Why this exists: 23 guides live on the site and the app never mentioned them.
A user asking hck_GPT "why is my disk at 100%" gets their own live numbers,
but the full explanation sat on a website they had no reason to visit.

Rules:
  - This module imports NOTHING from the app. It is pure data plus two helpers,
    so it is safe to import from the response builder and from the chat panel.
  - Offers are attached centrally in ResponseBuilder.build(), never inside the
    90+ individual handlers. One mechanism per subject.
  - Only intents whose question a guide genuinely answers are mapped. Short
    alias intents ("cpu", "ram", "dysk") deliberately get nothing: they are
    instant lookups, and an offer there would be noise.
  - An offer is a suggestion, never a substitute. The answer above it always
    stands on its own with the user's real data.

Guarded by tests/test_guide_links.py.
"""

SITE = "https://pcworkman.dev/guides/"

# The two guides written in Polish first: for them index.html IS the Polish
# page and the English one lives at index_en.html. Every other guide is the
# other way round. Getting this backwards would send users to the wrong
# language, so it is data, not a guess in the URL builder.
_PL_NATIVE = frozenset({
    "jak-przyspieszyc-komputer",
    "ktore-uslugi-windows-wylaczyc",
})

# slug -> short link label. Not the article H1: a chat line needs a label that
# reads in one glance, and several H1s are two-line headlines.
GUIDES = {
    "why-is-my-ram-usage-so-high": {
        "pl": "Dlaczego użycie RAM jest tak wysokie",
        "en": "Why is my RAM usage so high",
    },
    "why-is-my-disk-at-100-percent": {
        "pl": "Dlaczego dysk ma 100% użycia",
        "en": "Why is my disk at 100%",
    },
    "is-my-ssd-dying-drive-health": {
        "pl": "Czy mój SSD umiera",
        "en": "Is my SSD dying",
    },
    "is-my-pc-healthy": {
        "pl": "Czy mój komputer jest sprawny",
        "en": "Is my PC healthy",
    },
    "why-are-my-pc-fans-so-loud": {
        "pl": "Dlaczego wentylatory są tak głośne",
        "en": "Why are my PC fans so loud",
    },
    "cpu-gpu-throttling-thermal-vs-power": {
        "pl": "Dlaczego taktowanie spada pod obciążeniem",
        "en": "Why does my clock speed drop under load",
    },
    "normal-cpu-temperature": {
        "pl": "Jaka temperatura procesora jest prawidłowa",
        "en": "What is a normal CPU temperature",
    },
    "is-my-psu-dying-12v-rail": {
        "pl": "Czy program wykryje, że zasilacz umiera",
        "en": "Can software tell if your PSU is dying",
    },
    "which-startup-apps-can-i-disable": {
        "pl": "Które programy można wyłączyć z autostartu",
        "en": "Which startup apps can I disable",
    },
    "what-is-this-process": {
        "pl": "Co to za proces w Menedżerze zadań",
        "en": "What is this process in Task Manager",
    },
    "will-this-cpu-fit-motherboard": {
        "pl": "Czy ten procesor będzie działać z moją płytą",
        "en": "Will this CPU work with my motherboard",
    },
    "what-should-i-upgrade-first": {
        "pl": "Co wymienić najpierw",
        "en": "What should I upgrade first",
    },
    "how-much-vram-do-i-need": {
        "pl": "Ile VRAM naprawdę potrzebujesz",
        "en": "How much VRAM do you actually need",
    },
    "pc-slow-but-task-manager-looks-normal": {
        "pl": "Wszędzie 20%, a komputer działa wolno",
        "en": "Everything says 20% and the PC still feels slow",
    },
    "game-stutters-high-fps-frame-time": {
        "pl": "Wysoki FPS, a gra przycina",
        "en": "High FPS but the game still stutters",
    },
    "pc-restarts-while-gaming-kernel-power-41": {
        "pl": "Komputer restartuje się w grach (Kernel-Power 41)",
        "en": "PC restarts while gaming (Kernel-Power 41)",
    },
    "xmp-expo-crashes-ram-stability": {
        "pl": "Uruchomiony nie znaczy stabilny (XMP/EXPO)",
        "en": "Booted is not the same as stable (XMP/EXPO)",
    },
    "ghost-drivers-windows": {
        "pl": "Sterowniki widma w Windows",
        "en": "Ghost drivers in Windows",
    },
    "jak-przyspieszyc-komputer": {
        "pl": "Jak przyspieszyć komputer bez mitów",
        "en": "How to speed up a Windows PC without the myths",
    },
    "ktore-uslugi-windows-wylaczyc": {
        "pl": "Które usługi Windows można bezpiecznie wyłączyć",
        "en": "Which Windows services can you turn off safely",
    },
    "what-your-pc-learned": {
        "pl": "Czego Twój komputer nauczył się o sobie",
        "en": "What your PC has learned about itself",
    },
    "ai-pc-monitoring-vs-traditional": {
        "pl": "Przestań optymalizować przeciętny komputer",
        "en": "Stop optimizing the average PC",
    },
}

# intent -> slug. Only genuine matches; an offer that does not fit the question
# costs more trust than it earns.
INTENT_GUIDE = {
    # memory
    "ram_why_high":          "why-is-my-ram-usage-so-high",
    "daily_ram_usage":       "why-is-my-ram-usage-so-high",
    "gaming_ram_usage":      "why-is-my-ram-usage-so-high",
    "ram_compare":           "why-is-my-ram-usage-so-high",
    "swap_analysis":         "why-is-my-ram-usage-so-high",
    # storage
    "disk_usage_why":        "why-is-my-disk-at-100-percent",
    "disk_speed":            "why-is-my-disk-at-100-percent",
    "disk_health":           "is-my-ssd-dying-drive-health",
    # overall state
    "health_check":          "is-my-pc-healthy",
    "system_risk":           "is-my-pc-healthy",
    # cooling and noise
    "fan_speed":             "why-are-my-pc-fans-so-loud",
    "symptom_noisy":         "why-are-my-pc-fans-so-loud",
    "fan_noise_history":     "why-are-my-pc-fans-so-loud",
    "cooling_advice":        "why-are-my-pc-fans-so-loud",
    "fan_consult":           "why-are-my-pc-fans-so-loud",
    # thermals and clocks
    "throttle_check":        "cpu-gpu-throttling-thermal-vs-power",
    "thermal_prediction":    "cpu-gpu-throttling-thermal-vs-power",
    "cpu_clock":             "cpu-gpu-throttling-thermal-vs-power",
    "temperature":           "normal-cpu-temperature",
    "gpu_temp_why":          "normal-cpu-temperature",
    "hottest_component":     "normal-cpu-temperature",
    "thermal_history":       "normal-cpu-temperature",
    # power delivery
    "voltage_check":         "is-my-psu-dying-12v-rail",
    # startup
    "startup_check":         "which-startup-apps-can-i-disable",
    "startup_safety":        "which-startup-apps-can-i-disable",
    "startup_slowdown":      "which-startup-apps-can-i-disable",
    # processes and trust
    "process_info":          "what-is-this-process",
    "process_identity":      "what-is-this-process",
    "process_deep_dive":     "what-is-this-process",
    "virus_check":           "what-is-this-process",
    "top_resource_hog":      "what-is-this-process",
    # upgrades
    "upgrade_compat":        "will-this-cpu-fit-motherboard",
    "ram_compat":            "will-this-cpu-fit-motherboard",
    "upgrade_feasibility":   "will-this-cpu-fit-motherboard",
    "upgrade_advice":        "what-should-i-upgrade-first",
    "upgrade_plan":          "what-should-i-upgrade-first",
    "vram_usage":            "how-much-vram-do-i-need",
    "game_can_run":          "how-much-vram-do-i-need",
    # slowness and stutter
    "why_slow":              "pc-slow-but-task-manager-looks-normal",
    "perf_change":           "pc-slow-but-task-manager-looks-normal",
    "fps_degradation":       "game-stutters-high-fps-frame-time",
    # crashes and stability
    "crash_context":         "pc-restarts-while-gaming-kernel-power-41",
    "power_after_restart":   "pc-restarts-while-gaming-kernel-power-41",
    "symptom_freeze":        "xmp-expo-crashes-ram-stability",
    # drivers
    "driver_status":         "ghost-drivers-windows",
    # tuning
    "speed_up_pc":           "jak-przyspieszyc-komputer",
    "optimize_guide":        "jak-przyspieszyc-komputer",
    "tuneup_guide":          "jak-przyspieszyc-komputer",
    "unnecessary_programs":  "ktore-uslugi-windows-wylaczyc",
    "stale_apps":            "ktore-uslugi-windows-wylaczyc",
    # guides_available is deliberately absent: that handler IS the guide
    # answer, so an offer under it would repeat itself.
    # what the app learned
    "explain_proactive":     "what-your-pc-learned",
    "ai_context":            "what-your-pc-learned",
    "compare_baseline":      "what-your-pc-learned",
    "about_program":         "ai-pc-monitoring-vs-traditional",
}

# Shown before the clickable marker. First person, because a person wrote them.
_LEAD = {
    "pl": "Napisałem o tym cały poradnik, za darmo i bez logowania:",
    "en": "I wrote a full guide on this, free and with no signup:",
}
_MARK = {"pl": "Poradnik", "en": "Guide"}


def url_for(slug: str, lang: str = "pl") -> str:
    """Public URL of a guide in the requested language."""
    base = SITE + slug + "/"
    pl_native = slug in _PL_NATIVE
    if lang == "pl":
        return base if pl_native else base + "index_pl.html"
    return base + "index_en.html" if pl_native else base


def label_for(slug: str, lang: str = "pl") -> str:
    """Short link label, falling back to the other language then the slug."""
    entry = GUIDES.get(slug)
    if not entry:
        return slug.replace("-", " ")
    return entry.get(lang) or entry.get("en") or entry.get("pl") or slug


def marker_for(slug: str, lang: str = "pl") -> str:
    """The clickable token the chat panel turns into a link."""
    return "[-> %s: %s]" % (_MARK.get(lang, _MARK["en"]), label_for(slug, lang))


def offer_lines(intent: str, lang: str = "pl"):
    """
    Two lines offering the guide that matches this intent, or None.
    Returns lines only; deciding whether to show them belongs to the caller.
    """
    slug = INTENT_GUIDE.get(intent)
    if not slug:
        return None
    return [_LEAD.get(lang, _LEAD["en"]), marker_for(slug, lang)]


# Guides already offered in this app run. The point of the offer is to be
# useful once, not to repeat itself: a user asking about RAM five times gets
# the link on the first answer and clean answers afterwards. Process lifetime
# is the session, so no reset hook is needed outside tests.
_offered = set()


def take_offer(intent: str, lang: str = "pl"):
    """
    Offer lines for this intent the FIRST time its guide comes up, then None.
    Marks the guide as offered, so call it only when about to show the lines.
    """
    slug = INTENT_GUIDE.get(intent)
    if not slug or slug in _offered:
        return None
    _offered.add(slug)
    return offer_lines(intent, lang)


def reset_offers() -> None:
    """Forget what has been offered. Used by tests."""
    _offered.clear()


def slug_for_marker(text: str):
    """
    Reverse lookup used by the chat panel: given a rendered marker label,
    return the slug and language it came from. None when it is not a guide
    marker, so in-app navigation links are left alone.
    """
    for prefix_lang, prefix in _MARK.items():
        head = prefix + ": "
        if text.startswith(head):
            label = text[len(head):]
            for slug, names in GUIDES.items():
                if names.get(prefix_lang) == label or label in names.values():
                    return slug, prefix_lang
    return None
