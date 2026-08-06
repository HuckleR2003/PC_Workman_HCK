#!/usr/bin/env python3
"""
Regenerate the static roadmap snapshot after editing roadmap.json.

Usage from the repository root:
    python tools/build_roadmap_snapshot.py

The public page uses JSON for authoring and keeps a static HTML snapshot so
no-JS crawlers can index every feature.
"""
from pathlib import Path
import json, html, re
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/hck-labs/scaling-laws/assets/data/roadmap.json"
PAGE = ROOT / "docs/hck-labs/scaling-laws/roadmap/index.html"
MD = ROOT / "ROADMAP.md"

data = json.loads(DATA.read_text(encoding="utf-8"))
status_labels = {s["id"]: s["label"] for s in data["statuses"]}
lane_labels = {s["id"]: s["label"] for s in data["lanes"]}

def esc(value):
    return html.escape(str(value), quote=True)

items = []
for cat in data["categories"]:
    for index, row in enumerate(cat["items"], 1):
        items.append({
            "category": cat["id"],
            "categoryLabel": cat["label"],
            "title": row["title"],
            "status": row["status"],
            "lane": row["lane"],
            "description": row["description"],
            "slug": f'{cat["id"]}-{index:02d}',
        })

def card(item):
    checked = item["status"] == "shipped"
    return f"""<article class="slr-card" id="{esc(item['slug'])}" data-roadmap-item
      data-category="{esc(item['category'])}" data-status="{esc(item['status'])}"
      data-lane="{esc(item['lane'])}"
      data-search="{esc((item['title']+' '+item['description']+' '+item['categoryLabel']).lower())}">
      <div class="slr-card__top">
        <span class="slr-check {'is-checked' if checked else ''}" aria-hidden="true">{'✓' if checked else ''}</span>
        <div class="slr-card__meta">
          <span class="slr-status slr-status--{esc(item['status'])}">{esc(status_labels[item['status']])}</span>
          <span class="slr-lane">{esc(lane_labels[item['lane']])}</span>
        </div>
      </div>
      <h3>{esc(item['title'])}</h3>
      <p>{esc(item['description'])}</p>
      <a class="slr-anchor" href="#{esc(item['slug'])}" aria-label="Link to {esc(item['title'])}">#</a>
    </article>"""

def category(cat):
    subset = [i for i in items if i["category"] == cat["id"]]
    shipped = sum(i["status"] == "shipped" for i in subset)
    now = sum(i["lane"] == "now" for i in subset)
    return f"""<section class="slr-category" id="{esc(cat['id'])}" data-roadmap-category data-category-section="{esc(cat['id'])}">
      <header class="slr-category__head">
        <div><div class="slr-category__index">{esc(cat['short'])} / {len(subset):02d} items</div><h2>{esc(cat['label'])}</h2></div>
        <p>{esc(cat['description'])}</p>
        <div class="slr-category__counts"><span><strong>{shipped}</strong> shipped</span><span><strong>{now}</strong> now</span></div>
      </header>
      <div class="slr-grid">{''.join(card(i) for i in subset)}</div>
    </section>"""

snapshot = "\n".join(category(cat) for cat in data["categories"])
text = PAGE.read_text(encoding="utf-8")
start = "<!-- GENERATED FROM assets/data/roadmap.json. Do not hand-edit cards. -->"
end = '<div class="slr-empty"'
before, rest = text.split(start, 1)
_, after = rest.split(end, 1)
text = before + start + "\n" + snapshot + "\n\n        " + end + after
text = re.sub(r'data-roadmap-version="[^"]+"', f'data-roadmap-version="{esc(data["version"])}"', text, count=1)
PAGE.write_text(text, encoding="utf-8")

symbols = {"shipped":"✅","playable":"◆","polish":"◐","foundation":"◇","planned":"○"}
lines = [
    "# Scaling Laws — Roadmap",
    "",
    "> **SHIPPED means we stop making excuses for it.**",
    ">",
    f'> {data["rule"]}',
    "",
    f'Updated: **{data["updated"]}**',
    "",
    "Status: `✅ SHIPPED` · `◆ PLAYABLE` · `◐ POLISH` · `◇ FOUNDATION` · `○ PLANNED`",
    "",
]
for cat in data["categories"]:
    lines += [f"## {cat['label']}", "", cat["description"], ""]
    for item in cat["items"]:
        lines.append(
            f"- {symbols[item['status']]} **{item['title']}** — "
            f"{item['description']} _[{item['lane'].upper()}]_"
        )
    lines.append("")
MD.write_text("\n".join(lines), encoding="utf-8")
print(f"Updated {PAGE}")
print(f"Updated {MD}")
