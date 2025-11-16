#!/usr/bin/env python3
"""
Full Knowledge Map Pipeline

This script runs the complete pipeline to generate a knowledge map visualization:
1. Generate question embeddings
2. Project Wikipedia articles and questions to 2D UMAP space
3. Filter articles within question bounding box
4. Generate heatmap cell labels using LLM
5. Export all visualization data to JSON

Usage:
    python scripts/run_full_pipeline.py [--skip-embeddings] [--skip-export] [--skip-labels]

Options:
    --skip-embeddings    Skip question embedding generation (use existing)
    --skip-export       Skip Wikipedia article export (use existing)
    --skip-labels       Skip heatmap label generation (use existing)
    --grid-size N       Heatmap grid size (default: 40)
    --k N              Number of nearest neighbors for labeling (default: 10)
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors"""
    print("=" * 80)
    print(f"{description}")
    print("=" * 80)
    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"\n✗ Error: {description} failed with code {result.returncode}")
        sys.exit(1)

    print(f"\n✓ {description} completed successfully")
    print()


def main():
    parser = argparse.ArgumentParser(description='Run full knowledge map pipeline')
    parser.add_argument('--skip-embeddings', action='store_true',
                       help='Skip question embedding generation')
    parser.add_argument('--skip-export', action='store_true',
                       help='Skip Wikipedia article export')
    parser.add_argument('--skip-labels', action='store_true',
                       help='Skip heatmap label generation')
    parser.add_argument('--grid-size', type=int, default=40,
                       help='Heatmap grid size (default: 40)')
    parser.add_argument('--k', type=int, default=10,
                       help='Number of nearest neighbors for labeling (default: 10)')

    args = parser.parse_args()

    print("=" * 80)
    print("KNOWLEDGE MAP GENERATION PIPELINE")
    print("=" * 80)
    print()
    print("This pipeline will:")
    print("  1. Generate question embeddings (if not skipped)")
    print("  2. Export Wikipedia articles with UMAP coordinates")
    print("  3. Generate heatmap cell labels using LLM")
    print()

    # Step 1: Generate question embeddings
    if not args.skip_embeddings:
        run_command(
            ['python3', 'scripts/generate_question_embeddings.py'],
            "Step 1: Generating question embeddings"
        )
    else:
        print("Skipping question embedding generation (--skip-embeddings)")
        print()

    # Step 2: Export Wikipedia articles
    if not args.skip_export:
        run_command(
            ['python3', 'scripts/export_wikipedia_articles.py'],
            "Step 2: Exporting Wikipedia articles and questions"
        )
    else:
        print("Skipping Wikipedia article export (--skip-export)")
        print()

    # Step 3: Generate heatmap labels
    if not args.skip_labels:
        run_command(
            ['python3', 'scripts/generate_heatmap_labels.py',
             '--grid-size', str(args.grid_size),
             '--k', str(args.k)],
            "Step 3: Generating heatmap cell labels"
        )
    else:
        print("Skipping heatmap label generation (--skip-labels)")
        print()

    # Summary
    print("=" * 80)
    print("✓ PIPELINE COMPLETE")
    print("=" * 80)
    print()
    print("Generated files:")
    print("  - embeddings/question_embeddings.pkl")
    print("  - wikipedia_articles.json")
    print("  - question_coordinates.json")
    print("  - questions.json (updated coordinates)")
    print("  - heatmap_cell_labels.json")
    print()
    print("You can now view the visualization by opening index.html in a web browser")
    print("(make sure to serve it via HTTP, e.g., python -m http.server 8000)")
    print()


if __name__ == '__main__':
    main()
