/** Main application entry point — wires state, domain loading, estimator, quiz loop, and renderer. */

import { validateSchema, isAvailable, resetAll, exportResponses } from './state/persistence.js';
import {
  $activeDomain,
  $responses,
  $estimates,
  $answeredIds,
  $coverage,
  $questionMode,
} from './state/store.js';
import * as registry from './domain/registry.js';
import { load as loadDomain } from './domain/loader.js';
import { indexQuestions, getAvailableQuestions } from './domain/questions.js';
import { Estimator, DEFAULT_LENGTH_SCALE } from './learning/estimator.js';
import { Sampler } from './learning/sampler.js';
import { getCentrality } from './learning/curriculum.js';
import { Renderer } from './viz/renderer.js';
import { Minimap } from './viz/minimap.js';
import { ParticleSystem } from './viz/particles.js';
import * as controls from './ui/controls.js';
import * as quiz from './ui/quiz.js';
import * as modes from './ui/modes.js';
import * as insights from './ui/insights.js';
import * as share from './ui/share.js';
import { showDownload, hideDownload, updateConfidence, initConfidence } from './ui/progress.js';
import { announce, setupKeyboardNav } from './utils/accessibility.js';

const GLOBAL_REGION = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
const GLOBAL_GRID_SIZE = 50;

function lengthScaleForDomain(domain) {
  if (!domain) return DEFAULT_LENGTH_SCALE;
  if (domain.level === 'all') return DEFAULT_LENGTH_SCALE * 2;
  if (domain.level === 'sub') return DEFAULT_LENGTH_SCALE * 0.5;
  return DEFAULT_LENGTH_SCALE; // general
}

function lengthScaleForDomainId(domainId) {
  const domain = registry.getDomain(domainId);
  return lengthScaleForDomain(domain);
}

function enrichResponsesWithLengthScale(responses) {
  return responses.map(r => {
    if (r.lengthScale != null) return r;
    return { ...r, lengthScale: lengthScaleForDomainId(r.domain_id) };
  });
}

