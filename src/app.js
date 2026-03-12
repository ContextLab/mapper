/** Main application entry point — wires state, domain loading, estimator, quiz loop, and renderer. */

import { validateSchema, isAvailable, resetAll, exportResponses } from './state/persistence.js';
import {
  $activeDomain,
  $responses,
  $estimates,
  $answeredIds,
  $coverage,
  $questionMode,
  $watchedVideos,
  $preVideoSnapshot,
  $runningDifferenceMap,
  $phase,
  $quizDrawerCollapsed,
} from './state/store.js';
import * as registry from './domain/registry.js';
import { load as loadDomain, loadQuestionsForDomain } from './domain/loader.js';
import { indexQuestions } from './domain/questions.js';
import { Estimator } from './learning/estimator.js';
import { Sampler } from './learning/sampler.js';
import { getCentrality } from './learning/curriculum.js';
import { Renderer } from './viz/renderer.js';
import { Minimap } from './viz/minimap.js';
import { ParticleSystem, subsampleParticlePoints } from './viz/particles.js';
import * as controls from './ui/controls.js';
import * as quiz from './ui/quiz.js';
import * as modes from './ui/modes.js';

import * as insights from './ui/insights.js';
import * as share from './ui/share.js';
import { checkMilestone, highlightExpertiseButton, updateProgressDisplay } from './ui/milestones.js';
import { initTutorial, advanceTutorial, isTutorialActive, resetTutorial, dismissTutorial, setAnswerFeedback, goToStep as tutorialGoToStep } from './ui/tutorial.js';
import * as videoModal from './ui/video-modal.js';
import * as videoLoader from './domain/video-loader.js';
import * as videoPanel from './ui/video-panel.js';
import { computeRanking, takeSnapshot, handlePostVideoQuestion } from './learning/video-recommender.js';
import { updateConfidence, initConfidence } from './ui/progress.js';
import { announce, setupKeyboardNav } from './utils/accessibility.js';
import { lockLandscape, unlockOrientation } from './ui/orientation.js';

const GLOBAL_REGION = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
const GLOBAL_GRID_SIZE = 50;

// Uniform length scale for all observations — no per-domain variation.
const UNIFORM_LENGTH_SCALE = 0.18;

