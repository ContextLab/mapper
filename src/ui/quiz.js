/** Quiz UI for question display, answer input, and feedback. */

import { announce } from '../utils/accessibility.js';

let answerCallback = null;
let nextCallback = null;
let currentQuestion = null;
let uiElements = {};

// Randomization: maps display key → original key (e.g., { A: "C", B: "A", C: "D", D: "B" })
let displayToOriginal = { A: 'A', B: 'B', C: 'C', D: 'D' };
let originalToDisplay = { A: 'A', B: 'B', C: 'C', D: 'D' };

/** Fisher-Yates shuffle (in place). */
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/** Build random key mappings for option display. */
function buildShuffleMaps() {
  const keys = ['A', 'B', 'C', 'D'];
  const shuffled = shuffle([...keys]);
  displayToOriginal = {};
  originalToDisplay = {};
  keys.forEach((displayKey, i) => {
    displayToOriginal[displayKey] = shuffled[i];
    originalToDisplay[shuffled[i]] = displayKey;
  });
}

export function init(container) {

  const styleId = 'quiz-panel-styles';
  if (!document.getElementById(styleId)) {
    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
      .quiz-content.fade-in {
        animation: fadeIn 0.2s ease-in forwards;
      }
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .quiz-question {
        font-family: var(--font-heading);
        font-size: 0.82rem;
        line-height: 1.6;
        color: var(--color-text);
        margin-bottom: 1.25rem;
        text-align: left;
        text-indent: 0;
      }
      .quiz-instruction {
        font-size: 0.72rem;
        color: var(--color-text-muted);
        margin-bottom: 0.75rem;
        font-style: italic;
      }
      .quiz-options {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      .quiz-option {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 1px solid var(--color-border);
        background: var(--color-surface-raised);
        margin-bottom: 0.25rem;
        cursor: pointer;
        text-align: left;
        font-family: var(--font-body);
        font-size: 0.85rem;
        color: var(--color-text);
        transition: all 0.2s ease;
        min-height: 44px;
        display: block;
        width: 100%;
        touch-action: manipulation;
        line-height: 1.5;
      }
      .quiz-option b {
        color: var(--color-primary);
      }
      .quiz-option:hover:not(:disabled) {
        border-color: var(--color-primary);
        box-shadow: 0 0 8px var(--color-glow-primary);
      }
      .quiz-option:disabled {
        pointer-events: none;
        opacity: 0.6;
      }
      .quiz-option.selected.correct {
        background-color: var(--color-correct) !important;
        color: #ffffff !important;
        border-color: var(--color-correct) !important;
        box-shadow: 0 0 12px rgba(16,185,129,0.3) !important;
        opacity: 1 !important;
      }
      .quiz-option.selected.incorrect {
        background-color: var(--color-incorrect) !important;
        color: #ffffff !important;
        border-color: var(--color-incorrect) !important;
        box-shadow: 0 0 12px rgba(239,68,68,0.3) !important;
        opacity: 1 !important;
      }
      .quiz-option.correct-highlight {
        background-color: var(--color-correct) !important;
        color: #ffffff !important;
        border-color: var(--color-correct) !important;
        box-shadow: 0 0 12px rgba(16,185,129,0.3) !important;
        opacity: 1 !important;
      }
      .quiz-feedback {
        margin-top: 1rem;
        font-family: var(--font-body);
        font-weight: bold;
        min-height: 1.5em;
      }
      .quiz-meta {
        margin-top: 0.5rem;
        font-size: 0.8rem;
        font-family: var(--font-body);
        color: var(--color-text-muted);
      }
      .quiz-meta a {
        color: var(--color-secondary);
        text-decoration: underline;
        text-underline-offset: 2px;
      }
      .quiz-meta a:hover {
        text-shadow: 0 0 6px var(--color-glow-secondary);
      }
      .quiz-actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.75rem;
        flex-wrap: wrap;
      }
      .quiz-next-btn {
        padding: 0.5rem 1.25rem;
        border-radius: 8px;
        border: 1px solid var(--color-primary);
        background: var(--color-primary);
        color: #ffffff;
        font-family: var(--font-heading);
        font-size: 0.82rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        min-height: 36px;
      }
      .quiz-next-btn:hover {
        box-shadow: 0 0 12px var(--color-glow-primary);
        transform: translateY(-1px);
      }
      .quiz-learn-btn {
        padding: 0.4rem 0.75rem;
        border-radius: 6px;
        border: 1px solid var(--color-border);
        background: var(--color-surface-raised);
        color: var(--color-text-muted);
        font-family: var(--font-body);
        font-size: 0.75rem;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        min-height: 32px;
      }
      .quiz-learn-btn:hover {
        border-color: var(--color-secondary);
        color: var(--color-secondary);
        box-shadow: 0 0 8px var(--color-glow-secondary);
      }
      .katex { font-size: 1.05em; }
    `;
    document.head.appendChild(style);
  }


  container.innerHTML = `
    <div class="resize-handle"></div>
    <div class="quiz-content">
      <div class="quiz-question" aria-live="polite"></div>
      <div class="quiz-instruction">Click on the correct response</div>
      <div class="quiz-options" role="group" aria-label="Answer options">
        <button class="quiz-option" data-key="A" aria-label="Option A"></button>
        <button class="quiz-option" data-key="B" aria-label="Option B"></button>
        <button class="quiz-option" data-key="C" aria-label="Option C"></button>
        <button class="quiz-option" data-key="D" aria-label="Option D"></button>
      </div>
      <div class="quiz-feedback" aria-live="assertive"></div>
      <div class="quiz-actions" hidden>
        <button class="quiz-next-btn" aria-label="Next question">Next <i class="fa-solid fa-arrow-right" style="margin-left:0.3rem;font-size:0.75rem"></i></button>
        <a class="quiz-learn-btn" target="_blank" rel="noopener" data-learn="wikipedia" hidden><i class="fa-brands fa-wikipedia-w"></i> Wikipedia</a>
        <a class="quiz-learn-btn" target="_blank" rel="noopener" data-learn="khan" hidden><i class="fa-solid fa-graduation-cap"></i> Khan Academy</a>
      </div>
      <div class="quiz-meta"></div>
    </div>
  `;

  uiElements = {
    wrapper: container.querySelector('.quiz-content'),
    question: container.querySelector('.quiz-question'),
    instruction: container.querySelector('.quiz-instruction'),
    options: container.querySelectorAll('.quiz-option'),
    feedback: container.querySelector('.quiz-feedback'),
    actions: container.querySelector('.quiz-actions'),
    nextBtn: container.querySelector('.quiz-next-btn'),
    wikiBtn: container.querySelector('[data-learn="wikipedia"]'),
    khanBtn: container.querySelector('[data-learn="khan"]'),
    meta: container.querySelector('.quiz-meta')
  };


  uiElements.options.forEach(btn => {
    btn.addEventListener('click', () => handleOptionClick(btn.dataset.key));
  });

  if (uiElements.nextBtn) {
    uiElements.nextBtn.addEventListener('click', () => {
      if (nextCallback) nextCallback();
    });
  }

  document.addEventListener('keydown', handleKeyDown);

  const resizeHandle = container.querySelector('.resize-handle');
  if (resizeHandle) {
    let resizing = false;
    resizeHandle.addEventListener('mousedown', (e) => {
      e.preventDefault();
      resizing = true;
      resizeHandle.classList.add('active');
      const onMove = (ev) => {
        if (!resizing) return;
        const newWidth = Math.max(280, Math.min(600, window.innerWidth - ev.clientX));
        document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px');
      };
      const onUp = () => {
        resizing = false;
        resizeHandle.classList.remove('active');
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }
}

function handleKeyDown(e) {
  if (!currentQuestion || !uiElements.options) return;

  // If options are disabled (already answered), Enter/N/Space advances to next
  if (uiElements.options[0].disabled) {
    if (e.key === 'Enter' || e.key === 'n' || e.key === 'N' || e.key === ' ') {
      e.preventDefault();
      if (nextCallback) nextCallback();
    }
    return;
  }

  const key = e.key.toUpperCase();
  if (['1', 'A'].includes(key)) handleOptionClick('A');
  if (['2', 'B'].includes(key)) handleOptionClick('B');
  if (['3', 'C'].includes(key)) handleOptionClick('C');
  if (['4', 'D'].includes(key)) handleOptionClick('D');
}

export function showQuestion(question) {
  currentQuestion = question;
  
  if (uiElements.wrapper) {
    uiElements.wrapper.classList.remove('fade-in');
    void uiElements.wrapper.offsetWidth;
    uiElements.wrapper.classList.add('fade-in');
  }

  if (uiElements.question) {
    const questionText = question.question_text || '';
    uiElements.question.innerHTML = renderLatex(questionText);
    // T049: Announce question change
    announce(`Question: ${stripLatex(questionText)}`);
  }

   if (uiElements.options) {
    // Randomize option order each time a question is displayed
    buildShuffleMaps();
    uiElements.options.forEach(btn => {
      const displayKey = btn.dataset.key;          // A, B, C, D (button slot)
      const originalKey = displayToOriginal[displayKey]; // which original option to show here
      const text = question.options ? question.options[originalKey] : '';
      const renderedText = renderLatex(text || '');
      btn.innerHTML = renderedText;
      // T049: Update ARIA label with option text
      btn.setAttribute('aria-label', `Option ${displayKey}: ${stripLatex(text || '')}`);
      btn.disabled = false;
      btn.className = 'quiz-option';
    });
  }

  if (uiElements.feedback) {
    uiElements.feedback.innerHTML = '';
    uiElements.feedback.style.color = '';
  }
  
  if (uiElements.meta) {
    uiElements.meta.textContent = '';
  }

  // Hide Next/Learn more buttons until answer is given
  if (uiElements.actions) {
    uiElements.actions.hidden = true;
  }
}

function handleOptionClick(selectedDisplayKey) {
   if (!currentQuestion || !uiElements.options) return;

   uiElements.options.forEach(btn => {
     btn.disabled = true;
   });

  // Translate display keys back to original keys for correctness check
  const originalSelectedKey = displayToOriginal[selectedDisplayKey];
  const originalCorrectKey = currentQuestion.correct_answer;
  const isCorrect = originalSelectedKey === originalCorrectKey;

  // Highlight uses display keys (which button slot to color)
  const correctDisplayKey = originalToDisplay[originalCorrectKey];

  uiElements.options.forEach(btn => {
    const key = btn.dataset.key;
    if (key === selectedDisplayKey) {
      btn.classList.add('selected');
      btn.classList.add(isCorrect ? 'correct' : 'incorrect');
    }
    if (key === correctDisplayKey) {
      btn.classList.add('correct-highlight');
    }
  });

  if (uiElements.feedback) {
    if (isCorrect) {
      uiElements.feedback.textContent = 'Correct!';
      uiElements.feedback.style.color = 'var(--color-correct)';
    } else {
      uiElements.feedback.textContent = 'Incorrect';
      uiElements.feedback.style.color = 'var(--color-incorrect)';
    }
  }

  if (uiElements.meta && currentQuestion.source_article) {
    const article = currentQuestion.source_article;
    const url = `https://en.wikipedia.org/wiki/${encodeURIComponent(article)}`;
    uiElements.meta.textContent = '';
    const sourceLabel = document.createTextNode('Source: ');
    const sourceLink = document.createElement('a');
    sourceLink.href = url;
    sourceLink.target = '_blank';
    sourceLink.textContent = article;
    uiElements.meta.appendChild(sourceLabel);
    uiElements.meta.appendChild(sourceLink);
  }

  // Show Next button and Learn more links instead of auto-advancing
  if (uiElements.actions) {
    uiElements.actions.hidden = false;

    // Show Wikipedia link if we have a source article
    if (uiElements.wikiBtn && currentQuestion.source_article) {
      const wikiUrl = `https://en.wikipedia.org/wiki/${encodeURIComponent(currentQuestion.source_article)}`;
      uiElements.wikiBtn.href = wikiUrl;
      uiElements.wikiBtn.hidden = false;
    } else if (uiElements.wikiBtn) {
      uiElements.wikiBtn.hidden = true;
    }

    // Show Khan Academy search link based on question concepts or article
    if (uiElements.khanBtn) {
      const searchTerm = currentQuestion.source_article || '';
      if (searchTerm) {
        uiElements.khanBtn.href = `https://www.khanacademy.org/search?referer=%2F&page_search_query=${encodeURIComponent(searchTerm)}`;
        uiElements.khanBtn.hidden = false;
      } else {
        uiElements.khanBtn.hidden = true;
      }
    }
  }

  // Fire the answer callback with the ORIGINAL key (not the display key)
  // so that app.js records the correct option letter regardless of shuffle
  if (answerCallback) {
    answerCallback(originalSelectedKey, currentQuestion);
  }
}