let renderer = null;
let minimap = null;
let particleSystem = null;
let estimator = null;
let globalEstimator = null; // Always covers GLOBAL_REGION for minimap
let sampler = null;
let currentDomainBundle = null;
let currentViewport = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
let currentDomainRegion = GLOBAL_REGION;
let currentGridSize = GLOBAL_GRID_SIZE;
let domainQuestionCount = 0;
let switchGeneration = 0;
let questionIndex = new Map();

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

  const particleCanvas = document.getElementById('particle-canvas');
  if (particleCanvas) {
    particleSystem = new ParticleSystem();
    particleSystem.init(particleCanvas, import.meta.env.BASE_URL || '/');
  }

  renderer = new Renderer();
  renderer.init({
    container: document.getElementById('map-container'),
    onViewportChange: handleViewportChange,
    onCellClick: handleCellClick,
  });

  estimator = new Estimator();
  estimator.init(GLOBAL_GRID_SIZE, GLOBAL_REGION);
  globalEstimator = new Estimator();
  globalEstimator.init(GLOBAL_GRID_SIZE, GLOBAL_REGION);
  sampler = new Sampler();

  const headerEl = document.getElementById('app-header');
  controls.init(headerEl);
  controls.onDomainSelect((domainId) => $activeDomain.set(domainId));
  controls.onReset(handleReset);
  controls.onExport(handleExport);
  controls.onImport(handleImport);

  const landingWrapper = document.getElementById('landing-domain-wrapper');
  if (landingWrapper) {
    controls.createLandingSelector(landingWrapper, (domainId) => $activeDomain.set(domainId));
  }

  const quizPanel = document.getElementById('quiz-panel');
  quiz.init(quizPanel);
  quiz.onAnswer(handleAnswer);
  quiz.onNext(() => selectAndShowNextQuestion());

  renderer.onReanswer((questionId) => {
    const q = questionIndex.get(questionId);
    if (q) quiz.showQuestion(q);
  });

  modes.init(quizPanel);
  modes.onModeSelect(handleModeSelect);
  insights.init();
  initConfidence(quizPanel);

  const trophyBtn = document.getElementById('trophy-btn');
  if (trophyBtn) {
    trophyBtn.addEventListener('click', () => {
      if (!globalEstimator) return;
      // Use global estimator so leaderboard reflects the full map, not just the current domain
      const ck = insights.computeConceptKnowledge(
        globalEstimator.predict(),
        GLOBAL_REGION,
        GLOBAL_GRID_SIZE,
        { global: true },
      );
      insights.showLeaderboard(ck);
    });
  }

  const suggestBtn = document.getElementById('suggest-btn');
  if (suggestBtn) {
    suggestBtn.addEventListener('click', () => {
      if (!globalEstimator) return;
      // Use global estimator so suggestions reflect the full map, not just the current domain
      const ck = insights.computeConceptKnowledge(
        globalEstimator.predict(),
        GLOBAL_REGION,
        GLOBAL_GRID_SIZE,
        { global: true },
      );
      insights.showSuggestions(ck);
    });
  }

  share.init(headerEl, () => renderer._canvas, () => {
    if (!currentDomainBundle) return [];
    const ck = insights.computeConceptKnowledge(
      $estimates.get(),
      currentDomainRegion,
      currentGridSize,
    );
    const sorted = [...ck].sort((a, b) => b.knowledge - a.knowledge);
    return sorted.slice(0, 3).map(c => ({ label: c.concept, value: c.knowledge }));
  }, () => $responses.get().length, () => {
    if (!currentDomainBundle) return null;
    const estimates = $estimates.get();
    const grid = estimates.map(e => e.value);
    const articles = currentDomainBundle.articles.map(a => ({ x: a.x, y: a.y }));
    const responses = $responses.get();
    const answeredQuestions = responses
      .filter(r => r.x != null && r.y != null)
      .map(r => ({ x: r.x, y: r.y, isCorrect: r.is_correct }));
    return { estimateGrid: grid, articles, answeredQuestions };
  });

  const minimapContainer = document.getElementById('minimap-container');
  if (minimapContainer) {
    minimap = new Minimap();
    minimap.init(minimapContainer, registry.getDomains());
    minimap.onClick((domainId) => $activeDomain.set(domainId));
    minimap.onNavigate((region, animated) => {
      if (!renderer) return;
      if (animated) renderer.transitionTo(region, 400);
      else renderer.jumpTo(region);
    });

    // Load "all" domain articles for a static minimap background
    loadDomain('all', {}).then((allBundle) => {
      if (minimap && allBundle) {
        minimap.setArticles(articlesToPoints(allBundle.articles));
      }
    }).catch(() => {}); // Non-critical, minimap will just lack article dots
  }

  if (import.meta.env.DEV) {
    window.__mapper = { registry, estimator, sampler, renderer, minimap, $activeDomain, $estimates, $responses };
  }

  const quizToggle = document.getElementById('quiz-toggle');
  if (quizToggle) {
    quizToggle.addEventListener('click', () => toggleQuizPanel());
  }

  setupKeyboardNav({ onEscape: handleEscape });
  wireSubscriptions();

  announce('Knowledge Mapper loaded. Select a domain to begin.');
}

function wireSubscriptions() {
  $activeDomain.subscribe(async (domainId) => {
    if (!domainId) return;
    await switchDomain(domainId);
  });

  $estimates.subscribe(() => {
    if (!renderer) return;
    // Don't show heatmap until a domain has been selected (welcome screen should be clean)
    if (!currentDomainBundle) return;
    // Both renderer and minimap always show global estimates covering full [0,1] space
    if (globalEstimator) {
      const globalEstimates = globalEstimator.predict();
      renderer.setHeatmap(globalEstimates, GLOBAL_REGION);
      if (minimap) {
        minimap.setEstimates(globalEstimates, GLOBAL_REGION);
      }
    }
  });

  $coverage.subscribe((coverage) => {
    updateConfidence(coverage);
  });
}

function articlesToPoints(articles) {
  return articles.map((a) => ({
    id: a.title,
    x: a.x,
    y: a.y,
    z: a.z || 0,
    type: 'article',
    color: [148, 163, 184, 80],
    radius: 1.5,
    title: a.title,
    url: a.url,
    excerpt: a.excerpt || '',
  }));
}

function responsesToAnsweredDots(responses, qIndex) {
  const latest = new Map();
  for (const r of responses) {
    latest.set(r.question_id, r);
  }
  const dots = [];
  for (const [qid, r] of latest) {
    const q = qIndex.get(qid);
    if (!q) continue;
    dots.push({
      x: r.x,
      y: r.y,
      questionId: qid,
      title: q.question_text,
      isCorrect: r.is_correct,
      color: r.is_correct ? [0, 105, 62, 200] : [157, 22, 46, 200],
    });
  }
  return dots;
}

