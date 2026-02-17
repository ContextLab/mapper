/** Quiz UI for question display, answer input, and feedback. */

import { announce } from '../utils/accessibility.js';

let answerCallback = null;
let currentQuestion = null;
let uiElements = {};

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
        from { opacity: 0; }
        to { opacity: 1; }
      }
      .quiz-question {
        font-size: 1.1rem;
        line-height: 1.5;
        margin-bottom: 1.5rem;
      }
      .quiz-options {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      .quiz-option {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        border: 2px solid rgba(0,0,0,0.1);
        background: white;
        margin-bottom: 0.5rem;
        cursor: pointer;
        text-align: left;
        font-family: inherit;
        font-size: 1rem;
        transition: all 0.2s ease;
        min-height: 44px;
        display: flex;
        align-items: center;
        width: 100%;
        touch-action: manipulation; /* T046: Prevent double-tap zoom */
      }
      .quiz-option:hover:not(:disabled) {
        border-color: var(--color-primary, #007bff);
      }
      .quiz-option:disabled {
        pointer-events: none;
        opacity: 0.6;
      }
      .quiz-option.selected.correct {
        background-color: #4caf50 !important;
        color: white !important;
        border-color: #4caf50 !important;
        opacity: 1 !important;
      }
      .quiz-option.selected.incorrect {
        background-color: #f44336 !important;
        color: white !important;
        border-color: #f44336 !important;
        opacity: 1 !important;
      }
      .quiz-option.correct-highlight {
        background-color: #4caf50 !important;
        color: white !important;
        border-color: #4caf50 !important;
        opacity: 1 !important;
      }
      .quiz-feedback {
        margin-top: 1rem;
        font-weight: bold;
        min-height: 1.5em;
      }
      .quiz-meta {
        margin-top: 0.5rem;
        font-size: 0.85rem;
        color: #666;
      }
      .katex { font-size: 1.1em; }
    `;
    document.head.appendChild(style);
  }


  container.innerHTML = `
    <div class="quiz-content">
      <div class="quiz-question" aria-live="polite"></div>
      <div class="quiz-options" role="group" aria-label="Answer options">
        <button class="quiz-option" data-key="A" aria-label="Option A"></button>
        <button class="quiz-option" data-key="B" aria-label="Option B"></button>
        <button class="quiz-option" data-key="C" aria-label="Option C"></button>
        <button class="quiz-option" data-key="D" aria-label="Option D"></button>
      </div>
      <div class="quiz-feedback" aria-live="assertive"></div>
      <div class="quiz-meta"></div>
    </div>
  `;

  uiElements = {
    wrapper: container.querySelector('.quiz-content'),
    question: container.querySelector('.quiz-question'),
    options: container.querySelectorAll('.quiz-option'),
    feedback: container.querySelector('.quiz-feedback'),
    meta: container.querySelector('.quiz-meta')
  };


  uiElements.options.forEach(btn => {
    btn.addEventListener('click', () => handleOptionClick(btn.dataset.key));
  });


  document.addEventListener('keydown', handleKeyDown);
}

function handleKeyDown(e) {
  if (!currentQuestion || !uiElements.options) return;
  if (uiElements.options[0].disabled) return;

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
    uiElements.options.forEach(btn => {
      const key = btn.dataset.key;
      const text = question.options ? question.options[key] : '';
      const renderedText = renderLatex(text || '');
      btn.innerHTML = `<b>${key}.</b>&nbsp;${renderedText}`;
      // T049: Update ARIA label with option text
      btn.setAttribute('aria-label', `Option ${key}: ${stripLatex(text || '')}`);
      btn.disabled = false;
      btn.className = 'quiz-option';
    });
  }

  if (uiElements.feedback) {
    uiElements.feedback.innerHTML = '';
    uiElements.feedback.style.color = '';
  }
  
  if (uiElements.meta) {
    uiElements.meta.innerHTML = '';
  }
}

function handleOptionClick(selectedKey) {
  if (!currentQuestion || !uiElements.options) return;
  
  uiElements.options.forEach(btn => btn.disabled = true);

  const correctKey = currentQuestion.correct_answer;
  const isCorrect = selectedKey === correctKey;

  uiElements.options.forEach(btn => {
    const key = btn.dataset.key;
    if (key === selectedKey) {
      btn.classList.add('selected');
      btn.classList.add(isCorrect ? 'correct' : 'incorrect');
    }
    if (key === correctKey) {
      btn.classList.add('correct-highlight');
    }
  });

  if (uiElements.feedback) {
    if (isCorrect) {
      uiElements.feedback.textContent = 'Correct!';
      uiElements.feedback.style.color = '#4caf50';
    } else {
      uiElements.feedback.textContent = `Incorrect — the answer was ${correctKey}`;
      uiElements.feedback.style.color = '#f44336';
    }
  }

  if (uiElements.meta && currentQuestion.source_article) {
    const article = currentQuestion.source_article;
    const url = `https://en.wikipedia.org/wiki/${encodeURIComponent(article)}`;
    uiElements.meta.innerHTML = `Source: <a href="${url}" target="_blank" style="color: inherit; text-decoration: underline;">${article}</a>`;
  }

  if (answerCallback) {
    setTimeout(() => {
      answerCallback(selectedKey, currentQuestion);
    }, 800);
  }
}

export function onAnswer(callback) {
  answerCallback = callback;
}

/**
 * Replaces $...$ with KaTeX rendered HTML.
 * Heuristic: if content between $ signs contains only numbers/punctuation, treat as currency.
 * Fallback: if KaTeX is missing or fails, strips $ delimiters and shows raw text.
 */
export function renderLatex(text) {
  if (!text) return '';
  
  return text.replace(/\$([^$]+)\$/g, (match, content) => {
    if (/^[0-9.,\s]+$/.test(content)) {
      return match;
    }
    
    // T047: Check global failure flag
    if (window.katex && !window.__katexFailed) {
      try {
        return window.katex.renderToString(content, {
          throwOnError: false,
          displayMode: false
        });
      } catch (err) {
        console.warn('KaTeX render error:', err);
        return content; // Fallback to raw content
      }
    }
    
    return content; // Fallback to raw content
  });
}

/**
 * Helper to strip LaTeX delimiters for screen readers
 */
function stripLatex(text) {
  if (!text) return '';
  return text.replace(/\$([^$]+)\$/g, '$1');
}
