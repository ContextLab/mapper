/**
 * Knowledge insights — domain-level leaderboard (trophy) and concept-level suggestions (graduation cap).
 *
 * Two layers:
 *   - Domain rankings: aggregate GP predictions at question coordinates per domain/sub-domain
 *   - Concept suggestions: fine-grained concept → coordinate mapping for learning recommendations
 *
 * The trophy button uses domain-level rankings across the full map.
 * The share modal uses domain-level top-3 for the expertise summary.
 */

let modalEl = null;

// Domain-level: domainId → { name, level, parentId, coords: [{x, y}] }
let domainCoords = new Map();

// Precomputed: concept name → array of { x, y } from source articles
let conceptCoords = new Map();

// Global: accumulated across all domain loads — for full-map leaderboard/suggestions
let globalConceptCoords = new Map();

export function init() {
  if (!document.getElementById('insights-modal-style')) {
    const style = document.createElement('style');
    style.id = 'insights-modal-style';
    style.textContent = `
      .insights-modal-content { max-width: 500px; }
      .insights-modal-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: var(--font-heading);
        font-size: 1.1rem;
        color: var(--color-primary);
        margin-bottom: 1rem;
      }
      .insights-modal-list {
        list-style: none;
        padding: 0;
        margin: 0 0 1rem;
      }
      .insights-modal-list li {
        display: flex;
        align-items: center;
        padding: 0.5rem 0;
        font-size: 0.85rem;
        border-bottom: 1px solid var(--color-border);
      }
      .insights-modal-list li:last-child { border-bottom: none; }
      .insights-rank {
        font-weight: 700;
        color: var(--color-text-muted);
        min-width: 2rem;
        flex-shrink: 0;
      }
      .insights-concept {
        flex: 1;
        margin: 0 0.5rem;
        min-width: 0;
      }
      .insights-concept a {
        color: var(--color-secondary);
        text-decoration: underline;
        text-underline-offset: 2px;
        transition: color 0.2s;
      }
      .insights-concept a:hover { color: var(--color-primary); }
      .insights-pct {
        font-weight: 600;
        min-width: 3rem;
        text-align: right;
        flex-shrink: 0;
      }
      .insights-bar-mini {
        width: 60px;
        height: 6px;
        background: var(--color-surface-raised);
        border-radius: 3px;
        overflow: hidden;
        margin-left: 0.5rem;
        flex-shrink: 0;
      }
      .insights-bar-fill-mini {
        display: block;
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
      }
      .insights-empty-msg {
        color: var(--color-text-muted);
        font-style: italic;
        text-align: center;
        padding: 2rem 0;
        font-size: 0.9rem;
      }
      .insights-explainer {
        font-size: 0.8rem;
        color: var(--color-text-muted);
        line-height: 1.5;
        margin: 0 0 1rem;
      }
      .insights-caveat {
        font-size: 0.72rem;
        color: var(--color-text-muted);
        opacity: 0.8;
        line-height: 1.4;
        margin: 0.75rem 0 0;
        padding-top: 0.75rem;
        border-top: 1px solid var(--color-border);
      }
    `;
    document.head.appendChild(style);
  }

  modalEl = document.getElementById('insights-modal');
  if (!modalEl) {
    modalEl = document.createElement('div');
    modalEl.id = 'insights-modal';
    modalEl.className = 'modal';
    modalEl.hidden = true;
    modalEl.setAttribute('role', 'dialog');
    modalEl.setAttribute('aria-modal', 'true');
    modalEl.innerHTML = `
      <div class="modal-content insights-modal-content">
        <button type="button" class="modal-close-x close-modal" aria-label="Close">&times;</button>
        <div class="insights-modal-title" id="insights-modal-title"></div>
        <div id="insights-modal-body"></div>
      </div>
    `;
    document.body.appendChild(modalEl);

    const closeBtn = modalEl.querySelector('.close-modal');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => { modalEl.hidden = true; });
    }
    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) modalEl.hidden = true;
    });
  }
}

