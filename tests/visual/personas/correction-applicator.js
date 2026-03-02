/**
 * Correction applicator for pedant-verified question fixes.
 *
 * Reads verified corrections from pedant evaluation, filters to
 * CORRECTION_VERIFIED verdicts only, and updates domain question
 * JSON files with corrected answers.
 */
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, join } from 'node:path';

/**
 * Apply verified corrections to domain question JSON files.
 *
 * Only applies corrections with verdict === 'CORRECTION_VERIFIED'.
 * Writes a changelog documenting all changes.
 *
 * @param {string} correctionsPath - Path to {personaId}-corrections.json
 * @param {string} [domainJsonDir] - Override domain JSON directory (defaults to data/domains/)
 * @returns {{ applied: number, skipped: number, changelog: string }}
 */
export function applyVerifiedCorrections(correctionsPath, domainJsonDir) {
  const dir = domainJsonDir || resolve('data/domains');

  if (!existsSync(correctionsPath)) {
    return { applied: 0, skipped: 0, changelog: 'No corrections file found.' };
  }

  const corrections = JSON.parse(readFileSync(correctionsPath, 'utf-8'));
  if (!Array.isArray(corrections) || corrections.length === 0) {
    return { applied: 0, skipped: 0, changelog: 'No corrections to apply.' };
  }

  let applied = 0;
  let skipped = 0;
  const changelogEntries = [];

  // Group corrections by domain for efficient file access
  const byDomain = new Map();
  for (const c of corrections) {
    if (c.verdict !== 'CORRECTION_VERIFIED') {
      skipped++;
      continue;
    }
    const domain = c.domainId || 'unknown';
    if (!byDomain.has(domain)) byDomain.set(domain, []);
    byDomain.get(domain).push(c);
  }

  for (const [domainId, domainCorrections] of byDomain) {
    const domainPath = join(dir, `${domainId}.json`);
    if (!existsSync(domainPath)) {
      for (const c of domainCorrections) {
        changelogEntries.push(`SKIPPED: ${c.questionId} — domain file ${domainId}.json not found`);
        skipped++;
      }
      continue;
    }

    const domainData = JSON.parse(readFileSync(domainPath, 'utf-8'));
    const questions = domainData.questions || [];
    let modified = false;

    for (const correction of domainCorrections) {
      const question = questions.find(q => q.id === correction.questionId);
      if (!question) {
        changelogEntries.push(`SKIPPED: ${correction.questionId} — not found in ${domainId}.json`);
        skipped++;
        continue;
      }

      const oldAnswer = question.correct_answer;
      const newAnswer = correction.correctedAnswer;

      if (oldAnswer === newAnswer) {
        changelogEntries.push(`SKIPPED: ${correction.questionId} — answer already matches correction (${newAnswer})`);
        skipped++;
        continue;
      }

      // Apply the correction
      question.correct_answer = newAnswer;
      modified = true;
      applied++;

      changelogEntries.push(
        `APPLIED: ${correction.questionId} in ${domainId}\n` +
        `  Question: ${question.question_text?.substring(0, 80)}...\n` +
        `  Changed: ${oldAnswer} → ${newAnswer}\n` +
        `  Evidence: ${correction.evidence?.substring(0, 200) || 'N/A'}\n` +
        `  Source: ${correction.sourceUrl || 'N/A'}`
      );
    }

    // Write updated domain file if any corrections applied
    if (modified) {
      writeFileSync(domainPath, JSON.stringify(domainData, null, 2));
    }
  }

  // Write changelog
  const changelog = `# Corrections Applied\n\n` +
    `**Date**: ${new Date().toISOString()}\n` +
    `**Source**: ${correctionsPath}\n` +
    `**Applied**: ${applied} | **Skipped**: ${skipped}\n\n` +
    changelogEntries.join('\n\n') + '\n';

  // Write changelog to reports directory
  const reportsDir = resolve('tests/visual/reports');
  mkdirSync(reportsDir, { recursive: true });

  // Extract persona ID from corrections path filename
  const filename = correctionsPath.split('/').pop();
  const personaId = filename?.replace('-corrections.json', '') || 'unknown';
  const changelogPath = join(reportsDir, `${personaId}-corrections-applied.md`);
  writeFileSync(changelogPath, changelog);

  return { applied, skipped, changelog };
}

/**
 * Collect all flagged questions from evaluation files into a corrections JSON.
 *
 * Reads eval files from .working/personas/ and extracts questions where
 * isCorrectAsMarked === false with web verification data.
 *
 * @param {string} personaId - e.g., "P19"
 * @param {string} [workingDir] - Override working directory
 * @returns {object[]} Array of correction objects
 */
export function collectFlaggedQuestions(personaId, workingDir) {
  const dir = workingDir || resolve('tests/visual/.working/personas');
  if (!existsSync(dir)) return [];

  const files = readdirSync(dir)
    .filter(f => f.startsWith(`${personaId}-eval-`) && f.endsWith('.json'))
    .sort();

  const flagged = [];

  for (const file of files) {
    try {
      const evalData = JSON.parse(readFileSync(join(dir, file), 'utf-8'));
      for (const qe of evalData.questionEvaluations || []) {
        if (qe.isCorrectAsMarked === false && qe.webVerification) {
          flagged.push({
            questionId: qe.questionId,
            questionText: qe.questionText,
            currentAnswer: qe.markedAnswer,
            correctedAnswer: qe.webVerification.correctedAnswer || qe.agentAssessment,
            verdict: qe.webVerification.verdict,
            sourceUrl: qe.webVerification.sourceUrl,
            evidence: qe.webVerification.evidence,
            domainId: qe.domainId || 'unknown',
          });
        }
      }
    } catch { /* skip corrupt files */ }
  }

  return flagged;
}
