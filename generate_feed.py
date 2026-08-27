#!/usr/bin/env python3
"""
Auto-generates feed.xml (RSS 2.0) from the article pages in this directory.

Why this exists
---------------
A syndication feed is the concrete technical requirement for Microsoft Start
(MSN) Partner Hub, and GitHub Pages does not produce one. It is also how Bing
and several answer engines discover new articles fastest.

What it produces per item, because MSN rejects thin feeds:

  - <title>, <link>, <guid isPermaLink="true">   the canonical URL
  - <description>                                the page's meta description
  - <content:encoded>                            the full article body, with
                                                 every relative URL rewritten
                                                 absolute so it survives being
                                                 rendered on another domain
  - <pubDate> and <atom:updated>                 first publication and last
                                                 modification, taken from the
                                                 page's JSON-LD where present
  - <dc:creator> / <author>                      the publication
  - <media:content> and <enclosure>              the article's og:image
  - <category>                                   from the page's breadcrumb

The FTC affiliate disclosure is prepended to every <content:encoded> body.
A syndicated excerpt is a commercial link leaving this domain, and the
disclosure has to travel with it.

Usage:
    python3 generate_feed.py
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from email.utils import format_datetime

SITE_URL = "https://www.techpicksio.com"
OUTPUT_FILE = "feed.xml"
FEED_TITLE = "techpicksio.com — mobile filmmaking gear guides"
FEED_DESC = (
    "Spec-first buying guides for mobile filmmaking gear: cages, microphones, "
    "lighting, gimbals, drones and storage for iPhone and Android creators."
)
AUTHOR = "techpicksio.com editorial team"
EMAIL = "hello@techpicksio.com"
MAX_ITEMS = 25

# Utility pages carry no article body worth syndicating.
EXCLUDE = {
    "index.html",
    "google7a99f5f52cfafe41.html",
    "about.html",
    "contact.html",
    "privacy-policy.html",
    "terms-of-service.html",
    "methodology.html",   # editorial standards, not an article
    "404.html",
}

DISCLOSURE = (
    "<p><em><strong>Disclosure:</strong> techpicksio.com is a participant in the "
    "Amazon Services LLC Associates Program and earns from qualifying purchases "
    "made through links in this article, at no extra cost to you. Recommendations "
    "are compiled from published manufacturer specifications and documentation; "
    "techpicksio.com does not claim hands-on testing of the products covered.</em></p>"
)

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def meta(source: str, *, name: str = "", prop: str = "") -> str:
    attr, value = ("name", name) if name else ("property", prop)
    m = re.search(rf'<meta {attr}="{re.escape(value)}" content="([^"]*)"', source)
    return html.unescape(m.group(1)) if m else ""


def jsonld(source: str) -> list[dict]:
    out = []
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', source, re.S):
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        out.extend(obj if isinstance(obj, list) else [obj])
    return out


def git_first_commit_date(filename: str) -> datetime | None:
    """The date the page entered the repo — the honest pubDate for older pages
    whose JSON-LD only records a dateModified."""
    try:
        stamp = subprocess.run(
            ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "--", filename],
            capture_output=True, text=True, check=True, timeout=20,
        ).stdout.strip().splitlines()
        if stamp:
            return datetime.fromisoformat(stamp[-1])
    except (subprocess.SubprocessError, ValueError, OSError):
        pass
    return None


def dates(filename: str, source: str) -> tuple[datetime, datetime]:
    published = modified = None
    for node in jsonld(source):
        for key, target in (("datePublished", "published"), ("dateModified", "modified")):
            raw = node.get(key)
            if not raw:
                continue
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if target == "published" and published is None:
                published = parsed
            elif target == "modified" and modified is None:
                modified = parsed
    if published is None:
        published = git_first_commit_date(filename)
    if published is None:
        published = modified
    if modified is None:
        modified = published
    fallback = datetime.now(timezone.utc)
    return (published or fallback), (modified or fallback)


def category(source: str) -> str:
    """The middle rung of the visible breadcrumb, e.g. "Rigs & Cages"."""
    for node in jsonld(source):
        if node.get("@type") == "BreadcrumbList":
            items = node.get("itemListElement", [])
            if len(items) >= 3:
                return items[1]["name"]
    return "Guides"


def absolutise(fragment: str) -> str:
    """Rewrite every relative href/src/srcset so the body renders correctly on
    a syndication partner's domain."""
    def one(m):
        attr, value = m.group(1), m.group(2)
        if value.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
            return m.group(0)
        return f'{attr}="{SITE_URL}/{value.lstrip("/")}"'

    fragment = re.sub(r'\b(href|src)="([^"]+)"', one, fragment)

    def srcset(m):
        parts = []
        for candidate in m.group(1).split(","):
            candidate = candidate.strip()
            if not candidate:
                continue
            url, _, rest = candidate.partition(" ")
            if not url.startswith(("http://", "https://", "data:")):
                url = f'{SITE_URL}/{url.lstrip("/")}'
            parts.append(f"{url} {rest}".strip())
        return f'srcset="{", ".join(parts)}"'

    return re.sub(r'srcset="([^"]+)"', srcset, fragment)


