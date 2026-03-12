// Tutorial mode — state machine, modal rendering, step logic

const STORAGE_KEY = 'mapper-tutorial';
const MODAL_MAX_WIDTH = 380;
const MOBILE_BP = 480;
const HIGHLIGHT_REFRESH_MS = 200;

// ── Step definitions ────────────────────────────────────────────────
// advanceOn: event that moves to next step/substep
// onEnter: comma-separated actions to run when entering (openQuiz, closeQuiz, openVideo, closeVideo, closeModals)
// arrowTarget: selector for animated arrow
// arrowSide: 'left'|'right'|'above'|'below' — which side of target to place arrow
// removeOverlayOnAction: remove graying when the advanceOn action occurs
// followUp: { message, advanceOn } — second phase after the initial action
// showFeedback: show answer/skip feedback in-modal (step 4 only)
const STEPS = [
  {
    id: 1, title: 'Your Knowledge Map', subSteps: [
      {
        title: 'Your Knowledge Map',
        highlight: '#map-container',
        message: 'This is your *knowledge map*: a representation of everything you know! Each location on the map represents a different concept. You can zoom out to see an overview, or zoom in to see fine details.',
        advanceOn: 'click',
      },
      {
        title: 'Your Knowledge Map',
        highlight: '#map-container',
        message: () => {
          const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
          const verb = touch ? 'Drag your finger over' : 'Hover over';
          return `${verb} different locations to see what sorts of concepts "live" nearby. We've included thousands of Wikipedia articles and Khan Academy videos as "landmarks" to help give a sense of the landscape! ${touch ? 'Tap' : 'Click'} on anything to read the article or see the video.`;
        },
        advanceOn: 'click',
      },
    ]
  },
  {
    id: 2, title: 'The Quiz Panel',
    arrowTarget: '#quiz-toggle',
    arrowSide: 'above',
    positionHint: 'quiz-final',
    onEnter: 'openQuiz',
    message: () => {
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      return `Questions appear here. Answer them to build your map. ${touch ? 'Tap' : 'Click'} the toggle arrow to open and close this panel.`;
    },
    advanceOn: 'click',
  },
  {
    id: 3, title: 'Video Sidebar', subSteps: [
      {
        title: 'Video Sidebar',
        arrowTarget: '#video-toggle',
        arrowSide: 'above',
        positionHint: 'video-final',
        onEnter: 'closeQuiz,openVideo',
        message: 'Every video in our dataset lives at a different location on the map. This menu shows all of the videos contained within the current map view. The list adjusts dynamically as you zoom and pan.',
        advanceOn: 'click',
      },
      {
        title: 'Video Sidebar',
        positionHint: 'video-final',
        message: () => {
          const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
          const verb = touch ? 'Drag your finger over' : 'Hover over';
          return `${verb} any video in the list to see its *trajectory*: the "path" of concepts it touches on from moment to moment. ${touch ? 'Tap' : 'Click'} on any video to watch it!`;
        },
        advanceOn: 'click',
      },
    ]
  },
  {
    id: 4, title: 'Try Answering a Question',
    positionHint: 'quiz-final',
    onEnter: 'closeVideo,openQuiz',
    message: "Now let's start mapping your knowledge! Pick whatever answer you think is correct. If you don't know, just press the skip button. Our system learns with each question you answer. Knowing what you don't know tells us something too!",
    advanceOn: 'answer', // also responds to 'skip'
    showFeedback: true,
    removeOverlayOnAction: true,
  },
  {
    id: 5, title: 'Building Your Map', subSteps: [
      {
        title: 'Building Your Map',
        positionHint: 'quiz-final',
        message: 'Answer a few more questions and see how your map updates.',
        advanceOn: 'answer',
        questionTarget: 3,
      },
      {
        title: 'Building Your Map',
        positionHint: 'quiz-final',
        arrowTarget: '.auto-advance-label',
        arrowSide: 'right',
        message: () => {
          const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
          return `Try toggling the "Auto-advance" switch. Pausing after each question gives you a chance to review the correct answer. You can also ${touch ? 'tap' : 'click on'} the Wikipedia and Khan Academy links to learn more.`;
        },
        advanceOn: 'toggle-auto-advance',
      },
      {
        title: 'Building Your Map',
        positionHint: 'quiz-final',
        message: "Answer one more question to see how things work when auto-advance is disabled. Then we'll re-enable auto-advance and move on.",
        advanceOn: 'answer',
        questionTarget: 1,
      },
    ]
  },
  {
    id: 6, title: 'Deep Dive!',
    highlight: '.quiz-feedback-area',
    positionHint: 'left',
    onEnter: 'openQuiz,enableAutoAdvance',
    message: () => {
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      return `Every question has an associated Wikipedia article and/or Khan Academy video. ${touch ? 'Tap' : 'Click'} the buttons to view. If you answer incorrectly or skip a question, you can see the correct answer highlighted in green. Remember: every mistake is an opportunity to learn and grow!`;
    },
    advanceOn: 'click',
  },
  {
    id: 7, title: 'Question Modes',
    highlight: '.modes-wrapper',
    onEnter: 'closeModals,openQuiz,enableAutoAdvance',
    message: 'These buttons let you control the difficulty of your next question. "Give me an easy one" picks a question the system thinks you\'ll get right. "Challenge me" picks a hard question. "Test my weak spots" focuses on areas where your knowledge seems weakest.',
    advanceOn: 'click',
  },
  {
    id: 8, title: 'Save & Load Progress',
    highlight: '.header-actions',
    positionHint: 'left',
    onEnter: 'closeModals',
    message: 'Use these buttons to export your progress (download a file), import previously saved progress, or reset and start fresh.',
    advanceOn: 'click',
  },
  {
    id: 9, title: 'Switch Domains',
    highlight: '.domain-selector',
    message: 'Select a different knowledge domain from the dropdown menu to focus in on that part of your map!',
    arrowTarget: '.domain-selector .custom-select-trigger',
    arrowSide: 'right',
    advanceOn: 'domain-change',
    removeOverlayOnAction: true,
  },
  {
    id: 10, title: 'Exploring Domain-Specific Knowledge',
    positionHint: 'left',
    advanceOn: 'answer',
    questionTarget: 2,
    dynamicMessage: true, // message set in renderCurrentStep based on selected domain
    onEnter: 'openQuiz',
  },
  {
    id: 11, title: 'Your Expertise',
    highlight: '#trophy-btn',
    positionHint: 'right',
    message: () => {
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      return `As you answer questions, the system builds a picture of your knowledge. ${touch ? 'Tap' : 'Click'} this button to see how your answers are shaping up so far. Keep in mind, it gets more accurate with more questions!`;
    },
    advanceOn: 'expertise-click',
    removeOverlayOnAction: true,
    followUp: { dynamicMessage: true, advanceOn: 'click' },
  },
  {
    id: 12, title: 'Fill in Your Knowledge Gaps!',
    highlight: '#suggest-btn',
    positionHint: 'right',
    onEnter: 'closeModals',
    message: () => {
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      return `${touch ? 'Tap' : 'Click'} this button to see recommended Khan Academy videos based on your answers so far. These suggestions will become more targeted as you answer more questions!`;
    },
    advanceOn: 'suggest-click',
    removeOverlayOnAction: true,
    followUp: { message: () => { const t = 'ontouchstart' in window || navigator.maxTouchPoints > 0; return `${t ? 'Tap' : 'Click'} on any video to watch it!`; }, advanceOn: 'click' },
  },
  {
    id: 13, title: 'Share Your Map',
    highlight: '#share-btn',
    positionHint: 'right',
    onEnter: 'closeModals',
    message: () => {
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      return `${touch ? 'Tap' : 'Click'} this button to share your map on social media. Try it out!`;
    },
    advanceOn: 'share-click',
    removeOverlayOnAction: true,
    followUp: { message: 'You can share on LinkedIn, X, or Bluesky. You can also download an image of your map to show it off!', advanceOn: 'click' },
  },
  {
    id: 14, title: 'Learn More',
    highlight: '#about-btn',
    positionHint: 'right',
    onEnter: 'closeModals',
    message: () => {
      const touch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      return `Want to learn more about how Knowledge Mapper works? ${touch ? 'Tap' : 'Click'} the "About" button to read about the technique, view the research paper, and explore the methodology behind the system.`;
    },
    advanceOn: 'click',
  },
  {
    id: 15, title: 'Tutorial Complete!',
    advanceOn: 'click',
    onEnter: 'closeModals,showTutorialBtn',
    arrowTarget: '#tutorial-btn',
    arrowSide: 'below',
    isCompletion: true,
  },
];

