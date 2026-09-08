#!/usr/bin/env python3
"""
build_reviews.py - batch review generator for techpicksio.com

What it does, in order:
  1. Reads verified facts from products.json (you own these numbers).
  2. Asks Gemini for PROSE ONLY, returned as JSON. The model never supplies specs.
  3. Renders each product into a full HTML page using the site's own components,
     reusing the head bootstrap, header and footer lifted from a real page.
  4. Runs compliance checks. A page that fails is written to _drafts/ instead of
     the site root, with the reasons printed.

Usage:
  python build_reviews.py                       # every product in products.json
  python build_reviews.py --only dji-osmo-mobile-6-review
  python build_reviews.py --dry-run             # render from facts, no API call
  python build_reviews.py --force               # overwrite pages that already exist

Requires: pip install google-genai python-dotenv
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
TODAY = date.today().strftime("%d %B %Y")

# --------------------------------------------------------------------------
# 1. Compliance guards - these mirror references/compliance.md
# --------------------------------------------------------------------------

# Phrases that would claim hands-on testing the site has never done.
BANNED_PHRASES = [
    r"\bwe tested\b", r"\bwe've tested\b", r"\bin our test", r"\bour testing\b",
    r"\bwe measured\b", r"\bhands[- ]on\b", r"\blab[- ]verified\b",
    r"\bwe reviewed\b", r"\bafter weeks with\b", r"\bin the field we\b",
    r"\bour rating\b", r"\bwe rate\b", r"\bscore of\b",
]
# Star ratings / scores out of N, and live prices.
BANNED_PATTERNS = [
    (r"\b\d(?:\.\d)?\s*(?:out of|/)\s*(?:5|10)\b", "reads as a first-party rating"),
    (r"\b\d(?:\.\d)?\s*stars?\b", "star rating"),
    (r"[$£€]\s?\d", "live price figure - say 'check price' and link out"),
]

REQUIRED_LINK_ATTRS = ['target="_blank"', 'rel="sponsored nofollow"']

FTC_BLOCK = (
    '<div class="tpi-ftc mt-4 mb-8">\n'
    '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>\n'
    '    <p class="m-0"><strong>FTC Affiliate Disclosure:</strong> As an Amazon Associate, '
    'techpicksio.com earns from qualifying purchases. When you buy through links on our site, '
    'we may earn an affiliate commission at no extra cost to you.</p>\n'
    '</div>'
)

ICON_ARROW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M7 17 17 7M9 7h8v8"/></svg>')
ICON_CHECK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg>')
ICON_CROSS = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>')
ICON_TICK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" '
             'stroke-linecap="round" stroke-linejoin="round" style="width:1rem;height:1rem" '
             'aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>')
ICON_X = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" stroke-linejoin="round" style="width:1rem;height:1rem" '
          'aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>')

# --------------------------------------------------------------------------
# 2. Template scaffolding - lifted from a real page so it can never drift
# --------------------------------------------------------------------------

FALLBACK_BOOTSTRAP = (
    "<script>/* Theme bootstrap - runs before first paint so there is no light flash. */\n"
    "(function(){try{var t=localStorage.getItem('tpi-theme');"
    "if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)')"
    ".matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t);}"
    "catch(e){}})();</script>"
)


def lift(pattern, source, fallback=""):
    """Pull one block out of the template page, or fall back to a known-good copy."""
    m = re.search(pattern, source, re.S | re.I)
    return m.group(0).strip() if m else fallback


def load_template(path):
    """Read an existing article page and extract the parts every page shares."""
    if not path or not Path(path).exists():
        print(f"  ! template {path} not found - using built-in header/footer")
        return {"bootstrap": FALLBACK_BOOTSTRAP, "header": "", "footer": "",
                "progress": '<div class="tpi-progress" aria-hidden="true"></div>',
                "totop": "", "script": ""}

    src = Path(path).read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>.*?</script>", src, re.S | re.I)
    boot = next((s for s in scripts if "tpi-theme" in s and "localStorage" in s), FALLBACK_BOOTSTRAP)
    ui = next((s for s in reversed(scripts) if s is not boot), "")

    return {
        "bootstrap": boot,
        "header": lift(r"<header[^>]*class=\"[^\"]*tpi-header.*?</header>", src),
        "footer": lift(r"<footer[^>]*class=\"[^\"]*tpi-footer.*?</footer>", src),
        "progress": lift(r"<div[^>]*class=\"tpi-progress\"[^>]*></div>", src,
                         '<div class="tpi-progress" aria-hidden="true"></div>'),
        "totop": lift(r"<a[^>]*class=\"[^\"]*tpi-totop.*?</a>", src),
        "script": ui,
    }


# --------------------------------------------------------------------------
# 3. The prompt - prose only, facts supplied, JSON back
# --------------------------------------------------------------------------

VOICE_RULES = """
VOICE (techpicksio.com house style, follow exactly):
- Write the way you would explain it out loud to someone who films on their phone but
  is not an engineer. Short sentences. Everyday words.
