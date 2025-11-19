#!/usr/bin/env python3
"""
Test the subprocess approach with actual level 1 checkpoint data.
"""

import os
import json
import sys

# Add scripts to path
sys.path.insert(0, 'scripts')

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

print("=" * 80)
print("TEST: Subprocess Approach for Embedding + UMAP")
print("=" * 80)

# Load checkpoint
print("\n[1/3] Loading level 1 checkpoint (testing with 5 articles)...")
with open('checkpoints/level_1_after_download.json', 'r') as f:
    checkpoint = json.load(f)

# Use only first 5 articles for quick test
test_articles = checkpoint['articles'][:5]
print(f"  Loaded {len(test_articles)} test articles:")
for article in test_articles:
    print(f"    - {article['title']}")

# Load embedding model
print("\n[2/3] Loading embedding model (google/embeddinggemma-300m)...")
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer('google/embeddinggemma-300m')
print("  ✓ Model loaded")

# Test the generate_and_project_embeddings function
print("\n[3/3] Testing generate_and_project_embeddings with subprocess approach...")
from generate_level_n import generate_and_project_embeddings

# We don't need to load UMAP reducer since it's loaded in subprocess
result_articles = generate_and_project_embeddings(test_articles, embedding_model, None)

# Verify results
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"Processed {len(result_articles)} articles")
print("\nSample coordinates:")
for article in result_articles:
    print(f"  {article['title']}: x={article['x']:.4f}, y={article['y']:.4f}")

print("\n✓ SUCCESS: Subprocess approach works!")
