#!/usr/bin/env python3
"""
Test embedding repair strategy with actual UMAP inverse_transform.
"""

import os
import json
import pickle
import numpy as np

# Fix for macOS mutex/threading issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def load_umap_model(model_path='data/umap_reducer.pkl'):
    """Load pre-fitted UMAP model."""
    with open(model_path, 'rb') as f:
        return pickle.load(f)


def load_umap_bounds(bounds_path='data/umap_bounds.pkl'):
    """Load UMAP coordinate bounds."""
    with open(bounds_path, 'rb') as f:
        return pickle.load(f)


def load_questions(questions_path='questions.json'):
    """Load questions with full embeddings."""
    with open(questions_path, 'r') as f:
        questions = json.load(f)
    return questions


def analyze_inverse_transform_behavior(grid_size=2):
    """
    Test UMAP inverse_transform on a small grid to see actual extreme values.
    """
    print("="*70)
    print("UMAP Inverse Transform Analysis")
    print("="*70)

    # Load data
    umap_reducer = load_umap_model()
    bounds = load_umap_bounds()
    questions = load_questions()
    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    print(f"\nReference embeddings: {reference_embeddings.shape}")
    print(f"  L2 norms: [{np.linalg.norm(reference_embeddings, axis=1).min():.3f}, "
          f"{np.linalg.norm(reference_embeddings, axis=1).max():.3f}]")
    print(f"  Value range: [{reference_embeddings.min():.3f}, {reference_embeddings.max():.3f}]")

    ref_norms = np.linalg.norm(reference_embeddings, axis=1)
    ref_norm_mean = ref_norms.mean()
    ref_norm_std = ref_norms.std()
    print(f"  Norm mean±std: {ref_norm_mean:.6f}±{ref_norm_std:.6f}")

    ref_mean = reference_embeddings.mean(axis=0)
    ref_std = reference_embeddings.std(axis=0)
    print(f"  Element mean±std: {ref_mean.mean():.6f}±{ref_std.mean():.6f}")

    print(f"\nUMAP bounds: x=[{bounds['x_min']:.3f}, {bounds['x_max']:.3f}], "
          f"y=[{bounds['y_min']:.3f}, {bounds['y_max']:.3f}]")

    # Test grid cells
    print(f"\n{'='*70}")
    print(f"Testing {grid_size}x{grid_size} Grid Cells")
    print(f"{'='*70}")

    results = []

    for gy in range(grid_size):
        for gx in range(grid_size):
            # Cell center in normalized [0, 1] space
            x_norm = (gx + 0.5) / grid_size
            y_norm = (gy + 0.5) / grid_size

            # Convert to UMAP space
            x_umap = x_norm * (bounds['x_max'] - bounds['x_min']) + bounds['x_min']
            y_umap = y_norm * (bounds['y_max'] - bounds['y_min']) + bounds['y_min']

            print(f"\n--- Cell ({gx}, {gy}) ---")
            print(f"Normalized coords: ({x_norm:.3f}, {y_norm:.3f})")
            print(f"UMAP coords: ({x_umap:.3f}, {y_umap:.3f})")

            # Perform inverse transform
            coords_2d = np.array([[x_umap, y_umap]])
            embedding = umap_reducer.inverse_transform(coords_2d)[0]

            # Analyze raw inverse transform result
            norm = np.linalg.norm(embedding)
            norm_z_score = (norm - ref_norm_mean) / (ref_norm_std + 1e-8)

            z_scores = (embedding - ref_mean) / (ref_std + 1e-8)
            max_z_score = np.abs(z_scores).max()
            mean_z_score = np.abs(z_scores).mean()

            print(f"\nRaw inverse_transform result:")
            print(f"  L2 norm: {norm:.6f} (z-score: {norm_z_score:.2f})")
            print(f"  Value range: [{embedding.min():.6f}, {embedding.max():.6f}]")
            print(f"  Element z-score: max={max_z_score:.2f}, mean={mean_z_score:.2f}")
            print(f"  Has NaN/Inf: {not np.isfinite(embedding).all()}")

            # Check cosine similarity to nearest reference
            similarities = np.dot(reference_embeddings, embedding) / (
                np.linalg.norm(reference_embeddings, axis=1) * norm + 1e-8
            )
            max_similarity = similarities.max()
            print(f"  Max cosine similarity to reference: {max_similarity:.4f}")

            results.append({
                'gx': gx,
                'gy': gy,
                'norm': norm,
                'norm_z_score': norm_z_score,
                'max_z_score': max_z_score,
                'max_similarity': max_similarity,
                'embedding': embedding.copy()
            })

    # Summary statistics
    print(f"\n{'='*70}")
    print("Summary Statistics")
    print(f"{'='*70}")

    norms = [r['norm'] for r in results]
    norm_z_scores = [r['norm_z_score'] for r in results]
    max_z_scores = [r['max_z_score'] for r in results]
    max_sims = [r['max_similarity'] for r in results]

    print(f"\nL2 norms:")
    print(f"  Range: [{min(norms):.6f}, {max(norms):.6f}]")
    print(f"  Mean±Std: {np.mean(norms):.6f}±{np.std(norms):.6f}")

    print(f"\nNorm z-scores:")
    print(f"  Range: [{min(norm_z_scores):.2f}, {max(norm_z_scores):.2f}]")
    print(f"  Mean±Std: {np.mean(norm_z_scores):.2f}±{np.std(norm_z_scores):.2f}")

    print(f"\nMax element z-scores:")
    print(f"  Range: [{min(max_z_scores):.2f}, {max(max_z_scores):.2f}]")
    print(f"  Mean±Std: {np.mean(max_z_scores):.2f}±{np.std(max_z_scores):.2f}")

    print(f"\nMax cosine similarities:")
    print(f"  Range: [{min(max_sims):.4f}, {max(max_sims):.4f}]")
    print(f"  Mean±Std: {np.mean(max_sims):.4f}±{np.std(max_sims):.4f}")

    # Identify problem cells
    problem_cells = [r for r in results if abs(r['norm_z_score']) > 1000]
    if problem_cells:
        print(f"\n⚠️  Problem cells (|norm_z_score| > 1000): {len(problem_cells)}")
        for r in problem_cells:
            print(f"  Cell ({r['gx']}, {r['gy']}): norm={r['norm']:.2e}, z-score={r['norm_z_score']:.2e}")

    return results


