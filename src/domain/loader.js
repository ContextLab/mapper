/** Async domain data loading with progress callbacks. */

import { $domainCache } from '../state/store.js';

const PROGRESS_THROTTLE_MS = 100;

/**
 * Load a domain bundle, with caching and streaming progress.
 * @param {string} domainId
 * @param {{ onProgress?, onComplete?, onError? }} [callbacks={}]
 * @param {string} [basePath] - Defaults to import.meta.env.BASE_URL || '/mapper/'
 * @returns {Promise<object>} The domain bundle.
 */
export async function load(domainId, callbacks = {}, basePath) {
  const { onProgress, onComplete, onError } = callbacks;
  const base = basePath ?? (import.meta.env.BASE_URL || '/mapper/');

  // Return from cache if available
  const cached = $domainCache.get().get(domainId);
  if (cached) {
    onProgress?.({ loaded: 1, total: 1, percent: 100 });
    onComplete?.(cached);
    return cached;
  }

  try {
    const url = `${base}data/domains/${domainId}.json`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Failed to fetch domain ${domainId}: ${res.status} ${res.statusText}`);
    }

    let bundle;
    const contentLength = res.headers.get('Content-Length');
    const total = contentLength ? parseInt(contentLength, 10) : 0;

    if (total > 0 && res.body) {
      bundle = await readWithProgress(res.body, total, onProgress);
    } else {
      onProgress?.({ loaded: 0, total: 0, percent: 0 });
      bundle = await res.json();
      onProgress?.({ loaded: 1, total: 1, percent: 100 });
    }

    // Cache the result
    const next = new Map($domainCache.get());
    next.set(domainId, bundle);
    $domainCache.set(next);

    onComplete?.(bundle);
    return bundle;
  } catch (err) {
    onError?.(err);
    throw err;
  }
}

/** @param {ReadableStream} body */
async function readWithProgress(body, total, onProgress) {
  const reader = body.getReader();
  const chunks = [];
  let loaded = 0;
  let lastEmit = 0;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;

    chunks.push(value);
    loaded += value.byteLength;

    const now = performance.now();
    if (now - lastEmit >= PROGRESS_THROTTLE_MS) {
      lastEmit = now;
      onProgress?.({ loaded, total, percent: Math.round((loaded / total) * 100) });
    }
  }

  // Final progress
  onProgress?.({ loaded, total, percent: 100 });

  // Decode and parse
  const merged = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return JSON.parse(new TextDecoder().decode(merged));
}
