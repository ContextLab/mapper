#!/usr/bin/env python3
"""
Embed all 2,500 quiz questions using google/embeddinggemma-300m.

Each question is embedded as: question_text + " " + correct_answer_text
This gives richer semantic signal than question text alone, anchoring each
question near its topic in the shared embedding space.

Input:  data/domains/{domain_id}.json (50 files × 50 questions each)
Output: embeddings/question_embeddings_2500.pkl
        - embeddings: np.ndarray (N, 768) float32
        - question_ids: list[str]
        - question_texts: list[str]   (the raw embedding input strings)
        - domain_ids: list[list[str]] (domains each question belongs to)
        - model: str
        - dim: int
        - num_questions: int
        - checksum: str  (SHA-256 of the embedding matrix bytes)
        - timestamp: str

Usage:
    python scripts/embed_questions_v2.py
    python scripts/embed_questions_v2.py --cpu-only
    python scripts/embed_questions_v2.py --dry-run
"""

import argparse
import hashlib
import json
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
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"
OUTPUT_DIR = PROJECT_ROOT / "embeddings"
MODEL_NAME = "google/embeddinggemma-300m"


def parse_args():
    parser = argparse.ArgumentParser(description="Embed quiz questions (v2)")
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU mode")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Embedding batch size"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Load and validate without embedding"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (default: embeddings/question_embeddings_2500.pkl)",
    )
    return parser.parse_args()


def load_all_questions():
    """Load questions from all domain JSON files, deduplicated by ID."""
    index_path = DOMAINS_DIR / "index.json"
    with open(index_path) as f:
        index = json.load(f)

    domain_ids_list = [d["id"] for d in index["domains"]]

    seen_ids = set()
    questions = []
    domain_map = {}  # question_id -> list of domain_ids

    for domain_id in sorted(domain_ids_list):
        domain_path = DOMAINS_DIR / f"{domain_id}.json"
        if not domain_path.exists():
            print(f"  WARNING: {domain_path} not found, skipping")
            continue

        with open(domain_path) as f:
            bundle = json.load(f)

        if "questions" not in bundle:
            print(f"  WARNING: {domain_id}.json has no 'questions' key, skipping")
            continue

        for q in bundle["questions"]:
            qid = q["id"]
            if qid not in seen_ids:
                seen_ids.add(qid)
                questions.append(q)
                domain_map[qid] = q.get("domain_ids", [domain_id])
            else:
                # Track additional domain membership
                existing = domain_map[qid]
                if domain_id not in existing:
                    existing.append(domain_id)

    return questions, domain_map


def build_embedding_texts(questions):
    """Build embedding input: question_text + ' ' + correct_answer_text."""
    texts = []
    for q in questions:
        question_text = q["question_text"]
        correct_key = q["correct_answer"]  # "A", "B", "C", or "D"
        correct_text = q["options"][correct_key]
        embedding_text = f"{question_text} {correct_text}"
        texts.append(embedding_text)
    return texts


def validate_questions(questions, domain_map):
    """Validate question data before embedding."""
    errors = []

    for i, q in enumerate(questions):
        if "id" not in q:
            errors.append(f"Question {i}: missing 'id'")
        if "question_text" not in q:
            errors.append(f"Question {i} ({q.get('id', '?')}): missing 'question_text'")
        if "options" not in q:
            errors.append(f"Question {i} ({q.get('id', '?')}): missing 'options'")
        elif "correct_answer" not in q:
            errors.append(f"Question {i} ({q.get('id', '?')}): missing 'correct_answer'")
        elif q["correct_answer"] not in q["options"]:
            errors.append(
                f"Question {i} ({q.get('id', '?')}): correct_answer "
                f"'{q['correct_answer']}' not in options {list(q['options'].keys())}"
            )

    # Check for duplicate IDs
    ids = [q["id"] for q in questions]
    if len(ids) != len(set(ids)):
        from collections import Counter
        dupes = [k for k, v in Counter(ids).items() if v > 1]
        errors.append(f"Duplicate question IDs: {dupes}")

    return errors


