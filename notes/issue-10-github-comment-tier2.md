# Implementation Plan: Adaptive Sampling (Tier 2: Response-Aware)

## Overview

I've created a detailed implementation plan for **response-aware adaptive question selection**. Instead of random sampling, we'll use uncertainty-weighted algorithms that combine spatial coverage with intelligent response to user performance.

**Current State**: Random selection of 10 questions from 750 cells (229+ questions)

**Goal**: Adaptive sampling that:
- Maximizes information gain by targeting uncertain regions
- Responds to user performance (correct/incorrect answers)
- Enables early exit after ~3-5 questions when confidence is high
- Provides interactive exploration via cell clicking

---

## Recommended Approach: Uncertainty-Weighted Adaptive Sampling ⭐

**Complexity**: Medium | **Impact**: Very High | **Timeline**: 4-5 weeks

### Core Algorithm

**Phase 1: Initial Exploration (First 2-3 questions)**
- Use geometric sampling to establish baseline coverage
- Ask questions from distant regions

**Phase 2: Adaptive Uncertainty Sampling (Subsequent questions)**
- Maintain real-time uncertainty map based on responses
- Select cell that maximizes: `score = distance^α × uncertainty^β`
- Update uncertainty after each response

### How It Works

1. **K-Nearest Neighbor Prediction**
   - For each unasked cell, find K=5 nearest asked cells
   - Compute weighted average correctness using Gaussian kernel
   - Estimate predicted correctness p(correct|cell)

2. **Binary Entropy Uncertainty**
   - Uncertainty = -[p log p + (1-p) log(1-p)]
   - Highest (1.0) when p=0.5 (maximum ambiguity)
   - Lowest (0.0) when p=0 or 1 (high confidence)

3. **Uncertainty-Weighted Selection**
   - Score each cell: `distance^α × uncertainty^β`
   - Select cell with highest score
   - Parameters: α=1.0 (distance), β=1.0 (uncertainty) - balanced

4. **Dual Confidence Metrics**
   - Coverage confidence: % cells within threshold distance of asked cells
   - Uncertainty confidence: Average confidence across all cells
   - Combined: (coverage + uncertainty) / 2

### Why This Approach?

✅ **Adaptiv**e: Responds to user performance patterns
✅ **Efficient**: Targets knowledge gaps, avoids oversampling confident regions
✅ **Interpretable**: Users can understand "asking about topics you're unsure about"
✅ **Flexible**: Parameters (α, β, K, sigma) tunable based on empirical performance
✅ **Fast**: K-NN lookup + simple scoring, <50ms selection time

---

## Implementation Phases

### Phase 1: Foundation & Infrastructure (Week 1)
- Precompute pairwise distances → `cell_distances.json` (750×750 matrix, ~4MB)
- Create `AdaptiveSampler` class with state management
- Add configuration system for parameters (K, sigma, α, β)
- Build cell index mappings for O(1) lookup

### Phase 2: Uncertainty Estimation Engine (Week 2)
- Implement K-nearest neighbor finder
- Implement uncertainty estimation with Gaussian kernel weighting
- Update uncertainty map after each response
- Test entropy formula and edge cases

### Phase 3: Uncertainty-Weighted Selection (Week 3)
- Implement scoring function combining distance and uncertainty
- Implement adaptive question selection algorithm
- Integrate with existing quiz flow
- Test adaptation to correct/incorrect responses

### Phase 4: Confidence Metrics & Early Exit (Week 4)
- Implement dual confidence calculation (coverage + uncertainty)
- Add dynamic "Show Results" button
  - Enable when: `confidence ≥ 85% AND questions ≥ 3`
  - Show: "Show Results (87% confidence)"
- Add confidence visualizations (progress bar, stats)

### Phase 5: UI Enhancements & Polish (Week 5)
- "Answer More Questions" button (preserves state)
- Click-to-ask cells (answer questions about specific topics)
- Sampling mode selector (Random vs Adaptive for A/B testing)
- Uncertainty overlay visualization
- Parameter tuning UI (debug mode)

---

## Code Example: Complete AdaptiveSampler Class

