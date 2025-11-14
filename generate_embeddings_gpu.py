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

def load_questions():
    """Load the 10 questions from questions.json."""
    questions_file = Path(__file__).parent / "mapper.io" / "questions.json"

    if not questions_file.exists():
        print(f"Warning: questions.json not found at {questions_file}")
        return []

    with open(questions_file, 'r') as f:
        questions_data = json.load(f)

    # Extract question texts
    question_texts = []
    for q in questions_data:
        question_texts.append(q['question'])

    print(f"  Loaded {len(question_texts)} questions")
    return question_texts

def generate_embeddings_gpu(cluster_id, gpu_id, total_gpus=8):
    """
    Generate embeddings for a subset of articles on a specific GPU.

    Args:
        cluster_id: 1 or 2 (which cluster)
        gpu_id: 0-7 (which GPU on this cluster)
        total_gpus: Total GPUs per cluster (default 8)
    """

    # Constants
    TOTAL_ARTICLES = 250_000
    TOTAL_QUESTIONS = 10
    TOTAL_ITEMS = TOTAL_ARTICLES + TOTAL_QUESTIONS
    ITEMS_PER_CLUSTER = TOTAL_ITEMS // 2  # 125,005 per cluster

    # Calculate this worker's range
    if cluster_id == 1:
        cluster_start = 0
        cluster_end = ITEMS_PER_CLUSTER
    else:  # cluster_id == 2
        cluster_start = ITEMS_PER_CLUSTER
        cluster_end = TOTAL_ITEMS

    items_per_gpu = (cluster_end - cluster_start) // total_gpus
    gpu_start = cluster_start + (gpu_id * items_per_gpu)

    # Last GPU gets any remainder
    if gpu_id == total_gpus - 1:
        gpu_end = cluster_end
    else:
        gpu_end = gpu_start + items_per_gpu

    print("="*80)
    print(f"GPU WORKER: Cluster {cluster_id}, GPU {gpu_id}")
    print("="*80)
    print(f"Total items: {TOTAL_ITEMS:,}")
    print(f"Cluster range: {cluster_start:,} - {cluster_end:,} ({cluster_end - cluster_start:,} items)")
    print(f"GPU range: {gpu_start:,} - {gpu_end:,} ({gpu_end - gpu_start:,} items)")
    print(f"Started: {datetime.now()}")
    print("")

    # Set GPU device
    device = f"cuda:{gpu_id}"
    print(f"[1/6] Setting GPU device to {device}...")
    torch.cuda.set_device(gpu_id)
    print(f"  ✓ Using: {torch.cuda.get_device_name(gpu_id)}")
    print(f"  Memory: {torch.cuda.get_device_properties(gpu_id).total_memory / 1e9:.2f} GB")
    print("")

    # Load Wikipedia articles
    print("[2/6] Loading Wikipedia articles...")
    start = time.time()
    with open('../wikipedia.pkl', 'rb') as f:
        wiki_articles = pickle.load(f)
    load_time = time.time() - start
    print(f"  ✓ Loaded {len(wiki_articles):,} articles in {load_time:.2f}s")
    print("")

    # Load questions
    print("[3/6] Loading questions...")
    question_texts = load_questions()
    print("")

    # Combine articles + questions
    all_items = []

    # Add articles
    for article in wiki_articles:
        if isinstance(article, dict):
            text = article.get('text', article.get('content', str(article)))
        else:
            text = str(article)
        all_items.append(text)

    # Add questions at the end
    all_items.extend(question_texts)

    print(f"Total items combined: {len(all_items):,}")
    print(f"  Articles: {len(wiki_articles):,}")
    print(f"  Questions: {len(question_texts)}")
    print("")

    # Extract this GPU's subset
    my_items = all_items[gpu_start:gpu_end]
    print(f"This GPU will process {len(my_items):,} items (indices {gpu_start:,}-{gpu_end-1:,})")
    print("")

    # Load embedding model
    print("[4/6] Loading Qwen/Qwen3-Embedding-0.6B on GPU...")
    model_start = time.time()
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True, device=device)
    model_time = time.time() - model_start
    dim = model.get_sentence_embedding_dimension()
    print(f"  ✓ Model loaded in {model_time:.2f}s")
    print(f"  Embedding dimension: {dim}")
    print("")

    # Generate embeddings
    print(f"[5/6] Generating embeddings for {len(my_items):,} items...")
    print(f"  Batch size: 32")
    print(f"  Show progress: Every 1000 items")
    print("")

    embed_start = time.time()
    embeddings = model.encode(
        my_items,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        device=device
    )
    embed_time = time.time() - embed_start

    rate = len(my_items) / embed_time
    print("")
    print(f"  ✓ Generated {embeddings.shape[0]:,} embeddings ({embeddings.shape[1]}-dim)")
    print(f"  Time: {embed_time:.2f}s ({embed_time/60:.2f} min)")
    print(f"  Rate: {rate:.2f} items/sec")
    print("")

    # Save embeddings
    print("[6/6] Saving embeddings...")
    output_dir = Path("../embeddings")
    output_dir.mkdir(exist_ok=True)

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
        'model': 'Qwen/Qwen3-Embedding-0.6B'
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
    parser.add_argument('--cluster', type=int, required=True, choices=[1, 2],
                        help='Cluster ID (1 or 2)')
    parser.add_argument('--gpu', type=int, required=True, choices=range(8),
                        help='GPU ID (0-7)')
    parser.add_argument('--total-gpus', type=int, default=8,
                        help='Total GPUs per cluster (default: 8)')

    args = parser.parse_args()

    generate_embeddings_gpu(args.cluster, args.gpu, args.total_gpus)
