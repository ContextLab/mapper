/** Domain question aggregation tests (Phase 9, T-V105). */
import { describe, it, expect, beforeAll, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, '../../data/domains');

// Stub fetch to serve real domain JSON files from disk.
// This uses actual project data — no synthetic mocks.
function fileFetch(url) {
  const match = url.match(/data\/domains\/(.+\.json)$/);
  if (!match) {
    return Promise.resolve({ ok: false, status: 404, statusText: 'Not Found' });
  }
  try {
    const content = readFileSync(resolve(DATA_DIR, match[1]), 'utf-8');
    const json = JSON.parse(content);
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: { get: () => null },
      body: null,
      json: () => Promise.resolve(json),
    });
  } catch {
    return Promise.resolve({ ok: false, status: 404, statusText: 'Not Found' });
  }
}

vi.stubGlobal('fetch', fileFetch);

// Import after fetch stub is in place
const { init, getDomains, getDescendants } = await import(
  '../../src/domain/registry.js'
);
const { loadQuestionsForDomain } = await import('../../src/domain/loader.js');
const { $domainCache } = await import('../../src/state/store.js');

// ─── Setup: initialize registry with real index.json ────────────

beforeAll(async () => {
  await init('/');
});

// Clear domain cache between tests so each starts fresh
beforeEach(() => {
  $domainCache.set(new Map());
});

// ─── T-V105a: getDescendants correctness ────────────────────────

describe('getDescendants hierarchy traversal', () => {
  it('"all" domain returns every other domain ID (49)', () => {
    const descendants = getDescendants('all');
    const allDomains = getDomains();
    expect(descendants.length).toBe(allDomains.length - 1);
    expect(descendants).not.toContain('all');
  });

  it('parent "physics" returns exactly its 2 sub-domains', () => {
    const descendants = getDescendants('physics');
    expect(descendants).toHaveLength(2);
    expect(descendants).toContain('astrophysics');
    expect(descendants).toContain('quantum-physics');
  });

  it('parent "neuroscience" returns exactly its 3 sub-domains', () => {
    const descendants = getDescendants('neuroscience');
    expect(descendants).toHaveLength(3);
    expect(descendants).toContain('cognitive-neuroscience');
    expect(descendants).toContain('computational-neuroscience');
    expect(descendants).toContain('neurobiology');
  });

  it('parent "mathematics" returns exactly its 4 sub-domains', () => {
    const descendants = getDescendants('mathematics');
    expect(descendants).toHaveLength(4);
    expect(descendants).toContain('calculus');
    expect(descendants).toContain('linear-algebra');
    expect(descendants).toContain('number-theory');
    expect(descendants).toContain('probability-statistics');
  });

  it('parent "psychology" returns exactly its 4 sub-domains', () => {
    const descendants = getDescendants('psychology');
    expect(descendants).toHaveLength(4);
    expect(descendants).toContain('cognitive-psychology');
    expect(descendants).toContain('social-psychology');
    expect(descendants).toContain('developmental-psychology');
    expect(descendants).toContain('clinical-psychology');
  });

  it('leaf sub-domain "astrophysics" returns empty array', () => {
    expect(getDescendants('astrophysics')).toEqual([]);
  });

  it('leaf sub-domain "calculus" returns empty array', () => {
    expect(getDescendants('calculus')).toEqual([]);
  });

  it('getDescendants returns no duplicates for any parent', () => {
    const allDomains = getDomains();
    const parents = allDomains.filter(d => d.parent_id === null && d.id !== 'all');
    for (const parent of parents) {
      const descendants = getDescendants(parent.id);
      const unique = new Set(descendants);
      expect(unique.size).toBe(descendants.length);
    }
  });

  it('every child domain appears in exactly one parent\'s descendants', () => {
    const allDomains = getDomains();
    const parents = allDomains.filter(d => d.parent_id === null && d.id !== 'all');
    const subs = allDomains.filter(d => d.parent_id !== null);

    for (const sub of subs) {
      let foundIn = 0;
      for (const parent of parents) {
        if (getDescendants(parent.id).includes(sub.id)) foundIn++;
      }
      expect(foundIn).toBe(1);
    }
  });
});

