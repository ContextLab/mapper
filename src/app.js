/** Main application entry point — wires state, domain loading, estimator, quiz loop, and renderer. */

import { validateSchema, isAvailable, resetAll, exportResponses } from './state/persistence.js';
import {
  $activeDomain,
  $responses,
  $estimates,
  $answeredIds,
  $coverage,
} from './state/store.js';
import * as registry from './domain/registry.js';
import { load as loadDomain } from './domain/loader.js';
import { indexQuestions, getAvailableQuestions } from './domain/questions.js';
import { Estimator } from './learning/estimator.js';
import { Sampler } from './learning/sampler.js';
import { getCentrality } from './learning/curriculum.js';
import { Renderer } from './viz/renderer.js';
import * as controls from './ui/controls.js';
import * as quiz from './ui/quiz.js';
import { showDownload, hideDownload, updateConfidence, initConfidence } from './ui/progress.js';
import { announce, setupKeyboardNav } from './utils/accessibility.js';

let renderer = null;
let estimator = null;
let sampler = null;
let currentDomainBundle = null;
let currentViewport = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
let domainQuestionCount = 0;

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
  sampler = new Sampler();

  const headerEl = document.getElementById('app-header');
  controls.init(headerEl);
  controls.onDomainSelect((domainId) => $activeDomain.set(domainId));
  controls.onReset(handleReset);
  controls.onExport(handleExport);

  const quizPanel = document.getElementById('quiz-panel');
  quiz.init(quizPanel);
  quiz.onAnswer(handleAnswer);
  initConfidence(quizPanel);

  if (import.meta.env.DEV) {
    window.__mapper = { registry, estimator, sampler, renderer, $activeDomain, $estimates, $responses };
  }

  setupKeyboardNav({ onEscape: handleEscape });
  wireSubscriptions();

  announce('Wikipedia Knowledge Map loaded. Select a domain to begin.');
}

function wireSubscriptions() {
  $activeDomain.subscribe(async (domainId) => {
    if (!domainId) return;
    await switchDomain(domainId);
  });

  $estimates.subscribe((estimates) => {
    if (!renderer || !currentDomainBundle) return;
    renderer.setHeatmap(estimates, currentDomainBundle.domain.region);
  });

  $coverage.subscribe((coverage) => {
    updateConfidence(coverage);
  });
}

async function switchDomain(domainId) {
  const landing = document.getElementById('landing');
  if (landing) landing.classList.add('hidden');

  const quizPanel = document.getElementById('quiz-panel');

  try {
    const bundle = await loadDomain(domainId, {
      onProgress: ({ loaded, total, percent }) => showDownload(loaded, total),
      onError: (err) => {
        console.error('[app] Domain load failed:', err);
        announce(`Failed to load domain. ${err.message}`);
      },
    });

    currentDomainBundle = bundle;
    indexQuestions(bundle.questions);
    domainQuestionCount = 0;

    const domain = bundle.domain;
    estimator.init(domain.grid_size, domain.region);
    sampler.configure(domain.grid_size, domain.region);

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
    hideDownload();
    controls.showActionButtons();

    announce(`Loaded ${domain.name}. ${bundle.questions.length} questions available.`);

    selectAndShowNextQuestion();
  } catch (err) {
    hideDownload();
    console.error('[app] switchDomain failed:', err);
  }
}

function selectAndShowNextQuestion() {
  if (!currentDomainBundle || !estimator || !sampler) return;

  const answeredIds = $answeredIds.get();
  const available = getAvailableQuestions(currentDomainBundle, answeredIds);

  if (available.length === 0) {
    announce('Domain fully mapped! All questions answered. Try another domain.');
    quiz.showQuestion(null);
    return;
  }

  const estimates = $estimates.get();
  const scored = sampler.selectNext(available, estimates, currentViewport, answeredIds);

  if (!scored) {
    quiz.showQuestion(available[0]);
    return;
  }

  const question = available.find((q) => q.id === scored.questionId) || available[0];
  quiz.showQuestion(question);
}

function handleAnswer(selectedKey, question) {
  if (!question || !currentDomainBundle) return;

  const isCorrect = selectedKey === question.correct_answer;

  const response = {
    question_id: question.id,
    domain_id: currentDomainBundle.domain.id,
    selected: selectedKey,
    is_correct: isCorrect,
    timestamp: Date.now(),
    x: question.x,
    y: question.y,
  };

  const current = $responses.get();
  $responses.set([...current, response]);

  estimator.observe(question.x, question.y, isCorrect);
  const estimates = estimator.predict();
  $estimates.set(estimates);

  domainQuestionCount++;

  const feedback = isCorrect ? 'Correct!' : 'Incorrect.';
  const coverage = Math.round($coverage.get() * 100);
  announce(`${feedback} ${coverage}% of domain mapped. ${50 - domainQuestionCount} questions remaining.`);

  setTimeout(() => {
    selectAndShowNextQuestion();
  }, 900);
}

function handleReset() {
  if (!confirm('Are you sure? This will clear all progress.')) return;
  resetAll();
  currentDomainBundle = null;
  domainQuestionCount = 0;
  estimator.reset();
  renderer.setPoints([]);
  renderer.setHeatmap([], { x_min: 0, x_max: 1, y_min: 0, y_max: 1 });
  renderer.setLabels([]);
  const quizPanel = document.getElementById('quiz-panel');
  if (quizPanel) quizPanel.hidden = true;
  const landing = document.getElementById('landing');
  if (landing) landing.classList.remove('hidden');
  announce('All progress has been reset.');
}

function handleExport() {
  const blob = exportResponses();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `knowledge-map-export-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  announce('Progress exported.');
}

function handleViewportChange(viewport) {
  currentViewport = viewport;
}

function handleCellClick(_gx, _gy) {
  // Reserved for future question targeting by cell
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

function setupAboutModal() {
  const btn = document.getElementById('about-btn');
  const modal = document.getElementById('about-modal');
  if (!btn || !modal) return;
  btn.addEventListener('click', () => { modal.hidden = !modal.hidden; });
  const closeBtn = modal.querySelector('.close-modal');
  if (closeBtn) closeBtn.addEventListener('click', () => { modal.hidden = true; });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { setupAboutModal(); boot(); });
} else {
  setupAboutModal();
  boot();
}

export default boot;
