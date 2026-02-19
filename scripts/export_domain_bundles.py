#!/usr/bin/env python3
"""
Generate domain bundle JSON files for the frontend from RAG assignments.

For each domain:
  1. Load RAG-assigned curated articles (tagged as relevant)
  2. Load ALL articles that fall within the domain's bounding rectangle
  3. Build article list with: title, url, excerpt, x, y, z, curated flag
  4. Build question list with UMAP-projected coordinates
  5. Generate grid labels from article density
  6. Write bundle JSON file

Input:
  - data/domains/index_v2.json — RAG domain definitions
  - embeddings/domain_assignments.pkl — curated article→domain mapping
  - embeddings/umap_article_coords.pkl — (250K, 2) normalized coords
  - embeddings/umap_question_coords.pkl — (949, 2) normalized coords
  - embeddings/all_questions_for_embedding.json — question metadata
  - wikipedia.pkl — article text (for excerpts)

Output:
  - data/domains/{domain_id}.json — domain bundle for each domain
  - data/domains/index.json — replaced with index_v2 contents

Usage:
    python scripts/export_domain_bundles.py
"""

import json
import os
import sys
import pickle
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"

EXCERPT_MAX_CHARS = 200
MAX_SPATIAL_ARTICLES = 2000  # cap non-curated articles for file size


def make_excerpt(text, max_chars=EXCERPT_MAX_CHARS):
    """Create a clean excerpt from article text."""
    if not text:
        return ""
    # Clean whitespace
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    # Truncate at sentence boundary
    truncated = clean[:max_chars]
    last_period = max(
        truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? ")
    )
    if last_period > max_chars * 0.5:
        return truncated[: last_period + 1]
    # Truncate at word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.7:
        return truncated[:last_space] + "..."
    return truncated + "..."


def generate_labels(article_coords, grid_size, region, article_titles):
    """Generate grid labels based on most common article in each cell.

    Each cell gets a label from the article title closest to its center.
    """
    labels = []
    x_min, x_max = region["x_min"], region["x_max"]
    y_min, y_max = region["y_min"], region["y_max"]
    x_step = (x_max - x_min) / grid_size
    y_step = (y_max - y_min) / grid_size

    for gx in range(grid_size):
        for gy in range(grid_size):
            cx = x_min + (gx + 0.5) * x_step
            cy = y_min + (gy + 0.5) * y_step

            # Count articles in this cell
            cell_mask = (
                (article_coords[:, 0] >= x_min + gx * x_step)
                & (article_coords[:, 0] < x_min + (gx + 1) * x_step)
                & (article_coords[:, 1] >= y_min + gy * y_step)
                & (article_coords[:, 1] < y_min + (gy + 1) * y_step)
            )
            count = int(cell_mask.sum())

            if count > 0:
                # Find article closest to cell center
                cell_indices = np.where(cell_mask)[0]
                cell_coords = article_coords[cell_indices]
                dists = np.sqrt(
                    (cell_coords[:, 0] - cx) ** 2 + (cell_coords[:, 1] - cy) ** 2
                )
                nearest_idx = cell_indices[dists.argmin()]
                label = article_titles[nearest_idx]
            else:
                label = ""

            labels.append(
                {
                    "gx": gx,
                    "gy": gy,
                    "center_x": round(float(cx), 6),
                    "center_y": round(float(cy), 6),
                    "label": label,
                    "article_count": count,
                }
            )

    return labels


