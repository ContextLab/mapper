/**
 * AdaptiveSampler with Multi-Level Question Support (Phase 4)
 *
 * Enhancements over base AdaptiveSampler:
 * 1. Tracks performance per difficulty level (0-4)
 * 2. Adaptive difficulty progression based on user performance
 * 3. Level-aware question selection (considers both spatial coverage AND difficulty)
 * 4. Performance analytics per level
 * 5. RBF-based knowledge estimation with level-dependent sigma values
 *
 * Question Level Definitions:
 * - Level 0: Base questions from original Wikipedia articles (most specific)
 * - Level 1-4: Progressively broader/more abstract concepts
 *
 * Knowledge Estimation Algorithm (RBF-based):
 *
 * Each question has coordinates (x, y) and a level. When a question is answered,
 * it creates a Radial Basis Function (RBF) centered at (x, y) with sigma determined
 * by its level:
 *
 *   Level 0: sigma = 0.01  (very localized - 1% of space)
 *   Level 1: sigma = 0.05  (localized - 5% of space)
 *   Level 2: sigma = 0.075 (moderate - 7.5% of space)
 *   Level 3: sigma = 0.10  (broad - 10% of space)
 *   Level 4: sigma = 0.15  (very broad - 15% of space)
 *
 * Higher-level (more abstract) questions have broader "reach" in knowledge space.
 *
 * To estimate knowledge at any point (targetX, targetY):
 *
 *   p(targetX, targetY) = Σ w_i * correct_i / Σ w_i
 *
 * where:
 *   w_i = exp(-dist_i² / (2 * sigma_i²))
 *   dist_i = Euclidean distance from question i to target point
 *   sigma_i = sigma value for question i's level
 *   correct_i = 1.0 if correct, 0.0 if incorrect, 0.1 if "I Don't Know"
 *
 * This allows:
 * - Specific questions (level 0) to inform only nearby regions
 * - Abstract questions (level 4) to inform broad swaths of the knowledge map
 * - Natural mixing of evidence from different abstraction levels
 */

