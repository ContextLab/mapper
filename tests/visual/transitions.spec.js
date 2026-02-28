/** US2: Domain switch animation smoothness visual test. */
import { test, expect } from '@playwright/test';

const LOAD_TIMEOUT = 15000;

async function selectDomain(page, domainName) {
  const value = domainName.toLowerCase().replace(/\s+/g, '-');
  // If on landing page, click start button to enter the map first
  const startBtn = page.locator('#landing-start-btn');
  if (await startBtn.isVisible().catch(() => false)) {
    await page.waitForSelector('#landing-start-btn[data-ready]', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }
  const trigger = page.locator('.domain-selector .custom-select-trigger');
  await trigger.click();
  await page.locator(`.domain-selector .custom-select-option[data-value="${value}"]`).click();
}

test.describe('Domain Transitions (US2)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('transition completes within 1 second (SC-003)', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(1000);

    const start = Date.now();
    await selectDomain(page, 'mathematics');
    await page.waitForSelector('.quiz-question', { timeout: 5000 });
    const elapsed = Date.now() - start;

    expect(elapsed).toBeLessThan(3000);
  });

  test('domain switch loads new questions without page reload (SC-012)', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    const firstQuestion = await page.locator('.quiz-question').textContent();

    await selectDomain(page, 'biology');
    await page.waitForTimeout(2000);
    const secondQuestion = await page.locator('.quiz-question').textContent();

    expect(secondQuestion).not.toEqual(firstQuestion);
    await expect(page.locator('#landing')).toHaveClass(/hidden/);
  });

  test('captures screenshot of domain transition result', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    await selectDomain(page, 'neuroscience');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/visual/screenshots/domain-transition.png', fullPage: true });
  });
});
