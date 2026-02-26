#!/usr/bin/env python3
"""
Export a single video catalog JSON file.

Merges per-video coordinate files with Khan Academy metadata into a single
data/videos/catalog.json consumed by the frontend video-loader.js.

Each video entry: { id, title, duration_s, thumbnail_url, windows }
where windows is an array of [x, y] coordinate pairs from UMAP projection.

No domain assignment is needed — the recommendation engine scores videos
spatially using their window coordinates against the GP estimator grid.

Input:
    data/videos/.working/coordinates/{video_id}.json  (array of [x, y])
    data/videos/.working/khan_metadata.json           (video metadata)

Output:
    data/videos/catalog.json  (single file with all videos)

Usage:
    python scripts/export_video_catalog.py
    python scripts/export_video_catalog.py --dry-run
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
COORD_DIR = PROJECT_ROOT / "data" / "videos" / ".working" / "coordinates"
METADATA_PATH = PROJECT_ROOT / "data" / "videos" / ".working" / "khan_metadata.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "videos" / "catalog.json"

THUMBNAIL_TEMPLATE = "https://i.ytimg.com/vi/{id}/mqdefault.jpg"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export video catalog JSON file"
    )
    parser.add_argument(
        "--coord-dir", type=str, default=str(COORD_DIR),
        help="Directory containing per-video coordinate .json files",
    )
    parser.add_argument(
        "--metadata", type=str, default=str(METADATA_PATH),
        help="Path to khan_metadata.json",
    )
    parser.add_argument(
        "--output", type=str, default=str(OUTPUT_PATH),
        help="Output path for catalog JSON",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute catalog without writing file",
    )
    return parser.parse_args()


def load_metadata(metadata_path):
    """Load video metadata. Returns dict: video_id → metadata."""
    with open(metadata_path) as f:
        data = json.load(f)

    if isinstance(data, list):
        videos = data
    elif isinstance(data, dict) and "videos" in data:
        videos = data["videos"]
    else:
        videos = list(data.values()) if isinstance(data, dict) else data

    meta = {}
    for v in videos:
        vid = v.get("id") or v.get("video_id") or v.get("videoId")
        if vid:
            meta[vid] = v
    return meta


def parse_duration(raw):
    """Parse duration from various formats to integer seconds."""
    if not raw:
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        parts = raw.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        else:
            try:
                return int(raw)
            except ValueError:
                return 0
    return 0


def main():
    args = parse_args()
    coord_dir = Path(args.coord_dir)
    metadata_path = Path(args.metadata)
    output_path = Path(args.output)

    print("=" * 70)
    print("VIDEO CATALOG EXPORT")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print()

    if not coord_dir.exists():
        print(f"ERROR: Coordinate directory not found: {coord_dir}")
        sys.exit(1)
    if not metadata_path.exists():
        print(f"ERROR: Metadata file not found: {metadata_path}")
        sys.exit(1)

    # Load metadata
    print("Step 1: Loading video metadata...")
    metadata = load_metadata(metadata_path)
    print(f"  {len(metadata)} videos in metadata")

    # Load coordinate files
    print("\nStep 2: Loading video coordinates...")
    coord_files = sorted(coord_dir.glob("*.json"))
    if not coord_files:
        print("ERROR: No coordinate .json files found.")
        sys.exit(1)
    print(f"  {len(coord_files)} coordinate files")

    # Build catalog
    print("\nStep 3: Building catalog...")
    catalog = []
    seen_ids = set()
    no_metadata = 0
    total_windows = 0

    for cf in coord_files:
        video_id = cf.stem

        if video_id in seen_ids:
            print(f"  WARNING: Duplicate video ID {video_id}, skipping")
            continue
        seen_ids.add(video_id)

        with open(cf) as f:
            windows = json.load(f)

        meta = metadata.get(video_id)
        if not meta:
            no_metadata += 1
            continue

        duration = parse_duration(
            meta.get("duration_s") or meta.get("duration") or meta.get("lengthSeconds")
        )

        catalog.append({
            "id": video_id,
            "title": meta.get("title", ""),
            "duration_s": duration,
            "thumbnail_url": THUMBNAIL_TEMPLATE.format(id=video_id),
            "windows": windows,
        })
        total_windows += len(windows)

    print(f"  Videos with coordinates: {len(coord_files)}")
    print(f"  Videos with metadata: {len(coord_files) - no_metadata}")
    print(f"  Videos missing metadata: {no_metadata}")
    print(f"  Total windows: {total_windows}")
    print(f"  Avg windows/video: {total_windows / max(len(catalog), 1):.1f}")

    # Sort by title for deterministic output
    catalog.sort(key=lambda v: v["title"])

    if args.dry_run:
        print(f"\nDRY RUN — would write {len(catalog)} videos to {output_path}")
        est_size = sum(len(json.dumps(v)) for v in catalog[:10]) / 10 * len(catalog)
        print(f"  Estimated size: {est_size / 1024 / 1024:.1f} MB")
        return

    # Write catalog
    print(f"\nStep 4: Writing catalog...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(catalog, f)

    file_size = output_path.stat().st_size
    print(f"  Output: {output_path}")
    print(f"  Size: {file_size / 1024 / 1024:.1f} MB")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Videos: {len(catalog)}")
    print(f"  Windows: {total_windows}")
    print(f"  File: {output_path} ({file_size / 1024:.0f} KB)")
    print(f"  Finished: {datetime.now()}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
