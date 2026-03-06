import { test, expect } from './fixtures.js';

const TUTORIAL_DISMISSED = JSON.stringify({
  completed: false, dismissed: true, step: 1, subStep: 1,
  hasSkippedQuestion: false, skipToastShown: false, returningUser: false,
});

test.describe('Responsive Layout (SC-008)', () => {
  test('mobile viewport 375x667 is usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 375, height: 667 } });
    const page = await context.newPage();
    await page.addInitScript((state) => { localStorage.setItem('mapper-tutorial', state); }, TUTORIAL_DISMISSED);
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });

    const minimap = page.locator('#minimap-container');
    await expect(minimap).toBeHidden();

    await page.screenshot({ path: 'tests/visual/screenshots/mobile-375x667.png', fullPage: true });
    await context.close();
  });

  test('tablet viewport 768x1024 is usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 768, height: 1024 } });
    const page = await context.newPage();
    await page.addInitScript((state) => { localStorage.setItem('mapper-tutorial', state); }, TUTORIAL_DISMISSED);
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });
    await page.screenshot({ path: 'tests/visual/screenshots/tablet-768x1024.png', fullPage: true });
    await context.close();
  });

  test('desktop viewport 1280x800 is usable', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await page.addInitScript((state) => { localStorage.setItem('mapper-tutorial', state); }, TUTORIAL_DISMISSED);
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: 10000 });
    await page.screenshot({ path: 'tests/visual/screenshots/desktop-1280x800.png', fullPage: true });
    await context.close();
  });

  test('touch tap on answer button works on mobile (T062)', async ({ browser }) => {
    test.setTimeout(60000);
    const context = await browser.newContext({
      viewport: { width: 375, height: 667 },
      hasTouch: true,
    });
    const page = await context.newPage();
    await page.addInitScript((state) => { localStorage.setItem('mapper-tutorial', state); }, TUTORIAL_DISMISSED);
    await page.goto('/');

    // Click start to enter map (triggers switchDomain('all'))
    await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: 15000 });
    await page.locator('#landing-start-btn').click();

    // Wait for question to load (switchDomain loads all bundles via deduped fetches)
    const questionEl = page.locator('.quiz-question');
    await expect(questionEl).not.toBeEmpty({ timeout: 40000 });

    // Ensure quiz panel bottom sheet is open on mobile
    const quizPanel = page.locator('#quiz-panel');
    const isOpen = await quizPanel.evaluate(el => el.classList.contains('open'));
    if (!isOpen) {
      await page.locator('#quiz-toggle').click();
      await expect(quizPanel).toHaveClass(/open/, { timeout: 3000 });
    }

    const btn = page.locator('.quiz-option').first();
    await btn.waitFor({ state: 'visible' });
    await btn.click();

    const feedback = page.locator('.quiz-feedback');
    await expect(feedback).not.toBeEmpty({ timeout: 5000 });
    await context.close();
  });
});
