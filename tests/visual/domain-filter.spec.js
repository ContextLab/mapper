/** Domain filtering tests — verify zero cross-domain contamination (US2). */
import { test, expect } from './fixtures.js';

const LOAD_TIMEOUT = 15000;

async function selectDomain(page, domainName) {
  const value = domainName.toLowerCase().replace(/\s+/g, '-');
  const startBtn = page.locator('#landing-start-btn');
  if (await startBtn.isVisible().catch(() => false)) {
    await page.waitForSelector('#landing-start-btn[data-ready]:not([disabled])', { timeout: LOAD_TIMEOUT });
    await startBtn.click();
    await page.waitForSelector('#quiz-panel:not([hidden])', { timeout: LOAD_TIMEOUT });
  }
  const trigger = page.locator('.domain-selector .custom-select-trigger');
  await trigger.click();
  await page.locator(`.domain-selector .custom-select-option[data-value="${value}"]`).click();
}

/**
 * Answer N questions and collect the domain_ids from each question via __mapper API.
 * Returns an array of { questionId, domainIds } objects.
 */
async function answerAndCollect(page, count) {
  const results = [];
  for (let i = 0; i < count; i++) {
    // Wait for enabled quiz options (may take time after auto-advance)
    await page.waitForSelector('.quiz-option:not(:disabled)', { timeout: 15000 });
    await page.waitForTimeout(300); // let question state settle

    // Grab current question's domain_ids via exposed API
    const info = await page.evaluate(() => {
      const q = window.__mapper?.getCurrentQuestion?.();
      return q ? { id: q.id, domainIds: q.domain_ids || [] } : null;
    });
    if (info) results.push(info);

    // Answer the question (click first option)
    const prevId = info?.id;
    await page.locator('.quiz-option').first().click();

    // Wait for auto-advance to complete — new question or end of questions
    if (i < count - 1) {
      await page.waitForFunction(
        (pid) => {
          const q = window.__mapper?.getCurrentQuestion?.();
          return !q || q.id !== pid;
        },
        prevId,
        { timeout: 10000 }
      ).catch(() => {});
      await page.waitForTimeout(300);
    }
  }
  return results;
}

test.describe('Domain Filtering (US2)', () => {
  test.describe.configure({ timeout: 120000 });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#landing', { timeout: LOAD_TIMEOUT });
  });

  test('mathematics domain serves only math questions', async ({ page }) => {
    await selectDomain(page, 'mathematics');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(2000);

    const results = await answerAndCollect(page, 20);
    expect(results.length).toBeGreaterThanOrEqual(15);

    const mathDomains = new Set([
      'mathematics', 'calculus', 'linear-algebra', 'number-theory',
      'probability-statistics', 'logic', 'algorithms'
    ]);
    for (const r of results) {
      const hasMath = r.domainIds.some(d => mathDomains.has(d));
      expect(hasMath, `Question ${r.id} has domains [${r.domainIds}] — not math`).toBe(true);
    }
  });

  test('biology domain serves only biology questions', async ({ page }) => {
    await selectDomain(page, 'biology');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(2000);

    const results = await answerAndCollect(page, 20);
    expect(results.length).toBeGreaterThanOrEqual(15);

    const bioDomains = new Set([
      'biology', 'genetics', 'molecular-cell-biology', 'neurobiology'
    ]);
    for (const r of results) {
      const hasBio = r.domainIds.some(d => bioDomains.has(d));
      expect(hasBio, `Question ${r.id} has domains [${r.domainIds}] — not biology`).toBe(true);
    }
  });

  test('physics domain serves only physics questions', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(2000);

    const results = await answerAndCollect(page, 20);
    expect(results.length).toBeGreaterThanOrEqual(15);

    const physDomains = new Set([
      'physics', 'astrophysics', 'quantum-physics'
    ]);
    for (const r of results) {
      const hasPhys = r.domainIds.some(d => physDomains.has(d));
      expect(hasPhys, `Question ${r.id} has domains [${r.domainIds}] — not physics`).toBe(true);
    }
  });

  test('all domain serves questions from any domain', async ({ page }) => {
    await selectDomain(page, 'all');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(2000);

    const results = await answerAndCollect(page, 10);
    expect(results.length).toBeGreaterThanOrEqual(5);

    // All questions should have valid domain_ids (non-empty)
    for (const r of results) {
      expect(r.domainIds.length).toBeGreaterThan(0);
    }
  });

  test('switching domains changes question pool', async ({ page }) => {
    await selectDomain(page, 'physics');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(2000);
    const physicsResults = await answerAndCollect(page, 5);

    await selectDomain(page, 'philosophy');
    await page.waitForSelector('.quiz-question', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(2000);
    const philResults = await answerAndCollect(page, 5);

    // Physics questions should not appear in philosophy set
    const physicsIds = new Set(physicsResults.map(r => r.id));
    for (const r of philResults) {
      expect(physicsIds.has(r.id), `Question ${r.id} appeared in both physics and philosophy`).toBe(false);
    }
  });
});
