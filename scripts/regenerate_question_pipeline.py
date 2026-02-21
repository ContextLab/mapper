#!/usr/bin/env python3
"""
Unified pipeline script for regenerating question embeddings and coordinates.

This script runs the complete pipeline to update question coordinates after
questions have been regenerated:

  1. Embed questions using google/embeddinggemma-300m
  2. Joint UMAP projection (articles + questions together)
  3. Apply density flattening (mu=0.75)
  4. Compute hierarchical bounding boxes
  5. Export domain bundles

Usage:
    python scripts/regenerate_question_pipeline.py
    python scripts/regenerate_question_pipeline.py --mu 0.5
    python scripts/regenerate_question_pipeline.py --skip-embed  # if embeddings already exist
    python scripts/regenerate_question_pipeline.py --skip-umap   # if UMAP already done
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def run_script(script_name: str, args: list = None, description: str = None):
    """Run a Python script and check for errors."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    desc = description or script_name
    print(f"\n{'=' * 70}")
    print(f"RUNNING: {desc}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 70}\n")

    start = time.time()
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\nERROR: {script_name} failed with return code {result.returncode}")
        return False

    print(f"\nCompleted {script_name} in {elapsed:.1f}s")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Run complete question regeneration pipeline"
    )
    parser.add_argument(
        "--mu",
        type=float,
        default=0.75,
        help="Flattening parameter (default: 0.75)",
    )
    parser.add_argument(
        "--skip-embed",
        action="store_true",
        help="Skip embedding step (use existing embeddings)",
    )
    parser.add_argument(
        "--skip-umap",
        action="store_true",
        help="Skip UMAP step (use existing coordinates)",
    )
    parser.add_argument(
        "--skip-flatten",
        action="store_true",
        help="Skip flattening step (use existing flattened coords)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be run without executing",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("QUESTION REGENERATION PIPELINE")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Parameters:")
    print(f"  mu: {args.mu}")
    print(f"  skip-embed: {args.skip_embed}")
    print(f"  skip-umap: {args.skip_umap}")
    print(f"  skip-flatten: {args.skip_flatten}")
    print()

    pipeline_start = time.time()
    steps_run = 0
    steps_skipped = 0

    # Step 1: Embed questions
    if not args.skip_embed:
        if args.dry_run:
            print("Would run: embed_questions.py")
        else:
            if not run_script("embed_questions.py", description="Step 1/5: Embed questions"):
                print("\nPipeline aborted due to error in embed_questions.py")
                sys.exit(1)
            steps_run += 1
    else:
        print("Skipping Step 1: embed_questions.py (--skip-embed)")
        steps_skipped += 1

    # Step 2: Joint UMAP projection
    if not args.skip_umap:
        if args.dry_run:
            print("Would run: rebuild_umap_v2.py")
        else:
            if not run_script("rebuild_umap_v2.py", description="Step 2/5: Joint UMAP projection"):
                print("\nPipeline aborted due to error in rebuild_umap_v2.py")
                sys.exit(1)
            steps_run += 1
    else:
        print("Skipping Step 2: rebuild_umap_v2.py (--skip-umap)")
        steps_skipped += 1

    # Step 3: Density flattening
    if not args.skip_flatten:
        flatten_args = ["--mu", str(args.mu)]
        if args.dry_run:
            print(f"Would run: flatten_coordinates.py {' '.join(flatten_args)}")
        else:
            if not run_script("flatten_coordinates.py", flatten_args,
                            f"Step 3/5: Density flattening (mu={args.mu})"):
                print("\nPipeline aborted due to error in flatten_coordinates.py")
                sys.exit(1)
            steps_run += 1
    else:
        print("Skipping Step 3: flatten_coordinates.py (--skip-flatten)")
        steps_skipped += 1

    # Step 4: Compute bounding boxes
    if args.dry_run:
        print("Would run: compute_bounding_boxes.py")
    else:
        if not run_script("compute_bounding_boxes.py", description="Step 4/5: Compute bounding boxes"):
            print("\nPipeline aborted due to error in compute_bounding_boxes.py")
            sys.exit(1)
        steps_run += 1

    # Step 5: Export domain bundles
    if args.dry_run:
        print("Would run: export_domain_bundles.py")
    else:
        if not run_script("export_domain_bundles.py", description="Step 5/5: Export domain bundles"):
            print("\nPipeline aborted due to error in export_domain_bundles.py")
            sys.exit(1)
        steps_run += 1

    pipeline_elapsed = time.time() - pipeline_start

    print(f"\n{'=' * 70}")
    print("PIPELINE COMPLETE")
    print(f"{'=' * 70}")
    print(f"Steps run: {steps_run}")
    print(f"Steps skipped: {steps_skipped}")
    print(f"Total time: {pipeline_elapsed / 60:.1f} minutes")
    print(f"Finished: {datetime.now()}")
    print()
    print("Output files updated:")
    print("  - embeddings/question_embeddings*.pkl")
    print("  - embeddings/umap_*_coords.pkl")
    print("  - embeddings/umap_*_coords_flat.pkl")
    print("  - data/domains/index.json (bounding boxes)")
    print("  - data/domains/{domain_id}.json (questions with coords)")


if __name__ == "__main__":
    main()
