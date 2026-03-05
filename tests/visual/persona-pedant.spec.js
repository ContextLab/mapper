/**
 * Pedant Persona — Playwright end-to-end tests for content audit personas.
 *
 * Pedant personas (P19-P21) answer ALL questions in their domain with
 * checkpointInterval=1, capturing detailed per-question data for Opus
 * AI agent evaluation with web-search verification.
 *
 * Run a single pedant: npx playwright test persona-pedant.spec.js -g "Pedant: Dr. Pedantic"
 */
import { test, expect } from '@playwright/test';
import { PERSONAS } from './personas/definitions.js';
import { loadQuestionDb, getQuestionsForDomain, getAllDomainIds } from './personas/question-loader.js';
import { runPersonaSession, cleanWorkingFiles } from './personas/runner.js';

// Load question database
const questionDb = loadQuestionDb();
console.log(`Question DB loaded: ${questionDb.size} questions for persona-pedant`);

// ─── Pedant Personas (P19-P21) ───────────────────────────────

const pedants = PERSONAS.filter(p => p.category === 'pedant');

for (const persona of pedants) {
  test.describe(`Pedant: ${persona.name}`, () => {
    test(`audits ALL ${persona.domain} questions with per-question checkpoints`, async ({ page, browserName }) => {
      // Match browser
      if (persona.browser === 'chromium' && browserName !== 'chromium') {
        test.skip(true, `${persona.name} requires chromium`);
        return;
      }
      if (persona.browser === 'firefox' && browserName !== 'firefox') {
        test.skip(true, `${persona.name} requires firefox`);
        return;
      }

      await page.setViewportSize({ width: persona.device.width, height: persona.device.height });

      // Pedants answer ALL questions in domain + descendants — can take a long time.
      // The app aggregates questions from the root domain plus all child sub-domains.
      // E.g., physics (50) + astrophysics (50) + quantum-physics (50) = 150 total.
      // For 'all', every domain is a descendant.
      const DOMAIN_HIERARCHY = {
        physics: ['physics', 'astrophysics', 'quantum-physics'],
        biology: ['biology', 'genetics', 'molecular-cell-biology'],
        neuroscience: ['neuroscience', 'cognitive-neuroscience', 'computational-neuroscience', 'neurobiology'],
        mathematics: ['mathematics', 'calculus', 'linear-algebra', 'number-theory', 'probability-statistics'],
        'computer-science': ['computer-science', 'artificial-intelligence-ml', 'theory-of-computation', 'algorithms'],
        'art-history': ['art-history', 'european-art-history', 'chinese-art-history'],
        economics: ['economics', 'microeconomics', 'macroeconomics'],
        philosophy: ['philosophy', 'ethics', 'philosophy-of-mind', 'logic', 'metaphysics'],
        linguistics: ['linguistics', 'syntax', 'semantics', 'computational-linguistics'],
        sociology: ['sociology', 'political-sociology', 'criminology'],
        psychology: ['psychology', 'cognitive-psychology', 'social-psychology', 'developmental-psychology', 'clinical-psychology'],
        archaeology: ['archaeology', 'prehistoric-archaeology', 'forensic-archaeology'],
        'world-history': ['world-history', 'us-history', 'european-history', 'asian-history'],
      };

      let expectedQuestions;
      if (persona.domain === 'all') {
        expectedQuestions = getAllDomainIds().reduce(
          (sum, id) => sum + getQuestionsForDomain(id).length, 0
        );
      } else {
        const hierarchy = DOMAIN_HIERARCHY[persona.domain] || [persona.domain];
        expectedQuestions = hierarchy.reduce(
          (sum, id) => sum + getQuestionsForDomain(id).length, 0
        );
      }

      // 16 seconds per question (screenshot + answer + advance + overhead) + 5 min buffer for page load, domain re-trigger, cache warm-up, final screenshot.
      const timeoutMs = Math.max(600_000, expectedQuestions * 16_000 + 300_000);
      test.setTimeout(timeoutMs);

      cleanWorkingFiles(persona.id);

      // Pedants use the same runner but with numQuestions='ALL' which
      // means the runner answers until it runs out of questions or errors
      const session = await runPersonaSession(page, persona, questionDb, {
        seed: persona.id.charCodeAt(1) * 1000 + persona.id.charCodeAt(2),
      });

      // Pedants should answer many questions
      expect(session.totalQuestions).toBeGreaterThanOrEqual(10);

      // Each question should be its own checkpoint (interval=1)
      // Allow some tolerance — last batch might be partial
      expect(session.checkpoints.length).toBeGreaterThanOrEqual(
        Math.floor(session.totalQuestions * 0.8)
      );

      // No critical estimator errors
      const allErrors = session.checkpoints.flatMap(cp => cp.consoleErrors);
      const criticalErrors = allErrors.filter(e =>
        e.includes('Cholesky') || e.includes('NaN') || e.includes('Infinity')
      );
      expect(criticalErrors.length, `Critical errors during pedant audit`).toBe(0);

      console.log(`✓ ${persona.name}: ${session.totalQuestions}q audited, ${session.checkpoints.length} checkpoints, ${allErrors.length} console errors`);
    });
  });
}
