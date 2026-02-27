#!/usr/bin/env python3
"""
Compute hierarchical bounding boxes for each domain based on question positions.

Bounding Box Hierarchy:
  - Sub-domains: bounding box around that area's questions only
  - Broad domains: bounding box around that domain's questions AND its sub-domains' questions
  - "All (general)": full [0, 1] x [0, 1] view (encloses all articles + questions)

This script reads flattened question coordinates and domain assignments,
then computes appropriate bounding boxes for each domain level.

Input:
  - embeddings/umap_question_coords_flat.pkl (flattened question coordinates)
  - data/domains/index.json (domain hierarchy)
  - data/domains/{domain_id}.json (questions with domain_ids)

Output:
  - Updates data/domains/index.json with computed bounding boxes
  - Outputs embeddings/domain_bounding_boxes.json for reference

Usage:
    python scripts/compute_bounding_boxes.py
    python scripts/compute_bounding_boxes.py --margin 0.02
"""

import argparse
import json
import pickle
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"


def load_question_coordinates():
    """Load flattened question coordinates and IDs."""
    # Try flattened coords first, fall back to non-flattened
    flat_path = EMBEDDINGS_DIR / "umap_question_coords_flat.pkl"
    regular_path = EMBEDDINGS_DIR / "umap_question_coords.pkl"

    if flat_path.exists():
        with open(flat_path, "rb") as f:
            data = pickle.load(f)
        print(f"Loaded flattened question coords from {flat_path.name}")
    elif regular_path.exists():
        with open(regular_path, "rb") as f:
            data = pickle.load(f)
        print(f"Loaded question coords from {regular_path.name} (not flattened)")
    else:
        print("ERROR: No question coordinates found.")
        print(f"  Tried: {flat_path}")
        print(f"  Tried: {regular_path}")
        print("  Run rebuild_umap_v2.py and flatten_coordinates.py first.")
        sys.exit(1)

    coords = data["coords"]
    question_ids = data["question_ids"]
    print(f"  {len(question_ids)} questions with coordinates")

    return coords, question_ids


def load_domain_hierarchy():
    """Load domain hierarchy from index.json."""
    index_path = DOMAINS_DIR / "index.json"
    with open(index_path) as f:
        data = json.load(f)

    domains = {d["id"]: d for d in data["domains"]}
    print(f"Loaded {len(domains)} domains from index.json")
    return domains, data


def load_question_domain_assignments():
    """Load which questions belong to which domains from domain JSON files."""
    question_to_domains = {}

    for domain_file in DOMAINS_DIR.glob("*.json"):
        if domain_file.name == "index.json":
            continue

        try:
            with open(domain_file) as f:
                data = json.load(f)

            if "questions" not in data:
                continue

            for q in data["questions"]:
                qid = q.get("id")
                if not qid:
                    continue

                domain_ids = q.get("domain_ids", [])
                if qid not in question_to_domains:
                    question_to_domains[qid] = set()
                question_to_domains[qid].update(domain_ids)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Warning: Could not parse {domain_file.name}: {e}")
            continue

    print(f"Found domain assignments for {len(question_to_domains)} questions")
    return question_to_domains


