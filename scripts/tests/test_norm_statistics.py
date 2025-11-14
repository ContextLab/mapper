#!/usr/bin/env python3
"""
Generate comprehensive norm statistics for documentation.
"""

import os
import sys

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

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


def analyze_grid_statistics(grid_size=10):
    """
    Generate comprehensive statistics for documentation.
    """
    print("="*80)
    print(f"EMBEDDING REPAIR STATISTICS - {grid_size}x{grid_size} GRID")
    print("="*80)

    # Load data
    umap_reducer = load_umap_model()
    bounds = load_umap_bounds()
    questions = load_questions()
    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    print(f"\nReference Embeddings:")
    ref_norms = np.linalg.norm(reference_embeddings, axis=1)
    print(f"  Shape: {reference_embeddings.shape}")
    print(f"  L2 norm (target): {ref_norms.mean():.6f} ± {ref_norms.std():.6f}")
    print(f"  Value range: [{reference_embeddings.min():.6f}, {reference_embeddings.max():.6f}]")

    # Collect statistics
    stats_before = {
        'norms': [],
        'norm_z_scores': [],
        'element_z_scores': [],
        'similarities': []
    }

    stats_after = {
        'norms': [],
        'norm_z_scores': [],
        'element_z_scores': [],
        'similarities': []
    }

    repair_counts = {
        'total': 0,
        'invalid': 0,
        'normalized': 0,
        'clipped': 0,
        'projected': 0,
        'blended': 0
    }

    print(f"\nProcessing {grid_size}x{grid_size} grid...")

    for gy in range(grid_size):
        for gx in range(grid_size):
            x_norm = (gx + 0.5) / grid_size
            y_norm = (gy + 0.5) / grid_size

            # Invert
            embedding, quality = invert_umap_coordinates(x_norm, y_norm, umap_reducer, bounds)

            # Before stats
            is_valid, diag = validate_embedding(embedding, reference_embeddings)
            stats_before['norms'].append(diag.get('norm', 0))
            stats_before['norm_z_scores'].append(diag.get('norm_z_score', 0))
            if 'max_value_z_score' in diag:
                stats_before['element_z_scores'].append(diag['max_value_z_score'])
            if 'max_cosine_similarity' in diag:
                stats_before['similarities'].append(diag['max_cosine_similarity'])

            repair_counts['total'] += 1
            if not is_valid:
                repair_counts['invalid'] += 1

            # Repair
            repaired, repair_log = repair_embedding(embedding, reference_embeddings, quality)

            # Count repair types
            for msg in repair_log:
                if 'Normalized' in msg:
                    repair_counts['normalized'] += 1
                if 'Clipped' in msg:
                    repair_counts['clipped'] += 1
                if 'Projected' in msg:
                    repair_counts['projected'] += 1
                if 'Blended' in msg:
                    repair_counts['blended'] += 1

            # After stats
            is_valid_after, diag_after = validate_embedding(repaired, reference_embeddings)
            stats_after['norms'].append(diag_after.get('norm', 0))
            stats_after['norm_z_scores'].append(diag_after.get('norm_z_score', 0))
            if 'max_value_z_score' in diag_after:
                stats_after['element_z_scores'].append(diag_after['max_value_z_score'])
            if 'max_cosine_similarity' in diag_after:
                stats_after['similarities'].append(diag_after['max_cosine_similarity'])

    # Print statistics
    print(f"\n{'='*80}")
    print("BEFORE REPAIR")
    print(f"{'='*80}")

    print(f"\nL2 Norms:")
    norms_before = np.array(stats_before['norms'])
    print(f"  Min:    {norms_before.min():.6e}")
    print(f"  Max:    {norms_before.max():.6e}")
    print(f"  Mean:   {norms_before.mean():.6e}")
    print(f"  Median: {np.median(norms_before):.6e}")
    print(f"  Std:    {norms_before.std():.6e}")

    print(f"\nNorm Z-Scores:")
    z_before = np.array(stats_before['norm_z_scores'])
    print(f"  Min:    {z_before.min():.6e}")
    print(f"  Max:    {z_before.max():.6e}")
    print(f"  Mean:   {z_before.mean():.6e}")
    print(f"  Median: {np.median(z_before):.6e}")

    if stats_before['element_z_scores']:
        print(f"\nElement Z-Scores:")
        elem_z_before = np.array(stats_before['element_z_scores'])
        print(f"  Min:    {elem_z_before.min():.2f}")
        print(f"  Max:    {elem_z_before.max():.2f}")
        print(f"  Mean:   {elem_z_before.mean():.2f}")

    if stats_before['similarities']:
        print(f"\nCosine Similarities:")
        sim_before = np.array(stats_before['similarities'])
        print(f"  Min:    {sim_before.min():.6f}")
        print(f"  Max:    {sim_before.max():.6f}")
        print(f"  Mean:   {sim_before.mean():.6f}")

    print(f"\n{'='*80}")
    print("AFTER REPAIR")
    print(f"{'='*80}")

    print(f"\nL2 Norms:")
    norms_after = np.array(stats_after['norms'])
    print(f"  Min:    {norms_after.min():.12f}")
    print(f"  Max:    {norms_after.max():.12f}")
    print(f"  Mean:   {norms_after.mean():.12f}")
    print(f"  Median: {np.median(norms_after):.12f}")
    print(f"  Std:    {norms_after.std():.12e}")

    print(f"\nNorm Z-Scores:")
    z_after = np.array(stats_after['norm_z_scores'])
    print(f"  Min:    {z_after.min():.12e}")
    print(f"  Max:    {z_after.max():.12e}")
    print(f"  Mean:   {z_after.mean():.12e}")
    print(f"  Median: {np.median(z_after):.12e}")

    if stats_after['element_z_scores']:
        print(f"\nElement Z-Scores:")
        elem_z_after = np.array(stats_after['element_z_scores'])
        print(f"  Min:    {elem_z_after.min():.6f}")
        print(f"  Max:    {elem_z_after.max():.6f}")
        print(f"  Mean:   {elem_z_after.mean():.6f}")

    if stats_after['similarities']:
        print(f"\nCosine Similarities:")
        sim_after = np.array(stats_after['similarities'])
        print(f"  Min:    {sim_after.min():.6f}")
        print(f"  Max:    {sim_after.max():.6f}")
        print(f"  Mean:   {sim_after.mean():.6f}")

    print(f"\n{'='*80}")
    print("REPAIR OPERATIONS")
    print(f"{'='*80}")

    print(f"\nCells processed: {repair_counts['total']}")
    print(f"Invalid before repair: {repair_counts['invalid']} ({repair_counts['invalid']/repair_counts['total']*100:.1f}%)")
    print(f"\nRepair operations applied:")
    print(f"  Normalized: {repair_counts['normalized']} ({repair_counts['normalized']/repair_counts['total']*100:.1f}%)")
    print(f"  Clipped: {repair_counts['clipped']} ({repair_counts['clipped']/repair_counts['total']*100:.1f}%)")
    print(f"  Projected: {repair_counts['projected']} ({repair_counts['projected']/repair_counts['total']*100:.1f}%)")
    print(f"  Blended: {repair_counts['blended']} ({repair_counts['blended']/repair_counts['total']*100:.1f}%)")

    print(f"\n{'='*80}")
    print("IMPROVEMENT METRICS")
    print(f"{'='*80}")

    print(f"\nNorm improvement:")
    print(f"  Before: {norms_before.mean():.2e} ± {norms_before.std():.2e}")
    print(f"  After:  {norms_after.mean():.12f} ± {norms_after.std():.2e}")
    print(f"  Target: {ref_norms.mean():.12f}")
    print(f"  Error:  {abs(norms_after.mean() - ref_norms.mean()):.2e}")

    print(f"\nZ-score improvement:")
    print(f"  Before: max={z_before.max():.2e}, mean={abs(z_before).mean():.2e}")
    print(f"  After:  max={abs(z_after).max():.2e}, mean={abs(z_after).mean():.2e}")

    if stats_before['element_z_scores'] and stats_after['element_z_scores']:
        print(f"\nElement z-score improvement:")
        elem_z_before = np.array(stats_before['element_z_scores'])
        elem_z_after = np.array(stats_after['element_z_scores'])
        print(f"  Before: max={elem_z_before.max():.2f}")
        print(f"  After:  max={elem_z_after.max():.2f}")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    analyze_grid_statistics(grid_size=10)