// ── Internal state ──────────────────────────────────────────────────
let state = null;
let _questionsAnsweredInStep = 0;
let _lastAnswerCorrect = null;
let _lastAnswerSkipped = false;
let _inFollowUp = false; // true when showing follow-up message after initial action
let _highlightInterval = null; // interval for dynamic highlight refresh
let _currentHighlightSelector = null;
let _dragState = null; // { startX, startY, origLeft, origTop } for modal dragging

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
    welcomeShown: false,
    step: 1,
    subStep: 1,
    hasSkippedQuestion: false,
    skipToastShown: false,
    returningUser: false,
  };
}

// ── Public API ──────────────────────────────────────────────────────

export function initTutorial(appState = {}) {
  const saved = loadState();

  // Already dismissed or completed — never re-show
  if (saved && (saved.dismissed || saved.completed)) {
    state = saved;
    return;
  }

  // Welcome prompt was already shown (user accepted tutorial previously).
  // On page refresh + "Map my knowledge!", clear in-progress state silently
  // instead of resuming mid-tutorial.
  if (saved && saved.welcomeShown) {
    state = defaultState();
    state.welcomeShown = true;   // remember we already showed welcome
    state.dismissed = true;       // don't restart automatically
    _questionsAnsweredInStep = 0;
    _inFollowUp = false;
    saveState();
    removeOverlay();
    return;
  }

  state = defaultState();
  state.returningUser = (appState.responsesCount || 0) > 0;
  _questionsAnsweredInStep = 0;
  _inFollowUp = false;
  saveState();

  // Returning users skip the tutorial entirely
  if (state.returningUser) {
    dismissTutorial();
    return;
  }

  // Show welcome prompt instead of immediately starting tutorial
  showWelcomePrompt();
}

