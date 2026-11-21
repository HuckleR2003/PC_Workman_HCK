"""Static integrity audit for the PC Workman website.

The site is plain HTML under ``docs/``. This script intentionally uses only the
Python standard library so it can run before every content pass and in CI
without installing a browser or an HTML package.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


SITE_HOSTS = {"pcworkman.dev", "www.pcworkman.dev"}
SKIP_SCHEMES = {"data", "javascript", "mailto", "tel"}
STALE_AUTHOR_OR_PLACEHOLDER = (
    "@firmuga.marcin.s",
    "github.com/yourusername",
    "nl.linkedin.com",
)
CURRENT_FACT_SURFACES = (
    "index.html",
    "index_en.html",
    "download/index.html",
    "download/index_pl.html",
    "llms.txt",
    "llms-full.txt",
    "blog/profile.html",
    "blog/profile_pl.html",
    "roadmap/index.html",
    "roadmap/index_pl.html",
)
CURRENT_VERSION_SURFACES = CURRENT_FACT_SURFACES + (
    "SECURITY_report.html",
    "SECURITY_report_pl.html",
)
BLOG_HUBS = ("blog/index.html", "blog/index_pl.html")
PROCESS_FACT_SURFACES = (
    "index.html",
    "index_en.html",
    "llms.txt",
    "llms-full.txt",
    "blog/profile.html",
    "blog/profile_pl.html",
    "roadmap/index.html",
    "roadmap/index_pl.html",
    "guides/what-is-this-process/index.html",
    "guides/what-is-this-process/index_pl.html",
    "guides/jak-przyspieszyc-komputer/index.html",
    "guides/jak-przyspieszyc-komputer/index_en.html",
)
SERVICE_PROFILE_SURFACES = (
    "index.html",
    "index_en.html",
    "guides/ktore-uslugi-windows-wylaczyc/index.html",
    "guides/ktore-uslugi-windows-wylaczyc/index_en.html",
)
SERVICE_GUARD_SURFACES = (
    "guides/ktore-uslugi-windows-wylaczyc/index.html",
    "guides/ktore-uslugi-windows-wylaczyc/index_en.html",
)
HARDWARE_FULL_FACT_SURFACES = (
    "index.html",
    "llms.txt",
    "llms-full.txt",
    "blog/profile_pl.html",
    "roadmap/index_pl.html",
)
CPU_CHIPSET_FACT_SURFACES = (
    "guides/will-this-cpu-fit-motherboard/index.html",
    "guides/will-this-cpu-fit-motherboard/index_pl.html",
)
TEST_FACT_SURFACES = (
    "index.html",
    "index_en.html",
    "llms.txt",
    "llms-full.txt",
    "blog/profile.html",
    "blog/profile_pl.html",
    "blog/road-to-1.8.0_pl.html",
)
ENGLISH_ARCHIVE_PREFIXES = (
    "blog/monday-grind-blueprint/",
    "blog/wednesday-code-autopsy/",
    "blog/friday-shipped-scarred/",
)
HOST_VERIFICATION_RE = re.compile(r"^google[a-f0-9]+\.html$", re.IGNORECASE)
EXTERNAL_PROBE_EXCLUSIONS = {
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
}
LEARNING_FACT_SURFACES = (
    "index.html",
    "index_en.html",
    "guides/normal-cpu-temperature/index.html",
    "guides/normal-cpu-temperature/index_pl.html",
    "guides/ai-pc-monitoring-vs-traditional/index.html",
    "guides/ai-pc-monitoring-vs-traditional/index_pl.html",
)
MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "â€™", "â€œ", "â€\x9d", "Ä…", "Å‚")


REQUIRED_BILINGUAL_SURFACES = (
    ("index_en.html", "index.html"),
    ("download/index.html", "download/index_pl.html"),
    ("blog/index.html", "blog/index_pl.html"),
    ("blog/profile.html", "blog/profile_pl.html"),
    ("blog/road-to-1.8.0_en.html", "blog/road-to-1.8.0_pl.html"),
    ("blog/story_en.html", "blog/story.html"),
    (
        "blog/the-man-who-got-himself-back_en.html",
        "blog/the-man-who-got-himself-back_pl.html",
    ),
    (
        "blog/from-a-warehouse-floor-to-the-microsoft-store/index.html",
        "blog/from-a-warehouse-floor-to-the-microsoft-store/index_pl.html",
    ),
    (
        "blog/monday-grind-blueprint/index.html",
        "blog/monday-grind-blueprint/index_pl.html",
    ),
    (
        "blog/wednesday-code-autopsy/index.html",
        "blog/wednesday-code-autopsy/index_pl.html",
    ),
    (
        "blog/friday-shipped-scarred/index.html",
        "blog/friday-shipped-scarred/index_pl.html",
    ),
    ("guides/index.html", "guides/index_pl.html"),
    ("privacy_en.html", "privacy.html"),
    ("SECURITY_report.html", "SECURITY_report_pl.html"),
    ("roadmap/index.html", "roadmap/index_pl.html"),
)


@dataclass
class Page:
    path: Path
    lang: str = ""
    title: str = ""
    h1_count: int = 0
    ids: list[str] = field(default_factory=list)
    refs: list[tuple[str, str, int]] = field(default_factory=list)
    meta: list[dict[str, str]] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    missing_alt_lines: list[int] = field(default_factory=list)
    forms_without_action: list[int] = field(default_factory=list)
    json_ld: list[tuple[str, int]] = field(default_factory=list)


class PageParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(path)
        self._in_title = False
        self._title_parts: list[str] = []
        self._json_ld_depth = 0
        self._json_ld_line = 0
        self._json_ld_parts: list[str] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key.lower(): value or "" for key, value in attrs}

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        tag = tag.lower()
        data = self._attrs(attrs)
        line, _ = self.getpos()

        if tag == "html":
            self.page.lang = data.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.page.h1_count += 1
        elif tag == "meta":
            self.page.meta.append(data)
        elif tag == "link":
            self.page.links.append(data)
        elif tag == "img" and "alt" not in data:
            self.page.missing_alt_lines.append(line)
        elif tag == "form" and not data.get("action"):
            self.page.forms_without_action.append(line)
        elif tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self._json_ld_depth = 1
            self._json_ld_line = line
            self._json_ld_parts = []

        if "id" in data:
            self.page.ids.append(data["id"])

        for attr in ("href", "src", "poster"):
            if data.get(attr):
                self.page.refs.append((attr, data[attr], line))
        if data.get("srcset"):
            for candidate in data["srcset"].split(","):
                value = candidate.strip().split(" ", 1)[0]
                if value:
                    self.page.refs.append(("srcset", value, line))

        if tag == "a" and data.get("target", "").lower() == "_blank":
            rel = set(data.get("rel", "").lower().split())
            if "noopener" not in rel:
                self.page.refs.append(("unsafe-target-blank", data.get("href", ""), line))

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
            self.page.title = "".join(self._title_parts).strip()
        elif tag == "script" and self._json_ld_depth:
            self.page.json_ld.append(
                ("".join(self._json_ld_parts).strip(), self._json_ld_line)
            )
            self._json_ld_depth = 0

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._json_ld_depth:
            self._json_ld_parts.append(data)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def meta_values(page: Page, key: str, value: str) -> list[str]:
    return [
        item.get("content", "")
        for item in page.meta
        if item.get(key, "").lower() == value.lower()
    ]


def link_values(page: Page, rel_name: str) -> list[str]:
    result = []
    for item in page.links:
        rels = set(item.get("rel", "").lower().split())
        if rel_name in rels:
            result.append(item.get("href", ""))
    return result


def hreflang_map(page: Page) -> tuple[dict[str, str], list[str]]:
    """Return normalized hreflang targets and duplicate language codes."""
    result: dict[str, str] = {}
    duplicates: list[str] = []
    for item in page.links:
        rels = set(item.get("rel", "").lower().split())
        language = item.get("hreflang", "").strip().lower()
        href = item.get("href", "").strip()
        if "alternate" not in rels or not language:
            continue
        if language in result:
            duplicates.append(language)
        else:
            result[language] = href
    return result, sorted(set(duplicates))


def local_target(
    source: Path, raw_url: str, root: Path
) -> tuple[Path | None, str, bool]:
    """Return (filesystem target, fragment, is_local)."""
    value = raw_url.strip()
    if not value or value.startswith("#"):
        fragment = unquote(value[1:]) if value.startswith("#") else ""
        return source, fragment, True

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme in SKIP_SCHEMES:
        return None, "", False
    if scheme in {"http", "https"} and parsed.netloc.lower() not in SITE_HOSTS:
        return None, "", False
    if scheme and scheme not in {"http", "https"}:
        return None, "", False

    path_text = unquote(parsed.path).replace("/", os.sep)
    if parsed.path.startswith("/"):
        candidate = root / path_text.lstrip(os.sep)
    elif scheme in {"http", "https"}:
        candidate = root / path_text.lstrip(os.sep)
    else:
        candidate = source.parent / path_text

    if not parsed.path or parsed.path.endswith("/"):
        candidate = candidate / "index.html"

    try:
        candidate = candidate.resolve()
        candidate.relative_to(root.resolve())
    except (OSError, ValueError):
        return candidate, unquote(parsed.fragment), True

    if not candidate.exists() and not candidate.suffix:
        directory_index = candidate / "index.html"
        if directory_index.exists():
            candidate = directory_index

    return candidate, unquote(parsed.fragment), True


def page_for_target(target: Path, pages: dict[Path, Page]) -> Page | None:
    try:
        return pages.get(target.resolve())
    except OSError:
        return None


def expected_sitemap_target(url: str, root: Path) -> Path | None:
    parsed = urlsplit(url)
    if parsed.netloc.lower() not in SITE_HOSTS:
        return None
    path_text = unquote(parsed.path).replace("/", os.sep)
    target = root / path_text.lstrip(os.sep)
    if not parsed.path or parsed.path.endswith("/"):
        target = target / "index.html"
    return target.resolve()


def mapping_literal_size(path: Path, variable: str) -> int:
    """Count keys in a top-level literal dict without importing app modules."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        target_name = ""
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            value = node.value
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable:
                    target_name = target.id
                    break
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        if target_name == variable and isinstance(value, ast.Dict):
            return len(value.keys)
    raise ValueError(f"{variable} is not a top-level literal dict in {path}")


