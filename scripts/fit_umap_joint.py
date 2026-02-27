#!/usr/bin/env python3
"""
Fit UMAP jointly on articles + questions + transcripts.

Trains a single UMAP reducer on the concatenated embedding matrix from all
three document types, producing a unified 2D space. Coordinates are normalized
to [0, 1] range. The trained reducer is saved for later use with
reducer.transform() (e.g., for video sliding-window embeddings).

NOTE: pickle is used for numpy array and UMAP model serialization
(standard ML pipeline format for our own trusted pipeline data).

Input:
    embeddings/wikipedia_embeddings.pkl     (250000, 768)
    embeddings/question_embeddings_2500.pkl (2500, 768)
    embeddings/transcript_embeddings.pkl    (N, 768)

Output:
    embeddings/umap_reducer.pkl             - trained UMAP model
    embeddings/umap_bounds.pkl              - coordinate bounds for normalization
    embeddings/article_coords.pkl           - (250000, 2) normalized coords
    embeddings/question_coords.pkl          - (2500, 2) normalized coords
    embeddings/transcript_coords.pkl        - (N, 2) normalized coords

Usage:
    python scripts/fit_umap_joint.py
    python scripts/fit_umap_joint.py --skip-transcripts
    python scripts/fit_umap_joint.py --n-neighbors 15 --min-dist 0.1
    python scripts/fit_umap_joint.py --dry-run
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
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"


def parse_args():
    parser = argparse.ArgumentParser(description="Fit joint UMAP on all embeddings")
    parser.add_argument(
        "--n-neighbors", type=int, default=15, help="UMAP n_neighbors (default: 15)"
    )
    parser.add_argument(
        "--min-dist", type=float, default=0.1, help="UMAP min_dist (default: 0.1)"
    )
    parser.add_argument(
        "--random-state", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--skip-transcripts",
        action="store_true",
        help="Fit on articles + questions only (skip transcripts)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Load and validate without fitting"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: embeddings/)",
    )
    return parser.parse_args()


def load_embeddings(path, name):
    """Load a pickle file containing embeddings and validate."""
    if not path.exists():
        print(f"  ERROR: {name} not found at {path}")
        return None

    with open(path, "rb") as f:
        data = pickle.load(f)

    emb = data["embeddings"]
    print(f"  {name}: shape={emb.shape}, dtype={emb.dtype}")

    # Validate
    assert emb.ndim == 2, f"{name}: expected 2D array, got {emb.ndim}D"
    assert emb.shape[1] == 768, f"{name}: expected dim 768, got {emb.shape[1]}"
    assert not np.any(np.isnan(emb)), f"{name}: contains NaN values"
    assert not np.any(np.isinf(emb)), f"{name}: contains Inf values"

    return data


def main():
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else EMBEDDINGS_DIR

    print("=" * 70)
    print("JOINT UMAP FITTING")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"UMAP params: n_neighbors={args.n_neighbors}, min_dist={args.min_dist}, "
          f"random_state={args.random_state}")
    print(f"Skip transcripts: {args.skip_transcripts}")
    print()

    # Step 1: Load all embeddings
    print("Step 1: Loading embeddings...")

    article_data = load_embeddings(
        EMBEDDINGS_DIR / "wikipedia_embeddings.pkl", "Articles"
    )
    if article_data is None:
        sys.exit(1)

    question_data = load_embeddings(
        EMBEDDINGS_DIR / "question_embeddings_2500.pkl", "Questions"
    )
    if question_data is None:
        sys.exit(1)

    transcript_data = None
    if not args.skip_transcripts:
        transcript_data = load_embeddings(
            EMBEDDINGS_DIR / "transcript_embeddings.pkl", "Transcripts"
        )
        if transcript_data is None:
            print("  WARNING: Transcript embeddings not found. Use --skip-transcripts to proceed without them.")
            sys.exit(1)

    # Step 2: Concatenate
    print("\nStep 2: Concatenating embeddings...")
    parts = [article_data["embeddings"], question_data["embeddings"]]
    labels = ["articles", "questions"]
    counts = [article_data["embeddings"].shape[0], question_data["embeddings"].shape[0]]

    if transcript_data is not None:
        parts.append(transcript_data["embeddings"])
        labels.append("transcripts")
        counts.append(transcript_data["embeddings"].shape[0])

    combined = np.concatenate(parts, axis=0).astype(np.float32)
    print(f"  Combined shape: {combined.shape}")
    print(f"  Breakdown: {dict(zip(labels, counts))}")
    print(f"  Total: {combined.shape[0]} documents")

    # Verify no NaN/Inf in combined
    assert not np.any(np.isnan(combined)), "Combined matrix contains NaN"
    assert not np.any(np.isinf(combined)), "Combined matrix contains Inf"

    if args.dry_run:
        print(f"\n  DRY RUN: Would fit UMAP on {combined.shape[0]} documents. Exiting.")
        return

    # Step 3: Fit UMAP
    print(f"\nStep 3: Fitting UMAP on {combined.shape[0]} documents...")
    import umap

    fit_start = time.time()
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        metric="cosine",
        random_state=args.random_state,
        verbose=True,
    )
    coords_2d = reducer.fit_transform(combined)
    fit_time = time.time() - fit_start
    print(f"  UMAP fit in {fit_time:.1f}s")
    print(f"  Output shape: {coords_2d.shape}")

    # Step 4: Normalize to [0, 1]
    print("\nStep 4: Normalizing coordinates to [0, 1]...")
    x_min, x_max = coords_2d[:, 0].min(), coords_2d[:, 0].max()
    y_min, y_max = coords_2d[:, 1].min(), coords_2d[:, 1].max()

    x_range = x_max - x_min
    y_range = y_max - y_min

    # Avoid division by zero
    if x_range < 1e-10 or y_range < 1e-10:
        print("  ERROR: UMAP produced degenerate coordinates (zero range)")
        sys.exit(1)

    coords_norm = np.zeros_like(coords_2d)
    coords_norm[:, 0] = (coords_2d[:, 0] - x_min) / x_range
    coords_norm[:, 1] = (coords_2d[:, 1] - y_min) / y_range

    print(f"  Raw bounds: x=[{x_min:.4f}, {x_max:.4f}], y=[{y_min:.4f}, {y_max:.4f}]")
    print(f"  Normalized bounds: x=[{coords_norm[:, 0].min():.4f}, {coords_norm[:, 0].max():.4f}], "
          f"y=[{coords_norm[:, 1].min():.4f}, {coords_norm[:, 1].max():.4f}]")

    # Step 5: Split back into per-type coordinates
    print("\nStep 5: Splitting coordinates by document type...")
    offset = 0
    coord_splits = {}
    for label, count in zip(labels, counts):
        coord_splits[label] = coords_norm[offset : offset + count]
        print(f"  {label}: {coord_splits[label].shape}")
        offset += count

    assert offset == coords_norm.shape[0], (
        f"Split mismatch: offset={offset}, total={coords_norm.shape[0]}"
    )

    # Step 6: Save outputs
    print("\nStep 6: Saving outputs...")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat()

    # Save reducer
    reducer_path = output_dir / "umap_reducer.pkl"
    with open(reducer_path, "wb") as f:
        pickle.dump({
            "reducer": reducer,
            "n_neighbors": args.n_neighbors,
            "min_dist": args.min_dist,
            "random_state": args.random_state,
            "metric": "cosine",
            "n_components": 2,
            "n_training_samples": combined.shape[0],
            "training_labels": labels,
            "training_counts": counts,
            "timestamp": timestamp,
        }, f)
    print(f"  Saved reducer: {reducer_path} ({reducer_path.stat().st_size / 1024:.1f} KB)")

    # Save bounds (for normalizing future transform() outputs)
    bounds_path = output_dir / "umap_bounds.pkl"
    bounds = {
        "x_min": float(x_min),
        "x_max": float(x_max),
        "y_min": float(y_min),
        "y_max": float(y_max),
        "x_range": float(x_range),
        "y_range": float(y_range),
        "timestamp": timestamp,
    }
    with open(bounds_path, "wb") as f:
        pickle.dump(bounds, f)
    print(f"  Saved bounds: {bounds_path}")

    # Save per-type coordinates
    for label in labels:
        coords = coord_splits[label]
        checksum = hashlib.sha256(coords.tobytes()).hexdigest()
        coord_path = output_dir / f"{label.rstrip('s')}_coords.pkl"
        with open(coord_path, "wb") as f:
            pickle.dump({
                "coords": coords,
                "checksum": checksum,
                "n_points": coords.shape[0],
                "timestamp": timestamp,
            }, f)
        print(f"  Saved {label} coords: {coord_path} "
              f"({coords.shape[0]} points, {coord_path.stat().st_size / 1024:.1f} KB)")

    # Step 7: Summary statistics
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total documents: {combined.shape[0]}")
    for label, count in zip(labels, counts):
        print(f"    {label}: {count}")
    print(f"  UMAP fit time: {fit_time:.1f}s")
    print(f"  Coordinate range: [0, 1] x [0, 1]")
    print(f"  Output files:")
    print(f"    {reducer_path}")
    print(f"    {bounds_path}")
    for label in labels:
        print(f"    {output_dir / f'{label.rstrip(chr(115))}_coords.pkl'}")
    print(f"\n  Finished: {datetime.now()}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
