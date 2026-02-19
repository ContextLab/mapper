# Contract: State Management + Persistence

**Library**: Nano Stores (~286 bytes)
**Consumer**: All `src/` modules
**Provider**: `src/state/store.js`, `src/state/persistence.js`

## Store Atoms

```typescript
// src/state/store.js
import { atom, computed } from 'nanostores';
import { persistentAtom } from '@nanostores/persistent';

// === Persisted atoms (localStorage via FR-007) ===

// Schema version for migration detection
const SCHEMA_VERSION = "1.0.0";

// All user responses across all domains (append-only)
export const $responses = persistentAtom<UserResponse[]>(
  'mapper:responses',
  [],
  { encode: JSON.stringify, decode: JSON.parse }
);

// Schema version tag
export const $schemaVersion = persistentAtom<string>(
  'mapper:schema',
  SCHEMA_VERSION
);

// === Session atoms (in-memory only) ===

// Currently active domain ID (null = no domain selected)
export const $activeDomain = atom<string | null>(null);

// Loaded domain bundles (cache to avoid re-fetching)
export const $domainCache = atom<Map<string, DomainBundle>>(new Map());

// Current knowledge estimates for active domain
export const $estimates = atom<CellEstimate[]>([]);

// Animation/transition state
export const $transitionState = atom<"idle" | "animating">("idle");

// Current question mode
export const $questionMode = atom<"auto" | "easy" | "hardest-can-answer" | "dont-know">("auto");

// === Computed atoms ===

// Set of answered question IDs (derived from $responses)
export const $answeredIds = computed($responses, (responses) =>
  new Set(responses.map(r => r.question_id))
);

// Coverage percentage for active domain
export const $coverage = computed([$estimates], ([estimates]) => {
  if (estimates.length === 0) return 0;
  const withEvidence = estimates.filter(e => e.evidenceCount > 0);
  return withEvidence.length / estimates.length;
});

// Whether insights are available (>= 10 responses)
export const $insightsAvailable = computed($responses, (responses) =>
  responses.length >= 10
);
```

## Persistence Contract

```typescript
// src/state/persistence.js

interface Persistence {
  // Check schema version on app start
  // Returns true if data is compatible, false if discarded
  validateSchema(): boolean;

  // Export all responses as downloadable JSON (FR-022)
  exportResponses(): Blob;

  // Reset all persisted state (FR-021)
  // Clears localStorage, resets all atoms to defaults
  resetAll(): void;

  // Check if localStorage is available
  // Returns false in private browsing / disabled scenarios
  isAvailable(): boolean;
}
```

**Version migration contract (FR-007)**:
```javascript
function validateSchema() {
  const stored = $schemaVersion.get();
  if (stored !== SCHEMA_VERSION) {
    // Incompatible version — discard and notify
    $responses.set([]);
    $schemaVersion.set(SCHEMA_VERSION);
    return false; // Caller shows "progress could not be restored" notice
  }
  return true;
}
```

**Export contract (FR-022)**:
```javascript
function exportResponses() {
  const data = {
    exported_at: new Date().toISOString(),
    schema_version: SCHEMA_VERSION,
    responses: $responses.get().map(r => ({
      question_id: r.question_id,
      domain_id: r.domain_id,
      selected: r.selected,
      is_correct: r.is_correct,
      timestamp: r.timestamp
    }))
  };
  return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
}
```

## Subscription Pattern

Modules subscribe to atoms for reactivity:

```javascript
// Example: src/viz/renderer.js subscribing to estimate changes
import { $estimates, $activeDomain } from '../state/store.js';

$estimates.subscribe(estimates => {
  renderer.setHeatmap(estimates, currentRegion);
});

$activeDomain.subscribe(async domainId => {
  if (!domainId) return;
  const bundle = await loader.load(domainId);
  renderer.setPoints(bundle.articles);
  renderer.setLabels(bundle.labels);
});
```

## Atom Ownership

| Atom | Owner Module | Mutated By |
|------|-------------|------------|
| `$responses` | `state/store` | `ui/quiz.js` (on answer) |
| `$schemaVersion` | `state/persistence` | `state/persistence.js` (on validate) |
| `$activeDomain` | `state/store` | `ui/controls.js`, `viz/minimap.js` |
| `$domainCache` | `state/store` | `domain/loader.js` |
| `$estimates` | `state/store` | `learning/estimator.js` |
| `$transitionState` | `state/store` | `viz/transitions.js` |
| `$questionMode` | `state/store` | `ui/modes.js` |
