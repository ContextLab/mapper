/** Question mode selector with availability gating per FR-010/FR-011. */

const QUESTION_MODES = [
  { id: 'auto', label: 'Auto (best next question)', icon: 'fa-wand-magic-sparkles', minAnswers: 0, type: 'question', enabledTooltip: 'Pick the next question that maximizes gain in knowledge estimation accuracy' },
  { id: 'easy', label: 'Ask me an easy question', icon: 'fa-face-smile', minAnswers: 5, type: 'question', enabledTooltip: 'Pick a question the model predicts you can answer' },
  { id: 'hardest-can-answer', label: 'Hardest I can answer', icon: 'fa-fire', minAnswers: 5, type: 'question', enabledTooltip: 'Pick the hardest question the model thinks you can get right' },
  { id: 'dont-know', label: "Something I don't know", icon: 'fa-circle-question', minAnswers: 5, type: 'question', enabledTooltip: 'Pick a question in a low-knowledge area' },
];

const INSIGHT_MODES = [];

const ALL_MODES = [...QUESTION_MODES, ...INSIGHT_MODES];

let wrapper = null;
let buttons = new Map();
let activeMode = 'auto';
let currentAnswerCount = 0;
let onSelectCb = null;
let onSkipCb = null;
let autoAdvance = false;
let autoAdvanceToggleEl = null;
let skipBtnEl = null;

