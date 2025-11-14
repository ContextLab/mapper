#!/usr/bin/env python3
"""
GPU worker for distributed embedding generation.

This script:
1. Loads a subset of Wikipedia articles based on cluster and GPU ID
2. Generates embeddings using Qwen/Qwen3-Embedding-0.6B on GPU
3. Saves embeddings to individual checkpoint files
4. Updates progress file for monitoring
"""

import pickle
import json
import os
import sys
import time
import argparse
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from datetime import datetime

def generate_embeddings_gpu(cluster_id, gpu_id, total_gpus=8, total_clusters=1):
    """
    Generate embeddings for a subset of articles on a specific GPU.

    Args:
        cluster_id: 0, 1, 2, ... (sequential cluster ID, 0-indexed)
        gpu_id: 0-7 (which GPU on this cluster)
        total_gpus: Total GPUs per cluster (default 8)
        total_clusters: Total number of active clusters (default 1)
    """

    # Constants
    TOTAL_ARTICLES = 250_000
    TOTAL_ITEMS = TOTAL_ARTICLES  # Only embed Wikipedia articles, NOT questions

    # Calculate global worker position
    total_workers = total_clusters * total_gpus
    global_worker_id = (cluster_id * total_gpus) + gpu_id

    # Distribute items across all workers
    items_per_worker = TOTAL_ITEMS // total_workers
    gpu_start = global_worker_id * items_per_worker

    # Last worker gets any remainder
    if global_worker_id == total_workers - 1:
        gpu_end = TOTAL_ITEMS
    else:
        gpu_end = gpu_start + items_per_worker

    print("="*80)
    print(f"GPU WORKER: Cluster {cluster_id}, GPU {gpu_id}")
    print("="*80)
    print(f"Total items: {TOTAL_ITEMS:,}")
    print(f"Total clusters: {total_clusters}")
    print(f"Total workers: {total_workers} ({total_clusters} clusters × {total_gpus} GPUs)")
    print(f"Global worker ID: {global_worker_id}")
    print(f"This worker range: {gpu_start:,} - {gpu_end:,} ({gpu_end - gpu_start:,} items)")
    print(f"Started: {datetime.now()}")
    print("")

    # Set GPU device
    # When CUDA_VISIBLE_DEVICES is set, use device 0 (the only visible GPU)
    device = "cuda:0"
    print(f"[1/6] Setting GPU device to {device} (CUDA_VISIBLE_DEVICES={gpu_id})...")
    torch.cuda.set_device(0)
    print(f"  ✓ Using: {torch.cuda.get_device_name(0)}")
    print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    print("")

    # Load Wikipedia articles
    print("[2/6] Loading Wikipedia articles...")
    start = time.time()
    with open('wikipedia.pkl', 'rb') as f:
        wiki_articles = pickle.load(f)
    load_time = time.time() - start
    print(f"  ✓ Loaded {len(wiki_articles):,} articles in {load_time:.2f}s")
    print("")

    # Extract article text (questions NOT included)
    print("[3/6] Extracting article text...")
    all_items = []
    for article in wiki_articles:
        if isinstance(article, dict):
            text = article.get('text', article.get('content', str(article)))
        else:
            text = str(article)
        all_items.append(text)

    print(f"Total articles: {len(all_items):,}")
    print("")

    # Extract this GPU's subset
    my_items = all_items[gpu_start:gpu_end]
    print(f"This GPU will process {len(my_items):,} items (indices {gpu_start:,}-{gpu_end-1:,})")
    print("")

    # Authenticate with HuggingFace if token available
    hf_token_file = Path(__file__).parent / ".credentials" / "hf.token"
    if hf_token_file.exists():
        print("[3/5] Authenticating with HuggingFace...")
        with open(hf_token_file, 'r') as f:
            hf_token = f.read().strip()

        from huggingface_hub import login
        login(token=hf_token)
        print("  ✓ Authenticated with HuggingFace")
        print("")

    # Load embedding model
    print("[4/5] Loading google/embeddinggemma-300m on GPU...")
    model_start = time.time()
    model = SentenceTransformer('google/embeddinggemma-300m', device=device)
    model_time = time.time() - model_start
    dim = model.get_sentence_embedding_dimension()
    print(f"  ✓ Model loaded in {model_time:.2f}s")
    print(f"  Embedding dimension: {dim}")
    print("")

    # Generate embeddings with checkpointing
    print(f"[5/5] Generating embeddings for {len(my_items):,} articles...")
    print(f"  Batch size: 32")
    print(f"  Checkpoint: Every 1000 items")
    print("")

    # Create output directory
    output_dir = Path("embeddings")
    output_dir.mkdir(exist_ok=True)

    embed_start = time.time()

    # Process in chunks of 1000 items to enable checkpointing
    CHECKPOINT_INTERVAL = 1000
    all_embeddings = []

    for chunk_start in range(0, len(my_items), CHECKPOINT_INTERVAL):
        chunk_end = min(chunk_start + CHECKPOINT_INTERVAL, len(my_items))
        chunk_items = my_items[chunk_start:chunk_end]

        print(f"\nProcessing items {gpu_start + chunk_start:,} to {gpu_start + chunk_end-1:,} ({len(chunk_items)} items)...")
        chunk_embeddings = model.encode(
            chunk_items,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            device=device
        )
        all_embeddings.append(chunk_embeddings)

        # Save checkpoint
        checkpoint_file = output_dir / f"cluster{cluster_id}_gpu{gpu_id}_checkpoint_{gpu_start + chunk_end}.pkl"
        checkpoint_data = {
            'embeddings': np.vstack(all_embeddings),
            'start_index': gpu_start,
            'end_index': gpu_start + chunk_end,
            'items_processed': chunk_end,
            'cluster_id': cluster_id,
            'gpu_id': gpu_id,
            'timestamp': datetime.now().isoformat(),
            'model': 'google/embeddinggemma-300m'
        }

        with open(checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint_data, f)

        print(f"  ✓ Checkpoint saved: {checkpoint_file.name}")

    embeddings = np.vstack(all_embeddings)
    embed_time = time.time() - embed_start

    rate = len(my_items) / embed_time
    print("")
    print(f"  ✓ Generated {embeddings.shape[0]:,} embeddings ({embeddings.shape[1]}-dim)")
    print(f"  Time: {embed_time:.2f}s ({embed_time/60:.2f} min)")
    print(f"  Rate: {rate:.2f} items/sec")
    print("")

    # Save final embeddings
    print("[6/6] Saving final embeddings...")
    output_file = output_dir / f"cluster{cluster_id}_gpu{gpu_id}.pkl"

    checkpoint_data = {
        'embeddings': embeddings,
        'start_index': gpu_start,
        'end_index': gpu_end,
        'cluster_id': cluster_id,
        'gpu_id': gpu_id,
        'timestamp': datetime.now().isoformat(),
        'processing_time': embed_time,
        'rate': rate,
        'model': 'google/embeddinggemma-300m'
    }

    with open(output_file, 'wb') as f:
        pickle.dump(checkpoint_data, f)

    file_size_mb = output_file.stat().st_size / 1e6
    print(f"  ✓ Saved to {output_file}")
    print(f"  File size: {file_size_mb:.2f} MB")
    print("")

    # Update progress file
    progress_file = output_dir / "progress.json"

    # Load existing progress
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        progress = {}

    # Update this worker's progress
    worker_key = f"cluster{cluster_id}_gpu{gpu_id}"
    progress[worker_key] = {
        'start_index': gpu_start,
        'end_index': gpu_end,
        'items_processed': len(my_items),
        'processing_time': embed_time,
        'rate': rate,
        'completed_at': datetime.now().isoformat(),
        'output_file': str(output_file)
    }

    # Calculate total progress
    total_processed = sum(w['items_processed'] for w in progress.values())
    total_workers = len(progress)

    progress['_summary'] = {
        'total_workers_completed': total_workers,
        'total_items_processed': total_processed,
        'target_items': TOTAL_ITEMS,
        'percent_complete': (total_processed / TOTAL_ITEMS) * 100,
        'last_updated': datetime.now().isoformat()
    }

    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)

    print(f"  ✓ Updated progress file")
    print(f"  Total progress: {total_processed:,}/{TOTAL_ITEMS:,} ({progress['_summary']['percent_complete']:.1f}%)")
    print("")

    # Verify embeddings
    norms = np.linalg.norm(embeddings, axis=1)
    print("Embedding quality check:")
    print(f"  Norms - mean: {norms.mean():.4f}, std: {norms.std():.4f}")
    print(f"  Shape: {embeddings.shape}")
    print("")

    total_time = time.time() - embed_start
    print("="*80)
    print(f"WORKER COMPLETE: Cluster {cluster_id}, GPU {gpu_id}")
    print("="*80)
    print(f"Items processed: {len(my_items):,}")
    print(f"Total time: {total_time:.2f}s ({total_time/60:.2f} min)")
    print(f"Rate: {rate:.2f} items/sec")
    print(f"Output: {output_file}")
    print(f"Completed: {datetime.now()}")
    print("")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate embeddings on GPU')
    parser.add_argument('--cluster', type=int, required=True,
                        help='Cluster ID (0-indexed, e.g., 0, 1, 2, ...)')
    parser.add_argument('--gpu', type=int, required=True, choices=range(8),
                        help='GPU ID (0-7)')
    parser.add_argument('--total-gpus', type=int, default=8,
                        help='Total GPUs per cluster (default: 8)')
    parser.add_argument('--total-clusters', type=int, default=1,
                        help='Total number of active clusters (default: 1)')

    args = parser.parse_args()

    generate_embeddings_gpu(args.cluster, args.gpu, args.total_gpus, args.total_clusters)
