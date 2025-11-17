# Implementation Plan: Adaptive Sampling for Knowledge Map Quiz

## Overview

I've created a detailed implementation plan for adaptive question selection. Instead of random sampling, we'll use intelligent algorithms to maximize information gain about users' knowledge maps while minimizing questions needed.

**Current State**: Random selection of 10 questions from 750 cells (229+ questions, growing toward ~3,000)

**Goal**: Adaptive sampling that:
- Maximizes spatial coverage of the knowledge map
- Responds intelligently to user performance
- Enables early exit after ~3-5 questions when confidence is high
- Provides interactive exploration via cell clicking

---

## Proposed Approach: Three Tiers

### Tier 1: Geometric Distance-Based (RECOMMENDED FIRST) ⭐
**Complexity**: Low | **Impact**: High | **Timeline**: 2-3 weeks

Select questions that maximize spatial coverage using greedy max-distance algorithm:
1. Start with 1-2 random questions (avoid determinism)
2. For each subsequent question, select the cell furthest from any previously asked cell
3. Continue until confidence threshold met or max questions reached

**Advantages**: Simple, guaranteed coverage, fast, response-independent

### Tier 2: Response-Aware Adaptive Sampling
**Complexity**: Medium | **Impact**: Very High | **Timeline**: 4-6 weeks

Incorporate user responses to focus sampling on uncertain regions:
- Maintain uncertainty map for each cell (high uncertainty = no nearby questions OR conflicting predictions)
- Weight geometric distance by uncertainty: `d_weighted = d_geometric × uncertainty`
- Select cell with maximum weighted distance
- Update uncertainty after each response

**Advantages**: Adapts to performance, focuses on uncertain regions, more efficient

### Tier 3: Bayesian/Information-Theoretic (FUTURE WORK)
**Complexity**: High | **Timeline**: 2-3 months

Use principled probabilistic framework (Bayesian active learning, information gain optimization). Best as future enhancement after Tiers 1-2 working.

---

## Implementation Phases

### Phase 1: Foundation & Infrastructure (Week 1)
- Precompute pairwise distances between all cell centers → `cell_distances.json` (750×750 matrix)
- Refactor question selection into `AdaptiveSampler` class
- Add configuration system for sampling parameters

### Phase 2: Geometric Adaptive Sampling (Week 2)
- Implement max-distance selection algorithm
- Update quiz flow to use adaptive sampling
- Maintain cell history across rounds
- Testing: verify spatial coverage improves vs random

### Phase 3: Confidence Metrics & Early Exit (Week 3)
- Implement confidence estimation (% of cells within threshold distance of asked cells)
- Add dynamic "Show Results" button (appears after min questions + confidence threshold)
- Visualize confidence: progress bar, coverage percentage
- Target: Enable exit after 3-5 questions instead of requiring 10

### Phase 4: UI Enhancements (Week 4)
- **"Answer More Questions" button**: Continue from map view, preserve history
- **Click-to-ask cells**: Click any heatmap cell to answer question about that topic
- **Sampling mode selector**: Toggle between "Random" and "Adaptive" for A/B testing
- **Enhanced feedback**: Show which regions need more questions

### Phase 5: Response-Aware Sampling (Week 5+, Optional)
- Implement uncertainty estimation using K-nearest neighbors
- Uncertainty-weighted question selection
- Parameter tuning and performance comparison

---

## Technical Details

### Precomputation Script

Create `scripts/precompute_cell_distances.py`:
```python
import json
import numpy as np
from scipy.spatial.distance import cdist

def precompute_cell_distances():
    with open('cell_questions.json') as f:
        data = json.load(f)

    # Extract cell coordinates
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
        'metadata': {
            'num_cells': len(cells),
            'metric': 'euclidean',
            'coordinate_space': 'normalized [0,1]'
        }
    }

    with open('cell_distances.json', 'w') as f:
        json.dump(output, f)
```

### Core Algorithm (JavaScript)