export function onAnswer(callback) {
  answerCallback = callback;
}

export function onNext(callback) {
  nextCallback = callback;
}

export function getCurrentQuestion() {
  return currentQuestion;
}

/**
 * Replaces $...$ with KaTeX rendered HTML.
 * Heuristic: if content between $ signs contains only numbers/punctuation, treat as currency.
 * Fallback: if KaTeX is missing or fails, shows raw text with monospace styling.
 */
export function renderLatex(text) {
  if (!text) return '';
  
  return text.replace(/\$([^$]+)\$/g, (match, content) => {
    if (/^[0-9.,\s]+$/.test(content)) {
      return content;
    }
    
    if (window.katex && !window.__katexFailed) {
      try {
        return window.katex.renderToString(content, {
          throwOnError: false,
          displayMode: false
        });
      } catch (err) {
        console.warn('KaTeX render error:', err);
        return `<code style="font-family: 'Courier New', monospace; background: var(--color-surface); padding: 0.2em 0.4em; border-radius: 3px;">${content}</code>`;
      }
    }
    
    return `<code style="font-family: 'Courier New', monospace; background: var(--color-surface); padding: 0.2em 0.4em; border-radius: 3px;">${content}</code>`;
  });
}

/**
 * Helper to strip LaTeX delimiters for screen readers
 */
function stripLatex(text) {
  if (!text) return '';
  return text.replace(/\$([^$]+)\$/g, '$1');
}