let renderer = null;
let minimap = null;
let particleSystem = null;
let estimator = null;
let globalEstimator = null; // Always covers GLOBAL_REGION for minimap
let sampler = null;
let allDomainBundle = null;   // Permanent "all" domain data — never replaced
let currentDomainBundle = null; // Points to allDomainBundle once loaded
let aggregatedQuestions = [];   // Questions for active domain + descendants (CL-049)
let currentViewport = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
let domainQuestionCount = 0;
let consecutiveCorrect = 0;
let switchGeneration = 0;
let questionIndex = new Map();
let mergedVideoWindows = []; // Accumulated window coords from recent unwatched-between videos
let mapInitialized = false; // True once articles/questions/labels are set on the renderer

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
    // Particle data is set later via initWithPoints() after allDomainBundle loads
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
  sampler.configure(GLOBAL_GRID_SIZE, GLOBAL_REGION);

  // Attach the landing button BEFORE the data load so it's responsive immediately.
  // If clicked before data loads, we store the intent and act on it once data arrives.
  let earlyStartRequested = false;
  const landingStartBtn = document.getElementById('landing-start-btn');
  if (landingStartBtn) {
    landingStartBtn.addEventListener('click', () => {
      if (allDomainBundle) {
        // Data already loaded — transition immediately
        $activeDomain.set('all');
      } else {
        // Data still loading — record intent, show loading feedback
        earlyStartRequested = true;
        landingStartBtn.textContent = 'Loading…';
        landingStartBtn.disabled = true;
      }
    });
  }

  // Eagerly load the "all" domain — this is the permanent, full dataset.
  // All articles, questions, and labels come from here; domain selection
  // only pans/zooms the viewport rather than replacing data.
  try {
    allDomainBundle = await loadDomain('all', {});
    indexQuestions(allDomainBundle.questions);
    questionIndex = new Map(allDomainBundle.questions.map(q => [q.id, q]));
    insights.setConcepts(allDomainBundle.questions, allDomainBundle.articles);
    insights.setDomains(registry.getDomains());

    // Signal that data is loaded and button is clickable.
    // Tests wait for [data-ready] before clicking — must come AFTER data loads.
    if (landingStartBtn) landingStartBtn.dataset.ready = 'true';

    // Initialize particles in the background — don't block the transition.
    // If user already clicked start, skip particles entirely (they'd be destroyed anyway).
    if (particleSystem && particleCanvas && !earlyStartRequested) {
      const points = subsampleParticlePoints(allDomainBundle.articles);
      particleSystem.initWithPoints(particleCanvas, points);
    }
  } catch (err) {
    console.error('[app] Failed to pre-load "all" domain:', err);
    showLandingError('Could not load map data. Please try refreshing.');
    return;
  }

  // If user clicked "Map my Knowledge" while data was loading, transition now.
  if (earlyStartRequested) {
    $activeDomain.set('all');
  }

  // Start background video catalog loading (T-V051, FR-V041)
  // Videos are set on the renderer only after map initialization (in switchDomain)
  // so they don't appear as static gray squares on the welcome screen.
  videoLoader.startBackgroundLoad();
  videoLoader.getVideos().promise.then((videos) => {
    if (renderer && videos.length > 0 && mapInitialized) {
      renderer.setVideos(videosToMarkers(videos));
    }
    if (videos && videos.length > 0) {
      videoPanel.setVideos(videosToMarkers(videos));
      if (minimap) minimap.setVideos(videosToLastPoints(videos));
    }
  });

  // Pre-load all domain bundles in the background so domain switches are instant.
  const allDomainIds = registry.getDomains().map(d => d.id).filter(id => id !== 'all');
  for (const id of allDomainIds) {
    loadDomain(id, {}).catch(() => {});  // silent — will retry on demand
  }

  const headerEl = document.getElementById('app-header');
  controls.init(headerEl);
  controls.onDomainSelect((domainId) => $activeDomain.set(domainId));
  controls.onReset(handleReset);
  controls.onExport(handleExport);
  controls.onImport(handleImport);

  // Move action buttons (reset/download/upload) into .header-actions (left group)
  const headerActions = headerEl.querySelector('.header-actions');
  const actionBtns = controls.getActionButtons();
  if (headerActions && actionBtns.importButton) {
    headerActions.appendChild(actionBtns.resetButton);
    headerActions.appendChild(actionBtns.exportButton);
    headerActions.appendChild(actionBtns.importButton);
    for (const btn of [actionBtns.resetButton, actionBtns.exportButton, actionBtns.importButton]) {
      btn.classList.add('btn-icon');
    }
  }

  const quizPanel = document.getElementById('quiz-panel');
  quiz.init(quizPanel);
  quiz.onAnswer(handleAnswer);
  quiz.onNext(() => selectAndShowNextQuestion());

  renderer.onReanswer((questionId) => {
    const q = questionIndex.get(questionId);
    if (q) quiz.showQuestion(q);
  });

  renderer.onVideoClick((hit) => {
    videoModal.playVideo({
      id: hit.videoId,
      title: hit.title,
      duration_s: hit.durationS,
      thumbnail_url: hit.thumbnailUrl,
    });
  });

  // Video discovery panel (left sidebar)
  const videoPanelEl = document.getElementById('video-panel');
  if (videoPanelEl) {
    videoPanel.init(videoPanelEl, {
      onVideoSelect: (video) => videoModal.playVideo(video),
      onVideoHover: (videoId) => {
        if (renderer) renderer.setHoveredVideoId(videoId);
      },
    });
  }

  const videoToggle = document.getElementById('video-toggle');
  if (videoToggle) {
    videoToggle.addEventListener('click', () => toggleVideoPanel());
  }

  modes.init(quizPanel);
  modes.onModeSelect(handleModeSelect);
  modes.onSkip(handleSkip);
  insights.init();
  initConfidence(quizPanel);

  const trophyBtn = document.getElementById('trophy-btn');
  if (trophyBtn) {
    trophyBtn.addEventListener('click', () => {
      if (!globalEstimator) return;
      const dk = insights.computeDomainKnowledge(
        globalEstimator.predict(),
        GLOBAL_REGION,
        GLOBAL_GRID_SIZE,
      );
      insights.showLeaderboard(dk);
      advanceTutorial('expertise-click');
    });
  }

  const suggestBtn = document.getElementById('suggest-btn');
  if (suggestBtn) {
    suggestBtn.addEventListener('click', () => {
      if (!globalEstimator) return;
      advanceTutorial('suggest-click');
      const { data, promise } = videoLoader.getVideos();
      if (data) {
        openVideoModal(data);
      } else {
        videoModal.showVideoModal([]);
        promise.then((videos) => openVideoModal(videos));
      }
    });
  }

  // Initialize video modal and wire completion callback
  videoModal.init();
  videoModal.onVideoComplete(handleVideoComplete);

  // Wire share button click for tutorial
  const shareBtn = document.getElementById('share-btn');
  if (shareBtn) {
    shareBtn.addEventListener('click', () => advanceTutorial('share-click'));
  }

  share.init(headerEl, () => renderer._canvas, () => {
    if (!currentDomainBundle) return [];
    const dk = insights.computeDomainKnowledge(
      globalEstimator.predict(),
      GLOBAL_REGION,
      GLOBAL_GRID_SIZE,
    );
    const evidenced = dk.filter(d => d.hasEvidence !== false);
    const sorted = [...evidenced].sort((a, b) => b.knowledge - a.knowledge);
    return sorted.slice(0, 3).map(d => ({ label: d.name, value: d.knowledge }));
  }, () => $responses.get().length, () => {
    if (!currentDomainBundle) return null;
    const estimates = $estimates.get();
    const grid = estimates.map(e => e.value);
    const articles = currentDomainBundle.articles.map(a => ({ x: a.x, y: a.y }));
    const responses = $responses.get();
    const answeredQuestions = responses
      .filter(r => r.x != null && r.y != null)
      .map(r => ({ x: r.x, y: r.y, isCorrect: r.is_correct, isSkipped: !!r.is_skipped }));
    const { data: videoData } = videoLoader.getVideos();
    const videos = [];
    if (videoData) {
      for (const v of videoData) {
        if (!v.windows || v.windows.length === 0) continue;
        // Only include complete-transcript embedding (last point)
        const last = v.windows[v.windows.length - 1];
        videos.push({ x: last[0], y: last[1] });
      }
    }
    return { estimateGrid: grid, articles, answeredQuestions, videos };
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
    minimap.onPan((cx, cy, animated) => {
      if (!renderer) return;
      renderer.panToCenter(cx, cy, animated);
    });

    // Use the pre-loaded "all" domain for minimap background
    if (allDomainBundle) {
      minimap.setArticles(articlesToPoints(allDomainBundle.articles));
    }
  }

  if (import.meta.env.DEV) {
    window.__mapper = { registry, estimator, sampler, renderer, minimap, $activeDomain, $estimates, $responses, getCurrentQuestion: quiz.getCurrentQuestion, tutorialGoToStep };
  }

  const quizToggle = document.getElementById('quiz-toggle');
  if (quizToggle) {
    quizToggle.addEventListener('click', () => toggleQuizPanel());
  }

  // Mobile drawer pull toggle (custom event from quiz.js)
  const quizPanelEl = document.getElementById('quiz-panel');
  if (quizPanelEl) {
    quizPanelEl.addEventListener('drawer-pull-toggle', () => toggleQuizPanel());
  }

  // Wire auto-advance toggle for tutorial (created dynamically by modes.js)
  document.addEventListener('click', (e) => {
    if (e.target.closest('.auto-advance-track') || e.target.closest('.auto-advance-label')) {
      advanceTutorial('toggle-auto-advance');
    }
  });

  // Wire modal-dismiss for tutorial (insights/share/video modals closing)
  // Uses a body-level observer since insights-modal is created dynamically
  new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === 'attributes' && m.attributeName === 'hidden') {
        const el = m.target;
        if (el.hidden && (el.id === 'insights-modal' || el.id === 'share-modal')) {
          advanceTutorial('modal-dismiss');
        }
      }
    }
  }).observe(document.body, { attributes: true, attributeFilter: ['hidden'], subtree: true });

  setupKeyboardNav({ onEscape: handleEscape });
  wireSubscriptions();

  // Tutorial is initialized after first domain switch (when map becomes visible)
  // See switchDomain() — initTutorial() called there on first run.

  announce('Knowledge Mapper loaded. Select a domain to begin.');
}

