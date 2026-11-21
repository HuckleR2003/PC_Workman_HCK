"""ui.pages.health_report - the health report (2026-11-20).

My PC's "Health report" button led to the Health tab. This is a report to
read or keep: the score and its parts (core/health_score), what changed
since the last saved report, the three things most worth doing, and every
finding in the words hck_GPT uses. "Save the report" writes an HTML file to
the Desktop (to send to someone who helps with the PC) and remembers the
scores for the next comparison.

build_report(data, previous, lang) is plain Python; the page and the HTML
are drawn from it.
"""
from __future__ import annotations

import html
import json
import os
import threading
import time
import tkinter as tk

from utils.fonts import UI as _BODY, HDR as _HDR

BG = "#0a0e14"
PANEL = "#0f141c"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
GREEN = "#34d399"
AMBER = "#fbbf24"
RED = "#f87171"

_TX = {
    "title": {"pl": "Raport zdrowia", "en": "Health report"},
    "sub": {"pl": "Wszystko, co PC Workman wie o stanie tego komputera, na jednej stronie. Zapisz go, żeby porównać później albo wysłać komuś, kto pomaga.",
            "en": "Everything PC Workman knows about this PC's health, on one page. Save it to compare later or to send to someone who helps."},
    "save": {"pl": "Zapisz raport (HTML)", "en": "Save the report (HTML)"},
    "center": {"pl": "Centrum zdrowia", "en": "Health centre"},
    "checking": {"pl": "Zbieram dane: dziennik Windows, dyski, historia…", "en": "Gathering: the Windows log, drives, history…"},
    "score": {"pl": "WYNIK ZDROWIA", "en": "HEALTH SCORE"},
    "changes": {"pl": "OD OSTATNIEGO RAPORTU", "en": "SINCE THE LAST REPORT"},
    "first": {"pl": "To pierwszy raport: zapisz go, a następny pokaże zmiany.",
              "en": "The first report: save it and the next one shows the changes."},
    "same": {"pl": "Bez zmian od {d}.", "en": "No change since {d}."},
    "moved": {"pl": "{p}: {a} → {b}", "en": "{p}: {a} → {b}"},
    "total_moved": {"pl": "Wynik: {a} → {b} (raport z {d})", "en": "Score: {a} → {b} (report of {d})"},
    "todo": {"pl": "CO ZROBIĆ NAJPIERW", "en": "WHAT TO DO FIRST"},
    "nothing": {"pl": "Nic pilnego: komputer jest w dobrym stanie.", "en": "Nothing urgent: the PC is in good shape."},
    "all": {"pl": "WSZYSTKIE WNIOSKI", "en": "ALL FINDINGS"},
    "saved": {"pl": "✓ Zapisano: {p}", "en": "✓ Saved: {p}"},
    "html_title": {"pl": "PC Workman · Raport zdrowia", "en": "PC Workman · Health report"},
    "made": {"pl": "Utworzono {d} przez PC Workman. Dane zbierane lokalnie na tym komputerze.",
             "en": "Made {d} by PC Workman. Data collected locally on this PC."},
}
_ACTION = {
    "stability": {"pl": "Sprawdź zasilanie i przegrzewanie: restarty bez czystego zamknięcia to zwykle zasilacz, temperatura albo sterownik.",
                  "en": "Check power and overheating: restarts without a clean shutdown are usually the PSU, heat or a driver."},
    "drives": {"pl": "Zrób kopię ważnych plików i zwolnij miejsce (Oczyszczanie).",
               "en": "Back up what matters and free some room (Cleanup)."},
    "temps": {"pl": "Wyczyść kurz z wentylatorów i sprawdź przepływ powietrza w obudowie.",
              "en": "Clean the dust off the fans and check the airflow in the case."},
    "memory": {"pl": "Włącz XMP w BIOS-ie i rozważ dołożenie RAM-u (Upgrade Readiness podpowie, jaki pasuje).",
               "en": "Turn on XMP in the BIOS and consider more RAM (Upgrade Readiness says what fits)."},
    "drivers": {"pl": "Zaktualizuj sterownik karty graficznej (NVIDIA App / AMD Adrenalin).",
                "en": "Update the graphics driver (NVIDIA App / AMD Adrenalin)."},
    "startup": {"pl": "Wyłącz z autostartu to, czego nie potrzebujesz od razu po starcie.",
                "en": "Take out of startup what you do not need right after boot."},
}


def _lang():
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(k, lang, **kw):
    s = _TX[k][lang]
    return s.format(**kw) if kw else s


def _history_path():
    from utils.paths import APP_DIR
    return os.path.join(APP_DIR, "data", "cache", "health_reports.json")


