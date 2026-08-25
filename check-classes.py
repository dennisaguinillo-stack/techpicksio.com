#!/usr/bin/env python3
"""
techpicksio.com — dead-class checker.

style.css is a FROZEN Tailwind build plus a hand-authored design layer. A class
that was never compiled silently does nothing, which is the most likely way a
layout regression sneaks in. This script reports every class used in the HTML
that has no matching rule in style.css.

    ./check-classes.py            # check every .html in the repo
    ./check-classes.py index.html # check one page

Exit code 1 if anything is unresolved, so it can gate a commit hook or CI job.
"""
import glob
import re
import sys

# Marker classes that intentionally have no rule of their own: the typography
# plugin references `not-prose` from inside :not() selectors, `group` is a
# hook for group-hover variants, and `lead` marks the "quick answer" intro
# paragraph on article pages — always paired with text-lg/text-slate-600/mb-8,
# which already provide its whole visual treatment.
IGNORE = {"not-prose", "group", "lead"}


def escape(cls: str) -> str:
    """Escape a class name the way Tailwind escapes it in compiled CSS."""
    return re.sub(r"([:/.\[\]()%,#!])", r"\\\1", cls)


def is_resolved(cls: str, css: str) -> bool:
    """Whether `cls` has a matching selector somewhere in `css`.

    A plain substring check would call "p-8" resolved on the strength of an
    unrelated ".p-80" rule, since ".p-8" is a substring of ".p-80". This
    requires a real selector boundary right after the match — the next
    character (a combinator, a pseudo-class colon, end of string, ...) must
    not be one that could continue the same class name.
    """
    needle = re.escape("." + escape(cls))
    return re.search(needle + r"(?![A-Za-z0-9_-])", css) is not None


def main() -> int:
    css = open("style.css", encoding="utf-8").read()
    files = sys.argv[1:] or sorted(glob.glob("*.html"))
    total = 0

    for path in files:
        html = open(path, encoding="utf-8").read()
        used = {c for attr in re.findall(r'class="([^"]*)"', html) for c in attr.split()}
        missing = sorted(
            c for c in used
            if c not in IGNORE
            and not c.startswith("tpi-")
            and not is_resolved(c, css)
        )
        if missing:
            total += len(missing)
            print(f"{path}: {len(missing)} unresolved -> {', '.join(missing)}")

    if total:
        print(f"\n{total} unresolved class(es). Add them to src/techpicksio-ui.css, then ./build.sh")
        return 1

    print(f"All classes resolve across {len(files)} page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
