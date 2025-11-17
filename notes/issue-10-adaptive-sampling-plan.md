# Issue #10: Adaptive Sampling Implementation Plan

## Executive Summary

This plan outlines a comprehensive approach to implementing adaptive question selection for the knowledge map quiz system. Instead of random question selection, we will use intelligent algorithms to maximize information gain about the user's knowledge map while minimizing the number of questions needed.

**Current State**: Random selection of 10 questions from a pool of 750 cells (229+ questions available, growing to ~3,000 when generation completes).

**Goal**: Implement adaptive sampling that:
- Maximizes spatial coverage of the knowledge map
- Responds intelligently to user performance
- Enables early exit after ~3-5 questions when confidence is high
- Provides interactive exploration via cell clicking

---

## 1. Current State Analysis

### What We Have
- **Question Pool**: 750 cells with questions in `cell_questions_checkpoint.json` (target: 1,600 cells total, 4 questions each = ~6,400 questions)
- **Question Structure**: Each question has:
  - Grid coordinates (gx, gy) and normalized coordinates (cell_x, cell_y)
  - Semantic cell label (topic)
  - Source Wikipedia article
  - Multiple choice format (A/B/C/D)
- **Current Selection**: Pure random sampling (10 questions per round)
- **Multi-round Support**: Users can answer additional rounds of 10 questions
- **Note**: index.html currently loads `cell_questions_sample.json` - should be updated to `cell_questions.json` when full generation completes

### Limitations of Current Approach
1. **Poor Coverage**: Random sampling often clusters questions in one region
2. **Inefficient**: May ask 10+ questions when 3-5 well-chosen questions could provide same information
3. **No Early Exit**: Users must complete all 10 questions even if map is already well-defined
4. **No Response Adaptation**: Doesn't adjust based on correct/incorrect answers
5. **No Targeted Exploration**: Users can't explore specific regions of interest

---

## 2. Adaptive Sampling Approaches (Three Tiers)

### Tier 1: Geometric Distance-Based Sampling (RECOMMENDED FIRST)
**Complexity**: Low | **Impact**: High | **Implementation Time**: 2-3 days

Select questions that maximize spatial coverage of the map.

**Algorithm**: Greedy max-distance selection
```
1. Start with 1-2 random questions (avoid determinism)
2. For each subsequent question:
   - Compute distance from each unasked cell to its nearest asked cell
   - Select the cell with maximum distance (furthest from any asked question)
   - Ask a question from that cell
```

**Advantages**:
- Simple to implement and understand
- Guaranteed spatial coverage
- No complex probability calculations
- Works independently of responses

