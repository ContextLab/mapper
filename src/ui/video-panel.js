/** Left sidebar video discovery panel — viewport-filtered, searchable video list. */

let containerEl = null;
let listEl = null;
let searchEl = null;
let countEl = null;
let toggleEl = null;
let allMarkers = [];      // Full set of video markers [{x, y, videoId, title, thumbnailUrl, durationS}]
let filteredVideos = [];   // Grouped, viewport-filtered, deduplicated
let currentViewport = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
let watchedSet = new Set();
let searchQuery = '';
let onSelectCb = null;
let onHoverCb = null;
let onToggleMarkersCb = null;
let markersVisible = false;
let debounceTimer = null;

export function init(container, options = {}) {
  containerEl = container;
  onSelectCb = options.onVideoSelect || null;
  onHoverCb = options.onVideoHover || null;
  onToggleMarkersCb = options.onToggleMarkers || null;

  // Inject styles
  if (!document.getElementById('video-panel-styles')) {
    const style = document.createElement('style');
    style.id = 'video-panel-styles';
    style.textContent = PANEL_CSS;
    document.head.appendChild(style);
  }

  // Build panel DOM
  const header = document.createElement('div');
  header.className = 'video-panel-header';

  const titleRow = document.createElement('div');
  titleRow.className = 'video-panel-title-row';

  const title = document.createElement('span');
  title.className = 'video-panel-title';
  title.textContent = 'Lectures';

  countEl = document.createElement('span');
  countEl.className = 'video-panel-count';
  countEl.textContent = '0';

  toggleEl = document.createElement('button');
  toggleEl.className = 'video-panel-marker-toggle';
  toggleEl.type = 'button';
  toggleEl.title = 'Show/hide video markers on map';
  toggleEl.textContent = 'Show on map';
  toggleEl.addEventListener('click', () => {
    markersVisible = !markersVisible;
    toggleEl.textContent = markersVisible ? 'Hide on map' : 'Show on map';
    toggleEl.classList.toggle('active', markersVisible);
    if (onToggleMarkersCb) onToggleMarkersCb(markersVisible);
  });

  titleRow.appendChild(title);
  titleRow.appendChild(countEl);
  titleRow.appendChild(toggleEl);
  header.appendChild(titleRow);

  searchEl = document.createElement('input');
  searchEl.className = 'video-panel-search';
  searchEl.type = 'text';
  searchEl.placeholder = 'Search videos...';
  searchEl.setAttribute('aria-label', 'Search videos');
  searchEl.addEventListener('input', () => {
    searchQuery = searchEl.value.trim().toLowerCase();
    renderList();
  });
  header.appendChild(searchEl);

  listEl = document.createElement('div');
  listEl.className = 'video-panel-list';
  listEl.setAttribute('role', 'list');

  containerEl.appendChild(header);
  containerEl.appendChild(listEl);
}

export function setVideos(markers) {
  allMarkers = markers || [];
  filterAndRender();
}

export function updateViewport(viewport) {
  currentViewport = viewport;
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(filterAndRender, 100);
}

export function setWatchedVideos(watched) {
  watchedSet = watched instanceof Set ? watched : new Set(watched);
  renderList();
}

export function show() {
  if (containerEl) containerEl.classList.add('open');
}

export function hide() {
  if (containerEl) containerEl.classList.remove('open');
}

export function toggle() {
  if (containerEl) containerEl.classList.toggle('open');
}

export function isOpen() {
  return containerEl ? containerEl.classList.contains('open') : false;
}

export function destroy() {
  if (containerEl) containerEl.textContent = '';
  allMarkers = [];
  filteredVideos = [];
  containerEl = null;
  listEl = null;
  searchEl = null;
  countEl = null;
  toggleEl = null;
}

// ─── Internal ─────────────────────────────────

function filterAndRender() {
  const vp = currentViewport;

  // Group markers by videoId, counting how many windows are in viewport
  const videoMap = new Map();
  for (const m of allMarkers) {
    const inVp = m.x >= vp.x_min && m.x <= vp.x_max &&
                 m.y >= vp.y_min && m.y <= vp.y_max;
    if (!videoMap.has(m.videoId)) {
      videoMap.set(m.videoId, {
        videoId: m.videoId,
        title: m.title,
        thumbnailUrl: m.thumbnailUrl,
        durationS: m.durationS,
        inViewport: 0,
        total: 0,
      });
    }
    const entry = videoMap.get(m.videoId);
    entry.total++;
    if (inVp) entry.inViewport++;
  }

  // Filter to videos with at least one window in viewport, sort by relevance
  filteredVideos = [...videoMap.values()]
    .filter(v => v.inViewport > 0)
    .sort((a, b) => b.inViewport - a.inViewport);

  renderList();
}

