# pcworkman.dev

Static bilingual website for PC Workman. The site is served from `docs/` and
uses plain HTML, CSS and JavaScript.

## Current product facts

Check these against the source before every content update:

- Version: `utils/app_version.py -> APP_VERSION`
- hck_GPT intents: `hck_gpt/intents/vocabulary.py`
- Process definitions: `data/process_library.json`
- Hardware compatibility: `core/hardware_compat_db.py`
- Privacy and telemetry: `core/network.py` and `core/telemetry.py`
- Release notes: `README.md` and GitHub Releases

Historical blog articles keep the facts and counters that were true when each
article was published. Current facts belong on landing, download, profile,
roadmap and `llms*.txt` pages.

## Main files

```text
docs/
├── index.html                 # Polish landing
├── index_en.html              # English landing
├── download/                  # English and Polish download pages
├── privacy.html               # Polish privacy policy
├── privacy_en.html            # English privacy policy
├── SECURITY_report.html       # Security and release verification
├── roadmap/                   # Public roadmap
├── blog/                      # Blog hub, three series and RSS
├── guides/                    # Evergreen guides
├── assets/css/                # Shared styles
├── assets/js/                 # Shared interactions
├── assets/images/             # Screenshots and social images
├── llms.txt                   # Short AI/search reference
├── llms-full.txt              # Full technical reference
├── sitemap.xml
├── robots.txt
└── 404.html
```

## Integrity audit

Run from the repository root:

```powershell
python scripts/audit_site.py
```

The audit checks all HTML files for:

- required language, title, description and canonical metadata;
- one H1 per page;
- duplicate IDs and missing image alt text;
- broken local files and fragments;
- unsafe `target="_blank"` links;
- JSON-LD and XML parsing;
- sitemap targets, sitemap completeness and RSS integrity;
- current source-derived version, intent, process and hardware counts;
- stale learning-duration, telemetry and author-profile claims;
- forms without a real action.

For a network-dependent check of all unique outbound links:

```powershell
python scripts/audit_site.py --external
```

HTTP 401, 403 and 429 responses are reported as warnings because some services
block automated probes even when the public link works.

## Content rules

- Keep Polish and English current pages in sync.
- Do not claim that the whole app has zero network traffic. Monitoring and
  hck_GPT are local, while the current release can send a documented anonymous
  hardware snapshot. The switch is in Settings.
- Do not add a newsletter form unless it is connected to a real backend.
- Use dated labels for mutable GitHub and social counters.
- Add new pages to `sitemap.xml` and update relevant hreflang links.
- Preserve the existing design and shared navigation unless a redesign is the
  explicit task.

## Local preview

Serve `docs/` through any static HTTP server. Do not open the files directly
when testing root-relative links such as `/assets/...`.
