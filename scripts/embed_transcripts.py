#!/usr/bin/env python3
"""
Embed full video transcripts using google/embeddinggemma-300m.

Produces ONE embedding per transcript (the full document), used for joint
UMAP training alongside article and question embeddings. This is separate
from the sliding-window embeddings used for video trajectories (which are
projected via reducer.transform() after UMAP is trained).

Transcripts shorter than 100 words are excluded (per CL-021).

NOTE: pickle is used for numpy array serialization (standard ML pipeline format).

Input:  data/videos/.working/transcripts/*.txt
Output: embeddings/transcript_embeddings.pkl
        - embeddings: np.ndarray (N, 768) float32
        - video_ids: list[str]
        - transcript_lengths: list[int]   (word counts)
        - model: str
        - dim: int
        - num_transcripts: int
        - checksum: str
        - timestamp: str

Usage:
    python scripts/embed_transcripts.py
    python scripts/embed_transcripts.py --cpu-only
    python scripts/embed_transcripts.py --transcript-dir data/videos/.working/transcripts
    python scripts/embed_transcripts.py --dry-run
"""

import argparse
import hashlib
import os
import pickle
import sys
import time
import numpy as np
from datetime import datetime
from pathlib import Path

# macOS threading fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "embeddings"
MODEL_NAME = "google/embeddinggemma-300m"

MIN_WORDS = 100  # CL-021: exclude transcripts shorter than 100 words


def parse_args():
    parser = argparse.ArgumentParser(description="Embed video transcripts")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU mode")
    parser.add_argument(
        "--batch-size", type=int, default=8, help="Embedding batch size (smaller for long texts)"
    )
    parser.add_argument(
        "--transcript-dir",
        type=str,
        default=str(PROJECT_ROOT / "data" / "videos" / ".working" / "transcripts"),
        help="Directory containing .txt transcript files",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Load and validate without embedding"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (default: embeddings/transcript_embeddings.pkl)",
    )
    return parser.parse_args()


def load_transcripts(transcript_dir, min_words=MIN_WORDS):
    """Load all .txt transcripts from directory, filtering by minimum length."""
    transcript_dir = Path(transcript_dir)
    if not transcript_dir.exists():
        print(f"ERROR: Transcript directory not found: {transcript_dir}")
        sys.exit(1)

    txt_files = sorted(transcript_dir.glob("*.txt"))
    if not txt_files:
        print(f"ERROR: No .txt files found in {transcript_dir}")
        sys.exit(1)

    transcripts = []
    skipped_short = 0
    skipped_empty = 0

    for f in txt_files:
        video_id = f.stem  # filename without .txt extension
        text = f.read_text(encoding="utf-8").strip()

        if not text:
            skipped_empty += 1
            continue

        word_count = len(text.split())
        if word_count < min_words:
            skipped_short += 1
            continue

        transcripts.append({
            "video_id": video_id,
            "text": text,
            "word_count": word_count,
        })

    print(f"  Found {len(txt_files)} transcript files")
    print(f"  Loaded {len(transcripts)} valid transcripts (>= {min_words} words)")
    if skipped_short:
        print(f"  Skipped {skipped_short} short transcripts (< {min_words} words)")
    if skipped_empty:
        print(f"  Skipped {skipped_empty} empty transcripts")

    return transcripts


def main():
    args = parse_args()

    print("=" * 70)
    print("TRANSCRIPT EMBEDDING GENERATION")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Min words: {MIN_WORDS}")
    print()

    # Step 1: Load transcripts
    print("Step 1: Loading transcripts...")
    transcripts = load_transcripts(args.transcript_dir)

    if not transcripts:
        print("ERROR: No valid transcripts to embed")
        sys.exit(1)

    # Stats
    word_counts = [t["word_count"] for t in transcripts]
    print(f"\n  Word count stats:")
    print(f"    min: {min(word_counts)}, max: {max(word_counts)}, "
          f"mean: {sum(word_counts) / len(word_counts):.0f}, "
          f"median: {sorted(word_counts)[len(word_counts) // 2]}")

    # Check for duplicate video IDs
    video_ids = [t["video_id"] for t in transcripts]
    if len(video_ids) != len(set(video_ids)):
        from collections import Counter
        dupes = [k for k, v in Counter(video_ids).items() if v > 1]
        print(f"  ERROR: Duplicate video IDs: {dupes[:5]}")
        sys.exit(1)
    print(f"  All {len(video_ids)} video IDs are unique")

    if args.dry_run:
        print(f"\n  DRY RUN: Would embed {len(transcripts)} transcripts. Exiting.")
        return

    # Step 2: Setup device
    import torch

    if not args.cpu_only and torch.backends.mps.is_available():
        device = "mps"
    elif not args.cpu_only and torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"\nStep 2: Device: {device}")

    # Step 3: Load model
    print(f"\nStep 3: Loading {MODEL_NAME}...")
    model_start = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension()
    print(f"  Model loaded in {time.time() - model_start:.1f}s (dim={dim})")

    # Step 4: Prepare texts
    texts = [t["text"] for t in transcripts]

    # Step 5: Embed in batches
    print(f"\nStep 4: Embedding {len(texts)} transcripts...")
    embed_start = time.time()
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        device=device,
    )
    embed_time = time.time() - embed_start
    print(f"  Embedded in {embed_time:.1f}s ({len(texts) / embed_time:.1f} items/sec)")
    print(f"  Shape: {embeddings.shape}, dtype: {embeddings.dtype}")

    # Step 6: Validate
    print("\nStep 5: Validating embeddings...")
    assert embeddings.shape == (len(transcripts), dim), (
        f"Expected ({len(transcripts)}, {dim}), got {embeddings.shape}"
    )
    assert not np.any(np.isnan(embeddings)), "NaN values found in embeddings"
    assert not np.any(np.isinf(embeddings)), "Inf values found in embeddings"

    norms = np.linalg.norm(embeddings, axis=1)
    print(f"  Norms -- mean: {norms.mean():.4f}, std: {norms.std():.4f}, "
          f"min: {norms.min():.4f}, max: {norms.max():.4f}")

    # Compute checksum
    checksum = hashlib.sha256(embeddings.tobytes()).hexdigest()
    print(f"  SHA-256 checksum: {checksum[:16]}...")

    # Step 7: Save
    output_path = Path(args.output) if args.output else OUTPUT_DIR / "transcript_embeddings.pkl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "embeddings": embeddings,
        "video_ids": video_ids,
        "transcript_lengths": [t["word_count"] for t in transcripts],
        "model": MODEL_NAME,
        "dim": dim,
        "num_transcripts": len(transcripts),
        "min_words": MIN_WORDS,
        "checksum": checksum,
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_path, "wb") as f:
        pickle.dump(output_data, f)

    file_size = output_path.stat().st_size
    print(f"\nStep 6: Saved to {output_path} ({file_size / 1024:.1f} KB)")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE -- {len(transcripts)} transcripts embedded ({dim}-dim)")
    print(f"{'=' * 70}")
    print(f"Finished: {datetime.now()}")


if __name__ == "__main__":
    main()