function renderList() {
  if (!listEl) return;

  let videos = filteredVideos;

  // Apply search filter
  if (searchQuery) {
    videos = videos.filter(v => v.title.toLowerCase().includes(searchQuery));
  }

  if (countEl) countEl.textContent = String(videos.length);

  listEl.textContent = '';

  if (videos.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'video-panel-empty';
    empty.textContent = allMarkers.length === 0
      ? 'No videos loaded yet'
      : 'No videos in this area';
    listEl.appendChild(empty);
    return;
  }

  for (const v of videos) {
    const item = document.createElement('div');
    item.className = 'video-panel-item';
    item.setAttribute('role', 'listitem');
    if (watchedSet.has(v.videoId)) item.classList.add('watched');

    item.addEventListener('mouseenter', () => {
      if (onHoverCb) onHoverCb(v.videoId);
    });
    item.addEventListener('mouseleave', () => {
      if (onHoverCb) onHoverCb(null);
    });
    item.addEventListener('click', () => {
      if (onSelectCb) onSelectCb({
        id: v.videoId,
        title: v.title,
        duration_s: v.durationS,
        thumbnail_url: v.thumbnailUrl,
      });
    });

    const titleSpan = document.createElement('span');
    titleSpan.className = 'video-panel-item-title';
    titleSpan.textContent = v.title;

    const meta = document.createElement('span');
    meta.className = 'video-panel-item-meta';
    const dur = v.durationS ? formatDuration(v.durationS) : '';
    const watched = watchedSet.has(v.videoId) ? ' \u2713' : '';
    meta.textContent = dur + watched;

    item.appendChild(titleSpan);
    item.appendChild(meta);
    listEl.appendChild(item);
  }
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ─── Styles ─────────────────────────────────

const PANEL_CSS = `
  #video-panel {
    width: 0;
    min-width: 0;
    background: var(--color-surface);
    box-shadow: 2px 0 24px rgba(0,0,0,0.3), 1px 0 0 var(--color-border);
    z-index: 10;
    display: flex;
    flex-direction: column;
    padding: 0;
    overflow: hidden;
    transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), padding 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    flex-shrink: 0;
    order: -1;
  }
  #video-panel.open {
    width: var(--sidebar-width);
    padding: 1rem 1.25rem;
    overflow-y: auto;
    overflow-x: hidden;
  }
  #video-panel::-webkit-scrollbar { width: 5px; }
  #video-panel::-webkit-scrollbar-track { background: transparent; }
  #video-panel::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 3px; }
  #video-panel::-webkit-scrollbar-thumb:hover { background: var(--color-primary); }

  .video-panel-header {
    margin-bottom: 0.75rem;
    flex-shrink: 0;
  }
  .video-panel-title-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  .video-panel-title {
    font-family: var(--font-heading);
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text);
  }
  .video-panel-count {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    background: var(--color-surface-raised);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
  }
  .video-panel-marker-toggle {
    margin-left: auto;
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-raised);
    color: var(--color-text-muted);
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--font-body);
  }
  .video-panel-marker-toggle:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }
  .video-panel-marker-toggle.active {
    background: var(--color-primary);
    color: #fff;
    border-color: var(--color-primary);
  }

  .video-panel-search {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    border: 1px solid var(--color-border);
    background: var(--color-surface-raised);
    color: var(--color-text);
    font-family: var(--font-body);
    font-size: 0.8rem;
    outline: none;
    transition: border-color 0.2s;
    box-sizing: border-box;
  }
  .video-panel-search:focus {
    border-color: var(--color-primary);
    box-shadow: 0 0 6px var(--color-glow-primary);
  }

  .video-panel-list {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .video-panel-empty {
    text-align: center;
    padding: 2rem 0.5rem;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    font-style: italic;
  }

  .video-panel-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding: 0.6rem 0.75rem;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s ease;
    border-bottom: 1px solid rgba(148,163,184,0.1);
  }
  .video-panel-item:hover {
    background: var(--color-surface-raised);
    box-shadow: 0 0 8px var(--color-glow-primary);
  }
  .video-panel-item.watched {
    opacity: 0.6;
  }
  .video-panel-item-title {
    font-size: 0.8rem;
    color: var(--color-text);
    font-family: var(--font-body);
    line-height: 1.4;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .video-panel-item-meta {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .video-toggle-btn {
    position: absolute;
    top: 50%;
    left: 0;
    transform: translateY(-50%);
    z-index: 9;
    width: 28px;
    height: 56px;
    border: 1px solid var(--color-border);
    border-left: none;
    border-radius: 0 8px 8px 0;
    background: var(--color-surface);
    color: var(--color-text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    transition: all 0.2s ease;
    box-shadow: 2px 0 8px rgba(0,0,0,0.15);
  }
  .video-toggle-btn:hover {
    color: var(--color-primary);
    border-color: var(--color-primary);
    box-shadow: 2px 0 12px var(--color-glow-primary);
  }
  .video-toggle-btn.panel-open {
    left: var(--sidebar-width);
  }
  .video-toggle-btn[hidden] { display: none; }

  @media (max-width: 768px) {
    #video-panel.open { width: 50%; }
  }
  @media (max-width: 480px) {
    #video-panel { display: none; }
    .video-toggle-btn { display: none; }
  }
`;