async function switchDomain(domainId) {
  const generation = ++switchGeneration;
  const landing = document.getElementById('landing');
  if (landing) landing.classList.add('hidden');

  const appEl = document.getElementById('app');
  if (appEl) appEl.dataset.screen = 'map';

  if (particleSystem) {
    particleSystem.destroy();
    particleSystem = null;
  }

  const quizPanel = document.getElementById('quiz-panel');
  const previousBundle = currentDomainBundle;

  renderer.abortTransition();

  try {
    const bundle = await loadDomain(domainId, {
      onProgress: ({ loaded, total }) => showDownload(loaded, total),
      onError: (err) => {
        console.error('[app] Domain load failed:', err);
        announce(`Failed to load domain. ${err.message}`);
      },
    });

    if (generation !== switchGeneration) return;

     currentDomainBundle = bundle;
     indexQuestions(bundle.questions);
     questionIndex = new Map(bundle.questions.map(q => [q.id, q]));
     renderer.clearQuestions();
     renderer.addQuestions(bundle.questions);
     insights.setConcepts(bundle.questions, bundle.articles);
     domainQuestionCount = $responses.get().filter(r => r.domain_id === domainId).length;
     modes.updateAvailability(domainQuestionCount);
     updateInsightButtons($responses.get().length);

    const domain = bundle.domain;
    const domainRegion = domain.region || GLOBAL_REGION;
    const domainGrid = domain.grid_size || GLOBAL_GRID_SIZE;
    currentDomainRegion = domainRegion;
    currentGridSize = domainGrid;

    estimator.init(domainGrid, domainRegion);
    sampler.configure(domainGrid, domainRegion);

    const allResponses = enrichResponsesWithLengthScale($responses.get());
    const relevantResponses = allResponses.filter(
      (r) => r.x != null && r.y != null
    );
    if (relevantResponses.length > 0) {
      estimator.restore(relevantResponses);
      globalEstimator.restore(relevantResponses);
    }

    const estimates = estimator.predict();
    $estimates.set(estimates);

    const targetPoints = articlesToPoints(bundle.articles);

    if (previousBundle) {
      const sourcePoints = articlesToPoints(previousBundle.articles);
      const sourceRegion = previousBundle.domain.region || GLOBAL_REGION;
      const targetRegion = domain.region || GLOBAL_REGION;

      renderer.setLabels(bundle.labels, domainRegion, domainGrid);
      await renderer.transitionPoints(
        sourcePoints, targetPoints, sourceRegion, targetRegion
      );
    } else {
      renderer.setPoints(targetPoints);
      renderer.setLabels(bundle.labels, domainRegion, domainGrid);
      await renderer.transitionTo(domain.region || GLOBAL_REGION);
    }

    if (generation !== switchGeneration) return;

    if (minimap) {
      minimap.setActive(domainId);
      minimap.setViewport(renderer.getViewport());
    }

    toggleQuizPanel(true);
    const toggleBtn = document.getElementById('quiz-toggle');
    if (toggleBtn) toggleBtn.removeAttribute('hidden');
    hideDownload();
    controls.showActionButtons();

    announce(`Loaded ${domain.name}. ${bundle.questions.length} questions available.`);

    renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex));

    selectAndShowNextQuestion();
  } catch (err) {
    if (generation === switchGeneration) {
      hideDownload();
      console.error('[app] switchDomain failed:', err);
    }
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
  const activeMode = modes.getActiveMode();
  const scored = activeMode === 'auto'
    ? sampler.selectNext(available, estimates, currentViewport, answeredIds)
    : sampler.selectByMode(activeMode, available, estimates, currentViewport, answeredIds);

  if (!scored) {
    quiz.showQuestion(available[0]);
    return;
  }

  const question = available.find((q) => q.id === scored.questionId) || available[0];
  quiz.showQuestion(question);
}

function handleModeSelect(modeId) {
  $questionMode.set(modeId);
  selectAndShowNextQuestion();
}

