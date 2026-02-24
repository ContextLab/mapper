#!/usr/bin/env python3
"""
T-V003: Create sliding-window embeddings for all video transcripts.

Splits each transcript into sliding windows (512 words, 50-word stride per
CL-002). Embeds each window using google/embeddinggemma-300m (768-dim).
Supports GPU (MPS/CUDA) with batch processing. Checkpoints every 100 videos.

Input:  data/videos/.working/transcripts/{video_id}.txt
Output: data/videos/.working/embeddings/{video_id}.npy (shape [N_windows, 768])
See FR-V003, FR-V004, CL-002.
"""

import os
import sys
import time
import numpy as np
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"

TRANSCRIPT_DIR = Path("data/videos/.working/transcripts")
EMBEDDING_DIR = Path("data/videos/.working/embeddings")
MODEL_NAME = "google/embeddinggemma-300m"

WINDOW_SIZE = 512  # words
STRIDE = 50  # words (CL-002)
BATCH_SIZE = 32
CHECKPOINT_INTERVAL = 100


def create_windows(text, window_size=WINDOW_SIZE, stride=STRIDE):
    """Split text into overlapping sliding windows."""
    words = text.split()
    if len(words) < window_size:
        # Single window if text is shorter than window size but has enough content
        return [text] if len(words) >= 50 else []

    windows = []
    for i in range(0, len(words) - window_size + 1, stride):
        window = " ".join(words[i : i + window_size])
        windows.append(window)
    return windows


def embed_batch(texts, model, tokenizer, device):
    """Embed a batch of texts using mean pooling over last hidden state."""
    import torch

    inputs = tokenizer(
        texts, padding=True, truncation=True, max_length=512, return_tensors="pt"
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    # Mean pooling over non-padding tokens
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.cpu().numpy()


def get_device():
    """Detect best available device."""
    import torch

    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    if not TRANSCRIPT_DIR.exists():
        print(f"ERROR: {TRANSCRIPT_DIR} not found.")
        print("Run download_transcripts.py first.")
        sys.exit(1)

    transcript_files = sorted(TRANSCRIPT_DIR.glob("*.txt"))
    if not transcript_files:
        print("ERROR: No transcript files found.")
        sys.exit(1)

    EMBEDDING_DIR.mkdir(parents=True, exist_ok=True)

    # Filter to un-embedded transcripts
    remaining = []
    for tf in transcript_files:
        video_id = tf.stem
        emb_path = EMBEDDING_DIR / f"{video_id}.npy"
        if not emb_path.exists():
            remaining.append(tf)

    print(f"Total transcripts: {len(transcript_files)}")
    print(f"Already embedded: {len(transcript_files) - len(remaining)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("Nothing to do.")
        return

    # Load model
    import torch
    from transformers import AutoModel, AutoTokenizer

    device = get_device()
    print(f"\nDevice: {device}")
    print(f"Loading {MODEL_NAME}...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).to(device)
    model.requires_grad_(False)
    # Set to inference mode
    model.train(False)
    print("Model loaded.\n")

    total_windows = 0
    videos_done = 0
    skipped_empty = 0
    t0 = time.time()

    for i, tf in enumerate(remaining):
        video_id = tf.stem
        emb_path = EMBEDDING_DIR / f"{video_id}.npy"

        # Read transcript
        text = tf.read_text(encoding="utf-8").strip()
        windows = create_windows(text)

        if not windows:
            skipped_empty += 1
            continue

        # Embed in batches
        all_embeddings = []
        for j in range(0, len(windows), BATCH_SIZE):
            batch = windows[j : j + BATCH_SIZE]
            embs = embed_batch(batch, model, tokenizer, device)
            all_embeddings.append(embs)

        embeddings = np.vstack(all_embeddings).astype(np.float32)
        np.save(emb_path, embeddings)

        total_windows += len(windows)
        videos_done += 1

        # Progress
        if (i + 1) % CHECKPOINT_INTERVAL == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(remaining) - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i + 1}/{len(remaining)}] "
                f"{videos_done} embedded, {total_windows} total windows, "
                f"{elapsed:.0f}s elapsed, ETA {eta:.0f}s"
            )

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s")
    print(f"  Videos embedded: {videos_done}")
    print(f"  Skipped (too short): {skipped_empty}")
    print(f"  Total windows: {total_windows}")
    if videos_done > 0:
        print(f"  Avg windows/video: {total_windows / videos_done:.0f}")

    # Count total embedding files
    emb_count = len(list(EMBEDDING_DIR.glob("*.npy")))
    print(f"  Total embedding files on disk: {emb_count}")


if __name__ == "__main__":
    main()
