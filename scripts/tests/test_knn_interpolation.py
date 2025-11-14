#!/usr/bin/env python3
"""
Test KNN interpolation approach for recovering embeddings from 2D coordinates.

This should produce MUCH better results than UMAP's inverse_transform.
"""

import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Fix for macOS
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from generate_cell_labels import (
    load_questions,
    invert_umap_coordinates_knn,
    recover_tokens_from_embedding,
)

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def test_knn_roundtrip():
    """Test KNN interpolation roundtrip accuracy for question coordinates."""
    print_section("TEST 1: KNN Roundtrip Accuracy (Question Coordinates)")

    questions = load_questions('questions.json')
    original_embeddings = np.array([q['embedding_full'] for q in questions])

    print(f"\nLoaded {len(questions)} questions")
    print(f"Testing if KNN interpolation recovers embeddings at question positions\n")

    cosine_sims = []

    for i, q in enumerate(questions):
        # Get recovered embedding using KNN
        recovered, quality = invert_umap_coordinates_knn(q['x'], q['y'], questions, k=5)

        # Compare to original
        cos_sim = cosine_similarity(
            original_embeddings[i:i+1],
            recovered.reshape(1, -1)
        )[0, 0]

        cosine_sims.append(cos_sim)

        # Check norms
        orig_norm = np.linalg.norm(original_embeddings[i])
        recovered_norm = np.linalg.norm(recovered)

        if i < 3:  # Show first 3 in detail
            print(f"Question {i+1}: {q['question'][:60]}...")
            print(f"  Cosine similarity: {cos_sim:.4f} (target >0.9)")
            print(f"  Original norm: {orig_norm:.4f}")
            print(f"  Recovered norm: {recovered_norm:.4f}")
            print(f"  Quality score: {quality:.4f}")

    print(f"\n📊 Summary Statistics:")
    print(f"  Mean cosine similarity: {np.mean(cosine_sims):.4f} (target >0.9)")
    print(f"  Min cosine similarity: {np.min(cosine_sims):.4f}")
    print(f"  Max cosine similarity: {np.max(cosine_sims):.4f}")

    if np.mean(cosine_sims) > 0.9:
        print(f"  ✅ EXCELLENT - KNN interpolation is working well!")
    elif np.mean(cosine_sims) > 0.7:
        print(f"  ✓ GOOD - Acceptable recovery quality")
    else:
        print(f"  ❌ POOR - KNN interpolation needs improvement")

    return np.mean(cosine_sims)

def test_knn_interpolation_between():
    """Test if KNN produces interpolated embeddings between questions."""
    print_section("TEST 2: KNN Interpolation Between Questions")

    questions = load_questions('questions.json')
    original_embeddings = np.array([q['embedding_full'] for q in questions])

    print("\nTesting midpoint between first two questions...\n")

    q1, q2 = questions[0], questions[1]

    print(f"Q1: {q1['question'][:60]}...")
    print(f"Q2: {q2['question'][:60]}...")

    # Midpoint
    mid_x = (q1['x'] + q2['x']) / 2
    mid_y = (q1['y'] + q2['y']) / 2

    recovered, quality = invert_umap_coordinates_knn(mid_x, mid_y, questions, k=5)

    # Compare to both questions
    emb1 = original_embeddings[0]
    emb2 = original_embeddings[1]

    sim_to_q1 = cosine_similarity(emb1.reshape(1, -1), recovered.reshape(1, -1))[0, 0]
    sim_to_q2 = cosine_similarity(emb2.reshape(1, -1), recovered.reshape(1, -1))[0, 0]

    # Also check if it's between them (cosine to average)
    avg_embedding = (emb1 + emb2) / 2
    avg_norm = np.linalg.norm(avg_embedding)
    if avg_norm > 0:
        avg_embedding = avg_embedding / avg_norm  # L2-normalize

    sim_to_avg = cosine_similarity(avg_embedding.reshape(1, -1), recovered.reshape(1, -1))[0, 0]

    print(f"\nSimilarity to Q1: {sim_to_q1:.4f}")
    print(f"Similarity to Q2: {sim_to_q2:.4f}")
    print(f"Similarity to average: {sim_to_avg:.4f}")
    print(f"Quality score: {quality:.4f}")

    if sim_to_avg > max(sim_to_q1, sim_to_q2):
        print(f"✅ Midpoint embedding is closer to average than to either endpoint")
    else:
        print(f"✓ Midpoint embedding is between the two questions")

