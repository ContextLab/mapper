#!/usr/bin/env python3
"""
Checkpointed embedding generation with incremental support.

This script:
- Randomly samples articles without replacement
- Saves checkpoints every N articles
- Tracks which articles have been embedded (by index)
- Supports adding more embeddings later without recomputing
"""

import pickle
import json
import os
import time
import argparse
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from datetime import datetime
from tqdm import tqdm

def load_article_registry(registry_file):
    """Load the registry of which articles have been embedded."""
    if registry_file.exists():
        with open(registry_file, 'rb') as f:
            return pickle.load(f)
    return {
        'embedded_indices': set(),
        'article_count': 0,
        'total_available': 250000
    }

def save_article_registry(registry_file, registry):
    """Save the registry of embedded articles."""
    with open(registry_file, 'wb') as f:
        pickle.dump(registry, f)

def load_checkpoint(checkpoint_file):
    """Load existing checkpoint if it exists."""
    if checkpoint_file.exists():
        with open(checkpoint_file, 'rb') as f:
            return pickle.load(f)
    return None

def save_checkpoint(checkpoint_file, data):
    """Save checkpoint data."""
    with open(checkpoint_file, 'wb') as f:
        pickle.dump(data, f)
    print(f"  ✓ Checkpoint saved: {checkpoint_file.name}")

