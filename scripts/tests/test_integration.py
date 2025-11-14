#!/usr/bin/env python3
"""
Quick integration test - verify generate_cell_labels works with repaired embeddings.
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
    repair_embedding,
    recover_tokens_from_embedding,
    filter_tokens
)
import numpy as np


def test_full_pipeline():
    """
    Test full pipeline: invert → validate → repair → recover tokens.
    """
    print("="*70)
    print("Full Pipeline Integration Test")
    print("="*70)

    # Load data
    umap_reducer = load_umap_model()
    bounds = load_umap_bounds()
    questions = load_questions()
    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    # Test on a few cells from different regions
    test_cells = [
        (0.125, 0.125, "Corner: bottom-left"),
        (0.875, 0.875, "Corner: top-right"),
        (0.5, 0.5, "Center"),
    ]

    for x_norm, y_norm, label in test_cells:
        print(f"\n{'='*70}")
        print(f"Testing: {label}")
        print(f"Normalized coords: ({x_norm:.3f}, {y_norm:.3f})")
        print(f"{'='*70}")

        # Step 1: Invert UMAP
        embedding, quality = invert_umap_coordinates(x_norm, y_norm, umap_reducer, bounds)
        print(f"\n1. UMAP Inverse Transform:")
        print(f"   Quality score: {quality:.3f}")
        print(f"   Embedding norm: {np.linalg.norm(embedding):.2e}")

        # Step 2: Validate
        is_valid, diagnostics = validate_embedding(embedding, reference_embeddings)
        print(f"\n2. Validation:")
        print(f"   Valid: {is_valid}")
        print(f"   Norm z-score: {diagnostics.get('norm_z_score', 'N/A'):.2e}")
        if 'max_value_z_score' in diagnostics:
            print(f"   Max element z-score: {diagnostics['max_value_z_score']:.2f}")
        if 'needs_repair' in diagnostics:
            print(f"   Reason: {diagnostics['needs_repair']}")

        # Step 3: Repair if needed
        if not is_valid:
            repaired, repair_log = repair_embedding(embedding, reference_embeddings, quality)
            print(f"\n3. Repair:")
            for msg in repair_log:
                print(f"   - {msg}")

            # Re-validate
            is_valid_repaired, diag_repaired = validate_embedding(repaired, reference_embeddings)
            print(f"   Post-repair valid: {is_valid_repaired}")
            if is_valid_repaired:
                print(f"   ✅ Repair successful!")
                embedding = repaired
            else:
                print(f"   ⚠️  Still invalid after repair")
                continue
        else:
            print(f"\n3. Repair: Not needed (already valid)")

        # Step 4: Recover tokens
        tokens, metadata = recover_tokens_from_embedding(embedding)
        print(f"\n4. Token Recovery:")
        print(f"   Method: {metadata['method']}")
        print(f"   Raw tokens: {len(tokens)}")

        # Step 5: Filter tokens
        filtered = filter_tokens(tokens, max_tokens=10)
        print(f"\n5. Filtered Tokens (top 10):")
        for i, (word, weight) in enumerate(filtered[:10], 1):
            print(f"   {i:2d}. {word:<20} ({weight:.3f})")

        if not filtered:
            print(f"   (No tokens after filtering)")

    print(f"\n{'='*70}")
    print("✅ Integration test complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    test_full_pipeline()
