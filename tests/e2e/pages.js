const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');

// Not a real content page — search-engine ownership verification stub.
// Kept in sync with the EXCLUDE set in tests/htmlkit.py and
// generate_sitemap.py's EXCLUDE_FILES.
const EXCLUDE = new Set(['google7a99f5f52cfafe41.html']);

function allPages() {
  return fs
    .readdirSync(ROOT)
    .filter((f) => f.endsWith('.html') && !EXCLUDE.has(f))
    .sort();
}

module.exports = { allPages, ROOT };