class MultiLevelAdaptiveSampler {
    constructor(questionsPool, distances, config) {
        this.questionsPool = questionsPool;
        this.distances = distances.distances;  // 2D array
        this.cellKeys = distances.cell_keys;   // Array of "gx_gy" strings
        this.config = {
            mode: 'adaptive-multilevel',
            initialRandomQuestions: 2,
            minQuestionsBeforeExit: 3,
            confidenceThreshold: 0.85,
            maxQuestions: 10,
            K: 5,
            sigma: 0.15,  // Default sigma (will be overridden by level-specific values)
            alpha: 1.0,
            beta: 1.0,
            gamma: 0.5,  // Weight for level selection
            coverageDistance: 0.15,

            // Multi-level specific config
            startLevel: 0,  // Start with easiest questions
            maxLevel: 4,    // Maximum difficulty level
            levelProgressionThreshold: 0.7,  // 70% accuracy to progress to next level
            levelRegressionThreshold: 0.4,   // <40% accuracy to regress to easier level
            minQuestionsPerLevel: 3,  // Minimum questions before level change

            // Level-dependent sigma values
            // Higher levels (more abstract) have broader reach in knowledge space
            // Lower levels (more specific) have localized reach
            sigmaBylevel: {
                0: 0.01,   // Very localized (1% of space)
                1: 0.05,   // Localized (5% of space)
                2: 0.075,  // Moderate reach (7.5% of space)
                3: 0.10,   // Broad reach (10% of space)
                4: 0.15    // Very broad reach (15% of space)
            },

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

        // State (spatial)
        this.askedCells = [];  // Track which cells have been asked (for geometric sampling)
        this.askedQuestions = new Set();  // Set of question IDs asked
        this.askedQuestionData = [];  // Array of {questionId, x, y, level, correct}
        this.uncertaintyMap = {};

        // State (multi-level)
        this.currentLevel = this.config.startLevel;
        this.levelStats = {};  // level → {correct, total, accuracy}
        this.levelAskedCells = {};  // level → [cellKeys]
        this.levelResponses = {};  // level → {cellKey → correctness}

        // Initialize level stats
        for (let level = 0; level <= this.config.maxLevel; level++) {
            this.levelStats[level] = { correct: 0, total: 0, accuracy: 0 };
            this.levelAskedCells[level] = [];
            this.levelResponses[level] = {};
        }
    }

    // === Phase 1: Infrastructure ===

    _getAvailableQuestions() {
        // Return all questions that haven't been asked
        const available = [];
        for (const cellData of this.questionsPool.cells) {
            const cellKey = `${cellData.cell.gx}_${cellData.cell.gy}`;
            for (let i = 0; i < cellData.questions.length; i++) {
                const question = cellData.questions[i];
                const questionId = `${cellKey}_${question.level || 0}_${i}`;

                if (!this.askedQuestions.has(questionId)) {
                    available.push({
                        ...question,
                        cellKey,
                        cellData,
                        questionId,
                        level: question.level || 0  // Default to level 0 if not specified
                    });
                }
            }
        }
        return available;
    }

    _getAvailableQuestionsAtLevel(level) {
        // Filter questions by difficulty level
        const allAvailable = this._getAvailableQuestions();
        return allAvailable.filter(q => q.level === level);
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

    // === Phase 2: Uncertainty Estimation (per level) ===

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

    estimateUncertainty(targetX, targetY) {
        // Estimate knowledge at point (targetX, targetY) using RBFs from all asked questions

        if (this.askedQuestionData.length === 0) {
            return {
                predictedCorrectness: 0.5,
                uncertainty: 1.0,
                confidence: 0.0
            };
        }

        let totalWeight = 0;
        let weightedCorrectness = 0;

        // Compute weighted average using RBF from each asked question
        for (const questionData of this.askedQuestionData) {
            const { x, y, level, correct } = questionData;

            // Use level-specific sigma for this question's RBF
            // Higher level questions have broader "reach" in knowledge space
            const sigma = this.config.sigmaByLevel[level] || this.config.sigma;

            // Compute distance from question to target point
            const dx = targetX - x;
            const dy = targetY - y;
            const distSq = dx * dx + dy * dy;

            // Gaussian RBF weight
            const weight = Math.exp(-distSq / (2 * sigma * sigma));

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
            numQuestions: this.askedQuestionData.length
        };
    }

    updateUncertaintyMap() {
        // Evaluate uncertainty at each cell's center
        const uncertaintyMap = {};

        for (const cellData of this.questionsPool.cells) {
            const cellKey = `${cellData.cell.gx}_${cellData.cell.gy}`;

            // Get cell center coordinates
            // Assuming cell has x, y fields (or compute from grid)
            const cellX = cellData.cell.x || cellData.cell.gx / 40;  // Normalize if needed
            const cellY = cellData.cell.y || cellData.cell.gy / 40;

            // Estimate uncertainty at this cell's center using all asked questions
            uncertaintyMap[cellKey] = this.estimateUncertainty(cellX, cellY);
        }

        return uncertaintyMap;
    }

    // === Phase 3: Multi-Level Uncertainty-Weighted Selection ===

    scoreCell(cellKey, askedCells, uncertaintyMap, levelBonus = 0) {
        // Dynamic alpha/beta based on confidence
        const confidence = this.computeConfidence().overallConfidence;
        const alpha = 2 * (1 - confidence);
        const beta = 2 * confidence;

        // Spatial coverage term
        let minDistance = 1.0;
        if (askedCells.length > 0) {
            const cellIdx = this.cellKeyToIndex[cellKey];
            minDistance = Math.min(...askedCells.map(asked => {
                const askedIdx = this.cellKeyToIndex[asked];
                return this.distances[cellIdx][askedIdx];
            }));
        }

        // Uncertainty term
        const uncertainty = uncertaintyMap[cellKey]?.uncertainty || 1.0;

        // Combined score with level bonus
        const baseScore = Math.pow(minDistance, alpha) * Math.pow(uncertainty, beta);
        const score = baseScore * (1 + this.config.gamma * levelBonus);

        return score;
    }

    _selectGeometric(availableQuestions) {
        // Geometric sampling for initial questions
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
            }

            if (minDist > maxMinDistance) {
                maxMinDistance = minDist;
                bestQuestion = this._selectRandom(questions);
            }
        }

        return bestQuestion;
    }

