"""Quick check of the key components for the optimization guide (2026-11-17).

Two reports, both plain chat lines (headless, no Tk):

    components(lang) - CPU, GPU and RAM: use now, average over the last
        7 days, how hard the part usually works (near its limit / fine /
        lots of headroom), temperature as far as this PC reports it, and
        for RAM the virtual memory as it is set now.
    drivers(lang)    - how old the drivers behind those parts are, judged
        calmly: the graphics driver by its date, the platform (chipset /
        Management Engine) by its newest real date, RAM through the BIOS
        that runs it.

Rules: numbers come from this machine (psutil, the live sensor snapshot,
the stats history, the registry); a value that cannot be read is said to
be unreadable, never guessed. Intel ships chipset INF files dated
7-18-1968 on purpose; such placeholder dates are ignored.
"""
from __future__ import annotations

import datetime as _dt
import time

_DAY = 86400.0


def _t(lang, pl, en):
    return en if lang == "en" else pl


# ── data ──────────────────────────────────────────────────────────────────────
def _history(comp: str) -> dict:
    try:
        from hck_stats_engine import history
        now = time.time()
        return history.stats(comp, now - 7 * _DAY, now) or {}
    except Exception:
        return {}


def _live() -> dict:
    try:
        from hck_gpt.data.live_sensors import snapshot
        return snapshot() or {}
    except Exception:
        return {}


def _hw() -> dict:
    try:
        from hck_gpt.memory.user_knowledge import user_knowledge
        return user_knowledge.get_all_hardware() or {}
    except Exception:
        return {}


