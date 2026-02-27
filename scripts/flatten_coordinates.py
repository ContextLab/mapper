#!/usr/bin/env python3
"""
Flatten UMAP coordinates via approximate optimal transport.

Addresses extreme density imbalance in UMAP embedding space:
  - 80.3% of cells (50x50 grid) are empty
  - 88.9% of articles crammed into 10% of cells

Algorithm:
  1. Subsample M representative points via farthest-point sampling
  2. Generate M quasi-uniform target points (Halton sequence)
  3. Solve exact Hungarian assignment on M×M cost matrix
  4. Compute displacement vectors for matched pairs
  5. Interpolate displacement field to all N points via k-NN weighted average
  6. Apply with mixing parameter mu ∈ [0,1]
  7. Re-normalize to [0,1] with margin
  8. Apply same displacement field to question coordinates

Usage:
  python scripts/flatten_coordinates.py --mu 0.75
  python scripts/flatten_coordinates.py --mu 0.75 --subsample 5000 --knn 8
"""

import argparse
import pickle
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist


# ---------------------------------------------------------------------------
# Farthest-point sampling
# ---------------------------------------------------------------------------


def farthest_point_sampling(points: np.ndarray, m: int, seed: int = 42) -> np.ndarray:
    """
    Select m representative points via farthest-point (greedy) sampling.

    Starts from a random seed point, iteratively picks the point
    farthest from all previously selected points. O(N*M) time.

    Returns array of indices into `points`.
    """
    n = len(points)
    if m >= n:
        return np.arange(n)

    rng = np.random.default_rng(seed)
    selected = np.empty(m, dtype=np.int64)
    selected[0] = rng.integers(n)

    # min_dists[i] = min distance from points[i] to any selected point
    min_dists = np.full(n, np.inf, dtype=np.float64)

    for i in range(m):
        # Update min distances with the newly added point
        new_pt = points[selected[i]]
        dists = np.sum((points - new_pt) ** 2, axis=1)  # squared euclidean
        np.minimum(min_dists, dists, out=min_dists)

        if i < m - 1:
            # Pick the point with maximum min-distance
            # Exclude already-selected points by setting their dist to -1
            min_dists[selected[: i + 1]] = -1
            selected[i + 1] = np.argmax(min_dists)
            # Restore for future iterations
            min_dists[selected[: i + 1]] = 0.0

        if (i + 1) % 1000 == 0 or i == m - 1:
            print(f"  Farthest-point sampling: {i + 1}/{m}")

    return selected


# ---------------------------------------------------------------------------
# Halton sequence for quasi-uniform target generation
# ---------------------------------------------------------------------------


def halton_sequence(n: int, base: int) -> np.ndarray:
    """Generate n points of the Halton sequence for a given base."""
    result = np.zeros(n)
    for i in range(n):
        f = 1.0
        val = 0.0
        idx = i + 1  # 1-indexed to avoid 0
        while idx > 0:
            f /= base
            val += f * (idx % base)
            idx //= base
        result[i] = val
    return result


def generate_halton_targets(m: int, margin: float = 0.02) -> np.ndarray:
    """
    Generate m quasi-uniform 2D target points using Halton sequence.

    Points are placed in [margin, 1-margin]^2 to avoid edge artifacts.
    Halton sequences with bases 2 and 3 provide good 2D coverage
    with low discrepancy (more uniform than random, less structured than grid).
    """
    x = halton_sequence(m, base=2)
    y = halton_sequence(m, base=3)
    targets = np.column_stack([x, y])

    # Scale to [margin, 1-margin]
    targets = targets * (1.0 - 2 * margin) + margin

    return targets


# ---------------------------------------------------------------------------
# Density statistics
# ---------------------------------------------------------------------------