def body(source: str) -> str:
    """The article content, minus the navigation furniture that means nothing
    once the page is rendered somewhere else."""
    m = re.search(r"<article\b[^>]*>(.*?)</article>", source, re.S)
    if not m:
        return ""
    text = m.group(1)
    # In-page navigation, the byline block and the silo uplink are all
    # site-chrome; they either dead-link or read as noise off-domain.
    text = re.sub(r'<details class="tpi-toc-mobile.*?</details>', "", text, flags=re.S)
    text = re.sub(r'<div class="tpi-byline.*?\n\s*</div>\n\s*</div>', "", text, flags=re.S)
    text = re.sub(r'<p class="tpi-uplink.*?</p>', "", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return DISCLOSURE + absolutise(text.strip())


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def image_bytes(url: str) -> int:
    """Byte length for <enclosure>. The image lives in this repo, so read it."""
    if not url.startswith(f"{SITE_URL}/"):
        return 0
    path = url[len(SITE_URL) + 1:]
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def collect() -> list[dict]:
    items = []
    for filename in sorted(os.listdir(".")):
        if not filename.endswith(".html") or filename in EXCLUDE:
            continue
        with open(filename, encoding="utf-8") as f:
            source = f.read()
        if "<article" not in source:
            continue
        published, modified = dates(filename, source)
        image = meta(source, prop="og:image")
        items.append({
            "title": meta(source, prop="og:title") or filename,
            "url": f"{SITE_URL}/{filename}",
            "description": meta(source, name="description"),
            "body": body(source),
            "published": published,
            "modified": modified,
            "category": category(source),
            "image": image,
            "mime": MIME.get(os.path.splitext(image)[1].lower(), "image/jpeg"),
            "bytes": image_bytes(image),
        })
    items.sort(key=lambda i: i["published"], reverse=True)
    return items[:MAX_ITEMS]


def build(items: list[dict]) -> str:
    now = max((i["modified"] for i in items), default=datetime.now(timezone.utc))
    esc = lambda t: html.escape(t, quote=False)
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"',
        '     xmlns:content="http://purl.org/rss/1.0/modules/content/"',
        '     xmlns:dc="http://purl.org/dc/elements/1.1/"',
        '     xmlns:atom="http://www.w3.org/2005/Atom"',
        '     xmlns:media="http://search.yahoo.com/mrss/">',
        "  <channel>",
        f"    <title>{esc(FEED_TITLE)}</title>",
        f"    <link>{SITE_URL}/</link>",
        f"    <description>{esc(FEED_DESC)}</description>",
        "    <language>en-us</language>",
        f"    <copyright>Copyright {now.year} techpicksio.com</copyright>",
        f"    <managingEditor>{EMAIL} ({esc(AUTHOR)})</managingEditor>",
        f"    <webMaster>{EMAIL} ({esc(AUTHOR)})</webMaster>",
        f"    <lastBuildDate>{format_datetime(now)}</lastBuildDate>",
        "    <generator>generate_feed.py</generator>",
        "    <docs>https://www.rssboard.org/rss-specification</docs>",
        f'    <atom:link href="{SITE_URL}/{OUTPUT_FILE}" rel="self" type="application/rss+xml" />',
        "    <image>",
        f"      <url>{SITE_URL}/images/neewer-phone-cage.jpg</url>",
        f"      <title>{esc(FEED_TITLE)}</title>",
        f"      <link>{SITE_URL}/</link>",
        "    </image>",
    ]
    for item in items:
        out += [
            "    <item>",
            f"      <title>{esc(item['title'])}</title>",
            f"      <link>{item['url']}</link>",
            f'      <guid isPermaLink="true">{item["url"]}</guid>',
            f"      <description>{esc(item['description'])}</description>",
            f"      <content:encoded><![CDATA[{item['body']}]]></content:encoded>",
            f"      <pubDate>{format_datetime(item['published'])}</pubDate>",
            f"      <atom:updated>{item['modified'].astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')}</atom:updated>",
            f"      <dc:creator>{esc(AUTHOR)}</dc:creator>",
            f"      <author>{EMAIL} ({esc(AUTHOR)})</author>",
            f"      <category>{esc(item['category'])}</category>",
        ]
        if item["image"]:
            out += [
                f'      <media:content url="{item["image"]}" medium="image" type="{item["mime"]}">',
                f"        <media:title type=\"plain\">{esc(item['title'])}</media:title>",
                f"        <media:credit role=\"provider\">techpicksio.com</media:credit>",
                "      </media:content>",
                f'      <enclosure url="{item["image"]}" type="{item["mime"]}" length="{item["bytes"]}" />',
            ]
        out.append("    </item>")
    out += ["  </channel>", "</rss>"]
    return "\n".join(out) + "\n"


def main():
    items = collect()
    if not items:
        print("No article pages found. Run this script from the repo root.")
        return
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(build(items))
    print(f"Generated {OUTPUT_FILE} with {len(items)} items:")
    for item in items:
        print(f"   {item['published'].date()}  {item['title'][:64]}")


if __name__ == "__main__":
    main()
