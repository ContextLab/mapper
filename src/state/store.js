/** Reactive state atoms for responses, schema, domains, and learning estimates. */

import { atom, computed } from 'nanostores';
import { persistentAtom } from '@nanostores/persistent';

// === Schema ===
export const SCHEMA_VERSION = '1.0.0';

// === Persisted atoms (localStorage via FR-007) ===

/** All user responses across all domains (append-only) */
export const $responses = persistentAtom('mapper:responses', [], {
  encode: JSON.stringify,
  decode: JSON.parse,
});

/** Schema version tag for migration detection */
export const $schemaVersion = persistentAtom('mapper:schema', SCHEMA_VERSION);

// === Session atoms (in-memory only) ===

/** Currently active domain ID (null = no domain selected) */
export const $activeDomain = atom(null);

/** Loaded domain bundles (cache to avoid re-fetching) */
export const $domainCache = atom(new Map());

/** Current knowledge estimates for active domain */
export const $estimates = atom([]);

/** Animation/transition state */
export const $transitionState = atom('idle');

/** Current question mode */
export const $questionMode = atom('auto');

// === Computed atoms ===

/** Set of answered question IDs (derived from $responses) */
export const $answeredIds = computed($responses, (responses) =>
  new Set(responses.map((r) => r.question_id))
);

/** Coverage percentage for active domain (uncertainty-weighted) */
export const $coverage = computed($estimates, (estimates) => {
  if (estimates.length === 0) return 0;
  let totalCoverage = 0;
  for (const e of estimates) {
    if (e.state === 'unknown') continue;
    const contrib = 1 - e.uncertainty;
    // Guard against NaN from numerical instability in GP
    if (isFinite(contrib)) totalCoverage += contrib;
  }
  const result = totalCoverage / estimates.length;
  return isFinite(result) ? result : 0;
});

/** Whether insights are available (>= 10 responses) */
export const $insightsAvailable = computed($responses, (responses) =>
  responses.length >= 10
);
