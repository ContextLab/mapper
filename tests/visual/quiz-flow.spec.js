import { test, expect } from '@playwright/test';

const LOAD_TIMEOUT = 15000;

async function selectDomain(page, domainName) {
  const sel = page.locator('.domain-selector select');
  if (await sel.count() > 0) {
    const value = domainName.toLowerCase().replace(/\s+/g, '-');
    await sel.selectOption(value);
  }
}

test.describe('Quiz Flow (US1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('captures map view after domain load', async ({ page }) => {
    await page.waitForSelector('.domain-selector:not([hidden])', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/visual/screenshots/map-view.png', fullPage: true });
  });

  test('captures quiz panel with active question', async ({ page }) => {
    await page.waitForSelector('.domain-selector:not([hidden])', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'tests/visual/screenshots/quiz-active.png', fullPage: true });
  });

  test('shows feedback after answering', async ({ page }) => {
    await page.waitForSelector('.domain-selector:not([hidden])', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ state: 'visible', timeout: 5000 });
    await btn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'tests/visual/screenshots/quiz-feedback.png', fullPage: true });
  });

  test('captures about modal', async ({ page }) => {
    await page.locator('#about-btn').click();
    await page.waitForSelector('#about-modal:not([hidden])', { timeout: 3000 });
    await page.screenshot({ path: 'tests/visual/screenshots/about-modal.png', fullPage: true });
  });

  test('no raw $ delimiters in rendered question text (T057)', async ({ page }) => {
    await page.waitForSelector('.domain-selector:not([hidden])', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'mathematics');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(1000);
    const html = await page.locator('.quiz-question').innerHTML();
    const rawDollars = html.match(/(?<!\\)\$[^$]+\$/g);
    expect(rawDollars).toBeNull();
  });

  test('first question appears within 60s of page load (T058)', async ({ page }) => {
    const start = Date.now();
    await page.waitForSelector('.domain-selector:not([hidden])', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForSelector('.quiz-question', { timeout: 60000 });
    expect(Date.now() - start).toBeLessThan(60000);
  });
});
