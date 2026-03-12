import { describe, it, expect } from 'vitest';
import { encodeToken, decodeToken } from '../../src/sharing/token-codec.js';
import { buildIndex } from '../../src/sharing/question-index.js';

function makeQuestions(n) {
  return Array.from({ length: n }, (_, i) => ({
    id: `q${String(i).padStart(4, '0')}`,
    domain_ids: ['all'],
    x: Math.random(),
    y: Math.random(),
  }));
}

function makeResponses(questions, count) {
  const responses = [];
  for (let i = 0; i < count && i < questions.length; i++) {
    const roll = i % 3;
    responses.push({
      question_id: questions[i].id,
      is_correct: roll === 0,
      is_skipped: roll === 1,
      // roll === 2 → incorrect
    });
  }
  return responses;
}

describe('encodeToken / decodeToken round-trip', () => {
  it('round-trips 0 responses', () => {
    const questions = makeQuestions(100);
    const index = buildIndex(questions);
    const token = encodeToken([], index);
    const decoded = decodeToken(token, index);
    expect(decoded).toEqual([]);
  });

  it('round-trips 1 response', () => {
    const questions = makeQuestions(100);
    const index = buildIndex(questions);
    const responses = [{ question_id: questions[0].id, is_correct: true, is_skipped: false }];
    const token = encodeToken(responses, index);
    const decoded = decodeToken(token, index);
    expect(decoded).toHaveLength(1);
    expect(decoded[0].question_id).toBe(questions[0].id);
    expect(decoded[0].is_correct).toBe(true);
    expect(decoded[0].is_skipped).toBe(false);
  });

  it('round-trips 50 responses preserving correct/skipped/incorrect', () => {
    const questions = makeQuestions(200);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 50);
    const token = encodeToken(responses, index);
    const decoded = decodeToken(token, index);
    expect(decoded).toHaveLength(50);

    // Build lookup for comparison
    const byId = new Map(decoded.map(r => [r.question_id, r]));
    for (const orig of responses) {
      const got = byId.get(orig.question_id);
      expect(got).toBeDefined();
      expect(got.is_correct).toBe(!!orig.is_correct);
      expect(got.is_skipped).toBe(!!orig.is_skipped);
    }
  });

  it('round-trips 200 responses', () => {
    const questions = makeQuestions(500);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 200);
    const token = encodeToken(responses, index);
    const decoded = decodeToken(token, index);
    expect(decoded).toHaveLength(200);
  });

  it('round-trips 500 responses', () => {
    const questions = makeQuestions(1000);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 500);
    const token = encodeToken(responses, index);
    const decoded = decodeToken(token, index);
    expect(decoded).toHaveLength(500);
  });
});

describe('token URL safety', () => {
  it('produces only URL-safe characters', () => {
    const questions = makeQuestions(200);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 100);
    const token = encodeToken(responses, index);

    // base64url: only [A-Za-z0-9_-]
    expect(token).toMatch(/^[A-Za-z0-9_-]+$/);
  });
});

describe('token size constraints', () => {
  it('produces URL under 2000 chars for 200 responses', () => {
    const questions = makeQuestions(2500);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 200);
    const token = encodeToken(responses, index);
    const url = `https://context-lab.com/mapper/?t=${token}`;
    expect(url.length).toBeLessThan(2000);
  });
});

describe('invalid input handling', () => {
  it('returns null for garbage string', () => {
    const questions = makeQuestions(10);
    const index = buildIndex(questions);
    const result = decodeToken('INVALID_GARBAGE_STRING!!!', index);
    expect(result).toBeNull();
  });

  it('returns null for empty string', () => {
    const questions = makeQuestions(10);
    const index = buildIndex(questions);
    const result = decodeToken('', index);
    expect(result).toBeNull();
  });

  it('returns null for truncated token', () => {
    const questions = makeQuestions(100);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 50);
    const token = encodeToken(responses, index);
    // Truncate to half
    const truncated = token.substring(0, Math.floor(token.length / 2));
    const result = decodeToken(truncated, index);
    expect(result).toBeNull();
  });

  it('skips unknown question indices gracefully', () => {
    const questions = makeQuestions(100);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 20);
    const token = encodeToken(responses, index);

    // Decode with a smaller index (simulating removed questions)
    const smallerQuestions = questions.slice(0, 10);
    const smallerIndex = buildIndex(smallerQuestions);
    const decoded = decodeToken(token, smallerIndex);

    // Should decode some entries, skip unknown ones
    expect(decoded).not.toBeNull();
    expect(decoded.length).toBeLessThanOrEqual(20);
    // All decoded entries should have valid question_ids
    for (const entry of decoded) {
      expect(smallerIndex.toIndex.has(entry.question_id)).toBe(true);
    }
  });
});

describe('token versioning (forward compatibility)', () => {
  it('decodes old token with new index (added questions)', () => {
    const questions = makeQuestions(100);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 30);
    const token = encodeToken(responses, index);

    // Add more questions to simulate question bank update
    const newQuestions = [
      ...questions,
      ...Array.from({ length: 50 }, (_, i) => ({
        id: `new_q${i}`,
        domain_ids: ['new_domain'],
        x: Math.random(),
        y: Math.random(),
      })),
    ];
    const newIndex = buildIndex(newQuestions);
    const decoded = decodeToken(token, newIndex);

    expect(decoded).not.toBeNull();
    // Original responses should decode (indices may differ but question_ids mapped)
    expect(decoded.length).toBeGreaterThan(0);
  });

  it('decodes old token with new index (removed questions)', () => {
    const questions = makeQuestions(100);
    const index = buildIndex(questions);
    const responses = makeResponses(questions, 30);
    const token = encodeToken(responses, index);

    // Remove some questions
    const fewerQuestions = questions.slice(0, 50);
    const newIndex = buildIndex(fewerQuestions);
    const decoded = decodeToken(token, newIndex);

    expect(decoded).not.toBeNull();
    // Some responses may be lost (removed questions), rest should be valid
    for (const entry of decoded) {
      expect(newIndex.toIndex.has(entry.question_id)).toBe(true);
    }
  });
});