export function init(container) {
  if (!container) return;

  if (!document.getElementById('modes-style')) {
    const style = document.createElement('style');
    style.id = 'modes-style';
    style.textContent = `
      .modes-wrapper {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin-bottom: 0.75rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--color-border);
      }
      .mode-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.6rem;
        border: 1px solid var(--color-border);
        border-radius: 16px;
        background: var(--color-surface-raised);
        cursor: pointer;
        font-size: 0.75rem;
        font-family: var(--font-body);
        color: var(--color-text-muted);
        transition: all 0.15s ease;
        white-space: nowrap;
        position: relative;
      }
      .mode-btn:hover:not(:disabled) {
        border-color: var(--color-primary);
        color: var(--color-primary);
        box-shadow: 0 0 8px var(--color-glow-primary);
      }
      .mode-btn.active,
      .mode-btn.active:hover {
        background: var(--color-primary);
        color: #ffffff;
        border-color: var(--color-primary);
        box-shadow: 0 0 12px var(--color-glow-primary);
      }
      .mode-btn:disabled {
        opacity: 0.25;
        cursor: not-allowed;
      }
      .mode-btn:disabled i {
        display: none;
      }
      .mode-btn--insight {
        border-style: dashed;
        border-color: var(--color-secondary);
      }
      .mode-btn--insight:hover:not(:disabled) {
        border-color: var(--color-secondary);
        color: var(--color-secondary);
        box-shadow: 0 0 8px var(--color-glow-secondary);
      }
      .mode-btn--insight.active,
      .mode-btn--insight.active:hover {
        border-style: solid;
        background: var(--color-secondary);
        color: #ffffff;
        border-color: var(--color-secondary);
        box-shadow: 0 0 12px var(--color-glow-secondary);
      }
      /* Disabled mode button tooltips handled by global [data-tooltip] JS system */

      /* Auto-advance toggle */
      .auto-advance-wrap {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        margin-left: 0.25rem;
      }
      .auto-advance-label {
        font-size: 0.68rem;
        color: var(--color-text-muted);
        cursor: pointer;
        user-select: none;
        white-space: nowrap;
      }
      .auto-advance-track {
        position: relative;
        width: 30px;
        height: 16px;
        background: var(--color-surface-raised);
        border: 1px solid var(--color-border);
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.25s ease, border-color 0.25s ease;
        flex-shrink: 0;
      }
      .auto-advance-track.on {
        background: var(--color-primary);
        border-color: var(--color-primary);
      }
      .auto-advance-thumb {
        position: absolute;
        top: 1px;
        left: 1px;
        width: 12px;
        height: 12px;
        background: #fff;
        border-radius: 50%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      }
      .auto-advance-track.on .auto-advance-thumb {
        transform: translateX(14px);
      }
      .skip-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.6rem;
        border: 1px solid #d4a017;
        border-radius: 16px;
        background: var(--color-surface-raised);
        cursor: pointer;
        font-size: 0.75rem;
        font-family: var(--font-body);
        color: #b8860b;
        transition: all 0.15s ease;
        white-space: nowrap;
      }
      .skip-btn:hover {
        background: #d4a017;
        color: #ffffff;
        box-shadow: 0 0 8px rgba(212, 160, 23, 0.4);
      }
    `;
    document.head.appendChild(style);
  }

  wrapper = document.createElement('div');
  wrapper.className = 'modes-wrapper';
  wrapper.setAttribute('role', 'group');
  wrapper.setAttribute('aria-label', 'Question and insight modes');

  for (const mode of ALL_MODES) {
    const btn = document.createElement('button');
    btn.className = 'mode-btn' + (mode.id === activeMode ? ' active' : '');
    if (mode.type === 'insight') btn.classList.add('mode-btn--insight');
    btn.innerHTML = `<i class="fa-solid ${mode.icon}"></i> ${mode.label}`;
    btn.dataset.mode = mode.id;
    btn.dataset.type = mode.type;
    btn.dataset.tooltip = mode.enabledTooltip || '';

    if (mode.minAnswers > 0 && currentAnswerCount < mode.minAnswers) {
      btn.disabled = true;
      btn.dataset.tooltip = `Answer ${mode.minAnswers} more questions first`;
    }

    btn.addEventListener('click', () => handleSelect(mode.id, mode.type));
    buttons.set(mode.id, btn);
    wrapper.appendChild(btn);
  }

  // Skip button
  skipBtnEl = document.createElement('button');
  skipBtnEl.className = 'skip-btn';
  skipBtnEl.innerHTML = '<i class="fa-solid fa-forward"></i> Skip';
  skipBtnEl.dataset.tooltip = "Not sure of the answer? Don't guess, just press skip!";
  skipBtnEl.addEventListener('click', () => {
    if (onSkipCb) onSkipCb();
  });
  wrapper.appendChild(skipBtnEl);

  // Auto-advance toggle
  const toggleWrap = document.createElement('div');
  toggleWrap.className = 'auto-advance-wrap';

  const track = document.createElement('div');
  track.className = 'auto-advance-track';
  track.setAttribute('role', 'switch');
  track.setAttribute('aria-checked', 'false');
  track.setAttribute('aria-label', 'Auto-advance to next question');
  track.setAttribute('tabindex', '0');
  track.dataset.tooltip = 'Auto-advance to the next question after answering';

  const thumb = document.createElement('div');
  thumb.className = 'auto-advance-thumb';
  track.appendChild(thumb);

  const label = document.createElement('span');
  label.className = 'auto-advance-label';
  label.textContent = 'Auto-advance';

  function toggleAutoAdvance() {
    autoAdvance = !autoAdvance;
    track.classList.toggle('on', autoAdvance);
    track.setAttribute('aria-checked', String(autoAdvance));
  }

  track.addEventListener('click', toggleAutoAdvance);
  label.addEventListener('click', toggleAutoAdvance);
  track.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleAutoAdvance();
    }
  });

  toggleWrap.appendChild(track);
  toggleWrap.appendChild(label);
  wrapper.appendChild(toggleWrap);
  autoAdvanceToggleEl = track;

  container.prepend(wrapper);
}

export function onModeSelect(callback) {
  onSelectCb = callback;
}

export function onSkip(callback) {
  onSkipCb = callback;
}

export function updateAvailability(responseCount) {
  currentAnswerCount = responseCount;
  for (const mode of ALL_MODES) {
    const btn = buttons.get(mode.id);
    if (!btn) continue;

    const needed = mode.minAnswers - responseCount;
    if (needed > 0) {
      btn.disabled = true;
      btn.dataset.tooltip = `Answer ${needed} more question${needed > 1 ? 's' : ''} first`;
    } else {
      btn.disabled = false;
      btn.dataset.tooltip = mode.enabledTooltip || '';
    }
  }
}

export function getActiveMode() {
  return activeMode;
}

export function isAutoAdvance() {
  return autoAdvance;
}

function handleSelect(modeId, type) {
  if (type === 'question') {
    activeMode = modeId;
  }

  for (const [id, btn] of buttons) {
    btn.classList.toggle('active', id === modeId);
  }

  if (onSelectCb) onSelectCb(modeId, type || 'question');
}
