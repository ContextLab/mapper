// Tutorial mode — state machine, modal rendering, step logic

const STORAGE_KEY = 'mapper-tutorial';
const HIGHLIGHT_PAD = 8;
const MODAL_MAX_WIDTH = 360;
const MOBILE_BP = 480;

// ── Step definitions ────────────────────────────────────────────────
const STEPS = [
  {
    id: 1, title: 'Your Knowledge Map', subSteps: [
      { highlight: '#map-container', message: 'This is your Knowledge Map. Related topics cluster nearby, and colors show your knowledge level \u2014 green for strong, red for gaps.', advanceOn: 'click' },
      { highlight: '#quiz-panel', message: 'Answer questions here to build your map. Each answer adds data about what you know.', advanceOn: 'click' },
      { highlight: '#video-panel', message: 'Explore video recommendations here to fill knowledge gaps.', advanceOn: 'click', skipOnMobile: true },
    ]
  },
  {
    id: 2, title: 'Try It!', highlight: '#quiz-panel',
    message: "Let's try answering a question!",
    messageReturning: 'Your map already has some data \u2014 let\u2019s explore further!',
    advanceOn: 'answer',
  },
  {
    id: 3, title: 'Building Your Map', advanceOn: 'answer', questionTarget: 4,
    message: 'Great work! Notice how the map is developing. Each answer refines your knowledge profile.',
  },
  {
    id: 4, title: 'Skipping Questions', highlight: '.skip-btn, [data-action="skip"]',
    conditional: 'skipNotUsed',
    message: 'Not sure about a question? You can skip it \u2014 the system notes this topic might be unfamiliar.',
    advanceOn: 'any',
  },
  {
    id: 5, title: 'Switch Domains', highlight: '.domain-dropdown, #domain-select',
    message: 'Try exploring a different domain! Select one from the dropdown.',
    advanceOn: 'domain-change',
    postMessage: 'Great choice! Each domain reveals different areas of your knowledge map.',
  },
  {
    id: 6, title: 'Explore Another Domain', advanceOn: 'answer', questionTarget: 2,
    message: 'Answer a few questions in this domain to see how different map regions develop.',
  },
  {
    id: 7, title: 'Discover Features', subSteps: [
      { highlight: '#trophy-btn', message: 'Your estimated strongest topics, ranked. Tap to explore!', advanceOn: 'click' },
      { highlight: '#suggest-btn', message: 'Videos picked for your biggest knowledge gaps. Watching these gives you the largest boost!', advanceOn: 'click' },
      { highlight: '.share-btn, [data-action="share"]', message: 'Share your knowledge map with friends!', advanceOn: 'click' },
    ]
  },
  {
    id: 8, title: "You're Ready!", advanceOn: 'click', isCompletion: true,
  },
];

// ── Internal state ──────────────────────────────────────────────────
let state = null;
let _questionsAnsweredInStep = 0;
const prefersReducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ── Persistence ─────────────────────────────────────────────────────
function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveState() {
  if (!state) return;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* noop */ }
}

function defaultState() {
  return {
    completed: false,
    dismissed: false,
    step: 1,
    subStep: 1,
    hasSkippedQuestion: false,
    skipToastShown: false,
    returningUser: false,
  };
}

// ── Public API ──────────────────────────────────────────────────────

/**
 * Initialise the tutorial. Called once from app.js after first render.
 * @param {{ responsesCount?: number }} appState
 */
export function initTutorial(appState = {}) {
  const saved = loadState();

  if (saved && (saved.completed || saved.dismissed)) {
    state = saved;
    return; // don't start
  }

  if (saved) {
    // resume in-progress tutorial
    state = { ...defaultState(), ...saved };
  } else {
    state = defaultState();
  }

  state.returningUser = (appState.responsesCount || 0) > 0;
  _questionsAnsweredInStep = 0;
  saveState();
  renderCurrentStep();
}

/**
 * Advance the tutorial in response to an app event.
 * @param {'answer'|'skip'|'domain-change'|'click'|'dismiss'} event
 */
