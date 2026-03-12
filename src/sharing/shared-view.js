/**
 * Shared view mode — reuses the normal app infrastructure but injects
 * decoded token responses and hides interactive chrome.
 *
 * Instead of creating a separate renderer, we let boot() run normally,
 * then inject responses and configure the UI for read-only shared mode.
 */

import { buildIndex } from './question-index.js';
import { decodeToken } from './token-codec.js';
import { loadQuestionsForDomain } from '../domain/loader.js';

/**
 * Decode a share token and prepare data for injecting into the running app.
 * Called from boot() BEFORE the normal initialization, to set shared mode.
 * @param {string} tokenString - base64url-encoded response token
 * @returns {{ responses: Array, tokenString: string } | null}
 */
export async function decodeSharedToken(tokenString) {
  try {
    // Load ALL questions (2500) via descendant loading for correct token decoding
    const allQuestions = await loadQuestionsForDomain('all');
    const questionIndex = buildIndex(allQuestions);
    const decoded = decodeToken(tokenString, questionIndex);

    // Even empty/null decoded results are valid — show empty map
    const entries = decoded || [];

    // Build question lookup for coordinates
    const questionMap = new Map(allQuestions.map(q => [q.id, q]));

    // Create response objects with coordinates (matching $responses format)
    const responses = [];
    for (const entry of entries) {
      const q = questionMap.get(entry.question_id);
      if (q) {
        responses.push({
          question_id: entry.question_id,
          domain_id: q.domain_ids?.[0] || 'all',
          selected: entry.is_correct ? q.answer : 'X',
          is_correct: entry.is_correct,
          is_skipped: entry.is_skipped,
          difficulty: q.difficulty || 1,
          timestamp: Date.now(),
          x: q.x,
          y: q.y,
        });
      }
    }

    return { responses, tokenString };
  } catch (err) {
    console.warn('[shared-view] Failed to decode token:', err);
    return null;
  }
}

/**
 * Configure the UI for shared view mode after boot() has finished.
 * Hides interactive chrome, configures header, shows minimap.
 * @param {string} tokenString - original token for re-sharing
 */
export function applySharedViewChrome(tokenString) {
  // Hide interactive panels and drawer pulls
  const hideSelectors = [
    '#quiz-panel',
    '#video-panel',
    '.drawer-pull',
    '#drawer-pull-quiz',
    '#drawer-pull-video',
    '.loading-modal',
  ];
  for (const sel of hideSelectors) {
    for (const el of document.querySelectorAll(sel)) {
      el.style.display = 'none';
    }
  }

  // Configure header for shared view
  const header = document.getElementById('app-header');
  if (header) {
    // Hide entire left-group action bar (reset/download/upload)
    const headerActions = header.querySelector('.header-actions');
    if (headerActions) headerActions.style.display = 'none';

    // Hide right-group buttons not relevant to shared view
    for (const id of ['trophy-btn', 'suggest-btn', 'tutorial-btn']) {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    }

    // Ensure share + about buttons are visible
    for (const id of ['share-btn', 'about-btn']) {
      const el = document.getElementById(id);
      if (el) {
        el.style.display = '';
        el.disabled = false;
      }
    }

    // Override share button to copy the shared URL (not open the share modal)
    const shareBtn = document.getElementById('share-btn');
    if (shareBtn) {
      const newBtn = shareBtn.cloneNode(true);
      shareBtn.parentNode.replaceChild(newBtn, shareBtn);
      newBtn.addEventListener('click', () => {
        const url = window.location.origin + '/mapper/?t=' + tokenString;
        navigator.clipboard.writeText(url).then(() => {
          const icon = newBtn.querySelector('i');
          if (icon) {
            const origClass = icon.className;
            icon.className = 'fa-solid fa-check';
            setTimeout(() => { icon.className = origClass; }, 2000);
          }
        });
      });
    }
  }
}
