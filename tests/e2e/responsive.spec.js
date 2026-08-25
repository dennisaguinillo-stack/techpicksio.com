// @ts-check
const { test, expect } = require('@playwright/test');
const { allPages } = require('./pages');

// A common small-phone viewport (iPhone SE-class width).
const MOBILE_VIEWPORT = { width: 375, height: 812 };

test.describe('no horizontal overflow on mobile', () => {
  for (const filename of allPages()) {
    test(`${filename}: no horizontal scroll at 375px`, async ({ browser }) => {
      const context = await browser.newContext({ viewport: MOBILE_VIEWPORT });
      const page = await context.newPage();
      await page.goto(`/${filename}`);

      const { scrollWidth, clientWidth } = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }));

      expect(
        scrollWidth,
        `${filename}: overflows horizontally at 375px (scrollWidth=${scrollWidth}, clientWidth=${clientWidth})`
      ).toBeLessThanOrEqual(clientWidth);

      await context.close();
    });
  }
});
