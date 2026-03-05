/**
 * Report compiler for persona testing framework.
 *
 * Reads checkpoint and evaluation JSON files from .working/personas/,
 * assembles a PersonaReport per data-model.md schema, determines
 * PASS/FAIL/AMBIGUOUS, and writes JSON + Markdown reports.
 */
import { readFileSync, writeFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, join } from 'node:path';

/**
 * Compile a complete report for a single persona simulation.
 *
 * @param {string} personaId - e.g., "P01"
 * @param {string} [workingDir] - Override working directory (defaults to tests/visual/.working/personas)
 * @returns {object} PersonaReport object
 */
export function compileReport(personaId, workingDir) {
  const dir = workingDir || resolve('tests/visual/.working/personas');
  const reportsDir = resolve('tests/visual/reports');
  mkdirSync(reportsDir, { recursive: true });

  // Read all checkpoint files for this persona
  const checkpoints = readPersonaFiles(dir, personaId, 'checkpoint');
  const evaluations = readPersonaFiles(dir, personaId, 'eval');

  // Read corrections if they exist (pedant only)
  const correctionsPath = join(dir, `${personaId}-corrections.json`);
  const corrections = existsSync(correctionsPath)
    ? JSON.parse(readFileSync(correctionsPath, 'utf-8'))
    : [];

  // Assemble question audit from all evaluations
  const questionAudit = [];
  for (const evalData of evaluations) {
    if (evalData.questionEvaluations) {
      questionAudit.push(...evalData.questionEvaluations);
    }
  }

  // Collect all issues from evaluations
  const allIssues = [];
  for (const evalData of evaluations) {
    if (evalData.issuesFound) {
      for (const issue of evalData.issuesFound) {
        allIssues.push({
          ...issue,
          id: `${personaId}-I${allIssues.length + 1}`,
          personaId,
          checkpointNumber: evalData.checkpointNumber,
        });
      }
    }
  }

  // Sort issues by severity
  const severityOrder = { blocker: 0, major: 1, minor: 2, cosmetic: 3 };
  allIssues.sort((a, b) => (severityOrder[a.severity] ?? 4) - (severityOrder[b.severity] ?? 4));

  // Build experience summary from belief narratives
  const experienceSummary = evaluations
    .map(e => e.beliefNarrative || '')
    .filter(Boolean)
    .join('\n\n');

  // Calculate stats
  const totalQuestions = checkpoints.reduce(
    (sum, cp) => sum + (cp.questionsInBatch?.length || 0), 0
  );
  const correctCount = checkpoints.reduce(
    (sum, cp) => sum + (cp.questionsInBatch?.filter(q => q.wasCorrect).length || 0), 0
  );

  // Determine result
  const result = determineResult(allIssues, evaluations, questionAudit);

  const report = {
    personaId,
    personaName: evaluations[0]?.personaId ? `Persona ${personaId}` : personaId,
    startTime: checkpoints[0]?.timestamp || 0,
    endTime: checkpoints[checkpoints.length - 1]?.timestamp || 0,
    totalQuestions,
    correctCount,
    checkpoints,
    evaluations,
    experienceSummary,
    questionAudit,
    corrections,
    issuesFound: allIssues,
    result: result.verdict,
    resultReasoning: result.reasoning,
  };

  // Write JSON report
  const jsonPath = join(reportsDir, `${personaId}-report.json`);
  writeFileSync(jsonPath, JSON.stringify(report, null, 2));

  // Write Markdown report
  const mdPath = join(reportsDir, `${personaId}-report.md`);
  writeFileSync(mdPath, generateMarkdownReport(report));

  return report;
}

/**
 * Read all files matching a pattern for a persona.
 *
 * @param {string} dir - Directory to search
 * @param {string} personaId - Persona ID prefix
 * @param {string} type - File type ("checkpoint" or "eval")
 * @returns {object[]} Parsed JSON objects sorted by checkpoint number
 */
function readPersonaFiles(dir, personaId, type) {
  if (!existsSync(dir)) return [];

  const pattern = `${personaId}-${type}-`;
  const files = readdirSync(dir)
    .filter(f => f.startsWith(pattern) && f.endsWith('.json'))
    .sort((a, b) => {
      const numA = parseInt(a.match(/(\d+)\.json$/)?.[1] || '0', 10);
      const numB = parseInt(b.match(/(\d+)\.json$/)?.[1] || '0', 10);
      return numA - numB;
    });

  return files.map(f => {
    try {
      return JSON.parse(readFileSync(join(dir, f), 'utf-8'));
    } catch {
      return null;
    }
  }).filter(Boolean);
}

/**
 * Determine PASS/FAIL/AMBIGUOUS based on spec criteria.
 *
 * PASS: All checkpoints met expectations. No blocker/major issues.
 *       Positive experience. <=10% low-quality questions.
 * FAIL: Any blocker issue. Negative experience. >25% problematic questions.
 * AMBIGUOUS: Only minor/cosmetic issues but mixed feelings.
 *
 * @param {object[]} issues - All issues found
 * @param {object[]} evaluations - All evaluations
 * @param {object[]} questionAudit - All question evaluations
 * @returns {{ verdict: string, reasoning: string }}
 */
