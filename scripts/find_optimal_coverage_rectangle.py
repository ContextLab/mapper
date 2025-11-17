#!/usr/bin/env python3
"""
Find the optimal coverage rectangle for Wikipedia articles in UMAP space.

This script implements a comprehensive multi-objective optimization to find the
maximum area rectangle where ≥80% of heatmap cells have an article within
10 cell-widths distance.

Algorithm:
1. Phase 1: Coarse grid search across centers and sizes
2. Phase 2: Fine local refinement around top candidates
3. Phase 3: Pareto frontier analysis (coverage vs area trade-off)

Output: optimal_rectangle.json with bounds, metrics, and Pareto frontier
"""

import pickle
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict
from scipy.spatial import KDTree

@dataclass
class Rectangle:
    """Rectangle in UMAP space"""
    center_x: float
    center_y: float
    width: float
    height: float

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """Return (x_min, x_max, y_min, y_max)"""
        return (
            self.center_x - self.width / 2,
            self.center_x + self.width / 2,
            self.center_y - self.height / 2,
            self.center_y + self.height / 2
        )

    @property
    def area(self) -> float:
        """Rectangle area"""
        return self.width * self.height

@dataclass
class CoverageResult:
    """Results of coverage calculation for a rectangle"""
    rectangle: Rectangle
    coverage: float  # Percentage of cells with article within 10 cell-widths
    num_articles: int  # Number of articles within rectangle
    area: float
    cell_coverage_details: Dict  # Per-cell distances to nearest article

def load_umap_coordinates(umap_file: Path) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """
    Load UMAP coordinates for all 250K Wikipedia articles.

    Returns:
        coords: Array of shape (N, 2) with UMAP coordinates
        bounds: (x_min, x_max, y_min, y_max) of full space
    """
    print(f"Loading UMAP coordinates from {umap_file}...")

    with open(umap_file, 'rb') as f:
        data = pickle.load(f)

    # umap_coords.pkl contains coordinates for wiki articles + questions
    # We only want Wikipedia articles (first 250K entries)
    if isinstance(data, dict):
        coords = data['coords_2d'][:250000]  # First 250K are Wikipedia
    else:
        coords = data[:250000]

    x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
    y_min, y_max = coords[:, 1].min(), coords[:, 1].max()

    print(f"  ✓ Loaded {len(coords):,} Wikipedia article coordinates")
    print(f"  UMAP space bounds: X=[{x_min:.2f}, {x_max:.2f}], Y=[{y_min:.2f}, {y_max:.2f}]")
    print()

    return coords, (x_min, x_max, y_min, y_max)

