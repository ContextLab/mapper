#!/usr/bin/env python3
"""
Test embedding generation speed with a sample of Wikipedia articles.

This script:
1. Loads 10 random Wikipedia articles from wikipedia.pkl
2. Generates embeddings using Qwen/Qwen3-Embedding-0.6B
3. Measures the time and calculates rate
4. Provides an accurate estimate for the full 250k dataset
"""

import pickle
import time
import random
import sys
from datetime import datetime
import numpy as np

def test_embedding_speed(num_samples=10):
    """Test embedding speed with random Wikipedia articles."""

    print("="*80)
    print("EMBEDDING SPEED TEST")
    print("="*80)

    # Step 1: Load Wikipedia articles
    print("\n[1/4] Loading wikipedia.pkl...")
    start = time.time()

    with open('data/wikipedia.pkl', 'rb') as f:
        wiki_articles = pickle.load(f)

    load_time = time.time() - start
    print(f"  ✓ Loaded {len(wiki_articles):,} articles in {load_time:.2f}s")

    # Step 2: Sample random articles
    print(f"\n[2/4] Sampling {num_samples} random articles...")
    random.seed(42)  # For reproducibility
    sample_indices = random.sample(range(len(wiki_articles)), num_samples)
    sample_articles = [wiki_articles[i] for i in sorted(sample_indices)]

    # Extract text
    sample_texts = []
    for i, article in zip(sample_indices, sample_articles):
        if isinstance(article, dict):
            text = article.get('text', article.get('content', str(article)))
            title = article.get('title', f'Article {i}')
        else:
            text = str(article)
            title = f'Article {i}'

        sample_texts.append(text)
        print(f"  Article {i}: {title[:60]}... ({len(text)} chars)")

    # Step 3: Load embedding model
    print("\n[3/4] Loading Qwen/Qwen3-Embedding-0.6B...")
    from sentence_transformers import SentenceTransformer
    import torch

    # Force CPU for compatibility
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        print("  ⚠️  Disabling MPS (Apple GPU) - using CPU")
        device = 'cpu'
    else:
        device = None

    model_start = time.time()
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True, device=device)
    model_time = time.time() - model_start

    dim = model.get_sentence_embedding_dimension()
    print(f"  ✓ Model loaded in {model_time:.2f}s (dimension: {dim})")

    # Step 4: Generate embeddings and measure time
    print(f"\n[4/4] Generating embeddings for {num_samples} articles...")

    # Warm-up run (first encoding is slower)
    _ = model.encode(["warmup"], show_progress_bar=False, convert_to_numpy=True)

    # Actual timed run
    embed_start = time.time()
    embeddings = model.encode(sample_texts, show_progress_bar=False, convert_to_numpy=True)
    embed_time = time.time() - embed_start

    # Results
    rate = num_samples / embed_time
    per_item_ms = (embed_time / num_samples) * 1000

    print(f"\n  ✓ Generated {embeddings.shape[0]} embeddings ({embeddings.shape[1]}-dim)")
    print(f"  Time: {embed_time:.2f}s")
    print(f"  Rate: {rate:.2f} items/sec ({per_item_ms:.1f}ms per item)")

    # Step 5: Extrapolate to full dataset
    print("\n" + "="*80)
    print("EXTRAPOLATION TO FULL DATASET")
    print("="*80)

    total_items = 250_010  # 250k articles + 10 questions

    # Estimate for single-threaded processing
    estimated_seconds = total_items / rate
    estimated_hours = estimated_seconds / 3600

    print(f"\nFor {total_items:,} items at {rate:.2f} items/sec:")
    print(f"  Estimated time: {estimated_hours:.2f} hours ({estimated_seconds/60:.1f} minutes)")

    # Consider batch processing overhead
    batch_size = 32
    num_batches = total_items // batch_size
    overhead_per_batch = 0.01  # 10ms overhead per batch
    total_overhead = (num_batches * overhead_per_batch) / 3600

    adjusted_hours = estimated_hours + total_overhead
    print(f"  With batching overhead: {adjusted_hours:.2f} hours")

    # Add data loading time (observed: ~30 seconds for 250k articles)
    data_load_hours = 30 / 3600
    total_with_loading = adjusted_hours + data_load_hours

    print(f"  With data loading: {total_with_loading:.2f} hours")

    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    print(f"\nExpect the full build to take approximately:")
    print(f"  • Data loading: 0.5 minutes")
    print(f"  • Embedding generation: {adjusted_hours:.1f} hours")
    print(f"  • UMAP projection: 0.2-1.0 hours (estimated)")
    print(f"  • Total: {total_with_loading + 0.5:.1f} hours")

    # Verify embeddings are reasonable
    print("\n" + "="*80)
    print("EMBEDDING QUALITY CHECK")
    print("="*80)

    # Check embedding norms
    norms = np.linalg.norm(embeddings, axis=1)
    print(f"\nEmbedding norms:")
    print(f"  Mean: {norms.mean():.4f}")
    print(f"  Std: {norms.std():.4f}")
    print(f"  Min: {norms.min():.4f}")
    print(f"  Max: {norms.max():.4f}")

    # Check similarity between first two
    if len(embeddings) >= 2:
        from sklearn.metrics.pairwise import cosine_similarity
        sim = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        print(f"\nCosine similarity between first two articles: {sim:.4f}")

    print("\n✓ Test complete!")
    return rate, adjusted_hours

if __name__ == '__main__':
    num_samples = 10
    if len(sys.argv) > 1:
        num_samples = int(sys.argv[1])

    test_embedding_speed(num_samples)