- Lead with what it means for the reader, not with the specification.
- Explain jargon on first use or replace it. Established glosses you must reuse:
  ND filter = sunglasses for your lens; CRI = colour accuracy score, higher means
  colours look truer; sustained write speed = whether a drive keeps writing fast during
  a long take; anamorphic = squeezes a wider picture onto the sensor; modularity = how
  much gear you can add; ergonomics = how it feels to hold; vignetting = dark corners.
- No filler openings. Get to the point in the first clause.
- Paragraphs of about three sentences.
- End each explanatory section with who it suits, not a restatement of the spec.
- British-neutral spelling is fine; do not use em dashes in FAQ answers.

HARD RULES (breaking one makes the whole page unusable):
- The site NEVER tests gear. Never write "we tested", "in our testing", "hands-on",
  "we measured", "lab-verified", or anything implying first-party testing.
- Attribute figures to their source instead: "according to {source}", "per the
  published specs", "the rated figure is".
- Invent NO numbers, weights, prices, battery figures, dimensions or model names.
  Use only the facts given below, exactly as written. If you need a number that is not
  in the facts, leave it out and write around it.
- No prices, no star ratings, no scores out of five or ten, no urgency language.
- The cons must be real and specific. A page with no honest drawback reads as an ad.
"""

RESPONSE_SHAPE = """
Return ONE JSON object, nothing else, with exactly these keys:

