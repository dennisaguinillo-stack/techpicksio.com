# techpicksio.com

Static HTML/Tailwind affiliate site covering mobile filmmaking gear, served by
GitHub Pages. No build service, no npm in the deploy path.

## Working on it

```bash
# edit src/techpicksio-ui.css, never style.css
bash build.sh                 # regenerate style.css
python3 check-classes.py      # every class in the markup must resolve
python3 -m pytest tests/      # HTML, schema and feed contracts
python3 generate_sitemap.py   # sitemap.xml
python3 generate_feed.py      # feed.xml (RSS 2.0, MSN-ready)
```

CI runs all of the above plus Playwright smoke tests on every push and pull
request. `style.css` is generated — hand-edits are rejected by CI.

## Docs

| File | What it covers |
|---|---|
| `REDESIGN.md` | How the CSS is built and why it is built that way |
| `docs/MEASUREMENT.md` | Which queries and pages to watch in Search Console and Bing, and the monthly AI-citation spot-check |
| `docs/DISTRIBUTION.md` | Pinterest and Reddit copy ready to post, the RSS/MSN setup, and the open account-side follow-ups |
| `methodology.html` | The public statement of how gear is researched and what the site will not claim |

## Non-negotiables

- Every outbound affiliate link carries `target="_blank" rel="sponsored nofollow"`
  and the `?tag=techpicksio-20` tracking tag, with an FTC disclosure visible
  above the first commercial link on the page.
- The site publishes no ratings or scores of its own and makes no hands-on
  testing claims. `tests/test_structured_data.py` enforces the first of those.
- Never sign in to Amazon Associates over a VPN.
