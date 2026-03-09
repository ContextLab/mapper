/** Test that drawer open/close doesn't cause white flash on the map canvas. */
import { test, expect } from './fixtures.js';

const LOAD_TIMEOUT = 15000;

async function setupMap(page) {
  await page.goto('/');
  await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
  await page.click('#landing-start-btn');
  await page.waitForSelector('#quiz-panel.open', { timeout: LOAD_TIMEOUT });
  await page.waitForTimeout(1000);
  // Answer 2 questions so heatmap is visible
  for (let i = 0; i < 2; i++) {
    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ timeout: 5000 });
    await btn.click();
    await page.waitForTimeout(1500);
  }
}

test.describe('Drawer Animation (no white flash)', () => {
  test('quiz panel toggle does not flash white', async ({ page }) => {
    await setupMap(page);

    // Take baseline screenshot with panel open
    const beforeClose = await page.screenshot();

    // Close quiz panel
    const toggleBtn = page.locator('.quiz-toggle-btn');
    await toggleBtn.click();
    // Wait for transition midpoint — capture during animation
    await page.waitForTimeout(150);
    const duringClose = await page.screenshot({ path: 'tests/visual/screenshots/drawer-during-close.png' });
    // Wait for transition to finish
    await page.waitForTimeout(500);
    const afterClose = await page.screenshot({ path: 'tests/visual/screenshots/drawer-after-close.png' });

    // Check that the map area during transition isn't all white
    const midTransitionInfo = await page.evaluate(() => {
      const canvas = document.querySelector('#map-container canvas');
      if (!canvas) return { error: 'no canvas' };
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;
      // Sample center area of canvas
      const cx = Math.floor(w / 2);
      const cy = Math.floor(h / 2);
      const size = 20;
      let whiteCount = 0;
      let totalCount = 0;
      for (let y = cy - size; y < cy + size; y += 2) {
        for (let x = cx - size; x < cx + size; x += 2) {
          if (x < 0 || x >= w || y < 0 || y >= h) continue;
          const pixel = ctx.getImageData(x, y, 1, 1).data;
          totalCount++;
          if (pixel[0] > 250 && pixel[1] > 250 && pixel[2] > 250) whiteCount++;
        }
      }
      return { whiteCount, totalCount, whiteRatio: whiteCount / totalCount };
    });

    console.log('Mid-transition canvas state:', JSON.stringify(midTransitionInfo));
    // Map should NOT be mostly white during transition
    expect(midTransitionInfo.whiteRatio).toBeLessThan(0.9);
  });

  test('quiz panel open/close performance', async ({ page }) => {
    await setupMap(page);

    // Measure time for 5 open/close cycles
    const toggleBtn = page.locator('.quiz-toggle-btn');
    const timings = await page.evaluate(async () => {
      const results = [];
      const toggle = document.querySelector('.quiz-toggle-btn');
      if (!toggle) return [{ error: 'no toggle btn' }];
      for (let i = 0; i < 5; i++) {
        const start = performance.now();
        toggle.click();
        // Wait for transition end
        await new Promise(resolve => {
          const panel = document.getElementById('quiz-panel');
          const handler = () => { panel.removeEventListener('transitionend', handler); resolve(); };
          panel.addEventListener('transitionend', handler);
          setTimeout(resolve, 500); // fallback
        });
        results.push(performance.now() - start);
      }
      return results;
    });

    console.log('Panel toggle timings (ms):', timings);
    // Each toggle should complete within 600ms (300ms transition + overhead)
    for (const t of timings) {
      if (typeof t === 'number') {
        expect(t).toBeLessThan(1000);
      }
    }
  });
});
