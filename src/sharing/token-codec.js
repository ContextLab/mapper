/** Encode/decode response tokens using sparse binary format + pako deflate + base64url. */

import { deflate, inflate } from 'pako';

/** Response value encoding per contracts/token-format.md */
const VALUE_CORRECT = 2;
const VALUE_SKIPPED = 1;
const VALUE_INCORRECT = 0xFF; // -1 as uint8

/**
 * Map a response object to its encoded value byte.
 * @param {Object} response - { is_correct, is_skipped }
 * @returns {number} encoded value (1, 2, or 0xFF)
 */
function responseToValue(response) {
  if (response.is_skipped) return VALUE_SKIPPED;
  if (response.is_correct) return VALUE_CORRECT;
  return VALUE_INCORRECT;
}

/**
 * Map an encoded value byte back to response flags.
 * @param {number} value
 * @returns {{ is_correct: boolean, is_skipped: boolean }}
 */
function valueToResponse(value) {
  if (value === VALUE_CORRECT) return { is_correct: true, is_skipped: false };
  if (value === VALUE_SKIPPED) return { is_correct: false, is_skipped: true };
  return { is_correct: false, is_skipped: false }; // incorrect (0xFF or any other)
}

/**
 * Encode base64url from Uint8Array (RFC 4648 §5).
 * @param {Uint8Array} bytes
 * @returns {string}
 */
function toBase64url(bytes) {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Decode base64url string to Uint8Array.
 * @param {string} str
 * @returns {Uint8Array}
 */
function fromBase64url(str) {
  let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
  // Re-pad to multiple of 4
  while (base64.length % 4 !== 0) base64 += '=';
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Encode user responses into a compressed, URL-safe token string.
 * @param {Array} responses - Array of { question_id, is_correct, is_skipped }
 * @param {{ version: number, toIndex: Map<string, number> }} questionIndex
 * @returns {string} base64url-encoded compressed token
 */
export function encodeToken(responses, questionIndex) {
  // Filter to responses that exist in the index
  const pairs = [];
  for (const r of responses) {
    const idx = questionIndex.toIndex.get(r.question_id);
    if (idx !== undefined) {
      pairs.push({ index: idx, value: responseToValue(r) });
    }
  }

  // Sort by index for better compression
  pairs.sort((a, b) => a.index - b.index);

  // Binary format: [version:1][count:2][index:2,value:1]×count
  const count = pairs.length;
  const bufLen = 3 + count * 3;
  const buf = new Uint8Array(bufLen);
  const view = new DataView(buf.buffer);

  buf[0] = questionIndex.version;
  view.setUint16(1, count, false); // big-endian

  for (let i = 0; i < count; i++) {
    const offset = 3 + i * 3;
    view.setUint16(offset, pairs[i].index, false); // big-endian
    buf[offset + 2] = pairs[i].value;
  }

  // Compress with raw deflate
  const compressed = deflate(buf, { raw: true });

  return toBase64url(compressed);
}

/**
 * Decode a base64url token string back into response entries.
 * @param {string} base64urlString
 * @param {{ version: number, toId: Map<number, string> }} questionIndex
 * @returns {Array<{ question_id: string, is_correct: boolean, is_skipped: boolean }>|null}
 */
export function decodeToken(base64urlString, questionIndex) {
  try {
    const compressed = fromBase64url(base64urlString);
    const buf = inflate(compressed, { raw: true });

    if (buf.length < 3) return null;

    const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
    const version = buf[0];
    const count = view.getUint16(1, false); // big-endian

    // Verify buffer has enough bytes
    if (buf.length < 3 + count * 3) return null;

    const results = [];
    for (let i = 0; i < count; i++) {
      const offset = 3 + i * 3;
      const index = view.getUint16(offset, false);
      const value = buf[offset + 2];

      const questionId = questionIndex.toId.get(index);
      if (questionId) {
        const flags = valueToResponse(value);
        results.push({
          question_id: questionId,
          ...flags,
        });
      }
      // Silently skip entries with no matching question (version mismatch / removed question)
    }

    return results;
  } catch (err) {
    console.warn('[token-codec] Failed to decode token:', err.message);
    return null;
  }
}
