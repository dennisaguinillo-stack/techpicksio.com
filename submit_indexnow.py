#!/usr/bin/env python3
"""
Submits every URL in sitemap.xml to the IndexNow API so Bing (and any other
IndexNow-participating engine, which feeds Copilot answers) picks up new or
updated pages within minutes instead of waiting for the next crawl.

Requires the key file <INDEXNOW_KEY>.txt to already exist at the site root
and be published at https://www.techpicksio.com/<INDEXNOW_KEY>.txt — that is
how IndexNow verifies the submission belongs to this domain.

Usage:
    python3 submit_indexnow.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request

SITE_URL = "https://www.techpicksio.com"
HOST = "www.techpicksio.com"
INDEXNOW_KEY = "4bf0836544ff4db9b3dcefd45aaedab7"
KEY_LOCATION = f"{SITE_URL}/{INDEXNOW_KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
SITEMAP_FILE = "sitemap.xml"


def urls_from_sitemap(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        xml = f.read()
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def submit(url_list: list[str]) -> None:
    payload = json.dumps({
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": url_list,
    }).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"IndexNow: submitted {len(url_list)} URLs, status {resp.status}")
    except urllib.error.HTTPError as e:
        # IndexNow returns 200/202 on success; treat anything else as a
        # non-fatal warning so it never breaks the build.
        print(f"IndexNow: submission returned HTTP {e.code}: {e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        print(f"IndexNow: submission failed ({e.reason}) — will retry on next run")


def main():
    urls = urls_from_sitemap(SITEMAP_FILE)
    if not urls:
        print("No URLs found in sitemap.xml — nothing to submit.")
        return
    submit(urls)


if __name__ == "__main__":
    sys.exit(main())
