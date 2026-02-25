#!/usr/bin/env python3
"""
Define 50 domain regions in embedding space.

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
  ├─ Neuroscience           — general
  │  ├─ Cognitive Neuroscience  — sub
  │  ├─ Computational Neuroscience — sub
  │  └─ Neurobiology        — sub
  ├─ Mathematics            — general
  │  ├─ Calculus             — sub
  │  ├─ Linear Algebra       — sub
  │  ├─ Number Theory        — sub
  │  └─ Probability and Statistics — sub
  ├─ Computer Science        — general
  │  ├─ AI and Machine Learning — sub
  │  ├─ Theory of Computation   — sub
  │  └─ Algorithms              — sub
  ├─ Art History            — general
  │  ├─ European Art History — sub
  │  └─ Chinese Art History  — sub
  ├─ Biology                — general
  │  ├─ Molecular and Cell Biology — sub
  │  └─ Genetics            — sub
  ├─ Psychology              — general
  │  ├─ Cognitive Psychology   — sub
  │  ├─ Social Psychology      — sub
  │  ├─ Developmental Psychology — sub
  │  └─ Clinical Psychology    — sub
  ├─ Philosophy              — general
  │  ├─ Ethics                — sub
  │  ├─ Philosophy of Mind    — sub
  │  ├─ Logic                 — sub
  │  └─ Metaphysics           — sub
  ├─ World History           — general
  │  ├─ US History            — sub
  │  ├─ European History      — sub
  │  └─ Asian History         — sub
  ├─ Economics               — general
  │  ├─ Microeconomics        — sub
  │  └─ Macroeconomics        — sub
  ├─ Linguistics             — general
  │  ├─ Syntax                — sub
  │  ├─ Semantics             — sub
  │  └─ Computational Linguistics — sub
  ├─ Sociology               — general
  │  ├─ Political Sociology   — sub
  │  └─ Criminology           — sub
  └─ Archaeology             — general
     ├─ Prehistoric Archaeology — sub
     └─ Forensic Archaeology   — sub

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
    Define 50 domain regions by tiling the UMAP space.

    Layout (13 general domains — non-overlapping tiles):

      y=1.0 +------+------+------+------+
            |Phys  |Neuro |Math  | CS   |
            |0-0.25|.25-.5|.5-.75|.75-1 |
      y=0.75+------+------+------+------+
            | Art  | Bio  |Psych |Philos|
            |0-0.25|.25-.5|.5-.75|.75-1 |
      y=0.5 +------+------+------+------+
            |World Hist|Econ  |Linguist |
            | 0-0.33   |.33-.67| .67-1  |
      y=0.25+----------+------+---------+
            | Sociology | Archaeology   |
            |  0-0.5    |   0.5-1       |
      y=0.0 +-----------+---------------+
           x=0                         x=1.0
    """

    general_regions = {
        # Row 4 (top): y=0.75-1.0
        "physics": make_region(0.0, 0.25, 0.75, 1.0),
        "neuroscience": make_region(0.25, 0.50, 0.75, 1.0),
        "mathematics": make_region(0.50, 0.75, 0.75, 1.0),
        "computer-science": make_region(0.75, 1.0, 0.75, 1.0),
        # Row 3: y=0.5-0.75
        "art-history": make_region(0.0, 0.25, 0.50, 0.75),
        "biology": make_region(0.25, 0.50, 0.50, 0.75),
        "psychology": make_region(0.50, 0.75, 0.50, 0.75),
        "philosophy": make_region(0.75, 1.0, 0.50, 0.75),
        # Row 2: y=0.25-0.5
        "world-history": make_region(0.0, 0.333, 0.25, 0.50),
        "economics": make_region(0.333, 0.667, 0.25, 0.50),
        "linguistics": make_region(0.667, 1.0, 0.25, 0.50),
        # Row 1 (bottom): y=0.0-0.25
        "sociology": make_region(0.0, 0.50, 0.0, 0.25),
        "archaeology": make_region(0.50, 1.0, 0.0, 0.25),
    }

    sub_regions = {
        # Physics subs (horizontal split)
        "astrophysics": make_region(0.0, 0.25, 0.875, 1.0),
        "quantum-physics": make_region(0.0, 0.25, 0.75, 0.875),
        # Neuroscience subs (horizontal split into 3)
        "cognitive-neuroscience": make_region(0.25, 0.50, 0.917, 1.0),
        "computational-neuroscience": make_region(0.25, 0.50, 0.833, 0.917),
        "neurobiology": make_region(0.25, 0.50, 0.75, 0.833),
        # Mathematics subs (2x2 grid)
        "calculus": make_region(0.50, 0.625, 0.875, 1.0),
        "linear-algebra": make_region(0.625, 0.75, 0.875, 1.0),
        "number-theory": make_region(0.50, 0.625, 0.75, 0.875),
        "probability-statistics": make_region(0.625, 0.75, 0.75, 0.875),
        # Computer Science subs (horizontal split into 3)
        "artificial-intelligence-ml": make_region(0.75, 1.0, 0.917, 1.0),
        "theory-of-computation": make_region(0.75, 1.0, 0.833, 0.917),
        "algorithms": make_region(0.75, 1.0, 0.75, 0.833),
        # Art History subs (vertical split)
        "european-art-history": make_region(0.0, 0.125, 0.50, 0.75),
        "chinese-art-history": make_region(0.125, 0.25, 0.50, 0.75),
        # Biology subs (vertical split)
        "molecular-cell-biology": make_region(0.25, 0.375, 0.50, 0.75),
        "genetics": make_region(0.375, 0.50, 0.50, 0.75),
        # Psychology subs (2x2 grid)
        "cognitive-psychology": make_region(0.50, 0.625, 0.625, 0.75),
        "social-psychology": make_region(0.625, 0.75, 0.625, 0.75),
        "developmental-psychology": make_region(0.50, 0.625, 0.50, 0.625),
        "clinical-psychology": make_region(0.625, 0.75, 0.50, 0.625),
        # Philosophy subs (2x2 grid)
        "ethics": make_region(0.75, 0.875, 0.625, 0.75),
        "philosophy-of-mind": make_region(0.875, 1.0, 0.625, 0.75),
        "logic": make_region(0.75, 0.875, 0.50, 0.625),
        "metaphysics": make_region(0.875, 1.0, 0.50, 0.625),
        # World History subs (vertical split into 3)
        "us-history": make_region(0.0, 0.111, 0.25, 0.50),
        "european-history": make_region(0.111, 0.222, 0.25, 0.50),
        "asian-history": make_region(0.222, 0.333, 0.25, 0.50),
        # Economics subs (vertical split)
        "microeconomics": make_region(0.333, 0.50, 0.25, 0.50),
        "macroeconomics": make_region(0.50, 0.667, 0.25, 0.50),
        # Linguistics subs (horizontal split into 3)
        "syntax": make_region(0.667, 1.0, 0.417, 0.50),
        "semantics": make_region(0.667, 1.0, 0.333, 0.417),
        "computational-linguistics": make_region(0.667, 1.0, 0.25, 0.333),
        # Sociology subs (vertical split)
        "political-sociology": make_region(0.0, 0.25, 0.0, 0.25),
        "criminology": make_region(0.25, 0.50, 0.0, 0.25),
        # Archaeology subs (vertical split)
        "prehistoric-archaeology": make_region(0.50, 0.75, 0.0, 0.25),
        "forensic-archaeology": make_region(0.75, 1.0, 0.0, 0.25),
    }

    parent_map = {
        "astrophysics": "physics",
        "quantum-physics": "physics",
        "cognitive-neuroscience": "neuroscience",
        "computational-neuroscience": "neuroscience",
        "neurobiology": "neuroscience",
        "calculus": "mathematics",
        "linear-algebra": "mathematics",
        "number-theory": "mathematics",
        "probability-statistics": "mathematics",
        "artificial-intelligence-ml": "computer-science",
        "theory-of-computation": "computer-science",
        "algorithms": "computer-science",
        "european-art-history": "art-history",
        "chinese-art-history": "art-history",
        "molecular-cell-biology": "biology",
        "genetics": "biology",
        "cognitive-psychology": "psychology",
        "social-psychology": "psychology",
        "developmental-psychology": "psychology",
        "clinical-psychology": "psychology",
        "ethics": "philosophy",
        "philosophy-of-mind": "philosophy",
        "logic": "philosophy",
        "metaphysics": "philosophy",
        "us-history": "world-history",
        "european-history": "world-history",
        "asian-history": "world-history",
        "microeconomics": "economics",
        "macroeconomics": "economics",
        "syntax": "linguistics",
        "semantics": "linguistics",
        "computational-linguistics": "linguistics",
        "political-sociology": "sociology",
        "criminology": "sociology",
        "prehistoric-archaeology": "archaeology",
        "forensic-archaeology": "archaeology",
    }

    display_names = {
        "all": "All (General)",
        "physics": "Physics",
        "neuroscience": "Neuroscience",
        "mathematics": "Mathematics",
        "computer-science": "Computer Science",
        "art-history": "Art History",
        "biology": "Biology",
        "psychology": "Psychology",
        "philosophy": "Philosophy",
        "world-history": "World History",
        "economics": "Economics",
        "linguistics": "Linguistics",
        "sociology": "Sociology",
        "archaeology": "Archaeology",
        "astrophysics": "Astrophysics",
        "quantum-physics": "Quantum Physics",
        "cognitive-neuroscience": "Cognitive Neuroscience",
        "computational-neuroscience": "Computational Neuroscience",
        "neurobiology": "Neurobiology",
        "calculus": "Calculus",
        "linear-algebra": "Linear Algebra",
        "number-theory": "Number Theory",
        "probability-statistics": "Probability and Statistics",
        "artificial-intelligence-ml": "AI and Machine Learning",
        "theory-of-computation": "Theory of Computation",
        "algorithms": "Algorithms",
        "european-art-history": "European Art History",
        "chinese-art-history": "Chinese Art History",
        "molecular-cell-biology": "Molecular and Cell Biology",
        "genetics": "Genetics",
        "cognitive-psychology": "Cognitive Psychology",
        "social-psychology": "Social Psychology",
        "developmental-psychology": "Developmental Psychology",
        "clinical-psychology": "Clinical Psychology",
        "ethics": "Ethics",
        "philosophy-of-mind": "Philosophy of Mind",
        "logic": "Logic",
        "metaphysics": "Metaphysics",
        "us-history": "US History",
        "european-history": "European History",
        "asian-history": "Asian History",
        "microeconomics": "Microeconomics",
        "macroeconomics": "Macroeconomics",
        "syntax": "Syntax",
        "semantics": "Semantics",
        "computational-linguistics": "Computational Linguistics",
        "political-sociology": "Political Sociology",
        "criminology": "Criminology",
        "prehistoric-archaeology": "Prehistoric Archaeology",
        "forensic-archaeology": "Forensic Archaeology",
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

    if len(domains) != 50:
        errors.append(f"Expected 50 domains, got {len(domains)}")

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
    parser = argparse.ArgumentParser(description="Define 50 domain regions")
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
