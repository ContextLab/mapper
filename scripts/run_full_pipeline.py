#!/usr/bin/env python3
"""
Full Multi-Level Knowledge Map Pipeline

This script orchestrates the complete pipeline to generate a 5-level hierarchical
knowledge map using GPT-5-nano Batch API.

Pipeline Steps:
1. Rebuild UMAP (250K articles, ~30-60 min)
2. Find optimal rectangle
3. Export level-0 articles
4. Generate heatmap labels (GPT-5-nano batched)
5. Extract level-0 concepts (GPT-5-nano batched)
6. Generate level-0 questions (GPT-5-nano batched)
7. Generate levels 1-4 (iterative broadening)
8. Merge all levels into final outputs
9. Validate results

Usage:
    python scripts/run_full_pipeline.py [options]

Options:
    --skip-umap             Skip UMAP rebuild (use existing)
    --skip-rectangle        Skip optimal rectangle finding
    --skip-labels           Skip heatmap label generation
    --skip-level-0          Skip level-0 generation
    --levels START END      Generate specific levels (e.g., --levels 1 3)
    --skip-merge            Skip final data merging
    --dry-run               Show what would run without executing

Related to Issue #13
"""

import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime


def print_header(text):
    """Print formatted header"""
    print()
    print("=" * 80)
    print(text)
    print("=" * 80)
    print()


def print_step(step_num, total_steps, description):
    """Print step header"""
    print()
    print("=" * 80)
    print(f"STEP {step_num}/{total_steps}: {description}")
    print("=" * 80)
    print()


def run_command(cmd, description, dry_run=False):
    """Run a command and handle errors"""
    print(f"Command: {' '.join(cmd)}")
    print()

    if dry_run:
        print("[DRY RUN] Would execute command")
        return True

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"\n✗ Error: {description} failed with code {result.returncode}")
        print("Pipeline stopped.")
        return False

    print(f"\n✓ {description} completed successfully")
    return True


def check_file_exists(filepath, description):
    """Check if required file exists"""
    if not Path(filepath).exists():
        print(f"✗ Error: Required file missing: {filepath}")
        print(f"   {description}")
        return False
    return True


def should_skip_step(output_files, force_flag, global_force):
    """
    Check if step should be skipped based on existing outputs.

    Args:
        output_files: List of output file paths to check
        force_flag: Step-specific force flag (e.g., args.force_umap)
        global_force: Global force flag (args.force)

    Returns:
        (should_skip, reason) tuple
    """
    # If any force flag is set, don't skip
    if global_force or force_flag:
        return (False, "forced")

    # Check if all output files exist
    all_exist = all(Path(f).exists() for f in output_files)

    if all_exist:
        return (True, "outputs exist")
    else:
        return (False, "outputs missing")


