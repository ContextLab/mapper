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

## 2. Recommended Approach: Response-Aware Adaptive Sampling ⭐

### Overview
**Complexity**: Medium | **Impact**: Very High | **Implementation Time**: 3-4 weeks

We will implement **uncertainty-weighted adaptive sampling** that combines spatial coverage with intelligent response to user performance. This approach selects questions that maximize expected information gain by prioritizing regions of the knowledge map where our confidence is lowest.

### Core Algorithm

The algorithm operates in two phases:

**Phase 1: Initial Exploration (First 2-3 questions)**
- Use pure geometric sampling to establish baseline coverage
- Ask questions from distant regions to sample broad knowledge landscape
- Build initial uncertainty map

**Phase 2: Adaptive Uncertainty Sampling (Subsequent questions)**
- Maintain real-time uncertainty map based on responses
- Compute uncertainty-weighted score for each unasked cell
- Select cell that maximizes: `score = distance^α × uncertainty^β`
- Update uncertainty map after each response

### Detailed Algorithm

```
Algorithm: Uncertainty-Weighted Adaptive Sampling

Input:
  - Cell coordinates: {(gx_i, gy_i, x_i, y_i) for i = 1..N}
  - Questions by cell: Q[cell_key] = [q1, q2, ...]
  - Distance matrix: D[i,j] = distance between cell i and j
  - Parameters: α (distance weight), β (uncertainty weight), K (neighbors)

State:
  - asked_cells: Set of asked cell keys
  - responses: [(cell_key, correct/incorrect), ...]
  - uncertainty_map: {cell_key: uncertainty_score}

Initialize:
  - asked_cells = {}
  - responses = []
  - uncertainty_map = {cell: 1.0 for all cells}  # Maximum uncertainty initially

For question n = 1 to max_questions:

  If n <= initial_random_questions:
    # Phase 1: Random/geometric sampling
    cell = select_furthest_cell(asked_cells)
  Else:
    # Phase 2: Uncertainty-weighted sampling
    cell = select_uncertainty_weighted_cell(asked_cells, uncertainty_map)

  question = random_choice(Q[cell])
  response = ask_user(question)

  asked_cells.add(cell)
  responses.append((cell, response.correct))

  update_uncertainty_map(uncertainty_map, responses)

  confidence = compute_confidence(asked_cells, uncertainty_map)

  If confidence >= threshold AND n >= min_questions:
    offer_early_exit()
```

### Uncertainty Estimation

The key innovation is computing uncertainty for each cell based on nearby responses.

**Method: K-Nearest Neighbor Prediction with Entropy**

For each unasked cell c:
1. Find K nearest asked cells (using precomputed distances)
2. Compute weighted average correctness using Gaussian kernel
3. Estimate predicted correctness p(correct|c)
4. Uncertainty = entropy(p) = -[p log p + (1-p) log(1-p)]

```python
def estimate_uncertainty(cell_coord, asked_cells, responses, distances, K=5):
    """
    Estimate uncertainty for a cell using K-nearest neighbors.

    Returns:
      - predicted_correctness: float in [0, 1]
      - uncertainty: float in [0, 1], higher = more uncertain
      - confidence: float in [0, 1], inverse of uncertainty
    """
    # Find K nearest asked cells
    cell_idx = coord_to_index[cell_coord]
    asked_indices = [coord_to_index[c] for c in asked_cells]

    # Get distances to all asked cells
    dists = [(distances[cell_idx][idx], idx) for idx in asked_indices]
    dists.sort()  # Sort by distance
    nearest_K = dists[:K]

    # Gaussian kernel: weight = exp(-distance^2 / (2 * sigma^2))
    sigma = 0.15  # Bandwidth parameter (normalized coordinates)

    total_weight = 0
    weighted_correctness = 0

    for dist, idx in nearest_K:
        asked_cell = index_to_coord[idx]
        weight = np.exp(-dist**2 / (2 * sigma**2))
        correctness = 1.0 if responses[asked_cell] else 0.0

        weighted_correctness += weight * correctness
        total_weight += weight

    # Predicted correctness (between 0 and 1)
    if total_weight > 0:
        p = weighted_correctness / total_weight
    else:
        p = 0.5  # No information, assume 50%

    # Uncertainty = binary entropy
    # Highest (1.0) when p = 0.5, lowest (0.0) when p = 0 or 1
    epsilon = 1e-10  # Avoid log(0)
    p = np.clip(p, epsilon, 1 - epsilon)
    uncertainty = -p * np.log2(p) - (1-p) * np.log2(1-p)  # Range: [0, 1]

    return {
        'predicted_correctness': p,
        'uncertainty': uncertainty,
        'confidence': 1 - uncertainty,
        'num_neighbors': len(nearest_K),
        'mean_distance': np.mean([d for d, _ in nearest_K])
    }
```