def _num(v, default=-1.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ── verdicts ──────────────────────────────────────────────────────────────────
def load_verdict(st: dict, lang: str, comp: str) -> str:
    """How hard the part usually works, from 7 days of history."""
    if not st.get("has_data"):
        return _t(lang, "historia dopiero się zbiera, ocena po kilku godzinach pracy",
                  "history is still building up, a verdict after a few hours")
    avg, p95 = _num(st.get("avg"), 0), _num(st.get("p95"), 0)
    rec_min = max(1.0, _num(st.get("recorded_hours"), 0) * 60)
    high_share = _num(st.get("high_load_minutes"), 0) / rec_min
    if comp == "ram":
        if avg >= 85:
            return _t(lang, "prawie pełna przez większość czasu, brakuje zapasu",
                      "nearly full most of the time, no headroom")
        if avg >= 70:
            return _t(lang, "pracuje wysoko, zapasu jest niewiele",
                      "runs high, little headroom")
        return _t(lang, "jest zapas", "there is headroom")
    if avg >= 70 or high_share >= 0.30:
        return _t(lang, "pracuje ciężko, często blisko maksimum",
                  "works hard, often near its limit")
    if p95 >= 85:
        return _t(lang, "zwykle spokojnie, w szczytach (gry, ciężkie zadania) dochodzi do maksimum",
                  "usually calm, peaks (games, heavy work) reach the limit")
    if avg < 25:
        return _t(lang, "ma dużo wolnej mocy", "has plenty of spare power")
    return _t(lang, "pracuje optymalnie", "works at a healthy level")


def _gpu_temp_verdict(t: float, lang: str) -> str:
    if t < 70:
        return _t(lang, "chłodno", "cool")
    if t < 84:
        return _t(lang, "ciepło, normalne pod obciążeniem", "warm, normal under load")
    return _t(lang, "gorąco, warto sprawdzić przepływ powietrza", "hot, worth checking the airflow")


# ── report 1: components ─────────────────────────────────────────────────────
def components(lang: str = "pl") -> list:
    import psutil
    live, hw = _live(), _hw()
    out = []

    # CPU
    try:
        cpu_now = psutil.cpu_percent(interval=0.5)
    except Exception:
        cpu_now = _num(live.get("cpu_load"))
    st = _history("cpu")
    name = live.get("cpu_name") or hw.get("cpu_model") or "CPU"
    out.append(f"§STEP CPU · {name}")
    avg = (_t(lang, f"średnio {st['avg']:.0f}% przez 7 dni", f"average {st['avg']:.0f}% over 7 days")
           if st.get("has_data") else _t(lang, "średniej jeszcze nie ma", "no average yet"))
    out.append(_t(lang, f"  Teraz {cpu_now:.0f}%, {avg}.", f"  Now {cpu_now:.0f}%, {avg}."))
    out.append("  " + load_verdict(st, lang, "cpu").capitalize() + ".")
    out.append("")
    ct, src = _num(live.get("cpu_temp")), str(live.get("cpu_temp_src") or "")
    if ct > 0 and src == "sensor":
        out.append(_t(lang, f"  Temperatura: {ct:.0f}°C (czujnik).", f"  Temperature: {ct:.0f}°C (sensor)."))
    else:
        out.append(_t(lang,
            "  Temperatura: Windows nie podaje czujnika CPU bez dodatkowego programu "
            "(LibreHardwareMonitor), więc jej nie zgaduję.",
            "  Temperature: Windows gives no CPU sensor without an extra tool "
            "(LibreHardwareMonitor), so I do not guess it."))
    out.append("")

    # GPU
    st = _history("gpu")
    gname = live.get("gpu_name") or hw.get("gpu_model") or ""
    gload, gtemp = _num(live.get("gpu_load")), _num(live.get("gpu_temp"))
    if gname or gload >= 0 or st.get("has_data"):
        out.append(f"§STEP GPU · {gname or 'GPU'}")
        avg = (_t(lang, f"średnio {st['avg']:.0f}% przez 7 dni", f"average {st['avg']:.0f}% over 7 days")
               if st.get("has_data") else _t(lang, "średniej jeszcze nie ma", "no average yet"))
        if gload >= 0:
            out.append(_t(lang, f"  Teraz {gload:.0f}%, {avg}.", f"  Now {gload:.0f}%, {avg}."))
        else:
            out.append(_t(lang, f"  Teraz: brak odczytu, {avg}.", f"  Now: no reading, {avg}."))
        out.append("  " + load_verdict(st, lang, "gpu").capitalize() + ".")
        out.append("")
        if gtemp > 0:
            tmax = st.get("temp_max")
            peak = (_t(lang, f", najwyżej {tmax:.0f}°C w tym tygodniu", f", at most {tmax:.0f}°C this week")
                    if tmax else "")
            hot = max(gtemp, _num(tmax, 0))
            out.append(_t(lang,
                f"  Temperatura: {gtemp:.0f}°C teraz{peak} - {_gpu_temp_verdict(hot, lang)}.",
                f"  Temperature: {gtemp:.0f}°C now{peak} - {_gpu_temp_verdict(hot, lang)}."))
        else:
            out.append(_t(lang, "  Temperatura: karta jej teraz nie podaje.",
                          "  Temperature: the card does not report it right now."))
        out.append("")

    # RAM
    st = _history("ram")
    try:
        vm = psutil.virtual_memory()
        total_gb, ram_now = vm.total / 1024 ** 3, vm.percent
    except Exception:
        total_gb, ram_now = 0.0, -1.0
    out.append(f"§STEP RAM · {total_gb:.0f} GB" if total_gb else "§STEP RAM")
    avg = (_t(lang, f"średnio {st['avg']:.0f}% przez 7 dni", f"average {st['avg']:.0f}% over 7 days")
           if st.get("has_data") else _t(lang, "średniej jeszcze nie ma", "no average yet"))
    out.append(_t(lang, f"  Teraz {ram_now:.0f}%, {avg}.", f"  Now {ram_now:.0f}%, {avg}."))
    out.append("  " + load_verdict(st, lang, "ram").capitalize() + ".")
    if 0 < total_gb < 12 and _num(st.get("avg"), 0) >= 70:
        out.append(_t(lang,
            f"  Przy {total_gb:.0f} GB to typowe; 16 GB da najwięcej spokoju.",
            f"  With {total_gb:.0f} GB that is typical; 16 GB gives the most relief."))
    out.append("")
    try:
        from core.pagefile import describe
        out.append("  " + describe(lang) + ".")
    except Exception:
        pass
    out.append("  [-> Virtual Memory]")
    return out


# ── report 2: drivers ────────────────────────────────────────────────────────
_GPU_CLASS = "{4d36e968-e325-11ce-bfc1-08002be10318}"
_SYS_CLASS = "{4d36e97d-e325-11ce-bfc1-08002be10318}"
_PLATFORM_KEYS = ("management engine", "chipset", "serial io", "smbus", "gpio",
                  "amd psp", "amd gpio", "amd smbus", "pci express root")


def _parse_date(raw: str):
    """Registry DriverDate 'M-D-YYYY'; placeholder dates (before 2006) -> None."""
    try:
        m, d, y = (int(x) for x in str(raw).strip().split("-"))
        dt = _dt.date(y, m, d)
        return dt if y >= 2006 else None
    except Exception:
        return None


def _class_drivers(guid: str) -> list:
    out = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            rf"SYSTEM\CurrentControlSet\Control\Class\{guid}") as cls:
            for i in range(winreg.QueryInfoKey(cls)[0]):
                sub = winreg.EnumKey(cls, i)
                if not sub[:4].isdigit():
                    continue
                try:
                    with winreg.OpenKey(cls, sub) as dev:
                        def _v(name):
                            try:
                                return winreg.QueryValueEx(dev, name)[0]
                            except OSError:
                                return ""
                        out.append({"name": _v("DriverDesc"), "version": _v("DriverVersion"),
                                    "date": _parse_date(_v("DriverDate")),
                                    "provider": _v("ProviderName")})
                except OSError:
                    continue
    except Exception:
        pass
    return out


