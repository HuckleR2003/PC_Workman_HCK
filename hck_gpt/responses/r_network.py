"""hck_gpt.responses.r_network - internet questions, tested first (2026-11-20).

"Internet is slow", "do I have internet", "what's my ping", "pages won't
load": hck_GPT used to answer with a general checklist. Now every such
question starts the network guide, which measures first (core/net_check.py,
2-4 s) and answers from the numbers:

  step 1  the quick test: router, google.com, DNS, a verdict and the steps
          that fit it; offers a download speed test (25 MB from Cloudflare,
          only after "tak")
  step 2  the fix: on a DNS fault it offers to flush the DNS cache; otherwise
          it offers to test again after a change (router restart, cable)
  step 3  the comparison, before and after

The source of the verdict is said on a yellow band (§SRC): "Ocena według
testu połączenia z google.com".
"""
from __future__ import annotations

import time
from typing import List

from hck_gpt.intents.parser import ParseResult
from hck_gpt.responses.common import _t


def _ms(v) -> str:
    return "-" if v is None else f"{v:.0f} ms"


def _num(v, lang, nd=0) -> str:
    s = f"{v:.{nd}f}"
    return s.replace(".", ",") if lang == "pl" else s


_VERDICT = {
    "good": ("Połączenie działa dobrze: niski ping, bez strat.",
             "The connection works well: low ping, no loss."),
    "no_network": ("Komputer nie jest połączony z żadną siecią.",
                   "The PC is not connected to any network."),
    "no_router": ("Router nie odpowiada na tym połączeniu.",
                  "The router does not answer on this connection."),
    "no_internet": ("Router odpowiada, ale internet nie: problem leży za routerem (modem albo dostawca).",
                    "The router answers, the internet does not: the problem is past the router (modem or provider)."),
    "dns": ("Adresy działają, ale nazwy stron się nie tłumaczą: to DNS.",
            "Addresses work, but site names do not resolve: it is DNS."),
    "local_loss": ("Pakiety giną już między komputerem a routerem.",
                   "Packets get lost already between the PC and the router."),
    "loss": ("Część pakietów do google.com ginie po drodze.",
             "Some packets to google.com get lost on the way."),
    "slow_local": ("Sam odcinek do routera jest wolny: po kablu to 1-2 ms.",
                   "The hop to the router itself is slow: on a cable it is 1-2 ms."),
    "high_ping": ("Ping jest wysoki: do gier online dobrze, gdy jest poniżej 50 ms.",
                  "The ping is high: for online games under 50 ms is good."),
    "jitter": ("Ping mocno skacze: w grach i rozmowach wideo to lagi.",
               "The ping jumps a lot: in games and video calls that means lag."),
    "slow_dns": ("DNS odpowiada wolno, więc strony dłużej się otwierają.",
                 "DNS answers slowly, so pages take longer to open."),
}

