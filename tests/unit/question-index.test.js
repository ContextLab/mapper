import { describe, it, expect } from 'vitest';
import { buildIndex, getIndexVersion } from '../../src/sharing/question-index.js';

function makeQuestion(id, domainId = 'all') {
  return { id, domain_ids: [domainId], x: 0.5, y: 0.5 };
}

describe('buildIndex', () => {
  it('assigns contiguous indices starting from 0', () => {
    const questions = [
      makeQuestion('q1', 'math'),
      makeQuestion('q2', 'math'),
      makeQuestion('q3', 'science'),
    ];
    const index = buildIndex(questions);
    expect(index.toIndex.size).toBe(3);
    expect(index.toId.size).toBe(3);
    // Indices should be 0, 1, 2
    for (let i = 0; i < 3; i++) {
      expect(index.toId.has(i)).toBe(true);
    }
  });

  it('produces deterministic ordering across calls', () => {
    const questions = [
      makeQuestion('z_last', 'alpha'),
      makeQuestion('a_first', 'beta'),
      makeQuestion('m_mid', 'alpha'),
    ];
    const index1 = buildIndex(questions);
    const index2 = buildIndex([...questions].reverse());

    // Same questions should produce same index regardless of input order
    for (const q of questions) {
      expect(index1.toIndex.get(q.id)).toBe(index2.toIndex.get(q.id));
    }
  });

  it('sorts by (domain_ids[0], id)', () => {
    const questions = [
      makeQuestion('q2', 'beta'),
      makeQuestion('q1', 'alpha'),
      makeQuestion('q3', 'alpha'),
    ];
    const index = buildIndex(questions);

    // alpha/q1 < alpha/q3 < beta/q2
    expect(index.toIndex.get('q1')).toBe(0);
    expect(index.toIndex.get('q3')).toBe(1);
    expect(index.toIndex.get('q2')).toBe(2);
  });

  it('handles questions with multiple domain_ids (uses first)', () => {
    const q1 = { id: 'multi1', domain_ids: ['beta', 'alpha'], x: 0, y: 0 };
    const q2 = { id: 'multi2', domain_ids: ['alpha', 'gamma'], x: 0, y: 0 };
    const index = buildIndex([q1, q2]);

    // q2 domain_ids[0]='alpha' < q1 domain_ids[0]='beta'
    expect(index.toIndex.get('multi2')).toBe(0);
    expect(index.toIndex.get('multi1')).toBe(1);
  });

  it('round-trips via toIndex and toId', () => {
    const questions = [
      makeQuestion('abc', 'dom1'),
      makeQuestion('def', 'dom2'),
      makeQuestion('ghi', 'dom1'),
    ];
    const index = buildIndex(questions);

    for (const q of questions) {
      const i = index.toIndex.get(q.id);
      expect(index.toId.get(i)).toBe(q.id);
    }
  });

  it('handles empty question list', () => {
    const index = buildIndex([]);
    expect(index.toIndex.size).toBe(0);
    expect(index.toId.size).toBe(0);
    expect(index.version).toBe(0);
  });

  it('handles questions with missing domain_ids', () => {
    const q1 = { id: 'no_domain', x: 0, y: 0 };
    const q2 = makeQuestion('with_domain', 'alpha');
    const index = buildIndex([q1, q2]);

    // Empty string domain sorts before 'alpha'
    expect(index.toIndex.get('no_domain')).toBe(0);
    expect(index.toIndex.get('with_domain')).toBe(1);
  });
});

describe('getIndexVersion', () => {
  it('returns count mod 256', () => {
    const questions = Array.from({ length: 300 }, (_, i) => makeQuestion(`q${i}`));
    expect(getIndexVersion(questions)).toBe(300 & 0xFF); // 44
  });

  it('returns 0 for empty list', () => {
    expect(getIndexVersion([])).toBe(0);
  });
});
