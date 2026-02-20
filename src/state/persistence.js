import {
  SCHEMA_VERSION,
  $responses,
  $schemaVersion,
  $activeDomain,
  $domainCache,
  $estimates,
  $transitionState,
  $questionMode,
} from './store.js';

export function validateSchema() {
  const stored = $schemaVersion.get();
  if (stored !== SCHEMA_VERSION) {
    $responses.set([]);
    $schemaVersion.set(SCHEMA_VERSION);
    return false;
  }
  return true;
}

export function exportResponses() {
  const data = {
    exported_at: new Date().toISOString(),
    schema_version: SCHEMA_VERSION,
    responses: $responses.get().map((r) => ({
      question_id: r.question_id,
      domain_id: r.domain_id,
      selected: r.selected,
      is_correct: r.is_correct,
      timestamp: r.timestamp,
      x: r.x,
      y: r.y,
    })),
  };
  return new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
}

export function resetAll() {
  $responses.set([]);
  $schemaVersion.set(SCHEMA_VERSION);
  $activeDomain.set(null);
  $domainCache.set(new Map());
  $estimates.set([]);
  $transitionState.set('idle');
  $questionMode.set('auto');
}

export function isAvailable() {
  try {
    const key = '__mapper_storage_test__';
    localStorage.setItem(key, '1');
    localStorage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}
