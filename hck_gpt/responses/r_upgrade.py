"""hck_gpt.responses.r_upgrade - UpgradeResponses mixin (Upgrade Readiness).

Answers "will THIS part fit my machine" from the offline library in
core/hardware_compat.py (320 entries: CPUs, GPUs, chipsets, sockets).
upgrade_advice (r_hardware) answers the different question "WHAT should I
upgrade" from usage history. Composed into ResponseBuilder via MRO.
"""
from hck_gpt.responses.common import (  # shared helpers/data
    List,
    ParseResult,
    _t,
)


class UpgradeResponses:
    # ── Upgrade Readiness (core/hardware_compat) ──────────────────────────────
    # upgrade_advice answers "WHAT should I upgrade" from usage history;
    # these two answer "will THIS part fit" from the offline library.

    _UR_HEADS = {
        "compatible":         ("Pasuje od ręki", "Drops straight in"),
        "bios_update":        ("Pasuje po aktualizacji BIOS", "Fits after a BIOS update"),
        "vendor_dependent":   ("Zależy od producenta płyty", "Board-vendor dependent"),
        "check_support_list": ("Raczej pasuje - potwierdź listę wsparcia", "Likely fine - verify the support list"),
        "chipset_blocked":    ("Ten sam socket, ale chipset blokuje", "Same socket, blocked by chipset"),
        "needs_new_board":    ("Inny socket - potrzebna nowa płyta", "Different socket - new motherboard required"),
        "incompatible":       ("Niekompatybilne", "Incompatible"),
        "downgrade":          ("Zadziała, ale to downgrade", "Works, but it's a downgrade"),
        "info":               ("typ pamięci Twojej platformy", "your platform's memory type"),
        "unknown_part":       ("Nie mam tej części w bibliotece", "Not in my library yet"),
        "unknown_current":    ("Nie znam jeszcze Twojej płyty", "Your platform isn't identified yet"),
    }

    _UR_GPU_NOTES_PL = {
        "gtx 1060": "Dane dla wersji 6 GB (3 GB jest przycięta).",
        "rx 6500 xt": "Działa na PCIe x4 - na płycie z PCIe 3.0 zauważalnie traci.",
        "rtx 4080": "Złącze 16-pin 12VHPWR (adapter w zestawie, lepszy natywny kabel ATX 3.x).",
        "rtx 4080 super": "Złącze 16-pin 12VHPWR (adapter w zestawie, lepszy natywny kabel ATX 3.x).",
        "rtx 4090": "Złącze 16-pin 12VHPWR - w praktyce potrzebny nowoczesny zasilacz ATX 3.x.",
        "rtx 5080": "Złącze 12V-2x6 - w praktyce potrzebny nowoczesny zasilacz ATX 3.x.",
        "rtx 5090": "Złącze 12V-2x6 i 575 W samej karty - realnie wymagany zasilacz ATX 3.1.",
    }

    def _ur_head(self, verdict: str, lang: str) -> str:
        pl, en = self._UR_HEADS.get(verdict, ("Wynik", "Result"))
        return pl if lang == "pl" else en

    def _resp_upgrade_compat(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'Czy i5 11400F wejdzie na moją płytę?' - socket/chipset verdict for
        a concrete part named in the message, from the offline library."""
        P = self.PREFIX
        from core import hardware_compat as hc
        kind, _rec = hc.identify_part(r.raw_text)

        if kind is None:
            # RAM question without a concrete kit ("jaki ram pasuje do mojej
            # plyty") - the RAM handler answers with the platform's DDR facts.
            low = (r.raw_text or "").lower()
            if any(w in low for w in ("ram", "pami", "memory", "ddr")):
                return self._resp_ram_compat(r, lang)
            # No concrete part in the message: explain + contextual picks.
            plat = hc.current_platform()
            sug = hc.suggest_upgrades(plat)
            lines = [_t(lang,
                f"{P} Sprawdzę każdą część pod Twój zestaw ({hc.platform_label(plat)}).",
                f"{P} I can check any part against your build ({hc.platform_label(plat)}).")]
            lines.append(_t(lang,
                "  Podaj konkretny model, np. 'czy i5 11400F będzie pasować',",
                "  Name a concrete model, e.g. 'will an i5 11400F fit',"))
            lines.append(_t(lang,
                "  'wymiana karty na RTX 4070' albo 'czy DDR5 6000 zadziała'.",
                "  'swap my GPU for an RTX 4070' or 'will DDR5 6000 work'."))
            picks = [x["label"] for x in sug.get("cpu", [])[:2]]
            picks += [x["label"] for x in sug.get("gpu", [])[:2]]
            if picks:
                lines.append("")
                lines.append(_t(lang, "  Sensowne kierunki dla Twojej platformy:",
                                      "  Sensible directions for your platform:"))
                for p_lbl in picks:
                    lines.append(f"    - {p_lbl}")
            lines.append("")
            lines.append(_t(lang,
                "  Pełny sprawdzacz z podpowiedziami: [-> Upgrade Readiness]",
                "  The full checker with suggestions: [-> Upgrade Readiness]"))
            return lines

        if kind == "ram":
            return self._resp_ram_compat(r, lang)

        v = (hc.check_cpu_upgrade(r.raw_text) if kind == "cpu"
             else hc.check_gpu_upgrade(r.raw_text))
        return (self._ur_cpu_lines(v, lang) if kind == "cpu"
                else self._ur_gpu_lines(v, lang))

    def _ur_cpu_lines(self, v: dict, lang: str) -> List[str]:
        P = self.PREFIX
        from core.hardware_compat_db import SOCKETS
        tgt, plat = v.get("target"), v.get("current") or {}
        verdict = v.get("verdict", "")
        name = tgt["label"] if tgt else (v.get("target_text") or "").strip()
        lines = [f"{P} {name} - {self._ur_head(verdict, lang)}"]

        if verdict == "unknown_part":
            from core.hardware_compat import db_stats
            n = db_stats()["cpus"]
            lines.append(_t(lang,
                f"  Biblioteka offline obejmuje {n} desktopowych CPU (Intel 4. gen -> Core Ultra, AMD FX -> Ryzen 9000).",
                f"  The offline library covers {n} desktop CPUs (Intel 4th gen -> Core Ultra, AMD FX -> Ryzen 9000)."))
            lines.append(_t(lang,
                "  Podaj pełniejszą nazwę albo sprawdź na stronie: [-> Upgrade Readiness]",
                "  Try a fuller name, or use the page: [-> Upgrade Readiness]"))
            return lines
        if verdict == "unknown_current":
            lines.append(_t(lang,
                "  Otwórz My PC > Components, żeby przeszedł skan sprzętu, i zapytaj ponownie.",
                "  Open My PC > Components so the hardware scan runs, then ask again."))
            return lines

        cur_sock, chip = plat.get("socket"), plat.get("chipset")
        tgt_sock = tgt["socket"]
        spec = (f"  {tgt_sock} · {tgt['cores']}C/{tgt['threads']}T · "
                f"{tgt['tdp']} W")
        lines.append(spec)

        if verdict == "compatible":
            lines.append(_t(lang,
                f"  Ten sam socket ({tgt_sock}), a {chip or 'Twoja płyta'} obsługuje go natywnie - wymiana i start.",
                f"  Same socket ({tgt_sock}) and {chip or 'your board'} runs it natively - swap and boot."))
        elif verdict == "bios_update":
            lines.append(_t(lang,
                f"  Socket się zgadza ({tgt_sock}), ale płyty {chip} potrzebują aktualizacji BIOS dla tej generacji.",
                f"  Socket matches ({tgt_sock}), but {chip} boards need a BIOS update for this generation."))
            lines.append(_t(lang,
                "  Flashuj BIOS jeszcze na starym CPU, dopiero potem wymieniaj.",
                "  Flash the BIOS with the old CPU still installed, then swap."))
        elif verdict == "vendor_dependent":
            lines.append(_t(lang,
                f"  Część płyt {chip} dostała BIOS z obsługą tej generacji, część nigdy - sprawdź listę CPU swojego modelu przed zakupem.",
                f"  Some {chip} boards got BIOS support for this generation, some never did - check your exact model's CPU list before buying."))
        elif verdict == "chipset_blocked":
            lines.append(_t(lang,
                f"  Socket pasuje, ale {chip} w ogóle nie obsługuje tej generacji - żaden BIOS tego nie odblokuje.",
                f"  The socket matches, but {chip} does not support this generation at all - no BIOS unlocks it."))
            lines.append(_t(lang,
                "  Potrzebna płyta z chipsetem, który ma tę generację na liście.",
                "  You'd need a board whose chipset lists this generation."))
        elif verdict == "check_support_list":
            lines.append(_t(lang,
                f"  Socket pasuje ({tgt_sock}) - potwierdź model na liście wsparcia producenta płyty.",
                f"  Socket matches ({tgt_sock}) - confirm the model on your board vendor's support list."))
        elif verdict == "needs_new_board":
            both_1151 = {tgt_sock, cur_sock} == {"LGA1151", "LGA1151-2"}
            if both_1151:
                lines.append(_t(lang,
                    "  Piny wyglądają identycznie, ale LGA1151 (płyty 100/200) i LGA1151 v2 (300) są elektrycznie niekompatybilne.",
                    "  The pins look identical, but LGA1151 (100/200 boards) and LGA1151 v2 (300) are electrically incompatible."))
            else:
                lines.append(_t(lang,
                    f"  To {tgt_sock}, a Twoja płyta ma {cur_sock} - fizycznie nie wejdzie. Plan: wymiana płyty głównej.",
                    f"  It's {tgt_sock} and your board is {cur_sock} - it physically won't fit. Plan a motherboard swap."))
            if v.get("ram_change"):
                a, b = v["ram_change"]
                lines.append(_t(lang,
                    f"  Do tego zmiana pamięci {a} -> {b} - dolicz nowy RAM.",
                    f"  It also means {a} -> {b} memory - budget for new RAM."))
            else:
                carry = v.get("ram_carry") or "/".join(
                    SOCKETS.get(cur_sock, {}).get("ram", []))
                lines.append(_t(lang,
                    f"  Twój RAM ({carry}) przejdzie na nową płytę.",
                    f"  Your {carry} RAM carries over to the new board."))
            lines.append(_t(lang,
                "  Chłodzenie: montaż przejdzie bez zmian." if v.get("cooler_ok")
                else f"  Chłodzenie: potrzebny zestaw montażowy {SOCKETS[tgt_sock]['mount']} (albo nowy cooler).",
                "  Cooling: the mounting carries over." if v.get("cooler_ok")
                else f"  Cooling: you'll need a {SOCKETS[tgt_sock]['mount']} mounting kit (or a new cooler)."))

        # extras recomputed from facts (engine notes are EN-only)
        cur_cpu = plat.get("cpu")
        if tgt["tdp"] >= 125 and (not cur_cpu or cur_cpu["tdp"] <= 65):
            lines.append(_t(lang,
                f"  Uwaga: to część {tgt['tdp']} W - upewnij się, że cooler i sekcja VRM dadzą radę.",
                f"  Note: it's a {tgt['tdp']} W part - make sure the cooler and VRM are up to it."))
        if not tgt["igpu"] and not plat.get("gpu"):
            gname = (plat.get("gpu_name") or "").lower()
            if not gname or "graphics" in gname:
                lines.append(_t(lang,
                    "  Uwaga: wersja bez iGPU - bez dedykowanej karty nie będzie obrazu.",
                    "  Note: no integrated graphics - it needs a dedicated GPU for display."))
        if cur_cpu and tgt and cur_cpu["key"] == tgt["key"]:
            lines.append(_t(lang, "  ...to ten sam procesor, który już masz. 😄",
                                  "  ...that's the CPU you already have. 😄"))
        lines.append(_t(lang,
            "  Więcej wariantów sprawdzisz tu: [-> Upgrade Readiness]",
            "  Check more options here: [-> Upgrade Readiness]"))
        return lines

    def _ur_gpu_lines(self, v: dict, lang: str) -> List[str]:
        P = self.PREFIX
        tgt, plat = v.get("target"), v.get("current") or {}
        verdict = v.get("verdict", "")
        name = tgt["label"] if tgt else (v.get("target_text") or "").strip()
        lines = [f"{P} {name} - {self._ur_head(verdict, lang)}"]

        if verdict == "unknown_part":
            from core.hardware_compat import db_stats
            n = db_stats()["gpus"]
            lines.append(_t(lang,
                f"  Biblioteka offline obejmuje {n} kart (GTX 700 -> RTX 50, RX 500 -> RX 9000, Arc).",
                f"  The offline library covers {n} cards (GTX 700 -> RTX 50, RX 500 -> RX 9000, Arc)."))
            return lines

        lines.append(_t(lang,
            "  Standardowe PCIe x16 - elektrycznie pasuje do każdej płyty z biblioteki.",
            "  Standard PCIe x16 - electrically fits every board in the library."))
        lines.append(_t(lang,
            f"  Zasilanie: karta bierze do {tgt['tdp']} W, zalecany zasilacz {tgt['rec_psu']} W.",
            f"  Power: up to {tgt['tdp']} W, recommended PSU {tgt['rec_psu']} W."))

        cur = plat.get("gpu")
        delta = v.get("perf_delta_pct")
        if cur and delta is not None:
            if delta >= 25:
                lines.append(_t(lang,
                    f"  Względem Twojej {cur['label']}: ok. {delta:+d}% klasy - realny upgrade.",
                    f"  Versus your {cur['label']}: roughly {delta:+d}% in class - a real upgrade."))
            elif delta > -10:
                lines.append(_t(lang,
                    f"  Względem Twojej {cur['label']}: ok. {delta:+d}% - bardziej sidegrade niż upgrade.",
                    f"  Versus your {cur['label']}: about {delta:+d}% - more sidegrade than upgrade."))
            else:
                lines.append(_t(lang,
                    f"  Względem Twojej {cur['label']}: ok. {delta:+d}% - to zejście klasę niżej.",
                    f"  Versus your {cur['label']}: about {delta:+d}% - that's a class down."))
            if v.get("vram_delta_gb"):
                d = v["vram_delta_gb"]
                lines.append(f"  VRAM: {cur['vram_gb']} GB -> {tgt['vram_gb']} GB"
                             f" ({'+' if d > 0 else ''}{d} GB)")
            watt = tgt["tdp"] - cur["tdp"]
            if watt >= 75:
                lines.append(_t(lang,
                    f"  Bierze {watt} W więcej niż Twoja obecna karta - sprawdź moc i złącza zasilacza.",
                    f"  Draws {watt} W more than your current card - check PSU wattage and connectors."))
        elif not cur:
            lines.append(_t(lang,
                "  Nie widzę u Ciebie dedykowanej karty - to będzie dołożenie, nie wymiana.",
                "  I don't see a dedicated GPU here - this would be an addition, not a swap."))

        if v.get("bottleneck") and plat.get("cpu"):
            lines.append(_t(lang,
                f"  Parowanie: {plat['cpu']['label']} będzie ją ograniczać w grach CPU-heavy (1440p i niżej).",
                f"  Pairing: {plat['cpu']['label']} will hold it back in CPU-heavy games (1440p and below)."))
        if tgt.get("note"):
            note = (self._UR_GPU_NOTES_PL.get(tgt["key"], tgt["note"])
                    if lang == "pl" else tgt["note"])
            lines.append(f"  {note}")
        lines.append(_t(lang,
            "  Więcej wariantów sprawdzisz tu: [-> Upgrade Readiness]",
            "  Check more options here: [-> Upgrade Readiness]"))
        return lines

    def _resp_ram_compat(self, r: ParseResult, lang: str = "pl") -> List[str]:
        """'Czy DDR5 6000 zadziała?' / 'jaki RAM pasuje?' - DDR generation and
        speed vs the platform, with XMP/EXPO and chipset-lock caveats."""
        P = self.PREFIX
        from core import hardware_compat as hc
        from core.hardware_compat_db import SOCKETS
        v = hc.check_ram_upgrade(r.raw_text)
        verdict = v.get("verdict", "")
        plat = v.get("current") or {}
        sock, chip = plat.get("socket"), plat.get("chipset")

        if verdict == "unknown_current":
            return [f"{P} {self._ur_head(verdict, lang)}",
                    _t(lang,
                       "  Otwórz My PC > Components, żeby przeszedł skan sprzętu, i zapytaj ponownie.",
                       "  Open My PC > Components so the hardware scan runs, then ask again.")]

        supported = "/".join(SOCKETS.get(sock, {}).get("ram", []))
        ram_max = SOCKETS.get(sock, {}).get("ram_max", {})
        max_txt = ", ".join(f"{k}-{mv}" for k, mv in ram_max.items())
        want = v.get("target") or {}
        head = (want.get("ddr") or supported) + \
               (f" {want['speed']}" if want.get("speed") else "")
        lines = [f"{P} RAM {head} - {self._ur_head(verdict, lang)}"]

        if verdict == "incompatible":
            lines.append(_t(lang,
                f"  {sock} przyjmuje {supported}, nie {want.get('ddr')} - wcięcie na kości fizycznie nie pasuje.",
                f"  {sock} takes {supported}, not {want.get('ddr')} - the notch physically won't line up."))
            return lines

        lines.append(_t(lang,
            f"  Twoja platforma ({sock}) używa {supported}, oficjalnie do {max_txt}.",
            f"  Your platform ({sock}) uses {supported}, officially up to {max_txt}."))
        spd, ddr = want.get("speed"), want.get("ddr") or supported.split("/")[-1]
        official = ram_max.get(ddr)
        if spd and official:
            if spd <= official:
                lines.append(_t(lang,
                    f"  {spd} MT/s mieści się w oficjalnej specyfikacji - włóż i działa.",
                    f"  {spd} MT/s is within official spec - plug and play."))
            else:
                lines.append(_t(lang,
                    f"  {spd} MT/s to więcej niż oficjalne {ddr}-{official} - zadziała przez profil XMP/EXPO, większość płyt łyka to bez problemu.",
                    f"  {spd} MT/s is above the official {ddr}-{official} - it runs via an XMP/EXPO profile, which most boards handle fine."))
                if chip in ("H410", "B460", "H470"):
                    lines.append(_t(lang,
                        f"  Uwaga: {chip} blokuje OC pamięci - kit zejdzie do oficjalnych zegarów.",
                        f"  Caveat: {chip} locks memory OC - the kit will downclock to spec."))
        if sock == "AM4":
            lines.append(_t(lang, "  Sweet spot na AM4: DDR4-3600 CL16.",
                                  "  Sweet spot on AM4: DDR4-3600 CL16."))
        elif sock == "AM5":
            lines.append(_t(lang, "  Sweet spot na AM5: DDR5-6000 CL30 (EXPO).",
                                  "  Sweet spot on AM5: DDR5-6000 CL30 (EXPO)."))
        elif sock == "LGA1700" and ddr == "DDR5":
            lines.append(_t(lang, "  Sweet spot na LGA1700: okolice DDR5-6000.",
                                  "  Sweet spot on LGA1700: around DDR5-6000."))
        lines.append(_t(lang,
            "  Pełny sprawdzacz części: [-> Upgrade Readiness]",
            "  The full part checker: [-> Upgrade Readiness]"))
        return lines