export function advanceTutorial(event) {
  if (!state || state.completed || state.dismissed) return;

  if (event === 'dismiss') {
    dismissTutorial();
    return;
  }

  // Track skip usage globally
  if (event === 'skip') {
    if (!state.hasSkippedQuestion) {
      state.hasSkippedQuestion = true;
      saveState();
    }
  }

  const stepDef = getStepDef(state.step);
  if (!stepDef) { completeTutorial(); return; }

  // Handle follow-up state — waiting for click/dismiss after action
  if (_inFollowUp) {
    const fu = stepDef.followUp || (stepDef.subSteps && resolveSubStep(stepDef, state.subStep)?.followUp);
    if (fu && (fu.advanceOn === event || event === 'click' || event === 'modal-dismiss')) {
      _inFollowUp = false;
      moveToNextStep();
    }
    return;
  }

  // Steps with subSteps
  if (stepDef.subSteps) {
    const sub = resolveSubStep(stepDef, state.subStep);
    if (!sub) { moveToNextStep(); return; }

    // SubStep with questionTarget
    if (sub.questionTarget && (sub.advanceOn === 'answer')) {
      if (event === 'answer' || event === 'skip') {
        _questionsAnsweredInStep++;
        if (_questionsAnsweredInStep >= sub.questionTarget) {
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
      }
      return;
    }

    // Normal subStep advance
    if (sub.advanceOn === event || (sub.advanceOn === 'click' && event === 'click')) {
      // Check for follow-up
      if (sub.followUp && !_inFollowUp) {
        _inFollowUp = true;
        if (sub.removeOverlayOnAction) removeOverlayOnly();
        updateModalMessage(typeof sub.followUp.message === 'function' ? sub.followUp.message() : (sub.followUp.message || ''));
        return;
      }

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

  // Step with questionTarget (non-subStep)
  if (stepDef.questionTarget && (stepDef.advanceOn === 'answer')) {
    if (event === 'answer' || event === 'skip') {
      _questionsAnsweredInStep++;
      if (_questionsAnsweredInStep >= stepDef.questionTarget) {
        moveToNextStep();
      }
    }
    return;
  }

  // Step 4 special: showFeedback on answer or skip
  if (stepDef.showFeedback && (event === 'answer' || event === 'skip')) {
    if (stepDef.removeOverlayOnAction) removeOverlayOnly();
    showInModalFeedback(event === 'skip');
    _inFollowUp = true; // wait for Continue click
    return;
  }

  // Normal step — advance when event matches
  if (stepDef.advanceOn === event || (stepDef.advanceOn === 'answer' && event === 'skip')) {
    // Check for follow-up
    if (stepDef.followUp && !_inFollowUp) {
      _inFollowUp = true;
      if (stepDef.removeOverlayOnAction) removeOverlayOnly();
      const fuMsg = stepDef.followUp.dynamicMessage
        ? buildDynamicFollowUp(stepDef)
        : (typeof stepDef.followUp.message === 'function' ? stepDef.followUp.message() : (stepDef.followUp.message || ''));
      updateModalMessage(fuMsg);
      return;
    }

    if (stepDef.removeOverlayOnAction) removeOverlayOnly();
    if (stepDef.postMessage) showToast(stepDef.postMessage);
    moveToNextStep();
    return;
  }

  // 'click' event can advance follow-ups or steps waiting for click
  if (event === 'click' && _inFollowUp) {
    _inFollowUp = false;
    moveToNextStep();
    return;
  }

  // Modal-dismiss events can advance interactive steps
  if (event === 'modal-dismiss' && _inFollowUp) {
    _inFollowUp = false;
    moveToNextStep();
  }
}

function showDismissConfirmation() {
  // Don't stack confirmations
  if (document.getElementById('tutorial-dismiss-confirm')) return;

  const overlay = document.createElement('div');
  overlay.id = 'tutorial-dismiss-confirm';
  Object.assign(overlay.style, {
    position: 'fixed', inset: '0', zIndex: '10005',
    background: 'rgba(0,0,0,0.5)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  });

  const dialog = document.createElement('div');
  Object.assign(dialog.style, {
    background: 'var(--color-bg, #fff)', borderRadius: '12px',
    padding: '24px', maxWidth: '320px', width: '90%',
    boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
    textAlign: 'center', fontFamily: 'var(--font-body, -apple-system, BlinkMacSystemFont, sans-serif)',
  });

  const msg = document.createElement('p');
  Object.assign(msg.style, { margin: '0 0 16px', fontSize: '1rem', color: 'var(--color-text, #0f172a)' });
  msg.textContent = 'Are you sure you want to exit the tutorial?';
  dialog.appendChild(msg);

  const btnRow = document.createElement('div');
  Object.assign(btnRow.style, { display: 'flex', gap: '12px', justifyContent: 'center' });

  const cancelBtn = document.createElement('button');
  Object.assign(cancelBtn.style, {
    padding: '8px 20px', borderRadius: '8px', border: '1.5px solid var(--color-border, #ccc)',
    background: 'var(--color-bg, #fff)', cursor: 'pointer', fontSize: '0.9rem',
  });
  cancelBtn.textContent = 'Cancel';
  cancelBtn.addEventListener('click', () => overlay.remove());

  const exitBtn = document.createElement('button');
  Object.assign(exitBtn.style, {
    padding: '8px 20px', borderRadius: '8px', border: 'none',
    background: 'var(--color-primary, #00693e)', color: '#fff',
    cursor: 'pointer', fontSize: '0.9rem',
  });
  exitBtn.textContent = 'Exit';
  exitBtn.addEventListener('click', () => { overlay.remove(); dismissTutorial(); });

  btnRow.appendChild(cancelBtn);
  btnRow.appendChild(exitBtn);
  dialog.appendChild(btnRow);
  overlay.appendChild(dialog);

  // Click outside to cancel
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

export function dismissTutorial() {
  if (!state) state = defaultState();
  state.dismissed = true;
  saveState();
  removeOverlay();
  stopHighlightRefresh();
  document.body.classList.remove('tutorial-active');
}

export function resetTutorial() {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
  state = defaultState();
  state.welcomeShown = true;  // don't re-show welcome prompt on future refresh
  _questionsAnsweredInStep = 0;
  _inFollowUp = false;
  saveState();
  renderCurrentStep();
}

export function setAnswerFeedback(wasCorrect, wasSkipped = false) {
  _lastAnswerCorrect = wasCorrect;
  _lastAnswerSkipped = wasSkipped;
}

export function isTutorialActive() {
  return !!(state && !state.completed && !state.dismissed);
}

export function getTutorialStep() {
  if (!isTutorialActive()) return null;
  return { step: state.step, subStep: state.subStep };
}

/** Programmatically jump to a specific tutorial step (for testing). */
export function goToStep(step, subStep = 1) {
  if (!state) state = defaultState();
  state.completed = false;
  state.dismissed = false;
  state.welcomeShown = true;
  state.step = step;
  state.subStep = subStep;
  _questionsAnsweredInStep = 0;
  _inFollowUp = false;
  saveState();
  renderCurrentStep();
}

// ── Step navigation helpers ─────────────────────────────────────────

function getStepDef(id) {
  return STEPS.find(s => s.id === id) || null;
}

function moveToNextStep() {
  let nextId = state.step + 1;
  let nextDef = getStepDef(nextId);
  // Skip top-level steps marked skipOnMobile
  while (nextDef && nextDef.skipOnMobile && isMobile()) {
    nextId++;
    nextDef = getStepDef(nextId);
  }
  if (!nextDef) { completeTutorial(); return; }

  state.step = nextId;
  state.subStep = nextDef.subSteps ? nextValidSubStep(nextDef, 1) || 1 : 1;
  _questionsAnsweredInStep = 0;
  _inFollowUp = false;
  saveState();
  renderCurrentStep();
}

function completeTutorial() {
  if (!state) state = defaultState();
  state.completed = true;
  saveState();
  removeOverlay();
  stopHighlightRefresh();
  document.body.classList.remove('tutorial-active');

  // Re-select "All (General)" domain and zoom fully out
  const allOption = document.querySelector('.custom-select-option[data-value="all"]');
  if (allOption) allOption.click();

  // Jump to full view after domain switch settles
  setTimeout(() => {
    const renderer = window.__mapper?.renderer;
    if (renderer) {
      renderer.jumpTo({ x_min: 0, y_min: 0, x_max: 1, y_max: 1 });
    }
  }, 300);
}

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
  if (typeof window === 'undefined') return false;
  if (window.innerWidth <= MOBILE_BP) return true;
  // Landscape phone: short viewport + landscape orientation
  if (window.innerHeight <= 500 && window.matchMedia('(orientation: landscape)').matches) return true;
  return false;
}

// ── Welcome prompt ──────────────────────────────────────────────────

function showWelcomePrompt() {
  removeOverlay();

  const modal = document.createElement('div');
  modal.id = 'tutorial-welcome';

  const mobile = isMobile();
  Object.assign(modal.style, {
    position: 'fixed',
    zIndex: '10002',
    background: 'var(--color-bg, #ffffff)',
    color: 'var(--color-text, #0f172a)',
    maxWidth: mobile ? 'none' : `${MODAL_MAX_WIDTH}px`,
    width: mobile ? 'auto' : `${MODAL_MAX_WIDTH}px`,
    padding: '24px',
    borderRadius: mobile ? '12px 12px 0 0' : '12px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
    border: '1px solid var(--color-border, rgba(226,232,240,0.8))',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: '1.5',
    textAlign: 'center',
    opacity: '0',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms ease',
  });

  if (mobile) {
    Object.assign(modal.style, { bottom: '0', left: '0', right: '0' });
  } else {
    Object.assign(modal.style, {
      top: '50%', left: '50%',
      transform: 'translate(-50%, -50%)',
    });
  }

  const title = document.createElement('div');
  Object.assign(title.style, {
    fontWeight: '700', fontSize: '1.2em',
    color: 'var(--color-primary, #00693e)',
    marginBottom: '12px',
  });
  title.textContent = 'Welcome to Knowledge Mapper!';
  modal.appendChild(title);

  const msg = document.createElement('p');
  Object.assign(msg.style, {
    fontSize: '0.95em',
    color: 'var(--color-text-muted, #64748b)',
    margin: '0 0 20px 0',
  });
  msg.textContent = 'Would you like a quick tour of the interface? It only takes a minute.';
  modal.appendChild(msg);

  const btnRow = document.createElement('div');
  Object.assign(btnRow.style, {
    display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center',
  });

  const yesBtn = document.createElement('button');
  Object.assign(yesBtn.style, {
    background: 'var(--color-primary, #00693e)', color: '#fff', border: 'none',
    padding: '10px 24px', borderRadius: '8px', fontSize: '0.95em', cursor: 'pointer',
    fontWeight: '600', width: '100%',
  });
  yesBtn.textContent = 'Yes, show me around';
  yesBtn.addEventListener('click', () => {
    modal.remove();
    state.welcomeShown = true;
    saveState();
    renderCurrentStep();
  });
  btnRow.appendChild(yesBtn);

  const noBtn = document.createElement('button');
  Object.assign(noBtn.style, {
    background: 'transparent',
    color: 'var(--color-text-muted, #64748b)',
    border: '1px solid var(--color-border, rgba(226,232,240,0.8))',
    padding: '10px 24px', borderRadius: '8px', fontSize: '0.95em', cursor: 'pointer',
    fontWeight: '500', width: '100%',
  });
  noBtn.textContent = "No thanks, I'll explore on my own";
  noBtn.addEventListener('click', () => {
    modal.remove();
    state.welcomeShown = true;
    dismissTutorial();
  });
  btnRow.appendChild(noBtn);

  modal.appendChild(btnRow);
  document.body.appendChild(modal);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      modal.style.opacity = '1';
    });
  });
}

// ── Rendering ───────────────────────────────────────────────────────

function renderCurrentStep() {
  document.body.classList.add('tutorial-active');
  const stepDef = getStepDef(state.step);
  if (!stepDef) { completeTutorial(); return; }
  // Skip top-level steps marked skipOnMobile on render (e.g. resumed state)
  if (stepDef.skipOnMobile && isMobile()) { moveToNextStep(); return; }

  let highlight = stepDef.highlight || null;
  let message = typeof stepDef.message === 'function' ? stepDef.message() : (stepDef.message || '');
  let title = stepDef.title || '';
  let arrowTarget = stepDef.arrowTarget || null;
  let arrowSide = stepDef.arrowSide || 'left';
  let onEnter = stepDef.onEnter || null;
  let positionHint = stepDef.positionHint || null;

  // SubStep handling
  if (stepDef.subSteps) {
    const sub = resolveSubStep(stepDef, state.subStep);
    if (!sub) { moveToNextStep(); return; }
    highlight = sub.highlight ?? highlight;
    message = sub.message ? (typeof sub.message === 'function' ? sub.message() : sub.message) : message;
    title = sub.title || title;
    arrowTarget = sub.arrowTarget ?? arrowTarget;
    arrowSide = sub.arrowSide || arrowSide;
    onEnter = sub.onEnter ?? onEnter;
    positionHint = sub.positionHint ?? positionHint;
  }

  // Dynamic message for step 7 (domain-specific)
  if (stepDef.dynamicMessage || (stepDef.subSteps && resolveSubStep(stepDef, state.subStep)?.dynamicMessage)) {
    message = buildDynamicMessage(stepDef);
  }

  // Completion step
  if (stepDef.isCompletion) {
    message = "You've finished the formal tutorial. You can continue answering questions to refine your map and expand your knowledge!\n\nReplay the tutorial any time using the <span style=\"display:inline-flex;align-items:center;justify-content:center;width:1.3em;height:1.3em;border-radius:50%;background:var(--color-text-muted,#64748b);color:#fff;font-size:0.85em;font-weight:600;vertical-align:text-bottom\">?</span> button near the top of the screen.";
  }

  // Execute onEnter actions
  if (onEnter) {
    for (const action of onEnter.split(',')) {
      executeOnEnter(action.trim());
    }
  }

  const advanceOn = stepDef.subSteps
    ? (resolveSubStep(stepDef, state.subStep)?.advanceOn || 'click')
    : (stepDef.advanceOn || 'click');
  const isFinish = !!stepDef.isCompletion;
  const showNextBtn = advanceOn === 'click' || isFinish;

  renderOverlay(highlight, title, message, showNextBtn, isFinish, arrowTarget, arrowSide, positionHint);
  _currentHighlightSelector = highlight; // Set AFTER renderOverlay (which calls removeOverlay → clears it)
  startHighlightRefresh();
}

function buildDynamicMessage(stepDef) {
  // Step 10 (Exploring Domain-Specific Knowledge): include current domain name
  if (stepDef.id === 10) {
    const domainEl = document.querySelector('.custom-select-value');
    const domain = domainEl?.textContent?.trim() || 'a new domain';
    return `You selected ${domain} from the menu\u2014now all of the questions you see will be focused on this one area. You can go back to mapping general knowledge by selecting "All (General)" from the dropdown menu. But first, try answering a couple of questions in the domain you selected. Remember, you can always skip if you need to!`;
  }
  return '';
}

function buildDynamicFollowUp(stepDef) {
  // Step 11 (Your Expertise): follow-up with top sub-domain areas
  if (stepDef.id === 11) {
    const items = document.querySelectorAll('#insights-modal-body .insights-concept');
    const areas = Array.from(items).slice(0, 3).map(el => el.textContent?.trim()).filter(Boolean);
    if (areas.length >= 3) {
      return `Based on your answers so far, your strongest areas appear to be ${areas[0]}, ${areas[1]}, and ${areas[2]}. Keep answering questions for a more complete picture of your knowledge!`;
    }
    return 'Keep answering questions to see your knowledge profile take shape!';
  }
  return '';
}

/** Show answer/skip feedback within the existing modal (step 4). */
function showInModalFeedback(wasSkipped) {
  const modal = document.getElementById('tutorial-modal');
  if (!modal) return;

  // Determine feedback content
  let feedbackTitle, feedbackMsg, feedbackColor;
  if (wasSkipped) {
    feedbackTitle = 'Skipped';
    feedbackMsg = "Great\u2014you recognized that you didn't know this one! Skipping when you don't know something gives you a little credit. Notice how the map updated: a yellow dot was added to the map to denote which concept this question tested. Since you recognized a gap in your knowledge, the map is shaded slightly red. And areas *around* that question are updated too: a knowledge gap for one concept implies gaps in knowledge about *related* concepts too!";
    feedbackColor = 'var(--color-warning, #d97706)';
  } else if (_lastAnswerCorrect) {
    feedbackTitle = 'Correct!';
    feedbackMsg = "Nice, you got it right! Notice how the map updated: a green dot was added to the map to denote which concept this question tested. And areas *around* that question are updated too: knowledge about one concept implies knowledge about *related* concepts too!";
    feedbackColor = 'var(--color-correct, #059669)';
  } else {
    feedbackTitle = 'Not Quite!';
    feedbackMsg = "You missed that one! Notice how the map updated: a red dot was added to the map to denote which concept this question tested. And areas *around* that question are updated too: a knowledge gap for one concept implies gaps in knowledge about *related* concepts too!";
    feedbackColor = 'var(--color-incorrect, #dc2626)';
  }

  // Update modal content in place
  const titleEl = modal.querySelector('[data-tutorial-title]');
  const msgContainer = modal.querySelector('[data-tutorial-message]');
  const footer = modal.querySelector('[data-tutorial-footer]');

  if (titleEl) {
    titleEl.style.color = feedbackColor;
    titleEl.textContent = feedbackTitle;
  }
  if (msgContainer) {
    msgContainer.innerHTML = '';
    renderMarkdownLite(msgContainer, feedbackMsg);
  }

  // Replace footer with Continue button
  if (footer) {
    footer.innerHTML = '';
    const continueBtn = document.createElement('button');
    continueBtn.className = 'tutorial-next-btn';
    Object.assign(continueBtn.style, {
      background: 'var(--color-primary, #00693e)', color: '#fff', border: 'none',
      padding: '8px 20px', borderRadius: '8px', fontSize: '0.95em', cursor: 'pointer',
      fontWeight: '600', width: '100%',
    });
    continueBtn.textContent = 'Continue';
    continueBtn.addEventListener('click', () => {
      _inFollowUp = false;
      _lastAnswerCorrect = null;
      _lastAnswerSkipped = false;
      moveToNextStep();
    });
    footer.appendChild(continueBtn);
  }
}

/** Update the modal message text (for follow-up states). */
function updateModalMessage(message) {
  const modal = document.getElementById('tutorial-modal');
  if (!modal) return;
  const msgContainer = modal.querySelector('[data-tutorial-message]');
  if (msgContainer) {
    msgContainer.innerHTML = '';
    renderMarkdownLite(msgContainer, message);
  }

  // Ensure Next button is visible
  const footer = modal.querySelector('[data-tutorial-footer]');
  if (footer && !footer.querySelector('.tutorial-next-btn')) {
    const nextBtn = document.createElement('button');
    nextBtn.className = 'tutorial-next-btn';
    Object.assign(nextBtn.style, {
      background: 'var(--color-primary, #00693e)', color: '#fff', border: 'none',
      padding: '8px 20px', borderRadius: '8px', fontSize: '0.95em', cursor: 'pointer',
      fontWeight: '600',
    });
    nextBtn.textContent = 'Next';
    nextBtn.addEventListener('click', () => advanceTutorial('click'));
    footer.appendChild(nextBtn);
  }
}

function executeOnEnter(action) {
  if (action === 'openVideo') {
    const panel = document.getElementById('video-panel');
    const toggleBtn = document.getElementById('video-toggle');
    if (panel && !panel.classList.contains('open')) toggleBtn?.click();
  } else if (action === 'closeVideo') {
    const panel = document.getElementById('video-panel');
    const toggleBtn = document.getElementById('video-toggle');
    if (panel && panel.classList.contains('open')) toggleBtn?.click();
  } else if (action === 'openQuiz') {
    const panel = document.getElementById('quiz-panel');
    const toggleBtn = document.getElementById('quiz-toggle');
    if (panel && !panel.classList.contains('open')) toggleBtn?.click();
  } else if (action === 'closeQuiz') {
    const panel = document.getElementById('quiz-panel');
    const toggleBtn = document.getElementById('quiz-toggle');
    if (panel && panel.classList.contains('open')) toggleBtn?.click();
  } else if (action === 'closeModals') {
    // Close any open app modals (insights/expertise, video suggest, share, recommended videos)
    for (const id of ['insights-modal', 'share-modal', 'video-modal']) {
      const m = document.getElementById(id);
      if (m && !m.hidden) m.hidden = true;
    }
    // Also try generic modal overlays
    document.querySelectorAll('.modal-overlay, .share-overlay').forEach(el => {
      const closeBtn = el.querySelector('.close-modal, .close-btn, [aria-label="Close"]');
      if (closeBtn) closeBtn.click();
      else el.hidden = true;
    });
  } else if (action === 'enableAutoAdvance') {
    // Re-enable auto-advance after the user toggled it off during step 5
    const track = document.querySelector('.auto-advance-track');
    if (track && !track.classList.contains('on')) {
      track.click(); // toggles it on
    }
  } else if (action === 'showTutorialBtn') {
    const tutBtn = document.getElementById('tutorial-btn');
    if (tutBtn) {
      tutBtn.hidden = false;
      // Add highlighted circle style
      tutBtn.classList.add('tutorial-btn-highlight');
    }
  }
}

// ── Dynamic highlight refresh ───────────────────────────────────────

function startHighlightRefresh() {
  stopHighlightRefresh();

  // Start refresh if there's a highlight OR an active arrow (arrow-only steps need repositioning too)
  const hasArrow = !!document.getElementById('tutorial-arrow');
  if (!_currentHighlightSelector && !hasArrow) return;

  _highlightInterval = setInterval(() => {
    const arrowEl = document.getElementById('tutorial-arrow');
    if (!_currentHighlightSelector && !arrowEl) { stopHighlightRefresh(); return; }

    // Reposition arrow (panels may animate after onEnter)
    if (arrowEl && arrowEl._targetSelector) {
      const target = queryFirst(arrowEl._targetSelector);
      if (target) repositionArrow(arrowEl, target, arrowEl._side);
    }
  }, HIGHLIGHT_REFRESH_MS);

  // Also listen for resize
  window.addEventListener('resize', _onResizeHighlight);
}

function stopHighlightRefresh() {
  if (_highlightInterval) { clearInterval(_highlightInterval); _highlightInterval = null; }
  window.removeEventListener('resize', _onResizeHighlight);
}

function _onResizeHighlight() {
  // Reposition arrow on resize (works for both highlight and arrow-only steps)
  const arrowEl = document.getElementById('tutorial-arrow');
  if (arrowEl && arrowEl._targetSelector) {
    const target = queryFirst(arrowEl._targetSelector);
    if (target) repositionArrow(arrowEl, target, arrowEl._side);
  }
}

// ── Overlay & Modal DOM ─────────────────────────────────────────────

function removeOverlay() {
  stopHighlightRefresh();
  const overlay = document.getElementById('tutorial-overlay');
  if (overlay) overlay.remove();
  const modal = document.getElementById('tutorial-modal');
  if (modal) modal.remove();
  const welcome = document.getElementById('tutorial-welcome');
  if (welcome) welcome.remove();
  const arrow = document.getElementById('tutorial-arrow');
  if (arrow) arrow.remove();
  document.querySelectorAll('.tutorial-highlight').forEach(el =>
    el.classList.remove('tutorial-highlight'));
  // Clean up tutorial button highlight
  const tutBtn = document.getElementById('tutorial-btn');
  if (tutBtn) tutBtn.classList.remove('tutorial-btn-highlight');
  _currentHighlightSelector = null;
}

/** Remove only the overlay (graying), keep modal and arrow. */
function removeOverlayOnly() {
  const overlay = document.getElementById('tutorial-overlay');
  if (overlay) overlay.remove();
  document.querySelectorAll('.tutorial-highlight').forEach(el =>
    el.classList.remove('tutorial-highlight'));
  stopHighlightRefresh();
  _currentHighlightSelector = null;
}

function renderArrow(targetEl, side = 'left') {
  const existing = document.getElementById('tutorial-arrow');
  if (existing) existing.remove();

  const arrow = document.createElement('div');
  arrow.id = 'tutorial-arrow';
  arrow._targetSelector = null; // set by caller
  arrow._side = side;

  Object.assign(arrow.style, {
    position: 'fixed',
    zIndex: '10003',
    width: '32px',
    height: '32px',
    pointerEvents: 'none',
  });

  // SVG arrow — direction depends on side
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 32 32');
  svg.setAttribute('width', '32');
  svg.setAttribute('height', '32');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

  let d, animation;
  if (side === 'right') {
    // Arrow pointing left (placed to the right of target)
    d = 'M26 16 L10 16 L16 10 M10 16 L16 22';
    animation = 'tutorialArrowBounceLeft 1s ease-in-out infinite';
  } else if (side === 'above') {
    // Arrow pointing down (placed above target)
    d = 'M16 6 L16 22 L10 16 M16 22 L22 16';
    animation = 'tutorialArrowBounceDown 1s ease-in-out infinite';
  } else if (side === 'below') {
    // Arrow pointing up (placed below target)
    d = 'M16 26 L16 10 L10 16 M16 10 L22 16';
    animation = 'tutorialArrowBounceUp 1s ease-in-out infinite';
  } else {
    // Arrow pointing right (placed to the left of target)
    d = 'M6 16 L22 16 L16 10 M22 16 L16 22';
    animation = 'tutorialArrowBounce 1s ease-in-out infinite';
  }

  path.setAttribute('d', d);
  path.setAttribute('stroke', 'var(--color-primary, #00693e)');
  path.setAttribute('stroke-width', '3');
  path.setAttribute('stroke-linecap', 'round');
  path.setAttribute('stroke-linejoin', 'round');
  path.setAttribute('fill', 'none');
  // Add drop shadow for visibility
  const filter = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  filter.innerHTML = '<filter id="arrow-shadow"><feDropShadow dx="0" dy="0" stdDeviation="2" flood-color="#fff" flood-opacity="0.9"/></filter>';
  svg.appendChild(filter);
  path.setAttribute('filter', 'url(#arrow-shadow)');
  svg.appendChild(path);
  arrow.appendChild(svg);
  arrow.style.animation = animation;

  repositionArrow(arrow, targetEl, side);
  document.body.appendChild(arrow);
  return arrow;
}

function repositionArrow(arrow, targetEl, side) {
  let rect = targetEl.getBoundingClientRect();

  // If target is hidden (zero dimensions), try its parent panel as fallback
  if (rect.width === 0 && rect.height === 0) {
    const panel = targetEl.closest('#video-panel, #quiz-panel');
    if (panel) rect = panel.getBoundingClientRect();
    // Still zero? Hide arrow
    if (rect.width === 0 && rect.height === 0) {
      arrow.style.display = 'none';
      return;
    }
  }
  arrow.style.display = '';

  const size = 32;
  let top, left;

  if (side === 'right') {
    top = rect.top + rect.height / 2 - size / 2;
    left = rect.right + 8;
  } else if (side === 'above') {
    top = rect.top - size - 8;
    left = rect.left + rect.width / 2 - size / 2;
  } else if (side === 'below') {
    top = rect.bottom + 8;
    left = rect.left + rect.width / 2 - size / 2;
  } else {
    top = rect.top + rect.height / 2 - size / 2;
    left = rect.left - size - 8;
  }

  arrow.style.top = `${top}px`;
  arrow.style.left = `${left}px`;
}

function renderOverlay(highlightSelector, title, message, showNextBtn, isFinish, arrowTargetSelector, arrowSide = 'left', positionHint = null) {
  removeOverlay();

  // Overlay
  const overlay = document.createElement('div');
  overlay.id = 'tutorial-overlay';
  let highlightEl = null;
  if (highlightSelector) {
    highlightEl = queryFirst(highlightSelector);
  }

  Object.assign(overlay.style, {
    position: 'fixed',
    inset: '0',
    zIndex: '9998',
    background: highlightEl ? 'transparent' : 'rgba(0,0,0,0.45)',
    pointerEvents: 'none',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms var(--ease-emphasized-decel, ease)',
  });

  if (highlightEl) {
    highlightEl.classList.add('tutorial-highlight');
    // On mobile, scroll the highlighted element into view within its scrollable container
    if (isMobile()) {
      requestAnimationFrame(() => highlightEl.scrollIntoView({ behavior: 'smooth', block: 'center' }));
    }
  }

  document.body.appendChild(overlay);

  // Modal
  const modal = document.createElement('div');
  modal.id = 'tutorial-modal';

  const mobile = isMobile();
  Object.assign(modal.style, {
    position: 'fixed',
    zIndex: '10002',
    background: 'var(--color-bg, #ffffff)',
    color: 'var(--color-text, #0f172a)',
    maxWidth: mobile ? 'none' : `${MODAL_MAX_WIDTH}px`,
    width: mobile ? 'auto' : `${MODAL_MAX_WIDTH}px`,
    padding: '20px',
    borderRadius: mobile ? '12px 12px 0 0' : '12px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
    border: '1px solid var(--color-border, rgba(226,232,240,0.8))',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    lineHeight: '1.5',
    boxSizing: 'border-box',
    overflowY: 'auto',
    maxHeight: 'calc(100vh - 60px)',
    opacity: '0',
    transform: prefersReducedMotion() ? 'none' : 'translateY(8px)',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms var(--ease-emphasized-decel, ease), transform 300ms var(--ease-emphasized-decel, ease), left 300ms var(--ease-emphasized-decel, ease), top 300ms var(--ease-emphasized-decel, ease)',
    cursor: 'default',
  });

  // Mobile landscape positioning — extracted so it can be re-run after panel transitions
  function positionMobileLandscape(m) {
    const headerH = document.getElementById('app-header')?.offsetHeight || 48;
    const topPos = (headerH + 8) + 'px';
    m.style.maxHeight = `calc(100vh - ${headerH + 12}px)`;
    const quizPanel = document.getElementById('quiz-panel');
    const videoPanel = document.getElementById('video-panel');
    const quizOpen = quizPanel?.classList.contains('open');
    const videoOpen = videoPanel?.classList.contains('open');
    const toggleWidth = 36;

    const hintRight = positionHint === 'right' || positionHint === 'video-final';
    const hintLeft = positionHint === 'left' || positionHint === 'quiz-final';
    let placeLeft = hintLeft;
    let placeRight = hintRight;
    if (!placeLeft && !placeRight) {
      placeLeft = !videoOpen;
      placeRight = videoOpen && !quizOpen;
    }

    let availLeft = window.innerWidth;
    let availRight = window.innerWidth;
    if (quizOpen && quizPanel) {
      const qpRect = quizPanel.getBoundingClientRect();
      availLeft = Math.min(availLeft, qpRect.left - toggleWidth);
      availRight = Math.min(availRight, window.innerWidth - qpRect.left);
    }
    if (videoOpen && videoPanel) {
      const vpRect = videoPanel.getBoundingClientRect();
      availRight = Math.min(availRight, window.innerWidth - vpRect.right - toggleWidth);
      availLeft = Math.min(availLeft, vpRect.right);
    }

    const minUsable = 160;
    if (placeLeft && availLeft < minUsable && availRight > availLeft) {
      placeLeft = false; placeRight = true;
    } else if (placeRight && availRight < minUsable && availLeft > availRight) {
      placeRight = false; placeLeft = true;
    }

    const chosenAvail = placeLeft ? availLeft : availRight;
    if (chosenAvail < minUsable) {
      Object.assign(m.style, {
        width: `${MODAL_MAX_WIDTH}px`, maxWidth: '90vw', borderRadius: '12px',
        top: topPos, left: '50%', right: 'auto',
        transform: 'translateX(-50%)',
      });
    } else {
      const usableW = Math.max(Math.min(MODAL_MAX_WIDTH, chosenAvail - 24), minUsable);
      Object.assign(m.style, {
        width: usableW + 'px', maxWidth: usableW + 'px', borderRadius: '12px',
        top: topPos,
      });
      if (placeRight) {
        m.style.right = '12px';
        m.style.left = 'auto';
      } else {
        m.style.left = '12px';
        m.style.right = 'auto';
      }
    }
  }

  if (mobile) {
    const isLandscape = window.matchMedia('(orientation: landscape)').matches;
    if (isLandscape) {
      positionMobileLandscape(modal);
      // Defer reposition to catch panel CSS transitions
      setTimeout(() => positionMobileLandscape(modal), 350);
      setTimeout(() => positionMobileLandscape(modal), 600);
    } else {
      // Portrait: bottom sheet or top bar
      const highlightInBottom = highlightEl && highlightEl.getBoundingClientRect().bottom > window.innerHeight * 0.6;
      const quizOpen = document.getElementById('quiz-panel')?.classList.contains('open');
      const useTop = highlightInBottom || (!highlightEl && quizOpen);
      if (useTop) {
        Object.assign(modal.style, { top: '0', left: '0', right: '0', borderRadius: '0 0 12px 12px' });
      } else {
        Object.assign(modal.style, { bottom: '0', left: '0', right: '0' });
      }
    }
  }

  buildModalDOM(modal, title, message, showNextBtn, isFinish);
  makeDraggable(modal);

  document.body.appendChild(modal);

  // Position modal (immediate + deferred to catch panel transitions)
  if (!mobile && (highlightEl || positionHint) && !isFinish) {
    // Disable transition for initial placement so modal doesn't animate from default position
    modal.style.transition = 'none';
    positionModal(modal, highlightEl, positionHint);
    requestAnimationFrame(() => {
      modal.style.transition = prefersReducedMotion() ? 'none' : 'opacity 300ms var(--ease-emphasized-decel, ease), transform 300ms var(--ease-emphasized-decel, ease), left 300ms var(--ease-emphasized-decel, ease), top 300ms var(--ease-emphasized-decel, ease)';
    });
    setTimeout(() => positionModal(modal, highlightEl, positionHint), 350);
    setTimeout(() => positionModal(modal, highlightEl, positionHint), 600);
    setTimeout(() => positionModal(modal, highlightEl, positionHint), 700);
  } else if (!mobile) {
    Object.assign(modal.style, {
      top: '50%', left: '50%',
      transform: prefersReducedMotion() ? 'translate(-50%,-50%)' : 'translate(-50%,-50%) translateY(8px)',
    });
  }

  // Arrow
  if (arrowTargetSelector) {
    const arrowEl = queryFirst(arrowTargetSelector);
    if (arrowEl) {
      const a = renderArrow(arrowEl, arrowSide);
      a._targetSelector = arrowTargetSelector;
    }
  }

  // Animate in
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      modal.style.opacity = '1';
      if (!mobile && (highlightEl || positionHint) && !isFinish) {
        modal.style.transform = 'none';
      } else if (!mobile) {
        modal.style.transform = 'translate(-50%,-50%)';
      } else {
        modal.style.transform = 'translateY(0)';
      }
    });
  });
}

