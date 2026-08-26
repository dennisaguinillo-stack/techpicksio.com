// @ts-check
const { test, expect } = require('@playwright/test');
const { allPages } = require('./pages');

/**
 * Every page carries the theme bootstrap script and, via
 * src/techpicksio-ui.css, has its Tailwind slate utilities remapped to
 * theme custom properties — so the page should render in dark mode when
 * the OS prefers it, even on the pages that don't yet have a visible
 * toggle button (see REDESIGN.md's "known follow-ups").
 */
test.describe('dark mode follows OS preference', () => {
  for (const filename of allPages()) {
    test(`${filename}: renders on a dark ground under prefers-color-scheme: dark`, async ({
      browser,
    }) => {
      const context = await browser.newContext({ colorScheme: 'dark' });
      const page = await context.newPage();
      await page.goto(`/${filename}`);

      const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      const [r, g, b] = bg.match(/\d+/g).map(Number);
      const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;

      expect(luminance, `${filename}: body background was ${bg}, expected a dark ground`).toBeLessThan(80);

      await context.close();
    });
  }
});
