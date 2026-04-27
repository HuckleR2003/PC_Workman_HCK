# hck_gpt/chat_handler.py
from __future__ import annotations
from .service_setup_wizard import ServiceSetupWizard
from .services_manager import ServicesManager

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
# Exact stripped-lower match → response_builder intent name (bypasses parser).
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
}

# Keywords that show the styled help card (handled directly, not via builder).
_HELP_KEYWORDS = frozenset({
    "komendy", "commands", "help", "pomoc",
    "komendy!", "commands!", "help!", "pomoc!",
    "?",
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

    def _trigger_hw_scan(self) -> None:
        """Run hardware scan in background thread if knowledge DB is stale."""
        import threading
        def _scan():
            try:
                from .context.hardware_scanner import scan_and_store
                scan_and_store()
            except Exception:
                pass
        threading.Thread(target=_scan, daemon=True).start()

    def process_message(self, user_message: str,
                        ui_lang: str = "auto") -> list[str]:
        msg   = user_message.strip()
        lower = msg.lower().strip()

        # ── Language resolution ───────────────────────────────────────────────
        # ui_lang comes from the user's Language popup choice:
        #   "en"   → always English regardless of input language
        #   "pl"   → always Polish regardless of input language
        #   "auto" → detect from message (default behaviour)
        def _resolve_lang(text: str) -> str:
            if ui_lang in ("en", "pl"):
                return ui_lang
            return detect_language(text)

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

        # ── 3. Help card — exact trigger words ────────────────────────────────
        if lower in _HELP_KEYWORDS:
            return self._show_help(ui_lang if ui_lang in ("en", "pl") else self._last_lang)

        # ── 4. Reset command ──────────────────────────────────────────────────
        if lower in _RESET_KEYWORDS:
            return self._cmd_reset_confirm()

        # ── 5. Quick shorthand aliases (single-word bypasses full parser) ─────
        alias_intent = _QUICK_ALIASES.get(lower)
        if alias_intent and HAS_AI_LAYER:
            try:
                lang = _resolve_lang(msg)
                self._last_lang = lang
                if HAS_PROACTIVE:
                    try:
                        proactive_monitor.set_language(lang)
                    except Exception:
                        pass
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
        if HAS_AI_LAYER:
            try:
                lang = _resolve_lang(msg)
                self._last_lang = lang
                if HAS_PROACTIVE:
                    try:
                        proactive_monitor.set_language(lang)
                    except Exception:
                        pass

                result = intent_parser.parse(msg)
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

        # ── 7. Legacy keyword routes (habits/insights/teaser) ─────────────────
        for keywords, handler in _ROUTES:
            if any(kw in lower for kw in keywords):
                return getattr(self, handler)()

        # ── 8. Legacy habits (stats keyword) ──────────────────────────────────
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
                 "  • 'restore services'  — re-enable all",
                 "  • 'service setup'     — run again"]
        return msgs

    def _show_help(self, lang: str = "pl") -> list[str]:
        bar = "━" * 38
        if lang == "en":
            return [
                bar,
                "◈ hck_GPT — Commands & Capabilities",
                bar,
                "",
                "◈ Hardware  — just type one word or ask naturally",
                "  cpu · ram · gpu · mb · disk · storage · specs",
                "  'what CPU do I have'    'how much RAM'",
                "  'what motherboard'      'disk space free'",
                "",
                "◈ Diagnostics  — system health & performance",
                "  health · temp · perf · throttle",
                "  'health check'          'is CPU throttling'",
                "  'temperatures'          'top processes'",
                "",
                "◈ Statistics & Insights",
                "  stats · insights · alerts · teaser · report",
                "  uptime · optimization · power",
                "",
                "◈ Services",
                "  'service setup'    — optimization wizard",
                "  'service status'   — check service state",
                "  'restore services' — re-enable all services",
                "",
                "◈ Database",
                "  reset  — clear knowledge base (confirms first)",
                "  wipe db  — full data wipe",
                "",
                bar,
            ]
        # Polish
        return [
            bar,
            "◈ hck_GPT — Komendy i możliwości",
            bar,
            "",
            "◈ Sprzęt  — wpisz słowo lub zapytaj naturalnie",
            "  cpu · ram · gpu · mb · dysk · specs · storage",
            "  'jaki mam procesor'     'ile mam RAM'",
            "  'jaka płyta główna'     'ile miejsca na dysku'",
            "",
            "◈ Diagnostyka  — zdrowie i wydajność",
            "  health · temp · perf · throttle",
            "  'czy komputer jest zdrowy'   'czy CPU throttluje'",
            "  'jakie temperatury'          'top procesy'",
            "",
            "◈ Statystyki i wgląd",
            "  stats · insights · alerts · teaser · report",
            "  uptime · optimization · zasilanie",
            "",
            "◈ Serwisy",
            "  'service setup'     — kreator optymalizacji",
            "  'service status'    — stan serwisów",
            "  'restore services'  — przywróć wszystkie",
            "",
            "◈ Baza danych",
            "  reset  — wyczyść bazę wiedzy (pyta o potwierdzenie)",
            "  wipe db  — pełne czyszczenie danych",
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
            "Pamięć sesji (RAM) zostaje — zniknie po restarcie.",
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
        return ["hck_GPT: Anulowano — baza danych nie została zresetowana."]

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
        lines: list[str] = []
        if self.insights:
            current = self.insights.get_current_insight()
            if current:
                lines += [current, ""]
        lines += [
            "hck_GPT: Nie rozumiem tego zapytania.",
            "  Spróbuj: 'specyfikacja', 'health', 'stats', 'help'",
            "  lub zapytaj naturalnie: 'jaki mam procesor'",
        ]
        return lines

    def reset(self) -> None:
        self.wizard.reset()
