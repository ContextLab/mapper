#!/usr/bin/env python3
"""
Define 19 domain regions in embedding space.

Since Wikipedia articles in UMAP space don't form clean topic clusters (they're
organized by text similarity, not academic domain), we assign domain regions as
non-overlapping tiles that subdivide the embedding space. Each domain gets a
region containing ~1000-3000 articles. Questions are generated about the domain
topic, placed at articles within the region that are relevant.

The hierarchy:
  All (General)            — full [0,1]x[0,1]
  ├─ Physics               — general
  │  ├─ Astrophysics       — sub
  │  └─ Quantum Physics    — sub
  ├─ Art History            — general
  │  ├─ European Art History — sub
  │  └─ Chinese Art History  — sub
  ├─ Biology                — general
  │  ├─ Molecular and Cell Biology — sub
  │  └─ Genetics            — sub
  ├─ Neuroscience           — general
  │  ├─ Cognitive Neuroscience  — sub
  │  ├─ Computational Neuroscience — sub
  │  └─ Neurobiology        — sub
  └─ Mathematics            — general
     ├─ Calculus             — sub
     ├─ Linear Algebra       — sub
     ├─ Number Theory        — sub
     └─ Probability and Statistics — sub

Usage:
    python scripts/define_domains.py
"""

import json
import sys
import argparse
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def load_articles():
    path = PROJECT_ROOT / "wikipedia_articles.json"
    with open(path) as f:
        articles = json.load(f)
    print(f"Loaded {len(articles):,} articles")
    return articles


def count_articles_in_region(articles, region):
    return sum(
        1
        for a in articles
        if region["x_min"] <= a["x"] <= region["x_max"]
        and region["y_min"] <= a["y"] <= region["y_max"]
    )


def compute_grid_size(region, base_grid=39):
    w = region["x_max"] - region["x_min"]
    h = region["y_max"] - region["y_min"]
    area = max(0.01, w * h)
    return max(8, min(base_grid, int(np.sqrt(area) * base_grid)))


def make_region(x_min, x_max, y_min, y_max):
    return {
        "x_min": round(x_min, 4),
        "x_max": round(x_max, 4),
        "y_min": round(y_min, 4),
        "y_max": round(y_max, 4),
    }


def define_all_domains(articles):
    """
    Define 19 domain regions by tiling the UMAP space.

    Layout (general domains — non-overlapping):

      y=1.0 +-------+-------+-------+
            |       | Neuro |       |
            |Physics| sci.  | Math  |
            | 0-0.4 |0.4-0.6| 0.6-1 |
            |       |       |       |
      y=0.5 +-------+-------+-------+
            |   Art History  |       |
            |    0-0.5       | Bio   |
            |                | 0.5-1 |
      y=0.0 +----------------+-------+
           x=0             x=0.5     x=1.0
    """

    general_regions = {
        "physics": make_region(0.0, 0.40, 0.50, 1.0),
        "neuroscience": make_region(0.40, 0.60, 0.50, 1.0),
        "mathematics": make_region(0.60, 1.0, 0.50, 1.0),
        "art-history": make_region(0.0, 0.50, 0.0, 0.50),
        "biology": make_region(0.50, 1.0, 0.0, 0.50),
    }

    sub_regions = {
        # Physics subs (horizontal split)
        "astrophysics": make_region(0.0, 0.40, 0.75, 1.0),
        "quantum-physics": make_region(0.0, 0.40, 0.50, 0.75),
        # Art History subs (vertical split)
        "european-art-history": make_region(0.0, 0.25, 0.0, 0.50),
        "chinese-art-history": make_region(0.25, 0.50, 0.0, 0.50),
        # Biology subs (vertical split)
        "molecular-cell-biology": make_region(0.50, 0.75, 0.0, 0.50),
        "genetics": make_region(0.75, 1.0, 0.0, 0.50),
        # Neuroscience subs (horizontal split into 3)
        "cognitive-neuroscience": make_region(0.40, 0.60, 0.833, 1.0),
        "computational-neuroscience": make_region(0.40, 0.60, 0.667, 0.833),
        "neurobiology": make_region(0.40, 0.60, 0.50, 0.667),
        # Mathematics subs (2x2 grid)
        "calculus": make_region(0.60, 0.80, 0.75, 1.0),
        "linear-algebra": make_region(0.80, 1.0, 0.75, 1.0),
        "number-theory": make_region(0.60, 0.80, 0.50, 0.75),
        "probability-statistics": make_region(0.80, 1.0, 0.50, 0.75),
    }

    parent_map = {
        "astrophysics": "physics",
        "quantum-physics": "physics",
        "european-art-history": "art-history",
        "chinese-art-history": "art-history",
        "molecular-cell-biology": "biology",
        "genetics": "biology",
        "cognitive-neuroscience": "neuroscience",
        "computational-neuroscience": "neuroscience",
        "neurobiology": "neuroscience",
        "calculus": "mathematics",
        "linear-algebra": "mathematics",
        "number-theory": "mathematics",
        "probability-statistics": "mathematics",
    }

    display_names = {
        "all": "All (General)",
        "physics": "Physics",
        "neuroscience": "Neuroscience",
        "mathematics": "Mathematics",
        "art-history": "Art History",
        "biology": "Biology",
        "astrophysics": "Astrophysics",
        "quantum-physics": "Quantum Physics",
        "european-art-history": "European Art History",
        "chinese-art-history": "Chinese Art History",
        "molecular-cell-biology": "Molecular and Cell Biology",
        "genetics": "Genetics",
        "cognitive-neuroscience": "Cognitive Neuroscience",
        "computational-neuroscience": "Computational Neuroscience",
        "neurobiology": "Neurobiology",
        "calculus": "Calculus",
        "linear-algebra": "Linear Algebra",
        "number-theory": "Number Theory",
        "probability-statistics": "Probability and Statistics",
    }

    domains = []

    # "All"
    all_region = make_region(0, 1, 0, 1)
    domains.append(
        {
            "id": "all",
            "name": "All (General)",
            "parent_id": None,
            "level": "all",
            "region": all_region,
            "grid_size": 39,
            "question_count": 50,
        }
    )
    n = count_articles_in_region(articles, all_region)
    print(f"  {'All (General)':30s} [0.00,1.00]x[0.00,1.00]  articles={n:>6,}  grid=39")

    # General
    for did, region in general_regions.items():
        n = count_articles_in_region(articles, region)
        gs = compute_grid_size(region)
        domains.append(
            {
                "id": did,
                "name": display_names[did],
                "parent_id": None,
                "level": "general",
                "region": region,
                "grid_size": gs,
                "question_count": 50,
            }
        )
        r = region
        print(
            f"  {display_names[did]:30s} [{r['x_min']:.2f},{r['x_max']:.2f}]x"
            f"[{r['y_min']:.2f},{r['y_max']:.2f}]  articles={n:>6,}  grid={gs}"
        )

    # Sub
    for did, region in sub_regions.items():
        n = count_articles_in_region(articles, region)
        gs = compute_grid_size(region)
        domains.append(
            {
                "id": did,
                "name": display_names[did],
                "parent_id": parent_map[did],
                "level": "sub",
                "region": region,
                "grid_size": gs,
                "question_count": 50,
            }
        )
        r = region
        print(
            f"    {display_names[did]:28s} [{r['x_min']:.2f},{r['x_max']:.2f}]x"
            f"[{r['y_min']:.2f},{r['y_max']:.2f}]  articles={n:>6,}  grid={gs}"
        )

    return domains


