/** Domain hierarchy initialization and lookup. */

let domains = null;
let idMap = null;
let childrenMap = null;

function assertInitialized() {
  if (!domains) {
    throw new Error('Registry not initialized. Call init() first.');
  }
}

/**
 * Fetch and parse data/domains/index.json, build lookup maps.
 * @param {string} [basePath] - Base URL path. Defaults to import.meta.env.BASE_URL or '/mapper/'.
 */
export async function init(basePath) {
  const base = basePath ?? (import.meta.env.BASE_URL || '/mapper/');
  const url = `${base}data/domains/index.json`;

  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch domain index: ${res.status} ${res.statusText}`);
  }

  const json = await res.json();
  domains = json.domains;

  if (import.meta.env.DEV && domains.length !== 50) {
    console.warn(
      `[registry] Expected 50 domains, got ${domains.length}`
    );
  }

  // Build id → domain lookup
  idMap = new Map();
  for (const d of domains) {
    idMap.set(d.id, d);
  }

  // Build parentId → children lookup
  childrenMap = new Map();
  for (const d of domains) {
    if (d.parent_id != null) {
      const siblings = childrenMap.get(d.parent_id) || [];
      siblings.push(d);
      childrenMap.set(d.parent_id, siblings);
    }
  }
}

/**
 * Returns flat array of all domains.
 * @returns {Array} All domain objects.
 */
export function getDomains() {
  assertInitialized();
  return domains;
}

/**
 * Returns a single domain by id.
 * @param {string} id - Domain id.
 * @returns {object|undefined} The domain object.
 */
export function getDomain(id) {
  assertInitialized();
  return idMap.get(id);
}

/**
 * Returns array of child domains for a given parent id.
 * @param {string} parentId - Parent domain id.
 * @returns {Array} Child domain objects (empty array if none).
 */
export function getChildren(parentId) {
  assertInitialized();
  return childrenMap.get(parentId) || [];
}

/**
 * Returns tree structure: array of top-level nodes, each with a `children` array.
 * "all" domain first, then general domains each with their sub-domain children.
 * @returns {Array} Hierarchy tree nodes.
 */
export function getHierarchy() {
  assertInitialized();

  const result = [];

  // "all" domain first
  const allDomain = idMap.get('all');
  if (allDomain) {
    result.push({ ...allDomain, children: [] });
  }

  // General domains (parent_id is null, but not "all") with their children
  for (const d of domains) {
    if (d.parent_id === null && d.id !== 'all') {
      result.push({
        ...d,
        children: getChildren(d.id),
      });
    }
  }

  return result;
}
