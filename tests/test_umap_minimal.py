#!/usr/bin/env python3
"""
Minimal test of UMAP transform with correct 768-dim embeddings.
"""

import os
import pickle
import numpy as np

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

print("Loading UMAP reducer...")
with open('data/umap_reducer.pkl', 'rb') as f:
    umap_reducer = pickle.load(f)

print(f"UMAP expects: {umap_reducer._raw_data.shape[1]}-dim input")

# Test 1: Single random 768-dim vector
print("\nTest 1: Single 768-dim vector")
test_embedding = np.random.randn(1, 768).astype(np.float32)
print(f"  Input shape: {test_embedding.shape}")

try:
    result = umap_reducer.transform(test_embedding)
    print(f"  ✓ Success! Output: {result.shape}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    exit(1)

# Test 2: Two 768-dim vectors
print("\nTest 2: Two 768-dim vectors")
test_embedding = np.random.randn(2, 768).astype(np.float32)
print(f"  Input shape: {test_embedding.shape}")

try:
    result = umap_reducer.transform(test_embedding)
    print(f"  ✓ Success! Output: {result.shape}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    exit(1)

print("\n✓ All tests passed!")
