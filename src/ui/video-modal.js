/**
 * Video recommendation modal — list view + inline YouTube player.
 *
 * Replaces the old concept-based suggestion list with actual video recommendations.
 * Triggered by the graduation-cap suggest button.
 *
 * All dynamic content is escaped via escapeHtml/escapeAttr before insertion.
 * Video IDs originate from our own pipeline data, not user input.
 *
 * See FR-V030 through FR-V036, T-V040 through T-V044.
 */

import { $watchedVideos } from '../state/store.js';

let modalEl = null;
let listContainerEl = null;
let playerContainerEl = null;
let currentView = 'list'; // 'list' | 'player'
let currentVideos = [];
let ytPlayer = null;
let ytApiLoaded = false;
let ytApiLoading = false;
let onVideoCompleteCb = null;

const SPEED_OPTIONS = [0.5, 0.75, 1, 1.25, 1.5, 2];

// ─── Public API ─────────────────────────────────────────────

export function init() {
  if (document.getElementById('video-modal-style')) return;

  const style = document.createElement('style');
  style.id = 'video-modal-style';
  style.textContent = MODAL_CSS;
  document.head.appendChild(style);

  modalEl = document.createElement('div');
  modalEl.id = 'video-modal';
  modalEl.className = 'modal';
  modalEl.hidden = true;
  modalEl.setAttribute('role', 'dialog');
  modalEl.setAttribute('aria-modal', 'true');
  modalEl.setAttribute('aria-label', 'Video recommendations');

  // Build modal DOM using safe DOM methods
  const content = document.createElement('div');
  content.className = 'modal-content video-modal-content';

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'modal-close-x video-modal-close';
  closeBtn.setAttribute('aria-label', 'Close');
  closeBtn.textContent = '\u00D7';
  closeBtn.addEventListener('click', hide);

  listContainerEl = document.createElement('div');
  listContainerEl.id = 'video-list-view';

  playerContainerEl = document.createElement('div');
  playerContainerEl.id = 'video-player-view';
  playerContainerEl.hidden = true;

  content.appendChild(closeBtn);
  content.appendChild(listContainerEl);
  content.appendChild(playerContainerEl);
  modalEl.appendChild(content);
  document.body.appendChild(modalEl);

  // Close on backdrop click
  modalEl.addEventListener('click', (e) => {
    if (e.target === modalEl) hide();
  });
}

/**
 * Show the video modal with ranked video recommendations.
 *
 * @param {Array<{video: object, score: number}>} rankedVideos - From computeRanking()
 */
export function showVideoModal(rankedVideos) {
  if (!modalEl) init();

  currentVideos = rankedVideos || [];
  showListView();
  modalEl.hidden = false;
}

/** Hide the video modal and clean up player. */
export function hide() {
  if (!modalEl) return;
  destroyPlayer();
  modalEl.hidden = true;
  currentView = 'list';
}

/** Check if the video modal is currently visible. */
export function isVisible() {
  return modalEl && !modalEl.hidden;
}

/** Handle Escape key — back to list from player, or close from list. */
export function handleEscape() {
  if (!isVisible()) return false;

  if (currentView === 'player') {
    showListView();
    return true;
  }

  hide();
  return true;
}

/** Register callback for video completion events. */
export function onVideoComplete(callback) {
  onVideoCompleteCb = callback;
}

/**
 * Open the modal directly in player view for a single video (from map click).
 * No list view, no gain indicator — just a "Back to map" header + player.
 *
 * @param {{ id: string, title: string, duration_s?: number, thumbnail_url?: string }} video
 */