def test_repair_strategies(results):
    """
    Test different repair strategies on problematic embeddings.
    """
    print(f"\n{'='*70}")
    print("Testing Repair Strategies")
    print(f"{'='*70}")

    questions = load_questions()
    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    ref_norms = np.linalg.norm(reference_embeddings, axis=1)
    target_norm = ref_norms.mean()

    ref_mean = reference_embeddings.mean(axis=0)
    ref_std = reference_embeddings.std(axis=0)

    # Test on most extreme case
    worst_case = max(results, key=lambda r: abs(r['norm_z_score']))
    print(f"\nWorst case: Cell ({worst_case['gx']}, {worst_case['gy']})")
    print(f"  Original norm: {worst_case['norm']:.2e} (z-score: {worst_case['norm_z_score']:.2e})")

    embedding = worst_case['embedding'].copy()

    # Strategy 1: Simple L2 normalization
    print(f"\n--- Strategy 1: L2 Normalization to Target Norm ---")
    repaired_1 = embedding.copy()
    current_norm = np.linalg.norm(repaired_1)
    if current_norm > 0:
        repaired_1 = repaired_1 * (target_norm / current_norm)

    norm_1 = np.linalg.norm(repaired_1)
    z_scores_1 = (repaired_1 - ref_mean) / (ref_std + 1e-8)
    max_z_1 = np.abs(z_scores_1).max()
    similarities_1 = np.dot(reference_embeddings, repaired_1) / (
        np.linalg.norm(reference_embeddings, axis=1) * norm_1 + 1e-8
    )
    max_sim_1 = similarities_1.max()

    print(f"  L2 norm: {norm_1:.6f}")
    print(f"  Max element z-score: {max_z_1:.2f}")
    print(f"  Max cosine similarity: {max_sim_1:.4f}")

    # Strategy 2: L2 norm + aggressive element clipping
    print(f"\n--- Strategy 2: L2 Norm + Aggressive Clipping (±3σ) ---")
    repaired_2 = embedding.copy()
    current_norm = np.linalg.norm(repaired_2)
    if current_norm > 0:
        repaired_2 = repaired_2 * (target_norm / current_norm)

    # Clip to ±3σ
    lower_bound = ref_mean - 3 * ref_std
    upper_bound = ref_mean + 3 * ref_std
    repaired_2 = np.clip(repaired_2, lower_bound, upper_bound)

    # Re-normalize after clipping
    current_norm = np.linalg.norm(repaired_2)
    if current_norm > 0:
        repaired_2 = repaired_2 * (target_norm / current_norm)

    norm_2 = np.linalg.norm(repaired_2)
    z_scores_2 = (repaired_2 - ref_mean) / (ref_std + 1e-8)
    max_z_2 = np.abs(z_scores_2).max()
    similarities_2 = np.dot(reference_embeddings, repaired_2) / (
        np.linalg.norm(reference_embeddings, axis=1) * norm_2 + 1e-8
    )
    max_sim_2 = similarities_2.max()

    print(f"  L2 norm: {norm_2:.6f}")
    print(f"  Max element z-score: {max_z_2:.2f}")
    print(f"  Max cosine similarity: {max_sim_2:.4f}")

    # Strategy 3: Project onto reference embedding space
    print(f"\n--- Strategy 3: Project onto Reference Space (PCA-style) ---")
    # Use reference embeddings to define valid subspace
    # Project extreme embedding onto this subspace
    U, S, Vt = np.linalg.svd(reference_embeddings - ref_mean, full_matrices=False)

    # Project embedding onto principal components
    embedding_centered = embedding - ref_mean
    projection = embedding_centered @ Vt.T @ Vt
    repaired_3 = projection + ref_mean

    # Normalize
    current_norm = np.linalg.norm(repaired_3)
    if current_norm > 0:
        repaired_3 = repaired_3 * (target_norm / current_norm)

    norm_3 = np.linalg.norm(repaired_3)
    z_scores_3 = (repaired_3 - ref_mean) / (ref_std + 1e-8)
    max_z_3 = np.abs(z_scores_3).max()
    similarities_3 = np.dot(reference_embeddings, repaired_3) / (
        np.linalg.norm(reference_embeddings, axis=1) * norm_3 + 1e-8
    )
    max_sim_3 = similarities_3.max()

    print(f"  L2 norm: {norm_3:.6f}")
    print(f"  Max element z-score: {max_z_3:.2f}")
    print(f"  Max cosine similarity: {max_sim_3:.4f}")

    # Strategy 4: Hybrid - normalize, clip, project, re-normalize
    print(f"\n--- Strategy 4: Hybrid (Norm → Clip → Project → Norm) ---")
    repaired_4 = embedding.copy()

    # Step 1: Normalize
    current_norm = np.linalg.norm(repaired_4)
    if current_norm > 0:
        repaired_4 = repaired_4 * (target_norm / current_norm)

    # Step 2: Clip
    lower_bound = ref_mean - 3 * ref_std
    upper_bound = ref_mean + 3 * ref_std
    repaired_4 = np.clip(repaired_4, lower_bound, upper_bound)

    # Step 3: Project onto reference space
    embedding_centered = repaired_4 - ref_mean
    projection = embedding_centered @ Vt.T @ Vt
    repaired_4 = projection + ref_mean

    # Step 4: Final normalization
    current_norm = np.linalg.norm(repaired_4)
    if current_norm > 0:
        repaired_4 = repaired_4 * (target_norm / current_norm)

    norm_4 = np.linalg.norm(repaired_4)
    z_scores_4 = (repaired_4 - ref_mean) / (ref_std + 1e-8)
    max_z_4 = np.abs(z_scores_4).max()
    similarities_4 = np.dot(reference_embeddings, repaired_4) / (
        np.linalg.norm(reference_embeddings, axis=1) * norm_4 + 1e-8
    )
    max_sim_4 = similarities_4.max()

    print(f"  L2 norm: {norm_4:.6f}")
    print(f"  Max element z-score: {max_z_4:.2f}")
    print(f"  Max cosine similarity: {max_sim_4:.4f}")

    # Comparison
    print(f"\n{'='*70}")
    print("Strategy Comparison")
    print(f"{'='*70}")
    print(f"{'Strategy':<30} {'Norm':<12} {'Max Z-score':<15} {'Max Similarity':<15}")
    print(f"{'-'*70}")
    print(f"{'Original':<30} {worst_case['norm']:.6f}   {worst_case['max_z_score']:<15.2f} {worst_case['max_similarity']:<15.4f}")
    print(f"{'1: L2 Norm Only':<30} {norm_1:.6f}   {max_z_1:<15.2f} {max_sim_1:<15.4f}")
    print(f"{'2: L2 Norm + Clip':<30} {norm_2:.6f}   {max_z_2:<15.2f} {max_sim_2:<15.4f}")
    print(f"{'3: PCA Projection':<30} {norm_3:.6f}   {max_z_3:<15.2f} {max_sim_3:<15.4f}")
    print(f"{'4: Hybrid':<30} {norm_4:.6f}   {max_z_4:<15.2f} {max_sim_4:<15.4f}")
    print(f"{'-'*70}")
    print(f"{'Target (reference mean)':<30} {target_norm:.6f}   {'<3.0':<15} {'>0.3':<15}")

    return {
        'original': embedding,
        'strategy_1': repaired_1,
        'strategy_2': repaired_2,
        'strategy_3': repaired_3,
        'strategy_4': repaired_4,
    }


if __name__ == '__main__':
    # Test with 2x2 grid first
    print("\n" + "="*70)
    print("PART 1: Analyze UMAP Inverse Transform Behavior")
    print("="*70)

    results = analyze_inverse_transform_behavior(grid_size=2)

    print("\n" + "="*70)
    print("PART 2: Test Repair Strategies")
    print("="*70)

    repaired = test_repair_strategies(results)

    print("\n✅ Analysis complete!")
