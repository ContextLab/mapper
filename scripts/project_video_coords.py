#!/usr/bin/env python3
"""
T-V004: Project sliding-window embeddings into the UMAP 2D space.

Loads per-video .npy embedding files, projects them via reducer.transform(),
normalizes using stored bounds, and clips to [0,1]. Outputs per-video JSON
files with arrays of [x, y] coordinate pairs.

Per CL-038: clips out-of-bounds coordinates to [0.0, 1.0] and logs count.
Flags if >10% of windows are clipped.

NOTE: pickle is used for UMAP model and bounds deserialization
(standard ML pipeline format for our own trusted pipeline data).

Input:
    data/videos/.working/embeddings/{video_id}.npy  (N_windows, 768)
    embeddings/umap_reducer.pkl
    embeddings/umap_bounds.pkl

Output:
    data/videos/.working/coordinates/{video_id}.json  (array of [x, y])

Usage:
    python scripts/project_video_coords.py
    python scripts/project_video_coords.py --reducer embeddings/umap_reducer.pkl
    python scripts/project_video_coords.py --bounds embeddings/umap_bounds.pkl
    python scripts/project_video_coords.py --dry-run
    python scripts/project_video_coords.py --force
"""

import argparse
import json
import os
import pickle
import sys
import time
import numpy as np
from datetime import datetime
from pathlib import Path

