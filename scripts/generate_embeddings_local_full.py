#!/usr/bin/env python3
"""
Generate embeddings for all 250K Wikipedia articles locally using MPS (Apple Silicon).

Outputs: embeddings/wikipedia_embeddings.pkl
  - Contains numpy array of shape (250000, 768) + metadata

Uses google/embeddinggemma-300m with checkpointing every 5000 articles.
Estimated time: ~4.5 hours on Apple Silicon MPS.
"""

import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["HF_TOKEN"] = open(".credentials/hf.token").read().strip()

import pickle
import time
import sys
import numpy as np
from pathlib import Path
from datetime import datetime


def main():
    print("=" * 80)
    print("LOCAL EMBEDDING GENERATION (MPS)")
    print("=" * 80)
    print(f"Started: {datetime.now()}")
    print()

    # Paths
    input_file = Path("wikipedia.pkl")
    output_dir = Path("embeddings")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "wikipedia_embeddings.pkl"
    checkpoint_file = output_dir / "local_checkpoint.pkl"

    # Load articles
    print("[1/4] Loading Wikipedia articles...")
    t0 = time.time()
    with open(input_file, "rb") as f:
        articles = pickle.load(f)
    print(f"  Loaded {len(articles):,} articles in {time.time() - t0:.1f}s")

    # Extract text
    print("[2/4] Extracting article text...")
    texts = []
    for a in articles:
        text = a.get("text", str(a))
        texts.append(text)
    print(
        f"  {len(texts):,} texts, avg length: {sum(len(t) for t in texts[:1000]) / 1000:.0f} chars"
    )
    print()

    # Load model
    import torch
    from sentence_transformers import SentenceTransformer

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[3/4] Loading google/embeddinggemma-300m on {device}...")
    t0 = time.time()
    model = SentenceTransformer("google/embeddinggemma-300m", device=device)
    dim = model.get_sentence_embedding_dimension()
    print(f"  Model loaded in {time.time() - t0:.1f}s, dim={dim}")
    print()

    # Check for checkpoint
    start_idx = 0
    all_embeddings = None
    if checkpoint_file.exists():
        print("  Found checkpoint, resuming...")
        with open(checkpoint_file, "rb") as f:
            cp = pickle.load(f)
        start_idx = cp["next_index"]
        all_embeddings = cp["embeddings"]
        print(
            f"  Resuming from index {start_idx:,} ({start_idx}/{len(texts)} = {100 * start_idx / len(texts):.1f}%)"
        )
    else:
        all_embeddings = np.zeros((len(texts), dim), dtype=np.float32)

    # Generate embeddings in chunks with checkpointing
    CHUNK_SIZE = 5000
    BATCH_SIZE = 32
    total = len(texts)

    print(f"[4/4] Generating embeddings...")
    print(f"  Total: {total:,}, Starting from: {start_idx:,}")
    print(f"  Batch size: {BATCH_SIZE}, Checkpoint every: {CHUNK_SIZE:,}")
    print()

    overall_start = time.time()

    for chunk_start in range(start_idx, total, CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, total)
        chunk_texts = texts[chunk_start:chunk_end]

        t0 = time.time()
        chunk_embeddings = model.encode(
            chunk_texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            convert_to_numpy=True,
            device=device,
        )
        elapsed = time.time() - t0
        rate = len(chunk_texts) / elapsed

        all_embeddings[chunk_start:chunk_end] = chunk_embeddings

        # Progress
        done = chunk_end
        pct = 100 * done / total
        total_elapsed = time.time() - overall_start
        if done > start_idx:
            items_done = done - start_idx
            avg_rate = items_done / total_elapsed
            eta_sec = (total - done) / avg_rate if avg_rate > 0 else 0
            eta_min = eta_sec / 60
            print(
                f"  [{done:>7,}/{total:,}] {pct:5.1f}%  "
                f"chunk: {rate:.1f} items/s  "
                f"avg: {avg_rate:.1f} items/s  "
                f"ETA: {eta_min:.0f} min  "
                f"elapsed: {total_elapsed / 60:.0f} min"
            )

        # Save checkpoint
        with open(checkpoint_file, "wb") as f:
            pickle.dump(
                {
                    "embeddings": all_embeddings,
                    "next_index": chunk_end,
                    "timestamp": datetime.now().isoformat(),
                    "model": "google/embeddinggemma-300m",
                    "device": device,
                },
                f,
            )

    # Save final output
    print()
    print("Saving final embeddings...")
    with open(output_file, "wb") as f:
        pickle.dump(
            {
                "embeddings": all_embeddings,
                "num_articles": len(articles),
                "model": "google/embeddinggemma-300m",
                "device": device,
                "dim": dim,
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time() - overall_start,
            },
            f,
        )

    file_size_mb = output_file.stat().st_size / 1e6
    total_time = time.time() - overall_start

    # Clean up checkpoint
    if checkpoint_file.exists():
        checkpoint_file.unlink()

    # Verify
    norms = np.linalg.norm(all_embeddings, axis=1)

    print()
    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"  Output: {output_file} ({file_size_mb:.0f} MB)")
    print(f"  Shape: {all_embeddings.shape}")
    print(f"  Norms - mean: {norms.mean():.4f}, std: {norms.std():.4f}")
    print(f"  Time: {total_time / 60:.1f} min ({total_time / 3600:.1f} hours)")
    print(f"  Rate: {(len(texts) - start_idx) / total_time:.1f} items/sec")
    print(f"  Finished: {datetime.now()}")


if __name__ == "__main__":
    main()
