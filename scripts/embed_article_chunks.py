#!/usr/bin/env python3
"""
Chunk all 250K Wikipedia articles into ~500-token pieces and embed each chunk
using google/embeddinggemma-300m (same model as article + question embeddings).

These chunk embeddings are used for RAG-based domain assignment: given a domain
query, find the most relevant article chunks by cosine similarity, then map
chunks back to their source articles.

Input:  wikipedia.pkl (250K articles with text)
Output: embeddings/chunk_embeddings.pkl
        - embeddings: np.ndarray (N_chunks, 768) float32
        - chunk_texts: list[str] — the chunk text (first 200 chars stored for debugging)
        - article_indices: list[int] — which article (0-249999) each chunk came from
        - article_titles: list[str] — title of source article per chunk
        - chunk_offsets: list[int] — char offset within article
        - model: str
        - dim: int
        - timestamp: str

Checkpoints: Saves every 50K chunks to embeddings/chunk_checkpoint_{N}.pkl
             Resumes from last checkpoint automatically.

Usage:
    python scripts/embed_article_chunks.py
    python scripts/embed_article_chunks.py --cpu-only
    python scripts/embed_article_chunks.py --resume  # resume from checkpoint
"""

import json
import os
import sys
import time
import pickle
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime

# macOS threading fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).parent.parent
MODEL_NAME = "google/embeddinggemma-300m"
CHUNK_SIZE_CHARS = 2000  # ~500 tokens
OVERLAP_CHARS = 200  # overlap between chunks
CHECKPOINT_EVERY = 50000  # save checkpoint every N chunks


def parse_args():
    parser = argparse.ArgumentParser(description="Embed article chunks")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU mode")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Embedding batch size"
    )
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    return parser.parse_args()


def chunk_article(text, chunk_size=CHUNK_SIZE_CHARS, overlap=OVERLAP_CHARS):
    """Split article text into overlapping chunks.

    Returns list of (chunk_text, char_offset) tuples.
    Tries to split at sentence/word boundaries.
    """
    if not text or len(text) <= chunk_size:
        return [(text, 0)] if text else []

    chunks = []
    step = chunk_size - overlap
    pos = 0

    while pos < len(text):
        end = min(pos + chunk_size, len(text))
        chunk = text[pos:end]

        # If not the last chunk, try to break at sentence or word boundary
        if end < len(text):
            # Try sentence boundary (. ! ?)
            last_period = max(chunk.rfind(". "), chunk.rfind("! "), chunk.rfind("? "))
            if last_period > chunk_size * 0.5:  # only if past halfway
                chunk = chunk[: last_period + 1]
                end = pos + last_period + 1
            else:
                # Try word boundary
                last_space = chunk.rfind(" ")
                if last_space > chunk_size * 0.7:
                    chunk = chunk[:last_space]
                    end = pos + last_space

        chunks.append((chunk.strip(), pos))
        pos = end if end == len(text) else max(pos + step, end - overlap)

        # Safety: ensure forward progress
        if pos <= chunks[-1][1]:
            pos = chunks[-1][1] + step

    return chunks


def load_checkpoint(embeddings_dir):
    """Find and load the latest checkpoint."""
    checkpoints = sorted(embeddings_dir.glob("chunk_checkpoint_*.pkl"))
    if not checkpoints:
        return None

    latest = checkpoints[-1]
    print(f"Loading checkpoint: {latest}")
    with open(latest, "rb") as f:
        data = pickle.load(f)
    print(f"  Chunks so far: {len(data['embeddings'])}")
    print(f"  Articles processed: {data['articles_processed']}")
    return data


def save_checkpoint(data, chunk_count, embeddings_dir):
    """Save checkpoint with current state."""
    path = embeddings_dir / f"chunk_checkpoint_{chunk_count}.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)
    print(f"  Checkpoint saved: {path} ({chunk_count} chunks)")