### Selection Scoring

Once we have uncertainty estimates, we score each cell:

```python
def score_cell(cell, asked_cells, uncertainty_map, distances, alpha=1.0, beta=1.0):
    """
    Score a cell for selection.

    Higher score = better candidate.

    Parameters:
      - alpha: Weight for geometric distance (default 1.0)
      - beta: Weight for uncertainty (default 1.0)
    """
    cell_idx = coord_to_index[cell]

    # Geometric distance component: distance to nearest asked cell
    if len(asked_cells) > 0:
        min_distance = min(
            distances[cell_idx][coord_to_index[asked]]
            for asked in asked_cells
        )
    else:
        min_distance = 1.0  # Maximum distance if no questions asked

    # Uncertainty component
    uncertainty = uncertainty_map[cell]

    # Combined score
    score = (min_distance ** alpha) * (uncertainty ** beta)

    return score
```

**Parameter Tuning:**
- `alpha = 1.0, beta = 1.0`: Balanced (recommended start)
- `alpha = 2.0, beta = 1.0`: Prioritize coverage
- `alpha = 1.0, beta = 2.0`: Prioritize uncertainty reduction
- `K = 5`: Neighborhood size (tune based on cell density)
- `sigma = 0.15`: Kernel bandwidth (tune based on typical distances)

### Alternative Approaches Considered

**Option 1: Geometric Distance Only (Simpler)**
- Score = distance only
- Pros: Simple, guaranteed coverage
- Cons: Ignores user performance, may oversample confident regions

**Option 2: Uncertainty Only (Response-focused)**
- Score = uncertainty only
- Pros: Directly targets knowledge gaps
- Cons: May cluster questions, poor spatial coverage

**Option 3: Hybrid (Selected ⭐)**
- Score = distance × uncertainty
- Pros: Balances coverage and information gain
- Cons: Slightly more complex, requires parameter tuning

### Expected Performance

**Spatial Coverage:**
- Target: <0.10 mean distance after 5 questions (vs 0.25 with random)
- Mechanism: Distance component ensures spread

**Efficiency:**
- Target: 3-5 questions to reach 85% confidence (vs 8-12 random)
- Mechanism: Uncertainty component focuses sampling

**Adaptation:**
- System responds to performance patterns
- Poor performance in region → more questions there
- Strong performance → less sampling needed

### Why This Approach?

1. **Best Effort/Impact Ratio**: More sophisticated than pure geometric, but not as complex as Bayesian
2. **Interpretable**: Users can understand "asking about topics you're unsure about"
3. **Flexible**: Parameters can be tuned based on empirical performance
4. **Efficient**: Fast computation (K-NN lookup, simple scoring)
5. **Robust**: Degrades gracefully (falls back to geometric if uncertainty estimation fails)

---

## 3. Implementation Plan (Tier 2: Response-Aware Sampling)

### Phase 1: Foundation & Infrastructure (Week 1)
**Goal**: Set up data structures and utilities for adaptive sampling

#### Tasks:
1. **Precompute Pairwise Distances**
   - Create distance matrix between all cell centers
   - Store as `cell_distances.json` (750×750 matrix, ~2MB)
   - Use Euclidean distance in normalized coordinate space
   - Script: `scripts/precompute_cell_distances.py`

2. **Refactor Question Selection Code**
   - Extract question selection into separate function
   - Create `AdaptiveSampler` class to manage state
   - Maintain history of asked questions and responses
   - Store response correctness for uncertainty calculation

3. **Add Configuration System**
   - Create config object for sampling parameters:
     ```javascript
     const samplingConfig = {
       mode: 'adaptive-uncertainty',  // 'random' or 'adaptive-uncertainty'
       initialRandomQuestions: 2,
       minQuestionsBeforeExit: 3,
       confidenceThreshold: 0.85,
       maxQuestions: 10,

       // Uncertainty estimation parameters
       K: 5,                    // Number of nearest neighbors
       sigma: 0.15,            // Gaussian kernel bandwidth
       alpha: 1.0,             // Distance weight
       beta: 1.0,              // Uncertainty weight

       // Coverage thresholds
       coverageDistance: 0.15  // Max distance to consider "covered"
     }
     ```

4. **Create Cell Index Data Structure**
   - Build mapping: `cell_key → index` for O(1) lookup
   - Build reverse mapping: `index → cell_key`
   - Preload in initialization

**Deliverables**:
- `cell_distances.json` precomputed distance matrix
- `AdaptiveSampler` class skeleton in index.html
- Configuration system in place
- Cell index mappings created

**Testing**:
- Verify distance matrix loads correctly
- Check cell index mappings are bidirectional
- Validate configuration parameters

---

### Phase 2: Uncertainty Estimation Engine (Week 2)
**Goal**: Implement K-NN based uncertainty prediction

