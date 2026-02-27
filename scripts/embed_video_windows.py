#!/usr/bin/env python3
"""
T-V003: Create sliding-window embeddings for all video transcripts.

Splits each transcript into sliding windows (512 words, 50-word stride per
CL-002). Embeds each window using google/embeddinggemma-300m (768-dim) via
SentenceTransformer (same encoding method as articles, questions, and full
transcript embeddings — critical for UMAP transform() consistency).

Supports GPU (MPS/CUDA) with batch processing. Resumes from checkpoint
(skips videos that already have .npy files).

Input:  data/videos/.working/transcripts/{video_id}.txt
Output: data/videos/.working/embeddings/{video_id}.npy (shape [N_windows, 768])

See FR-V003, FR-V004, CL-002.

Usage:
    python scripts/embed_video_windows.py
    python scripts/embed_video_windows.py --cpu-only
    python scripts/embed_video_windows.py --batch-size 16
    python scripts/embed_video_windows.py --dry-run
    python scripts/embed_video_windows.py --force  # re-embed all, ignoring existing
"""

import argparse
import os
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
TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "transcripts"
EMBEDDING_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "embeddings"
MODEL_NAME = "google/embeddinggemma-300m"

WINDOW_SIZE = 512  # words (FR-V003)
STRIDE = 50  # words (CL-002)
MIN_WORDS = 50  # minimum words for a single-window transcript


def parse_args():
    parser = argparse.ArgumentParser(
        description="Embed video transcript sliding windows"
    )
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU mode")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Embedding batch size"
    )
    parser.add_argument(
        "--transcript-dir", type=str, default=str(TRANSCRIPT_DIR),
        help="Directory containing .txt transcript files",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(EMBEDDING_DIR),
        help="Directory for output .npy files",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count windows without embedding",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-embed all videos (ignore existing .npy files)",
    )
    return parser.parse_args()


def create_windows(text, window_size=WINDOW_SIZE, stride=STRIDE):
    """Split text into overlapping sliding windows.

    Returns list of window strings. If transcript is shorter than window_size
    but has at least MIN_WORDS words, returns a single window containing the
    full text. Returns empty list if transcript is too short.
    """
    words = text.split()
    if len(words) < MIN_WORDS:
        return []

    if len(words) < window_size:
        return [text]

    windows = []
    for i in range(0, len(words) - window_size + 1, stride):
        window = " ".join(words[i : i + window_size])
        windows.append(window)
    return windows


def main():
    args = parse_args()
    transcript_dir = Path(args.transcript_dir)
    output_dir = Path(args.output_dir)

    print("=" * 70)
    print("VIDEO SLIDING-WINDOW EMBEDDING")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Window: {WINDOW_SIZE} words, stride {STRIDE} words")
    print(f"Min words: {MIN_WORDS}")
    print()

    # Validate input
    if not transcript_dir.exists():
        print(f"ERROR: {transcript_dir} not found.")
        print("Run download_transcripts.py first.")
        sys.exit(1)

    transcript_files = sorted(transcript_dir.glob("*.txt"))
    if not transcript_files:
        print("ERROR: No transcript files found.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter to un-embedded transcripts (unless --force)
    if args.force:
        remaining = list(transcript_files)
    else:
        remaining = []
        for tf in transcript_files:
            video_id = tf.stem
            emb_path = output_dir / f"{video_id}.npy"
            if not emb_path.exists():
                remaining.append(tf)

    already_done = len(transcript_files) - len(remaining)
    print(f"Total transcripts: {len(transcript_files)}")
    print(f"Already embedded: {already_done}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("Nothing to do.")
        return

    # Dry run: count windows only
    if args.dry_run:
        total_windows = 0
        skipped = 0
        for tf in remaining:
            text = tf.read_text(encoding="utf-8").strip()
            windows = create_windows(text)
            if windows:
                total_windows += len(windows)
            else:
                skipped += 1
        print(f"\nDRY RUN:")
        print(f"  Would embed: {len(remaining) - skipped} videos")
        print(f"  Total windows: {total_windows}")
        print(f"  Skipped (too short): {skipped}")
        if len(remaining) - skipped > 0:
            print(f"  Avg windows/video: {total_windows / (len(remaining) - skipped):.0f}")
        return

    # Load model (SentenceTransformer for consistency with pipeline)
    import torch
    from sentence_transformers import SentenceTransformer

    if not args.cpu_only and torch.backends.mps.is_available():
        device = "mps"
    elif not args.cpu_only and torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    print(f"\nDevice: {device}")
    print(f"Loading {MODEL_NAME}...")
    model_start = time.time()
    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension()
    print(f"Model loaded in {time.time() - model_start:.1f}s (dim={dim})")

    total_windows = 0
    videos_done = 0
    skipped_empty = 0
    t0 = time.time()

    for i, tf in enumerate(remaining):
        video_id = tf.stem
        emb_path = output_dir / f"{video_id}.npy"

        # Read transcript and create windows
        text = tf.read_text(encoding="utf-8").strip()
        windows = create_windows(text)

        if not windows:
            skipped_empty += 1
            continue

        # Embed all windows for this video
        embeddings = model.encode(
            windows,
            batch_size=args.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            device=device,
        ).astype(np.float32)

        # Validate
        assert embeddings.shape == (len(windows), dim), (
            f"Video {video_id}: expected ({len(windows)}, {dim}), got {embeddings.shape}"
        )
        assert not np.any(np.isnan(embeddings)), f"NaN in {video_id} embeddings"

        np.save(emb_path, embeddings)

        total_windows += len(windows)
        videos_done += 1

        # Progress every 100 videos
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(remaining) - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i + 1}/{len(remaining)}] "
                f"{videos_done} embedded, {total_windows} windows, "
                f"{elapsed:.0f}s elapsed, ETA {eta:.0f}s"
            )

    elapsed = time.time() - t0

    # Count total embedding files
    emb_count = len(list(output_dir.glob("*.npy")))

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Videos embedded: {videos_done}")
    print(f"  Skipped (too short): {skipped_empty}")
    print(f"  Total windows: {total_windows}")
    if videos_done > 0:
        print(f"  Avg windows/video: {total_windows / videos_done:.1f}")
    print(f"  Time: {elapsed:.1f}s ({videos_done / elapsed:.1f} videos/sec)" if elapsed > 0 else "")
    print(f"  Total .npy files on disk: {emb_count}")
    print(f"  Finished: {datetime.now()}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
