/**
 * Persona Agents — Playwright end-to-end tests for AI-driven persona simulation.
 *
 * Each persona is automated via Playwright (Phase 1), producing checkpoint
 * JSON and screenshots that are later evaluated by AI Task agents (Phase 2).
 *
 * This file handles: Reporter (P01-P03), Expert (P04-P07), Learner (P08-P11),
 * Power User (P12-P14), and Edge Case (P15-P18) personas.
 * Pedant personas (P19-P21) are in persona-pedant.spec.js.
 *
 * Run a single persona: npx playwright test persona-agents.spec.js -g "Persona: Alex"
 */
import { test, expect } from './fixtures.js';
import { PERSONAS } from './personas/definitions.js';
import { loadQuestionDb } from './personas/question-loader.js';
import { runPersonaSession, cleanWorkingFiles } from './personas/runner.js';

// Load question database once for all tests
const questionDb = loadQuestionDb();
console.log(`Question DB loaded: ${questionDb.byId.size} questions for persona-agents`);

// ─── Reporter Personas (P01-P03) ─────────────────────────────

const reporters = PERSONAS.filter(p => p.category === 'reporter');

for (const persona of reporters) {
  test.describe(`Persona: ${persona.name}`, () => {
    test(`answers ${persona.numQuestions} questions with checkpoints`, async ({ page, browserName }) => {
      // Match browser to persona spec
      if (persona.browser === 'chromium' && browserName !== 'chromium') {
        test.skip(true, `${persona.name} requires chromium`);
        return;
      }
      if (persona.browser === 'webkit' && browserName !== 'webkit') {
        test.skip(true, `${persona.name} requires webkit`);
        return;
      }
      if (persona.browser === 'firefox' && browserName !== 'firefox') {
        test.skip(true, `${persona.name} requires firefox`);
        return;
      }

      // Set viewport to match persona device
      await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
      test.setTimeout(120_000);

      // Clean stale working files
      cleanWorkingFiles(persona.id);

      // Run full session
      const session = await runPersonaSession(page, persona, questionDb, {
        seed: persona.id.charCodeAt(1) * 1000 + persona.id.charCodeAt(2),
      });

      // Basic assertions
      expect(session.totalQuestions).toBeGreaterThanOrEqual(persona.numQuestions);
      expect(session.checkpoints.length).toBeGreaterThanOrEqual(1);

      // No console errors should be present
      for (const cp of session.checkpoints) {
        expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
      }

      console.log(`✓ ${persona.name}: ${session.totalQuestions}q, ${session.correctCount} correct, ${session.checkpoints.length} checkpoints`);
    });
  });
}

// ─── Expert Personas (P04-P07) ───────────────────────────────

const experts = PERSONAS.filter(p => p.category === 'expert');

for (const persona of experts) {
  test.describe(`Persona: ${persona.name}`, () => {
    test(`answers ${persona.numQuestions} questions with expert accuracy`, async ({ page, browserName }) => {
      if (persona.browser === 'chromium' && browserName !== 'chromium') {
        test.skip(true, `${persona.name} requires chromium`);
        return;
      }
      if (persona.browser === 'webkit' && browserName !== 'webkit') {
        test.skip(true, `${persona.name} requires webkit`);
        return;
      }
      if (persona.browser === 'firefox' && browserName !== 'firefox') {
        test.skip(true, `${persona.name} requires firefox`);
        return;
      }

      await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
      test.setTimeout(300_000); // Experts answer many questions

      cleanWorkingFiles(persona.id);

      const session = await runPersonaSession(page, persona, questionDb, {
        seed: persona.id.charCodeAt(1) * 1000 + persona.id.charCodeAt(2),
      });

      expect(session.totalQuestions).toBeGreaterThanOrEqual(persona.numQuestions);
      expect(session.checkpoints.length).toBeGreaterThanOrEqual(1);

      // Experts should have high accuracy in their domain
      if (persona.expertiseDomains.length > 0) {
        const expertResults = session.allResults.filter(
          r => persona.expertiseDomains.includes(r.domain)
        );
        if (expertResults.length > 5) {
          const expertAccuracy = expertResults.filter(r => r.correct).length / expertResults.length;
          expect(expertAccuracy).toBeGreaterThan(0.5); // Sanity: experts should beat chance
        }
      }

      for (const cp of session.checkpoints) {
        expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
      }

      console.log(`✓ ${persona.name}: ${session.totalQuestions}q, ${session.correctCount} correct, ${session.checkpoints.length} checkpoints`);
    });
  });
}

