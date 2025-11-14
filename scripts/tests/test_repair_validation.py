#!/usr/bin/env python3
"""
Comprehensive test of embedding repair with validation.
Verifies that repaired embeddings pass validation checks.
"""

import os
import sys

# Fix for macOS mutex/threading issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

# Add current directory to path to import from generate_cell_labels
sys.path.insert(0, '/Users/jmanning/mapper.io')

from generate_cell_labels import (
    load_umap_model,
    load_umap_bounds,
    load_questions,
    invert_umap_coordinates,
    validate_embedding,
    repair_embedding
)
import numpy as np


def test_repair_on_grid(grid_size=2):
    """
    Test repair strategy on a small grid and validate results.
    """
    print("="*70)
    print("Embedding Repair Validation Test")
    print("="*70)

    # Load data
    umap_reducer = load_umap_model()
    bounds = load_umap_bounds()
    questions = load_questions()
    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    print(f"\nReference embeddings: {reference_embeddings.shape}")
    ref_norms = np.linalg.norm(reference_embeddings, axis=1)
    print(f"  Target norm: {ref_norms.mean():.6f}")

    # Test grid
    print(f"\n{'='*70}")
    print(f"Testing {grid_size}x{grid_size} Grid")
    print(f"{'='*70}")

    results = []
    repair_stats = {
        'total': 0,
        'invalid_before': 0,
        'valid_after': 0,
        'still_invalid': 0
    }

    for gy in range(grid_size):
        for gx in range(grid_size):
            x_norm = (gx + 0.5) / grid_size
            y_norm = (gy + 0.5) / grid_size

            print(f"\n--- Cell ({gx}, {gy}) ---")

            # Invert UMAP
            embedding, quality = invert_umap_coordinates(x_norm, y_norm, umap_reducer, bounds)

            # Validate original
            is_valid_orig, diag_orig = validate_embedding(embedding, reference_embeddings)

            print(f"Original:")
            print(f"  Valid: {is_valid_orig}")
            print(f"  Norm: {diag_orig.get('norm', 'N/A'):.6f} (z-score: {diag_orig.get('norm_z_score', 0):.2e})")
            if 'max_value_z_score' in diag_orig:
                print(f"  Max element z-score: {diag_orig['max_value_z_score']:.2f}")
            if 'max_cosine_similarity' in diag_orig:
                print(f"  Max similarity: {diag_orig['max_cosine_similarity']:.4f}")
            if not is_valid_orig and 'needs_repair' in diag_orig:
                print(f"  Reason: {diag_orig['needs_repair']}")

            repair_stats['total'] += 1
            if not is_valid_orig:
                repair_stats['invalid_before'] += 1

            # Repair
            repaired, repair_log = repair_embedding(embedding, reference_embeddings, quality)

            print(f"\nRepair log:")
            for msg in repair_log:
                print(f"  - {msg}")

            # Validate repaired
            is_valid_repaired, diag_repaired = validate_embedding(repaired, reference_embeddings)

            print(f"\nRepaired:")
            print(f"  Valid: {is_valid_repaired}")
            print(f"  Norm: {diag_repaired.get('norm', 'N/A'):.6f} (z-score: {diag_repaired.get('norm_z_score', 0):.2e})")
            if 'max_value_z_score' in diag_repaired:
                print(f"  Max element z-score: {diag_repaired['max_value_z_score']:.2f}")
            if 'max_cosine_similarity' in diag_repaired:
                print(f"  Max similarity: {diag_repaired['max_cosine_similarity']:.4f}")

            if not is_valid_orig and is_valid_repaired:
                repair_stats['valid_after'] += 1
                print(f"  ✅ Successfully repaired!")
            elif not is_valid_orig and not is_valid_repaired:
                repair_stats['still_invalid'] += 1
                print(f"  ⚠️  Still invalid after repair")
                if 'needs_repair' in diag_repaired:
                    print(f"  Reason: {diag_repaired['needs_repair']}")

            results.append({
                'gx': gx,
                'gy': gy,
                'valid_orig': is_valid_orig,
                'valid_repaired': is_valid_repaired,
                'norm_orig': diag_orig.get('norm', 0),
                'norm_repaired': diag_repaired.get('norm', 0),
                'z_score_orig': diag_orig.get('norm_z_score', 0),
                'z_score_repaired': diag_repaired.get('norm_z_score', 0),
                'similarity_orig': diag_orig.get('max_cosine_similarity', 0),
                'similarity_repaired': diag_repaired.get('max_cosine_similarity', 0)
            })

    # Summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}")

    print(f"\nRepair Statistics:")
    print(f"  Total cells: {repair_stats['total']}")
    print(f"  Invalid before repair: {repair_stats['invalid_before']}")
    print(f"  Valid after repair: {repair_stats['valid_after']}")
    print(f"  Still invalid: {repair_stats['still_invalid']}")

    if repair_stats['invalid_before'] > 0:
        success_rate = repair_stats['valid_after'] / repair_stats['invalid_before'] * 100
        print(f"  Success rate: {success_rate:.1f}%")

    # Norm statistics
    norms_orig = [r['norm_orig'] for r in results]
    norms_repaired = [r['norm_repaired'] for r in results]

    print(f"\nNorm Statistics:")
    print(f"  Original: [{min(norms_orig):.2e}, {max(norms_orig):.2e}]")
    print(f"  Repaired: [{min(norms_repaired):.6f}, {max(norms_repaired):.6f}]")
    print(f"  Target: {ref_norms.mean():.6f}")

    # Z-score statistics
    z_scores_orig = [r['z_score_orig'] for r in results]
    z_scores_repaired = [r['z_score_repaired'] for r in results]

    print(f"\nNorm Z-Score Statistics:")
    print(f"  Original: [{min(z_scores_orig):.2e}, {max(z_scores_orig):.2e}]")
    print(f"  Repaired: [{min(z_scores_repaired):.6f}, {max(z_scores_repaired):.6f}]")

    # Similarity statistics
    sims_orig = [r['similarity_orig'] for r in results]
    sims_repaired = [r['similarity_repaired'] for r in results]

    print(f"\nCosine Similarity Statistics:")
    print(f"  Original: [{min(sims_orig):.4f}, {max(sims_orig):.4f}]")
    print(f"  Repaired: [{min(sims_repaired):.4f}, {max(sims_repaired):.4f}]")

    # Final verdict
    print(f"\n{'='*70}")
    all_valid = all(r['valid_repaired'] for r in results)
    if all_valid:
        print("✅ SUCCESS: All repaired embeddings pass validation!")
    else:
        print("⚠️  WARNING: Some repaired embeddings still fail validation")
        for r in results:
            if not r['valid_repaired']:
                print(f"  Cell ({r['gx']}, {r['gy']})")

    print(f"{'='*70}")

    return results, repair_stats


if __name__ == '__main__':
    results, stats = test_repair_on_grid(grid_size=2)

    # Exit with error code if repairs failed
    if stats['still_invalid'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
