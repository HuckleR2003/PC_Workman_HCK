"""Conversation Director responses.

These handlers operate on SessionMemory's bounded ConversationFrame. They do
not replace category handlers or guided flows. Their job is to keep a diagnosis
coherent when the user corrects a subject, supplies a short missing detail, or
returns after trying advice.
"""
from __future__ import annotations

import re
import unicodedata

from hck_gpt.responses.common import List, ParseResult, _t


def _fold(text: str) -> str:
    value = "".join(
        char for char in unicodedata.normalize("NFD", (text or "").lower())
        if unicodedata.category(char) != "Mn"
    ).translate(str.maketrans({"ł": "l", "ø": "o", "đ": "d"}))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s.-]", " ", value)).strip()


def _subject(frame: dict, lang: str) -> str:
    value = frame.get("subject_value") or ""
    kind = frame.get("subject_kind") or ""
    if value and value != "game":
        return value
    labels = {
        "component": ("podzespół", "component"),
        "process": ("proces", "process"),
        "part": ("część", "part"),
        "game": ("gra", "game"),
    }
    pl, en = labels.get(kind, ("ten problem", "this issue"))
    return en if lang == "en" else pl


def _outcome(raw: str) -> str:
    text = _fold(raw)
    if any(x in text for x in (
            "jest lepiej", "pomoglo", "dziala lepiej", "it is better",
            "works better", "that helped")):
        return "better"
    if any(x in text for x in (
            "jest gorzej", "pogorszylo", "worse", "got worse")):
        return "worse"
    if any(x in text for x in (
            "bez zmian", "nie pomoglo", "tak samo", "no change",
            "did not help", "same as before")):
        return "same"
    return "done"


def _delta_lines(deltas: dict, lang: str) -> List[str]:
    labels = {
        "cpu_pct": "CPU", "ram_pct": "RAM", "gpu_pct": "GPU",
        "cpu_temp": "CPU temp", "gpu_temp": "GPU temp",
    }
    lines = []
    for key in ("cpu_pct", "ram_pct", "gpu_pct", "cpu_temp", "gpu_temp"):
        if key not in deltas:
            continue
        delta = float(deltas[key])
        unit = "°C" if "temp" in key else " pp"
        direction = (_t(lang, "wyżej", "higher") if delta > 0
                     else _t(lang, "niżej", "lower") if delta < 0
                     else _t(lang, "bez zmiany", "unchanged"))
        lines.append(
            f"  {labels[key]}: {abs(delta):.1f}{unit} {direction}"
            if delta else f"  {labels[key]}: {direction}"
        )
    return lines


def _missing_question(key: str, lang: str, attempt: int = 1) -> str:
    questions = {
        "where_it_happens": (
            "Gdzie dokładnie to występuje: w grze, przeglądarce, przy starcie czy na pulpicie?",
            "Where exactly does it happen: in a game, browser, at startup, or on the desktop?",
        ),
        "when_during_game": (
            "Czy zaczyna się od razu, czy dopiero po kilku lub kilkunastu minutach gry?",
            "Does it start immediately, or only after several minutes of play?",
        ),
        "lag_type": (
            "Czy spadają FPS i obraz przycina, czy raczej rośnie ping i postać przeskakuje?",
            "Do FPS drop and the image stutter, or does ping rise and movement rubber-band?",
        ),
        "target_part": (
            "Jaki dokładny model części bierzesz pod uwagę?",
            "Which exact part model are you considering?",
        ),
        "workload": (
            "Do czego komputer ma służyć najczęściej: gry, praca, montaż czy programowanie?",
            "What is the PC mainly for: gaming, office work, editing, or development?",
        ),
        "budget": (
            "Jaki jest maksymalny budżet i w jakiej walucie?",
            "What is the maximum budget and currency?",
        ),
        "recurrence": (
            "Czy ten problem pojawił się pierwszy raz, czy już wcześniej wracał?",
            "Is this the first occurrence, or has the problem returned before?",
        ),
    }
    pl, en = questions.get(key, (
        "Jaki jeden szczegół zauważyłeś tuż przed problemem?",
        "What one detail did you notice just before the issue?",
    ))
    if attempt > 1:
        retry_questions = {
            "where_it_happens": (
                "Wybierz najbliższe: gra, przeglądarka, start Windows czy sam pulpit?",
                "Pick the closest match: game, browser, Windows startup, or the desktop?",
            ),
            "when_during_game": (
                "Wybierz najbliższe: od razu, po kilku minutach, w połowie czy pod koniec meczu?",
                "Pick the closest match: immediately, after a few minutes, mid-match, or near the end?",
            ),
            "lag_type": (
                "Jedno rozróżnienie: skacze ping lub postać, czy rwie obraz, FPS albo sterowanie?",
                "One distinction: does ping or movement jump, or do the image, FPS, or controls hitch?",
            ),
        }
        pl, en = retry_questions.get(key, (pl, en))
    return en if lang == "en" else pl


