#!/usr/bin/env python3
"""
Generate coordinates for quiz questions by embedding them with google/embeddinggemma-300m,
projecting to 2D using UMAP fitted on question embeddings per domain,
and computing PCA-3 z-coordinates.

Each domain's questions are placed within the domain's pre-defined region
from data/domains/index.json.

Usage:
    python scripts/generate_question_coords.py
    python scripts/generate_question_coords.py --cpu-only
    python scripts/generate_question_coords.py --domain physics

Input: /tmp/merged_domains/{domain_id}.json (50 questions each)
Output: data/domains/{domain_id}_questions.json (with x, y, z coordinates)
"""

import json
import os
import sys
import hashlib
import argparse
import numpy as np
import time
from pathlib import Path
from datetime import datetime

# macOS threading fix
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate question coordinates")
    parser.add_argument(
        "--domain", type=str, default=None, help="Process single domain"
    )
    parser.add_argument("--cpu-only", action="store_true", help="Force CPU mode")
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Embedding batch size"
    )
    return parser.parse_args()


def generate_question_id(question_text: str) -> str:
    """Generate deterministic 16-char hex ID from question text."""
    return hashlib.sha256(question_text.encode()).hexdigest()[:16]


def embed_texts(texts: list, model, device: str, batch_size: int = 32) -> np.ndarray:
    """Embed a list of texts using the SentenceTransformer model."""
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 20,
        convert_to_numpy=True,
        device=device,
    )
    return embeddings


def project_to_region(embeddings: np.ndarray, region: dict) -> tuple:
    """
    Project high-dimensional embeddings into a 2D region using PCA.
    PCA is fast, deterministic, and works well for 50 points.
    Returns (x_coords, y_coords) arrays normalized to region bounds.
    """
    from sklearn.decomposition import PCA

    n = len(embeddings)
    n_components = min(2, n, embeddings.shape[1])

    if n_components < 2:
        rng = np.random.default_rng(42)
        x = rng.uniform(region["x_min"] + 0.02, region["x_max"] - 0.02, n)
        y = rng.uniform(region["y_min"] + 0.02, region["y_max"] - 0.02, n)
        return x, y

    pca = PCA(n_components=2, random_state=42)
    coords_2d = pca.fit_transform(embeddings)

    # Normalize to [0, 1] then scale to region
    for dim in range(2):
        col = coords_2d[:, dim]
        cmin, cmax = col.min(), col.max()
        if cmax > cmin:
            coords_2d[:, dim] = (col - cmin) / (cmax - cmin)
        else:
            coords_2d[:, dim] = 0.5

    # Map to region with small margin to keep points inside
    margin = 0.01
    x_min = region["x_min"] + margin
    x_max = region["x_max"] - margin
    y_min = region["y_min"] + margin
    y_max = region["y_max"] - margin

    x = x_min + coords_2d[:, 0] * (x_max - x_min)
    y = y_min + coords_2d[:, 1] * (y_max - y_min)

    return x, y


def compute_z_from_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """Compute PCA-3 z-coordinate from embeddings, normalized to [0, 1]."""
    from sklearn.decomposition import PCA

    n = len(embeddings)
    n_components = min(3, n, embeddings.shape[1])
    if n_components < 3:
        return np.full(n, 0.5)

    pca = PCA(n_components=n_components, random_state=42)
    components = pca.fit_transform(embeddings)

    pc3 = components[:, 2]
    pc3_min, pc3_max = pc3.min(), pc3.max()
    if pc3_max > pc3_min:
        z = (pc3 - pc3_min) / (pc3_max - pc3_min)
    else:
        z = np.full(n, 0.5)

    return z