_STEPS = {
    "no_network": [("Wi-Fi włączone? Tryb samolotowy wyłączony? (ikona sieci w prawym dolnym rogu)",
                    "Wi-Fi on? Airplane mode off? (network icon in the bottom right)"),
                   ("Kabel: wyjmij i włóż z powrotem po obu stronach.", "Cable: unplug and plug back in at both ends."),
                   ("Ustawienia → Sieć i internet → Zaawansowane → Resetowanie sieci, gdy nic nie pomaga.",
                    "Settings → Network & internet → Advanced → Network reset, when nothing else helps.")],
    "no_router": [("Połącz się z Wi-Fi jeszcze raz (rozłącz i połącz).", "Reconnect to the Wi-Fi (disconnect, connect)."),
                  ("Wyłącz router na 30 sekund i włącz.", "Turn the router off for 30 seconds and back on.")],
    "no_internet": [("Wyłącz router i modem na 30 sekund, włącz najpierw modem.",
                     "Turn the router and modem off for 30 seconds, start the modem first."),
                    ("Sprawdź lampki modemu (internet / WAN). Czerwona albo zgaszona: awaria u dostawcy.",
                     "Check the modem lights (internet / WAN). Red or off: an outage at the provider."),
                    ("Na telefonie w tej samej sieci Wi-Fi: działa? Jeśli nie, to nie wina komputera.",
                     "On a phone on the same Wi-Fi: does it work? If not, it is not the PC.")],
    "dns": [("Mogę teraz wyczyścić pamięć DNS (ipconfig /flushdns): bezpieczne, nic nie usuwa.",
             "I can flush the DNS cache now (ipconfig /flushdns): safe, removes nothing."),
            ("Pomaga też ustawienie DNS 1.1.1.1 albo 8.8.8.8 we właściwościach karty sieciowej.",
             "Setting DNS to 1.1.1.1 or 8.8.8.8 in the adapter properties also helps.")],
    "local_loss": [("Podejdź bliżej routera albo podłącz kabel na próbę.", "Move closer to the router or try a cable."),
                   ("Pasmo 5 GHz zamiast 2,4 GHz, jeśli router ma oba.", "Use 5 GHz instead of 2.4 GHz if the router has both."),
                   ("Sterownik karty Wi-Fi ze strony producenta płyty albo laptopa.",
                    "The Wi-Fi driver from the board or laptop maker's site.")],
    "slow_local": [("Podejdź bliżej routera albo podłącz kabel na próbę.", "Move closer to the router or try a cable."),
                   ("Pasmo 5 GHz zamiast 2,4 GHz, jeśli router ma oba.", "Use 5 GHz instead of 2.4 GHz if the router has both.")],
    "loss": [("Wyłącz router na 30 sekund i sprawdź ponownie.", "Restart the router for 30 seconds and test again."),
             ("Jeśli straty zostają po kablu, zgłoś to dostawcy internetu.",
              "If the loss stays on a cable, report it to the provider.")],
    "high_ping": [("Pobieranie w tle (Steam, Windows Update, chmura) podnosi ping: sprawdzam to niżej.",
                   "Background downloads (Steam, Windows Update, cloud) raise the ping: checked below."),
                  ("Kabel zamiast Wi-Fi zwykle zbija ping i wahania.", "A cable instead of Wi-Fi usually lowers ping and jitter.")],
    "jitter": [("Kabel zamiast Wi-Fi zwykle zbija wahania.", "A cable instead of Wi-Fi usually removes the jitter."),
               ("Inne urządzenia w domu mogą teraz pobierać (filmy, aktualizacje).",
                "Other devices at home may be downloading now (videos, updates).")],
    "slow_dns": [("Ustaw DNS 1.1.1.1 albo 8.8.8.8 we właściwościach karty sieciowej.",
                  "Set DNS to 1.1.1.1 or 8.8.8.8 in the adapter properties.")],
}

_DOWNLOADERS = {"steam": "Steam", "epicgameslauncher": "Epic Games", "battle.net": "Battle.net",
                "onedrive": "OneDrive", "dropbox": "Dropbox", "googledrivefs": "Google Drive",
                "qbittorrent": "qBittorrent", "utorrent": "uTorrent", "bittorrent": "BitTorrent",
                "eadesktop": "EA app", "upc": "Ubisoft Connect"}


def _downloaders() -> list:
    try:
        import psutil
        seen = []
        for p in psutil.process_iter(["name"]):
            label = _DOWNLOADERS.get((p.info.get("name") or "").lower().removesuffix(".exe"))
            if label and label not in seen:
                seen.append(label)
        return seen
    except Exception:
        return []


def _traffic_mbps() -> tuple:
    try:
        import psutil
        a = psutil.net_io_counters()
        time.sleep(1.0)
        b = psutil.net_io_counters()
        return (b.bytes_recv - a.bytes_recv) * 8 / 1e6, (b.bytes_sent - a.bytes_sent) * 8 / 1e6
    except Exception:
        return None, None