function buildModalDOM(modal, title, message, showNextBtn, isFinish) {
  // Drag handle + dismiss
  const header = document.createElement('div');
  Object.assign(header.style, {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    marginBottom: '8px', cursor: 'grab', userSelect: 'none',
  });
  header.className = 'tutorial-drag-handle';

  const titleEl = document.createElement('div');
  titleEl.setAttribute('data-tutorial-title', '');
  Object.assign(titleEl.style, { fontWeight: '700', fontSize: '1.1em', color: 'var(--color-primary, #00693e)' });
  titleEl.textContent = title;
  header.appendChild(titleEl);

  const dismissBtn = document.createElement('button');
  dismissBtn.className = 'tutorial-dismiss';
  dismissBtn.setAttribute('aria-label', 'Close tutorial');
  Object.assign(dismissBtn.style, {
    background: 'none', border: 'none', color: 'var(--color-text-muted, #64748b)',
    fontSize: '20px', cursor: 'pointer', padding: '4px 8px', lineHeight: '1',
    flexShrink: '0',
  });
  dismissBtn.textContent = '\u00d7';
  dismissBtn.addEventListener('click', () => showDismissConfirmation());
  header.appendChild(dismissBtn);

  modal.appendChild(header);

  // Message
  const msgContainer = document.createElement('div');
  msgContainer.setAttribute('data-tutorial-message', '');
  Object.assign(msgContainer.style, { fontSize: '0.95em', color: 'var(--color-text-muted, #64748b)' });
  renderMarkdownLite(msgContainer, message);
  modal.appendChild(msgContainer);

  // Footer
  const footer = document.createElement('div');
  footer.setAttribute('data-tutorial-footer', '');
  Object.assign(footer.style, {
    marginTop: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px',
  });

  // Skip link removed — dismiss button (×) in header serves the same purpose

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

  // Start Over link removed — users can replay via the ? button in the header
}

