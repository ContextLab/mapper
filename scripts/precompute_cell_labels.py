#!/usr/bin/env python3
"""Precompute cell labels for the 50x50 global grid.

For each cell center, finds the nearest question and stores its
concepts_tested and source_article. Output is loaded by the frontend
for O(1) tooltip lookups.
"""

import json
import math
import re
import sys
from pathlib import Path

GRID_SIZE = 50
REGION = {"x_min": 0.0, "x_max": 1.0, "y_min": 0.0, "y_max": 1.0}


def clean_concept(raw: str) -> str:
    return re.sub(r"^Concept\s+\d+:\s*", "", raw, flags=re.IGNORECASE).strip()


def main():
    root = Path(__file__).parent.parent

    all_questions = {}
    domains_dir = root / "data" / "domains"
    for bundle_path in sorted(domains_dir.glob("*.json")):
        if bundle_path.name.startswith("index") or "_" in bundle_path.name:
            continue
        with open(bundle_path) as f:
            bundle = json.load(f)
        if not isinstance(bundle, dict) or "questions" not in bundle:
            continue
        for q in bundle["questions"]:
            if q["id"] not in all_questions and q.get("x") is not None:
                all_questions[q["id"]] = q

    questions = list(all_questions.values())
    print(
        f"Loaded {len(questions)} unique questions from {len(list(domains_dir.glob('*.json'))) - 1} domains"
    )

    x_span = REGION["x_max"] - REGION["x_min"]
    y_span = REGION["y_max"] - REGION["y_min"]
    cell_w = x_span / GRID_SIZE
    cell_h = y_span / GRID_SIZE

    labels = []
    for gy in range(GRID_SIZE):
        for gx in range(GRID_SIZE):
            cx = REGION["x_min"] + (gx + 0.5) * cell_w
            cy = REGION["y_min"] + (gy + 0.5) * cell_h

            best_q = None
            best_dist = float("inf")
            for q in questions:
                dx = q["x"] - cx
                dy = q["y"] - cy
                d = math.sqrt(dx * dx + dy * dy)
                if d < best_dist:
                    best_dist = d
                    best_q = q

            if best_q is None:
                labels.append(
                    {"gx": gx, "gy": gy, "concepts": [], "source_article": None}
                )
                continue

            concepts = [
                clean_concept(c)
                for c in best_q.get("concepts_tested", [])
                if clean_concept(c)
            ]

            labels.append(
                {
                    "gx": gx,
                    "gy": gy,
                    "concepts": concepts,
                    "source_article": best_q.get("source_article"),
                }
            )

    out_path = root / "data" / "cell_labels.json"
    with open(out_path, "w") as f:
        json.dump(
            {
                "grid_size": GRID_SIZE,
                "region": REGION,
                "labels": labels,
            },
            f,
            separators=(",", ":"),
        )

    size_kb = out_path.stat().st_size / 1024
    print(f"Wrote {len(labels)} cell labels to {out_path} ({size_kb:.1f} KB)")

    with_concepts = sum(1 for l in labels if l["concepts"])
    unique_articles = len(
        set(l["source_article"] for l in labels if l["source_article"])
    )
    print(f"Cells with concepts: {with_concepts}/{len(labels)}")
    print(f"Unique source articles referenced: {unique_articles}")


if __name__ == "__main__":
    main()
