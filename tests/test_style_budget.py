"""style.css is the only render-blocking resource on the site (no web
fonts, no external scripts — see build.sh). Guard its gzipped size so a
future change can't quietly blow the budget.
"""
import gzip
import os

from htmlkit import ROOT

# Current size is ~14KB gzipped (REDESIGN.md). 20KB leaves real headroom
# for new components while still catching a genuine bloat regression.
BUDGET_BYTES = 20 * 1024


def test_style_css_gzipped_size_is_within_budget():
    with open(os.path.join(ROOT, "style.css"), "rb") as f:
        raw = f.read()
    gzipped_size = len(gzip.compress(raw, compresslevel=9))
    assert gzipped_size <= BUDGET_BYTES, (
        f"style.css is {gzipped_size} bytes gzipped, over the {BUDGET_BYTES} "
        f"byte budget"
    )
