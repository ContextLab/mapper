/** Question mode selector with availability gating per FR-010/FR-011. */

const QUESTION_MODES = [
  { id: 'auto', label: 'Auto (best next question)', icon: 'fa-wand-magic-sparkles', minAnswers: 0 },
  { id: 'easy', label: 'Ask me an easy question', icon: 'fa-face-smile', minAnswers: 5 },
  { id: 'hardest-can-answer', label: 'Hardest I can answer', icon: 'fa-fire', minAnswers: 5 },
  { id: 'dont-know', label: "Something I don't know", icon: 'fa-circle-question', minAnswers: 5 },
];

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
  wrapper.setAttribute('aria-label', 'Question mode');

  for (const mode of QUESTION_MODES) {
    const btn = document.createElement('button');
    btn.className = 'mode-btn' + (mode.id === activeMode ? ' active' : '');
    btn.innerHTML = `<i class="fa-solid ${mode.icon}"></i> ${mode.label}`;
    btn.dataset.mode = mode.id;
    btn.dataset.tooltip = `Answer ${mode.minAnswers} more questions first`;

    if (mode.minAnswers > 0 && currentAnswerCount < mode.minAnswers) {
      btn.disabled = true;
    }

    btn.addEventListener('click', () => handleSelect(mode.id));
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
  for (const mode of QUESTION_MODES) {
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

function handleSelect(modeId) {
  activeMode = modeId;

  for (const [id, btn] of buttons) {
    btn.classList.toggle('active', id === modeId);
  }

  if (onSelectCb) onSelectCb(modeId);
}