# macOS threading fix
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDING_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "embeddings"
COORD_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "coordinates"
DEFAULT_REDUCER = PROJECT_ROOT / "embeddings" / "umap_reducer.pkl"
DEFAULT_BOUNDS = PROJECT_ROOT / "embeddings" / "umap_bounds.pkl"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Project video window embeddings into UMAP 2D space"
    )
    parser.add_argument(
        "--reducer", type=str, default=str(DEFAULT_REDUCER),
        help="Path to UMAP reducer pkl file",
    )
    parser.add_argument(
        "--bounds", type=str, default=str(DEFAULT_BOUNDS),
        help="Path to UMAP bounds pkl file",
    )
    parser.add_argument(
        "--embedding-dir", type=str, default=str(EMBEDDING_DIR),
        help="Directory containing per-video .npy files",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(COORD_DIR),
        help="Output directory for per-video .json files",
    )
    parser.add_argument(
        "--batch-size", type=int, default=5000,
        help="Number of windows to project per transform() call",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Count files without projecting",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-project all (ignore existing .json files)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    embedding_dir = Path(args.embedding_dir)
    output_dir = Path(args.output_dir)
    reducer_path = Path(args.reducer)
    bounds_path = Path(args.bounds)

    print("=" * 70)
    print("VIDEO WINDOW UMAP PROJECTION")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print()

    # Validate inputs
    if not embedding_dir.exists():
        print(f"ERROR: Embedding directory not found: {embedding_dir}")
        sys.exit(1)

    npy_files = sorted(embedding_dir.glob("*.npy"))
    if not npy_files:
        print("ERROR: No .npy embedding files found.")
        sys.exit(1)

    # Filter to un-projected videos (unless --force)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.force:
        remaining = list(npy_files)
    else:
        remaining = []
        for nf in npy_files:
            video_id = nf.stem
            coord_path = output_dir / f"{video_id}.json"
            if not coord_path.exists():
                remaining.append(nf)

    already_done = len(npy_files) - len(remaining)
    print(f"Total .npy files: {len(npy_files)}")
    print(f"Already projected: {already_done}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("Nothing to do.")
        return

    if args.dry_run:
        total_windows = sum(np.load(f).shape[0] for f in remaining)
        print(f"\nDRY RUN: Would project {len(remaining)} videos, {total_windows} total windows.")
        return

    # Load reducer and bounds
    if not reducer_path.exists():
        print(f"ERROR: Reducer not found: {reducer_path}")
        sys.exit(1)
    if not bounds_path.exists():
        print(f"ERROR: Bounds not found: {bounds_path}")
        sys.exit(1)

    print(f"\nLoading reducer from {reducer_path}...")
    load_start = time.time()
    with open(reducer_path, "rb") as f:
        reducer_data = pickle.load(f)
    reducer = reducer_data["reducer"]
    print(f"  Loaded in {time.time() - load_start:.1f}s")
    print(f"  Trained on {reducer_data['n_training_samples']} samples")

    with open(bounds_path, "rb") as f:
        bounds = pickle.load(f)
    x_min = bounds["x_min"]
    x_range = bounds["x_range"]
    y_min = bounds["y_min"]
    y_range = bounds["y_range"]
    print(f"  Bounds: x=[{bounds['x_min']:.4f}, {bounds['x_max']:.4f}], "
          f"y=[{bounds['y_min']:.4f}, {bounds['y_max']:.4f}]")

    # Process videos: collect all windows, batch-transform, then split back
    # This is much faster than transforming per-video because transform()
    # has high per-call overhead
    print(f"\nStep 1: Loading {len(remaining)} embedding files...")
    all_embeddings = []
    video_ids = []
    window_counts = []

    for nf in remaining:
        emb = np.load(nf).astype(np.float32)
        if emb.ndim != 2 or emb.shape[1] != 768:
            print(f"  WARNING: Skipping {nf.stem} — unexpected shape {emb.shape}")
            continue
        all_embeddings.append(emb)
        video_ids.append(nf.stem)
        window_counts.append(emb.shape[0])

    if not all_embeddings:
        print("ERROR: No valid embeddings to project.")
        sys.exit(1)

    combined = np.concatenate(all_embeddings, axis=0)
    total_windows = combined.shape[0]
    print(f"  {len(video_ids)} videos, {total_windows} total windows")
    print(f"  Combined shape: {combined.shape}")

    # Step 2: Transform in batches
    print(f"\nStep 2: UMAP transform on {total_windows} windows...")
    transform_start = time.time()

    if total_windows <= args.batch_size:
        coords_2d = reducer.transform(combined)
    else:
        # Process in batches to avoid memory issues
        coords_parts = []
        for i in range(0, total_windows, args.batch_size):
            batch = combined[i : i + args.batch_size]
            coords_batch = reducer.transform(batch)
            coords_parts.append(coords_batch)
            done = min(i + args.batch_size, total_windows)
            print(f"  [{done}/{total_windows}] windows projected")
        coords_2d = np.concatenate(coords_parts, axis=0)

    transform_time = time.time() - transform_start
    print(f"  Transform completed in {transform_time:.1f}s "
          f"({total_windows / transform_time:.0f} windows/sec)")

    # Step 3: Normalize using bounds
    print("\nStep 3: Normalizing coordinates...")
    coords_norm = np.zeros_like(coords_2d)
    coords_norm[:, 0] = (coords_2d[:, 0] - x_min) / x_range
    coords_norm[:, 1] = (coords_2d[:, 1] - y_min) / y_range

    # CL-038: Clip to [0, 1] and log count
    out_of_bounds = np.sum((coords_norm < 0) | (coords_norm > 1))
    total_values = coords_norm.size
    clip_pct = (out_of_bounds / total_values) * 100

    coords_norm = np.clip(coords_norm, 0.0, 1.0)

    print(f"  Out-of-bounds values clipped: {out_of_bounds} / {total_values} ({clip_pct:.2f}%)")
    if clip_pct > 10:
        print(f"  WARNING: >{clip_pct:.1f}% of values were clipped — projection may be suspect!")

    # Step 4: Split back per video and save
    print(f"\nStep 4: Saving {len(video_ids)} coordinate files...")
    offset = 0
    for vid, n_windows in zip(video_ids, window_counts):
        video_coords = coords_norm[offset : offset + n_windows]
        offset += n_windows

        # Save as array of [x, y] pairs (6 decimal places)
        windows_list = [
            [round(float(video_coords[j, 0]), 6), round(float(video_coords[j, 1]), 6)]
            for j in range(n_windows)
        ]

        coord_path = output_dir / f"{vid}.json"
        with open(coord_path, "w") as f:
            json.dump(windows_list, f)

    assert offset == total_windows, f"Split mismatch: {offset} != {total_windows}"

    # Summary
    coord_count = len(list(output_dir.glob("*.json")))

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Videos projected: {len(video_ids)}")
    print(f"  Total windows: {total_windows}")
    print(f"  Avg windows/video: {total_windows / len(video_ids):.1f}")
    print(f"  Transform time: {transform_time:.1f}s")
    print(f"  Clipped values: {out_of_bounds} ({clip_pct:.2f}%)")
    print(f"  Total .json files on disk: {coord_count}")
    print(f"  Finished: {datetime.now()}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