/** Update heatmap display on renderer and minimap using global estimates.
 *  Call this after every $estimates.set() instead of doing it via subscription
 *  to avoid a redundant globalEstimator.predict() on every $estimates change.
 *  Returns the global estimates array for callers that need it. */
let _lastGlobalEstimates = null;
function updateHeatmapDisplay() {
  if (!renderer || !currentDomainBundle || !globalEstimator) return null;
  _lastGlobalEstimates = globalEstimator.predict();
  renderer.setHeatmap(_lastGlobalEstimates, GLOBAL_REGION);
  if (minimap) {
    minimap.setEstimates(_lastGlobalEstimates, GLOBAL_REGION);
  }
  return _lastGlobalEstimates;
}

function wireSubscriptions() {
  $activeDomain.subscribe(async (domainId) => {
    if (!domainId) return;
    await switchDomain(domainId);
  });

  // Heatmap display is updated directly via updateHeatmapDisplay() at each
  // $estimates.set() call site — avoids redundant globalEstimator.predict().

  $coverage.subscribe((coverage) => {
    updateConfidence(coverage);
  });

  $watchedVideos.subscribe((watched) => {
    videoPanel.setWatchedVideos(watched);
  });
}

function articlesToPoints(articles) {
  return articles.map((a) => ({
    id: a.title,
    x: a.x,
    y: a.y,
    z: a.z || 0,
    type: 'article',
    color: [0, 0, 0, 30],
    radius: 1.5,
    title: a.title,
    url: a.url,
    excerpt: a.excerpt || '',
  }));
}