def main():
    parser = argparse.ArgumentParser(
        description='Run full multi-level knowledge map pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (all steps)
  python scripts/run_full_pipeline.py

  # Skip UMAP rebuild (use existing)
  python scripts/run_full_pipeline.py --skip-umap

  # Generate only levels 1-2
  python scripts/run_full_pipeline.py --skip-level-0 --levels 1 2

  # Dry run (show what would execute)
  python scripts/run_full_pipeline.py --dry-run
        """
    )

    parser.add_argument('--skip-umap', action='store_true',
                       help='Skip UMAP rebuild (use existing)')
    parser.add_argument('--skip-rectangle', action='store_true',
                       help='Skip optimal rectangle finding')
    parser.add_argument('--skip-labels', action='store_true',
                       help='Skip heatmap label generation')
    parser.add_argument('--skip-level-0', action='store_true',
                       help='Skip level-0 generation')
    parser.add_argument('--levels', nargs=2, type=int, metavar=('START', 'END'),
                       help='Generate specific levels (e.g., --levels 1 3)')
    parser.add_argument('--skip-merge', action='store_true',
                       help='Skip final data merging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would run without executing')

    # Force flags for idempotency
    parser.add_argument('--force', action='store_true',
                       help='Force rerun all steps (ignore existing outputs)')
    parser.add_argument('--force-umap', action='store_true',
                       help='Force UMAP rebuild even if outputs exist')
    parser.add_argument('--force-rectangle', action='store_true',
                       help='Force rectangle finding even if outputs exist')
    parser.add_argument('--force-labels', action='store_true',
                       help='Force label generation even if outputs exist')
    parser.add_argument('--force-level', action='store_true',
                       help='Force level generation even if outputs exist')
    parser.add_argument('--force-simplify', action='store_true',
                       help='Force question simplification even if outputs exist')
    parser.add_argument('--force-merge', action='store_true',
                       help='Force data merging even if outputs exist')

    args = parser.parse_args()

    # Calculate total steps
    total_steps = 0
    if not args.skip_umap:
        total_steps += 1
    if not args.skip_rectangle:
        total_steps += 1
    if not args.skip_rectangle:
        total_steps += 1  # export articles
    if not args.skip_labels:
        total_steps += 1
    if not args.skip_level_0:
        total_steps += 1  # level 0 (unified concepts + questions)

    # Level 1-4 generation
    if args.levels:
        level_range = range(args.levels[0], args.levels[1] + 1)
    else:
        level_range = range(1, 5) if not args.skip_level_0 else range(1, 5)
    total_steps += len(level_range)

    # Question simplification for levels 2, 3, 4
    simplify_levels = [l for l in [2, 3, 4] if l in level_range or not args.skip_level_0]
    total_steps += len(simplify_levels)

    if not args.skip_merge:
        total_steps += 1

    # Print pipeline overview
    print_header("MULTI-LEVEL KNOWLEDGE MAP PIPELINE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total steps: {total_steps}")
    print()
    print("Pipeline configuration:")
    print(f"  UMAP rebuild: {'SKIP' if args.skip_umap else 'RUN'}")
    print(f"  Optimal rectangle: {'SKIP' if args.skip_rectangle else 'RUN'}")
    print(f"  Heatmap labels: {'SKIP' if args.skip_labels else 'RUN'}")
    print(f"  Level 0: {'SKIP' if args.skip_level_0 else 'RUN'}")
    print(f"  Levels 1-4: {list(level_range)}")
    print(f"  Data merging: {'SKIP' if args.skip_merge else 'RUN'}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'EXECUTE'}")
    print()

    if args.dry_run:
        print("DRY RUN MODE: Commands will be displayed but not executed")
        print()

    current_step = 0

    # Step: Rebuild UMAP (250K articles)
    if not args.skip_umap:
        current_step += 1
        print_step(current_step, total_steps, "Rebuild UMAP (250K articles)")

        # Check if outputs already exist
        umap_outputs = ['umap_coords.pkl', 'data/umap_reducer.pkl', 'data/umap_bounds.pkl']
        should_skip, reason = should_skip_step(umap_outputs, args.force_umap, args.force)

        if should_skip:
            print(f"⏭️  Skipping UMAP rebuild - {reason}")
            print(f"   Existing files: {', '.join(umap_outputs)}")
            print(f"   Use --force-umap or --force to rerun")
            print()
        else:
            print("This step fits UMAP on all 250K Wikipedia articles.")
            print("Estimated time: 30-60 minutes")
            if reason == "forced":
                print(f"⚠️  Forcing rebuild (will overwrite existing files)")
            print()

            if not run_command(
                ['python3', 'scripts/rebuild_umap.py'],
                "UMAP rebuild",
                args.dry_run
            ):
                return 1

    # Step: Find optimal rectangle
    if not args.skip_rectangle:
        current_step += 1
        print_step(current_step, total_steps, "Find optimal coverage rectangle")

        # Check if outputs already exist
        rectangle_outputs = ['optimal_rectangle.json']
        should_skip, reason = should_skip_step(rectangle_outputs, args.force_rectangle, args.force)

        if should_skip:
            print(f"⏭️  Skipping rectangle finding - {reason}")
            print(f"   Existing files: {', '.join(rectangle_outputs)}")
            print(f"   Use --force-rectangle or --force to rerun")
            print()
        else:
            print("This step finds the optimal rectangle that maximizes article coverage.")
            print("Estimated time: 5-10 minutes")
            if reason == "forced":
                print(f"⚠️  Forcing rebuild (will overwrite existing files)")
            print()

            if not run_command(
                ['python3', 'scripts/find_optimal_coverage_rectangle.py'],
                "Optimal rectangle finding",
                args.dry_run
            ):
                return 1

    # Step: Export level-0 articles
    if not args.skip_rectangle:
        current_step += 1
        print_step(current_step, total_steps, "Export level-0 articles")

        # Check if outputs already exist
        article_outputs = ['wikipedia_articles_level_0.json']
        should_skip, reason = should_skip_step(article_outputs, args.force_rectangle, args.force)

        if should_skip:
            print(f"⏭️  Skipping article export - {reason}")
            print(f"   Existing files: {', '.join(article_outputs)}")
            print(f"   Use --force-rectangle or --force to rerun")
            print()
        else:
            print("This step exports articles within the optimal rectangle.")
            print("Estimated time: 1-2 minutes")
            if reason == "forced":
                print(f"⚠️  Forcing rebuild (will overwrite existing files)")
            print()

            if not run_command(
                ['python3', 'scripts/export_wikipedia_articles.py'],
                "Article export",
                args.dry_run
            ):
                return 1

    # Step: Generate heatmap labels
    if not args.skip_labels:
        current_step += 1
        print_step(current_step, total_steps, "Generate heatmap cell labels (GPT-5-nano)")

        # Check if outputs already exist
        label_outputs = ['heatmap_cell_labels.json']
        should_skip, reason = should_skip_step(label_outputs, args.force_labels, args.force)

        if should_skip:
            print(f"⏭️  Skipping label generation - {reason}")
            print(f"   Existing files: {', '.join(label_outputs)}")
            print(f"   Use --force-labels or --force to rerun")
            print()
        else:
            print("This step generates semantic labels for 1,521 heatmap cells.")
            print("Uses: OpenAI Batch API with prompt caching")
            print("Estimated time: 1-2 hours")
            print("Estimated cost: $0.01-0.02")
            if reason == "forced":
                print(f"⚠️  Forcing rebuild (will overwrite existing files)")
            print()

            if not run_command(
                ['python3', 'scripts/generate_heatmap_labels_gpt5.py'],
                "Heatmap label generation",
                args.dry_run
            ):
                return 1

    # Step: Generate level 0 (unified script)
    if not args.skip_level_0:
        current_step += 1
        print_step(current_step, total_steps, "Generate level 0 (concepts + questions)")

        # Check if outputs already exist
        level0_outputs = ['level_0_concepts.json', 'cell_questions_level_0.json']
        should_skip, reason = should_skip_step(level0_outputs, args.force_level, args.force)

        if should_skip:
            print(f"⏭️  Skipping level 0 generation - {reason}")
            print(f"   Existing files: {', '.join(level0_outputs)}")
            print(f"   Use --force-level or --force to rerun")
            print()
        else:
            print("This step processes existing Wikipedia articles to:")
            print("  1. Extract 1-3 concepts per article (GPT-5-nano)")
            print("  2. Generate 1 question per suitable concept (GPT-5-nano)")
            print("Uses: OpenAI Batch API with prompt caching")
            print("Estimated time: 2-3 hours")
            print("Estimated cost: $0.02-0.05")
            if reason == "forced":
                print(f"⚠️  Forcing rebuild (will overwrite existing files)")
            print()

            if not run_command(
                ['python3', '-u', 'scripts/generate_level_n.py', '--level', '0'],
                "Level 0 generation",
                args.dry_run
            ):
                return 1

    # Steps: Generate levels 1-4
    for level in level_range:
        current_step += 1
        print_step(current_step, total_steps, f"Generate level {level} (broader concepts)")

        print(f"This step generates progressively broader content for level {level}:")
        print("  1. Suggest broader Wikipedia articles (GPT-5-nano)")
        print("  2. Download articles")
        print("  3. Generate embeddings and project to UMAP")
        print("  4. Extract concepts (GPT-5-nano)")
        print("  5. Generate questions (GPT-5-nano)")
        print(f"Estimated time: 2-3 hours per level")
        print(f"Estimated cost: ~$0.50 per level")
        print()

        if not run_command(
            ['python3', '-u', 'scripts/generate_level_n.py', '--level', str(level)],
            f"Level {level} generation",
            args.dry_run
        ):
            return 1

    # Step: Simplify questions for levels 2, 3, 4
    simplify_levels = [l for l in [2, 3, 4] if l in level_range or not args.skip_level_0]
    for level in simplify_levels:
        current_step += 1
        level_name = {4: "middle school", 3: "high school", 2: "undergraduate"}[level]
        print_step(current_step, total_steps, f"Simplify level {level} questions ({level_name})")

        print(f"This step simplifies level {level} questions to {level_name} reading level:")
        print("  - Pass 1: Simplify existing questions with readability validation")
        print("  - Pass 2: Generate new questions if Pass 1 fails")
        print("  - Uses LaTeX notation for math ($x^2$, $\\frac{1}{2}$, etc.)")
        print(f"Estimated time: 15-30 minutes")
        print(f"Estimated cost: ~$0.05-0.10")
        print()

        if not run_command(
            ['python3', '-u', 'scripts/simplify_questions.py', '--level', str(level)],
            f"Level {level} simplification",
            args.dry_run
        ):
            return 1

    # Step: Merge all levels
    if not args.skip_merge:
        current_step += 1
        print_step(current_step, total_steps, "Merge multi-level data")

        print("This step merges all level outputs into final unified files.")
        print("Outputs:")
        print("  - wikipedia_articles.json (deduplicated)")
        print("  - cell_questions.json (merged by cell)")
        print("Estimated time: 1-2 minutes")
        print()

        if not run_command(
            ['python3', 'scripts/merge_multi_level_data.py'],
            "Data merging",
            args.dry_run
        ):
            return 1

    # Pipeline complete
    print_header("✓ PIPELINE COMPLETE")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not args.dry_run:
        print("Generated files:")
        print()
        print("UMAP & Coordinates:")
        print("  - umap_coords.pkl - Full UMAP coordinates (250K articles)")
        print("  - data/umap_reducer.pkl - Trained UMAP model")
        print("  - data/umap_bounds.pkl - Coordinate bounds")
        print("  - knowledge_map.pkl - Complete knowledge map")
        print()
        print("Level 0:")
        print("  - optimal_rectangle.json - Optimal coverage rectangle")
        print("  - wikipedia_articles.json - Base articles (with coordinates)")
        print("  - heatmap_cell_labels.json - Semantic cell labels")
        print("  - level_0_concepts.json - Extracted concepts")
        print("  - cell_questions_level_0.json - Level-0 questions")
        print("  - wikipedia_articles_level_0.json - Copy of base articles")
        print()
        print("Levels 1-4:")
        for level in level_range:
            print(f"  - wikipedia_articles_level_{level}.json")
            print(f"  - level_{level}_concepts.json")
            print(f"  - cell_questions_level_{level}.json")
        print()
        print("Final Merged Outputs:")
        print("  - wikipedia_articles.json - All articles (deduplicated)")
        print("  - cell_questions.json - All questions (merged by cell)")
        print("  - notes/merge_validation_report.json - Validation results")
        print()
        print("Next steps:")
        print("  1. Review validation report: cat notes/merge_validation_report.json")
        print("  2. View visualization: python -m http.server 8000")
        print("     Then open: http://localhost:8000/index.html")
    else:
        print("DRY RUN completed. No files were modified.")
        print("Run without --dry-run to execute the pipeline.")

    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