**Disadvantages**:
- Ignores user performance (doesn't adapt to correct/incorrect answers)
- May oversample high-confidence regions
- Doesn't directly optimize for information gain

### Tier 2: Response-Aware Adaptive Sampling
**Complexity**: Medium | **Impact**: Very High | **Implementation Time**: 4-6 days

Incorporate user responses to focus sampling on uncertain regions.

**Algorithm**: Uncertainty-weighted distance sampling
```
1. Start with geometric sampling for first 2-3 questions
2. Maintain uncertainty map for each cell:
   - High uncertainty = no nearby questions OR conflicting predictions
   - Low uncertainty = nearby questions with consistent predictions
3. For each subsequent question:
   - Compute uncertainty-weighted distance: d_weighted = d_geometric × uncertainty
   - Select cell with maximum weighted distance
4. Update uncertainty map after each response
```

**Advantages**:
- Adapts to user performance
- Focuses on uncertain regions
- More efficient than pure geometric sampling
- Still maintains good spatial coverage

**Disadvantages**:
- More complex implementation
- Requires uncertainty estimation
- Need to tune weighting parameters

### Tier 3: Bayesian/Information-Theoretic Sampling (FUTURE WORK)
**Complexity**: High | **Impact**: Highest | **Implementation Time**: 2-3 weeks

Use principled probabilistic framework to optimize information gain.

**Approaches**:
- **Bayesian Active Learning**: Maintain posterior distribution over user's knowledge map, select questions that minimize expected posterior variance
- **Information Gain**: Select questions that maximize mutual information between question response and knowledge map
- **Thompson Sampling**: Balance exploration vs exploitation using Bayesian posterior sampling

**Implementation Notes**:
- Requires probabilistic model of knowledge map (e.g., Gaussian Process)
- Computationally intensive (may need precomputation)
- Best as future enhancement after Tiers 1-2 are working

---

## 3. Implementation Plan

### Phase 1: Foundation & Infrastructure (Week 1)
**Goal**: Set up data structures and utilities for adaptive sampling

#### Tasks:
1. **Precompute Pairwise Distances**
   - Create distance matrix between all cell centers
   - Store as `cell_distances.json` (750×750 matrix, ~2MB)
   - Use Euclidean distance in normalized coordinate space

2. **Refactor Question Selection Code**
   - Extract question selection into separate function
   - Create `AdaptiveSampler` class to manage state
   - Maintain history of asked questions and responses

3. **Add Configuration System**
   - Create config object for sampling parameters:
     ```javascript
     const samplingConfig = {
       mode: 'adaptive-distance',  // 'random', 'adaptive-distance', 'adaptive-uncertainty'
       initialRandomQuestions: 2,
       minQuestionsBeforeExit: 3,
       confidenceThreshold: 0.85,
       maxQuestions: 10
     }
     ```

**Deliverables**:
- `cell_distances.json` precomputed distance matrix
- `AdaptiveSampler` class in index.html
- Configuration system in place

### Phase 2: Geometric Adaptive Sampling (Week 2)
**Goal**: Implement and test Tier 1 distance-based sampling

#### Tasks:
1. **Implement Max-Distance Selection**
   ```javascript
   class AdaptiveSampler {
     selectNextQuestion(askedCells, availableQuestions) {
       if (askedCells.length < this.config.initialRandomQuestions) {
         return this.selectRandomQuestion(availableQuestions);
       }
       return this.selectFurthestCell(askedCells, availableQuestions);
     }

     selectFurthestCell(askedCells, availableQuestions) {
       let maxMinDistance = -1;
       let bestQuestion = null;

       // Group questions by cell
       const questionsByCell = this.groupQuestionsByCell(availableQuestions);

       for (const [cellKey, questions] of Object.entries(questionsByCell)) {
         // Skip if cell already asked
         if (askedCells.includes(cellKey)) continue;

         // Compute minimum distance to any asked cell
         const minDistance = this.computeMinDistance(cellKey, askedCells);

         // Update best if this cell is furthest
         if (minDistance > maxMinDistance) {
           maxMinDistance = minDistance;
           bestQuestion = this.selectRandomFromCell(questions);
         }
       }

       return bestQuestion;
     }

     computeMinDistance(cellKey, askedCells) {
       const cellIdx = this.cellKeyToIndex[cellKey];
       let minDist = Infinity;

       for (const askedCell of askedCells) {
         const askedIdx = this.cellKeyToIndex[askedCell];
         const dist = this.distances[cellIdx][askedIdx];
         minDist = Math.min(minDist, dist);
       }

       return minDist;
     }
   }
   ```

2. **Update Quiz Flow**
   - Replace random selection with adaptive sampling
   - Maintain cell history across rounds
   - Log selection decisions for debugging

3. **Testing**
   - Verify spatial coverage improves vs random
   - Check for edge cases (duplicate cells, exhausted cells)
   - Performance testing (selection should be <50ms)

**Deliverables**:
- Working geometric adaptive sampling
- Improved spatial coverage metrics
- Unit tests for selection algorithm

### Phase 3: Confidence Metrics & Early Exit (Week 3)
**Goal**: Enable users to stop early when map is well-defined

#### Tasks:
1. **Implement Confidence Estimation**
   ```javascript
   function computeMapConfidence(askedCells, allCells, distances) {
     // For each cell, find distance to nearest asked cell
     const cellDistances = allCells.map(cell => {
       const minDist = Math.min(...askedCells.map(asked =>
         distances[cell.index][asked.index]
       ));
       return minDist;
     });

     // Confidence = % of cells within threshold distance
     const threshold = 0.15; // Normalized distance threshold
     const nearCells = cellDistances.filter(d => d < threshold).length;
     const confidence = nearCells / allCells.length;

     return {
       confidence: confidence,
       maxDistance: Math.max(...cellDistances),
       meanDistance: cellDistances.reduce((a,b) => a+b, 0) / cellDistances.length
     };
   }
   ```

2. **Add Dynamic "Show Results" Button**
   - Show button after minimum questions (default: 3)
   - Display confidence % on button: "Show Results (85% coverage)"
   - Disable until confidence threshold met OR max questions reached

3. **Add Confidence Visualizations**
   - Progress bar showing confidence over time
   - Text display: "Map Coverage: 85% - Ready to view!"
   - Optional: Mini heatmap showing asked vs unasked regions

**Deliverables**:
- Confidence calculation function
- Dynamic early exit button
- Confidence visualization UI

### Phase 4: UI Enhancements (Week 4)
**Goal**: Add interactive exploration features

#### Tasks:
1. **"Answer More Questions" Button**
   - Add button to map view
   - Preserve existing response history
   - Continue adaptive sampling from current state
   - Update map dynamically with new responses

2. **Click-to-Ask Cell Feature**
   - Make heatmap cells clickable
   - On click:
     - Select random question from that cell
     - Show question in modal/overlay
     - Update map with response
     - Recompute heatmap
   - Visual feedback: highlight selected cell

3. **Sampling Mode Selector**
   - Add dropdown/toggle: "Random" vs "Adaptive"
   - Enable A/B testing and user preference
   - Log mode choice for analytics

4. **Enhanced Feedback**
   - Show which regions need more questions
   - Display "Explore this region?" suggestions
   - Show question distribution histogram

**Deliverables**:
- Interactive map with clickable cells
- "Answer More" button with preserved state
- Mode selector UI
- Enhanced user feedback

### Phase 5: Response-Aware Sampling (Optional - Week 5+)
**Goal**: Implement Tier 2 uncertainty-weighted sampling

#### Tasks:
1. **Implement Uncertainty Estimation**
   ```javascript
   function estimateUncertainty(cellCoord, askedQuestions, responses) {
     // Find K nearest asked questions
     const K = 5;
     const nearest = findKNearest(cellCoord, askedQuestions, K);

     // Compute weighted average correctness
     let totalWeight = 0;
     let weightedCorrectness = 0;

     for (const neighbor of nearest) {
       const dist = distance(cellCoord, neighbor.coord);
       const weight = Math.exp(-dist * dist / (2 * 0.1 * 0.1)); // Gaussian kernel
       const correctness = responses[neighbor.index].correct ? 1.0 : 0.0;

       weightedCorrectness += weight * correctness;
       totalWeight += weight;
     }

     const predictedCorrectness = totalWeight > 0
       ? weightedCorrectness / totalWeight
       : 0.5;

     // Uncertainty is highest at 0.5 (maximum entropy)
     const uncertainty = 1 - 2 * Math.abs(predictedCorrectness - 0.5);

     return {
       predictedCorrectness,
       uncertainty,
       confidence: 1 - uncertainty
     };
   }
   ```

2. **Uncertainty-Weighted Selection**
   - Combine geometric distance with uncertainty
   - Weight: `score = distance^α × uncertainty^β`
   - Tune α and β parameters (start with α=1, β=1)

3. **Testing & Tuning**
   - Compare with pure geometric sampling
   - Measure: questions needed to reach confidence threshold
   - A/B test with real users

**Deliverables**:
- Uncertainty-weighted sampling
- Performance comparison metrics
- Parameter tuning results

---

## 4. Technical Implementation Details

### Data Structures

```javascript
// Question pool structure
const questionsPool = {
  cells: [
    {
      cell: { gx: 8, gy: 21, center_x: 0.218, center_y: 0.551, label: "..." },
      questions: [ { question: "...", options: {...}, correct_answer: "C", ... } ]
    }
  ],
  metadata: { num_cells: 750, total_questions: 229 }
};

// Sampling state
const samplingState = {
  askedCells: ["8_21", "19_10", ...],
  askedQuestions: [
    { cellKey: "8_21", question: {...}, response: {...}, correct: true }
  ],
  cellIndex: { "8_21": 0, "19_10": 1, ... },
  distances: [[0, 0.45, ...], [0.45, 0, ...], ...],
  confidence: 0.85,
  mode: 'adaptive-distance'
};
```

### Precomputation Script

Create `scripts/precompute_cell_distances.py`:
```python
import json
import numpy as np
from scipy.spatial.distance import cdist

def precompute_cell_distances():
    # Load cell questions
    with open('cell_questions_checkpoint.json') as f:
        data = json.load(f)

    # Extract cell coordinates
    cells = []
    cell_keys = []
    for cell_data in data['cells']:
        cell = cell_data['cell']
        cells.append([cell['center_x'], cell['center_y']])
        cell_keys.append(f"{cell['gx']}_{cell['gy']}")

    coords = np.array(cells)

    # Compute pairwise distances (Euclidean in normalized space)
    distances = cdist(coords, coords, metric='euclidean')

    # Save as JSON
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

    print(f"✓ Computed {len(cells)}×{len(cells)} distance matrix")
    print(f"✓ Saved to cell_distances.json")

if __name__ == '__main__':
    precompute_cell_distances()
```

### Performance Considerations

1. **Distance Computation**: Precompute all pairwise distances (~2MB file, O(1) lookup)
2. **Selection Speed**: Current approach is O(N×M) where N=cells, M=asked cells. Should be <50ms for 750 cells.
3. **Memory**: Sampling state is small (~10KB), no issues
4. **Caching**: Cache confidence calculations to avoid recomputation

---

## 5. Success Metrics

### Quantitative Metrics
1. **Spatial Coverage**: Mean distance from each cell to nearest asked cell
   - Target: <0.15 normalized distance units after 5 questions
   - Baseline (random): ~0.25 after 10 questions

2. **Questions to Confidence**: Number of questions to reach 85% confidence
   - Target: 3-5 questions with adaptive sampling
   - Baseline (random): 8-12 questions

3. **Early Exit Rate**: % of users who stop before 10 questions
   - Target: >50% of users exit after 3-5 questions

4. **Information Gain per Question**: Change in map confidence per question
   - Target: Adaptive >2× gain per question vs random

### Qualitative Metrics
1. **User Satisfaction**: Survey rating for "quiz felt efficient"
2. **Engagement**: Time spent exploring map vs answering questions
3. **Completion Rate**: % users who complete vs abandon

---

## 6. Testing Strategy

### Unit Tests
1. Distance computation correctness
2. Max-distance selection algorithm
3. Confidence calculation edge cases
4. State management across rounds

### Integration Tests
1. End-to-end quiz flow with adaptive sampling
2. Multi-round persistence
3. Click-to-ask functionality
4. Early exit behavior

### A/B Testing
1. **Groups**: Random (control) vs Adaptive (treatment)
2. **Metrics**: Questions to 85% confidence, completion rate, user satisfaction
3. **Sample Size**: 100+ users per group
4. **Duration**: 2 weeks

### User Testing
1. **Participants**: 5-10 users
2. **Tasks**:
   - Complete quiz with adaptive sampling
   - Use early exit when available
   - Click cells to explore specific topics
3. **Observations**: Confusion points, UI feedback, perceived efficiency

---

## 7. Implementation Priority & Timeline

### Must-Have (MVP - 3 weeks)
- [x] Phase 1: Foundation & Infrastructure (Week 1)
- [x] Phase 2: Geometric Adaptive Sampling (Week 2)
- [x] Phase 3: Confidence Metrics & Early Exit (Week 3)

### Should-Have (Enhanced - 4-5 weeks)
- [ ] Phase 4: UI Enhancements (Week 4)
  - Click-to-ask cells
  - Answer more questions button
  - Mode selector

### Nice-to-Have (Advanced - 6+ weeks)
- [ ] Phase 5: Response-Aware Sampling
- [ ] Bayesian/Information-Theoretic Sampling
- [ ] Advanced visualizations (uncertainty heatmap, question history)

---

## 8. Future Enhancements

### Short-term (3-6 months)
1. **Multi-Topic Quizzes**: Separate sampling for different domains
2. **Difficulty Adaptation**: Adjust question difficulty based on performance
3. **Time-Based Adaptation**: Faster questions in confident regions
4. **Comparison Mode**: Show knowledge map vs expert/average user

### Long-term (6-12 months)
1. **Bayesian Active Learning**: Full probabilistic framework
2. **Reinforcement Learning**: Learn optimal sampling policy from user data
3. **Multi-User Optimization**: Share information across users for cold-start
4. **Personalized Sampling**: Adapt to individual user preferences

---

## 9. Risk Mitigation

### Technical Risks
1. **Performance**: Distance computation too slow
   - Mitigation: Precompute distances, use spatial indexing if needed

2. **Edge Cases**: Run out of questions in target cells
   - Mitigation: Fall back to nearest cells with questions available

3. **Confidence Estimation**: Inaccurate confidence scores
   - Mitigation: Conservative thresholds, A/B test different metrics

### UX Risks
1. **User Confusion**: Adaptive sampling feels "random" or unfair
   - Mitigation: Explain approach, show coverage visualization

2. **Early Exit Too Soon**: Users miss important questions
   - Mitigation: Set minimum questions (3), show coverage gaps

3. **Click Fatigue**: Too many questions if clicking cells
   - Mitigation: Limit clicks per session, show "suggested questions"

---

## 10. Dependencies & Prerequisites

### Required Before Starting
- [x] Cell questions generation (issue #11) - 750/1,600 cells complete
- [x] Heatmap visualization working
- [x] Multi-round quiz infrastructure

### Can Implement in Parallel
- [ ] Additional cell questions (750→1,600 cells)
- [ ] Performance optimizations
- [ ] Advanced visualizations

### Blockers
None - can start implementation immediately with existing 750 cells

---

## Appendix: Code Examples

### A. Precompute Distances (Python)
See Section 4: Technical Implementation Details

### B. Adaptive Sampler Class (JavaScript)
```javascript
class AdaptiveSampler {
  constructor(questionsPool, distances, config) {
    this.questionsPool = questionsPool;
    this.distances = distances;
    this.config = config;
    this.askedCells = [];
    this.askedQuestions = [];
    this.cellKeyToIndex = this._buildCellIndex();
  }

  selectNextQuestion() {
    const availableQuestions = this._getAvailableQuestions();

    if (availableQuestions.length === 0) {
      return null; // No more questions
    }

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

      const minDist = this._computeMinDistance(cellKey);

      if (minDist > maxMinDist) {
        maxMinDist = minDist;
        bestQuestion = this._selectRandom(questions);
      }
    }

    return bestQuestion;
  }

  _computeMinDistance(cellKey) {
    const cellIdx = this.cellKeyToIndex[cellKey];
    let minDist = Infinity;

    for (const askedCell of this.askedCells) {
      const askedIdx = this.cellKeyToIndex[askedCell];
      const dist = this.distances[cellIdx][askedIdx];
      minDist = Math.min(minDist, dist);
    }

    return minDist;
  }

  recordResponse(question, response) {
    const cellKey = `${question.cell_gx}_${question.cell_gy}`;

    this.askedCells.push(cellKey);
    this.askedQuestions.push({
      question,
      response,
      cellKey,
      timestamp: Date.now()
    });
  }

  computeConfidence() {
    const allCells = Object.keys(this.cellKeyToIndex);
    let totalCells = allCells.length;
    let coveredCells = 0;
    const threshold = this.config.coverageThreshold || 0.15;

    for (const cellKey of allCells) {
      const minDist = this._computeMinDistance(cellKey);
      if (minDist < threshold) {
        coveredCells++;
      }
    }

    return coveredCells / totalCells;
  }

  // Helper methods
  _buildCellIndex() { /* ... */ }
  _getAvailableQuestions() { /* ... */ }
  _groupByCell(questions) { /* ... */ }
  _selectRandom(items) { /* ... */ }
}
```

### C. Confidence UI Component (HTML/JS)
```html
<div class="confidence-panel">
  <div class="confidence-label">Map Coverage</div>
  <div class="confidence-bar">
    <div class="confidence-fill" id="confidence-fill"></div>
  </div>
  <div class="confidence-text" id="confidence-text">45% - Keep going!</div>
</div>

<button id="show-results-btn" class="btn btn-primary" disabled>
  Show Results (need 3 more questions)
</button>

<style>
.confidence-panel {
  background: #f0f8f0;
  border: 2px solid #00693E;
  border-radius: 8px;
  padding: 15px;
  margin: 15px 0;
}

.confidence-bar {
  background: #ddd;
  border-radius: 10px;
  height: 20px;
  overflow: hidden;
  margin: 10px 0;
}

.confidence-fill {
  background: linear-gradient(90deg, #00693E, #00a859);
  height: 100%;
  transition: width 0.5s ease;
}
</style>

<script>
function updateConfidenceUI(confidence, minQuestions) {
  const fillEl = document.getElementById('confidence-fill');
  const textEl = document.getElementById('confidence-text');
  const btnEl = document.getElementById('show-results-btn');

  const percent = Math.round(confidence * 100);
  fillEl.style.width = `${percent}%`;

  const threshold = 85;
  const questionsNeeded = Math.max(0, minQuestions - currentQuestion);

  if (confidence >= threshold / 100 && questionsNeeded === 0) {
    textEl.textContent = `${percent}% - Ready to view!`;
    btnEl.disabled = false;
    btnEl.textContent = `Show Results (${percent}% coverage)`;
  } else if (questionsNeeded > 0) {
    textEl.textContent = `${percent}% - Need ${questionsNeeded} more question${questionsNeeded > 1 ? 's' : ''}`;
    btnEl.disabled = true;
    btnEl.textContent = `Show Results (need ${questionsNeeded} more)`;
  } else {
    textEl.textContent = `${percent}% - Keep going!`;
    btnEl.disabled = true;
    btnEl.textContent = `Show Results (need ${threshold - percent}% more coverage)`;
  }
}
</script>
```

---

## Summary

This plan provides a complete roadmap for implementing adaptive sampling in the knowledge map quiz system. The phased approach allows for incremental delivery of value:

1. **Week 1-2**: Core adaptive sampling (geometric distance-based)
2. **Week 3**: Early exit with confidence metrics
3. **Week 4**: Interactive UI enhancements
4. **Week 5+**: Advanced algorithms (optional)

The geometric distance-based approach (Tier 1) provides the best effort-to-impact ratio and should be implemented first. More sophisticated approaches (Tiers 2-3) can be added later based on user feedback and performance metrics.

**Recommended Next Steps**:
1. Review and approve this plan
2. Run precomputation script to generate `cell_distances.json`
3. Begin Phase 1 implementation
4. Set up A/B testing infrastructure for evaluation