#### Tasks:
1. **Implement K-Nearest Neighbor Finder**
   ```javascript
   findKNearestAsked(cellKey, askedCells, K) {
     const cellIdx = this.cellKeyToIndex[cellKey];
     const distances = [];

     for (const askedCell of askedCells) {
       const askedIdx = this.cellKeyToIndex[askedCell];
       const dist = this.distances[cellIdx][askedIdx];
       distances.push({ cellKey: askedCell, distance: dist });
     }

     // Sort by distance and return K nearest
     distances.sort((a, b) => a.distance - b.distance);
     return distances.slice(0, K);
   }
   ```

2. **Implement Uncertainty Estimation**
   ```javascript
   estimateUncertainty(cellKey, askedCells, responses) {
     const K = this.config.K;
     const sigma = this.config.sigma;

     // Find K nearest asked cells
     const nearest = this.findKNearestAsked(cellKey, askedCells, K);

     if (nearest.length === 0) {
       // No data yet, maximum uncertainty
       return {
         predictedCorrectness: 0.5,
         uncertainty: 1.0,
         confidence: 0.0
       };
     }

     // Compute weighted average correctness using Gaussian kernel
     let totalWeight = 0;
     let weightedCorrectness = 0;

     for (const neighbor of nearest) {
       const dist = neighbor.distance;
       const weight = Math.exp(-dist * dist / (2 * sigma * sigma));
       const correct = responses[neighbor.cellKey] ? 1.0 : 0.0;

       weightedCorrectness += weight * correct;
       totalWeight += weight;
     }

     // Predicted correctness
     const p = totalWeight > 0 ? weightedCorrectness / totalWeight : 0.5;

     // Binary entropy (uncertainty)
     const epsilon = 1e-10;
     const pClipped = Math.max(epsilon, Math.min(1 - epsilon, p));
     const uncertainty = -(pClipped * Math.log2(pClipped) +
                          (1 - pClipped) * Math.log2(1 - pClipped));

     return {
       predictedCorrectness: p,
       uncertainty: uncertainty,
       confidence: 1 - uncertainty,
       numNeighbors: nearest.length,
       meanDistance: nearest.reduce((sum, n) => sum + n.distance, 0) / nearest.length
     };
   }
   ```

3. **Update Uncertainty Map After Each Response**
   ```javascript
   updateUncertaintyMap(askedCells, responses) {
     const uncertaintyMap = {};

     // Recompute uncertainty for ALL cells
     for (const cellKey of this.allCellKeys) {
       if (!askedCells.includes(cellKey)) {
         uncertaintyMap[cellKey] = this.estimateUncertainty(
           cellKey,
           askedCells,
           responses
         );
       } else {
         // Already asked, zero uncertainty
         uncertaintyMap[cellKey] = {
           predictedCorrectness: responses[cellKey] ? 1.0 : 0.0,
           uncertainty: 0.0,
           confidence: 1.0
         };
       }
     }

     return uncertaintyMap;
   }
   ```

**Deliverables**:
- K-NN finder function
- Uncertainty estimation with Gaussian kernel
- Real-time uncertainty map updates

**Testing**:
- Unit test uncertainty calculation with known data
- Verify entropy formula (max at p=0.5, min at p=0 or 1)
- Test with edge cases (K > available responses)
- Performance: <10ms per uncertainty update

---

### Phase 3: Uncertainty-Weighted Selection (Week 3)
**Goal**: Implement question selection using uncertainty scores

#### Tasks:
1. **Implement Scoring Function**
   ```javascript
   scoreCell(cellKey, askedCells, uncertaintyMap) {
     const alpha = this.config.alpha;
     const beta = this.config.beta;

     // Geometric distance component
     let minDistance = 1.0;  // Default if no asked cells
     if (askedCells.length > 0) {
       const cellIdx = this.cellKeyToIndex[cellKey];
       minDistance = Math.min(...askedCells.map(asked => {
         const askedIdx = this.cellKeyToIndex[asked];
         return this.distances[cellIdx][askedIdx];
       }));
     }

     // Uncertainty component
     const uncertainty = uncertaintyMap[cellKey]?.uncertainty || 1.0;

     // Combined score: distance^α × uncertainty^β
     const score = Math.pow(minDistance, alpha) * Math.pow(uncertainty, beta);

     return score;
   }
   ```

