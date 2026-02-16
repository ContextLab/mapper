/** Question mode selector with availability gating per FR-010/FR-011. */

const QUESTION_MODES = [
  { id: 'auto', label: 'Auto (best next question)', icon: 'fa-wand-magic-sparkles', minAnswers: 0, type: 'question' },
  { id: 'easy', label: 'Ask me an easy question', icon: 'fa-face-smile', minAnswers: 5, type: 'question' },
  { id: 'hardest-can-answer', label: 'Hardest I can answer', icon: 'fa-fire', minAnswers: 5, type: 'question' },
  { id: 'dont-know', label: "Something I don't know", icon: 'fa-circle-question', minAnswers: 5, type: 'question' },
];

const INSIGHT_MODES = [
  { id: 'expertise', label: 'My areas of expertise', icon: 'fa-trophy', minAnswers: 10, type: 'insight' },
  { id: 'weakness', label: 'My areas of weakness', icon: 'fa-arrow-trend-down', minAnswers: 10, type: 'insight' },
  { id: 'suggested', label: 'Suggest something to learn', icon: 'fa-lightbulb', minAnswers: 10, type: 'insight' },
];

const ALL_MODES = [...QUESTION_MODES, ...INSIGHT_MODES];

let wrapper = null;
let buttons = new Map();
let activeMode = 'auto';
let currentAnswerCount = 0;
let onSelectCb = null;

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
      }
      .mode-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.35rem 0.6rem;
        border: 1px solid rgba(0,0,0,0.12);
        border-radius: 16px;
        background: white;
        cursor: pointer;
        font-size: 0.78rem;
        font-family: inherit;
        color: #555;
        transition: all 0.15s ease;
        white-space: nowrap;
        position: relative;
      }
      .mode-btn:hover:not(:disabled) {
        border-color: var(--color-primary, #3f51b5);
        color: var(--color-primary, #3f51b5);
      }
      .mode-btn.active {
        background: var(--color-primary, #3f51b5);
        color: white;
        border-color: var(--color-primary, #3f51b5);
      }
      .mode-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .mode-btn--insight {
        border-style: dashed;
      }
      .mode-btn--insight.active {
        border-style: solid;
      }
      .mode-btn:disabled:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: calc(100% + 6px);
        left: 50%;
        transform: translateX(-50%);
        background: #333;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        white-space: nowrap;
        z-index: 100;
        pointer-events: none;
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
    btn.dataset.tooltip = `Answer ${mode.minAnswers} more questions first`;

    if (mode.minAnswers > 0 && currentAnswerCount < mode.minAnswers) {
      btn.disabled = true;
    }

    btn.addEventListener('click', () => handleSelect(mode.id, mode.type));
    buttons.set(mode.id, btn);
    wrapper.appendChild(btn);
  }

  container.prepend(wrapper);
}

export function onModeSelect(callback) {
  onSelectCb = callback;
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
    }
  }
}

export function getActiveMode() {
  return activeMode;
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