function determineResult(issues, evaluations, questionAudit) {
  const reasons = [];

  // Check for blocker issues
  const blockers = issues.filter(i => i.severity === 'blocker');
  if (blockers.length > 0) {
    return {
      verdict: 'FAIL',
      reasoning: `${blockers.length} blocker issue(s): ${blockers.map(b => b.title).join('; ')}`,
    };
  }

  // Check for major issues
  const majors = issues.filter(i => i.severity === 'major');
  if (majors.length > 0) {
    reasons.push(`${majors.length} major issue(s)`);
  }

  // Check experience sentiment
  const sentiments = evaluations.map(e => e.overallSentiment).filter(Boolean);
  const negativeCount = sentiments.filter(s => s === 'negative' || s === 'confused').length;
  const positiveCount = sentiments.filter(s => s === 'positive').length;

  if (negativeCount > sentiments.length / 2) {
    return {
      verdict: 'FAIL',
      reasoning: `Predominantly negative experience: ${negativeCount}/${sentiments.length} checkpoints negative/confused. ${reasons.join('. ')}`,
    };
  }

  // Check question quality
  const totalQs = questionAudit.length;
  if (totalQs > 0) {
    const lowQuality = questionAudit.filter(q => {
      const avgRating = (
        (q.contentValidity || 3) +
        (q.distractorQuality || 3) +
        (q.clarityRating || 3) +
        (q.educationalValue || 3)
      ) / 4;
      return avgRating < 2.5;
    });

    const pctLow = lowQuality.length / totalQs;
    if (pctLow > 0.25) {
      return {
        verdict: 'FAIL',
        reasoning: `${(pctLow * 100).toFixed(0)}% low-quality questions (>${25}% threshold). ${reasons.join('. ')}`,
      };
    }
    if (pctLow > 0.10) {
      reasons.push(`${(pctLow * 100).toFixed(0)}% low-quality questions (>10% threshold)`);
    }

    // Check incorrect answers
    const incorrect = questionAudit.filter(q => q.isCorrectAsMarked === false);
    if (incorrect.length > 0) {
      reasons.push(`${incorrect.length} question(s) flagged as incorrectly marked`);
    }
  }

  // Determine final verdict
  if (majors.length === 0 && reasons.length === 0 && positiveCount >= sentiments.length / 2) {
    return {
      verdict: 'PASS',
      reasoning: `All checkpoints positive. No major issues. ${totalQs} questions evaluated.`,
    };
  }

  if (reasons.length > 0 || negativeCount > 0) {
    return {
      verdict: 'AMBIGUOUS',
      reasoning: `Mixed results requiring human review. ${reasons.join('. ')}`,
    };
  }

  return {
    verdict: 'PASS',
    reasoning: `No issues found. ${totalQs} questions evaluated with acceptable quality.`,
  };
}

/**
 * Generate a human-readable Markdown report.
 *
 * @param {object} report - PersonaReport object
 * @returns {string} Markdown content
 */
function generateMarkdownReport(report) {
  const resultEmoji = { PASS: '✅', FAIL: '❌', AMBIGUOUS: '⚠️' };
  const emoji = resultEmoji[report.result] || '❓';

  let md = `# Persona Report: ${report.personaName} (${report.personaId})

**Result**: ${emoji} ${report.result}
**Reasoning**: ${report.resultReasoning}

## Summary

| Metric | Value |
|--------|-------|
| Total questions | ${report.totalQuestions} |
| Correct answers | ${report.correctCount} (${report.totalQuestions > 0 ? ((report.correctCount / report.totalQuestions) * 100).toFixed(0) : 0}%) |
| Checkpoints | ${report.checkpoints.length} |
| Issues found | ${report.issuesFound.length} |
| Questions audited | ${report.questionAudit.length} |

## Experience Summary

${report.experienceSummary || '*No narrative available.*'}

`;

  // Issues section
  if (report.issuesFound.length > 0) {
    md += `## Issues Found

| # | Severity | Category | Title |
|---|----------|----------|-------|
`;
    for (const issue of report.issuesFound) {
      md += `| ${issue.id} | ${issue.severity} | ${issue.category} | ${issue.title} |\n`;
    }
    md += '\n';

    for (const issue of report.issuesFound) {
      md += `### ${issue.id}: ${issue.title}

- **Severity**: ${issue.severity}
- **Category**: ${issue.category}
- **Expected**: ${issue.expectedBehavior || 'N/A'}
- **Actual**: ${issue.actualBehavior || 'N/A'}
- **Recommendation**: ${issue.recommendation || 'N/A'}

${issue.description || ''}

`;
    }
  }

  // Question audit section
  if (report.questionAudit.length > 0) {
    const flagged = report.questionAudit.filter(q => !q.isCorrectAsMarked);
    if (flagged.length > 0) {
      md += `## Flagged Questions (${flagged.length})

| Question | Marked | Agent Says | Verdict |
|----------|--------|------------|---------|
`;
      for (const q of flagged) {
        const verdict = q.webVerification?.verdict || 'NOT_VERIFIED';
        md += `| ${q.questionText?.substring(0, 50)}... | ${q.markedAnswer} | ${q.agentAssessment} | ${verdict} |\n`;
      }
      md += '\n';
    }

    // Quality distribution
    const ratings = report.questionAudit.map(q => ({
      validity: q.contentValidity || 0,
      distractors: q.distractorQuality || 0,
      difficulty: q.difficultyRating || 0,
      educational: q.educationalValue || 0,
      clarity: q.clarityRating || 0,
    }));

    if (ratings.length > 0) {
      const avg = (arr) => (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1);
      md += `## Question Quality Summary

| Dimension | Average (1-5) |
|-----------|--------------|
| Content Validity | ${avg(ratings.map(r => r.validity))} |
| Distractor Quality | ${avg(ratings.map(r => r.distractors))} |
| Difficulty Rating | ${avg(ratings.map(r => r.difficulty))} |
| Educational Value | ${avg(ratings.map(r => r.educational))} |
| Clarity | ${avg(ratings.map(r => r.clarity))} |

`;
    }
  }

  // Corrections section (pedant only)
  if (report.corrections && report.corrections.length > 0) {
    md += `## Verified Corrections (${report.corrections.length})

| Question | Current | Corrected | Source |
|----------|---------|-----------|--------|
`;
    for (const c of report.corrections) {
      md += `| ${c.questionText?.substring(0, 40)}... | ${c.currentAnswer} | ${c.correctedAnswer} | [source](${c.sourceUrl}) |\n`;
    }
    md += '\n';
  }

  md += `---
*Report generated at ${new Date().toISOString()}*\n`;

  return md;
}

