# Density-First Optimization Implementation

## Date
2025-11-16

## Problem
Current algorithm maximizes area → 320 empty cells (20%) with poor content quality

## Solution
Density-first optimization: maximize minimum articles per cell

## Changes to scripts/find_optimal_coverage_rectangle.py

### 1. Add Density Calculation Function (after line 182)
```python
def calculate_density_metrics(
    rectangle: Rectangle,
    all_coords: np.ndarray,
    grid_size: int = 40
) -> Dict:
    """Calculate per-cell article counts and density statistics"""
```

### 2. Add Density Scoring Function (after density_metrics)
```python
def score_rectangle_by_density(result: CoverageResult, density_metrics: Dict) -> float:
    """Score rectangle by density quality, not area"""
```

### 3. Update Parameters (lines 187-188)
- min_coverage: 80.0 → 95.0
- Add max_distance_cell_widths parameter with default 3.0

### 4. Change Ranking Logic (line ~282)
- OLD: `sorted(valid_results, key=lambda r: r.area, reverse=True)[:10]`
- NEW: Rank by density score instead of area

### 5. Enhanced Reporting
Add density metrics to final output

## Expected Improvements
- Empty cells: 320 → 0-80 (20% → 0-5%)
- Mean distance: 4.86 → 0.5-1.5 cell-widths
- Min articles/cell: 0 → 5-20
- Total articles: 216,922 → 50,000-120,000 (better distributed)
