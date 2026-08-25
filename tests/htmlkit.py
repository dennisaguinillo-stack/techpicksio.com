"""
Minimal HTML extraction for the contract tests in this directory.

Uses only html.parser from the standard library — the repo deliberately
has no node/npm toolchain and no Python dependencies beyond pytest, and
this keeps it that way. Deliberately not a general-purpose parser: it
extracts exactly the handful of things the contract tests need to look at
(title, meta/link tags, headings, images, anchors, ids, JSON-LD scripts,
visible text) and nothing else.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from functools import lru_cache
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Not real content pages — search-engine ownership verification stubs.
# generate_sitemap.py excludes these too (plus 404.html, which doesn't
# exist yet in this repo).
EXCLUDE = {"google7a99f5f52cfafe41.html"}

SITE_URL = "https://www.techpicksio.com"


def all_pages() -> list[str]:
    """Every real page in the repo, as a filename relative to ROOT."""
    return sorted(
        os.path.basename(p)
        for p in glob.glob(os.path.join(ROOT, "*.html"))
        if os.path.basename(p) not in EXCLUDE
    )


def canonical_url_for(filename: str) -> str:
    return f"{SITE_URL}/" if filename == "index.html" else f"{SITE_URL}/{filename}"


@dataclass
class ParsedPage:
    filename: str
    title: str = ""
    meta: list[dict] = field(default_factory=list)
    link: list[dict] = field(default_factory=list)
    imgs: list[dict] = field(default_factory=list)
    anchors: list[dict] = field(default_factory=list)
    ids: set[str] = field(default_factory=set)
    headings: list[tuple[int, str]] = field(default_factory=list)
    jsonld_raw: list[str] = field(default_factory=list)
    text: str = ""

    def meta_content(self, *, name: str | None = None, prop: str | None = None):
        for m in self.meta:
            if name is not None and m.get("name") == name:
                return m.get("content")
            if prop is not None and m.get("property") == prop:
                return m.get("content")
        return None

    def canonical(self):
        for l in self.link:
            if l.get("rel") == "canonical":
                return l.get("href")
        return None


class _Parser(HTMLParser):
    def __init__(self, page: ParsedPage):
        super().__init__(convert_charrefs=True)
        self.page = page
        self._in_title = False
        self._h_stack: list[list] = []
        self._script_type = None
        self._script_buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.page.ids.add(d["id"])
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.page.meta.append(d)
        elif tag == "link":
            self.page.link.append(d)
        elif tag == "img":
            self.page.imgs.append(d)
        elif tag == "a":
            self.page.anchors.append(d)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._h_stack.append([int(tag[1]), ""])
        elif tag == "script":
            self._script_type = d.get("type", "")
            self._script_buf = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._h_stack:
            level, text = self._h_stack.pop()
            self.page.headings.append((level, text.strip()))
        elif tag == "script":
            if self._script_buf is not None and "ld+json" in (self._script_type or ""):
                self.page.jsonld_raw.append("".join(self._script_buf))
            self._script_type = None
            self._script_buf = None

    def handle_data(self, data):
        if self._in_title:
            self.page.title += data
        if self._h_stack:
            self._h_stack[-1][1] += data
        if self._script_buf is not None:
            self._script_buf.append(data)
        else:
            self.page.text += data


@lru_cache(maxsize=None)
def parse(filename: str) -> ParsedPage:
    path = os.path.join(ROOT, filename)
    with open(path, encoding="utf-8") as f:
        html = f.read()
    page = ParsedPage(filename=filename)
    _Parser(page).feed(html)
    page.title = page.title.strip()
    return page
