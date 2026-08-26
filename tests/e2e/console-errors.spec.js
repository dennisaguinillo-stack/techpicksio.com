// @ts-check
const { test, expect } = require('@playwright/test');
const { allPages } = require('./pages');

test.describe('no console or page errors on load', () => {
  for (const filename of allPages()) {
    test(`${filename}: loads without console errors`, async ({ page }) => {
      const errors = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') errors.push(msg.text());
      });
      page.on('pageerror', (err) => errors.push(err.message));

      await page.goto(`/${filename}`);
      await page.waitForLoadState('networkidle');

      expect(errors, `console/page errors on ${filename}`).toEqual([]);
    });
  }
});