2. **Implement Adaptive Question Selection**
   ```javascript
   selectNextQuestion() {
     const availableQuestions = this._getAvailableQuestions();

     if (availableQuestions.length === 0) {
       return null;
     }

     // Phase 1: First N questions use geometric sampling
     if (this.askedCells.length < this.config.initialRandomQuestions) {
       return this._selectGeometric(availableQuestions);
     }

     // Phase 2: Uncertainty-weighted sampling
     return this._selectUncertaintyWeighted(availableQuestions);
   }

   _selectUncertaintyWeighted(availableQuestions) {
     // Update uncertainty map
     const uncertaintyMap = this.updateUncertaintyMap(
       this.askedCells,
       this.responses
     );

     // Group questions by cell
     const questionsByCell = this._groupByCell(availableQuestions);

     // Score each unasked cell
     let bestScore = -Infinity;
     let bestQuestion = null;

     for (const [cellKey, questions] of Object.entries(questionsByCell)) {
       if (this.askedCells.includes(cellKey)) continue;

       const score = this.scoreCell(cellKey, this.askedCells, uncertaintyMap);

       if (score > bestScore) {
         bestScore = score;
         bestQuestion = this._selectRandom(questions);
       }
     }

     // Log selection for debugging
     console.log(`Selected cell score: ${bestScore.toFixed(3)}`);

     return bestQuestion;
   }
   ```

3. **Integrate with Quiz Flow**
   - Update `startNewQuizRound()` to use adaptive sampler
   - Store responses with correctness flag
   - Update uncertainty map after each question

**Deliverables**:
- Scoring function with tunable α and β parameters
- Full uncertainty-weighted selection algorithm
- Integration with existing quiz flow

**Testing**:
- Verify selection adapts to responses (correct vs incorrect)
- Test parameter sensitivity (α, β values)
- Compare coverage with random baseline
- Performance: selection should be <50ms

---

### Phase 4: Confidence Metrics & Early Exit (Week 4)
**Goal**: Enable users to stop early when map is well-defined

#### Tasks:
1. **Implement Confidence Estimation**
   ```javascript
   computeConfidence(askedCells, uncertaintyMap) {
     let coveredCells = 0;
     const threshold = this.config.coverageDistance;  // 0.15

     // Method 1: Distance-based coverage
     for (const cellKey of this.allCellKeys) {
       let minDist = Infinity;

       for (const askedCell of askedCells) {
         const cellIdx = this.cellKeyToIndex[cellKey];
         const askedIdx = this.cellKeyToIndex[askedCell];
         const dist = this.distances[cellIdx][askedIdx];
         minDist = Math.min(minDist, dist);
       }

       if (minDist < threshold) {
         coveredCells++;
       }
     }

     const coverageConfidence = coveredCells / this.allCellKeys.length;

     // Method 2: Uncertainty-based confidence
     let totalConfidence = 0;
     for (const cellKey of this.allCellKeys) {
       totalConfidence += uncertaintyMap[cellKey]?.confidence || 0;
     }
     const uncertaintyConfidence = totalConfidence / this.allCellKeys.length;

     // Combined confidence (average of both methods)
     const combinedConfidence = (coverageConfidence + uncertaintyConfidence) / 2;

     return {
       overallConfidence: combinedConfidence,
       coverageConfidence: coverageConfidence,
       uncertaintyConfidence: uncertaintyConfidence,
       coveredCells: coveredCells,
       totalCells: this.allCellKeys.length
     };
   }
   ```

2. **Add Dynamic "Show Results" Button**
   - Show button after minimum questions (default: 3)
   - Display confidence % on button: "Show Results (85% confidence)"
   - Enable when: `confidence >= threshold AND numQuestions >= minQuestions`
   - Disable otherwise with helpful message

3. **Add Confidence Visualizations**
   - Progress bar showing confidence over time
   - Two-part bar: coverage (green) + uncertainty (blue)
   - Text display: "85% confidence - Ready to view!"
   - Mini uncertainty heatmap (optional)

**Deliverables**:
- Dual-method confidence calculation
- Dynamic early exit button with state management
- Confidence visualization UI
- Real-time confidence updates

---

### Phase 5: UI Enhancements & Polish (Week 5)
**Goal**: Add interactive exploration features and polish UX

#### Tasks:
1. **"Answer More Questions" Button**
   - Add button to map view: "Answer More Questions"
   - Preserve existing response history and uncertainty map
   - Continue adaptive sampling from current state
   - Update map dynamically with new responses
   - Show running total: "10 questions answered"

2. **Click-to-Ask Cell Feature**
   - Make heatmap cells clickable
   - On click:
     - Select random question from that cell
     - Show question in modal/overlay with cell label
     - Update map with response
     - Recompute uncertainty map and heatmap
   - Visual feedback: highlight selected cell, show uncertainty score
   - Disable cells with no questions available

3. **Sampling Mode Selector (for A/B Testing)**
   - Add dropdown: "Random" vs "Adaptive (Recommended)"
   - Enable comparison and user preference
   - Log mode choice and performance metrics
   - Show explanation tooltips for each mode