def load_previous():
    try:
        items = json.load(open(_history_path(), encoding="utf-8"))
        return items[-1] if items else None
    except Exception:
        return None


def remember(report) -> None:
    p = _history_path()
    try:
        from utils.prefs_io import load_json, save_json
        items = load_json(p, [])
        if not isinstance(items, list):
            items = []
        items.append({"ts": report["ts"], "total": report["total"],
                      "parts": {x["key"]: x["score"] for x in report["parts"]}})
        save_json(p, items[-30:], indent=0)
    except Exception:
        pass


def build_report(scored: dict, findings_text: list, previous, lang: str, now=None) -> dict:
    """scored: core.health_score.score(); findings_text: [(sev, text)];
    previous: load_previous() or None."""
    from ui.components.health_center import part_text
    now = now or time.time()
    parts = []
    for p in scored.get("parts") or []:
        name, why = part_text(p, lang)
        parts.append({"key": p["key"], "name": name, "why": why, "score": p["score"]})
    changes = []
    if previous:
        d = time.strftime("%d.%m.%Y", time.localtime(previous["ts"]))
        if previous.get("total") is not None and scored.get("total") is not None \
                and previous["total"] != scored["total"]:
            changes.append(_tx("total_moved", lang, a=previous["total"], b=scored["total"], d=d))
        for p in parts:
            old = (previous.get("parts") or {}).get(p["key"])
            if old is not None and old != p["score"]:
                changes.append(_tx("moved", lang, p=p["name"], a=old, b=p["score"]))
        if not changes:
            changes.append(_tx("same", lang, d=d))
    else:
        changes.append(_tx("first", lang))
    todo = [{"name": p["name"], "do": _ACTION[p["key"]][lang], "score": p["score"]}
            for p in sorted(parts, key=lambda x: x["score"]) if p["score"] < 100][:3]
    return {"ts": now, "total": scored.get("total"), "parts": parts, "changes": changes,
            "todo": todo, "findings": findings_text}


