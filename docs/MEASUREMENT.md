# Measurement — techpicksio.com

What to watch, where, and how often. This file exists because most of the work
in Phases 1–3 pays off in places the repository cannot see: Search Console,
Bing Webmaster Tools, and the answer engines. None of that can be automated
from here, so it is written down instead.

---

## Verification status

| Property | Status | Where it lives |
|---|---|---|
| Google Search Console | **Verified, two ways** | `google7a99f5f52cfafe41.html` (file) and the `google-site-verification` meta on `index.html` |
| Bing Webmaster Tools | **Token in repo** — confirm the account side | `BingSiteAuth.xml` |
| IndexNow | **Not set up** | Needs a `<key>.txt` in the repo root; see below |

The Bing token being in the repo is not the same as the property being verified
and the sitemap being submitted. Sign in at bing.com/webmasters and confirm both;
importing the property from Search Console is the fastest route and carries the
existing verification across.

---

## 1. Google Search Console — monthly

### Queries to watch

The Phase 2 silo exists to catch intent that lands upstream of the product
guides. These are the query shapes that should start appearing in Performance
once it is indexed. None of them will show impressions on day one — the silo is
new, and informational pillar pages typically take longer to gain traction than
comparison pages do.

**Starter-kit intent**

- content creator starter kit
- what gear do I need to start content creation
- beginner filmmaking equipment for content creators
- gear to start making videos on your phone
- what do I need to start a youtube channel

**Cost intent**

- how much does it cost to start content creation
- content creation startup cost
- cheapest way to start making videos

**Phone-vs-camera intent**

- can you be a content creator with just a phone
- is a phone good enough for youtube
- phone vs camera for content creation

**Purchase-order intent**

- what should I buy first as a content creator
- first camera gear to buy
- content creator gear checklist

### Pages to watch

| Page | What good looks like |
|---|---|
| `content-creator-starter-kit.html` | The silo's entry point. Watch impressions first; clicks follow position. If impressions grow and CTR stays low, the title and meta description are the problem, not the content. |
| `first-5-purchases-new-creator.html` | Should pick up long-tail "what should I buy first" queries fastest of the five — it answers a narrower question. |
| `cost-to-start-content-creation.html` | Cost queries convert poorly but rank easily. Treat impressions here as a top-of-funnel signal, not a revenue one. |
| `phone-only-content-creation.html` | The most likely of the five to earn an AI-answer citation, because it answers a yes/no question directly in the first sentence. |
| `content-creator-gear-checklist.html` | Watch for "printable"/"checklist" queries and for Discover pickup. |

### Also check monthly

- **Discover tab** — appears in Search Console only once the site is eligible.
  Its absence is not an error; it means no Discover impressions yet.
- **Page indexing report** — every page in `sitemap.xml` should be indexed. A
  page stuck on "Discovered – currently not indexed" for more than a few weeks
  usually means thin content or a crawl-budget problem, not a bug.
- **Core Web Vitals report** — this is *field* data from real visitors and is
  the only version that counts for ranking. Lab measurements taken during
  development showed LCP 284–516ms and CLS 0.0000 under a 4× CPU throttle, but
  field data can differ sharply. INP in particular cannot be measured without
  real interactions.

---

## 2. Bing Webmaster Tools — monthly

Copilot's answers are generated from the Bing index, and MSN partly draws from
the same place, so this is the highest-leverage low-cost surface for the site.

- **Indexation status** — confirm the page count roughly matches `sitemap.xml`.
- **Sitemap submission** — should show as successfully fetched with no errors.
- **IndexNow** — once a key is set up, submissions show a success/failure count
  here. Failures usually mean the key file is not reachable at the URL claimed.

### Setting up IndexNow (one-off, ~10 minutes)

1. Generate a key in Bing Webmaster Tools.
2. Save it as `<key>.txt` in the repo root, containing only the key.
3. On publish, GET
   `https://api.indexnow.org/indexnow?url=<page-url>&key=<key>` — a step worth
   adding to the *Update Sitemap & Feed* workflow once the key exists.

Pages then reach the Bing index within minutes rather than waiting for a crawl.

---

## 3. AI answer engines — monthly, by hand

There is no reliable tool for this yet. Asking the questions directly and
recording what comes back is the only way to track it, and it takes about
fifteen minutes.

Ask each of the five questions below in **ChatGPT, Perplexity, Gemini and
Copilot**, in a fresh conversation each time with no prior context, and record
whether techpicksio.com is cited, linked, or paraphrased without attribution.

### The five target questions

1. *What gear do I need to start content creation on my phone?*
2. *What's the best wireless lavalier mic under $100?*
3. *Will a MagSafe phone cage work on a Samsung Galaxy?*
4. *How much does it cost to start making videos?*
5. *Do I need a camera or is my phone good enough for YouTube?*

### What to record

| Date | Engine | Question # | Cited? | Which page | Notes |
|---|---|---|---|---|---|
| | | | linked / named / paraphrased / absent | | which competitor was cited instead |

**How to read the result.** "Paraphrased without attribution" is a partial win
worth noting separately from "absent" — it means the content is in the model's
retrieved set and the phrasing is not distinctive enough to attribute. That is
usually fixed by tightening the Direct Answer Block into a more quotable
sentence, not by adding more content.

Consistently losing to the same competitor on a question is the useful signal:
open their page and compare the first two sentences under the heading against
ours. The answer is almost always that theirs states the conclusion earlier.

---

## 4. What the repository already checks

These run in CI on every push and pull request, so they do not need a monthly
review — a failure is a build failure.

| Check | Command |
|---|---|
| HTML contracts: canonicals, titles, OG tags, affiliate-link compliance, FTC disclosure, heading structure, internal links | `pytest tests/` |
| Structured data: required fields, breadcrumb-to-visible parity, FAQ answer parity, the no-ratings rule | `pytest tests/` |
| Feed completeness and disclosure in every syndicated body | `pytest tests/` |
| `llms.txt` URLs resolve and cover every page | `pytest tests/` |
| Every CSS class in markup resolves | `python3 check-classes.py` |
| `style.css` matches `src/` | `bash build.sh && git diff --exit-code style.css` |
| `sitemap.xml` and `feed.xml` match the pages on disk | `python3 generate_sitemap.py` / `generate_feed.py` |
| Contrast, tap targets, overflow, console errors, in both themes at 375/768/1280 | `python3 scripts/audit.py` (techpicksio-ui skill) |

---

## Cadence

| When | Do this |
|---|---|
| **On publish** | Regenerate `sitemap.xml` and `feed.xml` (the workflow does this on push to `main`). Ping IndexNow once a key exists. |
| **Monthly** | Sections 1–3 above. Budget 30 minutes. |
| **Quarterly** | Re-read the top five guides against current manufacturer specs. Update the visible "last updated" date only where something actually changed — a date bumped without a change is the kind of signal Google learns to ignore. |
| **When a guide drops in position** | Compare its Direct Answer Block against whoever replaced it before touching anything else. |

---

## Open items that need the site owner

See `docs/DISTRIBUTION.md` for the full list. The two that block measurement
specifically:

- **Bing Webmaster Tools** — confirm the property is verified and the sitemap is
  submitted. Nothing in section 2 can be read until it is.
- **Hero images ≥1200px wide** — every image in `images/` is at most 800px wide.
  Google Discover wants 1200px minimum, so Discover impressions are unlikely to
  appear in section 1 until that is fixed, regardless of everything else.
