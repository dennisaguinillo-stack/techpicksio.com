"""
Contract tests for every *.html page in the repo.

This site's product is its markup: a working affiliate link, a correct
canonical tag, valid structured data. These tests encode the invariants
that markup must hold, the same way check-classes.py already encodes
"every class used must resolve." Where a rule only applies to pages that
have a given feature (an affiliate link, a FAQPage block), the test is
written as a conditional over that feature rather than a hardcoded list
of "article pages" — new pages inherit the suite automatically.

Run with: pytest tests/
"""
from __future__ import annotations

import json
import os
import re

import pytest

from htmlkit import ROOT, SITE_URL, all_pages, canonical_url_for, parse

PAGES = all_pages()

AFFILIATE_TAG = "techpicksio-20"
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
DISCLOSURE_TEXT = "FTC Affiliate Disclosure"

# "#top" has no matching id anywhere on the site, but it isn't a bug: the
# HTML fragment-navigation algorithm scrolls to the top of the document
# when the fragment is literally "top" and no element has that id/name.
SPECIAL_FRAGMENTS = {"top", ""}


def _asin_from_amazon_href(href: str) -> str | None:
    m = re.search(r"/dp/([^/?#]+)", href)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_canonical_is_self_referential(filename):
    page = parse(filename)
    assert page.canonical() == canonical_url_for(filename), (
        f"{filename}: canonical should be {canonical_url_for(filename)!r}, "
        f"got {page.canonical()!r}"
    )


@pytest.mark.parametrize("filename", PAGES)
def test_og_url_matches_canonical(filename):
    page = parse(filename)
    og_url = page.meta_content(prop="og:url")
    assert og_url == page.canonical(), (
        f"{filename}: og:url ({og_url!r}) should match canonical ({page.canonical()!r})"
    )


@pytest.mark.parametrize("filename", PAGES)
def test_title_present_and_search_result_safe(filename):
    page = parse(filename)
    assert page.title, f"{filename}: <title> is empty"
    # ~60 characters is the practical point Google starts truncating titles
    # in search results.
    assert len(page.title) <= 60, (
        f"{filename}: title is {len(page.title)} chars, will truncate in "
        f"search results: {page.title!r}"
    )


@pytest.mark.parametrize("filename", PAGES)
def test_description_present_and_search_result_safe(filename):
    page = parse(filename)
    desc = page.meta_content(name="description")
    assert desc, f"{filename}: meta description is missing"
    assert len(desc) <= 160, (
        f"{filename}: description is {len(desc)} chars, will truncate in "
        f"search results"
    )


def test_titles_are_unique_across_site():
    seen = {}
    dupes = []
    for filename in PAGES:
        title = parse(filename).title
        if title in seen:
            dupes.append((title, seen[title], filename))
        else:
            seen[title] = filename
    assert not dupes, f"duplicate <title> across pages: {dupes}"


def test_descriptions_are_unique_across_site():
    seen = {}
    dupes = []
    for filename in PAGES:
        desc = parse(filename).meta_content(name="description")
        if desc in seen:
            dupes.append((desc, seen[desc], filename))
        else:
            seen[desc] = filename
    assert not dupes, f"duplicate meta description across pages: {dupes}"


@pytest.mark.parametrize("filename", PAGES)
def test_og_title_matches_title_when_present(filename):
    page = parse(filename)
    og_title = page.meta_content(prop="og:title")
    if og_title is not None:
        assert og_title == page.title, f"{filename}: og:title drifted from <title>"


@pytest.mark.parametrize("filename", PAGES)
def test_twitter_title_matches_title_when_present(filename):
    page = parse(filename)
    tw_title = page.meta_content(name="twitter:title")
    if tw_title is not None:
        assert tw_title == page.title, f"{filename}: twitter:title drifted from <title>"


# ---------------------------------------------------------------------------
# Heading structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_exactly_one_h1(filename):
    page = parse(filename)
    h1s = [h for h in page.headings if h[0] == 1]
    assert len(h1s) == 1, f"{filename}: expected exactly one <h1>, found {len(h1s)}"


@pytest.mark.parametrize("filename", PAGES)
def test_no_heading_level_skips(filename):
    page = parse(filename)
    prev = 0
    for level, _text in page.headings:
        if prev:
            assert level <= prev + 1, (
                f"{filename}: heading jumps from h{prev} to h{level} without "
                f"an intermediate level"
            )
        prev = level