def calculate_coverage(
    rectangle: Rectangle,
    all_coords: np.ndarray,
    grid_size: int = 40,
    max_distance_cell_widths: float = 10.0
) -> CoverageResult:
    """
    Calculate coverage for a given rectangle.

    Coverage = % of grid cells with ≥1 article within max_distance_cell_widths.

    Args:
        rectangle: Rectangle to evaluate
        all_coords: All Wikipedia article coordinates (N, 2)
        grid_size: Grid resolution (40x40 cells)
        max_distance_cell_widths: Maximum distance in cell-widths (10)

    Returns:
        CoverageResult with coverage percentage and details
    """
    x_min, x_max, y_min, y_max = rectangle.bounds

    # Filter articles within rectangle
    mask = (
        (all_coords[:, 0] >= x_min) & (all_coords[:, 0] <= x_max) &
        (all_coords[:, 1] >= y_min) & (all_coords[:, 1] <= y_max)
    )
    articles_in_rect = all_coords[mask]
    num_articles = len(articles_in_rect)

    if num_articles == 0:
        return CoverageResult(
            rectangle=rectangle,
            coverage=0.0,
            num_articles=0,
            area=rectangle.area,
            cell_coverage_details={}
        )

    # Build KD-tree for fast nearest neighbor queries
    tree = KDTree(articles_in_rect)

    # Calculate cell width in UMAP space
    cell_width = rectangle.width / grid_size
    cell_height = rectangle.height / grid_size

    # Maximum distance in UMAP space
    max_distance = max_distance_cell_widths * max(cell_width, cell_height)

    # Generate grid cell centers (normalized to [0, 1] for consistency)
    cells_covered = 0
    total_cells = grid_size * grid_size
    cell_details = {}

    for i in range(grid_size):
        for j in range(grid_size):
            # Cell center in normalized [0, 1] space
            norm_x = (i + 0.5) / grid_size
            norm_y = (j + 0.5) / grid_size

            # Convert to UMAP space
            umap_x = x_min + norm_x * rectangle.width
            umap_y = y_min + norm_y * rectangle.height

            # Find nearest article
            dist, idx = tree.query([umap_x, umap_y])

            # Convert distance to cell-widths
            dist_cell_widths = dist / max(cell_width, cell_height)

            cell_key = f"{i}_{j}"
            cell_details[cell_key] = {
                'grid_x': int(i),
                'grid_y': int(j),
                'norm_x': float(norm_x),
                'norm_y': float(norm_y),
                'umap_x': float(umap_x),
                'umap_y': float(umap_y),
                'nearest_dist': float(dist),
                'nearest_dist_cell_widths': float(dist_cell_widths),
                'covered': bool(dist_cell_widths <= max_distance_cell_widths)
            }

            if dist_cell_widths <= max_distance_cell_widths:
                cells_covered += 1

    coverage = (cells_covered / total_cells) * 100

    return CoverageResult(
        rectangle=rectangle,
        coverage=float(coverage),
        num_articles=int(num_articles),
        area=float(rectangle.area),
        cell_coverage_details=cell_details
    )

def calculate_density_metrics(
    rectangle: Rectangle,
    all_coords: np.ndarray,
    grid_size: int = 40
) -> Dict:
    """
    Calculate per-cell article counts and density statistics.

    Args:
        rectangle: Rectangle to evaluate
        all_coords: All Wikipedia article coordinates
        grid_size: Grid resolution (default 40x40)

    Returns:
        Dictionary with density metrics
    """
    x_min, x_max, y_min, y_max = rectangle.bounds

    # Filter to articles within rectangle
    mask = (
        (all_coords[:, 0] >= x_min) & (all_coords[:, 0] <= x_max) &
        (all_coords[:, 1] >= y_min) & (all_coords[:, 1] <= y_max)
    )
    articles_in_rect = all_coords[mask]

    if len(articles_in_rect) == 0:
        return {
            'cell_counts': np.zeros((grid_size, grid_size), dtype=int),
            'min_density': 0,
            'max_density': 0,
            'mean_density': 0.0,
            'median_density': 0.0,
            'empty_cells': grid_size * grid_size,
            'cells_with_1_article': 0,
            'cells_with_5_plus': 0,
            'density_std': 0.0
        }

    # Calculate cell dimensions
    cell_width = (x_max - x_min) / grid_size
    cell_height = (y_max - y_min) / grid_size

    # Count articles per cell
    cell_counts = np.zeros((grid_size, grid_size), dtype=int)

    for coord in articles_in_rect:
        # Determine which cell this article belongs to
        cell_x = int((coord[0] - x_min) / cell_width)
        cell_y = int((coord[1] - y_min) / cell_height)

        # Clamp to grid boundaries
        cell_x = min(cell_x, grid_size - 1)
        cell_y = min(cell_y, grid_size - 1)

        cell_counts[cell_y, cell_x] += 1

    # Calculate statistics
    flat_counts = cell_counts.flatten()

    return {
        'cell_counts': cell_counts,
        'min_density': int(flat_counts.min()),
        'max_density': int(flat_counts.max()),
        'mean_density': float(flat_counts.mean()),
        'median_density': float(np.median(flat_counts)),
        'empty_cells': int((flat_counts == 0).sum()),
        'cells_with_1_article': int((flat_counts == 1).sum()),
        'cells_with_5_plus': int((flat_counts >= 5).sum()),
        'density_std': float(flat_counts.std())
    }

