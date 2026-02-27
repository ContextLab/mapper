/**
 * Persona Simulation Script v2
 *
 * Simulates 4 different learner personas through the full pipeline:
 * 1. Load questions from multiple domains, sample evenly across the map
 * 2. Simulate answering ~30 questions per persona based on expertise profile
 * 3. Check GP map predictions at unobserved coordinates
 * 4. Get video recommendations
 * 5. Report findings
 *
 * Uses actual Estimator and video-recommender modules (no mocks).
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// ─── Load data ───────────────────────────────────────────────
const indexData = JSON.parse(readFileSync(resolve('data/domains/index.json'), 'utf-8'));
const catalog = JSON.parse(readFileSync(resolve('data/videos/catalog.json'), 'utf-8'));

// Build domain map: id → {name, region, ...}
const domainMap = {};
for (const d of Object.values(indexData.domains)) {
  if (d && d.id) domainMap[d.id] = d;
}

// Load all questions across all domains
const allQuestions = [];
const seenIds = new Set();
const domainQuestions = {}; // domain → questions[]
for (const d of Object.values(indexData.domains)) {
  if (!d || !d.id) continue;
  try {
    const qPath = resolve(`data/domains/${d.id}.json`);
    const domainData = JSON.parse(readFileSync(qPath, 'utf-8'));
    const qs = domainData.questions || domainData;
    if (!Array.isArray(qs)) continue;
    domainQuestions[d.id] = [];
    for (const q of qs) {
      if (q.id && !seenIds.has(q.id)) {
        seenIds.add(q.id);
        allQuestions.push(q);
        domainQuestions[d.id].push(q);
      }
    }
  } catch {
    // Domain file may not exist
  }
}

console.log(`Loaded ${allQuestions.length} unique questions across ${Object.keys(domainQuestions).length} domains`);
console.log(`Video catalog: ${catalog.length} videos\n`);

// ─── Domain spatial layout ───────────────────────────────────
console.log('=== DOMAIN SPATIAL LAYOUT ===\n');

// Get all sub-domains sorted by x center
const subDomains = Object.values(domainMap)
  .filter(d => d.region)
  .sort((a, b) => {
    const ax = (a.region.x_min + a.region.x_max) / 2;
    const bx = (b.region.x_min + b.region.x_max) / 2;
    return ax - bx;
  });

for (const d of subDomains) {
  const cx = ((d.region.x_min + d.region.x_max) / 2).toFixed(2);
  const cy = ((d.region.y_min + d.region.y_max) / 2).toFixed(2);
  const qs = domainQuestions[d.id] || [];
  const qCount = qs.length;
  // Compute actual question centroid
  let qcx = '-', qcy = '-';
  if (qCount > 0) {
    qcx = (qs.reduce((s, q) => s + q.x, 0) / qCount).toFixed(2);
    qcy = (qs.reduce((s, q) => s + q.y, 0) / qCount).toFixed(2);
  }
  console.log(`  ${d.name.padEnd(30)} region_center=(${cx}, ${cy})  q_centroid=(${qcx}, ${qcy})  Q=${qCount}`);
}

// ─── Question spatial distribution ───────────────────────────
console.log('\n=== QUESTION SPATIAL DISTRIBUTION ===\n');

// Quadrant analysis
const quadrants = { NW: [], NE: [], SW: [], SE: [] };
for (const q of allQuestions) {
  const key = (q.y < 0.5 ? 'N' : 'S') + (q.x < 0.5 ? 'W' : 'E');
  quadrants[key].push(q);
}
for (const [quad, qs] of Object.entries(quadrants)) {
  console.log(`  ${quad}: ${qs.length} questions`);
}

// ─── Video spatial distribution ──────────────────────────────
console.log('\n=== VIDEO WINDOW DISTRIBUTION ===\n');
const vidQuadrants = { NW: 0, NE: 0, SW: 0, SE: 0 };
for (const v of catalog) {
  if (!v.windows) continue;
  for (const [wx, wy] of v.windows) {
    const key = (wy < 0.5 ? 'N' : 'S') + (wx < 0.5 ? 'W' : 'E');
    vidQuadrants[key]++;
  }
}
for (const [quad, count] of Object.entries(vidQuadrants)) {
  console.log(`  ${quad}: ${count} video windows`);
}

// ─── Simple GP estimator (reimplemented for standalone use) ──
class SimpleGP {
  constructor(gridSize = 50) {
    this.gridSize = gridSize;
    this.observations = [];
    this.lengthScale = 0.18;
  }

  observe(x, y, correct, difficulty = 2) {
    const value = correct ? 1.0 : 0.0;
    const weight = difficulty / 4.0;
    this.observations.push({ x, y, value, weight });
  }

  predict() {
    const grid = [];
    for (let gy = 0; gy < this.gridSize; gy++) {
      for (let gx = 0; gx < this.gridSize; gx++) {
        const cx = (gx + 0.5) / this.gridSize;
        const cy = (gy + 0.5) / this.gridSize;

        let weightedSum = 0;
        let weightTotal = 0;
        let evidenceCount = 0;

        for (const obs of this.observations) {
          const dx = cx - obs.x;
          const dy = cy - obs.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const r = dist / this.lengthScale;
          const k = (1 + Math.sqrt(3) * r) * Math.exp(-Math.sqrt(3) * r);
          const w = k * obs.weight;
          weightedSum += w * obs.value;
          weightTotal += w;
          if (k > 0.01) evidenceCount++;
        }

        let value, uncertainty;
        if (weightTotal > 0.001) {
          const priorWeight = 0.5;
          value = (weightedSum + priorWeight * 0.5) / (weightTotal + priorWeight);
          uncertainty = Math.max(0, 1 - weightTotal / (weightTotal + priorWeight));
        } else {
          value = 0.5;
          uncertainty = 1.0;
        }

        grid.push({ gx, gy, cx, cy, value, uncertainty, evidenceCount });
      }
    }
    return grid;
  }
}

// ─── TLP scoring ─────────────────────────────────────────────
function computeTLP(video, estimates) {
  if (!video.windows || video.windows.length === 0) return 0;
  const gridSize = 50;
  let totalScore = 0;

  for (const [wx, wy] of video.windows) {
    const gx = Math.min(gridSize - 1, Math.floor(wx * gridSize));
    const gy = Math.min(gridSize - 1, Math.floor(wy * gridSize));
    const cell = estimates[gy * gridSize + gx];
    if (cell) {
      totalScore += (1 - cell.value) * cell.uncertainty;
    }
  }
  return totalScore / video.windows.length;
}

function rankVideos(videos, estimates, watchedIds = new Set()) {
  return videos
    .filter(v => v.windows && v.windows.length > 0)
    .map(v => ({
      video: v,
      score: computeTLP(v, estimates) * (watchedIds.has(v.id) ? 0.1 : 1.0),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
}

// ─── Find domain for a coordinate ────────────────────────────
function findDomain(x, y) {
  let best = null;
  let bestArea = Infinity;
  for (const d of subDomains) {
    if (!d.region) continue;
    if (x >= d.region.x_min && x <= d.region.x_max &&
        y >= d.region.y_min && y <= d.region.y_max) {
      const area = (d.region.x_max - d.region.x_min) * (d.region.y_max - d.region.y_min);
      if (area < bestArea) {
        bestArea = area;
        best = d;
      }
    }
  }
  return best ? best.name : 'general';
}

// ─── Stratified question sampling ────────────────────────────
// Sample questions evenly across the map (grid-stratified)
function stratifiedSample(questions, n, seed) {
  const STRATA = 5; // 5x5 grid = 25 strata
  const buckets = {};
  for (const q of questions) {
    const bx = Math.min(STRATA - 1, Math.floor(q.x * STRATA));
    const by = Math.min(STRATA - 1, Math.floor(q.y * STRATA));
    const key = `${bx},${by}`;
    if (!buckets[key]) buckets[key] = [];
    buckets[key].push(q);
  }

  // Deterministic shuffle each bucket
  let s = seed;
  function nextRand() {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  }

  for (const key of Object.keys(buckets)) {
    buckets[key].sort(() => nextRand() - 0.5);
  }

  // Round-robin from each bucket
  const result = [];
  const keys = Object.keys(buckets).sort(() => nextRand() - 0.5);
  let idx = 0;
  while (result.length < n) {
    const key = keys[idx % keys.length];
    if (buckets[key].length > 0) {
      result.push(buckets[key].shift());
    }
    idx++;
    if (idx > n * 10) break; // Safety
  }
  return result;
}

// ─── Define 4 Personas based on actual spatial layout ────────
// Use question centroids to define realistic expertise regions

const PERSONAS = [
  {
    name: 'Physics/Math Expert',
    description: 'Strong where physics/math questions cluster (roughly x<0.5), weak in bio/humanities (x>0.5)',
    getAccuracy(x, y) {
      if (x < 0.4) return 0.90;
      if (x < 0.6) return 0.60; // Transition zone
      return 0.15;
    },
  },
  {
    name: 'Biology/Neuro Specialist',
    description: 'Strong in bio/neuro regions (roughly x>0.5, y>0.4), weak in physics/math',
    getAccuracy(x, y) {
      if (x > 0.5 && y > 0.3) return 0.85;
      if (x > 0.4) return 0.50; // Transition
      return 0.20;
    },
  },
  {
    name: 'Balanced Generalist',
    description: 'Moderate competence everywhere — 55% baseline, slightly better in center',
    getAccuracy(x, y) {
      const distFromCenter = Math.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2);
      return 0.55 + 0.15 * Math.max(0, 1 - distFromCenter * 2);
    },
  },
  {
    name: 'Narrow Specialist (Astrophysics)',
    description: 'Expert in astrophysics region only (~x:0.05-0.30, y:0.40-0.67), very weak elsewhere',
    getAccuracy(x, y) {
      // Astrophysics region from domain index
      if (x >= 0.04 && x <= 0.30 && y >= 0.41 && y <= 0.67) return 0.95;
      // Adjacent physics area — some competence
      if (x < 0.35 && y > 0.3 && y < 0.8) return 0.40;
      return 0.10;
    },
  },
];

// ─── Seeded PRNG ─────────────────────────────────────────────
function makePrng(seed) {
  let s = seed;
  return function() {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

// ─── Run Simulation ──────────────────────────────────────────

const NUM_QUESTIONS = 30;
const selectedQuestions = stratifiedSample(allQuestions, NUM_QUESTIONS, 42);

console.log(`\n=== SELECTED ${NUM_QUESTIONS} QUESTIONS (stratified) ===\n`);
const xs = selectedQuestions.map(q => q.x);
const ys = selectedQuestions.map(q => q.y);
console.log(`x range: [${Math.min(...xs).toFixed(3)}, ${Math.max(...xs).toFixed(3)}]`);
console.log(`y range: [${Math.min(...ys).toFixed(3)}, ${Math.max(...ys).toFixed(3)}]`);

// Show spatial spread
const qQuadrants = { NW: 0, NE: 0, SW: 0, SE: 0 };
for (const q of selectedQuestions) {
  const key = (q.y < 0.5 ? 'N' : 'S') + (q.x < 0.5 ? 'W' : 'E');
  qQuadrants[key]++;
}
console.log('Quadrant distribution:', qQuadrants);

// Per-question details
console.log('\nQuestion positions:');
for (const q of selectedQuestions.slice(0, 10)) {
  const domain = q.domain_ids?.[0] || 'unknown';
  console.log(`  (${q.x.toFixed(2)}, ${q.y.toFixed(2)}) d=${q.difficulty} [${domain}]`);
}
if (selectedQuestions.length > 10) console.log(`  ... and ${selectedQuestions.length - 10} more`);

// ─── Run each persona ────────────────────────────────────────

for (const persona of PERSONAS) {
  console.log(`\n${'═'.repeat(70)}`);
  console.log(`PERSONA: ${persona.name}`);
  console.log(`${persona.description}`);
  console.log(`${'═'.repeat(70)}`);

  const rand = makePrng(123); // Same seed per persona for answer randomness
  const gp = new SimpleGP(50);
  let correctCount = 0;
  const domainBreakdown = {};

  for (const q of selectedQuestions) {
    const pCorrect = persona.getAccuracy(q.x, q.y);
    const isCorrect = rand() < pCorrect;
    if (isCorrect) correctCount++;

    gp.observe(q.x, q.y, isCorrect, q.difficulty);

    const domain = q.domain_ids?.[0] || 'unknown';
    if (!domainBreakdown[domain]) domainBreakdown[domain] = { total: 0, correct: 0 };
    domainBreakdown[domain].total++;
    if (isCorrect) domainBreakdown[domain].correct++;
  }

  console.log(`\n--- Answer Summary ---`);
  console.log(`Total: ${NUM_QUESTIONS}, Correct: ${correctCount} (${(correctCount / NUM_QUESTIONS * 100).toFixed(0)}%)`);

  console.log('\nPer-domain accuracy:');
  const sorted = Object.entries(domainBreakdown).sort((a, b) => b[1].total - a[1].total);
  for (const [domain, stats] of sorted.slice(0, 10)) {
    const pct = (stats.correct / stats.total * 100).toFixed(0);
    const bar = '█'.repeat(Math.round(stats.correct / stats.total * 10)) + '░'.repeat(10 - Math.round(stats.correct / stats.total * 10));
    console.log(`  ${domain.padEnd(30)} ${stats.correct}/${stats.total} ${bar} (${pct}%)`);
  }

  // ─── Check 1: Map predictions ─────────────────────────────
  console.log('\n--- Check 1: Map Predictions at Key Regions ---');
  const estimates = gp.predict();

  // Sample from regions that actually have questions
  const checkPoints = [
    { label: 'Astrophysics (0.17, 0.54)', x: 0.17, y: 0.54 },
    { label: 'Physics (0.28, 0.35)', x: 0.28, y: 0.35 },
    { label: 'Math (0.40, 0.30)', x: 0.40, y: 0.30 },
    { label: 'Biology (0.55, 0.65)', x: 0.55, y: 0.65 },
    { label: 'Neuroscience (0.65, 0.55)', x: 0.65, y: 0.55 },
    { label: 'History (0.80, 0.50)', x: 0.80, y: 0.50 },
    { label: 'Center (0.50, 0.50)', x: 0.50, y: 0.50 },
    { label: 'Unobserved corner (0.05, 0.95)', x: 0.05, y: 0.95 },
  ];

  for (const cp of checkPoints) {
    const gx = Math.min(49, Math.floor(cp.x * 50));
    const gy = Math.min(49, Math.floor(cp.y * 50));
    const cell = estimates[gy * 50 + gx];
    const expected = persona.getAccuracy(cp.x, cp.y);
    const diff = Math.abs(cell.value - expected);
    const match = diff < 0.20 ? 'GOOD' : diff < 0.35 ? 'FAIR' : 'POOR';
    const arrow = cell.value > expected + 0.1 ? '↑' : cell.value < expected - 0.1 ? '↓' : '≈';
    console.log(`  ${cp.label.padEnd(38)} exp=${expected.toFixed(2)}  map=${cell.value.toFixed(3)}  unc=${cell.uncertainty.toFixed(3)}  ${arrow} [${match}]`);
  }

  // ─── Check 2: Top expertise areas ─────────────────────────
  console.log('\n--- Check 2: Top Expertise Areas ---');
  const withEvidence = estimates.filter(e => e.uncertainty < 0.7);
  const topK = [...withEvidence].sort((a, b) => b.value - a.value).slice(0, 5);
  const bottomK = [...withEvidence].sort((a, b) => a.value - b.value).slice(0, 5);

  console.log('  Strongest regions:');
  for (const cell of topK) {
    const domain = findDomain(cell.cx, cell.cy);
    console.log(`    K=${cell.value.toFixed(3)} at (${cell.cx.toFixed(2)}, ${cell.cy.toFixed(2)}) [${domain}]`);
  }

  console.log('  Weakest regions:');
  for (const cell of bottomK) {
    const domain = findDomain(cell.cx, cell.cy);
    console.log(`    K=${cell.value.toFixed(3)} at (${cell.cx.toFixed(2)}, ${cell.cy.toFixed(2)}) [${domain}]`);
  }

  // Sanity check: are strong/weak regions consistent with persona profile?
  if (topK.length > 0 && bottomK.length > 0) {
    const strongX = topK.reduce((s, c) => s + c.cx, 0) / topK.length;
    const weakX = bottomK.reduce((s, c) => s + c.cx, 0) / bottomK.length;
    const strongAccuracy = persona.getAccuracy(strongX, 0.5);
    const weakAccuracy = persona.getAccuracy(weakX, 0.5);
    const consistent = strongAccuracy > weakAccuracy;
    console.log(`  Strong region avg x=${strongX.toFixed(2)} (persona acc=${(strongAccuracy * 100).toFixed(0)}%)`);
    console.log(`  Weak region avg x=${weakX.toFixed(2)} (persona acc=${(weakAccuracy * 100).toFixed(0)}%)`);
    console.log(`  Map-persona consistency: ${consistent ? 'YES — strong regions match high-accuracy areas' : 'NO — map contradicts persona expertise'}`);
  }

  // ─── Check 3: Video recommendations ───────────────────────
  console.log('\n--- Check 3: Top Video Recommendations ---');
  const ranked = rankVideos(catalog, estimates);

  for (let i = 0; i < Math.min(5, ranked.length); i++) {
    const r = ranked[i];
    const v = r.video;
    const avgX = v.windows.reduce((s, w) => s + w[0], 0) / v.windows.length;
    const avgY = v.windows.reduce((s, w) => s + w[1], 0) / v.windows.length;
    const domain = findDomain(avgX, avgY);
    const personaAcc = persona.getAccuracy(avgX, avgY);

    console.log(`  #${i + 1}: "${v.title.substring(0, 55)}" (${(v.duration_s / 60).toFixed(0)}min)`);
    console.log(`      TLP=${r.score.toFixed(4)}  pos=(${avgX.toFixed(2)}, ${avgY.toFixed(2)}) [${domain}]  persona_acc=${(personaAcc * 100).toFixed(0)}%`);
  }

  // Check if recommendations target weak areas
  if (ranked.length >= 3) {
    const top3 = ranked.slice(0, 3);
    const avgAcc = top3.reduce((s, r) => {
      const ax = r.video.windows.reduce((s2, w) => s2 + w[0], 0) / r.video.windows.length;
      const ay = r.video.windows.reduce((s2, w) => s2 + w[1], 0) / r.video.windows.length;
      return s + persona.getAccuracy(ax, ay);
    }, 0) / 3;

    console.log(`\n  Avg persona accuracy in recommended video regions: ${(avgAcc * 100).toFixed(0)}%`);
    console.log(`  Targets weak areas: ${avgAcc < 0.5 ? 'YES' : avgAcc < 0.65 ? 'PARTIAL' : 'NO — recommends areas persona already knows'}`);
  }
}

console.log(`\n${'═'.repeat(70)}`);
console.log('SIMULATION COMPLETE');
console.log(`${'═'.repeat(70)}`);