function handleAnswer(selectedKey, question) {
  if (!question || !currentDomainBundle) return;

  const isCorrect = selectedKey === question.correct_answer;

  const questionDomainId = (question.domain_ids || []).find(id => id !== 'all') || currentDomainBundle.domain.id;
  const ls = lengthScaleForDomainId(questionDomainId);

  const response = {
    question_id: question.id,
    domain_id: currentDomainBundle.domain.id,
    selected: selectedKey,
    is_correct: isCorrect,
    timestamp: Date.now(),
    x: question.x,
    y: question.y,
    lengthScale: ls,
  };

  const current = $responses.get();
  const filtered = current.filter(r => r.question_id !== question.id);
  const isReanswer = filtered.length < current.length;
  $responses.set([...filtered, response]);

  estimator.observe(question.x, question.y, isCorrect, ls);
  globalEstimator.observe(question.x, question.y, isCorrect, ls);
  const estimates = estimator.predict();
  $estimates.set(estimates);

  if (!isReanswer) {
    domainQuestionCount++;
    modes.updateAvailability(domainQuestionCount);
    updateInsightButtons($responses.get().length);
  }

  renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex));

  const feedback = isCorrect 
    ? 'Correct!' 
    : `Incorrect. The answer was ${question.correct_answer}.`;
  
  const coverage = Math.round($coverage.get() * 100);
  announce(`${feedback} ${coverage}% of domain mapped. ${50 - domainQuestionCount} questions remaining.`);
  // No auto-advance — user clicks "Next" button in quiz panel
}

