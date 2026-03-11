/** Mobile colorbar visibility and touch tests (US3). */
import { test, expect } from './fixtures.js';

const LOAD_TIMEOUT = 15000;

async function setupWithHeatmap(page) {
  await page.goto('/');
  await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
  await page.click('#landing-start-btn');
  await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
  await page.waitForTimeout(500);

  // Answer a question so heatmap renders
  const option = page.locator('.quiz-option').first();
  await option.waitFor({ state: 'visible', timeout: 5000 });
  await option.click();
  await page.waitForTimeout(1500);
}

test.describe('Mobile Colorbar Visibility (US3)', () => {
  // Use landscape viewport: phones force landscape on map screen
  test.use({ viewport: { width: 667, height: 375 } });

  test('colorbar is visible on mobile portrait after answering a question', async ({ page }) => {
    await setupWithHeatmap(page);

    const colorbar = page.locator('.map-colorbar');
    await expect(colorbar).toBeVisible();

    const box = await colorbar.boundingBox();
    expect(box).toBeTruthy();
    expect(box.x).toBeGreaterThan(0);
    expect(box.y).toBeGreaterThan(0);
    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);

    await page.screenshot({ path: 'tests/visual/screenshots/mobile-colorbar-visible.png' });
  });

  test('colorbar does not overlap with quiz panel', async ({ page }) => {
    await setupWithHeatmap(page);

    const colorbar = page.locator('.map-colorbar');
    const panel = page.locator('#quiz-panel');

    const colorbarBox = await colorbar.boundingBox();
    const panelBox = await panel.boundingBox();

    expect(colorbarBox).toBeTruthy();
    expect(panelBox).toBeTruthy();

    // Colorbar bottom should be above panel top
    const colorbarBottom = colorbarBox.y + colorbarBox.height;
    expect(colorbarBottom).toBeLessThanOrEqual(panelBox.y);
  });

  test('colorbar remains visible when quiz panel is expanded', async ({ page }) => {
    await setupWithHeatmap(page);

    const colorbar = page.locator('.map-colorbar');
    await expect(colorbar).toBeVisible();

    // Verify colorbar is within the visible viewport
    const colorbarBox = await colorbar.boundingBox();
    expect(colorbarBox).toBeTruthy();
    expect(colorbarBox.x).toBeGreaterThanOrEqual(0);
    expect(colorbarBox.y).toBeGreaterThanOrEqual(0);
    expect(colorbarBox.x + colorbarBox.width).toBeLessThanOrEqual(667);
    expect(colorbarBox.y + colorbarBox.height).toBeLessThanOrEqual(375);
  });

  test('colorbar does not overlap with header', async ({ page }) => {
    await setupWithHeatmap(page);

    const colorbar = page.locator('.map-colorbar');
    const header = page.locator('#app-header');

    const colorbarBox = await colorbar.boundingBox();
    const headerBox = await header.boundingBox();

    expect(colorbarBox).toBeTruthy();
    expect(headerBox).toBeTruthy();

    // Colorbar top should be below header bottom
    const headerBottom = headerBox.y + headerBox.height;
    expect(colorbarBox.y).toBeGreaterThanOrEqual(headerBottom);
  });
});

test.describe('Desktop Colorbar Visibility (US2)', () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test('colorbar does not overlap with side quiz panel on desktop', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
    await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
    await page.click('#landing-start-btn');
    await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(500);

    const option = page.locator('.quiz-option').first();
    await option.waitFor({ state: 'visible', timeout: 5000 });
    await option.click();
    await page.waitForTimeout(1500);

    const colorbar = page.locator('.map-colorbar');
    const panel = page.locator('#quiz-panel');

    const colorbarBox = await colorbar.boundingBox();
    const panelBox = await panel.boundingBox();

    expect(colorbarBox).toBeTruthy();
    expect(panelBox).toBeTruthy();

    // On desktop, colorbar right edge should be left of panel left edge
    const colorbarRight = colorbarBox.x + colorbarBox.width;
    expect(colorbarRight).toBeLessThanOrEqual(panelBox.x);
  });
});