```javascript
class AdaptiveSampler {
  selectNextQuestion() {
    const availableQuestions = this._getAvailableQuestions();

    // First N questions are random
    if (this.askedCells.length < this.config.initialRandomQuestions) {
      return this._selectRandom(availableQuestions);
    }

    // Subsequent questions use max-distance
    return this._selectMaxDistance(availableQuestions);
  }

  _selectMaxDistance(availableQuestions) {
    const questionsByCell = this._groupByCell(availableQuestions);
    let maxMinDist = -Infinity;
    let bestQuestion = null;

    for (const [cellKey, questions] of Object.entries(questionsByCell)) {
      if (this.askedCells.includes(cellKey)) continue;

      // Find minimum distance to any asked cell
      const minDist = this._computeMinDistance(cellKey);

      if (minDist > maxMinDist) {
        maxMinDist = minDist;
        bestQuestion = this._selectRandom(questions);
      }
    }

    return bestQuestion;
  }

  computeConfidence() {
    const allCells = Object.keys(this.cellKeyToIndex);
    let coveredCells = 0;
    const threshold = 0.15; // normalized distance

    for (const cellKey of allCells) {
      const minDist = this._computeMinDistance(cellKey);
      if (minDist < threshold) coveredCells++;
    }

    return coveredCells / allCells.length;
  }
}
```

---

## Success Metrics

### Quantitative
1. **Spatial Coverage**: Mean distance from each cell to nearest asked cell
   - Target: <0.15 (normalized) after 5 questions
   - Baseline: ~0.25 after 10 random questions

2. **Questions to Confidence**: Questions needed to reach 85% confidence
   - Target: 3-5 with adaptive
   - Baseline: 8-12 with random

3. **Early Exit Rate**: % users who stop before 10 questions
   - Target: >50% exit after 3-5 questions

### Qualitative
- User satisfaction: "Quiz felt efficient"
- Engagement: Time exploring map vs answering questions
- Completion rate: % complete vs abandon

---

## A/B Testing Plan

1. **Groups**: Random (control) vs Adaptive (treatment)
2. **Metrics**: Questions to 85% confidence, completion rate, satisfaction
3. **Sample**: 100+ users per group
4. **Duration**: 2 weeks

---

## Timeline & Priorities

### Must-Have (MVP - 3 weeks)
- ✅ Phase 1: Foundation & Infrastructure
- ✅ Phase 2: Geometric Adaptive Sampling
- ✅ Phase 3: Confidence Metrics & Early Exit

### Should-Have (4 weeks)
- Phase 4: UI Enhancements (click-to-ask, answer more, mode selector)

### Nice-to-Have (5+ weeks)
- Phase 5: Response-Aware Sampling
- Bayesian/Information-Theoretic approaches
- Advanced visualizations

---

## Dependencies

### Ready Now ✅
- [x] Cell questions generation (750/1,600 cells) - sufficient to start
- [x] Heatmap visualization working
- [x] Multi-round quiz infrastructure

### No Blockers
Can start implementation immediately with existing 750 cells. Additional cells (750→1,600) can be integrated as they're generated.

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Performance: Distance computation too slow | Precompute distances (~2MB file, O(1) lookup) |
| Edge case: Run out of questions in target cells | Fall back to nearest cells with available questions |
| UX: Adaptive feels "random" to users | Show coverage visualization, explain approach |
| Early exit too soon | Set minimum questions (3), show coverage gaps |

---

## Next Steps

1. **Review & approve** this plan
2. **Precompute distances**: Run `precompute_cell_distances.py` to generate `cell_distances.json`
3. **Implement Phase 1**: Set up infrastructure and data structures
4. **Set up A/B testing**: Prepare comparison with random baseline

**Full detailed plan** (with code examples, additional algorithms, testing strategy): See `notes/issue-10-adaptive-sampling-plan.md`

---

## Questions for Discussion

1. Should we implement Tier 1 first and evaluate, or jump to Tier 2 response-aware sampling?
2. What should the initial confidence threshold be for early exit? (Proposed: 85%)
3. Should adaptive sampling be default, or let users choose between random/adaptive?
4. Any specific visualizations you'd like for showing coverage/confidence?

Looking forward to feedback! Happy to adjust the plan based on priorities and preferences.