function videosToLastPoints(videos) {
  const points = [];
  for (const v of videos) {
    if (!v.windows || v.windows.length === 0) continue;
    const last = v.windows[v.windows.length - 1];
    points.push({ x: last[0], y: last[1] });
  }
  return points;
}

function videosToMarkers(videos) {
  const markers = [];
  for (const v of videos) {
    if (!v.windows) continue;
    for (const [x, y] of v.windows) {
      markers.push({
        x,
        y,
        videoId: v.id,
        title: v.title,
        thumbnailUrl: v.thumbnail_url,
        durationS: v.duration_s,
      });
    }
  }
  return markers;
}

function responsesToAnsweredDots(responses, qIndex) {
  const latest = new Map();
  for (const r of responses) {
    latest.set(r.question_id, r);
  }
  const dots = [];
  for (const [qid, r] of latest) {
    const q = qIndex.get(qid);
    // Show dot if we have coordinates — even if question isn't in index yet (e.g. during import)
    if (!q && (r.x == null || r.y == null)) continue;
    const isSkipped = !!r.is_skipped;
    dots.push({
      x: r.x,
      y: r.y,
      questionId: qid,
      title: q ? q.question_text : 'Imported question',
      isCorrect: r.is_correct,
      isSkipped,
      color: isSkipped ? [212, 160, 23, 200]
           : r.is_correct ? [0, 105, 62, 200]
           : [157, 22, 46, 200],
    });
  }
  return dots;
}

/**
 * Switch to a domain — now only pans/zooms the viewport.
 * All articles, questions, and labels remain from the "all" domain loaded at boot.
 * The first call also initializes the map display (articles, labels, estimator restore).
 */
