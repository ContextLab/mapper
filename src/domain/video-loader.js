/**
 * Video catalog loader.
 *
 * Loads a single catalog.json containing all videos with their
 * embedding coordinates. No per-domain splitting — the recommendation
 * engine scores videos spatially using window coordinates.
 *
 * See FR-V041, CL-010.
 */

let catalog = null;
let loadPromise = null;

/**
 * Get the base URL for data fetching (matches domain/loader.js convention).
 */
function getBaseUrl() {
  return import.meta.env.BASE_URL || '/mapper/';
}

/**
 * Start background-loading the video catalog.
 * Safe to call multiple times — only fetches once.
 */
export function startBackgroundLoad() {
  if (!loadPromise) {
    loadPromise = fetchCatalog();
  }
}

/**
 * Get the video catalog. Returns immediately if cached,
 * otherwise returns a promise that resolves when loaded.
 *
 * @returns {{ data: Array|null, promise: Promise<Array> }}
 */
export function getVideos() {
  if (catalog) {
    return { data: catalog, promise: Promise.resolve(catalog) };
  }

  if (!loadPromise) {
    loadPromise = fetchCatalog();
  }

  return { data: null, promise: loadPromise };
}

/**
 * Check if the video catalog is loaded.
 *
 * @returns {boolean}
 */
export function isLoaded() {
  return catalog !== null;
}

/**
 * Reprioritize — no-op now that we load a single file.
 * Kept for API compatibility with app.js.
 */
export function reprioritize() {}

// ─── Internal ───────────────────────────────────────────────

async function fetchCatalog() {
  try {
    const base = getBaseUrl();
    const url = `${base}data/videos/catalog.json`;
    const res = await fetch(url);

    if (!res.ok) {
      if (res.status === 404) {
        catalog = [];
        return catalog;
      }
      throw new Error(`Video catalog fetch failed: ${res.status}`);
    }

    catalog = await res.json();
    return catalog;
  } catch (err) {
    console.warn('[video-loader] Failed to load video catalog:', err.message);
    catalog = [];
    return catalog;
  }
}