{
  "meta_title":       "string, under 60 characters, includes the product name",
  "meta_description": "string, under 155 characters, plain language, no price",
  "h1":               "string, the on-page headline",
  "lead":             "string, one short paragraph under the h1",
  "verdict_paragraph":"string, ONE paragraph: what it is, who it is for, why it wins.
                       Recommendation first, reasoning after. No build-up.",
  "spec_why":         { "<exact spec name from the facts>": "one short clause on what
                        that number means for the reader" },
  "sections":         [ { "id": "kebab-case-id",
                          "heading": "string",
                          "paragraphs": ["string", "string"] } ],
  "pros":             ["string", "string", "string"],
  "cons":             ["string", "string"],
  "faq":              [ { "q": "question exactly as given", "a": "plain ASCII answer,
                          2-3 sentences, no em dashes, no quotation marks" } ]
}

"spec_why" must contain one entry for EVERY spec name in the facts, spelled identically.
"sections" must cover the section headings listed in the facts, in that order.
"""


def build_prompt(product):
    facts = {
        "product_name": product["name"],
        "source_of_specs": product.get("source", "the manufacturer's published specifications"),
        "who_it_is_for": product.get("audience", ""),
        "verified_specs": product.get("specs", []),
        "verified_headline_facts": product.get("verdict_facts", []),
        "known_pros_to_expand": product.get("known_pros", []),
        "known_cons_to_expand": product.get("known_cons", []),
        "section_headings": product.get("sections", []),
        "faq_questions": product.get("faq_questions", []),
    }
    return (
        "You are the staff writer for techpicksio.com, a research-based review site for "
        "mobile filmmaking gear.\n"
        f"{VOICE_RULES}\n"
        "VERIFIED FACTS (the only facts you may use):\n"
        f"{json.dumps(facts, indent=2, ensure_ascii=False)}\n"
        f"{RESPONSE_SHAPE}"
    )


def call_gemini(client, prompt, model, attempts=3):
    """One call per product, with a simple backoff for free-tier rate limits."""
    from google.genai import types
    cfg = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.4,
    )
    for i in range(attempts):
        try:
            r = client.models.generate_content(model=model, contents=prompt, config=cfg)
            return json.loads(r.text)
        except Exception as e:            # rate limit, transient 5xx, or bad JSON
            if i == attempts - 1:
                raise
            wait = 8 * (i + 1)
            print(f"  ... retry in {wait}s ({type(e).__name__})")
            time.sleep(wait)


# --------------------------------------------------------------------------
# 4. Rendering - facts go in raw (they may contain entities), prose is escaped
# --------------------------------------------------------------------------

def esc(text):
    """Model-written prose is escaped. Fact values from products.json are not."""
    return html.escape(str(text), quote=False)


def attr(text):
    return html.escape(str(text), quote=True)


def cta(product, tag, extra_class="", label="Check price on Amazon"):
    """An affiliate button, or the site's disabled placeholder when the ASIN is unknown."""
    asin = (product.get("asin") or "").strip()
    cls = f"tpi-btn tpi-btn--cta{(' ' + extra_class) if extra_class else ''}"
    if not asin:
        return (
            '<!-- ASIN NEEDED: replace with '
            f'https://www.amazon.com/dp/REAL_ASIN?tag={tag} -->\n'
            '<span class="tpi-btn" style="background-color:rgb(var(--surface-2));'
            'color:rgb(var(--muted));cursor:not-allowed" title="Affiliate link pending">'
            'Check price (link pending)</span>'
        )
    return (
        f'<a href="https://www.amazon.com/dp/{asin}?tag={tag}" class="{cls}" '
        f'target="_blank" rel="sponsored nofollow">\n            {label}\n            '
        f'{ICON_ARROW}\n        </a>'
    )


def render_verdict(product, copy, tag):
    facts = "".join(
        f'<div class="tpi-fact"><dt>{f["label"]}</dt><dd>{f["value"]}</dd></div>'
        for f in product.get("verdict_facts", [])[:3]
    )
    return f"""<section class="tpi-verdict not-prose" aria-labelledby="verdict-heading">
        <span class="tpi-badge tpi-badge--pick">{product.get("badge", "Review")}</span>
        <h2 id="verdict-heading">{product["name"]}</h2>
        <p>{esc(copy["verdict_paragraph"])}</p>

        <dl class="tpi-verdict__grid">{facts}</dl>

        {cta(product, tag)}
    </section>"""


def render_spec_table(product, copy):
    why = copy.get("spec_why", {}) or {}
    rows = []
    for s in product.get("specs", []):
        note = esc(why.get(s["spec"], ""))
        rows.append(
            f'                <tr>\n'
            f'                    <th scope="row">{s["spec"]}</th>\n'
            f'                    <td data-label="Spec">{s["value"]}</td>\n'
            f'                    <td data-label="Why it matters">{note}</td>\n'
            f'                </tr>'
        )
    body = "\n".join(rows)
    return f"""<div class="tpi-table-wrap not-prose my-8">
        <table class="tpi-table">
            <caption class="sr-only">Published specifications for the {esc(product["name"])}</caption>
            <thead>
                <tr>
                    <th scope="col">Specification</th>
                    <th scope="col">{esc(product["name"])}</th>
                    <th scope="col">What it means for you</th>
                </tr>
            </thead>
            <tbody>
{body}
            </tbody>
        </table>
    </div>"""


def render_pros_cons(copy):
    def items(entries, icon):
        return "\n".join(
            f'                <li>\n                    {icon}\n'
            f'                    <span>{esc(e)}</span>\n                </li>'
            for e in entries
        )
    return f"""<div class="tpi-pc not-prose my-8">
        <div class="tpi-pc__panel tpi-pc__panel--pro">
            <h3 class="tpi-pc__title">{ICON_TICK} Pros</h3>
            <ul class="tpi-pc__list">
{items(copy.get("pros", []), ICON_CHECK)}
            </ul>
        </div>
        <div class="tpi-pc__panel tpi-pc__panel--con">
            <h3 class="tpi-pc__title">{ICON_X} Cons</h3>
            <ul class="tpi-pc__list">
{items(copy.get("cons", []), ICON_CROSS)}
            </ul>
        </div>
    </div>"""


def render_sections(copy):
    out = []
    for s in copy.get("sections", []):
        paras = "\n            ".join(f"<p>{esc(p)}</p>" for p in s.get("paragraphs", []))
        out.append(
            f'        <div class="tpi-measure">\n'
            f'            <h2 id="{s["id"]}">{esc(s["heading"])}</h2>\n'
            f'            {paras}\n        </div>'
        )
    return "\n\n".join(out)


def render_faq(copy):
    """Visible FAQ. The JSON-LD below is built from the same list, so they cannot drift."""
    blocks = []
    for i, f in enumerate(copy.get("faq", [])):
        open_attr = " open" if i == 0 else ""
        blocks.append(
            f'        <details{open_attr}>\n'
            f'            <summary><span>{esc(f["q"])}</span></summary>\n'
            f'            <p>{esc(f["a"])}</p>\n'
            f'        </details>'
        )
    return '<div class="tpi-faq not-prose my-6">\n' + "\n".join(blocks) + "\n    </div>"


def render_toc(copy):
    links = "".join(
        f'<li><a href="#{s["id"]}">{esc(s["heading"])}</a></li>'
        for s in copy.get("sections", [])
    )
    return links


def render_page(product, copy, tpl, defaults):
    tag = defaults.get("affiliate_tag", "techpicksio-20")
    base = defaults.get("site_base", "https://www.techpicksio.com/").rstrip("/") + "/"
    url = f'{base}{product["slug"]}.html'
    img = product.get("image", {})

    # Structured data. No Product/Review rating: the site does not rate gear.
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in copy.get("faq", [])
        ],
    }
    crumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": base},
            {"@type": "ListItem", "position": 2, "name": product["category_label"],
             "item": f'{base}{product["category_anchor"]}'},
            {"@type": "ListItem", "position": 3, "name": product["name"], "item": url},
        ],
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{tpl["bootstrap"]}
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{attr(copy["meta_title"])}</title>
    <meta name="description" content="{attr(copy["meta_description"])}">
    <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
    <meta name="theme-color" content="#0e131b" media="(prefers-color-scheme: dark)">
    <link rel="stylesheet" href="style.css">
    <link rel="canonical" href="{url}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{attr(copy["meta_title"])}">
    <meta property="og:description" content="{attr(copy["meta_description"])}">
    <meta property="og:url" content="{url}">
    <meta property="og:image" content="{base}{img.get('src','')}">
    <meta name="twitter:card" content="summary_large_image">
    <script type="application/ld+json">
{json.dumps(faq_ld, indent=4, ensure_ascii=True)}
    </script>
    <script type="application/ld+json">
{json.dumps(crumb_ld, indent=4, ensure_ascii=True)}
    </script>
