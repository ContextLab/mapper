/** Milestone toasts, expertise button highlight, and running progress display. */

const MILESTONES = [
  { threshold: 10, message: '10 questions answered! Your map is taking shape.', hasConfetti: true },
  { threshold: 25, message: '25 questions! You\'re building a detailed knowledge map.', hasConfetti: false },
  { threshold: 50, message: '50 questions! You\'re a knowledge mapping expert.', hasConfetti: false },
];

const STORAGE_KEY = 'mapper-milestones';
const HIGHLIGHT_KEY = 'mapper-expertise-highlighted';
let shownThisSession = new Set();

// Inject styles once
function injectStyles() {
  const styleId = 'milestone-styles';
  if (document.getElementById(styleId)) return;
  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = `
    .milestone-toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--color-surface-raised, #1e293b);
      color: var(--color-text, #fff);
      border-radius: 12px;
      padding: 14px 20px;
      font-family: var(--font-body, sans-serif);
      font-size: 0.85rem;
      line-height: 1.4;
      z-index: 9999;
      pointer-events: none;
      transform: translateY(100%);
      opacity: 0;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25);
      max-width: 320px;
    }
    .milestone-toast.enter {
      animation: milestoneEnter 300ms cubic-bezier(0.05, 0.7, 0.1, 1.0) forwards;
    }
    .milestone-toast.exit {
      animation: milestoneExit 200ms cubic-bezier(0.3, 0.0, 0.8, 0.15) forwards;
    }
    @keyframes milestoneEnter {
      from { transform: translateY(100%); opacity: 0; }
      to   { transform: translateY(0); opacity: 1; }
    }
    @keyframes milestoneExit {
      from { transform: translateY(0); opacity: 1; }
      to   { transform: translateY(100%); opacity: 0; }
    }

    .milestone-confetti {
      position: fixed;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      z-index: 10000;
      pointer-events: none;
      animation: confettiBurst 1s ease-out forwards;
    }
    @keyframes confettiBurst {
      0%   { opacity: 1; transform: translate(0, 0) scale(1); }
      100% { opacity: 0; transform: translate(var(--cx), var(--cy)) scale(0.5); }
    }

    @keyframes expertisePulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(108,99,255,0.5); }
      50%      { box-shadow: 0 0 8px 3px rgba(108,99,255,0.4); }
    }
    .expertise-highlight {
      border: 2px solid #6C63FF !important;
      animation: expertisePulse 1.5s ease-in-out infinite;
    }

    .milestone-progress {
      font-family: var(--font-body, sans-serif);
      font-size: 0.72rem;
      color: var(--color-text-muted, #94a3b8);
      padding: 2px 0 4px 0;
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 18px;
    }
    .milestone-progress .streak {
      color: var(--color-accent, #d97706);
      font-weight: 600;
    }

    @media (prefers-reduced-motion: reduce) {
      .milestone-toast.enter,
      .milestone-toast.exit {
        animation: none;
      }
      .milestone-toast.enter {
        transform: translateY(0);
        opacity: 1;
      }
      .milestone-toast.exit {
        transform: translateY(100%);
        opacity: 0;
      }
      .milestone-confetti {
        animation: none;
        display: none;
      }
      .expertise-highlight {
        animation: none;
        box-shadow: 0 0 6px 2px rgba(108,99,255,0.4);
      }
    }
  `;
  document.head.appendChild(style);
}

function getShown() {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'));
  } catch { return new Set(); }
}

function markShown(threshold) {
  const shown = getShown();
  shown.add(threshold);
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...shown]));
  shownThisSession.add(threshold);
}

const CONFETTI_COLORS = ['#ff6b6b', '#feca57', '#48dbfb', '#ff9ff3', '#54a0ff', '#5f27cd', '#01a3a4', '#f368e0'];

function spawnConfetti(originEl) {
  const rect = originEl.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  for (let i = 0; i < 12; i++) {
    const dot = document.createElement('div');
    dot.className = 'milestone-confetti';
    const angle = (Math.PI * 2 * i) / 12 + (Math.random() - 0.5) * 0.4;
    const dist = 40 + Math.random() * 60;
    dot.style.left = cx + 'px';
    dot.style.top = cy + 'px';
    dot.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length];
    dot.style.setProperty('--cx', Math.cos(angle) * dist + 'px');
    dot.style.setProperty('--cy', Math.sin(angle) * dist - 30 + 'px');
    document.body.appendChild(dot);
    setTimeout(() => dot.remove(), 1100);
  }
}

function showToast(message, hasConfetti) {
  injectStyles();
  const toast = document.createElement('div');
  toast.className = 'milestone-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  // Force reflow then enter
  toast.offsetHeight; // eslint-disable-line no-unused-expressions
  toast.classList.add('enter');

  if (hasConfetti) {
    setTimeout(() => spawnConfetti(toast), 150);
  }

  setTimeout(() => {
    toast.classList.remove('enter');
    toast.classList.add('exit');
    setTimeout(() => toast.remove(), 250);
  }, 3000);
}

/**
 * Check whether the current question count has crossed a milestone threshold.
 * Call after each answer is recorded.
 */
export function checkMilestone(questionCount) {
  injectStyles();
  const shown = getShown();
  for (const m of MILESTONES) {
    if (questionCount >= m.threshold && !shown.has(m.threshold) && !shownThisSession.has(m.threshold)) {
      showToast(m.message, m.hasConfetti);
      markShown(m.threshold);
      return; // One at a time
    }
  }
}

/**
 * Add a pulsing highlight to the #trophy-btn to draw attention.
 * Fires at most once ever (persisted in localStorage).
 */
export function highlightExpertiseButton() {
  injectStyles();
  if (localStorage.getItem(HIGHLIGHT_KEY) === '1') return;

  const btn = document.getElementById('trophy-btn');
  if (!btn) return;

  localStorage.setItem(HIGHLIGHT_KEY, '1');
  btn.classList.add('expertise-highlight');

  const stop = () => btn.classList.remove('expertise-highlight');

  // Auto-stop after 6 seconds
  const timer = setTimeout(stop, 6000);

  // Stop on click
  btn.addEventListener('click', () => {
    clearTimeout(timer);
    stop();
  }, { once: true });
}

/**
 * Update the small running progress display in the quiz panel header area.
 * Shows question count and optional streak indicator.
 */
export function updateProgressDisplay(questionCount, consecutiveCorrect) {
  injectStyles();
  const panel = document.getElementById('quiz-panel');
  if (!panel) return;

  let el = panel.querySelector('.milestone-progress');
  if (!el) {
    // Insert before the .quiz-content wrapper
    el = document.createElement('div');
    el.className = 'milestone-progress';
    const content = panel.querySelector('.quiz-content');
    if (content) {
      content.parentNode.insertBefore(el, content);
    } else {
      panel.prepend(el);
    }
  }

  // Build progress display using safe DOM methods (questionCount and
  // consecutiveCorrect are always numbers, but we use textContent to be safe)
  el.textContent = '';

  const countSpan = document.createElement('span');
  countSpan.textContent = 'Q' + questionCount;
  el.appendChild(countSpan);

  if (consecutiveCorrect >= 3) {
    const streakSpan = document.createElement('span');
    streakSpan.className = 'streak';
    streakSpan.textContent = '\u{1F525} ' + consecutiveCorrect + ' in a row!';
    el.appendChild(streakSpan);
  }
}