    _selectUncertaintyWeighted(availableQuestions) {
        // Update uncertainty map using RBF-based estimation
        this.uncertaintyMap = this.updateUncertaintyMap();

        const questionsByCell = this._groupByCell(availableQuestions);
        let bestScore = -Infinity;
        let bestQuestion = null;
        let bestCellKey = null;

        for (const [cellKey, questions] of Object.entries(questionsByCell)) {
            if (this.askedCells.includes(cellKey)) continue;

            // Calculate level bonus (prefer current level, tolerate ±1 level)
            const cellLevel = questions[0].level || 0;
            const levelDiff = Math.abs(cellLevel - this.currentLevel);
            const levelBonus = levelDiff === 0 ? 1.0 : (levelDiff === 1 ? 0.5 : 0.0);

            const score = this.scoreCell(cellKey, this.askedCells, this.uncertaintyMap, levelBonus);

            if (score > bestScore) {
                bestScore = score;
                bestCellKey = cellKey;
                bestQuestion = this._selectRandom(questions);
            }
        }

        console.log(`Selected cell ${bestCellKey}, score: ${bestScore.toFixed(3)}, ` +
                    `level: ${bestQuestion?.level || 0}, uncertainty: ${this.uncertaintyMap[bestCellKey]?.uncertainty.toFixed(3)}`);

        return bestQuestion;
    }

    // === Phase 4: Adaptive Level Selection ===

    determineNextLevel() {
        const stats = this.levelStats[this.currentLevel];

        // Need minimum questions before changing level
        if (stats.total < this.config.minQuestionsPerLevel) {
            return this.currentLevel;
        }

        const accuracy = stats.accuracy;

        // Progress to harder level if doing well
        if (accuracy >= this.config.levelProgressionThreshold &&
            this.currentLevel < this.config.maxLevel) {
            console.log(`Level ${this.currentLevel} accuracy: ${(accuracy * 100).toFixed(1)}% → Progressing to level ${this.currentLevel + 1}`);
            return this.currentLevel + 1;
        }

        // Regress to easier level if struggling
        if (accuracy < this.config.levelRegressionThreshold &&
            this.currentLevel > 0) {
            console.log(`Level ${this.currentLevel} accuracy: ${(accuracy * 100).toFixed(1)}% → Regressing to level ${this.currentLevel - 1}`);
            return this.currentLevel - 1;
        }

        return this.currentLevel;
    }

    selectNextQuestion() {
        // Update current level based on performance
        this.currentLevel = this.determineNextLevel();

        // Try to get questions at current level first
        let availableQuestions = this._getAvailableQuestionsAtLevel(this.currentLevel);

        // If no questions at current level, try adjacent levels
        if (availableQuestions.length === 0) {
            console.log(`No questions available at level ${this.currentLevel}, trying adjacent levels`);
            for (let offset of [1, -1, 2, -2]) {
                const tryLevel = this.currentLevel + offset;
                if (tryLevel >= 0 && tryLevel <= this.config.maxLevel) {
                    availableQuestions = this._getAvailableQuestionsAtLevel(tryLevel);
                    if (availableQuestions.length > 0) {
                        console.log(`Using level ${tryLevel} instead`);
                        break;
                    }
                }
            }
        }

        // If still no questions, get any available
        if (availableQuestions.length === 0) {
            availableQuestions = this._getAvailableQuestions();
        }

        if (availableQuestions.length === 0) {
            return null;
        }

        // Select question using geometric or uncertainty-weighted strategy
        let selectedQuestion;
        if (this.askedCells.length < this.config.initialRandomQuestions) {
            selectedQuestion = this._selectGeometric(availableQuestions);
        } else {
            selectedQuestion = this._selectUncertaintyWeighted(availableQuestions);
        }

        // Mark question as asked
        if (selectedQuestion && selectedQuestion.questionId) {
            this.askedQuestions.add(selectedQuestion.questionId);
        }

        return selectedQuestion;
    }

