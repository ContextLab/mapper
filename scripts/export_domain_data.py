#!/usr/bin/env python3
"""
Export per-domain JSON bundles for the frontend.

Reads domain definitions, generated questions, heatmap labels, and articles,
then produces data/domains/{domain_id}.json files matching the domain-data contract.

Usage:
    python scripts/export_domain_data.py
    python scripts/export_domain_data.py --domain physics

Output: data/domains/{domain_id}.json for each domain
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

os.environ["TOKENIZERS_PARALLELISM"] = "false"


def parse_args():
    parser = argparse.ArgumentParser(description="Export per-domain JSON bundles")
    parser.add_argument(
        "--domain", type=str, default=None, help="Export only a specific domain (by ID)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing bundle files"
    )
    return parser.parse_args()


def load_json(path: Path, description: str) -> Any:
    """Load and return JSON file contents."""
    print(f"Loading {description} from {path}...")
    with open(path, "r") as f:
        data = json.load(f)
    return data


def get_articles_in_region(
    articles: List[Dict], region: Dict[str, float]
) -> List[Dict]:
    """Filter articles within a domain's region."""
    x_min, x_max = region["x_min"], region["x_max"]
    y_min, y_max = region["y_min"], region["y_max"]
    return [
        a for a in articles if x_min <= a["x"] <= x_max and y_min <= a["y"] <= y_max
    ]


def get_labels_in_region(
    labels_data: Dict, region: Dict[str, float], grid_size: int
) -> List[Dict]:
    """
    Extract heatmap cell labels that fall within a domain's region.
    Maps global cell coordinates to the domain's local grid.
    """
    cells = labels_data.get("cells", [])
    if not cells:
        return []

    global_grid = labels_data.get("metadata", {}).get("grid_size", 39)
    cell_width = 1.0 / global_grid
    cell_height = 1.0 / global_grid

    region_labels = []
    for cell in cells:
        gx, gy = cell["gx"], cell["gy"]
        center_x = (gx + 0.5) * cell_width
        center_y = (gy + 0.5) * cell_height

        if (
            region["x_min"] <= center_x <= region["x_max"]
            and region["y_min"] <= center_y <= region["y_max"]
        ):
            region_labels.append(
                {
                    "gx": gx,
                    "gy": gy,
                    "center_x": round(center_x, 6),
                    "center_y": round(center_y, 6),
                    "label": cell.get("label", "Unexplored"),
                    "article_count": len(cell.get("articles_in_cell", [])),
                }
            )

    return region_labels


def build_domain_bundle(
    domain: Dict[str, Any],
    questions: List[Dict[str, Any]],
    articles: List[Dict[str, Any]],
    labels: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build a complete domain bundle matching the contract schema."""
    question_ids = [q["id"] for q in questions]

    domain_info = {
        "id": domain["id"],
        "name": domain["name"],
        "parent_id": domain.get("parent_id"),
        "level": domain["level"],
        "region": domain["region"],
        "grid_size": domain["grid_size"],
        "question_ids": question_ids,
    }

    formatted_articles = []
    for a in articles:
        formatted_articles.append(
            {
                "title": a["title"],
                "url": a.get("url", ""),
                "x": a["x"],
                "y": a["y"],
                "z": a.get("z", 0.0),
            }
        )

    return {
        "domain": domain_info,
        "questions": questions,
        "labels": labels,
        "articles": formatted_articles,
    }


def export_domain(
    domain: Dict[str, Any],
    all_articles: List[Dict],
    labels_data: Dict,
    output_dir: Path,
    force: bool = False,
) -> Optional[str]:
    """Export a single domain bundle. Returns domain_id on success."""
    domain_id = domain["id"]
    bundle_path = output_dir / f"{domain_id}.json"
    questions_path = output_dir / f"{domain_id}_questions.json"

    if bundle_path.exists() and not force:
        print(f"  ⏭ {domain_id}: bundle exists (use --force)")
        return domain_id

    # Load questions
    if not questions_path.exists():
        print(f"  ✗ {domain_id}: no questions file at {questions_path}")
        return None

    with open(questions_path, "r") as f:
        questions = json.load(f)

    if not questions:
        print(f"  ✗ {domain_id}: empty questions file")
        return None

    # Get articles and labels in region
    region = domain["region"]
    region_articles = get_articles_in_region(all_articles, region)
    region_labels = get_labels_in_region(labels_data, region, domain["grid_size"])

    # Build bundle
    bundle = build_domain_bundle(domain, questions, region_articles, region_labels)

    # Write bundle
    with open(bundle_path, "w") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    size_kb = bundle_path.stat().st_size / 1024
    print(
        f"  ✓ {domain_id}: {len(questions)} questions, "
        f"{len(region_articles)} articles, "
        f"{len(region_labels)} labels ({size_kb:.0f} KB)"
    )

    return domain_id


def main():
    args = parse_args()

    project_root = Path(__file__).parent.parent
    domains_path = project_root / "data" / "domains" / "index.json"
    articles_path = project_root / "wikipedia_articles.json"
    labels_path = project_root / "heatmap_cell_labels.json"
    output_dir = project_root / "data" / "domains"

    print("=" * 60)
    print("DOMAIN DATA EXPORT")
    print("=" * 60)
    print()

    # Load shared data
    domains_data = load_json(domains_path, "domain definitions")
    domains = domains_data["domains"]
    articles = load_json(articles_path, "Wikipedia articles")
    labels_data = load_json(labels_path, "heatmap labels")

    if args.domain:
        domains = [d for d in domains if d["id"] == args.domain]
        if not domains:
            print(f"Error: Domain '{args.domain}' not found")
            sys.exit(1)

    print(f"\nExporting {len(domains)} domain bundles to {output_dir}/\n")

    exported = []
    failed = []

    for domain in domains:
        result = export_domain(
            domain, articles, labels_data, output_dir, force=args.force
        )
        if result:
            exported.append(result)
        else:
            failed.append(domain["id"])

    print(f"\n{'=' * 60}")
    print(f"Exported: {len(exported)}/{len(domains)} domains")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print(f"{'=' * 60}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
