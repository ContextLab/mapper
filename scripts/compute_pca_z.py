#!/usr/bin/env python3
"""
Compute PCA-3 z-coordinates from Wikipedia embeddings.

Loads the 250K×768 embedding matrix, runs PCA, extracts the 3rd principal
component, normalizes to [0,1], and saves z-coordinates for each article.
These z-values provide the depth axis for 3D domain transitions.

Usage:
    python scripts/compute_pca_z.py
    python scripts/compute_pca_z.py --input embeddings/local_checkpoint.pkl
    python scripts/compute_pca_z.py --output data/pca_z_coordinates.json

Outputs:
    data/pca_z_coordinates.json — {title: z_value} mapping
    Also patches data/domains/*_questions.json with z values
"""

import json
import os
import sys
import argparse
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "4"


def parse_args():
    parser = argparse.ArgumentParser(description="Compute PCA-3 z-coordinates")
    parser.add_argument(
        "--input",
        type=str,
        default="embeddings/wikipedia_embeddings.pkl",
        help="Path to embedding file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/pca_z_coordinates.json",
        help="Output path for z-coordinate mapping",
    )
    parser.add_argument(
        "--patch-questions",
        action="store_true",
        default=True,
        help="Update question files with z-coordinates (default: True)",
    )
    return parser.parse_args()


def load_embeddings(embedding_path: Path):
    print(f"Loading embeddings from {embedding_path}...")
    with open(embedding_path, "rb") as f:
        data = pickle.load(f)

    embeddings = data["embeddings"]

    if "next_index" in data:
        next_index = data["next_index"]
        print(f"  Checkpoint format: {next_index:,} / {embeddings.shape[0]:,}")
        if next_index < embeddings.shape[0]:
            print(f"  ⚠ Only {next_index:,} embeddings computed — using partial data")
            embeddings = embeddings[:next_index]
    else:
        print(f"  Full embedding format: {embeddings.shape[0]:,} articles")

    print(f"  Shape: {embeddings.shape}, dtype: {embeddings.dtype}")

    nan_mask = np.any(np.isnan(embeddings), axis=1)
    nan_count = int(np.sum(nan_mask))
    nonzero_mask = np.any(embeddings != 0, axis=1) & ~nan_mask
    valid_count = np.sum(nonzero_mask)
    print(f"  Non-zero rows: {int(valid_count):,}")
    if nan_count > 0:
        print(f"  ⚠ NaN rows: {nan_count:,} (will be excluded from PCA)")

    return embeddings, nonzero_mask


def compute_pca_z(embeddings: np.ndarray, n_components: int = 3) -> np.ndarray:
    """Run PCA and return the 3rd component normalized to [0,1]."""
    print(
        f"\nRunning PCA with {n_components} components on {embeddings.shape[0]:,} × {embeddings.shape[1]} matrix..."
    )

    from sklearn.decomposition import PCA

    pca = PCA(n_components=n_components, random_state=42)
    components = pca.fit_transform(embeddings)

    explained = pca.explained_variance_ratio_
    print(
        f"  Explained variance: PC1={explained[0]:.3f}, PC2={explained[1]:.3f}, PC3={explained[2]:.3f}"
    )
    print(f"  Total explained: {sum(explained):.3f}")

    pc3 = components[:, 2]

    pc3_min, pc3_max = pc3.min(), pc3.max()
    z_normalized = (pc3 - pc3_min) / (pc3_max - pc3_min)

    print(f"  PC3 range: [{pc3_min:.4f}, {pc3_max:.4f}]")
    print(f"  Z range: [{z_normalized.min():.4f}, {z_normalized.max():.4f}]")

    return z_normalized


def build_title_z_map(z_values: np.ndarray, articles_path: Path) -> dict:
    """Map article titles to z-coordinates using positional index."""
    print("\nBuilding title-to-z mapping...")

    with open(articles_path, "rb") as f:
        wiki_articles = pickle.load(f)

    z_map = {}
    for i, article in enumerate(wiki_articles):
        if i < len(z_values):
            title = article.get("title", article.get("name", f"article_{i}"))
            z_map[title] = round(float(z_values[i]), 6)

    print(f"  Mapped {len(z_map):,} articles to z-coordinates")
    return z_map


def patch_question_files(z_map: dict, domains_dir: Path):
    """Update z-coordinates in existing question files."""
    print("\nPatching question files with z-coordinates...")

    question_files = sorted(domains_dir.glob("*_questions.json"))

    for qf in question_files:
        with open(qf, "r") as f:
            questions = json.load(f)

        patched = 0
        missing = 0
        for q in questions:
            title = q.get("source_article", "")
            if title in z_map:
                q["z"] = z_map[title]
                patched += 1
            else:
                q["z"] = 0.5
                missing += 1

        with open(qf, "w") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

        status = (
            f"patched {patched}, default {missing}" if missing else f"patched {patched}"
        )
        print(f"  ✓ {qf.name}: {status}/{len(questions)} questions")


def main():
    args = parse_args()

    project_root = Path(__file__).parent.parent
    checkpoint_path = project_root / args.input
    output_path = project_root / args.output
    articles_path = project_root / "wikipedia.pkl"
    domains_dir = project_root / "data" / "domains"

    print("=" * 60)
    print("PCA-3 Z-COORDINATE COMPUTATION")
    print("=" * 60)
    print(f"Started: {datetime.now()}\n")

    if not checkpoint_path.exists():
        print(f"Error: Embedding file not found: {checkpoint_path}")
        print("Run scripts/generate_embeddings_local_full.py first.")
        sys.exit(1)

    embeddings, mask = load_embeddings(checkpoint_path)

    valid_embeddings = embeddings[mask] if not np.all(mask) else embeddings
    z_values_valid = compute_pca_z(valid_embeddings)

    z_all = np.zeros(len(mask))
    z_all[mask] = z_values_valid

    z_map = build_title_z_map(z_all, articles_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(z_map, f)
    print(
        f"\n✓ Saved z-coordinates to {output_path} ({output_path.stat().st_size / 1024:.0f} KB)"
    )

    if args.patch_questions:
        patch_question_files(z_map, domains_dir)

    print(f"\nCompleted: {datetime.now()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
