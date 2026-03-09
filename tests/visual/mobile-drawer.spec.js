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

    // Panel should be short (just the drawer pull bar, ~48px)
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

  test('swipe down closes quiz panel', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
      hasTouch: true,
    });
    const page = await context.newPage();
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });

    await selectDomain(page, 'physics');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    const panel = page.locator('#quiz-panel');
    const box = await panel.boundingBox();

    // Simulate swipe down via touch events
    await page.touchscreen.tap(box.x + box.width / 2, box.y + 20);
    await page.evaluate(({ x, startY, endY }) => {
      const el = document.querySelector('#quiz-panel');
      el.dispatchEvent(new TouchEvent('touchstart', {
        touches: [new Touch({ identifier: 0, target: el, clientX: x, clientY: startY })],
      }));
      el.dispatchEvent(new TouchEvent('touchend', {
        changedTouches: [new Touch({ identifier: 0, target: el, clientX: x, clientY: endY })],
      }));
    }, { x: box.x + box.width / 2, startY: box.y + 20, endY: box.y + 100 });
    await page.waitForTimeout(500);

    // Panel should be closed
    await expect(panel).not.toHaveClass(/\bopen\b/);
    await page.screenshot({ path: 'tests/visual/screenshots/mobile-swipe-closed.png' });
    await context.close();
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
});