def process_domain(
    domain_id: str,
    domain_info: dict,
    questions: list,
    model,
    device: str,
    batch_size: int,
) -> list:
    """Process a single domain: embed, project, compute z, format questions."""
    print(f"\n  [{domain_id}] Embedding {len(questions)} questions...")

    # Build embedding text: question_text + reasoning
    texts = []
    for q in questions:
        text = q["question_text"]
        if q.get("reasoning"):
            text += " " + q["reasoning"]
        texts.append(text)

    embeddings = embed_texts(texts, model, device, batch_size)
    print(f"  [{domain_id}] Embeddings: {embeddings.shape}")

    # Project to domain region
    print(f"  [{domain_id}] Projecting to region {domain_info['region']}...")
    x_coords, y_coords = project_to_region(embeddings, domain_info["region"])

    # Compute z-coordinates
    z_coords = compute_z_from_embeddings(embeddings)

    # Build output questions
    output_questions = []
    for i, q in enumerate(questions):
        # Determine domain_ids (this domain + parent if sub-domain)
        domain_ids = [domain_id]
        if domain_info.get("parent_id"):
            domain_ids.append(domain_info["parent_id"])

        out_q = {
            "id": generate_question_id(q["question_text"]),
            "question_text": q["question_text"],
            "options": q["options"],
            "correct_answer": q["correct_answer"],
            "difficulty": q["difficulty"],
            "x": round(float(x_coords[i]), 6),
            "y": round(float(y_coords[i]), 6),
            "z": round(float(z_coords[i]), 6),
            "source_article": q.get("concepts_tested", [""])[0]
            if q.get("concepts_tested")
            else "",
            "domain_ids": domain_ids,
            "concepts_tested": q.get("concepts_tested", []),
        }
        output_questions.append(out_q)

    print(
        f"  [{domain_id}] ✓ {len(output_questions)} questions with coordinates "
        f"(x: [{min(x_coords):.3f}, {max(x_coords):.3f}], "
        f"y: [{min(y_coords):.3f}, {max(y_coords):.3f}])"
    )

    return output_questions


def main():
    args = parse_args()

    project_root = Path(__file__).parent.parent
    domains_index_path = project_root / "data" / "domains" / "index.json"
    merged_dir = Path("/tmp/merged_domains")
    output_dir = project_root / "data" / "domains"

    print("=" * 60)
    print("QUESTION COORDINATE GENERATION")
    print("=" * 60)
    print(f"Started: {datetime.now()}\n")

    # Load domain definitions
    with open(domains_index_path) as f:
        domains_data = json.load(f)
    domains = {d["id"]: d for d in domains_data["domains"]}

    # Filter to single domain if specified
    if args.domain:
        if args.domain not in domains:
            print(f"Error: Domain '{args.domain}' not found")
            sys.exit(1)
        domains = {args.domain: domains[args.domain]}

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
    print("Loading google/embeddinggemma-300m...")
    model_start = time.time()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("google/embeddinggemma-300m", device=device)
    print(
        f"Model loaded in {time.time() - model_start:.1f}s (dim={model.get_sentence_embedding_dimension()})"
    )

    # Process each domain
    success = []
    failed = []
    total_start = time.time()

    for domain_id, domain_info in domains.items():
        input_path = merged_dir / f"{domain_id}.json"
        output_path = output_dir / f"{domain_id}_questions.json"

        if not input_path.exists():
            print(f"\n  ✗ {domain_id}: no input file at {input_path}")
            failed.append(domain_id)
            continue

        with open(input_path) as f:
            questions = json.load(f)

        if len(questions) != 50:
            print(f"\n  ✗ {domain_id}: expected 50 questions, got {len(questions)}")
            failed.append(domain_id)
            continue

        try:
            output_questions = process_domain(
                domain_id, domain_info, questions, model, device, args.batch_size
            )

            # Save
            with open(output_path, "w") as f:
                json.dump(output_questions, f, indent=2, ensure_ascii=False)

            success.append(domain_id)

        except Exception as e:
            print(f"\n  ✗ {domain_id}: {e}")
            import traceback

            traceback.print_exc()
            failed.append(domain_id)

    total_time = time.time() - total_start

    print(f"\n{'=' * 60}")
    print(f"RESULTS")
    print(f"{'=' * 60}")
    print(f"Success: {len(success)}/{len(domains)} domains")
    print(f"Failed: {len(failed)} ({', '.join(failed) if failed else 'none'})")
    print(f"Total time: {total_time:.1f}s")
    print(f"Output: {output_dir}/")
    print(f"Completed: {datetime.now()}")


if __name__ == "__main__":
    main()