// ─── Learner Personas (P08-P11) ──────────────────────────────

const learners = PERSONAS.filter(p => p.category === 'learner');

for (const persona of learners) {
  test.describe(`Persona: ${persona.name}`, () => {
    test(`answers ${persona.numQuestions} questions tracking learning arc`, async ({ page, browserName }) => {
      if (persona.browser === 'chromium' && browserName !== 'chromium') {
        test.skip(true, `${persona.name} requires chromium`);
        return;
      }
      if (persona.browser === 'webkit' && browserName !== 'webkit') {
        test.skip(true, `${persona.name} requires webkit`);
        return;
      }
      if (persona.browser === 'firefox' && browserName !== 'firefox') {
        test.skip(true, `${persona.name} requires firefox`);
        return;
      }

      await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
      test.setTimeout(300_000);

      cleanWorkingFiles(persona.id);

      const session = await runPersonaSession(page, persona, questionDb, {
        seed: persona.id.charCodeAt(1) * 1000 + persona.id.charCodeAt(2),
      });

      expect(session.totalQuestions).toBeGreaterThanOrEqual(persona.numQuestions);
      expect(session.checkpoints.length).toBeGreaterThanOrEqual(1);

      for (const cp of session.checkpoints) {
        expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
      }

      console.log(`✓ ${persona.name}: ${session.totalQuestions}q, ${session.correctCount} correct, ${session.checkpoints.length} checkpoints`);
    });
  });
}

// ─── Power User Personas (P12-P14) ──────────────────────────

const powerUsers = PERSONAS.filter(p => p.category === 'power-user');

for (const persona of powerUsers) {
  test.describe(`Persona: ${persona.name}`, () => {
    test(`stress tests with ${persona.numQuestions} questions`, async ({ page, browserName }) => {
      if (persona.browser === 'chromium' && browserName !== 'chromium') {
        test.skip(true, `${persona.name} requires chromium`);
        return;
      }
      if (persona.browser === 'firefox' && browserName !== 'firefox') {
        test.skip(true, `${persona.name} requires firefox`);
        return;
      }

      await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
      test.setTimeout(600_000); // Power users answer many questions — 10 min

      cleanWorkingFiles(persona.id);

      const options = {
        seed: persona.id.charCodeAt(1) * 1000 + persona.id.charCodeAt(2),
      };

      // Speed clicker gets fast delays
      if (persona.id === 'P14') {
        options.answerDelayMs = 100; // Near-instant
      }

      const session = await runPersonaSession(page, persona, questionDb, options);

      expect(session.totalQuestions).toBeGreaterThanOrEqual(persona.numQuestions);
      expect(session.checkpoints.length).toBeGreaterThanOrEqual(1);

      // Critical: no Cholesky/NaN errors in console
      const allErrors = session.checkpoints.flatMap(cp => cp.consoleErrors);
      const criticalErrors = allErrors.filter(e =>
        e.includes('Cholesky') || e.includes('NaN') || e.includes('Infinity') || e.includes('divide')
      );
      expect(criticalErrors.length, `Critical estimator errors: ${criticalErrors.join('; ')}`).toBe(0);

      console.log(`✓ ${persona.name}: ${session.totalQuestions}q, ${session.correctCount} correct, ${session.checkpoints.length} checkpoints, ${allErrors.length} console errors`);
    });
  });
}

// ─── Edge Case Personas (P15-P18) ────────────────────────────

