# hck_gpt/chat_handler.py
from __future__ import annotations
from .service_setup_wizard import ServiceSetupWizard
from .services_manager import ServicesManager
from import_core import register_component, update_status, STATUS_OK, STATUS_IDLE

try:
    from .insights import InsightsEngine
    HAS_INSIGHTS = True
except ImportError:
    HAS_INSIGHTS = False

# ── New AI layer (intent parser + response builder + memory) ──────────────────
try:
    from .intents.parser        import intent_parser
    from .intents.lang_detect   import detect_language
    from .responses.builder     import response_builder
    from .memory.session_memory import session_memory
    from .memory.user_knowledge import user_knowledge
    HAS_AI_LAYER = True
except Exception:
    HAS_AI_LAYER = False

# ── Proactive background monitor ──────────────────────────────────────────────
try:
    from .memory.proactive_monitor import proactive_monitor
    HAS_PROACTIVE = True
except Exception:
    HAS_PROACTIVE = False

# ── Hybrid Engine (rule + Ollama LLM) ─────────────────────────────────────────
try:
    from .engine.hybrid_engine import hybrid_engine
    HAS_HYBRID = True
except Exception:
    HAS_HYBRID = False

_NO_INSIGHTS = ["hck_GPT: Insights engine not available."]

def _t_handler(lang: str, pl: str, en: str) -> str:
    """Bilingual string helper for ChatHandler methods."""
    return en if lang == "en" else pl

# Legacy keyword routes (kept as fallback for service/wizard commands)
_ROUTES: list[tuple[tuple[str, ...], str]] = [
    (("service setup", "service's setup", "setup services"),
     "_cmd_service_setup"),
    (("restore services", "enable services", "restore all"),
     "_restore_services"),
    (("service status", "services status", "show services"),
     "_show_service_status"),
    (("alerts", "anomalies", "spikes", "anomalie", "alerty"),
     "_cmd_anomalies"),
    (("insights", "what's up", "whats up", "co nowego",
      "status", "co sie dzieje"),
     "_cmd_insights"),
    (("teaser", "predict", "guess", "co dzis"),
     "_cmd_teaser"),
    (("report", "raport", "today"),
     "_insights_report_text"),
]

# Intents handled by legacy route only (bypass AI layer entirely).
# Covers: service commands + InsightsEngine commands that must NOT go to Ollama.
_LEGACY_ONLY_KEYWORDS = (
    # ── Service wizard commands ───────────────────────────────────────────────
    "service setup", "service's setup", "setup services",
    "restore services", "enable services", "restore all",
    "service status", "services status", "show services",
    # ── InsightsEngine commands (must use stats DB, not Ollama) ───────────────
    "alerts", "anomalies", "anomalie", "alerty", "spikes",
    "insights", "co nowego", "co sie dzieje", "whats up", "what's up",
    "teaser", "predict", "co dzis", "guess",
    "today report", "raport",
)

# ── Quick shorthand aliases ───────────────────────────────────────────────────
# Exact stripped-lower match -> response_builder intent name (bypasses parser).
_QUICK_ALIASES: dict[str, str] = {
    # Hardware
    "cpu":           "hw_cpu",
    "procesor":      "hw_cpu",
    "ram":           "hw_ram",
    "pamiec":        "hw_ram",       # accent-stripped
    "pamięć":        "hw_ram",
    "gpu":           "hw_gpu",
    "karta":         "hw_gpu",
    "grafika":       "hw_gpu",
    "mb":            "hw_motherboard",
    "motherboard":   "hw_motherboard",
    "plyta":         "hw_motherboard",
    "płyta":         "hw_motherboard",
    "disk":          "hw_storage",
    "storage":       "hw_storage",
    "dysk":          "hw_storage",
    "dyski":         "hw_storage",
    "specs":         "hw_all",
    "spec":          "hw_all",
    "specyfikacja":  "hw_all",
    # Diagnostics
    "health":        "health_check",
    "zdrowie":       "health_check",
    "temp":          "temperature",
    "temps":         "temperature",
    "temperatury":   "temperature",
    "throttle":      "throttle_check",
    # Performance
    "perf":          "performance",
    "wydajnosc":     "performance",  # accent-stripped
    "wydajność":     "performance",
    "procesy":       "processes",
    "processes":     "processes",
    "top":           "processes",
    # New intents - quick aliases
    "turbo":         "turbo_boost",
    "lag":           "why_slow",
    "lagi":          "why_slow",
    "laguje":        "why_slow",
    # Stats / session
    "stats":         "stats",
    "statystyki":    "stats",
    "uptime":        "uptime",
    "sesja":         "uptime",
    # System
    "optimization":  "optimization",
    "optymalizacja": "optimization",
    "power":         "power_plan",
    "zasilanie":     "power_plan",
    # New intents
    "voltage":       "voltage_check",
    "vcore":         "voltage_check",
    "napięcie":      "voltage_check",
    "fans":          "fan_speed",
    "fan":           "fan_speed",
    "wentylator":    "fan_speed",
    "gaming":        "gaming_session",
    "fps":           "gaming_session",
    "weekly":        "weekly_trends",
    "tygodniowe":    "weekly_trends",
    "overheat":      "thermal_prediction",
    "przegrzanie":   "thermal_prediction",
    # Community feedback intents - quick aliases
    "sterowniki":         "driver_status",
    "drivers":            "driver_status",
    "driver":             "driver_status",
    "wentylatory":        "fan_noise_history",
    "glosnosc":           "fan_noise_history",
    "głośność":           "fan_noise_history",
    "czas gier":          "gaming_vs_work_time",
    "gaming time":        "gaming_vs_work_time",
    "nieuzywane":         "stale_apps",
    "unused apps":        "stale_apps",
    "degradacja fps":     "fps_degradation",
    "fps drop":           "fps_degradation",
    "startup wolny":      "startup_slowdown",
    "slow boot":          "startup_slowdown",
    "goracej":            "temp_comparison",
    "hotter":             "temp_comparison",
    "crash":              "crash_context",
    "freeze":             "crash_context",
    "bateria drain":      "battery_drain_rate",
    "battery drain":      "battery_drain_rate",
    "prad":               "power_after_restart",
    "power usage":        "power_after_restart",
    # Wave 2 community intents - quick aliases
    "game":               "game_can_run",
    "gra":                "game_can_run",
    "odpale":             "game_can_run",
    "gaming ram":         "gaming_ram_usage",
    "ram gaming":         "gaming_ram_usage",
    "ile ram gra":        "gaming_ram_usage",
    "daily ram":          "daily_ram_usage",
    "ile ram":            "daily_ram_usage",
    "ram dzien":          "daily_ram_usage",
    "bateria":            "battery_estimate",
    "battery":            "battery_estimate",
    "ile baterii":        "battery_estimate",
    "how long battery":   "battery_estimate",
    "upgrade":            "upgrade_feasibility",
    "ram upgrade":        "upgrade_feasibility",
    "rozbudowa":          "upgrade_feasibility",
    "dołożyć ram":        "upgrade_feasibility",
    "dolożyc ram":        "upgrade_feasibility",
    "top ram":            "top_resource_hog",
    "top disk":           "top_resource_hog",
    "top io":             "top_resource_hog",
    "who eats ram":       "top_resource_hog",
    "co zjada ram":       "top_resource_hog",
    "co zjada dysk":      "top_resource_hog",
    "swap":               "swap_analysis",
    "pagefile":           "swap_analysis",
    "plik wymiany":       "swap_analysis",
    "browser":            "browser_cache",
    "chrome ram":         "browser_cache",
    "network":            "network_usage",
    "siec":               "network_usage",
    "internet kto":       "network_usage",
}