export function advanceTutorial(event) {
  if (!state || state.completed || state.dismissed) return;

  // Handle skip events globally — track hasSkippedQuestion
  if (event === 'skip') {
    if (!state.hasSkippedQuestion) {
      state.hasSkippedQuestion = true;
      if (!state.skipToastShown) {
        state.skipToastShown = true;
        showToast('Noted! The system now knows this topic might be unfamiliar.');
      }
      saveState();
    }
  }

  if (event === 'dismiss') {
    dismissTutorial();
    return;
  }

  const stepDef = getStepDef(state.step);
  if (!stepDef) { completeTutorial(); return; }

  // Steps with subSteps
  if (stepDef.subSteps) {
    const sub = resolveSubStep(stepDef, state.subStep);
    if (!sub) { moveToNextStep(); return; }
    if (sub.advanceOn === event || event === 'click') {
      const nextSub = nextValidSubStep(stepDef, state.subStep + 1);
      if (nextSub !== null) {
        state.subStep = nextSub;
        _questionsAnsweredInStep = 0;
        saveState();
        renderCurrentStep();
      } else {
        moveToNextStep();
      }
    }
    return;
  }

  // Steps with questionTarget — need N answers
  if (stepDef.questionTarget && stepDef.advanceOn === 'answer') {
    if (event === 'answer' || event === 'skip') {
      _questionsAnsweredInStep++;
      if (_questionsAnsweredInStep >= stepDef.questionTarget) {
        moveToNextStep();
      }
    }
    return;
  }

  // advanceOn === 'any' — any event advances
  if (stepDef.advanceOn === 'any') {
    if (stepDef.postMessage) {
      showToast(stepDef.postMessage);
    }
    moveToNextStep();
    return;
  }

  // Normal step — advance when event matches
  if (stepDef.advanceOn === event) {
    if (stepDef.postMessage) {
      showToast(stepDef.postMessage);
    }
    moveToNextStep();
  }
}

/** Dismiss and stop the tutorial without completing it. */
export function dismissTutorial() {
  if (!state) state = defaultState();
  state.dismissed = true;
  saveState();
  removeOverlay();
}

/** Reset all tutorial state and restart from step 1. */
export function resetTutorial() {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
  state = defaultState();
  _questionsAnsweredInStep = 0;
  saveState();
  renderCurrentStep();
}

/** Whether the tutorial is currently active (not completed/dismissed). */
export function isTutorialActive() {
  return !!(state && !state.completed && !state.dismissed);
}

/** Return the current { step, subStep } or null. */
export function getTutorialStep() {
  if (!isTutorialActive()) return null;
  return { step: state.step, subStep: state.subStep };
}

// ── Step navigation helpers ─────────────────────────────────────────

function getStepDef(id) {
  return STEPS.find(s => s.id === id) || null;
}

function moveToNextStep() {
  const nextId = state.step + 1;
  const nextDef = getStepDef(nextId);
  if (!nextDef) { completeTutorial(); return; }

  // Skip conditional steps
  if (nextDef.conditional === 'skipNotUsed' && state.hasSkippedQuestion) {
    state.step = nextId;
    state.subStep = 1;
    _questionsAnsweredInStep = 0;
    saveState();
    moveToNextStep();
    return;
  }

  state.step = nextId;
  state.subStep = nextDef.subSteps ? nextValidSubStep(nextDef, 1) || 1 : 1;
  _questionsAnsweredInStep = 0;
  saveState();
  renderCurrentStep();
}

function completeTutorial() {
  if (!state) state = defaultState();
  state.completed = true;
  saveState();
  removeOverlay();
}

/** Resolve a subStep index, skipping mobile-only entries when needed. */
function resolveSubStep(stepDef, idx) {
  if (!stepDef.subSteps) return null;
  const sub = stepDef.subSteps[idx - 1];
  if (!sub) return null;
  if (sub.skipOnMobile && isMobile()) return null;
  return sub;
}

function nextValidSubStep(stepDef, from) {
  if (!stepDef.subSteps) return null;
  for (let i = from; i <= stepDef.subSteps.length; i++) {
    const s = stepDef.subSteps[i - 1];
    if (s.skipOnMobile && isMobile()) continue;
    return i;
  }
  return null;
}

function isMobile() {
  return typeof window !== 'undefined' && window.innerWidth <= MOBILE_BP;
}

// ── Rendering ───────────────────────────────────────────────────────

function renderCurrentStep() {
  const stepDef = getStepDef(state.step);
  if (!stepDef) { completeTutorial(); return; }

  let highlight = stepDef.highlight || null;
  let message = stepDef.message || '';
  const title = stepDef.title || '';

  // SubStep handling
  if (stepDef.subSteps) {
    const sub = resolveSubStep(stepDef, state.subStep);
    if (!sub) { moveToNextStep(); return; }
    highlight = sub.highlight || highlight;
    message = sub.message || message;
  }

  // Returning-user alternate message
  if (stepDef.messageReturning && state.returningUser) {
    message = stepDef.messageReturning;
  }

  // Completion step
  if (stepDef.isCompletion) {
    message = buildCompletionMessage();
  }

  const advanceOn = stepDef.subSteps
    ? (resolveSubStep(stepDef, state.subStep)?.advanceOn || 'click')
    : (stepDef.advanceOn || 'click');
  const isFinish = !!stepDef.isCompletion;
  const showNextBtn = advanceOn === 'click' || isFinish;

  renderOverlay(highlight, title, message, showNextBtn, isFinish);
}

