#!/usr/bin/env python3
"""
Export UMAP coordinates back into domain JSON files.

Updates each domain JSON file with:
  - x, y coordinates for each question (from question_coords.pkl)
  - x, y coordinates for each article (from article_coords.pkl)
  - Recomputed domain region bounds from all points

NOTE: pickle is used for numpy array deserialization of our own trusted
pipeline data.

Input:
    embeddings/question_coords.pkl
    embeddings/article_coords.pkl
    embeddings/question_embeddings_2500.pkl  (for question_id -> index mapping)
    embeddings/wikipedia_embeddings.pkl      (for title -> index mapping)
    data/domains/index.json
    data/domains/{domain_id}.json

Output:
    data/domains/{domain_id}.json  (updated in place)

Usage:
    python scripts/export_coords_to_domains.py
    python scripts/export_coords_to_domains.py --dry-run
    python scripts/export_coords_to_domains.py --questions-only
    python scripts/export_coords_to_domains.py --articles-only
"""

import argparse
import json
import pickle
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"

REGION_PADDING = 0.005  # small padding around domain bounds (legacy, used as fallback)

# Percentile-based bounding box parameters (prevents outlier-driven over-zoom)
BBOX_PERCENTILE_LO = 5    # 5th percentile
BBOX_PERCENTILE_HI = 95   # 95th percentile
BBOX_MIN_SPAN = 0.15      # minimum span in each axis
BBOX_MARGIN = 0.05        # margin around percentile bounds


def parse_args():
    parser = argparse.ArgumentParser(description="Export UMAP coords to domain JSONs")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change without writing"
    )
    parser.add_argument(
        "--questions-only", action="store_true", help="Only update question coordinates"
    )
    parser.add_argument(
        "--articles-only", action="store_true", help="Only update article coordinates"
    )
    parser.add_argument(
        "--update-index", action="store_true", default=True,
        help="Also update bounding boxes in index.json (default: True)"
    )
    parser.add_argument(
        "--no-update-index", action="store_false", dest="update_index",
        help="Skip updating index.json bounding boxes"
    )
    return parser.parse_args()


def load_question_coord_map():
    """Build question_id -> (x, y) mapping."""
    # Load question embeddings for ID list
    qe_path = EMBEDDINGS_DIR / "question_embeddings_2500.pkl"
    with open(qe_path, "rb") as f:
        qe_data = pickle.load(f)

    # Load question coordinates (prefer flattened, fall back to UMAP raw)
    qc_path = EMBEDDINGS_DIR / "question_coords_flat.pkl"
    if not qc_path.exists():
        qc_path = EMBEDDINGS_DIR / "umap_question_coords.pkl"
    with open(qc_path, "rb") as f:
        qc_data = pickle.load(f)  # trusted local pipeline data

    coords = qc_data["coords"]
    question_ids = qe_data["question_ids"]

    assert len(question_ids) == coords.shape[0], (
        f"Question ID count {len(question_ids)} != coord count {coords.shape[0]}"
    )

    return {
        qid: (float(coords[i, 0]), float(coords[i, 1]))
        for i, qid in enumerate(question_ids)
    }


def load_article_coord_map():
    """Build article_title -> (x, y) mapping."""
    # Load article embeddings for title list
    ae_path = EMBEDDINGS_DIR / "wikipedia_embeddings.pkl"
    with open(ae_path, "rb") as f:
        ae_data = pickle.load(f)

    # Load article coordinates (prefer flattened, fall back to UMAP raw)
    ac_path = EMBEDDINGS_DIR / "article_coords_flat.pkl"
    if not ac_path.exists():
        ac_path = EMBEDDINGS_DIR / "umap_article_coords.pkl"
    with open(ac_path, "rb") as f:
        ac_data = pickle.load(f)  # trusted local pipeline data

    coords = ac_data["coords"]
    titles = ae_data["titles"]

    assert len(titles) == coords.shape[0], (
        f"Title count {len(titles)} != coord count {coords.shape[0]}"
    )

    return {
        title: (float(coords[i, 0]), float(coords[i, 1]))
        for i, title in enumerate(titles)
    }


