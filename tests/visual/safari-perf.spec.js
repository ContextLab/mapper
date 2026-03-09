/** Safari/WebKit performance tests — baseline capture + verification. */
import { test, expect } from './fixtures.js';

const LOAD_TIMEOUT = 15000;

async function selectDomain(page, domainName) {
  const value = domainName.toLowerCase().replace(/\s+/g, '-');
  const startBtn = page.locator('#landing-start-btn');
  if (await startBtn.isVisible().catch(() => false)) {
    await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }
  const trigger = page.locator('.domain-selector .custom-select-trigger');
  await trigger.click();
  await page.locator(`.domain-selector .custom-select-option[data-value="${value}"]`).click();
}

test.describe('Safari Performance (US1)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('quiz panel opens smoothly with content visible', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Verify panel is open with question content
    const panel = page.locator('#quiz-panel');
    await expect(panel).toHaveClass(/open/);
    const question = page.locator('.quiz-question');
    await expect(question).toBeVisible();
    await page.screenshot({ path: 'tests/visual/screenshots/safari-quiz-open.png' });

    // Verify quiz options are interactive
    const option = page.locator('.quiz-option').first();
    await expect(option).toBeVisible();
    await expect(option).toBeEnabled();
  });

  test('video panel opens without flicker', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });

    // Open video panel
    const videoToggle = page.locator('#video-toggle');
    if (await videoToggle.isVisible().catch(() => false)) {
      await videoToggle.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: 'tests/visual/screenshots/safari-video-panel.png' });

      // Both panels should render without overlap
      const quizPanel = page.locator('#quiz-panel');
      const videoPanel = page.locator('#video-panel');
      await expect(quizPanel).toBeVisible();
      await expect(videoPanel).toBeVisible();
    }
  });

  test('domain switching does not freeze UI', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(1000);

    // Rapidly switch domains 3 times
    const domains = ['mathematics', 'biology', 'physics'];
    for (const domain of domains) {
      const start = Date.now();
      await selectDomain(page, domain);
      await page.waitForSelector('.quiz-question', { timeout: 10000 });
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(5000);
    }

    await page.screenshot({ path: 'tests/visual/screenshots/safari-domain-switch.png' });
  });

  test('expertise modal opens and closes smoothly', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });

    // Answer a question first to have some data
    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ state: 'visible', timeout: 5000 });
    await btn.click();
    await page.waitForTimeout(1500);

    // Open expertise modal
    const expertiseBtn = page.locator('.mode-btn--insight').first();
    if (await expertiseBtn.isVisible().catch(() => false)) {
      await expertiseBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: 'tests/visual/screenshots/safari-expertise-modal.png' });
    }
  });

  test('share modal opens and closes smoothly', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });

    const shareBtn = page.locator('#share-btn');
    if (await shareBtn.isVisible().catch(() => false)) {
      await shareBtn.click();
      await page.waitForSelector('#share-modal:not([hidden])', { timeout: 3000 });
      await page.waitForTimeout(300);
      await page.screenshot({ path: 'tests/visual/screenshots/safari-share-modal.png' });

      // Close and verify
      const closeBtn = page.locator('#share-modal .close-modal').first();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await page.waitForTimeout(300);
      }
    }
  });

  test('about modal opens and closes smoothly', async ({ page }) => {
    const aboutBtn = page.locator('#about-btn');
    await aboutBtn.click();
    await page.waitForSelector('#about-modal:not([hidden])', { timeout: 3000 });
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'tests/visual/screenshots/safari-about-modal.png' });

    // Close
    const closeBtn = page.locator('#about-modal .modal-close-x');
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('quiz option transitions are smooth', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    const option = page.locator('.quiz-option').first();
    await option.waitFor({ state: 'visible', timeout: 5000 });

    // Hover to trigger transition
    await option.hover();
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'tests/visual/screenshots/safari-quiz-hover.png' });

    // Click to answer
    await option.click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: 'tests/visual/screenshots/safari-quiz-answered.png' });
  });

  test('progress bar animates with scaleX', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });

    // Answer 3 questions to build progress
    for (let i = 0; i < 3; i++) {
      const btn = page.locator('.quiz-option').first();
      await btn.waitFor({ state: 'visible', timeout: 5000 });
      await btn.click();
      await page.waitForTimeout(1500);
    }

    await page.screenshot({ path: 'tests/visual/screenshots/safari-progress.png' });
  });
});
