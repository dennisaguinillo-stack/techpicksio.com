"""
Structured-data contracts.

test_html_contracts.py already checks that every JSON-LD block parses and
that FAQ questions exist in the visible copy. These tests go one level
further and check what Google's Rich Results Test checks structurally:
required fields present, entity types correct, and — the part that matters
most on an affiliate site — that the markup does not assert anything the
page itself does not.

The hard rule encoded here is the one in the design system's compliance
reference: techpicksio.com publishes no first-party rating, so no Review
node may carry a reviewRating. Adding one would turn honest research into
a fabricated score in every rich result that quotes it.

Run with: pytest tests/
"""
from __future__ import annotations

import html
import json
import re

import pytest

from htmlkit import ROOT, SITE_URL, all_pages, canonical_url_for, parse

PAGES = all_pages()

ORG_NAME = "techpicksio.com"


def _nodes(filename):
    """Every JSON-LD object on the page, flattened, with its root type."""
    page = parse(filename)
    out = []
    for raw in page.jsonld_raw:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue  # covered by test_jsonld_blocks_are_valid_json
        out.extend(obj if isinstance(obj, list) else [obj])
    return out


def _walk(node):
    """Yield every dict nested anywhere inside a JSON-LD object."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _of_type(filename, wanted):
    return [n for root in _nodes(filename) for n in _walk(root) if n.get("@type") == wanted]


def _raw(filename):
    with open(f"{ROOT}/{filename}", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_every_jsonld_block_declares_context_and_type(filename):
    for i, node in enumerate(_nodes(filename)):
        assert node.get("@context") == "https://schema.org", (
            f"{filename}: JSON-LD block #{i} is missing @context"
        )
        assert node.get("@type"), f"{filename}: JSON-LD block #{i} is missing @type"


@pytest.mark.parametrize("filename", PAGES)
def test_product_nodes_have_a_name_and_brand(filename):
    for product in _of_type(filename, "Product"):
        assert product.get("name"), f"{filename}: a Product node has no name"
        brand = product.get("brand")
        if brand is not None:
            assert brand.get("@type") == "Brand" and brand.get("name"), (
                f"{filename}: Product {product['name']!r} has a malformed brand"
            )


@pytest.mark.parametrize("filename", PAGES)
def test_review_nodes_are_attributed_and_have_a_body(filename):
    for review in _of_type(filename, "Review"):
        author = review.get("author")
        assert author, f"{filename}: a Review node has no author"
        assert author.get("name") == ORG_NAME, (
            f"{filename}: Review is attributed to {author.get('name')!r}; the site has no "
            f"named reviewer, so reviews must be attributed to {ORG_NAME!r}"
        )
        assert review.get("reviewBody", "").strip(), (
            f"{filename}: Review by {author.get('name')!r} has an empty reviewBody"
        )


@pytest.mark.parametrize("filename", PAGES)
def test_no_review_claims_a_rating(filename):
    """The site publishes no first-party score — see references/compliance.md."""
    for node in (n for root in _nodes(filename) for n in _walk(root)):
        for forbidden in ("reviewRating", "aggregateRating", "ratingValue"):
            assert forbidden not in node, (
                f"{filename}: JSON-LD contains {forbidden!r}. techpicksio.com does not "
                f"publish ratings, so a rating in the markup is a fabricated claim."
            )


@pytest.mark.parametrize("filename", PAGES)
def test_review_body_appears_in_the_visible_copy(filename):
    """A Review must quote the page, not add a verdict only crawlers can see."""
    text = re.sub(r"\s+", " ", parse(filename).text)
    for review in _of_type(filename, "Review"):
        body = re.sub(r"\s+", " ", review["reviewBody"]).strip()
        assert body in text, (
            f"{filename}: reviewBody is not present in the visible page copy: {body[:80]!r}…"
        )


@pytest.mark.parametrize("filename", PAGES)
def test_itemlist_entries_are_named_and_positioned(filename):
    """Both schema.org ItemList forms are allowed: a nested `item` node (used by
    the product roundups) or a ListItem carrying its own name (used by the
    ranked how-to lists). Either way every entry needs a name and a position."""
    for lst in _of_type(filename, "ItemList"):
        elements = lst.get("itemListElement", [])
        assert elements, f"{filename}: ItemList {lst.get('name')!r} is empty"
        for i, element in enumerate(elements, 1):
            assert element.get("@type") == "ListItem", (
                f"{filename}: ItemList entry #{i} is not a ListItem"
            )
            assert element.get("position") == i, (
                f"{filename}: ItemList entry #{i} has position {element.get('position')!r}"
            )
            name = element.get("name") or element.get("item", {}).get("name")
            assert name, f"{filename}: ItemList entry #{i} has no name"


# ---------------------------------------------------------------------------
# Markup must match the page
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_breadcrumb_schema_matches_the_visible_trail(filename):
    """Google requires BreadcrumbList to reflect a breadcrumb the reader can see."""
    crumbs = _of_type(filename, "BreadcrumbList")
    nav = re.search(r'<nav aria-label="Breadcrumb".*?</nav>', _raw(filename), re.S)
    if not crumbs:
        assert not nav, f"{filename}: has a visible breadcrumb but no BreadcrumbList markup"
        return
    assert nav, f"{filename}: has BreadcrumbList markup but no visible breadcrumb"

    visible = [
        re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", inner))).strip()
        for attrs, inner in re.findall(r"<li\b([^>]*)>(.*?)</li>", nav.group(0), re.S)
        if "aria-hidden" not in attrs
    ]
    marked = [item["name"] for item in crumbs[0]["itemListElement"]]
    assert marked == visible, (
        f"{filename}: BreadcrumbList {marked} does not match visible trail {visible}"
    )


@pytest.mark.parametrize("filename", PAGES)
def test_breadcrumb_positions_are_sequential_and_resolve(filename):
    for crumb in _of_type(filename, "BreadcrumbList"):
        for i, item in enumerate(crumb["itemListElement"], 1):
            assert item.get("position") == i, f"{filename}: breadcrumb position {i} is wrong"
            assert item.get("name"), f"{filename}: breadcrumb item {i} has no name"
            assert str(item.get("item", "")).startswith(SITE_URL), (
                f"{filename}: breadcrumb item {i} does not point at the site"
            )
        last = crumb["itemListElement"][-1]
        assert last["item"] == canonical_url_for(filename), (
            f"{filename}: the last breadcrumb should be the page's own canonical URL"
        )


@pytest.mark.parametrize("filename", PAGES)
def test_faq_answers_match_the_visible_answers(filename):
    """Mismatched answer text is a structured-data violation, not just a typo."""
    text = re.sub(r"\s+", " ", parse(filename).text)
    for faq in _of_type(filename, "FAQPage"):
        for question in faq.get("mainEntity", []):
            answer = re.sub(r"\s+", " ", question["acceptedAnswer"]["text"]).strip()
            assert answer in text, (
                f"{filename}: FAQ answer is not in the visible copy: {answer[:80]!r}…"
            )


# ---------------------------------------------------------------------------
# Discover / crawler readiness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", PAGES)
def test_large_image_previews_are_opted_in(filename):
    """Without this, Discover only ever gets a thumbnail-sized preview."""
    robots = parse(filename).meta_content(name="robots") or ""
    assert "max-image-preview:large" in robots, (
        f"{filename}: missing <meta name=\"robots\" content=\"max-image-preview:large\">"
    )


@pytest.mark.parametrize("filename", PAGES)
def test_open_graph_is_complete(filename):
    page = parse(filename)
    for prop in ("og:type", "og:title", "og:description", "og:url", "og:image"):
        assert page.meta_content(prop=prop), f"{filename}: missing {prop}"
    image = page.meta_content(prop="og:image")
    assert image.startswith(SITE_URL), f"{filename}: og:image must be an absolute URL"


def test_llms_txt_links_resolve():
    """The AI-facing site map is only useful if every URL in it exists."""
    with open(f"{ROOT}/llms.txt", encoding="utf-8") as f:
        body = f.read()
    for url in re.findall(r"\]\((/[^)]*)\)", body):
        filename = url.lstrip("/")
        assert filename in PAGES, f"llms.txt points at {url!r}, which is not a page in this repo"


def test_llms_txt_lists_every_page_in_the_sitemap():
    with open(f"{ROOT}/llms.txt", encoding="utf-8") as f:
        body = f.read()
    listed = {u.lstrip("/") for u in re.findall(r"\]\((/[^)]*)\)", body)}
    missing = [p for p in PAGES if p != "index.html" and p not in listed]
    assert not missing, f"pages missing from llms.txt: {missing}"


# ---------------------------------------------------------------------------
# Syndication feed
# ---------------------------------------------------------------------------

def _feed():
    import xml.etree.ElementTree as ET
    return ET.parse(f"{ROOT}/feed.xml").getroot().find("channel")


FEED_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
    "atom": "http://www.w3.org/2005/Atom",
}


def test_feed_channel_carries_the_fields_msn_requires():
    channel = _feed()
    for tag in ("title", "link", "description", "language", "lastBuildDate", "copyright"):
        element = channel.find(tag)
        assert element is not None and (element.text or "").strip(), (
            f"feed.xml: channel is missing <{tag}>"
        )
    self_link = channel.find("atom:link", FEED_NS)
    assert self_link is not None and self_link.get("rel") == "self", (
        "feed.xml: channel is missing its atom:link rel=self"
    )


def test_feed_items_are_complete():
    items = _feed().findall("item")
    assert items, "feed.xml: no items"
    for item in items:
        title = item.findtext("title", "")
        for tag in ("title", "link", "guid", "description", "pubDate", "category"):
            assert (item.findtext(tag) or "").strip(), f"feed.xml: {title!r} is missing <{tag}>"
        assert (item.findtext("content:encoded", "", FEED_NS)).strip(), (
            f"feed.xml: {title!r} has no content:encoded — MSN rejects thin feeds"
        )
        assert (item.findtext("dc:creator", "", FEED_NS)).strip(), (
            f"feed.xml: {title!r} has no dc:creator"
        )
        assert item.find("media:content", FEED_NS) is not None, (
            f"feed.xml: {title!r} has no media:content image"
        )


def test_feed_bodies_carry_the_affiliate_disclosure():
    """A syndicated body is a commercial link leaving this domain."""
    for item in _feed().findall("item"):
        body = item.findtext("content:encoded", "", FEED_NS)
        assert "Amazon Services LLC Associates Program" in body, (
            f"feed.xml: {item.findtext('title')!r} carries no affiliate disclosure"
        )


def test_feed_bodies_have_no_relative_urls():
    """A relative link breaks the moment a partner renders the body."""
    for item in _feed().findall("item"):
        body = item.findtext("content:encoded", "", FEED_NS)
        for attr, value in re.findall(r'\b(href|src)="([^"]+)"', body):
            assert value.startswith(("https://", "http://", "mailto:", "#", "data:")), (
                f"feed.xml: {item.findtext('title')!r} has a relative {attr}={value!r}"
            )


def test_feed_covers_every_article_page():
    links = {item.findtext("link") for item in _feed().findall("item")}
    import xml.etree.ElementTree as ET
    missing = []
    for filename in PAGES:
        with open(f"{ROOT}/{filename}", encoding="utf-8") as f:
            source = f.read()
        # Only pages with an <article> and a verdict or checklist body syndicate.
        if "<article" not in source or filename in {
            "about.html", "contact.html", "privacy-policy.html",
            "terms-of-service.html", "methodology.html", "index.html",
        }:
            continue
        if canonical_url_for(filename) not in links:
            missing.append(filename)
    assert not missing, f"feed.xml is missing article pages: {missing}"


@pytest.mark.parametrize("filename", PAGES)
def test_feed_is_discoverable_from_every_page(filename):
    page = parse(filename)
    assert any(
        l.get("rel") == "alternate" and l.get("type") == "application/rss+xml"
        for l in page.link
    ), f"{filename}: no <link rel=\"alternate\" type=\"application/rss+xml\">"


def _syndicated_pages():
    """Pages that appear as items in feed.xml — see EXCLUDE in generate_feed.py."""
    skip = {"about.html", "contact.html", "privacy-policy.html",
            "terms-of-service.html", "methodology.html", "index.html"}
    out = []
    for filename in PAGES:
        if filename in skip:
            continue
        if "<article" in _raw(filename):
            out.append(filename)
    return out


@pytest.mark.parametrize("filename", _syndicated_pages())
def test_every_article_declares_a_publication_date(filename):
    """A feed item's pubDate must come from the page, not from the clock.

    generate_feed.py used to fall back to the file's first git commit. On CI's
    depth-1 clone git sees one commit and attributes every file to it, so each
    merge re-stamped the whole archive and every article resurfaced as new.
    An explicit datePublished is now the only accepted source, so its absence
    has to be a test failure rather than a silently wrong date.
    """
    published = [
        node["datePublished"]
        for node in _nodes(filename)
        if node.get("datePublished")
    ]
    assert published, (
        f"{filename}: no top-level JSON-LD node declares datePublished, so its "
        f"feed pubDate would have no stable source"
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", published[0]), (
        f"{filename}: datePublished {published[0]!r} is not a plain ISO date"
    )


@pytest.mark.parametrize("filename", _syndicated_pages())
def test_feed_pubdate_matches_the_pages_declared_date(filename):
    """The generated feed must agree with the markup it was generated from."""
    from email.utils import parsedate_to_datetime

    declared = next(
        (n["datePublished"] for n in _nodes(filename) if n.get("datePublished")),
        None,
    )
    if declared is None:
        pytest.skip("no datePublished — reported by test_every_article_declares_a_publication_date")
    url = canonical_url_for(filename)
    for item in _feed().findall("item"):
        if item.findtext("link") != url:
            continue
        actual = parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
        assert actual == declared, (
            f"{filename}: feed pubDate is {actual}, page declares {declared}. "
            f"Regenerate with generate_feed.py."
        )
        return
    pytest.fail(f"{filename}: no feed item links to {url}")


def test_itemlist_nodes_do_not_carry_creativework_dates():
    """ItemList is an Intangible; datePublished/dateModified belong on the
    Article node, which every syndicated page now has."""
    for filename in PAGES:
        for lst in _of_type(filename, "ItemList"):
            for key in ("datePublished", "dateModified"):
                assert key not in lst, (
                    f"{filename}: ItemList carries {key!r}, which is not valid on "
                    f"an Intangible — it belongs on the page's Article node"
                )
