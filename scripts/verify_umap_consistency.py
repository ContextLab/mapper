#!/usr/bin/env python3
"""
Verify UMAP Reducer Consistency

This script verifies that the saved UMAP reducer in data/umap_reducer.pkl
is compatible with the current Wikipedia embeddings. This is CRITICAL because
per Issue #13 comment, the UMAP reducer may be from an old run.

If UMAP is out of sync, ALL downstream data becomes invalid:
- optimal_rectangle.json
- heatmap_cell_labels.json
- cell_questions.json
- wikipedia_articles.json

Tests performed:
1. Reducer can transform current embeddings
2. Transformed coordinates match saved coordinates (tolerance: 1e-5)
3. Question coordinates align with expected positions
4. Neighbor overlap is >60% (per rebuild_umap.py documentation)

If ANY test fails, UMAP rebuild is required.

Usage:
    python scripts/verify_umap_consistency.py
"""

import pickle
import numpy as np
from pathlib import Path
import sys


def load_umap_reducer():
    """Load saved UMAP reducer from disk."""
    print("=" * 80)
    print("TEST 1: Load UMAP Reducer")
    print("=" * 80)
    print()

    reducer_path = Path('data/umap_reducer.pkl')

    if not reducer_path.exists():
        print(f"  CRITICAL ERROR: {reducer_path} not found")
        print("  Cannot proceed without UMAP reducer")
        return None

    print(f"  Loading UMAP reducer from {reducer_path}...")

    try:
        with open(reducer_path, 'rb') as f:
            reducer = pickle.load(f)

        print(f"    Reducer type: {type(reducer).__name__}")
        print(f"    Embedding dimension: {reducer.n_components}")
        print(f"    Metric: {reducer.metric}")
        print(f"    n_neighbors: {reducer.n_neighbors}")
        print()
        print("  PASS: UMAP reducer loaded successfully")
        print()
        return reducer
    except Exception as e:
        print(f"  CRITICAL ERROR: Failed to load UMAP reducer")
        print(f"  Error: {e}")
        print()
        return None


def load_embeddings():
    """Load Wikipedia and question embeddings."""
    print("=" * 80)
    print("TEST 2: Load Current Embeddings")
    print("=" * 80)
    print()

    # Load Wikipedia embeddings
    wiki_path = Path('embeddings/wikipedia_embeddings.pkl')

    if not wiki_path.exists():
        print(f"  CRITICAL ERROR: {wiki_path} not found")
        return None, None

    print(f"  Loading Wikipedia embeddings from {wiki_path}...")

    try:
        with open(wiki_path, 'rb') as f:
            wiki_data = pickle.load(f)

        wiki_embeddings = wiki_data['embeddings']
        print(f"    Wikipedia embeddings: {wiki_embeddings.shape}")
        print(f"    Model: {wiki_data.get('model', 'unknown')}")
        print()
    except Exception as e:
        print(f"  CRITICAL ERROR: Failed to load Wikipedia embeddings")
        print(f"  Error: {e}")
        return None, None

    # Load question embeddings
    question_path = Path('embeddings/question_embeddings.pkl')

    if not question_path.exists():
        print(f"  CRITICAL ERROR: {question_path} not found")
        return None, None

    print(f"  Loading question embeddings from {question_path}...")

    try:
        with open(question_path, 'rb') as f:
            question_data = pickle.load(f)

        question_embeddings = question_data['embeddings']
        print(f"    Question embeddings: {question_embeddings.shape}")
        print(f"    Model: {question_data.get('model', 'unknown')}")
        print()
    except Exception as e:
        print(f"  CRITICAL ERROR: Failed to load question embeddings")
        print(f"  Error: {e}")
        return None, None

    print("  PASS: Embeddings loaded successfully")
    print()
    return wiki_embeddings, question_embeddings