def compute_region_bounds(points):
    """Compute percentile-based bounding box from a list of (x, y) tuples.

    Uses 5th-95th percentile with minimum span and margin to prevent
    outlier articles from causing domains to be over-zoomed. Falls back
    to simple min/max + padding when fewer than 5 points are available.
    """
    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    if len(points) < 5:
        # Too few points for percentile — use simple min/max
        return {
            "x_min": round(min(xs) - REGION_PADDING, 6),
            "x_max": round(max(xs) + REGION_PADDING, 6),
            "y_min": round(min(ys) - REGION_PADDING, 6),
            "y_max": round(max(ys) + REGION_PADDING, 6),
        }

    import numpy as np
    xs_arr = np.array(xs)
    ys_arr = np.array(ys)

    x_lo = float(np.percentile(xs_arr, BBOX_PERCENTILE_LO))
    x_hi = float(np.percentile(xs_arr, BBOX_PERCENTILE_HI))
    y_lo = float(np.percentile(ys_arr, BBOX_PERCENTILE_LO))
    y_hi = float(np.percentile(ys_arr, BBOX_PERCENTILE_HI))

    # Enforce minimum span
    x_span = x_hi - x_lo
    if x_span < BBOX_MIN_SPAN:
        x_mid = (x_lo + x_hi) / 2
        x_lo = x_mid - BBOX_MIN_SPAN / 2
        x_hi = x_mid + BBOX_MIN_SPAN / 2

    y_span = y_hi - y_lo
    if y_span < BBOX_MIN_SPAN:
        y_mid = (y_lo + y_hi) / 2
        y_lo = y_mid - BBOX_MIN_SPAN / 2
        y_hi = y_mid + BBOX_MIN_SPAN / 2

    # Add margin
    x_lo -= BBOX_MARGIN
    x_hi += BBOX_MARGIN
    y_lo -= BBOX_MARGIN
    y_hi += BBOX_MARGIN

    # Clamp to [0, 1]
    x_lo = max(0.0, x_lo)
    x_hi = min(1.0, x_hi)
    y_lo = max(0.0, y_lo)
    y_hi = min(1.0, y_hi)

    return {
        "x_min": round(x_lo, 6),
        "x_max": round(x_hi, 6),
        "y_min": round(y_lo, 6),
        "y_max": round(y_hi, 6),
    }


def main():
    args = parse_args()
    update_questions = not args.articles_only
    update_articles = not args.questions_only

    print("=" * 70)
    print("EXPORT UMAP COORDINATES TO DOMAIN FILES")
    print("=" * 70)
    print(f"  Update questions: {update_questions}")
    print(f"  Update articles: {update_articles}")
    print(f"  Dry run: {args.dry_run}")
    print()

    # Load coordinate maps
    question_map = {}
    article_map = {}

    if update_questions:
        print("Loading question coordinates...")
        question_map = load_question_coord_map()
        print(f"  {len(question_map)} question coordinates loaded")

    if update_articles:
        print("Loading article coordinates...")
        article_map = load_article_coord_map()
        print(f"  {len(article_map)} article coordinates loaded")

    # Load domain index
    index_path = DOMAINS_DIR / "index.json"
    with open(index_path) as f:
        index = json.load(f)

    domain_ids = [d["id"] for d in index["domains"]]
    print(f"\n{len(domain_ids)} domains to process")

    # Process each domain
    total_questions_updated = 0
    total_articles_updated = 0
    total_articles_missing = 0
    domains_updated = 0

    for domain_id in sorted(domain_ids):
        domain_path = DOMAINS_DIR / f"{domain_id}.json"
        if not domain_path.exists():
            print(f"  WARNING: {domain_path} not found, skipping")
            continue

        with open(domain_path) as f:
            bundle = json.load(f)

        changed = False
        all_points = []  # for region bounds computation

        # Update question coordinates
        if update_questions and "questions" in bundle:
            for q in bundle["questions"]:
                qid = q["id"]
                if qid in question_map:
                    x, y = question_map[qid]
                    if q.get("x") != x or q.get("y") != y:
                        q["x"] = round(x, 6)
                        q["y"] = round(y, 6)
                        changed = True
                        total_questions_updated += 1
                    all_points.append((x, y))

        # Update article coordinates
        if update_articles and "articles" in bundle:
            for a in bundle["articles"]:
                title = a["title"]
                if title in article_map:
                    x, y = article_map[title]
                    if a.get("x") != x or a.get("y") != y:
                        a["x"] = round(x, 6)
                        a["y"] = round(y, 6)
                        changed = True
                        total_articles_updated += 1
                    all_points.append((x, y))
                else:
                    total_articles_missing += 1

        # Recompute region bounds
        if all_points and "domain" in bundle:
            new_region = compute_region_bounds(all_points)
            if new_region and bundle["domain"].get("region") != new_region:
                bundle["domain"]["region"] = new_region
                changed = True

        if changed:
            domains_updated += 1
            if not args.dry_run:
                with open(domain_path, "w") as f:
                    json.dump(bundle, f, indent=2, ensure_ascii=False)
                    f.write("\n")

        status = "UPDATED" if changed else "no change"
        n_q = len(bundle.get("questions", []))
        n_a = len(bundle.get("articles", []))
        print(f"  {domain_id}: {n_q}q + {n_a}a -> {status}")

    # Update index.json bounding boxes
    if args.update_index and not args.dry_run:
        print("\nUpdating index.json bounding boxes...")
        update_index_bounding_boxes()

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Domains processed: {len(domain_ids)}")
    print(f"  Domains updated: {domains_updated}")
    print(f"  Questions updated: {total_questions_updated}")
    print(f"  Articles updated: {total_articles_updated}")
    if total_articles_missing:
        print(f"  Articles with no coords (not in embedding set): {total_articles_missing}")
    if args.dry_run:
        print("\n  DRY RUN -- no files were modified")
    print(f"{'=' * 70}")