def validate_domains(domains, articles):
    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    errors = []

    if len(domains) != 19:
        errors.append(f"Expected 19 domains, got {len(domains)}")

    ids = [d["id"] for d in domains]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate domain IDs")

    domain_map = {d["id"]: d for d in domains}

    for d in domains:
        r = d["region"]
        if r["x_min"] >= r["x_max"] or r["y_min"] >= r["y_max"]:
            errors.append(f"{d['id']}: invalid region")
        if r["x_min"] < 0 or r["x_max"] > 1 or r["y_min"] < 0 or r["y_max"] > 1:
            errors.append(f"{d['id']}: region outside [0,1]")

        if d["level"] == "sub":
            parent = domain_map.get(d["parent_id"])
            if not parent:
                errors.append(f"{d['id']}: parent {d['parent_id']} not found")
            else:
                pr = parent["region"]
                if (
                    r["x_min"] < pr["x_min"] - 0.001
                    or r["x_max"] > pr["x_max"] + 0.001
                    or r["y_min"] < pr["y_min"] - 0.001
                    or r["y_max"] > pr["y_max"] + 0.001
                ):
                    errors.append(f"{d['id']}: outside parent {d['parent_id']}")

        n = count_articles_in_region(articles, r)
        if n < 100 and d["level"] != "all":
            errors.append(f"{d['id']}: only {n} articles (need >= 100)")

    if errors:
        print(f"\n✗ {len(errors)} ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return False

    n_gen = sum(1 for d in domains if d["level"] == "general")
    n_sub = sum(1 for d in domains if d["level"] == "sub")
    print(f"\n✓ All {len(domains)} domains valid")
    print(f"  1 all + {n_gen} general + {n_sub} sub")
    print(f"  All sub-domains within parent bounds")
    return True


def save_index(domains):
    output_dir = PROJECT_ROOT / "data" / "domains"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "index.json"
    with open(output_file, "w") as f:
        json.dump({"schema_version": "1.0.0", "domains": domains}, f, indent=2)
    print(f"\nSaved {output_file} ({output_file.stat().st_size / 1024:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Define 19 domain regions")
    parser.parse_args()

    print("=" * 60)
    print("DEFINE DOMAINS")
    print("=" * 60)

    articles = load_articles()
    print()
    domains = define_all_domains(articles)
    valid = validate_domains(domains, articles)
    if not valid:
        sys.exit(1)
    save_index(domains)


if __name__ == "__main__":
    main()