def _nvidia_version(win_ver: str) -> str:
    """Windows driver version 32.0.16.1088 -> NVIDIA's 610.88."""
    try:
        a, b = win_ver.split(".")[-2:]
        digits = (a + b.zfill(4))[-5:]
        return f"{digits[:3]}.{digits[3:]}"
    except Exception:
        return ""


def _age_months(d) -> int:
    return max(0, (_dt.date.today() - d).days // 30)


def _age_text(months: int, lang: str) -> str:
    if months < 1:
        return _t(lang, "z tego miesiąca", "from this month")
    if months < 12:
        return _t(lang, f"ma {months} mies.", f"{months} months old")
    y = months / 12
    return _t(lang, f"ma ok. {y:.0f} {'rok' if round(y) == 1 else 'lata' if round(y) < 5 else 'lat'}",
              f"about {y:.0f} year{'s' if round(y) != 1 else ''} old")


def _bios() -> dict:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\BIOS") as k:
            def _v(n):
                try:
                    return str(winreg.QueryValueEx(k, n)[0]).strip()
                except OSError:
                    return ""
            raw = _v("BIOSReleaseDate")
            date = None
            try:
                mm, dd, yy = (int(x) for x in raw.split("/"))
                date = _dt.date(yy, mm, dd)
            except Exception:
                pass
            return {"version": _v("BIOSVersion"), "date": date,
                    "board": _v("BaseBoardProduct"), "maker": _v("BaseBoardManufacturer")}
    except Exception:
        return {}


def drivers(lang: str = "pl") -> list:
    out = []

    # GPU: the one driver that changes performance in games
    gpus = [g for g in _class_drivers(_GPU_CLASS)
            if g["name"] and "basic display" not in g["name"].lower()
            and "virtual" not in g["name"].lower()]
    out.append(_t(lang, "§STEP GPU · sterownik grafiki", "§STEP GPU · graphics driver"))
    if not gpus:
        out.append(_t(lang, "  Nie mogę odczytać sterownika karty.", "  Cannot read the graphics driver."))
    for g in gpus[:2]:
        ver = g["version"]
        if "nvidia" in (g["provider"] or g["name"]).lower():
            ver = _nvidia_version(ver) or ver
        if g["date"]:
            m = _age_months(g["date"])
            if m < 4:
                verdict = _t(lang, "aktualny", "up to date")
                tag = "§OK "
            elif m < 12:
                verdict = _t(lang, "w porządku, nowszy przyda się przy nowych grach",
                             "fine, a newer one helps with new games")
                tag = "§OK "
            elif m < 24:
                verdict = _t(lang, "warto zaktualizować przy okazji", "worth updating when convenient")
                tag = "§WARN "
            else:
                verdict = _t(lang, "stary, zaktualizuj", "old, update it")
                tag = "§WARN "
            out.append(tag + _t(lang,
                f"{g['name']}: {ver}, {g['date']:%d.%m.%Y} ({_age_text(m, lang)}) - {verdict}.",
                f"{g['name']}: {ver}, {g['date']:%Y-%m-%d} ({_age_text(m, lang)}) - {verdict}."))
        else:
            out.append(f"  {g['name']}: {ver}")
    out.append("")

    # CPU: the processor itself runs on Windows' own driver; the platform
    # drivers (Management Engine, Serial IO, chipset) are what can age
    out.append(_t(lang, "§STEP CPU · platforma (chipset)", "§STEP CPU · platform (chipset)"))
    plat = [d for d in _class_drivers(_SYS_CLASS)
            if d["date"] and "microsoft" not in (d["provider"] or "").lower()
            and any(k in d["name"].lower() for k in _PLATFORM_KEYS)]
    if plat:
        newest = max(plat, key=lambda d: d["date"])
        m = _age_months(newest["date"])
        verdict = (_t(lang, "w porządku", "fine") if m < 36 else
                   _t(lang, "starsze, aktualizacja ze strony producenta płyty nie zaszkodzi",
                      "older, an update from the board maker's site does no harm"))
        out.append(_t(lang,
            f"  Procesor korzysta ze sterownika Windows (aktualizuje go Windows Update).",
            f"  The processor uses Windows' own driver (Windows Update keeps it current)."))
        out.append(_t(lang,
            f"  Najnowszy sterownik platformy: {newest['name']}, {newest['date']:%m.%Y} "
            f"({_age_text(m, lang)}) - {verdict}.",
            f"  Newest platform driver: {newest['name']}, {newest['date']:%Y-%m} "
            f"({_age_text(m, lang)}) - {verdict}."))
    else:
        out.append(_t(lang,
            "  Procesor korzysta ze sterownika Windows; osobnych sterowników chipsetu z datą nie widzę.",
            "  The processor uses Windows' own driver; I see no dated chipset drivers."))
    out.append("")

    # RAM: no driver of its own - the BIOS sets it up
    out.append(_t(lang, "§STEP RAM · BIOS płyty", "§STEP RAM · motherboard BIOS"))
    b = _bios()
    out.append(_t(lang,
        "  Pamięć RAM nie ma własnego sterownika: ustawia ją BIOS płyty głównej.",
        "  RAM has no driver of its own: the motherboard BIOS sets it up."))
    if b.get("date"):
        m = _age_months(b["date"])
        board = f"{b.get('board') or ''}".strip()
        verdict = (_t(lang, "aktualizacja nie jest potrzebna", "no update needed") if m < 24 else
                   _t(lang, "jeśli wszystko działa stabilnie, aktualizacja nie jest konieczna",
                      "if everything runs stable, an update is not necessary"))
        out.append(_t(lang,
            f"  BIOS {b.get('version') or ''} z {b['date']:%m.%Y} ({_age_text(m, lang)})"
            + (f", płyta {board}" if board else "") + f" - {verdict}.",
            f"  BIOS {b.get('version') or ''} from {b['date']:%Y-%m} ({_age_text(m, lang)})"
            + (f", board {board}" if board else "") + f" - {verdict}."))
    else:
        out.append(_t(lang, "  Daty BIOS-u nie mogę odczytać.", "  Cannot read the BIOS date."))
    out.append("")
    out.append(_t(lang, "Wszystkie sterowniki z datami:", "All drivers with dates:"))
    out.append("[-> Setup & Drivers]")
    return out