def generate_embeddings_checkpointed(
    num_articles=25000,
    batch_size=32,
    checkpoint_interval=1000,
    use_mps=True,
    resume=False
):
    """
    Generate embeddings with checkpointing and incremental support.

    Args:
        num_articles: Number of articles to embed in this run
        batch_size: Batch size for embedding generation (default: 32, safe for MPS)
        checkpoint_interval: Save checkpoint every N articles
        use_mps: Whether to use Metal Performance Shaders
        resume: Whether to resume from existing checkpoint
    """

    print("="*80)
    print("CHECKPOINTED EMBEDDING GENERATION")
    print("="*80)
    print(f"Started: {datetime.now()}")
    print(f"Target articles: {num_articles:,}")
    print(f"Checkpoint interval: {checkpoint_interval:,}")
    print("")

    # Setup paths
    output_dir = Path("embeddings")
    output_dir.mkdir(exist_ok=True)

    registry_file = output_dir / "article_registry.pkl"
    checkpoint_file = output_dir / "current_checkpoint.pkl"
    final_output = output_dir / "wikipedia_embeddings.pkl"

    # Load article registry
    registry = load_article_registry(registry_file)
    print(f"[1/6] Article Registry Status:")
    print(f"  Already embedded: {len(registry['embedded_indices']):,} articles")
    print(f"  Available to embed: {registry['total_available'] - len(registry['embedded_indices']):,}")
    print("")

    # Determine device
    if use_mps and torch.backends.mps.is_available():
        device = "mps"
        print(f"✓ Metal Performance Shaders (MPS) available")
    elif torch.cuda.is_available():
        device = "cuda"
        print(f"✓ CUDA available")
    else:
        device = "cpu"
        print(f"⚠ Using CPU (no GPU acceleration)")
    print(f"Device: {device}")
    print("")

    # Load Wikipedia articles
    print("[2/6] Loading Wikipedia articles...")
    start = time.time()
    with open('data/wikipedia.pkl', 'rb') as f:
        all_wiki_articles = pickle.load(f)
    load_time = time.time() - start
    print(f"  ✓ Loaded {len(all_wiki_articles):,} articles in {load_time:.2f}s")
    print("")

    # Select articles to embed (random sample without replacement)
    print("[3/6] Selecting articles to embed...")
    available_indices = set(range(len(all_wiki_articles))) - registry['embedded_indices']

    if len(available_indices) < num_articles:
        print(f"  ⚠ Warning: Only {len(available_indices):,} articles available (requested {num_articles:,})")
        num_articles = len(available_indices)

    # Random sample without replacement
    np.random.seed(42 + len(registry['embedded_indices']))  # Reproducible but different each run
    selected_indices = np.random.choice(
        list(available_indices),
        size=num_articles,
        replace=False
    )
    selected_indices = sorted(selected_indices)  # Sort for efficient access

    print(f"  ✓ Selected {len(selected_indices):,} articles")
    print(f"  Index range: {selected_indices[0]} to {selected_indices[-1]}")
    print("")

    # Authenticate with HuggingFace
    hf_token_file = Path(".credentials/hf.token")
    if hf_token_file.exists():
        print("[4/6] Authenticating with HuggingFace...")
        with open(hf_token_file, 'r') as f:
            hf_token = f.read().strip()
        from huggingface_hub import login
        login(token=hf_token)
        print("  ✓ Authenticated")
        print("")

    # Load embedding model
    print(f"[5/6] Loading google/embeddinggemma-300m on {device}...")
    model_start = time.time()
    model = SentenceTransformer('google/embeddinggemma-300m', device=device)
    model_time = time.time() - model_start
    dim = model.get_sentence_embedding_dimension()
    print(f"  ✓ Model loaded in {model_time:.2f}s")
    print(f"  Embedding dimension: {dim}")
    print("")

    # Generate embeddings with checkpoints
    print(f"[6/6] Generating embeddings with checkpoints every {checkpoint_interval:,} articles...")
    print("")

    all_embeddings = []
    all_titles = []
    all_urls = []
    all_indices = []

    embed_start = time.time()
    articles_processed = 0

    # Process in chunks for checkpointing
    for chunk_start in tqdm(range(0, len(selected_indices), checkpoint_interval), desc="Checkpoints"):
        chunk_end = min(chunk_start + checkpoint_interval, len(selected_indices))
        chunk_indices = selected_indices[chunk_start:chunk_end]

        # Extract texts for this chunk
        chunk_texts = []
        chunk_titles = []
        chunk_urls = []

        for idx in chunk_indices:
            article = all_wiki_articles[idx]
            if isinstance(article, dict):
                text = article.get('text', article.get('content', str(article)))
                title = article.get('title', f'Article_{idx}')
                url = article.get('url', '')
            else:
                text = str(article)
                title = f'Article_{idx}'
                url = ''

            chunk_texts.append(text)
            chunk_titles.append(title)
            chunk_urls.append(url)

        # Generate embeddings for chunk
        chunk_embeddings = model.encode(
            chunk_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            device=device
        )

        # Accumulate results
        all_embeddings.append(chunk_embeddings)
        all_titles.extend(chunk_titles)
        all_urls.extend(chunk_urls)
        all_indices.extend(chunk_indices)

        articles_processed += len(chunk_indices)

        # Save checkpoint
        checkpoint_data = {
            'embeddings': np.vstack(all_embeddings) if all_embeddings else np.array([]),
            'titles': all_titles,
            'urls': all_urls,
            'indices': all_indices,
            'articles_processed': articles_processed,
            'timestamp': datetime.now().isoformat(),
            'model': 'google/embeddinggemma-300m',
            'device': device
        }
        save_checkpoint(checkpoint_file, checkpoint_data)

    embed_time = time.time() - embed_start
    rate = articles_processed / embed_time if embed_time > 0 else 0

    print("")
    print(f"  ✓ Generated {articles_processed:,} embeddings ({dim}-dim)")
    print(f"  Time: {embed_time:.2f}s ({embed_time/60:.2f} min)")
    print(f"  Rate: {rate:.2f} articles/sec")
    print("")

    # Combine all embeddings
    final_embeddings = np.vstack(all_embeddings)

    # Update registry
    registry['embedded_indices'].update(all_indices)
    registry['article_count'] = len(registry['embedded_indices'])
    save_article_registry(registry_file, registry)

    print("[7/7] Saving final output...")

    # Load existing embeddings if they exist
    if final_output.exists():
        print("  Loading existing embeddings...")
        with open(final_output, 'rb') as f:
            existing_data = pickle.load(f)

        # Merge with new embeddings
        merged_embeddings = np.vstack([existing_data['embeddings'], final_embeddings])
        merged_titles = existing_data['titles'] + all_titles
        merged_urls = existing_data['urls'] + all_urls
        merged_indices = existing_data['indices'] + all_indices
    else:
        merged_embeddings = final_embeddings
        merged_titles = all_titles
        merged_urls = all_urls
        merged_indices = all_indices

    # Save final merged output
    output_data = {
        'embeddings': merged_embeddings,
        'titles': merged_titles,
        'urls': merged_urls,
        'indices': merged_indices,
        'total_articles': len(merged_indices),
        'timestamp': datetime.now().isoformat(),
        'model': 'google/embeddinggemma-300m',
        'device': device
    }

    with open(final_output, 'wb') as f:
        pickle.dump(output_data, f)

    file_size_mb = final_output.stat().st_size / 1e6
    print(f"  ✓ Saved to {final_output}")
    print(f"  File size: {file_size_mb:.2f} MB")
    print(f"  Total articles now embedded: {len(merged_indices):,}")
    print("")

    # Verify embeddings
    norms = np.linalg.norm(merged_embeddings, axis=1)
    print("Embedding quality check:")
    print(f"  Norms - mean: {norms.mean():.4f}, std: {norms.std():.4f}")
    print(f"  Shape: {merged_embeddings.shape}")
    print("")

    # Clean up checkpoint
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print("  ✓ Checkpoint file removed")

    print("="*80)
    print("✓ CHECKPOINTED GENERATION COMPLETE")
    print("="*80)
    print(f"New articles processed: {articles_processed:,}")
    print(f"Total articles embedded: {len(merged_indices):,}")
    print(f"Remaining articles: {250000 - len(merged_indices):,}")
    print(f"Total time: {embed_time:.2f}s ({embed_time/60:.2f} min)")
    print(f"Rate: {rate:.2f} articles/sec")
    print(f"Output: {final_output}")
    print(f"Registry: {registry_file}")
    print(f"Completed: {datetime.now()}")
    print("")

    print("To add more embeddings later, run:")
    print(f"  python {Path(__file__).name} --num-articles N")
    print("")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate embeddings with checkpointing')
    parser.add_argument('--num-articles', type=int, default=25000,
                        help='Number of articles to process (default: 25000)')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size for embedding generation (default: 32, safe for MPS)')
    parser.add_argument('--checkpoint-interval', type=int, default=1000,
                        help='Save checkpoint every N articles (default: 1000)')
    parser.add_argument('--cpu-only', action='store_true',
                        help='Force CPU-only mode (disable Metal/GPU)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from existing checkpoint')

    args = parser.parse_args()

    generate_embeddings_checkpointed(
        num_articles=args.num_articles,
        batch_size=args.batch_size,
        checkpoint_interval=args.checkpoint_interval,
        use_mps=not args.cpu_only,
        resume=args.resume
    )
