#!/usr/bin/env python3
"""
Warp UMAP coordinates and update the demo in a single step.

Reads ORIGINAL coordinates (never modified), applies density flattening
with the given mu parameter, writes warped coords to the main coord files,
and re-exports domain bundles so the frontend reflects the change immediately.

Re-runnable: call with different mu values to iterate quickly.
  mu=0    → original (unwarped) coordinates
  mu=0.75 → moderate flattening
  mu=1.0  → fully flattened to uniform target

Usage:
  python scripts/warp_demo.py --mu 0.75
  python scripts/warp_demo.py --mu 0.9 --subsample 5000

The Vite dev server picks up bundle changes automatically.
"""

import argparse
import pickle
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"

ORIGINAL_ARTICLE_PATH = EMBEDDINGS_DIR / "umap_article_coords_orig.pkl"
ORIGINAL_QUESTION_PATH = EMBEDDINGS_DIR / "umap_question_coords_orig.pkl"

ACTIVE_ARTICLE_PATH = EMBEDDINGS_DIR / "umap_article_coords.pkl"
ACTIVE_QUESTION_PATH = EMBEDDINGS_DIR / "umap_question_coords.pkl"


def ensure_originals_exist():
    """Verify original coordinate files exist. These are the source of truth."""
    for path, label in [
        (ORIGINAL_ARTICLE_PATH, "article"),
        (ORIGINAL_QUESTION_PATH, "question"),
    ]:
        if not path.exists():
            print(f"ERROR: Original {label} coords not found at {path}")
            print("These should have been created by rebuild_umap_v2.py")
            sys.exit(1)

    # Sanity check: originals should NOT have coords_original key (that's a flat file)
    with open(ORIGINAL_ARTICLE_PATH, "rb") as f:
        data = pickle.load(f)
    if "coords_original" in data:
        print(
            f"ERROR: {ORIGINAL_ARTICLE_PATH} appears to be a flattened file, not the original!"
        )
        print("The _orig.pkl files must contain the unwarped UMAP output.")
        sys.exit(1)


def load_originals():
    with open(ORIGINAL_ARTICLE_PATH, "rb") as f:
        article_data = pickle.load(f)
    with open(ORIGINAL_QUESTION_PATH, "rb") as f:
        question_data = pickle.load(f)
    return article_data, question_data


def write_active_coords(
    article_data, flat_articles, question_data, flat_questions, params
):
    """Write warped coordinates to the active coord files read by the pipeline."""
    active_article = {
        "coords": flat_articles,
        "coords_original": article_data["coords"],
        "titles": article_data["titles"],
        "num_articles": article_data["num_articles"],
        "timestamp": datetime.now().isoformat(),
        "flatten_params": params,
    }
    with open(ACTIVE_ARTICLE_PATH, "wb") as f:
        pickle.dump(active_article, f)

    active_question = {
        "coords": flat_questions,
        "coords_original": question_data["coords"],
        "question_ids": question_data["question_ids"],
        "num_questions": question_data["num_questions"],
        "timestamp": datetime.now().isoformat(),
        "flatten_params": params,
    }
    with open(ACTIVE_QUESTION_PATH, "wb") as f:
        pickle.dump(active_question, f)


def export_domain_bundles():
    """Re-export domain bundles by calling the existing script."""
    print("\n--- Re-exporting domain bundles ---")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "export_domain_bundles.py")],
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print("ERROR: Domain bundle export failed!")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Warp coordinates and update demo in one step"
    )
    parser.add_argument(
        "--mu",
        type=float,
        required=True,
        help="Mixing parameter: 0=original, 1=fully flat",
    )
    parser.add_argument(
        "--method",
        choices=["patched", "subsample"],
        default="patched",
        help="Flattening method: patched (per-cluster Hungarian) or subsample (default: patched)",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=100,
        help="Number of K-means clusters for patched method (default: 100)",
    )
    parser.add_argument(
        "--subsample",
        type=int,
        default=5000,
        help="Subsample size for subsample method (default: 5000)",
    )
    parser.add_argument(
        "--knn",
        type=int,
        default=8,
        help="k-NN neighbors for interpolation (default: 8)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.02,
        help="Edge margin for target placement (default: 0.02)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--skip-bundles",
        action="store_true",
        help="Skip domain bundle re-export (coords only)",
    )
    args = parser.parse_args()

    print(f"{'=' * 70}")
    print(f"WARP DEMO — mu={args.mu}, method={args.method}")
    print(f"{'=' * 70}")
    t_start = time.time()

    ensure_originals_exist()
    article_data, question_data = load_originals()

    article_coords = article_data["coords"]
    question_coords = question_data["coords"]
    print(f"  Original articles: {article_coords.shape}")
    print(f"  Original questions: {question_coords.shape}")

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from flatten_coordinates import compute_density_stats, print_density_comparison

    if args.mu == 0:
        print("\n  mu=0 → restoring original coordinates (no warping)")
        flat_articles = article_coords.copy()
        flat_questions = question_coords.copy()
        params = {"mu": 0, "method": "identity"}
    elif args.method == "patched":
        from flatten_coordinates import flatten_coordinates_patched

        stats_before = compute_density_stats(article_coords)
        print(
            f"\n  BEFORE: {stats_before['empty_pct']:.1f}% empty, "
            f"top-10% has {stats_before['articles_in_top10pct_frac']:.1%} of articles"
        )

        flat_articles, flat_questions, params = flatten_coordinates_patched(
            article_coords=article_coords,
            question_coords=question_coords,
            mu=args.mu,
            n_clusters=args.clusters,
            knn_k=args.knn,
            margin=args.margin,
            seed=args.seed,
        )

        stats_after = compute_density_stats(flat_articles)
        print_density_comparison(stats_before, stats_after)
    else:
        from flatten_coordinates import flatten_coordinates

        stats_before = compute_density_stats(article_coords)
        print(
            f"\n  BEFORE: {stats_before['empty_pct']:.1f}% empty, "
            f"top-10% has {stats_before['articles_in_top10pct_frac']:.1%} of articles"
        )

        flat_articles, flat_questions, params = flatten_coordinates(
            article_coords=article_coords,
            question_coords=question_coords,
            mu=args.mu,
            subsample_m=args.subsample,
            knn_k=args.knn,
            margin=args.margin,
            seed=args.seed,
        )

        stats_after = compute_density_stats(flat_articles)
        print_density_comparison(stats_before, stats_after)

    write_active_coords(
        article_data, flat_articles, question_data, flat_questions, params
    )
    print(
        f"\n  Active coords updated ({ACTIVE_ARTICLE_PATH.name}, {ACTIVE_QUESTION_PATH.name})"
    )
    print(
        f"  Originals untouched ({ORIGINAL_ARTICLE_PATH.name}, {ORIGINAL_QUESTION_PATH.name})"
    )

    if not args.skip_bundles:
        export_domain_bundles()

    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"DONE — mu={args.mu}, {elapsed:.0f}s total")
    print(f"{'=' * 70}")
    print(f"  Demo updated. Refresh browser to see changes.")
    print(
        f"  Re-run:  python scripts/warp_demo.py --mu <value> [--method patched|subsample]"
    )
    print(f"  Restore: python scripts/warp_demo.py --mu 0")


if __name__ == "__main__":
    main()
