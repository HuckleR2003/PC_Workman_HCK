#!/usr/bin/env python3
"""
Tiny maintenance reminder for Scaling Laws publishing.

This does not invent post metadata. Add a new devlog page first, then update:
1. docs/hck-labs/scaling-laws/devlog/index.html
2. docs/hck-labs/scaling-laws/devlog/feed.xml
3. docs/llms.txt
4. docs/sitemap.xml

The sitemap in this repository is generated from canonical HTML pages by the
existing site tooling, so after the new page exists, run the normal sitemap
builder and verify the canonical was discovered.
"""
print(__doc__)
