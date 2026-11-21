"""Build docs/sitemap.xml from indexable HTML canonicals.

The HTML is the source of truth. Reciprocal hreflang is validated separately by
scripts/audit_site.py; this builder copies the complete set declared by each
page into its sitemap entry. Existing lastmod values are preserved when a page
does not expose a newer dateModified value.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITEMAP = DOCS / "sitemap.xml"
SITE = "https://pcworkman.dev/"

_CANONICAL_RE = re.compile(
    r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_ALTERNATE_RE = re.compile(
    r'<link\s+rel=["\']alternate["\']\s+hreflang=["\']([^"\']+)["\']'
    r'\s+href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_ROBOTS_RE = re.compile(
    r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_MODIFIED_PATTERNS = (
    re.compile(
        r'<meta\s+property=["\']article:modified_time["\']\s+'
        r'content=["\'](\d{4}-\d{2}-\d{2})',
        re.IGNORECASE,
    ),
    re.compile(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})'),
)


def _existing_lastmods() -> dict[str, str]:
    if not SITEMAP.exists():
        return {}
    try:
        root = ET.parse(SITEMAP).getroot()
    except ET.ParseError:
        return {}
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    out: dict[str, str] = {}
    for node in root.findall("s:url", ns):
        loc = node.findtext("s:loc", default="", namespaces=ns)
        lastmod = node.findtext("s:lastmod", default="", namespaces=ns)
        if loc and lastmod:
            out[loc] = lastmod
    return out


def _priority(url: str) -> tuple[str, str]:
    path = url.removeprefix(SITE)
    if path in {"", "index.html", "index_en.html"}:
        return "weekly", "1.0"
    if path in {
        "download/",
        "download/index_pl.html",
        "blog/",
        "blog/index_pl.html",
        "guides/",
        "guides/index_pl.html",
        "roadmap/",
        "roadmap/index_pl.html",
        # The labs hub and the game page are section entry points, not leaf content. They were
        # falling through to the 0.6 default, which gave them the same weight as an individual blog
        # post and left the sitemap with no hierarchy to describe.
        "hck-labs/",
        "hck-labs/scaling-laws/",
    }:
        return "weekly", "0.9"
    if path.startswith("guides/"):
        return "monthly", "0.8"
    if path.startswith("blog/"):
        return "monthly", "0.7"
    return "monthly", "0.6"


def _page_record(path: Path, old_dates: dict[str, str]) -> dict[str, object] | None:
    source = path.read_text(encoding="utf-8")
    canonical_match = _CANONICAL_RE.search(source)
    if not canonical_match:
        return None
    canonical = canonical_match.group(1)
    if not canonical.startswith(SITE):
        raise ValueError(f"{path}: canonical must use {SITE}")

    robots_match = _ROBOTS_RE.search(source)
    if robots_match and "noindex" in robots_match.group(1).lower():
        return None

    alternates: dict[str, str] = {}
    for language, target in _ALTERNATE_RE.findall(source):
        language = language.lower()
        if language in alternates and alternates[language] != target:
            raise ValueError(f"{path}: duplicate hreflang {language}")
        alternates[language] = target

    modified = ""
    for pattern in _MODIFIED_PATTERNS:
        match = pattern.search(source)
        if match:
            modified = match.group(1)
            break
    if not modified:
        modified = old_dates.get(canonical, "2026-07-25")

    changefreq, priority = _priority(canonical)
    return {
        "canonical": canonical,
        "lastmod": modified,
        "alternates": alternates,
        "changefreq": changefreq,
        "priority": priority,
        "path": path,
    }


def build() -> int:
    old_dates = _existing_lastmods()
    records = [
        record
        for path in sorted(DOCS.rglob("*.html"))
        if "google" not in path.name.lower()
        if (record := _page_record(path, old_dates)) is not None
    ]

    by_url: dict[str, dict[str, object]] = {}
    for record in records:
        canonical = str(record["canonical"])
        if canonical in by_url:
            raise ValueError(
                f"Duplicate canonical {canonical}: "
                f"{by_url[canonical]['path']} and {record['path']}"
            )
        by_url[canonical] = record

    for record in records:
        for language, target in dict(record["alternates"]).items():
            if target not in by_url:
                raise ValueError(
                    f"{record['path']}: hreflang {language} target missing from "
                    f"indexable canonicals: {target}"
                )

    records.sort(
        key=lambda item: (
            -float(str(item["priority"])),
            str(item["canonical"]),
        )
    )

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!-- Generated from indexable HTML canonicals by scripts/build_sitemap.py. -->",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
        "",
    ]
    lang_order = {"en": 0, "pl": 1, "x-default": 2}
    for record in records:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{html.escape(str(record['canonical']), quote=True)}</loc>",
                f"    <lastmod>{record['lastmod']}</lastmod>",
                f"    <changefreq>{record['changefreq']}</changefreq>",
                f"    <priority>{record['priority']}</priority>",
            ]
        )
        alternates = dict(record["alternates"])
        for language, target in sorted(
            alternates.items(), key=lambda pair: (lang_order.get(pair[0], 99), pair[0])
        ):
            lines.append(
                '    <xhtml:link rel="alternate" '
                f'hreflang="{html.escape(language, quote=True)}" '
                f'href="{html.escape(target, quote=True)}"/>'
            )
        lines.extend(["  </url>", ""])
    lines.append("</urlset>")
    SITEMAP.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {SITEMAP.relative_to(ROOT)} with {len(records)} URLs.")
    return len(records)


if __name__ == "__main__":
    build()