</head>
<body class="antialiased bg-slate-50">
    {tpl["progress"]}
    {tpl["header"]}

    <main class="max-w-6xl mx-auto px-4 pb-16" id="top">
        <nav aria-label="Breadcrumb" class="pt-5 pb-1 text-sm">
            <ol class="flex items-center gap-2 list-none p-0 m-0 text-slate-500">
                <li><a href="index.html" class="hover:text-accent transition-colors font-medium">Home</a></li>
                <li aria-hidden="true">&rsaquo;</li>
                <li><a href="{product["category_anchor"]}" class="hover:text-accent transition-colors font-medium">{product["category_label"]}</a></li>
                <li aria-hidden="true">&rsaquo;</li>
                <li aria-current="page" class="text-slate-700 font-semibold">{esc(product["name"])}</li>
            </ol>
        </nav>

        {FTC_BLOCK}

        <div class="tpi-layout">
        <article class="bg-white p-5 md:p-10 rounded-2xl shadow-sm border border-slate-200 prose max-w-none">
            <span class="tpi-badge">Review</span>
            <h1>{esc(copy["h1"])}</h1>
            <p class="text-sm text-slate-500 not-prose">Last updated {TODAY} &middot; Researched from {esc(product.get("source", "published specifications"))}</p>

            <div class="tpi-measure"><p class="lead">{esc(copy["lead"])}</p></div>

            <img src="{img.get('src','')}" width="{img.get('width','')}" height="{img.get('height','')}"
                 alt="{attr(img.get('alt',''))}" fetchpriority="high" decoding="async"
                 class="rounded-xl w-full h-auto my-6">

            {render_verdict(product, copy, tag)}

            <details class="tpi-toc-mobile not-prose">
                <summary>In this review</summary>
                <ul>{render_toc(copy)}</ul>
            </details>

