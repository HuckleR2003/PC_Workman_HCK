"""ui.components.slowdown_panel - "What slows this PC down", on screen
(2026-11-20).

My PC → Performance showed live clocks and cores and nothing that said what
they mean. Marcin: "I don't know myself what should be key here". hck_GPT
already knew (core/pc_insight): the weakest part, the CPU held back by
heat or a power limit, RAM against this PC's normal, virtual memory, drives,
driver age, hardware errors, heavy startup. This panel shows the same
conclusions, in the same words as the chat:

    verdict      the bottleneck answer (hck_GPT "do I have a bottleneck")
    findings     each one a coloured line: fix it / worth knowing / fine
    three tiles  the CPU clock now, virtual memory, what runs in the background

The findings read the drives and the event log (a few seconds), so they come
from a background thread that touches no Tk object.
"""
from __future__ import annotations

import threading
import tkinter as tk

from utils.fonts import UI as _BODY, HDR as _HDR

BG = "#0b0f16"
PANEL = "#0f141c"
PANEL2 = "#131a24"
LINE = "#1f2937"
TEXT = "#e5e7eb"
MUTED = "#8d97a8"
SEV_COL = {2: "#f87171", 1: "#fbbf24", 0: "#34d399"}

_TX = {
    "title": {"pl": "Co spowalnia ten komputer", "en": "What slows this PC down"},
    "checking": {"pl": "Sprawdzam historię, dyski i dziennik Windows…",
                 "en": "Checking the history, the drives and the Windows log…"},
    "fine_head": {"pl": "Sprawdzone i w porządku", "en": "Checked and fine"},
    "clock": {"pl": "PROCESOR TERAZ", "en": "PROCESSOR NOW"},
    "clock_v": {"pl": "{mhz} MHz  ·  {lim}% mocy", "en": "{mhz} MHz  ·  {lim}% of power"},
    "clock_free": {"pl": "nic go nie hamuje", "en": "nothing holds it back"},
    "clock_held": {"pl": "przyhamowany: temperatura albo limit mocy", "en": "held back: heat or a power limit"},
    "pf": {"pl": "PAMIĘĆ WIRTUALNA", "en": "VIRTUAL MEMORY"},
    "pf_none": {"pl": "wyłączona", "en": "off"},
    "pf_auto": {"pl": "zarządza Windows", "en": "managed by Windows"},
    "pf_custom": {"pl": "ustawiona ręcznie", "en": "set by hand"},
    "bg": {"pl": "W TLE", "en": "IN THE BACKGROUND"},
    "bg_v": {"pl": "TURBO: {a} z {n} uzbrojone", "en": "TURBO: {a} of {n} armed"},
}


def _lang() -> str:
    try:
        from utils.i18n import get_lang
        return "en" if get_lang() == "en" else "pl"
    except Exception:
        return "pl"


def _tx(k, **kw):
    s = _TX[k][_lang()]
    return s.format(**kw) if kw else s


def collect(lang: str) -> dict:
    """The panel's data; plain Python."""
    out = {"verdict": [], "findings": [], "clock": {}, "pf": {}, "turbo": (0, 0)}
    try:
        from hck_gpt.responses.builder import response_builder
        from hck_gpt.intents.parser import ParseResult
        lines = response_builder._resp_bottleneck(ParseResult("bottleneck", 1.0, raw_text=""), lang)
        out["verdict"] = [l.replace(response_builder.PREFIX, "").strip() for l in lines
                          if "[->" not in l and l.strip()]
        from core.pc_insight import findings
        for f in findings(deep=True):
            try:
                out["findings"].append((f["sev"], response_builder._finding_text(f, lang)))
            except Exception:
                continue
    except Exception as e:
        out["verdict"] = [str(e)]
    try:
        from core.pc_insight import cpu_clock
        out["clock"] = cpu_clock(0.5)
    except Exception:
        pass
    try:
        from core.pagefile import info
        out["pf"] = info()
    except Exception:
        pass
    try:
        from ui.pages.optimization_services import turbo_armed_summary
        armed = turbo_armed_summary()
        out["turbo"] = (sum(1 for _, on in armed if on), len(armed))
    except Exception:
        pass
    return out


class _Box:
    def __init__(self):
        self.data = None


def _work(box, lang):
    box.data = collect(lang)


