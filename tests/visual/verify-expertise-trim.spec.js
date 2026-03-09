import { test, expect } from './fixtures.js';

test('expertise modal: names are trimmed and limited to top 10', async ({ page }) => {
  test.setTimeout(90000);

  await page.goto('/');
  await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: 30000 });

  // Click "Map my Knowledge" to enter the map
  await page.click('#landing-start-btn');
  await page.waitForSelector('#app[data-screen="map"]', { timeout: 60000 });

  // Answer 6 questions to unlock expertise areas
  for (let i = 0; i < 6; i++) {
    // Wait for a fresh quiz-question to appear
    await page.waitForSelector('.quiz-question', { timeout: 10000 });
    const questionText = await page.textContent('.quiz-question');
    // Click the first option
    await page.locator('.quiz-option').first().click();
    // Wait for either a new question or for the current question to change
    try {
      await page.waitForFunction(
        (prevText) => {
          const q = document.querySelector('.quiz-question');
          return q && q.textContent !== prevText;
        },
        questionText,
        { timeout: 5000 }
      );
    } catch {
      // If question didn't change (e.g., last question), just wait
      await page.waitForTimeout(1500);
    }
  }

  // Wait for trophy button to become enabled (updateInsightButtons)
  await page.waitForSelector('#trophy-btn:not([disabled])', { timeout: 10000 });
  await page.click('#trophy-btn');
  await page.waitForSelector('#insights-modal:not([hidden])', { timeout: 5000 });

  // Extract all domain names from the modal list
  const names = await page.locator('.insights-modal-list .insights-concept').allTextContents();

  console.log('Found ' + names.length + ' domain entries:');
  for (const name of names) {
    const trimmed = name.trim();
    if (name !== trimmed) {
      console.log('  FAIL: "' + name + '" has leading/trailing whitespace');
    } else {
      console.log('  OK: "' + trimmed + '"');
    }
    expect(name).toBe(trimmed);
  }

  // Top 10 limit
  expect(names.length).toBeLessThanOrEqual(10);
  expect(names.length).toBeGreaterThan(0);
  console.log('Entries: ' + names.length + ' (<= 10 limit)');
});