{render_sections(copy)}

            {render_spec_table(product, copy)}

            {render_pros_cons(copy)}

            <div class="tpi-measure"><h2 id="faq">Common questions</h2></div>
            {render_faq(copy)}

            <div class="tpi-measure">
                <p class="text-sm text-slate-500">This review is built from {esc(product.get("source", "published specifications"))}. <a href="about.html">How we research</a>.</p>
            </div>

            <p class="not-prose">{cta(product, tag, "tpi-btn--block")}</p>
        </article>

        <aside class="tpi-toc" aria-label="On this page">
            <div class="tpi-toc__title">On this page</div>
            <ul>{render_toc(copy)}</ul>
            {cta(product, tag, "tpi-btn--block", "Check price")}
        </aside>
        </div>
    </main>

    {tpl["footer"]}

    <div class="tpi-stickybar" id="tpi-stickybar">
        <div class="tpi-stickybar__meta">
            <div class="tpi-stickybar__label">{product.get("badge", "Review")}</div>
            <div class="tpi-stickybar__name">{esc(product["name"])}</div>
        </div>
        {cta(product, tag, "", "Check price")}
    </div>

    {tpl["totop"]}
    {tpl["script"]}
</body>
</html>
"""


# --------------------------------------------------------------------------
# 5. Checks - run on the finished HTML, before it is allowed near the repo
# --------------------------------------------------------------------------

def check(page_html, product, copy):
    problems = []
    text = re.sub(r"<[^>]+>", " ", page_html)

    for pat in BANNED_PHRASES:
        m = re.search(pat, text, re.I)
        if m:
            problems.append(f"testing claim: '{m.group(0)}'")
    for pat, why in BANNED_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            problems.append(f"{why}: '{m.group(0).strip()}'")

    for a in re.findall(r"<a\s[^>]*amazon\.com[^>]*>", page_html, re.I):
        for need in REQUIRED_LINK_ATTRS:
            if need not in a:
                problems.append(f"affiliate link missing {need}")
        if "?tag=" not in a:
            problems.append("affiliate link missing ?tag= tracking tag")

    for td in re.findall(r"<td\b[^>]*>", page_html):
        if "data-label=" not in td:
            problems.append("table cell missing data-label (breaks the mobile card view)")

    if len(copy.get("meta_title", "")) > 60:
        problems.append(f"meta title {len(copy['meta_title'])} chars (limit 60)")
    if len(copy.get("meta_description", "")) > 155:
        problems.append(f"meta description {len(copy['meta_description'])} chars (limit 155)")

    if "FTC Affiliate Disclosure" not in page_html:
        problems.append("FTC disclosure missing")
    if "Amazon Services LLC Associates Program" not in page_html:
        problems.append("footer Associates statement missing (check your template page)")
    if len(copy.get("cons", [])) < 2:
        problems.append("fewer than two cons - reads as an advertisement")

    missing = [s["spec"] for s in product.get("specs", [])
               if s["spec"] not in (copy.get("spec_why") or {})]
    if missing:
        problems.append("no 'why it matters' for: " + ", ".join(missing))

    return sorted(set(problems))


# --------------------------------------------------------------------------
# 6. Runner
# --------------------------------------------------------------------------

def placeholder_copy(product):
    """--dry-run: renders the real layout from facts alone, no API call, no cost."""
    return {
        "meta_title": f'{product["name"]} Review'[:60],
        "meta_description": f'Specs, pros and cons for the {product["name"]}.'[:155],
        "h1": f'{product["name"]} Review',
        "lead": "PLACEHOLDER lead paragraph.",
        "verdict_paragraph": "PLACEHOLDER verdict paragraph.",
        "spec_why": {s["spec"]: "PLACEHOLDER" for s in product.get("specs", [])},
        "sections": [{"id": re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-"),
                      "heading": h, "paragraphs": ["PLACEHOLDER."]}
                     for h in product.get("sections", [])],
        "pros": product.get("known_pros", [])[:3],
        "cons": product.get("known_cons", [])[:2],
        "faq": [{"q": q, "a": "PLACEHOLDER answer."} for q in product.get("faq_questions", [])],
    }


def main():
    ap = argparse.ArgumentParser(description="Batch-generate techpicksio review pages.")
    ap.add_argument("--data", default="products.json")
    ap.add_argument("--only", action="append", help="slug to build (repeatable)")
    ap.add_argument("--out", help="output directory (default: from products.json)")
    ap.add_argument("--template", help="existing page to lift header/footer from")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--force", action="store_true", help="overwrite existing pages")
    ap.add_argument("--dry-run", action="store_true", help="render layout without calling Gemini")
    ap.add_argument("--pause", type=float, default=4.0, help="seconds between API calls")
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    products = [p for p in data["products"]
                if not args.only or p["slug"] in args.only]
    if not products:
        sys.exit("No matching products in " + args.data)

    out_dir = Path(args.out or defaults.get("output_dir", "."))
    drafts = out_dir / "_drafts"
    out_dir.mkdir(parents=True, exist_ok=True)

    tpl = load_template(args.template or defaults.get("template"))

    client = None
    if not args.dry_run:
        load_dotenv()
        key = os.environ.get("GEMINI_API_KEY")
        if not key or "paste_your" in key:
            sys.exit("GEMINI_API_KEY is missing from .env")
        from google import genai
        client = genai.Client(api_key=key)

    passed, flagged, failed = [], [], []

    for i, product in enumerate(products):
        target = out_dir / f'{product["slug"]}.html'
        if target.exists() and not args.force:
            print(f'- {product["slug"]}: exists, skipping (use --force to overwrite)')
            continue

        print(f'> {product["name"]}')
        try:
            copy = placeholder_copy(product) if args.dry_run else \
                call_gemini(client, build_prompt(product), args.model)
            page = render_page(product, copy, tpl, defaults)
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            failed.append(product["slug"])
            continue

        problems = check(page, product, copy)
        if problems:
            drafts.mkdir(parents=True, exist_ok=True)
            path = drafts / f'{product["slug"]}.html'
            path.write_text(page, encoding="utf-8")
            print(f"  HELD in _drafts/ - {len(problems)} issue(s):")
            for p in problems:
                print(f"    - {p}")
            flagged.append(product["slug"])
        else:
            target.write_text(page, encoding="utf-8")
            print(f"  wrote {target}")
            passed.append(product["slug"])

        if client and i < len(products) - 1:
            time.sleep(args.pause)

    print("\n--- summary ---")
    print(f"  clean:   {len(passed)}  {', '.join(passed) or '-'}")
    print(f"  held:    {len(flagged)}  {', '.join(flagged) or '-'}")
    print(f"  failed:  {len(failed)}  {', '.join(failed) or '-'}")
    if passed:
        print("\nNext: python3 check-classes.py && python3 scripts/audit.py " +
              " ".join(f"{s}.html" for s in passed))
        print("Then add each new page to index.html and sitemap.xml by hand.")


if __name__ == "__main__":
    main()
