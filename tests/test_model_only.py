#!/usr/bin/env python3
"""
Test just the embedding model without UMAP.
"""

import os
import numpy as np

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

print("Step 1: Loading embedding model...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('google/embeddinggemma-300m')
print("  ✓ Model loaded")

print("\nStep 2: Generating embeddings for 2 short texts...")
texts = ["Test sentence one.", "Test sentence two."]
embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
print(f"  ✓ Generated embeddings: {embeddings.shape}")
print(f"  Dimensions: {embeddings.shape[1]}")
print(f"  Has NaN: {np.isnan(embeddings).any()}")
print(f"  Has Inf: {np.isinf(embeddings).any()}")

print("\n✓ Model works correctly!")