    recordResponse(questionId, x, y, level, isCorrect, fractionalCorrectness = null) {
        // Store question data with coordinates for RBF-based estimation
        const correctness = fractionalCorrectness !== null ? fractionalCorrectness :
                           (isCorrect ? 1.0 : 0.0);

        this.askedQuestionData.push({
            questionId,
            x,
            y,
            level,
            correct: correctness
        });

        // Extract cell key from question location (for cell-based tracking)
        // Assuming questions have cellKey or we can infer from coordinates
        // For now, use a simple grid mapping
        const cellKey = `${Math.floor(x * 40)}_${Math.floor(y * 40)}`;

        // Update cell tracking (for geometric sampling)
        if (!this.askedCells.includes(cellKey)) {
            this.askedCells.push(cellKey);
        }

        // Update level-specific state
        if (!this.levelAskedCells[level].includes(cellKey)) {
            this.levelAskedCells[level].push(cellKey);
        }
        this.levelResponses[level][cellKey] = correctness;

        // Update level statistics
        this.levelStats[level].total++;
        if (correctness > 0.5) {  // Count as correct if >50%
            this.levelStats[level].correct++;
        }
        this.levelStats[level].accuracy = this.levelStats[level].correct / this.levelStats[level].total;
    }

    // === Phase 5: Confidence Metrics (Enhanced) ===

    computeConfidence() {
        if (this.askedCells.length === 0) {
            return {
                overallConfidence: 0,
                coverageConfidence: 0,
                uncertaintyConfidence: 0,
                coveredCells: 0,
                totalCells: this.allCellKeys.length,
                levelStats: this.levelStats,
                currentLevel: this.currentLevel
            };
        }

        // Coverage confidence
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

        // Uncertainty confidence
        if (!this.uncertaintyMap || Object.keys(this.uncertaintyMap).length === 0) {
            this.uncertaintyMap = this.updateUncertaintyMap(
                this.askedCells,
                this.responses
            );
        }

        let totalConfidence = 0;
        for (const cellKey of this.allCellKeys) {
            totalConfidence += (this.uncertaintyMap[cellKey]?.confidence || 0);
        }
        const uncertaintyConfidence = totalConfidence / this.allCellKeys.length;

        // Overall confidence (weighted average)
        const overallConfidence = 0.6 * coverageConfidence + 0.4 * uncertaintyConfidence;

        return {
            overallConfidence,
            coverageConfidence,
            uncertaintyConfidence,
            coveredCells,
            totalCells: this.allCellKeys.length,
            levelStats: this.levelStats,
            currentLevel: this.currentLevel
        };
    }

    getStats() {
        const confidence = this.computeConfidence();
        return {
            ...confidence,
            questionsAsked: this.askedCells.length,
            totalQuestions: this.questionsPool.cells.reduce((sum, cell) => sum + cell.questions.length, 0)
        };
    }

    shouldExit() {
        if (this.askedCells.length < this.config.minQuestionsBeforeExit) {
            return false;
        }

        const confidence = this.computeConfidence();
        return confidence.overallConfidence >= this.config.confidenceThreshold;
    }

    reset() {
        this.askedCells = [];
        this.askedQuestions = new Set();
        this.askedQuestionData = [];
        this.uncertaintyMap = {};
        this.currentLevel = this.config.startLevel;

        for (let level = 0; level <= this.config.maxLevel; level++) {
            this.levelStats[level] = { correct: 0, total: 0, accuracy: 0 };
            this.levelAskedCells[level] = [];
            this.levelResponses[level] = {};
        }
    }
}