function handleReset() {
  if (!confirm('Are you sure? This will clear all progress.')) return;
  resetAll();
  currentDomainBundle = null;
  domainQuestionCount = 0;
  currentDomainRegion = GLOBAL_REGION;
  currentGridSize = GLOBAL_GRID_SIZE;
  switchGeneration++;
  renderer.abortTransition();
  estimator.reset();
  estimator.init(GLOBAL_GRID_SIZE, GLOBAL_REGION);
  globalEstimator.reset();
  globalEstimator.init(GLOBAL_GRID_SIZE, GLOBAL_REGION);
  renderer.setPoints([]);
  renderer.setHeatmap([], GLOBAL_REGION);
  renderer.setLabels([]);
  renderer.setAnsweredQuestions([]);
  renderer.clearQuestions();
  insights.resetGlobalConcepts();
  questionIndex = new Map();
  if (minimap) {
    minimap.setActive(null);
    minimap.setEstimates([]);
  }
  toggleQuizPanel(false);
  const toggleBtn = document.getElementById('quiz-toggle');
  if (toggleBtn) toggleBtn.setAttribute('hidden', '');
  const landing = document.getElementById('landing');
  if (landing) landing.classList.remove('hidden');
  const appEl = document.getElementById('app');
  if (appEl) appEl.dataset.screen = 'welcome';
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

function handleImport(data) {
  if (!data) return;

  let responses = [];
  if (Array.isArray(data)) {
    responses = data;
  } else if (data.responses && Array.isArray(data.responses)) {
    responses = data.responses;
  } else {
    alert('Unrecognized file format. Expected an array of responses or an object with a "responses" key.');
    return;
  }

  const valid = responses.filter(r =>
    r.question_id && r.domain_id && r.selected && typeof r.is_correct === 'boolean'
  );

  if (valid.length === 0) {
    alert('No valid responses found in the imported file.');
    return;
  }

  // Enrich imported responses with x/y coordinates from questionIndex
  // (older exports may lack these, but we need them for the GP estimator)
  let coordsRecovered = 0;
  const enrichedValid = valid.map(r => {
    if (r.x != null && r.y != null) return r;
    const q = questionIndex.get(r.question_id);
    if (q && q.x != null && q.y != null) {
      coordsRecovered++;
      return { ...r, x: q.x, y: q.y };
    }
    return r;
  });

  if (coordsRecovered > 0) {
    console.log(`[import] Recovered x/y coordinates for ${coordsRecovered} responses from question index`);
  }

  const existing = $responses.get();
  const existingIds = new Set(existing.map(r => r.question_id));
  const newResponses = enrichedValid.filter(r => !existingIds.has(r.question_id));
  const merged = [...existing, ...newResponses];

  $responses.set(merged);

  if (estimator) {
    const enriched = enrichResponsesWithLengthScale(merged);
    const relevant = enriched.filter(r => r.x != null && r.y != null);
    estimator.restore(relevant);
    if (globalEstimator) globalEstimator.restore(relevant);
    const estimates = estimator.predict();
    $estimates.set(estimates);

    if (currentDomainBundle) {
      const domainId = currentDomainBundle.domain.id;
      domainQuestionCount = merged.filter(r => r.domain_id === domainId).length;
      modes.updateAvailability(domainQuestionCount);
    }
    renderer.setAnsweredQuestions(responsesToAnsweredDots(merged, questionIndex));
  }

  announce(`Imported ${newResponses.length} new responses (${valid.length} total in file, ${existing.length} already existed).`);
}

function handleViewportChange(viewport) {
  currentViewport = viewport;
  if (minimap) minimap.setViewport(viewport);
}

function handleCellClick(_gx, _gy) {
  // Reserved for future question targeting by cell
}

function handleEscape() {
  const insightsModal = document.getElementById('insights-modal');
  if (insightsModal && !insightsModal.hidden) {
    insightsModal.hidden = true;
    return;
  }
  const aboutModal = document.getElementById('about-modal');
  if (aboutModal && !aboutModal.hidden) {
    aboutModal.hidden = true;
    return;
  }
  const shareModal = document.getElementById('share-modal');
  if (shareModal && !shareModal.hidden) {
    shareModal.hidden = true;
    return;
  }
  toggleQuizPanel(false);
}

function toggleQuizPanel(show) {
  const quizPanel = document.getElementById('quiz-panel');
  const toggleBtn = document.getElementById('quiz-toggle');
  if (!quizPanel) return;

  if (show === undefined) show = !quizPanel.classList.contains('open');

  if (show) {
    quizPanel.classList.add('open');
    if (toggleBtn) {
      toggleBtn.classList.add('panel-open');
      toggleBtn.querySelector('i').className = 'fa-solid fa-chevron-right';
      toggleBtn.setAttribute('aria-label', 'Close quiz panel');
    }
  } else {
    quizPanel.classList.remove('open');
    if (toggleBtn) {
      toggleBtn.classList.remove('panel-open');
      toggleBtn.querySelector('i').className = 'fa-solid fa-chevron-left';
      toggleBtn.setAttribute('aria-label', 'Open quiz panel');
    }
  }
}

function _showBanner(message, type = 'warning') {
  const container = document.getElementById('app-main');
  if (!container) return;

  const banner = document.createElement('div');
  banner.className = `notice-banner ${type}`;
  banner.setAttribute('role', 'alert');

  const content = document.createElement('div');
  content.className = 'notice-banner-content';
  content.textContent = message;

  const dismissBtn = document.createElement('button');
  dismissBtn.className = 'notice-banner-dismiss';
  dismissBtn.setAttribute('aria-label', 'Dismiss notification');
  dismissBtn.innerHTML = '<i class="fa fa-times"></i>';

  const removeBanner = () => {
    banner.classList.add('dismissing');
    setTimeout(() => {
      if (banner.parentNode) banner.parentNode.removeChild(banner);
    }, 300);
  };

  dismissBtn.addEventListener('click', removeBanner);

  banner.appendChild(content);
  banner.appendChild(dismissBtn);
  container.insertBefore(banner, container.firstChild);

  let autoDismissTimer = setTimeout(removeBanner, 8000);

  banner.addEventListener('mouseenter', () => clearTimeout(autoDismissTimer));
  banner.addEventListener('mouseleave', () => {
    autoDismissTimer = setTimeout(removeBanner, 8000);
  });
}

function showNotice(message) {
  console.warn('[mapper]', message);
  announce(message);
  _showBanner(message);
}

function showLandingError(message) {
  const landing = document.getElementById('landing');
  if (landing) {
    const p = landing.querySelector('p');
    if (p) p.textContent = message;
  }
}

const INSIGHT_MIN_ANSWERS = 5;

function updateInsightButtons(answerCount) {
  const trophyBtn = document.getElementById('trophy-btn');
  const suggestBtn = document.getElementById('suggest-btn');
  const ready = answerCount >= INSIGHT_MIN_ANSWERS;
  if (trophyBtn) trophyBtn.disabled = !ready;
  if (suggestBtn) suggestBtn.disabled = !ready;
}

function setupAboutModal() {
  const btn = document.getElementById('about-btn');
  const modal = document.getElementById('about-modal');
  if (!btn || !modal) return;
  btn.addEventListener('click', () => { modal.hidden = !modal.hidden; });
  const closeBtn = modal.querySelector('.close-modal');
  if (closeBtn) closeBtn.addEventListener('click', () => { modal.hidden = true; });

  // Wire up inline info link on landing page to open the about modal
  const landingInfoLink = document.getElementById('landing-info-link');
  if (landingInfoLink) {
    landingInfoLink.addEventListener('click', (e) => {
      e.preventDefault();
      modal.hidden = false;
    });
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { setupAboutModal(); boot(); });
} else {
  setupAboutModal();
  boot();
}

export default boot;