```javascript
class AdaptiveSampler {
  constructor(questionsPool, distances, config) {
    this.questionsPool = questionsPool;
    this.distances = distances.distances;  // 2D array
    this.cellKeys = distances.cell_keys;
    this.config = {
      initialRandomQuestions: 2,
      minQuestionsBeforeExit: 3,
      confidenceThreshold: 0.85,
      K: 5,              // Nearest neighbors
      sigma: 0.15,       // Gaussian kernel bandwidth
      alpha: 1.0,        // Distance weight
      beta: 1.0,         // Uncertainty weight
      ...config
    };

    // Build index mappings
    this.cellKeyToIndex = {};
    this.cellKeys.forEach((key, idx) => {
      this.cellKeyToIndex[key] = idx;
    });

    // State
    this.askedCells = [];
    this.responses = {};  // cellKey → true/false
    this.uncertaintyMap = {};
  }

  // K-NN Uncertainty Estimation
  estimateUncertainty(cellKey, askedCells, responses) {
    const nearest = this.findKNearestAsked(cellKey, askedCells, this.config.K);

    if (nearest.length === 0) {
      return { uncertainty: 1.0, confidence: 0.0 };
    }

    // Gaussian kernel weighted average
    let totalWeight = 0, weightedCorrectness = 0;
    for (const neighbor of nearest) {
      const weight = Math.exp(-neighbor.distance**2 / (2 * this.config.sigma**2));
      const correct = responses[neighbor.cellKey] ? 1.0 : 0.0;
      weightedCorrectness += weight * correct;
      totalWeight += weight;
    }

    const p = totalWeight > 0 ? weightedCorrectness / totalWeight : 0.5;

    // Binary entropy
    const pClipped = Math.max(1e-10, Math.min(1 - 1e-10, p));
    const uncertainty = -(pClipped * Math.log2(pClipped) +
                         (1 - pClipped) * Math.log2(1 - pClipped));

    return { predictedCorrectness: p, uncertainty, confidence: 1 - uncertainty };
  }

  // Uncertainty-Weighted Selection
  selectNextQuestion() {
    const available = this._getAvailableQuestions();

    // Phase 1: Geometric sampling
    if (this.askedCells.length < this.config.initialRandomQuestions) {
      return this._selectGeometric(available);
    }

    // Phase 2: Uncertainty-weighted sampling
    this.uncertaintyMap = this.updateUncertaintyMap(this.askedCells, this.responses);

    let bestScore = -Infinity, bestQuestion = null;
    const questionsByCell = this._groupByCell(available);

    for (const [cellKey, questions] of Object.entries(questionsByCell)) {
      if (this.askedCells.includes(cellKey)) continue;

      // Score = distance^α × uncertainty^β
      const minDist = this._computeMinDistance(cellKey, this.askedCells);
      const uncertainty = this.uncertaintyMap[cellKey]?.uncertainty || 1.0;
      const score = Math.pow(minDist, this.config.alpha) *
                    Math.pow(uncertainty, this.config.beta);

      if (score > bestScore) {
        bestScore = score;
        bestQuestion = this._selectRandom(questions);
      }
    }

    return bestQuestion;
  }

  // Dual Confidence Calculation
  computeConfidence() {
    // Method 1: Coverage confidence
    let coveredCells = 0;
    for (const cellKey of this.cellKeys) {
      const minDist = this._computeMinDistance(cellKey, this.askedCells);
      if (minDist < 0.15) coveredCells++;
    }
    const coverageConfidence = coveredCells / this.cellKeys.length;

    // Method 2: Uncertainty confidence
    let totalConfidence = 0;
    for (const cellKey of this.cellKeys) {
      totalConfidence += this.uncertaintyMap[cellKey]?.confidence || 0;
    }
    const uncertaintyConfidence = totalConfidence / this.cellKeys.length;

    return {
      overallConfidence: (coverageConfidence + uncertaintyConfidence) / 2,
      coverageConfidence,
      uncertaintyConfidence
    };
  }

  canEarlyExit() {
    const conf = this.computeConfidence();
    return this.askedCells.length >= this.config.minQuestionsBeforeExit &&
           conf.overallConfidence >= this.config.confidenceThreshold;
  }
}
```