def to_html(r: dict, lang: str) -> str:
    def esc(x):
        return html.escape(str(x))

    def col(s):
        return "#16a34a" if s >= 80 else "#d97706" if s >= 55 else "#dc2626"
    rows = "".join(
        f"<tr><td>{esc(p['name'])}</td><td>{esc(p['why'])}</td>"
        f"<td style='color:{col(p['score'])};font-weight:700'>{p['score']}</td></tr>" for p in r["parts"])
    todo = "".join(f"<li><b>{esc(t['name'])}</b>: {esc(t['do'])}</li>" for t in r["todo"]) \
        or f"<li>{esc(_tx('nothing', lang))}</li>"
    ch = "".join(f"<li>{esc(c)}</li>" for c in r["changes"])
    fi = "".join(f"<li>{'⚠ ' if s >= 1 else '✓ '}{esc(t)}</li>" for s, t in r["findings"])
    total = "--" if r["total"] is None else r["total"]
    date = time.strftime("%d.%m.%Y %H:%M", time.localtime(r["ts"]))
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(_tx('html_title', lang))}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:32px auto;padding:0 16px;color:#111827}}
h1{{margin:0 0 4px}}.score{{font-size:56px;font-weight:800;color:{col(r['total'] or 0)}}}
table{{border-collapse:collapse;width:100%}}td{{padding:6px 8px;border-bottom:1px solid #e5e7eb}}
h2{{font-size:13px;letter-spacing:.06em;color:#6b7280;margin-top:28px}}small{{color:#6b7280}}</style></head><body>
<h1>{esc(_tx('html_title', lang))}</h1><small>{esc(_tx('made', lang, d=date))}</small>
<h2>{esc(_tx('score', lang))}</h2><div class="score">{total}</div><table>{rows}</table>
<h2>{esc(_tx('todo', lang))}</h2><ol>{todo}</ol>
<h2>{esc(_tx('changes', lang))}</h2><ul>{ch}</ul>
<h2>{esc(_tx('all', lang))}</h2><ul>{fi}</ul></body></html>"""


def save_html(r: dict, lang: str) -> str:
    from utils.paths import APP_DIR
    folder = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.environ.get("PCW_APP_DIR") or not os.path.isdir(folder):
        folder = APP_DIR          # tests and probes never write to the Desktop
    name = time.strftime("PC_Workman_health_%Y-%m-%d_%H%M.html", time.localtime(r["ts"]))
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_html(r, lang))
    remember(r)
    return path


class _Box:
    def __init__(self):
        self.data = None


def _work(box, lang):
    try:
        from core.health_score import collect, score
        from hck_gpt.responses.builder import response_builder
        data = collect()
        texts = []
        for f in data.get("findings") or []:
            try:
                texts.append((f["sev"], response_builder._finding_text(f, lang)))
            except Exception:
                pass
        box.data = build_report(score(data), texts, load_previous(), lang)
    except Exception as e:
        print(f"[HealthReport] {e}")
        box.data = {"ts": time.time(), "total": None, "parts": [], "changes": [], "todo": [], "findings": []}


def build_health_report(app, parent):
    lang = _lang()
    root = tk.Frame(parent, bg=BG)
    root.pack(fill="both", expand=True)
    box = _Box()
    status = {"lbl": None}

    def _save():
        if box.data is None:
            return
        try:
            path = save_html(box.data, lang)
            status["lbl"].config(text=_tx("saved", lang, p=path), fg=GREEN)
            try:
                os.startfile(path)
            except Exception:
                pass
        except Exception as e:
            status["lbl"].config(text=str(e), fg=RED)

    def _center():
        try:
            app._yourpc_initial_tab = "health"
            app._handle_sidebar_navigation("my_pc")
        except Exception:
            pass

    from ui.components.hero_banner import hero_banner, nav_crumbs
    hero_banner(root, _tx("title", lang), _tx("sub", lang), stops=["#10b981", "#0ea5e9", "#6366f1"],
                height=112, crumbs=nav_crumbs(app, _tx("title", lang)),
                buttons=[(_tx("save", lang), _save, True), (_tx("center", lang), _center, False)])
    status["lbl"] = tk.Label(root, text="", font=(_BODY, 8, "bold"), bg=BG, fg=GREEN, anchor="w")
    status["lbl"].pack(fill="x", padx=16, pady=(6, 0))
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=16, pady=(4, 12))
    wait = tk.Label(body, text=_tx("checking", lang), font=(_BODY, 9), bg=BG, fg=MUTED)
    wait.pack(anchor="w", pady=8)
    threading.Thread(target=_work, args=(box, lang), daemon=True, name="health-report").start()

    def _poll():
        try:
            if not root.winfo_exists():
                return
        except Exception:
            return
        if box.data is None:
            root.after(150, _poll)
            return
        wait.destroy()
        _draw(body, box.data, lang)
    _poll()
    return root


def _section(parent, title):
    f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    f.pack(fill="x", pady=(0, 8))
    tk.Label(f, text=title, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", padx=12, pady=(8, 4))
    return f


def _draw(body, r, lang):
    top = tk.Frame(body, bg=BG)
    top.pack(fill="x")
    sc = _section(top, _tx("score", lang))
    sc.pack_configure(side="left", fill="y", padx=(0, 8))
    total = r["total"]
    col = GREEN if (total or 0) >= 80 else AMBER if (total or 0) >= 55 else RED
    tk.Label(sc, text="--" if total is None else str(total), font=(_HDR, 34, "bold"), bg=PANEL,
             fg=col if total is not None else MUTED).pack(padx=24, pady=(0, 10))
    ch = _section(top, _tx("changes", lang))
    ch.pack_configure(side="left", fill="both", expand=True)
    for c in r["changes"]:
        tk.Label(ch, text="·  " + c, font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w").pack(fill="x", padx=12)
    tk.Frame(ch, bg=PANEL, height=8).pack()

    td = _section(body, _tx("todo", lang))
    if r["todo"]:
        for i, t in enumerate(r["todo"], 1):
            row = tk.Frame(td, bg=PANEL)
            row.pack(fill="x", padx=12, pady=1)
            tk.Label(row, text=f"{i}.", font=(_HDR, 10, "bold"), bg=PANEL, fg=AMBER).pack(side="left", anchor="n")
            tk.Label(row, text=f"{t['name']}: {t['do']}", font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w",
                     justify="left", wraplength=820).pack(side="left", fill="x", padx=(6, 0))
    else:
        tk.Label(td, text=_tx("nothing", lang), font=(_BODY, 9), bg=PANEL, fg=GREEN, anchor="w").pack(fill="x", padx=12)
    tk.Frame(td, bg=PANEL, height=8).pack()

    al = _section(body, _tx("all", lang))
    for sev, text in r["findings"]:
        row = tk.Frame(al, bg=PANEL)
        row.pack(fill="x", padx=12)
        tk.Label(row, text="●", font=(_BODY, 8), bg=PANEL,
                 fg=RED if sev >= 2 else AMBER if sev == 1 else GREEN).pack(side="left", anchor="n")
        tk.Label(row, text=text, font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                 wraplength=820).pack(side="left", fill="x", padx=(6, 0))
    tk.Frame(al, bg=PANEL, height=8).pack()