def main():
    print("=" * 70)
    print("DOMAIN BUNDLE EXPORT")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print()

    # ── Load data ──
    print("Loading data...")

    # Domain index v2
    with open(DOMAINS_DIR / "index_v2.json") as f:
        index_v2 = json.load(f)
    domains = index_v2["domains"]
    print(f"  Domains: {len(domains)}")

    # Domain assignments
    with open(EMBEDDINGS_DIR / "domain_assignments.pkl", "rb") as f:
        assignments_data = pickle.load(f)
    assignments = assignments_data["assignments"]  # domain_id → list of article indices
    print(f"  Domain assignments loaded")

    # UMAP article coordinates
    with open(EMBEDDINGS_DIR / "umap_article_coords.pkl", "rb") as f:
        article_coord_data = pickle.load(f)
    article_coords = article_coord_data["coords"]  # (250K, 2)
    print(f"  Article coords: {article_coords.shape}")

    # UMAP question coordinates
    with open(EMBEDDINGS_DIR / "umap_question_coords.pkl", "rb") as f:
        question_coord_data = pickle.load(f)
    question_coords = question_coord_data["coords"]  # (949, 2)
    question_ids_umap = question_coord_data["question_ids"]
    print(f"  Question coords: {question_coords.shape}")

    # Question metadata
    with open(EMBEDDINGS_DIR / "all_questions_for_embedding.json") as f:
        all_questions = json.load(f)
    questions_by_id = {q["id"]: q for q in all_questions}
    qid_to_umap_idx = {qid: i for i, qid in enumerate(question_ids_umap)}
    print(f"  Questions: {len(all_questions)}")

    # Wikipedia articles (for titles, urls, excerpts)
    print("  Loading wikipedia.pkl...")
    with open(PROJECT_ROOT / "wikipedia.pkl", "rb") as f:
        articles = pickle.load(f)
    print(f"  Articles: {len(articles):,}")
    print()

    # ── Process each domain ──
    for domain in domains:
        domain_id = domain["id"]
        region = domain["region"]
        grid_size = domain["grid_size"]

        print(f"\n[{domain_id}] grid={grid_size}, region={region}")

        # Get curated article indices from RAG assignment
        curated_indices = set(assignments.get(domain_id, []))

        # Get ALL articles within the bounding rectangle (for visualization density)
        in_region_mask = (
            (article_coords[:, 0] >= region["x_min"])
            & (article_coords[:, 0] <= region["x_max"])
            & (article_coords[:, 1] >= region["y_min"])
            & (article_coords[:, 1] <= region["y_max"])
        )
        region_indices = set(np.where(in_region_mask)[0].tolist())

        # Sample non-curated region articles to keep file sizes manageable
        spatial_only = sorted(region_indices - curated_indices)
        if len(spatial_only) > MAX_SPATIAL_ARTICLES:
            rng = np.random.default_rng(42)
            spatial_only = sorted(
                rng.choice(spatial_only, MAX_SPATIAL_ARTICLES, replace=False).tolist()
            )
        all_article_indices = sorted(set(spatial_only) | curated_indices)

        print(
            f"  Curated: {len(curated_indices)}, "
            f"In region: {len(region_indices)}, "
            f"Spatial sample: {len(spatial_only)}, "
            f"Total: {len(all_article_indices)}"
        )

        # Build article list
        article_list = []
        article_coords_for_labels = []
        article_titles_for_labels = []

        for idx in all_article_indices:
            article = articles[idx]
            x, y = float(article_coords[idx, 0]), float(article_coords[idx, 1])

            article_list.append(
                {
                    "title": article.get("title", "Untitled"),
                    "url": article.get("url", ""),
                    "excerpt": make_excerpt(article.get("text", "")),
                    "x": round(x, 6),
                    "y": round(y, 6),
                    "z": 0.0,  # will be computed later if PCA-3 needed
                    "curated": idx in curated_indices,
                }
            )
            article_coords_for_labels.append([x, y])
            article_titles_for_labels.append(article.get("title", "Untitled"))

        article_coords_np = np.array(article_coords_for_labels)

        # Build question list
        question_list = []
        for q in all_questions:
            # Check if this question belongs to this domain
            q_domain_ids = q.get("domain_ids", [])
            if domain_id not in q_domain_ids:
                # For general domains, also include child domain questions
                if domain.get("level") == "general":
                    children = [
                        d["id"] for d in domains if d.get("parent_id") == domain_id
                    ]
                    if not any(cid in q_domain_ids for cid in children):
                        continue
                elif domain.get("level") == "all" or domain_id == "all":
                    pass  # "all" includes everything
                else:
                    continue

            # Get UMAP coordinates
            if q["id"] not in qid_to_umap_idx:
                continue
            umap_idx = qid_to_umap_idx[q["id"]]
            qx, qy = (
                float(question_coords[umap_idx, 0]),
                float(question_coords[umap_idx, 1]),
            )

            question_list.append(
                {
                    "id": q["id"],
                    "question_text": q["question_text"],
                    "options": q["options"],
                    "correct_answer": q["correct_answer"],
                    "difficulty": q.get("difficulty", 3),
                    "x": round(qx, 6),
                    "y": round(qy, 6),
                    "z": 0.0,
                    "source_article": q.get("source_article", ""),
                    "domain_ids": q_domain_ids,
                    "concepts_tested": q.get("concepts_tested", []),
                }
            )

        print(f"  Questions: {len(question_list)}")

        # Generate labels
        labels = generate_labels(
            article_coords_np, grid_size, region, article_titles_for_labels
        )
        non_empty_labels = sum(1 for l in labels if l["label"])
        print(f"  Labels: {len(labels)} cells ({non_empty_labels} non-empty)")

        # Build bundle
        bundle = {
            "domain": {
                "id": domain_id,
                "name": domain["name"],
                "parent_id": domain.get("parent_id"),
                "level": domain.get("level"),
                "region": region,
                "grid_size": grid_size,
            },
            "questions": question_list,
            "labels": labels,
            "articles": article_list,
        }

        # Save
        output_path = DOMAINS_DIR / f"{domain_id}.json"
        with open(output_path, "w") as f:
            json.dump(bundle, f, indent=2, ensure_ascii=False)

        file_size = output_path.stat().st_size / 1024
        print(f"  Saved: {output_path} ({file_size:.0f} KB)")

    # ── Replace index.json with v2 ──
    print("\nUpdating index.json...")
    index_path = DOMAINS_DIR / "index.json"

    # Backup old index
    backup_path = DOMAINS_DIR / "index_v1_backup.json"
    if index_path.exists():
        with open(index_path) as f:
            old = json.load(f)
        with open(backup_path, "w") as f:
            json.dump(old, f, indent=2)
        print(f"  Backed up old index to {backup_path}")

    with open(index_path, "w") as f:
        json.dump(index_v2, f, indent=2)
    print(f"  ✓ Updated {index_path}")

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print("✓ DOMAIN BUNDLE EXPORT COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Bundles: {len(domains)}")
    total_articles = sum(
        len(json.load(open(DOMAINS_DIR / f"{d['id']}.json"))["articles"])
        for d in domains
    )
    print(
        f"  Total article entries: {total_articles:,} (articles appear in multiple domains)"
    )
    print(f"  Finished: {datetime.now()}")
    print()
    print("Next: Run scripts/verify_coordinates.py to verify coordinate integrity")


if __name__ == "__main__":
    main()
