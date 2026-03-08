/**
 * Question database loader for persona testing framework.
 *
 * Reads data/domains/index.json + per-domain JSONs and builds a
 * Map<questionText, questionObj> for answer lookup during Playwright
 * automation, plus a domain-grouped index for filtered retrieval.
 *
 * Reuses the same pattern as persona-simulation.spec.js (lines 17-33)
 * but extracted as a reusable module.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Load the complete question database from disk.
 *
 * @returns {{ byText: Map<string, object>, byId: Map<string, object> }}
 *   byText: Map keyed by first 100 chars of question_text
 *   byId: Map keyed by question id
 */
export function loadQuestionDb() {
  const indexPath = resolve('data/domains/index.json');
  const indexData = JSON.parse(readFileSync(indexPath, 'utf-8'));
  const byText = new Map();
  const byId = new Map();

  for (const d of Object.values(indexData.domains)) {
    if (!d || !d.id) continue;
    try {
      const domainPath = resolve(`data/domains/${d.id}.json`);
      const domainData = JSON.parse(readFileSync(domainPath, 'utf-8'));
      const qs = domainData.questions || [];
      for (const q of qs) {
        if (q.question_text && q.id) {
          const key = q.question_text.trim().substring(0, 100);
          byText.set(key, q);
          byId.set(q.id, q);
        }
      }
    } catch { /* skip missing domain files */ }
  }

  return { byText, byId };
}

/**
 * Get all questions belonging to a specific domain.
 *
 * @param {string} domainId - Domain identifier (e.g., "physics", "biology")
 * @returns {object[]} Array of question objects for this domain
 */
export function getQuestionsForDomain(domainId) {
  const domainPath = resolve(`data/domains/${domainId}.json`);
  try {
    const data = JSON.parse(readFileSync(domainPath, 'utf-8'));
    return data.questions || [];
  } catch {
    return [];
  }
}

/**
 * Get all domain IDs from the index.
 *
 * @returns {string[]} Array of domain IDs
 */
export function getAllDomainIds() {
  const indexPath = resolve('data/domains/index.json');
  const indexData = JSON.parse(readFileSync(indexPath, 'utf-8'));
  return Object.values(indexData.domains)
    .filter(d => d && d.id)
    .map(d => d.id);
}

/**
 * Get total question count across all domains (for pedant "ALL" mode).
 *
 * @param {string} domainFilter - "all" for every domain, or a specific domain ID
 * @returns {number} Total question count
 */
export function getTotalQuestionCount(domainFilter) {
  if (domainFilter === 'all') {
    const ids = getAllDomainIds();
    return ids.reduce((sum, id) => sum + getQuestionsForDomain(id).length, 0);
  }
  return getQuestionsForDomain(domainFilter).length;
}

/**
 * Strip LaTeX markup to plain text for fuzzy matching.
 * KaTeX renders $Re$ to DOM textContent like "ReReRe" — this normalizes
 * the DB source text similarly by removing LaTeX delimiters and commands.
 */
function stripLatex(text) {
  return text
    .replace(/\$([^$]*)\$/g, '$1')         // $x$ → x
    .replace(/\\[a-zA-Z]+\{([^}]*)\}/g, '$1') // \frac{a}{b} → a}b (rough)
    .replace(/\\[a-zA-Z]+/g, '')            // \lambda → ''
    .replace(/[\\{}^_]/g, '')               // remove remaining markup chars
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Look up a question by ID from the byId index.
 *
 * @param {{ byText: Map, byId: Map }} db - The loaded question database
 * @param {string} questionId - Question ID from app state
 * @returns {object|null} Matched question object, or null
 */
export function lookupQuestionById(db, questionId) {
  return db.byId.get(questionId) || null;
}

/**
 * Look up a question by matching displayed text against the database.
 * Tries exact prefix match first, then fuzzy fallback with LaTeX normalization.
 *
 * @param {Map<string, object>} questionDb - The byText map from loadQuestionDb()
 * @param {string} displayedText - Text from the DOM .quiz-question element
 * @returns {object|null} Matched question object, or null
 */
export function lookupQuestion(questionDb, displayedText) {
  // Exact prefix match (first 100 chars)
  const key = displayedText.substring(0, 100);
  if (questionDb.has(key)) return questionDb.get(key);

  // Fuzzy fallback: find best match by prefix overlap
  let bestMatch = null;
  let bestScore = 0;
  for (const [dbKey, q] of questionDb) {
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
  if (bestScore > 20) return bestMatch;

  // LaTeX-normalized fallback: strip LaTeX from DB keys and compare
  const normDisplay = stripLatex(displayedText).substring(0, 80).toLowerCase();
  bestMatch = null;
  bestScore = 0;
  for (const [dbKey, q] of questionDb) {
    const normDb = stripLatex(dbKey).substring(0, 80).toLowerCase();
    const len = Math.min(normDb.length, normDisplay.length);
    let score = 0;
    for (let i = 0; i < len; i++) {
      if (normDb[i] === normDisplay[i]) score++;
      else break;
    }
    if (score > bestScore) {
      bestScore = score;
      bestMatch = q;
    }
  }
  return bestScore > 15 ? bestMatch : null;
}