async function switchDomain(domainId) {
  const generation = ++switchGeneration;
  const landing = document.getElementById('landing');
  if (landing) landing.classList.add('hidden');

  const appEl = document.getElementById('app');
  if (appEl) appEl.dataset.screen = 'map';

  // Force landscape on phone-sized devices
  lockLandscape();

  if (particleSystem) {
    particleSystem.destroy();
    particleSystem = null;
  }

  $quizDrawerCollapsed.set(false);
  renderer.abortTransition();

  if (!allDomainBundle) return;

  // Look up the target domain's region from the registry (index.json).
  // For parent domains, compute the union bounding box of the domain + all descendants
  // so the view encompasses all sub-domain content.
  let targetRegion = GLOBAL_REGION;
  const registryEntry = registry.getDomain(domainId);
  if (registryEntry && registryEntry.region) {
    const descendants = registry.getDescendants(domainId);
    if (descendants.length > 0) {
      let { x_min, x_max, y_min, y_max } = registryEntry.region;
      for (const descId of descendants) {
        const desc = registry.getDomain(descId);
        if (desc && desc.region) {
          x_min = Math.min(x_min, desc.region.x_min);
          x_max = Math.max(x_max, desc.region.x_max);
          y_min = Math.min(y_min, desc.region.y_min);
          y_max = Math.max(y_max, desc.region.y_max);
        }
      }
      targetRegion = { x_min, x_max, y_min, y_max };
    } else {
      targetRegion = registryEntry.region;
    }
  }

  // Ensure the domain bundle is loaded/cached (for questions & labels).
  // Bundles are pre-loaded in the background after boot, so this is usually instant.
  try {
    await loadDomain(domainId, {});
    if (generation !== switchGeneration) return;
  } catch (err) {
    if (generation === switchGeneration) {
      console.error('[app] switchDomain load failed:', err);
    }
  }

  // First-time map initialization: set all articles, questions, labels, and restore GP
  if (!mapInitialized) {
    currentDomainBundle = allDomainBundle;
    renderer.addQuestions(allDomainBundle.questions);
    renderer.setLabels(allDomainBundle.labels, GLOBAL_REGION, GLOBAL_GRID_SIZE);

    // Enrich any responses missing x/y from the question index.
    let allResponses = $responses.get();
    let enriched = 0;
    const patched = allResponses.map(r => {
      if (r.x != null && r.y != null) return r;
      const q = questionIndex.get(r.question_id);
      if (q && q.x != null && q.y != null) {
        enriched++;
        return { ...r, x: q.x, y: q.y };
      }
      return r;
    });
    if (enriched > 0) {
      console.log(`[app] Enriched ${enriched} responses with x/y from question index`);
      $responses.set(patched);
      allResponses = patched;
    }

    const relevantResponses = allResponses.filter(r => r.x != null && r.y != null);
    if (relevantResponses.length > 0) {
      estimator.restore(relevantResponses, UNIFORM_LENGTH_SCALE, questionIndex);
      globalEstimator.restore(relevantResponses, UNIFORM_LENGTH_SCALE, questionIndex);
    }

    const estimates = estimator.predict();
    $estimates.set(estimates);
    updateHeatmapDisplay();

    renderer.setPoints(articlesToPoints(allDomainBundle.articles));
    renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex));

    mapInitialized = true;

    // Start tutorial now that the map is visible (after user clicks "Map my knowledge!")
    initTutorial({ responsesCount: $responses.get().length });

    // Show and wire the tutorial button in the header
    const tutorialBtn = document.getElementById('tutorial-btn');
    if (tutorialBtn) {
      tutorialBtn.hidden = false;
      tutorialBtn.addEventListener('click', () => resetTutorial());
    }

    // Set video markers now that the map is initialized
    const { data: earlyVideos } = videoLoader.getVideos();
    if (earlyVideos && earlyVideos.length > 0) {
      renderer.setVideos(videosToMarkers(earlyVideos));
      videoPanel.setVideos(videosToMarkers(earlyVideos));
      if (minimap) minimap.setVideos(videosToLastPoints(earlyVideos));
    }
  }

  // Aggregate questions for this domain + all descendants (CL-049)
  try {
    aggregatedQuestions = await loadQuestionsForDomain(domainId);
    if (generation !== switchGeneration) return;
    for (const q of aggregatedQuestions) {
      if (!questionIndex.has(q.id)) questionIndex.set(q.id, q);
    }
    indexQuestions(aggregatedQuestions);
    insights.setConcepts(aggregatedQuestions, allDomainBundle.articles);
    renderer.addQuestions(aggregatedQuestions);
  } catch (err) {
    console.error('[app] Question aggregation failed:', err);
    aggregatedQuestions = allDomainBundle ? allDomainBundle.questions : [];
  }

  // Re-apply answered dots now that questionIndex is fully populated
  // (fixes import-from-landing-page showing only the first dot)
  renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex));

  // Update domain-scoped tracking
  domainQuestionCount = $responses.get().length;
  modes.updateAvailability(domainQuestionCount);
  updateInsightButtons($responses.get().length);

  // Pan/zoom to the target domain's region
  await renderer.transitionTo(targetRegion);

  if (generation !== switchGeneration) return;

  if (minimap) {
    minimap.setActive(domainId);
    minimap.setViewport(renderer.getViewport());
  }

  toggleQuizPanel(true);
  const toggleBtn = document.getElementById('quiz-toggle');
  if (toggleBtn) toggleBtn.removeAttribute('hidden');
  const videoToggleBtn = document.getElementById('video-toggle');
  if (videoToggleBtn) videoToggleBtn.removeAttribute('hidden');
  controls.showActionButtons();

  // Set initial scroll positions for header button groups
  const headerActionsBar = document.querySelector('.header-actions');
  if (headerActionsBar) headerActionsBar.scrollLeft = 0; // left buttons visible
  const headerRightBar = document.querySelector('.header-right');
  if (headerRightBar) headerRightBar.scrollLeft = headerRightBar.scrollWidth; // right buttons visible

  const domainName = registry.getDomains().find(d => d.id === domainId)?.name || domainId;
  announce(`Navigated to ${domainName}. ${aggregatedQuestions.length} questions available.`);

  modes.setSkipVisible(true);
  selectAndShowNextQuestion();

  // Advance tutorial on domain switch
  advanceTutorial('domain-change');
}

