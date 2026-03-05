#!/usr/bin/env python3
"""
Remove videos flagged for removal by the video audit.

Reads the audit results and removes flagged videos from:
  1. embeddings/transcript_embeddings.pkl
  2. embeddings/umap_transcript_coords.pkl
  3. embeddings/umap_window_coords.pkl
  4. data/videos/catalog.json

NOTE: pickle is used intentionally for numpy array serialization. All .pkl
files are generated locally by our own pipeline scripts (trusted data).

After running this, re-run flatten_coordinates.py to regenerate
the flattened coordinate files.

Usage:
    python scripts/remove_audited_videos.py
    python scripts/remove_audited_videos.py --dry-run
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
AUDIT_RESULTS = PROJECT_ROOT / "data" / "videos" / ".working" / "audit-v2" / "all_results.json"
EMB_DIR = PROJECT_ROOT / "embeddings"
CATALOG_PATH = PROJECT_ROOT / "data" / "videos" / "catalog.json"


def load_removal_set():
    with open(AUDIT_RESULTS) as f:
        results = json.load(f)
    removed = {r["id"] for r in results if r["classification"] != "KEEP"}
    kept = {r["id"] for r in results if r["classification"] == "KEEP"}
    print(f"Audit results: {len(results)} total, {len(kept)} KEEP, {len(removed)} REMOVE")
    return removed


def filter_transcript_embeddings(removal_ids, dry_run):
    path = EMB_DIR / "transcript_embeddings.pkl"
    with open(path, "rb") as f:
        data = pickle.load(f)  # trusted local pipeline data

    video_ids = data["video_ids"]
    n_before = len(video_ids)
    keep_mask = np.array([vid not in removal_ids for vid in video_ids])
    n_removed = n_before - keep_mask.sum()

    print(f"\ntranscript_embeddings.pkl: {n_before} -> {keep_mask.sum()} ({n_removed} removed)")

    if dry_run or n_removed == 0:
        return

    data["embeddings"] = data["embeddings"][keep_mask]
    data["video_ids"] = [v for v, k in zip(video_ids, keep_mask) if k]
    data["transcript_lengths"] = [l for l, k in zip(data["transcript_lengths"], keep_mask) if k]
    data["num_transcripts"] = len(data["video_ids"])

    with open(path, "wb") as f:
        pickle.dump(data, f)  # trusted local pipeline data
    print(f"  Saved: {path}")


def filter_umap_transcript_coords(removal_ids, dry_run):
    path = EMB_DIR / "umap_transcript_coords.pkl"
    with open(path, "rb") as f:
        data = pickle.load(f)  # trusted local pipeline data

    video_ids = data["video_ids"]
    n_before = len(video_ids)
    keep_mask = np.array([vid not in removal_ids for vid in video_ids])
    n_removed = n_before - keep_mask.sum()

    print(f"\numap_transcript_coords.pkl: {n_before} -> {keep_mask.sum()} ({n_removed} removed)")

    if dry_run or n_removed == 0:
        return

    data["coords"] = data["coords"][keep_mask]
    data["coords_raw"] = data["coords_raw"][keep_mask]
    data["video_ids"] = [v for v, k in zip(video_ids, keep_mask) if k]
    data["num_transcripts"] = len(data["video_ids"])

    with open(path, "wb") as f:
        pickle.dump(data, f)  # trusted local pipeline data
    print(f"  Saved: {path}")


def filter_umap_window_coords(removal_ids, dry_run):
    path = EMB_DIR / "umap_window_coords.pkl"
    with open(path, "rb") as f:
        data = pickle.load(f)  # trusted local pipeline data

    video_ids = data["video_ids"]  # per-window video IDs
    n_before = len(video_ids)
    keep_mask = np.array([vid not in removal_ids for vid in video_ids])
    n_removed = n_before - keep_mask.sum()

    print(f"\numap_window_coords.pkl: {n_before} -> {keep_mask.sum()} windows ({n_removed} removed)")

    if dry_run or n_removed == 0:
        return

    data["coords"] = data["coords"][keep_mask]
    data["coords_raw"] = data["coords_raw"][keep_mask]
    data["video_ids"] = [v for v, k in zip(video_ids, keep_mask) if k]
    data["window_indices"] = [idx for idx, k in zip(data["window_indices"], keep_mask) if k]

    # Rebuild window_offsets from the filtered data
    new_offsets = {}
    current_vid = None
    start = 0
    for i, vid in enumerate(data["video_ids"]):
        if vid != current_vid:
            if current_vid is not None:
                new_offsets[current_vid] = (start, i - start)
            current_vid = vid
            start = i
    if current_vid is not None:
        new_offsets[current_vid] = (start, len(data["video_ids"]) - start)
    data["window_offsets"] = new_offsets

    with open(path, "wb") as f:
        pickle.dump(data, f)  # trusted local pipeline data
    print(f"  Saved: {path}")
    print(f"  Window offsets: {len(new_offsets)} videos")


def filter_catalog(removal_ids, dry_run):
    with open(CATALOG_PATH) as f:
        catalog = json.load(f)

    n_before = len(catalog)
    filtered = [v for v in catalog if v["id"] not in removal_ids]
    n_removed = n_before - len(filtered)

    print(f"\ncatalog.json: {n_before} -> {len(filtered)} ({n_removed} removed)")

    if dry_run or n_removed == 0:
        return

    with open(CATALOG_PATH, "w") as f:
        json.dump(filtered, f, separators=(",", ":"))
    print(f"  Saved: {CATALOG_PATH}")


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN ===\n")

    removal_ids = load_removal_set()

    filter_transcript_embeddings(removal_ids, dry_run)
    filter_umap_transcript_coords(removal_ids, dry_run)
    filter_umap_window_coords(removal_ids, dry_run)
    filter_catalog(removal_ids, dry_run)

    if dry_run:
        print("\n[DRY RUN] No files were modified.")
    else:
        print("\nDone! Now re-run: python scripts/flatten_coordinates.py --mu 0.75")


if __name__ == "__main__":
    main()