def report(r: dict, lang: str) -> List[str]:
    """The test result as chat lines (pure: no measuring)."""
    from core.net_check import verdict
    level, key = verdict(r)
    out = ["§SRC " + _t(lang, f"Ocena według testu połączenia z {r.get('target', 'google.com')} "
                              f"({time.strftime('%H:%M', time.localtime(r.get('ts', time.time())))})",
                        f"Verdict from a connection test to {r.get('target', 'google.com')} "
                        f"({time.strftime('%H:%M', time.localtime(r.get('ts', time.time())))})")]
    ad = r.get("adapter") or {}
    if ad.get("kind"):
        kind = {"wifi": ("Wi-Fi", "Wi-Fi"), "ethernet": ("kabel (Ethernet)", "cable (Ethernet)"),
                "other": ("inne", "other")}[ad["kind"]]
        link = (_t(lang, f", łącze z routerem {ad['speed_mbps']} Mb/s", f", link to the router {ad['speed_mbps']} Mb/s")
                if ad.get("speed_mbps") else "")
        out.append(_t(lang, f"  Połączenie: {kind[0]}{link}", f"  Connection: {kind[1]}{link}"))
    gw = r.get("gw")
    if r.get("gateway"):
        if gw and gw["avg"] is not None:
            out.append(_t(lang, f"  Router {r['gateway']}: {_ms(gw['avg'])}, straty {gw['lost']}/{gw['sent']}",
                          f"  Router {r['gateway']}: {_ms(gw['avg'])}, lost {gw['lost']}/{gw['sent']}"))
        else:
            out.append(_t(lang, f"  Router {r['gateway']}: brak odpowiedzi (część routerów nie odpowiada na ping)",
                          f"  Router {r['gateway']}: no reply (some routers ignore ping)"))
    web = r.get("web")
    if web and web["avg"] is not None:
        out.append(_t(lang,
            f"  google.com: ping {_ms(web['avg'])} ({web['min']:.0f}-{web['max']:.0f}), wahania {_ms(web['jitter'])}, straty {web['lost']}/{web['sent']}",
            f"  google.com: ping {_ms(web['avg'])} ({web['min']:.0f}-{web['max']:.0f}), jitter {_ms(web['jitter'])}, lost {web['lost']}/{web['sent']}"))
    elif r.get("tcp_ms") is not None:
        out.append(_t(lang, f"  google.com: ping zablokowany, połączenie TCP {_ms(r['tcp_ms'])}",
                      f"  google.com: ping blocked, TCP connection {_ms(r['tcp_ms'])}"))
    if r.get("dns_ms") is not None:
        out.append(_t(lang, f"  DNS (nazwa → adres): {_ms(r['dns_ms'])}", f"  DNS (name → address): {_ms(r['dns_ms'])}"))
    band = {"ok": "§OK ", "warn": "§WARN ", "bad": "§WARN "}[level]
    pl, en = _VERDICT[key]
    out.append(band + _t(lang, pl, en))
    steps = _STEPS.get(key, [])
    if steps:
        out.append(_t(lang, "Co zrobić:", "What to do:"))
        out += [f"  {i}. " + _t(lang, a, b) for i, (a, b) in enumerate(steps, 1)]
    return out