def main():
    args = parse_args()

    print("=" * 70)
    print("QUESTION EMBEDDING GENERATION (v2)")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Embedding text: question_text + correct_answer_text")
    print()

    # Step 1: Load all questions
    print("Step 1: Loading questions from domain files...")
    questions, domain_map = load_all_questions()
    all_domains = set()
    for domains in domain_map.values():
        all_domains.update(domains)
    print(f"  Loaded {len(questions)} unique questions from {len(all_domains)} domains")

    # Step 2: Validate
    print("\nStep 2: Validating questions...")
    errors = validate_questions(questions, domain_map)
    if errors:
        print(f"  VALIDATION FAILED ({len(errors)} errors):")
        for e in errors[:10]:
            print(f"    - {e}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more")
        sys.exit(1)
    print(f"  All {len(questions)} questions validated OK")

    # Step 3: Build embedding texts
    print("\nStep 3: Building embedding texts...")
    texts = build_embedding_texts(questions)
    question_ids = [q["id"] for q in questions]
    question_domains = [domain_map[qid] for qid in question_ids]

    # Show samples
    print(f"  Sample texts:")
    for i in range(min(3, len(texts))):
        preview = texts[i][:100] + "..." if len(texts[i]) > 100 else texts[i]
        print(f"    [{i}] {preview}")

    if args.dry_run:
        print(f"\n  DRY RUN: Would embed {len(texts)} questions. Exiting.")
        return

    # Step 4: Setup device
    import torch

    if not args.cpu_only and torch.backends.mps.is_available():
        device = "mps"
    elif not args.cpu_only and torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"\nStep 4: Device: {device}")

    # Step 5: Load model
    print(f"\nStep 5: Loading {MODEL_NAME}...")
    model_start = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME, device=device)
    dim = model.get_sentence_embedding_dimension()
    print(f"  Model loaded in {time.time() - model_start:.1f}s (dim={dim})")

    # Step 6: Embed
    print(f"\nStep 6: Embedding {len(texts)} questions...")
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

    # Step 7: Validate embeddings
    print("\nStep 7: Validating embeddings...")
    assert embeddings.shape == (len(questions), dim), (
        f"Expected ({len(questions)}, {dim}), got {embeddings.shape}"
    )
    assert not np.any(np.isnan(embeddings)), "NaN values found in embeddings"
    assert not np.any(np.isinf(embeddings)), "Inf values found in embeddings"

    norms = np.linalg.norm(embeddings, axis=1)
    print(f"  Norms -- mean: {norms.mean():.4f}, std: {norms.std():.4f}, "
          f"min: {norms.min():.4f}, max: {norms.max():.4f}")

    # Compute checksum
    checksum = hashlib.sha256(embeddings.tobytes()).hexdigest()
    print(f"  SHA-256 checksum: {checksum[:16]}...")

    # Step 8: Save
    output_path = Path(args.output) if args.output else OUTPUT_DIR / "question_embeddings_2500.pkl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "embeddings": embeddings,
        "question_ids": question_ids,
        "question_texts": texts,
        "domain_ids": question_domains,
        "model": MODEL_NAME,
        "dim": dim,
        "num_questions": len(questions),
        "checksum": checksum,
        "timestamp": datetime.now().isoformat(),
        "embedding_method": "question_text + correct_answer_text",
    }
    with open(output_path, "wb") as f:
        pickle.dump(output_data, f)

    file_size = output_path.stat().st_size
    print(f"\nStep 8: Saved to {output_path} ({file_size / 1024:.1f} KB)")

    print(f"\n{'=' * 70}")
    print(f"COMPLETE -- {len(questions)} questions embedded ({dim}-dim)")
    print(f"{'=' * 70}")
    print(f"Finished: {datetime.now()}")


if __name__ == "__main__":
    main()