4. **Enhanced Feedback & Visualizations**
   - Uncertainty overlay: color cells by uncertainty (red = high, green = low)
   - "Suggested Next Topics" panel showing high-uncertainty regions
   - Question distribution histogram
   - Performance stats: "You've covered 85% of the map in 5 questions!"

5. **Parameter Tuning UI (Debug Mode)**
   - Add settings panel for α, β, K, sigma
   - Real-time visualization of parameter effects
   - "Reset to defaults" button
   - Export session data for analysis

**Deliverables**:
- Interactive map with clickable cells
- "Answer More" button with preserved state
- Mode selector for A/B testing
- Uncertainty visualization overlay
- Parameter tuning interface (optional)

**Testing**:
- User testing: 5-10 participants
- Compare user satisfaction random vs adaptive
- Measure: time to confidence threshold, completion rate
- Collect qualitative feedback on UX

---

## 4. Complete Implementation: AdaptiveSampler Class

Here's the full implementation bringing together all phases:

```javascript
class AdaptiveSampler {
  constructor(questionsPool, distances, config) {
    this.questionsPool = questionsPool;
    this.distances = distances.distances;  // 2D array
    this.cellKeys = distances.cell_keys;   // Array of "gx_gy" strings
    this.config = {
      mode: 'adaptive-uncertainty',
      initialRandomQuestions: 2,
      minQuestionsBeforeExit: 3,
      confidenceThreshold: 0.85,
      maxQuestions: 10,
      K: 5,
      sigma: 0.15,
      alpha: 1.0,
      beta: 1.0,
      coverageDistance: 0.15,
      ...config  // Allow override
    };

    // Build cell index mappings
    this.cellKeyToIndex = {};
    this.indexToCellKey = {};
    this.cellKeys.forEach((key, idx) => {
      this.cellKeyToIndex[key] = idx;
      this.indexToCellKey[idx] = key;
    });

    this.allCellKeys = this.cellKeys;

    // State
    this.askedCells = [];
    this.responses = {};  // cellKey → true/false
    this.uncertaintyMap = {};
  }

  // === Phase 1: Infrastructure ===

  _getAvailableQuestions() {
    // Return all questions from cells that haven't been asked
    const available = [];
    for (const cellData of this.questionsPool.cells) {
      const cellKey = `${cellData.cell.gx}_${cellData.cell.gy}`;
      if (!this.askedCells.includes(cellKey)) {
        for (const question of cellData.questions) {
          available.push({ ...question, cellKey });
        }
      }
    }
    return available;
  }

  _groupByCell(questions) {
    const grouped = {};
    for (const q of questions) {
      if (!grouped[q.cellKey]) {
        grouped[q.cellKey] = [];
      }
      grouped[q.cellKey].push(q);
    }
    return grouped;
  }

  _selectRandom(items) {
    return items[Math.floor(Math.random() * items.length)];
  }

  // === Phase 2: Uncertainty Estimation ===

  findKNearestAsked(cellKey, askedCells, K) {
    const cellIdx = this.cellKeyToIndex[cellKey];
    const distances = [];

    for (const askedCell of askedCells) {
      const askedIdx = this.cellKeyToIndex[askedCell];
      const dist = this.distances[cellIdx][askedIdx];
      distances.push({ cellKey: askedCell, distance: dist });
    }

    distances.sort((a, b) => a.distance - b.distance);
    return distances.slice(0, K);
  }

  estimateUncertainty(cellKey, askedCells, responses) {
    const K = this.config.K;
    const sigma = this.config.sigma;

    const nearest = this.findKNearestAsked(cellKey, askedCells, K);

    if (nearest.length === 0) {
      return {
        predictedCorrectness: 0.5,
        uncertainty: 1.0,
        confidence: 0.0
      };
    }

    let totalWeight = 0;
    let weightedCorrectness = 0;

    for (const neighbor of nearest) {
      const dist = neighbor.distance;
      const weight = Math.exp(-dist * dist / (2 * sigma * sigma));
      const correct = responses[neighbor.cellKey] ? 1.0 : 0.0;

      weightedCorrectness += weight * correct;
      totalWeight += weight;
    }

    const p = totalWeight > 0 ? weightedCorrectness / totalWeight : 0.5;

    const epsilon = 1e-10;
    const pClipped = Math.max(epsilon, Math.min(1 - epsilon, p));
    const uncertainty = -(pClipped * Math.log2(pClipped) +
                         (1 - pClipped) * Math.log2(1 - pClipped));

    return {
      predictedCorrectness: p,
      uncertainty: uncertainty,
      confidence: 1 - uncertainty,
      numNeighbors: nearest.length
    };
  }

  updateUncertaintyMap(askedCells, responses) {
    const uncertaintyMap = {};

    for (const cellKey of this.allCellKeys) {
      if (!askedCells.includes(cellKey)) {
        uncertaintyMap[cellKey] = this.estimateUncertainty(
          cellKey,
          askedCells,
          responses
        );
      } else {
        uncertaintyMap[cellKey] = {
          predictedCorrectness: responses[cellKey] ? 1.0 : 0.0,
          uncertainty: 0.0,
          confidence: 1.0
        };
      }
    }

    return uncertaintyMap;
  }

  // === Phase 3: Uncertainty-Weighted Selection ===

  scoreCell(cellKey, askedCells, uncertaintyMap) {
    const alpha = this.config.alpha;
    const beta = this.config.beta;

    let minDistance = 1.0;
    if (askedCells.length > 0) {
      const cellIdx = this.cellKeyToIndex[cellKey];
      minDistance = Math.min(...askedCells.map(asked => {
        const askedIdx = this.cellKeyToIndex[asked];
        return this.distances[cellIdx][askedIdx];
      }));
    }

    const uncertainty = uncertaintyMap[cellKey]?.uncertainty || 1.0;
    const score = Math.pow(minDistance, alpha) * Math.pow(uncertainty, beta);

    return score;
  }

  _selectGeometric(availableQuestions) {
    // Fallback to geometric sampling for first N questions
    const questionsByCell = this._groupByCell(availableQuestions);
    let maxMinDistance = -Infinity;
    let bestQuestion = null;

    for (const [cellKey, questions] of Object.entries(questionsByCell)) {
      if (this.askedCells.includes(cellKey)) continue;

      const cellIdx = this.cellKeyToIndex[cellKey];
      let minDist = Infinity;

      if (this.askedCells.length > 0) {
        minDist = Math.min(...this.askedCells.map(asked => {
          const askedIdx = this.cellKeyToIndex[asked];
          return this.distances[cellIdx][askedIdx];
        }));
      } else {
        minDist = Math.random();  // Random for very first question
      }

      if (minDist > maxMinDistance) {
        maxMinDistance = minDist;
        bestQuestion = this._selectRandom(questions);
      }
    }

    return bestQuestion;
  }

  _selectUncertaintyWeighted(availableQuestions) {
    this.uncertaintyMap = this.updateUncertaintyMap(
      this.askedCells,
      this.responses
    );

    const questionsByCell = this._groupByCell(availableQuestions);
    let bestScore = -Infinity;
    let bestQuestion = null;
    let bestCellKey = null;

    for (const [cellKey, questions] of Object.entries(questionsByCell)) {
      if (this.askedCells.includes(cellKey)) continue;

      const score = this.scoreCell(cellKey, this.askedCells, this.uncertaintyMap);

      if (score > bestScore) {
        bestScore = score;
        bestCellKey = cellKey;
        bestQuestion = this._selectRandom(questions);
      }
    }

    console.log(`Selected cell ${bestCellKey}, score: ${bestScore.toFixed(3)}, ` +
                `uncertainty: ${this.uncertaintyMap[bestCellKey]?.uncertainty.toFixed(3)}`);

    return bestQuestion;
  }

  selectNextQuestion() {
    const availableQuestions = this._getAvailableQuestions();

    if (availableQuestions.length === 0) {
      return null;
    }

    if (this.askedCells.length < this.config.initialRandomQuestions) {
      return this._selectGeometric(availableQuestions);
    }

    return this._selectUncertaintyWeighted(availableQuestions);
  }

  recordResponse(question, isCorrect) {
    const cellKey = question.cellKey;
    this.askedCells.push(cellKey);
    this.responses[cellKey] = isCorrect;
  }

  // === Phase 4: Confidence Metrics ===

  computeConfidence() {
    if (this.askedCells.length === 0) {
      return {
        overallConfidence: 0,
        coverageConfidence: 0,
        uncertaintyConfidence: 0,
        coveredCells: 0,
        totalCells: this.allCellKeys.length
      };
    }

    let coveredCells = 0;
    const threshold = this.config.coverageDistance;

    for (const cellKey of this.allCellKeys) {
      const cellIdx = this.cellKeyToIndex[cellKey];
      let minDist = Infinity;

      for (const askedCell of this.askedCells) {
        const askedIdx = this.cellKeyToIndex[askedCell];
        const dist = this.distances[cellIdx][askedIdx];
        minDist = Math.min(minDist, dist);
      }

      if (minDist < threshold) {
        coveredCells++;
      }
    }

    const coverageConfidence = coveredCells / this.allCellKeys.length;

    // Update uncertainty map if not already updated
    if (Object.keys(this.uncertaintyMap).length === 0) {
      this.uncertaintyMap = this.updateUncertaintyMap(
        this.askedCells,
        this.responses
      );
    }

    let totalConfidence = 0;
    for (const cellKey of this.allCellKeys) {
      totalConfidence += this.uncertaintyMap[cellKey]?.confidence || 0;
    }
    const uncertaintyConfidence = totalConfidence / this.allCellKeys.length;

    const combinedConfidence = (coverageConfidence + uncertaintyConfidence) / 2;

    return {
      overallConfidence: combinedConfidence,
      coverageConfidence: coverageConfidence,
      uncertaintyConfidence: uncertaintyConfidence,
      coveredCells: coveredCells,
      totalCells: this.allCellKeys.length
    };
  }

  canEarlyExit() {
    const confidence = this.computeConfidence();
    return (
      this.askedCells.length >= this.config.minQuestionsBeforeExit &&
      confidence.overallConfidence >= this.config.confidenceThreshold
    );
  }

  // === Utility Methods ===

  getUncertaintyMap() {
    return this.uncertaintyMap;
  }

  getStats() {
    const confidence = this.computeConfidence();
    return {
      questionsAsked: this.askedCells.length,
      ...confidence,
      canExit: this.canEarlyExit()
    };
  }

  reset() {
    this.askedCells = [];
    this.responses = {};
    this.uncertaintyMap = {};
  }
}
```