# Keywords that show the styled help card (handled directly, not via builder).
_HELP_KEYWORDS = frozenset({
    "komendy", "commands", "help", "pomoc",
    "komendy!", "commands!", "help!", "pomoc!",
    "?",
})

# ── Greeting triggers ─────────────────────────────────────────────────────────
_GREETING_EXACT = frozenset({
    "cześć", "czesc", "hej", "hejka", "hejko", "siema", "siemano",
    "witaj", "witajcie", "dzień dobry", "dobry wieczór", "dobranoc",
    "hi", "hello", "hey", "good morning", "good evening", "yo",
    "elo", "eloo", "co tam", "co słychać", "jak tam",
})
_GREETING_PREFIXES = (
    "cześć", "hej", "hejka", "siema", "witaj", "dzień dobry",
    "hi ", "hey ", "hello ",
)

# ── "Tell me more" triggers ───────────────────────────────────────────────────
_MORE_TRIGGERS = frozenset({
    "więcej", "wiecej", "więcej szczegółów", "rozwiń", "rozwin",
    "tell me more", "more details", "more info", "more", "expand",
    "co jeszcze", "powiedz więcej", "powiedz wiecej",
    "elabor", "szczegóły", "szczegoly",
})

# ── "What should I do" triggers ──────────────────────────────────────────────
_ACTION_TRIGGERS = frozenset({
    "co zrobić", "co robic", "co powinienem zrobić", "co powinienem robic",
    "jak naprawić", "jak naprawic", "jak to naprawić",
    "co teraz", "co dalej", "jak to poprawić",
    "what should i do", "what do i do", "how do i fix",
    "how to fix", "what now", "what next", "fix it", "napraw to",
    "co mam zrobić", "co mam robic",
})

# ── "Thank you" triggers ──────────────────────────────────────────────────────
_THANKS_TRIGGERS = frozenset({
    "dzięki", "dzieki", "dzięki!", "dziękuję", "dziekuje", "thx",
    "thanks", "thank you", "thanks!", "dzieks", "dzięks",
    "spoko", "super", "świetnie", "fajnie", "ok dzieki",
    "okej dzieki", "ok dzięki", "dobra dzięki", "git", "git git",
})

# Keywords that trigger the reset confirmation flow.
_RESET_KEYWORDS = frozenset({
    "reset", "reset data", "reset db", "restore data",
    "zresetuj", "zresetuj dane", "resetuj dane",
    "clear data", "clear db", "reset bazy", "zresetuj baze",
    "wyczysc dane",
})


