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
import { lookupQuestion, lookupQuestionById } from './question-loader.js';

const LOAD_TIMEOUT = 15000;

/** Strip LaTeX markup and normalize Unicode for fuzzy text comparison. */
function stripLatex(text) {
  return text
    .replace(/\$([^$]*)\$/g, '$1')
    .replace(/\\[a-zA-Z]+\{([^}]*)\}/g, '$1')
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/[\\{}^_]/g, '')
    .replace(/\u2212/g, '-')   // Unicode minus → hyphen
    .replace(/\u2013/g, '-')   // en-dash → hyphen
    .replace(/\u2014/g, '-')   // em-dash → hyphen
    .replace(/\u00d7/g, 'x')   // × → x
    .replace(/\u2248/g, '~')   // ≈ → ~
    .replace(/\u2264/g, '<=')  // ≤ → <=
    .replace(/\u2265/g, '>=')  // ≥ → >=
    .replace(/\s+/g, ' ')
    .trim();
}

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

// ─── Tutorial flow ──────────────────────────────────────────

/**
 * Click through the full tutorial for 'complete' personas.
 * Handles all 11 steps: click-advance, answer questions, switch domains, button clicks.
 */
async function completeTutorialFlow(page) {
  const nextBtn = page.locator('.tutorial-next-btn');
  const modal = page.locator('#tutorial-modal');

  // Helper: wait for tutorial modal and click Next/Finish
  async function clickNext(timeout = 3000) {
    await nextBtn.waitFor({ state: 'visible', timeout });
    await nextBtn.click();
    await page.waitForTimeout(350);
  }

  // Helper: answer one question via the quiz panel
  async function answerOneQuestion() {
    const optionBtns = page.locator('.quiz-option');
    await optionBtns.first().waitFor({ state: 'visible', timeout: 5000 });
    await optionBtns.first().click();
    await page.waitForTimeout(1000); // auto-advance delay
    // If auto-advance is off, click the quiz Next button to load the next question
    const quizNextBtn = page.locator('#quiz-panel .quiz-next-btn, #quiz-panel button:has-text("Next")');
    try {
      if (await quizNextBtn.first().isVisible({ timeout: 500 })) {
        await quizNextBtn.first().click();
        await page.waitForTimeout(500);
      }
    } catch {
      // Auto-advance handled it
    }
  }

  try {
    await modal.waitFor({ state: 'visible', timeout: 5000 });

    // Step 1: Your Knowledge Map — 2 substeps, click Next each
    await clickNext(); // substep 1
    await clickNext(); // substep 2

    // Step 2: The Quiz Panel — click Next
    await clickNext();

    // Step 3: Video Recommendations — 2 substeps (may be skipped on mobile)
    try {
      await clickNext(); // substep 1
      await clickNext(); // substep 2
    } catch {
      // Skipped on mobile
    }

    // Step 4: Try Answering a Question — answer, see feedback, click Continue
    await modal.waitFor({ state: 'visible', timeout: 3000 });
    await answerOneQuestion();
    try {
      const continueBtn = page.locator('#tutorial-modal button', { hasText: 'Continue' });
      await continueBtn.waitFor({ state: 'visible', timeout: 3000 });
      await continueBtn.click();
      await page.waitForTimeout(350);
    } catch {
      // Feedback may not have appeared
    }

    // Step 5: Building Your Map — 3 substeps
    // Substep 1: answer 2 questions
    await modal.waitFor({ state: 'visible', timeout: 3000 });
    for (let i = 0; i < 2; i++) {
      await answerOneQuestion();
    }
    // Substep 2: toggle auto-advance (off then back on)
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      const autoAdvanceTrack = page.locator('.auto-advance-track');
      await autoAdvanceTrack.waitFor({ state: 'visible', timeout: 2000 });
      await autoAdvanceTrack.click(); // toggle OFF — advances tutorial
      await page.waitForTimeout(500);
      // Toggle back ON so subsequent answers auto-advance
      await autoAdvanceTrack.click();
      await page.waitForTimeout(300);
    } catch {
      try { await clickNext(1000); } catch { /* continue */ }
    }
    // Substep 3: answer 1 more question
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      await answerOneQuestion();
    } catch {
      // May have advanced
    }

    // Step 6: Switch Domains — select from dropdown
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      const trigger = page.locator('.domain-selector .custom-select-trigger');
      await trigger.click();
      const options = page.locator('.domain-selector .custom-select-option');
      const count = await options.count();
      if (count > 1) {
        await options.nth(1).click();
      }
      await page.waitForTimeout(1500);
    } catch {
      // May have auto-advanced
    }

    // Step 7: Exploring Domain-Specific Knowledge — answer 2
    try {
      await modal.waitFor({ state: 'visible', timeout: 3000 });
      for (let i = 0; i < 2; i++) {
        await answerOneQuestion();
      }
    } catch {
      // May have advanced
    }

    // Step 8: Your Expertise — click trophy button, then follow-up Next
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      const trophyBtn = page.locator('#trophy-btn');
      await trophyBtn.click();
      await page.waitForTimeout(500);
      await clickNext(2000);
    } catch {
      // May have completed
    }

    // Step 9: Fill in Your Knowledge Gaps! — click suggest, then follow-up Next
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      const suggestBtn = page.locator('#suggest-btn');
      await suggestBtn.click();
      await page.waitForTimeout(500);
      await clickNext(2000);
    } catch {
      // May have completed
    }

    // Step 10: Share Your Map — click share, then follow-up Next
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      const shareBtn = page.locator('#share-btn');
      await shareBtn.click();
      await page.waitForTimeout(500);
      await clickNext(2000);
    } catch {
      // May have completed
    }

    // Step 11: Tutorial Complete! — click Start Over / dismiss
    try {
      await modal.waitFor({ state: 'visible', timeout: 2000 });
      await clickNext();
    } catch {
      // Tutorial already done
    }

    await page.waitForTimeout(500);
  } catch {
    // Tutorial didn't appear or completed early — continue with test
  }
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
    await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }

  // Use header domain selector
  const trigger = page.locator('.domain-selector .custom-select-trigger');
  await trigger.click();

  // Prefer data-value attribute match (domain ID) — most reliable
  const byValue = page.locator(`.domain-selector .custom-select-option[data-value="${domainName}"]`);
  if (await byValue.count() > 0) {
    await byValue.click();
    return;
  }

  // Fallback: text matching for display names like "All (General)"
  const options = page.locator('.domain-selector .custom-select-option');
  const count = await options.count();
  const target = domainName.toLowerCase();
  for (let i = 0; i < count; i++) {
    const text = (await options.nth(i).textContent()).trim().toLowerCase();
    if (text.includes(target)) {
      await options.nth(i).click();
      return;
    }
  }
  // Last resort: click first option
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
  // Try to get the question ID directly from app state (avoids LaTeX text-matching issues)
  let question = null;
  try {
    const appQuestion = await page.evaluate(() => {
      const q = window.__mapper?.getCurrentQuestion?.();
      return q ? { id: q.id } : null;
    });
    if (appQuestion?.id) {
      question = lookupQuestionById(questionDb, appQuestion.id);
    }
  } catch { /* app state not available — fall through to text matching */ }

  // Fallback: text-based matching
  const displayedText = await getDisplayedQuestion(page);
  if (!question) {
    question = lookupQuestion(questionDb.byText || questionDb, displayedText);
  }

  if (!question) {
    // Can't find in DB — answer randomly
    console.warn('[runner] ? answer: DB miss — question text not found in index. Text preview:', displayedText.substring(0, 80));
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

  // Build complete DOM button index → DB key mapping BEFORE clicking.
  // The app shuffles option display order, so DOM position ≠ DB key.
  // Score each button against each option by common-prefix length,
  // then greedily assign best matches (handles near-identical options).
  const optionBtns = page.locator('.quiz-option');
  const btnCount = await optionBtns.count();
  const btnToDbKey = {};
  const dbKeyUsed = new Set();

  // Read all button texts once
  const btnTexts = [];
  for (let i = 0; i < btnCount; i++) {
    btnTexts.push((await optionBtns.nth(i).textContent()).trim());
  }

  // Score every (button, option) pair by common-prefix length.
  // Two passes: raw text first, then LaTeX-normalized for disambiguation.
  const scores = [];
  const optEntries = Object.entries(question.options);
  for (let i = 0; i < btnCount; i++) {
    for (const [key, rawText] of optEntries) {
      const dbText = rawText.trim();
      const domText = btnTexts[i];
      // Raw comparison: char-by-char longest common prefix
      const len = Math.min(domText.length, dbText.length);
      let rawScore = 0;
      for (let c = 0; c < len; c++) {
        if (domText[c] === dbText[c]) rawScore++;
        else break;
      }
      // LaTeX-normalized comparison for disambiguation
      const normDom = stripLatex(domText);
      const normDb = stripLatex(dbText);
      const normLen = Math.min(normDom.length, normDb.length);
      let normScore = 0;
      for (let c = 0; c < normLen; c++) {
        if (normDom[c] === normDb[c]) normScore++;
        else break;
      }
      // Use whichever score is higher (normalized helps with LaTeX options)
      scores.push({ btnIdx: i, key, score: Math.max(rawScore, normScore) });
    }
  }

  // Greedily assign best scores (highest first)
  scores.sort((a, b) => b.score - a.score);
  const btnUsed = new Set();
  for (const { btnIdx, key, score } of scores) {
    if (btnUsed.has(btnIdx) || dbKeyUsed.has(key)) continue;
    if (score >= 10) { // require reasonable match
      btnToDbKey[btnIdx] = key;
      btnUsed.add(btnIdx);
      dbKeyUsed.add(key);
    }
  }

  // Assign remaining by elimination
  const allKeys = Object.keys(question.options);
  for (let i = 0; i < btnCount; i++) {
    if (btnToDbKey[i]) continue;
    const remaining = allKeys.filter(k => !dbKeyUsed.has(k));
    if (remaining.length > 0) {
      btnToDbKey[i] = remaining[0];
      dbKeyUsed.add(remaining[0]);
    }
  }

  // Find correct and wrong button indices using the mapping
  const correctBtnIndex = Object.entries(btnToDbKey)
    .find(([_, key]) => key === question.correct_answer)?.[0] ?? 0;
  const wrongBtnIndex = Object.entries(btnToDbKey)
    .find(([idx, key]) => key !== question.correct_answer && idx !== String(correctBtnIndex))?.[0] ?? (correctBtnIndex === 0 ? 1 : 0);

  const targetIndex = shouldBeCorrect ? Number(correctBtnIndex) : Number(wrongBtnIndex);
  await optionBtns.nth(targetIndex).click();

  let selectedAnswer = btnToDbKey[targetIndex] || '?';

  // Read actual correctness from DOM feedback (the app adds .correct or
  // .incorrect class to the clicked button after answering).
  await page.waitForTimeout(100); // Let DOM update after click
  const wasCorrect = await optionBtns.nth(targetIndex).evaluate(
    el => el.classList.contains('correct')
  );

  // Reconcile selectedAnswer with DOM truth: if the DOM says correct,
  // selectedAnswer must be the correct key (fixes LaTeX mapping errors).
  if (wasCorrect) {
    selectedAnswer = question.correct_answer;
  } else if (shouldBeCorrect && selectedAnswer === question.correct_answer) {
    // We intended correct but got it wrong — mapping error.
    // Mark as unknown since we can't determine the actual key clicked.
    console.warn('[runner] ? answer: mapping error — intended correct but DOM says wrong. Question:', question.id, 'correctKey:', question.correct_answer);
    selectedAnswer = '?';
  }

  return {
    questionId: question.id,
    questionText: question.question_text.substring(0, 200),
    correct: wasCorrect,
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
    ? Infinity // Pedants answer until questions run out
    : persona.numQuestions;

  // Handle tutorial based on persona personality
  const tutorialBehavior = persona.tutorialBehavior || 'dismiss';
  if (tutorialBehavior === 'dismiss') {
    // Pre-dismiss: persona would close it immediately
    await page.addInitScript(() => {
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: false, dismissed: true, step: 1, subStep: 1,
        hasSkippedQuestion: false, skipToastShown: false, returningUser: false,
      }));
    });
  } else {
    // 'skip' and 'complete': override fixture dismissal — let tutorial appear
    await page.addInitScript(() => {
      localStorage.removeItem('mapper-tutorial');
    });
  }

  // Navigate to app
  await page.goto('/');
  await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });

  // Click "Map my knowledge!" to leave landing (tutorial starts after this)
  await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
  await page.locator('#landing-start-btn').click();

  // Handle tutorial before waiting for quiz (overlay can block quiz visibility)
  if (tutorialBehavior === 'skip') {
    // Wait for quiz to load, then force-dismiss tutorial via JS (more reliable than clicking)
    await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 30000 });
    await page.evaluate(() => {
      // Dismiss tutorial by setting localStorage and removing overlay/modal
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: false, dismissed: true, step: 1, subStep: 1,
        hasSkippedQuestion: false, skipToastShown: false, returningUser: false,
      }));
      const overlay = document.getElementById('tutorial-overlay');
      if (overlay) overlay.remove();
      const modal = document.getElementById('tutorial-modal');
      if (modal) modal.remove();
    });
    await page.waitForTimeout(300);
  } else if (tutorialBehavior === 'complete') {
    // Force-complete tutorial via JS (tutorial walkthrough is tested separately;
    // persona tests focus on question-answering behavior)
    await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 30000 });
    await page.evaluate(() => {
      localStorage.setItem('mapper-tutorial', JSON.stringify({
        completed: true, dismissed: false, step: 1, subStep: 1,
        hasSkippedQuestion: false, skipToastShown: false, returningUser: false,
      }));
      const overlay = document.getElementById('tutorial-overlay');
      if (overlay) overlay.remove();
      const modal = document.getElementById('tutorial-modal');
      if (modal) modal.remove();
    });
    await page.waitForTimeout(300);
  } else {
    // dismiss personas: tutorial was pre-dismissed via localStorage — no action needed
    // Wait for map screen — quiz panel appears after domain bundle loads
    await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 30000 });
  }

  // Select initial domain (already past landing page)
  const initialDomain = persona.domain === 'all' ? 'All (General)' : persona.domain;
  await selectDomain(page, initialDomain);
  await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 5000 });

  // Wait for domain bundles to fully load (the app announces "N questions available"
  // via the #live-region when switchDomain completes with aggregated questions).
  // For pedant mode, we need the full pool — wait for the count to stabilize.
  if (persona.numQuestions === 'ALL') {
    // For "all" domain: pre-warm cache by cycling through every parent domain.
    // Each selection triggers loadQuestionsForDomain which fetches descendants.
    if (persona.domain === 'all') {
      const parentDomains = [
        'physics', 'biology', 'neuroscience', 'mathematics', 'computer-science',
        'art-history', 'economics', 'philosophy', 'linguistics', 'sociology',
        'psychology', 'archaeology', 'world-history',
      ];
      for (const parentId of parentDomains) {
        const opt = page.locator(`.domain-selector .custom-select-option[data-value="${parentId}"]`);
        const triggerEl = page.locator('.domain-selector .custom-select-trigger');
        await triggerEl.click();
        if (await opt.count() > 0) {
          await opt.click();
          await page.waitForTimeout(1500); // Let descendants load
        }
      }
      // Now switch back to "all" — all descendants should be cached
      await selectDomain(page, 'All (General)');
      await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 5000 });
      await page.waitForTimeout(3000); // Let aggregation settle
    } else {
      await page.waitForTimeout(3000); // Allow async descendant bundles to load
      // Re-trigger domain load to pick up newly cached descendants
      // Use data-value attribute for exact domain ID match (avoids "biology" matching "neurobiology")
      const trigger = page.locator('.domain-selector .custom-select-trigger');
      await trigger.click();
      const domainValue = persona.domain;
      const exactOption = page.locator(`.domain-selector .custom-select-option[data-value="${domainValue}"]`);
      if (await exactOption.count() > 0) {
        await exactOption.click();
      } else {
        await selectDomain(page, initialDomain);
      }
      await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 5000 });
      await page.waitForTimeout(2000);
    }
  } else {
    await page.waitForTimeout(500);
  }

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
  let prevQuestionText = null;
  let sameQuestionCount = 0;

  for (let i = 0; i < numQuestions; i++) {
    // Domain hopping: switch domain at specified intervals
    if (domainSequence && questionsPerDomain && i > 0 && i % questionsPerDomain === 0) {
      currentDomainIndex = (currentDomainIndex + 1) % domainSequence.length;
      const nextDomain = domainSequence[currentDomainIndex];
      const displayDomain = nextDomain === 'all' ? 'All (General)' : nextDomain;
      await selectDomain(page, displayDomain);
      await page.waitForSelector('.quiz-option', { state: 'visible', timeout: 5000 });
      await page.waitForTimeout(500);
      prevQuestionText = null; // Reset after domain switch
    }

    try {
      // Read question text before answering to detect repetition
      const currentText = await getDisplayedQuestion(page);

      // Detect when the app has run out of questions: same question text
      // appears after advancing (the quiz element stays visible showing
      // the last answered question when no new questions are available).
      if (currentText === prevQuestionText) {
        sameQuestionCount++;
        if (sameQuestionCount >= 2) {
          // Same question 2+ times in a row — app has no more questions
          break;
        }
      } else {
        sameQuestionCount = 0;
      }

      // Also check if all option buttons are disabled (already answered)
      const enabledBtns = await page.locator('.quiz-option:not([disabled])').count();
      if (enabledBtns === 0) {
        // No clickable options — question already answered, no new question served
        break;
      }

      const result = await answerQuestion(page, persona, questionDb, rand);
      allResults.push(result);
      currentBatch.push(result);
      prevQuestionText = currentText;

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