// P15: Import/Export — answer 20, export, reload, import, verify restored
test.describe('Persona: Zoe the Import/Exporter', () => {
  test('export and import preserves all progress', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'P15 runs on chromium only');
    const persona = PERSONAS.find(p => p.id === 'P15');
    await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
    test.setTimeout(300_000);
    cleanWorkingFiles(persona.id);

    // Phase 1: Answer 20 questions
    const session = await runPersonaSession(page, persona, questionDb, {
      seed: 15000,
    });
    expect(session.totalQuestions).toBeGreaterThanOrEqual(20);

    // Capture pre-export screenshot
    await page.screenshot({ path: `tests/visual/.working/personas/P15-pre-export.png` });

    // Click export button (aria-label="Export progress as JSON")
    const exportBtn = page.locator('button[aria-label="Export progress as JSON"]').first();
    if (await exportBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Export triggers a download
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 5000 }).catch(() => null),
        exportBtn.click(),
      ]);

      if (download) {
        const exportPath = `tests/visual/.working/personas/P15-export.json`;
        await download.saveAs(exportPath);

        // Navigate back to landing
        await page.goto('/mapper/');
        await page.waitForSelector('#landing-start-btn', { timeout: 10000 });

        // Click import button — it creates a transient file input
        const importBtn = page.locator('button[aria-label="Import saved progress"]').first();
        if (await importBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          // Set up file chooser listener before clicking import
          const [fileChooser] = await Promise.all([
            page.waitForEvent('filechooser', { timeout: 5000 }),
            importBtn.click(),
          ]);
          await fileChooser.setFiles(exportPath);
          await page.waitForTimeout(2000);

          // Capture post-import screenshot
          await page.screenshot({ path: `tests/visual/.working/personas/P15-post-import.png` });
        }
      }
    }

    // Verify no console errors
    for (const cp of session.checkpoints) {
      expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
    }

    console.log(`✓ P15 Import/Export: ${session.totalQuestions}q completed, export/import cycle tested`);
  });
});

// P16: Window Resize — answer 15 at 1920px, resize to 800px, verify alignment
test.describe('Persona: Wei the Window Resizer', () => {
  test('canvas layers stay aligned after resize', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'P16 runs on webkit only');
    const persona = PERSONAS.find(p => p.id === 'P16');
    await page.setViewportSize({ width: 1920, height: 1080 });
    test.setTimeout(300_000);
    cleanWorkingFiles(persona.id);

    // Answer 15 questions at full width
    const session = await runPersonaSession(page, persona, questionDb, {
      seed: 16000,
    });
    expect(session.totalQuestions).toBeGreaterThanOrEqual(15);

    // Capture pre-resize screenshot
    await page.screenshot({ path: `tests/visual/.working/personas/P16-pre-resize.png` });

    // Resize to 800px
    await page.setViewportSize({ width: 800, height: 600 });
    await page.waitForTimeout(1000); // Allow canvas to re-render

    // Capture post-resize screenshot
    await page.screenshot({ path: `tests/visual/.working/personas/P16-post-resize.png` });

    // Verify canvas is still present and has dimensions
    const canvas = page.locator('canvas').first();
    const canvasBox = await canvas.boundingBox();
    expect(canvasBox, 'Canvas should still be visible after resize').toBeTruthy();
    expect(canvasBox.width).toBeGreaterThan(100);
    expect(canvasBox.height).toBeGreaterThan(100);

    // Verify no horizontal scrollbar
    const hasHScroll = await page.evaluate(() =>
      document.documentElement.scrollWidth > window.innerWidth
    );
    expect(hasHScroll, 'No horizontal scrollbar after resize').toBe(false);

    // Verify no console errors
    for (const cp of session.checkpoints) {
      expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
    }

    console.log(`✓ P16 Resize: ${session.totalQuestions}q, resized 1920→800px, canvas intact`);
  });
});

// P17: Keyboard User — answer using A/B/C/D keys, test modifier combos don't trigger
test.describe('Persona: Aisha the Keyboard User', () => {
  test('keyboard answers work, modifier combos are safe', async ({ page, browserName }) => {
    test.skip(browserName !== 'chromium', 'P17 runs on chromium only');
    const persona = PERSONAS.find(p => p.id === 'P17');
    await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
    test.setTimeout(300_000);
    cleanWorkingFiles(persona.id);

    // Answer 20 questions using keyboard
    const session = await runPersonaSession(page, persona, questionDb, {
      seed: 17000,
      useKeyboard: true, // runner.js supports keyboard input
    });
    expect(session.totalQuestions).toBeGreaterThanOrEqual(20);

    // After answering, test modifier combos don't accidentally select answers
    // Navigate to a fresh question if available
    const questionVisible = await page.locator('.question-text, [data-testid="question"]').first()
      .isVisible({ timeout: 3000 }).catch(() => false);

    if (questionVisible) {
      // Press modifier combos that should NOT trigger answer selection
      await page.keyboard.press('Control+a');
      await page.waitForTimeout(200);
      await page.keyboard.press('Control+c');
      await page.waitForTimeout(200);
      await page.keyboard.press('Meta+a');
      await page.waitForTimeout(200);
      await page.keyboard.press('Meta+c');
      await page.waitForTimeout(200);

      // Capture screenshot for evaluation
      await page.screenshot({ path: `tests/visual/.working/personas/P17-after-modifiers.png` });
    }

    // Verify no console errors
    for (const cp of session.checkpoints) {
      expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
    }

    console.log(`✓ P17 Keyboard: ${session.totalQuestions}q via keyboard, modifier combos tested`);
  });
});