class ChatHandler:
    def __init__(self) -> None:
        self.wizard           = ServiceSetupWizard()
        self.services_manager = ServicesManager()
        self.insights: InsightsEngine | None = (
            InsightsEngine() if HAS_INSIGHTS else None
        )
        # Background hardware scan on first init
        if HAS_AI_LAYER:
            self._trigger_hw_scan()

        # Proactive monitor is started from panel.py after callbacks are registered
        # (here we just keep a reference for lang sync)
        self._last_lang: str = "pl"

        # Two-step reset flow state
        self._pending_reset: bool = False

        register_component('hck_gpt.chat_handler', self, STATUS_OK)

    def _trigger_hw_scan(self) -> None:
        """
        Background thread: hardware scan + usage pattern update + pattern detection.
        - scan_and_store()         -> skipped if data is < 24 h old
        - update_usage_patterns()  -> skipped if patterns are < 24 h old
        - detect_and_log_patterns()-> analyses data, writes to insights_log (48 h cooldown)
        """
        import threading
        def _scan():
            try:
                from .context.hardware_scanner import (
                    scan_and_store,
                    update_usage_patterns,
                    detect_and_log_patterns,
                )
                scan_and_store()
                update_usage_patterns()
                detect_and_log_patterns()
            except Exception:
                pass
        threading.Thread(target=_scan, daemon=True, name="hck_hw_scan").start()

    def process_message(self, user_message: str,
                        ui_lang: str = "auto") -> list[str]:
        msg   = user_message.strip()
        lower = msg.lower().strip()

        # ── Language resolution - resolve ONCE at the top so every path uses it
        # ui_lang comes from the user's Language popup choice:
        #   "en"   -> always English regardless of input language
        #   "pl"   -> always Polish regardless of input language
        #   "auto" -> detect from message (default behaviour)
        if ui_lang in ("en", "pl"):
            lang = ui_lang
        else:
            lang = detect_language(msg) if HAS_AI_LAYER else "pl"
        self._last_lang = lang

        if HAS_PROACTIVE:
            try:
                proactive_monitor.set_language(lang)
                proactive_monitor.set_user_active()
            except Exception:
                pass

        def _resolve_lang(text: str) -> str:  # kept for inline calls below
            return lang

        # ── 0. Reset confirmation flow (two-step, waits for tak/yes) ─────────
        if self._pending_reset:
            return self._handle_reset_confirm(lower)

        # ── 1. Service wizard takes priority ──────────────────────────────────
        if self.wizard.is_active():
            return self.wizard.process_input(msg)

        # ── 2. Hard-route service/insights commands (bypass AI layer) ─────────
        if any(kw in lower for kw in _LEGACY_ONLY_KEYWORDS):
            for keywords, handler in _ROUTES:
                if any(kw in lower for kw in keywords):
                    return getattr(self, handler)()

        # ── 3. Help card - exact trigger words ────────────────────────────────
        if lower in _HELP_KEYWORDS:
            return self._show_help(ui_lang if ui_lang in ("en", "pl") else self._last_lang)

        # ── 3.5. Greeting detection ───────────────────────────────────────────
        if lower in _GREETING_EXACT or any(lower.startswith(p) for p in _GREETING_PREFIXES):
            return self._handle_greeting(lang)

        # ── 3.6. "Thank you" detection ────────────────────────────────────────
        if lower in _THANKS_TRIGGERS:
            return self._handle_thanks(lang)

        # ── 3.7. "Tell me more" / expand detection ────────────────────────────
        if lower in _MORE_TRIGGERS or lower.startswith(("więcej o ", "more about ")):
            resp = self._handle_more(lang)
            if resp:
                return resp

        # ── 3.8. "What should I do" / action request ─────────────────────────
        if lower in _ACTION_TRIGGERS or any(
            lower.startswith(p) for p in ("co zrobić z ", "how to fix ", "jak naprawić ")
        ):
            resp = self._handle_action_request(lang)
            if resp:
                return resp

        # ── 4. Reset command ──────────────────────────────────────────────────
        if lower in _RESET_KEYWORDS:
            return self._cmd_reset_confirm()

        # ── 4b. Smart "why" detection - before aliases, route WHY questions ─────
        # Detects "dlaczego X" / "why is X" and maps to the correct diagnostic intent.
        # This fires before the full parser so specific handlers get first priority.
        _WHY_TRIGGERS = frozenset({"dlaczego", "czemu", "skąd", "co powoduje",
                                   "why", "what causes", "why is", "why does"})
        _has_why = any(kw in lower for kw in _WHY_TRIGGERS)
        if _has_why and HAS_AI_LAYER:
            _why_map = [
                (("ram", "pamięć", "pamiec", "memory"), "ram_why_high"),
                (("gpu", "karta graficzna", "graphics card", "karta się grzeje"), "gpu_temp_why"),
                (("wolno", "lag", "lagi", "laguje", "slow", "sluggish", "stutter"), "why_slow"),
                (("cpu", "procesor", "processor"), "why_slow"),
            ]
            try:
                from .intents.parser import ParseResult as _PR_why
                for keywords, why_intent in _why_map:
                    if any(kw in lower for kw in keywords):
                        _fake_why = _PR_why(intent=why_intent, confidence=0.85, raw_text=msg)
                        _why_resp = response_builder.build(_fake_why, lang=lang)
                        if _why_resp:
                            session_memory.add_message("user", msg)
                            session_memory.push_topic(why_intent)
                            for line in _why_resp:
                                session_memory.add_message("assistant", line)
                            return _why_resp
            except Exception:
                pass

        # ── 5. Quick shorthand aliases (single-word bypasses full parser) ─────
        alias_intent = _QUICK_ALIASES.get(lower)
        if alias_intent and HAS_AI_LAYER:
            try:
                from .intents.parser import ParseResult as _PR
                fake = _PR(intent=alias_intent, confidence=1.0, raw_text=msg)
                resp = response_builder.build(fake, lang=lang)
                if resp:
                    session_memory.add_message("user", msg)
                    session_memory.push_topic(alias_intent)
                    for line in resp:
                        session_memory.add_message("assistant", line)
                    return resp
            except Exception:
                pass

        # ── 6. AI intent layer ────────────────────────────────────────────────
        _parsed_result = None   # shared across steps 6 + 7 to avoid double-parse
        if HAS_AI_LAYER:
            try:
                _parsed_result = intent_parser.parse(msg)
                result = _parsed_result
                session_memory.add_message("user", msg)

                # Hybrid engine: rule engine (fast) OR Ollama (smart)
                response = None
                if HAS_HYBRID:
                    response = hybrid_engine.process(msg, result, lang=lang)
                elif result.is_confident(threshold=0.4):
                    response = response_builder.build(result, lang=lang)

                if response:
                    session_memory.push_topic(result.intent)
                    for line in response:
                        session_memory.add_message("assistant", line)
                    try:
                        user_knowledge.log_message(
                            session_memory.session_id, "user", msg)
                        first_line = response[0] if response else ""
                        user_knowledge.log_message(
                            session_memory.session_id, "assistant", first_line)
                    except Exception:
                        pass
                    return response
            except Exception:
                pass

        # ── 7. Entity routing - unknown intent but clear hardware entity ─────────
        # If the parser found no confident intent but extracted a known entity
        # (cpu, gpu, ram, storage, motherboard), route directly to its hw_* handler.
        # Example: "my gpu?" or "procesor?" -> hw_gpu / hw_cpu
        if HAS_AI_LAYER:
            try:
                _entity_intent_map = {
                    "cpu":         "hw_cpu",
                    "gpu":         "hw_gpu",
                    "ram":         "hw_ram",
                    "storage":     "hw_storage",
                    "motherboard": "hw_motherboard",
                }
                # Reuse step-6 parse result to avoid calling the parser twice
                _result_for_entity = _parsed_result or intent_parser.parse(msg)
                if _result_for_entity.entities:
                    for ent_key, ent_intent in _entity_intent_map.items():
                        if ent_key in _result_for_entity.entities:
                            from .intents.parser import ParseResult as _PR2
                            _fake = _PR2(intent=ent_intent, confidence=0.75,
                                         entities=_result_for_entity.entities,
                                         raw_text=msg)
                            _resp = response_builder.build(_fake, lang=lang)
                            if _resp:
                                session_memory.add_message("user", msg)
                                session_memory.push_topic(ent_intent)
                                for line in _resp:
                                    session_memory.add_message("assistant", line)
                                return _resp
            except Exception:
                pass

        # ── 7b. Context carry-over - short vague follow-up reuses last topic ────
        # When the message is very short (≤ 2 tokens) and the last conversation
        # topic is a hardware intent, assume the user is asking about that component.
        # Example: "and?" / "a GPU?" after asking about CPU -> repeat/extend GPU info
        if HAS_AI_LAYER:
            try:
                last_topic = session_memory.current_topic()
                _hw_topics = {"hw_cpu", "hw_gpu", "hw_ram", "hw_storage",
                              "hw_motherboard", "hw_all", "health_check",
                              "temperature", "performance"}
                _short_followup_words = frozenset({
                    "a", "i", "to", "no", "ok", "and", "also", "more",
                    "what", "jak", "jaki", "jaka", "dalej", "jeszcze",
                })
                msg_tokens = [t for t in lower.split() if t not in _short_followup_words]
                if (last_topic in _hw_topics
                        and len(msg_tokens) <= 2
                        and not any(kw in lower for kw in _LEGACY_ONLY_KEYWORDS)):
                    from .intents.parser import ParseResult as _PR3
                    _ctx_fake = _PR3(intent=last_topic, confidence=0.65, raw_text=msg)
                    _ctx_resp = response_builder.build(_ctx_fake, lang=lang)
                    if _ctx_resp:
                        session_memory.add_message("user", msg)
                        session_memory.push_topic(last_topic)
                        for line in _ctx_resp:
                            session_memory.add_message("assistant", line)
                        return _ctx_resp
            except Exception:
                pass

        # ── 8. Legacy keyword routes (habits/insights/teaser) ─────────────────
        for keywords, handler in _ROUTES:
            if any(kw in lower for kw in keywords):
                return getattr(self, handler)()

        # ── 9. Legacy habits (stats keyword) ──────────────────────────────────
        if any(kw in lower for kw in (
            "habits", "top apps", "usage", "co uzywam",
            "nawyki", "summary", "podsumowanie"
        )):
            return self._cmd_habits()

        return self._default_response(msg)

    # ── Insights commands ─────────────────────────────────────────────

    def _cmd_habits(self) -> list[str]:
        return self.insights.get_habit_summary() if self.insights else _NO_INSIGHTS

    def _cmd_anomalies(self) -> list[str]:
        return self.insights.get_anomaly_report() if self.insights else _NO_INSIGHTS

    def _cmd_insights(self) -> list[str]:
        if not self.insights:
            return _NO_INSIGHTS
        msg = self.insights.get_current_insight()
        return [msg] if msg else ["hck_GPT: All quiet right now. No anomalies, no heavy loads."]

    def _cmd_teaser(self) -> list[str]:
        return self.insights.get_teaser() if self.insights else _NO_INSIGHTS

    def _cmd_health(self) -> list[str]:
        return self.insights.get_health_check() if self.insights else _NO_INSIGHTS

    def _cmd_service_setup(self) -> list[str]:
        return self.wizard.start()

    def _insights_report_text(self) -> list[str]:
        lines = (self.insights.get_health_check() if self.insights
                 else list(_NO_INSIGHTS))
        lines += ["", "Click the Today Report button above for the full visual report."]
        return lines

    # ── Service commands ──────────────────────────────────────────────

    def _restore_services(self) -> list[str]:
        msgs = ["━" * 28, "Restoring Services...", "━" * 28, ""]
        summary = self.services_manager.get_disabled_services_summary()

        if summary["count"] == 0:
            return msgs + [
                "No services to restore.",
                "All services are currently enabled.",
                "",
                "Type 'service setup' to optimize your PC",
            ]

        msgs += [f"Restoring {summary['count']} services...", ""]
        results = self.services_manager.restore_all_services()
        ok = sum(1 for _, s, _ in results if s)
        fail = len(results) - ok

        for service, success, _ in results:
            msgs.append(f"{'Restored' if success else 'Failed'}: {service}")

        msgs += ["", "━" * 28, f"Restore Complete!  {ok} restored"]
        if fail:
            msgs.append(f"   {fail} failed (may need admin rights)")
        return msgs

    def _show_service_status(self) -> list[str]:
        msgs = ["━" * 28, "Service Status", "━" * 28, ""]
        summary = self.services_manager.get_disabled_services_summary()
        msgs += [f"Disabled: {summary['count']}", f"Modified: {summary['timestamp']}", ""]

        if summary["count"] > 0:
            msgs.append("Currently disabled:")
            for svc in summary["services"]:
                label = svc
                for _, info in self.services_manager.SERVICES.items():
                    if svc in info["services"]:
                        label = f"{svc} ({info['display']})"
                        break
                msgs.append(f"  • {label}")
        else:
            msgs.append("No services are currently disabled")

        msgs += ["", "━" * 28,
                 "Commands:",
                 "  • 'restore services'  - re-enable all",
                 "  • 'service setup'     - run again"]
        return msgs

    def _show_help(self, lang: str = "pl") -> list[str]:
        bar = "━" * 38
        if lang == "en":
            return [
                bar,
                "◈ hck_GPT - Commands & Capabilities",
                bar,
                "",
                "◈ Hardware  - just type one word or ask naturally",
                "  cpu · ram · gpu · mb · disk · storage · specs",
                "  'what CPU do I have'    'how much RAM'",
                "  'what motherboard'      'disk space free'",
                "",
                "◈ Diagnostics  - system health & performance",
                "  health · temp · perf · throttle",
                "  'health check'          'is CPU throttling'",
                "  'temperatures'          'top processes'",
                "",
                "◈ Statistics & Insights",
                "  stats · insights · alerts · teaser · report",
                "  uptime · optimization · power",
                "",
                "◈ Time-Travel Diagnostics  - compare NOW vs history",
                "  'is my pc hotter than usual lately'  <- temp_comparison",
                "  'why are fps worse than last month'  <- fps_degradation",
                "  'what changed since yesterday'       <- pc_changes",
                "  'what was happening before the freeze' <- crash_context",
                "  'why did this app start behaving differently' <- app_behavior_change",
                "",
                "◈ Identity & Security",
                "  'is conhost.exe a windows process'  <- process_identity",
                "  'virus check'  ·  'suspicious processes'",
                "  'driver status'  ·  'which drivers are installed'",
                "",
                "◈ Gaming & Requirements",
                "  'can my pc run Cyberpunk'       <- game_can_run (with verdict + settings)",
                "  'how much ram do i use when gaming'  <- gaming_ram_usage",
                "  'which game stresses hardware most'  <- game_hardware_stress",
                "",
                "◈ Usage & Habits",
                "  'which apps haven't been opened in a month'  <- stale_apps",
                "  'gaming vs work time'   <- time breakdown",
                "  'what slows down startup'  <- startup_slowdown",
                "  'how much ram do i use daily'  <- daily_ram_usage",
                "  'which process uses the most ram/disk'  <- top_resource_hog",
                "",
                "◈ Battery & Upgrades",
                "  'how long will battery last while writing'  <- battery_estimate",
                "  'can i add more ram to this laptop'  <- upgrade_feasibility",
                "  'battery drain during gaming'  ·  'power since restart'",
                "",
                "◈ Services",
                "  'service setup'    - optimization wizard",
                "  'service status'   - check service state",
                "  'restore services' - re-enable all services",
                "",
                "◈ Database",
                "  reset  - clear knowledge base (confirms first)",
                "  wipe db  - full data wipe",
                "",
                bar,
            ]
        # Polish
        return [
            bar,
            "◈ hck_GPT - Komendy i możliwości",
            bar,
            "",
            "◈ Sprzęt  - wpisz słowo lub zapytaj naturalnie",
            "  cpu · ram · gpu · mb · dysk · specs · storage",
            "  'jaki mam procesor'     'ile mam RAM'",
            "  'jaka płyta główna'     'ile miejsca na dysku'",
            "",
            "◈ Diagnostyka  - zdrowie i wydajność",
            "  health · temp · perf · throttle",
            "  'czy komputer jest zdrowy'   'czy CPU throttluje'",
            "  'jakie temperatury'          'top procesy'",
            "",
            "◈ Statystyki i wgląd",
            "  stats · insights · alerts · teaser · report",
            "  uptime · optimization · zasilanie",
            "",
            "◈ Time-Travel Diagnostyka  - teraz vs historia",
            "  'czy komputer jest ostatnio goręcej niż zwykle'  <- temp_comparison",
            "  'dlaczego fps gorsze niż miesiąc temu'          <- fps_degradation",
            "  'co się zmieniło od wczoraj'                    <- pc_changes",
            "  'co się działo przed ostatnim freezem'          <- crash_context",
            "  'dlaczego ta aplikacja działa inaczej'          <- app_behavior_change",
            "",
            "◈ Identyfikacja i bezpieczeństwo",
            "  'czy conhost.exe to część windows'  <- process_identity",
            "  'sprawdź wirusy'  ·  'podejrzane procesy'",
            "  'sterowniki'  ·  'jakie mam sterowniki'",
            "",
            "◈ Gry i wymagania sprzętowe",
            "  'czy mój pc odpali Cyberpunk'   <- game_can_run (z werdyktem i ustawieniami)",
            "  'ile ram używam kiedy gram'      <- gaming_ram_usage",
            "  'która gra obciąża hardware'    <- game_hardware_stress",
            "",
            "◈ Nawyki i użytkowanie",
            "  'które apki nie były otwierane od miesiąca'  <- stale_apps",
            "  'ile czasu na grach vs praca'  <- gaming_vs_work_time",
            "  'co zwalnia uruchamianie'       <- startup_slowdown",
            "  'ile ramu używam na codzień'    <- daily_ram_usage",
            "  'co zjada mi ram/dysk'          <- top_resource_hog",
            "",
            "◈ Bateria i rozbudowa",
            "  'jak długo wytrzyma bateria przy pisaniu projektu'  <- battery_estimate",
            "  'czy mogę dołożyć RAM do tego laptopa'              <- upgrade_feasibility",
            "  'bateria podczas grania'  ·  'prąd od restartu'",
            "",
            "◈ Serwisy",
            "  'service setup'     - kreator optymalizacji",
            "  'service status'    - stan serwisów",
            "  'restore services'  - przywróć wszystkie",
            "",
            "◈ Baza danych",
            "  reset  - wyczyść bazę wiedzy (pyta o potwierdzenie)",
            "  wipe db  - pełne czyszczenie danych",
            "",
            bar,
        ]

    # ── Reset flow ────────────────────────────────────────────────────────────

    def _cmd_reset_confirm(self) -> list[str]:
        """First step: show confirmation prompt and set pending flag."""
        self._pending_reset = True
        bar = "━" * 34
        return [
            bar,
            "hck_GPT: ⚠ Reset bazy danych",
            bar,
            "",
            "Zostanie usunięte:",
            "  • Profil sprzętu  (CPU, GPU, RAM, płyta główna)",
            "  • Fakty i notatki o komputerze",
            "  • Historia rozmów (log)",
            "  • Wzorce użytkowania",
            "",
            "Pamięć sesji (RAM) zostaje - zniknie po restarcie.",
            "",
            "Wpisz  tak / yes  aby potwierdzić.",
            "Wpisz cokolwiek innego aby anulować.",
            "",
            bar,
        ]

    def _handle_reset_confirm(self, lower: str) -> list[str]:
        """Second step: execute or cancel based on user reply."""
        if lower.strip() in ("tak", "yes", "potwierdz", "potwierdź",
                              "confirm", "ok", "y", "yep"):
            return self._execute_reset()
        self._pending_reset = False
        lang = self._last_lang
        if lang == "en":
            return ["hck_GPT: Cancelled - database was not reset."]
        return ["hck_GPT: Anulowano - baza danych nie została zresetowana."]

    def _execute_reset(self) -> list[str]:
        """Wipe all tables in user_knowledge + clear in-RAM session state."""
        self._pending_reset = False
        bar = "━" * 34
        try:
            from .memory.user_knowledge import user_knowledge as _uk
            from .memory.session_memory  import session_memory as _sm
            _uk.reset_all()
            # Clear in-RAM session data too
            _sm._messages.clear()
            _sm._events.clear()
            _sm._topic_stack.clear()
            _sm._cpu_trend.clear()
            _sm._ram_trend.clear()
            _sm.conversation_summary    = ""
            _sm.greeted_this_session    = False
            _sm.hardware_scanned        = False
            # Restart background hardware scan so DB repopulates
            self._trigger_hw_scan()
            return [
                bar,
                "hck_GPT: ✓ Baza danych wyczyszczona.",
                bar,
                "",
                "Usunięto: profil sprzętu, fakty, historia rozmów.",
                "Pamięć sesji: wyczyszczona.",
                "",
                "Skanowanie sprzętu uruchomi się automatycznie.",
                "Wpisz 'specs' za chwilę aby zweryfikować.",
            ]
        except Exception as exc:
            return [
                f"hck_GPT: ⚠ Błąd podczas resetowania: {exc}",
                "  Spróbuj ponownie lub sprawdź uprawnienia do AppData.",
            ]

    def _default_response(self, msg: str) -> list[str]:
        import re
        lang  = self._last_lang
        lower = msg.lower().strip()

        # ── Smart proactive follow-up detection ───────────────────────────────
        # Catch patterns like "what 3/7", "what does 3/7 mean", "explain that",
        # "co to znaczy", etc. when there's a recent proactive message stored.
        _PROACTIVE_RE = re.compile(
            r'\d+/7'                        # "3/7", "5/7" etc.
            r'|explain|clarify|what.*mean'
            r'|that message|that alert|that notif'
            r'|co to znacz|wyjaśnij|wytłumacz|o co chodzi|co miałeś'
            r'|co znaczy|co oznacza|co chciałeś',
            re.I
        )
        if _PROACTIVE_RE.search(lower) and HAS_AI_LAYER:
            try:
                from .memory.session_memory import session_memory as _sm
                if _sm.get_last_proactive():
                    from .intents.parser import ParseResult as _PR4
                    _fake_ep = _PR4(intent="explain_proactive",
                                    confidence=0.90, raw_text=msg)
                    _ep_resp = response_builder.build(_fake_ep, lang=lang)
                    if _ep_resp:
                        session_memory.add_message("user", msg)
                        session_memory.push_topic("explain_proactive")
                        for line in _ep_resp:
                            session_memory.add_message("assistant", line)
                        return _ep_resp
            except Exception:
                pass

        # ── Try the hybrid engine one more time with lower confidence bar ───────
        if HAS_AI_LAYER and HAS_HYBRID:
            try:
                _late_result = intent_parser.parse(msg)
                if _late_result.confidence >= 0.18:   # lower floor than normal 0.20
                    _late_resp = hybrid_engine.process(msg, _late_result, lang=lang)
                    if _late_resp:
                        session_memory.add_message("user", msg)
                        for line in _late_resp:
                            session_memory.add_message("assistant", line)
                        return _late_resp
            except Exception:
                pass

        # ── .exe process name detection ───────────────────────────────────────
        if lower.endswith(".exe") or (".exe" in lower and len(lower) < 40):
            if HAS_AI_LAYER:
                try:
                    from .intents.parser import ParseResult as _PR5
                    _fake_proc = _PR5(intent="process_identity", confidence=0.85,
                                      raw_text=msg,
                                      entities={"process": lower.split()[0]})
                    _proc_resp = response_builder.build(_fake_proc, lang=lang)
                    if _proc_resp:
                        session_memory.add_message("user", msg)
                        for line in _proc_resp:
                            session_memory.add_message("assistant", line)
                        return _proc_resp
                except Exception:
                    pass

        lines: list[str] = []
        if self.insights:
            current = self.insights.get_current_insight()
            if current:
                lines += [current, ""]

        # ── Context-aware "I don't understand" ────────────────────────────────
        last_topic = None
        try:
            if HAS_AI_LAYER:
                last_topic = session_memory.current_topic()
        except Exception:
            pass

        import random as _rnd
        if lang == "en":
            _fallbacks_en = [
                "hck_GPT: Hmm, not sure what you mean. Try 'help' for all commands.",
                "hck_GPT: Can't match that to a known query. Type 'help' or try 'health'.",
                "hck_GPT: I don't follow. Try rephrasing - or type 'help' for ideas.",
                "hck_GPT: Didn't catch that one. 'specs', 'health' or 'help' might be what you need.",
            ]
            lines.append(_rnd.choice(_fallbacks_en))
            if last_topic and last_topic not in ("unknown", "small_talk"):
                lines.append(f"  (You were just asking about: {last_topic.replace('_', ' ')})")
            lines.append("  Try: 'specs' · 'health' · 'temps' · 'top' · 'help'")
        else:
            _fallbacks_pl = [
                "hck_GPT: Hmm, nie zrozumiałem. Wpisz 'help' żeby zobaczyć co potrafię.",
                "hck_GPT: Nie trafiłem w żaden znany wzorzec. Spróbuj inaczej lub wpisz 'help'.",
                "hck_GPT: Nie łapię o co chodzi - może inaczej? Albo wpisz 'pomoc' po listę komend.",
                "hck_GPT: Nie rozpoznałem zapytania. Wpisz 'specyfikacja', 'zdrowie', lub 'help'.",
            ]
            lines.append(_rnd.choice(_fallbacks_pl))
            if last_topic and last_topic not in ("unknown", "small_talk"):
                topic_clean = last_topic.replace("_", " ").replace("hw ", "")
                lines.append(f"  (Ostatnio pytałeś o: {topic_clean})")
            lines.append("  Spróbuj: 'specs' · 'zdrowie' · 'temp' · 'top' · 'help'")
        return lines

    # ── New conversation flow handlers ────────────────────────────────────────

    def _handle_greeting(self, lang: str) -> list[str]:
        """Warm, live-data-enriched greeting response."""
        import random as _rnd
        try:
            import psutil as _ps
            cpu = _ps.cpu_percent(interval=None)
            ram = _ps.virtual_memory().percent
            stat = ""
            if cpu > 80 or ram > 85:
                stat = (_t_handler(lang,
                    f"  ⚠ CPU {cpu:.0f}%, RAM {ram:.0f}% - trochę zajęty teraz.",
                    f"  ⚠ CPU {cpu:.0f}%, RAM {ram:.0f}% - kinda busy right now."))
            elif cpu > 50 or ram > 65:
                stat = (_t_handler(lang,
                    f"  CPU {cpu:.0f}%, RAM {ram:.0f}% - normalna aktywność.",
                    f"  CPU {cpu:.0f}%, RAM {ram:.0f}% - normal activity."))
            else:
                stat = (_t_handler(lang,
                    f"  CPU {cpu:.0f}%, RAM {ram:.0f}% - system spokojny.",
                    f"  CPU {cpu:.0f}%, RAM {ram:.0f}% - system calm."))
        except Exception:
            stat = ""

        greetings_pl = [
            "hck_GPT: Hej! Wszystko monitoruję. Co chcesz sprawdzić?",
            "hck_GPT: Cześć! Gotowy do pracy. Zapytaj o sprzęt, temperatury albo statystyki.",
            "hck_GPT: Hejka! Jestem tu. Wpisz 'help' jeśli nie wiesz od czego zacząć.",
            "hck_GPT: Witaj! Monitoruję Twój PC od startu. Co Cię interesuje?",
            "hck_GPT: Siema! Czekam na komendy. CPU · RAM · GPU · temps · health - do wyboru.",
        ]
        greetings_en = [
            "hck_GPT: Hey! Monitoring everything. What do you want to check?",
            "hck_GPT: Hi there! Ready. Ask about hardware, temperatures, or stats.",
            "hck_GPT: Hello! Type 'help' if you're not sure where to start.",
            "hck_GPT: Welcome! Watching your PC since startup. What are you curious about?",
            "hck_GPT: Hey! Waiting for commands. CPU · RAM · GPU · temps · health - pick one.",
        ]
        pool = greetings_en if lang == "en" else greetings_pl
        reply = _rnd.choice(pool)
        return [reply, stat] if stat else [reply]

    def _handle_thanks(self, lang: str) -> list[str]:
        """Friendly acknowledgment of thanks - keeps the conversation warm."""
        import random as _rnd
        replies_pl = [
            "hck_GPT: Spoko! Zawsze tu jestem. Wpisz 'help' kiedy będziesz potrzebował.",
            "hck_GPT: Nie ma za co. Pilnuję systemu w tle - pytaj kiedy chcesz.",
            "hck_GPT: Zawsze do usług. Wróć jak będziesz potrzebował czegoś sprawdzić.",
            "hck_GPT: Spoko! Monitoruję dalej. Daj znać jak coś się zmieni.",
        ]
        replies_en = [
            "hck_GPT: Sure! Always here. Type 'help' whenever you need.",
            "hck_GPT: No problem. Monitoring in the background - just ask anytime.",
            "hck_GPT: Anytime. Come back whenever you need something checked.",
            "hck_GPT: All good! Still monitoring. Let me know if anything changes.",
        ]
        pool = replies_en if lang == "en" else replies_pl
        return [_rnd.choice(pool)]

    def _handle_more(self, lang: str) -> "list[str] | None":
        """Expand on the last topic - re-run the last intent response."""
        if not HAS_AI_LAYER:
            return None
        try:
            last_topic = session_memory.current_topic()
            if not last_topic or last_topic in ("unknown", "small_talk", "help"):
                return None
            from .intents.parser import ParseResult as _PR6
            _more_fake = _PR6(intent=last_topic, confidence=0.80, raw_text="more")
            _more_resp = response_builder.build(_more_fake, lang=lang)
            if _more_resp:
                prefix = ("hck_GPT: Oto więcej o poprzednim temacie:"
                          if lang == "pl" else
                          "hck_GPT: More on the previous topic:")
                session_memory.add_message("user", "więcej" if lang == "pl" else "more")
                for line in _more_resp:
                    session_memory.add_message("assistant", line)
                return [prefix, ""] + _more_resp
        except Exception:
            pass
        return None

    def _handle_action_request(self, lang: str) -> "list[str] | None":
        """
        Context-aware 'what should I do?' handler.
        Looks at recent session events and conversation topic to give targeted advice.
        """
        if not HAS_AI_LAYER:
            return None
        try:
            last_topic  = session_memory.current_topic() or "unknown"
            recent_evts = session_memory.recent_events_summary(within_minutes=30)

            # Build context-aware response based on what was just discussed
            _TOPIC_ACTION_MAP = {
                "temperature":     "thermal_prediction",
                "throttle_check":  "thermal_prediction",
                "why_slow":        "optimization",
                "ram_why_high":    "swap_analysis",
                "health_check":    "optimization",
                "hw_cpu":          "performance",
                "hw_gpu":          "performance",
                "hw_ram":          "upgrade_feasibility",
                "performance":     "optimization",
                "disk_health":     "fps_degradation",
                "processes":       "unnecessary_programs",
                "virus_check":     "optimization",
            }

            target_intent = _TOPIC_ACTION_MAP.get(last_topic, "optimization")

            # Check for active events that override topic
            if recent_evts:
                if "cpu_temp_crit" in recent_evts or "temp_sustained" in recent_evts:
                    target_intent = "thermal_prediction"
                elif "ram_crit" in recent_evts or "ram_high" in recent_evts:
                    target_intent = "swap_analysis"
                elif "disk_low" in recent_evts or "multi_disk_low" in recent_evts:
                    target_intent = "disk_health"

            from .intents.parser import ParseResult as _PR7
            _action_fake = _PR7(intent=target_intent, confidence=0.80,
                                raw_text="what should I do")
            _action_resp = response_builder.build(_action_fake, lang=lang)
            if _action_resp:
                context_lbl = last_topic.replace("_", " ")
                prefix_pl = f"hck_GPT: Na podstawie ostatniej rozmowy ({context_lbl}):"
                prefix_en = f"hck_GPT: Based on recent context ({context_lbl}):"
                prefix = prefix_pl if lang == "pl" else prefix_en
                session_memory.add_message("user", "co zrobić" if lang == "pl" else "what should I do")
                for line in _action_resp:
                    session_memory.add_message("assistant", line)
                return [prefix, ""] + _action_resp
        except Exception:
            pass
        return None

    def reset(self) -> None:
        self.wizard.reset()
