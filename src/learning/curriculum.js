/** Curriculum weighting and domain centrality scoring. */

import { sigmoid } from '../utils/math.js';

/**
 * Compute curriculum weight for landmark vs. niche question selection.
 *
 * Returns a weight in [0, 1] controlling how much to prioritize landmark (central)
 * questions over niche (peripheral) questions.
 *
 * - 1.0 = fully landmark-heavy (ask central questions first)
 * - 0.0 = fully niche-heavy (ask peripheral questions)
 *
 * Uses a sigmoid transition centered at 30% coverage:
 * - At 0% coverage → weight ≈ 0.95 (almost all landmark)
 * - At 30% coverage → weight = 0.5 (mixed)
 * - At 60% coverage → weight ≈ 0.05 (almost all niche)
 *
 * @param {number} answeredCount - Number of questions answered (unused, for future extensions)
 * @param {number} coveragePercent - Coverage percentage (0-100)
 * @returns {number} Weight in [0, 1]
 */
export function getWeight(answeredCount, coveragePercent) {
  // Convert percentage to 0-1 range
  const coverage = coveragePercent / 100;
  
  // Sigmoid transition centered at 30% coverage
  // weight = 1.0 - sigmoid((coverage - 0.3) * 10)
  const weight = 1.0 - sigmoid((coverage - 0.3) * 10);
  
  return weight;
}

/**
 * Compute centrality scores for all grid cells in a domain.
 *
 * Centrality = article density in each cell relative to the densest cell.
 * High centrality = landmark/well-known topics (dense with articles).
 * Low centrality = niche/peripheral topics (sparse articles).
 *
 * @param {Object} domainBundle - Domain bundle containing {domain, articles, ...}
 * @param {Object} domainBundle.domain - Domain metadata with grid_size and region
 * @param {number} domainBundle.domain.grid_size - Grid size (e.g., 20 or 39)
 * @param {Object} domainBundle.domain.region - Bounding box {x_min, x_max, y_min, y_max}
 * @param {Array} domainBundle.articles - Array of articles with {x, y, ...}
 * @returns {Map<string, number>} Map from "gx,gy" cell keys to centrality scores [0, 1]
 */
export function getCentrality(domainBundle) {
  const { domain, articles } = domainBundle;
  const { grid_size: gridSize, region } = domain;
  
  // Count articles per cell
  const cellCounts = new Map();
  
  for (const article of articles) {
    // Map article (x, y) to grid cell (gx, gy)
    const gx = Math.floor(
      ((article.x - region.x_min) / (region.x_max - region.x_min)) * gridSize
    );
    const gy = Math.floor(
      ((article.y - region.y_min) / (region.y_max - region.y_min)) * gridSize
    );
    
    // Clamp to [0, gridSize-1]
    const gxClamped = Math.max(0, Math.min(gridSize - 1, gx));
    const gyClamped = Math.max(0, Math.min(gridSize - 1, gy));
    
    const key = `${gxClamped},${gyClamped}`;
    cellCounts.set(key, (cellCounts.get(key) || 0) + 1);
  }
  
  // Find maximum count
  let maxCount = 0;
  for (const count of cellCounts.values()) {
    if (count > maxCount) {
      maxCount = count;
    }
  }
  
  // Compute centrality = count / maxCount
  const centralityMap = new Map();
  
  if (maxCount === 0) {
    // No articles → all cells have centrality 0
    return centralityMap;
  }
  
  for (const [key, count] of cellCounts.entries()) {
    centralityMap.set(key, count / maxCount);
  }
  
  // Cells not in cellCounts have centrality 0 (implicit)
  return centralityMap;
}

/**
 * Compute centrality score for a specific question.
 *
 * Maps the question's (x, y) coordinates to its grid cell and returns
 * the centrality score for that cell.
 *
 * @param {Object} question - Question object with {x, y, ...}
 * @param {Map<string, number>} centralityMap - Map from "gx,gy" to centrality [0, 1]
 * @param {number} gridSize - Grid size (e.g., 20 or 39)
 * @param {Object} region - Bounding box {x_min, x_max, y_min, y_max}
 * @returns {number} Centrality score [0, 1]
 */
export function computeCentralityForQuestion(question, centralityMap, gridSize, region) {
  // Map question (x, y) to grid cell (gx, gy)
  const gx = Math.floor(
    ((question.x - region.x_min) / (region.x_max - region.x_min)) * gridSize
  );
  const gy = Math.floor(
    ((question.y - region.y_min) / (region.y_max - region.y_min)) * gridSize
  );
  
  // Clamp to [0, gridSize-1]
  const gxClamped = Math.max(0, Math.min(gridSize - 1, gx));
  const gyClamped = Math.max(0, Math.min(gridSize - 1, gy));
  
  const key = `${gxClamped},${gyClamped}`;
  
  // Return centrality (default 0 if cell not in map)
  return centralityMap.get(key) || 0;
}
