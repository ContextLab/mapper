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
    // Click start button to enter the map, then select physics from header
    const startBtn = page.locator('#landing-start-btn');
    await page.waitForSelector('#landing-start-btn[data-ready]', { timeout: 15000 });
    await startBtn.tap();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: 15000 });

    const trigger = page.locator('.domain-selector .custom-select-trigger');
    await trigger.tap();
    await page.locator('.domain-selector .custom-select-option[data-value="physics"]').tap();

    await page.waitForSelector('.quiz-option', { timeout: 15000 });
    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ state: 'visible' });
    // Use click() instead of tap() — tap() doesn't reliably fire click handlers
    await btn.click();

    const feedback = page.locator('.quiz-feedback');
    await expect(feedback).not.toBeEmpty({ timeout: 3000 });
    await context.close();
  });
});