/**
 * Precompute concept → coordinate mapping for the current domain.
 * Call once per domain switch.
 *
 * For each unique concept in concepts_tested:
 *   1. Find all questions that test it
 *   2. Get each question's source article coordinates (fall back to question coords)
 *   3. Store the list — duplicate articles get multiple entries (multiple votes)
 *
 * @param {Array} questions - Domain questions with concepts_tested, source_article, x, y
 * @param {Array} articles - Domain articles with { title, x, y }
 */
export function setConcepts(questions, articles) {
  conceptCoords = new Map();
  if (!questions) return;

  // Build article coordinate lookup
  const articleXY = new Map();
  if (articles) {
    for (const a of articles) {
      articleXY.set(a.title, { x: a.x, y: a.y });
    }
  }

  for (const q of questions) {
    if (!q.concepts_tested || !Array.isArray(q.concepts_tested)) continue;

    // Prefer source article coords, fall back to question coords
    let coords = null;
    if (q.source_article && articleXY.has(q.source_article)) {
      coords = articleXY.get(q.source_article);
    } else if (q.x != null && q.y != null) {
      coords = { x: q.x, y: q.y };
    }
    if (!coords) continue;

    for (const raw of q.concepts_tested) {
      const concept = raw.replace(/^Concept\s+\d+:\s*/i, '').trim();
      if (!concept) continue;

      // Domain-scoped map (rebuilt each switch)
      if (!conceptCoords.has(concept)) {
        conceptCoords.set(concept, []);
      }
      conceptCoords.get(concept).push(coords);

      // Global map (accumulated across all domain loads)
      if (!globalConceptCoords.has(concept)) {
        globalConceptCoords.set(concept, []);
      }
      globalConceptCoords.get(concept).push(coords);
    }
  }
}

/** Clear the global concept accumulator (call on full reset). */
export function resetGlobalConcepts() {
  globalConceptCoords = new Map();
}

/**
 * Store domain metadata (bounding boxes) from the domain index.
 * Call once after registry.init() completes.
 *
 * @param {Array} domainIndex - Array of domain objects from index.json
 */
export function setDomains(domainIndex) {
  domainCoords = new Map();
  if (!domainIndex) return;

  for (const d of domainIndex) {
    if (d.level === 'all') continue;
    if (!d.region) continue;
    domainCoords.set(d.id, {
      name: d.name,
      level: d.level,
      parentId: d.parent_id,
      region: d.region,
    });
  }
}

/** Clear domain coordinates (call on full reset). */
export function resetDomains() {
  domainCoords = new Map();
}

/**
 * Compute knowledge per domain by averaging GP grid cells that fall within
 * each domain's bounding box. Only cells with low uncertainty count.
 *
 * @param {Array} estimates - CellEstimate[] from estimator.predict()
 * @param {object} region - Global region { x_min, x_max, y_min, y_max }
 * @param {number} gridSize - Global grid dimension
 * @returns {Array<{ domainId, name, level, parentId, knowledge, count, evidencedCount, hasEvidence }>}
 */
export function computeDomainKnowledge(estimates, region, gridSize) {
  if (domainCoords.size === 0 || !estimates || estimates.length === 0 || !region) return [];

  // Build grid lookup: "gx,gy" → estimate
  const estimateMap = new Map();
  for (const e of estimates) {
    estimateMap.set(`${e.gx},${e.gy}`, e);
  }

  const cellW = (region.x_max - region.x_min) / gridSize;
  const cellH = (region.y_max - region.y_min) / gridSize;

  const UNCERTAINTY_THRESHOLD = 0.85;
  const MIN_EVIDENCE = 2;
  const results = [];

  for (const [domId, data] of domainCoords) {
    const dr = data.region;
    // Find grid cells that overlap this domain's bounding box
    const gxMin = Math.max(0, Math.floor((dr.x_min - region.x_min) / cellW));
    const gxMax = Math.min(gridSize - 1, Math.floor((dr.x_max - region.x_min) / cellW));
    const gyMin = Math.max(0, Math.floor((dr.y_min - region.y_min) / cellH));
    const gyMax = Math.min(gridSize - 1, Math.floor((dr.y_max - region.y_min) / cellH));

    let evidencedSum = 0;
    let evidencedCount = 0;
    let totalCells = 0;

    for (let gx = gxMin; gx <= gxMax; gx++) {
      for (let gy = gyMin; gy <= gyMax; gy++) {
        totalCells++;
        const cell = estimateMap.get(`${gx},${gy}`);
        if (!cell) continue;
        const u = cell.uncertainty ?? 1.0;
        if (u < UNCERTAINTY_THRESHOLD) {
          evidencedSum += isFinite(cell.value) ? cell.value : 0.5;
          evidencedCount++;
        }
      }
    }

    const hasEvidence = evidencedCount >= MIN_EVIDENCE;
    const knowledge = hasEvidence ? evidencedSum / evidencedCount : 0.5;

    results.push({
      domainId: domId,
      name: data.name,
      level: data.level,
      parentId: data.parentId,
      knowledge: isFinite(knowledge) ? knowledge : 0.5,
      count: totalCells,
      evidencedCount,
      hasEvidence,
    });
  }

  return results;
}

