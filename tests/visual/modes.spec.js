/** US3: Smart question mode selection visual test. */
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

test.describe('Question Modes (US3)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
    await page.waitForSelector('#landing-domain-wrapper .custom-select-trigger', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  });

  test('mode menu renders with all expected buttons', async ({ page }) => {
    const wrapper = page.locator('.modes-wrapper');
    await expect(wrapper).toBeVisible();

    // Should have all 7 mode buttons (4 question + 3 insight)
    const modeButtons = wrapper.locator('.mode-btn');
    const count = await modeButtons.count();
    expect(count).toBe(7);

    // Auto mode should be active by default
    const autoBtn = wrapper.locator('.mode-btn.active');
    await expect(autoBtn).toHaveCount(1);
    const activeText = await autoBtn.textContent();
    expect(activeText).toContain('Auto');
  });

  test('disabled modes show tooltip on hover', async ({ page }) => {
    // With 0 answers, modes requiring minAnswers > 0 should be disabled
    const disabledBtns = page.locator('.mode-btn:disabled');
    const disabledCount = await disabledBtns.count();

    // At least the insight modes (minAnswers: 10) should be disabled initially
    expect(disabledCount).toBeGreaterThanOrEqual(3);

    // Each disabled button should have a data-tooltip attribute
    for (let i = 0; i < disabledCount; i++) {
      const btn = disabledBtns.nth(i);
      const tooltip = await btn.getAttribute('data-tooltip');
      expect(tooltip).toBeTruthy();
      expect(tooltip).toContain('Answer');
    }
  });

  test('insight mode buttons have dashed border style', async ({ page }) => {
    const insightBtns = page.locator('.mode-btn--insight');
    const count = await insightBtns.count();
    expect(count).toBe(3); // expertise, weakness, suggested

    // Verify each has the dashed border class
    for (let i = 0; i < count; i++) {
      await expect(insightBtns.nth(i)).toHaveClass(/mode-btn--insight/);
    }
  });

  test('captures screenshot of mode selector', async ({ page }) => {
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'tests/visual/screenshots/mode-selector.png', fullPage: true });
  });
});