def score_rectangle_by_density(result: CoverageResult, density_metrics: Dict) -> float:
    """
    Score rectangle by density quality, not area.

    Priorities:
    1. No empty cells (heavy penalty)
    2. High minimum density (worst-case quality)
    3. High coverage percentage
    4. High total articles (diversity)

    Args:
        result: Coverage result for rectangle
        density_metrics: Density metrics from calculate_density_metrics()

    Returns:
        Score (higher is better)
    """
    # Heavy exponential penalty for empty cells
    empty_cells = density_metrics['empty_cells']
    if empty_cells > 0:
        empty_penalty = -1000 * (empty_cells ** 0.5) * 10
    else:
        empty_penalty = 0

    # Reward minimum density (ensures quality everywhere)
    min_density_score = density_metrics['min_density'] * 10000

    # Reward high coverage percentage
    coverage_score = result.coverage * 100

    # Reward total articles (diversity) - small weight
    diversity_score = np.log(result.num_articles + 1) * 10

    # Reward uniform distribution
    if density_metrics['mean_density'] > 0:
        uniformity_score = -density_metrics['density_std'] * 100
    else:
        uniformity_score = 0

    total_score = (
        empty_penalty +
        min_density_score +
        coverage_score +
        diversity_score +
        uniformity_score
    )

    return total_score