function buildCompletionMessage() {
  return "You're all set! Keep answering questions to refine your map.\n\nYour strongest: [domain]\nMost room to grow: [domain]\n\nYou can replay the tutorial anytime from Settings.";
}

// ── Overlay & Modal DOM ─────────────────────────────────────────────

function removeOverlay() {
  const overlay = document.getElementById('tutorial-overlay');
  if (overlay) overlay.remove();
  const modal = document.getElementById('tutorial-modal');
  if (modal) modal.remove();
  // Remove highlight classes
  document.querySelectorAll('.tutorial-highlight').forEach(el =>
    el.classList.remove('tutorial-highlight'));
}

function renderOverlay(highlightSelector, title, message, showNextBtn, isFinish) {
  removeOverlay();

  // Overlay
  const overlay = document.createElement('div');
  overlay.id = 'tutorial-overlay';
  Object.assign(overlay.style, {
    position: 'fixed',
    inset: '0',
    zIndex: '9998',
    background: 'rgba(0,0,0,0.5)',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms var(--ease-emphasized-decel, ease)',
  });

  // Clip-path cutout for highlighted element
  let highlightEl = null;
  if (highlightSelector) {
    highlightEl = queryFirst(highlightSelector);
  }

  if (highlightEl) {
    const rect = highlightEl.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const x1 = Math.max(0, rect.left - HIGHLIGHT_PAD);
    const y1 = Math.max(0, rect.top - HIGHLIGHT_PAD);
    const x2 = Math.min(vw, rect.right + HIGHLIGHT_PAD);
    const y2 = Math.min(vh, rect.bottom + HIGHLIGHT_PAD);

    overlay.style.clipPath = `polygon(
      0% 0%, 0% 100%, ${x1}px 100%, ${x1}px ${y1}px,
      ${x2}px ${y1}px, ${x2}px ${y2}px, ${x1}px ${y2}px,
      ${x1}px 100%, 100% 100%, 100% 0%
    )`;

    highlightEl.classList.add('tutorial-highlight');
  }

  // Prevent clicks through overlay (except on highlighted element)
  overlay.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  document.body.appendChild(overlay);

  // Modal
  const modal = document.createElement('div');
  modal.id = 'tutorial-modal';

  const mobile = isMobile();
  Object.assign(modal.style, {
    position: 'fixed',
    zIndex: '9999',
    background: 'var(--color-bg, #ffffff)',
    color: 'var(--color-text, #0f172a)',
    maxWidth: mobile ? 'none' : `${MODAL_MAX_WIDTH}px`,
    padding: '20px',
    borderRadius: mobile ? '12px 12px 0 0' : '12px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
    border: '1px solid var(--color-border, rgba(226,232,240,0.8))',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: '1.5',
    opacity: '0',
    transform: prefersReducedMotion() ? 'none' : 'translateY(8px)',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms var(--ease-emphasized-decel, ease), transform 300ms var(--ease-emphasized-decel, ease)',
  });

  if (mobile) {
    Object.assign(modal.style, { bottom: '0', left: '0', right: '0' });
  }

  // Build content via DOM (no innerHTML)
  buildModalDOM(modal, title, message, showNextBtn, isFinish);

  document.body.appendChild(modal);

  // Position modal near highlight (desktop only, non-completion)
  if (!mobile && highlightEl && !isFinish) {
    positionModal(modal, highlightEl);
  } else if (!mobile) {
    // Center
    Object.assign(modal.style, {
      top: '50%', left: '50%',
      transform: prefersReducedMotion() ? 'translate(-50%,-50%)' : 'translate(-50%,-50%) translateY(8px)',
    });
  }

  // Animate in
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      modal.style.opacity = '1';
      if (!mobile && highlightEl && !isFinish) {
        modal.style.transform = 'translateY(0)';
      } else if (!mobile) {
        modal.style.transform = 'translate(-50%,-50%)';
      } else {
        modal.style.transform = 'translateY(0)';
      }
    });
  });
}

