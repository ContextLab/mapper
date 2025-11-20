#!/usr/bin/env python3
"""
Test script to diagnose UMAP transform segfault.

This script tests different hypotheses:
1. OpenMP threading issues
2. Batch size issues
3. Memory corruption
4. Pickle/unpickle issues
"""

import os
import sys
import pickle
import numpy as np
import gc
import json

# Set threading env vars (BEFORE importing libraries)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("Environment variables set:")
print(f"  OMP_NUM_THREADS={os.environ['OMP_NUM_THREADS']}")
print(f"  MKL_NUM_THREADS={os.environ['MKL_NUM_THREADS']}")
print()


def test_1_load_umap():
    """Test 1: Can we load the UMAP model?"""
    print("="*80)
    print("TEST 1: Loading UMAP reducer")
    print("="*80)

    try:
        print("Loading UMAP reducer from data/umap_reducer.pkl...")
        with open('data/umap_reducer.pkl', 'rb') as f:
            reducer = pickle.load(f)

        print(f"✓ UMAP reducer loaded successfully")
        print(f"  Type: {type(reducer)}")
        print(f"  n_components: {reducer.n_components}")

        # Check if model has embedding_ attribute (fitted)
        if hasattr(reducer, 'embedding_'):
            print(f"  embedding_ shape: {reducer.embedding_.shape}")

        return reducer

    except Exception as e:
        print(f"✗ Failed to load UMAP reducer: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_2_load_checkpoint():
    """Test 2: Load checkpoint and generate embeddings."""
    print()
    print("="*80)
    print("TEST 2: Loading checkpoint and generating embeddings")
    print("="*80)

    try:
        checkpoint_path = 'checkpoints/level_1_after_download.json'
        print(f"Loading checkpoint from {checkpoint_path}...")

        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)

        articles = checkpoint['articles']
        print(f"✓ Loaded {len(articles)} articles")

        # Check if embeddings exist
        if 'embedding' in articles[0]:
            embedding_dim = len(articles[0]['embedding'])
            print(f"  Embedding dimension: {embedding_dim}")
            embeddings = np.array([article['embedding'] for article in articles])
        else:
            print("  No embeddings in checkpoint - generating now...")

            # Load embedding model
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

            # Extract texts
            texts = [article['text'] for article in articles]
            print(f"  Generating embeddings for {len(texts)} articles...")

            # Generate embeddings
            embeddings = model.encode(
                texts,
                show_progress_bar=True,
                batch_size=32,
                normalize_embeddings=True
            )

            print(f"  ✓ Generated embeddings")

        print(f"  Embeddings shape: {embeddings.shape}")
        print(f"  Embeddings dtype: {embeddings.dtype}")

        return articles, embeddings

    except Exception as e:
        print(f"✗ Failed to load checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_3_single_transform(reducer, embeddings):
    """Test 3: Transform a single embedding."""
    print()
    print("="*80)
    print("TEST 3: Transform single embedding")
    print("="*80)

    try:
        single = embeddings[:1]
        print(f"Transforming 1 embedding (shape: {single.shape})...")
        result = reducer.transform(single)
        print(f"✓ Single transform succeeded")
        print(f"  Result shape: {result.shape}")
        print(f"  Result: {result}")
        return True

    except Exception as e:
        print(f"✗ Single transform failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_small_batch(reducer, embeddings):
    """Test 4: Transform small batches."""
    print()
    print("="*80)
    print("TEST 4: Transform small batches")
    print("="*80)

    batch_sizes = [1, 5, 10, 20, 50, 100]

    for batch_size in batch_sizes:
        try:
            batch = embeddings[:batch_size]
            print(f"Transforming batch of {batch_size} embeddings...")
            result = reducer.transform(batch)
            print(f"  ✓ Batch size {batch_size} succeeded (result shape: {result.shape})")
            gc.collect()  # Force garbage collection

        except Exception as e:
            print(f"  ✗ Batch size {batch_size} failed: {e}")
            return batch_size

    print(f"✓ All small batches succeeded")
    return None


def test_5_full_transform_chunked(reducer, embeddings):
    """Test 5: Transform full dataset in chunks."""
    print()
    print("="*80)
    print("TEST 5: Transform full dataset in chunks")
    print("="*80)

    chunk_sizes = [100, 200, 500, 1000, 2000]

    for chunk_size in chunk_sizes:
        try:
            print(f"Attempting chunk size: {chunk_size}")
            results = []

            for i in range(0, len(embeddings), chunk_size):
                end_idx = min(i + chunk_size, len(embeddings))
                chunk = embeddings[i:end_idx]

                print(f"  Chunk {i//chunk_size + 1}: transforming {len(chunk)} embeddings...")
                chunk_result = reducer.transform(chunk)
                results.append(chunk_result)

                # Force garbage collection after each chunk
                gc.collect()

            # Combine results
            full_result = np.vstack(results)
            print(f"✓ Chunk size {chunk_size} succeeded")
            print(f"  Total transformed: {full_result.shape[0]} embeddings")
            return full_result

        except Exception as e:
            print(f"✗ Chunk size {chunk_size} failed: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"✗ All chunk sizes failed")
    return None


def test_6_memory_safe_transform(reducer, embeddings):
    """Test 6: Memory-safe transform with explicit cleanup."""
    print()
    print("="*80)
    print("TEST 6: Memory-safe transform")
    print("="*80)

    try:
        # Try very small chunks with aggressive cleanup
        chunk_size = 50
        print(f"Using very small chunk size: {chunk_size}")
        print(f"Total embeddings: {len(embeddings)}")

        results = []

        for i in range(0, len(embeddings), chunk_size):
            end_idx = min(i + chunk_size, len(embeddings))
            chunk = embeddings[i:end_idx]

            print(f"  Chunk {i//chunk_size + 1}/{(len(embeddings)-1)//chunk_size + 1}: {len(chunk)} embeddings...", end=" ")

            # Transform
            chunk_result = reducer.transform(chunk)
            print(f"✓")

            # Store result
            results.append(chunk_result.copy())

            # Aggressive cleanup
            del chunk_result
            del chunk
            gc.collect()

        # Combine results
        full_result = np.vstack(results)
        print(f"✓ Memory-safe transform succeeded")
        print(f"  Total transformed: {full_result.shape[0]} embeddings")
        return full_result

    except Exception as e:
        print(f"✗ Memory-safe transform failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_7_reload_umap_fresh(embeddings):
    """Test 7: Reload UMAP fresh (no stale state)."""
    print()
    print("="*80)
    print("TEST 7: Reload UMAP fresh")
    print("="*80)

    try:
        # Force cleanup
        gc.collect()

        # Reload
        print("Reloading UMAP reducer...")
        with open('data/umap_reducer.pkl', 'rb') as f:
            fresh_reducer = pickle.load(f)

        print(f"✓ Fresh UMAP loaded")

        # Try single transform
        print("Testing single transform with fresh reducer...")
        single = embeddings[:1]
        result = fresh_reducer.transform(single)
        print(f"✓ Single transform succeeded with fresh reducer")

        # Try small batch
        print("Testing small batch (10) with fresh reducer...")
        batch = embeddings[:10]
        result = fresh_reducer.transform(batch)
        print(f"✓ Small batch succeeded with fresh reducer")

        return fresh_reducer

    except Exception as e:
        print(f"✗ Fresh reload test failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    print("UMAP SEGFAULT DIAGNOSTIC TEST SUITE")
    print("="*80)
    print()

    # Test 1: Load UMAP
    reducer = test_1_load_umap()
    if reducer is None:
        print("\n❌ FATAL: Cannot load UMAP reducer")
        return 1

    # Test 2: Load checkpoint
    articles, embeddings = test_2_load_checkpoint()
    if embeddings is None:
        print("\n❌ FATAL: Cannot load embeddings")
        return 1

    # Test 3: Single transform
    success = test_3_single_transform(reducer, embeddings)
    if not success:
        print("\n❌ FATAL: Single transform failed")
        return 1

    # Test 4: Small batches
    fail_size = test_4_small_batch(reducer, embeddings)
    if fail_size is not None:
        print(f"\n⚠️  WARNING: Batch size {fail_size} failed")

    # Test 5: Full transform chunked
    result = test_5_full_transform_chunked(reducer, embeddings)
    if result is not None:
        print(f"\n✅ SUCCESS: Full transform succeeded")
        return 0

    # Test 6: Memory-safe transform
    result = test_6_memory_safe_transform(reducer, embeddings)
    if result is not None:
        print(f"\n✅ SUCCESS: Memory-safe transform succeeded")
        return 0

    # Test 7: Fresh reload
    fresh_reducer = test_7_reload_umap_fresh(embeddings)
    if fresh_reducer is not None:
        print("\nRetrying full transform with fresh reducer...")
        result = test_6_memory_safe_transform(fresh_reducer, embeddings)
        if result is not None:
            print(f"\n✅ SUCCESS: Fresh reducer with memory-safe transform succeeded")
            return 0

    print("\n❌ FATAL: All transform strategies failed")
    return 1


if __name__ == '__main__':
    sys.exit(main())
