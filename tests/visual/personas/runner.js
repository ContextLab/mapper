/**
 * Playwright runner engine for persona testing framework.
 *
 * Automates browser interactions: domain selection, question answering,
 * checkpoint capture (screenshot + DOM state + console errors).
 *
 * Reuses proven patterns from persona-simulation.spec.js but structured
 * as reusable exports for the AI evaluation pipeline.
 */
import { writeFileSync, mkdirSync, existsSync, readdirSync, unlinkSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { lookupQuestion } from './question-loader.js';

const LOAD_TIMEOUT = 15000;

// ─── Seeded PRNG ─────────────────────────────────────────────
/**
 * Linear congruential generator for deterministic answer sequences.
 * Same implementation as persona-simulation.spec.js.
 *
 * @param {number} seed - Integer seed
 * @returns {function(): number} Returns values in [0, 1)
 */
export function makePrng(seed) {
  let s = seed;
  return function () {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

// ─── Domain selection ────────────────────────────────────────

/**
 * Navigate from landing page into the app and select a domain.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} domainName - Domain display name (e.g., "physics", "All (General)")
 */
export async function selectDomain(page, domainName) {
  // If on landing page, click start button first
  const startBtn = page.locator('#landing-start-btn');
  if (await startBtn.isVisible().catch(() => false)) {
    await page.waitForSelector('#landing-start-btn[data-ready]', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }

  // Use header domain selector
  const trigger = page.locator('.domain-selector .custom-select-trigger');
  await trigger.click();

  const options = page.locator('.domain-selector .custom-select-option');
  const count = await options.count();
  for (let i = 0; i < count; i++) {
    const text = await options.nth(i).textContent();
    if (text.trim().toLowerCase().includes(domainName.toLowerCase())) {
      await options.nth(i).click();
      return;
    }
  }
  // Fallback: click first option
  await options.first().click();
}

// ─── Question interaction ────────────────────────────────────

/**
 * Read the currently displayed question text from the DOM.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<string>}
 */
export async function getDisplayedQuestion(page) {
  const el = page.locator('.quiz-question');
  await el.waitFor({ state: 'visible', timeout: 5000 });
  return (await el.textContent()).trim();
}

/**
 * Answer the currently displayed question using persona's accuracy profile.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} persona - Persona definition with getAccuracy(domainId)
 * @param {Map<string, object>} questionDb - Loaded question database
 * @param {function(): number} rand - Seeded PRNG function
 * @returns {Promise<object>} Answer result with question data
 */
export async function answerQuestion(page, persona, questionDb, rand) {
  const displayedText = await getDisplayedQuestion(page);
  const question = lookupQuestion(questionDb, displayedText);

  if (!question) {
    // Can't find in DB — answer randomly
    const firstBtn = page.locator('.quiz-option:not([disabled])').first();
    await firstBtn.click();
    return {
      questionId: 'unknown',
      questionText: displayedText.substring(0, 200),
      correct: false,
      selectedAnswer: '?',
      correctAnswer: '?',
      options: {},
      domain: 'unknown',
      difficulty: 2,
      x: 0.5,
      y: 0.5,
      matched: false,
    };
  }

  const domainId = question.domain_ids?.[0] || 'unknown';
  const pCorrect = persona.getAccuracy(domainId);
  const shouldBeCorrect = rand() < pCorrect;

  // Find correct and wrong button indices
  const optionBtns = page.locator('.quiz-option');
  const btnCount = await optionBtns.count();
  const correctAnswerText = question.options[question.correct_answer];

  let correctBtnIndex = -1;
  let wrongBtnIndex = -1;

  for (let i = 0; i < btnCount; i++) {
    const btnText = await optionBtns.nth(i).textContent();
    if (btnText.trim() === correctAnswerText.trim() ||
        btnText.includes(correctAnswerText.substring(0, 40))) {
      correctBtnIndex = i;
    } else if (wrongBtnIndex === -1) {
      wrongBtnIndex = i;
    }
  }

  if (correctBtnIndex === -1) {
    correctBtnIndex = 0;
    wrongBtnIndex = 1;
  }

  const targetIndex = shouldBeCorrect ? correctBtnIndex : (wrongBtnIndex >= 0 ? wrongBtnIndex : 0);
  await optionBtns.nth(targetIndex).click();

  // Determine which letter was selected
  const letters = ['A', 'B', 'C', 'D'];
  const selectedAnswer = letters[targetIndex] || '?';

  return {
    questionId: question.id,
    questionText: question.question_text.substring(0, 200),
    correct: shouldBeCorrect,
    selectedAnswer,
    correctAnswer: question.correct_answer,
    options: question.options,
    domain: domainId,
    difficulty: question.difficulty || 2,
    x: question.x,
    y: question.y,
    sourceArticle: question.source_article || '',
    matched: true,
  };
}

/**
 * Advance to the next question (press 'n' key).
 *
 * @param {import('@playwright/test').Page} page
 */
export async function advanceToNext(page) {
  await page.waitForTimeout(300);
  await page.keyboard.press('n');
  await page.waitForTimeout(500);
}

// ─── Checkpoint capture ──────────────────────────────────────

/**
 * Capture a checkpoint: screenshot + DOM state + console errors.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} persona - Persona definition
 * @param {number} checkpointNum - Checkpoint sequential index (1-based)
 * @param {object[]} questionBatch - Questions answered since last checkpoint
 * @param {string[]} consoleErrors - Console errors since last checkpoint
 * @param {number} totalAnswered - Total questions answered so far
 * @returns {Promise<object>} Checkpoint data object
 */
export async function captureCheckpoint(page, persona, checkpointNum, questionBatch, consoleErrors, totalAnswered) {
  const workingDir = resolve('tests/visual/.working/personas');
  const screenshotDir = resolve('tests/visual/screenshots/personas');
  mkdirSync(workingDir, { recursive: true });
  mkdirSync(screenshotDir, { recursive: true });

  const screenshotPath = join(screenshotDir, `${persona.id}-checkpoint-${checkpointNum}.png`);

  // Take screenshot
  await page.waitForTimeout(500); // Let canvas settle
  await page.screenshot({ path: screenshotPath, fullPage: true });

  // Read domain-mapped percentage from UI if available
  let domainMappedPct = 0;
  try {
    domainMappedPct = await page.evaluate(() => {
      const el = document.querySelector('.domain-mapped-pct, .progress-pct');
      if (el) {
        const match = el.textContent.match(/(\d+)/);
        return match ? parseInt(match[1], 10) : 0;
      }
      return 0;
    });
  } catch { /* ignore */ }

  const checkpoint = {
    personaId: persona.id,
    checkpointNumber: checkpointNum,
    questionsAnswered: totalAnswered,
    questionsInBatch: questionBatch.map(q => ({
      questionId: q.questionId,
      questionText: q.questionText,
      options: q.options,
      correctAnswer: q.correctAnswer,
      selectedAnswer: q.selectedAnswer,
      wasCorrect: q.correct,
      difficulty: q.difficulty,
      domainId: q.domain,
      sourceArticle: q.sourceArticle || '',
    })),
    screenshotPath,
    consoleErrors: [...consoleErrors],
    domainMappedPct,
    timestamp: Date.now(),
  };

  // Write checkpoint JSON
  const checkpointPath = join(workingDir, `${persona.id}-checkpoint-${checkpointNum}.json`);
  writeFileSync(checkpointPath, JSON.stringify(checkpoint, null, 2));

  return checkpoint;
}

// ─── Full session runner ─────────────────────────────────────

/**
 * Run a complete persona simulation session.
 *
 * Navigates to the app, selects domain, answers questions per persona
 * profile, captures checkpoints at the specified interval, and returns
 * all checkpoint data for AI evaluation.
 *
 * @param {import('@playwright/test').Page} page
 * @param {object} persona - Persona definition from definitions.js
 * @param {Map<string, object>} questionDb - Loaded question database
 * @param {object} [options] - Additional options
 * @param {number} [options.seed] - PRNG seed (defaults to persona index hash)
 * @param {string[]} [options.domainSequence] - For domain-hopper personas
 * @param {number} [options.questionsPerDomain] - Questions before switching domain
 * @param {number} [options.answerDelayMs] - Delay between answers (for speed tests)
 * @returns {Promise<object>} Session results with all checkpoints
 */
export async function runPersonaSession(page, persona, questionDb, options = {}) {
  const seed = options.seed ?? (persona.id.charCodeAt(1) * 1000 + persona.id.charCodeAt(2));
  const rand = makePrng(seed);
  const domainSequence = options.domainSequence || persona.domainSequence;
  const questionsPerDomain = options.questionsPerDomain || persona.questionsPerDomain;
  const answerDelayMs = options.answerDelayMs ?? 0;

  // Determine total questions
  const numQuestions = persona.numQuestions === 'ALL'
    ? 999 // Pedants answer until questions run out
    : persona.numQuestions;

  // Navigate to app
  await page.goto('/');
  await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });

  // Select initial domain
  const initialDomain = persona.domain === 'all' ? 'All (General)' : persona.domain;
  await selectDomain(page, initialDomain);
  await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  await page.waitForSelector('.quiz-question', { timeout: 5000 });
  await page.waitForTimeout(500);

  // Track state
  const allResults = [];
  let currentBatch = [];
  const consoleErrors = [];
  let checkpointNum = 0;
  const checkpoints = [];
  let currentDomainIndex = 0;

  // Capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  // Answer questions
  for (let i = 0; i < numQuestions; i++) {
    // Domain hopping: switch domain at specified intervals
    if (domainSequence && questionsPerDomain && i > 0 && i % questionsPerDomain === 0) {
      currentDomainIndex = (currentDomainIndex + 1) % domainSequence.length;
      const nextDomain = domainSequence[currentDomainIndex];
      const displayDomain = nextDomain === 'all' ? 'All (General)' : nextDomain;
      await selectDomain(page, displayDomain);
      await page.waitForSelector('.quiz-question', { timeout: 5000 });
      await page.waitForTimeout(500);
    }

    try {
      const result = await answerQuestion(page, persona, questionDb, rand);
      allResults.push(result);
      currentBatch.push(result);

      // Optional delay for speed-test personas
      if (answerDelayMs > 0) {
        await page.waitForTimeout(answerDelayMs);
      }

      await advanceToNext(page);

      // Capture checkpoint at intervals
      if (currentBatch.length >= persona.checkpointInterval) {
        checkpointNum++;
        const checkpoint = await captureCheckpoint(
          page, persona, checkpointNum, currentBatch,
          consoleErrors.splice(0), // drain captured errors
          allResults.length
        );
        checkpoints.push(checkpoint);
        currentBatch = [];
      }
    } catch (err) {
      // Check if we've run out of questions (pedant mode)
      if (persona.numQuestions === 'ALL') {
        break; // Expected: no more questions to answer
      }
      throw err; // Unexpected error
    }
  }

  // Capture final checkpoint for any remaining questions
  if (currentBatch.length > 0) {
    checkpointNum++;
    const checkpoint = await captureCheckpoint(
      page, persona, checkpointNum, currentBatch,
      consoleErrors.splice(0),
      allResults.length
    );
    checkpoints.push(checkpoint);
  }

  // Take final screenshot
  const finalScreenshotPath = resolve(`tests/visual/screenshots/personas/${persona.id}-final.png`);
  await page.screenshot({ path: finalScreenshotPath, fullPage: true });

  return {
    personaId: persona.id,
    personaName: persona.name,
    totalQuestions: allResults.length,
    correctCount: allResults.filter(r => r.correct).length,
    checkpoints,
    allResults,
    finalScreenshotPath,
    startTime: checkpoints[0]?.timestamp || Date.now(),
    endTime: Date.now(),
  };
}

// ─── Cleanup utility ─────────────────────────────────────────

/**
 * Remove stale working files for a persona before a fresh simulation.
 *
 * @param {string} personaId - e.g., "P01"
 */
export function cleanWorkingFiles(personaId) {
  const workingDir = resolve('tests/visual/.working/personas');
  if (!existsSync(workingDir)) return;

  const files = readdirSync(workingDir);
  for (const file of files) {
    if (file.startsWith(`${personaId}-`)) {
      unlinkSync(join(workingDir, file));
    }
  }

  // Also clean screenshots
  const screenshotDir = resolve('tests/visual/screenshots/personas');
  if (!existsSync(screenshotDir)) return;

  const screenshots = readdirSync(screenshotDir);
  for (const file of screenshots) {
    if (file.startsWith(`${personaId}-`)) {
      unlinkSync(join(screenshotDir, file));
    }
  }
}
