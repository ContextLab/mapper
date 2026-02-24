/**
 * Background video data loader with priority interruption.
 *
 * Loads per-domain video JSON files during the welcome screen.
 * Supports reprioritization when the user switches domains.
 *
 * See FR-V041, CL-010.
 */

const videoCache = new Map();
const pendingLoads = new Map();
let loadQueue = [];
let isProcessing = false;

/**
 * Get the base URL for data fetching (matches domain/loader.js convention).
 */
function getBaseUrl() {
  return import.meta.env.BASE_URL || '/mapper/';
}

/**
 * Start background-loading video files for the given domain IDs.
 * Prioritizes the first domain in the list (usually the active one).
 *
 * @param {string[]} domainIds - Domain IDs to load video data for
 */
export function startBackgroundLoad(domainIds) {
  loadQueue = domainIds.filter((id) => !videoCache.has(id) && !pendingLoads.has(id));
  if (loadQueue.length > 0 && !isProcessing) {
    processQueue();
  }
}

/**
 * Reprioritize: move the given domain to the front of the load queue.
 * Does not cancel in-flight requests, but ensures this domain loads next.
 *
 * @param {string} domainId - Domain to prioritize
 */
export function reprioritize(domainId) {
  if (videoCache.has(domainId) || pendingLoads.has(domainId)) return;

  const idx = loadQueue.indexOf(domainId);
  if (idx > 0) {
    loadQueue.splice(idx, 1);
    loadQueue.unshift(domainId);
  } else if (idx === -1) {
    loadQueue.unshift(domainId);
    if (!isProcessing) processQueue();
  }
}

/**
 * Get cached video data for a domain, or null if not yet loaded.
 * Returns a Promise that resolves when the data is available.
 *
 * @param {string} domainId
 * @returns {{ data: Array|null, promise: Promise<Array> }}
 */
export function getVideos(domainId) {
  const cached = videoCache.get(domainId);
  if (cached) {
    return { data: cached, promise: Promise.resolve(cached) };
  }

  // If already loading, return the pending promise
  const pending = pendingLoads.get(domainId);
  if (pending) {
    return { data: null, promise: pending };
  }

  // Not queued — start loading immediately
  const promise = loadDomain(domainId);
  return { data: null, promise };
}

/**
 * Check if video data for a domain is already loaded.
 *
 * @param {string} domainId
 * @returns {boolean}
 */
export function isLoaded(domainId) {
  return videoCache.has(domainId);
}

// ─── Internal ───────────────────────────────────────────────

async function processQueue() {
  isProcessing = true;

  while (loadQueue.length > 0) {
    const domainId = loadQueue.shift();
    if (videoCache.has(domainId)) continue;

    try {
      await loadDomain(domainId);
    } catch (err) {
      console.warn(`[video-loader] Failed to load videos for ${domainId}:`, err.message);
    }
  }

  isProcessing = false;
}

async function loadDomain(domainId) {
  if (videoCache.has(domainId)) return videoCache.get(domainId);

  const existing = pendingLoads.get(domainId);
  if (existing) return existing;

  const promise = fetchVideos(domainId);
  pendingLoads.set(domainId, promise);

  try {
    const data = await promise;
    videoCache.set(domainId, data);
    return data;
  } finally {
    pendingLoads.delete(domainId);
  }
}

async function fetchVideos(domainId) {
  const base = getBaseUrl();
  const url = `${base}data/videos/${domainId}.json`;
  const res = await fetch(url);

  if (!res.ok) {
    if (res.status === 404) {
      // No video file for this domain — cache empty array
      const empty = [];
      videoCache.set(domainId, empty);
      return empty;
    }
    throw new Error(`Video fetch failed for ${domainId}: ${res.status}`);
  }

  return res.json();
}
