#!/usr/bin/env python3
"""
Test actual model embeddings with UMAP, checking for NaN/Inf issues.
"""

import os
import pickle
import numpy as np

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

print("Loading embedding model...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('google/embeddinggemma-300m')

print("Generating embeddings for 2 short texts...")
texts = ["Test sentence one.", "Test sentence two."]
embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

print(f"Embedding shape: {embeddings.shape}")
print(f"Embedding dtype: {embeddings.dtype}")
print(f"Has NaN: {np.isnan(embeddings).any()}")
print(f"Has Inf: {np.isinf(embeddings).any()}")
print(f"Min value: {embeddings.min():.6f}")
print(f"Max value: {embeddings.max():.6f}")

# Convert to float32 to match training data
embeddings = embeddings.astype(np.float32)
print(f"\nAfter float32 conversion:")
print(f"  dtype: {embeddings.dtype}")

print("\nLoading UMAP reducer...")
with open('data/umap_reducer.pkl', 'rb') as f:
    umap_reducer = pickle.load(f)

print(f"UMAP expects: {umap_reducer._raw_data.shape[1]}-dim, dtype: {umap_reducer._raw_data.dtype}")

print("\nAttempting UMAP transform...")
try:
    result = umap_reducer.transform(embeddings)
    print(f"✓ Success! Output shape: {result.shape}")
    print(f"Coordinates: {result}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