function selectAndShowNextQuestion() {
  if (!currentDomainBundle || !estimator || !sampler) return;

  const answeredIds = $answeredIds.get();
  // Use aggregated questions (own + descendants) per CL-049
  const pool = aggregatedQuestions.length > 0 ? aggregatedQuestions : (currentDomainBundle.questions || []);
  let available = pool.filter(q => !answeredIds.has(q.id) && quiz.isValidQuestion(q).valid);

  // Filter to questions belonging to the active domain's lineage (CL-T014)
  const activeDomain = $activeDomain.get();
  if (activeDomain && activeDomain !== 'all') {
    const descendants = registry.getDescendants(activeDomain);
    const domainObj = registry.getDomain(activeDomain);
    const validIds = new Set([activeDomain, ...descendants]);
    if (domainObj && domainObj.parent_id) validIds.add(domainObj.parent_id);
    available = available.filter(q =>
      q.domain_ids && q.domain_ids.some(id => validIds.has(id))
    );
  }

  if (available.length === 0) {
    // Check if ALL domains are exhausted or just the current one
    const allPool = (currentDomainBundle.questions || []);
    const allExhausted = allPool.every(q => answeredIds.has(q.id) || !quiz.isValidQuestion(q).valid);
    const msg = allExhausted
      ? "You've finished mapping your knowledge. Congratulations!"
      : "You've finished mapping this domain; try choosing another domain from the dropdown menu!";
    announce(msg);
    quiz.showQuestion(null, msg);
    modes.setSkipVisible(false);
    progress.updateConfidence(1.0);
    return;
  }

  const estimates = $estimates.get();
  const activeMode = modes.getActiveMode();
  const phase = $phase.get();
  const scored = activeMode === 'auto'
    ? sampler.selectNext(available, estimates, currentViewport, answeredIds, phase)
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

  // Tag the response with the user's currently selected domain (for tracking),
  // not the bundle's domain id (which is always "all" now).
  const activeDomainId = $activeDomain.get() || 'all';

  const response = {
    question_id: question.id,
    domain_id: activeDomainId,
    selected: selectedKey,
    is_correct: isCorrect,
    difficulty: question.difficulty,
    timestamp: Date.now(),
    x: question.x,
    y: question.y,
  };

  const current = $responses.get();
  const filtered = current.filter(r => r.question_id !== question.id);
  const isReanswer = filtered.length < current.length;
  $responses.set([...filtered, response]);

  if (!isReanswer) {
    domainQuestionCount++;
    modes.updateAvailability(domainQuestionCount);
    updateInsightButtons($responses.get().length);
  }

  // Show answer dot and feedback immediately (before expensive GP computation)
  renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex));

  const feedback = isCorrect ? 'Correct!' : 'Incorrect.';
  announce(`${feedback}`);

  // Revert non-auto modes (easy/hardest/dont-know) back to auto after one answer
  modes.revertToAutoIfNeeded();

  // Auto-advance after a short delay if the toggle is on
  if (modes.isAutoAdvance()) {
    setTimeout(() => selectAndShowNextQuestion(), 800);
  }

  // Defer expensive GP computation so UI stays responsive (Issue #26)
  const difficulty = question.difficulty;
  const qx = question.x, qy = question.y;
  setTimeout(() => {
    estimator.observe(qx, qy, isCorrect, UNIFORM_LENGTH_SCALE, difficulty);
    globalEstimator.observe(qx, qy, isCorrect, UNIFORM_LENGTH_SCALE, difficulty);
    const estimates = estimator.predict();
    $estimates.set(estimates);
    updateHeatmapDisplay();

    const coverage = Math.round($coverage.get() * 100);
    announce(`${coverage}% mapped.`);

    // Video recommendation: post-video diff map flow (T-V052, FR-V021)
    if ($preVideoSnapshot.get() !== null) {
      // Reuse global estimates already computed by updateHeatmapDisplay above
      const globalEstimates = _lastGlobalEstimates || globalEstimator.predict();
      const result = handlePostVideoQuestion(globalEstimates, mergedVideoWindows);
      if (result.phaseComplete) {
        mergedVideoWindows = [];
      }
    }
  }, 0);

  // Engagement: track streak, update progress display, check milestones
  if (isCorrect) {
    consecutiveCorrect++;
  } else {
    consecutiveCorrect = 0;
  }
  const totalAnswered = $responses.get().length;
  updateProgressDisplay(totalAnswered, consecutiveCorrect);
  if (!isTutorialActive()) {
    checkMilestone(totalAnswered);
  }
  if (totalAnswered >= 15 && !isTutorialActive()) {
    highlightExpertiseButton();
  }

  // Advance tutorial on answer event (pass feedback for step 2)
  setAnswerFeedback(isCorrect);
  advanceTutorial('answer');
}

