#!/usr/bin/env python3
"""
Quick test to see if Qwen model can load properly.
"""
import sys
import time
from datetime import datetime

print(f"Starting Qwen load test at {datetime.now()}")
print(f"Python: {sys.version}")
print("="*80)

# Test 1: Import sentence_transformers
print("\n[1/4] Importing sentence_transformers...")
start = time.time()
try:
    from sentence_transformers import SentenceTransformer
    import torch
    print(f"✓ Import successful ({time.time()-start:.2f}s)")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Check MPS availability
print("\n[2/4] Checking device availability...")
if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print("  MPS (Apple GPU) is available")
    print("  → Forcing CPU due to tensor size limitations")
    device = 'cpu'
else:
    print("  MPS not available, using auto-detect")
    device = None

# Test 3: Load Qwen model
print("\n[3/4] Loading Qwen/Qwen3-Embedding-0.6B...")
print(f"  Device: {device}")
print(f"  trust_remote_code: True")
start = time.time()
try:
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True, device=device)
    load_time = time.time() - start
    print(f"✓ Model loaded successfully ({load_time:.2f}s)")
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")
except Exception as e:
    print(f"✗ Model loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test encoding
print("\n[4/4] Testing embedding generation...")
test_texts = [
    "This is a test sentence.",
    "Another test sentence for verification."
]
start = time.time()
try:
    embeddings = model.encode(test_texts, show_progress_bar=False, convert_to_numpy=True)
    encode_time = time.time() - start
    print(f"✓ Encoding successful ({encode_time:.2f}s)")
    print(f"  Shape: {embeddings.shape}")
    print(f"  Rate: {len(test_texts)/encode_time:.1f} texts/sec")
except Exception as e:
    print(f"✗ Encoding failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*80)
print("✓ All tests passed!")
print(f"Total time: {time.time()-start:.2f}s")
print("="*80)
