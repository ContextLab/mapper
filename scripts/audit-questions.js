import { readFileSync, readdirSync } from 'fs';
import { join, basename } from 'path';

const domainsDir = new URL('../data/domains/', import.meta.url).pathname;

// 1. Load valid domain IDs from index.json
const index = JSON.parse(readFileSync(join(domainsDir, 'index.json'), 'utf-8'));
const validDomainIds = new Set(index.domains.map(d => d.id));

// 2. Scan all *.json files excluding index.json
const files = readdirSync(domainsDir)
  .filter(f => f.endsWith('.json') && f !== 'index.json');

const issues = [];

for (const file of files) {
  const fileDomain = basename(file, '.json');
  const filePath = join(domainsDir, file);
  let data;
  try {
    data = JSON.parse(readFileSync(filePath, 'utf-8'));
  } catch (e) {
    issues.push({ file, id: '-', issue: `Failed to parse JSON: ${e.message}` });
    continue;
  }

  const questions = data.questions;
  if (!Array.isArray(questions)) {
    issues.push({ file, id: '-', issue: 'No questions array found' });
    continue;
  }

  for (const q of questions) {
    const qid = q.id || '(no id)';

    // Check domain_ids present and non-empty
    if (!Array.isArray(q.domain_ids) || q.domain_ids.length === 0) {
      issues.push({ file, id: qid, issue: 'domain_ids missing or empty' });
    } else {
      // Check for "unknown" values
      for (const did of q.domain_ids) {
        if (did === 'unknown') {
          issues.push({ file, id: qid, issue: 'domain_ids contains "unknown"' });
        }
      }
      // Check each domain_id is valid
      for (const did of q.domain_ids) {
        if (did !== 'unknown' && !validDomainIds.has(did)) {
          issues.push({ file, id: qid, issue: `domain_id "${did}" not in index.json` });
        }
      }
      // Check file domain matches at least one domain_id
      if (!q.domain_ids.includes(fileDomain)) {
        issues.push({ file, id: qid, issue: `file domain "${fileDomain}" not in domain_ids [${q.domain_ids.join(', ')}]` });
      }
    }

    // Check source_article
    if (!q.source_article || typeof q.source_article !== 'string' || q.source_article.trim() === '') {
      issues.push({ file, id: qid, issue: 'source_article missing or empty' });
    }

    // Self-answering check: correct answer text should not appear in question_text
    if (q.correct_answer && q.options && q.question_text) {
      const correctText = q.options[q.correct_answer];
      if (correctText && typeof correctText === 'string' && correctText.length > 4) {
        const qLower = q.question_text.toLowerCase();
        const aLower = correctText.toLowerCase();
        if (qLower.includes(aLower)) {
          issues.push({ file, id: qid, issue: `self-answering: correct answer "${correctText}" found in question text` });
        }
      }
    }
  }
}

// 4. Report
if (issues.length > 0) {
  for (const { file, id, issue } of issues) {
    console.log(`[${file}] ${id}: ${issue}`);
  }
}
console.log(`\nTotal issues: ${issues.length}`);
process.exit(issues.length > 0 ? 1 : 0);
