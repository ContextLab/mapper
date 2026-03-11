/**
 * Orientation lock for phone-sized devices.
 * Uses Screen Orientation API to force landscape on map screen.
 */

const PHONE_MAX_DIMENSION = 480;

function isTouchDevice() {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

function isPhone() {
  if (!isTouchDevice()) return false;
  const w = screen.width;
  const h = screen.height;
  return Math.min(w, h) <= PHONE_MAX_DIMENSION;
}

function isOrientationSupported() {
  return screen.orientation && typeof screen.orientation.lock === 'function';
}

/**
 * Lock to landscape on phone-sized devices.
 * No-op on tablets/desktops or if API unavailable.
 * Returns true if lock was requested.
 */
export async function lockLandscape() {
  if (!isPhone()) return false;
  if (!isOrientationSupported()) {
    showRotateOverlay();
    return false;
  }
  try {
    await screen.orientation.lock('landscape');
    hideRotateOverlay();
    return true;
  } catch (e) {
    // DOMException if not in fullscreen or not supported
    showRotateOverlay();
    return false;
  }
}

/**
 * Release orientation lock.
 */
export async function unlockOrientation() {
  hideRotateOverlay();
  if (!isOrientationSupported()) return;
  try {
    screen.orientation.unlock();
  } catch { /* noop */ }
}

/**
 * Show a "please rotate" overlay for phones when orientation API is unavailable.
 */
function showRotateOverlay() {
  if (!isPhone()) return;
  let overlay = document.getElementById('rotate-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'rotate-overlay';

    const content = document.createElement('div');
    content.className = 'rotate-overlay-content';

    const icon = document.createElement('i');
    icon.className = 'fa-solid fa-mobile-screen-button rotate-icon';
    content.appendChild(icon);

    const msg = document.createElement('p');
    msg.textContent = 'Please rotate your device to landscape mode for the best experience';
    content.appendChild(msg);

    overlay.appendChild(content);
    document.body.appendChild(overlay);
  }
  overlay.hidden = false;
  checkOrientationForOverlay();
  window.addEventListener('resize', checkOrientationForOverlay);
}

function hideRotateOverlay() {
  const overlay = document.getElementById('rotate-overlay');
  if (overlay) overlay.hidden = true;
  window.removeEventListener('resize', checkOrientationForOverlay);
}

function checkOrientationForOverlay() {
  const overlay = document.getElementById('rotate-overlay');
  if (!overlay) return;
  if (window.innerWidth > window.innerHeight) {
    overlay.hidden = true;
  } else {
    overlay.hidden = false;
  }
}