// ─── T-V105b: loadQuestionsForDomain aggregation ────────────────

describe('loadQuestionsForDomain aggregation', () => {
  it('leaf domain returns exactly 50 questions', async () => {
    const questions = await loadQuestionsForDomain('astrophysics', '/');
    expect(questions).toHaveLength(50);
  });

  it('parent "physics" aggregates own + 2 children = 150 questions', async () => {
    const questions = await loadQuestionsForDomain('physics', '/');
    expect(questions).toHaveLength(150);
  });

  it('parent "neuroscience" aggregates own + 3 children = 200 questions', async () => {
    const questions = await loadQuestionsForDomain('neuroscience', '/');
    expect(questions).toHaveLength(200);
  });

  it('parent "mathematics" aggregates own + 4 children = 250 questions', async () => {
    const questions = await loadQuestionsForDomain('mathematics', '/');
    expect(questions).toHaveLength(250);
  });

  it('"all" domain aggregates all 50 domains × 50 = 2500 questions', async () => {
    const questions = await loadQuestionsForDomain('all', '/');
    expect(questions).toHaveLength(2500);
  });

  it('all aggregated question IDs are unique (no duplicates)', async () => {
    const questions = await loadQuestionsForDomain('physics', '/');
    const ids = questions.map(q => q.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('"all" domain question IDs are globally unique', async () => {
    const questions = await loadQuestionsForDomain('all', '/');
    const ids = questions.map(q => q.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('every question has required fields', async () => {
    const questions = await loadQuestionsForDomain('physics', '/');
    for (const q of questions) {
      expect(q).toHaveProperty('id');
      expect(q).toHaveProperty('question_text');
      expect(q).toHaveProperty('options');
      expect(q).toHaveProperty('correct_answer');
      expect(q).toHaveProperty('difficulty');
    }
  });

  it('parent questions appear before child questions (insertion order)', async () => {
    const questions = await loadQuestionsForDomain('physics', '/');
    // First 50 should be physics's own questions
    const physicsBundle = await (await fetch('/data/domains/physics.json')).json();
    const firstParentId = physicsBundle.questions[0].id;
    expect(questions[0].id).toBe(firstParentId);
  });
});

// ─── T-V105c: caching behavior ──────────────────────────────────

describe('domain cache integration', () => {
  it('second load of same domain uses cache (no duplicate fetch)', async () => {
    const fetchSpy = vi.fn(fileFetch);
    vi.stubGlobal('fetch', fetchSpy);

    await loadQuestionsForDomain('astrophysics', '/');
    const callCount1 = fetchSpy.mock.calls.length;

    // Load again — should hit cache, no new fetches
    await loadQuestionsForDomain('astrophysics', '/');
    const callCount2 = fetchSpy.mock.calls.length;

    expect(callCount2).toBe(callCount1);

    // Restore original stub
    vi.stubGlobal('fetch', fileFetch);
  });

  it('parent load caches all children for subsequent individual loads', async () => {
    const fetchSpy = vi.fn(fileFetch);
    vi.stubGlobal('fetch', fetchSpy);

    // Load physics (fetches physics + astrophysics + quantum-physics)
    await loadQuestionsForDomain('physics', '/');
    const callsAfterParent = fetchSpy.mock.calls.length;
    expect(callsAfterParent).toBe(3);

    // Now load astrophysics alone — should be cached, zero new fetches
    await loadQuestionsForDomain('astrophysics', '/');
    expect(fetchSpy.mock.calls.length).toBe(callsAfterParent);

    vi.stubGlobal('fetch', fileFetch);
  });
});

// ─── T-V105d: performance ───────────────────────────────────────

describe('aggregation performance', () => {
  it('"all" domain aggregation completes in < 500ms', async () => {
    const start = performance.now();
    await loadQuestionsForDomain('all', '/');
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(500);
  });

  it('parent domain aggregation completes in < 100ms', async () => {
    const start = performance.now();
    await loadQuestionsForDomain('physics', '/');
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(100);
  });
});