### Usage Example

```javascript
// Initialize
const sampler = new AdaptiveSampler(
  questionsPool,      // From cell_questions.json
  distancesData,      // From cell_distances.json
  {
    confidenceThreshold: 0.85,
    K: 5,
    sigma: 0.15,
    alpha: 1.0,
    beta: 1.0
  }
);

// Quiz loop
while (true) {
  const question = sampler.selectNextQuestion();
  if (!question) break;

  // Show question to user
  const userAnswer = await askUser(question);
  const isCorrect = (userAnswer === question.correct_answer);

  // Record response
  sampler.recordResponse(question, isCorrect);

  // Check if can exit early
  const stats = sampler.getStats();
  updateConfidenceUI(stats);

  if (sampler.canEarlyExit()) {
    offerEarlyExit();
  }

  if (sampler.askedCells.length >= sampler.config.maxQuestions) {
    break;
  }
}

// Show results
showKnowledgeMap(sampler.responses, sampler.getUncertaintyMap());

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

## 5. Technical Details

### Precomputation Script

Create `scripts/precompute_cell_distances.py`:

```python
#!/usr/bin/env python3
"""Precompute pairwise distances between all cell centers."""

import json
import numpy as np
from scipy.spatial.distance import cdist
from pathlib import Path

def precompute_cell_distances():
    # Load cell questions
    input_file = Path('cell_questions.json')
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return

    with open(input_file) as f:
        data = json.load(f)

    # Extract cell coordinates
    cells = []
    cell_keys = []

    for cell_data in data['cells']:
        cell = cell_data['cell']
        cells.append([cell['center_x'], cell['center_y']])
        cell_keys.append(f"{cell['gx']}_{cell['gy']}")

    coords = np.array(cells)

    # Compute pairwise distances (Euclidean in normalized [0,1] space)
    print(f"Computing distances for {len(cells)} cells...")
    distances = cdist(coords, coords, metric='euclidean')

    # Create output
    output = {
        'cell_keys': cell_keys,
        'distances': distances.tolist(),
        'metadata': {
            'num_cells': len(cells),
            'metric': 'euclidean',
            'coordinate_space': 'normalized [0,1]',
            'source_file': str(input_file),
            'dimensions': list(distances.shape)
        }
    }

    output_file = Path('cell_distances.json')
    with open(output_file, 'w') as f:
        json.dump(output, f)

    file_size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"✓ Computed {len(cells)}×{len(cells)} distance matrix")
    print(f"✓ Saved to {output_file} ({file_size_mb:.2f} MB)")

    # Print statistics
    print(f"\nDistance statistics:")
    print(f"  Min: {distances.min():.4f}")
    print(f"  Max: {distances.max():.4f}")
    print(f"  Mean: {distances.mean():.4f}")
    print(f"  Median: {np.median(distances):.4f}")

