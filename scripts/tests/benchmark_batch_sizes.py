#!/usr/bin/env python3
"""
Benchmark different batch sizes to find the optimal configuration.

Tests batch sizes: 2, 4, 8, 16, 32, 64, 128, 256
Uses a representative sample to match production conditions.
"""

import pickle
import json
import time
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer
import sys

# Use FULL dataset for accurate measurements
SAMPLE_SIZE = None  # None = use all 250k articles
BATCH_SIZES = [2, 4, 8, 16, 32, 64, 128, 256]

def benchmark_batch_size(batch_size, model, items, device):
    """
    Benchmark a specific batch size.

    Returns:
        tuple: (batch_size, time_per_item, items_per_sec, total_time)
    """
    print(f"\n{'='*60}")
    print(f"Testing batch size: {batch_size}")
    print(f"{'='*60}")

    try:
        start_time = time.time()

        # Generate embeddings
        embeddings = model.encode(
            items,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            device=device
        )

        elapsed = time.time() - start_time
        items_per_sec = len(items) / elapsed
        time_per_item = elapsed / len(items)

        print(f"\nResults:")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Items/sec: {items_per_sec:.2f}")
        print(f"  Time/item: {time_per_item:.4f}s")

        # Estimate full dataset time (250k articles)
        estimated_full_time = 250000 / items_per_sec
        print(f"  Estimated time for 250k articles: {estimated_full_time/3600:.2f} hours")

        return (batch_size, time_per_item, items_per_sec, elapsed, estimated_full_time)

    except Exception as e:
        print(f"  ✗ Failed with error: {e}")
        return (batch_size, float('inf'), 0, float('inf'), float('inf'))

def main():
    print("="*80)
    print("BATCH SIZE OPTIMIZATION BENCHMARK (FULL DATASET)")
    print("="*80)
    print(f"Dataset: {'FULL (250k articles)' if SAMPLE_SIZE is None else f'{SAMPLE_SIZE} articles'}")
    print(f"Batch sizes to test: {BATCH_SIZES}")
    print("")

    # Determine device
    if torch.backends.mps.is_available():
        device = "mps"
        print("✓ Using Metal Performance Shaders (MPS)")
    elif torch.cuda.is_available():
        device = "cuda"
        print("✓ Using CUDA")
    else:
        device = "cpu"
        print("⚠ Using CPU")
    print("")

    # Load Wikipedia articles
    print("[1/3] Loading Wikipedia articles...")
    start = time.time()
    with open('data/wikipedia.pkl', 'rb') as f:
        wiki_articles = pickle.load(f)
    load_time = time.time() - start
    print(f"  ✓ Loaded {len(wiki_articles):,} articles in {load_time:.2f}s")

    # Use full dataset or sample
    if SAMPLE_SIZE is None:
        sample_articles = wiki_articles
        print(f"  ✓ Using FULL dataset: {len(sample_articles):,} articles")
    else:
        # Extract sample (use middle section to avoid any ordering bias)
        offset = len(wiki_articles) // 2 - SAMPLE_SIZE // 2
        sample_articles = wiki_articles[offset:offset + SAMPLE_SIZE]
        print(f"  ✓ Using {len(sample_articles)} articles from middle of dataset")
    print("")

    # Extract text
    sample_items = []
    for article in sample_articles:
        if isinstance(article, dict):
            text = article.get('text', article.get('content', str(article)))
        else:
            text = str(article)
        sample_items.append(text)

    # Authenticate with HuggingFace
    hf_token_file = Path(__file__).parent / ".credentials" / "hf.token"
    if hf_token_file.exists():
        print("[2/3] Authenticating with HuggingFace...")
        with open(hf_token_file, 'r') as f:
            hf_token = f.read().strip()
        from huggingface_hub import login
        login(token=hf_token)
        print("  ✓ Authenticated")
        print("")

    # Load model
    print("[3/3] Loading google/embeddinggemma-300m...")
    model_start = time.time()
    model = SentenceTransformer('google/embeddinggemma-300m', device=device)
    model_time = time.time() - model_start
    print(f"  ✓ Model loaded in {model_time:.2f}s")
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")
    print("")

    # Benchmark each batch size
    results = []

    for batch_size in BATCH_SIZES:
        result = benchmark_batch_size(batch_size, model, sample_items, device)
        results.append(result)

        # Add a small delay between tests to let GPU cool down
        time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*80)
    print(f"\n{'Batch Size':<12} {'Time/Item (s)':<15} {'Items/Sec':<12} {'Est. Hours':<12} {'Total Time (s)':<15}")
    print("-" * 80)

    for batch_size, time_per_item, items_per_sec, total_time, est_full_time in results:
        if time_per_item == float('inf'):
            print(f"{batch_size:<12} {'FAILED':<15} {'FAILED':<12} {'FAILED':<12} {'FAILED':<15}")
        else:
            print(f"{batch_size:<12} {time_per_item:<15.6f} {items_per_sec:<12.2f} {est_full_time/3600:<12.2f} {total_time:<15.2f}")

    # Find optimal batch size
    valid_results = [(bs, ips, eft) for bs, tpi, ips, tt, eft in results if ips > 0]

    if valid_results:
        optimal_batch_size, optimal_rate, optimal_time = max(valid_results, key=lambda x: x[1])

        print("\n" + "="*80)
        print("OPTIMAL CONFIGURATION")
        print("="*80)
        print(f"  Best batch size: {optimal_batch_size}")
        print(f"  Processing rate: {optimal_rate:.2f} items/sec")
        print(f"  Estimated time for 250k articles: {optimal_time/3600:.2f} hours ({optimal_time/60:.1f} minutes)")
        print("")

        # Save results
        output_file = Path("batch_size_benchmark_results.json")
        results_data = {
            'device': device,
            'sample_size': SAMPLE_SIZE,
            'batch_sizes_tested': BATCH_SIZES,
            'results': [
                {
                    'batch_size': bs,
                    'time_per_item': tpi if tpi != float('inf') else None,
                    'items_per_sec': ips if ips != float('inf') else None,
                    'total_time': tt if tt != float('inf') else None,
                    'estimated_full_time_hours': eft/3600 if eft != float('inf') else None
                }
                for bs, tpi, ips, tt, eft in results
            ],
            'optimal_batch_size': optimal_batch_size,
            'optimal_rate': optimal_rate,
            'optimal_time_hours': optimal_time/3600
        }

        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Results saved to: {output_file}")
        print("")
    else:
        print("\n✗ All batch sizes failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
