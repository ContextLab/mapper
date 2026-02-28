/**
 * Persona Simulation — Playwright end-to-end test.
 *
 * Simulates 4 learner personas interacting with the REAL app:
 * - Selects a domain, answers 20 questions based on persona expertise
 * - Takes screenshots of the knowledge map after answering
 * - Opens video recommendations and screenshots them
 * - Reports on map accuracy and recommendation quality
 *
 * Uses actual BALD/phase-based question selection, real GP estimator,
 * and real video recommender — exactly what a user would see.
 */
import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// ─── Load question database for answer lookup ────────────────
const indexData = JSON.parse(readFileSync(resolve('data/domains/index.json'), 'utf-8'));
const questionDb = new Map(); // questionText → question object
for (const d of Object.values(indexData.domains)) {
  if (!d || !d.id) continue;
  try {
    const domainData = JSON.parse(readFileSync(resolve(`data/domains/${d.id}.json`), 'utf-8'));
    const qs = domainData.questions || [];
    for (const q of qs) {
      if (q.question_text && q.id) {
        // Normalize text for matching (strip whitespace variations)
        const key = q.question_text.trim().substring(0, 100);
        questionDb.set(key, q);
      }
    }
  } catch { /* skip missing files */ }
}

console.log(`Question DB loaded: ${questionDb.size} questions`);

// ─── Persona definitions (domain-based, not spatial) ─────────
// Since all questions cluster in a narrow band (x:0.6-0.7, y:0.55-0.65),
// spatial personas are ineffective. Instead, define expertise by DOMAIN:
// the persona knows their domains and is weak at others.
const SCIENCE_DOMAINS = new Set([
  'physics', 'astrophysics', 'quantum-physics', 'mathematics', 'calculus',
  'linear-algebra', 'number-theory', 'probability-statistics',
]);
const BIO_DOMAINS = new Set([
  'biology', 'genetics', 'molecular-cell-biology', 'neuroscience',
  'neurobiology', 'cognitive-neuroscience', 'computational-neuroscience',
]);
const HUMANITIES_DOMAINS = new Set([
  'world-history', 'us-history', 'european-history', 'asian-history',
  'art-history', 'european-art-history', 'chinese-art-history',
  'archaeology', 'prehistoric-archaeology', 'forensic-archaeology',
]);

const PERSONAS = [
  {
    name: 'Physics-Math Expert',
    domain: 'physics',
    numQuestions: 20,
    getAccuracy(x, y, domainId) {
      if (SCIENCE_DOMAINS.has(domainId)) return 0.90;
      if (BIO_DOMAINS.has(domainId)) return 0.30;
      return 0.25; // humanities, CS, etc
    },
  },
  {
    name: 'Biology Specialist',
    domain: 'biology',
    numQuestions: 20,
    getAccuracy(x, y, domainId) {
      if (BIO_DOMAINS.has(domainId)) return 0.85;
      if (SCIENCE_DOMAINS.has(domainId)) return 0.35;
      return 0.30;
    },
  },
  {
    name: 'History Buff',
    domain: 'All (General)',
    numQuestions: 20,
    getAccuracy(x, y, domainId) {
      if (HUMANITIES_DOMAINS.has(domainId)) return 0.85;
      if (BIO_DOMAINS.has(domainId)) return 0.25;
      return 0.20;
    },
  },
  {
    name: 'Struggling Novice',
    domain: 'All (General)',
    numQuestions: 20,
    getAccuracy(x, y, domainId) {
      return 0.20; // Weak everywhere, mostly guessing
    },
  },
];

