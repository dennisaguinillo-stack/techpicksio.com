// @ts-check
const { test, expect } = require('@playwright/test');
const { allPages } = require('./pages');

/**
 * Only some pages currently ship the #tpi-theme-toggle button (see
 * REDESIGN.md). This runs on every page and skips itself where the button
 * isn't present, so a page picks up the assertion automatically the day it
 * gets the toggle.
 */
test.describe('theme toggle', () => {
  for (const filename of allPages()) {
    test(`${filename}: toggle flips data-theme, persists, and updates aria-pressed`, async ({
      page,
    }) => {
      await page.goto(`/${filename}`);

      const toggle = page.locator('#tpi-theme-toggle');
      test.skip((await toggle.count()) === 0, 'page has no theme toggle button yet');

      const before = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
      await toggle.click();
      const after = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));

      expect(after, 'data-theme should flip on click').not.toBe(before);
      expect(['light', 'dark']).toContain(after);

      const stored = await page.evaluate(() => localStorage.getItem('tpi-theme'));
      expect(stored, 'the new theme should be persisted to localStorage').toBe(after);

      const ariaPressed = await toggle.getAttribute('aria-pressed');
      expect(ariaPressed, 'aria-pressed should track whether dark mode is on').toBe(
        after === 'dark' ? 'true' : 'false'
      );
    });
  }
});
