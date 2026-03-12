/** Stable question→integer index mapping for token encoding/decoding. */

/**
 * Build a deterministic question index from all loaded questions.
 * Sort by (domain_ids[0], id) to produce stable integer indices.
 * @param {Array} allQuestions - All questions from the domain bundle
 * @returns {{ version: number, toIndex: Map<string, number>, toId: Map<number, string> }}
 */
export function buildIndex(allQuestions) {
  const sorted = [...allQuestions].sort((a, b) => {
    const aDomain = (a.domain_ids && a.domain_ids[0]) || '';
    const bDomain = (b.domain_ids && b.domain_ids[0]) || '';
    if (aDomain < bDomain) return -1;
    if (aDomain > bDomain) return 1;
    if (a.id < b.id) return -1;
    if (a.id > b.id) return 1;
    return 0;
  });

  const toIndex = new Map();
  const toId = new Map();
  for (let i = 0; i < sorted.length; i++) {
    toIndex.set(sorted[i].id, i);
    toId.set(i, sorted[i].id);
  }

  // Version is derived from question count — simple but effective for detecting changes
  const version = allQuestions.length & 0xFF;

  return { version, toIndex, toId };
}

/**
 * Get the index version for the current question bank.
 * @param {Array} allQuestions
 * @returns {number}
 */
export function getIndexVersion(allQuestions) {
  return allQuestions.length & 0xFF;
}
