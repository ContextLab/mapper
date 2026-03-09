/**
 * Tutorial verification — takes screenshots at key steps to verify
 * visual fixes for issues #38-#45.
 */
import { test } from '@playwright/test';

const BASE = 'http://localhost:5173/mapper/';
const SHOTS = 'tests/visual/screenshots/tutorial-verify';

async function resetAndLoad(page) {
  await page.goto(BASE);
  await page.evaluate(() => {
    localStorage.removeItem('mapper-tutorial');
    localStorage.removeItem('mapper-responses');
  });
  await page.goto(BASE);
  await page.waitForSelector('#landing-start-btn[data-ready="true"]', { timeout: 30000 });
}

async function clickStartAndWaitForMap(page) {
  await page.click('#landing-start-btn');
  await page.waitForSelector('#app[data-screen="map"]', { timeout: 30000 });
  await page.waitForTimeout(2000);
}

async function goToTutorialStep(page, step, subStep = 1) {
  await page.evaluate(({ step, subStep }) => {
    if (window.__mapper && window.__mapper.tutorialGoToStep) {
      window.__mapper.tutorialGoToStep(step, subStep);
    }
  }, { step, subStep });
  await page.waitForTimeout(500);
}

async function answerQuestion(page) {
  try {
    await page.waitForSelector('.quiz-question', { timeout: 5000 });
    const prevText = await page.textContent('.quiz-question');
    const opt = page.locator('.quiz-option:not([disabled])').first();
    await opt.waitFor({ state: 'visible', timeout: 5000 });
    await opt.click({ timeout: 5000 });
    // Wait for question to change (auto-advance) or timeout
    try {
      await page.waitForFunction(
        (prev) => {
          const q = document.querySelector('.quiz-question');
          return q && q.textContent !== prev;
        },
        prevText,
        { timeout: 5000 }
      );
    } catch {
      await page.waitForTimeout(1500);
    }
    return true;
  } catch { return false; }
}

