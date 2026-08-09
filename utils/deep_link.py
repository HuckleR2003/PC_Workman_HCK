# utils/deep_link.py
"""
THE one parser for pcworkman:// links.

Why this exists: 23 guides live on pcworkman.dev and the app can now link out
to them. This closes the loop in the other direction, so a guide can say
"open the Startup Manager" and the reader lands on that page instead of
hunting through a sidebar.

Contract:
  pcworkman://open/<page>              -> switch to a sidebar page
  pcworkman://guide/<slug>             -> open that guide in the browser
  pcworkman://ask?q=<text>             -> put a question into hck_GPT

Rules:
  - Parsing NEVER performs the action. It returns an intent, and the caller
    decides. A link arriving from a web page must not be able to make the app
    do anything by itself.
  - Only page ids in _PAGES are accepted. An unknown page is rejected rather
    than passed through, so a crafted link cannot reach an arbitrary handler.
  - `ask` returns text only. It is placed in the chat input for the user to
    send, never sent automatically.

Guarded by tests/test_deep_link.py.
"""
from __future__ import annotations

from urllib.parse import urlparse, parse_qs, unquote

SCHEME = "pcworkman"

# Sidebar pages a link may open. Anything not listed is refused.
# Verified against the page_id branches in ui/windows/main_window_expanded.py.
# A test fails the build if this drifts from the real router.
_PAGES = {
    "dashboard", "my_pc", "your_pc", "monitoring_alerts", "optimization",
    "startup_manager", "services_manager", "fan_control", "fans_hardware",
    "fans_usage_stats", "overclock", "statistics", "first_setup",
    "upgrade_readiness", "guide", "settings", "hck_labs", "live_graphs",
    "sensors",
}


def parse(url: str):
    """
    Turn a pcworkman:// URL into an intent dict, or None when it is not ours
    or not understood.

    Returns one of:
      {"action": "open",  "page": "<id>"}
      {"action": "guide", "slug": "<slug>"}
      {"action": "ask",   "text": "<question>"}
    """
    if not url or not isinstance(url, str):
        return None
    try:
        u = urlparse(url.strip())
    except Exception:
        return None
    if (u.scheme or "").lower() != SCHEME:
        return None

    # pcworkman://open/my_pc -> netloc "open", path "/my_pc"
    head = (u.netloc or "").lower()
    tail = unquote((u.path or "").strip("/"))

    if head == "open":
        page = tail.lower()
        return {"action": "open", "page": page} if page in _PAGES else None

    if head == "guide":
        slug = tail.strip().lower()
        # slugs are lowercase words joined by hyphens; refuse anything else so
        # a link cannot be used to build an arbitrary URL
        if slug and all(c.isalnum() or c == "-" for c in slug):
            return {"action": "guide", "slug": slug}
        return None

    if head == "ask":
        q = parse_qs(u.query or "").get("q", [""])[0].strip()
        return {"action": "ask", "text": q[:300]} if q else None

    return None


def from_argv(argv) -> list:
    """Every pcworkman:// intent found in a process argument list."""
    out = []
    for a in (argv or []):
        got = parse(a)
        if got:
            out.append(got)
    return out


def guide_url(slug: str, lang: str = "pl"):
    """Public URL for a guide slug, reusing the app's one guide map."""
    try:
        from hck_gpt.guide_links import url_for, GUIDES
        return url_for(slug, lang) if slug in GUIDES else None
    except Exception:
        return None