class ConversationResponses:
    def _resp_correct_subject(self, r: ParseResult,
                              lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        before = session_memory.frame_snapshot()
        kind, value = session_memory.correct_subject_from_text(r.raw_text)
        if not value:
            return [
                self.PREFIX + _t(
                    lang,
                    " Rozumiem, że poprawiasz temat, ale nie widzę nowego podzespołu, procesu ani części.",
                    " I understand that you are correcting the subject, but I cannot identify the new component, process, or part.",
                ),
                _t(lang, "  Napisz np. „nie GPU, tylko CPU”.",
                         "  Write, for example, 'not the GPU, the CPU'."),
            ]
        old = before.get("subject_value") or _t(lang, "poprzedni temat", "the previous subject")
        return [
            self.PREFIX + _t(lang, " Poprawione.", " Corrected."),
            _t(lang, f"  Było: {old}", f"  Before: {old}"),
            _t(lang, f"  Teraz diagnozuję: {value}", f"  Now diagnosing: {value}"),
            _t(lang, "  Zachowuję cel rozmowy i zebrane fakty, ale nie przenoszę założeń o starym podzespole.",
                     "  I am keeping the goal and confirmed facts, but not assumptions about the old subject."),
        ]

    def _resp_explain_previous_advice(self, r: ParseResult,
                                      lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        frame = session_memory.frame_snapshot()
        if not frame or not frame.get("advice"):
            return [self.PREFIX + _t(
                lang,
                " Nie mam w tej sesji aktywnej porady do wyjaśnienia. Najpierw opisz problem albo wskaż wcześniejszy krok.",
                " I do not have an active piece of advice to explain in this session. Describe the issue or name the earlier step first.",
            )]
        evidence = frame.get("evidence") or {}
        facts = ", ".join(f"{k}={v}" for k, v in list(evidence.items())[:4])
        lines = [
            self.PREFIX + _t(lang, " Poprzednia porada nie była strzałem w ciemno:",
                             " The previous advice was not a blind guess:"),
            f"  {_subject(frame, lang)}: {frame['advice']}",
        ]
        if facts:
            lines.append(_t(lang, f"  Oparłem ją na: {facts}.",
                                  f"  It was based on: {facts}."))
        else:
            lines.append(_t(
                lang,
                "  Oparłem ją na rodzaju objawu, ale brakuje jeszcze pomiaru potwierdzającego przyczynę.",
                "  It was based on the symptom type, but a confirming measurement is still missing.",
            ))
        if frame.get("missing_evidence"):
            lines.append(_t(
                lang,
                "  To nadal hipoteza robocza, bo nie mam jeszcze: " + ", ".join(frame["missing_evidence"][:3]) + ".",
                "  It is still a working hypothesis because I still lack: " + ", ".join(frame["missing_evidence"][:3]) + ".",
            ))
        return lines

    def _resp_verify_after_action(self, r: ParseResult,
                                  lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        frame = session_memory.frame_snapshot()
        if not frame or not frame.get("advice"):
            return [self.PREFIX + _t(
                lang,
                " Nie mam aktywnego kroku do weryfikacji. Powiedz, co zostało zmienione, a zbuduję nowy punkt odniesienia.",
                " I do not have an active step to verify. Tell me what changed and I will establish a new baseline.",
            )]
        result = _outcome(r.raw_text)
        current = session_memory.collect_live_evidence()
        deltas = session_memory.compare_frame_evidence(current)
        if result == "done":
            session_memory.set_advice_state("accepted", "waiting")
            lines = [self.PREFIX + _t(
                lang,
                " Mam ten krok jako wykonany. Nie ogłoszę sukcesu tylko dlatego, że kliknięcie się udało.",
                " I have marked the step as completed. I will not call it a success just because the action ran.",
            )]
            lines.extend(_delta_lines(deltas, lang))
            lines.append(_t(lang, "  Jest odczuwalnie lepiej, bez zmian czy gorzej?",
                                  "  Does it feel better, unchanged, or worse?"))
            return lines

        session_memory.record_verification(result, current)
        heads = {
            "better": ("To ważny sygnał: objaw osłabł.", "That matters: the symptom eased."),
            "same": ("Dobrze, nie będziemy bronić porady, która nie pomogła.",
                     "Good, we will not defend advice that did not help."),
            "worse": ("Cofnij tę zmianę, jeśli jest odwracalna i bezpieczna.",
                      "Revert that change if it is reversible and safe."),
        }
        pl, en = heads[result]
        lines = [self.PREFIX + (en if lang == "en" else pl)]
        lines.extend(_delta_lines(deltas, lang))
        if result == "better":
            lines.append(_t(
                lang,
                "  Zostawmy stan na kilka minut i sprawdźmy, czy poprawa utrzyma się pod tym samym obciążeniem.",
                "  Keep this state for a few minutes and check whether the improvement holds under the same workload.",
            ))
        elif result == "same":
            missing, attempt = session_memory.next_frame_question(mark_asked=True)
            lines.append("  " + _missing_question(
                missing or "next_evidence", lang, attempt,
            ))
        else:
            lines.append(_t(
                lang,
                "  Po cofnięciu porównamy stan ponownie, zanim przejdziemy do innej przyczyny.",
                "  After reverting, we will compare again before testing another cause.",
            ))
        return lines

    def _resp_compare_after_change(self, r: ParseResult,
                                   lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        frame = session_memory.frame_snapshot()
        if not frame or not frame.get("baseline"):
            return [self.PREFIX + _t(
                lang,
                " Nie mam uczciwego pomiaru sprzed zmiany, więc nie wymyślę różnicy. Mogę zapisać stan teraz jako nowy punkt odniesienia.",
                " I do not have an honest pre-change measurement, so I will not invent a difference. I can save the current state as a new baseline.",
            )]
        current = session_memory.collect_live_evidence()
        deltas = session_memory.compare_frame_evidence(current)
        session_memory.record_verification("measured", current)
        lines = [self.PREFIX + _t(
            lang,
            " Porównanie z pomiarem zapisanym przy poprzedniej poradzie:",
            " Comparison with the measurement saved alongside the previous advice:",
        )]
        measured = _delta_lines(deltas, lang)
        if measured:
            lines.extend(measured)
            lines.append(_t(
                lang,
                "  To chwilowy odczyt, nie dowód przyczynowy. Najważniejsze jest porównanie przy podobnym obciążeniu.",
                "  This is an instantaneous reading, not proof of causation. Compare under a similar workload.",
            ))
        else:
            lines.append(_t(
                lang,
                "  Brakuje wspólnych, wiarygodnych metryk przed i po zmianie.",
                "  There are no shared reliable metrics before and after the change.",
            ))
        return lines

    def _resp_continue_diagnosis(self, r: ParseResult,
                                 lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        details = session_memory.conversation_details(r.raw_text)
        frame = session_memory.active_frame()
        if frame is None:
            return [
                self.PREFIX + _t(lang, " Zacznijmy bez zgadywania.", " Let us start without guessing."),
                "  " + _missing_question("where_it_happens", lang),
            ]
        before = session_memory.frame_snapshot()
        if details.get("game"):
            session_memory.set_frame_subject("game", str(details["game"]))
        if details:
            session_memory.record_frame_evidence(details, frame.goal,
                                                 "continue_diagnosis")
        frame_data = session_memory.frame_snapshot()
        evidence = frame_data.get("evidence") or {}
        lines = [self.PREFIX + _t(
            lang,
            " Dopisuję ten szczegół do tej samej diagnozy, nie zaczynam od zera.",
            " I am adding that detail to the same diagnosis, not starting over.",
        )]
        accepted = []
        for key, label in (
            ("context", _t(lang, "miejsce", "context")),
            ("game", _t(lang, "gra", "game")),
            ("timing", _t(lang, "moment", "timing")),
            ("lag_kind", _t(lang, "rodzaj", "type")),
            ("recurrence", _t(lang, "powtarzalność", "recurrence")),
            ("frequency", _t(lang, "częstotliwość", "frequency")),
            ("scope", _t(lang, "zakres", "scope")),
            ("trigger", _t(lang, "punkt startowy", "trigger")),
        ):
            if key in details:
                accepted.append(f"{label}={details[key]}")
        if accepted:
            lines.append("  " + ", ".join(accepted))

        previous_evidence = before.get("evidence") or {}
        revised = [
            key for key, value in details.items()
            if key in previous_evidence and previous_evidence[key] != value
        ]
        if revised:
            changes = ", ".join(
                f"{key}: {previous_evidence[key]} -> {details[key]}"
                for key in revised[:3]
            )
            lines.append(_t(
                lang,
                f"  Aktualizuję wcześniejsze ustalenie: {changes}.",
                f"  I am revising the earlier detail: {changes}.",
            ))

        missing = frame_data.get("missing_evidence") or []
        if missing:
            question, attempt = session_memory.next_frame_question(
                mark_asked=True,
            )
            lines.append("  " + _missing_question(
                question or missing[0], lang, attempt,
            ))
        elif evidence.get("context") == "gaming":
            lines.append(_t(
                lang,
                "  Mamy już miejsce, moment i typ problemu. Następny krok: odtwórz go w tej samej grze i sprawdź [-> My PC], wtedy zestawię CPU, RAM, GPU i temperatury.",
                "  We now have the context, timing, and issue type. Next, reproduce it in the same game and check [-> My PC], then I can line up CPU, RAM, GPU, and temperatures.",
            ))
        else:
            lines.append(_t(
                lang,
                "  Kontekst jest wystarczający do kolejnego pomiaru. Powtórz objaw, a potem napisz „sprawdź ponownie”.",
                "  The context is sufficient for the next measurement. Reproduce the issue, then say 'check again'.",
            ))
        return lines

    def _resp_decline_advice(self, r: ParseResult,
                             lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        if not session_memory.set_advice_state("declined", "none"):
            return [self.PREFIX + _t(lang, " Jasne. Nie mam teraz aktywnej operacji do pominięcia.",
                                           " Understood. There is no active operation to skip." )]
        return [
            self.PREFIX + _t(lang, " Jasne, odkładamy ten krok. Nie wykonam go ani nie będę naciskał.",
                             " Understood, we are leaving that step alone. I will not run it or push it."),
            _t(lang, "  Zachowuję samą diagnozę. Możemy szukać wariantu tylko obserwacyjnego albo całkowicie odwracalnego.",
                     "  I am keeping the diagnosis. We can look for an observation-only or fully reversible alternative."),
        ]

    def _resp_explain_confidence(self, r: ParseResult,
                                 lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        frame = session_memory.frame_snapshot()
        if not frame:
            return [self.PREFIX + _t(
                lang,
                " Nie mam aktywnej diagnozy, więc nie podam sztucznego procentu pewności.",
                " There is no active diagnosis, so I will not give you a made-up confidence percentage.",
            )]
        confidence = float(frame.get("confidence") or 0)
        evidence = frame.get("evidence") or {}
        missing = frame.get("missing_evidence") or []
        if confidence >= 0.9 and evidence and not missing:
            level = _t(lang, "wysoka", "high")
        elif confidence >= 0.65 and (evidence or not missing):
            level = _t(lang, "umiarkowana", "moderate")
        else:
            level = _t(lang, "wstępna", "preliminary")
        lines = [
            self.PREFIX + _t(lang, f" Pewność diagnozy: {level}.",
                             f" Diagnostic confidence: {level}."),
            _t(lang,
               "  Pewność routingu pytania nie jest tym samym co pewność przyczyny problemu.",
               "  Confidence in understanding the question is not confidence in the root cause."),
        ]
        if evidence:
            lines.append(_t(lang, f"  Potwierdzone w rozmowie: {len(evidence)} fakt(y).",
                                  f"  Confirmed in the conversation: {len(evidence)} fact(s)."))
        if missing:
            lines.append(_t(lang, "  Brakuje: " + ", ".join(missing[:3]) + ".",
                                  "  Missing: " + ", ".join(missing[:3]) + "."))
        return lines

    def _resp_compat_missing_details(self, r: ParseResult,
                                     lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        frame = session_memory.ensure_frame("upgrade", "compat_missing_details")
        snap = session_memory.frame_snapshot()
        known = []
        try:
            from core import hardware_compat as hc
            platform = hc.current_platform()
            for key in ("board", "socket", "chipset", "ram_actual"):
                if platform.get(key):
                    known.append(f"{key}={platform[key]}")
        except Exception:
            platform = {}
        if snap.get("subject_value"):
            known.append(_t(lang, "część=", "part=") + snap["subject_value"])
        missing = list(snap.get("missing_evidence") or [])
        if not platform.get("board"):
            missing.insert(0, "motherboard")
        lines = [self.PREFIX + _t(
            lang,
            " Sprawdzę kompatybilność tylko z danych, które naprawdę znam.",
            " I will check compatibility only from data I actually know.",
        )]
        if known:
            lines.append(_t(lang, "  Już mam: ", "  Already known: ") + ", ".join(known))
        if missing:
            lines.append(_t(lang, "  Nadal potrzebuję: ", "  Still needed: ")
                         + ", ".join(dict.fromkeys(missing)))
        lines.append(_t(
            lang,
            "  Przy karcie graficznej dodatkowo potwierdź model zasilacza i miejsce w obudowie. Tych danych Windows zwykle nie wykrywa.",
            "  For a graphics card, also confirm the PSU model and case clearance. Windows usually cannot detect those facts.",
        ))
        return lines

    def _resp_upgrade_budget(self, r: ParseResult,
                             lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        details = session_memory.conversation_details(r.raw_text)
        budget = details.get("budget")
        if not budget:
            session_memory.ensure_frame("upgrade", "upgrade_budget")
            return [
                self.PREFIX + _t(lang, " Uwzględnię budżet bez naciągania go pod droższe części.",
                                 " I will respect the budget instead of stretching it toward pricier parts."),
                "  " + _missing_question("budget", lang),
            ]
        session_memory.record_frame_evidence(
            {"budget": budget}, "upgrade", "upgrade_budget")
        return [
            self.PREFIX + _t(lang, f" Zapisuję budżet tej rozmowy: {budget}.",
                             f" Budget saved for this conversation: {budget}."),
            _t(lang,
               "  Będę liczył cały koszt zmiany platformy, nie tylko cenę jednego podzespołu.",
               "  I will account for the full platform-change cost, not only one component."),
        ]

    def _resp_upgrade_workload(self, r: ParseResult,
                               lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        details = session_memory.conversation_details(r.raw_text)
        workload = details.get("workload")
        if not workload:
            session_memory.ensure_frame("upgrade", "upgrade_workload")
            return [self.PREFIX + " " + _missing_question("workload", lang)]
        session_memory.record_frame_evidence(
            {"workload": workload}, "upgrade", "upgrade_workload")
        return [
            self.PREFIX + _t(lang, f" Priorytet modernizacji: {workload}.",
                             f" Upgrade priority: {workload}."),
            _t(lang,
               "  To zmienia kolejność zakupów. Wniosek oprę jeszcze na obecnym sprzęcie, historii obciążenia i budżecie.",
               "  That changes the purchase order. I will also use the current hardware, workload history, and budget."),
        ]

    def _resp_desktop_recurrence(self, r: ParseResult,
                                 lang: str = "pl") -> List[str]:
        from hck_gpt.memory.session_memory import session_memory
        frame = session_memory.record_frame_evidence(
            {"recurrence": "recurring"}, "repair_desktop",
            "desktop_recurrence")
        frame.symptom = "desktop_recurrent"
        return [
            self.PREFIX + _t(
                lang,
                " Skoro problem z pulpitem wraca, nie traktuję go już jako jednorazowego zawieszenia Explorer.exe.",
                " Because the desktop issue returned, I am no longer treating it as a one-off Explorer.exe hang.",
            ),
            _t(
                lang,
                "  Najpierw zbierzemy dowód: Explorer/DWM, moment zaniku ikon lub paska oraz zdarzenia sprzed awarii. Nie restartuję niczego automatycznie.",
                "  First we will gather evidence: Explorer/DWM state, when the icons or taskbar vanished, and events before the failure. Nothing is restarted automatically.",
            ),
            _t(lang, "  Uruchom bezpieczny odczyt: [-> Stability Tests]",
                     "  Run the safe read-only check: [-> Stability Tests]"),
            _t(lang,
               "  Co znika jako pierwsze: ikony, pasek zadań czy cały obraz poza kursorem?",
               "  What disappears first: icons, the taskbar, or everything except the cursor?"),
        ]


__all__ = ["ConversationResponses"]