test.describe('Tutorial visual verification', () => {
  test.setTimeout(120_000);

  test('Issue #39: Welcome prompt appears', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    await clickStartAndWaitForMap(page);

    // Welcome prompt should appear
    await page.waitForSelector('#tutorial-welcome', { timeout: 10000 });
    await page.screenshot({ path: `${SHOTS}/issue39-welcome-prompt.png` });
    console.log('Issue #39: Welcome prompt verified');

    // Click "Yes"
    await page.click('#tutorial-welcome button:first-of-type');
    await page.waitForSelector('#tutorial-modal', { timeout: 5000 });
    await page.screenshot({ path: `${SHOTS}/issue39-tutorial-started.png` });
  });

  test('Issue #38/#42: Overlay uses box-shadow, highlight visible', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    // Set tutorial to step 6 (Switch Domains) to test highlight on dropdown
    await clickStartAndWaitForMap(page);
    await goToTutorialStep(page, 6);
    await page.waitForTimeout(2000);

    // Take screenshot showing the domain selector highlighted (#42)
    await page.screenshot({ path: `${SHOTS}/issue42-domain-selector.png` });

    // Check overlay is transparent (box-shadow on highlight, not clip-path)
    const overlayBg = await page.evaluate(() => {
      const o = document.getElementById('tutorial-overlay');
      return o ? getComputedStyle(o).background : 'no-overlay';
    });
    console.log('Issue #38: Overlay background:', overlayBg);

    // Check highlight has box-shadow
    const highlightShadow = await page.evaluate(() => {
      const h = document.querySelector('.tutorial-highlight');
      return h ? getComputedStyle(h).boxShadow : 'no-highlight';
    });
    console.log('Issue #38: Highlight box-shadow:', highlightShadow.substring(0, 80));

    // Check highlight z-index
    const highlightZ = await page.evaluate(() => {
      const h = document.querySelector('.tutorial-highlight');
      return h ? getComputedStyle(h).zIndex : 'none';
    });
    console.log('Issue #42: Highlight z-index:', highlightZ);
  });

  test('Issue #40: Modal position consistent step 1→2', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    await clickStartAndWaitForMap(page);
    // Click through welcome prompt
    await page.waitForSelector('#tutorial-welcome', { timeout: 10000 });
    await page.click('#tutorial-welcome button:first-of-type');
    await page.waitForSelector('#tutorial-modal', { timeout: 10000 });
    await page.waitForTimeout(500);

    // Capture step 1 modal position
    const pos1 = await page.evaluate(() => {
      const m = document.getElementById('tutorial-modal');
      const r = m?.getBoundingClientRect();
      return r ? { left: Math.round(r.left), top: Math.round(r.top) } : null;
    });
    await page.screenshot({ path: `${SHOTS}/issue40-step1-position.png` });
    console.log('Issue #40: Step 1 modal position:', JSON.stringify(pos1));

    // Advance to step 2 (click Next twice for substeps)
    await page.click('#tutorial-modal .tutorial-next-btn');
    await page.waitForTimeout(500);
    await page.click('#tutorial-modal .tutorial-next-btn');
    await page.waitForTimeout(1000);

    const pos2 = await page.evaluate(() => {
      const m = document.getElementById('tutorial-modal');
      const r = m?.getBoundingClientRect();
      return r ? { left: Math.round(r.left), top: Math.round(r.top) } : null;
    });
    await page.screenshot({ path: `${SHOTS}/issue40-step2-position.png` });
    console.log('Issue #40: Step 2 modal position:', JSON.stringify(pos2));
  });

  test('Issue #41: Title says "Videos in View"', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    await clickStartAndWaitForMap(page);
    await goToTutorialStep(page, 3, 1);
    await page.waitForSelector('#tutorial-modal', { timeout: 10000 });
    await page.waitForTimeout(800);

    const title = await page.textContent('[data-tutorial-title]');
    console.log('Issue #41: Step 3 title:', title);
    await page.screenshot({ path: `${SHOTS}/issue41-videos-in-view.png` });
  });

  test('Issue #44: Expertise text softened', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    await clickStartAndWaitForMap(page);
    await goToTutorialStep(page, 8);
    await page.waitForSelector('#tutorial-modal', { timeout: 10000 });
    await page.waitForTimeout(500);

    const msg = await page.textContent('[data-tutorial-message]');
    console.log('Issue #44: Step 8 message:', msg?.substring(0, 100));
    await page.screenshot({ path: `${SHOTS}/issue44-expertise-text.png` });
  });

  test('Issue #45: New tutorial steps exist (modes, save/load, about)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    await clickStartAndWaitForMap(page);

    // Step 11: Question Modes
    await goToTutorialStep(page, 11);
    await page.waitForSelector('#tutorial-modal', { timeout: 10000 });
    await page.waitForTimeout(500);
    const title11 = await page.textContent('[data-tutorial-title]');
    console.log('Issue #45: Step 11 title:', title11);
    await page.screenshot({ path: `${SHOTS}/issue45-step11-modes.png` });

    // Step 12: Save & Load
    await goToTutorialStep(page, 12);
    await page.waitForSelector('#tutorial-modal', { timeout: 10000 });
    await page.waitForTimeout(500);
    const title12 = await page.textContent('[data-tutorial-title]');
    console.log('Issue #45: Step 12 title:', title12);
    await page.screenshot({ path: `${SHOTS}/issue45-step12-save-load.png` });

    // Step 13: Learn More
    await goToTutorialStep(page, 13);
    await page.waitForSelector('#tutorial-modal', { timeout: 10000 });
    await page.waitForTimeout(500);
    const title13 = await page.textContent('[data-tutorial-title]');
    console.log('Issue #45: Step 13 title:', title13);
    await page.screenshot({ path: `${SHOTS}/issue45-step13-about.png` });
  });

  test('Issue #43: Panels use transform animation', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    // Dismiss tutorial to test panel independently
    await page.evaluate(() => {
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: true, dismissed: true, step: 14, subStep: 1,
      }));
    });
    await clickStartAndWaitForMap(page);
    await page.waitForTimeout(1000);

    // Check quiz panel uses transform
    const quizTransition = await page.evaluate(() => {
      const p = document.getElementById('quiz-panel');
      return p ? getComputedStyle(p).transition : 'not-found';
    });
    console.log('Issue #43: Quiz panel transition:', quizTransition);

    // Open quiz panel and screenshot
    const toggle = page.locator('#quiz-toggle');
    await toggle.click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SHOTS}/issue43-panel-open.png` });
  });

  test('Issue #46: Khan Academy button only for STEM', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    // Dismiss tutorial
    await page.evaluate(() => {
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: true, dismissed: true, step: 14, subStep: 1,
      }));
    });
    await clickStartAndWaitForMap(page);
    await page.waitForTimeout(1000);

    // Answer a question and check Khan button visibility
    const answered = await answerQuestion(page);
    if (answered) {
      const khanVisible = await page.evaluate(() => {
        const btn = document.querySelector('[data-learn="khan"]');
        return btn ? !btn.hidden : 'not-found';
      });
      const questionDomains = await page.evaluate(() => {
        return window.__mapper?.getCurrentQuestion()?.domain_ids || 'unknown';
      });
      console.log('Issue #46: Khan visible:', khanVisible, 'domains:', questionDomains);
      await page.screenshot({ path: `${SHOTS}/issue46-khan-button.png` });
    }
  });

  test('Issue #48: Suggested learning shows 50 items scrollable', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await resetAndLoad(page);
    // Dismiss tutorial and answer some questions
    await page.evaluate(() => {
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: true, dismissed: true, step: 14, subStep: 1,
      }));
    });
    await clickStartAndWaitForMap(page);
    await page.waitForTimeout(1000);

    // Answer a few questions to enable suggest button
    for (let i = 0; i < 5; i++) {
      if (!await answerQuestion(page)) break;
    }

    // Click suggest button
    const suggestEnabled = await page.evaluate(() => {
      const btn = document.getElementById('suggest-btn');
      return btn && !btn.disabled;
    });
    if (suggestEnabled) {
      await page.click('#suggest-btn');
      await page.waitForTimeout(1000);

      // Count items and check scrollability
      const info = await page.evaluate(() => {
        const items = document.querySelectorAll('#insights-modal-body .insights-modal-list li');
        const list = document.querySelector('#insights-modal-body .insights-modal-list');
        return {
          count: items.length,
          maxHeight: list ? (list.style.maxHeight || getComputedStyle(list).maxHeight) : 'not-found',
          overflowY: list ? (list.style.overflowY || getComputedStyle(list).overflowY) : 'not-found',
        };
      });
      console.log('Issue #48: Items:', info.count, 'maxHeight:', info.maxHeight, 'overflow:', info.overflowY);
      await page.screenshot({ path: `${SHOTS}/issue48-suggest-modal.png` });
    } else {
      console.log('Issue #48: Suggest button still disabled after 5 questions — need more answers');
      await page.screenshot({ path: `${SHOTS}/issue48-suggest-disabled.png` });
    }
  });
});