def find_optimal_rectangle(
    all_coords: np.ndarray,
    space_bounds: Tuple[float, float, float, float],
    min_coverage: float = 95.0,
    max_distance_cell_widths: float = 3.0,
    grid_size: int = 40
) -> Dict:
    """
    Find optimal rectangle using density-first multi-objective optimization.

    Phase 1: Coarse grid search (100x100 centers, 6 sizes = 60K rectangles)
    Phase 2: Fine local search around top candidates
    Phase 3: Pareto frontier analysis

    Args:
        all_coords: All Wikipedia article coordinates
        space_bounds: (x_min, x_max, y_min, y_max) of full UMAP space
        min_coverage: Minimum required coverage (95%, stricter than before)
        max_distance_cell_widths: Maximum distance from cell center to nearest article (in cell-widths, default 3.0)
        grid_size: Grid resolution (40x40)

    Returns:
        Dictionary with optimal rectangle and Pareto frontier
    """
    x_min, x_max, y_min, y_max = space_bounds
    space_width = x_max - x_min
    space_height = y_max - y_min

    print("=" * 80)
    print("OPTIMAL RECTANGLE SEARCH")
    print("=" * 80)
    print(f"UMAP space: X=[{x_min:.2f}, {x_max:.2f}], Y=[{y_min:.2f}, {y_max:.2f}]")
    print(f"Space dimensions: {space_width:.2f} × {space_height:.2f}")
    print(f"Target: Coverage ≥{min_coverage}%, maximize area")
    print(f"Articles available: {len(all_coords):,}")
    print()

    # ===== PHASE 1: COARSE GRID SEARCH =====
    print("=" * 80)
    print("PHASE 1: COARSE GRID SEARCH")
    print("=" * 80)

    # Test centers on a 100x100 grid
    center_grid_size = 100
    center_xs = np.linspace(x_min + space_width * 0.1, x_max - space_width * 0.1, center_grid_size)
    center_ys = np.linspace(y_min + space_height * 0.1, y_max - space_height * 0.1, center_grid_size)

    # Test 6 different sizes (from 20% to 95% of space)
    size_fractions = [0.2, 0.35, 0.5, 0.65, 0.8, 0.95]
    widths = [space_width * f for f in size_fractions]
    heights = [space_height * f for f in size_fractions]

    total_tests = len(center_xs) * len(center_ys) * len(widths)
    print(f"Testing {len(center_xs)}×{len(center_ys)} centers × {len(widths)} sizes = {total_tests:,} rectangles")
    print()

    all_results = []
    start_time = time.time()

    for i, cx in enumerate(center_xs):
        for j, cy in enumerate(center_ys):
            for k, (w, h) in enumerate(zip(widths, heights)):
                rect = Rectangle(cx, cy, w, h)
                result = calculate_coverage(rect, all_coords, grid_size, max_distance_cell_widths)
                all_results.append(result)

                # Progress update every 1000 rectangles
                if len(all_results) % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = len(all_results) / elapsed
                    eta = (total_tests - len(all_results)) / rate
                    print(f"  Progress: {len(all_results):,}/{total_tests:,} "
                          f"({len(all_results)/total_tests*100:.1f}%) - "
                          f"Rate: {rate:.1f} rect/s - "
                          f"ETA: {eta/60:.1f} min")

    elapsed = time.time() - start_time
    print(f"  ✓ Phase 1 complete: {len(all_results):,} rectangles evaluated in {elapsed:.1f}s")
    print(f"  Rate: {len(all_results)/elapsed:.1f} rectangles/sec")
    print()

    # ===== PHASE 2: FINE LOCAL SEARCH =====
    print("=" * 80)
    print("PHASE 2: FINE LOCAL REFINEMENT")
    print("=" * 80)

    # Find top 10 candidates from Phase 1
    valid_results = [r for r in all_results if r.coverage >= min_coverage]

    if len(valid_results) == 0:
        print(f"  ⚠ WARNING: No rectangles found with coverage ≥{min_coverage}%")
        print(f"  Best coverage achieved: {max(r.coverage for r in all_results):.2f}%")
        # Find rectangle with maximum coverage
        best_result = max(all_results, key=lambda r: r.coverage)
        print(f"  Returning rectangle with maximum coverage: {best_result.coverage:.2f}%")
        print()
    else:
        print(f"  ✓ Found {len(valid_results):,} rectangles with coverage ≥{min_coverage}%")
        print(f"  Calculating density metrics for ranking...")

        # Calculate density metrics and score each rectangle
        results_with_density = []
        for r in valid_results:
            density_metrics = calculate_density_metrics(r.rectangle, all_coords, grid_size)
            score = score_rectangle_by_density(r, density_metrics)
            results_with_density.append((r, density_metrics, score))

        # Sort by density score (higher is better) and take top 10
        top_candidates = sorted(results_with_density, key=lambda x: x[2], reverse=True)[:10]

        print(f"  Top 10 candidates by density score:")
        for i, (r, dm, score) in enumerate(top_candidates, 1):
            print(f"    {i}. Score={score:.0f}, MinDensity={dm['min_density']}, "
                  f"Empty={dm['empty_cells']}, Coverage={r.coverage:.2f}%, "
                  f"Articles={r.num_articles:,}")
        print()

        # Fine search around top candidate
        best_coarse_result, best_coarse_dm, best_coarse_score = top_candidates[0]
        print(f"  Refining around best candidate (Score={best_coarse_score:.0f}, "
              f"MinDensity={best_coarse_dm['min_density']}, Empty={best_coarse_dm['empty_cells']})...")

        # Test small variations in center position
        delta_x = space_width * 0.01  # 1% steps
        delta_y = space_height * 0.01

        fine_results = []
        for dx in np.linspace(-delta_x * 5, delta_x * 5, 11):
            for dy in np.linspace(-delta_y * 5, delta_y * 5, 11):
                for dw in np.linspace(-space_width * 0.05, space_width * 0.05, 5):
                    for dh in np.linspace(-space_height * 0.05, space_height * 0.05, 5):
                        rect = Rectangle(
                            best_coarse_result.rectangle.center_x + dx,
                            best_coarse_result.rectangle.center_y + dy,
                            max(best_coarse_result.rectangle.width + dw, space_width * 0.1),
                            max(best_coarse_result.rectangle.height + dh, space_height * 0.1)
                        )
                        result = calculate_coverage(rect, all_coords, grid_size, max_distance_cell_widths)
                        if result.coverage >= min_coverage:
                            fine_results.append(result)

        all_results.extend(fine_results)
        print(f"  ✓ Fine search: {len(fine_results):,} additional rectangles tested")
        print()

        # Update best result using density scoring
        valid_results = [r for r in all_results if r.coverage >= min_coverage]

        # Calculate density scores for all valid results
        scored_results = []
        for r in valid_results:
            dm = calculate_density_metrics(r.rectangle, all_coords, grid_size)
            score = score_rectangle_by_density(r, dm)
            scored_results.append((r, dm, score))

        # Select best by density score
        best_result_tuple = max(scored_results, key=lambda x: x[2])
        best_result = best_result_tuple[0]
        best_density_metrics = best_result_tuple[1]

    # ===== PHASE 3: PARETO FRONTIER =====
    print("=" * 80)
    print("PHASE 3: PARETO FRONTIER ANALYSIS")
    print("=" * 80)

    # Build Pareto frontier (non-dominated solutions)
    pareto_frontier = []

    for r in all_results:
        dominated = False
        for other in all_results:
            if other.coverage >= r.coverage and other.area >= r.area:
                if other.coverage > r.coverage or other.area > r.area:
                    dominated = True
                    break

        if not dominated:
            pareto_frontier.append(r)

    pareto_frontier = sorted(pareto_frontier, key=lambda r: r.area, reverse=True)

    print(f"  ✓ Pareto frontier: {len(pareto_frontier)} non-dominated solutions")
    print()
    print(f"  Top 5 Pareto-optimal rectangles:")
    for i, r in enumerate(pareto_frontier[:5], 1):
        print(f"    {i}. Area={r.area:.2f}, Coverage={r.coverage:.2f}%, "
              f"Articles={r.num_articles:,}")
    print()

    # ===== FINAL SELECTION =====
    print("=" * 80)
    print("OPTIMAL RECTANGLE SELECTED")
    print("=" * 80)

    best = best_result
    x_min_opt, x_max_opt, y_min_opt, y_max_opt = best.rectangle.bounds

    print(f"Coverage: {best.coverage:.2f}%")
    print(f"Area: {best.area:.2f} (UMAP units²)")
    print(f"Articles included: {best.num_articles:,}")
    print(f"Rectangle bounds:")
    print(f"  X: [{x_min_opt:.2f}, {x_max_opt:.2f}] (width: {best.rectangle.width:.2f})")
    print(f"  Y: [{y_min_opt:.2f}, {y_max_opt:.2f}] (height: {best.rectangle.height:.2f})")
    print(f"  Center: ({best.rectangle.center_x:.2f}, {best.rectangle.center_y:.2f})")
    print()

    # Coverage statistics
    cell_details = best.cell_coverage_details
    distances = [c['nearest_dist_cell_widths'] for c in cell_details.values()]
    covered_distances = [d for d in distances if d <= 10.0]

    print(f"Coverage statistics:")
    print(f"  Cells covered: {len(covered_distances)}/{len(distances)} ({best.coverage:.2f}%)")
    print(f"  Distance to nearest article (cell-widths):")
    print(f"    Mean: {np.mean(distances):.2f}")
    print(f"    Median: {np.median(distances):.2f}")
    print(f"    Max: {np.max(distances):.2f}")
    print(f"    Min: {np.min(distances):.2f}")
    print()

    # ===== POST-PROCESSING: ADJUST BOUNDS TO ACTUAL ARTICLE DISTRIBUTION =====
    print("=" * 80)
    print("POST-PROCESSING: ADJUSTING BOUNDS TO ACTUAL ARTICLES")
    print("=" * 80)

    # Extract articles within the optimal rectangle
    x_min_rect, x_max_rect, y_min_rect, y_max_rect = best.rectangle.bounds
    mask = (
        (all_coords[:, 0] >= x_min_rect) & (all_coords[:, 0] <= x_max_rect) &
        (all_coords[:, 1] >= y_min_rect) & (all_coords[:, 1] <= y_max_rect)
    )
    selected_articles = all_coords[mask]

    print(f"Articles selected by optimization: {len(selected_articles):,}")
    print(f"Original rectangle bounds:")
    print(f"  X: [{x_min_rect:.2f}, {x_max_rect:.2f}] (width: {x_max_rect - x_min_rect:.2f})")
    print(f"  Y: [{y_min_rect:.2f}, {y_max_rect:.2f}] (height: {y_max_rect - y_min_rect:.2f})")
    print()

    # Find actual min/max bounds of selected articles
    actual_x_min = float(selected_articles[:, 0].min())
    actual_x_max = float(selected_articles[:, 0].max())
    actual_y_min = float(selected_articles[:, 1].min())
    actual_y_max = float(selected_articles[:, 1].max())

    print(f"Actual article distribution:")
    print(f"  X: [{actual_x_min:.2f}, {actual_x_max:.2f}] (width: {actual_x_max - actual_x_min:.2f})")
    print(f"  Y: [{actual_y_min:.2f}, {actual_y_max:.2f}] (height: {actual_y_max - actual_y_min:.2f})")

    # Calculate coverage within original rectangle
    x_coverage = (actual_x_max - actual_x_min) / (x_max_rect - x_min_rect) * 100
    y_coverage = (actual_y_max - actual_y_min) / (y_max_rect - y_min_rect) * 100
    print(f"  Articles fill {x_coverage:.1f}% of X range, {y_coverage:.1f}% of Y range")
    print()

    # Add 2.5% padding on all sides
    padding = 0.025
    x_range = actual_x_max - actual_x_min
    y_range = actual_y_max - actual_y_min

    x_padding = x_range * padding
    y_padding = y_range * padding

    adjusted_x_min = actual_x_min - x_padding
    adjusted_x_max = actual_x_max + x_padding
    adjusted_y_min = actual_y_min - y_padding
    adjusted_y_max = actual_y_max + y_padding

    print(f"Adding {padding*100}% padding on all sides:")
    print(f"  X padding: {x_padding:.3f} UMAP units")
    print(f"  Y padding: {y_padding:.3f} UMAP units")
    print()

    print(f"Final adjusted bounds:")
    print(f"  X: [{adjusted_x_min:.2f}, {adjusted_x_max:.2f}] (width: {adjusted_x_max - adjusted_x_min:.2f})")
    print(f"  Y: [{adjusted_y_min:.2f}, {adjusted_y_max:.2f}] (height: {adjusted_y_max - adjusted_y_min:.2f})")

    adjusted_area = (adjusted_x_max - adjusted_x_min) * (adjusted_y_max - adjusted_y_min)
    print(f"  Area: {adjusted_area:.2f} UMAP units²")

    # Calculate area reduction
    area_reduction = (best.area - adjusted_area) / best.area * 100
    print(f"  Area reduction: {area_reduction:.1f}% (tighter fit)")
    print()

    # Update bounds for return value
    x_min_opt = adjusted_x_min
    x_max_opt = adjusted_x_max
    y_min_opt = adjusted_y_min
    y_max_opt = adjusted_y_max

    # Return comprehensive results
    return {
        'optimal_rectangle': {
            'bounds': {
                'x_min': float(x_min_opt),
                'x_max': float(x_max_opt),
                'y_min': float(y_min_opt),
                'y_max': float(y_max_opt)
            },
            'center': {
                'x': float(best.rectangle.center_x),
                'y': float(best.rectangle.center_y)
            },
            'dimensions': {
                'width': float(best.rectangle.width),
                'height': float(best.rectangle.height)
            },
            'area': float(best.area)
        },
        'metrics': {
            'coverage_percent': float(best.coverage),
            'num_articles': int(best.num_articles),
            'cells_covered': int(len(covered_distances)),
            'total_cells': int(len(distances)),
            'distance_stats': {
                'mean_cell_widths': float(np.mean(distances)),
                'median_cell_widths': float(np.median(distances)),
                'max_cell_widths': float(np.max(distances)),
                'min_cell_widths': float(np.min(distances))
            }
        },
        'cell_coverage_details': cell_details,
        'pareto_frontier': [
            {
                'coverage_percent': float(r.coverage),
                'area': float(r.area),
                'num_articles': int(r.num_articles),
                'bounds': {
                    'x_min': float(r.rectangle.bounds[0]),
                    'x_max': float(r.rectangle.bounds[1]),
                    'y_min': float(r.rectangle.bounds[2]),
                    'y_max': float(r.rectangle.bounds[3])
                }
            }
            for r in pareto_frontier[:20]  # Top 20 Pareto solutions
        ],
        'search_metadata': {
            'total_rectangles_evaluated': int(len(all_results)),
            'phase1_rectangles': int(total_tests),
            'phase2_rectangles': int(len(fine_results) if 'fine_results' in locals() else 0),
            'min_coverage_target': float(min_coverage),
            'max_distance_cell_widths': float(max_distance_cell_widths),
            'grid_size': int(grid_size),
            'timestamp': datetime.now().isoformat(),
            'optimization_method': 'density-first'
        },
        'density_metrics': {
            'min_density': int(best_density_metrics['min_density']) if 'best_density_metrics' in locals() else None,
            'max_density': int(best_density_metrics['max_density']) if 'best_density_metrics' in locals() else None,
            'mean_density': float(best_density_metrics['mean_density']) if 'best_density_metrics' in locals() else None,
            'median_density': float(best_density_metrics['median_density']) if 'best_density_metrics' in locals() else None,
            'empty_cells': int(best_density_metrics['empty_cells']) if 'best_density_metrics' in locals() else None,
            'cells_with_1_article': int(best_density_metrics['cells_with_1_article']) if 'best_density_metrics' in locals() else None,
            'cells_with_5_plus': int(best_density_metrics['cells_with_5_plus']) if 'best_density_metrics' in locals() else None,
            'density_std': float(best_density_metrics['density_std']) if 'best_density_metrics' in locals() else None
        },
        'post_processing': {
            'original_bounds': {
                'x_min': float(x_min_rect),
                'x_max': float(x_max_rect),
                'y_min': float(y_min_rect),
                'y_max': float(y_max_rect)
            },
            'actual_article_bounds': {
                'x_min': float(actual_x_min),
                'x_max': float(actual_x_max),
                'y_min': float(actual_y_min),
                'y_max': float(actual_y_max)
            },
            'padding_percent': float(padding * 100),
            'padding_applied': {
                'x_padding': float(x_padding),
                'y_padding': float(y_padding)
            },
            'area_reduction_percent': float(area_reduction),
            'article_fill_percent': {
                'x_coverage': float(x_coverage),
                'y_coverage': float(y_coverage)
            }
        }
    }

