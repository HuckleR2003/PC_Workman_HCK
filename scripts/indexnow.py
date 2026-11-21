"""scripts/indexnow.py - tell Bing (and the engines that share IndexNow) which
pages of pcworkman.dev changed (2026-11-21).

Bing's index feeds the search in ChatGPT and Copilot, and Bing does not crawl a
small site often. IndexNow lets the site say "these URLs changed" right after
an upload, instead of waiting for a crawler.

Run it AFTER the files are live on the server, never before: IndexNow checks
the key file on the live domain, and a URL announced before it exists is a 404
the engine remembers.

    py scripts/indexnow.py --check                 # key file live? nothing is sent
    py scripts/indexnow.py https://pcworkman.dev/features/cleanup/ ...
    py scripts/indexnow.py --sitemap-since 2026-11-21   # every sitemap URL with lastmod >= date

The key is the file docs/<key>.txt (its content is the key itself). It is
public by design: it only proves that this site owns the announcement.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import urllib.request

HOST = "pcworkman.dev"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
ENDPOINT = "https://api.indexnow.org/indexnow"
# Cloudflare answers 403 to the default "Python-urllib" agent (2026-11-21)
UA = {"User-Agent": "PCWorkman-IndexNow/1.0"}


def key() -> str:
    for p in glob.glob(os.path.join(DOCS, "*.txt")):
        name = os.path.basename(p)[:-4]
        if re.fullmatch(r"[0-9a-f]{32}", name):
            with open(p, encoding="utf-8") as f:
                if f.read().strip() == name:
                    return name
    sys.exit("no IndexNow key file (docs/<32 hex>.txt containing its own name)")


def key_is_live(k: str) -> bool:
    try:
        req = urllib.request.Request(f"https://{HOST}/{k}.txt", headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200 and r.read().decode().strip() == k
    except Exception:
        return False


def sitemap_since(date: str) -> list:
    with open(os.path.join(DOCS, "sitemap.xml"), encoding="utf-8") as f:
        xml = f.read()
    out = []
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        mod = re.search(r"<lastmod>([^<]+)</lastmod>", block)
        if loc and mod and mod.group(1)[:10] >= date:
            out.append(loc.group(1).strip())
    return out


def submit(k: str, urls: list) -> int:
    urls = [u for u in dict.fromkeys(urls) if u.startswith(f"https://{HOST}/")]
    if not urls:
        print("nothing to submit")
        return 0
    body = json.dumps({"host": HOST, "key": k, "keyLocation": f"https://{HOST}/{k}.txt",
                       "urlList": urls[:10000]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8", **UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: HTTP {r.status} for {len(urls)} URL(s)")
        return r.status


def main(argv):
    k = key()
    live = key_is_live(k)
    print(f"key {k}: {'live' if live else 'NOT live yet - upload docs/' + k + '.txt first'}")
    if "--check" in argv or not live:
        return
    if "--sitemap-since" in argv:
        urls = sitemap_since(argv[argv.index("--sitemap-since") + 1])
    else:
        urls = [a for a in argv if a.startswith("https://")]
    submit(k, urls)


if __name__ == "__main__":
    main(sys.argv[1:])