def main():
    args = parse_args()
    embeddings_dir = PROJECT_ROOT / "embeddings"

    print("=" * 70)
    print("ARTICLE CHUNK EMBEDDING GENERATION")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Chunk size: {CHUNK_SIZE_CHARS} chars (~500 tokens)")
    print(f"Overlap: {OVERLAP_CHARS} chars")
    print()

    # Load articles
    print("Loading wikipedia.pkl...")
    load_start = time.time()
    with open(PROJECT_ROOT / "wikipedia.pkl", "rb") as f:
        articles = pickle.load(f)
    print(f"Loaded {len(articles):,} articles in {time.time() - load_start:.1f}s")

    # Check for resume
    checkpoint = None
    start_article = 0
    all_embeddings = []
    all_article_indices = []
    all_article_titles = []
    all_chunk_offsets = []
    all_chunk_previews = []

    if args.resume:
        checkpoint = load_checkpoint(embeddings_dir)
        if checkpoint:
            start_article = checkpoint["articles_processed"]
            all_embeddings = list(checkpoint["embeddings"])
            all_article_indices = list(checkpoint["article_indices"])
            all_article_titles = list(checkpoint["article_titles"])
            all_chunk_offsets = list(checkpoint["chunk_offsets"])
            all_chunk_previews = list(checkpoint["chunk_previews"])
            print(f"Resuming from article {start_article}")

    if start_article == 0:
        # Pre-compute total chunks for progress display
        print("Pre-computing chunk count...")
        total_chunks = 0
        for a in articles:
            text = a.get("text", "")
            chunks = chunk_article(text)
            total_chunks += len(chunks)
        print(f"Total chunks to embed: {total_chunks:,}")
    else:
        total_chunks = len(all_embeddings) + sum(
            len(chunk_article(a.get("text", ""))) for a in articles[start_article:]
        )
        print(f"Remaining chunks: ~{total_chunks - len(all_embeddings):,}")
    print()

    # Setup device
    import torch

    if not args.cpu_only and torch.backends.mps.is_available():
        device = "mps"
    elif not args.cpu_only and torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"Device: {device}")

    # Load model
    print(f"Loading {MODEL_NAME}...")
    model_start = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension()
    print(f"Model loaded in {time.time() - model_start:.1f}s (dim={dim})")
    print()

    # Process articles in batches
    embed_start = time.time()
    batch_texts = []
    batch_meta = []  # (article_idx, title, offset)
    chunks_since_checkpoint = 0
    total_embedded = len(all_embeddings)
    last_report = time.time()

    for article_idx in range(start_article, len(articles)):
        article = articles[article_idx]
        text = article.get("text", "")
        title = article.get("title", "Untitled")

        chunks = chunk_article(text)

        for chunk_text, offset in chunks:
            if not chunk_text.strip():
                continue
            batch_texts.append(chunk_text)
            batch_meta.append((article_idx, title, offset, chunk_text[:200]))

        # Embed when batch is full
        while len(batch_texts) >= args.batch_size:
            batch_to_embed = batch_texts[: args.batch_size]
            meta_to_save = batch_meta[: args.batch_size]
            batch_texts = batch_texts[args.batch_size :]
            batch_meta = batch_meta[args.batch_size :]

            embeddings = model.encode(
                batch_to_embed,
                batch_size=args.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                device=device,
            )

            all_embeddings.append(embeddings)
            for aidx, atitle, aoffset, apreview in meta_to_save:
                all_article_indices.append(aidx)
                all_article_titles.append(atitle)
                all_chunk_offsets.append(aoffset)
                all_chunk_previews.append(apreview)

            total_embedded += len(batch_to_embed)
            chunks_since_checkpoint += len(batch_to_embed)

            # Progress report every 30 seconds
            now = time.time()
            if now - last_report > 30:
                elapsed = now - embed_start
                rate = (
                    total_embedded - len(checkpoint["embeddings"])
                    if checkpoint
                    else total_embedded
                ) / max(elapsed, 1)
                remaining = (total_chunks - total_embedded) / max(rate, 0.1)
                pct = total_embedded / total_chunks * 100
                print(
                    f"  [{total_embedded:>7,}/{total_chunks:,}] {pct:5.1f}%  "
                    f"rate: {rate:.1f}/s  "
                    f"article: {article_idx:,}/{len(articles):,}  "
                    f"ETA: {remaining / 60:.0f} min  "
                    f"elapsed: {elapsed / 60:.0f} min"
                )
                last_report = now

            # Checkpoint
            if chunks_since_checkpoint >= CHECKPOINT_EVERY:
                stacked = (
                    np.vstack(all_embeddings)
                    if isinstance(all_embeddings[0], np.ndarray)
                    and all_embeddings[0].ndim == 2
                    else np.array(all_embeddings)
                )
                save_checkpoint(
                    {
                        "embeddings": stacked,
                        "article_indices": all_article_indices,
                        "article_titles": all_article_titles,
                        "chunk_offsets": all_chunk_offsets,
                        "chunk_previews": all_chunk_previews,
                        "articles_processed": article_idx + 1,
                        "model": MODEL_NAME,
                        "dim": dim,
                    },
                    total_embedded,
                    embeddings_dir,
                )
                chunks_since_checkpoint = 0

    # Embed remaining batch
    if batch_texts:
        embeddings = model.encode(
            batch_texts,
            batch_size=args.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            device=device,
        )
        all_embeddings.append(embeddings)
        for aidx, atitle, aoffset, apreview in batch_meta:
            all_article_indices.append(aidx)
            all_article_titles.append(atitle)
            all_chunk_offsets.append(aoffset)
            all_chunk_previews.append(apreview)
        total_embedded += len(batch_texts)

    embed_time = time.time() - embed_start

    # Stack all embeddings
    print("\nStacking embeddings...")
    if all_embeddings and isinstance(all_embeddings[0], np.ndarray):
        final_embeddings = np.vstack(all_embeddings)
    else:
        final_embeddings = np.array(all_embeddings)

    print(f"Final shape: {final_embeddings.shape}")
    assert final_embeddings.shape[0] == len(all_article_indices), (
        f"Mismatch: {final_embeddings.shape[0]} embeddings vs {len(all_article_indices)} indices"
    )

    # Validate
    norms = np.linalg.norm(final_embeddings[:1000], axis=1)  # sample
    print(f"Norms (sample 1000) — mean: {norms.mean():.4f}, std: {norms.std():.4f}")

    # Save final output
    output_path = embeddings_dir / "chunk_embeddings.pkl"
    output_data = {
        "embeddings": final_embeddings,
        "article_indices": all_article_indices,
        "article_titles": all_article_titles,
        "chunk_offsets": all_chunk_offsets,
        "chunk_previews": all_chunk_previews,
        "model": MODEL_NAME,
        "dim": dim,
        "num_chunks": len(all_article_indices),
        "num_articles": len(articles),
        "chunk_size_chars": CHUNK_SIZE_CHARS,
        "overlap_chars": OVERLAP_CHARS,
        "timestamp": datetime.now().isoformat(),
    }

    print(f"\nSaving to {output_path}...")
    with open(output_path, "wb") as f:
        pickle.dump(output_data, f)

    file_size = output_path.stat().st_size

    # Clean up checkpoints
    for cp in embeddings_dir.glob("chunk_checkpoint_*.pkl"):
        cp.unlink()
        print(f"  Removed checkpoint: {cp.name}")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Chunks: {final_embeddings.shape[0]:,}")
    print(f"  Shape: {final_embeddings.shape}")
    print(f"  Output: {output_path} ({file_size / 1024 / 1024:.0f} MB)")
    print(f"  Time: {embed_time / 60:.1f} min ({embed_time / 3600:.1f} hours)")
    print(f"  Rate: {total_embedded / embed_time:.1f} items/sec")
    print(f"  Finished: {datetime.now()}")


if __name__ == "__main__":
    main()