export function playVideo(video) {
  if (!modalEl) init();

  currentVideos = [];
  currentView = 'player';
  listContainerEl.hidden = true;
  playerContainerEl.hidden = false;
  playerContainerEl.textContent = '';
  modalEl.hidden = false;

  // Header with close button (no gain indicator)
  const header = document.createElement('div');
  header.className = 'video-player-header';

  const backBtn = document.createElement('button');
  backBtn.className = 'video-back-btn';
  backBtn.type = 'button';
  const backIcon = document.createElement('i');
  backIcon.className = 'fa-solid fa-arrow-left';
  backBtn.appendChild(backIcon);
  backBtn.appendChild(document.createTextNode(' Back to map'));
  backBtn.addEventListener('click', hide);

  header.appendChild(backBtn);
  playerContainerEl.appendChild(header);

  // Video title
  const titleDiv = document.createElement('div');
  titleDiv.className = 'video-player-title';
  titleDiv.textContent = video.title || 'Video';
  playerContainerEl.appendChild(titleDiv);

  // Player frame container
  const frameDiv = document.createElement('div');
  frameDiv.id = 'video-player-frame';
  frameDiv.className = 'video-player-frame';
  playerContainerEl.appendChild(frameDiv);

  // Speed controls
  const speedDiv = document.createElement('div');
  speedDiv.className = 'video-speed-controls';

  for (const s of SPEED_OPTIONS) {
    const btn = document.createElement('button');
    btn.className = 'speed-btn' + (s === 1 ? ' active' : '');
    btn.dataset.speed = String(s);
    btn.textContent = `${s}\u00D7`;
    btn.addEventListener('click', () => {
      if (ytPlayer && ytPlayer.setPlaybackRate) {
        ytPlayer.setPlaybackRate(s);
        speedDiv.querySelectorAll('.speed-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
      }
    });
    speedDiv.appendChild(btn);
  }

  playerContainerEl.appendChild(speedDiv);

  loadYouTubePlayer(video.id, 'video-player-frame');
}

// ─── List View (T-V040, T-V041) ────────────────────────────

function showListView() {
  currentView = 'list';
  destroyPlayer();
  playerContainerEl.hidden = true;
  listContainerEl.hidden = false;

  // Clear previous content
  listContainerEl.textContent = '';

  const watchedIds = $watchedVideos.get();

  // Title
  const titleDiv = document.createElement('div');
  titleDiv.className = 'video-modal-title';
  const icon = document.createElement('i');
  icon.className = 'fa-solid fa-graduation-cap';
  titleDiv.appendChild(icon);
  titleDiv.appendChild(document.createTextNode(' Recommended Videos'));
  listContainerEl.appendChild(titleDiv);

  if (currentVideos.length === 0) {
    const emptyDiv = document.createElement('div');
    emptyDiv.className = 'video-empty-msg';
    emptyDiv.textContent = 'No recommended videos for this domain yet. ';
    const link = document.createElement('a');
    link.href = 'https://www.khanacademy.org';
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'Browse Khan Academy \u2192';
    emptyDiv.appendChild(link);
    listContainerEl.appendChild(emptyDiv);
    return;
  }

  const ul = document.createElement('ul');
  ul.className = 'video-list';

  for (let i = 0; i < currentVideos.length; i++) {
    const { video, score } = currentVideos[i];
    const pct = Math.round(score * 100);
    const isWatched = watchedIds.has(video.id);
    const duration = formatDuration(video.duration_s);
    const gainClass = pct >= 65 ? 'gain-high' : pct >= 35 ? 'gain-mid' : 'gain-low';

    const li = document.createElement('li');
    li.className = 'video-item';
    li.dataset.videoIdx = String(i);

    // Rank
    const rankSpan = document.createElement('span');
    rankSpan.className = 'video-rank';
    rankSpan.textContent = String(i + 1);
    li.appendChild(rankSpan);

    // Play icon
    const playSpan = document.createElement('span');
    playSpan.className = 'video-play-icon';
    const playIcon = document.createElement('i');
    playIcon.className = 'fa-solid fa-play';
    playSpan.appendChild(playIcon);
    li.appendChild(playSpan);

    // Title
    const titleSpan = document.createElement('span');
    titleSpan.className = 'video-title';
    titleSpan.textContent = video.title;
    titleSpan.title = video.title;
    li.appendChild(titleSpan);

    // Gain indicator
    const gainSpan = document.createElement('span');
    gainSpan.className = `video-gain ${gainClass}`;

    const barSpan = document.createElement('span');
    barSpan.className = 'video-gain-bar';
    const fillSpan = document.createElement('span');
    fillSpan.className = 'video-gain-fill';
    fillSpan.style.width = `${pct}%`;
    barSpan.appendChild(fillSpan);
    gainSpan.appendChild(barSpan);

    const pctSpan = document.createElement('span');
    pctSpan.className = 'video-gain-pct';
    pctSpan.textContent = `${pct}%`;
    gainSpan.appendChild(pctSpan);
    li.appendChild(gainSpan);

    // Duration
    const durSpan = document.createElement('span');
    durSpan.className = 'video-duration';
    durSpan.textContent = duration;
    li.appendChild(durSpan);

    // Watched indicator
    if (isWatched) {
      const watchSpan = document.createElement('span');
      watchSpan.className = 'video-watched';
      watchSpan.title = 'Watched';
      const checkIcon = document.createElement('i');
      checkIcon.className = 'fa-solid fa-check';
      watchSpan.appendChild(checkIcon);
      li.appendChild(watchSpan);
    } else {
      const placeholder = document.createElement('span');
      placeholder.className = 'video-watched-placeholder';
      li.appendChild(placeholder);
    }

    // Click handler
    li.addEventListener('click', () => {
      if (currentVideos[i]) {
        showPlayerView(currentVideos[i].video, currentVideos[i].score);
      }
    });

    ul.appendChild(li);
  }

  listContainerEl.appendChild(ul);
}

// ─── Player View (T-V042, T-V043) ──────────────────────────

function showPlayerView(video, score) {
  currentView = 'player';
  listContainerEl.hidden = true;
  playerContainerEl.hidden = false;
  playerContainerEl.textContent = '';

  const pct = Math.round(score * 100);

  // Header with back button and gain
  const header = document.createElement('div');
  header.className = 'video-player-header';

  const backBtn = document.createElement('button');
  backBtn.className = 'video-back-btn';
  backBtn.type = 'button';
  const backIcon = document.createElement('i');
  backIcon.className = 'fa-solid fa-arrow-left';
  backBtn.appendChild(backIcon);
  backBtn.appendChild(document.createTextNode(' Back to list'));
  backBtn.addEventListener('click', showListView);

  const gainSpan = document.createElement('span');
  gainSpan.className = 'video-player-gain';
  gainSpan.textContent = `${pct}% estimated gain`;

  header.appendChild(backBtn);
  header.appendChild(gainSpan);
  playerContainerEl.appendChild(header);

  // Video title
  const titleDiv = document.createElement('div');
  titleDiv.className = 'video-player-title';
  titleDiv.textContent = video.title;
  playerContainerEl.appendChild(titleDiv);

  // Player frame container
  const frameDiv = document.createElement('div');
  frameDiv.id = 'video-player-frame';
  frameDiv.className = 'video-player-frame';
  playerContainerEl.appendChild(frameDiv);

  // Speed controls
  const speedDiv = document.createElement('div');
  speedDiv.className = 'video-speed-controls';

  for (const s of SPEED_OPTIONS) {
    const btn = document.createElement('button');
    btn.className = 'speed-btn' + (s === 1 ? ' active' : '');
    btn.dataset.speed = String(s);
    btn.textContent = `${s}\u00D7`;
    btn.addEventListener('click', () => {
      if (ytPlayer && ytPlayer.setPlaybackRate) {
        ytPlayer.setPlaybackRate(s);
        speedDiv.querySelectorAll('.speed-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
      }
    });
    speedDiv.appendChild(btn);
  }

  playerContainerEl.appendChild(speedDiv);

  // Load YouTube player
  loadYouTubePlayer(video.id, 'video-player-frame');
}

function loadYouTubePlayer(videoId, containerId) {
  const createPlayer = () => {
    try {
      ytPlayer = new window.YT.Player(containerId, {
        videoId,
        host: 'https://www.youtube-nocookie.com',
        playerVars: {
          autoplay: 1,
          modestbranding: 1,
          rel: 0,
        },
        events: {
          onReady: onPlayerReady,
          onStateChange: onPlayerStateChange,
          onError: () => showEmbedFallback(videoId, containerId),
        },
      });
    } catch {
      showEmbedFallback(videoId, containerId);
    }
  };

  if (ytApiLoaded) {
    createPlayer();
  } else {
    loadYouTubeApi().then(createPlayer).catch(() => {
      showEmbedFallback(videoId, containerId);
    });
  }
}

function loadYouTubeApi() {
  if (ytApiLoaded) return Promise.resolve();
  if (ytApiLoading) {
    return new Promise((resolve) => {
      const check = setInterval(() => {
        if (ytApiLoaded) { clearInterval(check); resolve(); }
      }, 100);
    });
  }

  ytApiLoading = true;

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://www.youtube.com/iframe_api';
    script.onerror = () => { ytApiLoading = false; reject(new Error('YouTube API failed to load')); };

    window.onYouTubeIframeAPIReady = () => {
      ytApiLoaded = true;
      ytApiLoading = false;
      resolve();
    };

    document.head.appendChild(script);
  });
}

