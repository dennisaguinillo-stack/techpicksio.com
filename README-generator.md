# Batch review generator — how to use it

Three files sit next to each other, inside your `techpicksio.com` repo folder:

```
techpicksio.com/
├── build_reviews.py     ← the script
├── products.json        ← your verified facts
├── .env                 ← your Gemini key
├── rode-phone-cage-review.html   ← the page it copies the header/footer from
└── style.css, index.html, images/ ...
```

## One-time setup

```bash
pip install google-genai python-dotenv
```

Your `.env` only needs one line now — the Serper key isn't used:

```
GEMINI_API_KEY="your_google_ai_studio_key"
```

## The important idea

Gemini never writes the numbers. You put every spec, weight, battery figure and ASIN
into `products.json`. The script hands those to Gemini as fixed facts and asks only for
the writing around them, then builds the page itself from your own components.

That's what stops it inventing a weight, and it's why the output already has the right
classes, the FTC box, the frozen comparison table, the pros/cons panels and the theme
script — none of that is left to the model.

## Adding a product

Copy one block in `products.json` and fill it in. The fields that matter:

- `slug` — becomes the filename, e.g. `dji-osmo-mobile-6-review.html`
- `verdict_facts` — exactly three, the ones a buyer compares across products
- `specs` — the table. You give the value; Gemini writes the "what it means for you" column
- `known_pros` / `known_cons` — rough notes are fine, it turns them into sentences
- `sections` — the H2 headings you want, in order
- `faq_questions` — real search questions; answers get written and mirrored into the
  structured data automatically
- `asin` — leave it empty and you get the site's "link pending" placeholder instead of
  a guessed link that 404s

## Running it

```bash
python3 build_reviews.py --dry-run        # builds the layout with PLACEHOLDER text, no API cost
python3 build_reviews.py                  # every product
python3 build_reviews.py --only dji-osmo-mobile-6-review
python3 build_reviews.py --force          # overwrite pages that already exist
```

Free Gemini keys are rate-limited, so it waits 4 seconds between products. Raise it with
`--pause 8` if you get retry messages.

## What happens to a bad page

Before writing anything, the script checks the finished HTML for:

- testing language ("we tested", "hands-on", "we measured")
- star ratings, scores out of five or ten, and dollar figures
- affiliate links missing `target="_blank"`, `rel="sponsored nofollow"` or the `?tag=`
- table cells missing `data-label`, which breaks the mobile card view
- meta title over 60 characters, meta description over 155
- a missing FTC box or Associates footer line
- fewer than two cons

A page that fails goes to `_drafts/` with the reasons printed, and never lands in your
site root. A page that passes is written next to your other articles.

## After it runs

The script doesn't touch anything else, so finish by hand:

```bash
python3 check-classes.py
python3 scripts/audit.py your-new-page.html
```

Then add the new page to `index.html` and `sitemap.xml`, and drop the product photo into
`images/` at the width and height you put in `products.json`.

Read the copy once before you commit. The facts are yours and the structure is fixed, but
the sentences are still a first draft.