def update_index_bounding_boxes():
    """Recompute percentile-based bounding boxes in index.json from domain question coordinates.

    Uses question coordinates (not articles) as the primary source for domain
    regions, since questions define the interactive area where users engage.
    Falls back to article coordinates for the 'all' domain.
    """
    index_path = DOMAINS_DIR / "index.json"
    with open(index_path) as f:
        index = json.load(f)

    updated = 0
    for entry in index["domains"]:
        domain_id = entry["id"]
        domain_path = DOMAINS_DIR / f"{domain_id}.json"
        if not domain_path.exists():
            continue

        with open(domain_path) as f:
            bundle = json.load(f)

        # Collect question coordinates as primary source
        q_points = []
        for q in bundle.get("questions", []):
            if "x" in q and "y" in q:
                q_points.append((q["x"], q["y"]))

        # For 'all' domain or domains with very few questions, include articles
        a_points = []
        if domain_id == "all" or len(q_points) < 5:
            for a in bundle.get("articles", []):
                if "x" in a and "y" in a:
                    a_points.append((a["x"], a["y"]))

        points = q_points if q_points else a_points
        if not points:
            continue

        new_region = compute_region_bounds(points)
        if new_region:
            old_region = entry.get("region", {})
            if old_region != new_region:
                entry["region"] = new_region
                updated += 1

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"  Updated {updated}/{len(index['domains'])} domain bounding boxes in index.json")


def run_export():
    """Programmatic entry point for calling from other scripts (e.g. flatten_coordinates.py).

    Runs the full export with default settings (update questions, articles, and index).
    """
    print("\n" + "=" * 70)
    print("AUTO-EXPORTING COORDINATES TO DOMAIN JSON FILES")
    print("=" * 70)

    question_map = load_question_coord_map()
    print(f"  {len(question_map)} question coordinates loaded")

    article_map = load_article_coord_map()
    print(f"  {len(article_map)} article coordinates loaded")

    index_path = DOMAINS_DIR / "index.json"
    with open(index_path) as f:
        index = json.load(f)

    domain_ids = [d["id"] for d in index["domains"]]
    total_q = 0
    total_a = 0

    for domain_id in sorted(domain_ids):
        domain_path = DOMAINS_DIR / f"{domain_id}.json"
        if not domain_path.exists():
            continue

        with open(domain_path) as f:
            bundle = json.load(f)

        all_points = []

        if "questions" in bundle:
            for q in bundle["questions"]:
                if q["id"] in question_map:
                    x, y = question_map[q["id"]]
                    q["x"] = round(x, 6)
                    q["y"] = round(y, 6)
                    total_q += 1
                    all_points.append((x, y))

        if "articles" in bundle:
            for a in bundle["articles"]:
                if a["title"] in article_map:
                    x, y = article_map[a["title"]]
                    a["x"] = round(x, 6)
                    a["y"] = round(y, 6)
                    total_a += 1
                    all_points.append((x, y))

        if all_points and "domain" in bundle:
            new_region = compute_region_bounds(all_points)
            if new_region:
                bundle["domain"]["region"] = new_region

        with open(domain_path, "w") as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)
            f.write("\n")

    update_index_bounding_boxes()

    print(f"  Questions updated: {total_q}")
    print(f"  Articles updated: {total_a}")
    print(f"  Domains processed: {len(domain_ids)}")


if __name__ == "__main__":
    main()
