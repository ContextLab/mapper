import { test, expect } from '@playwright/test';

test.describe('Responsive Layout (SC-008)', () => {
  test('mobile viewport 375x667 is usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 375, height: 667 } });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });

    const minimap = page.locator('#minimap-container');
    await expect(minimap).toBeHidden();

    await page.screenshot({ path: 'tests/visual/screenshots/mobile-375x667.png', fullPage: true });
    await context.close();
  });

  test('tablet viewport 768x1024 is usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 768, height: 1024 } });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });
    await page.screenshot({ path: 'tests/visual/screenshots/tablet-768x1024.png', fullPage: true });
    await context.close();
  });

  test('desktop viewport 1280x800 is usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });
    await page.screenshot({ path: 'tests/visual/screenshots/desktop-1280x800.png', fullPage: true });
    await context.close();
  });

  test('touch tap on answer button works on mobile (T062)', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
      hasTouch: true,
    });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForSelector('.domain-selector:not([hidden])', { timeout: 15000 });

    const sel = page.locator('.domain-selector select');
    if (await sel.count() > 0) {
      await sel.selectOption('physics');
    }
    await page.waitForSelector('.quiz-option', { timeout: 15000 });
    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ state: 'visible' });
    await btn.tap();
    await page.waitForTimeout(500);

    const feedback = page.locator('.quiz-feedback');
    await expect(feedback).not.toBeEmpty();
    await context.close();
  });
});
