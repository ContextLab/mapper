#!/usr/bin/env python3
"""
Test that the embedding dimension fix works:
1. Load google/embeddinggemma-300m model
2. Generate embeddings for a few sample articles
3. Verify dimensions are 768
4. Test UMAP transform with correct dimensions
"""

import os
import pickle
import json
import numpy as np

# Set environment variables to avoid threading issues
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

print("=" * 80)
print("TEST: Embedding Dimension Fix")
print("=" * 80)

# Step 1: Load the checkpoint with level 1 articles
print("\n[1/4] Loading level 1 checkpoint...")
with open('checkpoints/level_1_after_download.json', 'r') as f:
    checkpoint = json.load(f)

articles = checkpoint['articles'][:5]  # Test with first 5 articles
print(f"  Loaded {len(articles)} sample articles")
for article in articles:
    print(f"    - {article['title']}")

# Step 2: Load embedding model
print("\n[2/4] Loading google/embeddinggemma-300m embedding model...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('google/embeddinggemma-300m')
print(f"  ✓ Model loaded")

# Step 3: Generate embeddings
print("\n[3/4] Generating embeddings...")
texts = [article['text'] for article in articles]
embeddings = model.encode(
    texts,
    show_progress_bar=True,
    batch_size=5,
    normalize_embeddings=True
)

print(f"  ✓ Generated {len(embeddings)} embeddings")
print(f"  Embedding shape: {embeddings.shape}")
print(f"  Expected: (5, 768)")

if embeddings.shape[1] != 768:
    print(f"  ✗ ERROR: Expected 768 dimensions, got {embeddings.shape[1]}")
    exit(1)
else:
    print(f"  ✓ Dimensions correct: 768")

# Step 4: Test UMAP transform
print("\n[4/4] Testing UMAP transform...")
with open('data/umap_reducer.pkl', 'rb') as f:
    umap_reducer = pickle.load(f)

print(f"  UMAP expects input shape: (*, {umap_reducer._raw_data.shape[1]})")

try:
    umap_coords = umap_reducer.transform(embeddings)
    print(f"  ✓ UMAP transform successful!")
    print(f"  Output shape: {umap_coords.shape}")
    print(f"  Sample coordinates:")
    for i, (article, coords) in enumerate(zip(articles, umap_coords)):
        print(f"    {article['title']}: ({coords[0]:.4f}, {coords[1]:.4f})")
except Exception as e:
    print(f"  ✗ UMAP transform failed: {e}")
    exit(1)

print("\n" + "=" * 80)
print("SUCCESS: All tests passed!")
print("=" * 80)
print("\nThe embedding dimension fix is working correctly.")
print("Ready to resume level 1 pipeline with corrected embeddings.")