if __name__ == '__main__':
    precompute_cell_distances()
```

**Run precomputation:**
```bash
python3 scripts/precompute_cell_distances.py
```

### Performance Considerations

1. **Distance Computation**: O(1) lookup from precomputed matrix
2. **Selection Speed**: O(N×M) where N=cells (~750), M=asked cells (<10). Target: <50ms
3. **Uncertainty Update**: O(N×K) where K=5. Target: <10ms per cell, <100ms total
4. **Memory**: Distance matrix ~4MB, uncertainty map ~30KB, total <5MB
5. **Optimization**: If slow, can use spatial indexing (KD-tree) or approximate nearest neighbors

---

## 6. Success Metrics

### Quantitative Metrics

1. **Spatial Coverage**: Mean distance from each cell to nearest asked cell
   - Target: <0.10 normalized distance after 5 questions
   - Baseline (random): ~0.25 after 10 questions

2. **Questions to Confidence**: Questions needed to reach 85% confidence
   - Target: 3-5 with adaptive
   - Baseline: 8-12 with random

3. **Early Exit Rate**: % users who stop before 10 questions
   - Target: >60% exit after 3-5 questions

4. **Information Gain per Question**: Change in map confidence per question
   - Target: Adaptive >2× gain per question vs random

5. **Adaptation Quality**: Correlation between uncertainty and next question
   - Target: >0.7 correlation (high uncertainty → more likely to be asked)

### Qualitative Metrics

1. **User Satisfaction**: Survey rating for "quiz felt efficient"
2. **Engagement**: Time spent exploring map vs answering questions
3. **Completion Rate**: % users who complete vs abandon
4. **Perceived Intelligence**: "The system adapted to my knowledge"

---

## 7. A/B Testing Plan

### Test Setup
1. **Groups**:
   - Control: Random sampling
   - Treatment: Adaptive uncertainty-weighted sampling
2. **Assignment**: Random 50/50 split
3. **Sample Size**: 200+ users (100 per group)
4. **Duration**: 2-3 weeks

### Metrics to Compare
- Questions to 85% confidence
- Early exit rate
- Completion rate
- User satisfaction (post-quiz survey)
- Time to completion

### Success Criteria
- Adaptive reduces questions by >30%
- Early exit rate >50%
- No decrease in completion rate
- User satisfaction ≥ random

---

## 8. Timeline & Priorities

### Must-Have (MVP - 4 weeks)
- **Week 1**: Foundation & infrastructure ✅
- **Week 2**: Uncertainty estimation engine ✅
- **Week 3**: Uncertainty-weighted selection ✅
- **Week 4**: Confidence metrics & early exit ✅

### Should-Have (5 weeks)
- **Week 5**: UI enhancements (click cells, answer more, visualizations)

### Nice-to-Have (6+ weeks)
- Parameter tuning UI
- Advanced visualizations (uncertainty heatmap)
- Bayesian/Information-theoretic approaches
- Multi-objective optimization

---

## 9. Dependencies & Blockers

### Ready Now ✅
- [x] Cell questions generation (750/1,600 cells) - sufficient to start
- [x] Heatmap visualization working
- [x] Multi-round quiz infrastructure
- [x] Response tracking in place

### No Blockers
Can start implementation immediately with existing 750 cells. Additional cells (750→1,600) can be integrated as they're generated.

---

## 10. Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| **Performance**: Uncertainty updates too slow | Precompute distances, optimize K-NN, use spatial indexing if needed |
| **Complexity**: Too many parameters to tune | Start with defaults (α=β=1), tune only if needed |
| **Edge cases**: Run out of questions in high-uncertainty cells | Fall back to nearest cells with questions |
| **UX**: Adaptive feels unpredictable | Show uncertainty visualization, explain selection |
| **Overfitting**: Parameters tuned on small dataset | Use cross-validation, test on held-out users |

---

## Summary

This plan provides a complete roadmap for implementing **Tier 2: Response-Aware Adaptive Sampling** in the knowledge map quiz system. The approach combines spatial coverage with intelligent response to user performance, selecting questions that maximize expected information gain.

### Key Features
- ✅ **Uncertainty-weighted selection**: Prioritizes regions where confidence is lowest
- ✅ **K-NN prediction**: Uses nearby responses to estimate correctness
- ✅ **Binary entropy**: Measures uncertainty (high when p≈0.5)
- ✅ **Dual confidence**: Combines coverage and uncertainty metrics
- ✅ **Early exit**: Enable stop after 3-5 questions when confidence ≥85%
- ✅ **Parameter tuning**: α, β, K, sigma adjustable for optimization

### Implementation Timeline
1. **Week 1**: Foundation & precomputation
2. **Week 2**: Uncertainty estimation (K-NN + entropy)
3. **Week 3**: Uncertainty-weighted selection
4. **Week 4**: Confidence metrics & early exit
5. **Week 5**: UI enhancements & polish

### Expected Impact
- **Efficiency**: 3-5 questions to reach confidence (vs 8-12 random)
- **Coverage**: <0.10 mean distance after 5 questions (vs 0.25 random)
- **Adaptation**: System responds to user performance patterns
- **User Experience**: Intelligent, efficient, interpretable

### Next Steps
1. **Review & approve** this Tier 2 plan
2. **Precompute distances**: Run `precompute_cell_distances.py` → `cell_distances.json`
3. **Implement Phase 1**: Set up infrastructure and configuration
4. **Set up A/B testing**: Prepare comparison framework
5. **Iterative development**: Build, test, refine across weeks 2-5

**Full detailed plan**: See this document for complete algorithms, code, testing strategy, and success metrics.
