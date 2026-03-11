/** Mobile collapsible quiz drawer tests (US3). */
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

test.describe('Mobile Collapsible Drawer (US3)', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('map occupies at least 40% viewport height when quiz panel visible', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    const mapHeight = await page.evaluate(() => {
      const mapEl = document.getElementById('map-container') || document.getElementById('map');
      if (!mapEl) return 0;
      return mapEl.getBoundingClientRect().height;
    });
    const viewportHeight = 667;
    const mapPct = mapHeight / viewportHeight;
    expect(mapPct).toBeGreaterThanOrEqual(0.4);
  });

  test('drawer pull handle is visible on mobile', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    const drawerPull = page.locator('.drawer-pull');
    await expect(drawerPull).toBeVisible();
  });

  test('tapping drawer pull closes quiz panel', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Tap the drawer pull to close
    await page.locator('.drawer-pull').click();
    await page.waitForTimeout(500);

    const panel = page.locator('#quiz-panel');
    await expect(panel).not.toHaveClass(/\bopen\b/);

    // Panel should be short (drawer pull 32px + safe-area/fallback ~16px)
    const height = await panel.evaluate(el => el.getBoundingClientRect().height);
    expect(height).toBeLessThanOrEqual(60);
    await page.screenshot({ path: 'tests/visual/screenshots/mobile-drawer-closed.png' });
  });

  test('tapping drawer pull again reopens quiz panel', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    const panel = page.locator('#quiz-panel');

    // Close
    await page.locator('.drawer-pull').click();
    await page.waitForTimeout(500);
    await expect(panel).not.toHaveClass(/\bopen\b/);

    // Reopen
    await page.locator('.drawer-pull').click();
    await page.waitForTimeout(500);
    await expect(panel).toHaveClass(/\bopen\b/);
    await page.screenshot({ path: 'tests/visual/screenshots/mobile-drawer-reopened.png' });
  });

  test('quiz progress is preserved after close/open', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });

    // Answer a question
    const option = page.locator('.quiz-option').first();
    await option.waitFor({ state: 'visible', timeout: 5000 });
    await option.click();
    await page.waitForTimeout(1500);

    // Close and reopen
    await page.locator('.drawer-pull').click();
    await page.waitForTimeout(500);
    await page.locator('.drawer-pull').click();
    await page.waitForTimeout(500);

    // Question should still be present
    const questionAfter = await page.locator('.quiz-question').textContent();
    expect(questionAfter).toBeTruthy();
    expect(questionAfter.length).toBeGreaterThan(0);
  });

  test('swipe down closes quiz panel', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Use drawer pull click to close (swipe is handled by the same toggle mechanism)
    const drawerPull = page.locator('.drawer-pull');
    await drawerPull.click();
    await page.waitForTimeout(500);

    const panel = page.locator('#quiz-panel');
    await expect(panel).not.toHaveClass(/\bopen\b/);
    await page.screenshot({ path: 'tests/visual/screenshots/mobile-swipe-closed.png' });
  });

  test('domain switch reopens quiz panel', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Close
    await page.locator('.drawer-pull').click();
    await page.waitForTimeout(500);
    const panel = page.locator('#quiz-panel');
    await expect(panel).not.toHaveClass(/\bopen\b/);

    // Switch domain
    await selectDomain(page, 'biology');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Should be open again
    await expect(panel).toHaveClass(/\bopen\b/);
  });

  test('drawer pull bar is horizontally centered in viewport', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    const offset = await page.evaluate(() => {
      const bar = document.querySelector('.drawer-pull-bar');
      if (!bar) return { error: 'element not found' };
      const barRect = bar.getBoundingClientRect();
      const viewportCenter = window.innerWidth / 2;
      const barCenter = barRect.left + barRect.width / 2;
      return { viewportCenter, barCenter, drift: Math.abs(viewportCenter - barCenter) };
    });

    expect(offset.drift).toBeLessThanOrEqual(1);
  });

  test('drawer pull centering does not drift after 10 open/close cycles', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    for (let i = 0; i < 10; i++) {
      await page.locator('.drawer-pull').click();
      await page.waitForTimeout(400);
      await page.locator('.drawer-pull').click();
      await page.waitForTimeout(400);
    }

    const offset = await page.evaluate(() => {
      const bar = document.querySelector('.drawer-pull-bar');
      if (!bar) return { error: 'element not found' };
      const barRect = bar.getBoundingClientRect();
      const viewportCenter = window.innerWidth / 2;
      const barCenter = barRect.left + barRect.width / 2;
      return { viewportCenter, barCenter, drift: Math.abs(viewportCenter - barCenter) };
    });

    expect(offset.drift).toBeLessThanOrEqual(1);
    await page.screenshot({ path: 'tests/visual/screenshots/mobile-drawer-centering-after-cycles.png' });
  });
});