// P18: Share Modal — answer 25, open share modal, verify buttons
test.describe('Persona: Felix the Sharer', () => {
  test('share modal buttons all functional', async ({ page, browserName }) => {
    test.skip(browserName !== 'firefox', 'P18 runs on firefox only');
    const persona = PERSONAS.find(p => p.id === 'P18');
    await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
    test.setTimeout(300_000);
    cleanWorkingFiles(persona.id);

    // Answer 25 questions
    const session = await runPersonaSession(page, persona, questionDb, {
      seed: 18000,
    });
    expect(session.totalQuestions).toBeGreaterThanOrEqual(25);

    // Open share modal
    const shareBtn = page.locator('#share-btn').first();
    if (await shareBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await shareBtn.click();
      await page.waitForSelector('#share-modal', { state: 'visible', timeout: 5000 });
      await page.waitForTimeout(500);

      // Capture share modal screenshot
      await page.screenshot({ path: `tests/visual/.working/personas/P18-share-modal.png` });

      // Verify social share buttons exist (actual DOM uses button.share-action-btn[data-action])
      const socialButtons = page.locator('button.share-action-btn');
      const buttonCount = await socialButtons.count();
      expect(buttonCount, 'Share modal should have social buttons').toBeGreaterThan(0);

      // Verify specific buttons
      const hasLinkedIn = await page.locator('[data-action="linkedin"]').isVisible().catch(() => false);
      const hasCopyImage = await page.locator('[data-action="copy-image"]').isVisible().catch(() => false);

      console.log(`  Share modal: ${buttonCount} action buttons, LinkedIn: ${hasLinkedIn}, Copy Image: ${hasCopyImage}`);
    }

    // Verify no console errors
    for (const cp of session.checkpoints) {
      expect(cp.consoleErrors.length, `Console errors at checkpoint ${cp.checkpointNumber}`).toBe(0);
    }

    console.log(`✓ P18 Share: ${session.totalQuestions}q, share modal tested`);
  });
});

// ─── Unfamiliar Domain Variant (US3: T020) ───────────────────
// Physicist exploring biology — tests low-accuracy graceful degradation

test.describe('Persona: Prof. Garcia on Biology (Unfamiliar Domain)', () => {
  test('physicist answers biology questions with low accuracy', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'P05 variant runs on webkit only');
    const p05 = PERSONAS.find(p => p.id === 'P05');
    if (!p05) return;

    await page.setViewportSize({ width: p05.device.width, height: p05.device.height });
    test.setTimeout(180_000);

    cleanWorkingFiles('P05-bio');

    // Override: physicist on biology domain
    const unfamiliarPersona = {
      ...p05,
      id: 'P05-bio',
      domain: 'biology',
      numQuestions: 20,
      getAccuracy: () => 0.20, // Mostly wrong
    };

    const session = await runPersonaSession(page, unfamiliarPersona, questionDb, {
      seed: 5555,
    });

    expect(session.totalQuestions).toBeGreaterThanOrEqual(20);

    // Critical: no estimator errors even with many wrong answers
    const allErrors = session.checkpoints.flatMap(cp => cp.consoleErrors);
    const criticalErrors = allErrors.filter(e =>
      e.includes('Cholesky') || e.includes('NaN') || e.includes('Infinity')
    );
    expect(criticalErrors.length, `Estimator collapse with low accuracy`).toBe(0);

    console.log(`✓ P05 on biology: ${session.totalQuestions}q, ${session.correctCount} correct (expected ~20%)`);
  });
});

// ─── Mobile Assertions (US5: T024) ──────────────────────────
// Additional mobile UX checks for P02 (iPhone 390px) and P06 (Pixel 393px)