/** Render simple markdown: *italic* → <em>, preserving newlines as paragraphs. */
function renderMarkdownLite(container, text) {
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.trim() === '') {
      container.appendChild(document.createElement('br'));
      continue;
    }
    const p = document.createElement('p');
    Object.assign(p.style, { margin: '0.4em 0' });
    // Simple *italic* and <span> rendering
    const parts = line.split(/(\*[^*]+\*|<span[^>]*>.*?<\/span>)/g);
    for (const part of parts) {
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
        const em = document.createElement('em');
        em.textContent = part.slice(1, -1);
        p.appendChild(em);
      } else if (part.startsWith('<span')) {
        const temp = document.createElement('template');
        temp.innerHTML = part;
        p.appendChild(temp.content);
      } else {
        p.appendChild(document.createTextNode(part));
      }
    }
    container.appendChild(p);
  }
}

// ── Draggable modal ─────────────────────────────────────────────────

function makeDraggable(modal) {
  const handle = modal.querySelector('.tutorial-drag-handle');
  if (!handle) return;

  handle.addEventListener('mousedown', (e) => {
    if (e.target.closest('button, a')) return; // don't drag on buttons
    e.preventDefault();
    const rect = modal.getBoundingClientRect();
    // Lock width so text doesn't reflow when right/bottom are cleared
    modal.style.width = rect.width + 'px';
    _dragState = { startX: e.clientX, startY: e.clientY, origLeft: rect.left, origTop: rect.top };
    modal.style.transition = 'none';
    handle.style.cursor = 'grabbing';

    function onMove(ev) {
      if (!_dragState) return;
      const dx = ev.clientX - _dragState.startX;
      const dy = ev.clientY - _dragState.startY;
      modal.style.left = `${_dragState.origLeft + dx}px`;
      modal.style.top = `${_dragState.origTop + dy}px`;
      modal.style.transform = 'none';
      modal.style.right = 'auto';
      modal.style.bottom = 'auto';
    }
    function onUp() {
      _dragState = null;
      handle.style.cursor = 'grab';
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });

  // Touch support
  handle.addEventListener('touchstart', (e) => {
    if (e.target.closest('button, a')) return;
    const touch = e.touches[0];
    const rect = modal.getBoundingClientRect();
    // Lock width so text doesn't reflow when right/bottom are cleared
    modal.style.width = rect.width + 'px';
    _dragState = { startX: touch.clientX, startY: touch.clientY, origLeft: rect.left, origTop: rect.top };
    modal.style.transition = 'none';

    function onTouchMove(ev) {
      if (!_dragState) return;
      ev.preventDefault();
      const t = ev.touches[0];
      const dx = t.clientX - _dragState.startX;
      const dy = t.clientY - _dragState.startY;
      modal.style.left = `${_dragState.origLeft + dx}px`;
      modal.style.top = `${_dragState.origTop + dy}px`;
      modal.style.transform = 'none';
      modal.style.right = 'auto';
      modal.style.bottom = 'auto';
    }
    function onTouchEnd() {
      _dragState = null;
      document.removeEventListener('touchmove', onTouchMove);
      document.removeEventListener('touchend', onTouchEnd);
    }
    document.addEventListener('touchmove', onTouchMove, { passive: false });
    document.addEventListener('touchend', onTouchEnd);
  }, { passive: true });
}

function positionModal(modal, highlightEl, positionHint = null) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const gap = 16;
  const mw = MODAL_MAX_WIDTH;
  const headerH = 56;

  let left, top;

  // Position hints override normal positioning
  if (positionHint === 'quiz-final') {
    // Position as if quiz panel is at its final open position (right edge)
    const sidebarW = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--quiz-sidebar-width')) || 380;
    left = vw - sidebarW - mw - gap;
    if (left < 12) left = 12;
    top = headerH + gap;
    Object.assign(modal.style, { top: `${top}px`, left: `${left}px`, transform: 'none' });
    return;
  }

  if (positionHint === 'video-final') {
    // Position as if video panel is at its final open position (left edge)
    const sidebarW = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--video-sidebar-width')) || 380;
    left = sidebarW + gap;
    if (left + mw > vw - 12) left = vw - mw - 12;
    top = headerH + gap;
    Object.assign(modal.style, { top: `${top}px`, left: `${left}px`, transform: 'none' });
    return;
  }

  if (positionHint === 'right') {
    // Right-aligned: right edge of modal has same margin as header-to-modal gap
    left = vw - mw - gap;
    top = headerH + gap;
    Object.assign(modal.style, { top: `${top}px`, left: `${left}px`, transform: 'none' });
    return;
  }

  if (positionHint === 'left') {
    // Left-aligned: left edge of modal has same margin as header-to-modal gap
    left = gap;
    top = headerH + gap;
    Object.assign(modal.style, { top: `${top}px`, left: `${left}px`, transform: 'none' });
    return;
  }

  const rect = highlightEl.getBoundingClientRect();

  const isRight = rect.left > vw * 0.5;    // highlight on right side (quiz panel)
  const isLeft = rect.right < vw * 0.4;    // highlight on left side (video panel)
  const isTop = rect.bottom < vh * 0.25;   // highlight in header area
  const isLarge = rect.width > vw * 0.5;   // highlight spans most of viewport (map)

  if (isLarge) {
    // Large element (map container) — center modal in the map area.
    const mapEl = document.getElementById('map-container');
    const mapRect = mapEl ? mapEl.getBoundingClientRect() : rect;
    left = mapRect.left + (mapRect.width - mw) / 2;
    if (left < gap) left = gap;
    top = Math.max(headerH + gap, rect.top + gap);
  } else if (isRight) {
    // Right-side highlight — place modal to the left of highlight
    left = rect.left - mw - gap;
    if (left < 12) left = 12;
    top = Math.max(headerH + gap, rect.top);
  } else if (isLeft) {
    // Left-side highlight — place modal to the right of highlight
    left = rect.right + gap;
    if (left + mw > vw - 12) left = vw - mw - 12;
    top = Math.max(headerH + gap, rect.top);
  } else if (isTop) {
    // Header element — place modal below highlight
    left = Math.max(12, Math.min(rect.left, vw - mw - 12));
    top = rect.bottom + gap;
  } else {
    // Fallback — place below the highlight
    left = Math.max(12, Math.min(rect.left, vw - mw - 12));
    top = rect.bottom + gap;
    if (top + 200 > vh - 12) {
      top = Math.max(headerH + gap, rect.top - 200 - gap);
    }
  }

  // Clamp within viewport
  if (left + mw > vw - 12) left = vw - mw - 12;
  if (left < 12) left = 12;
  if (top + 200 > vh - 12) top = Math.max(headerH + gap, vh - 212);
  if (top < headerH + gap) top = headerH + gap;

  Object.assign(modal.style, {
    top: `${top}px`,
    left: `${left}px`,
    transform: 'none',
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
    top: '24px',
    left: '50%',
    transform: 'translateX(-50%)',
    background: 'var(--color-bg, #ffffff)',
    color: 'var(--color-text, #0f172a)',
    padding: '12px 24px',
    borderRadius: '8px',
    border: '1px solid var(--color-border, rgba(226,232,240,0.8))',
    boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
    fontSize: '0.9em',
    zIndex: '10000',
    maxWidth: '360px',
    textAlign: 'center',
    opacity: '0',
    transition: prefersReducedMotion() ? 'none' : 'opacity 300ms ease',
  });
  toast.textContent = msg;
  document.body.appendChild(toast);

  requestAnimationFrame(() => { toast.style.opacity = '1'; });

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 350);
  }, 3000);
}

// ── Utilities ───────────────────────────────────────────────────────

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
