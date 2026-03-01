/** US3: Smart question mode selection visual test. */
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

test.describe('Question Modes (US3)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  });

  test('mode menu renders with all expected buttons', async ({ page }) => {
    const wrapper = page.locator('.modes-wrapper');
    await expect(wrapper).toBeVisible();

    // Should have all 4 question mode buttons (insight modes are currently empty)
    const modeButtons = wrapper.locator('.mode-btn');
    const count = await modeButtons.count();
    expect(count).toBe(4);

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

    // 3 modes require minAnswers > 0 (easy, hardest-can-answer, dont-know)
    expect(disabledCount).toBe(3);

    // Each disabled button should have a data-tooltip attribute
    for (let i = 0; i < disabledCount; i++) {
      const btn = disabledBtns.nth(i);
      const tooltip = await btn.getAttribute('data-tooltip');
      expect(tooltip).toBeTruthy();
      expect(tooltip).toContain('Answer');
    }
  });

  test('insight mode buttons have dashed border style (when present)', async ({ page }) => {
    const insightBtns = page.locator('.mode-btn--insight');
    const count = await insightBtns.count();
    // INSIGHT_MODES is currently empty — verify no insight buttons rendered
    expect(count).toBe(0);
  });

  test('captures screenshot of mode selector', async ({ page }) => {
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'tests/visual/screenshots/mode-selector.png', fullPage: true });
  });
});