def compute_bounding_box(coords: np.ndarray, margin: float = 0.02) -> dict:
    """
    Compute bounding box for a set of coordinates.

    Args:
        coords: (N, 2) array of x, y coordinates
        margin: margin to add around the bounding box (as fraction of range)

    Returns:
        dict with x_min, x_max, y_min, y_max
    """
    if len(coords) == 0:
        return None

    x_min, y_min = coords.min(axis=0)
    x_max, y_max = coords.max(axis=0)

    # Add margin
    x_range = x_max - x_min
    y_range = y_max - y_min

    # Ensure minimum size for very small clusters
    min_size = 0.05
    if x_range < min_size:
        center_x = (x_min + x_max) / 2
        x_min = center_x - min_size / 2
        x_max = center_x + min_size / 2
        x_range = min_size
    if y_range < min_size:
        center_y = (y_min + y_max) / 2
        y_min = center_y - min_size / 2
        y_max = center_y + min_size / 2
        y_range = min_size

    # Apply margin
    x_min = max(0.0, x_min - x_range * margin)
    x_max = min(1.0, x_max + x_range * margin)
    y_min = max(0.0, y_min - y_range * margin)
    y_max = min(1.0, y_max + y_range * margin)

    return {
        "x_min": round(float(x_min), 6),
        "x_max": round(float(x_max), 6),
        "y_min": round(float(y_min), 6),
        "y_max": round(float(y_max), 6),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compute hierarchical bounding boxes from question positions"
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.02,
        help="Margin around bounding boxes (default: 0.02)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results without updating files",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("HIERARCHICAL BOUNDING BOX COMPUTATION")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Margin: {args.margin}")
    print()

    # Load data
    coords, question_ids = load_question_coordinates()
    domains, index_data = load_domain_hierarchy()
    question_to_domains = load_question_domain_assignments()

    # Build coordinate lookup by question ID
    id_to_coord = {qid: coords[i] for i, qid in enumerate(question_ids)}

    # Identify domain hierarchy
    sub_domains = {d["id"]: d for d in domains.values() if d.get("level") == "sub"}
    general_domains = {d["id"]: d for d in domains.values() if d.get("level") == "general"}
    all_domain = next((d for d in domains.values() if d.get("level") == "all"), None)

    # Map parent domains to their sub-domains
    parent_to_children = {}
    for sub_id, sub_info in sub_domains.items():
        parent_id = sub_info.get("parent_id")
        if parent_id:
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(sub_id)

    print(f"\nDomain hierarchy:")
    print(f"  Sub-domains: {len(sub_domains)}")
    print(f"  General domains: {len(general_domains)}")
    print(f"  All domain: {'yes' if all_domain else 'no'}")
    print()

    # Compute bounding boxes
    bounding_boxes = {}

    # Step 1: Sub-domains - bbox around that area's questions only
    print("Computing sub-domain bounding boxes...")
    for domain_id in sub_domains:
        # Find questions that belong to this domain
        domain_coords = []
        for qid, qdomains in question_to_domains.items():
            if domain_id in qdomains and qid in id_to_coord:
                domain_coords.append(id_to_coord[qid])

        if domain_coords:
            bbox = compute_bounding_box(np.array(domain_coords), args.margin)
            bounding_boxes[domain_id] = bbox
            print(f"  {domain_id}: {len(domain_coords)} questions -> "
                  f"[{bbox['x_min']:.3f}, {bbox['x_max']:.3f}] x [{bbox['y_min']:.3f}, {bbox['y_max']:.3f}]")
        else:
            print(f"  {domain_id}: NO QUESTIONS FOUND - using existing region")
            # Fall back to existing region if no questions
            if domain_id in domains and "region" in domains[domain_id]:
                bounding_boxes[domain_id] = domains[domain_id]["region"].copy()

    # Step 2: General domains - bbox around domain's questions + sub-domains' questions
    print("\nComputing general domain bounding boxes...")
    for domain_id in general_domains:
        # Collect all questions from this domain AND its sub-domains
        domain_coords = []

        # Questions directly assigned to this general domain
        for qid, qdomains in question_to_domains.items():
            if domain_id in qdomains and qid in id_to_coord:
                domain_coords.append(id_to_coord[qid])

        # Questions from sub-domains
        child_ids = parent_to_children.get(domain_id, [])
        for child_id in child_ids:
            for qid, qdomains in question_to_domains.items():
                if child_id in qdomains and qid in id_to_coord:
                    coord = id_to_coord[qid]
                    # Avoid duplicates
                    if not any(np.allclose(coord, c) for c in domain_coords):
                        domain_coords.append(coord)

        if domain_coords:
            bbox = compute_bounding_box(np.array(domain_coords), args.margin)
            bounding_boxes[domain_id] = bbox
            print(f"  {domain_id}: {len(domain_coords)} questions (incl. {len(child_ids)} sub-domains) -> "
                  f"[{bbox['x_min']:.3f}, {bbox['x_max']:.3f}] x [{bbox['y_min']:.3f}, {bbox['y_max']:.3f}]")
        else:
            print(f"  {domain_id}: NO QUESTIONS FOUND - using existing region")
            if domain_id in domains and "region" in domains[domain_id]:
                bounding_boxes[domain_id] = domains[domain_id]["region"].copy()

    # Step 3: "All" domain - full [0, 1] view
    print("\nSetting 'all' domain bounding box...")
    if all_domain:
        bounding_boxes["all"] = {
            "x_min": 0.0,
            "x_max": 1.0,
            "y_min": 0.0,
            "y_max": 1.0,
        }
        print(f"  all: full view [0, 1] x [0, 1]")

    # Output results
    print(f"\n{'=' * 70}")
    print(f"RESULTS: {len(bounding_boxes)} bounding boxes computed")
    print(f"{'=' * 70}")

    if args.dry_run:
        print("\n--dry-run mode: not updating files")
        print("\nBounding boxes:")
        for domain_id, bbox in sorted(bounding_boxes.items()):
            print(f"  {domain_id}: {bbox}")
        return

    # Update index.json with new bounding boxes
    print("\nUpdating data/domains/index.json...")
    for domain in index_data["domains"]:
        domain_id = domain["id"]
        if domain_id in bounding_boxes:
            domain["region"] = bounding_boxes[domain_id]

    index_data["bounding_boxes_computed"] = datetime.now().isoformat()
    index_data["bounding_box_params"] = {"margin": args.margin}

    index_path = DOMAINS_DIR / "index.json"
    with open(index_path, "w") as f:
        json.dump(index_data, f, indent=2)
    print(f"  Updated {index_path}")

    # Save bounding boxes as separate reference file
    bbox_output = {
        "bounding_boxes": bounding_boxes,
        "computed": datetime.now().isoformat(),
        "params": {"margin": args.margin},
        "source": "compute_bounding_boxes.py",
    }
    bbox_path = EMBEDDINGS_DIR / "domain_bounding_boxes.json"
    with open(bbox_path, "w") as f:
        json.dump(bbox_output, f, indent=2)
    print(f"  Saved reference to {bbox_path}")

    print(f"\nDone! Finished: {datetime.now()}")
    print("\nNext: Run scripts/export_domain_bundles.py to update domain JSON files")


if __name__ == "__main__":
    main()
