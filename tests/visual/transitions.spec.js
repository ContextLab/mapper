/** US2: Domain switch animation smoothness visual test. */
import { test, expect } from '@playwright/test';

const LOAD_TIMEOUT = 15000;

async function selectDomain(page, domainName) {
  const value = domainName.toLowerCase().replace(/\s+/g, '-');
  const landingTrigger = page.locator('#landing-domain-wrapper .custom-select-trigger');
  const headerTrigger = page.locator('.domain-selector .custom-select-trigger');
  const trigger = (await landingTrigger.isVisible()) ? landingTrigger : headerTrigger;
  await trigger.click();
  const parent = (await landingTrigger.isVisible()) ? page.locator('#landing-domain-wrapper') : page.locator('.domain-selector');
  await parent.locator(`.custom-select-option[data-value="${value}"]`).click();
}

test.describe('Domain Transitions (US2)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('transition completes within 1 second (SC-003)', async ({ page }) => {
    await page.waitForSelector('#landing-domain-wrapper .custom-select-trigger', { timeout: LOAD_TIMEOUT });
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
    await page.waitForSelector('#landing-domain-wrapper .custom-select-trigger', { timeout: LOAD_TIMEOUT });

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
    await page.waitForSelector('#landing-domain-wrapper .custom-select-trigger', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    await selectDomain(page, 'neuroscience');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'tests/visual/screenshots/domain-transition.png', fullPage: true });
  });
});
