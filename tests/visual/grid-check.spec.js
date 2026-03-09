/** Verify heatmap grid cells are visible on the map canvas. */
import { test, expect } from './fixtures.js';

const LOAD_TIMEOUT = 15000;

test('grid lines visible on heatmap after answering questions', async ({ page }) => {
  await page.goto('/');
  await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
  await page.click('#landing-start-btn');
  await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
  await page.waitForTimeout(2000);

  // Answer 3 questions to build heatmap
  for (let i = 0; i < 3; i++) {
    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ timeout: 5000 });
    await btn.click();
    await page.waitForTimeout(1500);
  }

  await page.screenshot({ path: 'tests/visual/screenshots/grid-after-3-answers.png' });

  // Verify heatmap canvas has visible grid cells by sampling pixel data
  // The canvas is dynamically created inside #map-container
  const gridInfo = await page.evaluate(() => {
    const canvas = document.querySelector('#map-container canvas');
    if (!canvas) return { error: 'no canvas' };
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    // Sample a horizontal line across the middle
    const y = Math.floor(h / 2);
    const samples = [];
    for (let x = 0; x < w; x += 2) {
      const pixel = ctx.getImageData(x, y, 1, 1).data;
      samples.push({ r: pixel[0], g: pixel[1], b: pixel[2] });
    }

    // Count color transitions
    let transitions = 0;
    for (let i = 1; i < samples.length; i++) {
      const dr = Math.abs(samples[i].r - samples[i - 1].r);
      const dg = Math.abs(samples[i].g - samples[i - 1].g);
      const db = Math.abs(samples[i].b - samples[i - 1].b);
      if (dr + dg + db > 5) transitions++;
    }

    const nonWhite = samples.filter(s => s.r < 250 || s.g < 250 || s.b < 250).length;

    return { totalSamples: samples.length, transitions, nonWhitePixels: nonWhite, canvasSize: { w, h } };
  });

  console.log('Grid analysis:', JSON.stringify(gridInfo, null, 2));
  expect(gridInfo.nonWhitePixels).toBeGreaterThan(10);
  expect(gridInfo.transitions).toBeGreaterThan(5);
});
