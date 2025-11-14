#!/usr/bin/env python3
"""
Local embedding generation using Metal (Apple Silicon GPU acceleration).

This script generates embeddings for Wikipedia articles + questions locally,
using Metal Performance Shaders (MPS) for GPU acceleration on Apple Silicon.
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

def load_questions():
    """Load the 10 questions from questions.json."""
    questions_file = Path(__file__).parent / "questions.json"

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

def generate_embeddings_local(num_articles=None, use_mps=True, batch_size=128, include_questions=False):
    """
    Generate embeddings locally using Metal acceleration.

    Args:
        num_articles: Number of articles to process (None = all 250k)
        use_mps: Whether to use Metal Performance Shaders (default True)
        batch_size: Batch size for embedding generation (default 128)
        include_questions: Whether to include questions in the embedding (default False)
    """

    # Constants
    TOTAL_ARTICLES = 250_000
    TOTAL_QUESTIONS = 10

    print("="*80)
    print("LOCAL EMBEDDING GENERATION (Metal Accelerated)")
    print("="*80)
    print(f"Started: {datetime.now()}")
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
    print("[1/5] Loading Wikipedia articles...")
    start = time.time()
    with open('wikipedia.pkl', 'rb') as f:
        wiki_articles = pickle.load(f)
    load_time = time.time() - start
    print(f"  ✓ Loaded {len(wiki_articles):,} articles in {load_time:.2f}s")

    # Limit articles if specified
    if num_articles is not None:
        wiki_articles = wiki_articles[:num_articles]
        print(f"  ⚠ Limited to first {num_articles:,} articles for testing")

    print("")

    # Load questions (optional)
    question_texts = []
    if include_questions:
        print("[2/5] Loading questions...")
        question_texts = load_questions()
        print("")
    else:
        print("[2/5] Skipping questions (include_questions=False)")
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

    # Add questions at the end (if included)
    if include_questions:
        all_items.extend(question_texts)

    total_items = len(all_items)
    print(f"Total items to process: {total_items:,}")
    print(f"  Articles: {len(wiki_articles):,}")
    if include_questions:
        print(f"  Questions: {len(question_texts)}")
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
    print(f"[4/5] Loading google/embeddinggemma-300m on {device}...")
    model_start = time.time()
    model = SentenceTransformer('google/embeddinggemma-300m', device=device)
    model_time = time.time() - model_start
    dim = model.get_sentence_embedding_dimension()
    print(f"  ✓ Model loaded in {model_time:.2f}s")
    print(f"  Embedding dimension: {dim}")
    print("")

    # Generate embeddings
    print(f"[5/5] Generating embeddings for {total_items:,} items...")
    print(f"  Batch size: {batch_size}")
    print(f"  Device: {device}")
    print("")

    embed_start = time.time()
    embeddings = model.encode(
        all_items,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        device=device
    )
    embed_time = time.time() - embed_start

    rate = total_items / embed_time
    print("")
    print(f"  ✓ Generated {embeddings.shape[0]:,} embeddings ({embeddings.shape[1]}-dim)")
    print(f"  Time: {embed_time:.2f}s ({embed_time/60:.2f} min)")
    print(f"  Rate: {rate:.2f} items/sec")
    print("")

    # Save embeddings
    print("[6/6] Saving embeddings...")
    output_dir = Path("embeddings")
    output_dir.mkdir(exist_ok=True)

    if num_articles is not None:
        output_file = output_dir / f"local_test_{num_articles}.pkl"
    else:
        output_file = output_dir / "wikipedia.pkl"

    checkpoint_data = {
        'embeddings': embeddings,
        'num_articles': len(wiki_articles),
        'num_questions': len(question_texts),
        'total_items': total_items,
        'timestamp': datetime.now().isoformat(),
        'processing_time': embed_time,
        'rate': rate,
        'model': 'google/embeddinggemma-300m',
        'device': device
    }

    with open(output_file, 'wb') as f:
        pickle.dump(checkpoint_data, f)

    file_size_mb = output_file.stat().st_size / 1e6
    print(f"  ✓ Saved to {output_file}")
    print(f"  File size: {file_size_mb:.2f} MB")
    print("")

    # Verify embeddings
    norms = np.linalg.norm(embeddings, axis=1)
    print("Embedding quality check:")
    print(f"  Norms - mean: {norms.mean():.4f}, std: {norms.std():.4f}")
    print(f"  Shape: {embeddings.shape}")
    print("")

    total_time = time.time() - embed_start
    print("="*80)
    print("✓ LOCAL GENERATION COMPLETE")
    print("="*80)
    print(f"Items processed: {total_items:,}")
    print(f"Total time: {total_time:.2f}s ({total_time/60:.2f} min)")
    print(f"Rate: {rate:.2f} items/sec")
    print(f"Output: {output_file}")
    print(f"Completed: {datetime.now()}")
    print("")

    # Estimate time for full dataset
    if num_articles is not None and num_articles < TOTAL_ARTICLES:
        estimated_full_time = (TOTAL_ARTICLES + TOTAL_QUESTIONS) / rate
        print("Estimated time for full dataset:")
        print(f"  {estimated_full_time:.2f}s ({estimated_full_time/60:.2f} min = {estimated_full_time/3600:.2f} hours)")
        print("")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate embeddings locally with Metal acceleration')
    parser.add_argument('--num-articles', type=int, default=None,
                        help='Number of articles to process (default: all 250k)')
    parser.add_argument('--cpu-only', action='store_true',
                        help='Force CPU-only mode (disable Metal/GPU)')
    parser.add_argument('--batch-size', type=int, default=128,
                        help='Batch size for embedding generation (default: 128)')
    parser.add_argument('--include-questions', action='store_true',
                        help='Include questions in embedding generation (default: False)')

    args = parser.parse_args()

    generate_embeddings_local(
        num_articles=args.num_articles,
        use_mps=not args.cpu_only,
        batch_size=args.batch_size,
        include_questions=args.include_questions
    )