# ── the guide ────────────────────────────────────────────────────────────
def _n0_test(rb, state, lang):
    from core.net_check import check, verdict
    r = check()
    state["first"] = r
    level, key = verdict(r)
    state["key"] = key
    mode = state.get("mode", "check")
    head = {
        "slow": ("Wolny internet: najpierw mierzę, potem radzę.", "Slow internet: measuring first, advice after."),
        "down": ("Sprawdzam, gdzie urywa się połączenie.", "Checking where the connection breaks."),
        "drop": ("Zrywanie połączenia: sprawdzam, jak wygląda teraz.", "Dropping connection: checking how it looks now."),
        "speed": ("Najpierw szybki test, potem pomiar prędkości.", "A quick test first, then the speed."),
        "dns": ("Sprawdzam połączenie i DNS.", "Checking the connection and DNS."),
    }.get(mode, ("Sprawdzam połączenie z internetem.", "Checking the internet connection."))
    out = ["§PAUSE", _t(lang, f"🌐 {head[0]}", f"🌐 {head[1]}"),
           "§STEP " + _t(lang, "TEST POŁĄCZENIA", "CONNECTION TEST")]
    out += report(r, lang)
    if mode in ("slow", "speed") or key in ("high_ping", "jitter", "loss"):
        down, up = _traffic_mbps()
        if down is not None:
            busy = down > 5 or up > 2
            out.append(("§WARN " if busy else "§OK ") + _t(lang,
                f"Ten komputer teraz pobiera {_num(down, lang, 1)} Mb/s i wysyła {_num(up, lang, 1)} Mb/s"
                + (": coś w tle zajmuje łącze." if busy else ": nie zajmuje łącza."),
                f"This PC now downloads {down:.1f} Mb/s and uploads {up:.1f} Mb/s"
                + (": something in the background uses the link." if busy else ": it is not filling the link.")))
        dl = _downloaders()
        if dl:
            out.append(_t(lang, "  Działają programy, które pobierają w tle: " + ", ".join(dl) + ".",
                          "  Running programs that download in the background: " + ", ".join(dl) + "."))
    if mode == "down" and level == "ok":
        out.append(_t(lang,
            "  Z tego komputera internet teraz działa. Jeśli nie działa jedna przeglądarka albo program: "
            "zamknij go i otwórz ponownie, wyłącz na próbę VPN lub rozszerzenia. Jeśli nie działa na innych urządzeniach: router.",
            "  From this PC the internet works now. If one browser or program does not: close and reopen it, "
            "try without the VPN or extensions. If other devices have no internet: the router."))
    if mode == "drop":
        out.append(_t(lang,
            "  Jeden test nie złapie zerwania, które trwa chwilę. Najczęstsza przyczyna na Wi-Fi: oszczędzanie energii karty "
            "(Menedżer urządzeń → karta Wi-Fi → Zarządzanie energią → odznacz wyłączanie).",
            "  One test cannot catch a drop that lasts a moment. The usual Wi-Fi cause: adapter power saving "
            "(Device Manager → Wi-Fi adapter → Power Management → untick turning it off)."))
    if level != "bad" or key == "dns":
        out.append("§NOTE " + _t(lang,
            "Zmierzyć prędkość pobierania? Pobiorę ok. 25 MB z serwera testowego Cloudflare (5-20 s). Nic o Tobie nie wysyłam.",
            "Measure the download speed? I download about 25 MB from Cloudflare's test server (5-20 s). Nothing about you is sent."))
        out.append(_t(lang, "➡ 'tak' mierzy, 'pomiń' przechodzi dalej.", "➡ 'yes' measures, 'skip' moves on."))
    else:
        # nothing to measure without a connection: "tak" tests again instead
        state["no_speed"] = True
        out.append(_t(lang, "➡ Zrób krok z listy i napisz 'tak': sprawdzę jeszcze raz. 'pomiń' kończy.",
                      "➡ Do a step from the list and say 'yes': I test again. 'skip' ends."))
    return out


def _n0_speed(rb, state, lang):
    if state.get("no_speed"):
        state["fix"] = "retest"
        state["done"] = True            # step 2 has nothing more to offer
        return _n1_act(rb, state, lang)
    from core.net_check import speed_test
    s = speed_test()
    state["speed"] = s
    if not s.get("ok"):
        return ["§PAUSE", "§WARN " + _t(lang, "Pomiar się nie udał (serwer nie odpowiedział albo połączenie się zerwało).",
                                         "The measurement failed (no answer from the server or the connection dropped).")]
    mbps = s["mbps"]
    grade = (("Wolno: wideo w HD może się zacinać.", "Slow: HD video may stutter.") if mbps < 10 else
             ("W porządku na co dzień i do gier.", "Fine for everyday use and gaming.") if mbps < 100 else
             ("Szybko.", "Fast."))
    out = ["§PAUSE", ("§OK " if mbps >= 10 else "§WARN ") + _t(lang,
        f"Pobieranie: {_num(mbps, lang, 0)} Mb/s ({s['bytes'] / 1e6:.0f} MB w {_num(s['secs'], lang, 1)} s). {grade[0]}",
        f"Download: {mbps:.0f} Mb/s ({s['bytes'] / 1e6:.0f} MB in {s['secs']:.1f} s). {grade[1]}")]
    out.append(_t(lang, "  Porównaj z prędkością w umowie. Po Wi-Fi zwykle wychodzi mniej niż po kablu.",
                  "  Compare with your plan's speed. Wi-Fi usually gives less than a cable."))
    ad = (state.get("first") or {}).get("adapter") or {}
    if ad.get("speed_mbps") and mbps > 0.7 * ad["speed_mbps"]:
        out.append(_t(lang, f"  Ograniczeniem może być samo łącze z routerem ({ad['speed_mbps']} Mb/s).",
                      f"  The link to the router itself may be the limit ({ad['speed_mbps']} Mb/s)."))
    return out