def compute_density_stats(coords: np.ndarray, grid_size: int = 50) -> dict:
    """Compute density statistics on a grid."""
    # Clip to [0, 1] for binning
    clipped = np.clip(coords, 0, 1 - 1e-10)
    cell_x = np.clip((clipped[:, 0] * grid_size).astype(int), 0, grid_size - 1)
    cell_y = np.clip((clipped[:, 1] * grid_size).astype(int), 0, grid_size - 1)

    grid = np.zeros((grid_size, grid_size), dtype=int)
    for cx, cy in zip(cell_x, cell_y):
        grid[cx, cy] += 1

    total_cells = grid_size * grid_size
    empty_cells = np.sum(grid == 0)
    nonempty = grid[grid > 0]

    # What fraction of articles are in top 10% densest cells
    flat = grid.flatten()
    sorted_counts = np.sort(flat)[::-1]
    top_10pct_cells = max(1, total_cells // 10)
    articles_in_top10 = sorted_counts[:top_10pct_cells].sum()

    stats = {
        "total_points": len(coords),
        "grid_size": grid_size,
        "total_cells": total_cells,
        "empty_cells": empty_cells,
        "empty_pct": 100.0 * empty_cells / total_cells,
        "max_density": int(grid.max()),
        "median_density_nonzero": float(np.median(nonempty))
        if len(nonempty) > 0
        else 0,
        "mean_density_nonzero": float(np.mean(nonempty)) if len(nonempty) > 0 else 0,
        "std_density_nonzero": float(np.std(nonempty)) if len(nonempty) > 0 else 0,
        "articles_in_top10pct": int(articles_in_top10),
        "articles_in_top10pct_frac": float(articles_in_top10) / len(coords),
        "x_range": (float(coords[:, 0].min()), float(coords[:, 0].max())),
        "y_range": (float(coords[:, 1].min()), float(coords[:, 1].max())),
    }
    return stats


def print_density_comparison(before: dict, after: dict):
    """Print a comparison table of density stats."""
    print("\n" + "=" * 70)
    print("DENSITY COMPARISON (50x50 grid)")
    print("=" * 70)
    fmt = "  {:<35s} {:>12s}  {:>12s}"
    print(fmt.format("Metric", "BEFORE", "AFTER"))
    print("  " + "-" * 62)

    rows = [
        ("Empty cells", f"{before['empty_pct']:.1f}%", f"{after['empty_pct']:.1f}%"),
        (
            "Articles in top 10% cells",
            f"{before['articles_in_top10pct_frac']:.1%}",
            f"{after['articles_in_top10pct_frac']:.1%}",
        ),
        ("Max cell density", f"{before['max_density']}", f"{after['max_density']}"),
        (
            "Median density (non-zero)",
            f"{before['median_density_nonzero']:.0f}",
            f"{after['median_density_nonzero']:.0f}",
        ),
        (
            "Mean density (non-zero)",
            f"{before['mean_density_nonzero']:.0f}",
            f"{after['mean_density_nonzero']:.0f}",
        ),
        (
            "Std density (non-zero)",
            f"{before['std_density_nonzero']:.0f}",
            f"{after['std_density_nonzero']:.0f}",
        ),
        (
            "Std/Mean ratio",
            f"{before['std_density_nonzero'] / max(before['mean_density_nonzero'], 1):.2f}",
            f"{after['std_density_nonzero'] / max(after['mean_density_nonzero'], 1):.2f}",
        ),
        (
            "X range",
            f"[{before['x_range'][0]:.3f}, {before['x_range'][1]:.3f}]",
            f"[{after['x_range'][0]:.3f}, {after['x_range'][1]:.3f}]",
        ),
        (
            "Y range",
            f"[{before['y_range'][0]:.3f}, {before['y_range'][1]:.3f}]",
            f"[{after['y_range'][0]:.3f}, {after['y_range'][1]:.3f}]",
        ),
    ]
    for label, bval, aval in rows:
        print(fmt.format(label, bval, aval))
    print("=" * 70)


# ---------------------------------------------------------------------------
# Semantic coherence check
# ---------------------------------------------------------------------------


def check_semantic_coherence(
    original: np.ndarray,
    flattened: np.ndarray,
    k: int = 10,
    sample_size: int = 5000,
    seed: int = 42,
):
    """
    Check that local neighborhoods are preserved after flattening.

    For a sample of points, compute k-nearest neighbors in both original
    and flattened spaces. Report mean overlap (Jaccard-like metric).
    """
    rng = np.random.default_rng(seed)
    n = len(original)
    sample_idx = rng.choice(n, size=min(sample_size, n), replace=False)

    tree_orig = cKDTree(original)
    tree_flat = cKDTree(flattened)

    overlaps = []
    for idx in sample_idx:
        _, nn_orig = tree_orig.query(original[idx], k=k + 1)  # +1 for self
        _, nn_flat = tree_flat.query(flattened[idx], k=k + 1)

        set_orig = set(nn_orig[1:])  # exclude self
        set_flat = set(nn_flat[1:])
        overlap = len(set_orig & set_flat) / k
        overlaps.append(overlap)

    mean_overlap = np.mean(overlaps)
    print(
        f"\n  Semantic coherence (k={k}-NN overlap, {len(sample_idx)} samples): {mean_overlap:.3f}"
    )
    print(f"  (1.0 = perfect preservation, 0.0 = completely reshuffled)")

    if mean_overlap < 0.3:
        print("  WARNING: Low coherence — mu may be too high. Consider reducing.")
    elif mean_overlap > 0.8:
        print(
            "  NOTE: Very high coherence — density may not be sufficiently flattened."
        )
    else:
        print("  OK: Reasonable balance between flattening and semantic structure.")

    return mean_overlap


# ---------------------------------------------------------------------------
# Patch-based flattening (per-cluster Hungarian)
# ---------------------------------------------------------------------------


def flatten_coordinates_patched(
    article_coords: np.ndarray,
    question_coords: np.ndarray,
    mu: float = 0.75,
    n_clusters: int = 100,
    max_cluster_size: int = 2000,
    knn_k: int = 8,
    margin: float = 0.02,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Patch-based optimal transport: K-means clustering + per-cluster Hungarian.

    Unlike the subsample method, this gives EVERY article point its own unique
    uniform target via exact Hungarian assignment within clusters. Questions
    use k-NN interpolation from article displacement vectors.

    Auto-increases K if any cluster exceeds max_cluster_size to keep
    per-cluster Hungarian tractable (O(n³) is expensive above ~2000 points).
    """
    from sklearn.cluster import MiniBatchKMeans
    from scipy.stats.qmc import Halton

    N = len(article_coords)
    K = n_clusters

    print(f"\n{'=' * 70}")
    print(f"PATCH-BASED COORDINATE FLATTENING")
    print(f"{'=' * 70}")
    print(f"  Articles:   {N:,}")
    print(f"  Questions:  {len(question_coords):,}")
    print(f"  mu:         {mu}")
    print(f"  Clusters:   {K} (max size: {max_cluster_size})")
    print(f"  k-NN:       {knn_k}")
    print()

    # ---- Step 1: K-means cluster original points ----
    # Auto-increase K until no cluster exceeds max_cluster_size
    print("Step 1/6: K-means clustering originals...")
    t0 = time.time()
    while True:
        kmeans = MiniBatchKMeans(
            n_clusters=K, random_state=seed, batch_size=10000, n_init=3
        )
        kmeans.fit(article_coords)
        orig_labels = kmeans.labels_
        centers = kmeans.cluster_centers_
        cluster_sizes = np.bincount(orig_labels, minlength=K)
        if cluster_sizes.max() <= max_cluster_size:
            break
        old_K = K
        K = int(K * 1.5)
        print(
            f"  K={old_K}: max cluster {cluster_sizes.max()} > {max_cluster_size}, "
            f"increasing to K={K}"
        )

    print(
        f"  Done in {time.time() - t0:.1f}s — K={K}, "
        f"sizes: min={cluster_sizes.min()}, max={cluster_sizes.max()}, "
        f"mean={cluster_sizes.mean():.0f}"
    )

    # ---- Step 2: Generate N uniform Halton targets ----
    print(f"\nStep 2/6: Generating {N:,} Halton target points...")
    t0 = time.time()
    sampler = Halton(d=2, scramble=True, seed=seed)
    targets = sampler.random(n=N)
    targets = targets * (1.0 - 2 * margin) + margin
    print(f"  Done in {time.time() - t0:.1f}s")

    # ---- Step 3: Assign targets to clusters (capacitated) ----
    # Each cluster must receive exactly cluster_sizes[k] target points
    print(f"\nStep 3/6: Capacitated target assignment to {K} clusters...")
    t0 = time.time()
    target_dists = cdist(targets, centers)
    cluster_ranking = np.argsort(target_dists, axis=1)

    target_labels = np.full(N, -1, dtype=int)
    cluster_remaining = cluster_sizes.copy()
    unassigned = np.arange(N)

    for round_idx in range(K):
        if len(unassigned) == 0:
            break
        preferred = cluster_ranking[unassigned, round_idx]

        newly_assigned = []
        for k in range(K):
            if cluster_remaining[k] == 0:
                continue
            wanting_k = unassigned[preferred == k]
            if len(wanting_k) == 0:
                continue
            if len(wanting_k) <= cluster_remaining[k]:
                target_labels[wanting_k] = k
                cluster_remaining[k] -= len(wanting_k)
                newly_assigned.extend(wanting_k.tolist())
            else:
                dists_to_k = target_dists[wanting_k, k]
                keep = np.argsort(dists_to_k)[: cluster_remaining[k]]
                target_labels[wanting_k[keep]] = k
                cluster_remaining[k] = 0
                newly_assigned.extend(wanting_k[keep].tolist())

        unassigned = np.where(target_labels == -1)[0]
        if (round_idx + 1) % 10 == 0:
            print(f"  Round {round_idx + 1}: {len(unassigned):,} unassigned")

    n_unassigned = np.sum(target_labels < 0)
    if n_unassigned > 0:
        print(f"  WARNING: {n_unassigned} targets still unassigned, using fallback")
        for idx in np.where(target_labels < 0)[0]:
            for k in cluster_ranking[idx]:
                if cluster_remaining[k] > 0:
                    target_labels[idx] = k
                    cluster_remaining[k] -= 1
                    break

    assigned_sizes = np.bincount(target_labels, minlength=K)
    assert np.array_equal(assigned_sizes, cluster_sizes), (
        "Target/original size mismatch"
    )
    print(f"  Done in {time.time() - t0:.1f}s — all targets assigned")

    # ---- Step 4: Hungarian within each cluster ----
    print(f"\nStep 4/6: Per-cluster Hungarian assignment ({K} clusters)...")
    t0 = time.time()
    displacements = np.zeros_like(article_coords)
    total_cost = 0.0

    sorted_clusters = np.argsort(cluster_sizes)[::-1]
    for progress, k in enumerate(sorted_clusters):
        orig_idx = np.where(orig_labels == k)[0]
        targ_idx = np.where(target_labels == k)[0]
        n_k = len(orig_idx)

        cost = cdist(article_coords[orig_idx], targets[targ_idx])
        row_ind, col_ind = linear_sum_assignment(cost)
        displacements[orig_idx[row_ind]] = (
            targets[targ_idx[col_ind]] - article_coords[orig_idx[row_ind]]
        )
        total_cost += cost[row_ind, col_ind].sum()

        if (progress + 1) % 20 == 0 or progress == K - 1:
            elapsed = time.time() - t0
            print(
                f"  {progress + 1}/{K} clusters done "
                f"(largest so far: {n_k}×{n_k}, {elapsed:.1f}s elapsed)"
            )

    mean_disp = np.mean(np.linalg.norm(displacements, axis=1))
    max_disp = np.max(np.linalg.norm(displacements, axis=1))
    print(f"  Total cost: {total_cost:.2f}")
    print(f"  Displacement: mean={mean_disp:.4f}, max={max_disp:.4f}")

    # ---- Step 5: Apply mu mixing + question interpolation ----
    print(f"\nStep 5/6: Applying mu={mu} mixing...")
    flat_articles = article_coords + mu * displacements

    tree = cKDTree(article_coords)
    dists, idx = tree.query(question_coords, k=knn_k)
    weights = 1.0 / (dists + 1e-10)
    weights /= weights.sum(axis=1, keepdims=True)
    q_disp = (weights[:, :, None] * displacements[idx]).sum(axis=1)
    flat_questions = question_coords + mu * q_disp

    print(
        f"  Article displacement: mean={np.mean(np.linalg.norm(mu * displacements, axis=1)):.4f}"
    )
    print(
        f"  Question displacement: mean={np.mean(np.linalg.norm(mu * q_disp, axis=1)):.4f}"
    )

    # ---- Step 6: Re-normalize to [0, 1] ----
    print(f"\nStep 6/6: Re-normalizing to [0, 1]...")
    all_flat = np.vstack([flat_articles, flat_questions])
    xmin, ymin = all_flat.min(axis=0)
    xmax, ymax = all_flat.max(axis=0)

    def normalize(coords):
        normed = coords.copy()
        normed[:, 0] = (normed[:, 0] - xmin) / (xmax - xmin)
        normed[:, 1] = (normed[:, 1] - ymin) / (ymax - ymin)
        normed = normed * (1.0 - 2 * margin) + margin
        return normed

    flat_articles = normalize(flat_articles)
    flat_questions = normalize(flat_questions)

    print(
        f"  Articles range: x=[{flat_articles[:, 0].min():.4f}, {flat_articles[:, 0].max():.4f}], "
        f"y=[{flat_articles[:, 1].min():.4f}, {flat_articles[:, 1].max():.4f}]"
    )
    print(
        f"  Questions range: x=[{flat_questions[:, 0].min():.4f}, {flat_questions[:, 0].max():.4f}], "
        f"y=[{flat_questions[:, 1].min():.4f}, {flat_questions[:, 1].max():.4f}]"
    )

    info = {
        "mu": mu,
        "method": "patched",
        "n_clusters": K,
        "knn_k": knn_k,
        "margin": margin,
        "seed": seed,
        "total_assignment_cost": float(total_cost),
        "mean_displacement": float(mean_disp),
        "max_displacement": float(max_disp),
        "cluster_size_range": (int(cluster_sizes.min()), int(cluster_sizes.max())),
    }

    return flat_articles, flat_questions, info


# ---------------------------------------------------------------------------
# Subsample-based flattening (original method)
# ---------------------------------------------------------------------------


def flatten_coordinates(
    article_coords: np.ndarray,
    question_coords: np.ndarray,
    mu: float = 0.75,
    subsample_m: int = 5000,
    knn_k: int = 8,
    margin: float = 0.02,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Flatten coordinate density via approximate optimal transport.

    Parameters
    ----------
    article_coords : (N, 2) array in [0, 1]
    question_coords : (Q, 2) array in [0, 1]
    mu : mixing parameter, 0=original, 1=fully flattened
    subsample_m : number of representative points for Hungarian
    knn_k : number of neighbors for displacement interpolation
    margin : margin for target point placement
    seed : random seed

    Returns
    -------
    flat_articles : (N, 2) flattened article coordinates
    flat_questions : (Q, 2) flattened question coordinates
    info : dict with diagnostic information
    """
    n_articles = len(article_coords)
    n_questions = len(question_coords)

    print(f"\n{'=' * 70}")
    print(f"COORDINATE FLATTENING via Approximate Optimal Transport")
    print(f"{'=' * 70}")
    print(f"  Articles:   {n_articles:,}")
    print(f"  Questions:  {n_questions:,}")
    print(f"  mu:         {mu}")
    print(f"  Subsample:  {subsample_m:,}")
    print(f"  k-NN:       {knn_k}")
    print(f"  Margin:     {margin}")
    print()

    # ---- Step 1: Farthest-point subsampling ----
    print("Step 1/6: Farthest-point subsampling...")
    t0 = time.time()
    subsample_idx = farthest_point_sampling(article_coords, subsample_m, seed=seed)
    X_sub = article_coords[subsample_idx]
    print(
        f"  Done in {time.time() - t0:.1f}s — {len(X_sub)} representative points selected"
    )

    # ---- Step 2: Generate quasi-uniform targets ----
    print("\nStep 2/6: Generating Halton target points...")
    t0 = time.time()
    Y_target = generate_halton_targets(subsample_m, margin=margin)
    print(
        f"  Done in {time.time() - t0:.1f}s — {len(Y_target)} target points in [{margin}, {1 - margin}]^2"
    )

    # ---- Step 3: Hungarian assignment ----
    print(
        f"\nStep 3/6: Hungarian assignment on {subsample_m}x{subsample_m} cost matrix..."
    )
    t0 = time.time()
    cost_matrix = cdist(X_sub, Y_target, metric="euclidean")
    print(f"  Cost matrix: {cost_matrix.shape}, {cost_matrix.nbytes / 1e6:.1f} MB")
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    total_cost = cost_matrix[row_ind, col_ind].sum()
    print(
        f"  Done in {time.time() - t0:.1f}s — total assignment cost: {total_cost:.2f}"
    )

    # Compute displacement vectors at subsample points
    displacements = Y_target[col_ind] - X_sub
    print(
        f"  Displacement stats: mean={np.mean(np.linalg.norm(displacements, axis=1)):.4f}, "
        f"max={np.max(np.linalg.norm(displacements, axis=1)):.4f}"
    )

    # ---- Step 4: Build k-NN tree on subsample ----
    print(f"\nStep 4/6: Building k-NN displacement field (k={knn_k})...")
    t0 = time.time()
    tree = cKDTree(X_sub)

    # ---- Step 5: Interpolate displacements to all points ----
    print(
        f"\nStep 5/6: Interpolating displacements to {n_articles + n_questions:,} points..."
    )

    def interpolate_displacements(coords: np.ndarray, label: str) -> np.ndarray:
        """Apply k-NN weighted displacement interpolation."""
        dists, idx = tree.query(coords, k=knn_k)

        # Inverse-distance weighting
        weights = 1.0 / (dists + 1e-10)
        weights /= weights.sum(axis=1, keepdims=True)

        # Weighted average of displacements
        # displacements[idx] has shape (N, k, 2), weights has shape (N, k)
        interp_disp = (weights[:, :, None] * displacements[idx]).sum(axis=1)

        # Apply with mu mixing
        flat = coords + mu * interp_disp
        print(
            f"  {label}: displacement mean={np.mean(np.linalg.norm(mu * interp_disp, axis=1)):.4f}"
        )
        return flat

    flat_articles = interpolate_displacements(article_coords, "Articles")
    flat_questions = interpolate_displacements(question_coords, "Questions")
    print(f"  Done in {time.time() - t0:.1f}s")

    # ---- Step 6: Re-normalize to [0, 1] with margin ----
    print(f"\nStep 6/6: Re-normalizing to [0, 1]...")

    # Use article coords to define the normalization (questions follow same transform)
    all_flat = np.vstack([flat_articles, flat_questions])
    xmin, ymin = all_flat.min(axis=0)
    xmax, ymax = all_flat.max(axis=0)

    def normalize(coords):
        normed = coords.copy()
        normed[:, 0] = (normed[:, 0] - xmin) / (xmax - xmin)
        normed[:, 1] = (normed[:, 1] - ymin) / (ymax - ymin)
        # Apply slight inward scaling to avoid points exactly at edges
        normed = normed * (1.0 - 2 * margin) + margin
        return normed

    flat_articles = normalize(flat_articles)
    flat_questions = normalize(flat_questions)

    print(
        f"  Articles range: x=[{flat_articles[:, 0].min():.4f}, {flat_articles[:, 0].max():.4f}], "
        f"y=[{flat_articles[:, 1].min():.4f}, {flat_articles[:, 1].max():.4f}]"
    )
    print(
        f"  Questions range: x=[{flat_questions[:, 0].min():.4f}, {flat_questions[:, 0].max():.4f}], "
        f"y=[{flat_questions[:, 1].min():.4f}, {flat_questions[:, 1].max():.4f}]"
    )

    info = {
        "mu": mu,
        "subsample_m": subsample_m,
        "knn_k": knn_k,
        "margin": margin,
        "seed": seed,
        "total_assignment_cost": float(total_cost),
        "mean_displacement": float(np.mean(np.linalg.norm(displacements, axis=1))),
        "normalization": {
            "xmin": float(xmin),
            "xmax": float(xmax),
            "ymin": float(ymin),
            "ymax": float(ymax),
        },
    }

    return flat_articles, flat_questions, info


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Flatten UMAP coordinates via approximate optimal transport"
    )
    parser.add_argument(
        "--mu",
        type=float,
        default=0.75,
        help="Mixing parameter: 0=original, 1=fully flat (default: 0.75)",
    )
    parser.add_argument(
        "--subsample",
        type=int,
        default=5000,
        help="Number of subsample points for Hungarian (default: 5000)",
    )
    parser.add_argument(
        "--knn",
        type=int,
        default=8,
        help="k-NN neighbors for displacement interpolation (default: 8)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.02,
        help="Margin from edges for target placement (default: 0.02)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--embeddings-dir",
        type=str,
        default=None,
        help="Directory for embedding files (default: <project>/embeddings)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only print density stats, don't flatten",
    )
    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent
    emb_dir = (
        Path(args.embeddings_dir)
        if args.embeddings_dir
        else project_root / "embeddings"
    )

    article_path = emb_dir / "article_coords.pkl"
    question_path = emb_dir / "question_coords.pkl"
    output_article_path = emb_dir / "article_coords_flat.pkl"
    output_question_path = emb_dir / "question_coords_flat.pkl"

    # Load coordinates
    print("Loading coordinates...")
    with open(article_path, "rb") as f:
        article_data = pickle.load(f)
    with open(question_path, "rb") as f:
        question_data = pickle.load(f)

    article_coords = article_data["coords"]
    question_coords = question_data["coords"]
    print(f"  Articles: {article_coords.shape}")
    print(f"  Questions: {question_coords.shape}")

    # Density stats (before)
    print("\nComputing density statistics (BEFORE)...")
    stats_before = compute_density_stats(article_coords)
    print(f"  Empty cells: {stats_before['empty_pct']:.1f}%")
    print(
        f"  Articles in top 10% cells: {stats_before['articles_in_top10pct_frac']:.1%}"
    )
    print(f"  Max density: {stats_before['max_density']}")
    print(
        f"  Std/Mean: {stats_before['std_density_nonzero'] / max(stats_before['mean_density_nonzero'], 1):.2f}"
    )

    if args.stats_only:
        print("\n--stats-only mode, exiting.")
        return

    # Flatten
    flat_articles, flat_questions, info = flatten_coordinates(
        article_coords=article_coords,
        question_coords=question_coords,
        mu=args.mu,
        subsample_m=args.subsample,
        knn_k=args.knn,
        margin=args.margin,
        seed=args.seed,
    )

    # Density stats (after)
    print("\nComputing density statistics (AFTER)...")
    stats_after = compute_density_stats(flat_articles)
    print_density_comparison(stats_before, stats_after)

    # Semantic coherence check
    print("\nChecking semantic coherence...")
    coherence = check_semantic_coherence(article_coords, flat_articles)
    info["semantic_coherence_k10"] = float(coherence)
    info["density_before"] = stats_before
    info["density_after"] = stats_after

    # Save flattened article coordinates
    print(f"\nSaving flattened coordinates...")
    flat_article_data = {
        "coords": flat_articles,
        "coords_original": article_coords,
        "n_points": len(flat_articles),
        "timestamp": datetime.now().isoformat(),
        "flatten_params": info,
    }
    with open(output_article_path, "wb") as f:
        pickle.dump(flat_article_data, f)
    print(
        f"  Saved: {output_article_path} ({output_article_path.stat().st_size / 1e6:.1f} MB)"
    )

    # Save flattened question coordinates
    flat_question_data = {
        "coords": flat_questions,
        "coords_original": question_coords,
        "n_points": len(flat_questions),
        "timestamp": datetime.now().isoformat(),
        "flatten_params": info,
    }
    with open(output_question_path, "wb") as f:
        pickle.dump(flat_question_data, f)
    print(
        f"  Saved: {output_question_path} ({output_question_path.stat().st_size / 1e6:.1f} MB)"
    )

    print(f"\nDone! Flattened coordinates saved with mu={args.mu}")
    print(f"  To adjust: python scripts/flatten_coordinates.py --mu <value>")


if __name__ == "__main__":
    main()
