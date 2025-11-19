#!/usr/bin/env python3
"""
Test embedding + UMAP together carefully, with separate processes.
"""

import os
import subprocess
import sys

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

# Step 1: Generate embeddings in one process, save to file
print("=" * 80)
print("Step 1: Generate embeddings...")
print("=" * 80)

embed_code = """
import os
import numpy as np
from sentence_transformers import SentenceTransformer

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

model = SentenceTransformer('google/embeddinggemma-300m')
texts = ["Test sentence one.", "Test sentence two.", "Test sentence three."]
embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

print(f"Generated {embeddings.shape}")
np.save('/tmp/test_embeddings.npy', embeddings)
print("Saved to /tmp/test_embeddings.npy")
"""

result = subprocess.run([sys.executable, '-c', embed_code], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"✗ Failed: {result.stderr}")
    exit(1)

# Step 2: Load embeddings and apply UMAP in separate process
print("\n" + "=" * 80)
print("Step 2: Apply UMAP transform...")
print("=" * 80)

umap_code = """
import os
import numpy as np
import pickle

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

embeddings = np.load('/tmp/test_embeddings.npy')
print(f"Loaded embeddings: {embeddings.shape}")

with open('data/umap_reducer.pkl', 'rb') as f:
    umap_reducer = pickle.load(f)

print(f"UMAP expects {umap_reducer._raw_data.shape[1]}-dim")
coords = umap_reducer.transform(embeddings)
print(f"✓ Transform successful: {coords.shape}")
print(f"Coordinates:\\n{coords}")
"""

result = subprocess.run([sys.executable, '-c', umap_code], capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f"✗ Failed (exit {result.returncode}): {result.stderr}")
    exit(1)

print("\n" + "=" * 80)
print("✓ SUCCESS: Both steps work in separate processes!")
print("=" * 80)
