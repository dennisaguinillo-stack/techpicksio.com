#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# techpicksio.com — stylesheet build
#
# style.css = compiled Tailwind build  +  hand-authored UI design layer
#
# There is no npm/node dependency. src/tailwind.build.css is the frozen
# Tailwind v3.4.19 output that shipped with the site; src/techpicksio-ui.css
# is the maintained design layer. Edit the design layer, run this, commit.
#
#   ./build.sh
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

cat src/tailwind.build.css src/techpicksio-ui.css > style.css

printf 'style.css rebuilt — %s bytes (%s gzipped)\n' \
  "$(wc -c < style.css)" \
  "$(gzip -c style.css | wc -c)"
