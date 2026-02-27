/** Download progress bar and learning confidence indicator. */

let confidenceWrapper = null;
let confidenceFill = null;
let confidenceText = null;
let hideTimeout = null;

export function showDownload(loaded, total) {
  const modal = document.getElementById('loading-modal');
  const text = document.getElementById('loading-modal-text');
  const fill = document.getElementById('loading-modal-fill');
  if (!modal) return;

  if (hideTimeout) {
    clearTimeout(hideTimeout);
    hideTimeout = null;
  }

  modal.removeAttribute('hidden');

  let percent = 0;
  if (total && total > 0) {
    percent = Math.min(100, Math.max(0, (loaded / total) * 100));
    if (text) text.textContent = `Loading… ${Math.round(percent)}%`;
    if (fill) fill.style.width = `${percent}%`;
  } else {
    if (text) text.textContent = 'Loading…';
    if (fill) fill.style.width = '0%';
  }
}

export function hideDownload() {
  const modal = document.getElementById('loading-modal');
  if (!modal) return;

  modal.setAttribute('hidden', '');
  const fill = document.getElementById('loading-modal-fill');
  if (fill) fill.style.width = '0%';
}

export function initConfidence(container) {
  if (!container) return;
  if (confidenceWrapper) return;

  confidenceWrapper = document.createElement('div');
  Object.assign(confidenceWrapper.style, {
    marginBottom: '1rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  });

  confidenceText = document.createElement('div');
  Object.assign(confidenceText.style, {
    fontSize: '0.75rem',
    fontFamily: 'var(--font-heading)',
    fontWeight: '500',
    color: 'var(--color-text-muted)'
  });
  confidenceText.textContent = 'Domain mapped: 0%';

  const track = document.createElement('div');
  Object.assign(track.style, {
    height: '6px',
    backgroundColor: 'var(--color-surface-raised)',
    borderRadius: '3px',
    overflow: 'hidden'
  });

  confidenceFill = document.createElement('div');
  Object.assign(confidenceFill.style, {
    height: '100%',
    width: '0%',
    background: '#00693e',
    transition: 'width 0.3s ease'
  });

  track.appendChild(confidenceFill);
  confidenceWrapper.appendChild(confidenceText);
  confidenceWrapper.appendChild(track);
  
  container.prepend(confidenceWrapper);
}

export function updateConfidence(coverage) {
  if (!confidenceFill || !confidenceText) return;

  // Guard against NaN from GP numerical instability
  const safeCoverage = isFinite(coverage) ? coverage : 0;
  const pct = Math.min(100, Math.max(0, safeCoverage * 100));
  confidenceFill.style.width = `${pct}%`;
  confidenceText.textContent = `Domain mapped: ${Math.round(pct)}%`;
}
