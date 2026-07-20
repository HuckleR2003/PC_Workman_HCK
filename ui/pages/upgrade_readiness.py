# ui/pages/upgrade_readiness.py
"""
Upgrade Readiness page - "will that part fit this PC?"

Reached from My PC > Components (per-part buttons), First Setup & Drivers and
Monitoring & Alerts, via ExpandedMainWindow.open_upgrade_readiness(). All the
intelligence lives in core/hardware_compat.py - this file only renders:

  YOUR PLATFORM card  - live machine identity (socket / chipset / GPU / RAM)
  search row          - type the planned purchase ('i5 11400F', 'RTX 4070',
                        'DDR5 6000'), Enter or CHECK
  quick-pick chips    - suggest_upgrades() picks that make sense HERE
  verdict card        - green / amber / red with reasons and notes
"""
import threading
import tkinter as tk

try:
    from utils.fonts import UI as _UIF, MONO as _MONOF
except ImportError:
    _UIF, _MONOF = "Segoe UI", "Consolas"
_HDR = "Segoe UI Semibold"
_BODY = _UIF
_MONO = _MONOF

BG = "#0a0e14"
CARD = "#10141d"
LINE = "#1e2535"

# verdict -> accent colour (green = go, amber = go with homework, red = stop)
_VERDICT_COLOR = {
    "compatible": "#10b981", "info": "#10b981",
    "bios_update": "#f59e0b", "vendor_dependent": "#f59e0b",
    "check_support_list": "#f59e0b", "downgrade": "#f59e0b",
    "chipset_blocked": "#ef4444", "needs_new_board": "#ef4444",
    "incompatible": "#ef4444",
    "unknown_part": "#64748b", "unknown_current": "#64748b",
}

# verdict -> loud status badge on the verdict card (one-glance answer)
_VERDICT_BADGE = {
    "compatible": "FITS", "info": "OK",
    "bios_update": "BIOS UPDATE", "vendor_dependent": "CHECK VENDOR",
    "check_support_list": "VERIFY", "downgrade": "DOWNGRADE",
    "chipset_blocked": "BLOCKED", "needs_new_board": "NEW BOARD",
    "incompatible": "NOT COMPATIBLE",
    "unknown_part": "UNKNOWN", "unknown_current": "NO DATA",
}