/**
 * Compute knowledge per concept using precomputed coordinates and current estimates.
 *
 * @param {Array} estimates - CellEstimate[] from estimator.predict()
 * @param {object} region - { x_min, x_max, y_min, y_max }
 * @param {number} gridSize - Grid dimension
 * @param {object} [opts] - Options
 * @param {boolean} [opts.global] - Use global concept map (all domains) instead of current domain
 * @returns {Array<{ concept: string, knowledge: number, count: number }>}
 */
export function computeConceptKnowledge(estimates, region, gridSize, opts = {}) {
  const coords = opts.global ? globalConceptCoords : conceptCoords;
  if (coords.size === 0 || !estimates || estimates.length === 0 || !region) return [];

  // Grid lookup: "gx,gy" → { value, uncertainty }
  const estimateMap = new Map();
  for (const e of estimates) {
    estimateMap.set(`${e.gx},${e.gy}`, { value: e.value, uncertainty: e.uncertainty ?? 1.0 });
  }

  const cellW = (region.x_max - region.x_min) / gridSize;
  const cellH = (region.y_max - region.y_min) / gridSize;

  function knowledgeAt(x, y) {
    const gx = Math.min(gridSize - 1, Math.max(0, Math.floor((x - region.x_min) / cellW)));
    const gy = Math.min(gridSize - 1, Math.max(0, Math.floor((y - region.y_min) / cellH)));
    const cell = estimateMap.get(`${gx},${gy}`);
    if (!cell) return { value: 0.5, uncertainty: 1.0 };
    const val = isFinite(cell.value) ? cell.value : 0.5;
    return { value: val, uncertainty: cell.uncertainty };
  }

  // Uncertainty threshold: cells with uncertainty above this are considered "no data"
  // (the GP hasn't received enough nearby evidence to meaningfully update from the prior)
  const UNCERTAINTY_THRESHOLD = 0.85;

  const results = [];
  for (const [concept, pts] of coords) {
    let sum = 0;
    let uncertaintySum = 0;
    for (const c of pts) {
      const k = knowledgeAt(c.x, c.y);
      sum += k.value;
      uncertaintySum += k.uncertainty;
    }
    const knowledge = pts.length > 0 ? sum / pts.length : 0.5;
    const avgUncertainty = pts.length > 0 ? uncertaintySum / pts.length : 1.0;
    // hasEvidence: true if the average uncertainty is low enough that the GP has
    // meaningfully updated from the prior for this concept's grid cells
    results.push({
      concept,
      knowledge: isFinite(knowledge) ? knowledge : 0.5,
      count: pts.length,
      hasEvidence: avgUncertainty < UNCERTAINTY_THRESHOLD,
    });
  }

  return results;
}

// Shared caveat about genuine effort (used in both modals)
const CAVEAT_HTML = `<p class="insights-caveat"><strong>Note:</strong> These estimates assume responses reflect genuine effort. Randomly clicking through questions without thinking will generate estimates that aren't useful or meaningful.</p>`;