def assignment_literal(path: Path, variable: str) -> object:
    """Read a top-level assignment that contains only Python literals."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        value: ast.expr | None = None
        found = False
        if isinstance(node, ast.Assign):
            value = node.value
            found = any(
                isinstance(target, ast.Name) and target.id == variable
                for target in node.targets
            )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = node.value
            found = node.target.id == variable
        if found and value is not None:
            return ast.literal_eval(value)
    raise ValueError(f"{variable} is not a top-level literal in {path}")


def load_source_facts(project_root: Path) -> tuple[dict[str, str | int], list[str]]:
    """Read current product facts from their canonical repository sources."""
    facts: dict[str, str | int] = {}
    errors: list[str] = []
    try:
        version_text = (project_root / "utils" / "app_version.py").read_text(
            encoding="utf-8"
        )
        match = re.search(
            r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']',
            version_text,
            re.MULTILINE,
        )
        if not match:
            raise ValueError("APP_VERSION assignment not found")
        facts["app_version"] = match.group(1)
    except (OSError, ValueError) as exc:
        errors.append(f"source facts: cannot read APP_VERSION ({exc})")

    try:
        facts["intents"] = mapping_literal_size(
            project_root / "hck_gpt" / "intents" / "vocabulary.py",
            "INTENT_PATTERNS",
        )
    except (OSError, SyntaxError, ValueError) as exc:
        errors.append(f"source facts: cannot count intents ({exc})")

    try:
        process_data = json.loads(
            (project_root / "data" / "process_library.json").read_text(
                encoding="utf-8"
            )
        )
        if not isinstance(process_data, (dict, list)):
            raise ValueError("process library root is not a mapping or list")
        facts["processes"] = len(process_data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"source facts: cannot count process definitions ({exc})")

    hardware_path = project_root / "core" / "hardware_compat_db.py"
    hardware_total = 0
    for variable, fact_name in (
        ("CPUS", "cpus"),
        ("GPUS", "gpus"),
        ("CHIPSETS", "chipsets"),
    ):
        try:
            count = mapping_literal_size(hardware_path, variable)
            facts[fact_name] = count
            hardware_total += count
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"source facts: cannot count {variable} ({exc})")
    if all(name in facts for name in ("cpus", "gpus", "chipsets")):
        facts["hardware_total"] = hardware_total

    try:
        turbo_path = project_root / "core" / "turbo_manager.py"
        profiles = assignment_literal(turbo_path, "PROFILES")
        protected = assignment_literal(turbo_path, "_SVC_WHITELIST")
        if not isinstance(profiles, dict) or not isinstance(protected, set):
            raise ValueError("service profile sources have unexpected types")
        for profile_name in ("gaming", "economy", "manager"):
            profile = profiles.get(profile_name)
            if not isinstance(profile, dict) or not isinstance(
                profile.get("services"), list
            ):
                raise ValueError(f"missing literal service list for {profile_name}")
            facts[f"{profile_name}_services"] = len(profile["services"])
        facts["protected_services"] = len(protected)
    except (OSError, SyntaxError, ValueError) as exc:
        errors.append(f"source facts: cannot read TURBO service profiles ({exc})")

    try:
        test_count = 0
        for test_path in sorted((project_root / "tests").rglob("test_*.py")):
            tree = ast.parse(
                test_path.read_text(encoding="utf-8"), filename=str(test_path)
            )
            for class_node in (
                node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ):
                test_count += sum(
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name.startswith("test")
                    for item in class_node.body
                )
        if not test_count:
            raise ValueError("no unittest methods found")
        facts["tests"] = test_count
    except (OSError, SyntaxError, ValueError) as exc:
        errors.append(f"source facts: cannot count unittest methods ({exc})")

    return facts, errors


def read_surface(root: Path, name: str) -> str | None:
    path = root / Path(name)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def collect_external_urls(root: Path) -> set[str]:
    """Collect outbound HTTP(S) links from site text artifacts."""
    urls: set[str] = set()
    url_re = re.compile(r"https?://[^\s\"'<>]+")
    for pattern in ("*.html", "*.xml", "*.txt"):
        for path in root.rglob(pattern):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for match in url_re.finditer(text):
                value = match.group(0).rstrip(").,;")
                parsed = urlsplit(value)
                if (
                    parsed.netloc.lower() not in SITE_HOSTS
                    and value not in EXTERNAL_PROBE_EXCLUSIONS
                ):
                    urls.add(value)
    return urls


def probe_external_url(url: str, timeout: float) -> tuple[str, str]:
    """Return (status, detail), where status is ok, blocked, or error."""
    headers = {
        "User-Agent": "PC-Workman-site-audit/1.0 (+https://pcworkman.dev)",
        "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8",
    }
    for method in ("HEAD", "GET"):
        request_headers = dict(headers)
        if method == "GET":
            request_headers["Range"] = "bytes=0-0"
        request = Request(url, headers=request_headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return "ok", str(response.status)
        except HTTPError as exc:
            if exc.code in {401, 403, 405, 406, 429, 999}:
                if method == "HEAD" and exc.code in {403, 405, 406}:
                    continue
                return "blocked", f"HTTP {exc.code}"
            if method == "HEAD" and exc.code in {400, 404}:
                continue
            return "error", f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError) as exc:
            if method == "HEAD":
                continue
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                return "blocked", "certificate chain could not be verified"
            return "error", str(exc)
    return "error", "request failed"


def audit_external_urls(
    root: Path, timeout: float, workers: int = 8
) -> tuple[list[str], list[str], int]:
    urls = sorted(collect_external_urls(root))
    errors: list[str] = []
    warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {
            executor.submit(probe_external_url, url, timeout): url for url in urls
        }
        for future in as_completed(pending):
            url = pending[future]
            try:
                status, detail = future.result()
            except Exception as exc:
                status, detail = "error", str(exc)
            if status == "error":
                errors.append(f"external link failed: {url} ({detail})")
            elif status == "blocked":
                warnings.append(
                    f"external link blocked automated verification: {url} ({detail})"
                )
    return sorted(errors), sorted(warnings), len(urls)


def audit(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []
    pages: dict[Path, Page] = {}
    texts: dict[Path, str] = {}
    sitemap_url_count = 0
    bilingual_pair_keys: set[tuple[str, str, str]] = set()
    unpaired_indexable: list[Page] = []

    for path in sorted(root.rglob("*.html")):
        # Google Search Console verification stubs are token files, not pages.
        if path.parent == root and HOST_VERIFICATION_RE.fullmatch(path.name):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{rel(path, root)}: invalid UTF-8 ({exc})")
            continue
        texts[path.resolve()] = text
        parser = PageParser(path.resolve())
        try:
            parser.feed(text)
            parser.close()
        except Exception as exc:
            errors.append(f"{rel(path, root)}: HTML parser failure ({exc})")
            continue
        pages[path.resolve()] = parser.page

    canonical_to_pages: defaultdict[str, list[str]] = defaultdict(list)
    canonical_to_page: dict[str, Page] = {}

    for path, page in pages.items():
        name = rel(path, root)
        text = texts[path]
        robots = " ".join(meta_values(page, "name", "robots")).lower()
        indexable = "noindex" not in robots
        if not page.lang:
            errors.append(f"{name}: missing <html lang>")
        if not page.title:
            errors.append(f"{name}: missing <title>")
        if page.h1_count != 1:
            errors.append(f"{name}: expected exactly one <h1>, found {page.h1_count}")

        duplicate_ids = sorted(key for key, count in Counter(page.ids).items() if count > 1)
        if duplicate_ids:
            errors.append(f"{name}: duplicate id(s): {', '.join(duplicate_ids)}")
        for line in page.missing_alt_lines:
            errors.append(f"{name}:{line}: image missing alt attribute")
        for line in page.forms_without_action:
            warnings.append(f"{name}:{line}: form has no action")

        if indexable:
            descriptions = meta_values(page, "name", "description")
            if len(descriptions) != 1 or not descriptions[0].strip():
                errors.append(f"{name}: expected one non-empty meta description")
            if "nosnippet" in robots or re.search(
                r"\bmax-snippet\s*:\s*0\b", robots
            ):
                errors.append(
                    f"{name}: robots metadata blocks text snippets and AI search previews"
                )

            canonicals = link_values(page, "canonical")
            if len(canonicals) != 1:
                errors.append(f"{name}: expected one canonical URL, found {len(canonicals)}")
            else:
                canonical_to_pages[canonicals[0]].append(name)
                canonical_to_page.setdefault(canonicals[0], page)
                parsed_canonical = urlsplit(canonicals[0])
                if (
                    parsed_canonical.scheme != "https"
                    or parsed_canonical.netloc.lower() not in SITE_HOSTS
                ):
                    errors.append(f"{name}: invalid canonical URL {canonicals[0]!r}")

        for block, line in page.json_ld:
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"{name}:{line}: invalid JSON-LD ({exc.msg})")

        for marker in MOJIBAKE_MARKERS:
            if marker in text:
                warnings.append(f"{name}: possible mojibake marker {marker!r}")
                break

        for attr, value, line in page.refs:
            if attr == "unsafe-target-blank":
                errors.append(f"{name}:{line}: target=_blank missing rel=noopener ({value})")
                continue
            target, fragment, is_local = local_target(path, value, root)
            if not is_local or target is None:
                continue
            try:
                target.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{name}:{line}: local reference escapes docs/: {value}")
                continue
            if not target.exists():
                errors.append(f"{name}:{line}: broken local reference {value}")
                continue
            if fragment:
                target_page = page_for_target(target, pages)
                if target_page is not None and fragment not in set(target_page.ids):
                    errors.append(
                        f"{name}:{line}: missing fragment #{fragment} in {rel(target, root)}"
                    )

    for canonical, names in sorted(canonical_to_pages.items()):
        if len(names) > 1:
            errors.append(f"duplicate canonical {canonical}: {', '.join(names)}")

    expected_languages = {"en", "pl", "x-default"}
    html_hreflang: dict[str, dict[str, str]] = {}
    for canonical, page in sorted(canonical_to_page.items()):
        if len(canonical_to_pages[canonical]) != 1:
            continue
        name = rel(page.path, root)
        alternates, duplicates = hreflang_map(page)
        if duplicates:
            errors.append(
                f"{name}: duplicate hreflang code(s): {', '.join(duplicates)}"
            )
        if not alternates:
            unpaired_indexable.append(page)
            continue
        if set(alternates) != expected_languages:
            actual = ", ".join(sorted(alternates)) or "none"
            errors.append(
                f"{name}: hreflang set must be en, pl, x-default; found {actual}"
            )
            continue
        page_language = page.lang.strip().lower().split("-", 1)[0]
        if page_language in {"en", "pl"} and alternates[page_language] != canonical:
            errors.append(
                f"{name}: hreflang {page_language} does not self-reference its canonical"
            )
        for language in ("en", "pl"):
            if alternates[language] not in canonical_to_page:
                errors.append(
                    f"{name}: hreflang {language} target is not an indexable canonical "
                    f"({alternates[language]})"
                )
        html_hreflang[canonical] = alternates
        bilingual_pair_keys.add(
            (alternates["en"], alternates["pl"], alternates["x-default"])
        )

    for canonical, alternates in sorted(html_hreflang.items()):
        page = canonical_to_page[canonical]
        name = rel(page.path, root)
        for language in ("en", "pl"):
            target = alternates[language]
            target_alternates = html_hreflang.get(target)
            if target_alternates != alternates:
                errors.append(
                    f"{name}: hreflang {language} target does not return the same "
                    "reciprocal language set"
                )

    for page in unpaired_indexable:
        name = rel(page.path, root)
        is_archive_episode = any(
            name.startswith(prefix) and name != f"{prefix}index.html"
            for prefix in ENGLISH_ARCHIVE_PREFIXES
        )
        if not page.lang.lower().startswith("en") or not is_archive_episode:
            errors.append(
                f"{name}: indexable page has no PL/EN hreflang pair and is not "
                "an English weekly-archive episode"
            )

    for en_name, pl_name in REQUIRED_BILINGUAL_SURFACES:
        en_path = (root / en_name).resolve()
        pl_path = (root / pl_name).resolve()
        if en_path not in pages:
            errors.append(f"{en_name}: required English surface is missing")
        elif not pages[en_path].lang.lower().startswith("en"):
            errors.append(f"{en_name}: required English surface has wrong lang")
        if pl_path not in pages:
            errors.append(f"{pl_name}: required Polish surface is missing")
        elif not pages[pl_path].lang.lower().startswith("pl"):
            errors.append(f"{pl_name}: required Polish surface has wrong lang")

    guides_root = root / "guides"
    if guides_root.exists():
        for guide_dir in sorted(path for path in guides_root.iterdir() if path.is_dir()):
            primary = (guide_dir / "index.html").resolve()
            if primary not in pages:
                continue
            primary_lang = pages[primary].lang.lower()
            counterpart_name = "index_pl.html" if primary_lang.startswith("en") else "index_en.html"
            counterpart = (guide_dir / counterpart_name).resolve()
            if counterpart not in pages:
                errors.append(
                    f"{rel(primary, root)}: missing bilingual counterpart "
                    f"{rel(counterpart, root)}"
                )

    sitemap = root / "sitemap.xml"
    if not sitemap.exists():
        errors.append("sitemap.xml: missing")
    else:
        try:
            tree = ET.parse(sitemap)
            sitemap_entries: dict[str, dict[str, str]] = {}
            for url_node in tree.getroot():
                if url_node.tag.rsplit("}", 1)[-1] != "url":
                    continue
                loc_nodes = [
                    child
                    for child in url_node
                    if child.tag.rsplit("}", 1)[-1] == "loc"
                ]
                if len(loc_nodes) != 1 or not (loc_nodes[0].text or "").strip():
                    errors.append("sitemap.xml: each <url> must contain one non-empty <loc>")
                    continue
                url = (loc_nodes[0].text or "").strip()
                if url in sitemap_entries:
                    errors.append(f"sitemap.xml: duplicate <loc> {url}")
                    continue
                alternates: dict[str, str] = {}
                for child in url_node:
                    if child.tag.rsplit("}", 1)[-1] != "link":
                        continue
                    if child.attrib.get("rel", "").lower() != "alternate":
                        continue
                    language = child.attrib.get("hreflang", "").strip().lower()
                    href = child.attrib.get("href", "").strip()
                    if not language or not href:
                        errors.append(
                            f"sitemap.xml: incomplete alternate link under {url}"
                        )
                    elif language in alternates:
                        errors.append(
                            f"sitemap.xml: duplicate hreflang {language} under {url}"
                        )
                    else:
                        alternates[language] = href
                sitemap_entries[url] = alternates

            sitemap_url_count = len(sitemap_entries)
            for url, alternates in sitemap_entries.items():
                target = expected_sitemap_target(url, root)
                if target is not None and not target.exists():
                    errors.append(f"sitemap.xml: URL has no local file: {url}")
                if url not in canonical_to_page:
                    errors.append(
                        f"sitemap.xml: URL is not an indexable HTML canonical: {url}"
                    )
                    continue
                expected_alternates = html_hreflang.get(url, {})
                if alternates != expected_alternates:
                    errors.append(
                        f"sitemap.xml: hreflang links differ from HTML for {url}"
                    )

            for canonical, page in sorted(canonical_to_page.items()):
                if canonical not in sitemap_entries:
                    errors.append(
                        f"sitemap.xml: missing indexable page {rel(page.path, root)}"
                    )
        except (ET.ParseError, OSError) as exc:
            errors.append(f"sitemap.xml: invalid XML ({exc})")

    for feed_name, expected_language in (
        ("blog/feed.xml", "en"),
        ("blog/feed_pl.xml", "pl"),
    ):
        feed = root / feed_name
        if not feed.exists():
            errors.append(f"{feed_name}: missing")
            continue
        try:
            feed_tree = ET.parse(feed)
            channel = feed_tree.getroot().find("channel")
            if channel is None:
                errors.append(f"{feed_name}: missing RSS channel")
                continue
            language = (channel.findtext("language") or "").strip().lower()
            if language != expected_language:
                errors.append(
                    f"{feed_name}: expected language {expected_language}, found "
                    f"{language or 'none'}"
                )
            self_links = [
                node.attrib.get("href", "")
                for node in channel
                if node.tag.rsplit("}", 1)[-1] == "link"
                and node.attrib.get("rel", "").lower() == "self"
            ]
            expected_self = f"https://pcworkman.dev/{feed_name}"
            if self_links != [expected_self]:
                errors.append(
                    f"{feed_name}: expected one Atom self link to {expected_self}"
                )
            item_dates = []
            for position, item in enumerate(channel.findall("item"), start=1):
                for field_name in ("title", "link", "guid", "pubDate", "description"):
                    if not (item.findtext(field_name) or "").strip():
                        errors.append(
                            f"{feed_name}: item {position} has empty {field_name}"
                        )
                raw_date = (item.findtext("pubDate") or "").strip()
                try:
                    item_dates.append(parsedate_to_datetime(raw_date))
                except (TypeError, ValueError):
                    errors.append(
                        f"{feed_name}: item {position} has invalid pubDate {raw_date!r}"
                    )
            if item_dates != sorted(item_dates, reverse=True):
                errors.append(f"{feed_name}: items are not ordered newest first")
        except (ET.ParseError, OSError) as exc:
            errors.append(f"{feed_name}: invalid XML ({exc})")

    facts, source_fact_errors = load_source_facts(root.parent)
    errors.extend(source_fact_errors)

    for name in CURRENT_VERSION_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: current-fact surface is missing or unreadable")
            continue
        version = facts.get("app_version")
        if version and str(version) not in text:
            errors.append(f"{name}: does not mention current APP_VERSION {version}")

    current_intents = facts.get("intents")
    stale_intent_re = re.compile(
        r"\b(?:82|84|90|92|100)\s+(?:AI\s+)?(?:intents?|intencj\w*)",
        re.IGNORECASE,
    )
    for name in CURRENT_FACT_SURFACES:
        text = read_surface(root, name)
        if text is None:
            continue
        stale = stale_intent_re.search(text)
        if stale:
            errors.append(f"{name}: stale current intent claim {stale.group(0)!r}")
        if current_intents and not re.search(
            rf"\b{re.escape(str(current_intents))}\b", text
        ):
            errors.append(
                f"{name}: does not mention current intent count {current_intents}"
            )
        if re.search(r"\b(?:0|no|zero)\s+telemetry\b", text, re.IGNORECASE):
            errors.append(f"{name}: misleading zero-telemetry claim")

    for name in PROCESS_FACT_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: process-fact surface is missing or unreadable")
            continue
        process_count = facts.get("processes")
        if process_count and not re.search(
            rf"\b{re.escape(str(process_count))}\b", text
        ):
            errors.append(
                f"{name}: does not mention current process count {process_count}"
            )

    for name in SERVICE_PROFILE_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: service-profile surface is missing or unreadable")
            continue
        for profile_name in ("gaming", "economy"):
            count = facts.get(f"{profile_name}_services")
            if count and not re.search(rf"\b{re.escape(str(count))}\b", text):
                errors.append(
                    f"{name}: does not mention current {profile_name} service "
                    f"count {count}"
                )
        if "manager" not in text.lower():
            errors.append(f"{name}: does not mention the user-composed Manager profile")

    for name in SERVICE_GUARD_SURFACES:
        text = read_surface(root, name)
        protected_count = facts.get("protected_services")
        if text is not None and protected_count and not re.search(
            rf"\b{re.escape(str(protected_count))}\b", text
        ):
            errors.append(
                f"{name}: does not mention protected service count {protected_count}"
            )

    for name in HARDWARE_FULL_FACT_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: hardware-fact surface is missing or unreadable")
            continue
        for fact_name, label in (
            ("cpus", "CPU"),
            ("gpus", "GPU"),
            ("chipsets", "chipset"),
        ):
            count = facts.get(fact_name)
            if count and not re.search(rf"\b{re.escape(str(count))}\b", text):
                errors.append(f"{name}: does not mention current {label} count {count}")

    for name in CPU_CHIPSET_FACT_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: CPU-compatibility surface is missing or unreadable")
            continue
        for fact_name, label in (("cpus", "CPU"), ("chipsets", "chipset")):
            count = facts.get(fact_name)
            if count and not re.search(rf"\b{re.escape(str(count))}\b", text):
                errors.append(f"{name}: does not mention current {label} count {count}")

    for name in TEST_FACT_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: test-fact surface is missing or unreadable")
            continue
        test_count = facts.get("tests")
        if test_count and not re.search(
            rf"\b{re.escape(str(test_count))}\b", text
        ):
            errors.append(f"{name}: does not mention current test count {test_count}")

    for name in BLOG_HUBS:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: blog hub is missing or unreadable")
            continue
        if current_intents and not re.search(
            rf'<div class="stat"><b>{re.escape(str(current_intents))}</b>',
            text,
        ):
            errors.append(
                f"{name}: top stats do not show current intent count {current_intents}"
            )
        process_count = facts.get("processes")
        if process_count and not re.search(
            rf'<div class="stat"><b>{re.escape(str(process_count))}</b>',
            text,
        ):
            errors.append(
                f"{name}: top stats do not show process count {process_count}"
            )

    stale_learning_re = re.compile(
        r"(?:last|ostatni\w*)\s+14\s+(?:days?|dni)"
        r"|6\s*[–—-]\s*12\s+(?:months?|miesi\w*)",
        re.IGNORECASE,
    )
    for name in LEARNING_FACT_SURFACES:
        text = read_surface(root, name)
        if text is None:
            errors.append(f"{name}: learning-fact surface is missing or unreadable")
            continue
        claim = stale_learning_re.search(text)
        if claim:
            errors.append(f"{name}: stale learning-duration claim {claim.group(0)!r}")

    for path, text in texts.items():
        name = rel(path, root)
        for marker in STALE_AUTHOR_OR_PLACEHOLDER:
            if marker.lower() in text.lower():
                errors.append(f"{name}: stale author/profile value {marker!r}")
        if re.search(
            r"<form\b[^>]*(?:newsletter|subscribe)",
            text,
            re.IGNORECASE | re.DOTALL,
        ):
            errors.append(f"{name}: newsletter/subscribe form requires a real backend")
        if not name.startswith("blog/") and re.search(
            r"\b100%\s+offline\b|\b(?:0|no|zero)\s+telemetry\b",
            text,
            re.IGNORECASE,
        ):
            errors.append(f"{name}: misleading whole-product offline/telemetry claim")

    security_text = read_surface(root, ".well-known/security.txt")
    if security_text and re.search(
        r"\b100%\s+offline\b|\b(?:0|no|zero)\s+telemetry\b",
        security_text,
        re.IGNORECASE,
    ):
        errors.append(
            ".well-known/security.txt: misleading whole-product offline/telemetry claim"
        )

    stats = {
        "html_pages": len(pages),
        "indexable_pages": len(canonical_to_page),
        "indexable_en": sum(
            1 for page in canonical_to_page.values() if page.lang.lower().startswith("en")
        ),
        "indexable_pl": sum(
            1 for page in canonical_to_page.values() if page.lang.lower().startswith("pl")
        ),
        "english_archive_only": len(unpaired_indexable),
        "local_refs": sum(len(page.refs) for page in pages.values()),
        "json_ld_blocks": sum(len(page.json_ld) for page in pages.values()),
        "bilingual_pairs": len(bilingual_pair_keys),
        "sitemap_urls": sitemap_url_count,
        "source_intents": int(facts.get("intents", 0)),
        "source_processes": int(facts.get("processes", 0)),
        "source_hardware": int(facts.get("hardware_total", 0)),
        "source_gaming_services": int(facts.get("gaming_services", 0)),
        "source_economy_services": int(facts.get("economy_services", 0)),
        "source_protected_services": int(facts.get("protected_services", 0)),
        "source_tests": int(facts.get("tests", 0)),
        "errors": len(errors),
        "warnings": len(warnings),
    }
    return errors, warnings, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="also probe unique outbound HTTP(S) links",
    )
    parser.add_argument(
        "--external-timeout",
        type=float,
        default=10.0,
        help="per-request timeout in seconds for --external (default: 10)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"Site root not found: {root}", file=sys.stderr)
        return 2

    errors, warnings, stats = audit(root)
    if args.external:
        ext_errors, ext_warnings, ext_count = audit_external_urls(
            root, max(1.0, args.external_timeout)
        )
        errors.extend(ext_errors)
        warnings.extend(ext_warnings)
        stats["external_urls"] = ext_count
        stats["errors"] = len(errors)
        stats["warnings"] = len(warnings)
    print(
        "Site audit: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )
    if errors:
        print("\nERRORS")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("\nWARNINGS")
        for item in warnings:
            print(f"- {item}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