def build_slowdown_panel(parent) -> tk.Frame:
    lang = _lang()
    root = tk.Frame(parent, bg=BG)
    root.pack(fill="x", padx=8, pady=(6, 4))
    head = tk.Frame(root, bg=BG)
    head.pack(fill="x")
    tk.Frame(head, bg="#a78bfa", width=3, height=18).pack(side="left", padx=(0, 8))
    tk.Label(head, text=_tx("title"), font=(_HDR, 12, "bold"), bg=BG, fg=TEXT).pack(side="left")

    body = tk.Frame(root, bg=BG)
    body.pack(fill="x", pady=(6, 0))
    left = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    left.pack(side="left", fill="both", expand=True)
    tiles = tk.Frame(body, bg=BG, width=230)
    tiles.pack(side="right", fill="y", padx=(8, 0))
    tiles.pack_propagate(False)
    wait = tk.Label(left, text=_tx("checking"), font=(_BODY, 9), bg=PANEL, fg=MUTED)
    wait.pack(padx=12, pady=14, anchor="w")

    box = _Box()
    threading.Thread(target=_work, args=(box, lang), daemon=True, name="slowdown").start()

    def _poll():
        try:
            if not root.winfo_exists():
                return
        except Exception:
            return
        if box.data is None:
            root.after(150, _poll)
            return
        _fill(left, tiles, box.data)
    _poll()
    return root


def _tile(parent, cap, value, sub, col=TEXT):
    f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
    f.pack(fill="x", pady=(0, 6))
    tk.Label(f, text=cap, font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED, anchor="w").pack(fill="x", padx=10, pady=(6, 0))
    tk.Label(f, text=value, font=(_HDR, 11, "bold"), bg=PANEL, fg=col, anchor="w").pack(fill="x", padx=10)
    tk.Label(f, text=sub, font=(_BODY, 7), bg=PANEL, fg=MUTED, anchor="w", justify="left",
             wraplength=200).pack(fill="x", padx=10, pady=(0, 6))


def _fill(left, tiles, d):
    for w in left.winfo_children():
        w.destroy()
    for i, line in enumerate(d.get("verdict") or []):
        tk.Label(left, text=line, font=(_BODY, 10, "bold") if i == 0 else (_BODY, 9),
                 bg=PANEL, fg=TEXT if i == 0 else MUTED, anchor="w", justify="left",
                 wraplength=620).pack(fill="x", padx=12, pady=(10 if i == 0 else 2, 0))
    tk.Frame(left, bg=LINE, height=1).pack(fill="x", padx=12, pady=8)
    fine = [t for s, t in d.get("findings") or [] if s == 0]
    for sev, text in d.get("findings") or []:
        if sev == 0:
            continue
        row = tk.Frame(left, bg=PANEL)
        row.pack(fill="x", padx=12, pady=2)
        tk.Label(row, text="●", font=(_BODY, 9), bg=PANEL, fg=SEV_COL.get(sev, MUTED)).pack(side="left", anchor="n")
        tk.Label(row, text=text, font=(_BODY, 9), bg=PANEL, fg=TEXT, anchor="w", justify="left",
                 wraplength=600).pack(side="left", fill="x", padx=(6, 0))
    if fine:
        tk.Label(left, text=_tx("fine_head"), font=(_BODY, 7, "bold"), bg=PANEL, fg=MUTED,
                 anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        for text in fine:
            row = tk.Frame(left, bg=PANEL)
            row.pack(fill="x", padx=12, pady=1)
            tk.Label(row, text="●", font=(_BODY, 8), bg=PANEL, fg=SEV_COL[0]).pack(side="left", anchor="n")
            tk.Label(row, text=text, font=(_BODY, 8), bg=PANEL, fg=MUTED, anchor="w", justify="left",
                     wraplength=600).pack(side="left", fill="x", padx=(6, 0))
    tk.Frame(left, bg=PANEL, height=8).pack()

    for w in tiles.winfo_children():
        w.destroy()
    clk = d.get("clock") or {}
    if clk.get("actual"):
        lim = clk.get("limit_pct") or 100
        _tile(tiles, _tx("clock"), _tx("clock_v", mhz=f"{clk['actual']:.0f}", lim=f"{lim:.0f}"),
              _tx("clock_free") if lim >= 95 else _tx("clock_held"),
              TEXT if lim >= 95 else SEV_COL[1])
    pf = d.get("pf") or {}
    mode = pf.get("mode")
    if mode:
        sub = {"none": _tx("pf_none"), "custom": _tx("pf_custom")}.get(mode, _tx("pf_auto"))
        val = f"{pf['size_gb']:.0f} GB" if pf.get("size_gb") else "--"
        _tile(tiles, _tx("pf"), val, sub, SEV_COL[2] if mode == "none" else TEXT)
    a, n = d.get("turbo") or (0, 0)
    if n:
        _tile(tiles, _tx("bg"), _tx("bg_v", a=a, n=n), "", TEXT)