function handleSkip() {
  const question = quiz.getCurrentQuestion();
  if (!question || !currentDomainBundle) return;

  const activeDomainId = $activeDomain.get() || 'all';

  const response = {
    question_id: question.id,
    domain_id: activeDomainId,
    selected: null,
    is_correct: false,
    is_skipped: true,
    difficulty: question.difficulty,
    timestamp: Date.now(),
    x: question.x,
    y: question.y,
  };

  const current = $responses.get();
  const filtered = current.filter(r => r.question_id !== question.id);
  const isReanswer = filtered.length < current.length;
  $responses.set([...filtered, response]);

  if (!isReanswer) {
    domainQuestionCount++;
    modes.updateAvailability(domainQuestionCount);
    updateInsightButtons($responses.get().length);
  }

  // Show answer dot and feedback immediately (before expensive GP computation)
  renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex));

  // Show feedback with correct answer highlighted (like wrong-answer flow)
  quiz.showSkipFeedback(question);
  announce('Skipped. The correct answer is highlighted.');

  // Reset streak and update progress display
  consecutiveCorrect = 0;
  const totalAnswered = $responses.get().length;
  updateProgressDisplay(totalAnswered, consecutiveCorrect);

  // Revert non-auto modes back to auto after skip
  modes.revertToAutoIfNeeded();

  // Auto-advance after delay if toggle is on; otherwise user clicks "Next"
  if (modes.isAutoAdvance()) {
    setTimeout(() => selectAndShowNextQuestion(), 800);
  }

  // Defer expensive GP computation so UI stays responsive (Issue #26)
  const difficulty = question.difficulty;
  const qx = question.x, qy = question.y;
  setTimeout(() => {
    estimator.observeSkip(qx, qy, UNIFORM_LENGTH_SCALE, difficulty);
    globalEstimator.observeSkip(qx, qy, UNIFORM_LENGTH_SCALE, difficulty);
    const estimates = estimator.predict();
    $estimates.set(estimates);
    updateHeatmapDisplay();
  }, 0);

  // Advance tutorial on skip event
  setAnswerFeedback(false, true);
  advanceTutorial('skip');
}

function handleReset() {
  if (!confirm('Are you sure? This will clear all progress.')) return;
  dismissTutorial();
  // Clear tutorial state so it re-shows on next domain select (like first visit)
  try { localStorage.removeItem('mapper-tutorial'); } catch { /* noop */ }
  // Release landscape lock so welcome screen can be portrait
  unlockOrientation();
  resetAll();
  currentDomainBundle = null;
  mapInitialized = false;
  domainQuestionCount = 0;
  aggregatedQuestions = [];
  switchGeneration++;
  renderer.abortTransition();
  estimator.reset();
  estimator.init(GLOBAL_GRID_SIZE, GLOBAL_REGION);
  globalEstimator.reset();
  globalEstimator.init(GLOBAL_GRID_SIZE, GLOBAL_REGION);
  renderer.setPoints([]);
  renderer.setVideos([]);
  renderer.setHeatmap([], GLOBAL_REGION);
  renderer.setLabels([]);
  renderer.setAnsweredQuestions([]);
  renderer.clearQuestions();
  insights.resetGlobalConcepts();
  insights.resetDomains();
  videoModal.hide();
  mergedVideoWindows = [];
  // Re-set concepts and domains from the permanent "all" bundle so insights work on next domain select
  if (allDomainBundle) {
    insights.setConcepts(allDomainBundle.questions, allDomainBundle.articles);
    insights.setDomains(registry.getDomains());
  }
  questionIndex = allDomainBundle
    ? new Map(allDomainBundle.questions.map(q => [q.id, q]))
    : new Map();
  if (minimap) {
    minimap.setActive(null);
    minimap.setEstimates([]);
  }
  // Reset viewport to full map
  renderer.jumpTo(GLOBAL_REGION);
  toggleQuizPanel(false);
  toggleVideoPanel(false);
  const toggleBtn = document.getElementById('quiz-toggle');
  if (toggleBtn) toggleBtn.setAttribute('hidden', '');
  const videoToggleBtn = document.getElementById('video-toggle');
  if (videoToggleBtn) videoToggleBtn.setAttribute('hidden', '');
  const landing = document.getElementById('landing');
  if (landing) landing.classList.remove('hidden');
  const appEl = document.getElementById('app');
  if (appEl) appEl.dataset.screen = 'welcome';

  // Re-create particle system for the welcome screen
  const pCanvas = document.getElementById('particle-canvas');
  if (pCanvas && allDomainBundle) {
    particleSystem = new ParticleSystem();
    const points = subsampleParticlePoints(allDomainBundle.articles);
    particleSystem.initWithPoints(pCanvas, points);
  }

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
  console.log('[import] handleImport called with', data ? 'data' : 'null');
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
    r.question_id && r.domain_id && typeof r.is_correct === 'boolean'
    && (r.selected || r.is_skipped || r.selected === null)
  ).map(r => {
    // Infer is_skipped for older exports that lack the field
    if (!r.is_skipped && r.selected === null) {
      return { ...r, is_skipped: true };
    }
    return r;
  });

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
    const relevant = merged.filter(r => r.x != null && r.y != null);
    estimator.restore(relevant, UNIFORM_LENGTH_SCALE, questionIndex);
    if (globalEstimator) globalEstimator.restore(relevant, UNIFORM_LENGTH_SCALE, questionIndex);
    const estimates = estimator.predict();
    $estimates.set(estimates);
    updateHeatmapDisplay();

    domainQuestionCount = merged.length;
    modes.updateAvailability(domainQuestionCount);
    renderer.setAnsweredQuestions(responsesToAnsweredDots(merged, questionIndex));
  }

  const msg = `Imported ${newResponses.length} new responses (${valid.length} total in file, ${existing.length} already existed).`;
  announce(msg);
  _showBanner(msg, 'success');
  console.log('[import]', msg);

  // If we're still on the welcome screen, switch to map view with "all" domain.
  if (!currentDomainBundle) {
    controls.setSelectedDomain('all');
    $activeDomain.set('all');
  }
}