/**
 * Compile an aggregate report across all persona simulations.
 *
 * @param {string} [reportsDir] - Directory containing individual reports
 * @returns {object} Aggregate report summary
 */
export function compileAggregateReport(reportsDir) {
  const dir = reportsDir || resolve('tests/visual/reports');
  if (!existsSync(dir)) return { personas: [], passRate: 0, summary: 'No reports found.' };

  const reportFiles = readdirSync(dir)
    .filter(f => f.match(/^P\d+-report\.json$/))
    .sort();

  const personas = [];
  let passCount = 0;
  let totalIssues = 0;
  let totalFlagged = 0;

  for (const file of reportFiles) {
    try {
      const report = JSON.parse(readFileSync(join(dir, file), 'utf-8'));
      const issuesBySeverity = {};
      for (const issue of report.issuesFound || []) {
        issuesBySeverity[issue.severity] = (issuesBySeverity[issue.severity] || 0) + 1;
      }

      const flaggedQuestions = (report.questionAudit || []).filter(q => !q.isCorrectAsMarked).length;

      personas.push({
        personaId: report.personaId,
        personaName: report.personaName,
        result: report.result,
        totalQuestions: report.totalQuestions,
        correctCount: report.correctCount,
        issueCount: (report.issuesFound || []).length,
        issuesBySeverity,
        flaggedQuestions,
      });

      if (report.result === 'PASS') passCount++;
      totalIssues += (report.issuesFound || []).length;
      totalFlagged += flaggedQuestions;
    } catch { /* skip corrupt files */ }
  }

  const passRate = personas.length > 0 ? (passCount / personas.length) * 100 : 0;

  const aggregate = {
    totalPersonas: personas.length,
    passCount,
    failCount: personas.filter(p => p.result === 'FAIL').length,
    ambiguousCount: personas.filter(p => p.result === 'AMBIGUOUS').length,
    passRate,
    totalIssues,
    totalFlaggedQuestions: totalFlagged,
    personas,
    meetsTarget: passRate >= 90, // SC-010 target
  };

  // Write aggregate markdown
  let md = `# Aggregate Persona Testing Report

**Date**: ${new Date().toISOString()}
**Pass Rate**: ${passRate.toFixed(0)}% (${passCount}/${personas.length})
**Target**: 90% (SC-010) — ${aggregate.meetsTarget ? '✅ MET' : '❌ NOT MET'}

## Summary

| Persona | Result | Questions | Correct | Issues | Flagged Qs |
|---------|--------|-----------|---------|--------|------------|
`;
  for (const p of personas) {
    const emoji = { PASS: '✅', FAIL: '❌', AMBIGUOUS: '⚠️' }[p.result] || '?';
    const pct = p.totalQuestions > 0 ? ((p.correctCount / p.totalQuestions) * 100).toFixed(0) : 0;
    md += `| ${p.personaName} (${p.personaId}) | ${emoji} ${p.result} | ${p.totalQuestions} | ${p.correctCount} (${pct}%) | ${p.issueCount} | ${p.flaggedQuestions} |\n`;
  }

  md += `
## Totals

- **Total issues**: ${totalIssues}
- **Total flagged questions**: ${totalFlagged}
- **Pass rate**: ${passRate.toFixed(0)}%

---
*Aggregate report generated at ${new Date().toISOString()}*\n`;

  writeFileSync(join(dir, 'aggregate-report.md'), md);

  return aggregate;
}