def build_upgrade_readiness_page(win, parent, focus=None):
    """Build the page into *parent*. `focus` preselects a chip row
    ('cpu' | 'gpu' | 'ram') when the user arrived from a specific part."""
    from core import hardware_compat as hc

    page = tk.Frame(parent, bg=BG)
    page.pack(fill="both", expand=True, padx=14, pady=(8, 6))

    # ── YOUR PLATFORM ────────────────────────────────────────────────────
    plat_card = tk.Frame(page, bg=CARD, highlightbackground=LINE,
                         highlightthickness=1)
    plat_card.pack(fill="x")
    plat_head = tk.Frame(plat_card, bg=CARD)
    plat_head.pack(fill="x", padx=12, pady=(8, 2))
    tk.Label(plat_head, text="YOUR PLATFORM", font=(_MONO, 8, "bold"),
             bg=CARD, fg="#64748b").pack(side="left")
    plat_line = tk.Label(plat_head, text="", font=(_MONO, 8, "bold"),
                         bg=CARD, fg="#10b981")
    plat_line.pack(side="right")
    plat_body = tk.Frame(plat_card, bg=CARD)
    plat_body.pack(fill="x", padx=12, pady=(0, 8))
    loading = tk.Label(plat_body, text="Reading your hardware...",
                       font=(_BODY, 9), bg=CARD, fg="#6b7280")
    loading.pack(anchor="w")

    state = {"plat": None}

    def _plat_cell(row, label, value):
        cell = tk.Frame(row, bg=CARD)
        cell.pack(side="left", fill="x", expand=True)
        tk.Label(cell, text=label, font=(_BODY, 7), bg=CARD,
                 fg="#6b7280", anchor="w").pack(fill="x")
        tk.Label(cell, text=value or "not detected", font=(_BODY, 9, "bold"),
                 bg=CARD, fg="#e2e8f0" if value else "#4b5563",
                 anchor="w").pack(fill="x")

    def _render_platform():
        try:
            if not plat_body.winfo_exists():
                return
        except Exception:
            return
        plat = state["plat"] or {}
        try:
            loading.destroy()
        except Exception:
            pass
        plat_line.config(text=hc.platform_label(plat))
        row = tk.Frame(plat_body, bg=CARD)
        row.pack(fill="x")
        cpu = plat.get("cpu")
        gpu = plat.get("gpu")
        _plat_cell(row, "CPU", cpu["label"] if cpu
                   else (plat.get("cpu_name") or "").strip()[:34])
        _plat_cell(row, "MOTHERBOARD",
                   " / ".join(filter(None, [plat.get("chipset"),
                                            plat.get("socket")])))
        _plat_cell(row, "GPU", gpu["label"] if gpu
                   else (plat.get("gpu_name") or "").strip()[:30])
        ram_bits = [plat.get("ram_type") or ""]
        if plat.get("ram_speed"):
            ram_bits.append(f"{plat['ram_speed']} MHz")
        _plat_cell(row, "RAM", " ".join(b for b in ram_bits if b).strip())
        _render_chips()

    def _load_platform():
        # Worker thread: only compute, then one after(0) hop to the UI.
        try:
            state["plat"] = hc.current_platform()
        except Exception:
            state["plat"] = {}
        try:
            page.after(0, _render_platform)
        except Exception:
            pass

    # ── Search row ───────────────────────────────────────────────────────
    search = tk.Frame(page, bg=BG)
    search.pack(fill="x", pady=(10, 0))
    box = tk.Frame(search, bg="#12161f", highlightbackground="#2a3348",
                   highlightthickness=1)
    box.pack(side="left", fill="x", expand=True)
    entry = tk.Entry(box, font=(_MONO, 11), bg="#12161f", fg="#e8edf6",
                     insertbackground="#10b981", relief="flat", bd=0)
    entry.pack(fill="x", padx=10, ipady=7)

    btn = tk.Label(search, text="CHECK", font=(_MONO, 10, "bold"),
                   bg="#10b981", fg="#04110b", padx=18, pady=8,
                   cursor="hand2")
    btn.pack(side="left", padx=(8, 0))
    btn.bind("<Enter>", lambda e: btn.config(bg="#34d399"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#10b981"))

    tk.Label(page, text="Type the part you plan to buy - a CPU "
                        "(i5 11400F, Ryzen 7 5800X3D), a GPU (RTX 4070, "
                        "RX 7800 XT) or RAM (DDR5 6000).",
             font=(_BODY, 8), bg=BG, fg="#6b7280",
             anchor="w").pack(fill="x", pady=(4, 0))

    # ── Quick-pick chips ─────────────────────────────────────────────────
    chips_row = tk.Frame(page, bg=BG)
    chips_row.pack(fill="x", pady=(6, 0))

    def _chip(parent_row, text, query):
        c = tk.Label(parent_row, text=text, font=(_MONO, 8), bg="#161b28",
                     fg="#94a3b8", padx=9, pady=3, cursor="hand2")
        c.pack(side="left", padx=(0, 6), pady=2)
        c.bind("<Enter>", lambda e: c.config(bg="#1f2739", fg="#e2e8f0"))
        c.bind("<Leave>", lambda e: c.config(bg="#161b28", fg="#94a3b8"))
        c.bind("<Button-1>", lambda e: _run_check(query))

    def _render_chips():
        try:
            if not chips_row.winfo_exists():
                return
        except Exception:
            return
        for w in chips_row.winfo_children():
            w.destroy()
        try:
            sug = hc.suggest_upgrades(state["plat"])
        except Exception:
            return
        order = ["cpu", "gpu", "ram"]
        if focus in order:                      # arrived from a specific part
            order.remove(focus)
            order.insert(0, focus)
        tk.Label(chips_row, text="TRY:", font=(_MONO, 8, "bold"),
                 bg=BG, fg="#4b5563").pack(side="left", padx=(0, 8))
        shown = 0
        for kind in order:
            for rec in sug.get(kind, []):
                if shown >= 6:
                    break
                if isinstance(rec, str):        # RAM entries are plain text
                    _chip(chips_row, rec, rec)
                else:
                    short = rec["label"].replace("Intel Core ", "") \
                                        .replace("NVIDIA GeForce ", "") \
                                        .replace("AMD Radeon ", "") \
                                        .replace("AMD ", "").replace("Intel ", "")
                    _chip(chips_row, short, short)
                shown += 1

    # ── Verdict area ─────────────────────────────────────────────────────
    result = tk.Frame(page, bg=BG)
    result.pack(fill="both", expand=True, pady=(10, 0))

    def _render_verdict(v):
        for w in result.winfo_children():
            w.destroy()
        color = _VERDICT_COLOR.get(v.get("verdict"), "#64748b")
        card = tk.Frame(result, bg=CARD, highlightbackground=LINE,
                        highlightthickness=1)
        card.pack(fill="x")
        bar = tk.Frame(card, bg=color, width=4)
        bar.pack(side="left", fill="y")
        body = tk.Frame(card, bg=CARD)
        body.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        tgt = v.get("target")
        title = tgt["label"] if tgt else (v.get("target_text") or "").strip()
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text=title, font=(_HDR, 11, "bold"), bg=CARD,
                 fg="#e8edf6", anchor="w").pack(side="left")
        if tgt and tgt.get("kind") == "cpu":
            tk.Label(top, text=f"{tgt['socket']} · {tgt['cores']}C/"
                               f"{tgt['threads']}T · {tgt['tdp']} W",
                     font=(_MONO, 8), bg=CARD, fg="#4b5563").pack(
                side="right")
        elif tgt and tgt.get("kind") == "gpu":
            tk.Label(top, text=f"{tgt['vram_gb']} GB · {tgt['tdp']} W · "
                               f"PSU {tgt['rec_psu']} W",
                     font=(_MONO, 8), bg=CARD, fg="#4b5563").pack(
                side="right")

        # Headline + loud status badge: the answer readable from across the
        # room - colour bar (left), coloured headline AND a filled pill.
        head_row = tk.Frame(body, bg=CARD)
        head_row.pack(fill="x", pady=(4, 6))
        tk.Label(head_row, text=v.get("headline", ""), font=(_HDR, 13, "bold"),
                 bg=CARD, fg=color, anchor="w").pack(side="left")
        badge_txt = _VERDICT_BADGE.get(v.get("verdict"), "RESULT")
        badge_fg = "#ffffff" if color == "#ef4444" else "#081018"
        tk.Label(head_row, text=f" {badge_txt} ", font=(_MONO, 9, "bold"),
                 bg=color, fg=badge_fg, padx=8, pady=3).pack(side="right")
        for r in v.get("reasons", []):
            tk.Label(body, text="-  " + r, font=(_BODY, 9), bg=CARD,
                     fg="#cbd5e1", anchor="w", justify="left",
                     wraplength=820).pack(fill="x", pady=1)
        for n in v.get("notes", []):
            tk.Label(body, text="*  " + n, font=(_BODY, 8), bg=CARD,
                     fg="#8593a8", anchor="w", justify="left",
                     wraplength=820).pack(fill="x", pady=1)

    def _run_check(prefill=None):
        if prefill is not None:
            entry.delete(0, "end")
            entry.insert(0, prefill)
        text = entry.get().strip()
        if not text:
            return
        try:
            v = hc.check_upgrade(text, state["plat"])
        except Exception as ex:
            v = {"verdict": "unknown_part", "headline": "Check failed",
                 "reasons": [f"Internal error: {ex}"], "notes": [],
                 "target": None, "target_text": text}
        _render_verdict(v)

    btn.bind("<Button-1>", lambda e: _run_check())
    entry.bind("<Return>", lambda e: _run_check())

    # ── Footer ───────────────────────────────────────────────────────────
    try:
        s = hc.db_stats()
        foot = (f"Offline library v{s['version']}: {s['cpus']} CPUs · "
                f"{s['gpus']} GPUs · {s['chipsets']} chipsets. Guidance only - "
                "always cross-check the board vendor's CPU support list.")
    except Exception:
        foot = "Offline library. Cross-check the board vendor's support list."
    tk.Label(page, text=foot, font=(_BODY, 7), bg=BG,
             fg="#4b5563", anchor="w").pack(fill="x", side="bottom",
                                            pady=(6, 0))

    threading.Thread(target=_load_platform, daemon=True,
                     name="UpgradeReadinessScan").start()
    try:
        entry.focus_set()
    except Exception:
        pass