function handleViewportChange(viewport) {
  currentViewport = viewport;
  if (minimap) minimap.setViewport(viewport);
  videoPanel.updateViewport(viewport);
}

function handleCellClick(_gx, _gy) {
  // Reserved for future question targeting by cell
}

function handleEscape() {
  if (videoModal.handleEscape()) return;
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
    // On mobile, close the video panel to avoid overlapping bottom sheets
    if (window.innerWidth <= 480) {
      const videoEl = document.getElementById('video-panel');
      if (videoEl && videoEl.classList.contains('open')) {
        toggleVideoPanel(false);
      }
    }
    quizPanel.classList.add('open');
    // On mobile, ensure drawer-collapsed is cleared when opening
    if (window.innerWidth <= 480) $quizDrawerCollapsed.set(false);
    if (toggleBtn) {
      toggleBtn.querySelector('i').className = 'fa-solid fa-chevron-right';
      toggleBtn.setAttribute('aria-label', 'Close quiz panel');
    }
  } else {
    quizPanel.classList.remove('open');
    if (toggleBtn) {
      toggleBtn.querySelector('i').className = 'fa-solid fa-chevron-left';
      toggleBtn.setAttribute('aria-label', 'Open quiz panel');
    }
  }
}

function toggleVideoPanel(show) {
  const panel = document.getElementById('video-panel');
  const toggleBtn = document.getElementById('video-toggle');
  if (!panel) return;

  if (show === undefined) show = !panel.classList.contains('open');

  if (show) {
    // On mobile, close the quiz panel to avoid overlapping bottom sheets
    if (window.innerWidth <= 480) {
      toggleQuizPanel(false);
    }
    panel.classList.add('open');
    if (toggleBtn) {
      toggleBtn.querySelector('i').className = 'fa-solid fa-chevron-left';
      toggleBtn.setAttribute('aria-label', 'Close video panel');
    }
  } else {
    panel.classList.remove('open');
    if (toggleBtn) {
      toggleBtn.querySelector('i').className = 'fa-solid fa-chevron-right';
      toggleBtn.setAttribute('aria-label', 'Open video panel');
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

  const iconEl = document.createElement('i');
  iconEl.className = 'fa fa-times';
  dismissBtn.appendChild(iconEl);

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

// ─── Video recommendation helpers (T-V050, T-V051, T-V052) ──

function openVideoModal(videos) {
  if (!globalEstimator) return;
  const globalEstimates = globalEstimator.predict();
  const watchedIds = $watchedVideos.get();
  const runningDiffMap = $runningDifferenceMap.get();
  const ranked = computeRanking(videos, globalEstimates, watchedIds, runningDiffMap);
  videoModal.showVideoModal(ranked);
}

function handleVideoComplete(videoId) {
  if (!globalEstimator) return;
  // Take snapshot for diff map computation (FR-V020, CL-004)
  const globalEstimates = globalEstimator.predict();
  const snapshotTaken = takeSnapshot(globalEstimates);

  // Find the completed video's windows and merge them
  const { data } = videoLoader.getVideos();
  if (data) {
    const video = data.find((v) => v.id === videoId);
    if (video && video.windows) {
      if (snapshotTaken) {
        mergedVideoWindows = [...video.windows];
      } else {
        // Multiple videos without questions — merge windows (CL-004)
        mergedVideoWindows = mergedVideoWindows.concat(video.windows);
      }
    }
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
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.hidden) modal.hidden = true;
  });

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