def _n1_fix(rb, state, lang):
    if state.get("done"):
        return []
    key = state.get("key")
    out = ["§STEP " + _t(lang, "CO DALEJ", "NEXT")]
    if key in ("dns", "slow_dns"):
        out.append(_t(lang, "Wyczyścić teraz pamięć DNS i sprawdzić ponownie?",
                      "Flush the DNS cache now and test again?"))
        state["fix"] = "dns"
    else:
        out.append(_t(lang, "Gdy coś zmienisz (restart routera, kabel, bliżej routera), sprawdzę jeszcze raz i porównam.",
                      "After a change (router restart, cable, closer to the router) I test again and compare."))
        state["fix"] = "retest"
    out.append(_t(lang, "➡ 'tak' sprawdza, 'pomiń' kończy.", "➡ 'yes' checks, 'skip' ends here."))
    return out


def _n1_act(rb, state, lang):
    from core.net_check import check, verdict
    out = ["§PAUSE"]
    if state.get("fix") == "dns":
        from core.cleanup import flush_dns
        out.append(("🧹 " + _t(lang, "Pamięć DNS wyczyszczona.", "DNS cache flushed.")) if flush_dns()
                   else ("⚠ " + _t(lang, "Nie udało się wyczyścić pamięci DNS.", "Could not flush the DNS cache.")))
    r = check()
    a, b = state.get("first") or {}, r
    out += report(r, lang)
    wa, wb = (a.get("web") or {}).get("avg"), (b.get("web") or {}).get("avg")
    if wa is not None and wb is not None:
        out.append(_t(lang, f"Przed → po: ping {wa:.0f} → {wb:.0f} ms, straty {a['web']['lost']} → {b['web']['lost']}.",
                      f"Before → after: ping {wa:.0f} → {wb:.0f} ms, lost {a['web']['lost']} → {b['web']['lost']}."))
    if verdict(r)[0] != "ok" and verdict(a)[0] != "ok" and verdict(r)[1] == verdict(a)[1]:
        out.append(_t(lang, "Bez zmian. Jeśli po restarcie routera i na kablu jest tak samo, zadzwoń do dostawcy internetu.",
                      "No change. If it stays the same after a router restart and on a cable, call the provider."))
    return out


def _finish(rb, state, lang):
    return [_t(lang, "✓ Gotowe. Test powtórzysz pytaniem 'sprawdź internet'.",
                     "✓ Done. Ask 'check my internet' to test again.")]


def _register():
    from hck_gpt.engine.flow_engine import flow_engine, Flow, FlowStep
    flow_engine.register(Flow("network", [
        FlowStep(_n0_test, act=_n0_speed,
                 yes=lambda st: (("TAK, SPRAWDŹ PONOWNIE", "YES, TEST AGAIN") if st.get("no_speed")
                                 else ("TAK, ZMIERZ", "YES, MEASURE"))),
        FlowStep(_n1_fix, act=_n1_act, yes=("TAK, SPRAWDŹ", "YES, CHECK")),
    ], finish=_finish))


_register()


class NetworkResponses:
    """Mixin for ResponseBuilder: every internet question starts the guide."""

    def _net_guide(self, lang, mode):
        from hck_gpt.engine.flow_engine import flow_engine
        out = flow_engine.start("network", self, lang, {"mode": mode})
        if not out:
            return [self.PREFIX + _t(lang, " Test połączenia chwilowo niedostępny.",
                                     " The connection test is unavailable right now.")]
        # the prefix goes on the first real line, after §PAUSE
        i = 1 if out and out[0] == "§PAUSE" else 0
        out[i] = f"{self.PREFIX} {out[i]}"
        return out

    def _resp_network_check(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return self._net_guide(lang, "check")

    def _resp_network_down(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return self._net_guide(lang, "down")

    def _resp_network_speed(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return self._net_guide(lang, "speed")

    def _resp_network_dns(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return self._net_guide(lang, "dns")

    def _resp_network_slow(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return self._net_guide(lang, "slow")

    def _resp_network_drop(self, r: ParseResult, lang: str = "pl") -> List[str]:
        return self._net_guide(lang, "drop")