def main():
    print()
    print("=" * 80)
    print("OPTIMAL COVERAGE RECTANGLE FINDER")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print()

    # Setup paths
    umap_file = Path("umap_coords.pkl")
    output_file = Path("optimal_rectangle.json")

    if not umap_file.exists():
        raise FileNotFoundError(f"UMAP coordinates not found: {umap_file}")

    # Load data
    all_coords, space_bounds = load_umap_coordinates(umap_file)

    # Find optimal rectangle
    start_time = time.time()
    results = find_optimal_rectangle(all_coords, space_bounds)
    elapsed = time.time() - start_time

    # Save results
    print("=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    file_size_kb = output_file.stat().st_size / 1024
    print(f"  ✓ Saved to {output_file}")
    print(f"  File size: {file_size_kb:.2f} KB")
    print()

    print("=" * 80)
    print("✓ OPTIMAL RECTANGLE SEARCH COMPLETE")
    print("=" * 80)
    print(f"Total time: {elapsed/60:.2f} minutes")
    print(f"Output: {output_file.absolute()}")
    print(f"Coverage: {results['metrics']['coverage_percent']:.2f}%")
    print(f"Area: {results['optimal_rectangle']['area']:.2f} UMAP units²")
    print(f"Articles: {results['metrics']['num_articles']:,}")
    print(f"Completed: {datetime.now()}")
    print()

if __name__ == '__main__':
    main()