/**
 * Show leaderboard modal — domains ranked by estimated knowledge.
 * @param {Array} domainKnowledge - From computeDomainKnowledge()
 */
export function showLeaderboard(domainKnowledge) {
  if (!modalEl) return;

  const titleEl = document.getElementById('insights-modal-title');
  const bodyEl = document.getElementById('insights-modal-body');
  if (!titleEl || !bodyEl) return;

  titleEl.textContent = '';
  const icon = document.createElement('i');
  icon.className = 'fa-solid fa-trophy';
  icon.style.color = '#d4a017';
  titleEl.appendChild(icon);
  titleEl.appendChild(document.createTextNode(' My Areas of Expertise'));

  const emptyMsg = 'Answer more questions to discover your areas of expertise.';
  if (!domainKnowledge || domainKnowledge.length === 0) {
    bodyEl.textContent = '';
    const msg = document.createElement('div');
    msg.className = 'insights-empty-msg';
    msg.textContent = emptyMsg;
    bodyEl.appendChild(msg);
    modalEl.hidden = false;
    return;
  }

  // Only show domains with nearby evidence
  const evidenced = domainKnowledge.filter(c => c.hasEvidence !== false);
  if (evidenced.length === 0) {
    bodyEl.textContent = '';
    const msg = document.createElement('div');
    msg.className = 'insights-empty-msg';
    msg.textContent = emptyMsg;
    bodyEl.appendChild(msg);
    modalEl.hidden = false;
    return;
  }
  const sorted = [...evidenced].sort((a, b) => b.knowledge - a.knowledge);

  // Build the body using safe DOM methods
  bodyEl.textContent = '';
  const explainer = document.createElement('p');
  explainer.className = 'insights-explainer';
  explainer.textContent = 'Your knowledge estimated per domain, ranked highest first. '
    + 'Each score averages the GP prediction at every question coordinate in that domain.';
  bodyEl.appendChild(explainer);
  bodyEl.appendChild(buildDomainList(sorted));
  const caveat = document.createElement('p');
  caveat.className = 'insights-caveat';
  const strong = document.createElement('strong');
  strong.textContent = 'Note:';
  caveat.appendChild(strong);
  caveat.appendChild(document.createTextNode(' These estimates assume responses reflect genuine effort. Randomly clicking through questions without thinking will generate estimates that aren\'t useful or meaningful.'));
  bodyEl.appendChild(caveat);
  modalEl.hidden = false;
}

/**
 * Show suggestions modal — bottom 10 least-known concepts with Khan Academy links.
 */
export function showSuggestions(conceptKnowledge) {
  if (!modalEl) return;

  const titleEl = document.getElementById('insights-modal-title');
  const bodyEl = document.getElementById('insights-modal-body');
  if (!titleEl || !bodyEl) return;

  titleEl.textContent = '';
  const icon = document.createElement('i');
  icon.className = 'fa-solid fa-graduation-cap';
  icon.style.color = 'var(--color-primary)';
  titleEl.appendChild(icon);
  titleEl.appendChild(document.createTextNode(' Suggested Learning'));

  if (!conceptKnowledge || conceptKnowledge.length === 0) {
    bodyEl.textContent = '';
    const msg = document.createElement('div');
    msg.className = 'insights-empty-msg';
    msg.textContent = 'Answer more questions to get personalized learning suggestions.';
    bodyEl.appendChild(msg);
    modalEl.hidden = false;
    return;
  }

  // Only show concepts with nearby evidence — unexplored areas are always "low" but not useful suggestions
  const evidenced = conceptKnowledge.filter(c => c.hasEvidence !== false);
  if (evidenced.length === 0) {
    bodyEl.textContent = '';
    const msg = document.createElement('div');
    msg.className = 'insights-empty-msg';
    msg.textContent = 'Answer more questions to get personalized learning suggestions.';
    bodyEl.appendChild(msg);
    modalEl.hidden = false;
    return;
  }

  const sorted = [...evidenced].sort((a, b) => a.knowledge - b.knowledge);

  // Filter to concepts likely to have good Khan Academy results:
  // - At least 2 words (single words are often too generic)
  // - Not excessively long (5+ words are usually too niche)
  // - Skip concepts that are just numbers or very short
  const filtered = sorted.filter(item => {
    const words = item.concept.trim().split(/\s+/);
    if (words.length < 2 || words.length > 5) return false;
    if (item.concept.length < 5) return false;
    return true;
  });
  // Fall back to unfiltered if filtering removes too many
  const candidates = filtered.length >= 10 ? filtered : sorted;
  const top10 = candidates.slice(0, 10);

  const explainer = '<p class="insights-explainer">'
    + 'Clicking a link below will search <strong>Khan Academy</strong> for related learning content. '
    + 'Suggestions are based on concepts where the system estimates your knowledge is lowest, '
    + 'determined by your responses to nearby questions on the map.'
    + '</p>';
  bodyEl.innerHTML = explainer + renderList(top10, 'var(--color-incorrect)', true) + CAVEAT_HTML;
  modalEl.hidden = false;
}

