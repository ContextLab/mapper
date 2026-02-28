// @ts-check
import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

async function selectDomain(page) {
  // Wait for app JS to initialize, then click start button to enter the map
  const startBtn = page.locator('#landing-start-btn');
  await page.waitForSelector('#landing-start-btn[data-ready]', { timeout: 15000 });
  await startBtn.click();

  // Wait for the map/quiz to load
  await page.waitForSelector('.quiz-question', { timeout: 15000 });
  await page.waitForTimeout(1000);
}

test.describe('Skip button and share image', () => {
  test('Skip button appears and works', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('#landing', { state: 'visible', timeout: 10000 });

    await selectDomain(page);

    // Verify the Skip button exists in the modes wrapper
    const skipBtn = page.locator('.skip-btn');
    await expect(skipBtn).toBeVisible({ timeout: 5000 });
    await expect(skipBtn).toContainText('skip');

    // Verify the tooltip
    const tooltip = await skipBtn.getAttribute('data-tooltip');
    expect(tooltip).toContain("Don't guess");

    // Get the question text before skipping
    const questionBefore = await page.locator('.quiz-question').textContent();
    expect(questionBefore.length).toBeGreaterThan(0);

    // Click skip
    await skipBtn.click();

    // Should advance to next question
    await page.waitForTimeout(500);
    const questionAfter = await page.locator('.quiz-question').textContent();
    expect(questionAfter.length).toBeGreaterThan(0);

    console.log('Skip button test passed');
    console.log('Question before skip:', questionBefore.slice(0, 60));
    console.log('Question after skip:', questionAfter.slice(0, 60));
  });

  test('Skip records response with is_skipped and yellow dot', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('#landing', { state: 'visible', timeout: 10000 });

    await selectDomain(page);

    // Skip a question
    const skipBtn = page.locator('.skip-btn');
    await skipBtn.click();
    await page.waitForTimeout(500);

    // Verify the skipped response is stored with is_skipped flag
    const responses = await page.evaluate(() => {
      const store = window.__mapper;
      if (store && store.$responses) {
        return store.$responses.get();
      }
      return [];
    });

    const skipped = responses.find(r => r.is_skipped === true);
    expect(skipped).toBeTruthy();
    expect(skipped.selected).toBeNull();
    console.log('Skipped response found:', JSON.stringify(skipped));

    // Check the answered dots include the skipped question with yellow color
    const answeredDots = await page.evaluate(() => {
      const store = window.__mapper;
      if (store && store.renderer && store.renderer._answeredData) {
        return store.renderer._answeredData;
      }
      return [];
    });

    const skippedDot = answeredDots.find(d => d.isSkipped === true);
    expect(skippedDot).toBeTruthy();
    // Verify yellow color [212, 160, 23, 200]
    expect(skippedDot.color[0]).toBe(212);
    expect(skippedDot.color[1]).toBe(160);
    expect(skippedDot.color[2]).toBe(23);

    console.log('Skipped dot color verified:', skippedDot.color);
  });

  test('Answer options are randomized across reloads', async ({ page }) => {
    // Load the app and get the first question's option texts in display order
    await page.goto(BASE);
    await page.waitForSelector('#landing', { state: 'visible', timeout: 10000 });
    await selectDomain(page);

    const getOptionTexts = async () => {
      return page.evaluate(() => {
        const buttons = document.querySelectorAll('.quiz-option');
        return Array.from(buttons).map(b => b.textContent.trim());
      });
    };

    const firstLoad = await getOptionTexts();
    expect(firstLoad).toHaveLength(4);
    expect(firstLoad.every(t => t.length > 0)).toBe(true);

    // Reload multiple times and collect option orderings
    // With 4! = 24 permutations, getting the same order 5 times in a row
    // has probability (1/24)^4 ≈ 0.0003% — essentially impossible if randomized
    const orderings = [firstLoad.join('|||')];
    for (let i = 0; i < 4; i++) {
      await page.goto(BASE);
      await page.waitForSelector('#landing', { state: 'visible', timeout: 10000 });
      await selectDomain(page);
      const texts = await getOptionTexts();
      orderings.push(texts.join('|||'));
    }

    // At least 2 different orderings should appear across 5 loads
    const unique = new Set(orderings);
    console.log(`Randomization: ${unique.size} unique orderings out of ${orderings.length} loads`);
    expect(unique.size).toBeGreaterThan(1);
  });
});
