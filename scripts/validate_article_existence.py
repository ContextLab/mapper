#!/usr/bin/env python3
"""
Validate that all source_article references in generated questions
correspond to real Wikipedia articles via the Wikipedia REST API.

Usage:
    python scripts/validate_article_existence.py
    python scripts/validate_article_existence.py --domain physics
    python scripts/validate_article_existence.py --fix  # Remove questions with invalid articles

Exit codes:
    0: All articles validated
    1: Some articles not found (printed to stderr)
"""

import json
import os
import sys
import time
import argparse
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, Set

os.environ["TOKENIZERS_PARALLELISM"] = "false"

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"
REQUEST_DELAY = 0.2  # 200ms between requests to avoid Wikipedia rate limits


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate Wikipedia article existence for generated questions"
    )
    parser.add_argument(
        "--domain",
        type=str,
        default=None,
        help="Validate only a specific domain (by ID)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Remove questions with non-existent source articles",
    )
    return parser.parse_args()


def check_article_exists(title: str, max_retries: int = 3) -> bool:
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"{WIKIPEDIA_API_BASE}/{encoded}"

    for attempt in range(max_retries):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "WikipediaKnowledgeMap/1.0 (educational project)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if e.code == 429 and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            print(f"  HTTP {e.code} for '{title}'", file=sys.stderr)
            return False
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"  Error checking '{title}': {e}", file=sys.stderr)
            return False
    return False


def validate_domain_questions(
    questions_path: Path, domain_id: str, fix: bool = False
) -> Dict[str, Any]:
    """Validate all source articles in a domain's questions file."""
    if not questions_path.exists():
        return {
            "domain": domain_id,
            "status": "missing",
            "total": 0,
            "valid": 0,
            "invalid": [],
        }

    with open(questions_path, "r") as f:
        questions = json.load(f)

    if not questions:
        return {
            "domain": domain_id,
            "status": "empty",
            "total": 0,
            "valid": 0,
            "invalid": [],
        }

    # Collect unique article titles
    titles = set()
    for q in questions:
        if q.get("source_article"):
            titles.add(q["source_article"])

    print(f"  Checking {len(titles)} unique articles for {domain_id}...")

    valid_titles: Set[str] = set()
    invalid_titles: Set[str] = set()

    for i, title in enumerate(sorted(titles)):
        exists = check_article_exists(title)
        if exists:
            valid_titles.add(title)
        else:
            invalid_titles.add(title)
            print(f"    ✗ Not found: '{title}'", file=sys.stderr)

        if (i + 1) % 20 == 0:
            print(f"    Checked {i + 1}/{len(titles)}...")

        time.sleep(REQUEST_DELAY)

    # Fix mode: remove questions with invalid articles
    if fix and invalid_titles:
        original_count = len(questions)
        questions = [
            q for q in questions if q.get("source_article") not in invalid_titles
        ]
        removed = original_count - len(questions)
        print(f"  Removed {removed} questions with invalid articles")

        with open(questions_path, "w") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

    return {
        "domain": domain_id,
        "status": "validated",
        "total": len(titles),
        "valid": len(valid_titles),
        "invalid": sorted(invalid_titles),
    }


def main():
    args = parse_args()

    project_root = Path(__file__).parent.parent
    domains_path = project_root / "data" / "domains" / "index.json"
    output_dir = project_root / "data" / "domains"

    print("=" * 60)
    print("WIKIPEDIA ARTICLE EXISTENCE VALIDATION")
    print("=" * 60)
    print()

    with open(domains_path, "r") as f:
        domains = json.load(f)["domains"]

    if args.domain:
        domains = [d for d in domains if d["id"] == args.domain]
        if not domains:
            print(f"Error: Domain '{args.domain}' not found")
            sys.exit(1)

    results = []
    total_valid = 0
    total_invalid = 0

    for domain in domains:
        domain_id = domain["id"]
        questions_path = output_dir / f"{domain_id}_questions.json"

        result = validate_domain_questions(questions_path, domain_id, fix=args.fix)
        results.append(result)
        total_valid += result["valid"]
        total_invalid += len(result["invalid"])

    print(f"\n{'=' * 60}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 60}")

    for r in results:
        if r["status"] == "missing":
            print(f"  ⏭ {r['domain']}: no questions file")
        elif r["status"] == "empty":
            print(f"  ⏭ {r['domain']}: empty")
        else:
            status = "✓" if not r["invalid"] else "✗"
            print(f"  {status} {r['domain']}: {r['valid']}/{r['total']} valid", end="")
            if r["invalid"]:
                print(f" ({len(r['invalid'])} invalid)")
            else:
                print()

    print(f"\n  Total: {total_valid} valid, {total_invalid} invalid")

    if total_invalid > 0:
        print("\n  Run with --fix to remove questions with invalid articles")
        sys.exit(1)
    else:
        print("\n  ✓ All articles validated!")


if __name__ == "__main__":
    main()