/** Hide the insights modal. */
export function hide() {
  if (modalEl) modalEl.hidden = true;
}

// ======== Private helpers ========

/** Build a DOM list of domain rankings. */
function buildDomainList(items) {
  const ul = document.createElement('ul');
  ul.className = 'insights-modal-list';
  const barColor = 'var(--color-correct)';

  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const pct = Math.round(item.knowledge * 100);
    const noData = item.hasEvidence === false;

    const li = document.createElement('li');

    const rank = document.createElement('span');
    rank.className = 'insights-rank';
    rank.textContent = `${i + 1}.`;

    const nameSpan = document.createElement('span');
    nameSpan.className = 'insights-concept';
    // Indent sub-domains under their parent
    const label = item.level === 'sub' ? item.name : item.name;
    nameSpan.textContent = label;
    if (item.level === 'sub') {
      nameSpan.style.paddingLeft = '0.75rem';
      nameSpan.style.fontSize = '0.8rem';
    }

    const pctSpan = document.createElement('span');
    pctSpan.className = 'insights-pct';
    pctSpan.textContent = noData ? '—' : `${pct}%`;
    pctSpan.style.color = noData ? 'var(--color-text-muted)' : barColor;

    const barOuter = document.createElement('span');
    barOuter.className = 'insights-bar-mini';
    const barFill = document.createElement('span');
    barFill.className = 'insights-bar-fill-mini';
    barFill.style.width = `${noData ? 0 : pct}%`;
    barFill.style.background = barColor;
    barOuter.appendChild(barFill);

    li.appendChild(rank);
    li.appendChild(nameSpan);
    li.appendChild(pctSpan);
    li.appendChild(barOuter);
    ul.appendChild(li);
  }

  return ul;
}

/** Build an HTML string list of concept rankings. */
function renderList(items, barColor, showLinks) {
  let html = '<ul class="insights-modal-list">';
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const pct = Math.round(item.knowledge * 100);
    const text = escapeHtml(item.concept);
    const conceptContent = showLinks
      ? `<a href="${kaLink(item.concept)}" target="_blank" rel="noopener" title="Search Khan Academy for ${text}">${text}</a>`
      : text;

    const noData = item.hasEvidence === false;
    const pctText = noData ? '—' : `${pct}%`;
    const barWidth = noData ? 0 : pct;
    const pctColor = noData ? 'var(--color-text-muted)' : barColor;

    html += `
      <li>
        <span class="insights-rank">${i + 1}.</span>
        <span class="insights-concept">${conceptContent}</span>
        <span class="insights-pct" style="color:${pctColor};">${pctText}</span>
        <span class="insights-bar-mini">
          <span class="insights-bar-fill-mini" style="width:${barWidth}%;background:${barColor};"></span>
        </span>
      </li>`;
  }
  html += '</ul>';
  return html;
}

function kaLink(concept) {
  // Use unquoted search — quoted exact-match returns zero results for many concepts
  const query = encodeURIComponent(concept);
  return `https://www.khanacademy.org/search?page_search_query=${query}`;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
