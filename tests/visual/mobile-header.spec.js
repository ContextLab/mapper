/** Mobile header button layout tests (US1). */
import { test, expect } from './fixtures.js';

const LOAD_TIMEOUT = 15000;

async function enterMapMode(page) {
  await page.goto('/');
  await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
  await page.click('#landing-start-btn');
  await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  await page.waitForTimeout(500);
}

test.describe('Mobile Header Button Layout (US1)', () => {
  // Use landscape viewport: phones force landscape on map screen
  test.use({ viewport: { width: 667, height: 375 } });

  test('action buttons are in header-actions container (left group)', async ({ page }) => {
    await enterMapMode(page);
    const headerActions = page.locator('.header-actions');
    await expect(headerActions).toBeVisible();

    // reset, download, upload should be in .header-actions
    const resetBtn = headerActions.locator('[aria-label="Reset all progress"]');
    const exportBtn = headerActions.locator('[aria-label="Export progress as JSON"]');
    const importBtn = headerActions.locator('[aria-label="Import saved progress"]');
    await expect(resetBtn).toBeAttached();
    await expect(exportBtn).toBeAttached();
    await expect(importBtn).toBeAttached();
  });

  test('discovery buttons remain in header-right container (right group)', async ({ page }) => {
    await enterMapMode(page);
    const headerRight = page.locator('.header-right');

    const trophyBtn = headerRight.locator('#trophy-btn');
    const suggestBtn = headerRight.locator('#suggest-btn');
    const shareBtn = headerRight.locator('#share-btn');
    const aboutBtn = headerRight.locator('#about-btn');
    await expect(trophyBtn).toBeAttached();
    await expect(suggestBtn).toBeAttached();
    await expect(shareBtn).toBeAttached();
    await expect(aboutBtn).toBeAttached();
  });

  test('dropdown remains fixed during header scroll', async ({ page }) => {
    await enterMapMode(page);
    const dropdown = page.locator('.domain-selector');
    const dropdownBox = await dropdown.boundingBox();
    expect(dropdownBox).toBeTruthy();

    // Scroll header-actions right
    await page.evaluate(() => {
      const el = document.querySelector('.header-actions');
      if (el) el.scrollLeft = el.scrollWidth;
    });
    await page.waitForTimeout(200);

    const dropdownBoxAfter = await dropdown.boundingBox();
    expect(dropdownBoxAfter.x).toBe(dropdownBox.x);
  });

  test('welcome screen shows only upload (left) and share/info (right)', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    // Import button should be visible
    const importBtn = page.locator('[aria-label="Import saved progress"]');
    await expect(importBtn).toBeVisible();

    // Trophy, suggest, tutorial should be hidden
    await expect(page.locator('#trophy-btn')).not.toBeVisible();
    await expect(page.locator('#suggest-btn')).not.toBeVisible();
    await expect(page.locator('#tutorial-btn')).not.toBeVisible();

    // Share and about should be visible
    await expect(page.locator('#share-btn')).toBeVisible();
    await expect(page.locator('#about-btn')).toBeVisible();

    await page.screenshot({ path: 'tests/visual/screenshots/mobile-header-welcome.png' });
  });

  test('header layout screenshot on map screen', async ({ page }) => {
    await enterMapMode(page);
    await page.screenshot({ path: 'tests/visual/screenshots/mobile-header-map.png' });
  });
});
