#!/usr/bin/env python3
"""
Embed all 949 quiz questions using google/embeddinggemma-300m.

Uses the SAME model as article embeddings so that UMAP transform()
will place questions in the same coordinate space as articles.

Input:  embeddings/all_questions_for_embedding.json
Output: embeddings/question_embeddings_949.pkl
        - embeddings: np.ndarray (949, 768) float32
        - question_ids: list[str]
        - question_texts: list[str]
        - model: str
        - dim: int
        - timestamp: str

Usage:
    python scripts/embed_questions.py
    python scripts/embed_questions.py --cpu-only
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


def parse_args():
    parser = argparse.ArgumentParser(description="Embed quiz questions")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU mode")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Embedding batch size"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print("QUESTION EMBEDDING GENERATION")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Model: {MODEL_NAME}")
    print()

    # Load questions
    input_path = PROJECT_ROOT / "embeddings" / "all_questions_for_embedding.json"
    with open(input_path) as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions from {input_path}")

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

    # Prepare texts — use question_text only (no reasoning, to match how
    # questions will be semantically placed on the map)
    texts = [q["question_text"] for q in questions]
    question_ids = [q["id"] for q in questions]

    # Embed
    print(f"Embedding {len(texts)} questions...")
    embed_start = time.time()
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        device=device,
    )
    embed_time = time.time() - embed_start
    print(f"Embedded in {embed_time:.1f}s ({len(texts) / embed_time:.1f} items/sec)")
    print(f"Shape: {embeddings.shape}, dtype: {embeddings.dtype}")

    # Validate
    assert embeddings.shape == (len(questions), dim), (
        f"Expected ({len(questions)}, {dim}), got {embeddings.shape}"
    )
    norms = np.linalg.norm(embeddings, axis=1)
    print(
        f"Norms — mean: {norms.mean():.4f}, std: {norms.std():.4f}, "
        f"min: {norms.min():.4f}, max: {norms.max():.4f}"
    )

    # Save
    output_path = PROJECT_ROOT / "embeddings" / "question_embeddings_949.pkl"
    output_data = {
        "embeddings": embeddings,
        "question_ids": question_ids,
        "question_texts": texts,
        "model": MODEL_NAME,
        "dim": dim,
        "num_questions": len(questions),
        "timestamp": datetime.now().isoformat(),
    }
    with open(output_path, "wb") as f:
        pickle.dump(output_data, f)

    file_size = output_path.stat().st_size
    print(f"\nSaved to {output_path} ({file_size / 1024:.1f} KB)")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE — {len(questions)} questions embedded")
    print(f"{'=' * 70}")
    print(f"Finished: {datetime.now()}")


if __name__ == "__main__":
    main()
