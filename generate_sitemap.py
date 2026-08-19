#!/usr/bin/env python3
"""
Auto-generates sitemap.xml by scanning the current directory for .html files.
Run this from the root of your techpicksio.com repo whenever you add/remove pages.

Usage:
    python3 generate_sitemap.py
"""

import os
from datetime import date

# ---- Config ----
SITE_URL = "https://www.techpicksio.com"
OUTPUT_FILE = "sitemap.xml"

# Files/folders to skip
EXCLUDE_FILES = {"404.html"}
EXCLUDE_DIRS = {".git", ".github", "node_modules"}
# ----------------

def find_html_files(root="."):
    html_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # skip excluded directories (in place, so os.walk won't descend into them)
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for filename in filenames:
            if filename.endswith(".html") and filename not in EXCLUDE_FILES:
                full_path = os.path.join(dirpath, filename)
                # Convert to URL path relative to root
                rel_path = os.path.relpath(full_path, root).replace(os.sep, "/")
                if rel_path == "index.html":
                    url = f"{SITE_URL}/"
                elif rel_path.endswith("/index.html"):
                    url = f"{SITE_URL}/{rel_path[:-len('index.html')]}"
                else:
                    url = f"{SITE_URL}/{rel_path}"
                html_files.append(url)
    return sorted(set(html_files))


def build_sitemap(urls):
    today = date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    for url in urls:
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    urls = find_html_files(".")
    if not urls:
        print("No .html files found. Run this script from your repo root.")
        return

    sitemap_content = build_sitemap(urls)
    with open(OUTPUT_FILE, "w") as f:
        f.write(sitemap_content)

    print(f"✅ Generated {OUTPUT_FILE} with {len(urls)} URLs:")
    for url in urls:
        print(f"   - {url}")


if __name__ == "__main__":
    main()
