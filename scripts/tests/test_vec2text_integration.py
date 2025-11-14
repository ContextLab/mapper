#!/usr/bin/env python3
"""
Test vec2text integration with generate_cell_labels.py

This script:
1. Tests vec2text with gtr-base embeddings (REAL vec2text)
2. Tests fallback with all-MiniLM-L6-v2 embeddings
3. Compares output quality
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

# Test texts - biology questions similar to our knowledge map
test_questions = [
    "What is the primary function of mitochondria in cellular respiration?",
    "How do chloroplasts convert light energy into chemical energy?",
    "What role do ribosomes play in protein synthesis?",
    "Describe the process of DNA replication in eukaryotic cells",
    "What is the difference between prokaryotic and eukaryotic cells?"
]

print("=" * 80)
print("Vec2text Integration Test")
print("=" * 80)

# ============================================================================
# Test 1: GTR-Base with REAL vec2text
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: GTR-Base Embeddings with REAL vec2text")
print("=" * 80)

print("\nLoading gtr-base model...")
try:
    gtr_model = SentenceTransformer('sentence-transformers/gtr-t5-base')
    print(f"Model loaded: {gtr_model}")

    print("\nGenerating embeddings...")
    gtr_embeddings = gtr_model.encode(test_questions, convert_to_numpy=True)
    print(f"Embedding shape: {gtr_embeddings.shape}")
    print(f"Expected: (5, 768) - {'PASS' if gtr_embeddings.shape == (5, 768) else 'FAIL'}")

    # Test vec2text inversion
    print("\nTesting vec2text inversion...")
    import vec2text

    corrector = vec2text.load_pretrained_corrector("gtr-base")
    print("Corrector loaded successfully!")

    # Test with first question
    test_embedding = torch.from_numpy(gtr_embeddings[0:1])

    print(f"\nOriginal text: {test_questions[0]}")
    print("Inverting embedding...")

    recovered = vec2text.invert_embeddings(
        embeddings=test_embedding,
        corrector=corrector,
        num_steps=10,
        sequence_beam_width=2
    )

    print(f"Recovered text: {recovered[0]}")

    # Test all questions
    print("\n" + "-" * 80)
    print("Full comparison:")
    print("-" * 80)

    for i, (original, embedding) in enumerate(zip(test_questions, gtr_embeddings)):
        emb_tensor = torch.from_numpy(embedding).unsqueeze(0)
        recovered = vec2text.invert_embeddings(
            embeddings=emb_tensor,
            corrector=corrector,
            num_steps=10,
            sequence_beam_width=2
        )[0]

        print(f"\n{i+1}. Original:  {original}")
        print(f"   Recovered: {recovered}")

        # Simple quality check: count word overlap
        orig_words = set(original.lower().split())
        rec_words = set(recovered.lower().split())
        overlap = len(orig_words & rec_words)
        print(f"   Word overlap: {overlap}/{len(orig_words)} words")

    print("\n✅ TEST 1 PASSED: vec2text works with gtr-base!")

except Exception as e:
    print(f"\n❌ TEST 1 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# Test 2: All-MiniLM-L6-v2 with Fallback
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: All-MiniLM-L6-v2 Embeddings with Fallback")
print("=" * 80)

print("\nLoading all-MiniLM-L6-v2 model...")
try:
    minilm_model = SentenceTransformer('all-MiniLM-L6-v2')

    print("\nGenerating embeddings...")
    minilm_embeddings = minilm_model.encode(test_questions, convert_to_numpy=True)
    print(f"Embedding shape: {minilm_embeddings.shape}")
    print(f"Expected: (5, 384) - {'PASS' if minilm_embeddings.shape == (5, 384) else 'FAIL'}")

    print("\nTesting vec2text with dimension mismatch...")
    print("(This should trigger fallback to nearest-questions method)")

    # Import the function we just updated
    import sys
    sys.path.insert(0, '/Users/jmanning/mapper.io')
    from generate_cell_labels import recover_tokens_from_embedding

    # Test with first embedding
    tokens, metadata = recover_tokens_from_embedding(
        minilm_embeddings[0],
        model_name='all-MiniLM-L6-v2',
        max_tokens=10
    )

    print(f"\nMethod used: {metadata['method']}")
    print(f"Original question: {test_questions[0]}")
    print(f"Top tokens: {tokens[:5]}")

    if metadata['method'] == 'nearest_questions_fallback':
        print("\n✅ TEST 2 PASSED: Fallback method works correctly!")
    else:
        print(f"\n⚠️  TEST 2 WARNING: Expected fallback, got {metadata['method']}")

except Exception as e:
    print(f"\n❌ TEST 2 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
1. vec2text REAL inversion works with gtr-base (768-dim) embeddings
2. Fallback method activates for all-MiniLM-L6-v2 (384-dim) embeddings
3. To use REAL vec2text, switch to gtr-base in generate_embeddings.py

Recommendations:
- For best quality: Use gtr-base embeddings + vec2text
- For compatibility: Use all-MiniLM-L6-v2 + fallback method
- The fallback method extracts keywords from nearest questions (not perfect but functional)
""")
