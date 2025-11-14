#!/usr/bin/env python3
"""
Systematic diagnosis of the cell label generation pipeline.

Tests each stage:
1. UMAP inverse transform quality
2. Vec2text token recovery quality
3. GPT-OSS label generation quality
4. Overall label diversity and spatial distribution
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
    load_umap_model,
    load_umap_bounds,
    invert_umap_coordinates,
    validate_embedding,
    repair_embedding,
    recover_tokens_from_embedding,
)

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def test_umap_inversion():
    """Test if UMAP inverse transform is recovering reasonable embeddings."""
    print_section("PHASE 1: UMAP Inverse Transform Quality")

    # Load data
    questions = load_questions('questions.json')
    reducer = load_umap_model('umap_reducer.pkl')
    bounds = load_umap_bounds('umap_bounds.pkl')

    print(f"\nLoaded {len(questions)} questions")
    print(f"Embedding dimension: {len(questions[0]['embedding_full'])}")

    # Test 1: Roundtrip accuracy for actual question coordinates
    print("\n" + "-" * 80)
    print("TEST 1A: Roundtrip Accuracy (Question Coordinates)")
    print("-" * 80)

    roundtrip_errors = []
    cosine_sims = []

    for i, q in enumerate(questions):
        # Forward: embedding → 2D
        original_embedding = np.array(q['embedding_full'])

        # Inverse: 2D → embedding
        recovered_embedding, quality_score = invert_umap_coordinates(
            q['x'], q['y'], reducer, bounds
        )

        # Compare
        cos_sim = cosine_similarity(
            original_embedding.reshape(1, -1),
            recovered_embedding.reshape(1, -1)
        )[0, 0]

        l2_error = np.linalg.norm(original_embedding - recovered_embedding)

        roundtrip_errors.append(l2_error)
        cosine_sims.append(cos_sim)

        if i < 3:  # Show first 3 in detail
            print(f"\nQuestion {i+1}: {q['question'][:60]}...")
            print(f"  Cosine similarity: {cos_sim:.4f}")
            print(f"  L2 error: {l2_error:.2f}")
            print(f"  Quality score: {quality_score:.4f}")

    print(f"\n📊 Summary Statistics:")
    print(f"  Mean cosine similarity: {np.mean(cosine_sims):.4f} (want close to 1.0)")
    print(f"  Min cosine similarity: {np.min(cosine_sims):.4f}")
    print(f"  Mean L2 error: {np.mean(roundtrip_errors):.2f}")

    # Test 1B: Cells near questions
    print("\n" + "-" * 80)
    print("TEST 1B: Cells Near Questions")
    print("-" * 80)
    print("Testing if cells close to questions recover similar embeddings")

    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    for i in range(min(3, len(questions))):
        q = questions[i]
        print(f"\nNear Question {i+1}: {q['question'][:60]}...")

        # Test cell slightly offset from question
        offset = 0.05  # 5% offset
        test_x = q['x'] + offset * (0.5 - q['x'])  # Move 5% toward center
        test_y = q['y'] + offset * (0.5 - q['y'])

        recovered, quality = invert_umap_coordinates(test_x, test_y, reducer, bounds)

        # Validate
        is_valid, diagnostics = validate_embedding(recovered, reference_embeddings)

        if not is_valid:
            print(f"  ⚠️  Invalid embedding - needs repair")
            print(f"     Reason: {diagnostics.get('needs_repair', 'unknown')}")
            recovered, repair_log = repair_embedding(recovered, reference_embeddings, quality)
            for log in repair_log:
                print(f"     {log}")

        # Compare to original question
        original = np.array(q['embedding_full'])
        cos_sim = cosine_similarity(original.reshape(1, -1), recovered.reshape(1, -1))[0, 0]

        print(f"  Similarity to original question: {cos_sim:.4f}")
        print(f"  Quality score: {quality:.4f}")

    # Test 1C: Cells between questions
    print("\n" + "-" * 80)
    print("TEST 1C: Cells Between Questions")
    print("-" * 80)
    print("Testing if midpoint cells recover embeddings between the two questions")

    if len(questions) >= 2:
        q1, q2 = questions[0], questions[1]

        print(f"\nBetween:")
        print(f"  Q1: {q1['question'][:50]}...")
        print(f"  Q2: {q2['question'][:50]}...")

        # Midpoint
        mid_x = (q1['x'] + q2['x']) / 2
        mid_y = (q1['y'] + q2['y']) / 2

        recovered, quality = invert_umap_coordinates(mid_x, mid_y, reducer, bounds)

        # Validate & repair if needed
        is_valid, diagnostics = validate_embedding(recovered, reference_embeddings)
        if not is_valid:
            recovered, _ = repair_embedding(recovered, reference_embeddings, quality)

        # Compare to both questions
        emb1 = np.array(q1['embedding_full'])
        emb2 = np.array(q2['embedding_full'])

        sim_to_q1 = cosine_similarity(emb1.reshape(1, -1), recovered.reshape(1, -1))[0, 0]
        sim_to_q2 = cosine_similarity(emb2.reshape(1, -1), recovered.reshape(1, -1))[0, 0]

        # Also check if it's between them (cosine to average)
        avg_embedding = (emb1 + emb2) / 2
        sim_to_avg = cosine_similarity(avg_embedding.reshape(1, -1), recovered.reshape(1, -1))[0, 0]

        print(f"\n  Similarity to Q1: {sim_to_q1:.4f}")
        print(f"  Similarity to Q2: {sim_to_q2:.4f}")
        print(f"  Similarity to average: {sim_to_avg:.4f}")
        print(f"  Quality score: {quality:.4f}")

        if sim_to_avg > max(sim_to_q1, sim_to_q2):
            print(f"  ✅ Midpoint embedding is closer to average than to either endpoint")
        else:
            print(f"  ⚠️  Midpoint embedding may not be interpolating correctly")

    return np.mean(cosine_sims)

def test_vec2text_recovery():
    """Test if vec2text is recovering sensible text."""
    print_section("PHASE 2: Vec2text Token Recovery Quality")

    questions = load_questions('questions.json')
    reducer = load_umap_model('umap_reducer.pkl')
    bounds = load_umap_bounds('umap_bounds.pkl')
    reference_embeddings = np.array([q['embedding_full'] for q in questions])

    print("\nTesting vec2text recovery for question coordinates...\n")

    for i in range(min(3, len(questions))):
        q = questions[i]
        print("-" * 80)
        print(f"Question {i+1}: {q['question']}")
        print(f"Position: ({q['x']:.3f}, {q['y']:.3f})")

        # Recover embedding
        recovered_emb, quality = invert_umap_coordinates(q['x'], q['y'], reducer, bounds)

        # Validate & repair
        is_valid, _ = validate_embedding(recovered_emb, reference_embeddings)
        if not is_valid:
            recovered_emb, _ = repair_embedding(recovered_emb, reference_embeddings, quality)

        # Vec2text recovery
        print("\nRecovering text via vec2text...")
        tokens, metadata = recover_tokens_from_embedding(
            recovered_emb,
            model_name='sentence-transformers/gtr-t5-base'
        )

        print(f"\n✅ Recovered text:")
        print(f"   \"{metadata['recovered_text']}\"")

        print(f"\n📝 Top tokens:")
        for word, weight in tokens[:10]:
            print(f"   - {word}: {weight:.3f}")

        # Check if recovered text has any overlap with question
        question_words = set(q['question'].lower().split())
        recovered_words = set(metadata['recovered_text'].lower().split())
        overlap = question_words & recovered_words

        print(f"\n🔍 Word overlap with original question: {len(overlap)} words")
        if overlap:
            print(f"   Common words: {', '.join(list(overlap)[:5])}")
        else:
            print(f"   ⚠️  No word overlap - vec2text may not be recovering semantic content")

    # Test nearby cells
    print("\n" + "=" * 80)
    print("Testing vec2text for cells near same question...")
    print("=" * 80)

    q = questions[0]
    print(f"\nBase question: {q['question']}")

    recovered_texts = []
    for offset_factor in [0.0, 0.02, 0.05]:
        test_x = q['x'] + offset_factor * (0.5 - q['x'])
        test_y = q['y'] + offset_factor * (0.5 - q['y'])

        recovered_emb, quality = invert_umap_coordinates(test_x, test_y, reducer, bounds)
        is_valid, _ = validate_embedding(recovered_emb, reference_embeddings)
        if not is_valid:
            recovered_emb, _ = repair_embedding(recovered_emb, reference_embeddings, quality)

        tokens, metadata = recover_tokens_from_embedding(recovered_emb)
        recovered_texts.append(metadata['recovered_text'])

        print(f"\nOffset {offset_factor:.0%}: \"{metadata['recovered_text'][:80]}...\"")

    # Check similarity
    print(f"\n🔍 Checking if nearby cells produce similar text...")
    if recovered_texts[0] == recovered_texts[1] == recovered_texts[2]:
        print(f"   ⚠️  All cells produce identical text - may indicate caching or quantization issues")
    else:
        print(f"   ✅ Nearby cells produce varied text")

def test_label_generation():
    """Test GPT-OSS label generation (if LM Studio is running)."""
    print_section("PHASE 3: GPT-OSS Label Generation Quality")

    from generate_cell_labels import call_lm_studio_api

    print("\nTesting if LM Studio is accessible...")

    try:
        test_prompt = "Generate a 2-4 word label for: cellular respiration and energy production"
        label, metadata = call_lm_studio_api(test_prompt, max_tokens=10)

        print(f"✅ LM Studio is running and accessible")
        print(f"   Test label: \"{label}\"")
        print(f"   Label length: {len(label.split())} words")

        # Test with vec2text output
        print("\n" + "-" * 80)
        print("Testing label generation from vec2text output...")
        print("-" * 80)

        test_texts = [
            "mitochondria powerhouse cell energy ATP production cellular respiration",
            "photosynthesis chloroplast sunlight energy plant cells green",
            "DNA genetic information heredity chromosome nucleus replication"
        ]

        for text in test_texts:
            prompt = f"Based on this text: \"{text}\", generate a 2-4 word label describing the main topic."
            label, _ = call_lm_studio_api(prompt, max_tokens=10)

            print(f"\nInput: {text[:60]}...")
            print(f"Label: \"{label}\"")
            print(f"Words: {len(label.split())}")

            if len(label.split()) > 4:
                print(f"   ⚠️  Label too long ({len(label.split())} words)")

    except Exception as e:
        print(f"❌ LM Studio not accessible: {e}")
        print(f"   Labels will be empty unless LM Studio is running on port 1234")

def test_label_diversity():
    """Test label diversity using existing generated labels."""
    print_section("PHASE 4: Label Diversity Analysis")

    try:
        with open('heatmap_cell_labels.json') as f:
            data = json.load(f)

        cells = data['cells']
        grid_size = data['metadata']['grid_size']

        print(f"\nAnalyzing {len(cells)} labels from {grid_size}x{grid_size} grid...")

        # Extract labels
        labels = [cell.get('label', '') for cell in cells]
        non_empty_labels = [l for l in labels if l and l.strip()]

        print(f"\n📊 Basic Statistics:")
        print(f"  Total cells: {len(cells)}")
        print(f"  Non-empty labels: {len(non_empty_labels)}")
        print(f"  Empty labels: {len(labels) - len(non_empty_labels)}")

        # Label frequency
        from collections import Counter
        label_counts = Counter(non_empty_labels)

        print(f"\n🎯 Label Diversity:")
        print(f"  Unique labels: {len(label_counts)}")
        print(f"  Diversity ratio: {len(label_counts) / len(non_empty_labels):.2%}")

        # Most common labels
        print(f"\n📈 Most common labels:")
        for label, count in label_counts.most_common(10):
            pct = count / len(non_empty_labels) * 100
            print(f"  \"{label}\": {count} cells ({pct:.1f}%)")

        # Check spatial clustering of duplicate labels
        print(f"\n🗺️  Spatial Distribution of Duplicate Labels:")
        for label, count in label_counts.most_common(5):
            if count > 1:
                # Find cells with this label
                cell_positions = [(c['gx'], c['gy']) for c in cells if c.get('label') == label]

                # Calculate average distance between cells with same label
                if len(cell_positions) > 1:
                    distances = []
                    for i in range(len(cell_positions)):
                        for j in range(i+1, len(cell_positions)):
                            dx = cell_positions[i][0] - cell_positions[j][0]
                            dy = cell_positions[i][1] - cell_positions[j][1]
                            dist = np.sqrt(dx*dx + dy*dy)
                            distances.append(dist)

                    avg_dist = np.mean(distances)
                    max_possible_dist = np.sqrt(2 * grid_size**2)

                    print(f"\n  \"{label}\" ({count} cells):")
                    print(f"    Positions: {cell_positions[:5]}{'...' if len(cell_positions) > 5 else ''}")
                    print(f"    Avg distance: {avg_dist:.1f} (out of {max_possible_dist:.1f} max)")

                    if avg_dist < grid_size / 4:
                        print(f"    ✅ Labels are spatially clustered")
                    else:
                        print(f"    ⚠️  Labels are scattered - may indicate poor specificity")

    except FileNotFoundError:
        print("\n❌ No cell labels file found")
        print("   Run: python generate_cell_labels.py --grid-size 3 first")

def main():
    print("\n" + "=" * 80)
    print("CELL LABEL GENERATION PIPELINE DIAGNOSTICS")
    print("=" * 80)
    print("\nThis script tests each stage of the pipeline to identify issues:")
    print("  1. UMAP inverse transform quality")
    print("  2. Vec2text token recovery quality")
    print("  3. GPT-OSS label generation quality")
    print("  4. Label diversity and spatial distribution")

    # Run all tests
    umap_quality = test_umap_inversion()
    test_vec2text_recovery()
    test_label_generation()
    test_label_diversity()

    # Final summary
    print_section("DIAGNOSIS SUMMARY")
    print(f"\n✅ UMAP Roundtrip Quality: {umap_quality:.4f} cosine similarity")
    print(f"   (Target: >0.9 for good quality, >0.7 acceptable)")

    print(f"\n📝 Check the detailed output above for:")
    print(f"  - Vec2text recovery quality (word overlap, semantic coherence)")
    print(f"  - Label generation quality (length, format, relevance)")
    print(f"  - Label diversity (uniqueness, spatial clustering)")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