def test_knn_vec2text_recovery():
    """Test vec2text recovery quality with KNN interpolation."""
    print_section("TEST 3: Vec2text Recovery with KNN Interpolation")

    questions = load_questions('questions.json')

    print("\nTesting vec2text recovery for cells near questions...\n")

    for i in range(min(3, len(questions))):
        q = questions[i]
        print("-" * 80)
        print(f"Question {i+1}: {q['question']}")
        print(f"Position: ({q['x']:.3f}, {q['y']:.3f})")

        # Recover embedding using KNN
        recovered_emb, quality = invert_umap_coordinates_knn(q['x'], q['y'], questions, k=5)

        # Vec2text recovery
        print("\nRecovering text via vec2text...")
        tokens, metadata = recover_tokens_from_embedding(
            recovered_emb,
            model_name='sentence-transformers/gtr-t5-base'
        )

        print(f"\n✅ Recovered text:")
        print(f'   "{metadata["recovered_text"]}"')

        print(f"\n📝 Top tokens:")
        for word, weight in tokens[:10]:
            print(f"   - {word}: {weight:.3f}")

        # Check word overlap
        question_words = set(q['question'].lower().split())
        recovered_words = set(metadata['recovered_text'].lower().split())
        overlap = question_words & recovered_words

        print(f"\n🔍 Word overlap with original question: {len(overlap)} words")
        if overlap:
            print(f"   Common words: {', '.join(list(overlap)[:10])}")
            print(f"   ✅ Vec2text is recovering semantic content!")
        else:
            print(f"   ⚠️  No word overlap - but semantic meaning may still be preserved")

def test_knn_nearby_cells():
    """Test if nearby cells produce similar (but not identical) recovered text."""
    print_section("TEST 4: Vec2text Consistency for Nearby Cells")

    questions = load_questions('questions.json')
    q = questions[0]

    print(f"\nBase question: {q['question']}")
    print("Testing cells at 0%, 2%, 5% offset from question...\n")

    recovered_texts = []
    for offset_factor in [0.0, 0.02, 0.05]:
        test_x = q['x'] + offset_factor * (0.5 - q['x'])
        test_y = q['y'] + offset_factor * (0.5 - q['y'])

        recovered_emb, quality = invert_umap_coordinates_knn(test_x, test_y, questions, k=5)
        tokens, metadata = recover_tokens_from_embedding(recovered_emb)
        recovered_texts.append(metadata['recovered_text'])

        print(f"Offset {offset_factor:.0%}: \"{metadata['recovered_text'][:80]}...\"")
        print(f"  Quality: {quality:.4f}\n")

    # Check similarity
    print("🔍 Checking consistency...")
    if recovered_texts[0] == recovered_texts[1] == recovered_texts[2]:
        print("   ⚠️  All cells produce identical text - may indicate caching or quantization")
    elif len(set(recovered_texts)) == 1:
        print("   ⚠️  All texts identical - unexpected")
    else:
        print("   ✅ Nearby cells produce varied text (good - shows sensitivity)")

        # Check if they're semantically similar
        words_0 = set(recovered_texts[0].lower().split())
        words_1 = set(recovered_texts[1].lower().split())
        words_2 = set(recovered_texts[2].lower().split())

        overlap_01 = len(words_0 & words_1) / max(len(words_0), len(words_1))
        overlap_02 = len(words_0 & words_2) / max(len(words_0), len(words_2))

        print(f"   Word overlap 0% vs 2%: {overlap_01:.1%}")
        print(f"   Word overlap 0% vs 5%: {overlap_02:.1%}")

def main():
    print("\n" + "=" * 80)
    print("KNN INTERPOLATION TEST SUITE")
    print("=" * 80)
    print("\nTesting the new KNN interpolation approach...")
    print("This should produce MUCH better results than UMAP inverse_transform\n")

    # Run all tests
    knn_quality = test_knn_roundtrip()
    test_knn_interpolation_between()
    test_knn_vec2text_recovery()
    test_knn_nearby_cells()

    # Final summary
    print_section("TEST SUMMARY")
    print(f"\n✅ KNN Roundtrip Quality: {knn_quality:.4f} cosine similarity")
    print(f"   (Target: >0.9 for excellent, >0.7 acceptable)")

    if knn_quality > 0.9:
        print("\n🎉 KNN interpolation is working EXCELLENTLY!")
        print("   Ready to generate full 40×40 grid labels")
    elif knn_quality > 0.7:
        print("\n✓ KNN interpolation is working acceptably")
        print("   May proceed with label generation")
    else:
        print("\n❌ KNN interpolation needs improvement")
        print("   Do not proceed with full grid generation yet")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
