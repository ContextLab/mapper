/** Main application entry point — wires state, domain loading, estimator, and renderer. */

import { validateSchema, isAvailable } from './state/persistence.js';
import {
  $activeDomain,
  $responses,
  $estimates,
  $answeredIds,
  $domainCache,
} from './state/store.js';
import * as registry from './domain/registry.js';
import { load as loadDomain } from './domain/loader.js';
import { indexQuestions } from './domain/questions.js';
import { Estimator } from './learning/estimator.js';
import { Renderer } from './viz/renderer.js';
import { announce, setupKeyboardNav } from './utils/accessibility.js';

let renderer = null;
let estimator = null;
let currentDomainBundle = null;
let keyboardCleanup = null;

async function boot() {
  const storageAvailable = isAvailable();
  if (!storageAvailable) {
    showNotice('Progress won\u2019t be saved across visits (localStorage unavailable).');
  }

  const schemaOk = validateSchema();
  if (!schemaOk && storageAvailable) {
    showNotice('Previous progress was from an older version and could not be restored.');
  }

  try {
    await registry.init();
  } catch (err) {
    console.error('[app] Failed to load domain registry:', err);
    showLandingError('Could not load domain data. Please try refreshing.');
    return;
  }

  renderer = new Renderer();
  renderer.init({
    container: document.getElementById('map-container'),
    onViewportChange: handleViewportChange,
    onCellClick: handleCellClick,
  });

  estimator = new Estimator();

  // Expose for console debugging (Phase 2 checkpoint)
  if (import.meta.env.DEV) {
    window.__mapper = { registry, estimator, renderer, $activeDomain, $estimates, $responses };
  }

  keyboardCleanup = setupKeyboardNav({
    onEscape: handleEscape,
  });

  renderDomainSelector();
  wireSubscriptions();

  announce('Wikipedia Knowledge Map loaded. Select a domain to begin.');
}

function wireSubscriptions() {
  $activeDomain.subscribe(async (domainId) => {
    if (!domainId) return;
    await switchDomain(domainId);
  });

  $responses.subscribe(() => {
    if (!estimator || !currentDomainBundle) return;
    const estimates = estimator.predict();
    $estimates.set(estimates);
  });

  $estimates.subscribe((estimates) => {
    if (!renderer || !currentDomainBundle) return;
    renderer.setHeatmap(estimates, currentDomainBundle.domain.region);
  });
}

async function switchDomain(domainId) {
  const landing = document.getElementById('landing');
  if (landing) landing.classList.add('hidden');

  const quizPanel = document.getElementById('quiz-panel');

  try {
    const bundle = await loadDomain(domainId, {
      onProgress: ({ percent }) => updateProgress(percent),
      onError: (err) => {
        console.error('[app] Domain load failed:', err);
        announce(`Failed to load domain. ${err.message}`);
      },
    });

    currentDomainBundle = bundle;
    indexQuestions(bundle.questions);

    const domain = bundle.domain;
    estimator.init(domain.grid_size, domain.region);

    // Restore prior responses for cross-domain knowledge persistence
    const allResponses = $responses.get();
    if (allResponses.length > 0) {
      const relevantResponses = allResponses.filter(
        (r) => r.x != null && r.y != null
      );
      estimator.restore(relevantResponses);
    }

    const estimates = estimator.predict();
    $estimates.set(estimates);

    renderer.setPoints(
      bundle.articles.map((a) => ({
        id: a.title,
        x: a.x,
        y: a.y,
        z: a.z || 0,
        type: 'article',
        color: [180, 180, 220, 100],
        radius: 2,
        title: a.title,
      }))
    );

    renderer.setLabels(bundle.labels);
    await renderer.transitionTo(domain.region);

    if (quizPanel) quizPanel.removeAttribute('hidden');
    hideProgress();

    announce(`Loaded ${domain.name}. ${bundle.questions.length} questions available.`);
  } catch (err) {
    hideProgress();
    console.error('[app] switchDomain failed:', err);
  }
}

function renderDomainSelector() {
  const selectorContainer = document.querySelector('.domain-selector');
  if (!selectorContainer) return;

  const hierarchy = registry.getHierarchy();
  const select = document.createElement('select');
  select.setAttribute('aria-label', 'Select knowledge domain');
  select.id = 'domain-select';

  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = 'Choose a domain\u2026';
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  for (const node of hierarchy) {
    const opt = document.createElement('option');
    opt.value = node.id;
    opt.textContent = node.name;
    select.appendChild(opt);

    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        const childOpt = document.createElement('option');
        childOpt.value = child.id;
        childOpt.textContent = `\u00A0\u00A0\u00A0${child.name}`;
        select.appendChild(childOpt);
      }
    }
  }

  select.addEventListener('change', (e) => {
    if (e.target.value) {
      $activeDomain.set(e.target.value);
    }
  });

  selectorContainer.innerHTML = '';
  selectorContainer.appendChild(select);
  selectorContainer.removeAttribute('hidden');
}

function handleViewportChange(_viewport) {
  // Viewport tracking for future minimap + viewport-restricted sampling
}

function handleCellClick(_gx, _gy) {
  // Cell click handling for future question targeting
}

function handleEscape() {
  const aboutModal = document.getElementById('about-modal');
  if (aboutModal && !aboutModal.hidden) {
    aboutModal.hidden = true;
    return;
  }
  const quizPanel = document.getElementById('quiz-panel');
  if (quizPanel && !quizPanel.hidden) {
    quizPanel.hidden = true;
  }
}

function showNotice(message) {
  console.warn('[mapper]', message);
  announce(message);
}

function showLandingError(message) {
  const landing = document.getElementById('landing');
  if (landing) {
    const p = landing.querySelector('p');
    if (p) p.textContent = message;
  }
}

function updateProgress(percent) {
  const overlay = document.getElementById('progress-overlay');
  if (!overlay) return;
  overlay.style.background = `linear-gradient(to right, var(--color-primary) ${percent}%, transparent ${percent}%)`;
  overlay.setAttribute('aria-valuenow', String(percent));
}

function hideProgress() {
  const overlay = document.getElementById('progress-overlay');
  if (overlay) {
    overlay.style.background = 'transparent';
    overlay.removeAttribute('aria-valuenow');
  }
}

// Wire the about button
function setupAboutModal() {
  const btn = document.getElementById('about-btn');
  const modal = document.getElementById('about-modal');
  if (!btn || !modal) return;

  btn.addEventListener('click', () => {
    modal.hidden = !modal.hidden;
  });

  const closeBtn = modal.querySelector('.close-modal');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      modal.hidden = true;
    });
  }
}

// Boot on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setupAboutModal();
    boot();
  });
} else {
  setupAboutModal();
  boot();
}

export default boot;
