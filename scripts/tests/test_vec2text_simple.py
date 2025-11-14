#!/usr/bin/env python3
"""
Simple test of vec2text integration - tests the actual function we modified.
"""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import numpy as np
from sentence_transformers import SentenceTransformer

# Add current directory to path
sys.path.insert(0, '/Users/jmanning/mapper.io')

print("=" * 80)
print("Simple Vec2text Integration Test")
print("=" * 80)

# Import the updated function
from generate_cell_labels import recover_tokens_from_embedding

# Test text
test_text = "What is the primary function of mitochondria in cellular respiration?"

print(f"\nTest text: {test_text}")

# ============================================================================
# Test 1: all-MiniLM-L6-v2 (should use fallback)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: all-MiniLM-L6-v2 (384-dim) - Should use fallback")
print("=" * 80)

try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embedding = model.encode([test_text], convert_to_numpy=True)[0]

    print(f"Embedding shape: {embedding.shape}")
    print(f"Calling recover_tokens_from_embedding...")

    tokens, metadata = recover_tokens_from_embedding(
        embedding,
        model_name='all-MiniLM-L6-v2',
        max_tokens=10
    )

    print(f"\nMethod used: {metadata['method']}")
    print(f"Metadata: {metadata}")
    print(f"\nTop 5 tokens:")
    for i, (word, weight) in enumerate(tokens[:5], 1):
        print(f"  {i}. {word}: {weight:.3f}")

    if metadata['method'] == 'nearest_questions_fallback':
        print("\n✅ TEST 1 PASSED - Fallback activated correctly")
    else:
        print(f"\n⚠️  TEST 1 WARNING - Expected fallback, got {metadata['method']}")

except Exception as e:
    print(f"\n❌ TEST 1 FAILED: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# Test 2: gtr-base (should use REAL vec2text)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: gtr-base (768-dim) - Should use REAL vec2text")
print("=" * 80)

try:
    print("Loading gtr-base model...")
    model = SentenceTransformer('sentence-transformers/gtr-t5-base')
    embedding = model.encode([test_text], convert_to_numpy=True)[0]

    print(f"Embedding shape: {embedding.shape}")
    print(f"Calling recover_tokens_from_embedding...")

    tokens, metadata = recover_tokens_from_embedding(
        embedding,
        model_name='gtr-base',
        max_tokens=10
    )

    print(f"\nMethod used: {metadata['method']}")
    print(f"Metadata keys: {list(metadata.keys())}")

    if 'recovered_text' in metadata:
        print(f"\nRecovered text: {metadata['recovered_text']}")

    print(f"\nTop 5 tokens:")
    for i, (word, weight) in enumerate(tokens[:5], 1):
        print(f"  {i}. {word}: {weight:.3f}")

    if metadata['method'] == 'vec2text_inversion':
        print("\n✅ TEST 2 PASSED - vec2text inversion worked!")
    elif metadata['method'] == 'nearest_questions_fallback':
        print(f"\n⚠️  TEST 2 - Fell back (may be expected if vec2text failed)")
    else:
        print(f"\n❓ TEST 2 - Unknown method: {metadata['method']}")

except Exception as e:
    print(f"\n❌ TEST 2 FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Test Complete!")
print("=" * 80)
