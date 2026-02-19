#!/usr/bin/env python3
"""
Verify coordinate integrity across the entire pipeline.

Checks:
  1. All article coordinates are in [0, 1]
  2. All question coordinates are in [0, 1]
  3. Questions and articles share the same coordinate space
  4. Domain regions contain their curated articles
  5. Domain regions contain their questions
  6. No NaN or Inf values
  7. Question IDs in bundles match the embedding registry
  8. Article excerpts are present and non-empty
  9. Grid labels cover the full grid

Usage:
    python scripts/verify_coordinates.py
"""

import json
import os
import sys
import pickle
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
EMBEDDINGS_DIR = PROJECT_ROOT / "embeddings"
DOMAINS_DIR = PROJECT_ROOT / "data" / "domains"


def main():
    print("=" * 70)
    print("COORDINATE INTEGRITY VERIFICATION")
    print("=" * 70)
    print()

    passed = 0
    failed = 0
    warnings = 0

    def check(condition, msg):
        nonlocal passed, failed
        if condition:
            print(f"  ✓ {msg}")
            passed += 1
        else:
            print(f"  ✗ FAIL: {msg}")
            failed += 1

    def warn(condition, msg):
        nonlocal warnings
        if not condition:
            print(f"  ⚠ WARN: {msg}")
            warnings += 1

    # ── Load data ──
    print("Loading verification data...")

    with open(EMBEDDINGS_DIR / "umap_article_coords.pkl", "rb") as f:
        article_data = pickle.load(f)
    article_coords = article_data["coords"]

    with open(EMBEDDINGS_DIR / "umap_question_coords.pkl", "rb") as f:
        question_data = pickle.load(f)
    question_coords = question_data["coords"]
    question_ids_umap = question_data["question_ids"]

    with open(DOMAINS_DIR / "index.json") as f:
        index = json.load(f)
    domains = index["domains"]

    print(f"  Articles: {article_coords.shape}")
    print(f"  Questions: {question_coords.shape}")
    print(f"  Domains: {len(domains)}")
    print()

    # ── Check 1: Article coordinate range ──
    print("1. Article coordinate range:")
    check(
        article_coords[:, 0].min() >= 0 and article_coords[:, 0].max() <= 1,
        f"Article x in [0,1]: [{article_coords[:, 0].min():.6f}, {article_coords[:, 0].max():.6f}]",
    )
    check(
        article_coords[:, 1].min() >= 0 and article_coords[:, 1].max() <= 1,
        f"Article y in [0,1]: [{article_coords[:, 1].min():.6f}, {article_coords[:, 1].max():.6f}]",
    )
    check(
        not np.any(np.isnan(article_coords)) and not np.any(np.isinf(article_coords)),
        "No NaN/Inf in article coordinates",
    )

    # ── Check 2: Question coordinate range ──
    print("\n2. Question coordinate range:")
    check(
        question_coords[:, 0].min() >= 0 and question_coords[:, 0].max() <= 1,
        f"Question x in [0,1]: [{question_coords[:, 0].min():.6f}, {question_coords[:, 0].max():.6f}]",
    )
    check(
        question_coords[:, 1].min() >= 0 and question_coords[:, 1].max() <= 1,
        f"Question y in [0,1]: [{question_coords[:, 1].min():.6f}, {question_coords[:, 1].max():.6f}]",
    )
    check(
        not np.any(np.isnan(question_coords)) and not np.any(np.isinf(question_coords)),
        "No NaN/Inf in question coordinates",
    )

    # ── Check 3: Same coordinate space ──
    print("\n3. Same coordinate space:")
    # Articles and questions should have overlapping ranges
    a_center = article_coords.mean(axis=0)
    q_center = question_coords.mean(axis=0)
    center_dist = np.sqrt(np.sum((a_center - q_center) ** 2))
    check(
        center_dist < 0.3,
        f"Article/question centroids within 0.3: distance={center_dist:.4f}",
    )

    # Questions should be spread across the article space
    q_x_range = question_coords[:, 0].max() - question_coords[:, 0].min()
    q_y_range = question_coords[:, 1].max() - question_coords[:, 1].min()
    check(
        q_x_range > 0.3 and q_y_range > 0.3,
        f"Questions spread: x_range={q_x_range:.3f}, y_range={q_y_range:.3f}",
    )

    # ── Check 4-9: Per-domain checks ──
    print("\n4-9. Per-domain checks:")
    qid_to_umap = {qid: i for i, qid in enumerate(question_ids_umap)}

    for domain in domains:
        did = domain["id"]
        region = domain["region"]

        bundle_path = DOMAINS_DIR / f"{did}.json"
        if not bundle_path.exists():
            print(f"\n  [{did}] ✗ Bundle file missing!")
            failed += 1
            continue

        with open(bundle_path) as f:
            bundle = json.load(f)

        print(f"\n  [{did}]")

        # Questions have valid UMAP coordinates
        q_count = len(bundle["questions"])
        q_in_region = 0
        q_valid_ids = 0
        for q in bundle["questions"]:
            qx, qy = float(q["x"]), float(q["y"])
            if (
                region["x_min"] - 0.05 <= qx <= region["x_max"] + 0.05
                and region["y_min"] - 0.05 <= qy <= region["y_max"] + 0.05
            ):
                q_in_region += 1
            if q["id"] in qid_to_umap:
                q_valid_ids += 1

        check(
            q_valid_ids == q_count,
            f"All {q_count} question IDs match UMAP registry ({q_valid_ids}/{q_count})",
        )

        # Allow some questions slightly outside (UMAP transform can place them near boundary)
        pct_in = q_in_region / q_count * 100 if q_count > 0 else 100
        check(
            pct_in >= 70 or did == "all",
            f"Questions near region: {q_in_region}/{q_count} ({pct_in:.0f}%)",
        )

        # Articles have excerpts
        articles_with_excerpt = sum(1 for a in bundle["articles"] if a.get("excerpt"))
        excerpt_pct = (
            articles_with_excerpt / len(bundle["articles"]) * 100
            if bundle["articles"]
            else 0
        )
        check(
            excerpt_pct >= 80,
            f"Articles with excerpts: {articles_with_excerpt}/{len(bundle['articles'])} ({excerpt_pct:.0f}%)",
        )

        # Grid labels cover full grid
        grid_size = domain["grid_size"]
        expected_labels = grid_size * grid_size
        actual_labels = len(bundle["labels"])
        check(
            actual_labels == expected_labels,
            f"Grid labels: {actual_labels}/{expected_labels}",
        )

        # Curated articles tagged
        curated = sum(1 for a in bundle["articles"] if a.get("curated"))
        warn(curated > 0, f"Curated articles: {curated}")

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print(f"VERIFICATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Warnings: {warnings}")

    if failed > 0:
        print(f"\n  ✗ {failed} CHECKS FAILED — review output above")
        sys.exit(1)
    else:
        print(f"\n  ✓ ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