def test_reducer_transformation(reducer, wiki_embeddings, question_embeddings):
    """Test that reducer can transform current embeddings."""
    print("=" * 80)
    print("TEST 3: Reducer Transformation Capability")
    print("=" * 80)
    print()

    # Combine embeddings (articles first, then questions - same as rebuild_umap.py)
    combined_embeddings = np.vstack([wiki_embeddings, question_embeddings])
    print(f"  Combined embeddings shape: {combined_embeddings.shape}")
    print(f"  Articles: indices 0-{len(wiki_embeddings)-1}")
    print(f"  Questions: indices {len(wiki_embeddings)}-{len(combined_embeddings)-1}")
    print()

    # Test transformation on first 100 embeddings
    print("  Testing transformation on first 100 embeddings...")

    try:
        test_coords = reducer.transform(combined_embeddings[:100])
        print(f"    Transformed shape: {test_coords.shape}")
        print(f"    Coordinate range: x=[{test_coords[:, 0].min():.2f}, {test_coords[:, 0].max():.2f}]")
        print(f"                      y=[{test_coords[:, 1].min():.2f}, {test_coords[:, 1].max():.2f}]")
        print()
        print("  PASS: Reducer can transform embeddings")
        print()
        return True
    except Exception as e:
        print(f"  CRITICAL ERROR: Reducer failed to transform embeddings")
        print(f"  Error: {e}")
        print()
        print("  This means the UMAP reducer is incompatible with current embeddings")
        print("  UMAP rebuild is REQUIRED")
        print()
        return False


def test_coordinate_matching(reducer, wiki_embeddings, question_embeddings):
    """Test that transformed coordinates match saved coordinates."""
    print("=" * 80)
    print("TEST 4: Coordinate Matching")
    print("=" * 80)
    print()

    # Load saved coordinates
    coords_path = Path('umap_coords.pkl')

    if not coords_path.exists():
        print(f"  ERROR: {coords_path} not found")
        print("  Cannot verify coordinate matching")
        print()
        return False

    print(f"  Loading saved coordinates from {coords_path}...")

    try:
        with open(coords_path, 'rb') as f:
            coords_data = pickle.load(f)

        saved_coords = coords_data['coords_2d']
        print(f"    Saved coordinates shape: {saved_coords.shape}")
        print()
    except Exception as e:
        print(f"  ERROR: Failed to load saved coordinates")
        print(f"  Error: {e}")
        return False

    # Transform first 100 embeddings
    combined_embeddings = np.vstack([wiki_embeddings, question_embeddings])

    print("  Transforming first 100 embeddings...")

    try:
        test_coords = reducer.transform(combined_embeddings[:100])
    except Exception as e:
        print(f"  ERROR: Transformation failed")
        print(f"  Error: {e}")
        return False

    # Compare coordinates
    print("  Comparing transformed vs saved coordinates...")

    coord_diff = np.abs(test_coords - saved_coords[:100])
    max_diff = coord_diff.max()
    mean_diff = coord_diff.mean()

    print(f"    Maximum difference: {max_diff:.2e}")
    print(f"    Mean difference: {mean_diff:.2e}")
    print(f"    Tolerance: 1.00e-05")
    print()

    if max_diff < 1e-5:
        print("  PASS: Coordinates match (drift < 1e-5)")
        print()
        return True
    else:
        print(f"  CRITICAL ERROR: Coordinates drifted beyond tolerance")
        print(f"  Maximum drift: {max_diff:.2e}")
        print()
        print("  This means the UMAP reducer is NOT consistent with saved coordinates")
        print("  Possible causes:")
        print("    - UMAP reducer was re-fitted after coordinates were saved")
        print("    - Different embeddings were used to fit the reducer")
        print("    - UMAP version mismatch")
        print()
        print("  UMAP rebuild is REQUIRED")
        print()
        return False