# ---------------------------------------------------------------------------
# Affiliate links
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_amazon_links_carry_full_affiliate_contract(filename):
    page = parse(filename)
    for a in page.anchors:
        href = a.get("href", "")
        if "amazon.com" not in href:
            continue
        assert f"tag={AFFILIATE_TAG}" in href, (
            f"{filename}: Amazon link missing affiliate tag: {href}"
        )
        asin = _asin_from_amazon_href(href)
        assert asin and ASIN_RE.match(asin), (
            f"{filename}: Amazon link has a malformed ASIN {asin!r}: {href}"
        )
        rel = set(a.get("rel", "").split())
        assert {"sponsored", "nofollow", "noopener"} <= rel, (
            f"{filename}: Amazon link rel={a.get('rel')!r} is missing "
            f"sponsored/nofollow/noopener: {href}"
        )
        assert a.get("target") == "_blank", (
            f"{filename}: Amazon link should open in a new tab: {href}"
        )


@pytest.mark.parametrize("filename", PAGES)
def test_ftc_disclosure_present_when_page_has_affiliate_links(filename):
    page = parse(filename)
    has_affiliate_link = any("amazon.com" in a.get("href", "") for a in page.anchors)
    if has_affiliate_link:
        assert DISCLOSURE_TEXT in page.text, (
            f"{filename}: has an Amazon affiliate link but no FTC disclosure"
        )


# ---------------------------------------------------------------------------
# Structured data
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_jsonld_blocks_are_valid_json(filename):
    page = parse(filename)
    for i, raw in enumerate(page.jsonld_raw):
        try:
            json.loads(raw)
        except json.JSONDecodeError as e:
            pytest.fail(f"{filename}: JSON-LD block #{i} does not parse: {e}")


@pytest.mark.parametrize("filename", PAGES)
def test_faqpage_questions_appear_in_visible_text(filename):
    page = parse(filename)
    for raw in page.jsonld_raw:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue  # covered by test_jsonld_blocks_are_valid_json
        items = obj if isinstance(obj, list) else [obj]
        for item in items:
            if item.get("@type") != "FAQPage":
                continue
            for question in item.get("mainEntity", []):
                name = question.get("name", "")
                assert name in page.text, (
                    f"{filename}: FAQPage question not found in visible copy: {name!r}"
                )


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_images_have_alt_text(filename):
    page = parse(filename)
    for img in page.imgs:
        assert img.get("alt", "").strip(), f"{filename}: <img src={img.get('src')!r}> has no alt text"


@pytest.mark.parametrize("filename", PAGES)
def test_images_have_explicit_dimensions(filename):
    page = parse(filename)
    for img in page.imgs:
        assert "width" in img and "height" in img, (
            f"{filename}: <img src={img.get('src')!r}> is missing width/height "
            f"(causes layout shift while it loads)"
        )


@pytest.mark.parametrize("filename", PAGES)
def test_local_image_sources_exist_on_disk(filename):
    page = parse(filename)
    for img in page.imgs:
        src = img.get("src", "")
        if src.startswith(("http://", "https://", "data:")):
            continue
        assert os.path.exists(os.path.join(ROOT, src)), (
            f"{filename}: <img src={src!r}> does not exist on disk"
        )


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_internal_page_links_resolve(filename):
    page = parse(filename)
    for a in page.anchors:
        href = a.get("href", "")
        if not href or href.startswith(("http://", "https://", "mailto:", "tel:", "#")):
            continue
        target = href.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        assert os.path.exists(os.path.join(ROOT, target)), (
            f"{filename}: link to {href!r} does not resolve to a file on disk"
        )


@pytest.mark.parametrize("filename", PAGES)
def test_fragment_links_resolve_to_a_real_id(filename):
    page = parse(filename)
    for a in page.anchors:
        href = a.get("href", "")
        if "#" not in href:
            continue
        target_file, _, fragment = href.partition("#")
        if fragment in SPECIAL_FRAGMENTS:
            continue
        target_file = target_file or filename
        if not target_file.endswith(".html") or target_file not in PAGES:
            continue  # not a same-site page link; not this test's job
        target_ids = parse(target_file).ids
        assert fragment in target_ids, (
            f"{filename}: link to {href!r} has no matching id on {target_file}"
        )


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------

def test_sitemap_covers_every_page():
    with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as f:
        sitemap = f.read()
    locs = set(re.findall(r"<loc>(.*?)</loc>", sitemap))
    missing = [f for f in PAGES if canonical_url_for(f) not in locs]
    assert not missing, f"pages missing from sitemap.xml: {missing}"