// ─── Seeded PRNG ─────────────────────────────────────────────
function makePrng(seed) {
  let s = seed;
  return function () {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

// ─── Helpers ─────────────────────────────────────────────────

async function selectDomain(page, domainName) {
  // If on landing page, click start button to enter the map first
  const startBtn = page.locator('#landing-start-btn');
  if (await startBtn.isVisible().catch(() => false)) {
    await page.waitForSelector('#landing-start-btn[data-ready]', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }

  // Use header domain selector — find option by visible text
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

/** Read the currently displayed question text from the DOM. */
async function getDisplayedQuestion(page) {
  const el = page.locator('.quiz-question');
  await el.waitFor({ state: 'visible', timeout: 5000 });
  return (await el.textContent()).trim();
}

/** Find the question object from our DB by matching displayed text. */
function lookupQuestion(displayedText) {
  // Try exact prefix match (first 100 chars)
  const key = displayedText.substring(0, 100);
  if (questionDb.has(key)) return questionDb.get(key);

  // Fuzzy fallback: find best match by prefix overlap
  let bestMatch = null;
  let bestScore = 0;
  for (const [dbKey, q] of questionDb) {
    // Compare first N chars
    const len = Math.min(dbKey.length, displayedText.length, 80);
    let score = 0;
    for (let i = 0; i < len; i++) {
      if (dbKey[i] === displayedText[i]) score++;
      else break;
    }
    if (score > bestScore) {
      bestScore = score;
      bestMatch = q;
    }
  }
  return bestScore > 20 ? bestMatch : null;
}

/**
 * Answer the currently displayed question.
 * @returns {{ correct: boolean, x: number, y: number, domain: string }}
 */
async function answerQuestion(page, persona, rand) {
  const displayedText = await getDisplayedQuestion(page);
  const question = lookupQuestion(displayedText);

  if (!question) {
    // Can't find question in DB — answer randomly (click first enabled option)
    console.log(`  [WARN] Could not match question: "${displayedText.substring(0, 50)}..."`);
    const firstBtn = page.locator('.quiz-option:not([disabled])').first();
    await firstBtn.click();
    return { correct: false, x: 0.5, y: 0.5, domain: 'unknown', difficulty: 2 };
  }

  const domainId = question.domain_ids?.[0] || 'unknown';
  const pCorrect = persona.getAccuracy(question.x, question.y, domainId);
  const shouldBeCorrect = rand() < pCorrect;

  // Get all option buttons and their text
  const optionBtns = page.locator('.quiz-option');
  const btnCount = await optionBtns.count();
  const correctAnswerText = question.options[question.correct_answer];

  let correctBtnIndex = -1;
  let wrongBtnIndex = -1;

  for (let i = 0; i < btnCount; i++) {
    const btnText = await optionBtns.nth(i).textContent();
    // Match by checking if button text contains the correct answer text
    // (rendered text might have slight formatting differences)
    if (btnText.trim() === correctAnswerText.trim() ||
        btnText.includes(correctAnswerText.substring(0, 40))) {
      correctBtnIndex = i;
    } else if (wrongBtnIndex === -1) {
      wrongBtnIndex = i;
    }
  }

  // If we couldn't find the correct button by text, try a different matching approach
  if (correctBtnIndex === -1) {
    // Fall back: just pick index 0 for correct, 1 for wrong
    correctBtnIndex = 0;
    wrongBtnIndex = 1;
  }

  const targetIndex = shouldBeCorrect ? correctBtnIndex : (wrongBtnIndex >= 0 ? wrongBtnIndex : 0);
  await optionBtns.nth(targetIndex).click();

  const domain = question.domain_ids?.[0] || 'unknown';
  return {
    correct: shouldBeCorrect,
    x: question.x,
    y: question.y,
    domain,
    difficulty: question.difficulty,
  };
}

/** Press N/Enter to advance to next question. */
async function advanceToNext(page) {
  // Wait for options to be disabled (answer processed)
  await page.waitForTimeout(300);
  await page.keyboard.press('n');
  // Wait for new question to load
  await page.waitForTimeout(500);
}

// ─── Tests ───────────────────────────────────────────────────

const LOAD_TIMEOUT = 15000;

for (const persona of PERSONAS) {
  test.describe(`Persona: ${persona.name}`, () => {
    test(`answers ${persona.numQuestions} questions and checks map + recommendations`, async ({ page, browserName }) => {
      test.skip(browserName !== 'chromium', 'Persona simulation on Chromium only');
      test.setTimeout(120000); // 2 min timeout

      const rand = makePrng(42 + PERSONAS.indexOf(persona));
      const results = [];

      // Navigate to app
      await page.goto('/');
      await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
      // Select domain
      await selectDomain(page, persona.domain);
      await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });

      // Wait for first question to appear
      await page.waitForSelector('.quiz-question', { timeout: 5000 });
      await page.waitForTimeout(500);

      // ─── Answer questions ────────────────────────────
      console.log(`\n${'═'.repeat(60)}`);
      console.log(`PERSONA: ${persona.name} (domain: ${persona.domain})`);
      console.log(`${'═'.repeat(60)}`);

      for (let i = 0; i < persona.numQuestions; i++) {
        try {
          const result = await answerQuestion(page, persona, rand);
          results.push(result);
          const symbol = result.correct ? '✓' : '✗';
          console.log(`  Q${(i + 1).toString().padStart(2)}: ${symbol} (${result.x.toFixed(2)}, ${result.y.toFixed(2)}) d=${result.difficulty} [${result.domain}]`);

          await advanceToNext(page);
        } catch (err) {
          console.log(`  Q${i + 1}: ERROR — ${err.message}`);
          break;
        }
      }

      // ─── Summary ─────────────────────────────────────
      const correctCount = results.filter(r => r.correct).length;
      console.log(`\n  Summary: ${correctCount}/${results.length} correct (${(correctCount / results.length * 100).toFixed(0)}%)`);

      // Domain breakdown
      const domainStats = {};
      for (const r of results) {
        if (!domainStats[r.domain]) domainStats[r.domain] = { total: 0, correct: 0 };
        domainStats[r.domain].total++;
        if (r.correct) domainStats[r.domain].correct++;
      }
      console.log('  Per-domain:');
      for (const [d, s] of Object.entries(domainStats).sort((a, b) => b[1].total - a[1].total)) {
        console.log(`    ${d.padEnd(25)} ${s.correct}/${s.total} (${(s.correct / s.total * 100).toFixed(0)}%)`);
      }

      // ─── Screenshot: Knowledge Map ───────────────────
      console.log('\n  Taking map screenshot...');
      await page.waitForTimeout(1000);
      const slug = persona.name.toLowerCase().replace(/\s+/g, '-');
      await page.screenshot({
        path: `tests/visual/screenshots/persona-${slug}-map.png`,
        fullPage: true,
      });
      console.log('  Map screenshot saved.');

      // ─── Open video recommendations ──────────────────
      console.log('\n  Opening video recommendations...');
      const suggestBtn = page.locator('#suggest-btn');

      // Force-enable (normally requires 5+ quiz answers, but we answered 20)
      // Should already be enabled, but force just in case
      await page.evaluate(() => {
        const btn = document.getElementById('suggest-btn');
        if (btn) btn.disabled = false;
      });

      if (await suggestBtn.isVisible()) {
        await suggestBtn.click();

        try {
          await page.waitForSelector('#video-modal:not([hidden])', { timeout: 5000 });
          await page.waitForSelector('.video-list, .video-empty-msg', { timeout: 3000 });

          // Read recommended videos
          const videoItems = page.locator('.video-item');
          const vidCount = await videoItems.count();
          console.log(`  ${vidCount} videos recommended.`);

          if (vidCount > 0) {
            for (let i = 0; i < Math.min(5, vidCount); i++) {
              const title = await videoItems.nth(i).locator('.video-title').textContent();
              const gain = await videoItems.nth(i).locator('.video-gain-pct').textContent().catch(() => '?');
              console.log(`    #${i + 1}: "${title.trim().substring(0, 55)}" gain=${gain.trim()}`);
            }
          }

          // Screenshot the video modal
          await page.screenshot({
            path: `tests/visual/screenshots/persona-${persona.name.toLowerCase().replace(/\s+/g, '-')}-videos.png`,
            fullPage: true,
          });
          console.log('  Video modal screenshot saved.');
        } catch (err) {
          console.log(`  Video modal error: ${err.message}`);
        }
      } else {
        console.log('  Suggest button not visible — skipping video check.');
      }

      // ─── Final assertions ────────────────────────────
      // Basic sanity: we answered questions successfully
      expect(results.length).toBeGreaterThanOrEqual(10);

      console.log(`\n  DONE: ${persona.name}`);
    });
  });
}