function onPlayerReady(event) {
  if (event.target.getAvailablePlaybackRates) {
    const available = event.target.getAvailablePlaybackRates();
    playerContainerEl?.querySelectorAll('.speed-btn').forEach((btn) => {
      const speed = parseFloat(btn.dataset.speed);
      if (!available.includes(speed)) {
        btn.disabled = true;
        btn.classList.add('unavailable');
      }
    });
  }
}

function onPlayerStateChange(event) {
  // YT.PlayerState.ENDED === 0
  if (event.data === 0) {
    const videoId = ytPlayer?.getVideoData?.()?.video_id;
    if (videoId) {
      markWatched(videoId);
    }
  }
}

function showEmbedFallback(videoId, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.textContent = '';

  const fallback = document.createElement('div');
  fallback.className = 'video-embed-fallback';

  const msg = document.createElement('p');
  msg.textContent = 'Video embed is unavailable.';
  fallback.appendChild(msg);

  const link = document.createElement('a');
  link.href = `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`;
  link.target = '_blank';
  link.rel = 'noopener';
  const linkIcon = document.createElement('i');
  linkIcon.className = 'fa-solid fa-external-link-alt';
  link.appendChild(linkIcon);
  link.appendChild(document.createTextNode(' Watch on YouTube'));
  fallback.appendChild(link);

  container.appendChild(fallback);
}