function buildModalDOM(modal, title, message, showNextBtn, isFinish) {
  // Dismiss button
  const dismissBtn = document.createElement('button');
  dismissBtn.className = 'tutorial-dismiss';
  dismissBtn.setAttribute('aria-label', 'Close tutorial');
  Object.assign(dismissBtn.style, {
    position: 'absolute', top: '8px', right: '8px', background: 'none',
    border: 'none', color: 'var(--color-text-muted, #64748b)', fontSize: '20px', cursor: 'pointer',
    padding: '4px 8px', lineHeight: '1',
  });
  dismissBtn.textContent = '\u00d7';
  dismissBtn.addEventListener('click', () => dismissTutorial());
  modal.appendChild(dismissBtn);

  // Title
  const titleEl = document.createElement('div');
  Object.assign(titleEl.style, { fontWeight: '700', fontSize: '1.1em', marginBottom: '8px', color: 'var(--color-primary, #00693e)' });
  titleEl.textContent = title;
  modal.appendChild(titleEl);

  // Message — split on newlines, each line as a paragraph
  const msgContainer = document.createElement('div');
  Object.assign(msgContainer.style, { fontSize: '0.95em', color: 'var(--color-text-muted, #64748b)' });
  const lines = message.split('\n');
  for (const line of lines) {
    if (line.trim() === '') {
      msgContainer.appendChild(document.createElement('br'));
    } else {
      const p = document.createElement('p');
      Object.assign(p.style, { margin: '0.4em 0' });
      p.textContent = line;
      msgContainer.appendChild(p);
    }
  }
  modal.appendChild(msgContainer);

  // Footer row
  const footer = document.createElement('div');
  Object.assign(footer.style, {
    marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  });

  const skipLink = document.createElement('a');
  skipLink.href = '#';
  skipLink.className = 'tutorial-skip-link';
  Object.assign(skipLink.style, {
    color: 'var(--color-text-muted, #64748b)', fontSize: '0.85em', textDecoration: 'underline', cursor: 'pointer',
  });
  skipLink.textContent = 'Skip Tutorial';
  skipLink.addEventListener('click', (e) => { e.preventDefault(); dismissTutorial(); });
  footer.appendChild(skipLink);

  if (showNextBtn) {
    const nextBtn = document.createElement('button');
    nextBtn.className = 'tutorial-next-btn';
    Object.assign(nextBtn.style, {
      background: 'var(--color-primary, #00693e)', color: '#fff', border: 'none',
      padding: '8px 20px', borderRadius: '8px', fontSize: '0.95em', cursor: 'pointer',
      fontWeight: '600',
    });
    nextBtn.textContent = isFinish ? 'Finish' : 'Next';
    nextBtn.addEventListener('click', () => advanceTutorial('click'));
    footer.appendChild(nextBtn);
  }

  modal.appendChild(footer);

  // Replay link for completion step
  if (isFinish) {
    const replayP = document.createElement('p');
    Object.assign(replayP.style, { marginTop: '12px', fontSize: '0.8em', color: 'var(--color-text-muted, #64748b)' });
    const replayLink = document.createElement('a');
    replayLink.href = '#';
    replayLink.className = 'tutorial-replay-btn';
    Object.assign(replayLink.style, { color: '#888', textDecoration: 'underline' });
    replayLink.textContent = 'Replay tutorial';
    replayLink.addEventListener('click', (e) => { e.preventDefault(); resetTutorial(); });
    replayP.appendChild(replayLink);
    modal.appendChild(replayP);
  }
}

function positionModal(modal, highlightEl) {
  const rect = highlightEl.getBoundingClientRect();
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const gap = 16;

  // Prefer placing below; fall back to above, then right, then left
  const mw = MODAL_MAX_WIDTH;
  let left = Math.max(12, Math.min(rect.left, vw - mw - 12));
  let top = rect.bottom + gap + HIGHLIGHT_PAD;

  if (top + 200 > vh) {
    // try above
    top = rect.top - gap - HIGHLIGHT_PAD - 200;
    if (top < 12) {
      // place to the right
      top = Math.max(12, rect.top);
      left = rect.right + gap + HIGHLIGHT_PAD;
      if (left + mw > vw) {
        // place to the left
        left = rect.left - gap - HIGHLIGHT_PAD - mw;
        if (left < 12) left = 12;
      }
    }
  }

  Object.assign(modal.style, {
    top: `${Math.max(12, top)}px`,
    left: `${left}px`,
  });
}

// ── Toast ───────────────────────────────────────────────────────────

function showToast(msg) {
  const existing = document.getElementById('tutorial-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'tutorial-toast';
  Object.assign(toast.style, {
    position: 'fixed',
    bottom: '24px',
    left: '50%',
    transform: 'translateX(-50%)',
    background: '#333',
    color: '#fff',
    padding: '12px 24px',
    borderRadius: '8px',
    fontSize: '0.9em',
    zIndex: '10000',
    maxWidth: '320px',
    textAlign: 'center',
    opacity: '0',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms ease',
  });
  toast.textContent = msg;
  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = '1';
  });

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 350);
  }, 3000);
}

// ── Utilities ───────────────────────────────────────────────────────

/** Query first matching element from a potentially comma-separated selector. */
function queryFirst(selector) {
  const parts = selector.split(',').map(s => s.trim());
  for (const s of parts) {
    try {
      const el = document.querySelector(s);
      if (el) return el;
    } catch { /* invalid selector, skip */ }
  }
  return null;
}