---

## Technical Details

### Precomputation Script

```python
# scripts/precompute_cell_distances.py
import json
import numpy as np
from scipy.spatial.distance import cdist

def precompute_cell_distances():
    with open('cell_questions.json') as f:
        data = json.load(f)

    cells = []
    cell_keys = []
    for cell_data in data['cells']:
        cell = cell_data['cell']
        cells.append([cell['center_x'], cell['center_y']])
        cell_keys.append(f"{cell['gx']}_{cell['gy']}")

    coords = np.array(cells)
    distances = cdist(coords, coords, metric='euclidean')

    output = {
        'cell_keys': cell_keys,
        'distances': distances.tolist(),
        'metadata': { 'num_cells': len(cells), 'metric': 'euclidean' }
    }

    with open('cell_distances.json', 'w') as f:
        json.dump(output, f)
```

Run: `python3 scripts/precompute_cell_distances.py`

---

## Success Metrics

### Quantitative
1. **Spatial Coverage**: <0.10 mean distance after 5 questions (vs 0.25 random)
2. **Questions to Confidence**: 3-5 to reach 85% (vs 8-12 random)
3. **Early Exit Rate**: >60% exit after 3-5 questions
4. **Information Gain**: >2× gain per question vs random
5. **Adaptation Quality**: >0.7 correlation (uncertainty → selection)

### Qualitative
- User satisfaction: "Quiz felt efficient"
- Engagement: Time exploring map vs answering
- Completion rate: % complete vs abandon
- Perceived intelligence: "System adapted to my knowledge"

---

## A/B Testing Plan

1. **Groups**: Random (control) vs Adaptive (treatment)
2. **Sample**: 200+ users (100 per group)
3. **Duration**: 2-3 weeks
4. **Metrics**: Questions to 85% confidence, early exit rate, completion rate, satisfaction
5. **Success**: Adaptive reduces questions by >30%, early exit >50%, no decrease in completion

---

## Timeline & Priorities

### Must-Have (MVP - 4 weeks)
- **Week 1**: Foundation & infrastructure
- **Week 2**: Uncertainty estimation engine
- **Week 3**: Uncertainty-weighted selection
- **Week 4**: Confidence metrics & early exit

### Should-Have (5 weeks)
- **Week 5**: UI enhancements (click cells, answer more, visualizations)

### Nice-to-Have (6+ weeks)
- Parameter tuning UI
- Advanced visualizations
- Bayesian/information-theoretic approaches

---

## Dependencies

### Ready Now ✅
- [x] Cell questions generation (750/1,600 cells) - sufficient to start
- [x] Heatmap visualization
- [x] Multi-round quiz infrastructure
- [x] Response tracking

### No Blockers
Can start immediately with 750 cells. Additional cells integrate seamlessly as generated.

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Performance: Uncertainty updates too slow | Precompute distances, optimize K-NN |
| Complexity: Too many parameters | Start with defaults (α=β=1), tune only if needed |
| Edge cases: No questions in high-uncertainty cells | Fall back to nearest cells with questions |
| UX: Adaptive feels unpredictable | Show uncertainty visualization, explain |

---

## Next Steps

1. **Review & approve** this Tier 2 plan
2. **Precompute distances**: Run script → `cell_distances.json`
3. **Implement Phase 1**: Infrastructure & configuration
4. **Set up A/B testing**: Comparison framework
5. **Iterative development**: Build, test, refine (weeks 2-5)

**Full detailed plan** (1,280+ lines with complete algorithms, testing strategy, code examples): See `notes/issue-10-adaptive-sampling-plan.md`

---

## Questions for Discussion

1. Do these success metrics seem appropriate? Should we adjust thresholds?
2. Should parameter tuning UI be included in MVP or later phase?
3. Any specific uncertainty visualizations you'd like to see?
4. Preference for default parameters (α=β=1 balanced, or other)?

Looking forward to feedback! Happy to refine the plan based on priorities and preferences.