function markWatched(videoId) {
  const current = $watchedVideos.get();
  if (current.has(videoId)) return;

  const next = new Set(current);
  next.add(videoId);
  $watchedVideos.set(next);

  // Update checkmark in the list
  for (let i = 0; i < currentVideos.length; i++) {
    if (currentVideos[i].video.id === videoId) {
      const placeholder = listContainerEl?.querySelector(
        `[data-video-idx="${i}"] .video-watched-placeholder`
      );
      if (placeholder) {
        const watchSpan = document.createElement('span');
        watchSpan.className = 'video-watched';
        watchSpan.title = 'Watched';
        const checkIcon = document.createElement('i');
        checkIcon.className = 'fa-solid fa-check';
        watchSpan.appendChild(checkIcon);
        placeholder.replaceWith(watchSpan);
      }
      break;
    }
  }

  if (onVideoCompleteCb) onVideoCompleteCb(videoId);
}

function destroyPlayer() {
  if (ytPlayer) {
    try { ytPlayer.destroy(); } catch { /* ignore */ }
    ytPlayer = null;
  }
}

// ─── Helpers ────────────────────────────────────────────────

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

// ─── CSS ────────────────────────────────────────────────────

const MODAL_CSS = `
  .video-modal-content {
    max-width: 560px;
    min-height: 300px;
  }

  .video-modal-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-heading);
    font-size: 1.1rem;
    color: var(--color-primary);
    margin-bottom: 1rem;
  }

  .video-empty-msg {
    color: var(--color-text-muted);
    font-style: italic;
    text-align: center;
    padding: 2rem 0;
    font-size: 0.9rem;
  }
  .video-empty-msg a {
    display: block;
    margin-top: 0.75rem;
    color: var(--color-secondary);
    text-decoration: underline;
  }

  /* ── List view ── */

  .video-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .video-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.5rem 0.25rem;
    border-bottom: 1px solid var(--color-border);
    cursor: pointer;
    transition: background 0.15s ease;
    font-size: 0.85rem;
  }
  .video-item:last-child { border-bottom: none; }
  .video-item:hover {
    background: var(--color-surface-raised);
    border-radius: 6px;
  }

  .video-rank {
    font-weight: 700;
    color: var(--color-text-muted);
    min-width: 1.5rem;
    flex-shrink: 0;
    text-align: right;
  }

  .video-play-icon {
    color: var(--color-primary);
    font-size: 0.7rem;
    flex-shrink: 0;
    width: 1.2rem;
    text-align: center;
  }

  .video-title {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .video-gain {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    flex-shrink: 0;
    min-width: 80px;
  }

  .video-gain-bar {
    width: 40px;
    height: 5px;
    background: var(--color-surface-raised);
    border-radius: 3px;
    overflow: hidden;
    flex-shrink: 0;
  }

  .video-gain-fill {
    display: block;
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .gain-high .video-gain-fill { background: var(--color-correct); }
  .gain-mid .video-gain-fill { background: var(--color-accent, #d4a017); }
  .gain-low .video-gain-fill { background: var(--color-text-muted); }

  .video-gain-pct {
    font-size: 0.75rem;
    font-weight: 600;
    min-width: 2.5rem;
    text-align: right;
  }

  .gain-high .video-gain-pct { color: var(--color-correct); }
  .gain-mid .video-gain-pct { color: var(--color-accent, #d4a017); }
  .gain-low .video-gain-pct { color: var(--color-text-muted); }

  .video-duration {
    color: var(--color-text-muted);
    font-size: 0.75rem;
    flex-shrink: 0;
    min-width: 2.5rem;
    text-align: right;
  }

  .video-watched {
    color: var(--color-correct);
    font-size: 0.75rem;
    flex-shrink: 0;
    width: 1.2rem;
    text-align: center;
  }

  .video-watched-placeholder {
    width: 1.2rem;
    flex-shrink: 0;
  }

  /* ── Player view ── */

  .video-player-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .video-back-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.35rem 0.6rem;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    background: var(--color-surface-raised);
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 0.8rem;
    font-family: var(--font-body);
    transition: all 0.15s ease;
  }
  .video-back-btn:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  .video-player-gain {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .video-player-title {
    font-family: var(--font-heading);
    font-size: 0.95rem;
    margin-bottom: 0.75rem;
    line-height: 1.3;
  }

  .video-player-frame {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 0.75rem;
  }
  .video-player-frame iframe {
    width: 100%;
    height: 100%;
    border: none;
  }

  .video-embed-fallback {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 200px;
    color: var(--color-text-muted);
    gap: 0.75rem;
  }
  .video-embed-fallback a {
    color: var(--color-secondary);
    text-decoration: underline;
    font-size: 0.9rem;
  }

  .video-speed-controls {
    display: flex;
    gap: 0.35rem;
    justify-content: center;
  }

  .speed-btn {
    padding: 0.3rem 0.6rem;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    background: var(--color-surface-raised);
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 0.75rem;
    font-family: var(--font-body);
    transition: all 0.15s ease;
    min-width: unset;
    min-height: unset;
  }
  .speed-btn:hover:not(:disabled) {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }
  .speed-btn.active {
    background: var(--color-primary);
    color: #fff;
    border-color: var(--color-primary);
  }
  .speed-btn:disabled,
  .speed-btn.unavailable {
    opacity: 0.3;
    cursor: not-allowed;
  }

  /* ── Responsive: mobile bottom sheet (T-V044) ── */

  @media (max-width: 480px) {
    .video-modal-content {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      max-width: 100%;
      width: 100%;
      max-height: 80vh;
      border-radius: 16px 16px 0 0;
      padding: 1.25rem;
      margin: 0;
    }

    .video-player-frame {
      aspect-ratio: auto;
      height: 56vw;
    }
  }
`;
