/** Download progress bar and learning confidence indicator. */

let confidenceWrapper = null;
let confidenceFill = null;
let confidenceText = null;
let downloadText = null;
let hideTimeout = null;

export function showDownload(loaded, total) {
  const overlay = document.getElementById('progress-overlay');
  if (!overlay) return;

  if (hideTimeout) {
    clearTimeout(hideTimeout);
    hideTimeout = null;
  }

  // Ensure text element exists
  if (!downloadText) {
    downloadText = document.createElement('div');
    Object.assign(downloadText.style, {
      position: 'absolute',
      top: '8px',
      right: '10px',
      fontSize: '12px',
      fontFamily: 'var(--font-sans, system-ui, sans-serif)',
      color: 'var(--color-primary, #3f51b5)',
      fontWeight: '600',
      pointerEvents: 'none',
      textShadow: '0 0 2px rgba(255,255,255,0.8)'
    });
    overlay.appendChild(downloadText);
  }

  overlay.style.display = 'block';
  overlay.style.opacity = '1';
  overlay.style.backgroundColor = 'var(--color-primary, #3f51b5)';
  overlay.style.transition = 'width 0.2s ease, opacity 0.3s ease';
  overlay.style.overflow = 'visible';

  let percent = 0;
  if (total && total > 0) {
    percent = Math.min(100, Math.max(0, (loaded / total) * 100));
    overlay.style.width = `${percent}%`;
    downloadText.textContent = `Loading… ${Math.round(percent)}%`;
  } else {
    overlay.style.width = '100%';
    downloadText.textContent = 'Loading…';
  }
  
  downloadText.style.display = 'block';
}

export function hideDownload() {
  const overlay = document.getElementById('progress-overlay');
  if (!overlay) return;

  overlay.style.opacity = '0';
  
  if (downloadText) {
    downloadText.style.display = 'none';
  }

  hideTimeout = setTimeout(() => {
    overlay.style.width = '0%';
    hideTimeout = null;
  }, 300);
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
    fontWeight: '500',
    color: 'var(--color-text, #333)'
  });
  confidenceText.textContent = 'Domain mapped: 0%';

  const track = document.createElement('div');
  Object.assign(track.style, {
    height: '6px',
    backgroundColor: 'rgba(0,0,0,0.1)',
    borderRadius: '3px',
    overflow: 'hidden'
  });

  confidenceFill = document.createElement('div');
  Object.assign(confidenceFill.style, {
    height: '100%',
    width: '0%',
    backgroundColor: '#ff4444', 
    transition: 'width 0.3s ease, background-color 0.3s ease'
  });

  track.appendChild(confidenceFill);
  confidenceWrapper.appendChild(confidenceText);
  confidenceWrapper.appendChild(track);
  
  container.prepend(confidenceWrapper);
}

export function updateConfidence(coverage) {
  if (!confidenceFill || !confidenceText) return;
  
  const pct = Math.min(100, Math.max(0, coverage * 100));
  const hue = pct * 1.2; 
  const color = `hsl(${hue}, 80%, 45%)`;
  
  confidenceFill.style.width = `${pct}%`;
  confidenceFill.style.backgroundColor = color;
  
  confidenceText.textContent = `Domain mapped: ${Math.round(pct)}%`;
}
