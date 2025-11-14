#!/usr/bin/env python3
"""Test vec2text functionality with sample embeddings."""

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
import vec2text

print("Loading embedding model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

# Test texts
test_texts = [
    "Cellular respiration produces ATP energy",
    "Mitochondria are the powerhouse of the cell",
    "Photosynthesis converts light energy to chemical energy"
]

print("\nGenerating embeddings for test texts...")
embeddings = embedder.encode(test_texts, convert_to_tensor=True)
print(f"Embedding shape: {embeddings.shape}")

# Try using gtr-base corrector (closest to our sentence-transformer)
print("\nLoading vec2text corrector (gtr-base)...")
try:
    corrector = vec2text.load_pretrained_corrector("gtr-base")
    print("Corrector loaded successfully!")

    print("\nInverting embeddings to text...")
    # Note: gtr-base expects 768-dim, our embeddings are 384-dim
    # This will likely not work perfectly, but let's try

    # Option 1: Try direct inversion (will likely fail due to dimension mismatch)
    try:
        results = vec2text.invert_embeddings(
            embeddings=embeddings.cuda() if torch.cuda.is_available() else embeddings,
            corrector=corrector,
            num_steps=5,
            sequence_beam_width=2
        )

        print("\nResults:")
        for i, (original, recovered) in enumerate(zip(test_texts, results)):
            print(f"\n{i+1}. Original:  {original}")
            print(f"   Recovered: {recovered}")

    except Exception as e:
        print(f"\nDirect inversion failed (expected - dimension mismatch): {e}")
        print("\nThis is expected since all-MiniLM-L6-v2 (384-dim) != gtr-base (768-dim)")
        print("We need to handle this in the actual implementation.")

except Exception as e:
    print(f"Error loading corrector: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Conclusion:")
print("="*60)
print("vec2text is designed for specific embedding models.")
print("For all-MiniLM-L6-v2, we have two options:")
print("1. Use nearest-question approach (current fallback)")
print("2. Switch to gtr-base embeddings to use vec2text properly")
print("3. Train custom vec2text model (out of scope)")