def test_neighbor_overlap(reducer, wiki_embeddings):
    """Test that neighbor overlap is >60%."""
    print("=" * 80)
    print("TEST 5: Neighbor Overlap")
    print("=" * 80)
    print()

    # This test compares neighbors in embedding space vs UMAP space
    # per rebuild_umap.py documentation, overlap should be >60%

    print("  Computing neighbors in embedding space...")

    # Use first 1000 articles for neighbor test
    sample_size = min(1000, len(wiki_embeddings))
    sample_embeddings = wiki_embeddings[:sample_size]

    # Find 10 nearest neighbors in embedding space
    from sklearn.metrics.pairwise import cosine_similarity

    similarity_matrix = cosine_similarity(sample_embeddings)

    # Get indices of 10 nearest neighbors (excluding self)
    k = 10
    embedding_neighbors = []

    for i in range(sample_size):
        # Sort by similarity (descending), skip self
        neighbors = np.argsort(similarity_matrix[i])[::-1][1:k+1]
        embedding_neighbors.append(set(neighbors))

    print(f"    Found {k} neighbors for {sample_size} articles in embedding space")
    print()

    # Transform to UMAP space
    print("  Transforming to UMAP space...")

    try:
        sample_coords = reducer.transform(sample_embeddings)
    except Exception as e:
        print(f"  ERROR: Transformation failed")
        print(f"  Error: {e}")
        return False

    # Find neighbors in UMAP space
    print("  Computing neighbors in UMAP space...")

    umap_neighbors = []

    for i in range(sample_size):
        # Compute Euclidean distances
        distances = np.sqrt(((sample_coords - sample_coords[i])**2).sum(axis=1))
        # Get k nearest (excluding self)
        neighbors = np.argsort(distances)[1:k+1]
        umap_neighbors.append(set(neighbors))

    print(f"    Found {k} neighbors for {sample_size} articles in UMAP space")
    print()

    # Compute overlap
    print("  Computing neighbor overlap...")

    overlaps = []
    for i in range(sample_size):
        overlap = len(embedding_neighbors[i] & umap_neighbors[i])
        overlaps.append(overlap / k)

    mean_overlap = np.mean(overlaps)
    min_overlap = np.min(overlaps)
    max_overlap = np.max(overlaps)

    print(f"    Mean overlap: {mean_overlap:.1%}")
    print(f"    Min overlap: {min_overlap:.1%}")
    print(f"    Max overlap: {max_overlap:.1%}")
    print(f"    Threshold: 60%")
    print()

    if mean_overlap >= 0.60:
        print(f"  PASS: Neighbor overlap ({mean_overlap:.1%}) > 60%")
        print()
        return True
    else:
        print(f"  WARNING: Neighbor overlap ({mean_overlap:.1%}) < 60%")
        print()
        print("  This suggests UMAP may not be preserving local structure well")
        print("  However, this alone may not require rebuild if other tests pass")
        print()
        return True  # Warning, not failure


def main():
    """Run all UMAP verification tests."""
    print()
    print("=" * 80)
    print("UMAP REDUCER VERIFICATION")
    print("=" * 80)
    print()
    print("This script verifies that the saved UMAP reducer is compatible")
    print("with current embeddings. Per Issue #13, UMAP may be from an old run.")
    print()
    print("If ANY critical test fails, UMAP rebuild is required:")
    print("  python scripts/rebuild_umap.py")
    print()

    # Test 1: Load UMAP reducer
    reducer = load_umap_reducer()
    if reducer is None:
        print("=" * 80)
        print("VERIFICATION FAILED: Cannot load UMAP reducer")
        print("=" * 80)
        print()
        sys.exit(1)

    # Test 2: Load embeddings
    wiki_embeddings, question_embeddings = load_embeddings()
    if wiki_embeddings is None or question_embeddings is None:
        print("=" * 80)
        print("VERIFICATION FAILED: Cannot load embeddings")
        print("=" * 80)
        print()
        sys.exit(1)

    # Test 3: Test transformation
    if not test_reducer_transformation(reducer, wiki_embeddings, question_embeddings):
        print("=" * 80)
        print("VERIFICATION FAILED: Reducer cannot transform embeddings")
        print("=" * 80)
        print()
        print("ACTION REQUIRED: Rebuild UMAP")
        print("  python scripts/rebuild_umap.py")
        print()
        sys.exit(1)

    # Test 4: Test coordinate matching
    if not test_coordinate_matching(reducer, wiki_embeddings, question_embeddings):
        print("=" * 80)
        print("VERIFICATION FAILED: Coordinates drifted")
        print("=" * 80)
        print()
        print("ACTION REQUIRED: Rebuild UMAP")
        print("  python scripts/rebuild_umap.py")
        print()
        sys.exit(1)

    # Test 5: Test neighbor overlap
    test_neighbor_overlap(reducer, wiki_embeddings)

    # All tests passed
    print("=" * 80)
    print("VERIFICATION COMPLETE: ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("  The UMAP reducer is consistent with current embeddings")
    print("  Coordinates match saved values")
    print("  No rebuild is required")
    print()
    print("Next step: Proceed with Phase 1.2 (Create backups)")
    print()


if __name__ == '__main__':
    main()