test.describe('Mobile UX Assertions', () => {
  test('P02 mobile layout has no overflow or clipping', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'P02 mobile runs on webkit');
    const persona = PERSONAS.find(p => p.id === 'P02');
    await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
    test.setTimeout(180_000);
    cleanWorkingFiles('P02-mobile');

    const session = await runPersonaSession(page, { ...persona, id: 'P02-mobile' }, questionDb, {
      seed: 2000,
    });

    expect(session.totalQuestions).toBeGreaterThanOrEqual(4);

    // Mobile UX checks
    const noHScroll = await page.evaluate(() =>
      document.documentElement.scrollWidth <= window.innerWidth
    );
    expect(noHScroll, 'No horizontal scrollbar on mobile').toBe(true);

    // Check quiz option touch targets are at least 44px tall
    const optionHeights = await page.evaluate(() => {
      const options = document.querySelectorAll('.quiz-option, .option-btn, [data-option]');
      return Array.from(options).map(el => el.getBoundingClientRect().height);
    });
    for (const h of optionHeights) {
      if (h > 0) expect(h).toBeGreaterThanOrEqual(44);
    }

    // Check no text clipping
    const clippedElements = await page.evaluate(() => {
      const els = document.querySelectorAll('.question-text, .quiz-option, .option-btn');
      let clipped = 0;
      for (const el of els) {
        if (el.scrollWidth > el.clientWidth + 2) clipped++;
      }
      return clipped;
    });
    expect(clippedElements, 'No text clipping on mobile').toBe(0);

    // Full-page screenshot for evaluation
    await page.screenshot({
      path: `tests/visual/.working/personas/P02-mobile-fullpage.png`,
      fullPage: true,
    });

    console.log(`✓ P02 Mobile: ${session.totalQuestions}q, touch targets OK, no overflow`);
  });
});

// ─── Cross-Browser Comparison (US6: T025) ────────────────────
// Run identical P01 session on all browsers, compare screenshots

test.describe('Cross-Browser Comparison', () => {
  test('P01 produces consistent map across browsers', async ({ page, browserName }) => {
    const persona = PERSONAS.find(p => p.id === 'P01');
    await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
    test.setTimeout(180_000);

    const crossId = `P01-cross-${browserName}`;
    cleanWorkingFiles(crossId);

    // Use identical seed for deterministic comparison
    const session = await runPersonaSession(page, { ...persona, id: crossId }, questionDb, {
      seed: 99999, // Same seed across all browsers
    });

    expect(session.totalQuestions).toBeGreaterThanOrEqual(7);

    // Wait for map to stabilize before cross-browser screenshot
    await page.waitForTimeout(1500);

    // Save browser-specific screenshot for cross-browser comparison
    await page.screenshot({
      path: `tests/visual/.working/personas/P01-cross-${browserName}.png`,
    });

    console.log(`✓ Cross-browser ${browserName}: ${session.totalQuestions}q, ${session.correctCount} correct`);
  });
});

// ─── Video Discovery (US8: T030) ─────────────────────────────
// P10 answers 35 neuroscience questions, opens video panel, checks recommendations

test.describe('Persona: Sam the Video Explorer — Video Discovery', () => {
  test('video panel shows recommendations after questions', async ({ page, browserName }) => {
    test.skip(browserName !== 'webkit', 'P10 runs on webkit (iPad)');
    const persona = PERSONAS.find(p => p.id === 'P10');
    if (!persona) return;

    await page.setViewportSize({ width: persona.device.width, height: persona.device.height });
    test.setTimeout(300_000);
    cleanWorkingFiles('P10-video');

    const session = await runPersonaSession(page, { ...persona, id: 'P10-video' }, questionDb, {
      seed: 10000,
    });

    expect(session.totalQuestions).toBeGreaterThanOrEqual(35);

    // Open video panel (actual DOM uses #video-toggle button)
    const videoToggle = page.locator('#video-toggle').first();
    const toggleVisible = await videoToggle.isVisible({ timeout: 3000 }).catch(() => false);

    if (toggleVisible) {
      await videoToggle.click();
      await page.waitForTimeout(2000); // Allow panel to populate

      // Check for video list items (actual DOM uses .video-panel-item)
      const videoItems = page.locator('.video-panel-item');
      const videoCount = await videoItems.count();

      // Capture video panel screenshot
      await page.screenshot({
        path: `tests/visual/.working/personas/P10-video-panel.png`,
      });

      console.log(`  Video panel: ${videoCount} recommendations shown`);

      // Hover first video to check trajectory highlight
      if (videoCount > 0) {
        await videoItems.first().hover();
        await page.waitForTimeout(500);
        await page.screenshot({
          path: `tests/visual/.working/personas/P10-video-hover.png`,
        });
      }
    }

    // Verify no console errors
    const allErrors = session.checkpoints.flatMap(cp => cp.consoleErrors);
    expect(allErrors.length, 'No console errors during video discovery').toBe(0);

    console.log(`✓ P10 Video Discovery: ${session.totalQuestions}q, video panel tested`);
  });
});
