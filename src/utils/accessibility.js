/** Accessibility utilities for focus management, screen reader announcements, and keyboard navigation. */

let activeTrap = null;

/**
 * Initialize a focus trap within the given element.
 * @param {HTMLElement} element - Container element to trap focus within
 * @returns {Function} Cleanup function to release the trap
 */
export function initFocusTrap(element) {
  if (activeTrap) {
    activeTrap();
    activeTrap = null;
  }

  const focusableSelector = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const focusableElements = Array.from(element.querySelectorAll(focusableSelector));

  if (focusableElements.length === 0) {
    return () => {};
  }

  const firstFocusable = focusableElements[0];
  const lastFocusable = focusableElements[focusableElements.length - 1];

  const handleKeydown = (e) => {
    if (e.key !== 'Tab') return;

    if (e.shiftKey) {
      if (document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      }
    } else {
      if (document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  };

  element.addEventListener('keydown', handleKeydown);

  firstFocusable.focus();

  const cleanup = () => {
    element.removeEventListener('keydown', handleKeydown);
    if (activeTrap === cleanup) {
      activeTrap = null;
    }
  };

  activeTrap = cleanup;
  return cleanup;
}

/**
 * Announce a message to screen readers via ARIA live region.
 * @param {string} message - Message to announce
 * @param {string} priority - 'polite' or 'assertive' (default: 'polite')
 */
export function announce(message, priority = 'polite') {
  let liveRegion = document.getElementById('aria-live');

  if (!liveRegion) {
    liveRegion = document.createElement('div');
    liveRegion.id = 'aria-live';
    liveRegion.className = 'sr-only';
    liveRegion.setAttribute('aria-live', priority);
    liveRegion.setAttribute('aria-atomic', 'true');
    document.body.appendChild(liveRegion);
  } else {
    liveRegion.setAttribute('aria-live', priority);
  }

  // Clear and set message via requestAnimationFrame to ensure re-announcement
  liveRegion.textContent = '';
  requestAnimationFrame(() => {
    liveRegion.textContent = message;
  });
}

/**
 * Set up global keyboard navigation handlers.
 * @param {Object} handlers - Event handlers { onEscape: Function }
 * @returns {Function} Cleanup function to remove listeners
 */
export function setupKeyboardNav(handlers = {}) {
  const handleKeydown = (e) => {
    if (e.key === 'Escape' && handlers.onEscape) {
      handlers.onEscape();
    }
  };

  document.addEventListener('keydown', handleKeydown);

  const skipLink = document.querySelector('[data-skip-to-content]');
  const handleSkipClick = (e) => {
    e.preventDefault();
    const mapContainer = document.getElementById('map-container');
    if (mapContainer) {
      mapContainer.focus();
    }
  };

  if (skipLink) {
    skipLink.addEventListener('click', handleSkipClick);
  }

  return () => {
    document.removeEventListener('keydown', handleKeydown);
    if (skipLink) {
      skipLink.removeEventListener('click', handleSkipClick);
    }
  };
}
