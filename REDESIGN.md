# techpicksio.com — UI redesign, stage 1

Drop these files into the repo root, overwriting the existing ones. `images/` is
untouched. Nothing here needs npm, node, or a build service — GitHub Pages serves it
as-is.

## What is in this package

| Path | Status | What it is |
|---|---|---|
| `src/tailwind.build.css` | new | The frozen Tailwind v3.4.19 output that was previously `style.css`, kept as the base layer. |
| `src/techpicksio-ui.css` | new | The maintained design layer: tokens, utility re-mapping, and every component. **This is the file you edit.** |
| `build.sh` | new | `cat src/tailwind.build.css src/techpicksio-ui.css > style.css`. Run after editing the design layer. |
| `check-classes.py` | new | Reports classes used in the HTML that have no rule in `style.css`. |
| `style.css` | rebuilt | Generated output. Do not hand-edit — it is overwritten by `build.sh`. |
| `index.html` | redesigned | New header, hero, category sections, card grid, footer. |
| `rode-phone-cage-review.html` | redesigned | The reference article template. |
| 15 other pages | patched | Theme bootstrap script + theme-color metas only. Content untouched. |

## The workflow from here

```bash
# edit src/techpicksio-ui.css
./build.sh                 # regenerate style.css
./check-classes.py         # every class must resolve
git add -A && git commit -m "…" && git push
```

`style.css` is 65KB raw, ~14KB gzipped, and is still the only render-blocking
resource on the site. There are no web fonts and no external scripts.

## Why the CSS is built this way

The original `style.css` was a Tailwind build with no config, no input file, and no
build script in the repo — so no utility class could be added without recompiling
Tailwind somewhere outside the project. Rather than introduce a node toolchain into a
GitHub Pages deploy, the compiled output is frozen as a base layer and everything new
lives in a hand-authored layer appended after it.

Because that layer loads later at equal specificity, it can re-point Tailwind's colour
utilities at theme tokens. That is what makes every page dark-mode-capable without
editing a single class name in the markup.

The trade-off is real and worth stating: new Tailwind utilities are not available for
free. `check-classes.py` exists because of that, and it must pass before you push.

## Known follow-ups (stage 2)

- The other 15 pages still carry the old centred header and footer. They render
  correctly in both themes, but they have no theme toggle — a visitor who lands on one
  of those pages first cannot switch themes until they reach the homepage or the Rode
  review.
- `universal-android-video-cages.html` is in `sitemap.xml` but was linked from no page
  on the site. It is now linked from the homepage's Rigs & Cages section.
- `budget-iphone-rig-under-150.html` still has an "ASIN pending" placeholder button.
- The Related Guides list on the Rode review previously linked to
  `iphone-video-cages.html` twice under two different titles; it is now three distinct
  guides.
